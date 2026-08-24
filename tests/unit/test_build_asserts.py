"""Asserts de calidad del activo (§6.4).

La prueba central de este archivo cubre un fallo real: una capa que no se
construye entra vacia por ``ensure_layer_tables``, el LEFT JOIN la convierte en
ceros y el activo se escribe sin que nada proteste. El assert de total nacional
no lo ve porque solo mira poblacion.
"""

from __future__ import annotations

from typing import Any

import pytest

from pipelines.p0_exposure.build import REQUIRED_COVERAGE, validate_layer_coverage

#: Una celda con todas las capas presentes. Los valores son irrelevantes: lo
#: que se prueba es que ninguna columna requerida quede entera en cero.
CELDA_COMPLETA = {
    "pop_total": 1200.0,
    "pop_0_14": 300.0,
    "pop_65p": 150.0,
    "pop_alt_worldpop": 1180.0,
    "bld_count": 320,
    "built_m2": 45000.0,
    "road_km_primary": 1.2,
    "road_km_secondary": 0.8,
    "road_km_other": 3.1,
    "health_count": 2,
    "edu_count": 5,
}


def _exposure(con: Any, **anulados: float) -> None:
    """Materializa ``exposure_h3`` con una fila, anulando las capas indicadas."""
    fila = {**CELDA_COMPLETA, **anulados}
    columnas = ", ".join(f"{valor} AS {nombre}" for nombre, valor in fila.items())
    con.execute(f"CREATE OR REPLACE TABLE exposure_h3 AS SELECT {columnas}")


@pytest.fixture
def con() -> Any:
    import duckdb

    return duckdb.connect()


@pytest.mark.geo
def test_un_activo_completo_pasa(con: Any) -> None:
    _exposure(con)
    assert validate_layer_coverage(con) == []


@pytest.mark.geo
@pytest.mark.parametrize(
    ("anulados", "capa"),
    [
        ({"bld_count": 0}, "buildings"),
        ({"built_m2": 0.0}, "built_ghsl"),
        ({"road_km_primary": 0.0, "road_km_secondary": 0.0, "road_km_other": 0.0}, "roads"),
        ({"pop_65p": 0.0}, "pop_worldpop_agesex"),
        ({"pop_0_14": 0.0}, "pop_worldpop_agesex"),
        ({"health_count": 0}, "health"),
        ({"edu_count": 0}, "education"),
        ({"pop_alt_worldpop": 0.0}, "pop_worldpop_total"),
    ],
)
def test_una_capa_que_no_se_construyo_detiene_el_build(
    con: Any, anulados: dict[str, float], capa: str
) -> None:
    """El cero silencioso es el modo de falla que este assert existe para matar."""
    _exposure(con, **anulados)
    problemas = validate_layer_coverage(con)
    assert problemas, f"la capa {capa} vacia paso desapercibida"
    assert capa in problemas[0]


@pytest.mark.geo
def test_el_assert_nombra_la_capa_del_manifest(con: Any) -> None:
    """El mensaje tiene que decir que arreglar, no solo que fallo."""
    _exposure(con, bld_count=0)
    assert "buildings" in validate_layer_coverage(con)[0]


def test_todas_las_capas_requeridas_estan_cubiertas() -> None:
    """El assert y el catalogo de capas no pueden divergir."""
    from pipelines.p0_exposure.layers import required_layers

    vigiladas = {capa for _, _, capa in REQUIRED_COVERAGE}
    sin_vigilar = {
        capa.id for capa in required_layers() if capa.id not in vigiladas and capa.columnas
    }
    assert sin_vigilar == {"divisions"}, (
        f"Capas requeridas sin assert de cobertura: {sin_vigilar}. "
        f"'divisions' se exceptua porque sin ella no hay crosswalk y el build "
        f"ya falla antes de llegar aqui."
    )
