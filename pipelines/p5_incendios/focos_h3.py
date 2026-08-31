"""De detecciones sueltas a celdas H3, y de ahi al cruce con la exposicion.

66.806 detecciones en 24 h se convierten en 22.701 celdas r8. Ese colapso es lo
que hace viable todo el pipeline: 22.701 celdas es nada frente a los 4,5
millones del activo de Brasil, y el cruce es un `JOIN ... USING (h3_08)` que
DuckDB resuelve sin despeinarse.

Es tambien lo que disuelve el problema de volumen que parecia bloquear el
diseno. La unidad correcta no es la deteccion: es la celda, que es la unidad en
la que este sistema ya sabe medir exposicion.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pyarrow as pa

from ..common.constants import H3_RES_COMPUTE
from ..common.logging import get_logger
from .firms import Foco

_log = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class CeldaConFuego:
    """Lo que un satelite vio sobre una celda, y lo que hay debajo."""

    h3: str
    detecciones: int
    detecciones_baja: int
    frp_max: float
    frp_suma: float
    primera_utc: str
    ultima_utc: str
    #: Pais de la celda, del activo. Cadena vacia si cae fuera de los activos
    #: cargados — el fuego no respeta fronteras y una corrida regional siempre
    #: tiene celdas de paises sin activo. "No se sabe" no es lo mismo que un
    #: ISO3, y por eso no es None ni un pais por defecto.
    iso3: str = ""
    #: Exposicion de la celda, del activo del pais. Cero si no hay activo.
    pop: float = 0.0
    bld: int = 0
    salud: int = 0
    edu: int = 0
    vias_km: float = 0.0
    #: Cobertura del suelo, en porcentaje de la celda.
    arbolado_pct: float = 0.0
    pastizal_pct: float = 0.0
    cultivo_pct: float = 0.0
    humedal_pct: float = 0.0


#: Agrupa las detecciones por celda. La confianza baja se cuenta aparte en vez
#: de descartarse: publicar lo que se descarta es regla del proyecto desde que
#: un M4,9 sentido en media Colombia solo existia en un log de CI.
SQL_CELDAS = """
CREATE OR REPLACE TABLE focos_h3 AS
SELECT h3_latlng_to_cell(lat, lon, {resolucion})              AS h3_08,
       count(*) FILTER (WHERE confianza <> 'low')             AS detecciones,
       count(*) FILTER (WHERE confianza =  'low')             AS detecciones_baja,
       max(frp)                                               AS frp_max,
       round(sum(frp), 1)                                     AS frp_suma,
       min(adquirido_utc)                                     AS primera_utc,
       max(adquirido_utc)                                     AS ultima_utc
FROM focos_arrow
GROUP BY 1
HAVING count(*) FILTER (WHERE confianza <> 'low') > 0
"""

#: Cruce con el activo. `LEFT JOIN`: una celda con fuego y sin exposicion sigue
#: siendo informacion —un incendio en selva sin nadie importa— y perderla por
#: no tener poblacion seria confundir "no hay nadie" con "no hay fuego".
SQL_CRUCE = """
SELECT f.*,
       -- El pais de la celda. El activo lo sabe y no se publicaba, asi que el
       -- visor no podia filtrar el fuego por pais como si filtra los sismos.
       -- Cadena vacia y no NULL cuando la celda cae fuera de los activos
       -- cargados: "no se sabe" tiene que poder distinguirse de un ISO3.
       COALESCE(e.iso3, '')                 AS iso3,
       COALESCE(e.pop_total, 0.0)           AS pop,
       COALESCE(e.bld_count, 0)             AS bld,
       COALESCE(e.health_count, 0)          AS salud,
       COALESCE(e.edu_count, 0)             AS edu,
       COALESCE(e.road_km_primary, 0.0)
       + COALESCE(e.road_km_secondary, 0.0)
       + COALESCE(e.road_km_other, 0.0)     AS vias_km,
       COALESCE(e.lulc_arbolado_pct, 0.0)   AS arbolado_pct,
       COALESCE(e.lulc_pastizal_pct, 0.0)   AS pastizal_pct,
       COALESCE(e.lulc_cultivo_pct, 0.0)    AS cultivo_pct,
       COALESCE(e.lulc_humedal_pct, 0.0)    AS humedal_pct
FROM focos_h3 f
LEFT JOIN exposure e USING (h3_08)
ORDER BY f.frp_suma DESC
"""


def registrar_focos(con: Any, focos: list[Foco], *, resolucion: int = H3_RES_COMPUTE) -> int:
    """Mete las detecciones en DuckDB y las agrupa por celda.

    Via Arrow y no `VALUES`: son decenas de miles de filas y el SQL generado
    seria de megabytes. Mismo motivo que en `exposure_join.register_cells`.
    """
    con.register(
        "focos_arrow",
        pa.table(
            {
                "lon": pa.array([f.lon for f in focos], pa.float64()),
                "lat": pa.array([f.lat for f in focos], pa.float64()),
                "confianza": pa.array([f.confianza for f in focos], pa.string()),
                "frp": pa.array([f.frp for f in focos], pa.float64()),
                "adquirido_utc": pa.array([f.adquirido_utc for f in focos], pa.string()),
            }
        ),
    )
    con.execute(SQL_CELDAS.format(resolucion=resolucion))
    con.unregister("focos_arrow")

    celdas = int(con.execute("SELECT count(*) FROM focos_h3").fetchone()[0])
    _log.info(
        "detecciones agrupadas por celda",
        extra={"context": {"detecciones": len(focos), "celdas": celdas}},
    )
    return celdas


def cruzar_con_exposicion(con: Any) -> list[CeldaConFuego]:
    """Une las celdas con fuego con lo que el activo sabe de ellas.

    Si no hay activo registrado, la vista `exposure` no existe y el cruce
    devuelve las celdas con exposicion a cero. **Eso no es un fallo**: hay
    diecinueve activos y el fuego no respeta fronteras, asi que una corrida
    regional siempre tendra celdas de paises cuyo activo no esta cargado. Lo que
    seria un fallo es publicarlas como si valieran cero de verdad.
    """
    try:
        filas = con.execute(SQL_CRUCE).fetchall()
    except Exception:
        _log.warning("sin activo de exposicion registrado; se publica solo el fuego", extra={})
        filas = con.execute(
            "SELECT *, '', 0.0, 0, 0, 0, 0.0, 0.0, 0.0, 0.0, 0.0 "
            "FROM focos_h3 ORDER BY frp_suma DESC"
        ).fetchall()

    import h3

    return [
        CeldaConFuego(
            h3=h3.int_to_str(int(f[0])),
            detecciones=int(f[1]),
            detecciones_baja=int(f[2]),
            frp_max=round(float(f[3]), 1),
            frp_suma=round(float(f[4]), 1),
            primera_utc=str(f[5]),
            ultima_utc=str(f[6]),
            iso3=str(f[7] or ""),
            pop=round(float(f[8]), 1),
            bld=int(f[9]),
            salud=int(f[10]),
            edu=int(f[11]),
            vias_km=round(float(f[12]), 1),
            arbolado_pct=float(f[13]),
            pastizal_pct=float(f[14]),
            cultivo_pct=float(f[15]),
            humedal_pct=float(f[16]),
        )
        for f in filas
    ]
