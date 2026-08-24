"""Agregacion de Overture a celdas H3, leyendo los parquet en remoto.

Overture no se descarga: el tema ``buildings`` del release vigente son 277 GB y
Colombia usa once de sus 512 ficheros. DuckDB los lee por HTTPS y poda por la
columna ``bbox``, que es la que tiene estadisticas por row-group; el resultado
es que el pais entero se agrega sin dejar un solo byte de Overture en disco.

**Dos contratos medidos** contra el release ``2026-08-19.0``, ambos contrarios
a lo que dice la receta habitual de Overture:

1. ``geometry`` llega tipada como ``GEOMETRY('OGC:CRS84')``, no como ``BLOB``.
   Envolverla en ``ST_GeomFromWKB`` —que es lo que hacen los ejemplos
   publicados— falla con "no function matches".
2. Cada tema particiona sus ficheros por su cuenta. El fichero ``00013`` de
   ``buildings`` y el ``00013`` de ``transportation`` cubren areas distintas,
   asi que la seleccion se resuelve contra el catalogo de **cada** tema. Medido:
   la caja de Quibdó cae en el ``00013`` de edificaciones y en ninguno de
   transporte con ese indice.
"""

from __future__ import annotations

from typing import Any

from ..common.constants import H3_RES_COMPUTE
from ..common.geo import BBox
from ..common.logging import get_logger
from .sources.overture import bbox_predicate
from .vector_h3 import (
    NON_VEHICLE_CLASSES,
    VectorSum,
    aggregate_lines_to_h3,
    road_class_expression,
)

_log = get_logger(__name__)

#: Extension que DuckDB necesita para leer parquet por HTTPS. No entra en
#: :data:`pipelines.p2_impact.exposure_join.DUCKDB_EXTENSIONS` a proposito: P2
#: lee el activo desde disco y no debe pagar esta instalacion en el camino
#: critico de un sismo.
HTTPFS_EXTENSION = "httpfs"

#: Ajustes de red para leer Overture en remoto.
#:
#: **El default de DuckDB no sirve aqui.** ``http_timeout`` viene en 30 s, y un
#: fichero de Overture con la poda por `bbox` aplicada tarda **minutos** en una
#: conexion domestica: medido, el primer fichero de Colombia tardo 3 min 47 s y
#: el segundo murio con "Timeout was reached" a mitad del build, despues de una
#: hora de descargas. En el runner de GitHub Actions no se nota; en la maquina
#: de quien reconstruye el activo, si.
#:
#: Se sube tambien el numero de reintentos: una lectura remota de varios minutos
#: tiene mas superficie para un corte transitorio que una de segundos.
HTTPFS_SETTINGS: dict[str, object] = {
    "http_timeout": 600_000,
    "http_retries": 5,
    "http_retry_backoff": 4,
    "http_keep_alive": True,
}

#: Subtipo de ``transportation`` que cuenta como via. El tema tambien publica
#: ``rail`` y ``water``, y sumarlos inflaria los kilometros de carretera.
ROAD_SUBTYPE = "road"


def ensure_httpfs(con: Any) -> None:
    """Carga ``httpfs`` y le pone plazos que aguanten una conexion lenta."""
    con.execute(f"INSTALL {HTTPFS_EXTENSION}")
    con.execute(f"LOAD {HTTPFS_EXTENSION}")
    for ajuste, valor in HTTPFS_SETTINGS.items():
        con.execute(f"SET {ajuste} = ?", [valor])


def _lista_sql(urls: list[str]) -> str:
    """Lista de rutas para ``read_parquet``, entrecomillada."""
    return "[" + ", ".join(f"'{u}'" for u in urls) + "]"


def aggregate_buildings_to_h3(
    con: Any,
    urls: list[str],
    *,
    bbox: BBox,
    tabla: str = "bld_h3",
    resolution: int = H3_RES_COMPUTE,
) -> VectorSum:
    """Cuenta edificaciones y suma su area por celda del centroide.

    Se procesa fichero a fichero y no en una sola consulta sobre los once: asi
    un corte de red a mitad de camino cuesta un fichero y no el pais entero, y
    el log deja ver cuanto aporto cada uno.
    """
    ensure_httpfs(con)
    con.execute(f"DROP TABLE IF EXISTS {tabla}")
    con.execute(f"CREATE TABLE {tabla} (h3_08 UBIGINT, bld_count BIGINT, bld_area_m2 DOUBLE)")

    for url in urls:
        con.execute(
            f"""
            INSERT INTO {tabla}
            SELECT h3_latlng_to_cell(ST_Y(c), ST_X(c), {resolution}) AS h3_08,
                   count(*)   AS bld_count,
                   sum(area)  AS bld_area_m2
            FROM (
                SELECT ST_Centroid(geometry) AS c,
                       ST_Area_Spheroid(geometry) AS area
                FROM read_parquet('{url}')
                WHERE {bbox_predicate(bbox)}
            ) t
            GROUP BY 1
            """
        )
        _log.info("fichero de edificaciones agregado", extra={"context": {"url": url}})

    # Una celda puede recibir edificaciones de dos ficheros vecinos: consolidar.
    con.execute(
        f"""
        CREATE OR REPLACE TABLE {tabla} AS
        SELECT h3_08, sum(bld_count) AS bld_count, sum(bld_area_m2) AS bld_area_m2
        FROM {tabla} GROUP BY 1
        """
    )
    celdas, total = con.execute(f"SELECT count(*), sum(bld_count) FROM {tabla}").fetchone()
    _log.info(
        "edificaciones agregadas",
        extra={"context": {"tabla": tabla, "celdas": celdas, "edificaciones": total}},
    )
    return VectorSum(tabla=tabla, celdas=int(celdas or 0), total=float(total or 0))


def roads_source_query(urls: list[str], bbox: BBox) -> str:
    """Consulta ``(geometry, clase)`` que consume :func:`aggregate_lines_to_h3`.

    Excluye las clases sin acceso rodado: Overture hereda de OSM que una
    escalera o un sendero son ``subtype='road'``, y el reporte publica
    "kilometros de via", no "kilometros de cosas por las que se puede pasar".
    """
    excluidas = ", ".join(f"'{c}'" for c in NON_VEHICLE_CLASSES)
    return f"""
        SELECT geometry, {road_class_expression("class")} AS clase
        FROM read_parquet({_lista_sql(urls)})
        WHERE subtype = '{ROAD_SUBTYPE}'
          AND (class IS NULL OR class NOT IN ({excluidas}))
          AND {bbox_predicate(bbox)}
    """


def aggregate_roads_to_h3(
    con: Any,
    urls: list[str],
    *,
    bbox: BBox,
    tabla: str = "roads_h3",
    resolution: int = H3_RES_COMPUTE,
) -> VectorSum:
    """Reparte kilometros de via entre las celdas que atraviesa.

    Fichero a fichero, igual que las edificaciones. **Overture particiona filas,
    no geometrias**: cada segmento vive entero en un solo fichero, asi que
    trocear el trabajo da exactamente el mismo resultado que una consulta sobre
    los once. Y evita que un corte de red a mitad de la densificacion —el paso
    mas caro del build— tire el pais entero.

    La consolidacion final suma por celda: una celda en el borde de dos ficheros
    recibe kilometros de los dos.
    """
    ensure_httpfs(con)
    partes: list[str] = []
    for i, url in enumerate(urls):
        parte = f"_{tabla}_p{i}"
        resumen = aggregate_lines_to_h3(
            con, roads_source_query([url], bbox), tabla=parte, resolution=resolution
        )
        partes.append(parte)
        _log.info(
            "fichero de vias agregado",
            extra={"context": {"url": url, "celdas": resumen.celdas, "km": resumen.total}},
        )

    union = " UNION ALL ".join(f"SELECT * FROM {p}" for p in partes)
    con.execute(
        f"""
        CREATE OR REPLACE TABLE {tabla} AS
        SELECT h3_08,
               sum(road_km_primary)   AS road_km_primary,
               sum(road_km_secondary) AS road_km_secondary,
               sum(road_km_other)     AS road_km_other
        FROM ({union}) GROUP BY 1
        """
    )
    for parte in partes:
        con.execute(f"DROP TABLE IF EXISTS {parte}")

    celdas, total = con.execute(
        f"SELECT count(*), sum(road_km_primary+road_km_secondary+road_km_other) FROM {tabla}"
    ).fetchone()
    _log.info(
        "vias agregadas",
        extra={"context": {"tabla": tabla, "celdas": celdas, "km": total, "ficheros": len(urls)}},
    )
    return VectorSum(tabla=tabla, celdas=int(celdas or 0), total=float(total or 0))
