"""Mapa estatico del reporte (T0.8).

Este modulo no tenia ni una prueba, y por eso los tres reportes publicados
salieron durante meses con el mismo PNG vacio: la estrella del epicentro clavada
en (0, 0) y ni un municipio dibujado. Las dos causas eran desconexiones, no
errores de calculo — el renderizador leia campos que nadie le pasaba — asi que
lo que se prueba aqui es justamente el cableado.
"""

from __future__ import annotations

from itertools import pairwise
from pathlib import Path

import pytest

from pipelines.p3_report.model import Evento, Inputs, Report, Totales
from pipelines.p3_report.static_map import (
    MMI_COLORS,
    MapVariant,
    _coordenada,
    _epicentro,
    _puntos_municipales,
    banda_de_mmi,
    color_for_mmi,
    render_map,
)


@pytest.fixture
def reporte() -> Report:
    return Report(
        event=Evento(
            usgs_id="us7000sint",
            mag=7.1,
            depth_km=30.0,
            utc="2026-08-19T05:00:00Z",
            lugar="38 km al W de Bahia Solano, Choco, Colombia",
            lon=-77.6,
            lat=6.2,
        ),
        inputs=Inputs(
            shakemap_version=3, groundfailure_version=2, exposure_manifest="col-v0.1-draft"
        ),
        totales=Totales(),
    )


def test_epicentro_sale_del_reporte(reporte: Report) -> None:
    """Antes venia de un registro de modulo que no rellenaba nadie."""
    assert _epicentro(reporte) == (-77.6, 6.2)


def test_epicentro_ausente_no_se_inventa() -> None:
    """Sin coordenadas se devuelve ``None``, no ``(0, 0)``.

    El valor por defecto anterior dibujaba la estrella en el golfo de Guinea,
    que es un sitio perfectamente valido para un punto y ninguno para el
    epicentro de un sismo en Colombia.
    """
    sin_coords = Report(
        event=Evento(usgs_id="us7000sint", mag=7.1, depth_km=30.0, utc="", lugar=""),
        inputs=Inputs(shakemap_version=1, groundfailure_version=1, exposure_manifest="x"),
        totales=Totales(),
    )
    assert _epicentro(sin_coords) is None


def test_municipios_desde_columnas_lon_lat() -> None:
    """Las filas del CSV traen ``lon``/``lat``; el render solo leia WKT."""
    filas = [
        {"lon": -75.7, "lat": 4.8, "mmi_max": 7.5, "pop_mmi7p": 498099.0, "nombre": "PEREIRA"},
        {"lon": -77.1, "lat": 3.6, "mmi_max": 7.0, "pop_mmi7p": 401081.0, "nombre": "BUENAVENTURA"},
    ]
    puntos = _puntos_municipales(filas)
    assert len(puntos) == 2
    assert puntos[0][:3] == (-75.7, 4.8, 7.5)


def test_municipios_acepta_wkt_como_respaldo() -> None:
    filas = [{"centroide": "POINT (-74.1 4.6)", "mmi_max": 6.5, "pop_mmi7p": 10.0, "nombre": "X"}]
    assert _puntos_municipales(filas)[0][:2] == (-74.1, 4.6)


def test_municipio_sin_coordenadas_se_descarta() -> None:
    assert _puntos_municipales([{"mmi_max": 7.0, "nombre": "X"}]) == []
    assert _coordenada({"lon": "", "lat": ""}) is None


def test_la_rampa_cubre_la_intensidad_maxima_publicada() -> None:
    """El evento de Catia La Mar llega a 8,5 y la rampa se quedaba en 8,0."""
    assert 8.5 in MMI_COLORS
    assert color_for_mmi(8.5) != color_for_mmi(8.0)


def test_la_rampa_es_monotona_en_luminosidad() -> None:
    """Requisito del modulo: legible impresa en blanco y negro."""

    def luminancia(hexa: str) -> float:
        canales = [int(hexa[i : i + 2], 16) / 255 for i in (1, 3, 5)]
        lineal = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in canales]
        return 0.2126 * lineal[0] + 0.7152 * lineal[1] + 0.0722 * lineal[2]

    valores = [luminancia(MMI_COLORS[v]) for v in sorted(MMI_COLORS)]
    assert valores == sorted(valores, reverse=True)
    assert all(a - b > 0.02 for a, b in pairwise(valores))


def test_banda_por_debajo_del_minimo_cae_en_la_primera() -> None:
    assert banda_de_mmi(5.0) == 6.0
    assert banda_de_mmi(7.4) == 7.0


@pytest.mark.render
def test_render_dibuja_los_municipios(reporte: Report, tmp_path: Path) -> None:
    """Un PNG con municipios pesa mas que uno vacio.

    No se compara pixel a pixel —seria fragil frente a cualquier version de
    matplotlib— pero un mapa que dibuja 60 puntos y sus etiquetas no puede pesar
    lo mismo que uno que no dibuja ninguno, y ese era exactamente el sintoma.
    """
    pytest.importorskip("matplotlib")
    filas = [
        {
            "lon": -77.0 + i * 0.05,
            "lat": 6.0 + i * 0.04,
            "mmi_max": 6.0 + (i % 6) * 0.5,
            "pop_mmi7p": 1000.0 * (i + 1),
            "nombre": f"MUNICIPIO {i}",
        }
        for i in range(60)
    ]
    con = tmp_path / "con.png"
    sin = tmp_path / "sin.png"
    render_map(reporte, MapVariant.GENERAL, con, municipios=filas)
    render_map(reporte, MapVariant.GENERAL, sin, municipios=[])
    assert con.stat().st_size > sin.stat().st_size
