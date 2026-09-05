"""El camino degradado de P2, que decia soportarse y no habia funcionado nunca.

`_cargar_admin_lookup` promete en su propio comentario que sin
`admin_lookup.parquet` "el reporte sigue saliendo, con el codigo del municipio
como nombre: es peor de leer, pero mejor que no publicar".

No salia. La rama de respaldo leia `FROM exposure`, que es una vista que
registra `compute_impact` **despues**, asi que moria con:

    Catalog Error: Table with name exposure does not exist!

Y arreglado eso, moria un paso mas alla: el respaldo pone el centroide en cadena
vacia —no lo tiene— y `_enriquecer_con_admin` se lo pasaba a `ST_GeomFromText`,
que eleva `Invalid Input Error: Expected geometry type`.

Dos roturas encadenadas en el unico camino alternativo del modulo. No se
ejercitaba porque el activo publicado como Release trae siempre el diccionario
al lado; se vio el 4-sep-2026 corriendo P2 contra un activo local sin el, al
publicar los backtests de Tarata y Loncopue.

Es el patron de siempre en este repositorio: la pieza escrita, documentada y sin
nadie que la ejecute.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import duckdb
import pytest

from pipelines.p2_impact.exposure_join import connect
from pipelines.p2_impact.run import _cargar_admin_lookup, _enriquecer_con_admin


@pytest.fixture
def activo(tmp_path: Path) -> str:
    """Un activo minimo **sin** `admin_lookup.parquet` al lado."""
    ruta = tmp_path / "exposure_h3.parquet"
    con = duckdb.connect()
    con.execute(
        f"""
        COPY (SELECT 1::BIGINT AS h3_08, 'BOL' AS iso3, 'BO01' AS adm1_id,
                     'BO0101' AS adm2_id, 10.0 AS pop_total
              UNION ALL
              SELECT 2::BIGINT, 'BOL', 'BO01', 'BO0102', 20.0)
        TO '{ruta.as_posix()}' (FORMAT PARQUET)
        """
    )
    return ruta.as_posix()


def _con() -> Any:
    """La misma conexion que usa P2: `ST_GeomFromText` vive en la extension
    espacial, y una prueba con `duckdb.connect()` a secas comprobaria un entorno
    que el pipeline no tiene."""
    return connect()


def test_sin_diccionario_el_respaldo_se_construye(activo: str) -> None:
    """Leyendo el parquet, no una vista que todavia no existe.

    El orden real de P2 es este: `_cargar_admin_lookup` corre **antes** de que
    `compute_impact` registre `exposure`. Por eso la prueba no la registra: si
    volviera a depender de ella, aqui fallaria igual que en produccion.
    """
    con = _con()

    _cargar_admin_lookup(con, activo, None)

    filas = con.execute("SELECT adm2_id, nombre FROM admin_lookup ORDER BY 1").fetchall()
    assert filas == [("BO0101", "BO0101"), ("BO0102", "BO0102")]


def test_el_respaldo_usa_el_codigo_como_nombre(activo: str) -> None:
    """Es lo que el comentario promete y lo que el CSV acaba enseñando."""
    con = _con()

    _cargar_admin_lookup(con, activo, None)

    nombres = {r[0] for r in con.execute("SELECT nombre FROM admin_lookup").fetchall()}
    assert nombres == {"BO0101", "BO0102"}


def test_un_municipio_sin_centroide_no_tumba_el_reporte(activo: str) -> None:
    """`ST_GeomFromText('')` eleva, y una sola fila asi mataba el evento entero."""
    con = _con()
    _cargar_admin_lookup(con, activo, None)

    filas = _enriquecer_con_admin(con, [{"adm2_id": "BO0101", "pop_mmi7p": 0.0}])

    assert filas[0]["nombre"] == "BO0101"
    # Sin coordenadas, no en (0, 0) inventado: `static_map._coordenada` descarta
    # el municipio sin ellas en vez de dibujarlo en el golfo de Guinea.
    assert filas[0]["lon"] == 0.0
    assert filas[0]["lat"] == 0.0


def test_con_diccionario_el_centroide_si_viaja(tmp_path: Path, activo: str) -> None:
    """El camino normal no se toca: quien tiene centroide lo conserva."""
    lookup = tmp_path / "admin_lookup.parquet"
    con = _con()
    con.execute(
        f"""
        COPY (SELECT 'BO0101' AS adm2_id, 'Tarata' AS nombre, 'BO01' AS adm1_id,
                     'Cochabamba' AS departamento, 'BOL' AS iso3,
                     'POINT (-66.02 -17.61)' AS centroide)
        TO '{lookup.as_posix()}' (FORMAT PARQUET)
        """
    )

    _cargar_admin_lookup(con, activo, str(lookup))
    filas = _enriquecer_con_admin(con, [{"adm2_id": "BO0101"}])

    assert filas[0]["nombre"] == "Tarata"
    assert (filas[0]["lon"], filas[0]["lat"]) == (-66.02, -17.61)
