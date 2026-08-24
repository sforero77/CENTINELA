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


#: Distancia por debajo de la cual dos puntos de fuentes distintas se toman por
#: el mismo establecimiento.
#:
#: **No es un parametro de gusto.** Medido sobre Colombia el 23-ago-2026:
#: HOTOSM trae 9.618 sedes de salud y healthsites.io 8.443, y **el 96,6 % de
#: las de healthsites cae a menos de 20 m de una de HOTOSM** — las dos derivan
#: de OpenStreetMap. Sumarlas sin deduplicar da 18.061 sedes, casi el doble de
#: las que hay, y ninguna guardia lo notaria porque el numero sigue siendo
#: positivo y del orden correcto. Subir el umbral a 50 o 100 m apenas mueve el
#: solape (96,9 % y 97,1 %): 20 m ya captura la duplicacion real y deja fuera
#: los establecimientos que de verdad estan pegados.
DEDUPE_METERS = 20.0

#: Grados por metro sobre el meridiano. Se usa igual en latitud y longitud, lo
#: que hace la ventana un cuadrado y no un circulo, y algo mas ancha en
#: longitud segun se sube de latitud (un grado de longitud mide 111 km en el
#: ecuador y 93 km a 33°N, el extremo norte de la ventana LATAM). Para decidir
#: si dos puntos son el mismo hospital, esa holgura es irrelevante y evita una
#: distancia esferoidal por cada par.
DEGREES_PER_METER = 1.0 / 111_320.0


def aggregate_points_to_h3(
    con: Any,
    fuentes: list[str],
    *,
    tabla: str,
    columna: str,
    resolution: int = H3_RES_COMPUTE,
    filtro: str = "TRUE",
    dedupe_m: float = DEDUPE_METERS,
) -> VectorSum:
    """Cuenta elementos por celda, tomando el centroide de cada geometria.

    Las fuentes se procesan **en el orden en que llegan**, que es el del
    manifest: la primera es la principal y entra entera; cada una posterior
    aporta solo los puntos que no estan a menos de ``dedupe_m`` de otro ya
    aceptado. Es lo que el catalogo de capas declara como "deduplicado por
    proximidad", y hasta ahora estaba declarado pero no implementado.

    Args:
        fuentes: rutas legibles por ``ST_Read`` (GeoPackage, shapefile,
            GeoJSON), la principal primero.
        filtro: SQL adicional, p. ej. para quedarse con un subconjunto de tags.
        dedupe_m: umbral de proximidad. ``0`` desactiva la deduplicacion.
    """
    grados = dedupe_m * DEGREES_PER_METER
    puntos = f"_pts_{tabla}"
    con.execute(f"DROP TABLE IF EXISTS {puntos}")
    con.execute(f"CREATE TABLE {puntos} (lon DOUBLE, lat DOUBLE)")

    for orden, fuente in enumerate(fuentes):
        con.execute(
            f"""
            CREATE OR REPLACE TEMP TABLE _entrantes AS
            SELECT ST_X(c) AS lon, ST_Y(c) AS lat
            FROM (SELECT ST_Centroid(geom) AS c FROM ST_Read('{fuente}') WHERE {filtro})
            """
        )
        if orden == 0 or grados <= 0:
            con.execute(f"INSERT INTO {puntos} SELECT lon, lat FROM _entrantes")
            nuevos = con.execute("SELECT count(*) FROM _entrantes").fetchone()[0]
            descartados = 0
        else:
            # Anti-join contra lo ya aceptado. Se materializa antes de insertar:
            # leer y escribir la misma tabla en una sola sentencia haria que los
            # puntos de esta fuente se deduplicaran contra si mismos.
            con.execute(
                f"""
                CREATE OR REPLACE TEMP TABLE _nuevos AS
                SELECT e.lon, e.lat FROM _entrantes e
                WHERE NOT EXISTS (
                    SELECT 1 FROM {puntos} p
                    WHERE abs(p.lon - e.lon) < {grados} AND abs(p.lat - e.lat) < {grados}
                )
                """
            )
            con.execute(f"INSERT INTO {puntos} SELECT lon, lat FROM _nuevos")
            nuevos = con.execute("SELECT count(*) FROM _nuevos").fetchone()[0]
            descartados = con.execute("SELECT count(*) FROM _entrantes").fetchone()[0] - nuevos
        _log.info(
            "fuente de puntos incorporada",
            extra={
                "context": {
                    "tabla": tabla,
                    "fuente": fuente,
                    "nuevos": nuevos,
                    "duplicados_descartados": descartados,
                }
            },
        )

    con.execute(
        f"""
        CREATE OR REPLACE TABLE {tabla} AS
        SELECT h3_latlng_to_cell(lat, lon, {resolution}) AS h3_08,
               count(*)::BIGINT AS {columna}
        FROM {puntos} GROUP BY 1
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
