"""Las funciones geodesicas de DuckDB leen (lat, lon) y el sistema trabaja en (lon, lat).

El fallo que estas pruebas fijan estuvo publicado: `ST_Area_Spheroid` y
`ST_Length_Spheroid` recibian la geometria de Overture tal cual, en (lon, lat),
y devolvian un area escalada por cos(longitud) —o NaN donde |longitud| > 90—.
No se cayo nada. Mexico publicaba `bld_area_m2` NaN en el 96,1 % de sus celdas
con edificacion y 3,4 km de via en las 842.796 celdas donde viven 126,3
millones de personas, porque el guardia `isfinite` de las vias, puesto para que
un NaN no envenenara la suma del pais, descartaba en silencio el pais entero.

Aqui se comprueban las dos mitades: que DuckDB sigue leyendo (lat, lon) —si
algun dia lo cambia, esto falla y el `ST_FlipCoordinates` sobra— y que nadie
vuelve a nombrar a esas funciones fuera del unico modulo que las traduce.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import pytest

from pipelines.common.geo import area_spheroid_m2, length_spheroid_m

#: Un cuadrado de 0,001° junto al meridiano -75 y el paralelo 5 (Colombia).
CUADRADO = "POLYGON((-75 5, -74.999 5, -74.999 5.001, -75 5.001, -75 5))"
#: Un tramo de 0,001° de longitud a la altura de Ciudad de Mexico (-99, 19).
TRAMO = "LINESTRING(-99 19, -98.999 19)"
#: Un cuadrado al oeste del meridiano -90, donde el fallo daba NaN.
CUADRADO_OESTE = "POLYGON((-100 20, -99.999 20, -99.999 20.001, -100 20.001, -100 20))"

#: Grados de latitud en metros, WGS84, suficiente para comparar con holgura.
METROS_POR_GRADO = 111_320.0


def _con() -> Any:
    """La misma conexion que usa P2, para medir contra la libreria de verdad."""
    from pipelines.p2_impact.exposure_join import connect

    return connect()


@pytest.mark.geo
def test_duckdb_sigue_leyendo_lat_lon() -> None:
    """La premisa del arreglo. Si esto falla, el flip sobra y hay que quitarlo."""
    con = _con()
    directo = con.execute(f"SELECT ST_Area_Spheroid(ST_GeomFromText('{CUADRADO}'))").fetchone()[0]
    # Leyendo (lat, lon) el cuadrado se cree a latitud -75, no 5.
    esperado_al_reves = (METROS_POR_GRADO * 0.001) ** 2 * math.cos(math.radians(75))
    assert directo == pytest.approx(esperado_al_reves, rel=0.02)


@pytest.mark.geo
def test_el_area_con_flip_es_la_del_paralelo_correcto() -> None:
    con = _con()
    geom = f"ST_GeomFromText('{CUADRADO}')"
    area = con.execute(f"SELECT {area_spheroid_m2(geom)}").fetchone()[0]
    esperado = (METROS_POR_GRADO * 0.001) ** 2 * math.cos(math.radians(5))
    assert area == pytest.approx(esperado, rel=0.02)


@pytest.mark.geo
def test_la_longitud_con_flip_es_la_del_paralelo_correcto() -> None:
    con = _con()
    geom = f"ST_GeomFromText('{TRAMO}')"
    metros = con.execute(f"SELECT {length_spheroid_m(geom)}").fetchone()[0]
    esperado = METROS_POR_GRADO * 0.001 * math.cos(math.radians(19))
    assert metros == pytest.approx(esperado, rel=0.02)


@pytest.mark.geo
def test_al_oeste_del_meridiano_90_ya_no_sale_nan() -> None:
    """El caso que borro a Mexico del mapa de vias."""
    con = _con()
    crudo = con.execute(f"SELECT ST_Area_Spheroid(ST_GeomFromText('{CUADRADO_OESTE}'))").fetchone()[
        0
    ]
    assert math.isnan(crudo), "sin flip, |lon| > 90 daba NaN; si ya no, revisar el arreglo"

    geom = f"ST_GeomFromText('{CUADRADO_OESTE}')"
    area = con.execute(f"SELECT {area_spheroid_m2(geom)}").fetchone()[0]
    assert math.isfinite(area)
    esperado = (METROS_POR_GRADO * 0.001) ** 2 * math.cos(math.radians(20))
    assert area == pytest.approx(esperado, rel=0.02)


def test_nadie_llama_al_esferoide_por_su_nombre() -> None:
    """`geo.py` es el unico sitio donde se nombra a `ST_*_Spheroid`.

    Sin este guardia el arreglo dura hasta el siguiente que escriba la consulta
    obvia: la version sin flip compila, corre y devuelve numeros.
    """
    raiz = Path(__file__).resolve().parents[2] / "pipelines"
    permitido = raiz / "common" / "geo.py"
    culpables = [
        f"{ruta.relative_to(raiz.parent)}:{n}"
        for ruta in raiz.rglob("*.py")
        if ruta != permitido
        for n, linea in enumerate(ruta.read_text(encoding="utf-8").splitlines(), 1)
        # El parentesis distingue la llamada de la prosa: el comentario de
        # `constants.py` y el metadato publicado de `layers.py` nombran a las
        # funciones a proposito, y nombrarlas no es llamarlas.
        if "ST_Area_Spheroid(" in linea or "ST_Length_Spheroid(" in linea
    ]
    assert not culpables, (
        "llaman a la funcion geodesica sin traducir el orden de coordenadas; "
        f"usar geo.area_spheroid_m2 / geo.length_spheroid_m: {culpables}"
    )
