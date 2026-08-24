"""Construccion del activo ``exposure_h3`` de un pais (O4, RF-08).

Punto de entrada de ``make country ISO=COL``. El pipeline es
descarga -> agregacion por capa -> join -> asserts de calidad -> parquet
particionado, y todo el linaje queda registrado en el manifest.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..common.geo import BBox
from ..common.http import Fetcher
from ..common.logging import get_logger
from ..common.manifest import Manifest, lint_manifest
from .download import ISO3_A_ISO2
from .layers import LAYERS, LayerSpec, required_layers

_log = get_logger(__name__)

#: Release de Overture usado cuando no se pasa uno explicito. Los manifests
#: fijan el suyo; esto solo cubre la llamada suelta.
OVERTURE_RELEASE_POR_DEFECTO = "2026-08-19.0"


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
#:
#: **"Sin nada" tiene que significar sin nada de las nueve capas.** El filtro
#: miraba solo poblacion, edificaciones y vias, asi que una celda cuyo unico
#: contenido fuera una escuela o un hospital se descartaba con el equipamiento
#: dentro. Se detecto comparando dos corridas: al dejar de contar los senderos
#: como via, 28 sedes educativas desaparecieron del activo — estaban en celdas
#: que solo se salvaban por un sendero. Una escuela remota, sin poblacion
#: censada alrededor y sin via mapeada, es justo el sitio que un reporte de
#: exposicion no puede permitirse perder.
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
    COALESCE(s.built_m2, 0.0)                         AS built_m2,
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
LEFT JOIN built_h3      s USING (h3_08)
LEFT JOIN health_h3     h USING (h3_08)
LEFT JOIN edu_h3        e USING (h3_08)
LEFT JOIN roads_h3      r USING (h3_08)
WHERE COALESCE(p.pop_total, 0) > 0
   OR COALESCE(b.bld_count, 0) > 0
   OR COALESCE(r.road_km_primary, 0) + COALESCE(r.road_km_secondary, 0)
      + COALESCE(r.road_km_other, 0) > 0
   OR COALESCE(h.health_count, 0) > 0
   OR COALESCE(e.edu_count, 0) > 0
   OR COALESCE(s.built_m2, 0) > 0
"""

#: Banderas de calidad de §6.4. Se **publican**, no se ocultan: una celda con
#: gente y sin edificios registrados suele ser asentamiento informal mal
#: mapeado, y esconderlo seria fingir una cobertura que no existe.
SQL_FLAGS = """
    NULLIF(
        CONCAT_WS(',',
            CASE WHEN COALESCE(b.bld_count,0)=0 AND COALESCE(p.pop_total,0)>500
                 THEN 'revisar_sin_edificios' END,
            CASE WHEN COALESCE(b.bld_count,0)=0 AND COALESCE(s.built_m2,0)>1000
                 THEN 'construido_no_mapeado' END,
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
               sum(built_m2),
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
        "built_m2": fila[4] or 0.0,
        "edu_count": fila[5] or 0,
        "road_km": fila[6] or 0.0,
        "municipios": fila[7],
        "celdas_marcadas": fila[8],
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
    "built_h3": "h3_08 UBIGINT, built_m2 DOUBLE",
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


#: Capas que tienen que llegar al activo con algo dentro. El par es
#: (expresion SQL, nombre legible, capa del manifest).
#:
#: Existe por un fallo real: ``ensure_layer_tables`` crea vacia la tabla de una
#: capa que no se construyo, el LEFT JOIN la convierte en ceros y el activo se
#: escribe sin que nada falle. El assert de total nacional no lo ve porque solo
#: mira poblacion. El resultado seria un reporte que dice "0 edificaciones en
#: MMI>=7" con la misma cara de seriedad que una cifra real — exactamente el
#: cero silencioso que este proyecto promete no publicar nunca.
REQUIRED_COVERAGE: tuple[tuple[str, str, str], ...] = (
    ("sum(pop_total)", "poblacion", "pop_ghs"),
    ("sum(pop_0_14)", "poblacion de 0 a 14", "pop_worldpop_agesex"),
    ("sum(pop_65p)", "poblacion de 65 o mas", "pop_worldpop_agesex"),
    ("sum(pop_alt_worldpop)", "poblacion de contraste", "pop_worldpop_total"),
    ("sum(bld_count)", "edificaciones", "buildings"),
    ("sum(built_m2)", "superficie construida", "built_ghsl"),
    (
        "sum(road_km_primary + road_km_secondary + road_km_other)",
        "kilometros de via",
        "roads",
    ),
    ("sum(health_count)", "sedes de salud", "health"),
    ("sum(edu_count)", "sedes educativas", "education"),
)


def validate_layer_coverage(con: Any) -> list[str]:
    """Assert de §6.4: ninguna capa requerida puede quedar entera en cero.

    Una capa vacia es indistinguible de una capa cuyo pais no tiene el dato, y
    esa ambiguedad se resuelve fallando: es preferible no publicar activo a
    publicar uno que informa cero donde no midio nada.
    """
    import math

    columnas = ", ".join(expresion for expresion, _, _ in REQUIRED_COVERAGE)
    fila = con.execute(f"SELECT {columnas} FROM exposure_h3").fetchone()

    problemas: list[str] = []
    for (_, nombre, capa), valor in zip(REQUIRED_COVERAGE, fila, strict=True):
        numero = float(valor) if valor is not None else 0.0
        if not math.isfinite(numero):
            # `bool(float('nan'))` es True, asi que una comprobacion de
            # veracidad deja pasar un NaN. Ecuador publico un activo con
            # `road_km: NaN` justo por eso: la capa "aportaba" y la cifra era
            # basura. Un NaN es peor que un cero — se propaga a todo lo que
            # toca y el reporte publicaria "NaN km de via".
            problemas.append(
                f"La capa '{capa}' produjo un valor no finito: {nombre} = {numero}. "
                f"Casi siempre viene de una geometria degenerada; un NaN se propaga "
                f"y acabaria impreso en el reporte."
            )
        elif numero == 0.0:
            problemas.append(
                f"La capa '{capa}' no aporto nada al activo: {nombre} suma 0. "
                f"Se construyo vacia o no se construyo."
            )
    if not problemas:
        _log.info(
            "todas las capas requeridas aportan al activo",
            extra={"context": {"capas": len(REQUIRED_COVERAGE)}},
        )
    return problemas


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
    "built_h3": ("built_ghsl", "built_m2"),
}
POINT_LAYERS: dict[str, tuple[str, str]] = {
    "health_h3": ("health", "health_count"),
    "edu_h3": ("education", "edu_count"),
}


#: Capa del manifest que trae los rasters de estructura etaria.
AGESEX_LAYER = "pop_worldpop_agesex"

#: Marcas que delatan el nivel municipal dentro de una entrega administrativa.
#: El COD-AB de OCHA viene en un solo ZIP con los cuatro niveles mas lineas y
#: puntos; tomar el primero que aparezca daria el pais entero como un municipio.
ADM2_HINTS: tuple[str, ...] = ("admin2", "adm2", "mpio", "municip")

#: Sufijos de copias del mismo nivel. El COD-AB de El Salvador publica
#: ``slv_admin2.geojson`` y ``slv_admin2_em.geojson``: medidos, **los dos traen
#: los mismos 48 registros y las mismas columnas**. Ante el empate se toma el
#: nombre sin decorar como canonico, en vez de detener el build por una copia.
#: Si algun dia una variante trae datos distintos, seguira sin distinguirse por
#: el nombre — pero el pais tendra que declararlo en el manifest.
ADM2_VARIANT_SUFFIXES: tuple[str, ...] = ("_em",)


def pick_admin_source(rutas: list[Path], *, iso3: str = "", con: Any | None = None) -> Path:
    """Elige el archivo de geometria municipal entre los de la capa divisions.

    Dos filtros, en orden, porque uno solo no basta:

    1. **Por nombre.** El COD-AB llega en un ZIP con los cuatro niveles mas
       lineas y puntos; tomar el primero daria el pais entero como un municipio.
    2. **Por columnas**, si sigue habiendo empate y hay conexion. Colombia
       declara dos fuentes municipales —el MGN del DANE y el adm2 del COD-AB— y
       la que manda es la que trae las columnas que el pais declara en
       :data:`~pipelines.p0_exposure.crosswalk.ADMIN_COLUMNS`. Para Colombia esa
       es el MGN, que es la fuente de verdad del codigo DIVIPOLA.

    Raises:
        ValueError: si no hay geometria, o si el empate no se puede deshacer.
            Adivinar aqui produce un crosswalk con el numero de municipios
            equivocado y todo lo demas cuadra igual.
    """
    from .crosswalk import admin_columns
    from .download import GEOMETRY_SUFFIXES

    candidatas = [p for p in rutas if p.suffix.lower() in GEOMETRY_SUFFIXES]
    if not candidatas:
        raise ValueError(
            "El manifest no aporto geometria administrativa. Sin municipios no "
            "hay crosswalk, y sin crosswalk no hay activo."
        )

    municipales = [p for p in candidatas if any(h in p.name.lower() for h in ADM2_HINTS)]
    if len(municipales) > 1:
        # Descartar copias del mismo nivel antes de dar el empate por irresoluble.
        sin_variantes = [
            p
            for p in municipales
            if not any(p.stem.lower().endswith(s) for s in ADM2_VARIANT_SUFFIXES)
        ]
        if len(sin_variantes) == 1:
            _log.info(
                "capa municipal elegida descartando copias",
                extra={
                    "context": {
                        "elegida": sin_variantes[0].name,
                        "copias": [p.name for p in municipales if p != sin_variantes[0]],
                    }
                },
            )
            return sin_variantes[0]
        municipales = sin_variantes or municipales
    if len(municipales) == 1:
        return municipales[0]
    if not municipales and len(candidatas) == 1:
        return candidatas[0]

    if len(municipales) > 1 and con is not None and iso3:
        from .crosswalk import match_columns

        variantes = admin_columns(iso3)
        coinciden = [
            p for p in municipales if match_columns(variantes, _columnas_de(con, p)) is not None
        ]
        if len(coinciden) == 1:
            _log.info(
                "capa municipal elegida por columnas declaradas",
                extra={
                    "context": {
                        "iso3": iso3,
                        "elegida": coinciden[0].name,
                        "descartadas": [p.name for p in municipales if p != coinciden[0]],
                    }
                },
            )
            return coinciden[0]
        municipales = coinciden or municipales

    raise ValueError(
        f"No se puede elegir la capa municipal entre {[p.name for p in candidatas]}. "
        f"Coincidencias con {ADM2_HINTS}: {[p.name for p in municipales]}. "
        f"Declara el mapeo del pais en ADMIN_COLUMNS o acota la fuente en el manifest."
    )


def validate_bbox_covers_country(con: Any, bbox: BBox, *, iso3: str) -> list[str]:
    """La caja declarada tiene que contener la geometria administrativa real.

    La caja se declara **antes** de descargar nada, asi que no puede derivarse
    del limite del pais: es el unico dato del pipeline que empieza siendo una
    afirmacion. Una caja corta no falla — recorta teselas de GHS-POP y ficheros
    de Overture, y el activo sale con una punta del pais sin poblacion ni
    edificaciones. Cuadra todo y falta territorio.

    Aqui, con el limite ya cargado, la afirmacion se puede comprobar.
    """
    fila = con.execute(
        "SELECT min(ST_XMin(geom)), min(ST_YMin(geom)), "
        "max(ST_XMax(geom)), max(ST_YMax(geom)) FROM admin_geom"
    ).fetchone()
    if fila is None or fila[0] is None:
        return [f"admin_geom vacia para {iso3}: no se puede validar la caja (aviso)"]

    xmin, ymin, xmax, ymax = (float(v) for v in fila)
    fuera = []
    if xmin < bbox.lon_min:
        fuera.append(f"oeste: el pais llega a {xmin:.4f} y la caja a {bbox.lon_min}")
    if ymin < bbox.lat_min:
        fuera.append(f"sur: el pais llega a {ymin:.4f} y la caja a {bbox.lat_min}")
    if xmax > bbox.lon_max:
        fuera.append(f"este: el pais llega a {xmax:.4f} y la caja a {bbox.lon_max}")
    if ymax > bbox.lat_max:
        fuera.append(f"norte: el pais llega a {ymax:.4f} y la caja a {bbox.lat_max}")

    if fuera:
        return [
            f"COUNTRY_BBOX['{iso3}'] no cubre el pais y se perderia territorio "
            f"en silencio — " + "; ".join(fuera)
        ]
    _log.info(
        "la caja declarada cubre el pais",
        extra={
            "context": {
                "iso3": iso3,
                "pais": [round(xmin, 4), round(ymin, 4), round(xmax, 4), round(ymax, 4)],
                "caja": list(bbox.as_tuple()),
            }
        },
    )
    return []


def _columnas_de(con: Any, ruta: Path) -> set[str]:
    """Columnas de una capa vectorial, en minusculas. Vacio si no se abre."""
    try:
        filas = con.execute(f"DESCRIBE SELECT * FROM ST_Read('{ruta.as_posix()}')").fetchall()
    except Exception:  # una capa ilegible no puede tumbar la eleccion
        return set()
    return {str(f[0]).lower() for f in filas}


def age_rasters_by_column(rutas: list[Path]) -> dict[str, list[Path]]:
    """Reparte los GeoTIFF descargados de WorldPop entre las columnas etarias.

    La clasificacion vive en ``sources/worldpop.py`` y trabaja sobre nombres:
    aqui solo se traduce de nombre a ruta.
    """
    from .sources.worldpop import select_age_rasters

    por_nombre = {ruta.name: ruta for ruta in rutas}
    return {
        columna: [por_nombre[nombre] for nombre in nombres]
        for columna, nombres in select_age_rasters(list(por_nombre)).items()
    }


def load_country_neighbours(
    con: Any,
    iso3: str,
    *,
    bbox: BBox,
    fetcher: Fetcher,
    release: str = "",
) -> int:
    """Carga los paises limitrofes para que el rescate no invada al vecino.

    El rescate asigna municipio a las celdas con poblacion que caen fuera del
    pais. Sin saber donde empieza el vecino, "fuera del pais y cerca" incluye el
    otro lado de la frontera: medido, Paraguay se llevaba 459.518 personas de
    Brasil, Argentina y Bolivia — el 93 % de su desvio frente a la ONU.

    No sustituye al rescate: Chile rescata el 31 % de su poblacion y esta bien,
    porque su rescate es mar. Lo que acota es **de donde** puede rescatar.

    Si Overture no responde se sigue sin vecinos, con el comportamiento anterior:
    para una isla es correcto y para un pais con frontera terrestre, generoso.
    Un fallo aqui no puede tumbar un build de casi una hora.
    """
    from .overture_h3 import load_neighbours
    from .sources.overture import THEME_DIVISIONS, resolve_data_urls, select_files

    iso2 = ISO3_A_ISO2.get(iso3.upper(), "")
    if not iso2:
        _log.warning(
            "sin ISO2 declarado: el rescate no podra distinguir mar de pais vecino",
            extra={"context": {"iso3": iso3}},
        )
        return 0
    try:
        ficheros = select_files(
            fetcher,
            bbox,
            release=release or OVERTURE_RELEASE_POR_DEFECTO,
            theme=THEME_DIVISIONS[0],
            type_=THEME_DIVISIONS[1],
        )
        return load_neighbours(
            con, resolve_data_urls(fetcher, ficheros), bbox=bbox, iso2_propio=iso2
        )
    except Exception as exc:  # el rescate degrada, no se cae
        _log.warning(
            "no se pudieron cargar los paises vecinos; el rescate sera mas generoso",
            extra={"context": {"iso3": iso3, "error": str(exc)}},
        )
        return 0


def build_overture_layers(
    con: Any,
    manifest: Manifest,
    *,
    bbox: BBox,
    fetcher: Fetcher,
) -> None:
    """Agrega edificaciones y vias leyendo los parquet de Overture en remoto.

    El release sale del ``vintage`` que fija el manifest, nunca de ``latest``:
    el catalogo STAC tiene un alias al ultimo release y seguirlo haria que un
    reporte de hace seis meses dejara de ser reproducible (RNF-04).

    Cada tema se resuelve contra **su propio** catalogo. Los ficheros de
    ``buildings`` y los de ``transportation`` no cubren las mismas areas aunque
    compartan numero, asi que reutilizar una seleccion para el otro tema leeria
    los ficheros equivocados.
    """
    from .overture_h3 import aggregate_buildings_to_h3, aggregate_roads_to_h3
    from .sources.overture import (
        THEME_BUILDINGS,
        THEME_TRANSPORTATION,
        resolve_data_urls,
        select_files,
    )

    def urls_de(capa: str, tema: tuple[str, str]) -> list[str]:
        fuentes = manifest.by_layer(capa)
        if not fuentes:
            raise ValueError(f"El manifest {manifest.iso3} no declara la capa {capa!r}")
        release = fuentes[0].vintage
        ficheros = select_files(fetcher, bbox, release=release, theme=tema[0], type_=tema[1])
        if not ficheros:
            raise ValueError(
                f"Ningun fichero de {tema[0]} del release {release} toca la caja de "
                f"{manifest.iso3}. Revisa COUNTRY_BBOX antes de seguir: un activo sin "
                f"esta capa se escribiria en ceros."
            )
        _log.info(
            "ficheros de Overture seleccionados",
            extra={"context": {"tema": tema[0], "release": release, "ficheros": len(ficheros)}},
        )
        return resolve_data_urls(fetcher, ficheros)

    aggregate_buildings_to_h3(con, urls_de("buildings", THEME_BUILDINGS), bbox=bbox)
    aggregate_roads_to_h3(con, urls_de("roads", THEME_TRANSPORTATION), bbox=bbox)


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
    from .download import COUNTRY_BBOX, download_manifest
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

    load_admin_geometry(
        conexion,
        pick_admin_source(por_capa.get("divisions", []), iso3=plan.iso3, con=conexion),
        iso3=plan.iso3,
    )
    caja = COUNTRY_BBOX[plan.iso3]
    if fallos := validate_bbox_covers_country(conexion, caja, iso3=plan.iso3):
        raise ValueError("\n  - ".join(["La caja del pais no sirve:", *fallos]))
    build_crosswalk(conexion, iso3=plan.iso3)

    for tabla, (capa, columna) in RASTER_LAYERS.items():
        rasters = [p for p in por_capa.get(capa, []) if p.suffix in (".tif", ".tiff")]
        if rasters:
            aggregate_rasters_to_h3(conexion, rasters, tabla=tabla, columna=columna)

    for tabla, (capa, columna) in POINT_LAYERS.items():
        fuentes = [str(p) for p in por_capa.get(capa, [])]
        if fuentes:
            aggregate_points_to_h3(conexion, fuentes, tabla=tabla, columna=columna)

    for columna, rutas in age_rasters_by_column(por_capa.get(AGESEX_LAYER, [])).items():
        aggregate_rasters_to_h3(conexion, rutas, tabla=f"{columna}_h3", columna=columna)

    # Overture no pasa por disco: son 277 GB de los que Colombia usa once
    # ficheros, y DuckDB los lee por HTTPS podando por la columna `bbox`.
    build_overture_layers(conexion, plan.manifest, bbox=caja, fetcher=fetcher)

    # El rescate de costa necesita saber que celdas tienen dato, asi que va
    # despues de la poblacion y antes del ensamblaje.
    ensure_layer_tables(conexion)
    load_country_neighbours(conexion, plan.iso3, bbox=caja, fetcher=fetcher)
    rescue_unassigned(conexion, tabla_datos="pop_h3")

    resumen = assemble_exposure(conexion, iso3=plan.iso3, manifest_id=plan.manifest.manifest_id)
    referencia = getattr(plan.manifest, "referencia_oficial", None)
    problemas = [
        p
        for p in (
            *validate_national_total(conexion, plan.manifest, referencia=referencia),
            *validate_layer_coverage(conexion),
        )
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
