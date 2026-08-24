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

from pipelines.p0_exposure.crosswalk import _poblacion_rescatada


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
    assert _poblacion_rescatada(con, "pop_h3")["pop_rescatada_pct"] == 0.0


@pytest.mark.geo
def test_se_mide_la_gente_y_no_solo_las_celdas(con: Any) -> None:
    """Una celda rescatada puede traer mucha o ninguna poblacion.

    Contar celdas no distingue entre rescatar un islote vacio y reclamar una
    ciudad del pais vecino.
    """
    _celda(con, 1, 9000.0, rescatada=False)
    _celda(con, 2, 1000.0, rescatada=True)
    medida = _poblacion_rescatada(con, "pop_h3")
    assert medida["pop_rescatada"] == 1000
    assert medida["pop_total"] == 10000
    assert medida["pop_rescatada_pct"] == 10.0


@pytest.mark.geo
def test_un_pais_sin_datos_no_divide_por_cero(con: Any) -> None:
    assert _poblacion_rescatada(con, "pop_h3")["pop_rescatada_pct"] == 0.0


@pytest.mark.geo
def test_sin_tabla_de_poblacion_devuelve_vacio(con: Any) -> None:
    """El rescate corre tambien sobre capas sin `pop_total`; no debe reventar."""
    assert _poblacion_rescatada(con, "no_existe") == {}


def test_el_rescate_registra_la_poblacion_no_solo_el_conteo() -> None:
    """Guardia de texto: la medicion no puede desaparecer en un refactor."""
    import inspect

    from pipelines.p0_exposure.crosswalk import rescue_unassigned

    assert "_poblacion_rescatada" in inspect.getsource(rescue_unassigned)
