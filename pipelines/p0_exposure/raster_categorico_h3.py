"""Agregar un raster **categorico** a H3: contar clases, no sumarlas.

`aggregate_rasters_to_h3` no sirve aqui, y el motivo merece quedar escrito. Esa
funcion materializa una sola columna DOUBLE y hace `sum(valor)`. Sumar codigos
de clase —10 arbolado, 30 pastizal, 40 cultivo— produce un numero perfectamente
plausible y completamente sin sentido: una celda mitad arbolado y mitad cultivo
daria 25, que es el codigo de nada.

Es el modo de fallo que este proyecto persigue desde el primer dia: el que no
revienta, el que publica una cifra creible.

**Y tampoco sirve su forma de emitir datos.** `raster_blocks_to_arrow` cede una
fila por pixel con dato, lo cual es razonable con GHS-POP, que es disperso: 2,2
millones de pixeles con dato de cada 100. La cobertura del suelo es **densa** —
todo pixel de tierra tiene clase—, asi que Colombia entera serian miles de
millones de filas para acabar en unas 250.000 celdas.

Por eso aqui se agrega **dentro de numpy, por bloque**, y a DuckDB solo llega lo
ya contado: una fila por (celda, clase). Los conteos son sumables entre teselas
vecinas; las fracciones no, y por eso se derivan al final y nunca por bloque.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pyarrow as pa

from ..common.constants import H3_RES_COMPUTE
from ..common.geo import ensure_bundled_proj
from ..common.logging import get_logger

_log = get_logger(__name__)

#: Filas de la piramide que se leen de una vez. A /8 una tesela son 4.500x4.500
#: pixeles; 512 filas son ~2,3 M de pixeles, unos 20 MB entre banda y arrays
#: intermedios. El pico no depende del pais, que es todo el objetivo.
FILAS_POR_BLOQUE: int = 512


@dataclass(frozen=True, slots=True)
class ClaseSum:
    """Lo que produjo una agregacion categorica."""

    tabla: str
    celdas: int
    pixeles: int


def clases_por_celda(
    fuente: str | Path,
    *,
    overview: int = 1,
    nodata: int = 0,
    agrupacion: dict[int, str] | None = None,
    filas_por_bloque: int = FILAS_POR_BLOQUE,
    resolution: int = H3_RES_COMPUTE,
) -> Iterator[pa.Table]:
    """Cuenta pixeles por (celda H3, clase) leyendo por bloques de filas.

    Args:
        fuente: ruta local o ``/vsicurl/...`` para leer en remoto sin descargar.
        overview: nivel de piramide. ``8`` sobre un producto de 10 m da ~80 m.
        nodata: valor que no cuenta. WorldCover usa 0 y no lo declara.
        agrupacion: codigo -> nombre publicado. Los codigos ausentes se
            descartan: no todas las clases del producto interesan, y arrastrar
            las que no llenaria el contrato de columnas siempre a cero.
        filas_por_bloque: filas de la piramide por lectura.
        resolution: resolucion H3 de computo.

    Yields:
        Tablas ``(lon float64, lat float64, clase string)``, una por bloque. El
        indice H3 lo resuelve DuckDB con su extension, igual que
        `aggregate_rasters_to_h3`: `h3-py` v4 devuelve cadenas y convertirlas en
        Python seria un bucle por pixel sobre millones de filas.
    """
    ensure_bundled_proj()
    import rasterio
    from rasterio.enums import Resampling
    from rasterio.windows import Window

    with rasterio.open(str(fuente)) as src:
        alto, ancho = src.height // overview, src.width // overview
        # La transformacion de la piramide, no la del raster completo: sin
        # escalarla, cada bloque saldria desplazado por el factor de overview.
        transform = src.transform * src.transform.scale(overview, overview)

        for inicio in range(0, alto, filas_por_bloque):
            filas = min(filas_por_bloque, alto - inicio)
            # `out_shape` es lo que hace que GDAL sirva la overview en vez de
            # remuestrear la banda completa; `mode` es la unica remuestra
            # honesta para datos categoricos — `average` inventaria clases que
            # no estan (la media de 10 y 30 es 20, que existe y es otra cosa).
            banda = src.read(
                1,
                window=Window(0, inicio * overview, src.width, filas * overview),
                out_shape=(filas, ancho),
                resampling=Resampling.mode,
            )

            validos = banda != nodata
            if agrupacion is not None:
                validos &= np.isin(banda, list(agrupacion))
            fs, cs = np.nonzero(validos)
            if fs.size == 0:
                continue

            xs, ys = rasterio.transform.xy(transform, fs + inicio, cs)
            valores = banda[fs, cs]

            # El mapeo codigo -> nombre se hace con una tabla de busqueda de 256
            # entradas en vez de un bucle por pixel: son millones por bloque.
            if agrupacion is not None:
                tabla_nombres = np.array([agrupacion.get(i, "") for i in range(256)], dtype=object)
                nombres = tabla_nombres[valores]
            else:
                nombres = valores.astype(str)

            yield pa.table(
                {
                    "lon": pa.array(np.asarray(xs, dtype="float64")),
                    "lat": pa.array(np.asarray(ys, dtype="float64")),
                    "clase": pa.array(nombres, pa.string()),
                }
            )


def aggregate_categorical_to_h3(
    con: Any,
    fuentes: list[str],
    *,
    tabla: str,
    overview: int = 1,
    nodata: int = 0,
    agrupacion: dict[int, str] | None = None,
    resolution: int = H3_RES_COMPUTE,
) -> ClaseSum:
    """Agrega varias teselas categoricas a una tabla ``(h3_08, clase, pixeles)``.

    Los conteos se **suman** entre teselas: una celda H3 en el borde recibe
    pixeles de dos, y sin la consolidacion final aparecerian dos filas para el
    mismo par (celda, clase). Las fracciones se derivan despues, sobre el total
    consolidado — derivarlas por tesela daria porcentajes sobre denominadores
    distintos, que es la forma silenciosa de este error.
    """
    con.execute(f"DROP TABLE IF EXISTS {tabla}")
    con.execute(f"CREATE TABLE {tabla} (h3_08 UBIGINT, clase VARCHAR, pixeles BIGINT)")

    pixeles = 0
    ausentes = 0
    for fuente in fuentes:
        # UNA TESELA QUE NO EXISTE NO ES UN FALLO.
        #
        # El proveedor solo publica las que contienen tierra, y `tiles_for_bbox`
        # genera la rejilla completa: la caja de Chile son 210 teselas y la
        # mayoria son Pacifico abierto. Es el mismo criterio que `download_ghsl`
        # ya aplicaba —"tesela ausente, probablemente solo oceano"— y que aqui
        # falto: tumbo diez de diecinueve builds con un 404 de GDAL.
        #
        # El try envuelve el bucle y no una lista materializada, para no perder
        # la lectura por bloques: el 404 salta al abrir el fichero, que es lo
        # primero que hace el generador, asi que nunca hay inserciones a medias.
        try:
            for bloque in clases_por_celda(
                fuente,
                overview=overview,
                nodata=nodata,
                agrupacion=agrupacion,
                resolution=resolution,
            ):
                pixeles += bloque.num_rows
                con.register("_bloque_clases", bloque)
                con.execute(
                    f"INSERT INTO {tabla} "
                    f"SELECT h3_latlng_to_cell(lat, lon, {resolution}) AS h3_08, "
                    "clase, count(*) FROM _bloque_clases GROUP BY 1, 2"
                )
                con.unregister("_bloque_clases")
        except Exception as error:
            if "404" not in str(error):
                raise
            ausentes += 1

    # UNA TESELA AUSENTE NO ES UN FALLO; TODAS AUSENTES SI LO ES.
    #
    # El proveedor solo publica las teselas con tierra, asi que un 404 suelto es
    # oceano y se salta. Pero si **ninguna** responde, la causa no es el mar: es
    # que la coleccion se movio de bucket o cambio de version —las URL son
    # constantes fijas—. La tabla quedaria vacia, el LEFT JOIN del ensamblaje
    # pondria 0.0 en las siete columnas de cobertura de todas las celdas, y el
    # activo se publicaria con "0 % arbolado" en la Amazonia pasando todos los
    # asserts. Es el cero silencioso, por la unica puerta que no lo vigilaba.
    if fuentes and ausentes == len(fuentes):
        raise ValueError(
            f"Ninguna de las {len(fuentes)} teselas de '{tabla}' respondio: todas dieron 404. "
            "Una tesela ausente es oceano; todas ausentes es la coleccion movida de sitio. "
            f"Revisar la URL de la fuente antes de reconstruir. Primera: {fuentes[0]}"
        )

    con.execute(
        f"CREATE OR REPLACE TABLE {tabla} AS "
        f"SELECT h3_08, clase, sum(pixeles) AS pixeles FROM {tabla} GROUP BY 1, 2"
    )
    celdas = con.execute(f"SELECT count(DISTINCT h3_08) FROM {tabla}").fetchone()[0]

    _log.info(
        "capa categorica agregada",
        extra={
            "context": {
                "tabla": tabla,
                "celdas": celdas,
                "pixeles": pixeles,
                "teselas_ausentes": ausentes,
            }
        },
    )
    return ClaseSum(tabla=tabla, celdas=int(celdas), pixeles=pixeles)


def fracciones_por_celda(con: Any, *, origen: str, destino: str, clases: tuple[str, ...]) -> int:
    """Pivota ``(celda, clase, pixeles)`` a una fila por celda con porcentajes.

    El denominador es el total de pixeles **clasificados** de la celda, no el
    numero de pixeles que caben en ella. La diferencia importa en la costa y en
    los bordes de tesela, donde media celda puede ser mar: dividir por la
    capacidad teorica daria porcentajes que no suman nada reconocible y harian
    parecer despoblada una celda perfectamente medida.

    Se publica tambien ``lulc_px``, que dice cuanta evidencia hay detras de esos
    porcentajes. Una celda con nueve pixeles y otra con ciento cuarenta no
    merecen la misma confianza, y sin el conteo no hay forma de distinguirlas.
    """
    columnas = ", ".join(
        f"round(100.0 * sum(CASE WHEN clase = '{c}' THEN pixeles ELSE 0 END) / total, 1) "
        f"AS lulc_{c}_pct"
        for c in clases
    )
    con.execute(
        f"CREATE OR REPLACE TABLE {destino} AS "
        f"SELECT h3_08, {columnas}, total AS lulc_px "
        f"FROM (SELECT *, sum(pixeles) OVER (PARTITION BY h3_08) AS total FROM {origen}) "
        "WHERE total > 0 GROUP BY h3_08, total"
    )
    return int(con.execute(f"SELECT count(*) FROM {destino}").fetchone()[0])
