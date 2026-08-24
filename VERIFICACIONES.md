# Registro de verificaciones

Cierre de las tareas ⚠️ de §8 de la especificacion. Cada entrada dice **como**
se verifico, no solo el resultado: una verificacion que no se puede repetir no
sirve de nada dentro de seis meses.

Rondas: **23 de agosto de 2026** (fuentes de §8) y **auditoria completa del registro**, misma fecha. Metodo: peticiones reales a las
fuentes primarias (listados S3, indices HTTP, API de Socrata de datos.gov.co,
paginas de licencia de los publicadores).

---

## Resumen

### Ronda 2 — auditoria del registro completo

Criterio de admision aplicado a cada fuente: **sin geometria no sirve**. Un
registro administrativo sin coordenadas no se puede asignar a una celda H3, por
buena que sea su cobertura.

| Fuente | Geometria | Veredicto |
|---|---|---|
| USGS feeds / detail / ShakeMap / Ground Failure / PAGER | sí | ✅ probados contra el evento real de Chocó |
| GHS-POP, WorldPop, Overture, MGN-DANE | sí | ✅ (ronda 1) |
| REPS (`c36g-9fc2`), MEN (`cfw5-qzt5`) | **no** | ❌ fuera del activo |
| **API** de healthsites.io | sí | ❌ exige API key, viola O4 |
| HOTOSM `hotosm_<iso>_health_facilities` (HDX) | sí | ✅ **sustituye al REPS** |
| HOTOSM `hotosm_<iso>_education_facilities` (HDX) | sí | ✅ **sustituye al MEN** |
| healthsites.io publicado en HDX | sí | ✅ complemento sin credenciales |
| COD-AB de OCHA `cod-ab-<iso3>` | sí | ✅ **cubre los 19 paises de LATAM** (ronda 4) |

### Ronda 1 — tareas ⚠️ de §8

| Tarea | Estado | Resultado |
|---|---|---|
| T0.4 MGN-DANE | ✅ resuelta | **CC BY 4.0**, uso comercial y redistribucion permitidos |
| T0.5 REPS | ⚠️ resuelta en contra | Sin coordenadas y **CC BY-SA 4.0**: fuera del activo |
| T0.6 MEN | ⚠️ resuelta en contra | Idem REPS |
| T1.2 OurAirports | ✅ resuelta | Dominio publico citado: pagina de datos + The Unlicense |
| Overture release | ✅ corregida | `2026-08-19.0`; el bucket solo guarda **dos** releases |
| WorldPop age-sex | ✅ mejora | Hay desglose **para 2025**: cae un supuesto de la espec |
| WorldPop total | ✅ corregida | Ruta real hallada |
| GHS-POP | ✅ confirmada | Ambas variantes sirven |

---

## Ronda 3 — validacion de datos antes de construir P0

No basta con que la URL responda: hay que abrir el archivo y comprobar que dice
lo que se espera. Esta ronda descargo los datos y los midio.

### El total nacional cuadra

GHS-POP E2025 recortado por el limite oficial del MGN 2025 da **52.601.276**
habitantes para Colombia. El DANE proyecta **~53 millones** para 2025. La
diferencia es **-0,75 %**, dentro del ±1 % que exige el assert de §6.4. Es la
primera evidencia de que la cadena poblacional sirve para lo que se quiere.

### Contratos medidos, no supuestos

| Fuente | Lo medido |
|---|---|
| GHS-POP tesela | `ESRI:54009`, 10.000×10.000 px a 100 m, `float64`, **nodata = -200** |
| MGN 2025 dptos | 33 registros, `dpto_ccdgo` VARCHAR con el cero inicial intacto, EPSG:4326 |
| Overture buildings | `id` (GERS), `bbox` STRUCT(xmin,xmax,ymin,ymax), `geometry` OGC:CRS84 |
| HOTOSM salud COL | 9.618 elementos, geometrias **mixtas** POINT/POLYGON/MULTIPOLYGON |
| OurAirports | 738 aeropuertos en Colombia, **todos** con coordenadas |

El nodata de GHS-POP importa: son unos **22 millones de celdas por tesela**, todo
oceano. Sumar sin enmascarar da poblacion negativa y dispara el assert de calidad
sobre datos que en realidad estan sanos. Y las geometrias mixtas de HOTOSM
significan que el conteo por celda tiene que pasar por centroide, no asumir puntos.

### Descargar el subconjunto, no el mundo

Dos fuentes son inmanejables enteras y ambas tienen una via de escape que hubo
que encontrar:

**GHS-POP**: el mosaico global pesa **5,25 GB**. El JRC publica el mismo producto
en **375 teselas**; Colombia necesita **nueve**, que suman **93 MB**. El esquema de
teselado (origen en x=-18.041.000, y=9.000.000, teselas de 1.000 km) se derivo y
se verifico contra la georreferenciacion real de una tesela descargada.

**Overture**: el tema `buildings` son **512 ficheros, 277 GB y 2.529 millones de
edificaciones**. Colombia toca **once**. El `collection.json` del catalogo STAC
(155 KB) trae el bbox de cada fichero, asi que la seleccion no cuesta leer datos.
Dentro de cada fichero, el filtro sobre la columna `bbox` poda por row-group:
**contar las edificaciones de Quibdó en un fichero remoto de 5 millones de filas
toma 2,2 segundos**. Sin esto P0 no seria viable, asi que dejo de ser un detalle
de implementacion.

### 9. La trampa del catalogo STAC de Overture

El estandar STAC dice que `extent.spatial.bbox[0]` es la **union** de las
sub-extensiones, y que las reales empiezan en el indice 1. Overture no hace eso:
publica **512 entradas para 512 ficheros**, y la `[0]` es el bbox del primer
fichero.

Aplicar la lectura del estandar —saltarse la primera— desplaza todo un puesto y
hace leer los ficheros equivocados. Y como los ficheros vecinos cubren zonas
adyacentes, el resultado seria plausible: un conteo de edificaciones que parece
razonable y esta mal. Se detecto al cruzar los bboxes del catalogo con la
extension real medida sobre los ficheros con DuckDB.

`parse_collection()` falla explicitamente si el conteo deja de ser 1:1, porque
esa es la unica senal de que la suposicion dejo de valer.

### 10. Overture publica PMTiles por release

`https://tiles.overturemaps.org/<release>/<tema>.pmtiles`. Las capas de contexto
del visor no necesitan `tippecanoe`: ya estan teseladas. Las de CENTINELA
—coropletas de exposicion e impacto— siguen siendo propias, porque son datos
nuestros.

---

## Ronda 4 — cobertura regional y lo que destapo (23-ago-2026)

El proyecto es para LATAM, asi que la pregunta no es si las fuentes existen para
Colombia sino si existen **para todos**. Una peticion real por fuente y pais
sobre los 19 de LATAM hispanohablante mas Brasil: ARG, BOL, BRA, CHL, COL, CRI,
CUB, DOM, ECU, GTM, HND, MEX, NIC, PAN, PER, PRY, SLV, URY, VEN.

### El camino esta despejado para los 19

| Fuente | Cobertura |
|---|---|
| WorldPop age-sex R2025A 2025 | **19/19**, con las 20 bandas (00…90) cada uno |
| WorldPop total constrained 2025 | **19/19** |
| `cod-ab-<iso3>` (OCHA) | **19/19**, todos CC BY-IGO |
| `hotosm_<iso>_health_facilities` | **19/19**, todos ODbL |
| `hotosm_<iso>_education_facilities` | **19/19**, todos ODbL |

No hay ningun pais sin camino. Eso convierte Fase 1 en escribir manifests, no en
buscar datos.

### Dos irregularidades del COD-AB

**Cinco paises no publican GeoJSON** y caen a SHP: COL, ARG, BRA, PRY, URY.

**Colombia publica cuatro recursos SHP en el mismo dataset**, y el resolutor
tomaba el primero de cada formato: `MGN2024_URB_SECCION.zip`, 48 MB de
**secciones urbanas** en vez de municipios. El que se quiere es
`COL Administrative Divisions Shapefiles.zip`. De ahi el campo `hdx_resource`
del manifest: un dataset con varios recursos del mismo formato tiene que fijar
cual, igual que fija el vintage, y el resolutor falla si el fragmento no
identifica exactamente uno.

### Las columnas del COD-AB no son las que documenta HDX

Leidas abriendo `ven_admin2.shp` con DuckDB, no de la documentacion:
`adm2_pcode`, `adm2_name`, `adm1_pcode`, `adm1_name` — en minusculas, y **no**
los `ADM2_PCODE` / `ADM2_ES` de las entregas antiguas. 336 registros, que
cuadra con los 335 municipios de Venezuela mas el Distrito Capital.

La caja envolvente del pais se midio sobre ese mismo archivo
(−73,3691..−59,7411 / 0,6346..12,4988) en vez de estimarla. El extremo norte lo
pone Dependencias Federales; el COD-AB no incluye la Isla de Aves.

Pendiente para el mantenedor de pais: los toponimos salen mal codificados
(«Falc?n» por «Falcón»). Hay que resolverlo antes de publicar un reporte de
Venezuela, porque esos nombres se imprimen.

### El solape entre HOTOSM y healthsites.io: 96,6 %

El catalogo de capas declaraba la agregacion de salud como «conteo de puntos
por celda, **deduplicado por proximidad**». La deduplicacion estaba declarada y
**no implementada**: las dos fuentes se sumaban.

Medido sobre Colombia:

| | |
|---|---|
| HOTOSM `hotosm_col_health_facilities` | 9.618 puntos |
| healthsites.io via HDX | 8.443 puntos |
| De healthsites, a <20 m de un punto de HOTOSM | **8.152 (96,6 %)** |
| a <50 m | 8.181 (96,9 %) |
| a <100 m | 8.194 (97,1 %) |
| **Suma sin deduplicar** | **18.061** |

Las dos derivan de OpenStreetMap, asi que el solape era esperable en cuanto se
midio. Sumadas daban **casi el doble** de las sedes que hay, y ninguna guardia
lo habria notado: la cifra es positiva y del orden correcto. Que el umbral
apenas mueva el solape entre 20 y 100 m confirma que se trata de los mismos
establecimientos y no de vecindad casual; se fija en **20 m**.

La correccion es la que el catalogo ya prometia: las fuentes entran en el orden
del manifest, la primera completa, y cada siguiente aporta solo lo que no esta a
menos de 20 m de un punto ya aceptado. healthsites aporta asi unas 290 sedes
reales en vez de 8.443 duplicadas.

### ¿Son estas las mayores fuentes posibles? Comprobado, y falta una

**Edificaciones y vias: si.** Overture no es «una fuente mas»: es la fusion de
las tres mayores colecciones abiertas. Medido leyendo la columna `sources` de
las edificaciones de Quibdó en el parquet remoto:

| Origen | Edificaciones |
|---|---:|
| OpenStreetMap | 22.176 |
| Microsoft ML Buildings | 7.915 |
| Google Open Buildings | 5.092 |

**Poblacion: si, y con el release correcto.** El listado del FTP del JRC
confirma que `GHS_POP_GLOBE_R2023A` sigue siendo el ultimo global; el
`GHS_POP_ARCTIC_R2025A` que aparece al lado es solo del Artico. Dentro de
R2023A, la epoca E2025 a 100 m es la mas fina util (E2030 existe, pero proyecta
a 2030). WorldPop R2025A tambien es el ultimo.

**Mas resolucion no habria sido mejor.** Existe el HRSL de Meta a **30 m**,
CC BY, publicado en HDX para Colombia — once veces mas fino. Su vintage es
**2019**. A celda H3 r8 (~0,74 km²) un raster de 100 m ya aporta ~74 pixeles por
celda, asi que el detalle adicional se promedia y desaparece, mientras que seis
anos de desactualizacion no. Cambiar habria sido regalar vigencia a cambio de
nada. Por la misma razon **r8 no es una limitacion**: es la escala que
corresponde a entradas de 100 m; bajar a r9 multiplica por siete las celdas para
representar informacion que la fuente no tiene.

**Lo que si faltaba: GHS-BUILT-S.** La debilidad documentada del conteo de
edificaciones son los huecos de OSM en asentamientos informales y zona rural
dispersa — donde vive la poblacion mas expuesta. GHS-BUILT-S deriva de
Sentinel-2 y Landsat, asi que no tiene ese hueco. Comparte retícula, epoca,
proyeccion y licencia con GHS-POP (verificado: la tesela R9_C11 responde con el
mismo esquema de nombres), de modo que reutiliza el selector de teselas y cuesta
unos 90 MB por pais. Entra como columna `built_m2` y convierte la bandera
`revisar_sin_edificios` en una cifra: `construido_no_mapeado`.

### La ventana del disparador cortaba paises cubiertos

Al medir las cajas de los 19 paises con `division_area` de Overture salio que
`LATAM_BBOX` —el filtro de RF-01— dejaba fuera territorio de paises que el
sistema dice cubrir:

| | Llega a | La ventana cortaba en |
|---|---|---|
| Mexico (Isla Guadalupe, Revillagigedo) | 118,65°O | 118,0°O |
| Chile (Cabo de Hornos, Diego Ramirez) | 56,78°S | 56,0°S |
| Brasil (Fernando de Noronha, ~3.000 hab.) | 32,42°O | 34,0°O |

Un sismo relevante ahi no habria fallado: habria dejado de existir para el
sistema, sin rastro que revisar. Chile es el caso serio — la zona de fractura de
Shackleton produce sismos justo en ese margen.

Nueva ventana: `lon -119,0..-32,0 / lat -57,5..33,0`. El limite este se detiene
antes del archipielago de San Pedro y San Pablo (29,35°O), que se asienta
**sobre la dorsal mesoatlantica**: estirar la ventana hasta el compraria
sismicidad oceanica frecuente y sin poblacion a cambio de una estacion
cientifica con unas pocas personas.

### El release de Overture sigue vigente

`2026-08-19.0` responde y es el ultimo; `2026-07-22.0` tambien. Confirmado que
el bucket conserva **dos**, asi que el vintage fijado caduca solo. La prueba
nocturna de contrato ahora lo vigila.

---

## Hallazgos de la ronda 2

### 4. Un bug de seleccion de version, cazado por las fixtures reales

El caso que justifica congelar productos reales en vez de sinteticos.

En `us6000t7zp` (Venezuela, M7.5) el ShakeMap va por la version **14**. Con
`includesuperseded=true` se ven las catorce, y sus pesos son estos:

| Version | Fecha | `preferredWeight` |
|---|---|---|
| v1–v4 | junio 2026 | **232** |
| v13–v14 | agosto 2026 | **228** |

El parser ordenaba por `preferredWeight` y elegia **v4**: un ShakeMap de hace
mes y medio. El reporte habria salido con cifras equivocadas, ninguna prueba
habria fallado y nada en la salida habria delatado el problema.

`preferredWeight` desempata **contribuidores** (`us` frente a `atlas` o una red
regional), no versiones de un mismo contribuidor. El criterio correcto, ya
implementado: descartar `DELETE`, elegir contribuidor por peso, y dentro de el
la entrada mas reciente por `updateTime`. Verificado contra la respuesta
autoritativa de ComCat para los tres eventos: v7, v14 y v9.

La regresion vive en `tests/golden/test_g2_venezuela.py::test_no_se_elige_una_version_obsoleta`,
y comprueba primero que la fixture siga reproduciendo la trampa — una prueba de
regresion que deja de reproducir el caso es peor que no tenerla.

### 5. `includesuperseded=true` funciona directo en FDSN

La espec asumia que recuperar el historial de versiones requeria `libcomcat`.
No: el parametro funciona sobre el endpoint FDSN y devuelve todas las versiones
de cada producto. Una dependencia menos en el procedimiento de congelado.

### 6. T0.1 resuelta: los tres eventos identificados

| Evento | `usgs_id` | Cuando | Detalle |
|---|---|---|---|
| Chocó | `us6000tjl2` | 2026-08-10T12:34:28Z | M7.4, **110 km**, PAGER rojo, ShakeMap v7 |
| Catia La Mar | `us6000t7zp` | 2026-06-24T22:05:04Z | M7.5, 10 km, ShakeMap v14 |
| San Felipe | `us6000t7zc` | 2026-06-24T22:04:31Z | M7.2, 10 km, ShakeMap v9 |

Dos cosas que la espec no anticipaba. Los eventos de Venezuela estan separados
por **33 segundos** y 145 km: ese es el «evento doble» de G2, y el sistema debe
producir dos reportes con areas de intensidad solapadas sin fusionarlos. Y Chocó
fue **profundo** (110 km) pero **si** tiene Ground Failure, asi que G3 no puede
definirse como «evento profundo» — lo que hay que probar es la ausencia del
producto, venga de donde venga.

### 7. La URL de HOTOSM cambia de forma segun el pais

Para la misma capa logica `health_facilities` conviven al menos tres patrones:

```
COL -> production-raw-data-api.s3.amazonaws.com/ISO3/COL/health_facilities/…
MEX -> s3.dualstack.us-east-1.amazonaws.com/production-raw-data-api/ISO3/MEX/health_facilities/points/…
PER -> export.hotosm.org/downloads/<uuid>/…
```

Adivinar la ruta funciona para unos paises y falla para
dos — es decir, funciona hasta que alguien agrega el pais que no encaja, y falla
en produccion, no en CI. El identificador estable es el **nombre del dataset**;
la URL se resuelve por la API de CKAN de HDX en cada build
(`pipelines/common/hdx.py`).

### 8. COD-AB cubre los siete paises de Fase 1 (ampliado a 19 en la ronda 4)

`cod-ab-col`, `cod-ab-mex`, `cod-ab-per`, `cod-ab-ecu`, `cod-ab-chl`,
`cod-ab-ven` y `cod-ab-gtm` existen, todos **CC BY-IGO**, todos con shapefile o
geodatabase. Para Colombia el COD es el propio MGN del DANE reempaquetado, asi
que no aporta geometria nueva; su valor esta en Fase 1, donde evita que cada
mantenedor de pais tenga que ingeniar el geoportal nacional de turno solo para
obtener adm1/adm2.

---

## Hallazgos que cambian el diseno

### 1. WorldPop publica estructura etaria para 2025 (mejora)

**Lo que decia la espec (§2.2):** el desglose por edad y sexo solo existe para
2020, de donde salia la limitacion documentada *«proporciones de 2020 aplicadas
sobre totales 2025 de GHS-POP (supuesto de estructura estable)»*, declarada en
los metadatos de cada reporte.

**Lo verificado:** el release `Global_2015_2030/R2025A` publica age-sex
constrained por epoca anual hasta 2026. Para Colombia, 2025, 100 m constrained
hay **62 rasters** (`col_f_00`…`col_m_80`, mas los totales `col_T_F` y
`col_T_M`).

```
https://data.worldpop.org/GIS/AgeSex_structures/Global_2015_2030/R2025A/2025/COL/v1/100m/constrained/
```

**Consecuencia:** el supuesto de estructura etaria estable desaparece. Es una
limitacion menos que declarar en cada reporte, y la cifra de poblacion de 65+
en MMI≥7 —una de las mas sensibles del producto— deja de arrastrar cinco anos
de desfase.

### 2. Overture conserva solo dos releases (riesgo nuevo)

**Lo verificado:** el listado del bucket, no truncado, contiene exactamente dos
prefijos: `release/2026-07-22.0/` y `release/2026-08-19.0/`.

**Consecuencia:** fijar el release explicito —decision correcta y que se
mantiene— da reproducibilidad **del calculo**, no **de la descarga**. Pasados
unos dos meses la URL del manifest deja de existir y nadie puede rehacer el
build desde cero. RNF-04 se sostiene solo si el activo construido se publica
como Release propio con su `sha256`; esa copia, no la URL de Overture, es la
que hace re-derivable un numero publicado.

Subtipos correctos, tambien verificados: `theme=buildings/type=building` (no
`building_part`, que inflaria `bld_count`), `theme=transportation/type=segment`
y `theme=divisions/type=division_area`.

### 3. REPS y MEN no pueden entrar al activo (dos bloqueos independientes)

| | REPS salud | MEN educacion |
|---|---|---|
| Dataset | `c36g-9fc2` | `cfw5-qzt5` |
| Filas | 76.821 sedes | 588.334 (multi-anio) |
| Actualizado | 2026-04-17 | 2025-11-13 |
| Coordenadas | **ninguna** | **ninguna** |
| Llave geografica | `municipiosede` (DIVIPOLA) + direccion | `cod_dane_municipio` + direccion |
| Licencia | **CC BY-SA 4.0** | **CC BY-SA 4.0** |

**Bloqueo (a) — sin geometria.** Ninguno de los dos publica latitud/longitud.
Sin coordenadas no hay celda H3 a la que asignarlos. La espec preveia
geocodificar «la parte del REPS que viene sin coordenadas»; en realidad es el
dataset entero, y geocodificar 76.821 direcciones no es una tarea de la semana 2.

**Bloqueo (b) — copyleft incompatible.** Ambos son CC BY-SA 4.0, no «abierta
gov» como asumia la espec. CC BY-SA 4.0 y ODbL son **ambas** share-alike y
**mutuamente incompatibles**: cada una exige que el derivado se publique bajo
ella, y no existe licencia que satisfaga a las dos. Meter REPS en la misma
tabla que las edificaciones de Overture produce un `exposure_h3` que no se
puede licenciar bajo ninguna licencia.

**Decision aplicada:** `health_count` y `edu_count` por celda salen de
OpenStreetMap, la unica fuente con coordenadas. REPS y MEN pasan a ser
referencia de **completitud municipal** —cuantas sedes dice el registro oficial
que hay en el municipio X frente a cuantas tiene OSM— en una tabla aparte bajo
CC BY-SA. Esa comparacion es ademas mas honesta que un conteo: convierte el
hueco de OSM en una cifra publicada en vez de en un silencio.

**Guardia en codigo:** `resolve_bucket()` ahora rechaza la combinacion
ODbL + CC BY-SA 4.0 con un error explicito. La regla de los tres cubos por si
sola no atrapaba este caso, porque ambas licencias caen del lado
«redistribuible».

---

## Detalle por tarea

### T0.4 — Marco Geoestadistico Nacional (DANE) · resuelta

El Geoportal DANE publica su informacion geografica bajo **CC BY 4.0**: permite
uso comercial y redistribucion «en todos los medios y formatos actualmente
conocidos o por crearse», y pide citar *«Departamento Administrativo Nacional
de Estadistica - DANE: www.dane.gov.co»*.

Descarga directa verificada (HTTP 206, `application/zip`):

```
https://geoportal.dane.gov.co/descargas/mgn_2025/MGN2025_00_COLOMBIA.zip   3,39 GB
https://geoportal.dane.gov.co/descargas/mgn_2025/MGN2025_DPTO_POLITICO.zip 12,5 MB
https://geoportal.dane.gov.co/descargas/mgn_2025/MGN2025_CLASE.zip          120 MB
```

**Pendiente acotado:** existen entregas por nivel mucho mas livianas que el
archivo nacional, pero el nombre exacto del nivel municipal no se deduce
probando (`MPIO`, `MPIO_POLITICO`, `MUNICIPIO`… todos 404). Hay que leerlo del
geoportal antes del primer build: bajar 3,4 GB cada trimestre para quedarse con
1.100 poligonos municipales es desperdicio puro.

### T0.5 — REPS · resuelta en contra

Ver «Hallazgos» arriba. Dataset correcto identificado (`c36g-9fc2`,
*Registro Especial de Prestadores y Sedes de Servicios de Salud*), pero no
sirve para el proposito que la espec le daba.

### T0.6 — Sedes educativas MEN · resuelta en contra

Dataset nacional identificado (`cfw5-qzt5`,
*MEN_ESTABLECIMIENTOS_EDUCATIVOS_PREESCOLAR_BASICA_Y_MEDIA*). Ademas de los dos
bloqueos, tiene columna `a_o`: las 588.334 filas son registros por
establecimiento **y anio**, asi que habria que filtrar por el anio vigente
antes de contar nada.

### T1.2 — OurAirports · **resuelta** (23-ago-2026)

`https://davidmegginson.github.io/ourairports-data/airports.csv` responde
HTTP 200 con 12,7 MB. El texto que faltaba citar esta en dos sitios, ambos
leidos directamente:

- **Pagina de datos** (`https://ourairports.com/data/`): «All data is released
  to the Public Domain, and comes with no guarantee of accuracy or fitness for
  use».
- **Repositorio de descargas** (`github.com/davidmegginson/ourairports-data`):
  el `LICENSE` es **The Unlicense** integro — «This is free and unencumbered
  software released into the public domain… Anyone is free to copy, modify,
  publish, use, compile, sell, or distribute this software… for any purpose,
  commercial or non-commercial».

**Matiz que se deja escrito en vez de redondear:** The Unlicense habla de
*software*, y lo que aqui se reutiliza son *datos*. La declaracion que cubre el
caso es la de la pagina de datos, explicita sobre «all data»; el `LICENSE` la
respalda. Con las dos juntas la intencion no admite otra lectura, pero la
cobertura no viene del `LICENSE` solo.

Nota operativa: el repositorio pide expresamente **no abrir pull requests**;
las correcciones se hacen con una cuenta en ourairports.com y entran en el
volcado diario.

### GHS-POP · confirmada

Ambas variantes de la epoca 2025 sirven (HTTP 206): Mollweide 100 m
(`…_54009_100_V1_0.zip`, la del manifest) y WGS84 3 segundos de arco
(`…_4326_3ss_V1_0.zip`), esta ultima util si reproyectar desde Mollweide
resulta ser el cuello de botella de P0.

---

## Sigue abierto

| Tarea | Que falta |
|---|---|
| T0.2 (resto) | Congelar los **contenidos**: `cont_mmi.json` y rasters de Ground Failure, que necesita el polyfill H3. Lo congelado hoy es la estructura de productos y su historial de versiones |
| T0.9 (nueva) | Nombre del archivo MGN a nivel municipal: el nacional pesa 3,39 GB |
| T0.7 | Benchmark `exactextract` vs muestreo simple (<1 % en poblacion nacional) |
| T0.8 | Motor del mapa estatico: matplotlib+contextily vs MapLibre headless |
| T1.1 | Formatos y terminos de las redes sismologicas nacionales |
| T1.3 | Plantillas HDX y validacion de las cabeceras HXL |
| T2.1–T2.4 | Todo lo de la brigada de imagen (Fase 2) |
| T3.1 | Redistribucion de embeddings (Fase 3) |
