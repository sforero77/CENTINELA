"""Agregacion raster -> celda H3 (§6.1: suma nacional dentro del 1 % del oficial).

El problema de escala: una tesela de GHS-POP son 100 millones de pixeles y
Colombia necesita nueve. Recorrerlos todos en Python seria inviable. Pero la
poblacion es dispersa —en la tesela R9_C11 solo 2,2 millones de pixeles de 100
millones tienen habitantes—, asi que se filtran primero los pixeles con dato y
solo esos se reproyectan y se indexan.

El resto del trabajo lo hace DuckDB: ``h3_latlng_to_cell`` sobre una columna es
vectorizado en C++, mientras que llamarlo en un bucle de Python por cada pixel
no lo es.

**El nodata no es opcional.** GHS-POP marca el oceano con -200 y hay unos 22
millones de esas celdas por tesela. Sumarlas da poblacion negativa, y el assert
de calidad de §6.4 marcaria como corruptos unos datos que estan perfectos.
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


@dataclass(frozen=True, slots=True)
class RasterSum:
    """Resultado de agregar un raster a celdas H3."""

    tabla: str
    celdas: int
    total: float


#: Cuantos pixeles se leen de golpe. A float32 son unos 128 MB por lectura, mas
#: la mascara: cabe de sobra en cualquier runner y es bastante grande como para
#: que el coste por bloque no se note.
PIXELES_POR_BLOQUE = 32 << 20


def _tabla_vacia() -> pa.Table:
    """Tipada a proposito: sin tipos, DuckDB no puede unirla con las demas."""
    return pa.table(
        {
            "lon": pa.array([], pa.float64()),
            "lat": pa.array([], pa.float64()),
            "valor": pa.array([], pa.float64()),
        }
    )


def raster_blocks_to_arrow(
    path: Path,
    *,
    nodata: float | None = None,
    min_value: float = 0.0,
    pixeles_por_bloque: int = PIXELES_POR_BLOQUE,
) -> Iterator[pa.Table]:
    """Los pixeles con dato de un raster, en bloques de filas.

    **Leer el raster entero no escala con el tamano del pais.** `src.read(1)`
    trae toda la banda a memoria de una vez, y eso es lineal en el area:

    ======  ==============  ==================
    Pais    Pixeles         Banda + mascara
    ======  ==============  ==================
    COL     0,39 G          1,9 GB
    MEX     0,86 G          4,3 GB
    BRA     **2,57 G**      **12,8 GB**
    ======  ==============  ==================

    Un runner de GitHub tiene 16 GB. El build de Brasil murio dos veces en el
    mismo punto —treinta y ocho segundos despues de terminar `pop_h3`, que es
    justo cuando empieza `pop_alt_h3` con el WorldPop total del pais— y lo que
    lo mataba era esa sola linea.

    Por bloques, el pico no depende del pais: son los mismos ~128 MB para
    Colombia que para Brasil. Y de paso abarata los diecisiete restantes.

    Yields:
        Una tabla ``(lon, lat, valor)`` por bloque con algo dentro. Los bloques
        vacios —oceano, desierto— no se emiten.
    """
    ensure_bundled_proj()

    import rasterio
    from pyproj import Transformer

    with rasterio.open(path) as src:
        sin_dato = src.nodata if nodata is None else nodata
        a_wgs84 = (
            Transformer.from_crs(src.crs, "EPSG:4326", always_xy=True)
            if src.crs and src.crs.to_string() != "EPSG:4326"
            else None
        )
        filas_por_bloque = max(1, pixeles_por_bloque // max(1, src.width))

        for inicio in range(0, src.height, filas_por_bloque):
            alto = min(filas_por_bloque, src.height - inicio)
            ventana = rasterio.windows.Window(0, inicio, src.width, alto)
            banda = src.read(1, window=ventana)

            mascara = banda > min_value
            if sin_dato is not None:
                mascara &= banda != sin_dato

            filas, columnas = np.nonzero(mascara)
            if filas.size == 0:
                continue

            valores = banda[filas, columnas].astype("float64")
            # Centro del pixel, no su esquina: desplazar media celda evita un
            # sesgo sistematico de 50 m que a r8 puede cambiar de hexagono.
            # `filas` es relativa a la ventana, asi que se le suma el origen.
            xs, ys = src.xy(filas + inicio, columnas)
            xs = np.asarray(xs, dtype="float64")
            ys = np.asarray(ys, dtype="float64")

            if a_wgs84 is not None:
                xs, ys = a_wgs84.transform(xs, ys)

            yield pa.table({"lon": pa.array(xs), "lat": pa.array(ys), "valor": pa.array(valores)})


def espacio_libre_mb(ruta: Path) -> int:
    """Megabytes libres en el disco donde vive `ruta`.

    Existe porque el mensaje con que GitHub mata un runner sin recursos
    —«The runner has received a shutdown signal»— **no distingue disco de
    memoria**, y sin esa distincion el diagnostico de un build caido es una
    conjetura. Brasil se cayo dos veces en el mismo punto y hubo que deducirlo.
    """
    import shutil

    try:
        return shutil.disk_usage(ruta).free // (1 << 20)
    except OSError:  # pragma: no cover - depende del sistema de archivos
        return -1


def aggregate_rasters_to_h3(
    con: Any,
    rasters: list[Path],
    *,
    tabla: str,
    columna: str,
    resolution: int = H3_RES_COMPUTE,
    nodata: float | None = None,
    liberar: bool = False,
) -> RasterSum:
    """Suma varios rasters a celdas H3 y materializa ``tabla(h3_08, columna)``.

    Los rasters se procesan de uno en uno: nueve teselas de 100 millones de
    pixeles no caben simultaneamente en memoria de un runner.

    Args:
        liberar: borra cada raster **en cuanto esta agregado**. Un raster ya
            sumado a la tabla H3 no se vuelve a leer, asi que conservarlo solo
            ocupa disco — y en Brasil eso son 9,1 GB de WorldPop mas 437 MB de
            GHSL que siguen ahi cuando DuckDB necesita derramar una tabla de
            4,29 millones de celdas, sobre un runner con ~14 GB libres.

            Por defecto **no** libera: en local, conservarlos es lo que hace
            que reanudar un build de una hora sea barato, que es una regla dura
            del proyecto. En CI el runner arranca vacio cada vez y no hay nada
            que reanudar, asi que ahi si conviene.
    """
    con.execute(f"DROP TABLE IF EXISTS {tabla}")
    con.execute(f"CREATE TABLE {tabla} (h3_08 UBIGINT, {columna} DOUBLE)")

    for raster in rasters:
        # POR BLOQUES, NO EL RASTER ENTERO.
        #
        # `raster_to_arrow` traia la banda completa a memoria, y eso es lineal
        # en el area del pais: 1,9 GB para Colombia y **12,8 GB para Brasil**,
        # sobre un runner de 16. El build de Brasil murio dos veces por esta
        # linea. Ver `raster_blocks_to_arrow`.
        pixeles = 0
        for bloque in raster_blocks_to_arrow(raster, nodata=nodata):
            con.register("pixeles", bloque)
            con.execute(
                f"""
                INSERT INTO {tabla}
                SELECT h3_latlng_to_cell(lat, lon, {resolution}) AS h3_08,
                       sum(valor) AS {columna}
                FROM pixeles GROUP BY 1
                """
            )
            con.unregister("pixeles")
            pixeles += bloque.num_rows

        if pixeles == 0:
            _log.info("raster sin pixeles con dato", extra={"context": {"raster": raster.name}})
            if liberar:
                raster.unlink(missing_ok=True)
            continue

        if liberar:
            raster.unlink(missing_ok=True)

        _log.info(
            "raster agregado",
            extra={
                "context": {
                    "raster": raster.name,
                    "pixeles": pixeles,
                    "liberado": liberar,
                    "disco_libre_mb": espacio_libre_mb(raster.parent),
                }
            },
        )

    # Una celda puede recibir pixeles de dos teselas vecinas: consolidar.
    con.execute(
        f"""
        CREATE OR REPLACE TABLE {tabla} AS
        SELECT h3_08, sum({columna}) AS {columna} FROM {tabla} GROUP BY 1
        """
    )
    celdas, total = con.execute(f"SELECT count(*), sum({columna}) FROM {tabla}").fetchone()
    _log.info(
        "agregacion completa",
        extra={
            "context": {
                "tabla": tabla,
                "celdas": celdas,
                "total": total,
                "disco_libre_mb": espacio_libre_mb(rasters[0].parent if rasters else Path()),
            }
        },
    )
    return RasterSum(tabla=tabla, celdas=int(celdas), total=float(total or 0.0))
