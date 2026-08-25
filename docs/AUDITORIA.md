# Auditoria del 25-ago-2026

Auditoria completa del repositorio el dia siguiente a que el sistema entrara en
operacion. Este documento es el **spec de las tareas que abrio**: cada una con
su evidencia, su criterio de aceptacion y su estado.

No es un documento vivo. Cuando todas las tareas cierren, lo que quede abierto
se muda a [`../PENDIENTES.md`](../PENDIENTES.md) y esto se queda como registro
de que se audito y con que metodo.

## Estado medido, no declarado

| | |
|---|---|
| Pruebas sin red | 523, todas pasan, ninguna saltada |
| `ruff check` · `ruff format` · `mypy --strict` | limpios (102 modulos) |
| Cobertura | 72 % |
| Trigger en produccion | 20+ corridas el 25-ago, todas verdes |
| Activos publicados | 18 de 19 paises (falta BRA) |
| Reportes publicados | 3 backtests · G1, G2, G3 verdes |
| Issues / PRs abiertos | ninguno · arbol limpio |

El estado real iba **por delante** de lo que decian `README.md`,
`PENDIENTES.md` y `docs/OPERACION.md`. Ese desfase es en si mismo un hallazgo:
un repositorio publico cuyo argumento es la confianza en sus cifras no puede
publicar cifras viejas en la portada.

---

## A1 · El latido de `/status` nunca llegaba a publicarse

**Severidad:** alta · **Estado:** ✅ cerrada

`cli.py` escribe el latido en **cada** corrida del trigger, con este comentario
al lado:

> «Se escribe siempre, tambien cuando no hay eventos: la ausencia de latidos es
> la senal de que el cron se desactivo, que es el modo de falla mas probable de
> todo el sistema.»

Pero `trigger.yml` condicionaba el commit a `hay_trabajo == 'true'`. En una
corrida tranquila —el caso normal, y **exactamente el caso que el latido existe
para vigilar**— el fichero se escribia en el runner y se tiraba.

**Evidencia.** `site/status.json` llevaba `"latidos": []` despues de 20+
corridas exitosas el mismo dia. La pagina publica decia «Sin latidos
registrados todavia» y lo iba a decir siempre.

El ping a healthchecks.io si salia (`if: always()`), asi que el monitor privado
funcionaba. Era la pagina publica la que estaba ciega.

**Criterio de aceptacion.** Una corrida sin eventos deja el latido en git. El
commit de estado no depende de que haya trabajo.

**Decision de cadencia.** Publicar el latido en cada corrida son ~36 commits al
dia. Se acota conservando los ultimos `MAX_LATIDOS` y **saltando el commit
cuando el fichero no cambia de forma relevante**: el trigger empuja como mucho
un commit por hora. Efecto lateral bueno: eso solo ya mantiene vivos los
schedules contra la desactivacion a los 60 dias.

## A2 · `status.json` tampoco se refrescaba al publicar un reporte

**Severidad:** alta · **Estado:** ✅ cerrada

`impact.yml` hacia `git add events/ reports/` — sin `site/status.json` y sin
llamar a `centinela status`.

**Evidencia.** Los tres reportes se publicaron el 25-ago a las 03:2x;
`status.json` seguia diciendo `generado_utc: 2026-08-23T18:27`,
`backtests_excluidos: 1`, y listaba un solo evento.

**Por que importa.** «Latencia medida y publicada» es uno de los dos requisitos
que quedan para cerrar Fase 0. No lo cerraba el primer sismo: lo bloqueaba este
`git add`. El sistema iba a calcular la latencia correctamente y a no
publicarla.

**Criterio de aceptacion.** Publicar un reporte actualiza la pagina de estado en
la misma corrida.

## A3 · El build trimestral solo reconstruia Colombia

**Severidad:** media-alta · **Estado:** ✅ cerrada

`exposure_quarterly.yml` fijaba `ISO3: ${{ inputs.iso3 || 'COL' }}`. El
comentario de al lado todavia decia «Fase 0 construye un solo pais. Cuando Fase
1 traiga los siete, esto vuelve a ser una matriz» — pero Fase 1 ya habia
ocurrido: hay 18 activos publicados.

**Por que urge.** Los 19 manifests fijan el mismo release de Overture,
`2026-08-19.0`, y Overture conserva solo dos (~2 meses). La corrida del 1-oct
refrescaba COL con el pin todavia vivo; poco despues el pin muere y **ninguno de
los otros 17 paises se puede reconstruir** hasta que alguien suba los vintages.

**Criterio de aceptacion.** La corrida programada reconstruye todos los paises
con activo publicado, un pais roto no impide los demas, y el despacho manual de
un solo pais sigue funcionando igual.

## A4 · El README publicaba cifras que ya no eran las publicadas

**Severidad:** media-alta · **Estado:** ✅ cerrada

Unico documento sin tocar desde el 23-ago 22:50 — antes de reconstruir el activo
(col-v0.4 → col-v0.5) y de regenerar los reportes. Cinco de nueve filas del
backtest del Choco no coincidian con `reports/us6000tjl2/report.json`:

| README | Publicado |
|---|---|
| 65 anos o mas: 270 mil | 289.257 |
| Edificaciones: 444.281 | 444.424 |
| Sedes de salud: 512 | 518 |
| Sedes educativas: 997 | 998 |
| **Km de via en MMI≥7: 1.400** | **8.503** (984,7 principales) |
| Licuefaccion: 1.660.190 | 1.600.028 |

Mas «52,9 millones de habitantes» contra `medido_ghs_pop: 52.620.466`. La cifra
de vias estaba errada por un factor de seis, en la portada de un repositorio
publico cuyo argumento entero es que sus numeros son de fiar.

**Criterio de aceptacion.** Las cifras del README salen del artefacto publicado,
y una prueba falla si vuelven a divergir. Una tabla de cifras a mano se
desincroniza; una tabla con prueba, no.

## A5 · La capa que conecta todo no tenia ni una prueba

**Severidad:** media-alta · **Estado:** ✅ cerrada

| Modulo | Cobertura previa | Que hace |
|---|---|---|
| `pipelines/cli.py` | **0 %** (172 sentencias) | El punto de entrada de todos los workflows |
| `p0_exposure/raster_h3.py` | **0 %** | Agregacion raster→H3: de aqui sale **cada cifra de poblacion** |
| `p3_report/celdas.py` | **0 %** | Escribe `celdas.json`, el fichero que dibuja el visor |

Los dos ultimos solo se importan, en import diferido, desde dentro de funciones
de `build.py` y `run.py` — en tramos que la cobertura marcaba sin ejecutar.

**Por que importa mas que el numero.** Es literalmente la clase de fallo que
este proyecto ya se cazo tres veces: `static_map.py` no tenia pruebas y publico
seis PNG vacios en tres reportes; `compute_preliminary` estaba escrita, probada
y sin llamador; tres capas del activo se agregaban a tablas que nadie leia.
Todos fueron fallos de **cableado**, y la capa de cableado era la que no tenia
pruebas. `celdas.py` estaba donde estaba `static_map.py` una semana antes.

**Criterio de aceptacion.** Los tres modulos con pruebas que ejerciten el camino
real, no solo la funcion. Para `cli.py` eso significa despachar subcomandos.

## A6 · Los asserts de calidad de §6.4 no corrian en el camino vivo

**Severidad:** media · **Estado:** ✅ cerrada

`exposure_join.check_quality()` —`pop_negativa`, `pop_nula`,
`crosswalk_incompleto`— no se llamaba en produccion **ni en las pruebas**. Su
llamador previsto, `run_join()`, cuya docstring afirmaba «corre los asserts de
calidad de §6.4 sobre el resultado», estaba muerto tambien:
`pipeline.compute_impact()` lo reemplazo y hace el register + SQL en linea, sin
los asserts.

**Criterio de aceptacion.** Los asserts corren en el camino de impacto y su
resultado va al log y a las notas del reporte. Un assert que no corre es peor
que no tenerlo: ocupa el sitio de la vigilancia que no existe.

## A7 · Codigo muerto que se leia como vivo

**Severidad:** media · **Estado:** ✅ cerrada

- **`hdx.resolve_resource`** — 40 lineas, **11 referencias en pruebas**, cero
  llamadores. La reemplazo `resolve_attempts`, que es la que usa `download.py`.
  Las pruebas probaban la muerta.
- **`licensing.assert_publishable_in_report`** — la guarda que impide que una
  fuente NC alimente el reporte automatico. Probada, nunca invocada.
- `products.fetch_products`, `paths.ensure_workspace`, `paths.report_dir`,
  `crosswalk.validate_fractions`, `crosswalk.prorate` — sin llamador.
- `exposure_join.QUALITY_FLAGS` — copia inerte de `build.SQL_FLAGS`, que es la
  viva. Identicas hoy; dos copias de la misma regla es una trampa de deriva.

En un proyecto cuyo fallo recurrente es «una funcion escrita no es una funcion
conectada», **probada-pero-sin-cablear es el mejor disfraz que existe**: la
cobertura la marca en verde.

**Criterio de aceptacion.** Cada funcion sin llamador queda borrada o cableada,
nunca en el limbo. Y una prueba impide que el limbo vuelva.

## A8 · Deriva documental

**Severidad:** media · **Estado:** ✅ cerrada

- `docs/OPERACION.md` §6 listaba como abiertos «PMTiles del visor (hoy el mapa
  esta vacio)» y «RF-03… se calcula por radios pero no se emite». Ambos
  cerrados. Su §4 decia «solo Colombia esta medida» — son 18.
- `PENDIENTES.md` §2.1 decia que faltaba correr el backtest de Venezuela (esta
  publicado) y que su tolerancia era 5 % (es 5,44, **estrechada** desde 8,0).
  §2.5 decia que los paises nuevos llevan «un 5 % provisional».

**Criterio de aceptacion.** Los cuatro documentos de estado describen lo que
hay. Donde se pueda, con una prueba que lo sostenga en vez de con disciplina.

## A9 · No habia comando para regenerar los mapas publicados

**Severidad:** baja · **Estado:** ✅ cerrada

Los seis PNG de los tres reportes se rehicieron con un script de usar y tirar
tras el arreglo de `static_map.py`. La proxima correccion de simbologia
dependia de que alguien recordara como se hacia.

**Criterio de aceptacion.** `centinela regenerar-mapas [USGS_ID]` rehace los
mapas de un reporte publicado, o de todos, desde sus artefactos en disco.

---

# Lo que aparecio mientras se arreglaba

Cinco hallazgos que no estaban en la auditoria inicial. Los cuatro primeros
salieron de A5 y A7 — de escribir las pruebas que faltaban y de mirar el grafo
de llamadas con cuidado. Eso es lo que se esperaba de ellos.

## A11 · Un PROJ del sistema dejaba inservible todo el pipeline geo

**Severidad:** alta · **Estado:** ✅ cerrada

Encontrado al escribir las primeras pruebas de `raster_h3`, que son las
primeras del repositorio que escriben un GeoTIFF con CRS.

`rasterio` y `pyproj` empaquetan cada una su base de datos de PROJ y la
encuentran solas. Una variable `PROJ_LIB` puesta en el sistema las tapa a las
dos, y entonces **ningun CRS se resuelve**:

    proj.db contains DATABASE.LAYOUT.VERSION.MINOR = 2 whereas a number >= 6
    is expected. It comes from another PROJ installation.

Pasa sin que nadie lo pida: instalar PostgreSQL con PostGIS en Windows deja
`PROJ_LIB` apuntando a su propio PROJ. Con el se cae la reproyeccion de GHS-POP
desde Mollweide, que es el primer paso de cada cifra de poblacion. O sea
`centinela country` inservible en un equipo que cumple todos los requisitos, y
con un mensaje que no apunta a la causa.

O4 dice que el sistema construye un pais desde un clon limpio **sin
dependencias del sistema**. Un PROJ del sistema es una dependencia del sistema,
y encima una que nadie eligio.

`ensure_bundled_proj()` la aparta antes de cada import de GDAL/PROJ — tiene que
ser antes, porque GDAL fija su ruta de busqueda al inicializarse y despues ya no
la relee. Hay escape (`CENTINELA_RESPETA_PROJ=1`) para quien de verdad necesite
rejillas geoidales nacionales.

## A12 · RF-04 renderizaba un changelog que nadie calculaba

**Severidad:** media · **Estado:** ✅ cerrada

RF-04 pide re-emitir el reporte «con changelog de deltas», y da el ejemplo:
`pop MMI≥7: 340k → 355k`. Estaba escrito casi entero: `Report.changelog`
existia, `markdown.py` renderizaba la seccion, `format_delta_prose` daba
exactamente ese formato. **Ninguna linea del pipeline lo llenaba**, asi que la
seccion no aparecio en un solo reporte publicado.

Importa durante una emergencia: un ShakeMap se revisa muchas veces —el de
Venezuela llego a v14— y quien ya leyo la version anterior necesita saber que
cambio, no releerla entera.

Se compara la cifra **ya redondeada**, no la exacta: si una revision mueve la
poblacion de 2.415.793 a 2.415.802, el reporte dice "2,4 millones" en los dos
sitios y anunciarlo seria inventar una diferencia que nadie puede ver.

## A13 · La licencia de la fuente no se contrastaba nunca

**Severidad:** media-alta · **Estado:** ✅ cerrada

La docstring de `dataset_license` decia desde el primer dia que esto «se
consulta en cada build y se contrasta con lo que dice el manifest: si el
publicador cambia la licencia, queremos enterarnos por un fallo del lint y no
por un reclamo». Ni ella ni `map_license` tenian un solo llamador.

Es el peor sitio para ese hueco. La contaminacion entre cubos es el riesgo que
la espec clasifica de impacto alto (§7), el manifest fija la licencia una vez y
a mano, y un publicador que la cambie —de CC BY a CC BY-NC— dejaria el activo
con una fuente que el reporte no puede consumir, con todo pasando en verde.

Ahora `download_hdx` la contrasta antes de bajar un byte, y **falla el build**:
descargar sabiendo que la licencia no es la declarada es justo lo que no se
puede hacer, porque el archivo entra al activo y el activo se publica.

## A14 · Una prueba verde apuntando a la funcion muerta

**Severidad:** baja (el codigo vivo estaba bien) · **Estado:** ✅ cerrada

`test_todas_las_rutas_de_descarga_saltan_lo_que_ya_esta` verifica el invariante
de que reanudar un build sea barato. Recorria cuatro funciones y una era
`download_zip_entries`, **la muerta**. Al borrarla, la prueba paso a mirar
`download_zip_completo`, la viva, y fallo.

Resulto ser la prueba y no el codigo: `download_zip_completo` si comprueba el
disco, con `is_dir()` en vez de `exists()`, y la prueba emparejaba texto. Pero
el susto es el hallazgo: durante meses ese invariante se estuvo verificando
sobre codigo que no corria. Una prueba que cubre una funcion muerta da la misma
sensacion de seguridad y no cubre nada.

## A15 · Las pruebas de raster pasaban por orden de ejecucion

**Severidad:** baja · **Estado:** ✅ cerrada

Tras arreglar A11, las pruebas nuevas de `raster_h3` pasaban en la suite
completa y fallaban sueltas: para cuando les llegaba el turno, otro modulo ya
habia llamado a `ensure_bundled_proj()`. Verde por orden de ejecucion, que es
peor que rojo — desaparece en cuanto alguien corre una prueba sola o pytest
reordena.

La llamada vive ahora en `tests/conftest.py`, antes de que ningun modulo de
prueba importe rasterio.

---

# Segunda tanda: que el sistema sirva a LATAM de verdad

Los hallazgos de arriba salieron de leer el codigo. Los de aqui salieron de
**correrlo sobre la region entera**: diecisiete backtests historicos en doce
paises, del catalogo real de USGS. Ninguno se habria encontrado sin esos datos.

## A16 · Chile no habria tenido reporte nunca

**Severidad:** critica · **Estado:** ✅ cerrada

`countries_for_point` devuelve los paises cuya **caja envolvente** contiene el
epicentro, ordenados por area, y `impact.yml` se quedaba con el primero que
tuviera Release publicado.

El area es un mal criterio y el caso que lo rompe no es raro: **la caja de Chile
mide 1.719 grados cuadrados porque llega a Rapa Nui**, y la de Argentina 671.
Medido sobre el epicentro real del M6,7 de Coquimbo (2019), los candidatos salen
`[ARG, CHL, BRA]`. El workflow habria bajado el activo argentino, el join no
habria encontrado una sola celda y el evento se habria quedado sin reporte.
Cada vez, para uno de los paises mas sismicos de la region.

Lo mas incomodo del hallazgo: **el diseno correcto estaba escrito desde el
principio y en dos sitios**. Las docstrings de `countries_for_point` y de
`paises-candidatos` dicen que el llamador «prueba en ese orden y el join contra
las celdas H3 desempata de verdad». El workflow no lo hacia. Es el mismo patron
de A5 y A7 —lo escrito y lo conectado— pero en el peor sitio posible.

Cerrado con un codigo de salida propio (`3`, "este activo no es de este sismo")
que el workflow distingue de un fallo real, y un bucle que prueba los candidatos
hasta que uno alcanza celdas. El backtest de Coquimbo, ya publicado, da 467.130
personas en MMI≥7.

## A17 · Casi la mitad de los sismos reales no llegan a MMI≥7

**Severidad:** alta · **Estado:** ✅ cerrada

El producto entero —el titular del visor, el ranking municipal, la tabla del
markdown, el circulo del epicentro, el hilo— daba por supuesto que MMI≥7 es *la*
banda. Sobre los primeros dieciocho reportes del catalogo LATAM, **ocho no
alcanzan MMI≥7 sobre poblacion**. El 44 %.

No son casos raros: son los sismos profundos y los de mar adentro, que en esta
region son la mitad del catalogo. Para ellos el sistema publicaba:

* una cifra grande que decia **0 personas**,
* una tabla de "municipios mas expuestos" ordenada por una columna de ceros —o
  sea, en orden alfabetico—,
* y quince ceros bajo un rotulo que prometia cifras.

**Tehuantepec 2017 se publicaba asi.** Un M8,2 con 98 muertos, cuyo maximo sobre
poblacion mexicana es MMI 6,5 segun el ShakeMap que el propio USGS prefiere,
salia como "0 personas en MMI≥7" con una tabla alfabetica debajo. Un cero es
cierto y se lee como que el sistema fallo, o como que el sismo no fue nada.

Cerrado con `Totales.banda_titular`: la banda mas alta que alcanzo poblacion.
Con ella se titula, se ordena y se rotula. Cuando el evento llega a MMI≥7 —el
caso normal— no cambia absolutamente nada.

## A18 · El producto nombraba sus sismos en ingles

**Severidad:** media-alta · **Estado:** ✅ cerrada

USGS publica el lugar en ingles —`20 km W of Catia La Mar, Venezuela`— y esa
cadena viajaba tal cual al titulo del reporte, al hilo para redes, al mapa
estatico y al visor. RF-06 pide "reporte en espanol neutro con toponimos
oficiales del pais": la segunda mitad se cumplia, la primera no.

Se notaba poco porque el unico reporte publicado era el del Choco, cuyo lugar
venia de una fixture escrita a mano en espanol. En cuanto entraron diecisiete
eventos reales, el tablero quedo en ingles.

`traducir_lugar` traduce el andamiaje —`W of` → `al O de`, `Mexico` → `México`—
y **nunca el toponimo**: `Catia La Mar` es un nombre propio, y traducirlo
produciria lugares que no existen en ningun mapa oficial. Ante una forma que no
reconoce devuelve el original: un lugar en ingles se lee raro, uno mal traducido
lleva a otro sitio.

## A19 · La tabla municipal rotulaba todo como DIVIPOLA

**Severidad:** media · **Estado:** ✅ cerrada

La columna de codigos del reporte decia "DIVIPOLA", que es el codigo municipal
**de Colombia**. En el reporte de Tehuantepec rotulaba `MX20043` como DIVIPOLA.

Es la marca de agua de un sistema que se construyo con un pais y se declaro
regional. Ahora se rotula por lo que es —un codigo de municipio— y el pais lo
pone el manifest.

## A20 · El visor no decia que el sistema es regional

**Severidad:** media-alta · **Estado:** ✅ cerrada

El tablero listaba eventos y nada mas. Con tres reportes de dos paises eso se
lee como una demo, y lo que hay detras no lo es: **dieciocho paises con su
activo construido, medido contra la cifra oficial de su instituto o de la ONU, y
publicado — 430,9 millones de personas ya en la malla hexagonal, calculadas
antes de que ocurra nada**.

Ese hecho responde la pregunta que se hace quien llega —*¿esto sirve para mi
pais?*— y no aparecia en ninguna pantalla. La respuesta que daba el tablero,
por omision, era que no.

`site/cobertura.json` sale de los manifests y no de un listado aparte, para que
**no pueda prometer mas paises de los que el sistema construyo**: lo que delata
a un pais construido es su `medido_ghs_pop`, que solo escribe un build de
verdad. Brasil aparece marcado como pendiente en vez de esconderse.

## A21 · Que un pais no tenga reporte no significa lo mismo en todos

**Severidad:** media · **Estado:** ✅ cerrada

Al buscar historicos para los seis paises que no tenian ninguno, la respuesta
resulto ser distinta en cada caso — y el tablero los mostraba igual, como un
hueco.

**Paraguay y Uruguay no han tenido un solo sismo M≥5,5 desde el ano 2000.**
Ninguno. Su activo esta construido, medido y esperando. Para un sistema cuyo
proposito es estar listo por adelantado, eso no es una carencia: es exactamente
el estado que se persigue, y presentarlo como un vacio lo cuenta al reves.

**Brasil no puede tener reporte, y no es por el activo.** Sus doce sismos
M≥5,5 desde 2000 estan todos entre 534 y 603 km de profundidad, en Acre, y
**USGS no publica contornos MMI para ninguno**. Un sistema que calcula sobre
`cont_mmi` no tiene nada que calcular ahi. Construir su activo sigue teniendo
sentido —un sismo somero raro en la costa cambiaria eso en un dia— pero
conviene decir por que su casilla de reportes esta vacia.

**Argentina y Republica Dominicana si tenian eventos**, y no aparecian porque
el primer lote se busco con umbral M6,3 —el sistema dispara a M5,5— y porque
las cajas envolventes de Argentina y Bolivia se llenan de sismos chilenos, que
tapaban a los suyos al ordenar por relevancia. Ya tienen reporte: Pocito 2021
(M6,4, San Juan) y Bani 2012 (M5,5).

**Bolivia resulto ser el caso de Brasil.** Sus veintidos sismos M≥5,5 desde
2000 estan entre 359 y 596 km, y el unico con contornos publicados no produjo
una sola celda por encima de MMI 5. No es un hueco de cobertura: es que a esa
profundidad no hay intensidad de superficie que medir.

**Y el descarte por pais se estreno en real.** De los tres eventos dominicanos
probados, dos —ambos frente a Punta Cana, a 77 y 102 km mar adentro— salieron
con codigo 3: el activo dominicano no los alcanza. Con el comportamiento
anterior habrian publicado un reporte de ceros.

La nota de la seccion de cobertura del visor ahora distingue los tres estados:
construido con reportes, construido y en silencio, y sin construir.

---

## A10 · Clean Code aplicado al repositorio

**Estado:** ✅ cerrada

La auditoria incorporo una revision contra los principios de *Clean Code*
(Robert C. Martin) y su lectura moderna en Python. Lo adoptado, con lo que
significa **aqui**, esta en [`CLEAN_CODE.md`](CLEAN_CODE.md).

La regla que mas trabajo dio no es de estilo: **«always find root cause»**.
Cinco de los nueve hallazgos son la misma causa raiz —una funcion escrita y no
conectada— apareciendo en cinco sitios distintos. Arreglarlos uno a uno sin
nombrar el patron habria dejado el sexto para la proxima auditoria. Por eso A5
y A7 cierran con **pruebas que vigilan el patron**, no solo con los arreglos.
