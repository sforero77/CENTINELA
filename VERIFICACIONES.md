# Registro de verificaciones

Cierre de las tareas ⚠️ de §8 de la especificación. Cada entrada dice **como**
se verifico, no solo el resultado: una verificación que no se puede repetir no
sirve de nada dentro de seis meses.

Rondas: **23 de agosto de 2026** (fuentes de §8) y **auditoría completa del registro**, misma fecha. Método: peticiones reales a las
fuentes primarias (listados S3, índices HTTP, API de Socrata de datos.gov.co,
paginas de licencia de los publicadores).

---

## Resumen

### Ronda 2 — auditoría del registro completo

Criterio de admisión aplicado a cada fuente: **sin geometría no sirve**. Un
registro administrativo sin coordenadas no se puede asignar a una celda H3, por
buena que sea su cobertura.

| Fuente | Geometría | Veredicto |
|---|---|---|
| USGS feeds / detail / ShakeMap / Ground Failure / PAGER | sí | ✅ probados contra el evento real de Chocó |
| GHS-POP, WorldPop, Overture, MGN-DANE | sí | ✅ (ronda 1) |
| REPS (`c36g-9fc2`), MEN (`cfw5-qzt5`) | **no** | ❌ fuera del activo |
| **API** de healthsites.io | sí | ❌ exige API key, viola O4 |
| HOTOSM `hotosm_<iso>_health_facilities` (HDX) | sí | ✅ **sustituye al REPS** |
| HOTOSM `hotosm_<iso>_education_facilities` (HDX) | sí | ✅ **sustituye al MEN** |
| healthsites.io publicado en HDX | sí | ✅ complemento sin credenciales |
| COD-AB de OCHA `cod-ab-<iso3>` | sí | ✅ **cubre los 19 países de LATAM** (ronda 4) |

### Ronda 1 — tareas ⚠️ de §8

| Tarea | Estado | Resultado |
|---|---|---|
| T0.4 MGN-DANE | ✅ resuelta | **CC BY 4.0**, uso comercial y redistribucion permitidos |
| T0.5 REPS | ⚠️ resuelta en contra | Sin coordenadas y **CC BY-SA 4.0**: fuera del activo |
| T0.6 MEN | ⚠️ resuelta en contra | Ídem REPS |
| T1.2 OurAirports | ✅ resuelta | Dominio público citado: página de datos + The Unlicense |
| Overture release | ✅ corregida | `2026-08-19.0`; el bucket solo guarda **dos** releases |
| WorldPop age-sex | ✅ mejora | Hay desglose **para 2025**: cae un supuesto de la espec |
| WorldPop total | ✅ corregida | Ruta real hallada |
| GHS-POP | ✅ confirmada | Ambas variantes sirven |

---

## Ronda 3 — validación de datos antes de construir P0

No basta con que la URL responda: hay que abrir el archivo y comprobar que dice
lo que se espera. Esta ronda descargo los datos y los midió.

### El total nacional cuadra

GHS-POP E2025 recortado por el límite oficial del MGN 2025 da **52.601.276**
habitantes para Colombia. El DANE proyecta **~53 millones** para 2025. La
diferencia es **-0,75 %**, dentro del ±1 % que exige el assert de §6.4. Es la
primera evidencia de que la cadena poblacional sirve para lo que se quiere.

### Contratos medidos, no supuestos

| Fuente | Lo medido |
|---|---|
| GHS-POP tesela | `ESRI:54009`, 10.000×10.000 px a 100 m, `float64`, **nodata = -200** |
| MGN 2025 dptos | 33 registros, `dpto_ccdgo` VARCHAR con el cero inicial intacto, EPSG:4326 |
| Overture buildings | `id` (GERS), `bbox` STRUCT(xmin,xmax,ymin,ymax), `geometry` OGC:CRS84 |
| HOTOSM salud COL | 9.618 elementos, geometrías **mixtas** POINT/POLYGON/MULTIPOLYGON |
| OurAirports | 738 aeropuertos en Colombia, **todos** con coordenadas |

El nodata de GHS-POP importa: son unos **22 millones de celdas por tesela**, todo
océano. Sumar sin enmascarar da población negativa y dispara el assert de calidad
sobre datos que en realidad están sanos. Y las geometrías mixtas de HOTOSM
significan que el conteo por celda tiene que pasar por centroide, no asumir puntos.

### Descargar el subconjunto, no el mundo

Dos fuentes son inmanejables enteras y ambas tienen una vía de escape que hubo
que encontrar:

**GHS-POP**: el mosaico global pesa **5,25 GB**. El JRC publica el mismo producto
en **375 teselas**; Colombia necesita **nueve**, que suman **93 MB**. El esquema de
teselado (origen en x=-18.041.000, y=9.000.000, teselas de 1.000 km) se derivo y
se verifico contra la georreferenciacion real de una tesela descargada.

**Overture**: el tema `buildings` son **512 ficheros, 277 GB y 2.529 millones de
edificaciones**. Colombia toca **once**. El `collection.json` del catálogo STAC
(155 KB) trae el bbox de cada fichero, así que la selección no cuesta leer datos.
Dentro de cada fichero, el filtro sobre la columna `bbox` poda por row-group:
**contar las edificaciones de Quibdó en un fichero remoto de 5 millones de filas
toma 2,2 segundos**. Sin esto P0 no sería viable, así que dejo de ser un detalle
de implementación.

### 9. La trampa del catálogo STAC de Overture

El estándar STAC dice que `extent.spatial.bbox[0]` es la **unión** de las
sub-extensiones, y que las reales empiezan en el índice 1. Overture no hace eso:
publica **512 entradas para 512 ficheros**, y la `[0]` es el bbox del primer
fichero.

Aplicar la lectura del estándar —saltarse la primera— desplaza todo un puesto y
hace leer los ficheros equivocados. Y como los ficheros vecinos cubren zonas
adyacentes, el resultado sería plausible: un conteo de edificaciones que parece
razonable y esta mal. Se detecto al cruzar los bboxes del catálogo con la
extensión real medida sobre los ficheros con DuckDB.

`parse_collection()` falla explícitamente si el conteo deja de ser 1:1, porque
esa es la única señal de que la suposición dejo de valer.

### 10. Overture publica PMTiles por release

`https://tiles.overturemaps.org/<release>/<tema>.pmtiles`. Las capas de contexto
del visor no necesitan `tippecanoe`: ya están teseladas. Las de CENTINELA
—coropletas de exposición e impacto— siguen siendo propias, porque son datos
nuestros.

---

## Ronda 4 — cobertura regional y lo que destapo (23-ago-2026)

El proyecto es para LATAM, así que la pregunta no es si las fuentes existen para
Colombia sino si existen **para todos**. Una petición real por fuente y país
sobre los 19 de LATAM hispanohablante más Brasil: ARG, BOL, BRA, CHL, COL, CRI,
CUB, DOM, ECU, GTM, HND, MEX, NIC, PAN, PER, PRY, SLV, URY, VEN.

### El camino esta despejado para los 19

| Fuente | Cobertura |
|---|---|
| WorldPop age-sex R2025A 2025 | **19/19**, con las 20 bandas (00…90) cada uno |
| WorldPop total constrained 2025 | **19/19** |
| `cod-ab-<iso3>` (OCHA) | **19/19**, todos CC BY-IGO |
| `hotosm_<iso>_health_facilities` | **19/19**, todos ODbL |
| `hotosm_<iso>_education_facilities` | **19/19**, todos ODbL |

No hay ningún país sin camino. Eso convierte Fase 1 en escribir manifests, no en
buscar datos.

### Dos irregularidades del COD-AB

**Cinco países no publican GeoJSON** y caen a SHP: COL, ARG, BRA, PRY, URY.

**Colombia publica cuatro recursos SHP en el mismo dataset**, y el resolutor
tomaba el primero de cada formato: `MGN2024_URB_SECCION.zip`, 48 MB de
**secciones urbanas** en vez de municipios. El que se quiere es
`COL Administrative Divisions Shapefiles.zip`. De ahí el campo `hdx_resource`
del manifest: un dataset con varios recursos del mismo formato tiene que fijar
cual, igual que fija el vintage, y el resolutor falla si el fragmento no
identifica exactamente uno.

### Las columnas del COD-AB no son las que documenta HDX

Leídas abriendo `ven_admin2.shp` con DuckDB, no de la documentación:
`adm2_pcode`, `adm2_name`, `adm1_pcode`, `adm1_name` — en minúsculas, y **no**
los `ADM2_PCODE` / `ADM2_ES` de las entregas antiguas. 336 registros, que
cuadra con los 335 municipios de Venezuela más el Distrito Capital.

La caja envolvente del país se midió sobre ese mismo archivo
(−73,3691..−59,7411 / 0,6346..12,4988) en vez de estimarla. El extremo norte lo
pone Dependencias Federales; el COD-AB no incluye la Isla de Aves.

Pendiente para el mantenedor de país: los topónimos salen mal codificados
(«Falc?n» por «Falcón»). Hay que resolverlo antes de publicar un reporte de
Venezuela, porque esos nombres se imprimen.

### El solape entre HOTOSM y healthsites.io: 96,6 %

El catálogo de capas declaraba la agregación de salud como «conteo de puntos
por celda, **deduplicado por proximidad**». La deduplicacion estaba declarada y
**no implementada**: las dos fuentes se sumaban.

Medido sobre Colombia:

| | |
|---|---|
| HOTOSM `hotosm_col_health_facilities` | 9.618 puntos |
| healthsites.io vía HDX | 8.443 puntos |
| De healthsites, a <20 m de un punto de HOTOSM | **8.152 (96,6 %)** |
| a <50 m | 8.181 (96,9 %) |
| a <100 m | 8.194 (97,1 %) |
| **Suma sin deduplicar** | **18.061** |

Las dos derivan de OpenStreetMap, así que el solape era esperable en cuanto se
midió. Sumadas daban **casi el doble** de las sedes que hay, y ninguna guardia
lo habría notado: la cifra es positiva y del orden correcto. Que el umbral
apenas mueva el solape entre 20 y 100 m confirma que se trata de los mismos
establecimientos y no de vecindad casual; se fija en **20 m**.

La corrección es la que el catálogo ya prometía: las fuentes entran en el orden
del manifest, la primera completa, y cada siguiente aporta solo lo que no esta a
menos de 20 m de un punto ya aceptado. healthsites aporta así unas 290 sedes
reales en vez de 8.443 duplicadas.

### ¿Son estas las mayores fuentes posibles? Comprobado, y falta una

**Edificaciones y vías: si.** Overture no es «una fuente más»: es la fusión de
las tres mayores colecciones abiertas. Medido leyendo la columna `sources` de
las edificaciones de Quibdó en el parquet remoto:

| Origen | Edificaciones |
|---|---:|
| OpenStreetMap | 22.176 |
| Microsoft ML Buildings | 7.915 |
| Google Open Buildings | 5.092 |

**Población: si, y con el release correcto.** El listado del FTP del JRC
confirma que `GHS_POP_GLOBE_R2023A` sigue siendo el último global; el
`GHS_POP_ARCTIC_R2025A` que aparece al lado es solo del Ártico. Dentro de
R2023A, la época E2025 a 100 m es la más fina útil (E2030 existe, pero proyecta
a 2030). WorldPop R2025A también es el último.

**Más resolución no habría sido mejor.** Existe el HRSL de Meta a **30 m**,
CC BY, publicado en HDX para Colombia — once veces más fino. Su vintage es
**2019**. A celda H3 r8 (~0,74 km²) un ráster de 100 m ya aporta ~74 píxeles por
celda, así que el detalle adicional se promedia y desaparece, mientras que seis
años de desactualizacion no. Cambiar habría sido regalar vigencia a cambio de
nada. Por la misma razón **r8 no es una limitación**: es la escala que
corresponde a entradas de 100 m; bajar a r9 multiplica por siete las celdas para
representar información que la fuente no tiene.

**Lo que si faltaba: GHS-BUILT-S.** La debilidad documentada del conteo de
edificaciones son los huecos de OSM en asentamientos informales y zona rural
dispersa — donde vive la población más expuesta. GHS-BUILT-S deriva de
Sentinel-2 y Landsat, así que no tiene ese hueco. Comparte retícula, época,
proyección y licencia con GHS-POP (verificado: la tesela R9_C11 responde con el
mismo esquema de nombres), de modo que reutiliza el selector de teselas y cuesta
unos 90 MB por país. Entra como columna `built_m2` y convierte la bandera
`revisar_sin_edificios` en una cifra: `construido_no_mapeado`.

### La ventana del disparador cortaba países cubiertos

Al medir las cajas de los 19 países con `division_area` de Overture salió que
`LATAM_BBOX` —el filtro de RF-01— dejaba fuera territorio de países que el
sistema dice cubrir:

| | Llega a | La ventana cortaba en |
|---|---|---|
| México (Isla Guadalupe, Revillagigedo) | 118,65°O | 118,0°O |
| Chile (Cabo de Hornos, Diego Ramírez) | 56,78°S | 56,0°S |
| Brasil (Fernando de Noronha, ~3.000 hab.) | 32,42°O | 34,0°O |

Un sismo relevante ahí no habría fallado: habría dejado de existir para el
sistema, sin rastro que revisar. Chile es el caso serio — la zona de fractura de
Shackleton produce sismos justo en ese margen.

Nueva ventana: `lon -119,0..-32,0 / lat -57,5..33,0`. El límite este se detiene
antes del archipiélago de San Pedro y San Pablo (29,35°O), que se asienta
**sobre la dorsal mesoatlantica**: estirar la ventana hasta el compraria
sismicidad oceanica frecuente y sin población a cambio de una estación
cientifica con unas pocas personas.

### GHS-POP sobrestima Venezuela en 1,8 millones de personas

El hallazgo que Venezuela existía para producir, y la razón de haber elegido la
ONU como referencia en vez del INE.

| | |
|---|---:|
| GHS-POP E2025 recortado por el COD-AB | **30.313.601** |
| ONU, World Population Prospects 2025 | 28.516.896 |
| **Desvío** | **+6,30 %** |
| Colombia, para comparar | -0,11 % |

La primera corrida de `centinela country VEN` fallo con la tolerancia en 5 %, y
**eso fue el assert funcionando**: detecto una divergencia real entre dos
modelos de población en un país sin censo desde 2011. Se subio a 8 % para poder
construir el activo, no porque la divergencia deje de importar.

**Por que divergen.** GHS-POP R2023A parte de la ronda censal de 2010 y
desagrega con volumen construido. Las casas de quien emigro siguen en pie y
siguen pesando en el modelo. WPP si incorpora el saldo migratorio. Para un
sistema de exposición la diferencia no es academica: sobrestimar la población de
una zona infla la cifra que lee una sala de crisis.

**El contraste que no cierra la cuestión.** El ráster total de WorldPop 2025
constrained suma 28.460.161, a -0,20 % de WPP. Parece confirmar a la ONU y no
confirma nada: los productos "constrained" de WorldPop **se calibran contra los
totales nacionales de WPP**, así que coincidir es como están construidos. La
fuente que se aparta es GHS-POP, que es justamente de donde sale la cifra
principal del reporte.

**Consecuencia operativa.** Cualquier reporte de un evento venezolano hereda ese
+6,30 %. Un mantenedor de país con proyecciones del INE posteriores a 2011 puede
sustituir la referencia y estrechar la tolerancia.

### Una geometría rota deja el país entero en NaN

Ecuador construyó y publicó un activo con `road_km: NaN`. La cadena entera:

1. Overture trae una geometría degenerada cuya longitud esferoidal no es finita.
2. El filtro `ST_Length_Spheroid(geometry) > 0` descarta el cero y el NaN, pero
   **no el infinito**.
3. `sum()` propaga: un solo segmento roto y el total nacional es NaN.
4. `validate_layer_coverage` no lo detuvo porque comprobaba `if not valor`, y
   **`bool(float('nan'))` es `True`**. Para la guardia, la capa "aportaba".

Un NaN es peor que un cero: el cero es una afirmación falsa pero acotada, y el
NaN contamina toda operación que lo toque hasta acabar impreso en el reporte.

Corregido midiendo: Ecuador pasa de `NaN` a **133.385 km**. La guardia exige
ahora que el valor sea finito, y la agregación descarta longitudes infinitas o
mayores de 2.000 km — Overture parte las vías en segmentos mucho más cortos, así
que por encima de eso no hay carretera sino geometría rota.

### El sesgo de población era del pipeline, no de GHS-POP

Medidos los 18 países, los desvios de GHS-POP frente a World Population
Prospects van de **-0,80 % (Chile) a +6,59 % (Paraguay)**, y quince de dieciocho
son positivos. Eso no es dispersión: es un sesgo con dirección.

Dos explicaciones se propusieron y **las dos eran falsas**:

1. *"Se desvian los países sin censo reciente."* Uruguay censo en 2023 y se
   desvia +6,28 %, casi lo mismo que Venezuela.
2. *"GHS-POP sobrestima de forma sistemática."* Se formulo viendo quince
   positivos seguidos; faltaban Chile, México y Colombia —cuyas corridas se
   lanzaron antes de que el workflow pusiera el ISO3 en el nombre— y los tres
   resultaron ser los negativos.

Lo que si ordena los datos es **cuanta frontera tiene cada país en proporción a
su área**. Se instrumento el rescate de celdas fronterizas para medirlo, y
Paraguay —interior, todo frontera— lo confirmo:

| | |
|---|---:|
| Población rescatada | 459.518 |
| Total del activo | 7.474.922 |
| **Fracción rescatada** | **6,147 %** |
| Desvío frente a la ONU | 6,585 % |
| **Total descontando el rescate** | **7.015.404** |
| Referencia de la ONU | 7.013.078 |
| **Desvío corregido** | **+0,03 %** |

**El rescate explica el 93 % del exceso.** Sin el, la cifra clava la referencia.

La causa es geometrica y evidente una vez medida: la cota del rescate es 0,02°
(~2,2 km), y en un país interior **cada kilómetro de perímetro es frontera**, de
modo que se reclama una franja de 2,2 km de Brasil, Argentina y Bolivia
alrededor de todo el país. Chile y México salen negativos porque su rescate es
sobre todo **mar**, que es el caso para el que se diseño y donde es correcto.

Es el mismo fallo que ya se corrigio una vez para Colombia —rescatar sin acotar
llevo la población nacional de 52,6 a 167 millones— pero en pequeño, dentro de
la cota, y por eso invisible durante meses.

**La corrección:** rescatar una celda solo si su centro no cae dentro de otro
país. Una celda cuyo centro esta en tierra brasilena es de Brasil, por cerca que
este de la línea. Se resuelve con los polígonos de país de `division_area` de
Overture, los mismos ficheros que se leyeron para medir las cajas envolventes.

#### Medida, en dos intentos

El primero **no arreglo nada y no fallo**: Paraguay volvio a salir con los
mismos 459.518 rescatados. La tabla de vecinos se había cargado con **cero
polígonos** y el build siguio adelante. La consulta corrio, devolvio cero filas,
nadie se quejo — el modo de fallo que este proyecto persigue, cometido por el
código que lo persigue.

La causa: el filtro de poda de Overture comprueba que la **esquina inferior
izquierda** del rasgo caiga dentro de la caja del país. Vale para un edificio o
un tramo de vía, que son más pequenos que la caja. Deja de valer para un país:
la esquina de Brasil esta en -73,99, muy al oeste de la caja paraguena, aunque
Brasil ocupe media caja. Medido contra Overture 2026-08-19.0:

| Poda | Países devueltos en la caja de Paraguay |
|---|---|
| Contención | PY |
| **Interseccion** | **AR, BO, BR**, PY, FJ |

Como el país propio se excluye por definición, con contención la tabla quedaba
vacía. (FJ aparece porque Fiji cruza el antimeridiano y su caja abarca el globo;
no estorba, ningún punto paraguayo cae dentro de un polígono fiyiano.)

Corregido a interseccion, y el caso "cero vecinos" pasa de INFO a WARNING: en
LATAM solo Cuba no toca a nadie por tierra, y hasta su caja alcanza a Haití.

#### Resultado

| Paraguay | Antes | Después |
|---|---:|---:|
| Celdas rescatadas | 1.945 | **23** |
| Población rescatada | 459.518 | **112** |
| Fracción rescatada | 6,147 % | **0,002 %** |
| Total nacional | 7.474.922 | **7.015.517** |
| **Desvío frente a la ONU** | **+6,585 %** | **+0,035 %** |

La prediccion era 7.015.404 —el total menos el rescate medido antes— y salieron
7.015.517: los 113 de diferencia son el rescate legítimo que queda.

### Simplificar la geometría administrativa: control sobre Uruguay

El COD-AB de Chile pesa más de 182 MB y `h3_polygon_wkt_to_cells` recibe la
geometría como **texto**: el `ST_AsText` de una sola provincia de Magallanes
agoto los 12,4 GB del runner. Se simplifica al cargar, con tolerancia 0,0005
grados (~55 m).

La pregunta es que se pierde. Reconstruido Uruguay con y sin simplificación, el
mismo día y con el mismo código por lo demás:

| | Sin simplificar | Simplificado |
|---|---:|---:|
| Celdas | 150.314 | 150.314 |
| Población | 3.429.034 | 3.429.034 |
| Edificaciones | 2.418.920 | 2.418.920 |
| Superficie construida | 389.300.479 | 389.300.479 |
| Kilómetros de vía | 89.090 | 89.090 |
| Sedes de salud | 1.149 | 1.149 |
| Sedes educativas | 4.433 | 4.433 |
| Fracción rescatada | 0,934 % | 0,934 % |
| Desvío | +1,3102 % | +1,3102 % |

**Identicas hasta la última unidad.** Es lo que tenía que pasar: el reparto
asigna por el centro de la celda y una celda r8 mide unos 740 m, así que mover
una frontera 55 m solo puede cambiar de municipio las celdas cuyo centro caiga
casi encima de la línea — y esas pasan al vecino, no al vacío.

Lo que este control **no** prueba es la distribución municipal, que es donde el
efecto vive por definición. Prueba lo que importa más: que no se pierde nadie.

### Reemitir el backtest del Chocó: cuanto corregian los arreglos

El reporte publicado el 23-ago-2026 se calculó contra `col-v0.4`, el activo
anterior a cablear las tres capas sueltas, a subir las bandas de edad hasta 90 y
a añadir GHS-BUILT-S. Reemitido contra `col-v0.5` con `--reprocesar`:

| Cifra en MMI≥7 | Publicado | Reemitido | |
|---|---:|---:|---|
| Kilómetros de vía | 1.397,7 | **8.502,9** | ×6,1 |
| Población 65+ | 271.688 | **289.257** | +6,5 % |
| Edificaciones | 444.281 | 444.424 | +143 |
| Sedes de salud | 512 | 518 | +6 |
| Sedes educativas | 997 | 998 | +1 |
| Superficie construida | — | 69,8 km² | capa nueva |
| **Población en MMI≥7** | **2.415.793,459** | **2.415.793,459** | **idéntica** |

Dos cosas que conviene no mezclar.

**La cifra principal no se movio ni un bit.** El golden de G1 la fija con ±0,5 %
y pasa exacto. Tiene sentido: el área MMI≥7 de este evento es interior
—Pereira, Buenaventura, Armenia, Tuluá, Dosquebradas— y ni el rescate de
frontera ni el arreglo del multipoligono la tocan.

**Los kilómetros de vía estaban seis veces cortos.** Un reporte publicado decía
1.397 km cuando eran 8.503. Nadie lo habría notado: 1.397 km es una cifra
perfectamente creíble para una zona de intensidad. Es el cero silencioso en su
versión más peligrosa — no un cero, un número.

### El reparto no veia las islas, y el rescate lo tapaba

`h3_polygon_wkt_to_cells` devuelve **cero** celdas ante un MULTIPOLYGON. No la
primera parte: cero. Medido:

| Geometría | Celdas r8 devueltas |
|---|---:|
| `POLYGON` (cuadrado A) | 22.365 |
| `POLYGON` (cuadrado B) | 20.160 |
| `MULTIPOLYGON(A, B)` | **0** |
| `MULTIPOLYGON(A, B)` con `ST_Dump` | 42.525 |

Un municipio con una isla, un exclave o un trozo separado por un rio es un
MULTIPOLYGON. Ninguno de ellos aportaba una celda al reparto por contención.

**Nadie lo vio porque el paso siguiente lo tapaba.** Esas celdas quedaban sin
asignar, caian dentro del país, y el rescate las mandaba al municipio más
cercano — que para un punto dentro del municipio esta a distancia cero, o sea
el correcto. La cifra nacional salía bien por un camino que no era el suyo.

Lo delato Uruguay al instrumentar el embudo del rescate:

    candidatas: 896.936 → junto al país: 6.538 → descartadas por vecino: 909
    pop_rescatada_pct: 48,026 %

**El 48 % de la población de Uruguay entraba por el rescate**, más que Chile con
sus 4.000 km de costa. No era costa: eran departamentos multipoligono entrando
enteros por la puerta de atrás.

El coste no era la cifra, era el marcador. `rescatada = TRUE` significa "esto es
una aproximacion, auditalo", y puesto sobre medio país no significa nada. Y deja
al reparto dependiendo de que el rescate exista, que es corrección por
accidente: acotar más el rescate —cosa que se hizo dos veces esta semana— se
habría llevado medio país por delante sin avisar.

#### Chile responde la pregunta que quedaba abierta

Se afirmo, viendo que Chile rescataba el 31 % de su población con un desvío
correcto, que ese rescate era **mar** y que por eso la magnitud del rescate no
distinguía lo correcto de lo contaminado. La primera mitad era falsa.

Reconstruido con el reparto viendo los multipoligonos:

| Chile | Antes | Después |
|---|---:|---:|
| Población rescatada | 6.126.336 | **145.195** |
| Fracción rescatada | 31,097 % | **0,737 %** |
| Desvío frente a la ONU | -0,80 % | -0,85 % |

Aquel 31 % **no era mar**: eran comunas multipoligono entrando enteras por la
puerta de atrás, igual que en Uruguay. Y el desvío apenas se mueve —cinco
centesimas— porque la población ya estaba llegando, solo que por un camino que
no era el suyo.

La conclusión de fondo aguanta y sale reforzada: lo que distingue un rescate
correcto de uno contaminado no es cuanto se rescata sino **sobre que esta la
celda**. Lo que no aguantaba era el ejemplo con el que se ilustro.

(El reparto de Chile necesito 1.201 teselas para sus 56 provincias, y seis
intentos: cuatro OutOfMemory, uno por duplicados al simplificar mal, y este.)

#### No era solo el marcador: se perdian datos

El rescate solo mira celdas **con población** (`FROM pop_h3`). Una celda dentro
de un municipio multipoligono con un colegio, una vía o unas edificaciones pero
sin población censada no entraba por ninguno de los dos caminos: ni por el
reparto —que no veia el multipoligono— ni por el rescate. Desaparecia del activo.

Medido en Uruguay, misma corrida antes y después del `ST_Dump`:

| | Antes | Después | Recuperado |
|---|---:|---:|---:|
| Celdas | 145.488 | 150.314 | **+4.826** |
| Edificaciones | 2.411.764 | 2.418.920 | **+7.156** |
| Kilómetros de vía | 86.867 | 89.090 | **+2.223** |
| Población | 3.426.966 | 3.429.034 | +2.068 |
| Sedes educativas | 4.430 | 4.433 | +3 |
| Sedes de salud | 1.149 | 1.149 | 0 |

Y la fracción rescatada cae de **48,026 % a 0,934 %**, que es lo que siempre
debio medir: costa y frontera, no departamentos enteros.

El desvío nacional apenas se mueve (+1,25 % → +1,31 %), lo que confirma que la
población ya estaba llegando —por el camino equivocado— y que lo que faltaba era
sobre todo infraestructura sin población alrededor.

Es el mismo perfil que el fallo del filtro de celdas que perdio 1.664 colegios
de Colombia: lo que se pierde no es donde vive la mayoría, es la periferia.

Consecuencia: **la fracción rescatada de los diecinueve hay que remedirla**.
Hasta ahora no media lo que se creia que medida, y la afirmación "Chile rescata
el 31 % porque su rescate es mar" esta sin comprobar por el mismo motivo.

### Chile: dos muertes por memoria, un solo error de diseño

Corregido Paraguay, Chile tumbo el build dos veces. La primera con
`OutOfMemoryException` de DuckDB (12,3 de 12,4 GB), la segunda llevandose el
proceso entero por delante — el paso salió `cancelled`, sin traza.

**No era el tamaño del país.** Los dos filtros del rescate vivian en el mismo
`WHERE`, así que el planificador no garantizaba cual evaluaba primero. Y el
conjunto de partida no son las celdas costeras de Chile: son **todas** las
celdas con población del recorte de GHS-POP que el polyfill dejo fuera, o sea
media Argentina, Bolivia y Perú. Millones de puntos contra un multipoligono
continental.

Separado en cuatro pasos materializados —candidatas, acotar al país, descartar
vecinos, asignar municipio— al descarte solo llegan las que sobrevivieron a la
cota.

Y los polígonos se simplifican al cargarlos, con tolerancia 0,001 grados
(~110 m), veinte veces más fina que la cota del rescate. Medido sobre la caja de
Chile con Overture 2026-08-19.0:

| Vecino | Vertices tras recortar y simplificar |
|---|---:|
| AR | 7.698 |
| BO | 735 |
| PE | 60 |
| BR, NZ, FJ | 0 (su interseccion con la caja es vacía) |
| **Unión** | **8.317** |

60.000 puntos contra esa unión: **5,2 s**.

### Overture publica dos polígonos por país, no uno

`division_area` con `subtype='country'` devuelve **dos filas** por país: la
terrestre (`is_land`) y la de aguas territoriales (`is_territorial`). Medido
sobre la caja de Chile:

    AR  is_land=False is_territorial=True    AR  is_land=True is_territorial=False
    PE  is_land=False is_territorial=True    PE  is_land=True is_territorial=False
    BO  is_land=True  is_territorial=True

Cargar las dos rompe justo el caso para el que existe el rescate: las aguas
peruanas llegan hasta la frontera de Arica, así que una celda del Pacífico
frente a la costa chilena caería "dentro de Perú" y se descartaria con su
población dentro. El mar no es de nadie a estos efectos.

(Bolivia sale marcada con las dos, siendo interior. No estorba: se filtra por
`is_land`, que en su caso es cierto.)

### El COD-AB publica dos nomenclaturas, no una

Ecuador fue el primer país construido con el COD-AB como única fuente
administrativa, y fallo:

```
ecu_adm_adm2_2024.shp no trae las columnas ['adm2_name', 'adm1_name'].
Tiene: ['adm0_es', 'adm0_pcode', 'adm1_es', 'adm1_pcode', 'adm2_es', 'adm2_pcode', ...]
```

El código va siempre en `adm2_pcode`, pero el nombre depende de cuando se genero
la entrega: `adm2_name` en las recientes —medido sobre Venezuela— y `adm2_es` en
las antiguas. Con diecinueve países, descubrir cada variante fallando no escala,
así que el mapeo admite varias y gana la primera cuyas cuatro columnas existan.

### El release de Overture sigue vigente

`2026-08-19.0` responde y es el último; `2026-07-22.0` también. Confirmado que
el bucket conserva **dos**, así que el vintage fijado caduca solo. La prueba
nocturna de contrato ahora lo vigila.

---

## Hallazgos de la ronda 2

### 4. Un bug de selección de versión, cazado por las fixtures reales

El caso que justifica congelar productos reales en vez de sinteticos.

En `us6000t7zp` (Venezuela, M7.5) el ShakeMap va por la versión **14**. Con
`includesuperseded=true` se ven las catorce, y sus pesos son estos:

| Versión | Fecha | `preferredWeight` |
|---|---|---|
| v1–v4 | junio 2026 | **232** |
| v13–v14 | agosto 2026 | **228** |

El parser ordenaba por `preferredWeight` y elegía **v4**: un ShakeMap de hace
mes y medio. El reporte habría salido con cifras equivocadas, ninguna prueba
habría fallado y nada en la salida habría delatado el problema.

`preferredWeight` desempata **contribuidores** (`us` frente a `atlas` o una red
regional), no versiones de un mismo contribuidor. El criterio correcto, ya
implementado: descartar `DELETE`, elegir contribuidor por peso, y dentro de el
la entrada más reciente por `updateTime`. Verificado contra la respuesta
autoritativa de ComCat para los tres eventos: v7, v14 y v9.

La regresión vive en `tests/golden/test_g2_venezuela.py::test_no_se_elige_una_version_obsoleta`,
y comprueba primero que la fixture siga reproduciendo la trampa — una prueba de
regresión que deja de reproducir el caso es peor que no tenerla.

### 5. `includesuperseded=true` funciona directo en FDSN

La espec asumia que recuperar el historial de versiones requeria `libcomcat`.
No: el parámetro funciona sobre el endpoint FDSN y devuelve todas las versiones
de cada producto. Una dependencia menos en el procedimiento de congelado.

### 6. T0.1 resuelta: los tres eventos identificados

| Evento | `usgs_id` | Cuando | Detalle |
|---|---|---|---|
| Chocó | `us6000tjl2` | 2026-08-10T12:34:28Z | M7.4, **110 km**, PAGER rojo, ShakeMap v7 |
| Catia La Mar | `us6000t7zp` | 2026-06-24T22:05:04Z | M7.5, 10 km, ShakeMap v14 |
| San Felipe | `us6000t7zc` | 2026-06-24T22:04:31Z | M7.2, 10 km, ShakeMap v9 |

Dos cosas que la espec no anticipaba. Los eventos de Venezuela están separados
por **32,2 segundos** y 145 km: ese es el «evento doble» de G2, y el sistema debe
producir dos reportes con áreas de intensidad solapadas sin fusionarlos. Y Chocó
fue **profundo** (110 km) pero **si** tiene Ground Failure, así que G3 no puede
definirse como «evento profundo» — lo que hay que probar es la ausencia del
producto, venga de donde venga.

### 7. La URL de HOTOSM cambia de forma según el país

Para la misma capa lógica `health_facilities` conviven al menos tres patrones:

```
COL -> production-raw-data-api.s3.amazonaws.com/ISO3/COL/health_facilities/…
MEX -> s3.dualstack.us-east-1.amazonaws.com/production-raw-data-api/ISO3/MEX/health_facilities/points/…
PER -> export.hotosm.org/downloads/<uuid>/…
```

Adivinar la ruta funciona para unos países y falla para
dos — es decir, funciona hasta que alguien agrega el país que no encaja, y falla
en producción, no en CI. El identificador estable es el **nombre del dataset**;
la URL se resuelve por la API de CKAN de HDX en cada build
(`pipelines/common/hdx.py`).

### 8. COD-AB cubre los siete países de Fase 1 (ampliado a 19 en la ronda 4)

`cod-ab-col`, `cod-ab-mex`, `cod-ab-per`, `cod-ab-ecu`, `cod-ab-chl`,
`cod-ab-ven` y `cod-ab-gtm` existen, todos **CC BY-IGO**, todos con shapefile o
geodatabase. Para Colombia el COD es el propio MGN del DANE reempaquetado, así
que no aporta geometría nueva; su valor esta en Fase 1, donde evita que cada
mantenedor de país tenga que ingeniar el geoportal nacional de turno solo para
obtener adm1/adm2.

---

## Hallazgos que cambian el diseño

### 1. WorldPop publica estructura etaria para 2025 (mejora)

**Lo que decía la espec (§2.2):** el desglose por edad y sexo solo existe para
2020, de donde salía la limitación documentada *«proporciones de 2020 aplicadas
sobre totales 2025 de GHS-POP (supuesto de estructura estable)»*, declarada en
los metadatos de cada reporte.

**Lo verificado:** el release `Global_2015_2030/R2025A` publica age-sex
constrained por época anual hasta 2026. Para Colombia, 2025, 100 m constrained
hay **62 rasters** (`col_f_00`…`col_m_80`, más los totales `col_T_F` y
`col_T_M`).

```
https://data.worldpop.org/GIS/AgeSex_structures/Global_2015_2030/R2025A/2025/COL/v1/100m/constrained/
```

**Consecuencia:** el supuesto de estructura etaria estable desaparece. Es una
limitación menos que declarar en cada reporte, y la cifra de población de 65+
en MMI≥7 —una de las más sensibles del producto— deja de arrastrar cinco años
de desfase.

### 2. Overture conserva solo dos releases (riesgo nuevo)

**Lo verificado:** el listado del bucket, no truncado, contiene exactamente dos
prefijos: `release/2026-07-22.0/` y `release/2026-08-19.0/`.

**Consecuencia:** fijar el release explícito —decisión correcta y que se
mantiene— da reproducibilidad **del cálculo**, no **de la descarga**. Pasados
unos dos meses la URL del manifest deja de existir y nadie puede rehacer el
build desde cero. RNF-04 se sostiene solo si el activo construido se publica
como Release propio con su `sha256`; esa copia, no la URL de Overture, es la
que hace re-derivable un número publicado.

Subtipos correctos, también verificados: `theme=buildings/type=building` (no
`building_part`, que inflaria `bld_count`), `theme=transportation/type=segment`
y `theme=divisions/type=division_area`.

### 3. REPS y MEN no pueden entrar al activo (dos bloqueos independientes)

| | REPS salud | MEN educación |
|---|---|---|
| Dataset | `c36g-9fc2` | `cfw5-qzt5` |
| Filas | 76.821 sedes | 588.334 (multi-anio) |
| Actualizado | 2026-04-17 | 2025-11-13 |
| Coordenadas | **ninguna** | **ninguna** |
| Llave geografica | `municipiosede` (DIVIPOLA) + dirección | `cod_dane_municipio` + dirección |
| Licencia | **CC BY-SA 4.0** | **CC BY-SA 4.0** |

**Bloqueo (a) — sin geometría.** Ninguno de los dos publica latitud/longitud.
Sin coordenadas no hay celda H3 a la que asignarlos. La espec preveia
geocodificar «la parte del REPS que viene sin coordenadas»; en realidad es el
dataset entero, y geocodificar 76.821 direcciones no es una tarea de la semana 2.

**Bloqueo (b) — copyleft incompatible.** Ambos son CC BY-SA 4.0, no «abierta
gov» como asumia la espec. CC BY-SA 4.0 y ODbL son **ambas** share-alike y
**mutuamente incompatibles**: cada una exige que el derivado se publique bajo
ella, y no existe licencia que satisfaga a las dos. Meter REPS en la misma
tabla que las edificaciones de Overture produce un `exposure_h3` que no se
puede licenciar bajo ninguna licencia.

**Decisión aplicada:** `health_count` y `edu_count` por celda salen de
OpenStreetMap, la única fuente con coordenadas. REPS y MEN pasan a ser
referencia de **completitud municipal** —cuantas sedes dice el registro oficial
que hay en el municipio X frente a cuantas tiene OSM— en una tabla aparte bajo
CC BY-SA. Esa comparación es además más honesta que un conteo: convierte el
hueco de OSM en una cifra publicada en vez de en un silencio.

**Guardia en código:** `resolve_bucket()` ahora rechaza la combinación
ODbL + CC BY-SA 4.0 con un error explícito. La regla de los tres cubos por si
sola no atrapaba este caso, porque ambas licencias caen del lado
«redistribuible».

---

## Detalle por tarea

### T0.4 — Marco Geoestadístico Nacional (DANE) · resuelta

El Geoportal DANE publica su información geografica bajo **CC BY 4.0**: permite
uso comercial y redistribucion «en todos los medios y formatos actualmente
conocidos o por crearse», y pide citar *«Departamento Administrativo Nacional
de Estadística - DANE: www.dane.gov.co»*.

Descarga directa verificada (HTTP 206, `application/zip`):

```
https://geoportal.dane.gov.co/descargas/mgn_2025/MGN2025_00_COLOMBIA.zip   3,39 GB
https://geoportal.dane.gov.co/descargas/mgn_2025/MGN2025_DPTO_POLITICO.zip 12,5 MB
https://geoportal.dane.gov.co/descargas/mgn_2025/MGN2025_CLASE.zip          120 MB
```

**Pendiente acotado:** existen entregas por nivel mucho más livianas que el
archivo nacional, pero el nombre exacto del nivel municipal no se deduce
probando (`MPIO`, `MPIO_POLITICO`, `MUNICIPIO`… todos 404). Hay que leerlo del
geoportal antes del primer build: bajar 3,4 GB cada trimestre para quedarse con
1.100 polígonos municipales es desperdicio puro.

### T0.5 — REPS · resuelta en contra

Ver «Hallazgos» arriba. Dataset correcto identificado (`c36g-9fc2`,
*Registro Especial de Prestadores y Sedes de Servicios de Salud*), pero no
sirve para el propósito que la espec le daba.

### T0.6 — Sedes educativas MEN · resuelta en contra

Dataset nacional identificado (`cfw5-qzt5`,
*MEN_ESTABLECIMIENTOS_EDUCATIVOS_PREESCOLAR_BASICA_Y_MEDIA*). Además de los dos
bloqueos, tiene columna `a_o`: las 588.334 filas son registros por
establecimiento **y anio**, así que habría que filtrar por el anio vigente
antes de contar nada.

### T1.2 — OurAirports · **resuelta** (23-ago-2026)

`https://davidmegginson.github.io/ourairports-data/airports.csv` responde
HTTP 200 con 12,7 MB. El texto que faltaba citar esta en dos sitios, ambos
leidos directamente:

- **Página de datos** (`https://ourairports.com/data/`): «All data is released
  to the Public Domain, and comes with no guarantee of accuracy or fitness for
  use».
- **Repositorio de descargas** (`github.com/davidmegginson/ourairports-data`):
  el `LICENSE` es **The Unlicense** íntegro — «This is free and unencumbered
  software released into the public domain… Anyone is free to copy, modify,
  publish, use, compile, sell, or distribute this software… for any purpose,
  commercial or non-commercial».

**Matiz que se deja escrito en vez de redondear:** The Unlicense habla de
*software*, y lo que aquí se reutiliza son *datos*. La declaración que cubre el
caso es la de la página de datos, explicita sobre «all data»; el `LICENSE` la
respalda. Con las dos juntas la intención no admite otra lectura, pero la
cobertura no viene del `LICENSE` solo.

Nota operativa: el repositorio pide expresamente **no abrir pull requests**;
las correcciones se hacen con una cuenta en ourairports.com y entran en el
volcado diario.

### GHS-POP · confirmada

Ambas variantes de la época 2025 sirven (HTTP 206): Mollweide 100 m
(`…_54009_100_V1_0.zip`, la del manifest) y WGS84 3 segundos de arco
(`…_4326_3ss_V1_0.zip`), esta última útil si reproyectar desde Mollweide
resulta ser el cuello de botella de P0.

---

## Ronda 5 — fuentes de Fase 2, validadas el 24-ago-2026

### T2.1 — Copernicus EMS Rapid Mapping · **resuelta**

Los términos de uso del servicio permiten expresamente «reproduction,
distribution, communication to the public, adaptation, modification and
combination with other data», sin restricción comercial. La única obligación es
«inform the recipients of the source of that data and information», con el
formato de cita fijado por el servicio:

    Copernicus Emergency Management Service (© activation_year European Union), Activation ID

y para un producto concreto:

    Copernicus Emergency Management Service (© 2025 European Union), [EMSR780] Kaweni (AOI03): Grading Map

Matiz que conviene tener escrito: los términos anaden que «any independent
intellectual property right generated as a result of modifying or adapting the
data shall be owned by the respective creator(s)». O sea que las etiquetas
derivadas son nuestras, con la atribución puesta.

**Consecuencia para el cubo de licencias:** EMS entra sin conflicto. No es
share-alike, así que no arrastra al activo.

### T2.2 — SAR abierto · **resuelta, las dos**

| Fuente | Licencia | Bucket | Credenciales |
|---|---|---|---|
| Umbra Open Data | CC BY 4.0 | `umbra-open-data-catalog` (us-west-2) | ninguna |
| Capella Open Data | CC BY 4.0 | `capella-open-data` (us-west-2) | ninguna |

Comprobado el listado de los dos buckets por HTTPS sin firmar: responden 200 y
devuelven claves. Ninguno es requester-pays, así que leerlos no cuesta ni
requiere cuenta de AWS — la misma propiedad que hace posible leer Overture en
remoto.

Umbra no publica un fichero de licencia en el bucket; la declaración vive en su
entrada del AWS Open Data Registry y en su página de datos abiertos. Capella
declara CC BY 4.0 en el registro y añade datos cada trimestre.

**La vía SAR importa por dos razones**: no la tapan las nubes —decisivo en la
región andina y en el Caribe— y no tiene el problema de licencia NC que
arrastra xBD.

### T2.3 — Hay verdad de campo para **los dos eventos golden**

Buscando el GeoPackage de Cali apareció algo mejor: en HDX ya hay evaluaciones
de daño abiertas de los dos sismos que este proyecto usa como golden.

| Dataset | Organización | Licencia | Contenido |
|---|---|---|---|
| `2026-colombia-earthquake` | Microsoft AI for Good Lab | **CC BY** | Huellas con prediccion de daño sobre Cali, con dos fuentes de huella: Google (320.178 edificaciones, 621 dañadas) y **Overture** (97.085, 266) |
| `building-damage-assessment-la-guaira-coastline...` | Microsoft AI for Good Lab | **CC BY** | 26.142 edificaciones con prediccion en la costa de La Guaira |
| `building-debris-assessment-venezuela-earthquake-june-2026` | UNEP/OCHA Joint Environment Unit | **CC BY-SA** | Escombros por detección de cambio SAR multisensor: rejilla de 3 km, rejilla de 350 m y por edificación |

Cali es el área del sismo del Chocó del 10-ago-2026 (`us6000tjl2`), y La Guaira
es donde cae Catia La Mar (`us6000t7zp`). O sea que **para los dos eventos
congelados existe una evaluación independiente y abierta**.

Tres cosas que se siguen de esto:

1. El primer hito de Fase 2 no es entrenar un modelo. Es **contrastar** lo que
   CENTINELA publica —población y edificaciones expuestas por banda de
   intensidad— contra una estimación de daño hecha por otros con otro método.
   Exposición y daño no son lo mismo, y esa distinción es justo la que el
   sistema promete no confundir: tener las dos cifras del mismo evento permite
   enseñar la diferencia en vez de explicarla.
2. Microsoft uso **Overture**, la misma fuente de huellas que este proyecto.
   Eso hace la comparación de conteos interpretable en vez de anecdótica.
3. **Ojo con el cubo.** El de UNEP/OCHA es CC BY-SA y no puede mezclarse con el
   activo ODbL sin arrastrarlo. Se consume como referencia externa, no como
   capa del activo. `resolve_bucket` ya lo impide.

### Primera contrastacion: exposición frente a daño, mismo evento

`centinela contraste` lleva cada edificación evaluada a su celda r8 por el
centroide, igual que hace el activo, y compara sobre **las mismas celdas**. Así
la única diferencia entre las dos cifras es lo que cada fuente metió en la
celda, no como se recorto el mapa.

Medido sobre **los dos eventos golden**, con los activos reconstruidos:

| | Cali (`us6000tjl2`) | La Guaira (`us6000t7zp`) |
|---|---:|---:|
| Celdas H3 r8 comparadas | 328 | 74 |
| Microsoft: edificaciones evaluadas | 97.351 | 26.143 |
| **con daño detectado** | **266 (0,273 %)** | **965 (3,69 %)** |
| CENTINELA: edificaciones Overture | 107.252 | 35.611 |
| CENTINELA: población | 1.995.749 | 166.989 |
| Razón de conteo CENTINELA/Microsoft | 1,10 | 1,36 |
| **celdas evaluadas que el activo no cubre** | **0** | **0** |

Tres lecturas.

**La cobertura del activo es completa en los dos.** Ni una sola de las 402
celdas evaluadas por Microsoft falta del activo, en dos países distintos y dos
sismos distintos. Es la comprobación más dura que se le ha hecho a la cobertura,
porque la lista de celdas la puso otro.

**Las razones de conteo, 1,10 y 1,36, no son descuadres.** La evaluación externa
se recorta a su máscara de área valida —donde la imagen servia— y una celda r8
puede quedar medio dentro, aportando todas sus edificaciones a un lado y solo
parte al otro. Que Cali salga en 1,10 y La Guaira en 1,36 es consistente con
eso: la máscara de Cali cubre 328 celdas y la de La Guaira solo 74, así que el
efecto de borde pesa el doble en la segunda. Sirve para detectar un orden de
magnitud raro, no para calibrar.

**Y las cifras que importan: 0,27 % y 3,69 %.** Los reportes de esos eventos
publican 444.424 y 504.955 edificaciones en MMI≥7 para todo el país. En las
zonas evaluadas, una fuente independiente detecta daño en menos del 4 % de lo
que miro, y en Cali en menos del 0,3 %. Son dos preguntas distintas y ahora se
pueden enseñar juntas en vez de explicarlas.

El contraste entre los dos también dice algo: Cali quedó en MMI 7-7,5 y La
Guaira mucho más cerca del epicentro. Un factor de trece en la fracción dañada
entre dos zonas de un mismo rango de exposición es exactamente por que exposición
no se puede leer como daño.

Un matiz sobre el dato de Microsoft que conviene no perder: `damage_pct_0m` no
pasa de 1,0 y promedia 0,4 % en las edificaciones marcadas. Su `damaged` es una
**detección de cambio**, no una medida de severidad. Leerlo como "965 edificios
destruidos" sería exactamente el tipo de lectura que este proyecto intenta
evitar.

#### El fallo que casi lo invalida

La primera corrida dio **cero celdas en común**, que se lee igual que un "no hay
solape" legítimo. La causa: EPSG:4326 declara el orden de ejes **lat-lon**, y
`ST_Transform` lo respeta. Sin `always_xy := true` las coordenadas salen
invertidas —la longitud sale 10,58 y la latitud -66,97— la celda calculada no
existe en ningún sitio y el join devuelve cero filas sin quejarse.

Hay una prueba que lo fija.

### T3.1 — Embeddings: la elección es de licencia, no de calidad

| Fuente | Publica | Licencia | ¿Puede entrar al activo? |
|---|---|---|---|
| **AlphaEarth Foundations** | Google / Google DeepMind | **CC-BY 4.0** | **Si**, con su atribución |
| **Major TOM** | ESA Φ-lab | **CC-BY-SA 4.0** | **No**: share-alike, arrastraría el cubo entero |

AlphaEarth publica 64 canales anuales de 2017 a 2025 en `gs://alphaearth_foundations`,
y exige la cadena literal: «The AlphaEarth Foundations Satellite Embedding
dataset is produced by Google and Google DeepMind».

Major TOM es más rico —incluye embeddings derivados de Sentinel-1 y Sentinel-2
con varios modelos, y hasta una versión del propio AlphaEarth— pero su CC-BY-SA
lo deja fuera del activo por la misma regla que deja fuera el dato de escombros
de UNEP/OCHA. Se consume como referencia externa o no se consume.

**Que la elección sea de licencia y no de calidad conviene tenerlo escrito**,
porque el día que alguien compare las dos por su rendimiento y elija Major TOM,
la decisión correcta seguira siendo la otra.

#### Y el contrato de esquema no lo comprobaba nadie

`schemas/parquet/tables.yaml` declara las columnas del activo, sus tipos y su
procedencia. **Ni una línea de código lo referenciaba**, así que había derivado:

* no declaraba `built_m2`, anadida al meter GHS-BUILT-S;
* seguía atribuyendo salud a **REPS** y educación al directorio del **MEN**,
  dos fuentes resueltas en contra en T0.5 y T0.6.

Lo segundo es peor que lo primero. Un contrato incompleto se nota; un contrato
que nombra una fuente que no se usa **parece trazabilidad** y no lo es.

Corregido, y con una prueba que construye el activo mínimo y compara sus
columnas reales contra las declaradas. Es el mismo patrón que el cálculo del
preliminar escrito y nunca llamado: un artefacto correcto que nadie ejecuta deja
de ser correcto sin avisar.

### T2.4 — La rama de pesos, sin cambios

Sigue en pie tal como esta escrito en `p4_brigada/protocol.py`: un modelo
afinado desde xBD/xView2 hereda CC BY-NC-SA y va al cubo `nc/`. Lo que cambia
tras T2.1 y T2.2 es que **la rama limpia ya tiene de que alimentarse**: EMS para
etiquetas, Umbra y Capella para imagen, las dos CC BY. La rama limpia deja de
ser una aspiracion y pasa a ser una ruta con fuentes nombradas.

---

## Ronda 6 — el visor, recorrido como usuario final (31-ago / 1-sep-2026)

Metodo: abrir la pagina publicada y usarla, con criterio de UX/UI y de
cartografia digital, cruzando cada cifra contra `report.json`, `cobertura.json`,
la API de USGS y el `report.md` que produce el propio pipeline. Las medidas de
pantalla se tomaron con Playwright sobre el sitio armado igual que lo publica
`site.yml`.

**La pestana del MCP no sirve para esto.** Corre en `visibilityState: hidden`,
MapLibre no llega a disparar `load` y el mapa parece vacio estando bien. Todo lo
de abajo se midio con Playwright.

### Cifras que decian lo que no era

| Que | Como se comprobo | Resultado |
|---|---|---|
| «La sacudida no alcanzo MMI 7 sobre población» en Muisne | `report.json` del evento | **Falso**: `pop_mmi7p` = 2.283.454. La nota estaba escrita para el caso contrario y salia en los 3 eventos que llegan a MMI 8 |
| «Municipios más expuestos» | `top_municipios` de los 21 reportes | Ordenaba por la banda cumbre: Quininde salia con **0** teniendo 164.691 en MMI≥7, y Portoviejo (333.075) no salia. Filas en cero en 12 de los 21 |
| «Difiere del total nacional del mismo producto… remuestreo a hexagonos» | SQL de `p2_impact/pipeline.py` y `markdown.py` | Es el desacuerdo **GHS-POP vs WorldPop en el area afectada**. El `.md` lo decia bien y el visor al reves. Carupano publica 416,9 % |
| «La malla de 5,2 km² con la que se calcula» | `H3_RES_COMPUTE` = 8, `H3_RES_VIEWER` = (7, 6) | El calculo va en r8 (0,74 km²); 5,2 km² es la resolucion de publicacion |
| PAGER «naranja» del visor | API de USGS (`fdsnws/event/1/query`) | ✅ coincide. El `.md` lo publicaba sin traducir |
| Suma de la malla vs totales del pipeline | 8.517 celdas de Muisne sumadas en el navegador | ✅ 4.311.562 contra `pop_mmi6p` = 4.311.549 |
| Recorte de la malla al contorno MMI 6 | `querySourceFeatures` sobre `celdas` y `contornos` | ✅ Quito y Guayaquil quedan fuera, y **deben** quedar fuera |

### Medidas de pantalla

| Que | Antes | Despues |
|---|---|---|
| Longitud visible al abrir (1540 px) | 191° para una region de 73° | 126° a 1440×900; la region ocupa del 41 % al 88 % segun el tamano |
| Tinta de la capa de fuego a zoom 2 | 413.000 px² — **1,23× el lienzo** | 117.000 px² — 0,15× |
| Tinta de las celdas ≤10 MW frente a las ≥400 MW | 10,9 : 1 | 2,0 : 1 |
| Celdas que caen sobre un pixel ya ocupado (z2) | 69 %, y las 150 más energeticas **sin excepcion** | igual, pero ahora el fuego fuerte se dibuja encima |
| Barra de escala vs leyenda en 390 px, con evento abierto | −22 px (solapando) | +1 px |
| Rueda del raton sobre el mapa | zoom 2,05 → 1,65 **y** pagina 300 px, en un gesto | la rueda no toca el mapa |

### El mapa de calor, descartado por medida

Con `heatmap-intensity` y `heatmap-radius` **fijos**, se leyo el color del pixel
del mismo punto geografico (un foco del Beni) a tres zooms:

| zoom | color |
|---|---|
| 2 | `rgb(183, 39, 78)` — carmesi |
| 4 | `rgb(238, 113, 21)` — naranja |
| 6 | `rgb(223, 220, 209)` — el color del papel: desaparece |

`heatmap-density` mide vecinos por pixel de pantalla, no energia. Una rampa que
cambia de significado con el zoom no se puede rotular en MW.

### Lo publicado estaba rancio

`markdown.py`, `social.py` y `DISCLAIMERS` llevaban las tildes puestas en el
repositorio; los veintiun paquetes servidos se emitieron antes de esa correccion
y nadie volvia a tocarlos. Comprobado con la lista negra de
`test_textos_publicados.py`: **13 formas sin tilde** en el `report.md`
publicado y 8 en el `hilo.txt`, incluido «Exposición no es daño» como cierre del
hilo para redes.

Se anadio `centinela regenerar-textos` y se re-emitieron los 21. Verificado
contra la pagina publicada tras la fusion: 0 ficheros con formas sin tilde.

### Un defecto que ya estaba en produccion

Comparando el visor publicado contra el arreglado, con `?evento=` y estilo frio:

    [main]  fallo al dibujar sobre el mapa: Error: Source "celdas" already exists.
    [ahora] (sin errores)

La red de seguridad de `cuandoElEstiloEsteListo` no se cancelaba cuando el
camino normal funcionaba, asi que todo dibujo diferido corria dos veces. Ver la
familia 10 de [`docs/FAMILIAS_DE_FALLO.md`](docs/FAMILIAS_DE_FALLO.md).

---

## Sigue abierto

| Tarea | Que falta |
|---|---|
| T0.2 (resto) | Congelar los **contenidos**: `cont_mmi.json` y rasters de Ground Failure, que necesita el polyfill H3. Lo congelado hoy es la estructura de productos y su historial de versiones |
| T0.9 (nueva) | Nombre del archivo MGN a nivel municipal: el nacional pesa 3,39 GB |
| T0.7 | Benchmark `exactextract` vs muestreo simple (<1 % en población nacional) |
| T0.8 | Motor del mapa estático: matplotlib+contextily vs MapLibre headless |
| T1.1 | Formatos y términos de las redes sismologicas nacionales |
| T1.3 | Plantillas HDX y validación de las cabeceras HXL |
| T2.1–T2.3 | ✅ resueltas el 24-ago-2026 (ronda 5) |
| T2.4 | La rama de pesos limpia ya tiene fuentes; falta construirla |
| T3.1 | ✅ resuelta el 24-ago-2026: AlphaEarth CC-BY 4.0 entra; Major TOM CC-BY-SA no |
