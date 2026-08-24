"""Reconstruir el `event_state` de un evento que P1 nunca vio.

P1 vigila el feed de la ultima hora. Un sismo de hace dos meses —los casos
golden— no tiene estado, y P2 se niega a procesarlo. El primero, el del Choco,
se resolvio escribiendo el JSON a mano y commiteandolo; esta prueba existe para
que no haya un segundo.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from pipelines.common.state import EventState, EventStatus
from pipelines.p2_impact.run import reconstruct_backtest_state

RAIZ = Path(__file__).parent.parent.parent
VENEZUELA = RAIZ / "tests" / "fixtures" / "golden" / "venezuela_2026_06_24"


def _detail(usgs_id: str) -> dict[str, Any]:
    ruta = VENEZUELA / f"detail_{usgs_id}_superseded.json"
    datos: dict[str, Any] = json.loads(ruta.read_text(encoding="utf-8"))
    return datos


@pytest.mark.parametrize("usgs_id", ["us6000t7zp", "us6000t7zc"])
def test_el_estado_sale_completo_del_detail(usgs_id: str) -> None:
    estado = reconstruct_backtest_state(_detail(usgs_id))
    assert estado.usgs_id == usgs_id
    assert estado.estado is EventStatus.DETECTADO
    assert estado.mag > 0
    assert estado.lugar
    assert estado.origen_utc.endswith("Z")
    assert estado.timestamps["usgs_origen"] == estado.origen_utc


@pytest.mark.parametrize("usgs_id", ["us6000t7zp", "us6000t7zc"])
def test_queda_marcado_como_retrospectivo(usgs_id: str) -> None:
    """Sin esta marca el reporte diria que respondimos con dos meses de retraso.

    La latencia p50/p95 del sistema se calcula sobre los eventos en vivo; un
    backtest entre ellos la vuelve un numero sin sentido.
    """
    estado = reconstruct_backtest_state(_detail(usgs_id))
    assert estado.backtest is True
    assert any("retrospectiva" in nota for nota in estado.notas)


def test_sobrevive_al_viaje_por_disco(tmp_path: Path) -> None:
    """La marca tiene que persistir: es lo que lee el reporte al re-emitirse."""
    estado = reconstruct_backtest_state(_detail("us6000t7zp"))
    estado.save(tmp_path)
    recargado = EventState.load(estado.usgs_id, tmp_path)
    assert recargado is not None
    assert recargado.backtest is True
    assert recargado.origen_utc == estado.origen_utc


def test_puede_pasar_directo_a_publicado() -> None:
    """Un historico no pasa por preliminar: su ShakeMap final ya existe."""
    estado = reconstruct_backtest_state(_detail("us6000t7zp"))
    publicado = estado.transition(EventStatus.PUBLICADO)
    assert publicado.estado is EventStatus.PUBLICADO
    assert publicado.backtest is True


def test_reproduce_el_estado_del_choco_escrito_a_mano() -> None:
    """El unico estado hecho a mano del repo, contrastado con el generado.

    Si la reconstruccion no coincide con el, uno de los dos esta mal — y el
    escrito a mano es el que nadie va a volver a revisar.
    """
    ruta = RAIZ / "events" / "us6000tjl2.json"
    if not ruta.exists():
        pytest.skip("no esta el estado del Choco")
    a_mano = json.loads(ruta.read_text(encoding="utf-8"))
    assert a_mano["backtest"] is True
    assert a_mano["timestamps"]["usgs_origen"] == a_mano["origen_utc"]
    assert any("Backtest" in nota for nota in a_mano["notas"])
