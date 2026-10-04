"""Constantes de dominio fijadas por la especificacion tecnica v0.9.

Todo valor aqui es una *decision de diseno citada*, no un parametro ajustable
al vuelo: cambiarlo cambia el comportamiento publicado del sistema y debe pasar
por PR con actualizacion de los golden tests.

ESA PROMESA SOLO VALE SI ALGUIEN LEE LA CONSTANTE. La auditoria del 5-sep-2026
encontro siete que no leia nadie —y al medirlo sin contar comentarios salio una
octava, `MMI_BANDS_INFRAESTRUCTURA`, citada en cuatro comentarios y leida por
cero lineas de codigo—. Cambiar cualquiera no cambiaba nada, en el modulo que
dice lo contrario. Se borraron o se conectaron, y
`test_constantes_vivas.py` falla si una vuelve a quedarse sin lector.
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

#: Resolucion a la que se agrega la malla que dibuja el visor (`celdas.json`).
#:
#: Era `(7, 6)` y no la leia nadie: `p3_report/celdas.py` tenia su propio
#: `RES_VISOR = 7`, y la r6 no se publica en ningun sitio. Dos definiciones del
#: mismo numero, una muerta y otra viva, en un modulo que promete que cambiar
#: esta cambia el comportamiento. Ahora `RES_VISOR` sale de aqui.
H3_RES_VIEWER: Final[int] = 7

# --- Bandas de intensidad publicadas (RF-05) ------------------------------
#
# NO SON CONSTANTES, SON COLUMNAS. Aqui vivian `MMI_BANDS = (6, 7, 8)`,
# `MMI_BANDS_INFRAESTRUCTURA = (6, 7)` y `MMI_BANDS_AGE_BREAKDOWN = (6, 7)`, y
# ninguna linea de codigo las leia: las bandas estan escritas en el nombre de
# cada columna (`pop_mmi6p`, `bld_mmi7p`, ...) del SQL de
# `p2_impact/pipeline.py`, del dataclass `Totales` y del esquema de
# `report.json`. Cambiar la tupla no movia una cifra. Se borraron el 3-oct-2026
# (auditoria #78); la justificacion se queda, porque es la que citan
# `p3_report/model.py`, `markdown.py`, `csv_out.py` y `docs/datos/agregaciones.md`.
#
# EQUIPAMIENTO E INFRAESTRUCTURA SE PUBLICAN EN MMI>=6 Y >=7, no solo la
# poblacion: edificaciones, superficie construida, salud, educacion y vias.
#
# POR QUE 6 Y NO SOLO 7. Hasta el 3-sep-2026 todo lo que no fuera poblacion se
# agregaba unicamente en MMI>=7, sin justificacion citada. El efecto medido:
# **trece de veintitres reportes no tienen poblacion en MMI>=7**, asi que
# publicaban "0 edificaciones, 0 hospitales, 0 escuelas, 0 km de via" con
# millones de personas dentro de MMI>=6. El peor caso, `us7000jl3s`: 4,75
# millones de personas —3,1 de ellas en Guayaquil— y ni un solo hospital que
# nombrar.
#
# No se encontro **ninguna** fuente autorizada que situe el inicio del dano en
# MMI VII. Lo que hay dice lo contrario, y converge en VI:
#
# * **USGS, Mercalli abreviada**, grado VI: *"Damage slight"*. El grado VII ya
#   describe *"considerable damage in poorly built structures"*.
# * **ShakeMap**, tabla de intensidad instrumental: el dano potencial deja de
#   ser *"None"* en **MMI 5** (*"Very light"*), y en MMI 6 es *"Light"*.
# * **EMS-98** (Grunthal): para la clase de vulnerabilidad A —mamposteria de
#   piedra, adobe— el dano de grado 1 aparece en muchas construcciones ya en
#   **intensidad VI**. El umbral se corre tres grados segun el tipo
#   constructivo, cosa que un corte fijo no puede representar.
# * **GDACS** (Comision Europea): la compuerta de alerta esta en **MMI VI**;
#   por debajo la alerta es verde.
# * **OPS/OMS**, sismos de Venezuela 2026: reporta *"91 emergency hospitals
#   located in areas affected by Intensity VI or above, including 20 hospitals
#   exposed to Intensity VII or higher"*. Es el precedente operativo exacto
#   —equipamiento de salud, en MMI>=VI, con el >=VII anidado— y es de LATAM.
#
# Y un argumento que va al reves de lo que parece: los hospitales tienen norma
# sismorresistente mas exigente (NSR-10 los pone en Grupo IV, "indispensables"),
# pero la OPS mide que *"nonstructural elements contribute more to vulnerability
# than structural factors"*. Que el hospital no se caiga a MMI 6,5 no significa
# que siga atendiendo — y significa que **se convierte en el destino de los
# heridos de la zona**. Es mas razon para inventariarlo en MMI>=6, no menos.
#
# SE ANADE, NO SE MUEVE. Las columnas `*_mmi7p` conservan su significado exacto
# para no romper la serie ni a quien integre el `report.json`. Las `*_mmi6p`
# son nuevas y no cambian una sola cifra ya publicada.
#
# EL DESGLOSE ETARIO TAMBIEN SE PUBLICA EN MMI>=6 Y >=7.
#
# Estuvo en MMI>=7 y solo ahi, y `docs/datos/agregaciones.md` lo justificaba
# diciendo que "mas abajo la incertidumbre del modelo etario seria mayor que la
# senal". **Esa razon no es una razon**: la incertidumbre etaria viene de mezclar
# GHS-POP con WorldPop —el mismo documento lo explica dos secciones antes— y es
# la misma en MMI 6 que en MMI 7. No es funcion de la intensidad.
#
# El efecto: en los trece eventos sin MMI>=7, la cifra de mayores era cero por
# construccion, justo donde una poblacion mayor expuesta es lo mas accionable.

#: Que parte de la poblacion de MMI>=6 tiene que estar en una banda mas alta
#: para que el reporte titule y ordene por ella.
#:
#: SIN SUELO, CUATRO PERSONAS Y MEDIA DECIDIAN EL REPORTE ENTERO. Hasta el
#: 3-oct-2026 `banda_publicada` y `banda_titular` decidian con `> 0`: un evento
#: con 760 mil personas en MMI>=6 y 4,5 en una esquina de MMI>=7 —una celda
#: cuyo centro cae justo dentro del contorno, o una fraccion de pixel de
#: WorldPop— se titulaba "4 personas en MMI>=7", ordenaba la tabla por esa
#: banda y descartaba a todo municipio sin nadie en ella, y bajaba a MMI>=7 el
#: equipamiento, los mayores, el mapa y el visor. Del evento quedaba una fila.
#:
#: POR QUE RELATIVO Y POR QUE EL 1 %. Un suelo absoluto —mil personas, por
#: ejemplo— borraria un MMI>=7 real en un pais poco poblado y no significaria
#: nada en Lima; lo que hay que preguntar es si la banda **describe** el evento
#: o es su borde. El borde es ruido conocido: `mmi_max` es la isolinea que
#: contiene el centro de la celda, y el propio ShakeMap tiene incertidumbre de
#: medio grado o mas lejos de las estaciones. El 1 % queda por debajo de la
#: banda real mas delgada del catalogo publicado —`us7000nr0v`, 3.291 personas
#: en MMI>=7 de 173.018 en MMI>=6, el 1,9 %, con tres municipios con cifra—, asi
#: que ningun reporte publicado cambia de banda; solo deja de poder decidirla un
#: punado de personas.
#:
#: El visor la repite como `FRACCION_MINIMA_DE_BANDA` en `site/assets/app.js`, y
#: `test_banda_titular.py` vigila que las dos digan lo mismo.
FRACCION_MINIMA_DE_BANDA: Final[float] = 0.01

#: Se conserva por compatibilidad: es la banda cuyo campo `pop_65p_mmi7p` viaja
#: en los veintitres `report.json` ya publicados.
MMI_BAND_AGE_BREAKDOWN: Final[int] = 7

#: Profundidad desde la que un sismo deja de ser superficial (km).
#:
#: La clasificacion estandar —superficial < 70, intermedio 70-300, profundo
#: > 300— que el visor ya explicaba en prosa y no existia como constante. Se
#: usa para explicar por que un sismo grande puede no alcanzar ninguna banda
#: sobre poblacion: a 359 km la energia llega repartida a la superficie.
PROFUNDIDAD_INTERMEDIA_KM: Final[float] = 70.0

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

#: Horas durante las que se reintenta el preliminar mientras no aparece ShakeMap.
#:
#: Aqui vivia tambien `PRELIMINARY_RETRY_MINUTES = 30`, la cadencia de RF-03, y
#: no la leia nadie: era un **suelo de la especificacion, no un freno del
#: codigo**. Quien decide cada cuanto se vuelve a mirar es el vigia, y desde el
#: cron externo pasa cada cinco minutos (`CADENCIA_MINIMA_MIN`): comprobar mas a
#: menudo detecta el ShakeMap antes, y el SLO se cuenta desde que ese ShakeMap
#: existe. Un valor que no cambia nada al cambiarlo no pinta en este modulo; se
#: borro el 3-oct-2026 (auditoria #78).
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

#: Suelo entre dos despachos del MISMO evento, en minutos.
#:
#: P1 re-despachaba todo evento vivo en **cada** pasada. Con el vigia a cinco
#: minutos eso son 288 despachos al dia por evento: medido, 257 despachos y 262
#: commits por dos sismos en 24 h, en el directorio que el README llama «la base
#: de datos del sistema». P2 hace lo correcto —devuelve OMITIR si la version no
#: avanzo— pero cada despacho cuesta una corrida de la cola de Actions, que este
#: proyecto documenta como su cuello de botella.
#:
#: No afecta a la deteccion: un evento **nuevo** se despacha en el acto. Solo
#: pone suelo a los re-despachos, y quince minutos son de sobra para no perder
#: una revision de ShakeMap — un re-despacho a los cinco minutos del anterior
#: casi siempre trae la misma version y P2 lo descarta.
MINUTOS_ENTRE_REDESPACHOS: Final[int] = 15
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

# --- Publicacion ------------------------------------------------------------
#
# Aqui estaban `PHASE_0_COUNTRIES` y `PHASE_1_COUNTRIES`, las listas de paises
# de cada fase. No las leia nadie: que paises atiende el sistema lo dicen los
# manifests de `manifests/` y lo publica `site/cobertura.json`. Una tercera
# lista a mano solo podia divergir de las dos de verdad. Tambien
# `CRS_PUBLICATION = "EPSG:4326"`, igual de muerta: la nota de por que no hay
# reproyeccion y como se miden areas y longitudes vive donde se miden, en
# `common/geo.py` (`area_spheroid_m2`, `length_spheroid_m`).

#: Raiz de la pagina publicada. Vivia en `frescura.py`, que era el unico que la
#: usaba; el hilo tambien la necesita para poder enlazar el reporte que promete.
SITIO_PUBLICADO: Final[str] = "https://sforero77.github.io/CENTINELA"
