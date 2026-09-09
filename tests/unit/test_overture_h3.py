"""Lectura remota de Overture y su traduccion a celdas H3.

Las consultas se revisan como texto: armarlas mal no falla, devuelve una cifra
plausible y equivocada. Es el mismo riesgo que documenta ``sources/overture.py``
para el emparejamiento del catalogo.
"""

from __future__ import annotations

import pytest

from pipelines.common.geo import BBox
from pipelines.p0_exposure.overture_h3 import ROAD_SUBTYPE, roads_source_query

COLOMBIA = BBox(lon_min=-82.0, lat_min=-4.3, lon_max=-66.8, lat_max=13.5)
URLS = ["https://ejemplo/part-00013.parquet", "https://ejemplo/part-00014.parquet"]


def test_las_vias_se_filtran_por_subtipo() -> None:
    """`transportation` tambien publica rail y water: sumarlos inflaria los km."""
    assert f"subtype = '{ROAD_SUBTYPE}'" in roads_source_query(URLS, COLOMBIA)
    assert ROAD_SUBTYPE == "road"


def test_la_consulta_poda_por_la_columna_bbox() -> None:
    """Sin la poda, DuckDB descomprimiria los ficheros enteros."""
    sql = roads_source_query(URLS, COLOMBIA)
    assert "bbox.xmin BETWEEN -82.0 AND -66.8" in sql
    assert "bbox.ymin BETWEEN -4.3 AND 13.5" in sql


def test_la_consulta_no_envuelve_la_geometria_en_st_geomfromwkb() -> None:
    """Contrato medido: Overture entrega GEOMETRY, no BLOB.

    La receta publicada usa ``ST_GeomFromWKB(geometry)`` y aqui falla con "no
    function matches". Es el tipo de error que solo aparece con red, asi que se
    fija como prueba de texto.
    """
    assert "ST_GeomFromWKB" not in roads_source_query(URLS, COLOMBIA)


def test_entran_todos_los_ficheros_seleccionados() -> None:
    sql = roads_source_query(URLS, COLOMBIA)
    assert all(url in sql for url in URLS)


def test_la_consulta_expone_las_columnas_que_espera_el_agregador() -> None:
    """``aggregate_lines_to_h3`` lee ``geometry`` y ``clase``."""
    sql = roads_source_query(URLS, COLOMBIA)
    assert "geometry" in sql and "AS clase" in sql


def test_las_vias_se_procesan_fichero_a_fichero() -> None:
    """Overture particiona filas, no geometrias.

    Cada segmento vive entero en un fichero, asi que trocear el trabajo da el
    mismo resultado y evita que un corte de red tire el pais. La consulta que
    consume el agregador lleva **un** fichero, no los once.
    """
    sql = roads_source_query(URLS[:1], COLOMBIA)
    assert URLS[0] in sql
    assert URLS[1] not in sql


@pytest.mark.geo
def test_los_plazos_de_red_aguantan_una_conexion_lenta() -> None:
    """El default de 30 s de DuckDB mato un build tras una hora de descargas.

    Un fichero de Overture, ya podado por `bbox`, tarda minutos en una conexion
    domestica: medido, el primero de Colombia tardo 3 min 47 s. El fallo llega
    ademas en el peor momento posible — al final, con todo lo caro ya hecho.
    """
    from pipelines.p0_exposure.overture_h3 import HTTPFS_SETTINGS, ensure_httpfs
    from pipelines.p2_impact.exposure_join import connect

    con = connect()
    ensure_httpfs(con)
    for ajuste in HTTPFS_SETTINGS:
        valor = con.execute(
            f"SELECT value FROM duckdb_settings() WHERE name = '{ajuste}'"
        ).fetchone()
        assert valor is not None, f"{ajuste} no existe en esta version de DuckDB"

    timeout_ms = int(
        con.execute("SELECT value FROM duckdb_settings() WHERE name = 'http_timeout'").fetchone()[0]
    )
    assert timeout_ms >= 300_000, "menos de cinco minutos no cubre un fichero real"
