"""Identidad de un evento y de una version de producto (auditoria del 5-sep-2026).

Seis hallazgos con la misma raiz: el sistema identificaba cosas por un pedazo de
su identidad. Un sismo por el id preferido de hoy, cuando USGS lo conoce por
varios (#87). Una version de ShakeMap por su numero, cuando el numero es por
contribuidor (#81, #95). Un contorno de intensidad por una propiedad que USGS no
publica (#98). Una magnitud por su redondeo (#169). Un instante por un sello que
podia venir sin zona (#168).
"""

from __future__ import annotations

import copy
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from tests.conftest import load_fixture

from pipelines.common.constants import USGS_FEED_BACKFILL, USGS_FEED_PRIMARY
from pipelines.common.http import FixtureFetcher
from pipelines.common.state import EventState, EventStatus, ProcessedVersions
from pipelines.p1_trigger.feed import EventCandidate, feed_url, parse_feed
from pipelines.p1_trigger.observados import EventoObservado, podar
from pipelines.p1_trigger.rezago import Rezago
from pipelines.p1_trigger.run import run_trigger
from pipelines.p2_impact.products import parse_products
from pipelines.p2_impact.run import Action, decide
from pipelines.p2_impact.shakemap import parse_contours
from pipelines.p3_report.changelog import build_changelog
from pipelines.p3_report.markdown import render_markdown
from pipelines.p3_report.model import Report

VACIO: dict[str, Any] = {"type": "FeatureCollection", "features": []}


def _estado_publicado(usgs_id: str, versiones: ProcessedVersions | None = None) -> EventState:
    return EventState(
        usgs_id=usgs_id,
        estado=EventStatus.PUBLICADO,
        mag=6.9,
        lon=-77.85,
        lat=6.42,
        depth_km=24.7,
        lugar="Choco, Colombia",
        origen_utc="2026-08-19T05:00:00Z",
        versiones_procesadas=versiones or ProcessedVersions(shakemap=3, groundfailure=2),
    )


def _feed_con(feed_payload: dict[str, Any], **cambios: Any) -> dict[str, Any]:
    """El feed de la fixture con solo `us7000sint`, y los cambios pedidos."""
    feature = copy.deepcopy(next(f for f in feed_payload["features"] if f["id"] == "us7000sint"))
    if "id" in cambios:
        feature["id"] = cambios.pop("id")
    feature["properties"].update(cambios)
    return {**feed_payload, "features": [feature]}


def _fetcher(feed: dict[str, Any]) -> FixtureFetcher:
    return FixtureFetcher({feed_url(USGS_FEED_PRIMARY): feed, feed_url(USGS_FEED_BACKFILL): VACIO})


# --- #87: un evento renumerado o retirado -----------------------------------


def test_el_feed_lee_todos_los_ids_del_evento(feed_payload: dict[str, Any]) -> None:
    feed = _feed_con(feed_payload, id="us7000renu", ids=",us7000renu,us7000sint,pt26001,")
    (candidato,) = parse_feed(feed)
    assert candidato.identificadores == ("us7000renu", "us7000sint", "pt26001")


def test_un_evento_renumerado_no_se_publica_dos_veces(
    feed_payload: dict[str, Any], events_dir: Path
) -> None:
    """USGS cambia el preferido y deja el viejo en `ids`.

    Pasa de verdad: el 3-oct-2026 el detail de `pr2025056002` declaraba
    `,pt25056000,us6000pvad,pr2025056002,usauto6000pvad,`. Con el dedupe por
    cadena, el vigia no encontraba `events/us6000pvad.json`, lo daba por nuevo
    y P2 publicaba un segundo reporte del mismo sismo.
    """
    _estado_publicado("us7000sint").save(events_dir)
    feed = _feed_con(feed_payload, id="us7000renu", ids=",us7000renu,us7000sint,")

    resultado = run_trigger(_fetcher(feed), events_dir=events_dir)

    assert resultado.nuevos == [], "el mismo sismo con otro id se tomo por nuevo"
    assert resultado.revisitados == ["us7000sint"], "se despacha con el id del estado"
    assert not (events_dir / "us7000renu.json").exists()


def test_un_alias_con_forma_rara_no_cuenta_como_estado_ilegible(
    feed_payload: dict[str, Any], events_dir: Path
) -> None:
    """Un id de otra red que no podria ser nombre de fichero no es un fichero roto nuestro."""
    feed = _feed_con(feed_payload, ids=",us7000sint,a/b,")

    resultado = run_trigger(_fetcher(feed), events_dir=events_dir)

    assert resultado.estados_ilegibles == []
    assert resultado.nuevos == ["us7000sint"]


def test_un_evento_conocido_que_usgs_retira_se_cierra_y_no_se_despacha(
    feed_payload: dict[str, Any], events_dir: Path
) -> None:
    _estado_publicado("us7000sint").save(events_dir)
    feed = _feed_con(feed_payload, status="deleted")

    resultado = run_trigger(_fetcher(feed), events_dir=events_dir)

    assert resultado.a_despachar == []
    assert resultado.retirados == ["us7000sint"]
    estado = EventState.load("us7000sint", events_dir)
    assert estado is not None and estado.estado is EventStatus.DESCARTADO


def test_un_evento_retirado_que_no_se_conocia_no_crea_nada(
    feed_payload: dict[str, Any], events_dir: Path
) -> None:
    feed = _feed_con(feed_payload, status="deleted")

    resultado = run_trigger(_fetcher(feed), events_dir=events_dir)

    assert resultado.a_despachar == []
    assert resultado.observados == []
    assert list(events_dir.iterdir()) == []


# --- #81 y #95: la identidad de una version es (contribuidor, numero) ---------


def _detail(*shakemaps: tuple[str, int, int, int]) -> dict[str, Any]:
    """Un detail con ShakeMaps `(source, version, preferredWeight, updateTime)`."""
    return {
        "id": "us7000sint",
        "properties": {
            "products": {
                "shakemap": [
                    {
                        "source": fuente,
                        "status": "UPDATE",
                        "preferredWeight": peso,
                        "updateTime": cuando,
                        "properties": {"version": str(version)},
                        "contents": {"download/cont_mmi.json": {"url": "https://x/cont_mmi.json"}},
                    }
                    for fuente, version, peso, cuando in shakemaps
                ]
            }
        },
    }


def test_el_contribuidor_del_preferido_no_se_tira() -> None:
    """Los numeros de `atlas` y `us` son cuentas distintas: sin `source`, «v1» no es nada."""
    productos = parse_products(_detail(("us", 6, 233, 2), ("atlas", 1, 325, 1)))
    assert (productos.shakemap_fuente, productos.shakemap_version) == ("atlas", 1)


def test_el_contribuidor_del_preferido_en_un_detail_real() -> None:
    productos = parse_products(load_fixture("golden", "choco_2026_08_10", "detail_superseded.json"))
    assert productos.shakemap_fuente, "el detail real trae `source` y se perdia"


def test_cambiar_de_contribuidor_reemite_aunque_el_numero_baje() -> None:
    """`us` v6 -> `atlas` v1: con `1 > 6` el reporte se congelaba para siempre."""
    estado = _estado_publicado(
        "us7000sint",
        ProcessedVersions(shakemap=6, groundfailure=0, shakemap_fuente="us"),
    )
    productos = parse_products(_detail(("us", 6, 233, 2), ("atlas", 1, 325, 1)))

    decision = decide(estado, productos)

    assert decision.action is Action.COMPLETO
    assert decision.razon == "ShakeMap v6 (us) -> v1 (atlas)"


def test_el_rezago_ve_el_cambio_de_contribuidor() -> None:
    rezago = Rezago(
        usgs_id="us7000sint",
        shakemap_publicado=6,
        shakemap_vigente=1,
        groundfailure_publicado=0,
        groundfailure_vigente=0,
        manifiesto_publicado="col-v0.7",
        manifiesto_vigente="col-v0.7",
        shakemap_fuente_publicada="us",
        shakemap_fuente_vigente="atlas",
    )
    assert rezago.productos
    assert "ShakeMap v6 (us) -> v1 (atlas)" in rezago.describir()


def test_la_procedencia_dice_de_que_contribuidor_es_la_version(reporte: Report) -> None:
    con_fuente = replace(reporte, inputs=replace(reporte.inputs, shakemap_fuente="atlas"))
    assert f"ShakeMap consumido: **v{reporte.inputs.shakemap_version}** de `atlas`" in (
        render_markdown(con_fuente)
    )


def test_un_reporte_anterior_sin_contribuidor_se_sigue_leyendo(reporte: Report) -> None:
    datos = reporte.to_dict()
    del datos["inputs"]["shakemap_fuente"]
    del datos["inputs"]["groundfailure_fuente"]
    assert Report.from_dict(datos).inputs.shakemap_fuente == ""


def test_el_changelog_registra_el_cambio_de_contribuidor(reporte: Report) -> None:
    antes = replace(reporte, inputs=replace(reporte.inputs, shakemap_fuente="us"))
    despues = replace(reporte, inputs=replace(reporte.inputs, shakemap_fuente="atlas"))
    v = reporte.inputs.shakemap_version
    assert f"ShakeMap: v{v} (us) → v{v} (atlas)" in build_changelog(antes, despues)


# --- #98: el filtro de MMI lee lo que USGS publica ----------------------------


def test_los_contornos_reales_traen_units_y_no_type() -> None:
    """El filtro miraba `type`, que el ShakeMap v4 no publica: no filtraba nada."""
    cont = load_fixture("golden", "choco_2026_08_10", "cont_mmi_v7.json")
    props = [f["properties"] for f in cont["features"]]
    assert all("type" not in p and p.get("units") == "mmi" for p in props)
    assert len(parse_contours(cont)) == len(props)


def test_un_contorno_de_aceleracion_no_se_toma_por_intensidad() -> None:
    cont = copy.deepcopy(load_fixture("golden", "choco_2026_08_10", "cont_mmi_v7.json"))
    pga = copy.deepcopy(cont["features"][0])
    pga["properties"] = {"value": 40.0, "units": "%g", "color": "#000", "weight": 4}
    cont["features"].append(pga)

    valores = [c.value for c in parse_contours(cont)]

    assert 40.0 not in valores, "un contorno en %g se habria pintado como MMI 40"


# --- #169: la magnitud publicada es la de la razon ----------------------------


def test_la_magnitud_observada_no_se_redondea_hasta_el_umbral() -> None:
    """M5.49 salia como «M5,5» junto a «M5.49 < umbral M5.5»."""
    candidato = EventCandidate(
        usgs_id="us7000casi",
        mag=5.49,
        lon=-73.05,
        lat=6.8,
        depth_km=160.0,
        lugar="4 km E of Jordan, Colombia",
        origen_utc="2026-08-26T16:45:00Z",
        detail_url="",
        tipo="earthquake",
        estado_revision="reviewed",
        actualizado_utc="2026-08-26T16:45:00Z",
    )
    observado = EventoObservado.desde_candidato(candidato, "M5.49 < umbral M5.5")
    assert observado.mag == 5.49


# --- #168: un sello sin zona no tumba la poda ---------------------------------


def test_un_origen_sin_zona_no_tumba_la_poda() -> None:
    """`podar` comparaba un sello naive con `datetime.now(UTC)` y lanzaba TypeError."""
    ayer = (datetime.now(UTC) - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S")
    sin_zona = EventoObservado(
        usgs_id="us7000nz",
        mag=4.8,
        lon=-75.0,
        lat=5.0,
        depth_km=10.0,
        lugar="Colombia",
        origen_utc=ayer,
        razon="M4.8 < umbral M5.5",
    )
    assert podar([sin_zona]) == [sin_zona]
