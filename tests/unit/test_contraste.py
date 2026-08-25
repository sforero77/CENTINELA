"""Contraste del activo contra una evaluacion de dano externa (Fase 2).

Exposicion no es dano. Este modulo existe para poder ensenar la diferencia con
cifras del mismo evento en vez de explicarla con palabras.
"""

from __future__ import annotations

from typing import Any

import pytest

from pipelines.p2_impact.contraste import Contraste, contrastar


def _resultado(**kw: Any) -> Contraste:
    base: dict[str, Any] = {
        "etiqueta": "prueba",
        "celdas": 74,
        "celdas_sin_activo": 0,
        "evaluadas": 26_143,
        "danadas": 965,
        "bld_activo": 35_611.0,
        "pop_activo": 166_988.6,
    }
    return Contraste(**(base | kw))


def test_la_fraccion_danada_es_lo_que_distingue_dano_de_exposicion() -> None:
    """Medido en La Guaira: 3,69 % de lo evaluado, no el 100 % de lo expuesto."""
    assert _resultado().fraccion_danada_pct == pytest.approx(3.691, abs=0.001)


def test_sin_edificaciones_evaluadas_no_divide_por_cero() -> None:
    vacio = _resultado(evaluadas=0, danadas=0, bld_activo=0.0)
    assert vacio.fraccion_danada_pct == 0.0
    assert vacio.razon_conteo == 0.0


def test_la_razon_de_conteo_no_tiene_por_que_ser_uno() -> None:
    """La evaluacion externa se recorta a su mascara de area valida.

    Una celda r8 puede quedar medio dentro, asi que el activo cuenta mas. Sirve
    para detectar un orden de magnitud raro, no para calibrar.
    """
    assert _resultado().razon_conteo == pytest.approx(1.362, abs=0.001)


@pytest.mark.geo
def test_el_orden_de_ejes_no_manda_las_celdas_al_oceano() -> None:
    """Guardia del fallo real: EPSG:4326 declara los ejes en orden lat-lon.

    `ST_Transform` lo respeta, asi que sin `always_xy` las coordenadas salen
    invertidas, la celda calculada no existe en ningun sitio y el join devuelve
    cero filas — que se lee igual que un "no hay solape" legitimo.
    """
    from pipelines.p2_impact.exposure_join import connect

    con = connect()
    con.execute(
        "CREATE TABLE p AS SELECT ST_Transform("
        "ST_Point(721000, 1170000), 'EPSG:32619', 'EPSG:4326', always_xy := true) AS g"
    )
    lon, lat = con.execute("SELECT ST_X(g), ST_Y(g) FROM p").fetchone()
    # La Guaira: lon cerca de -67, lat cerca de 10,6. Invertido daria lo contrario.
    assert -70 < lon < -64, f"longitud fuera de rango: {lon}"
    assert 8 < lat < 13, f"latitud fuera de rango: {lat}"


@pytest.mark.geo
def test_una_celda_evaluada_que_el_activo_no_tiene_se_cuenta(tmp_path: Any) -> None:
    """Es un hueco de cobertura del activo, no un matiz: sale por separado."""
    from pipelines.p2_impact.exposure_join import connect

    con = connect()
    # Activo con una sola celda.
    con.execute(
        "CREATE TABLE exposure AS SELECT h3_latlng_to_cell(10.6, -66.9, 8) AS h3_08, "
        "100.0 AS bld_count, 500.0 AS pop_total"
    )
    con.execute(
        "CREATE TABLE celdas_evaluadas AS "
        "SELECT h3_latlng_to_cell(10.6, -66.9, 8) AS h3_08, 10 AS evaluadas, 1::BIGINT AS danadas "
        "UNION ALL SELECT h3_latlng_to_cell(4.6, -74.1, 8), 7, 2::BIGINT"
    )
    huerfanas = con.execute(
        "SELECT count(*) FROM celdas_evaluadas c LEFT JOIN exposure e USING (h3_08) "
        "WHERE e.h3_08 IS NULL"
    ).fetchone()[0]
    assert huerfanas == 1


def test_contrastar_es_importable_sin_red() -> None:
    """El import no puede arrastrar httpfs ni GDAL: P2 corre en el camino critico."""
    assert callable(contrastar)


def test_una_url_normal_se_convierte_en_ruta_gdal() -> None:
    """Pedir el `/vsicurl/` escrito a mano resulto una trampa.

    Una ruta que empieza por barra la convierte Git Bash a ruta de Windows antes
    de que salga de la maquina, asi que el workflow recibio
    "C:/Program Files/Git/vsicurl/https;//..." y fallo. Con la URL a secas no
    hay nada que convertir.
    """
    from pipelines.p2_impact.contraste import VSI_HTTP, ruta_gdal

    assert ruta_gdal("https://x/y.gpkg") == f"{VSI_HTTP}https://x/y.gpkg"
    assert ruta_gdal("http://x/y.gpkg") == f"{VSI_HTTP}http://x/y.gpkg"


def test_no_se_duplica_el_prefijo_ni_se_toca_una_ruta_local() -> None:
    from pipelines.p2_impact.contraste import ruta_gdal

    assert ruta_gdal("/vsicurl/https://x/y.gpkg") == "/vsicurl/https://x/y.gpkg"
    assert ruta_gdal("/datos/local.gpkg") == "/datos/local.gpkg"
    assert ruta_gdal("C:/datos/local.gpkg") == "C:/datos/local.gpkg"
