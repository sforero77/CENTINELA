"""Agregacion de capas vectoriales a H3."""

from __future__ import annotations

import pytest

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


# --- Donde cae la masa de cada subtramo ------------------------------------


@pytest.mark.geo
def test_la_masa_de_un_subtramo_cae_en_su_centro_y_no_en_su_final() -> None:
    """EL SESGO QUE CIERRA.

    Con `fraction = 1/n` y `repeat = true`, DuckDB devuelve las fracciones
    1/n, 2/n ... 1,0: el **final** de cada subtramo, nunca el principio. Cada
    trozo aportaba su masa a la celda de su punto final, con un sesgo de medio
    subtramo siempre en la direccion del trazado. No se compensa entre vias
    porque no es aleatorio.

    Se comprueba con dos subtramos sobre una linea larga: los puntos tienen que
    caer en las celdas del 25 % y el 75 % del recorrido, no en las del 50 % y
    el 100 %.
    """
    from pipelines.p0_exposure.vector_h3 import aggregate_lines_to_h3
    from pipelines.p2_impact.exposure_join import connect

    con = connect()
    # De -75,00 a -74,90 en el paralelo 4: unos 11,1 km. Con `paso_km` mayor que
    # la mitad, `n_puntos` cae al minimo de 2.
    con.execute(
        "CREATE TABLE vias AS SELECT "
        "ST_GeomFromText('LINESTRING(-75.00 4.00, -74.90 4.00)') AS geometry, "
        "'primary' AS clase"
    )
    aggregate_lines_to_h3(con, "SELECT geometry, clase FROM vias", tabla="roads_h3", paso_km=100.0)

    centros = {
        r[0]
        for r in con.execute(
            "SELECT h3_latlng_to_cell(4.00, -74.975, 8) UNION "
            "SELECT h3_latlng_to_cell(4.00, -74.925, 8)"
        ).fetchall()
    }
    extremos = {
        r[0]
        for r in con.execute(
            "SELECT h3_latlng_to_cell(4.00, -74.950, 8) UNION "
            "SELECT h3_latlng_to_cell(4.00, -74.900, 8)"
        ).fetchall()
    }
    con_masa = {
        r[0] for r in con.execute("SELECT h3_08 FROM roads_h3 WHERE road_km_primary > 0").fetchall()
    }

    assert con_masa == centros, (
        "el muestreo no cae en el centro de cada subtramo; celdas con masa: "
        f"{sorted(con_masa)}, esperadas {sorted(centros)}"
    )
    assert not (con_masa & extremos), "sigue cayendo en el final de cada subtramo"


@pytest.mark.geo
def test_el_reparto_conserva_la_longitud_total() -> None:
    """`sum(km/n)` es `km` solo si vuelven exactamente n puntos.

    Ningun assert lo comprobaba, y la correccion del sesgo pide el doble de
    puntos y descarta la mitad — justo el cambio que podria romperlo.
    """
    from pipelines.p0_exposure.vector_h3 import aggregate_lines_to_h3
    from pipelines.p2_impact.exposure_join import connect

    con = connect()
    con.execute(
        "CREATE TABLE vias AS SELECT "
        "ST_GeomFromText('LINESTRING(-75.00 4.00, -74.90 4.00)') AS geometry, "
        "'primary' AS clase"
    )
    esperado: float = con.execute(
        "SELECT ST_Length_Spheroid(geometry) / 1000.0 FROM vias"
    ).fetchone()[0]

    resumen = aggregate_lines_to_h3(
        con, "SELECT geometry, clase FROM vias", tabla="roads_h3", paso_km=0.2
    )

    assert resumen.total == pytest.approx(esperado, rel=1e-9)
