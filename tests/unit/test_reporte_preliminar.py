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


# --- La guardia de pais del preliminar -------------------------------------
#
# El camino completo comprueba que el ShakeMap toque al menos una celda del
# activo y, si no, lanza `ExposureCountryMismatchError` para que el orquestador
# pruebe el siguiente pais. El preliminar no lo hacia: con el activo equivocado
# devolvia {25: 0, 50: 0, 100: 0}, `run_impact` salia con exito e `impact.yml`
# daba el evento por resuelto en el primer candidato. Un "0 personas a 100 km"
# publicado en la primera hora de un sismo real es la cifra falsa y creible que
# este sistema no se permite en ningun otro sitio.


def _activo_de_una_celda(con: object, tmp_path: Path, lat: float, lon: float) -> str:
    """Un parquet con una sola celda r8, en la coordenada que se le pida."""
    destino = tmp_path / "exposure_h3.parquet"
    con.execute(  # type: ignore[attr-defined]
        "COPY (SELECT h3_latlng_to_cell(?, ?, 8)::UBIGINT AS h3_08, "
        "'COL' AS iso3, '05' AS adm1_id, '05001' AS adm2_id, 5000.0 AS pop_total, "
        "'col-v0.6' AS src_manifest) "
        f"TO '{destino.as_posix()}' (FORMAT PARQUET)",
        [lat, lon],
    )
    return destino.as_posix()


@pytest.mark.geo
def test_el_preliminar_cuenta_lo_que_tiene_cerca(estado: EventState, tmp_path: Path) -> None:
    """Con el activo del pais correcto, la celda entra en los tres radios."""
    from pipelines.p2_impact.exposure_join import connect
    from pipelines.p2_impact.pipeline import compute_preliminary

    con = connect()
    ruta = _activo_de_una_celda(con, tmp_path, estado.lat, estado.lon)

    por_radio = compute_preliminary(con, estado, exposure_glob=ruta)

    assert por_radio == {25: 5000.0, 50: 5000.0, 100: 5000.0}


@pytest.mark.geo
def test_el_preliminar_no_publica_ceros_con_el_activo_de_otro_pais(
    estado: EventState, tmp_path: Path
) -> None:
    """El caso de Coquimbo, que el propio codigo documenta.

    La caja de Chile mide 1.719 grados cuadrados por Rapa Nui, asi que un sismo
    chileno sale como argentino primero. Antes de la guardia, el preliminar se
    calculaba contra el activo argentino y publicaba tres ceros; ahora levanta,
    y el bucle de `impact.yml` prueba el siguiente candidato.
    """
    from pipelines.p2_impact.exposure_join import connect
    from pipelines.p2_impact.pipeline import ExposureCountryMismatchError, compute_preliminary

    con = connect()
    # Una celda en Buenos Aires para un epicentro en el Choco: nada a 100 km.
    ruta = _activo_de_una_celda(con, tmp_path, -34.60, -58.38)

    with pytest.raises(ExposureCountryMismatchError, match="100 km del epicentro"):
        compute_preliminary(con, estado, exposure_glob=ruta)
