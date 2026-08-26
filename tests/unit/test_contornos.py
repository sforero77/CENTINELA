"""`contornos.json`: el area de afectacion, que no es la de la exposicion.

El visor dibujaba la malla H3, que llega **hasta donde hay algo expuesto**. Su
propia nota lo admitia —«el hueco no es ausencia de sacudida, es ausencia de
gente»— y aun asi era lo unico que enseñaba: quien preguntaba «¿hasta donde
llego el terremoto?» no tenia donde mirarlo.

Medido sobre Balao 2023: el area sentida mide unos 410 km de lado y la que el
sistema cuantifica unos 180. Cuatro veces. Todo eso quedaba fuera del tablero, y
el pipeline **ya descargaba** las isolineas en cada evento —son la entrada del
polyfill— y las tiraba al terminar.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from pipelines.p3_report.contornos import (
    MMI_MINIMO_CONTORNO,
    build_contours,
    write_contours_json,
)

RAIZ = Path(__file__).parent.parent.parent
FIXTURE = RAIZ / "tests" / "fixtures" / "golden" / "choco_2026_08_10" / "cont_mmi_v7.json"


@pytest.fixture(scope="module")
def cont_mmi() -> dict[str, Any]:
    """Los contornos reales del Choco, tal como los publica USGS."""
    datos: dict[str, Any] = json.loads(FIXTURE.read_text(encoding="utf-8"))
    return datos


def test_se_publica_desde_mmi_4(cont_mmi: dict[str, Any]) -> None:
    """Por debajo, USGS dibuja niveles que casi nadie percibe.

    La fixture del Choco trae una isolinea de 3,5: multiplica el peso del
    fichero con lineas que no significan nada para quien responde.
    """
    niveles = {f["properties"]["mmi"] for f in build_contours(cont_mmi)["features"]}

    assert min(niveles) >= MMI_MINIMO_CONTORNO
    assert 3.5 not in niveles, "la fixture trae 3,5 y no deberia publicarse"


def test_llega_mas_lejos_que_la_franja_que_el_sistema_cuantifica(
    cont_mmi: dict[str, Any],
) -> None:
    """Es la razon de existir del fichero.

    Si solo publicara MMI≥6 seria redundante con la malla y no responderia la
    pregunta que motiva todo esto.
    """
    niveles = {f["properties"]["mmi"] for f in build_contours(cont_mmi)["features"]}

    assert niveles & {4.0, 4.5, 5.0, 5.5}, "no publica ningun nivel por debajo de 6"
    assert niveles & {6.0, 6.5, 7.0, 7.5}, "no publica la franja que el reporte cuantifica"


def test_el_area_sentida_es_mucho_mayor_que_la_cuantificada(
    cont_mmi: dict[str, Any],
) -> None:
    """La cifra que justifica dibujarlas: cuatro veces mas ancha en Balao."""

    def ancho(features: list[dict[str, Any]]) -> float:
        lons = [
            float(c[0]) for f in features for linea in f["geometry"]["coordinates"] for c in linea
        ]
        return max(lons) - min(lons)

    todas = build_contours(cont_mmi)["features"]
    solo_6 = [f for f in todas if f["properties"]["mmi"] >= 6]

    assert ancho(todas) > ancho(solo_6) * 1.5


def test_se_ordena_de_mayor_a_menor(cont_mmi: dict[str, Any]) -> None:
    """Al dibujar, las de intensidad alta quedan encima: son las que importan."""
    valores = [f["properties"]["mmi"] for f in build_contours(cont_mmi)["features"]]

    assert valores == sorted(valores, reverse=True)


def test_no_se_copia_el_color_de_la_fuente(cont_mmi: dict[str, Any]) -> None:
    """ShakeMap trae su propio `color` y `weight`, y el visor tiene su rampa.

    Arrastrar la de la fuente pintaria el mismo evento de dos colores segun
    donde se mire — el error que ya se corrigio una vez entre el visor y el mapa
    estatico del reporte.
    """
    props = build_contours(cont_mmi)["features"][0]["properties"]

    assert set(props) == {"mmi"}


def test_una_isolinea_sin_valor_no_tumba_el_fichero() -> None:
    """USGS puede publicar una geometria sin `value`; el resto sigue sirviendo."""
    payload = {
        "features": [
            {"properties": {}, "geometry": {"type": "MultiLineString", "coordinates": []}},
            {
                "properties": {"value": 6.0},
                "geometry": {"type": "MultiLineString", "coordinates": [[[0, 0], [1, 1]]]},
            },
        ]
    }

    assert len(build_contours(payload)["features"]) == 1


def test_se_escribe_compacto_y_donde_el_visor_lo_busca(tmp_path: Path) -> None:
    destino = write_contours_json(FIXTURE, tmp_path / "contornos.json")

    assert destino.name == "contornos.json"
    texto = destino.read_text(encoding="utf-8")
    assert ", " not in texto, "el fichero se sirve tal cual; el sangrado es peso puro"
    assert json.loads(texto)["features"]


def test_cabe_de_sobra_en_un_navegador(tmp_path: Path) -> None:
    """110 kB del original, y menos tras podar los niveles bajos y el estilo."""
    destino = write_contours_json(FIXTURE, tmp_path / "contornos.json")

    assert destino.stat().st_size < 200_000


# --- Contra los reportes publicados -----------------------------------------


def test_todo_reporte_publicado_trae_su_area_de_afectacion() -> None:
    """Un reporte sin contornos deja al visor enseñando solo la exposicion.

    Los emitidos antes de que el fichero existiera se rellenan con
    `centinela contornos`, que los trae de USGS sin recomputar el impacto.
    """
    reportes = sorted(p.parent.name for p in (RAIZ / "reports").glob("*/report.json"))
    sin_contornos = [r for r in reportes if not (RAIZ / "reports" / r / "contornos.json").is_file()]

    assert sin_contornos == [], (
        f"Reportes sin area de afectacion: {sin_contornos}. Corre `centinela contornos`."
    )


def test_el_pipeline_lo_escribe_solo_en_cada_evento() -> None:
    """Escribir el modulo y no llamarlo desde P2 seria el fallo de siempre."""
    import inspect

    from pipelines.p2_impact.run import run_impact

    assert "write_contours_json" in inspect.getsource(run_impact)


def test_el_visor_lo_dibuja_debajo_de_la_malla() -> None:
    """Donde hay hexagonos manda el dato; fuera de ellos, la linea es lo unico."""
    app = (RAIZ / "site" / "assets" / "app.js").read_text(encoding="utf-8")

    assert "dibujarContornos(m, contornos, antes)" in app
    assert "extremosDeContorno" in app, "el encuadre no considera el area afectada"
