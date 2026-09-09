"""Las tres bandas etarias tienen que sumar la poblacion de su celda.

No sumaban. `pop_total` sale de GHS-POP y `pop_0_14` / `pop_65p` salian de
WorldPop age-sex como **conteos absolutos**, metidos en la misma fila. Son dos
modelos de poblacion distintos: a escala nacional coinciden (Colombia, 53,0 M
de WorldPop frente a 52,6 M de GHS-POP) pero reparten la gente en celdas
distintas. Medido sobre el activo publicado, el 31 % de las celdas de Colombia
tenia mas mayores de 65 anios que habitantes, y el 40 % sumaba las bandas por
encima del total.

Y salio al dato publicado, no se quedo en el parquet:
`reports/us6000tjl2/adm2.csv` publica EL CARMEN DE ATRATO con 69,21 habitantes
y 128,23 mayores de 65 en MMI>=6, y MISTRATO con 27,80 y 99,89.

El `GREATEST(..., 0.0)` de `pop_15_64` era justo lo que impedia verlo: en vez de
dar negativo —que habria chillado— ponia la banda central en cero.
"""

from __future__ import annotations

from typing import Any

import pytest

from pipelines.p0_exposure.build import assemble_exposure, validate_age_bands


@pytest.fixture
def con() -> Any:
    from pipelines.p0_exposure.build import ensure_layer_tables
    from pipelines.p2_impact.exposure_join import connect

    con = connect()
    con.execute(
        "CREATE OR REPLACE TABLE crosswalk_h3_adm AS SELECT 1::UBIGINT AS h3_08, '05001' AS adm2_id"
    )
    con.execute(
        "CREATE OR REPLACE TABLE admin_lookup AS SELECT '05001' AS adm2_id, '05' AS adm1_id"
    )
    ensure_layer_tables(con)
    return con


def _celda(con: Any, *, ghs: float, wp_total: float, wp_0_14: float, wp_65p: float) -> Any:
    con.execute(f"INSERT INTO pop_h3 (h3_08, pop_total) VALUES (1::UBIGINT, {ghs})")
    con.execute(f"INSERT INTO pop_alt_h3 (h3_08, pop_alt_worldpop) VALUES (1::UBIGINT, {wp_total})")
    con.execute(f"INSERT INTO pop_0_14_h3 (h3_08, pop_0_14) VALUES (1::UBIGINT, {wp_0_14})")
    con.execute(f"INSERT INTO pop_65p_h3 (h3_08, pop_65p) VALUES (1::UBIGINT, {wp_65p})")
    assemble_exposure(con, iso3="COL", manifest_id="test")
    return con.execute("SELECT pop_total, pop_0_14, pop_15_64, pop_65p FROM exposure_h3").fetchone()


@pytest.mark.geo
def test_las_bandas_son_la_cuota_de_worldpop_sobre_el_total_de_ghs(con: Any) -> None:
    """WorldPop pone la forma del reparto; GHS-POP, la magnitud."""
    total, b0_14, b15_64, b65p = _celda(con, ghs=100.0, wp_total=200.0, wp_0_14=60.0, wp_65p=40.0)
    assert total == pytest.approx(100.0)
    # Cuotas 30 % y 20 % aplicadas a los 100 de GHS-POP, no los 60 y 40 crudos.
    assert b0_14 == pytest.approx(30.0)
    assert b65p == pytest.approx(20.0)
    assert b15_64 == pytest.approx(50.0)


@pytest.mark.geo
def test_las_tres_bandas_suman_el_total(con: Any) -> None:
    total, b0_14, b15_64, b65p = _celda(con, ghs=1234.5, wp_total=987.6, wp_0_14=300.0, wp_65p=90.0)
    assert b0_14 + b15_64 + b65p == pytest.approx(total)


@pytest.mark.geo
def test_el_caso_de_mistrato_ya_no_puede_ocurrir(con: Any) -> None:
    """La celda real que publico 27,80 habitantes y 99,89 mayores de 65.

    WorldPop pone mucha mas gente que GHS-POP en esa celda. Con el reescalado
    eso deja de ser una cifra imposible y pasa a ser lo que de verdad dice el
    dato: una cuota etaria alta sobre una poblacion pequenia.
    """
    total, _, _, b65p = _celda(con, ghs=27.80, wp_total=110.0, wp_0_14=5.0, wp_65p=99.89)
    assert b65p <= total, "sigue publicando mas mayores de 65 que habitantes"
    assert b65p == pytest.approx(27.80 * 99.89 / 110.0)


@pytest.mark.geo
def test_sin_poblacion_de_worldpop_las_bandas_son_cero_y_no_revientan(con: Any) -> None:
    """El denominador puede ser cero y una division por cero tumbaria el build."""
    total, b0_14, b15_64, b65p = _celda(con, ghs=50.0, wp_total=0.0, wp_0_14=0.0, wp_65p=0.0)
    assert (b0_14, b65p) == (0.0, 0.0)
    assert b15_64 == pytest.approx(total)


# --- El assert que lo detiene ----------------------------------------------


def _activo(con: Any, filas: list[tuple[float, float, float, float]]) -> None:
    valores = ", ".join(f"({t}, {a}, {b}, {c})" for t, a, b, c in filas)
    con.execute(
        "CREATE OR REPLACE TABLE exposure_h3 AS SELECT * FROM (VALUES "
        f"{valores}) AS t(pop_total, pop_0_14, pop_15_64, pop_65p)"
    )


@pytest.mark.geo
def test_un_activo_coherente_pasa(con: Any) -> None:
    _activo(con, [(100.0, 30.0, 50.0, 20.0), (0.0, 0.0, 0.0, 0.0)])
    assert validate_age_bands(con) == []


@pytest.mark.geo
def test_una_banda_por_encima_del_total_detiene_el_build(con: Any) -> None:
    """Exactamente lo que hay hoy en los diecinueve activos publicados."""
    _activo(con, [(27.8, 5.0, 0.0, 99.89)])
    problemas = validate_age_bands(con)
    assert problemas and "por encima del total" in problemas[0]


@pytest.mark.geo
def test_unas_bandas_que_no_suman_detienen_el_build(con: Any) -> None:
    """El caso que el `GREATEST(..., 0.0)` escondia poniendo la central en cero."""
    _activo(con, [(100.0, 60.0, 0.0, 40.0), (100.0, 80.0, 0.0, 70.0)])
    problemas = validate_age_bands(con)
    assert any("no reconstruyen pop_total" in p for p in problemas)


def test_el_assert_esta_conectado_al_build() -> None:
    """Un assert que nadie invoca no es un assert.

    Se comprueba contra la lista que `build_country` recorre de verdad, no
    contra su codigo fuente: un guardia de `inspect.getsource` pasa igual
    aunque la funcion no llegue a ejecutarse nunca.
    """
    from pipelines.p0_exposure.build import ASSERTS_DEL_ACTIVO

    assert validate_age_bands in ASSERTS_DEL_ACTIVO
