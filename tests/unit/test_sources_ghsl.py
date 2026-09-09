"""Seleccion de teselas de GHS-POP.

Los valores esperados salen de la georreferenciacion real de la tesela
R9_C11 leida con rasterio, no de la documentacion.
"""

from __future__ import annotations

import pytest

from pipelines.common.geo import BBox
from pipelines.p0_exposure.sources.ghsl import (
    NODATA,
    RELEASE,
    Tile,
    global_url,
    tiles_for_mollweide_bbox,
)


def test_nombre_y_url_de_la_tesela() -> None:
    t = Tile(row=9, col=11)
    assert t.name == "GHS_POP_E2025_GLOBE_R2023A_54009_100_V1_0_R9_C11"
    assert t.url.endswith("/tiles/GHS_POP_E2025_GLOBE_R2023A_54009_100_V1_0_R9_C11.zip")


def test_los_limites_coinciden_con_el_raster_real() -> None:
    """Medido con rasterio sobre la tesela descargada: x [-8041000, -7041000],
    y [0, 1000000]."""
    assert Tile(row=9, col=11).bounds_mollweide == (-8_041_000.0, 0.0, -7_041_000.0, 1_000_000.0)


def test_las_teselas_vecinas_encajan_sin_hueco_ni_solape() -> None:
    a = Tile(row=9, col=11).bounds_mollweide
    derecha = Tile(row=9, col=12).bounds_mollweide
    abajo = Tile(row=10, col=11).bounds_mollweide
    assert a[2] == derecha[0]
    assert a[1] == abajo[3]


def test_seleccion_por_caja_mollweide() -> None:
    """Extension real de Colombia en Mollweide, calculada con pyproj."""
    teselas = tiles_for_mollweide_bbox(-8_218_266, -531_482, -6_580_074, 1_663_278)
    assert {(t.row, t.col) for t in teselas} == {(r, c) for r in (8, 9, 10) for c in (10, 11, 12)}


def test_una_caja_dentro_de_una_tesela_devuelve_una() -> None:
    teselas = tiles_for_mollweide_bbox(-7_500_000, 200_000, -7_400_000, 300_000)
    assert [(t.row, t.col) for t in teselas] == [(9, 11)]


def test_el_nodata_es_negativo_y_debe_enmascararse() -> None:
    """22 millones de celdas por tesela valen -200: sumarlas da poblacion negativa."""
    assert NODATA == -200.0


def test_el_release_global_vigente_sigue_siendo_r2023a() -> None:
    assert RELEASE == "R2023A"
    assert "R2023A" in global_url()


@pytest.mark.geo
def test_seleccion_por_caja_en_grados() -> None:
    from pipelines.p0_exposure.sources.ghsl import tiles_for_bbox

    colombia = BBox(lon_min=-82.0, lat_min=-4.3, lon_max=-66.8, lat_max=13.5)
    filas = {t.row for t in tiles_for_bbox(colombia)}
    columnas = {t.col for t in tiles_for_bbox(colombia)}
    assert filas == {8, 9, 10}
    assert columnas == {10, 11, 12}
