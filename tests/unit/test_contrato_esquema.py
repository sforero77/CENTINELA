"""El contrato de `schemas/parquet/tables.yaml` contra el activo que se produce.

Ese fichero declara las columnas del activo, sus tipos y de donde sale cada una.
**No lo referenciaba ni una linea de codigo**, asi que derivo: no declaraba
`built_m2`, anadida al meter GHS-BUILT-S, y seguia atribuyendo salud a REPS y
educacion al MEN cuando las dos fuentes se habian resuelto en contra.

Es el mismo patron que el calculo del reporte preliminar escrito y sin llamar:
un artefacto correcto que nadie ejecuta deja de ser correcto sin avisar.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

RAIZ = Path(__file__).parent.parent.parent
CONTRATO = RAIZ / "schemas" / "parquet" / "tables.yaml"


@pytest.fixture(scope="module")
def contrato() -> dict[str, Any]:
    datos: dict[str, Any] = yaml.safe_load(CONTRATO.read_text(encoding="utf-8"))
    return datos


def _columnas_reales() -> list[str]:
    """Las columnas que `assemble_exposure` produce de verdad."""
    from pipelines.p0_exposure.build import assemble_exposure, ensure_layer_tables
    from pipelines.p2_impact.exposure_join import connect

    con = connect()
    con.execute(
        "CREATE TABLE crosswalk_h3_adm AS SELECT 0::UBIGINT AS h3_08, 'X' AS adm2_id, "
        "1.0 AS frac_area, FALSE AS rescatada"
    )
    con.execute(
        "CREATE TABLE admin_lookup AS SELECT 'X' AS adm2_id, 'Uno' AS nombre, "
        "'01' AS adm1_id, 'Depto' AS departamento"
    )
    ensure_layer_tables(con)
    assemble_exposure(con, iso3="XXX", manifest_id="xxx-v0.1")
    return [c[0] for c in con.execute("DESCRIBE exposure_h3").fetchall()]


@pytest.mark.geo
def test_el_contrato_declara_lo_que_el_activo_produce(contrato: dict[str, Any]) -> None:
    declaradas = {c["nombre"] for c in contrato["exposure_h3"]["columnas"]}
    reales = set(_columnas_reales())
    faltan = reales - declaradas
    sobran = declaradas - reales
    assert not faltan, (
        f"El activo produce columnas que el contrato no declara: {sorted(faltan)}. "
        f"Anadelas a schemas/parquet/tables.yaml con su fuente."
    )
    assert not sobran, (
        f"El contrato declara columnas que el activo no produce: {sorted(sobran)}. "
        f"O se dejo de construir una capa, o el contrato quedo viejo."
    )


def test_ninguna_fuente_descartada_sigue_declarada(contrato: dict[str, Any]) -> None:
    """REPS (T0.5) y el directorio del MEN (T0.6) se resolvieron en contra.

    Seguian figurando como fuente de salud y educacion. Un contrato que nombra
    una fuente que no se usa es peor que uno incompleto: parece trazabilidad.
    """
    descartadas = ("REPS", "MEN")
    for col in contrato["exposure_h3"]["columnas"]:
        fuente = str(col.get("fuente", ""))
        for mala in descartadas:
            assert mala not in fuente.split(), (
                f"La columna {col['nombre']} declara {mala} como fuente, y se descarto."
            )


def test_la_puerta_a_embeddings_esta_declarada(contrato: dict[str, Any]) -> None:
    """T3.1: la decision es de licencia, no de calidad, y hay que dejarla escrita.

    AlphaEarth es CC-BY 4.0 y puede entrar al activo con su atribucion. Major TOM
    es CC-BY-SA 4.0 y no puede sin arrastrar el cubo entero.
    """
    extension = contrato["exposure_h3"]["extension_embeddings"]
    nombres = {c["nombre"] for c in extension}
    assert "emb_alphaearth" in nombres
    fuentes = " ".join(str(c["fuente"]) for c in extension)
    assert "CC-BY 4.0" in fuentes
    # Y la columna es nula: un activo sin embeddings sigue siendo valido.
    assert all(c["nulo"] for c in extension)


def test_la_clave_y_el_particionado_no_cambian(contrato: dict[str, Any]) -> None:
    """Lo que sostiene "sin refactor": anadir columnas no toca ni la una ni el otro."""
    tabla = contrato["exposure_h3"]
    assert tabla["clave_primaria"] == ["h3_08"]
    assert tabla["particion"] == ["iso3", "layer"]
