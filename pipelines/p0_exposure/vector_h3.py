"""Agregacion de capas vectoriales a celdas H3.

Dos formas distintas, con trampas distintas:

**Puntos** (salud, educacion, aeropuertos). El extracto de HOTOSM **no trae solo
puntos**: verificado sobre Colombia, `health_facilities` mezcla `POINT`,
`POLYGON` y `MULTIPOLYGON`, porque un hospital grande esta mapeado en OSM como
edificio y no como nodo. Asumir puntos perderia justo los establecimientos mas
grandes, que son los que importan. Se toma el centroide de lo que venga.

**Lineas** (vias). Una via cruza muchas celdas, asi que no basta con asignarla a
una: hay que **partirla** por celda y sumar la longitud de cada trozo. Hacerlo
exacto exige intersectar cada segmento con cada hexagono. La aproximacion que
usa este modulo —densificar la linea en puntos e imputar longitud a la celda de
cada punto— converge al valor exacto conforme el paso se hace menor que la
celda, y cuesta ordenes de magnitud menos.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..common.constants import H3_RES_COMPUTE
from ..common.logging import get_logger

_log = get_logger(__name__)

#: Paso de densificacion de lineas, en kilometros. 200 m es menos de la quinta
#: parte del ancho de una celda r8 (~1.060 m): la condicion para que ninguna
#: celda atravesada se pierda y para que el reparto de longitud converja.
LINE_STEP_KM = 0.2

#: Tope de puntos por via. Sin el, una troncal de 500 km generaria 2.500 puntos
#: y unas pocas geometrias patologicas dominarian el coste de todo el build.
MAX_POINTS_PER_LINE = 2000


@dataclass(frozen=True, slots=True)
class VectorSum:
    """Resultado de agregar una capa vectorial."""

    tabla: str
    celdas: int
    total: float


def aggregate_points_to_h3(
    con: Any,
    fuentes: list[str],
    *,
    tabla: str,
    columna: str,
    resolution: int = H3_RES_COMPUTE,
    filtro: str = "TRUE",
) -> VectorSum:
    """Cuenta elementos por celda, tomando el centroide de cada geometria.

    Args:
        fuentes: rutas legibles por ``ST_Read`` (GeoPackage, shapefile,
            GeoJSON). Varias fuentes se acumulan en la misma tabla.
        filtro: SQL adicional, p. ej. para quedarse con un subconjunto de tags.
    """
    con.execute(f"DROP TABLE IF EXISTS {tabla}")
    con.execute(f"CREATE TABLE {tabla} (h3_08 UBIGINT, {columna} BIGINT)")
    for fuente in fuentes:
        con.execute(
            f"""
            INSERT INTO {tabla}
            SELECT h3_latlng_to_cell(ST_Y(c), ST_X(c), {resolution}) AS h3_08,
                   count(*) AS {columna}
            FROM (
                SELECT ST_Centroid(geom) AS c FROM ST_Read('{fuente}') WHERE {filtro}
            ) t
            GROUP BY 1
            """
        )
    con.execute(
        f"""
        CREATE OR REPLACE TABLE {tabla} AS
        SELECT h3_08, sum({columna}) AS {columna} FROM {tabla} GROUP BY 1
        """
    )
    celdas, total = con.execute(f"SELECT count(*), sum({columna}) FROM {tabla}").fetchone()
    _log.info(
        "capa de puntos agregada",
        extra={"context": {"tabla": tabla, "celdas": celdas, "total": total}},
    )
    return VectorSum(tabla=tabla, celdas=int(celdas or 0), total=float(total or 0))


#: Clases de via de Overture que el reporte separa. El resto cae en `other`.
ROAD_CLASSES = {
    "primary": ("motorway", "trunk", "primary"),
    "secondary": ("secondary",),
}


def road_class_expression(columna: str = "class") -> str:
    """``CASE`` que mapea la clase de Overture a las tres columnas del reporte."""
    primarias = ", ".join(f"'{c}'" for c in ROAD_CLASSES["primary"])
    secundarias = ", ".join(f"'{c}'" for c in ROAD_CLASSES["secondary"])
    return (
        f"CASE WHEN {columna} IN ({primarias}) THEN 'primary' "
        f"WHEN {columna} IN ({secundarias}) THEN 'secondary' ELSE 'other' END"
    )


def aggregate_lines_to_h3(
    con: Any,
    consulta_fuente: str,
    *,
    tabla: str,
    resolution: int = H3_RES_COMPUTE,
    paso_km: float = LINE_STEP_KM,
) -> VectorSum:
    """Reparte longitud de lineas entre las celdas que atraviesan.

    ``consulta_fuente`` debe devolver ``(geometry, clase)``. La longitud se mide
    sobre el esferoide en kilometros y se reparte a partes iguales entre los
    puntos densificados: una via recta que cruza tres celdas por igual aporta un
    tercio a cada una.

    DuckDB no tiene ``ST_Densify``; ``ST_LineInterpolatePoints`` hace lo mismo
    pidiendo la fraccion de recorrido entre punto y punto, que aqui se deriva de
    la longitud real de cada via.
    """
    con.execute(f"DROP TABLE IF EXISTS {tabla}")
    con.execute(
        f"""
        CREATE TABLE {tabla} AS
        WITH vias AS (
            SELECT geometry, clase,
                   ST_Length_Spheroid(geometry) / 1000.0 AS km
            FROM ({consulta_fuente})
            WHERE ST_Length_Spheroid(geometry) > 0
        ),
        con_paso AS (
            SELECT geometry, clase, km,
                   LEAST(
                       GREATEST(CEIL(km / {paso_km}), 2),
                       {MAX_POINTS_PER_LINE}
                   )::BIGINT AS n_puntos
            FROM vias
        ),
        puntos AS (
            SELECT clase, km, n_puntos,
                   unnest(ST_Dump(
                       ST_LineInterpolatePoints(geometry, 1.0 / n_puntos, true)
                   )) AS p
            FROM con_paso
        )
        SELECT h3_latlng_to_cell(ST_Y(p.geom), ST_X(p.geom), {resolution}) AS h3_08,
               sum(CASE WHEN clase='primary'   THEN km / n_puntos ELSE 0 END) AS road_km_primary,
               sum(CASE WHEN clase='secondary' THEN km / n_puntos ELSE 0 END) AS road_km_secondary,
               sum(CASE WHEN clase='other'     THEN km / n_puntos ELSE 0 END) AS road_km_other
        FROM puntos GROUP BY 1
        """
    )
    celdas, total = con.execute(
        f"SELECT count(*), sum(road_km_primary+road_km_secondary+road_km_other) FROM {tabla}"
    ).fetchone()
    _log.info(
        "capa de vias agregada",
        extra={"context": {"tabla": tabla, "celdas": celdas, "km": total}},
    )
    return VectorSum(tabla=tabla, celdas=int(celdas or 0), total=float(total or 0))
