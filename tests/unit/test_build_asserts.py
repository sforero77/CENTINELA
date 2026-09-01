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
    "lulc_px": 9100,
}


def _exposure(con: Any, **anulados: float) -> None:
    """Materializa ``exposure_h3`` con una fila, anulando las capas indicadas."""
    import math

    def literal(valor: float) -> str:
        """SQL para el valor. DuckDB no acepta `nan` ni `inf` a secas."""
        if isinstance(valor, float) and not math.isfinite(valor):
            return (
                "'NaN'::DOUBLE"
                if math.isnan(valor)
                else f"'{'-' if valor < 0 else ''}Infinity'::DOUBLE"
            )
        return str(valor)

    fila = {**CELDA_COMPLETA, **anulados}
    columnas = ", ".join(f"{literal(valor)} AS {nombre}" for nombre, valor in fila.items())
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
        # La cobertura del suelo no pasa por `_verificar_insumos` —no se
        # descarga— asi que este assert es la unica puerta que la vigila.
        ({"lulc_px": 0}, "landcover"),
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


# --- Valores no finitos -----------------------------------------------------


@pytest.mark.geo
def test_un_nan_en_una_capa_detiene_el_build(con: Any) -> None:
    """`bool(float('nan'))` es True, asi que una comprobacion de veracidad lo deja pasar.

    Ecuador publico un activo con `road_km: NaN` exactamente por eso: la capa
    "aportaba" y la cifra era basura. Un NaN es peor que un cero — se propaga y
    el reporte acabaria imprimiendo "NaN km de via".
    """
    _exposure(con, road_km_primary=float("nan"))
    problemas = validate_layer_coverage(con)
    assert problemas and "no finito" in problemas[0]
    assert "roads" in problemas[0]


@pytest.mark.geo
def test_un_infinito_tambien_detiene_el_build(con: Any) -> None:
    """El filtro `> 0` descarta el NaN pero no el infinito."""
    _exposure(con, built_m2=float("inf"))
    problemas = validate_layer_coverage(con)
    assert problemas and "no finito" in problemas[0]


@pytest.mark.geo
def test_el_mensaje_distingue_no_finito_de_vacio(con: Any) -> None:
    """Son dos averias distintas y se arreglan en sitios distintos."""
    _exposure(con, bld_count=0)
    assert "no aporto nada" in validate_layer_coverage(con)[0]
