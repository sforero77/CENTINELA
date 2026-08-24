"""Cuanta poblacion entra por el rescate de celdas fronterizas.

El rescate asigna municipio a las celdas cuyo centro cae fuera de todo poligono
—costa y frontera— pero que tienen poblacion. Es necesario: sin el, esa gente
desaparece del reporte municipal.

Tambien es el sospechoso principal de un sesgo que aparecio al medir los 18
paises de LATAM. Los desvios de GHS-POP frente a la ONU van de -0,80 % (Chile)
a +6,59 % (Paraguay) y se ordenan por cuanta frontera tiene cada pais en
proporcion a su area, no por cuando fue su ultimo censo. Si el rescate esta
reclamando gente del otro lado de la linea, esta cifra lo delata.
"""

from __future__ import annotations

from typing import Any

import pytest

from pipelines.p0_exposure.crosswalk import poblacion_rescatada


@pytest.fixture
def con() -> Any:
    from pipelines.p2_impact.exposure_join import connect

    con = connect()
    con.execute(
        "CREATE TABLE crosswalk_h3_adm (h3_08 UBIGINT, adm2_id VARCHAR, "
        "frac_area DOUBLE, rescatada BOOLEAN)"
    )
    con.execute("CREATE TABLE pop_h3 (h3_08 UBIGINT, pop_total DOUBLE)")
    return con


def _celda(con: Any, h3: int, pop: float, *, rescatada: bool) -> None:
    con.execute(f"INSERT INTO crosswalk_h3_adm VALUES ({h3}::UBIGINT, '05001', 1.0, {rescatada})")
    con.execute(f"INSERT INTO pop_h3 VALUES ({h3}::UBIGINT, {pop})")


@pytest.mark.geo
def test_sin_rescate_la_fraccion_es_cero(con: Any) -> None:
    _celda(con, 1, 1000.0, rescatada=False)
    assert poblacion_rescatada(con, "pop_h3")["pop_rescatada_pct"] == 0.0


@pytest.mark.geo
def test_se_mide_la_gente_y_no_solo_las_celdas(con: Any) -> None:
    """Una celda rescatada puede traer mucha o ninguna poblacion.

    Contar celdas no distingue entre rescatar un islote vacio y reclamar una
    ciudad del pais vecino.
    """
    _celda(con, 1, 9000.0, rescatada=False)
    _celda(con, 2, 1000.0, rescatada=True)
    medida = poblacion_rescatada(con, "pop_h3")
    assert medida["pop_rescatada"] == 1000
    assert medida["pop_total"] == 10000
    assert medida["pop_rescatada_pct"] == 10.0


@pytest.mark.geo
def test_un_pais_sin_datos_no_divide_por_cero(con: Any) -> None:
    assert poblacion_rescatada(con, "pop_h3")["pop_rescatada_pct"] == 0.0


@pytest.mark.geo
def test_sin_tabla_de_poblacion_devuelve_vacio(con: Any) -> None:
    """El rescate corre tambien sobre capas sin `pop_total`; no debe reventar."""
    assert poblacion_rescatada(con, "no_existe") == {}


def test_el_rescate_registra_la_poblacion_no_solo_el_conteo() -> None:
    """Guardia de texto: la medicion no puede desaparecer en un refactor."""
    import inspect

    from pipelines.p0_exposure.crosswalk import rescue_unassigned

    assert "poblacion_rescatada" in inspect.getsource(rescue_unassigned)


# --- Acotar el rescate al mar, no al pais vecino ----------------------------


@pytest.fixture
def escenario() -> Any:
    """Un pais cuadrado, un vecino pegado al este, y mar al oeste."""
    from pipelines.p2_impact.exposure_join import connect

    con = connect()
    con.execute(
        "CREATE TABLE admin_geom AS SELECT '001' AS adm2_id, 'Costa' AS nombre, "
        "'01' AS adm1_id, 'Depto' AS departamento, "
        "ST_GeomFromText('POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))') AS geom"
    )
    con.execute(
        "CREATE TABLE vecinos AS SELECT 'XX' AS iso2, "
        "ST_GeomFromText('POLYGON((1 0, 2 0, 2 1, 1 1, 1 0))') AS geom"
    )
    con.execute(
        "CREATE TABLE crosswalk_h3_adm (h3_08 UBIGINT, adm2_id VARCHAR, "
        "frac_area DOUBLE, rescatada BOOLEAN)"
    )
    con.execute("CREATE TABLE pop_h3 (h3_08 UBIGINT, pop_total DOUBLE)")
    con.execute(
        "CREATE OR REPLACE TEMP TABLE pais AS SELECT ST_Union_Agg(geom) AS geom FROM admin_geom"
    )
    return con


def _sembrar_celda(con: Any, lon: float, lat: float, pop: float) -> int:
    h3 = con.execute(f"SELECT h3_latlng_to_cell({lat}, {lon}, 8)").fetchone()[0]
    con.execute(f"INSERT INTO pop_h3 VALUES ({h3}::UBIGINT, {pop})")
    return int(h3)


@pytest.mark.geo
def test_una_celda_en_el_mar_si_se_rescata(escenario: Any) -> None:
    """Es el caso para el que existe el rescate: costa con poblacion.

    Chile rescata asi el 31 % de su poblacion y su cifra nacional es correcta;
    sin el rescate perderia 6,1 millones de personas.
    """
    from pipelines.p0_exposure.crosswalk import rescue_unassigned

    _sembrar_celda(escenario, -0.005, 0.5, 800.0)  # justo al oeste, en el mar
    rescue_unassigned(escenario, tabla_datos="pop_h3", max_grados=0.02)
    assert escenario.execute("SELECT count(*) FROM crosswalk_h3_adm").fetchone()[0] == 1


@pytest.mark.geo
def test_una_celda_dentro_del_vecino_no_se_rescata(escenario: Any) -> None:
    """El fallo que medimos: Paraguay se llevaba 459.518 personas de sus vecinos.

    Una celda cuyo centro esta en tierra del vecino es del vecino, por cerca que
    este de la linea.
    """
    from pipelines.p0_exposure.crosswalk import rescue_unassigned

    _sembrar_celda(escenario, 1.005, 0.5, 800.0)  # justo al este, dentro de XX
    rescue_unassigned(escenario, tabla_datos="pop_h3", max_grados=0.02)
    assert escenario.execute("SELECT count(*) FROM crosswalk_h3_adm").fetchone()[0] == 0


@pytest.mark.geo
def test_sin_tabla_de_vecinos_el_rescate_sigue_funcionando(escenario: Any) -> None:
    """Overture puede fallar; un build de una hora no puede caerse por eso."""
    from pipelines.p0_exposure.crosswalk import rescue_unassigned

    escenario.execute("DELETE FROM vecinos")
    _sembrar_celda(escenario, -0.005, 0.5, 800.0)
    rescue_unassigned(escenario, tabla_datos="pop_h3", max_grados=0.02)
    assert escenario.execute("SELECT count(*) FROM crosswalk_h3_adm").fetchone()[0] == 1
