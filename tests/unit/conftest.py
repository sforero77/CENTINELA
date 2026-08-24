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
