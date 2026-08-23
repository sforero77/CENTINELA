"""Agregacion de capas vectoriales a H3."""

from __future__ import annotations

from pipelines.p0_exposure.vector_h3 import (
    LINE_STEP_KM,
    MAX_POINTS_PER_LINE,
    ROAD_CLASSES,
    road_class_expression,
)


def test_las_clases_de_via_cubren_las_tres_columnas() -> None:
    expr = road_class_expression()
    assert "'primary'" in expr and "'secondary'" in expr and "'other'" in expr


def test_motorway_y_trunk_cuentan_como_primarias() -> None:
    """Overture separa motorway/trunk/primary; el reporte los junta."""
    assert set(ROAD_CLASSES["primary"]) == {"motorway", "trunk", "primary"}
    expr = road_class_expression()
    assert "'motorway'" in expr and "'trunk'" in expr


def test_el_paso_es_menor_que_una_celda_r8() -> None:
    """Condicion para que ninguna celda atravesada se pierda.

    Una celda r8 mide ~1,06 km de ancho; con pasos de 200 m ningun tramo puede
    saltarse una celda entera.
    """
    ancho_celda_r8_km = 1.063
    assert ancho_celda_r8_km / 2 > LINE_STEP_KM


def test_hay_tope_de_puntos_por_via() -> None:
    """Sin tope, unas pocas troncales dominarian el coste del build entero."""
    assert 100 < MAX_POINTS_PER_LINE <= 10_000


def test_la_expresion_acepta_otra_columna() -> None:
    assert "highway" in road_class_expression("highway")
