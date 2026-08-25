"""Contraste del activo contra una evaluacion de dano externa (Fase 2, §6.6).

**Exposicion no es dano, y este modulo existe para poder ensenar la diferencia
en vez de explicarla.** CENTINELA publica cuanta gente y cuanta infraestructura
quedo dentro de una franja de intensidad. Cuanta de esa infraestructura resulto
danada es otra pregunta, con otro metodo y otra incertidumbre.

Para los dos eventos golden hay respuesta abierta de terceros: el Microsoft AI
for Good Lab publico en HDX evaluaciones de dano de Cali —el sismo del Choco— y
de La Guaira —el de Catia La Mar—, las dos CC BY, y ademas usando huellas de
**Overture**, la misma fuente de este proyecto. Eso hace la comparacion de
conteos interpretable y no anecdotica.

Se compara sobre las **mismas celdas H3**, no sobre areas dibujadas a ojo: cada
edificacion evaluada se lleva a su celda r8 por el centroide, igual que hace el
activo. Asi la unica diferencia entre las dos cifras es lo que cada uno metio en
la celda, no como se recorto el mapa.

Ojo con las licencias: el dato de Microsoft es CC BY y se puede citar sin mas.
El de UNEP/OCHA sobre escombros es **CC BY-SA** y no puede entrar en el activo
sin arrastrar el cubo entero — se consume como referencia externa.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..common.constants import H3_RES_COMPUTE
from ..common.logging import get_logger

_log = get_logger(__name__)

#: EPSG del activo y de las celdas H3.
CRS_ACTIVO = "EPSG:4326"


@dataclass(frozen=True, slots=True)
class Contraste:
    """Lo que dice cada fuente sobre las mismas celdas."""

    etiqueta: str
    celdas: int
    #: Celdas con edificaciones evaluadas que el activo no tiene. Cualquier
    #: valor mayor que cero es un hueco de cobertura del activo, no un matiz.
    celdas_sin_activo: int
    evaluadas: int
    danadas: int
    bld_activo: float
    pop_activo: float

    @property
    def fraccion_danada_pct(self) -> float:
        return 100.0 * self.danadas / self.evaluadas if self.evaluadas else 0.0

    @property
    def razon_conteo(self) -> float:
        """Edificaciones del activo por cada una evaluada.

        No tiene por que ser 1: la evaluacion externa se recorta a su mascara de
        area valida —donde la imagen servia— y una celda r8 puede quedar medio
        dentro. Sirve para detectar un orden de magnitud raro, no para calibrar.
        """
        return self.bld_activo / self.evaluadas if self.evaluadas else 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "etiqueta": self.etiqueta,
            "celdas": self.celdas,
            "celdas_sin_activo": self.celdas_sin_activo,
            "evaluadas": self.evaluadas,
            "danadas": self.danadas,
            "fraccion_danada_pct": round(self.fraccion_danada_pct, 3),
            "bld_activo": self.bld_activo,
            "pop_activo": self.pop_activo,
            "razon_conteo": round(self.razon_conteo, 3),
        }


#: Lleva cada edificacion evaluada a su celda r8 por el centroide.
#:
#: `always_xy := true` no es opcional. EPSG:4326 declara el orden de ejes
#: lat-lon, y `ST_Transform` lo respeta: sin esto las coordenadas salen
#: invertidas, la celda calculada no existe en ningun sitio y el join devuelve
#: cero filas — que es exactamente lo que parece un "no hay solape" legitimo.
SQL_CELDAS_EVALUADAS = """
CREATE OR REPLACE TABLE celdas_evaluadas AS
WITH puntos AS (
    SELECT {columna_danado} AS danado,
           ST_Centroid(ST_Transform(geom, '{crs_origen}', '{crs_destino}', always_xy := true)) AS p
    FROM ST_Read('{fuente}')
)
SELECT h3_latlng_to_cell(ST_Y(p), ST_X(p), {resolution}) AS h3_08,
       count(*)          AS evaluadas,
       sum(danado)::BIGINT AS danadas
FROM puntos
GROUP BY 1
"""


#: Prefijo de GDAL para leer un fichero remoto por rangos.
VSI_HTTP = "/vsicurl/"


def ruta_gdal(fuente: str) -> str:
    """Normaliza la fuente a algo que ``ST_Read`` sepa abrir.

    Acepta una URL normal y le pone el prefijo. Pedirlo ya escrito parecia mas
    explicito y resulto una trampa: una ruta que empieza por barra la convierte
    Git Bash a ruta de Windows antes de que salga de la maquina, asi que el
    workflow recibio algo como "C:/Program Files/Git/vsicurl/https;//..." y
    fallo. Con la URL a secas no hay nada que convertir.
    """
    if fuente.startswith(VSI_HTTP) or not fuente.lower().startswith(("http://", "https://")):
        return fuente
    return f"{VSI_HTTP}{fuente}"


def contrastar(
    con: Any,
    *,
    fuente: str,
    exposure_glob: str,
    etiqueta: str,
    crs_origen: str,
    columna_danado: str = "damaged",
    resolution: int = H3_RES_COMPUTE,
) -> Contraste:
    """Compara una evaluacion de dano externa con el activo, celda a celda.

    Args:
        fuente: ruta local o URL del vector de dano. Una URL http(s) se lee
            por rangos con `/vsicurl/`, sin bajar el fichero entero.
        exposure_glob: activo de exposicion del pais.
        crs_origen: EPSG del vector de dano. Los productos de Microsoft en HDX
            vienen proyectados en la zona UTM del area.
    """
    from .pipeline import register_exposure_view

    register_exposure_view(con, exposure_glob)
    con.execute(
        SQL_CELDAS_EVALUADAS.format(
            columna_danado=columna_danado,
            crs_origen=crs_origen,
            crs_destino=CRS_ACTIVO,
            fuente=ruta_gdal(fuente),
            resolution=resolution,
        )
    )
    fila = con.execute(
        """
        SELECT count(*),
               COALESCE(sum(c.evaluadas), 0),
               COALESCE(sum(c.danadas), 0),
               COALESCE(sum(e.bld_count), 0.0),
               COALESCE(sum(e.pop_total), 0.0)
        FROM celdas_evaluadas c JOIN exposure e USING (h3_08)
        """
    ).fetchone()
    huerfanas: int = con.execute(
        """
        SELECT count(*) FROM celdas_evaluadas c
        LEFT JOIN exposure e USING (h3_08) WHERE e.h3_08 IS NULL
        """
    ).fetchone()[0]

    resultado = Contraste(
        etiqueta=etiqueta,
        celdas=int(fila[0]),
        celdas_sin_activo=int(huerfanas),
        evaluadas=int(fila[1]),
        danadas=int(fila[2]),
        bld_activo=float(fila[3]),
        pop_activo=float(fila[4]),
    )
    registrar = _log.warning if huerfanas else _log.info
    registrar(
        "contraste con evaluacion de dano externa"
        if not huerfanas
        else "hay celdas evaluadas que el activo no cubre",
        extra={"context": resultado.to_dict()},
    )
    return resultado
