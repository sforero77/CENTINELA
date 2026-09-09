"""Las cifras nacionales se arman por nombre y no por posicion.

`ImpactTotals(*fila)` volcaba veinte sumas sin alias en el orden en que
`SQL_TOTALES` las escribia. Los dos ficheros eran correctos por separado; lo que
estaba mal era la costura, y una costura no se ve leyendo ninguno de los dos.

Comprobado antes del arreglo: intercambiar las dos lineas de salud y educacion
del SQL dejaba la suite entera en verde, y el reporte publicaba "1.003 sedes de
salud" donde hay 516 y "516 sedes educativas" donde hay 1.003. Nadie se habria
dado cuenta: las dos cifras son plausibles y ninguna prueba las ataba a su
expresion.
"""

from __future__ import annotations

from dataclasses import fields
from typing import Any

import pytest

from pipelines.common.constants import GROUND_FAILURE_HIGH_PROB, MMI_BAND_AGE_BREAKDOWN
from pipelines.p2_impact.pipeline import SQL_TOTALES, ImpactTotals, leer_totales

#: Campos de `ImpactTotals` que no salen de una columna del SQL.
FUERA_DEL_SQL = {"columnas_ausentes"}

#: Una celda por banda, con cifras distintas en cada columna para que una
#: permutacion no pueda pasar desapercibida.
CELDAS = [
    # mmi_max, pop_total, pop_65p, bld, built_m2, health, edu, prim, sec, other, ls, lq
    # `ls_prob` alto solo en la primera y `lq_prob` solo en la segunda, para que
    # las dos cifras de terreno no puedan salir iguales por casualidad. El
    # umbral es GROUND_FAILURE_HIGH_PROB = 0,10.
    (8.2, 1000.0, 100.0, 11.0, 2100.0, 3.0, 5.0, 1.5, 2.5, 4.5, 0.9, 0.01),
    (7.1, 2000.0, 200.0, 22.0, 3200.0, 7.0, 9.0, 2.5, 3.5, 5.5, 0.01, 0.9),
    (6.4, 4000.0, 400.0, 33.0, 4300.0, 13.0, 17.0, 3.5, 4.5, 6.5, 0.0, 0.0),
    # Por debajo de la banda publicada: no debe entrar en ninguna cifra.
    (5.2, 8000.0, 800.0, 99.0, 9900.0, 99.0, 99.0, 9.9, 9.9, 9.9, 1.0, 1.0),
]


@pytest.fixture
def con() -> Any:
    from pipelines.p2_impact.exposure_join import connect

    con = connect()
    valores = ", ".join(str(c) for c in CELDAS)
    con.execute(
        "CREATE OR REPLACE TABLE impact_h3 AS SELECT * FROM (VALUES "
        f"{valores}) AS t(mmi_max, pop_total, pop_65p, bld_count, built_m2, "
        "health_count, edu_count, road_km_primary, road_km_secondary, "
        "road_km_other, ls_prob, lq_prob)"
    )
    con.execute("ALTER TABLE impact_h3 ADD COLUMN pop_alt_worldpop DOUBLE DEFAULT 0.0")
    con.execute("UPDATE impact_h3 SET pop_alt_worldpop = pop_total * 1.1")
    return con


def test_el_sql_nombra_exactamente_los_campos_del_dataclass() -> None:
    """La costura, comprobada sin ejecutar nada.

    Basta con que el SQL y el dataclass declaren el mismo conjunto de nombres:
    si alguien anade una suma y olvida el campo, o al reves, esto lo dice.
    """
    sql = SQL_TOTALES.format(edad=MMI_BAND_AGE_BREAKDOWN, gf=GROUND_FAILURE_HIGH_PROB)
    alias = {
        linea.rsplit(" AS ", 1)[1].strip().rstrip(",")
        for linea in sql.splitlines()
        if " AS " in linea
    }
    campos = {f.name for f in fields(ImpactTotals)} - FUERA_DEL_SQL
    assert alias == campos, (
        f"el SQL y ImpactTotals no declaran los mismos nombres; "
        f"solo en el SQL: {sorted(alias - campos)}; solo en el dataclass: {sorted(campos - alias)}"
    )


@pytest.mark.geo
def test_cada_cifra_sale_de_su_expresion(con: Any) -> None:
    """La prueba que el intercambio de salud y educacion tenia que romper."""
    t = leer_totales(con)

    # Poblacion por banda: acumulativa hacia arriba.
    assert t.pop_mmi8p == pytest.approx(1000.0)
    assert t.pop_mmi7p == pytest.approx(3000.0)
    assert t.pop_mmi6p == pytest.approx(7000.0)
    assert t.pop_65p_mmi7p == pytest.approx(300.0)
    assert t.pop_65p_mmi6p == pytest.approx(700.0)

    # Equipamiento: salud y educacion tienen cifras distintas a proposito.
    assert t.health_mmi7p == pytest.approx(10.0)
    assert t.edu_mmi7p == pytest.approx(14.0)
    assert t.health_mmi6p == pytest.approx(23.0)
    assert t.edu_mmi6p == pytest.approx(31.0)
    assert t.health_mmi7p != t.edu_mmi7p, "sin cifras distintas la permutacion no se veria"

    assert t.bld_mmi7p == pytest.approx(33.0)
    assert t.bld_mmi6p == pytest.approx(66.0)
    assert t.built_m2_mmi7p == pytest.approx(5300.0)
    assert t.built_m2_mmi6p == pytest.approx(9600.0)

    # Vias: el total incluye `other`; la principal, no.
    assert t.road_km_mmi7p == pytest.approx(1.5 + 2.5 + 4.5 + 2.5 + 3.5 + 5.5)
    assert t.road_km_principal_mmi7p == pytest.approx(1.5 + 2.5 + 2.5 + 3.5)
    assert t.road_km_mmi7p > t.road_km_principal_mmi7p

    # Terreno: la celda de MMI 8 tiene deslizamiento y la de 7 licuefaccion.
    assert t.pop_ls_alta == pytest.approx(1000.0)
    assert t.pop_lq_alta == pytest.approx(2000.0)
    assert t.pop_ls_alta != t.pop_lq_alta


@pytest.mark.geo
def test_la_banda_por_debajo_de_6_no_entra_en_ninguna_cifra(con: Any) -> None:
    """El WHERE del SQL. La celda de MMI 5,2 lleva 8.000 personas."""
    t = leer_totales(con)
    assert t.pop_mmi6p == pytest.approx(7000.0)
    assert t.health_mmi6p == pytest.approx(23.0)


@pytest.mark.geo
def test_una_columna_renombrada_en_el_sql_revienta_en_vez_de_correrse(con: Any) -> None:
    """Antes, quitar o renombrar una columna corria las demas una posicion."""
    import pipelines.p2_impact.pipeline as modulo

    original = modulo.SQL_TOTALES
    try:
        modulo.SQL_TOTALES = original.replace("AS health_mmi7p", "AS sedes_de_salud")
        with pytest.raises(TypeError, match="sedes_de_salud"):
            leer_totales(con)
    finally:
        modulo.SQL_TOTALES = original


@pytest.mark.geo
def test_la_discrepancia_sin_worldpop_es_none_y_no_cero(con: Any) -> None:
    """ "Coinciden perfectamente" es lo contrario de "no habia con que comparar"."""
    con.execute("UPDATE impact_h3 SET pop_alt_worldpop = 0.0")
    assert leer_totales(con).discrepancia_pct is None
