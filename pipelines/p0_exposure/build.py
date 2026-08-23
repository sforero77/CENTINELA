"""Construccion del activo ``exposure_h3`` de un pais (O4, RF-08).

Punto de entrada de ``make country ISO=COL``. El pipeline es
descarga -> agregacion por capa -> join -> asserts de calidad -> parquet
particionado, y todo el linaje queda registrado en el manifest.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..common.logging import get_logger
from ..common.manifest import Manifest, lint_manifest
from .layers import LAYERS, LayerSpec, required_layers

_log = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class BuildPlan:
    """Plan de construccion resuelto contra un manifest."""

    iso3: str
    manifest: Manifest
    #: Capas que se van a construir, en orden.
    capas: tuple[LayerSpec, ...]
    salida: Path

    @property
    def capas_faltantes(self) -> tuple[LayerSpec, ...]:
        """Capas requeridas sin fuente declarada en el manifest."""
        declaradas = {source.layer for source in self.manifest.sources}
        return tuple(layer for layer in required_layers() if layer.id not in declaradas)


def plan_build(iso3: str, *, manifests_dir: Path | None = None, out_dir: Path) -> BuildPlan:
    """Resuelve el plan y valida el manifest antes de descargar nada.

    Fallar temprano importa: descargar GHS-POP y un release de Overture cuesta
    minutos y gigas; un manifest con una licencia NC colada o un vintage
    flotante debe detenerse antes de eso.

    Raises:
        ValueError: si el manifest no pasa el lint o faltan capas requeridas.
    """
    manifest = Manifest.load(iso3, manifests_dir)
    problemas = [p for p in lint_manifest(manifest) if "(aviso)" not in p]
    if problemas:
        raise ValueError(f"Manifest {iso3} invalido:\n  - " + "\n  - ".join(problemas))

    plan = BuildPlan(
        iso3=manifest.iso3,
        manifest=manifest,
        capas=LAYERS,
        salida=out_dir / f"iso3={manifest.iso3}" / "layer=exposure",
    )
    if plan.capas_faltantes:
        faltan = ", ".join(layer.id for layer in plan.capas_faltantes)
        raise ValueError(f"Manifest {iso3} no declara capas requeridas: {faltan}")

    _log.info(
        "plan de construccion resuelto",
        extra={
            "context": {
                "iso3": plan.iso3,
                "manifest": manifest.manifest_id,
                "cubo": manifest.bucket.value,
                "capas": len(plan.capas),
            }
        },
    )
    return plan


#: Ensamblaje final del activo. Todas las capas entran por LEFT JOIN sobre el
#: crosswalk: una celda sin edificios registrados es una celda con cero
#: edificios, no una celda ausente. Y se descartan las celdas sin nada — no
#: aportan al reporte y multiplicarian por tres el tamano del parquet.
SQL_EXPOSURE = """
CREATE OR REPLACE TABLE exposure_h3 AS
SELECT
    c.h3_08,
    '{iso3}' AS iso3,
    a.adm1_id,
    c.adm2_id,
    COALESCE(p.pop_total, 0.0)                        AS pop_total,
    COALESCE(j.pop_0_14, 0.0)                         AS pop_0_14,
    GREATEST(
        COALESCE(p.pop_total, 0.0)
        - COALESCE(j.pop_0_14, 0.0) - COALESCE(v.pop_65p, 0.0), 0.0
    )                                                 AS pop_15_64,
    COALESCE(v.pop_65p, 0.0)                          AS pop_65p,
    COALESCE(w.pop_alt_worldpop, 0.0)                 AS pop_alt_worldpop,
    COALESCE(b.bld_count, 0)                          AS bld_count,
    COALESCE(b.bld_area_m2, 0.0)                      AS bld_area_m2,
    COALESCE(h.health_count, 0)                       AS health_count,
    COALESCE(e.edu_count, 0)                          AS edu_count,
    COALESCE(r.road_km_primary, 0.0)                  AS road_km_primary,
    COALESCE(r.road_km_secondary, 0.0)                AS road_km_secondary,
    COALESCE(r.road_km_other, 0.0)                    AS road_km_other,
    {flags}                                           AS flags_calidad,
    '{manifest}'                                      AS src_manifest
FROM crosswalk_h3_adm c
JOIN admin_lookup a USING (adm2_id)
LEFT JOIN pop_h3        p USING (h3_08)
LEFT JOIN pop_0_14_h3   j USING (h3_08)
LEFT JOIN pop_65p_h3    v USING (h3_08)
LEFT JOIN pop_alt_h3    w USING (h3_08)
LEFT JOIN bld_h3        b USING (h3_08)
LEFT JOIN health_h3     h USING (h3_08)
LEFT JOIN edu_h3        e USING (h3_08)
LEFT JOIN roads_h3      r USING (h3_08)
WHERE COALESCE(p.pop_total, 0) > 0
   OR COALESCE(b.bld_count, 0) > 0
   OR COALESCE(r.road_km_primary + r.road_km_secondary + r.road_km_other, 0) > 0
"""

#: Banderas de calidad de §6.4. Se **publican**, no se ocultan: una celda con
#: gente y sin edificios registrados suele ser asentamiento informal mal
#: mapeado, y esconderlo seria fingir una cobertura que no existe.
SQL_FLAGS = """
    NULLIF(
        CONCAT_WS(',',
            CASE WHEN COALESCE(b.bld_count,0)=0 AND COALESCE(p.pop_total,0)>500
                 THEN 'revisar_sin_edificios' END,
            CASE WHEN COALESCE(w.pop_alt_worldpop,0)>0
                  AND abs(COALESCE(p.pop_total,0)-w.pop_alt_worldpop)
                      / NULLIF(w.pop_alt_worldpop,0) > 2.0
                 THEN 'discrepancia_poblacional' END
        ), ''
    )
"""


def assemble_exposure(con: Any, *, iso3: str, manifest_id: str) -> dict[str, float]:
    """Ensambla ``exposure_h3`` a partir de las tablas por capa ya agregadas.

    Espera que existan ``crosswalk_h3_adm``, ``admin_lookup`` y las tablas de
    capa. Las que falten se pueden crear vacias con :func:`ensure_layer_tables`.
    """
    con.execute(SQL_EXPOSURE.format(iso3=iso3, manifest=manifest_id, flags=SQL_FLAGS))
    fila = con.execute(
        """
        SELECT count(*), sum(pop_total), sum(bld_count), sum(health_count),
               sum(edu_count), sum(road_km_primary+road_km_secondary+road_km_other),
               count(DISTINCT adm2_id),
               count(*) FILTER (WHERE flags_calidad IS NOT NULL)
        FROM exposure_h3
        """
    ).fetchone()
    resumen = {
        "celdas": fila[0],
        "pop_total": fila[1] or 0.0,
        "bld_count": fila[2] or 0,
        "health_count": fila[3] or 0,
        "edu_count": fila[4] or 0,
        "road_km": fila[5] or 0.0,
        "municipios": fila[6],
        "celdas_marcadas": fila[7],
    }
    _log.info("activo ensamblado", extra={"context": {"iso3": iso3, **resumen}})
    return resumen


#: Capas opcionales. Si una no se construyo, entra vacia en vez de romper el
#: ensamblaje: es preferible un activo con una columna en cero y declarado asi,
#: que ningun activo.
LAYER_TABLES: dict[str, str] = {
    "pop_h3": "h3_08 UBIGINT, pop_total DOUBLE",
    "pop_0_14_h3": "h3_08 UBIGINT, pop_0_14 DOUBLE",
    "pop_65p_h3": "h3_08 UBIGINT, pop_65p DOUBLE",
    "pop_alt_h3": "h3_08 UBIGINT, pop_alt_worldpop DOUBLE",
    "bld_h3": "h3_08 UBIGINT, bld_count BIGINT, bld_area_m2 DOUBLE",
    "health_h3": "h3_08 UBIGINT, health_count BIGINT",
    "edu_h3": "h3_08 UBIGINT, edu_count BIGINT",
    "roads_h3": (
        "h3_08 UBIGINT, road_km_primary DOUBLE, road_km_secondary DOUBLE, road_km_other DOUBLE"
    ),
}


def ensure_layer_tables(con: Any) -> list[str]:
    """Crea vacias las tablas de capa que falten. Devuelve cuales falto crear."""
    existentes = {r[0] for r in con.execute("SELECT table_name FROM duckdb_tables()").fetchall()}
    creadas = []
    for tabla, esquema in LAYER_TABLES.items():
        if tabla not in existentes:
            con.execute(f"CREATE TABLE {tabla} ({esquema})")
            creadas.append(tabla)
    if creadas:
        _log.warning(
            "capas ausentes, se crean vacias",
            extra={"context": {"tablas": creadas}},
        )
    return creadas


def validate_national_total(
    con: Any, manifest: Manifest, *, referencia: dict[str, Any] | None
) -> list[str]:
    """Assert de §6.4: el total nacional dentro de la tolerancia del oficial."""
    if not referencia:
        return ["Sin referencia oficial en el manifest: no se puede validar el total (aviso)"]
    total: float = con.execute("SELECT sum(pop_total) FROM exposure_h3").fetchone()[0] or 0.0
    esperado = float(referencia["poblacion_2025"])
    tolerancia = float(referencia.get("tolerancia_pct", 1.0))
    desvio = 100.0 * (total - esperado) / esperado
    if abs(desvio) > tolerancia:
        return [
            f"Total nacional {total:,.0f} se desvia {desvio:+.2f}% de la referencia "
            f"{esperado:,.0f} ({manifest.iso3}); tolerancia {tolerancia}%"
        ]
    _log.info(
        "total nacional dentro de tolerancia",
        extra={"context": {"total": total, "referencia": esperado, "desvio_pct": desvio}},
    )
    return []


def write_asset(con: Any, plan: BuildPlan) -> Path:
    """Escribe el activo como GeoParquet particionado Hive."""
    plan.salida.mkdir(parents=True, exist_ok=True)
    destino = plan.salida / "exposure_h3.parquet"
    con.execute(f"COPY exposure_h3 TO '{destino}' (FORMAT PARQUET, COMPRESSION ZSTD)")
    _log.info(
        "activo escrito",
        extra={"context": {"ruta": str(destino), "bytes": destino.stat().st_size}},
    )
    return destino


#: Como se agrega cada capa. La clave es la tabla que produce; el valor dice de
#: donde sale. Separarlo del codigo hace que agregar una capa en Fase 1 sea
#: anadir una entrada, no tocar el orquestador.
RASTER_LAYERS: dict[str, tuple[str, str]] = {
    "pop_h3": ("pop_ghs", "pop_total"),
    "pop_alt_h3": ("pop_worldpop_total", "pop_alt_worldpop"),
}
POINT_LAYERS: dict[str, tuple[str, str]] = {
    "health_h3": ("health", "health_count"),
    "edu_h3": ("education", "edu_count"),
}


def build_country(
    iso3: str,
    *,
    manifests_dir: Path | None = None,
    out_dir: Path,
    con: Any | None = None,
) -> Path:
    """Construye el activo completo de un pais, de la descarga al parquet.

    Es el comando que sostiene O4: cualquiera reconstruye el activo de un pais
    desde fuentes publicas, sin credenciales. Los pasos son descarga guiada por
    manifest, crosswalk, agregacion por capa, ensamblaje, asserts de calidad y
    escritura.

    El paso pesado no es el computo sino la descarga, y ahi esta el trabajo
    real de este pipeline: ``sources/`` sabe pedir 93 MB de GHS-POP en vez de
    5,25 GB, once ficheros de Overture en vez de 512, y 100 MB del ZIP de 3,39
    GB del DANE.
    """
    from ..common.http import HttpFetcher
    from .crosswalk import build_crosswalk, load_admin_geometry, rescue_unassigned
    from .download import download_manifest
    from .raster_h3 import aggregate_rasters_to_h3
    from .vector_h3 import aggregate_points_to_h3

    plan = plan_build(iso3, manifests_dir=manifests_dir, out_dir=out_dir)
    trabajo = out_dir / "descargas" / plan.iso3
    fetcher = HttpFetcher(timeout_s=600.0)

    inventario = download_manifest(plan.manifest, trabajo, fetcher=fetcher)
    por_capa: dict[str, list[Path]] = {}
    for item in inventario:
        por_capa.setdefault(item.layer, []).append(item.path)
    _log.info(
        "descarga completa",
        extra={
            "context": {
                "iso3": plan.iso3,
                "archivos": len(inventario),
                "bytes": sum(i.bytes for i in inventario),
            }
        },
    )

    from ..p2_impact.exposure_join import connect
    from .crosswalk import EXTENSIONS  # noqa: F401  (documenta el requisito)

    conexion = con if con is not None else connect()

    shapefiles = [p for p in por_capa.get("divisions", []) if p.suffix == ".shp"]
    if not shapefiles:
        raise ValueError(
            f"El manifest de {plan.iso3} no aporto geometria administrativa. "
            f"Sin municipios no hay crosswalk, y sin crosswalk no hay activo."
        )
    load_admin_geometry(conexion, shapefiles[0], iso3=plan.iso3)
    build_crosswalk(conexion, iso3=plan.iso3)

    for tabla, (capa, columna) in RASTER_LAYERS.items():
        rasters = [p for p in por_capa.get(capa, []) if p.suffix in (".tif", ".tiff")]
        if rasters:
            aggregate_rasters_to_h3(conexion, rasters, tabla=tabla, columna=columna)

    for tabla, (capa, columna) in POINT_LAYERS.items():
        fuentes = [str(p) for p in por_capa.get(capa, [])]
        if fuentes:
            aggregate_points_to_h3(conexion, fuentes, tabla=tabla, columna=columna)

    # El rescate de costa necesita saber que celdas tienen dato, asi que va
    # despues de la poblacion y antes del ensamblaje.
    ensure_layer_tables(conexion)
    rescue_unassigned(conexion, tabla_datos="pop_h3")

    resumen = assemble_exposure(conexion, iso3=plan.iso3, manifest_id=plan.manifest.manifest_id)
    referencia = getattr(plan.manifest, "referencia_oficial", None)
    problemas = [
        p
        for p in validate_national_total(conexion, plan.manifest, referencia=referencia)
        if "(aviso)" not in p
    ]
    if problemas:
        raise ValueError(
            "El activo no pasa los asserts de calidad:\n  - " + "\n  - ".join(problemas)
        )

    destino = write_asset(conexion, plan)
    conexion.execute(
        f"COPY admin_lookup TO '{plan.salida / 'admin_lookup.parquet'}' (FORMAT PARQUET)"
    )
    _log.info("activo construido", extra={"context": {"iso3": plan.iso3, **resumen}})
    return destino
