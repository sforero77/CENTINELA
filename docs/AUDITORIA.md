# Auditoría del 25-ago-2026

Auditoría completa del repositorio el día siguiente a que el sistema entrara en
operación. Este documento es el **spec de las tareas que abrio**: cada una con
su evidencia, su criterio de aceptación y su estado.

No es un documento vivo. Cuando todas las tareas cierren, lo que quede abierto
se muda a [`../PENDIENTES.md`](../PENDIENTES.md) y esto se queda como registro
de que se audito y con que método.

> **Los fallos agrupados por causa están en
> [FAMILIAS_DE_FALLO.md](FAMILIAS_DE_FALLO.md).** Este fichero los lista uno a
> uno; aquel los reduce a siete familias, que es lo que sirve para reconocer el
> siguiente antes de que muerda.

## Estado medido, no declarado

| | |
|---|---|
| Pruebas sin red | 523, todas pasan, ninguna saltada |
| `ruff check` · `ruff format` · `mypy --strict` | limpios (102 módulos) |
| Cobertura | 72 % |
| Trigger en producción | 20+ corridas el 25-ago, todas verdes |
| Activos publicados | 18 de 19 países (falta BRA) |
| Reportes publicados | 3 backtests · G1, G2, G3 verdes |
| Issues / PRs abiertos | ninguno · árbol limpio |

El estado real iba **por delante** de lo que decian `README.md`,
`PENDIENTES.md` y `docs/OPERACION.md`. Ese desfase es en si mismo un hallazgo:
un repositorio público cuyo argumento es la confianza en sus cifras no puede
publicar cifras viejas en la portada.

---

## A1 · El latido de `/status` nunca llegaba a publicarse

**Severidad:** alta · **Estado:** ✅ cerrada

`cli.py` escribe el latido en **cada** corrida del trigger, con este comentario
al lado:

> «Se escribe siempre, también cuando no hay eventos: la ausencia de latidos es
> la señal de que el cron se desactivo, que es el modo de falla más probable de
> todo el sistema.»

Pero `trigger.yml` condicionaba el commit a `hay_trabajo == 'true'`. En una
corrida tranquila (el caso normal, y **exactamente el caso que el latido existe
para vigilar**) el fichero se escribia en el runner y se tiraba.

**Evidencia.** `site/status.json` llevaba `"latidos": []` después de 20+
corridas exitosas el mismo día. La página pública decía «Sin latidos
registrados todavía» y lo iba a decir siempre.

El ping a healthchecks.io si salía (`if: always()`), así que el monitor privado
funcionaba. Era la página pública la que estaba ciega.

**Criterio de aceptación.** Una corrida sin eventos deja el latido en git. El
commit de estado no depende de que haya trabajo.

**Decisión de cadencia.** Publicar el latido en cada corrida son ~36 commits al
día. Se acota conservando los últimos `MAX_LATIDOS` y **saltando el commit
cuando el fichero no cambia de forma relevante**: el trigger empuja como mucho
un commit por hora. Efecto lateral bueno: eso solo ya mantiene vivos los
schedules contra la desactivacion a los 60 días.

## A2 · `status.json` tampoco se refrescaba al publicar un reporte

**Severidad:** alta · **Estado:** ✅ cerrada

`impact.yml` hacia `git add events/ reports/`, sin `site/status.json` y sin
llamar a `centinela status`.

**Evidencia.** Los tres reportes se publicaron el 25-ago a las 03:2x;
`status.json` seguía diciendo `generado_utc: 2026-08-23T18:27`,
`backtests_excluidos: 1`, y listaba un solo evento.

**Por qué importa.** «Latencia medida y publicada» es uno de los dos requisitos
que quedan para cerrar Fase 0. No lo cerraba el primer sismo: lo bloqueaba este
`git add`. El sistema iba a calcular la latencia correctamente y a no
publicarla.

**Criterio de aceptación.** Publicar un reporte actualiza la página de estado en
la misma corrida.

## A3 · El build trimestral solo reconstruia Colombia

**Severidad:** media-alta · **Estado:** ✅ cerrada

`exposure_quarterly.yml` fijaba `ISO3: ${{ inputs.iso3 || 'COL' }}`. El
comentario de al lado todavía decía «Fase 0 construye un solo país. Cuando Fase
1 traiga los siete, esto vuelve a ser una matriz», pero Fase 1 ya había
ocurrido: hay 18 activos publicados.

**Por qué urge.** Los 19 manifests fijan el mismo release de Overture,
`2026-08-19.0`, y Overture conserva solo dos (~2 meses). La corrida del 1-oct
refrescaba COL con el pin todavía vivo; poco después el pin muere y **ninguno de
los otros 17 países se puede reconstruir** hasta que alguien suba los vintages.

**Criterio de aceptación.** La corrida programada reconstruye todos los países
con activo publicado, un país roto no impide los demás, y el despacho manual de
un solo país sigue funcionando igual.

## A4 · El README publicaba cifras que ya no eran las publicadas

**Severidad:** media-alta · **Estado:** ✅ cerrada

Único documento sin tocar desde el 23-ago 22:50: antes de reconstruir el activo
(col-v0.4 → col-v0.5) y de regenerar los reportes. Cinco de nueve filas del
backtest del Chocó no coincidian con `reports/us6000tjl2/report.json`:

| README | Publicado |
|---|---|
| 65 años o más: 270 mil | 289.257 |
| Edificaciones: 444.281 | 444.424 |
| Sedes de salud: 512 | 518 |
| Sedes educativas: 997 | 998 |
| **Km de vía en MMI≥7: 1.400** | **8.503** (984,7 principales) |
| Licuefacción: 1.660.190 | 1.600.028 |

Más «52,9 millones de habitantes» contra `medido_ghs_pop: 52.620.466`. La cifra
de vías estaba errada por un factor de seis, en la portada de un repositorio
público cuyo argumento entero es que sus números son de fiar.

**Criterio de aceptación.** Las cifras del README salen del artefacto publicado,
y una prueba falla si vuelven a divergir. Una tabla de cifras a mano se
desincroniza; una tabla con prueba, no.

## A5 · La capa que conecta todo no tenía ni una prueba

**Severidad:** media-alta · **Estado:** ✅ cerrada

| Módulo | Cobertura previa | Qué hace |
|---|---|---|
| `pipelines/cli.py` | **0 %** (172 sentencias) | El punto de entrada de todos los workflows |
| `p0_exposure/raster_h3.py` | **0 %** | Agregación ráster→H3: de aquí sale **cada cifra de población** |
| `p3_report/celdas.py` | **0 %** | Escribe `celdas.json`, el fichero que dibuja el visor |

Los dos últimos solo se importan, en import diferido, desde dentro de funciones
de `build.py` y `run.py`, en tramos que la cobertura marcaba sin ejecutar.

**Por qué importa más que el número.** Es literalmente la clase de fallo que
este proyecto ya se cazó tres veces: `static_map.py` no tenía pruebas y publicó
seis PNG vacios en tres reportes; `compute_preliminary` estaba escrita, probada
y sin llamador; tres capas del activo se agregaban a tablas que nadie leia.
Todos fueron fallos de **cableado**, y la capa de cableado era la que no tenía
pruebas. `celdas.py` estaba donde estaba `static_map.py` una semana antes.

**Criterio de aceptación.** Los tres módulos con pruebas que ejerciten el camino
real, no solo la función. Para `cli.py` eso significa despachar subcomandos.

## A6 · Los asserts de calidad de §6.4 no corrian en el camino vivo

**Severidad:** media · **Estado:** ✅ cerrada

`exposure_join.check_quality()` (`pop_negativa`, `pop_nula`,
`crosswalk_incompleto`) no se llamaba en producción **ni en las pruebas**. Su
llamador previsto, `run_join()`, cuya docstring afirmaba «corre los asserts de
calidad de §6.4 sobre el resultado», estaba muerto también:
`pipeline.compute_impact()` lo reemplazo y hace el register + SQL en línea, sin
los asserts.

**Criterio de aceptación.** Los asserts corren en el camino de impacto y su
resultado va al log y a las notas del reporte. Un assert que no corre es peor
que no tenerlo: ocupa el sitio de la vigilancia que no existe.

## A7 · Código muerto que se leia como vivo

**Severidad:** media · **Estado:** ✅ cerrada

- **`hdx.resolve_resource`**: 40 líneas, **11 referencias en pruebas**, cero
  llamadores. La reemplazo `resolve_attempts`, que es la que usa `download.py`.
  Las pruebas probaban la muerta.
- **`licensing.assert_publishable_in_report`**: la guarda que impide que una
  fuente NC alimente el reporte automático. Probada, nunca invocada.
- `products.fetch_products`, `paths.ensure_workspace`, `paths.report_dir`,
  `crosswalk.validate_fractions`, `crosswalk.prorate`: sin llamador.
- `exposure_join.QUALITY_FLAGS`: copia inerte de `build.SQL_FLAGS`, que es la
  viva. Identicas hoy; dos copias de la misma regla es una trampa de deriva.

En un proyecto cuyo fallo recurrente es «una función escrita no es una función
conectada», **probada-pero-sin-cablear es el mejor disfraz que existe**: la
cobertura la marca en verde.

**Criterio de aceptación.** Cada función sin llamador queda borrada o cableada,
nunca en el limbo. Y una prueba impide que el limbo vuelva.

## A8 · Deriva documental

**Severidad:** media · **Estado:** ✅ cerrada

- `docs/OPERACION.md` §6 listaba como abiertos «PMTiles del visor (hoy el mapa
  esta vacío)» y «RF-03… se calcula por radios pero no se emite». Ambos
  cerrados. Su §4 decía «solo Colombia está medida»: son 18.
- `PENDIENTES.md` §2.1 decía que faltaba correr el backtest de Venezuela (esta
  publicado) y que su tolerancia era 5 % (es 5,44, **estrechada** desde 8,0).
  §2.5 decía que los países nuevos llevan «un 5 % provisional».

**Criterio de aceptación.** Los cuatro documentos de estado describen lo que
hay. Donde se pueda, con una prueba que lo sostenga en vez de con disciplina.

## A9 · No había comando para regenerar los mapas publicados

**Severidad:** baja · **Estado:** ✅ cerrada

Los seis PNG de los tres reportes se rehicieron con un script de usar y tirar
tras el arreglo de `static_map.py`. La proxima corrección de simbología
dependia de que alguien recordara como se hacia.

**Criterio de aceptación.** `centinela regenerar-mapas [USGS_ID]` rehace los
mapas de un reporte publicado, o de todos, desde sus artefactos en disco.

---

# Lo que apareció mientras se arreglaba

Cinco hallazgos que no estaban en la auditoría inicial. Los cuatro primeros
salieron de A5 y A7: de escribir las pruebas que faltaban y de mirar el grafo
de llamadas con cuidado. Eso es lo que se esperaba de ellos.

## A11 · Un PROJ del sistema dejaba inservible todo el pipeline geo

**Severidad:** alta · **Estado:** ✅ cerrada

Encontrado al escribir las primeras pruebas de `raster_h3`, que son las
primeras del repositorio que escriben un GeoTIFF con CRS.

`rasterio` y `pyproj` empaquetan cada una su base de datos de PROJ y la
encuentran solas. Una variable `PROJ_LIB` puesta en el sistema las tapa a las
dos, y entonces **ningún CRS se resuelve**:

    proj.db contains DATABASE.LAYOUT.Versión.MINOR = 2 whereas a number >= 6
    is expected. It comes from another PROJ installation.

Pasa sin que nadie lo pida: instalar PostgreSQL con PostGIS en Windows deja
`PROJ_LIB` apuntando a su propio PROJ. Con el se cae la reproyección de GHS-POP
desde Mollweide, que es el primer paso de cada cifra de población. O sea
`centinela country` inservible en un equipo que cumple todos los requisitos, y
con un mensaje que no apunta a la causa.

O4 dice que el sistema construye un país desde un clon limpio **sin
dependencias del sistema**. Un PROJ del sistema es una dependencia del sistema,
y encima una que nadie eligio.

`ensure_bundled_proj()` la aparta antes de cada import de GDAL/PROJ, y tiene que
ser antes, porque GDAL fija su ruta de búsqueda al inicializarse y después ya no
la relee. Hay escape (`CENTINELA_RESPETA_PROJ=1`) para quien de verdad necesite
rejillas geoidales nacionales.

## A12 · RF-04 renderizaba un changelog que nadie calculaba

**Severidad:** media · **Estado:** ✅ cerrada

RF-04 pide re-emitir el reporte «con changelog de deltas», y da el ejemplo:
`pop MMI≥7: 340k → 355k`. Estaba escrito casi entero: `Report.changelog`
existía, `markdown.py` renderizaba la sección, `format_delta_prose` daba
exactamente ese formato. **Ninguna línea del pipeline lo llenaba**, así que la
sección no apareció en un solo reporte publicado.

Importa durante una emergencia: un ShakeMap se revisa muchas veces (el de
Venezuela llegó a v14) y quien ya leyó la versión anterior necesita saber que
cambio, no releerla entera.

Se compara la cifra **ya redondeada**, no la exacta: si una revisión mueve la
población de 2.424.287 a 2.424.296, el reporte dice "2,4 millones" en los dos
sitios y anunciarlo sería inventar una diferencia que nadie puede ver.

## A13 · La licencia de la fuente no se contrastaba nunca

**Severidad:** media-alta · **Estado:** ✅ cerrada

La docstring de `dataset_license` decía desde el primer día que esto «se
consulta en cada build y se contrasta con lo que dice el manifest: si el
publicador cambia la licencia, queremos enterarnos por un fallo del lint y no
por un reclamo». Ni ella ni `map_license` tenían un solo llamador.

Es el peor sitio para ese hueco. La contaminación entre cubos es el riesgo que
la espec clasifica de impacto alto (§7), el manifest fija la licencia una vez y
a mano, y un publicador que la cambie (de CC BY a CC BY-NC) dejaria el activo
con una fuente que el reporte no puede consumir, con todo pasando en verde.

Ahora `download_hdx` la contrasta antes de bajar un byte, y **falla el build**:
descargar sabiendo que la licencia no es la declarada es justo lo que no se
puede hacer, porque el archivo entra al activo y el activo se publica.

## A14 · Una prueba verde apuntando a la función muerta

**Severidad:** baja (el código vivo estaba bien) · **Estado:** ✅ cerrada

`test_todas_las_rutas_de_descarga_saltan_lo_que_ya_esta` verifica el invariante
de que reanudar un build sea barato. Recorria cuatro funciones y una era
`download_zip_entries`, **la muerta**. Al borrarla, la prueba pasó a mirar
`download_zip_completo`, la viva, y fallo.

Resultó ser la prueba y no el código: `download_zip_completo` si comprueba el
disco, con `is_dir()` en vez de `exists()`, y la prueba emparejaba texto. Pero
el susto es el hallazgo: durante meses ese invariante se estuvo verificando
sobre código que no corría. Una prueba que cubre una función muerta da la misma
sensación de seguridad y no cubre nada.

## A15 · Las pruebas de ráster pasaban por orden de ejecución

**Severidad:** baja · **Estado:** ✅ cerrada

Tras arreglar A11, las pruebas nuevas de `raster_h3` pasaban en la suite
completa y fallaban sueltas: para cuando les llegaba el turno, otro módulo ya
había llamado a `ensure_bundled_proj()`. Verde por orden de ejecución, que es
peor que rojo: desaparece en cuanto alguien corre una prueba sola o pytest
reordena.

La llamada vive ahora en `tests/conftest.py`, antes de que ningún módulo de
prueba importe rasterio.

---

# Segunda tanda: que el sistema sirva a LATAM de verdad

Los hallazgos de arriba salieron de leer el código. Los de aquí salieron de
**correrlo sobre la región entera**: diecisiete backtests históricos en doce
países, del catálogo real de USGS. Ninguno se habría encontrado sin esos datos.

## A16 · Chile no habría tenido reporte nunca

**Severidad:** crítica · **Estado:** ✅ cerrada

`countries_for_point` devuelve los países cuya **caja envolvente** contiene el
epicentro, ordenados por área, y `impact.yml` se quedaba con el primero que
tuviera Release publicado.

El área es un mal criterio y el caso que lo rompe no es raro: **la caja de Chile
mide 1.719 grados cuadrados porque llega a Rapa Nui**, y la de Argentina 671.
Medido sobre el epicentro real del M6,7 de Coquimbo (2019), los candidatos salen
`[ARG, CHL, BRA]`. El workflow habría bajado el activo argentino, el join no
habría encontrado una sola celda y el evento se habría quedado sin reporte.
Cada vez, para uno de los países más sísmicos de la región.

Lo más incomodo del hallazgo: **el diseño correcto estaba escrito desde el
principio y en dos sitios**. Las docstrings de `countries_for_point` y de
`paises-candidatos` dicen que el llamador «prueba en ese orden y el join contra
las celdas H3 desempata de verdad». El workflow no lo hacia. Es el mismo patrón
de A5 y A7 (lo escrito y lo conectado) pero en el peor sitio posible.

Cerrado con un código de salida propio (`3`, "este activo no es de este sismo")
que el workflow distingue de un fallo real, y un bucle que prueba los candidatos
hasta que uno alcanza celdas. El backtest de Coquimbo, ya publicado, da 467.130
personas en MMI≥7.

## A17 · Casi la mitad de los sismos reales no llegan a MMI≥7

**Severidad:** alta · **Estado:** ✅ cerrada

El producto entero (el titular del visor, el ranking municipal, la tabla del
markdown, el círculo del epicentro, el hilo) daba por supuesto que MMI≥7 es *la*
banda. Sobre los primeros dieciocho reportes del catálogo LATAM, **ocho no
alcanzan MMI≥7 sobre población**. El 44 %.

No son casos raros: son los sismos profundos y los de mar adentro, que en esta
región son la mitad del catálogo. Para ellos el sistema publicaba:

* una cifra grande que decía **0 personas**,
* una tabla de "municipios más expuestos" ordenada por una columna de ceros (o
  sea, en orden alfabético),
* y quince ceros bajo un rótulo que prometía cifras.

**Tehuantepec 2017 se publicaba así.** Un M8,2 con 98 muertos, cuyo máximo sobre
población mexicana es MMI 6,5 según el ShakeMap que el propio USGS prefiere,
salía como "0 personas en MMI≥7" con una tabla alfabetica debajo. Un cero es
cierto y se lee como que el sistema fallo, o como que el sismo no fue nada.

Cerrado con `Totales.banda_titular`: la banda más alta que alcanzo población.
Con ella se titula, se ordena y se rotula. Cuando el evento llega a MMI≥7 (el
caso normal) no cambia absolutamente nada.

## A18 · El producto nombraba sus sismos en inglés

**Severidad:** media-alta · **Estado:** ✅ cerrada

USGS publica el lugar en inglés (`20 km W of Catia La Mar, Venezuela`) y esa
cadena viajaba tal cual al título del reporte, al hilo para redes, al mapa
estático y al visor. RF-06 pide "reporte en español neutro con topónimos
oficiales del país": la segunda mitad se cumplia, la primera no.

Se notaba poco porque el único reporte publicado era el del Chocó, cuyo lugar
venía de una fixture escrita a mano en español. En cuanto entraron diecisiete
eventos reales, el tablero quedó en inglés.

`traducir_lugar` traduce el andamiaje (`W of` → `al O de`, `Mexico` → `México`)
y **nunca el topónimo**: `Catia La Mar` es un nombre propio, y traducirlo
produciría lugares que no existen en ningún mapa oficial. Ante una forma que no
reconoce devuelve el original: un lugar en inglés se lee raro, uno mal traducido
lleva a otro sitio.

## A19 · La tabla municipal rotulaba todo como DIVIPOLA

**Severidad:** media · **Estado:** ✅ cerrada

La columna de codigos del reporte decía "DIVIPOLA", que es el código municipal
**de Colombia**. En el reporte de Tehuantepec rotulaba `MX20043` como DIVIPOLA.

Es la marca de agua de un sistema que se construyó con un país y se declaro
regional. Ahora se rotula por lo que es (un código de municipio) y el país lo
pone el manifest.

## A20 · El visor no decía que el sistema es regional

**Severidad:** media-alta · **Estado:** ✅ cerrada

El tablero listaba eventos y nada más. Con tres reportes de dos países eso se
lee como una demo, y lo que hay detrás no lo es: **dieciocho países con su
activo construido, medido contra la cifra oficial de su instituto o de la ONU, y
publicado: 430,9 millones de personas ya en la malla hexagonal, calculadas
antes de que ocurra nada**.

Ese hecho responde la pregunta que se hace quien llega (*¿esto sirve para mi
país?*) y no aparecia en ninguna pantalla. La respuesta que daba el tablero,
por omisión, era que no.

`site/cobertura.json` sale de los manifests y no de un listado aparte, para que
**no pueda prometer más países de los que el sistema construyó**: lo que delata
a un país construido es su `medido_ghs_pop`, que solo escribe un build de
verdad. Brasil aparece marcado como pendiente en vez de esconderse.

## A21 · Que un país no tenga reporte no significa lo mismo en todos

**Severidad:** media · **Estado:** ✅ cerrada

Al buscar históricos para los seis países que no tenían ninguno, la respuesta
resultó ser distinta en cada caso, y el tablero los mostraba igual, como un
hueco.

**Paraguay y Uruguay no han tenido un solo sismo M≥5,5 desde el año 2000.**
Ninguno. Su activo está construido, medido y esperando. Para un sistema cuyo
propósito es estar listo por adelantado, eso no es una carencia: es exactamente
el estado que se persigue, y presentarlo como un vacío lo cuenta al revés.

**Brasil no puede tener reporte, y no es por el activo.** Sus doce sismos
M≥5,5 desde 2000 están todos entre 534 y **645** km de profundidad, en Acre, y
**USGS no publica contornos MMI para ninguno**. (El tope decía 603 y estaba mal;
recontado el 1-sep-2026, el más profundo es `usp000fgsv` a 644,9 km. La
conclusión no cambia: cuanto más profundo, menos superficie que medir.) Un sistema que calcula sobre
`cont_mmi` no tiene nada que calcular ahí. Construir su activo sigue teniendo
sentido (un sismo somero raro en la costa cambiaria eso en un día) pero
conviene decir por que su casilla de reportes esta vacía.

**Argentina y Republica Dominicana si tenían eventos**, y no aparecían porque
el primer lote se busco con umbral M6,3 (el sistema dispara a M5,5) y porque
las cajas envolventes de Argentina y Bolivia se llenan de sismos chilenos, que
tapaban a los suyos al ordenar por relevancia. Ya tienen reporte: Pocito 2021
(M6,4, San Juan) y Baní 2012 (M5,5).

**Bolivia resultó NO ser el caso de Brasil, y esta sección lo dijo al revés
durante seis días.** Decía que sus veintidós sismos M≥5,5 desde 2000 estaban
«entre 359 y 596 km». Recontado el 1-sep-2026 contra el catálogo de USGS, van
**de 33 a 608 km**, y el más somero (`usp000ahzc`, M6,2 del 4-jul-2001, cerca de
Colomi) tiene MMI modelada de 6,4 y publica `cont_mmi.json`.

**La causa es la que esta misma sección describe dos parrafos más abajo**, y por
eso duele: la búsqueda se ordenó por relevancia sobre una caja envolvente que se
llena de sismos chilenos. Se diagnóstico para Argentina y Republica Dominicana,
se corrigio para las dos, y a Bolivia se le aplicó la conclusión de Brasil sin
volver a mirar. Un sesgo identificado y no barrido hasta el final deja
exactamente este residuo.

Bolivia tiene un reporte pendiente de construir, no un silencio explicado: esta
en `PENDIENTES.md` §2.1.bis, y `tests/integration/test_silencio_de_paises_live.py`
vuelve a comprobarlo contra USGS en cada corrida nocturna.

**Y el descarte por país se estreno en real.** De los tres eventos dominicanos
probados, dos (ambos frente a Punta Cana, a 77 y 102 km mar adentro) salieron
con código 3: el activo dominicano no los alcanza. Con el comportamiento
anterior habrían publicado un reporte de ceros.

La nota de la sección de cobertura del visor ahora distingue los tres estados:
construido con reportes, construido y en silencio, y sin construir.

---

# Tercera tanda: auditoría de UX/UI y cartografia

Hecha **abriendo el visor publicado con los 21 reportes reales**, no leyendo su
código. Los cinco hallazgos siguen ese orden: primero lo que se ve, luego por
que.

## A22 · El mapa se quedaba en blanco al abrir un enlace compartido

**Severidad:** alta · **Estado:** ✅ cerrada

`?evento=us7000nr0v` con la caché fría dejaba el mapa **completamente vacío**:
sin base, sin malla, sin leyenda, sin selector de capas y **sin un solo error en
consola**. El panel lateral cargaba entero, así que ni siquiera parecia roto:
parecia un mapa que no tiene nada que enseñar.

El mismo enlace con la caché caliente funciona. Es una carrera, y le toca justo
a **quien abre por primera vez un enlace que alguien le compartió**: el único
público que este visor tiene hasta que ocurra el primer sismo en vivo.

La causa: `cuandoElEstiloEsteListo` usaba `m.once("load", fn)`. Ese evento
dispara **una sola vez**. Si ya disparo y `isStyleLoaded()` sigue devolviendo
false (cosa que pasa mientras una fuente está en vuelo) el callback queda
registrado para algo que no volverá a ocurrir. Se cambia por `styledata` +
`idle`, que entre los dos no dejan ventana.

## A23 · El epicentro se salía del encuadre

**Severidad:** media-alta · **Estado:** ✅ cerrada

`fitBounds` se calculaba sobre la malla y nada más. La malla llega hasta donde
hay algo expuesto, así que **en un sismo mar adentro el epicentro queda fuera**.
Medido sobre los 18 eventos con malla: en Carúpano, La Libertad y Bartolomé Masó
cae fuera de la caja, y en Cuba la estrella salía cortada por el borde inferior
de la pantalla.

Ver la afectación *desde el epicentro* empieza por ver el epicentro.

## A24 · La celda no se podía citar

**Severidad:** media · **Estado:** ✅ cerrada

`celdasAGeoJson` excluía explícitamente el índice H3 de las propiedades del
hexágono (`if (nombre !== "h3")`), así que la ficha enseñaba siete cifras y
ninguna forma de saber **de que celda**.

Con eso se iba la única manera de cruzar lo que se ve en el mapa con el
`celdas.json` que el propio visor ofrece para descargar dos paneles más abajo, y
con el parquet del activo. Para quien trabaja con SIG, un dato que no se puede
referenciar es un dato que no se puede usar. Quince caracteres por celda.

## A25 · La ficha no decía a que distancia del epicentro estaba la celda

**Severidad:** media · **Estado:** ✅ cerrada

Es la primera pregunta ante una celda sacudida, y la que separa «esta cerca» de
«esta lejos y aun así le llegó». No estaba en ninguna parte del visor.

Se calcula con **el mismo radio terrestre que usa el pipeline**
(`pipelines/common/geo.py`). Dos números distintos para la misma distancia, uno
en el mapa y otro en el reporte, es la clase de discrepancia que destruye la
confianza en todo lo demás, y hay una prueba que compara las dos formulas.

## A26 · La profundidad estaba enterrada, y es lo que explica el catálogo

**Severidad:** media · **Estado:** ✅ cerrada

Vivía en una línea de metadatos, entre la fecha y la versión del ShakeMap. A
igual magnitud, la profundidad decide cuanto se siente en superficie: o sea que
es **exactamente lo que explica los casos raros del catálogo**: Tehuantepec fue
un M8,2 y su máximo sobre población mexicana es MMI 6,5; los veintidós sismos
bolivianos van de 33 a 608 km, y el más somero si produce celdas: ver arriba y
`PENDIENTES.md` §2.1.bis.

Un lector que ve «M8,2» y «0 personas en MMI≥7» sin ver «47 km» no tiene con que
entenderlo. Ahora es el primer distintivo, clasificado con los cortes estándar
de sismología: superficial hasta 70 km, intermedio hasta 300, profundo por
encima.

## A27 · El tablero enseñaba la exposición y la llamaba afectación

**Severidad:** alta · **Estado:** ✅ cerrada

Lo pidio quien lo usa, mirando el evento de Baláo: «me gustaria ver el área de
afectación del terremoto». No estaba.

La malla H3 llega **hasta donde hay algo expuesto** y se corta ahí, con huecos
que son ausencia de población y no de sacudida. La nota de la leyenda lo
admitia («el hueco no es ausencia de sacudida, es ausencia de gente y de
infraestructura») y aun así era lo único que el visor dibujaba. Enseñaba **la
forma de la población recortada por el sismo**, y quien preguntaba hasta donde
llegó el terremoto no tenía donde mirarlo.

Medido sobre Baláo 2023: el área sentida (MMI 4) mide unos 410 km de lado y la
que el sistema cuantifica (MMI≥6) unos 180. **Cuatro veces más ancha**, y toda
esa diferencia quedaba fuera del tablero.

Lo más incomodo: **el pipeline ya descargaba los contornos en cada evento** (son
la entrada del polyfill que produce la malla) y los tiraba al terminar. El dato
estaba, pasaba por las manos del sistema y no llegaba a ninguna pantalla.

Ahora `contornos.json` viaja con cada reporte (unos 20 kB) y el visor dibuja las
isolíneas **debajo** de la malla: donde hay hexágonos manda el dato, y fuera de
ellos la línea es lo único: que es justo donde hacia falta. La de MMI 6 va más
gruesa, porque es la frontera desde la que este sistema publica cifras. Por
debajo de 6 van en gris: son niveles que se sienten y que el sistema **no
cuantifica**, y pintarlos con la rampa de intensidad sugeriría que si.

El encuadre pasa a cubrir el contorno de MMI 6 además de la malla y el
epicentro. No el de MMI 4: en un M8 abarca medio continente y dejaria la malla
del tamaño de un sello.

Los 21 reportes ya publicados se rellenaron con `centinela contornos`, que los
trae de USGS sin recomputar el impacto: un comando y no un script de usar y
tirar, por lo mismo que existe `regenerar-mapas`.

## Lo que se revisó y estaba bien

Conviene decirlo, porque son decisiones que costaron y que la auditoría
confirma:

* **La rampa de intensidad** es secuencial naranja-rojo, no el arcoíris de
  ShakeMap, con luminosidad estrictamente descendente: sobrevive al daltonismo
  rojo-verde y a la impresión en blanco y negro.
* **La leyenda rotula solo las clases que el evento alcanza.** El Chocó no pasa
  de 7,5 y su leyenda tiene cuatro muestras, no seis.
* **La coropleta va debajo de los topónimos.** Quibdó, Pereira y Cali se leen
  sobre el dato.
* **Los cortes están medidos** sobre la distribución real, con clases
  geométricas, y cada capa declara su fuente y su unidad en la propia leyenda.
* **La barra de escala** acompana el zoom, y el borde del hexágono aparece solo
  cuando la celda mide lo bastante como para que su contorno signifique algo.

---

## A10 · Clean Code aplicado al repositorio

**Estado:** ✅ cerrada

La auditoría incorporo una revisión contra los principios de *Clean Code*
(Robert C. Martin) y su lectura moderna en Python. Lo adoptado, con lo que
significa **aquí**, está en [`CLEAN_CODE.md`](CLEAN_CODE.md).

La regla que más trabajo dio no es de estilo: **«always find root cause»**.
Cinco de los nueve hallazgos son la misma causa raíz (una función escrita y no
conectada) apareciendo en cinco sitios distintos. Arreglarlos uno a uno sin
nombrar el patrón habría dejado el sexto para la proxima auditoría. Por eso A5
y A7 cierran con **pruebas que vigilan el patrón**, no solo con los arreglos.
