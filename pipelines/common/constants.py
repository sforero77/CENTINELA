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

#: CRS de publicacion. **No hay ninguna reproyeccion en el repositorio.**
#:
#: Este comentario decia "el computo de areas usa proyeccion equiarea local", y
#: eran dos cosas mal a la vez. Una: no existe tal reproyeccion; longitudes y
#: areas se calculan con `ST_Length_Spheroid` y `ST_Area_Spheroid`, que es
#: **geodesico sobre el elipsoide**, no proyectado. Dos: una equiarea conserva
#: superficie a costa de la distancia, asi que seria la clase equivocada para
#: medir longitud — y `road_km` es una cifra titular.
#:
#: Los numeros estan bien: nadie calcula en grados, y las columnas estan bien
#: nombradas. Lo que estaba mal era lo que el codigo decia de si mismo, que en
#: `layers.py` ademas no era un comentario sino metadato publicado.
CRS_PUBLICATION: Final[str] = "EPSG:4326"

# --- Bandas de intensidad publicadas (RF-05) ------------------------------

#: Bandas MMI reportadas como totales.
MMI_BANDS: Final[tuple[int, ...]] = (6, 7, 8)

#: Bandas en las que se publica **equipamiento e infraestructura**, no solo
#: poblacion: edificaciones, superficie construida, salud, educacion y vias.
#:
#: POR QUE 6 Y NO SOLO 7. Hasta el 3-sep-2026 todo lo que no fuera poblacion se
#: agregaba unicamente en MMI>=7, sin justificacion citada. El efecto medido:
#: **trece de veintitres reportes no tienen poblacion en MMI>=7**, asi que
#: publicaban "0 edificaciones, 0 hospitales, 0 escuelas, 0 km de via" con
#: millones de personas dentro de MMI>=6. El peor caso, `us7000jl3s`: 4,75
#: millones de personas —3,1 de ellas en Guayaquil— y ni un solo hospital que
#: nombrar.
#:
#: No se encontro **ninguna** fuente autorizada que situe el inicio del dano en
#: MMI VII. Lo que hay dice lo contrario, y converge en VI:
#:
#: * **USGS, Mercalli abreviada**, grado VI: *"Damage slight"*. El grado VII ya
#:   describe *"considerable damage in poorly built structures"*.
#: * **ShakeMap**, tabla de intensidad instrumental: el dano potencial deja de
#:   ser *"None"* en **MMI 5** (*"Very light"*), y en MMI 6 es *"Light"*.
#: * **EMS-98** (Grunthal): para la clase de vulnerabilidad A —mamposteria de
#:   piedra, adobe— el dano de grado 1 aparece en muchas construcciones ya en
#:   **intensidad VI**. El umbral se corre tres grados segun el tipo
#:   constructivo, cosa que un corte fijo no puede representar.
#: * **GDACS** (Comision Europea): la compuerta de alerta esta en **MMI VI**;
#:   por debajo la alerta es verde.
#: * **OPS/OMS**, sismos de Venezuela 2026: reporta *"91 emergency hospitals
#:   located in areas affected by Intensity VI or above, including 20 hospitals
#:   exposed to Intensity VII or higher"*. Es el precedente operativo exacto
#:   —equipamiento de salud, en MMI>=VI, con el >=VII anidado— y es de LATAM.
#:
#: Y un argumento que va al reves de lo que parece: los hospitales tienen norma
#: sismorresistente mas exigente (NSR-10 los pone en Grupo IV, "indispensables"),
#: pero la OPS mide que *"nonstructural elements contribute more to vulnerability
#: than structural factors"*. Que el hospital no se caiga a MMI 6,5 no significa
#: que siga atendiendo — y significa que **se convierte en el destino de los
#: heridos de la zona**. Es mas razon para inventariarlo en MMI>=6, no menos.
#:
#: SE ANADE, NO SE MUEVE. Las columnas `*_mmi7p` conservan su significado exacto
#: para no romper la serie ni a quien integre el `report.json`. Las `*_mmi6p`
#: son nuevas y no cambian una sola cifra ya publicada.
MMI_BANDS_INFRAESTRUCTURA: Final[tuple[int, ...]] = (6, 7)

#: Bandas del desglose etario.
#:
#: Estuvo en MMI>=7 y solo ahi, y `docs/datos/agregaciones.md` lo justificaba
#: diciendo que "mas abajo la incertidumbre del modelo etario seria mayor que la
#: senal". **Esa razon no es una razon**: la incertidumbre etaria viene de mezclar
#: GHS-POP con WorldPop —el mismo documento lo explica dos secciones antes— y es
#: la misma en MMI 6 que en MMI 7. No es funcion de la intensidad.
#:
#: El efecto: en los trece eventos sin MMI>=7, la cifra de mayores era cero por
#: construccion, justo donde una poblacion mayor expuesta es lo mas accionable.
MMI_BANDS_AGE_BREAKDOWN: Final[tuple[int, ...]] = (6, 7)

#: Se conserva por compatibilidad: es la banda cuyo campo `pop_65p_mmi7p` viaja
#: en los veintitres `report.json` ya publicados.
MMI_BAND_AGE_BREAKDOWN: Final[int] = 7

#: Umbral a partir del cual una celda entra en el conteo de poblacion expuesta
#: a falla de terreno.
#:
#: **NO ES UN UMBRAL DE USGS Y NO SIGNIFICA LO MISMO EN LOS DOS MODELOS.** Era el
#: unico valor de este modulo sin justificacion citada, en un modulo que promete
#: que todo valor de aqui es una decision citada. Lo que hay que saber:
#:
#: * Jessee (2018), deslizamiento, entrega **probabilidad** de que la celda
#:   falle. Un 0,10 es "una entre diez".
#: * Zhu (2017), licuefaccion, entrega **cobertura areal**: la fraccion del area
#:   de la celda que se espera cubierta. Un 0,10 es "el 10 % de la superficie",
#:   que no es una probabilidad y no se lee como tal.
#:
#: Las dos distribuciones son distintas, asi que el mismo 0,10 no marca lo mismo
#: en cada una y **"alta" no es una categoria que USGS publique** a este valor.
#: El reporte por eso nombra la unidad de cada modelo en vez de decir "alta", y
#: pone al lado la alerta que USGS si publica.
#:
#: El valor se conserva porque es el corte con el que se calculo todo el
#: catalogo historico y cambiarlo mueve las veintiuna cifras publicadas a la vez;
#: cuando se cambie, se cambia con el catalogo entero y el delta publicado.
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

#: Raiz de la pagina publicada. Vivia en `frescura.py`, que era el unico que la
#: usaba; el hilo tambien la necesita para poder enlazar el reporte que promete.
SITIO_PUBLICADO: Final[str] = "https://sforero77.github.io/CENTINELA"
