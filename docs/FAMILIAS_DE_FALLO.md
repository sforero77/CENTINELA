# Once formas de romper este sistema sin que nada se ponga rojo

Escrito el 27-ago-2026, tras tres dias de auditoria y unos cuarenta fallos
encontrados. La octava se anadio el 31-ago, y se anadio mal: se encontro
validando produccion en vez de antes del PR, que es justo lo que este documento
existe para evitar. Las tres ultimas salieron el 1-sep de una revision del visor
como usuario final, y **las tres estaban publicadas**: una frase que negaba sus
propias cifras, un dibujo que corria dos veces y una prueba que no vigilaba nada.
`AUDITORIA.md` los lista uno a uno; esto los agrupa por **causa**, que es lo que
sirve para reconocer el siguiente antes de que muerda.

El hilo comun: **casi ninguno falla ruidosamente.** Producen resultados
plausibles, corridas en verde y cifras creibles. Por eso hay que buscarlos.

---

## 1 · Escrito no es conectado

Una funcion existe, tiene pruebas verdes, y **nadie la llama** — o la llama pero
su resultado no le llega a nadie.

| Caso | Como se veia |
|---|---|
| El latido de `/status` no se commiteaba | 20+ corridas verdes, `"latidos": []` |
| Latencia calculada y no publicada | la pagina decia "sin datos" |
| Asserts de §6.4 sin correr en P2 | reportes publicados sin validar |
| Contornos de ShakeMap bajados y tirados | el mapa sin area de afectacion |
| Epicentros del visor nunca dibujados | mapa base y ni una estrella |
| **El visor 17 h congelado** | los dos workflows en verde |
| `focos_en` sin llamador | 27-ago, cazado por el guardia |

**Por que pasa.** Las pruebas comprueban que la pieza *funciona*, no que este
*enchufada*. El fallo vive en el hueco entre dos cosas que por separado estan
bien, y no hay hueco que se pueda probar por dentro.

**Que lo detecta.** `test_funciones_conectadas.py` recorre el grafo de llamadas
y exige que toda funcion publica tenga llamador en produccion, o una
justificacion escrita. Ha cazado tres cambios mios esta semana.

---

## 2 · El guardia confunde la prosa con el codigo

Una prueba busca una cadena y la encuentra en el comentario que la explica.

| Buscaba | La encontro en |
|---|---|
| `src.read(1)` | el docstring que explicaba el arreglo |
| `gh workflow run site.yml` | el cuerpo de un issue |
| `WHERE` | un comentario de SQL |
| `bottom: 58px` | el comentario que decia por que ya no esta |

**Cuatro veces en dos dias.** No es mala suerte: es una trampa que este
repositorio se pone a si mismo por escribir buenos comentarios. **Cuanto mejor
se documenta un arreglo, mas probable es que su propia prueba lo de por roto.**

**La regla.** Un guardia de texto quita los comentarios del medio que inspecciona
**antes** de buscar. Y donde se puede, no empareja texto: recorre el AST
(`test_disco_del_build`), parsea el YAML (`test_el_visor_se_republica`) o exige
la linea entera (`republica()`).

---

## 3 · Un tercero cambia el dato y un pais desaparece

| Caso | Que cambio |
|---|---|
| ARG, COD-AB republicado | aparecio coordenada Z; tipo WKB 3 → 1003 |
| ARG, mismo fichero | Itati englobando a San Luis del Palmar al 100 % |
| WorldCover | teselas que no existen (solo mar) → 404 |
| Overture | el `vintage` fijado caduca en octubre |
| **PER, JRC caido** | **el origen no responde y el pais sale "todo oceano"** |

**El caso peruano, del 27-ago-2026, es el mas instructivo porque el tercero no
cambio nada: se cayo.** `HttpFetcher.download_to` lanza el mismo `RuntimeError`
generico para cualquier causa —404, timeout, 500, conexion cortada— y
`download_ghsl` lo captura para tratar un caso legitimo: las teselas que solo
cubren oceano no existen en el servidor, y ahi un 404 **es** la respuesta
correcta. Con el JRC caido tres horas, las nueve teselas de Peru agotaron sus
reintentos, se contaron una a una como «tesela ausente, probablemente solo
oceano», y el pais se ensamblo con poblacion 0 y superficie construida 0.

Lo detuvo el assert de §6.4 —`Total nacional 0 se desvia -100.00%`— pero al
final de la cadena, tres horas y 24 millones de edificaciones despues. Desde el
27-ago-2026 lo detiene antes `_verificar_insumos`: una fuente que **si** descarga
y vuelve con cero ficheros levanta `InsumoAusenteError` al terminar esa descarga.
Vacio no es lo mismo que remoto, y suponerlo era el agujero.

**Cerrado del todo el 28-ago-2026, en tres piezas.** La caida *parcial* seguia
abierta —si de nueve teselas responden cinco no hay cero que detectar, y el pais
sale con una fraccion de su poblacion: una cifra plausible, del orden correcto y
equivocada—. Lo que faltaba era que el fetcher distinguiera «404, esta tesela no
existe» de «no pude descargarla», que eran la misma excepcion.

| | Antes | Ahora |
|---|---|---|
| Tesela oceanica (404) | 3 intentos, 14 s de espera | `RecursoAusenteError`, sin reintento |
| Origen caido | 3 intentos, ~6,7 min, y «oceano» | sube el fallo con su nombre |
| Origen caido, el pais entero | se descubre a las 4 h | `comprobar_origenes`, ~10 s |
| Reintento | por fichero, 14 s | por pais, 10 y 30 min, solo si el codigo es 4 |

`RecursoAusenteError` es la unica excepcion que `download_ghsl` acepta como
«solo oceano»; cualquier otra sube. `comprobar_origenes` pregunta por HEAD a
cada host distinto del manifest antes de la primera descarga, y **cualquier
codigo de estado cuenta como vivo** —404, 403, 405 incluidos—: la pregunta es si
el servidor esta en pie, no si el recurso existe, y un chequeo que confundiera
las dos cosas seria un generador de falsos positivos desactivado en una semana.

Y `centinela country` sale con **codigo 4** cuando el origen no estaba, para que
el workflow reintente solo eso: un activo que no pasa los asserts de calidad
falla igual las tres veces, y repetirlo solo retrasaria el diagnostico media
hora.

**Por que pasa.** Dependemos de HDX, USGS, JRC, ESA, Overture. Ninguno avisa. Y
lo mas fino del caso argentino: el filtro `ST_GeometryType(...) = 'POLYGON'`
**parecia cubrirlo y no podia**, porque devuelve `POLYGON` tanto para el tipo 3
como para el 1003 — borra la dimension al contestar.

**La puerta, puesta el 27-ago-2026.** Cada fuente se compara contra su
`insumos_sha256` en cuanto sus ficheros estan en disco, y un insumo republicado
detiene el build ahi —a los minutos, nombrando la fuente y el fichero— en vez de
salir a las dos horas disfrazado de error de geometria.

**Por que llevaba vacio desde el primer dia, que no era disciplina.** El campo se
llamaba `sha256` y era escalar, y **una fuente del manifest no es un fichero**:
GHS-POP son nueve u once teselas, el desglose etario de WorldPop veinte rasters,
un COD-AB el shapefile con su `.dbf` y su `.prj`, y Overture no baja ninguno. No
habia un fichero al que pertenecer, asi que las 194 fuentes de los diecinueve
manifiestos no podian llenarse. El campo es ahora `insumos_sha256` y hashea la
lista canonica `(nombre, sha256)` del conjunto, que si existe para los tres
casos.

El segundo motivo era mas simple: `_registrar` **ya calculaba** un sha256 real de
cada fichero en cada corrida desde siempre, y del inventario solo llegaba al log
un conteo de ficheros y un total de bytes. Los hashes se computaban y se tiraban,
build tras build. Ahora sobreviven en el bloque `insumos` de `medicion.json`, que
ya viaja en el Release al lado del parquet.

**Lo que falta.** Los 194 digests siguen vacios: solo se pueden medir
construyendo, y los diecinueve activos publicados se construyeron antes de que
esto existiera. Se llenan pais a pais con `centinela fijar-insumos <ISO3>` sobre
la medicion de la proxima reconstruccion —la misma que ya alinea la version del
activo—, y hasta entonces el lint lo reporta como aviso y el build lo registra
sin detenerse.

---

## 4 · El recurso escala con el tamano del pais

Brasil, tres diagnosticos: tiempo, disco, y por fin **memoria** — `src.read(1)`
traia 12,8 GB sobre un runner de 16.

| Pais | Pixeles | En RAM | ¿Cabe? |
|---|---|---|---|
| Colombia | 0,39 G | 1,9 GB | si |
| Mexico | 0,86 G | 4,3 GB | si |
| Brasil | 2,57 G | 12,8 GB | no |

**Por que pasa.** Funciona en Colombia y en Mexico, asi que parece correcto.
Brasil es seis veces Colombia y solo entonces revienta. Y el mensaje con que
GitHub mata un runner sin recursos no distingue disco de memoria, lo que costo
dos diagnosticos equivocados.

**La regla.** *El pico no puede depender del tamano del pais.* Aplicada desde el
principio en WorldCover: 20 MB por tesela, igual para Colombia que para Brasil.

---

## 5 · El guardia se convierte en el fallo

`download_to` validaba el tamano final contra `Content-Length`, que cuenta bytes
**en la red**. Con `Content-Encoding: gzip`, lo que llega a disco es mayor sin
que nada haya ido mal.

    airports.csv llego incompleto: 12707477 bytes de 3882778

**Tumbo diez de diecinueve builds.** Y es peor que no tener guardia: el mensaje
"llego incompleto" manda a investigar la red cuando el problema es el guardia.

**La regla.** Un guardia que puede fallar sobre datos correctos necesita su
propia prueba del caso bueno — no solo del malo.

---

## 6 · Se publica una cifra que no es una medicion

| Caso | Lo que decia |
|---|---|
| `us7000abcd` | sismo inexistente, en vivo, latencia de 20,0 min |
| `pop = 0` sin activo cargado | se lee como "no hay nadie" |
| `lulc_*` a cero en activos viejos | se lee como "no hay bosque" |
| `manifest_id` sin subir | dos activos distintos, mismo identificador |

**Por que pasa.** Cero es un numero perfectamente creible, y un identificador
repetido no chirria.

**La regla, y sostiene media arquitectura del proyecto:** *ausencia de medicion
no es medicion de cero.* De ahi que `observados.json` tenga esquema propio sin
un solo campo de impacto, que el popup de incendios omita la poblacion cuando es
cero, que `event_latencies` exija que exista el reporte, y que
`COLUMNAS_OPCIONALES` deje aviso de que sustituyo.

---

## 7 · Correcto y fisicamente invisible

Los hexagonos H3 r8 a **0,05 pixeles** en la vista continental. La rampa de
fuego con seis colores y ninguna leyenda.

**Por que pasa.** Las pruebas comprueban que la capa se *declara*, y estaba
perfectamente declarada. La unica forma de verlo es mirar.

**La regla.** Una capa nueva se abre en un navegador antes de darla por hecha, y
se comprueba en el zoom en el que la gente la va a mirar — no en el que la
escribiste.

---

## 8 · La fuente entera se cayo y la corrida salio en verde

P5 lee seis ficheros de FIRMS. Un fichero caido no puede tumbar los otros cinco
—perder una region entera es peor que publicar con cinco sextos del dato— asi
que el fallo se anota en el log y se sigue. Correcto.

El 30-ago-2026 fallaron **los seis**:

    {"detecciones": 0, "utiles": 0, "ficheros_fallidos": [los seis]}

Cero detecciones, cero celdas, y el workflow **verde**. La capa publicada se
salvo porque el pipeline ya se niega a publicar ceros —la familia 6 hizo su
trabajo— pero nadie se entero de que ese dia no se miro. Si FIRMS se cayera una
semana, el visor serviria fuego de hace siete dias con el sello «revisado hace 5
min» que este mismo repositorio anade para que eso no pase.

**Y estaba en tres sitios.** La auditoria posterior lo encontro tambien en
`frescura` —el vigilante que existe porque el visor estuvo diecisiete horas
congelado en verde, apuntandose un verde cuando no podia leer la pagina— y en el
repaso de versiones, escrito ese mismo dia para arreglar otro fallo de esta
misma familia.

**La regla.** Tolerar fallos parciales exige contar el denominador. Dos fallidos
de seis es un roce; dos de dos es no haber mirado, y eso no es «sin cambios».
Todo bucle que lee N fuentes y tolera que alguna falle necesita responder
**¿fallaron todas?** — y si la respuesta es si, salir en rojo.

**El corolario, que es el que costo.** Los tres sitios tenian su fallo parcial
bien pensado y documentado. La ceguera total no aparecio en ninguna revision
porque **nadie escribe la prueba del caso que cree imposible**. Si un bucle
tolera fallos, la prueba de «fallan todos» va con la de «falla uno».

---

## 9 · La nota escrita para un caso se imprime en el contrario

`bandaDeTotales` devuelve 8 cuando hay poblacion en MMI≥8 y 6 cuando la sacudida
no llego a 7. Una sola rama cubria los dos y ponia la misma nota:

    La sacudida no alcanzo MMI 7 sobre poblacion: ninguna de las cifras de
    abajo, que se cuentan en MMI≥7, aplica a este evento.

En banda 6 es cierta. **En banda 8 dice lo contrario de lo que el propio panel
ensena dos bloques mas arriba**: Muisne tiene 2.283.454 personas en MMI≥7. Los
tres eventos mas fuertes del catalogo eran los que llevaban la frase que niega
sus propias cifras.

**La regla.** Una condicion escrita como "el caso raro" (`banda !== 7`) agrupa
dos casos opuestos en cuanto aparece el tercero. Se enumeran, no se niegan.

---

## 10 · La red de seguridad no se cancela

`cuandoElEstiloEsteListo` esperaba a que MapLibre terminara y ademas armaba un
`setTimeout` de cuatro segundos por si ese momento no llegaba nunca. El camino
normal quitaba los escuchadores **y dejaba el temporizador en pie**, asi que
todo dibujo diferido corria dos veces.

    fallo al dibujar sobre el mapa: Error: Source "celdas" already exists.

No se veia al arrancar, porque ahi el estilo suele estar listo y se toma el
atajo. Se veia con `?evento=` sobre estilo frio — el enlace profundo, que es
como llega quien recibe un reporte compartido.

**La regla.** Una red de seguridad tiene que apagarse cuando el camino bueno
funciona. Si no, no es una red: es una segunda ejecucion.

---

## 11 · La prueba pasa porque el escenario no ocurre

El bloque «Ambiente» del panel de fuego se quedaba con su titulo y su parrafo
cuando GFS no cubria el foco. Se arreglo, se escribio una prueba que recorria
doce focos buscando el caso… y pasaba siempre. Medido despues: **los 3.337
puntos de la rejilla de viento cubren los 6.239 focos, ninguno a mas de medio
grado**. El caso no se da nunca.

Una prueba asi da verde el dia que el arreglo se rompe, porque nunca lo ejecuto.
La prueba buena **provoca** el escenario: vacia la rejilla y comprueba que el
bloque desaparece.

De la misma familia, y encontrado a la vez: recortar el codigo por un numero
fijo de caracteres. Dos pruebas leian 900 caracteres desde el id de una capa; al
crecer el bloque las aserciones quedaron fuera y siguieron en verde sobre codigo
que ya no miraban.

**La regla.** Ante una prueba nueva, romper el arreglo a proposito y comprobar
que falla. Si no falla, no vigila nada.

---

## Lo que estas once comparten

Ninguna se detecta leyendo el codigo de la pieza. Todas se detectan preguntando
una de estas cosas:

1. **¿Quien llama a esto?** (familia 1)
2. **¿Que pasa si el dato de fuera cambia de forma?** (familias 3 y 5)
3. **¿Que pasa cuando el pais es seis veces mas grande?** (familia 4)
4. **¿Esto se puede leer como algo que no es?** (familias 2, 6, 7 y 9)
5. **¿Y si falla todo a la vez, no solo una parte?** (familia 8)
6. **¿Que corre dos veces, o ninguna?** (familia 10)
7. **¿Esta prueba falla si rompo el arreglo?** (familia 11)

Y la regla que las cubre todas, que es del dueno del proyecto: **el sistema tiene
que demostrar que funciona por si mismo, no porque alguien lo note y pregunte.**
Ante cualquier arreglo, la pregunta es *¿que lo vigila cuando nadie mira?* — una
prueba que falle en CI, un workflow programado que abra issue, o un dato
publicado que delate el problema. Un comentario no cuenta.
