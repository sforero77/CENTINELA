"""Crosswalk hex <-> division politico-administrativa (§3.2).

El problema: cada celda H3 r8 (~0,7 km²) tiene que saber a que municipio
pertenece, y ninguna persona puede perderse en el camino. La suma de poblacion
por municipio debe igualar la suma nacional — ese es el invariante que verifica
CI, y el que hace que un alcalde pueda confiar en la cifra de su municipio.

Estrategia, en dos pasos deliberadamente separados:

1. **Reparto por contencion.** ``h3_polygon_wkt_to_cells`` asigna a cada
   municipio las celdas cuyo *centro* cae dentro. Verificado sobre el MGN 2025:
   el reparto sale limpio, **sin una sola celda reclamada por dos municipios**.
   Eso hace que la mayoria de celdas tengan ``frac_area = 1.0`` y evita el coste
   de intersectar 1,5 millones de hexagonos.

2. **Rescate de la costa y la frontera.** El reparto por centro deja fuera las
   celdas cuyo centro cae en el mar o del otro lado de la linea, aunque
   contengan poblacion en su parte terrestre. Esas celdas existen: Colombia
   tiene 3.000 km de costa. Se les asigna el municipio mas cercano, y quedan
   marcadas para que el hecho sea auditable en vez de invisible.

La alternativa —intersectar cada hexagono con cada poligono municipal para
obtener fracciones exactas— es correcta pero cuesta ordenes de magnitud mas, y
su ganancia es marginal: a r8, una celda fronteriza aporta menos de 0,7 km² a un
municipio que mide miles. Se deja documentada como ``frac_area`` por si alguna
vez hace falta.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..common.constants import H3_RES_COMPUTE
from ..common.logging import get_logger

_log = get_logger(__name__)

#: Tolerancia relativa del invariante de suma (suma municipal vs nacional).
SUM_TOLERANCE = 1e-6

#: Extensiones DuckDB que necesita este modulo.
EXTENSIONS = ("spatial", "h3")


@dataclass(frozen=True, slots=True)
class CrosswalkRow:
    """Fraccion del area de una celda que cae en un municipio."""

    h3_08: int
    adm2_id: str
    frac_area: float


@dataclass(frozen=True, slots=True)
class AdminColumns:
    """Como se llaman en la fuente las cuatro columnas que el crosswalk usa."""

    adm2_id: str
    nombre: str
    adm1_id: str
    departamento: str


#: Esquema por defecto: el **COD-AB de OCHA**, que publica adm1/adm2 con la
#: misma forma para los 19 paises de LATAM. Es lo que evita pelear con veinte
#: geoportales nacionales para obtener lo mismo.
#:
#: Medido sobre ``ven_admin2.shp`` del COD-AB de Venezuela (336 municipios): los
#: nombres son minusculas y **no** son los ``ADM2_PCODE`` / ``ADM2_ES`` de la
#: documentacion antigua de HDX. El shapefile trunca a diez caracteres, que es
#: por lo que ``adm2_ref_name`` aparece como ``adm2_ref_n``.
COD_AB_COLUMNS = AdminColumns(
    adm2_id="adm2_pcode",
    nombre="adm2_name",
    adm1_id="adm1_pcode",
    departamento="adm1_name",
)

#: Excepciones por pais. Colombia usa el MGN del DANE y no el COD-AB, porque el
#: MGN es la fuente de verdad del codigo DIVIPOLA y del toponimo oficial.
ADMIN_COLUMNS: dict[str, AdminColumns] = {
    "COL": AdminColumns(
        adm2_id="mpio_cdpmp",
        nombre="mpio_cnmbr",
        adm1_id="dpto_ccdgo",
        departamento="dpto_cnmbr",
    ),
}


def admin_columns(iso3: str) -> AdminColumns:
    """Mapeo de columnas del pais; COD-AB si no hay excepcion declarada."""
    return ADMIN_COLUMNS.get(iso3.upper(), COD_AB_COLUMNS)


def validate_fractions(rows: Iterable[CrosswalkRow]) -> list[str]:
    """Verifica que las fracciones de cada celda sumen 1.

    Devuelve la lista de celdas problematicas. Una celda cuyas fracciones no
    suman 1 significa que parte de su poblacion se perderia o se contaria dos
    veces al prorratear: es un error de construccion, no un aviso.
    """
    totals: dict[int, float] = {}
    for row in rows:
        if not 0.0 <= row.frac_area <= 1.0:
            return [f"h3={row.h3_08} adm2={row.adm2_id}: frac_area fuera de [0,1]"]
        totals[row.h3_08] = totals.get(row.h3_08, 0.0) + row.frac_area

    return [
        f"h3={h3}: las fracciones suman {total:.9f}, no 1"
        for h3, total in sorted(totals.items())
        if abs(total - 1.0) > SUM_TOLERANCE
    ]


def prorate(value: float, rows: Iterable[CrosswalkRow]) -> dict[str, float]:
    """Reparte el valor de una celda entre municipios segun ``frac_area``."""
    return {row.adm2_id: value * row.frac_area for row in rows}


# --- SQL del reparto -------------------------------------------------------

#: Paso 1: cada municipio reclama las celdas cuyo centro contiene.
SQL_POLYFILL = """
CREATE OR REPLACE TABLE crosswalk_h3_adm AS
SELECT
    unnest(h3_polygon_wkt_to_cells(ST_AsText(geom), {resolution})) AS h3_08,
    adm2_id,
    1.0 AS frac_area,
    FALSE AS rescatada
FROM admin_geom
"""

#: Diccionario administrativo que consume el reporte (§3.2).
SQL_ADMIN_LOOKUP = """
CREATE OR REPLACE TABLE admin_lookup AS
SELECT
    adm2_id,
    nombre,
    adm1_id,
    departamento,
    '{iso3}' AS iso3,
    ST_AsText(ST_Centroid(geom)) AS centroide
FROM admin_geom
"""

#: Guardia del paso 1: ninguna celda puede pertenecer a dos municipios.
SQL_ASSERT_SIN_DUPLICADOS = """
SELECT h3_08, count(*) AS n
FROM crosswalk_h3_adm
GROUP BY h3_08 HAVING count(*) > 1
"""


def load_admin_geometry(
    con: Any, fuente: Path, *, iso3: str, columnas: AdminColumns | None = None
) -> int:
    """Carga los poligonos municipales en la tabla ``admin_geom``.

    ``fuente`` es cualquier cosa que ``ST_Read`` sepa abrir: shapefile,
    GeoPackage o GeoJSON. El mapeo de columnas sale de :func:`admin_columns`,
    que por defecto asume COD-AB; un pais con fuente nacional propia declara su
    excepcion en :data:`ADMIN_COLUMNS` y no toca nada mas.

    Raises:
        ValueError: si la fuente no trae alguna de las cuatro columnas. Fallar
            aqui es barato; descubrirlo despues de agregar nueve capas no.
    """
    mapeo = columnas or admin_columns(iso3)
    ruta = fuente.as_posix()
    disponibles = {
        str(fila[0]).lower()
        for fila in con.execute(f"DESCRIBE SELECT * FROM ST_Read('{ruta}')").fetchall()
    }
    faltan = [
        col
        for col in (mapeo.adm2_id, mapeo.nombre, mapeo.adm1_id, mapeo.departamento)
        if col.lower() not in disponibles
    ]
    if faltan:
        raise ValueError(
            f"{fuente.name} no trae las columnas {faltan} que {iso3} necesita. "
            f"Tiene: {sorted(disponibles)}. Declara el mapeo del pais en "
            f"pipelines/p0_exposure/crosswalk.py::ADMIN_COLUMNS."
        )

    con.execute(
        f"""
        CREATE OR REPLACE TABLE admin_geom AS
        SELECT
            {mapeo.adm2_id}      AS adm2_id,
            {mapeo.nombre}       AS nombre,
            {mapeo.adm1_id}      AS adm1_id,
            {mapeo.departamento} AS departamento,
            geom
        FROM ST_Read('{ruta}')
        """
    )
    n: int = con.execute("SELECT count(*) FROM admin_geom").fetchone()[0]
    _log.info(
        "geometria administrativa cargada",
        extra={"context": {"iso3": iso3, "municipios": n, "fuente": str(fuente)}},
    )
    return n


def build_crosswalk(
    con: Any,
    *,
    iso3: str,
    resolution: int = H3_RES_COMPUTE,
) -> int:
    """Construye ``crosswalk_h3_adm`` y ``admin_lookup`` sobre ``admin_geom``.

    Returns:
        Numero de celdas repartidas.

    Raises:
        ValueError: si alguna celda queda reclamada por dos municipios. Seria
            doble conteo de poblacion, y es preferible fallar el build.
    """
    con.execute(SQL_POLYFILL.format(resolution=resolution))
    con.execute(SQL_ADMIN_LOOKUP.format(iso3=iso3))

    duplicadas = con.execute(SQL_ASSERT_SIN_DUPLICADOS).fetchall()
    if duplicadas:
        raise ValueError(
            f"{len(duplicadas)} celdas reclamadas por mas de un municipio: "
            f"seria doble conteo. Ejemplos: {duplicadas[:5]}"
        )

    celdas: int = con.execute("SELECT count(*) FROM crosswalk_h3_adm").fetchone()[0]
    _log.info(
        "crosswalk construido",
        extra={"context": {"iso3": iso3, "celdas": celdas, "resolucion": resolution}},
    )
    return celdas


#: Distancia maxima, en grados, a la que una celda sin asignar puede seguir
#: siendo del pais. ~0,02 grados son unos 2,2 km en el ecuador: mas que
#: suficiente para una celda r8 (~0,7 km²) partida por la linea de costa, y muy
#: poco para alcanzar el pais vecino.
RESCUE_MAX_DEGREES = 0.02

#: Paso 2, en dos tiempos. Primero se acota a las celdas que estan **junto al
#: pais**; solo despues se busca municipio.
#:
#: El orden importa y costo un error: rescatar por "municipio mas cercano" sin
#: acotar antes reclama todo el continente. Las teselas de GHS-POP cubren
#: tambien Panama, Venezuela, Ecuador, Peru y Brasil, y cada celda de esos
#: paises tiene, por definicion, un municipio colombiano que es el mas cercano.
#: La primera version de este paso rescato 832.506 celdas y la poblacion
#: nacional paso de 52,6 a 167 millones.
SQL_RESCATE = """
INSERT INTO crosswalk_h3_adm
WITH sin_asignar AS (
    SELECT DISTINCT d.h3_08,
           h3_cell_to_lng(d.h3_08) AS lng,
           h3_cell_to_lat(d.h3_08) AS lat
    FROM {tabla_datos} d
    WHERE d.h3_08 NOT IN (SELECT h3_08 FROM crosswalk_h3_adm)
),
junto_al_pais AS (
    SELECT s.*
    FROM sin_asignar s
    WHERE ST_DWithin(ST_Point(s.lng, s.lat), (SELECT geom FROM pais), {max_grados})
)
SELECT j.h3_08, m.adm2_id, 1.0, TRUE
FROM junto_al_pais j
JOIN LATERAL (
    SELECT g.adm2_id
    FROM admin_geom g
    WHERE ST_DWithin(ST_Point(j.lng, j.lat), g.geom, {max_grados})
    ORDER BY ST_Distance(ST_Point(j.lng, j.lat), g.geom)
    LIMIT 1
) m ON TRUE
"""


def rescue_unassigned(
    con: Any,
    *,
    tabla_datos: str = "pop_h3",
    max_grados: float = RESCUE_MAX_DEGREES,
) -> int:
    """Asigna municipio a las celdas con datos que el polyfill dejo fuera.

    Son celdas costeras y de frontera: su centro cae fuera de todo poligono
    municipal pero su parte terrestre tiene poblacion. Sin este paso esa gente
    desaparece del reporte municipal, y el invariante de suma se rompe.

    **La cota de distancia no es una optimizacion, es correccion.** El activo se
    construye desde teselas globales que cubren tambien los paises vecinos, y
    para cualquier celda de Panama o Venezuela existe un municipio colombiano
    que es "el mas cercano". Rescatar sin acotar reclama el continente entero.

    Las celdas rescatadas quedan marcadas con ``rescatada = TRUE``: es una
    aproximacion y tiene que poder auditarse.
    """
    con.execute(
        """
        CREATE OR REPLACE TEMP TABLE pais AS
        SELECT ST_Union_Agg(geom) AS geom FROM admin_geom
        """
    )
    antes: int = con.execute("SELECT count(*) FROM crosswalk_h3_adm").fetchone()[0]
    con.execute(SQL_RESCATE.format(tabla_datos=tabla_datos, max_grados=max_grados))
    despues: int = con.execute("SELECT count(*) FROM crosswalk_h3_adm").fetchone()[0]
    rescatadas = despues - antes
    _log.info(
        "celdas rescatadas junto a la linea de costa o frontera",
        extra={"context": {"celdas": rescatadas, "max_grados": max_grados}},
    )
    return rescatadas
