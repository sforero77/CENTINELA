"""Un activo publicado antes que el codigo tiene que seguir dando un reporte.

El caso real: `built_m2` llega en col-v0.5, y el Release publicado en ese
momento era col-v0.4. Entre actualizar el codigo y republicar el activo hay una
ventana, y si el primer sismo cae dentro no puede quedarse sin reporte.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from pipelines.p2_impact.pipeline import COLUMNAS_OPCIONALES, register_exposure_view

#: Columnas de col-v0.4, sin `built_m2`.
COLUMNAS_V04 = (
    "h3_08 UBIGINT, iso3 VARCHAR, adm1_id VARCHAR, adm2_id VARCHAR, "
    "pop_total DOUBLE, pop_0_14 DOUBLE, pop_15_64 DOUBLE, pop_65p DOUBLE, "
    "pop_alt_worldpop DOUBLE, bld_count BIGINT, bld_area_m2 DOUBLE, "
    "health_count BIGINT, edu_count BIGINT, road_km_primary DOUBLE, "
    "road_km_secondary DOUBLE, road_km_other DOUBLE, "
    "flags_calidad VARCHAR, src_manifest VARCHAR"
)


@pytest.fixture
def con() -> Any:
    from pipelines.p2_impact.exposure_join import connect

    return connect()


def _activo(con: Any, tmp_path: Path, columnas: str, *, built: bool) -> str:
    extra = ", 1500.0 AS built_m2" if built else ""
    con.execute(f"CREATE OR REPLACE TABLE _tmp ({columnas})")
    con.execute(
        "INSERT INTO _tmp SELECT 1::UBIGINT, 'COL', '05', '05001', 100.0, 20.0, 70.0, 10.0, "
        "105.0, 8, 900.0, 1, 2, 0.5, 0.3, 1.1, NULL, 'col-v0.4'"
    )
    destino = tmp_path / "exposure_h3.parquet"
    con.execute(f"COPY (SELECT *{extra} FROM _tmp) TO '{destino.as_posix()}' (FORMAT PARQUET)")
    return destino.as_posix()


@pytest.mark.geo
def test_un_activo_al_dia_no_sustituye_nada(con: Any, tmp_path: Path) -> None:
    ruta = _activo(con, tmp_path, COLUMNAS_V04, built=True)
    assert register_exposure_view(con, ruta) == []
    assert con.execute("SELECT built_m2 FROM exposure").fetchone()[0] == 1500.0


@pytest.mark.geo
def test_un_activo_v04_sigue_sirviendo(con: Any, tmp_path: Path) -> None:
    """Sin esto, el primer sismo tras actualizar el codigo se queda sin reporte."""
    ruta = _activo(con, tmp_path, COLUMNAS_V04, built=False)
    assert register_exposure_view(con, ruta) == ["built_m2"]
    assert con.execute("SELECT built_m2 FROM exposure").fetchone()[0] == 0.0


@pytest.mark.geo
def test_el_resto_de_columnas_llega_intacto(con: Any, tmp_path: Path) -> None:
    """Rellenar una columna no puede alterar las que si estaban."""
    ruta = _activo(con, tmp_path, COLUMNAS_V04, built=False)
    register_exposure_view(con, ruta)
    fila = con.execute("SELECT pop_total, bld_count, src_manifest FROM exposure").fetchone()
    assert fila == (100.0, 8, "col-v0.4")


def test_el_sustituto_es_cero_y_eso_es_deliberado() -> None:
    """Cero aqui no se publica como cifra.

    La tabla de totales y la nota de superficie omiten el dato cuando vale 0,
    asi que el reporte muestra una **ausencia**, no "0 km² construidos".
    """
    assert COLUMNAS_OPCIONALES == {"built_m2": "0.0"}
