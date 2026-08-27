"""La reticula de ESA WorldCover y la agregacion categorica a H3.

Dos piezas nuevas y una idea que no existia en el activo: hasta ahora todas las
capas eran **sumas** de magnitudes continuas —personas, metros, kilometros—. La
cobertura del suelo es categorica, y sumar codigos de clase produce numeros
creibles y sin sentido: una celda mitad arbolado (10) y mitad cultivo (40)
daria 25, que es el codigo de nada.

Lo que estas pruebas protegen es justo eso: que nadie vuelva a tratarla como una
suma, y que la rejilla no desplace medio pais a la tesela vecina.
"""

from __future__ import annotations

from typing import Any

import pytest

from pipelines.common.geo import BBox
from pipelines.p0_exposure.sources import worldcover as wc

# --- La rejilla -------------------------------------------------------------


def test_el_nombre_de_la_tesela_es_el_del_bucket() -> None:
    """Verificado contra el bucket real: `N03W075` responde 200."""
    assert wc.Tile(lat=3, lon=-75).name == "N03W075"
    assert wc.Tile(lat=-12, lon=-78).name == "S12W078"
    assert wc.Tile(lat=0, lon=-60).name == "N00W060"


def test_una_longitud_negativa_baja_a_la_tesela_que_la_contiene() -> None:
    """El error que habria desplazado medio pais.

    Truncar hacia cero mandaria `-76,7` a la tesela `W075`, que empieza en -75 y
    no lo contiene. Colombia occidental se leeria del raster vecino y saldrian
    clases de otro sitio — sin fallar, con numeros plausibles.
    """
    teselas = wc.tiles_for_bbox(BBox(lon_min=-76.7, lat_min=5.0, lon_max=-76.6, lat_max=5.1))

    assert [t.name for t in teselas] == ["N03W078"]


def test_la_tesela_contiene_el_punto_que_la_pidio() -> None:
    """La comprobacion que de verdad importa, hecha sobre los limites."""
    lon, lat = -76.7, 5.72
    # `BBox` no admite cajas degeneradas, asi que se pide una minima alrededor.
    caja = BBox(lon_min=lon, lat_min=lat, lon_max=lon + 0.01, lat_max=lat + 0.01)
    tesela = wc.tiles_for_bbox(caja)[0]
    x0, y0, x1, y1 = tesela.bounds

    assert x0 <= lon < x1
    assert y0 <= lat < y1


def test_una_caja_grande_pide_la_malla_entera() -> None:
    teselas = wc.tiles_for_bbox(BBox(lon_min=-76.0, lat_min=4.0, lon_max=-71.0, lat_max=8.0))

    # Tres columnas: -76 cae en W078 y -71 en W072, asi que la de en medio
    # tambien hace falta aunque la caja no empiece ni acabe en ella.
    assert {t.name for t in teselas} == {
        "N03W078",
        "N03W075",
        "N03W072",
        "N06W078",
        "N06W075",
        "N06W072",
    }


def test_no_se_piden_teselas_fuera_de_la_cobertura_del_producto() -> None:
    """El producto llega a 60°S. Chile y Argentina tienen bbox mas al sur.

    Pedir una tesela inexistente no es gratis: es un 404 y varios segundos de
    reintentos de GDAL, multiplicados por cada tesela fantasma de la fila.
    """
    teselas = wc.tiles_for_bbox(BBox(lon_min=-75.0, lat_min=-90.0, lon_max=-72.0, lat_max=-58.0))

    assert all(t.lat >= wc.LAT_MIN for t in teselas)
    assert teselas, "y aun asi debe devolver las que si existen"


def test_la_url_apunta_al_fichero_que_existe() -> None:
    url = wc.Tile(lat=3, lon=-75).url

    assert url.endswith("/v200/2021/map/ESA_WorldCover_10m_2021_v200_N03W075_Map.tif")
    assert url.startswith("https://"), "s3:// lo trataria download_manifest como Overture"


def test_se_lee_en_remoto_y_no_se_descarga() -> None:
    """858 teselas a 96 MB son 82 GB, y un runner de CI tiene ~14 libres."""
    assert wc.Tile(lat=3, lon=-75).vsicurl.startswith("/vsicurl/https://")


# --- Las clases que se publican ---------------------------------------------


def test_humedal_y_manglar_van_a_la_misma_columna() -> None:
    """Los dos son suelo organico y arden igual de mal y de largo.

    Separarlos daria dos columnas casi vacias en dieciocho de los diecinueve
    paises.
    """
    assert wc.AGRUPACION[90] == wc.AGRUPACION[95] == "humedal"


def test_lo_que_no_arde_no_ocupa_una_columna() -> None:
    """Agua, nieve, suelo desnudo y musgo se quedan fuera a proposito.

    Nombrarlas en el contrato publicado para que sean siempre cero es ensanchar
    el parquet sin anadir informacion — y `exposure_h3` se hereda entero en
    `impact_h3`, asi que cada columna se paga dos veces.
    """
    for codigo in (60, 70, 80, 100):
        assert codigo not in wc.AGRUPACION


def test_cada_clase_publicada_tiene_su_grupo() -> None:
    """Que las dos estructuras no se separen: `CLASES` rotula, `AGRUPACION` suma."""
    assert {c.nombre for c in wc.CLASES} == set(wc.AGRUPACION.values())


# --- La agregacion ----------------------------------------------------------


@pytest.fixture
def con() -> Any:
    from pipelines.p2_impact.exposure_join import connect

    return connect()


@pytest.mark.geo
def test_los_conteos_se_suman_entre_teselas_vecinas(con: Any) -> None:
    """Una celda H3 de borde recibe pixeles de dos teselas.

    Sin la consolidacion final aparecerian dos filas para el mismo par (celda,
    clase), y el pivote posterior elegiria una de las dos en silencio.
    """
    import pyarrow as pa

    from pipelines.p0_exposure.raster_categorico_h3 import fracciones_por_celda

    con.execute("CREATE TABLE lulc (h3_08 UBIGINT, clase VARCHAR, pixeles BIGINT)")
    con.register(
        "_x",
        pa.table(
            {
                "h3_08": pa.array([1, 1, 1], pa.uint64()),
                "clase": pa.array(["arbolado", "arbolado", "cultivo"], pa.string()),
                "pixeles": pa.array([60, 20, 20], pa.int64()),
            }
        ),
    )
    con.execute("INSERT INTO lulc SELECT h3_08, clase, sum(pixeles) FROM _x GROUP BY 1, 2")

    filas = fracciones_por_celda(
        con, origen="lulc", destino="lulc_pct", clases=("arbolado", "cultivo")
    )
    fila = con.execute(
        "SELECT lulc_arbolado_pct, lulc_cultivo_pct, lulc_px FROM lulc_pct"
    ).fetchone()

    assert filas == 1
    assert fila == (80.0, 20.0, 100)


@pytest.mark.geo
def test_el_denominador_es_lo_clasificado_y_no_lo_que_cabe(con: Any) -> None:
    """En la costa media celda es mar, y el mar no cuenta.

    Dividir por la capacidad teorica de la celda daria porcentajes que no suman
    nada reconocible, y una celda costera perfectamente medida pareceria vacia.
    """
    import pyarrow as pa

    from pipelines.p0_exposure.raster_categorico_h3 import fracciones_por_celda

    con.execute("CREATE TABLE lulc (h3_08 UBIGINT, clase VARCHAR, pixeles BIGINT)")
    con.register(
        "_x",
        pa.table(
            {
                "h3_08": pa.array([7], pa.uint64()),
                "clase": pa.array(["arbolado"], pa.string()),
                "pixeles": pa.array([9], pa.int64()),
            }
        ),
    )
    con.execute("INSERT INTO lulc SELECT * FROM _x")

    fracciones_por_celda(con, origen="lulc", destino="lulc_pct", clases=("arbolado",))
    fila = con.execute("SELECT lulc_arbolado_pct, lulc_px FROM lulc_pct").fetchone()

    assert fila[0] == 100.0, "nueve pixeles de arbolado son el 100 % de lo medido"
    assert fila[1] == 9, "y `lulc_px` es lo que avisa de que la evidencia es poca"


@pytest.mark.geo
def test_nadie_puede_sumar_codigos_de_clase() -> None:
    """El error que esta funcion existe para evitar.

    Si alguien enruta la cobertura del suelo por `aggregate_rasters_to_h3`,
    obtendra `sum(valor)` sobre codigos: mitad arbolado (10) y mitad cultivo
    (40) darian 25, que es el codigo de nada y un numero perfectamente creible.
    """
    import inspect

    from pipelines.p0_exposure.raster_categorico_h3 import aggregate_categorical_to_h3

    fuente = inspect.getsource(aggregate_categorical_to_h3)

    assert "sum(pixeles)" in fuente
    assert "GROUP BY 1, 2" in fuente, "la clase tiene que estar en el agrupamiento"
