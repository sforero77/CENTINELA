"""Que celdas entran al activo y cuales se descartan.

El activo descarta las celdas vacias para no triplicar el parquet. El riesgo es
que "vacia" se defina con menos capas de las que hay: una celda cuyo unico
contenido sea una escuela remota es exactamente la que un reporte de exposicion
no puede permitirse perder.
"""

from __future__ import annotations

from typing import Any

import pytest

from pipelines.p0_exposure.build import SQL_EXPOSURE, SQL_FLAGS, assemble_exposure

#: Una celda por capa: cada una tiene solo esa capa y nada mas.
CAPAS = {
    "pop_h3": ("pop_total", 120.0),
    "bld_h3": ("bld_count", 5),
    "roads_h3": ("road_km_primary", 2.5),
    "health_h3": ("health_count", 1),
    "edu_h3": ("edu_count", 1),
    "built_h3": ("built_m2", 3000.0),
}


@pytest.fixture
def con() -> Any:
    from pipelines.p0_exposure.build import ensure_layer_tables
    from pipelines.p2_impact.exposure_join import connect

    con = connect()
    con.execute(
        "CREATE OR REPLACE TABLE crosswalk_h3_adm AS "
        "SELECT * FROM (VALUES " + ",".join(f"({i}::UBIGINT, '05001')" for i in range(1, 8)) + ") "
        "AS t(h3_08, adm2_id)"
    )
    con.execute(
        "CREATE OR REPLACE TABLE admin_lookup AS SELECT '05001' AS adm2_id, '05' AS adm1_id"
    )
    ensure_layer_tables(con)
    return con


def _sembrar(con: Any) -> dict[int, str]:
    """Una celda por capa. Devuelve h3 -> capa que la sostiene."""
    quien: dict[int, str] = {}
    for i, (tabla, (columna, valor)) in enumerate(CAPAS.items(), start=1):
        con.execute(f"INSERT INTO {tabla} (h3_08, {columna}) VALUES ({i}::UBIGINT, {valor})")
        quien[i] = tabla
    return quien


@pytest.mark.geo
def test_ninguna_capa_sostiene_su_celda_sola_menos_las_declaradas(con: Any) -> None:
    """Cada una de las seis capas de contenido debe bastar por si sola."""
    quien = _sembrar(con)
    assemble_exposure(con, iso3="COL", manifest_id="test")
    presentes = {int(r[0]) for r in con.execute("SELECT h3_08 FROM exposure_h3").fetchall()}
    perdidas = {quien[h] for h in quien if h not in presentes}
    assert perdidas == set(), f"estas capas no bastan para conservar su celda: {perdidas}"


@pytest.mark.geo
def test_una_escuela_sola_conserva_su_celda(con: Any) -> None:
    """El caso real: 28 sedes educativas se perdieron por esto.

    Estaban en celdas que solo se salvaban porque pasaba un sendero, y al dejar
    de contar los senderos como via la celda —y la escuela— desaparecieron.
    """
    con.execute("INSERT INTO edu_h3 (h3_08, edu_count) VALUES (1::UBIGINT, 1)")
    assemble_exposure(con, iso3="COL", manifest_id="test")
    assert con.execute("SELECT sum(edu_count) FROM exposure_h3").fetchone()[0] == 1


@pytest.mark.geo
def test_un_hospital_solo_conserva_su_celda(con: Any) -> None:
    con.execute("INSERT INTO health_h3 (h3_08, health_count) VALUES (1::UBIGINT, 1)")
    assemble_exposure(con, iso3="COL", manifest_id="test")
    assert con.execute("SELECT sum(health_count) FROM exposure_h3").fetchone()[0] == 1


@pytest.mark.geo
def test_una_celda_del_todo_vacia_si_se_descarta(con: Any) -> None:
    """El filtro tiene que seguir existiendo: sin el, el parquet se triplica."""
    assemble_exposure(con, iso3="COL", manifest_id="test")
    assert con.execute("SELECT count(*) FROM exposure_h3").fetchone()[0] == 0


def test_el_filtro_menciona_las_seis_capas_de_contenido() -> None:
    """Guardia de texto: anadir una capa obliga a revisar este filtro."""
    where = SQL_EXPOSURE.format(iso3="COL", manifest="m", flags=SQL_FLAGS).split("WHERE")[1]
    for columna in (
        "pop_total",
        "bld_count",
        "road_km_primary",
        "health_count",
        "edu_count",
        "built_m2",
    ):
        assert columna in where, f"{columna} no sostiene su celda en el filtro"


@pytest.mark.geo
def test_una_celda_con_solo_via_primaria_se_conserva(con: Any) -> None:
    """`COALESCE(a + b + c, 0)` da NULL si cualquiera lo es, y descarta la celda.

    En el pipeline real las tres columnas de via siempre llegan con valor, asi
    que no se notaba; basta que una fuente futura deje una en NULL para perder
    celdas con via. Cada termino coalesce por separado.
    """
    con.execute("INSERT INTO roads_h3 (h3_08, road_km_primary) VALUES (1::UBIGINT, 2.5)")
    assemble_exposure(con, iso3="COL", manifest_id="test")
    fila = con.execute("SELECT count(*), sum(road_km_primary) FROM exposure_h3").fetchone()
    assert fila == (1, 2.5)
