"""G2 — Venezuela, 24 de junio de 2026 · `us6000t7zp` + `us6000t7zc` (§6.3).

Ademas de las aserciones de G1, este caso valida el **evento doble**: dos
mainshocks separados por 32,2 segundos y 145 km, no un sismo con replica. El
sistema debe emitir dos reportes independientes y no fusionarlos.

Aqui se cazo el bug de seleccion de version de producto: ver
``test_no_se_elige_una_version_obsoleta``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from pipelines.common.http import FixtureFetcher
from pipelines.common.state import EventState
from pipelines.p1_trigger.feed import feed_url, parse_feed
from pipelines.p1_trigger.filters import evaluate
from pipelines.p1_trigger.run import run_trigger
from pipelines.p2_impact.products import parse_products

pytestmark = pytest.mark.golden

CATIA_LA_MAR = "us6000t7zp"
SAN_FELIPE = "us6000t7zc"

#: Versiones vigentes al congelar la fixture, contrastadas contra la respuesta
#: autoritativa de ComCat (el feed detail sin `includesuperseded`).
VIGENTES = {
    CATIA_LA_MAR: {"shakemap": 14, "ground-failure": 12},
    SAN_FELIPE: {"shakemap": 9, "ground-failure": 7},
}


def test_ambos_mainshocks_pasan_el_filtro(venezuela_feed: dict[str, Any]) -> None:
    relevantes = [c for c in parse_feed(venezuela_feed) if evaluate(c)]
    assert {c.usgs_id for c in relevantes} == {CATIA_LA_MAR, SAN_FELIPE}


def test_estan_separados_por_segundos(venezuela_feed: dict[str, Any]) -> None:
    """32,2 segundos: lo bastante cerca para confundirlos, y son dos eventos."""
    from datetime import datetime

    tiempos = {
        c.usgs_id: datetime.fromisoformat(c.origen_utc.replace("Z", "+00:00"))
        for c in parse_feed(venezuela_feed)
    }
    delta = abs((tiempos[CATIA_LA_MAR] - tiempos[SAN_FELIPE]).total_seconds())
    assert delta == pytest.approx(33.0, abs=1.0)


def test_cada_mainshock_genera_su_propio_estado(
    venezuela_feed: dict[str, Any], tmp_path: Path
) -> None:
    """Dos eventos, dos `event_state`: nunca uno tratado como replica del otro."""
    fetcher = FixtureFetcher(
        {
            feed_url("4.5_hour"): venezuela_feed,
            feed_url("4.5_day"): {"type": "FeatureCollection", "features": []},
        }
    )
    resultado = run_trigger(fetcher, events_dir=tmp_path)
    assert sorted(resultado.nuevos) == sorted([CATIA_LA_MAR, SAN_FELIPE])
    assert len(list(tmp_path.glob("*.json"))) == 2
    for usgs_id in (CATIA_LA_MAR, SAN_FELIPE):
        assert EventState.load(usgs_id, tmp_path) is not None


def test_el_bbox_cubre_venezuela(venezuela_feed: dict[str, Any]) -> None:
    for c in parse_feed(venezuela_feed):
        assert evaluate(c).razon == "dentro de alcance"


@pytest.mark.parametrize("usgs_id", [CATIA_LA_MAR, SAN_FELIPE])
def test_se_elige_la_version_vigente(
    venezuela_details: dict[str, dict[str, Any]], usgs_id: str
) -> None:
    productos = parse_products(venezuela_details[usgs_id])
    assert productos.shakemap_version == VIGENTES[usgs_id]["shakemap"]
    assert productos.groundfailure_version == VIGENTES[usgs_id]["ground-failure"]


def test_no_se_elige_una_version_obsoleta(
    venezuela_details: dict[str, dict[str, Any]],
) -> None:
    """Regresion del bug que cazo esta fixture.

    En `us6000t7zp` las versiones v1-v4 de junio tienen `preferredWeight` 232 y
    la vigente v14 de agosto tiene 228. Ordenar por peso —que era lo que hacia
    el parser— elegia un ShakeMap de hace mes y medio, y el reporte habria
    salido con cifras equivocadas sin que nada fallara.

    `preferredWeight` desempata **contribuidores**, no versiones.
    """
    detail = venezuela_details[CATIA_LA_MAR]
    pesos = {
        int(e["properties"]["version"]): int(e["preferredWeight"])
        for e in detail["properties"]["products"]["shakemap"]
    }
    # La trampa sigue en los datos: si esto deja de cumplirse, la prueba ya no
    # esta probando lo que cree.
    assert pesos[4] > pesos[14], "la fixture ya no reproduce el caso del bug"
    assert parse_products(detail).shakemap_version == 14


def test_ambos_eventos_traen_contornos(
    venezuela_details: dict[str, dict[str, Any]],
) -> None:
    for usgs_id, detail in venezuela_details.items():
        url = parse_products(detail).cont_mmi_url()
        assert url is not None, f"{usgs_id} sin cont_mmi"


#: Reportes de los dos mainshocks. Mientras no exista el activo de Venezuela no
#: hay reporte que congelar, asi que la asercion (b) se salta **sola** en vez de
#: estar apagada a mano: el dia que `centinela country VEN` produzca el activo y
#: se publique el backtest, esta prueba empieza a correr sin que nadie recuerde
#: quitarle un decorador.
def _reporte_publicado(usgs_id: str) -> dict[str, Any]:
    import json

    ruta = Path(__file__).parent.parent.parent / "reports" / usgs_id / "report.json"
    if not ruta.exists():
        pytest.skip(
            f"Aun no hay reporte publicado de {usgs_id}: requiere el activo de "
            f"Venezuela (`centinela country VEN`, manifest ven-v0.1)."
        )
    datos: dict[str, Any] = json.loads(ruta.read_text(encoding="utf-8"))
    return datos


#: Cifras del backtest, fijadas el 24-ago-2026 con la primera corrida real del
#: camino P2→P3 en CI. Moverlas en silencio es lo que los golden existen para
#: impedir, asi que cambiarlas exige explicar por que en el PR.
#:
#: Calculadas contra `ven-v0.1` reconstruido con el rescate de frontera acotado
#: al vecino y el reparto viendo los municipios multipoligono. El desvio de
#: poblacion nacional que hereda este pais es +4,94 % frente a la ONU, y esa
#: parte **no** es un fallo del pipeline: GHS-POP deriva de la ronda censal de
#: 2010 y no modela la emigracion venezolana.
POP_MMI7P_ESPERADO: dict[str, float] = {
    CATIA_LA_MAR: 2_276_853.971352878,
    SAN_FELIPE: 491_580.875195766,
}
TOLERANCIA_POP = 0.005  # ±0,5 % (§6.3)


@pytest.mark.parametrize("usgs_id", [CATIA_LA_MAR, SAN_FELIPE])
def test_pop_mmi7p_estable(usgs_id: str) -> None:
    """Asercion (b) de G1, aplicada a los dos mainshocks."""
    totales = _reporte_publicado(usgs_id)["totales"]
    esperado = POP_MMI7P_ESPERADO.get(usgs_id)
    if esperado is None:
        pytest.skip(
            f"Hay reporte de {usgs_id} pero no cifra congelada. Anota "
            f"pop_mmi7p={totales['pop_mmi7p']:,.0f} en POP_MMI7P_ESPERADO."
        )
    desvio = abs(totales["pop_mmi7p"] - esperado) / esperado
    assert desvio <= TOLERANCIA_POP, (
        f"pop_mmi7p de {usgs_id} paso de {esperado:,.0f} a "
        f"{totales['pop_mmi7p']:,.0f} ({100 * desvio:.2f}%)."
    )


@pytest.mark.parametrize("usgs_id", [CATIA_LA_MAR, SAN_FELIPE])
def test_las_capas_del_activo_llegan_al_reporte(usgs_id: str) -> None:
    """Un activo de VEN al que le falte una capa publicaria ceros creibles."""
    totales = _reporte_publicado(usgs_id)["totales"]
    for columna in ("bld_mmi7p", "health_mmi7p", "edu_mmi7p", "road_km_mmi7p", "pop_65p_mmi7p"):
        assert totales[columna] > 0, f"{columna} en cero: ¿se perdio una capa?"


def test_los_dos_eventos_no_se_fusionan() -> None:
    """El corazon de G2: dos reportes, no uno con la suma de ambos."""
    catia = _reporte_publicado(CATIA_LA_MAR)
    san_felipe = _reporte_publicado(SAN_FELIPE)
    assert catia["event"]["usgs_id"] != san_felipe["event"]["usgs_id"]
    assert catia["totales"]["pop_mmi7p"] != san_felipe["totales"]["pop_mmi7p"]
