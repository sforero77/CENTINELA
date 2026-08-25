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

### GHS-POP sobrestima Venezuela en 1,8 millones de personas

El hallazgo que Venezuela existia para producir, y la razon de haber elegido la
ONU como referencia en vez del INE.

| | |
|---|---:|
| GHS-POP E2025 recortado por el COD-AB | **30.313.601** |
| ONU, World Population Prospects 2025 | 28.516.896 |
| **Desvio** | **+6,30 %** |
| Colombia, para comparar | -0,11 % |

La primera corrida de `centinela country VEN` fallo con la tolerancia en 5 %, y
**eso fue el assert funcionando**: detecto una divergencia real entre dos
modelos de poblacion en un pais sin censo desde 2011. Se subio a 8 % para poder
construir el activo, no porque la divergencia deje de importar.

**Por que divergen.** GHS-POP R2023A parte de la ronda censal de 2010 y
desagrega con volumen construido. Las casas de quien emigro siguen en pie y
siguen pesando en el modelo. WPP si incorpora el saldo migratorio. Para un
sistema de exposicion la diferencia no es academica: sobrestimar la poblacion de
una zona infla la cifra que lee una sala de crisis.

**El contraste que no cierra la cuestion.** El raster total de WorldPop 2025
constrained suma 28.460.161, a -0,20 % de WPP. Parece confirmar a la ONU y no
confirma nada: los productos "constrained" de WorldPop **se calibran contra los
totales nacionales de WPP**, asi que coincidir es como estan construidos. La
fuente que se aparta es GHS-POP, que es justamente de donde sale la cifra
principal del reporte.

**Consecuencia operativa.** Cualquier reporte de un evento venezolano hereda ese
+6,30 %. Un mantenedor de pais con proyecciones del INE posteriores a 2011 puede
sustituir la referencia y estrechar la tolerancia.

### Una geometria rota deja el pais entero en NaN

Ecuador construyo y publico un activo con `road_km: NaN`. La cadena entera:

1. Overture trae una geometria degenerada cuya longitud esferoidal no es finita.
2. El filtro `ST_Length_Spheroid(geometry) > 0` descarta el cero y el NaN, pero
   **no el infinito**.
3. `sum()` propaga: un solo segmento roto y el total nacional es NaN.
4. `validate_layer_coverage` no lo detuvo porque comprobaba `if not valor`, y
   **`bool(float('nan'))` es `True`**. Para la guardia, la capa "aportaba".

Un NaN es peor que un cero: el cero es una afirmacion falsa pero acotada, y el
NaN contamina toda operacion que lo toque hasta acabar impreso en el reporte.

Corregido midiendo: Ecuador pasa de `NaN` a **133.385 km**. La guardia exige
ahora que el valor sea finito, y la agregacion descarta longitudes infinitas o
mayores de 2.000 km — Overture parte las vias en segmentos mucho mas cortos, asi
que por encima de eso no hay carretera sino geometria rota.

### El sesgo de poblacion era nuestro, no de GHS-POP

Medidos los 18 paises, los desvios de GHS-POP frente a World Population
Prospects van de **-0,80 % (Chile) a +6,59 % (Paraguay)**, y quince de dieciocho
son positivos. Eso no es dispersion: es un sesgo con direccion.

Dos explicaciones se propusieron y **las dos eran falsas**:

1. *"Se desvian los paises sin censo reciente."* Uruguay censo en 2023 y se
   desvia +6,28 %, casi lo mismo que Venezuela.
2. *"GHS-POP sobrestima de forma sistematica."* Se formulo viendo quince
   positivos seguidos; faltaban Chile, Mexico y Colombia —cuyas corridas se
   lanzaron antes de que el workflow pusiera el ISO3 en el nombre— y los tres
   resultaron ser los negativos.

Lo que si ordena los datos es **cuanta frontera tiene cada pais en proporcion a
su area**. Se instrumento el rescate de celdas fronterizas para medirlo, y
Paraguay —interior, todo frontera— lo confirmo:

| | |
|---|---:|
| Poblacion rescatada | 459.518 |
| Total del activo | 7.474.922 |
| **Fraccion rescatada** | **6,147 %** |
| Desvio frente a la ONU | 6,585 % |
| **Total descontando el rescate** | **7.015.404** |
| Referencia de la ONU | 7.013.078 |
| **Desvio corregido** | **+0,03 %** |

**El rescate explica el 93 % del exceso.** Sin el, la cifra clava la referencia.

La causa es geometrica y evidente una vez medida: la cota del rescate es 0,02°
(~2,2 km), y en un pais interior **cada kilometro de perimetro es frontera**, de
modo que se reclama una franja de 2,2 km de Brasil, Argentina y Bolivia
alrededor de todo el pais. Chile y Mexico salen negativos porque su rescate es
sobre todo **mar**, que es el caso para el que se diseno y donde es correcto.

Es el mismo fallo que ya se corrigio una vez para Colombia —rescatar sin acotar
llevo la poblacion nacional de 52,6 a 167 millones— pero en pequeno, dentro de
la cota, y por eso invisible durante meses.

**La correccion:** rescatar una celda solo si su centro no cae dentro de otro
pais. Una celda cuyo centro esta en tierra brasilena es de Brasil, por cerca que
este de la linea. Se resuelve con los poligonos de pais de `division_area` de
Overture, los mismos ficheros que se leyeron para medir las cajas envolventes.

#### Medida, en dos intentos

El primero **no arreglo nada y no fallo**: Paraguay volvio a salir con los
mismos 459.518 rescatados. La tabla de vecinos se habia cargado con **cero
poligonos** y el build siguio adelante. La consulta corrio, devolvio cero filas,
nadie se quejo — el modo de fallo que este proyecto persigue, cometido por el
codigo que lo persigue.

La causa: el filtro de poda de Overture comprueba que la **esquina inferior
izquierda** del rasgo caiga dentro de la caja del pais. Vale para un edificio o
un tramo de via, que son mas pequenos que la caja. Deja de valer para un pais:
la esquina de Brasil esta en -73,99, muy al oeste de la caja paraguena, aunque
Brasil ocupe media caja. Medido contra Overture 2026-08-19.0:

| Poda | Paises devueltos en la caja de Paraguay |
|---|---|
| Contencion | PY |
| **Interseccion** | **AR, BO, BR**, PY, FJ |

Como el pais propio se excluye por definicion, con contencion la tabla quedaba
vacia. (FJ aparece porque Fiji cruza el antimeridiano y su caja abarca el globo;
no estorba, ningun punto paraguayo cae dentro de un poligono fiyiano.)

Corregido a interseccion, y el caso "cero vecinos" pasa de INFO a WARNING: en
LATAM solo Cuba no toca a nadie por tierra, y hasta su caja alcanza a Haiti.

#### Resultado

| Paraguay | Antes | Despues |
|---|---:|---:|
| Celdas rescatadas | 1.945 | **23** |
| Poblacion rescatada | 459.518 | **112** |
| Fraccion rescatada | 6,147 % | **0,002 %** |
| Total nacional | 7.474.922 | **7.015.517** |
| **Desvio frente a la ONU** | **+6,585 %** | **+0,035 %** |

La prediccion era 7.015.404 —el total menos el rescate medido antes— y salieron
7.015.517: los 113 de diferencia son el rescate legitimo que queda.

### Simplificar la geometria administrativa: control sobre Uruguay

El COD-AB de Chile pesa mas de 182 MB y `h3_polygon_wkt_to_cells` recibe la
geometria como **texto**: el `ST_AsText` de una sola provincia de Magallanes
agoto los 12,4 GB del runner. Se simplifica al cargar, con tolerancia 0,0005
grados (~55 m).

La pregunta es que se pierde. Reconstruido Uruguay con y sin simplificacion, el
mismo dia y con el mismo codigo por lo demas:

| | Sin simplificar | Simplificado |
|---|---:|---:|
| Celdas | 150.314 | 150.314 |
| Poblacion | 3.429.034 | 3.429.034 |
| Edificaciones | 2.418.920 | 2.418.920 |
| Superficie construida | 389.300.479 | 389.300.479 |
| Kilometros de via | 89.090 | 89.090 |
| Sedes de salud | 1.149 | 1.149 |
| Sedes educativas | 4.433 | 4.433 |
| Fraccion rescatada | 0,934 % | 0,934 % |
| Desvio | +1,3102 % | +1,3102 % |

**Identicas hasta la ultima unidad.** Es lo que tenia que pasar: el reparto
asigna por el centro de la celda y una celda r8 mide unos 740 m, asi que mover
una frontera 55 m solo puede cambiar de municipio las celdas cuyo centro caiga
casi encima de la linea — y esas pasan al vecino, no al vacio.

Lo que este control **no** prueba es la distribucion municipal, que es donde el
efecto vive por definicion. Prueba lo que importa mas: que no se pierde nadie.

### Reemitir el backtest del Choco: cuanto corregian los arreglos

El reporte publicado el 23-ago-2026 se calculo contra `col-v0.4`, el activo
anterior a cablear las tres capas sueltas, a subir las bandas de edad hasta 90 y
a anadir GHS-BUILT-S. Reemitido contra `col-v0.5` con `--reprocesar`:

| Cifra en MMI≥7 | Publicado | Reemitido | |
|---|---:|---:|---|
| Kilometros de via | 1.397,7 | **8.502,9** | ×6,1 |
| Poblacion 65+ | 271.688 | **289.257** | +6,5 % |
| Edificaciones | 444.281 | 444.424 | +143 |
| Sedes de salud | 512 | 518 | +6 |
| Sedes educativas | 997 | 998 | +1 |
| Superficie construida | — | 69,8 km² | capa nueva |
| **Poblacion en MMI≥7** | **2.415.793,459** | **2.415.793,459** | **identica** |

Dos cosas que conviene no mezclar.

**La cifra principal no se movio ni un bit.** El golden de G1 la fija con ±0,5 %
y pasa exacto. Tiene sentido: el area MMI≥7 de este evento es interior
—Pereira, Buenaventura, Armenia, Tuluá, Dosquebradas— y ni el rescate de
frontera ni el arreglo del multipoligono la tocan.

**Los kilometros de via estaban seis veces cortos.** Un reporte publicado decia
1.397 km cuando eran 8.503. Nadie lo habria notado: 1.397 km es una cifra
perfectamente creible para una zona de intensidad. Es el cero silencioso en su
version mas peligrosa — no un cero, un numero.

### El reparto no veia las islas, y el rescate lo tapaba

`h3_polygon_wkt_to_cells` devuelve **cero** celdas ante un MULTIPOLYGON. No la
primera parte: cero. Medido:

| Geometria | Celdas r8 devueltas |
|---|---:|
| `POLYGON` (cuadrado A) | 22.365 |
| `POLYGON` (cuadrado B) | 20.160 |
| `MULTIPOLYGON(A, B)` | **0** |
| `MULTIPOLYGON(A, B)` con `ST_Dump` | 42.525 |

Un municipio con una isla, un exclave o un trozo separado por un rio es un
MULTIPOLYGON. Ninguno de ellos aportaba una celda al reparto por contencion.

**Nadie lo vio porque el paso siguiente lo tapaba.** Esas celdas quedaban sin
asignar, caian dentro del pais, y el rescate las mandaba al municipio mas
cercano — que para un punto dentro del municipio esta a distancia cero, o sea
el correcto. La cifra nacional salia bien por un camino que no era el suyo.

Lo delato Uruguay al instrumentar el embudo del rescate:

    candidatas: 896.936 → junto al pais: 6.538 → descartadas por vecino: 909
    pop_rescatada_pct: 48,026 %

**El 48 % de la poblacion de Uruguay entraba por el rescate**, mas que Chile con
sus 4.000 km de costa. No era costa: eran departamentos multipoligono entrando
enteros por la puerta de atras.

El coste no era la cifra, era el marcador. `rescatada = TRUE` significa "esto es
una aproximacion, auditalo", y puesto sobre medio pais no significa nada. Y deja
al reparto dependiendo de que el rescate exista, que es correccion por
accidente: acotar mas el rescate —cosa que se hizo dos veces esta semana— se
habria llevado medio pais por delante sin avisar.

#### Chile responde la pregunta que quedaba abierta

Se afirmo, viendo que Chile rescataba el 31 % de su poblacion con un desvio
correcto, que ese rescate era **mar** y que por eso la magnitud del rescate no
distinguia lo correcto de lo contaminado. La primera mitad era falsa.

Reconstruido con el reparto viendo los multipoligonos:

| Chile | Antes | Despues |
|---|---:|---:|
| Poblacion rescatada | 6.126.336 | **145.195** |
| Fraccion rescatada | 31,097 % | **0,737 %** |
| Desvio frente a la ONU | -0,80 % | -0,85 % |

Aquel 31 % **no era mar**: eran comunas multipoligono entrando enteras por la
puerta de atras, igual que en Uruguay. Y el desvio apenas se mueve —cinco
centesimas— porque la poblacion ya estaba llegando, solo que por un camino que
no era el suyo.

La conclusion de fondo aguanta y sale reforzada: lo que distingue un rescate
correcto de uno contaminado no es cuanto se rescata sino **sobre que esta la
celda**. Lo que no aguantaba era el ejemplo con el que se ilustro.

(El reparto de Chile necesito 1.201 teselas para sus 56 provincias, y seis
intentos: cuatro OutOfMemory, uno por duplicados al simplificar mal, y este.)

#### No era solo el marcador: se perdian datos

El rescate solo mira celdas **con poblacion** (`FROM pop_h3`). Una celda dentro
de un municipio multipoligono con un colegio, una via o unas edificaciones pero
sin poblacion censada no entraba por ninguno de los dos caminos: ni por el
reparto —que no veia el multipoligono— ni por el rescate. Desaparecia del activo.

Medido en Uruguay, misma corrida antes y despues del `ST_Dump`:

| | Antes | Despues | Recuperado |
|---|---:|---:|---:|
| Celdas | 145.488 | 150.314 | **+4.826** |
| Edificaciones | 2.411.764 | 2.418.920 | **+7.156** |
| Kilometros de via | 86.867 | 89.090 | **+2.223** |
| Poblacion | 3.426.966 | 3.429.034 | +2.068 |
| Sedes educativas | 4.430 | 4.433 | +3 |
| Sedes de salud | 1.149 | 1.149 | 0 |

Y la fraccion rescatada cae de **48,026 % a 0,934 %**, que es lo que siempre
debio medir: costa y frontera, no departamentos enteros.

El desvio nacional apenas se mueve (+1,25 % → +1,31 %), lo que confirma que la
poblacion ya estaba llegando —por el camino equivocado— y que lo que faltaba era
sobre todo infraestructura sin poblacion alrededor.

Es el mismo perfil que el fallo del filtro de celdas que perdio 1.664 colegios
de Colombia: lo que se pierde no es donde vive la mayoria, es la periferia.

Consecuencia: **la fraccion rescatada de los diecinueve hay que remedirla**.
Hasta ahora no media lo que se creia que medida, y la afirmacion "Chile rescata
el 31 % porque su rescate es mar" esta sin comprobar por el mismo motivo.

### Chile: dos muertes por memoria, un solo error de diseno

Corregido Paraguay, Chile tumbo el build dos veces. La primera con
`OutOfMemoryException` de DuckDB (12,3 de 12,4 GB), la segunda llevandose el
proceso entero por delante — el paso salio `cancelled`, sin traza.

**No era el tamano del pais.** Los dos filtros del rescate vivian en el mismo
`WHERE`, asi que el planificador no garantizaba cual evaluaba primero. Y el
conjunto de partida no son las celdas costeras de Chile: son **todas** las
celdas con poblacion del recorte de GHS-POP que el polyfill dejo fuera, o sea
media Argentina, Bolivia y Peru. Millones de puntos contra un multipoligono
continental.

Separado en cuatro pasos materializados —candidatas, acotar al pais, descartar
vecinos, asignar municipio— al descarte solo llegan las que sobrevivieron a la
cota.

Y los poligonos se simplifican al cargarlos, con tolerancia 0,001 grados
(~110 m), veinte veces mas fina que la cota del rescate. Medido sobre la caja de
Chile con Overture 2026-08-19.0:

| Vecino | Vertices tras recortar y simplificar |
|---|---:|
| AR | 7.698 |
| BO | 735 |
| PE | 60 |
| BR, NZ, FJ | 0 (su interseccion con la caja es vacia) |
| **Union** | **8.317** |

60.000 puntos contra esa union: **5,2 s**.

### Overture publica dos poligonos por pais, no uno

`division_area` con `subtype='country'` devuelve **dos filas** por pais: la
terrestre (`is_land`) y la de aguas territoriales (`is_territorial`). Medido
sobre la caja de Chile:

    AR  is_land=False is_territorial=True    AR  is_land=True is_territorial=False
    PE  is_land=False is_territorial=True    PE  is_land=True is_territorial=False
    BO  is_land=True  is_territorial=True

Cargar las dos rompe justo el caso para el que existe el rescate: las aguas
peruanas llegan hasta la frontera de Arica, asi que una celda del Pacifico
frente a la costa chilena caeria "dentro de Peru" y se descartaria con su
poblacion dentro. El mar no es de nadie a estos efectos.

(Bolivia sale marcada con las dos, siendo interior. No estorba: se filtra por
`is_land`, que en su caso es cierto.)

### El COD-AB publica dos nomenclaturas, no una

Ecuador fue el primer pais construido con el COD-AB como unica fuente
administrativa, y fallo:

```
ecu_adm_adm2_2024.shp no trae las columnas ['adm2_name', 'adm1_name'].
Tiene: ['adm0_es', 'adm0_pcode', 'adm1_es', 'adm1_pcode', 'adm2_es', 'adm2_pcode', ...]
```

El codigo va siempre en `adm2_pcode`, pero el nombre depende de cuando se genero
la entrega: `adm2_name` en las recientes —medido sobre Venezuela— y `adm2_es` en
las antiguas. Con diecinueve paises, descubrir cada variante fallando no escala,
asi que el mapeo admite varias y gana la primera cuyas cuatro columnas existan.

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

## Ronda 5 — fuentes de Fase 2, validadas el 24-ago-2026

### T2.1 — Copernicus EMS Rapid Mapping · **resuelta**

Los terminos de uso del servicio permiten expresamente «reproduction,
distribution, communication to the public, adaptation, modification and
combination with other data», sin restriccion comercial. La unica obligacion es
«inform the recipients of the source of that data and information», con el
formato de cita fijado por el servicio:

    Copernicus Emergency Management Service (© activation_year European Union), Activation ID

y para un producto concreto:

    Copernicus Emergency Management Service (© 2025 European Union), [EMSR780] Kaweni (AOI03): Grading Map

Matiz que conviene tener escrito: los terminos anaden que «any independent
intellectual property right generated as a result of modifying or adapting the
data shall be owned by the respective creator(s)». O sea que las etiquetas
derivadas son nuestras, con la atribucion puesta.

**Consecuencia para el cubo de licencias:** EMS entra sin conflicto. No es
share-alike, asi que no arrastra al activo.

### T2.2 — SAR abierto · **resuelta, las dos**

| Fuente | Licencia | Bucket | Credenciales |
|---|---|---|---|
| Umbra Open Data | CC BY 4.0 | `umbra-open-data-catalog` (us-west-2) | ninguna |
| Capella Open Data | CC BY 4.0 | `capella-open-data` (us-west-2) | ninguna |

Comprobado el listado de los dos buckets por HTTPS sin firmar: responden 200 y
devuelven claves. Ninguno es requester-pays, asi que leerlos no cuesta ni
requiere cuenta de AWS — la misma propiedad que hace posible leer Overture en
remoto.

Umbra no publica un fichero de licencia en el bucket; la declaracion vive en su
entrada del AWS Open Data Registry y en su pagina de datos abiertos. Capella
declara CC BY 4.0 en el registro y anade datos cada trimestre.

**La via SAR importa por dos razones**: no la tapan las nubes —decisivo en la
region andina y en el Caribe— y no tiene el problema de licencia NC que
arrastra xBD.

### T2.3 — Hay verdad de campo para **los dos eventos golden**

Buscando el GeoPackage de Cali aparecio algo mejor: en HDX ya hay evaluaciones
de dano abiertas de los dos sismos que este proyecto usa como golden.

| Dataset | Organizacion | Licencia | Contenido |
|---|---|---|---|
| `2026-colombia-earthquake` | Microsoft AI for Good Lab | **CC BY** | Huellas con prediccion de dano sobre Cali, con dos fuentes de huella: Google (320.178 edificaciones, 621 danadas) y **Overture** (97.085, 266) |
| `building-damage-assessment-la-guaira-coastline...` | Microsoft AI for Good Lab | **CC BY** | 26.142 edificaciones con prediccion en la costa de La Guaira |
| `building-debris-assessment-venezuela-earthquake-june-2026` | UNEP/OCHA Joint Environment Unit | **CC BY-SA** | Escombros por deteccion de cambio SAR multisensor: rejilla de 3 km, rejilla de 350 m y por edificacion |

Cali es el area del sismo del Choco del 10-ago-2026 (`us6000tjl2`), y La Guaira
es donde cae Catia La Mar (`us6000t7zp`). O sea que **para los dos eventos
congelados existe una evaluacion independiente y abierta**.

Tres cosas que se siguen de esto:

1. El primer hito de Fase 2 no es entrenar un modelo. Es **contrastar** lo que
   CENTINELA publica —poblacion y edificaciones expuestas por banda de
   intensidad— contra una estimacion de dano hecha por otros con otro metodo.
   Exposicion y dano no son lo mismo, y esa distincion es justo la que el
   sistema promete no confundir: tener las dos cifras del mismo evento permite
   ensenar la diferencia en vez de explicarla.
2. Microsoft uso **Overture**, la misma fuente de huellas que este proyecto.
   Eso hace la comparacion de conteos interpretable en vez de anecdotica.
3. **Ojo con el cubo.** El de UNEP/OCHA es CC BY-SA y no puede mezclarse con el
   activo ODbL sin arrastrarlo. Se consume como referencia externa, no como
   capa del activo. `resolve_bucket` ya lo impide.

### Primera contrastacion: exposicion frente a dano, mismo evento

`centinela contraste` lleva cada edificacion evaluada a su celda r8 por el
centroide, igual que hace el activo, y compara sobre **las mismas celdas**. Asi
la unica diferencia entre las dos cifras es lo que cada fuente metio en la
celda, no como se recorto el mapa.

Medido sobre **los dos eventos golden**, con los activos reconstruidos:

| | Cali (`us6000tjl2`) | La Guaira (`us6000t7zp`) |
|---|---:|---:|
| Celdas H3 r8 comparadas | 328 | 74 |
| Microsoft: edificaciones evaluadas | 97.351 | 26.143 |
| **con dano detectado** | **266 (0,273 %)** | **965 (3,69 %)** |
| CENTINELA: edificaciones Overture | 107.252 | 35.611 |
| CENTINELA: poblacion | 1.995.749 | 166.989 |
| Razon de conteo CENTINELA/Microsoft | 1,10 | 1,36 |
| **celdas evaluadas que el activo no cubre** | **0** | **0** |

Tres lecturas.

**La cobertura del activo es completa en los dos.** Ni una sola de las 402
celdas evaluadas por Microsoft falta del activo, en dos paises distintos y dos
sismos distintos. Es la comprobacion mas dura que se le ha hecho a la cobertura,
porque la lista de celdas la puso otro.

**Las razones de conteo, 1,10 y 1,36, no son descuadres.** La evaluacion externa
se recorta a su mascara de area valida —donde la imagen servia— y una celda r8
puede quedar medio dentro, aportando todas sus edificaciones a un lado y solo
parte al otro. Que Cali salga en 1,10 y La Guaira en 1,36 es consistente con
eso: la mascara de Cali cubre 328 celdas y la de La Guaira solo 74, asi que el
efecto de borde pesa el doble en la segunda. Sirve para detectar un orden de
magnitud raro, no para calibrar.

**Y las cifras que importan: 0,27 % y 3,69 %.** Los reportes de esos eventos
publican 444.424 y 504.955 edificaciones en MMI≥7 para todo el pais. En las
zonas evaluadas, una fuente independiente detecta dano en menos del 4 % de lo
que miro, y en Cali en menos del 0,3 %. Son dos preguntas distintas y ahora se
pueden ensenar juntas en vez de explicarlas.

El contraste entre los dos tambien dice algo: Cali quedo en MMI 7-7,5 y La
Guaira mucho mas cerca del epicentro. Un factor de trece en la fraccion danada
entre dos zonas de un mismo rango de exposicion es exactamente por que exposicion
no se puede leer como dano.

Un matiz sobre el dato de Microsoft que conviene no perder: `damage_pct_0m` no
pasa de 1,0 y promedia 0,4 % en las edificaciones marcadas. Su `damaged` es una
**deteccion de cambio**, no una medida de severidad. Leerlo como "965 edificios
destruidos" seria exactamente el tipo de lectura que este proyecto intenta
evitar.

#### El fallo que casi lo invalida

La primera corrida dio **cero celdas en comun**, que se lee igual que un "no hay
solape" legitimo. La causa: EPSG:4326 declara el orden de ejes **lat-lon**, y
`ST_Transform` lo respeta. Sin `always_xy := true` las coordenadas salen
invertidas —la longitud sale 10,58 y la latitud -66,97— la celda calculada no
existe en ningun sitio y el join devuelve cero filas sin quejarse.

Hay una prueba que lo fija.

### T3.1 — Embeddings: la eleccion es de licencia, no de calidad

| Fuente | Publica | Licencia | ¿Puede entrar al activo? |
|---|---|---|---|
| **AlphaEarth Foundations** | Google / Google DeepMind | **CC-BY 4.0** | **Si**, con su atribucion |
| **Major TOM** | ESA Φ-lab | **CC-BY-SA 4.0** | **No**: share-alike, arrastraria el cubo entero |

AlphaEarth publica 64 canales anuales de 2017 a 2025 en `gs://alphaearth_foundations`,
y exige la cadena literal: «The AlphaEarth Foundations Satellite Embedding
dataset is produced by Google and Google DeepMind».

Major TOM es mas rico —incluye embeddings derivados de Sentinel-1 y Sentinel-2
con varios modelos, y hasta una version del propio AlphaEarth— pero su CC-BY-SA
lo deja fuera del activo por la misma regla que deja fuera el dato de escombros
de UNEP/OCHA. Se consume como referencia externa o no se consume.

**Que la eleccion sea de licencia y no de calidad conviene tenerlo escrito**,
porque el dia que alguien compare las dos por su rendimiento y elija Major TOM,
la decision correcta seguira siendo la otra.

#### Y el contrato de esquema no lo comprobaba nadie

`schemas/parquet/tables.yaml` declara las columnas del activo, sus tipos y su
procedencia. **Ni una linea de codigo lo referenciaba**, asi que habia derivado:

* no declaraba `built_m2`, anadida al meter GHS-BUILT-S;
* seguia atribuyendo salud a **REPS** y educacion al directorio del **MEN**,
  dos fuentes resueltas en contra en T0.5 y T0.6.

Lo segundo es peor que lo primero. Un contrato incompleto se nota; un contrato
que nombra una fuente que no se usa **parece trazabilidad** y no lo es.

Corregido, y con una prueba que construye el activo minimo y compara sus
columnas reales contra las declaradas. Es el mismo patron que el calculo del
preliminar escrito y nunca llamado: un artefacto correcto que nadie ejecuta deja
de ser correcto sin avisar.

### T2.4 — La rama de pesos, sin cambios

Sigue en pie tal como esta escrito en `p4_brigada/protocol.py`: un modelo
afinado desde xBD/xView2 hereda CC BY-NC-SA y va al cubo `nc/`. Lo que cambia
tras T2.1 y T2.2 es que **la rama limpia ya tiene de que alimentarse**: EMS para
etiquetas, Umbra y Capella para imagen, las dos CC BY. La rama limpia deja de
ser una aspiracion y pasa a ser una ruta con fuentes nombradas.

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
| T2.1–T2.3 | ✅ resueltas el 24-ago-2026 (ronda 5) |
| T2.4 | La rama de pesos limpia ya tiene fuentes; falta construirla |
| T3.1 | ✅ resuelta el 24-ago-2026: AlphaEarth CC-BY 4.0 entra; Major TOM CC-BY-SA no |
