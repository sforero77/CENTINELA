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

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pyarrow as pa

from ..common.constants import H3_RES_COMPUTE
from ..common.logging import get_logger

_log = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class RasterSum:
    """Resultado de agregar un raster a celdas H3."""

    tabla: str
    celdas: int
    total: float


def raster_to_arrow(
    path: Path,
    *,
    nodata: float | None = None,
    min_value: float = 0.0,
) -> pa.Table:
    """Pixeles con dato de un raster, como tabla ``(lon, lat, valor)``.

    Args:
        path: GeoTIFF a leer.
        nodata: valor de nodata. Si es ``None`` se usa el declarado en el
            archivo; si el archivo tampoco lo declara, no se enmascara nada.
        min_value: se descartan los pixeles por debajo de este umbral. Por
            defecto 0: un pixel sin gente no aporta nada y multiplicaria por
            veinte el volumen a procesar.
    """
    import rasterio
    from pyproj import Transformer

    with rasterio.open(path) as src:
        banda = src.read(1)
        sin_dato = src.nodata if nodata is None else nodata
        mascara = banda > min_value
        if sin_dato is not None:
            mascara &= banda != sin_dato

        filas, columnas = np.nonzero(mascara)
        if filas.size == 0:
            return pa.table(
                {
                    "lon": pa.array([], pa.float64()),
                    "lat": pa.array([], pa.float64()),
                    "valor": pa.array([], pa.float64()),
                }
            )

        valores = banda[filas, columnas].astype("float64")
        # Centro del pixel, no su esquina: desplazar media celda evita un sesgo
        # sistematico de 50 m que a r8 puede cambiar de hexagono.
        xs, ys = src.xy(filas, columnas)
        xs = np.asarray(xs, dtype="float64")
        ys = np.asarray(ys, dtype="float64")

        if src.crs and src.crs.to_string() != "EPSG:4326":
            a_wgs84 = Transformer.from_crs(src.crs, "EPSG:4326", always_xy=True)
            xs, ys = a_wgs84.transform(xs, ys)

    return pa.table({"lon": pa.array(xs), "lat": pa.array(ys), "valor": pa.array(valores)})


def aggregate_rasters_to_h3(
    con: Any,
    rasters: list[Path],
    *,
    tabla: str,
    columna: str,
    resolution: int = H3_RES_COMPUTE,
    nodata: float | None = None,
) -> RasterSum:
    """Suma varios rasters a celdas H3 y materializa ``tabla(h3_08, columna)``.

    Los rasters se procesan de uno en uno: nueve teselas de 100 millones de
    pixeles no caben simultaneamente en memoria de un runner.
    """
    con.execute(f"DROP TABLE IF EXISTS {tabla}")
    con.execute(f"CREATE TABLE {tabla} (h3_08 UBIGINT, {columna} DOUBLE)")

    for raster in rasters:
        tabla_pixeles = raster_to_arrow(raster, nodata=nodata)
        if tabla_pixeles.num_rows == 0:
            _log.info("raster sin pixeles con dato", extra={"context": {"raster": raster.name}})
            continue
        con.register("pixeles", tabla_pixeles)
        con.execute(
            f"""
            INSERT INTO {tabla}
            SELECT h3_latlng_to_cell(lat, lon, {resolution}) AS h3_08,
                   sum(valor) AS {columna}
            FROM pixeles GROUP BY 1
            """
        )
        con.unregister("pixeles")
        _log.info(
            "raster agregado",
            extra={"context": {"raster": raster.name, "pixeles": tabla_pixeles.num_rows}},
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
        extra={"context": {"tabla": tabla, "celdas": celdas, "total": total}},
    )
    return RasterSum(tabla=tabla, celdas=int(celdas), total=float(total or 0.0))
