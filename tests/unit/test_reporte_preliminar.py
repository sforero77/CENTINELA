"""RF-03: el reporte que sale mientras USGS no publica el ShakeMap.

El calculo por radios estaba escrito desde el principio y **no lo llamaba
nadie**: el evento pasaba a estado `preliminar` y no se publicaba nada, asi que
durante las primeras horas —las unicas en que un preliminar sirve— el sistema
callaba. Estas pruebas existen para que no vuelva a desconectarse.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from pipelines.common.state import EventState, EventStatus
from pipelines.p2_impact.pipeline import build_preliminary_report
from pipelines.p2_impact.products import ProductSet
from pipelines.p3_report.markdown import render_markdown

SCHEMAS_DIR = Path(__file__).parent.parent.parent / "schemas"


@pytest.fixture
def estado() -> EventState:
    return EventState(
        usgs_id="us7000prel",
        estado=EventStatus.PRELIMINAR,
        mag=6.8,
        lon=-76.2422,
        lat=4.8436,
        depth_km=32.0,
        lugar="Choco, Colombia",
        origen_utc="2026-08-24T03:11:00Z",
    )


@pytest.fixture
def sin_productos() -> ProductSet:
    return ProductSet(usgs_id="us7000prel", shakemap=None, ground_failure=None, losspager=None)


RADIOS = {25: 41_233.0, 50: 210_884.0, 100: 1_004_512.0}


def test_no_publica_cifras_por_intensidad(estado: EventState, sin_productos: ProductSet) -> None:
    """El nucleo de RF-03: una tabla de ceros con titulo creible es peor que nada.

    Sin ShakeMap no hay modelo de sacudida. Publicar "poblacion en MMI>=7: 0"
    seria una respuesta falsa y del todo verosimil.
    """
    reporte = build_preliminary_report(estado, sin_productos, RADIOS, manifest_id="col-v0.5")
    md = render_markdown(reporte)
    # El encabezado de seccion, no la palabra: un disclaimer dice "Exposicion
    # estimada, no dano observado" y ese si debe seguir ahi.
    assert "## Exposición estimada" not in md
    assert "MMI≥7" not in md
    assert "Población por distancia al epicentro" in md


def test_publica_cada_radio(estado: EventState, sin_productos: ProductSet) -> None:
    reporte = build_preliminary_report(estado, sin_productos, RADIOS, manifest_id="col-v0.5")
    md = render_markdown(reporte)
    for km in RADIOS:
        assert f"| {km} km |" in md
    assert [r.radio_km for r in reporte.radios] == [25, 50, 100]


def test_advierte_que_un_radio_no_es_una_intensidad(
    estado: EventState, sin_productos: ProductSet
) -> None:
    """Un M6 superficial y uno a 200 km tienen el mismo circulo de 50 km."""
    md = render_markdown(build_preliminary_report(estado, sin_productos, RADIOS, manifest_id="x"))
    assert "no son bandas de intensidad" in md
    assert "Reporte preliminar sin ShakeMap" in md


def test_declara_shakemap_cero(estado: EventState, sin_productos: ProductSet) -> None:
    """La procedencia no puede sugerir que se consumio un ShakeMap."""
    reporte = build_preliminary_report(estado, sin_productos, RADIOS, manifest_id="col-v0.5")
    assert reporte.inputs.shakemap_version == 0
    assert reporte.preliminar is True
    assert "v0" in render_markdown(reporte)


def test_lleva_el_epicentro(estado: EventState, sin_productos: ProductSet) -> None:
    """Es lo unico que un preliminar sabe con certeza; tiene que viajar."""
    reporte = build_preliminary_report(estado, sin_productos, RADIOS, manifest_id="x")
    assert (reporte.event.lon, reporte.event.lat) == (estado.lon, estado.lat)


def test_cumple_el_schema(estado: EventState, sin_productos: ProductSet) -> None:
    schema = json.loads((SCHEMAS_DIR / "report-1.0.schema.json").read_text(encoding="utf-8"))
    reporte = build_preliminary_report(estado, sin_productos, RADIOS, manifest_id="col-v0.5")
    errores = sorted(Draft202012Validator(schema).iter_errors(reporte.to_dict()), key=str)
    assert errores == [], [e.message for e in errores]


def test_sobrevive_al_roundtrip(estado: EventState, sin_productos: ProductSet) -> None:
    from pipelines.p3_report.model import Report

    reporte = build_preliminary_report(estado, sin_productos, RADIOS, manifest_id="col-v0.5")
    assert Report.from_dict(reporte.to_dict()).to_dict() == reporte.to_dict()


def test_sin_radios_lo_dice_en_vez_de_callar(estado: EventState, sin_productos: ProductSet) -> None:
    """Si no hay activo del pais, el hueco se declara; no se publica una tabla vacia."""
    md = render_markdown(build_preliminary_report(estado, sin_productos, {}, manifest_id="x"))
    assert "No se pudo calcular el corte por radios" in md
