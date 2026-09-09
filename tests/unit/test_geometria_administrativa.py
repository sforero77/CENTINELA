"""Dos formas en que un COD-AB republicado tumba el build de un pais entero.

Las dos aparecieron en Argentina el 27-ago-2026, en el mismo fichero, y las dos
son de la clase que este proyecto persigue: no las provoca un cambio de codigo
sino un cambio en el dato de un tercero, y ninguna avisa hasta que revienta.

Argentina construyo bien el 24-ago. El mismo dataset, republicado, la dejo fuera
del sistema.
"""

from __future__ import annotations

from typing import Any

import pytest

pytestmark = pytest.mark.geo


@pytest.fixture
def con() -> Any:
    from pipelines.p2_impact.exposure_join import connect

    return connect()


def _admin(con: Any, filas: list[tuple[str, str]]) -> None:
    """`admin_geom` con las columnas que el crosswalk necesita."""
    con.execute(
        "CREATE OR REPLACE TABLE admin_geom "
        "(adm2_id VARCHAR, nombre VARCHAR, adm1_id VARCHAR, departamento VARCHAR, geom GEOMETRY)"
    )
    for adm2_id, wkt in filas:
        con.execute(
            "INSERT INTO admin_geom VALUES (?, ?, '01', 'x', ST_GeomFromText(?))",
            [adm2_id, adm2_id, wkt],
        )


# --- La Z que nadie declara -------------------------------------------------


def test_una_z_a_cero_no_puede_tumbar_el_polyfill(con: Any) -> None:
    """El COD-AB de Argentina se republico con coordenada Z, y vale cero.

    Eso cambia el codigo de tipo del WKB de 3 a 1003, y
    `h3_polygon_wkb_to_cells` responde "Invalid WKB: expected polygon at 5" —
    que es exactamente el byte donde vive ese codigo.
    """
    from pipelines.p0_exposure.crosswalk import SQL_POLYFILL_TESELA

    assert "ST_Force2D" in SQL_POLYFILL_TESELA, "una Z de terceros vuelve a tumbar el build"


def test_el_filtro_de_tipo_no_puede_ver_la_z(con: Any) -> None:
    """Lo que hace el fallo dificil de encontrar.

    `ST_GeometryType` devuelve `POLYGON` tanto para el tipo 3 como para el 1003:
    borra la dimension al contestar. El `WHERE` del polyfill parece cubrir el
    caso y no lo cubre — por eso el arreglo tiene que ser `ST_Force2D` y no un
    filtro mas.
    """
    tipo = con.execute(
        "SELECT ST_GeometryType(ST_GeomFromText('POLYGON Z ((0 0 0, 1 0 0, 1 1 0, 0 0 0))'))"
    ).fetchone()[0]

    assert tipo == "POLYGON", "si esto cambia, el filtro de tipo ya bastaria"


# --- La unidad que se traga a otra ------------------------------------------


def test_una_unidad_que_contiene_a_otra_le_devuelve_su_territorio(con: Any) -> None:
    """Las unidades adm2 **parten** el territorio: no se anidan.

    El COD-AB republicado dibujo Itati englobando entero a San Luis del Palmar,
    que son departamentos vecinos de Corrientes. Sin recortar, 4.197 celdas
    quedaban reclamadas por dos municipios y el guardia de doble conteo —con
    razon— tumbaba el build.
    """
    from pipelines.p0_exposure.crosswalk import recortar_contenidos

    _admin(
        con,
        [
            ("grande", "POLYGON ((0 0, 10 0, 10 10, 0 10, 0 0))"),
            ("dentro", "POLYGON ((2 2, 4 2, 4 4, 2 4, 2 2))"),
        ],
    )

    assert recortar_contenidos(con) == 1

    solape = con.execute(
        "SELECT ST_Area(ST_Intersection(a.geom, b.geom)) FROM admin_geom a, admin_geom b "
        "WHERE a.adm2_id = 'grande' AND b.adm2_id = 'dentro'"
    ).fetchone()[0]
    assert solape == pytest.approx(0.0, abs=1e-9)


def test_el_contenido_conserva_su_territorio_entero(con: Any) -> None:
    """Se resta al continente, no al contenido.

    Al reves seria peor que el bug: borraria del mapa a la unidad pequena, y su
    poblacion se sumaria a la grande sin que nada protestara.
    """
    from pipelines.p0_exposure.crosswalk import recortar_contenidos

    _admin(
        con,
        [
            ("grande", "POLYGON ((0 0, 10 0, 10 10, 0 10, 0 0))"),
            ("dentro", "POLYGON ((2 2, 4 2, 4 4, 2 4, 2 2))"),
        ],
    )
    recortar_contenidos(con)

    area = con.execute("SELECT ST_Area(geom) FROM admin_geom WHERE adm2_id = 'dentro'").fetchone()[
        0
    ]
    assert area == pytest.approx(4.0)


def test_un_enclave_legitimo_se_trata_igual_y_esta_bien(con: Any) -> None:
    """No hace falta distinguir el error del enclave.

    Si una unidad rodea de verdad a otra —pasa—, el territorio de la rodeada
    sigue siendo suyo. La respuesta correcta es la misma en los dos casos, y por
    eso `ST_Difference` no inventa geometria: aplica la definicion de particion.
    """
    from pipelines.p0_exposure.crosswalk import recortar_contenidos

    _admin(
        con,
        [
            ("rodea", "POLYGON ((0 0, 10 0, 10 10, 0 10, 0 0))"),
            ("enclave", "POLYGON ((4 4, 6 4, 6 6, 4 6, 4 4))"),
        ],
    )
    recortar_contenidos(con)

    total = con.execute("SELECT round(sum(ST_Area(geom)), 6) FROM admin_geom").fetchone()[0]
    assert total == pytest.approx(100.0), "el pais no cambia de tamano al repartirlo bien"


def test_un_dato_sano_no_se_toca(con: Any) -> None:
    """Dieciocho de diecinueve paises pasan por aqui sin que nada cambie."""
    from pipelines.p0_exposure.crosswalk import recortar_contenidos

    _admin(
        con,
        [
            ("a", "POLYGON ((0 0, 5 0, 5 5, 0 5, 0 0))"),
            ("b", "POLYGON ((5 0, 10 0, 10 5, 5 5, 5 0))"),
        ],
    )

    assert recortar_contenidos(con) == 0
