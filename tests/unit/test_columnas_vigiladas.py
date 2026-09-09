"""Ninguna columna publicada del activo puede quedarse sin guardia.

`REQUIRED_COVERAGE` se escribio incidente a incidente: diez expresiones sobre un
activo de veintiseis columnas. Lo que quedaba fuera quedaba fuera en silencio, y
`bld_area_m2` era una de esas: Mexico publico un activo con el 96,1 % de sus
celdas con edificacion en NaN y el build termino en verde, porque el unico
centinela de la capa de edificaciones era `sum(bld_count)`.

La leccion no es "anadir bld_area_m2 a la lista". Es que la lista no puede ser
la unica puerta: `validate_finite_values` le pregunta a la tabla que columnas
tiene, asi que una columna nueva queda vigilada el dia que se anade.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

from pipelines.p0_exposure.build import (
    ASSERTS_DEL_ACTIVO,
    REQUIRED_COVERAGE,
    columnas_no_finitas,
    validate_finite_values,
)

RAIZ = Path(__file__).parent.parent.parent
CONTRATO = RAIZ / "schemas" / "parquet" / "tables.yaml"

#: Columnas del contrato que no son cifras de exposicion y no llevan guardia.
NO_NUMERICAS = {"h3_08", "iso3", "adm1_id", "adm2_id", "flags_calidad", "src_manifest"}


@pytest.fixture
def con() -> Any:
    from pipelines.p2_impact.exposure_join import connect

    return connect()


def _tabla(con: Any, **columnas: object) -> None:
    def literal(v: object) -> str:
        if isinstance(v, float) and v != v:
            return "'NaN'::DOUBLE"
        if v == float("inf"):
            return "'Infinity'::DOUBLE"
        return str(v)

    expr = ", ".join(f"{literal(v)} AS {k}" for k, v in columnas.items())
    con.execute(f"CREATE OR REPLACE TABLE exposure_h3 AS SELECT {expr}")


@pytest.mark.geo
def test_un_activo_finito_pasa(con: Any) -> None:
    _tabla(con, pop_total=100.0, bld_area_m2=4200.0, bld_count=3)
    assert validate_finite_values(con) == []


@pytest.mark.geo
def test_el_nan_de_mexico_detiene_el_build(con: Any) -> None:
    """El caso exacto: area NaN con el conteo de edificaciones intacto."""
    _tabla(con, pop_total=100.0, bld_area_m2=float("nan"), bld_count=3)
    problemas = validate_finite_values(con)
    assert problemas and "bld_area_m2" in problemas[0]


@pytest.mark.geo
def test_el_infinito_tambien(con: Any) -> None:
    _tabla(con, pop_total=100.0, bld_area_m2=float("inf"), bld_count=3)
    assert validate_finite_values(con)


@pytest.mark.geo
def test_una_columna_nueva_queda_vigilada_sin_tocar_ninguna_lista(con: Any) -> None:
    """La propiedad que hace que esto no vuelva a pasar."""
    _tabla(con, pop_total=100.0, columna_inventada_m2=float("nan"))
    assert columnas_no_finitas(con) == ["columna_inventada_m2"]


@pytest.mark.geo
def test_los_enteros_no_se_consultan(con: Any) -> None:
    """`isfinite` sobre un BIGINT no aporta y en algunas versiones da error."""
    con.execute(
        "CREATE OR REPLACE TABLE exposure_h3 AS SELECT 3::BIGINT AS bld_count, "
        "9::INTEGER AS edu_count, 1.0::DOUBLE AS pop_total"
    )
    assert columnas_no_finitas(con) == []


def test_toda_columna_numerica_del_contrato_esta_vigilada() -> None:
    """El contrato manda sobre el guardia, y no al reves.

    Una columna se publica porque esta en `tables.yaml`; que ademas se vigile no
    puede depender de que alguien se acuerde de anadirla a `REQUIRED_COVERAGE`.
    """
    contrato = yaml.safe_load(CONTRATO.read_text(encoding="utf-8"))
    numericas = {
        c["nombre"] for c in contrato["exposure_h3"]["columnas"] if c["nombre"] not in NO_NUMERICAS
    }
    en_cobertura = {c for c in numericas if any(c in expr for expr, _, _ in REQUIRED_COVERAGE)}
    sin_cobertura = numericas - en_cobertura

    # Las que no llevan assert de no-cero tienen una razon: pueden ser cero de
    # verdad en un pais. Lo que ninguna puede es quedarse sin el barrido de
    # finitud, y ese cubre la tabla entera por construccion.
    assert validate_finite_values in ASSERTS_DEL_ACTIVO, (
        "sin el barrido de finitud, estas columnas no tendrian ninguna puerta: "
        f"{sorted(sin_cobertura)}"
    )

    # Y las capas que un pais no puede tener vacias si llevan assert de no-cero.
    debe_aportar = {
        "pop_total",
        "pop_0_14",
        "pop_65p",
        "pop_alt_worldpop",
        "bld_count",
        "bld_area_m2",
        "built_m2",
        "health_count",
        "edu_count",
        "lulc_px",
    }
    assert debe_aportar <= en_cobertura, (
        f"capas que no pueden quedar en cero y no tienen assert: "
        f"{sorted(debe_aportar - en_cobertura)}"
    )
