"""Seleccion de rasters de WorldPop age-sex.

El listado de la fixture es el real del release R2025A de Colombia, epoca 2025,
recortado a las bandas que importan mas las trampas que hay que esquivar.
"""

from __future__ import annotations

import pytest

from pipelines.p0_exposure.sources.worldpop import (
    AGE_GROUPS,
    age_band,
    missing_bands,
    parse_listing,
    raster_url,
    select_age_rasters,
)

DIRECTORIO = (
    "https://data.worldpop.org/GIS/AgeSex_structures/Global_2015_2030/"
    "R2025A/2025/COL/v1/100m/constrained/"
)

#: Bandas reales del release: 20 por serie, de 00 a 90.
BANDAS_REALES = (
    "00",
    "01",
    "05",
    "10",
    "15",
    "20",
    "25",
    "30",
    "35",
    "40",
    "45",
    "50",
    "55",
    "60",
    "65",
    "70",
    "75",
    "80",
    "85",
    "90",
)


def _listado_real() -> str:
    nombres = ["col_T_F_2025_CN_100m_R2025A_v1.tif", "col_T_M_2025_CN_100m_R2025A_v1.tif"]
    for serie in ("f", "m", "t"):
        nombres += [f"col_{serie}_{banda}_2025_CN_100m_R2025A_v1.tif" for banda in BANDAS_REALES]
    filas = "".join(f'<tr><td><a href="{n}">{n}</a></td></tr>' for n in nombres)
    return f"<html><body><table>{filas}</table></body></html>"


def test_el_listado_real_trae_62_rasters() -> None:
    """Tres series de 20 bandas mas los dos totales por sexo."""
    assert len(parse_listing(_listado_real())) == 62


def test_solo_entra_la_serie_combinada() -> None:
    """La trampa: sumar f + m + t contaria a cada persona dos veces."""
    seleccion = select_age_rasters(parse_listing(_listado_real()))
    elegidos = [n for nombres in seleccion.values() for n in nombres]
    assert all("_t_" in nombre for nombre in elegidos)
    assert not any("_f_" in nombre or "_m_" in nombre for nombre in elegidos)


def test_los_totales_por_sexo_no_se_cuelan() -> None:
    """``col_T_F`` es el total femenino, no una banda de edad."""
    assert age_band("col_T_F_2025_CN_100m_R2025A_v1.tif") is None
    assert age_band("col_T_M_2025_CN_100m_R2025A_v1.tif") is None
    assert age_band("col_t_65_2025_CN_100m_R2025A_v1.tif") == "65"


def test_las_columnas_no_se_solapan() -> None:
    """Una banda en dos columnas sumaria a la misma gente dos veces."""
    seleccion = select_age_rasters(parse_listing(_listado_real()))
    elegidos = [n for nombres in seleccion.values() for n in nombres]
    assert len(elegidos) == len(set(elegidos))
    assert set(seleccion) == set(AGE_GROUPS)


def test_la_banda_superior_es_90_no_80() -> None:
    """Cortar en 80 dejaria fuera a los mas expuestos de todos."""
    seleccion = select_age_rasters(parse_listing(_listado_real()))
    assert any("_t_90_" in nombre for nombre in seleccion["pop_65p"])
    assert len(seleccion["pop_65p"]) == 6  # 65, 70, 75, 80, 85, 90


def test_la_banda_central_no_se_descarga() -> None:
    """15-64 es el residuo de pop_total: traerla seria pagar por una resta."""
    seleccion = select_age_rasters(parse_listing(_listado_real()))
    elegidos = [n for nombres in seleccion.values() for n in nombres]
    assert not any(f"_t_{banda}_" in n for n in elegidos for banda in ("15", "30", "60"))


def test_una_banda_ausente_se_reporta() -> None:
    """Un hueco silencioso publica menos adultos mayores con cifra plausible."""
    sin_90 = [n for n in parse_listing(_listado_real()) if "_t_90_" not in n]
    faltantes = missing_bands(select_age_rasters(sin_90), sin_90)
    assert faltantes == {"pop_65p": ["90"]}


def test_un_listado_completo_no_reporta_huecos() -> None:
    nombres = parse_listing(_listado_real())
    assert missing_bands(select_age_rasters(nombres), nombres) == {}


@pytest.mark.parametrize("base", [DIRECTORIO, DIRECTORIO.rstrip("/")])
def test_la_url_se_arma_con_o_sin_barra(base: str) -> None:
    assert raster_url(base, "col_t_65.tif") == f"{DIRECTORIO}col_t_65.tif"
