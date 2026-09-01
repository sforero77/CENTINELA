"""Fixtures compartidas de las pruebas unitarias.

Vive en un conftest y no en un modulo importable porque `tests/unit` no es
un paquete: un `from .test_x import y` falla con "attempted relative import
with no known parent package".
"""

from __future__ import annotations

import pytest

from pipelines.p3_report.model import (
    Descargas,
    Evento,
    Incertidumbre,
    Inputs,
    MunicipioTop,
    Report,
    Totales,
)


@pytest.fixture
def reporte() -> Report:
    return Report(
        event=Evento(
            usgs_id="us6000tjl2",
            mag=7.4,
            depth_km=110.3,
            utc="2026-08-10T12:34:28Z",
            lugar="5 km al S de San José del Palmar, Chocó, Colombia",
        ),
        inputs=Inputs(shakemap_version=7, groundfailure_version=7, exposure_manifest="col-v0.5"),
        totales=Totales(pop_mmi6p=6_960_086, pop_mmi7p=2_415_793, bld_mmi7p=444_281),
        top_municipios=(MunicipioTop("66001", "Pereira", 7.5, 500_000),),
        incertidumbre=Incertidumbre(pop_discrepancia_pct=3.2),
        descargas=Descargas(csv_adm2="adm2.csv"),
    )


@pytest.fixture
def reporte_completo() -> Report:
    """Un reporte con todo lo que puede tener texto: PAGER, ground failure y
    municipios.

    `reporte` deja fuera la alerta de PAGER y las cifras de terreno, asi que el
    markdown que produce no ejercita las secciones donde se colaron las formas
    sin tilde. Se copia el evento de Muisne porque su toponimo —"27 km al SSE de
    Muisne"— es el que destapa la preposicion del hilo.
    """
    return Report(
        event=Evento(
            usgs_id="us20005j32",
            mag=7.8,
            depth_km=20.59,
            utc="2016-04-16T23:58:36Z",
            lugar="27 km al SSE de Muisne, Ecuador",
            pager_alert="orange",
            lon=-79.9218,
            lat=0.3819,
        ),
        inputs=Inputs(shakemap_version=1, groundfailure_version=1, exposure_manifest="ecu-v0.1"),
        totales=Totales(
            pop_mmi6p=4_311_549,
            pop_mmi7p=2_283_454,
            pop_mmi8p=107_904,
            pop_65p_mmi7p=173_953,
            bld_mmi7p=1_012_045,
            built_m2_mmi7p=131_022_681,
            health_mmi7p=527,
            edu_mmi7p=2_412,
            road_km_mmi7p=23_966,
            road_km_principal_mmi7p=1_713,
            pop_ls_alta=206_312,
            pop_lq_alta=1_160_483,
        ),
        backtest=True,
        top_municipios=(MunicipioTop("EC1317", "Pedernales", 8.0, 65_950),),
        incertidumbre=Incertidumbre(pop_discrepancia_pct=3.2),
        descargas=Descargas(csv_adm2="adm2.csv"),
    )
