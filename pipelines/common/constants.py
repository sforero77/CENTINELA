"""Constantes de dominio fijadas por la especificacion tecnica v0.9.

Todo valor aqui es una *decision de diseno citada*, no un parametro ajustable
al vuelo: cambiarlo cambia el comportamiento publicado del sistema y debe pasar
por PR con actualizacion de los golden tests.
"""

from __future__ import annotations

from typing import Final

# --- Disparo (RF-01, §5.1) -------------------------------------------------

#: Magnitud minima que dispara un evento. Umbral elegido para acotar el falso
#: disparo (riesgo "cifra alarmista", §7).
MIN_MAGNITUDE: Final[float] = 5.5

#: Feeds GeoJSON en tiempo real recomendados por USGS para apps automatizadas
#: (D7). NUNCA polling a FDSN: FDSN solo para backtests e historicos.
USGS_FEED_BASE: Final[str] = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary"
USGS_FEED_PRIMARY: Final[str] = "4.5_hour"
#: Feed de respaldo cuando el trigger despierta tras una demora del cron
#: (GitHub Actions documenta demoras de 5-30 min, §4.2).
USGS_FEED_BACKFILL: Final[str] = "4.5_day"

#: Solo para backtests e historicos (G1/G2). No usar en el camino critico.
USGS_FDSN_EVENT: Final[str] = "https://earthquake.usgs.gov/fdsnws/event/1/query"

# --- Unidad de analisis (D1, §3.1) ----------------------------------------

#: Resolucion H3 de computo.
H3_RES_COMPUTE: Final[int] = 8
#: Resoluciones agregadas que consume el visor.
H3_RES_VIEWER: Final[tuple[int, ...]] = (7, 6)

#: CRS de publicacion. El computo de areas usa proyeccion equiarea local.
CRS_PUBLICATION: Final[str] = "EPSG:4326"

# --- Bandas de intensidad publicadas (RF-05) ------------------------------

#: Bandas MMI reportadas como totales. El desglose etario solo se publica
#: para MMI>=7.
MMI_BANDS: Final[tuple[int, ...]] = (6, 7, 8)
MMI_BAND_AGE_BREAKDOWN: Final[int] = 7

#: Umbral de probabilidad a partir del cual Ground Failure se considera
#: "alta" para el conteo de poblacion expuesta.
GROUND_FAILURE_HIGH_PROB: Final[float] = 0.10

# --- Reintentos del reporte preliminar (RF-03) ----------------------------

#: Cadencia de reintento que declara RF-03 mientras no aparece ShakeMap.
#:
#: Es un **suelo de la especificacion, no un freno del codigo**. Quien decide
#: cada cuanto se vuelve a mirar es el vigia, y desde el cron externo pasa cada
#: cinco minutos: comprobar mas a menudo detecta el ShakeMap antes, y el SLO se
#: cuenta desde que ese ShakeMap existe. El coste es nulo —el commit del
#: reporte esta guardado por `git diff --staged --quiet`, asi que un preliminar
#: identico no publica nada— y la ganancia son hasta veinticinco minutos.
PRELIMINARY_RETRY_MINUTES: Final[int] = 30
PRELIMINARY_MAX_HOURS: Final[int] = 6

#: Cada cuanto puede pasar el vigia, en el caso mas rapido.
#:
#: Es el intervalo del cron externo por `repository_dispatch`, y tambien el
#: minimo que GitHub acepta en un `schedule`. Existe aqui porque la ventana de
#: RF-03 se conto durante un tiempo en **intentos** y no en horas: con el vigia
#: a media hora, doce intentos eran seis horas y nadie noto la diferencia; al
#: bajar a cinco minutos, esos doce intentos pasaron a ser **una** hora y la
#: ventana se encogio en silencio. Ver `_ventana_preliminar_agotada`.
CADENCIA_MINIMA_MIN: Final[int] = 5
#: Radios (km) de la exposicion preliminar sin ShakeMap.
PRELIMINARY_RADII_KM: Final[tuple[int, ...]] = (25, 50, 100)

# --- Reporte ---------------------------------------------------------------

REPORT_SCHEMA_ID: Final[str] = "centinela/report/1.0"
#: Municipios listados en el ranking del reporte (RF-05).
TOP_ADM2_COUNT: Final[int] = 15
#: Cifras significativas en prosa (RF-06). CSV/parquet van exactos.
PROSE_SIGNIFICANT_DIGITS: Final[int] = 2

#: Disclaimers fijos, obligatorios en todo artefacto (§1.2).
DISCLAIMERS: Final[tuple[str, ...]] = (
    "Exposición estimada, no daño observado.",
    "Este sistema no es una alerta temprana ni una recomendación de evacuación.",
    "No reemplaza a los servicios geológicos ni a las unidades de gestión del riesgo.",
    "Fuentes, vintages y versiones consumidas: ver manifiesto enlazado.",
)

# --- Cobertura por fase (O2) ----------------------------------------------

PHASE_0_COUNTRIES: Final[tuple[str, ...]] = ("COL",)
PHASE_1_COUNTRIES: Final[tuple[str, ...]] = ("COL", "MEX", "PER", "ECU", "CHL", "VEN", "GTM")
