"""Join intensidad x exposicion en DuckDB (D3).

DuckDB con las extensiones ``spatial`` y ``h3`` hace todo el trabajo pesado
dentro del runner de GitHub Actions, leyendo GeoParquet particionado
directamente. Sin servidor, sin credenciales, sin costo (RNF-01).

Las consultas viven aqui como constantes con marcadores nombrados, no armadas
por concatenacion: son parte del contrato revisable del sistema.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..common.constants import GROUND_FAILURE_HIGH_PROB

#: Extensiones que P0 y P2 requieren cargadas.
DUCKDB_EXTENSIONS: tuple[str, ...] = ("spatial", "h3")

#: Materializa ``impact_h3`` (§3.3): una fila por celda alcanzada, con TODAS
#: las columnas de exposicion copiadas al momento del corte. La copia es
#: deliberada: el reporte debe ser inmutable aunque el activo se reconstruya
#: manana.
SQL_IMPACT_H3 = """
CREATE OR REPLACE TABLE impact_h3 AS
SELECT
    $usgs_id            AS usgs_id,
    $shakemap_version   AS shakemap_version,
    e.h3_08,
    e.iso3, e.adm1_id, e.adm2_id,
    m.mmi_mean, m.mmi_max,
    COALESCE(g.ls_prob, 0.0) AS ls_prob,
    COALESCE(g.lq_prob, 0.0) AS lq_prob,
    e.pop_total, e.pop_0_14, e.pop_15_64, e.pop_65p, e.pop_alt_worldpop,
    e.bld_count, e.bld_area_m2, e.built_m2,
    e.health_count, e.edu_count,
    e.road_km_primary, e.road_km_secondary, e.road_km_other,
    e.src_manifest
FROM read_parquet($exposure_glob) AS e
JOIN mmi_cells AS m USING (h3_08)
LEFT JOIN gf_cells AS g USING (h3_08)
"""

#: Agrega a municipio (§3.3). Es la tabla que consume el mundo: prensa, salas
#: de crisis y ONG leen ``impact_adm2``, no las celdas.
SQL_IMPACT_ADM2 = """
CREATE OR REPLACE TABLE impact_adm2 AS
SELECT
    i.usgs_id,
    i.shakemap_version,
    i.adm2_id,
    a.nombre,
    MAX(i.mmi_max)                                              AS mmi_max,
    SUM(CASE WHEN i.mmi_max >= 6 THEN i.pop_total ELSE 0 END)   AS pop_mmi6p,
    SUM(CASE WHEN i.mmi_max >= 7 THEN i.pop_total ELSE 0 END)   AS pop_mmi7p,
    SUM(CASE WHEN i.mmi_max >= 8 THEN i.pop_total ELSE 0 END)   AS pop_mmi8p,
    SUM(CASE WHEN i.mmi_max >= 7 THEN i.pop_65p ELSE 0 END)     AS pop_65p_mmi7p,
    SUM(CASE WHEN i.mmi_max >= 7 THEN i.bld_count ELSE 0 END)   AS bld_mmi7p,
    SUM(CASE WHEN i.mmi_max >= 7 THEN i.built_m2 ELSE 0 END)    AS built_m2_mmi7p,
    SUM(CASE WHEN i.mmi_max >= 7 THEN i.health_count ELSE 0 END) AS health_mmi7p,
    SUM(CASE WHEN i.mmi_max >= 7 THEN i.edu_count ELSE 0 END)   AS edu_mmi7p,
    SUM(CASE WHEN i.mmi_max >= 7
             THEN i.road_km_primary + i.road_km_secondary + i.road_km_other
             ELSE 0 END)                                        AS road_km_mmi7p,
    SUM(CASE WHEN i.mmi_max >= 7
             THEN i.road_km_primary + i.road_km_secondary
             ELSE 0 END)                                        AS road_km_principal_mmi7p,
    SUM(CASE WHEN i.ls_prob >= $gf_high THEN i.pop_total ELSE 0 END) AS ls_pop_expuesta,
    SUM(CASE WHEN i.lq_prob >= $gf_high THEN i.pop_total ELSE 0 END) AS lq_pop_expuesta
FROM impact_h3 AS i
JOIN admin_lookup AS a USING (adm2_id)
GROUP BY ALL
ORDER BY pop_mmi7p DESC
"""

#: Asserts de calidad que corren en P0 y P2 (§6.4). Cada entrada es
#: (nombre, consulta que debe devolver 0 filas).
QUALITY_ASSERTIONS: tuple[tuple[str, str], ...] = (
    (
        "pop_negativa",
        "SELECT h3_08 FROM exposure_h3 WHERE pop_total < 0",
    ),
    (
        "pop_nula",
        "SELECT h3_08 FROM exposure_h3 WHERE pop_total IS NULL OR adm2_id IS NULL",
    ),
    (
        "crosswalk_incompleto",
        "SELECT adm2_id FROM impact_adm2 WHERE mmi_max >= 6 "
        "AND adm2_id NOT IN (SELECT adm2_id FROM admin_lookup)",
    ),
)

#: Condiciones que NO son error sino bandera publicada. La espec es explicita:
#: "se publica el flag, no se oculta" (§6.4).
QUALITY_FLAGS: tuple[tuple[str, str], ...] = (
    (
        "revisar_sin_edificios",
        "bld_count = 0 AND pop_total > 500",
    ),
    (
        # La version medible de la anterior: no "puede que falte mapeo" sino
        # "el satelite ve 1.000 m² construidos donde no hay ninguna
        # edificacion registrada".
        "construido_no_mapeado",
        "bld_count = 0 AND built_m2 > 1000",
    ),
    (
        "discrepancia_poblacional",
        "pop_alt_worldpop > 0 AND abs(pop_total - pop_alt_worldpop) "
        "/ nullif(pop_alt_worldpop, 0) > 2.0",
    ),
)


@dataclass(frozen=True, slots=True)
class JoinInputs:
    """Insumos del join de impacto."""

    usgs_id: str
    shakemap_version: int
    #: Ruta o glob del activo de exposicion (GeoParquet particionado).
    exposure_glob: str
    #: ``h3_08 -> MmiCell`` del polyfill de contornos.
    mmi_cells: dict[int, Any]
    #: ``h3_08 -> GroundFailureCell``. Vacio si el producto no existe (G3).
    gf_cells: dict[int, Any]


def connect(database: Path | None = None) -> Any:
    """Abre una conexion DuckDB con las extensiones cargadas.

    ``database=None`` abre en memoria, que es el modo normal: el estado
    persistente son los parquet, no un archivo de base de datos.
    """
    import duckdb  # import diferido: el trigger no debe pagar este costo

    con = duckdb.connect(str(database) if database else ":memory:")
    for extension in DUCKDB_EXTENSIONS:
        origen = " FROM community" if extension == "h3" else ""
        con.execute(f"INSTALL {extension}{origen}")
        con.execute(f"LOAD {extension}")
    return con


def register_cells(con: Any, inputs: JoinInputs) -> None:
    """Materializa las celdas de intensidad y de falla de terreno.

    Se pasan por Arrow y no por ``VALUES``: un ShakeMap de M7 alcanza cientos de
    miles de celdas, y armar esa sentencia como texto es lento y fragil.
    """
    import pyarrow as pa

    celdas = list(inputs.mmi_cells.values())
    con.register(
        "mmi_arrow",
        pa.table(
            {
                "h3_08": pa.array([c.h3_08 for c in celdas], pa.uint64()),
                "mmi_mean": pa.array([c.mmi_mean for c in celdas], pa.float64()),
                "mmi_max": pa.array([c.mmi_max for c in celdas], pa.float64()),
            }
        ),
    )
    con.execute("CREATE OR REPLACE TABLE mmi_cells AS SELECT * FROM mmi_arrow")
    con.unregister("mmi_arrow")

    gf = list(inputs.gf_cells.values())
    con.register(
        "gf_arrow",
        pa.table(
            {
                "h3_08": pa.array([c.h3_08 for c in gf], pa.uint64()),
                "ls_prob": pa.array([c.ls_prob for c in gf], pa.float64()),
                "lq_prob": pa.array([c.lq_prob for c in gf], pa.float64()),
            }
        ),
    )
    con.execute("CREATE OR REPLACE TABLE gf_cells AS SELECT * FROM gf_arrow")
    con.unregister("gf_arrow")


def run_join(inputs: JoinInputs, *, con: Any, gf_high: float = GROUND_FAILURE_HIGH_PROB) -> Any:
    """Ejecuta el join completo y devuelve la conexion con las tablas creadas.

    Deja materializadas ``impact_h3`` e ``impact_adm2``, y corre los asserts de
    calidad de §6.4 sobre el resultado.
    """
    register_cells(con, inputs)
    con.execute(
        SQL_IMPACT_H3,
        {
            "usgs_id": inputs.usgs_id,
            "shakemap_version": inputs.shakemap_version,
            "exposure_glob": inputs.exposure_glob,
        },
    )
    con.execute(SQL_IMPACT_ADM2, {"gf_high": gf_high})
    return con


def check_quality(con: Any, *, tabla_exposicion: str = "exposure_h3") -> list[str]:
    """Corre los asserts de §6.4. Devuelve la lista de fallos (vacia = limpio)."""
    fallos: list[str] = []
    for nombre, consulta in QUALITY_ASSERTIONS:
        try:
            filas = con.execute(consulta.replace("exposure_h3", tabla_exposicion)).fetchall()
        except Exception as exc:  # tabla ausente en una corrida parcial
            fallos.append(f"{nombre}: no se pudo evaluar ({exc})")
            continue
        if filas:
            fallos.append(f"{nombre}: {len(filas)} filas incumplen (ej. {filas[:3]})")
    return fallos
