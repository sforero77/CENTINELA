"""G1 — Choco, M7.4, 10 de agosto de 2026 · `us6000tjl2` (§6.3).

Es el evento que motiva el proyecto: el pais tardo dias en saber cuanta
poblacion estaba en la zona de intensidad fuerte. La prueba fija que el sistema
habria respondido, y que la respuesta no cambia al refactorizar.

Las fixtures son productos reales congelados de ComCat, recortados a lo que el
pipeline consume (ver ``tests/fixtures/golden/README.md``).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from pipelines.common.state import EventState, EventStatus
from pipelines.p1_trigger.feed import parse_feed
from pipelines.p1_trigger.filters import evaluate
from pipelines.p1_trigger.run import run_trigger
from pipelines.p2_impact.products import parse_products
from pipelines.p2_impact.run import Action, decide

pytestmark = pytest.mark.golden

USGS_ID = "us6000tjl2"
#: Ultima version publicada de cada producto al congelar la fixture.
SHAKEMAP_VIGENTE = 7
GROUNDFAILURE_VIGENTE = 7


# --- Asercion (a): el trigger habria disparado -----------------------------


def test_el_trigger_habria_disparado(choco_feed: dict[str, Any]) -> None:
    candidatos = parse_feed(choco_feed)
    relevantes = [c for c in candidatos if evaluate(c)]
    assert [c.usgs_id for c in relevantes] == [USGS_ID]


def test_datos_del_evento(choco_feed: dict[str, Any]) -> None:
    evento = parse_feed(choco_feed)[0]
    assert evento.mag == 7.4
    assert evento.origen_utc == "2026-08-10T12:34:28Z"
    assert "San José del Palmar" in evento.lugar
    # 110 km: un evento profundo, no superficial. La profundidad importa para
    # la interpretacion del reporte y para elegir el caso de G3.
    assert evento.depth_km == pytest.approx(110.285)


def test_el_pipeline_completo_crea_el_estado(choco_feed: dict[str, Any], tmp_path: Path) -> None:
    from pipelines.common.http import FixtureFetcher
    from pipelines.p1_trigger.feed import feed_url

    fetcher = FixtureFetcher(
        {
            feed_url("4.5_hour"): choco_feed,
            feed_url("4.5_day"): {"type": "FeatureCollection", "features": []},
        }
    )
    resultado = run_trigger(fetcher, events_dir=tmp_path)
    assert resultado.nuevos == [USGS_ID]

    estado = EventState.load(USGS_ID, tmp_path)
    assert estado is not None and estado.estado is EventStatus.DETECTADO


# --- Asercion (d): se consume la ultima version del ShakeMap ---------------


def test_se_elige_la_version_vigente_del_shakemap(choco_detail: dict[str, Any]) -> None:
    productos = parse_products(choco_detail)
    assert productos.shakemap_version == SHAKEMAP_VIGENTE
    assert productos.groundfailure_version == GROUNDFAILURE_VIGENTE


def test_la_fixture_conserva_todas_las_versiones(choco_detail: dict[str, Any]) -> None:
    """Sin el historial no se puede probar el changelog de RF-04."""
    versiones = {
        int(e["properties"]["version"]) for e in choco_detail["properties"]["products"]["shakemap"]
    }
    assert versiones == set(range(1, SHAKEMAP_VIGENTE + 1))


def test_hay_contornos_de_intensidad(choco_detail: dict[str, Any]) -> None:
    """El polyfill H3 se alimenta de `cont_mmi`; sin el no hay reporte completo."""
    url = parse_products(choco_detail).cont_mmi_url()
    assert url is not None and url.endswith("cont_mmi.json")


def test_pager_se_lee_como_referencia(choco_detail: dict[str, Any]) -> None:
    assert parse_products(choco_detail).pager_alert() == "red"


# --- RF-04: re-emision al aparecer una version nueva -----------------------


def test_un_estado_atrasado_dispara_reproceso(choco_detail: dict[str, Any]) -> None:
    from pipelines.common.state import ProcessedVersions

    estado = EventState(
        usgs_id=USGS_ID,
        estado=EventStatus.PUBLICADO,
        mag=7.4,
        lon=-76.2422,
        lat=4.8436,
        depth_km=110.285,
        lugar="5 km S of San José del Palmar, Colombia",
        origen_utc="2026-08-10T12:34:28Z",
        versiones_procesadas=ProcessedVersions(shakemap=6, groundfailure=6),
    )
    decision = decide(estado, parse_products(choco_detail))
    assert decision.action is Action.COMPLETO
    assert decision.shakemap_version == SHAKEMAP_VIGENTE


def test_un_estado_al_dia_no_reprocesa(choco_detail: dict[str, Any]) -> None:
    from pipelines.common.state import ProcessedVersions

    estado = EventState(
        usgs_id=USGS_ID,
        estado=EventStatus.PUBLICADO,
        mag=7.4,
        lon=-76.2422,
        lat=4.8436,
        depth_km=110.285,
        lugar="5 km S of San José del Palmar, Colombia",
        origen_utc="2026-08-10T12:34:28Z",
        versiones_procesadas=ProcessedVersions(
            shakemap=SHAKEMAP_VIGENTE, groundfailure=GROUNDFAILURE_VIGENTE
        ),
    )
    assert decide(estado, parse_products(choco_detail)).action is Action.OMITIR


# --- Pendiente de P0/P2 ----------------------------------------------------


@pytest.mark.skip(reason="Requiere exposure_h3 de Colombia (P0, Fase 0 semana 2)")
def test_pop_mmi7p_estable() -> None:
    """Asercion (b): la cifra principal no se mueve mas de ±0.5% entre commits."""


@pytest.mark.skip(reason="Requiere exposure_h3 de Colombia (P0, Fase 0 semana 2)")
def test_top15_municipios_estable() -> None:
    """Asercion (c): el ranking municipal es estable."""
