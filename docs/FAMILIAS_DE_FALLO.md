# Ocho formas de romper este sistema sin que nada se ponga rojo

Escrito el 27-ago-2026, tras tres días de auditoría y unos cuarenta fallos
encontrados. La octava se anadio el 31-ago, y se anadio mal: se encontró
validando producción en vez de antes del PR, que es justo lo que este documento
existe para evitar. `AUDITORIA.md` los lista uno a uno; esto los agrupa por **causa**,
que es lo que sirve para reconocer el siguiente antes de que muerda.

El hilo común: **casi ninguno falla ruidosamente.** Producen resultados
plausibles, corridas en verde y cifras creibles. Por eso hay que buscarlos.

---

## 1 · Escrito no es conectado

Una función existe, tiene pruebas verdes, y **nadie la llama** — o la llama pero
su resultado no le llega a nadie.

| Caso | Como se veia |
|---|---|
| El latido de `/status` no se commiteaba | 20+ corridas verdes, `"latidos": []` |
| Latencia calculada y no publicada | la página decía "sin datos" |
| Asserts de §6.4 sin correr en P2 | reportes publicados sin validar |
| Contornos de ShakeMap bajados y tirados | el mapa sin área de afectación |
| Epicentros del visor nunca dibujados | mapa base y ni una estrella |
| **El visor 17 h congelado** | los dos workflows en verde |
| `focos_en` sin llamador | 27-ago, cazado por el guardia |

**Por que pasa.** Las pruebas comprueban que la pieza *funciona*, no que este
*enchufada*. El fallo vive en el hueco entre dos cosas que por separado están
bien, y no hay hueco que se pueda probar por dentro.

**Que lo detecta.** `test_funciones_conectadas.py` recorre el grafo de llamadas
y exige que toda función pública tenga llamador en producción, o una
justificación escrita. Ha cazado tres cambios mios esta semana.

---

## 2 · El guardia confunde la prosa con el código

Una prueba busca una cadena y la encuentra en el comentario que la explica.

| Buscaba | La encontró en |
|---|---|
| `src.read(1)` | el docstring que explicaba el arreglo |
| `gh workflow run site.yml` | el cuerpo de un issue |
| `WHERE` | un comentario de SQL |
| `bottom: 58px` | el comentario que decía por que ya no esta |

**Cuatro veces en dos días.** No es mala suerte: es una trampa que este
repositorio se pone a si mismo por escribir buenos comentarios. **Cuanto mejor
se documenta un arreglo, más probable es que su propia prueba lo de por roto.**

**La regla.** Un guardia de texto quita los comentarios del medio que inspecciona
**antes** de buscar. Y donde se puede, no empareja texto: recorre el AST
(`test_disco_del_build`), parsea el YAML (`test_el_visor_se_republica`) o exige
la línea entera (`republica()`).

---

## 3 · Un tercero cambia el dato y un país desaparece

| Caso | Que cambio |
|---|---|
| ARG, COD-AB republicado | apareció coordenada Z; tipo WKB 3 → 1003 |
| ARG, mismo fichero | Itati englobando a San Luis del Palmar al 100 % |
| WorldCover | teselas que no existen (solo mar) → 404 |
| Overture | el `vintage` fijado caduca en octubre |
| **PER, JRC caído** | **el origen no responde y el país sale "todo océano"** |

**El caso peruano, del 27-ago-2026, es el más instructivo porque el tercero no
cambio nada: se cayó.** `HttpFetcher.download_to` lanza el mismo `RuntimeError`
genérico para cualquier causa —404, timeout, 500, conexión cortada— y
`download_ghsl` lo captura para tratar un caso legítimo: las teselas que solo
cubren océano no existen en el servidor, y ahí un 404 **es** la respuesta
correcta. Con el JRC caído tres horas, las nueve teselas de Perú agotaron sus
reintentos, se contaron una a una como «tesela ausente, probablemente solo
océano», y el país se ensamblo con población 0 y superficie construida 0.

Lo detuvo el assert de §6.4 —`Total nacional 0 se desvia -100.00%`— pero al
final de la cadena, tres horas y 24 millones de edificaciones después. Desde el
27-ago-2026 lo detiene antes `_verificar_insumos`: una fuente que **si** descarga
y vuelve con cero ficheros levanta `InsumoAusenteError` al terminar esa descarga.
Vacío no es lo mismo que remoto, y suponerlo era el agujero.

**Cerrado del todo el 28-ago-2026, en tres piezas.** La caída *parcial* seguía
abierta —si de nueve teselas responden cinco no hay cero que detectar, y el país
sale con una fracción de su población: una cifra plausible, del orden correcto y
equivocada—. Lo que faltaba era que el fetcher distinguiera «404, esta tesela no
existe» de «no pude descargarla», que eran la misma excepción.

| | Antes | Ahora |
|---|---|---|
| Tesela oceanica (404) | 3 intentos, 14 s de espera | `RecursoAusenteError`, sin reintento |
| Origen caído | 3 intentos, ~6,7 min, y «océano» | sube el fallo con su nombre |
| Origen caído, el país entero | se descubre a las 4 h | `comprobar_origenes`, ~10 s |
| Reintento | por fichero, 14 s | por país, 10 y 30 min, solo si el código es 4 |

`RecursoAusenteError` es la única excepción que `download_ghsl` acepta como
«solo océano»; cualquier otra sube. `comprobar_origenes` pregunta por HEAD a
cada host distinto del manifest antes de la primera descarga, y **cualquier
código de estado cuenta como vivo** —404, 403, 405 incluidos—: la pregunta es si
el servidor esta en pie, no si el recurso existe, y un chequeo que confundiera
las dos cosas sería un generador de falsos positivos desactivado en una semana.

Y `centinela country` sale con **código 4** cuando el origen no estaba, para que
el workflow reintente solo eso: un activo que no pasa los asserts de calidad
falla igual las tres veces, y repetirlo solo retrasaria el diagnóstico media
hora.

**Por que pasa.** Dependemos de HDX, USGS, JRC, ESA, Overture. Ninguno avisa. Y
lo más fino del caso argentino: el filtro `ST_GeometryType(...) = 'POLYGON'`
**parecia cubrirlo y no podía**, porque devuelve `POLYGON` tanto para el tipo 3
como para el 1003 — borra la dimensión al contestar.

**La puerta, puesta el 27-ago-2026.** Cada fuente se compara contra su
`insumos_sha256` en cuanto sus ficheros están en disco, y un insumo republicado
detiene el build ahí —a los minutos, nombrando la fuente y el fichero— en vez de
salir a las dos horas disfrazado de error de geometría.

**Por que llevaba vacío desde el primer día, que no era disciplina.** El campo se
llamaba `sha256` y era escalar, y **una fuente del manifest no es un fichero**:
GHS-POP son nueve u once teselas, el desglose etario de WorldPop veinte rasters,
un COD-AB el shapefile con su `.dbf` y su `.prj`, y Overture no baja ninguno. No
había un fichero al que pertenecer, así que las 194 fuentes de los diecinueve
manifiestos no podían llenarse. El campo es ahora `insumos_sha256` y hashea la
lista canónica `(nombre, sha256)` del conjunto, que si existe para los tres
casos.

El segundo motivo era más simple: `_registrar` **ya calculaba** un sha256 real de
cada fichero en cada corrida desde siempre, y del inventario solo llegaba al log
un conteo de ficheros y un total de bytes. Los hashes se computaban y se tiraban,
build tras build. Ahora sobreviven en el bloque `insumos` de `medicion.json`, que
ya viaja en el Release al lado del parquet.

**Lo que falta.** Los 194 digests siguen vacios: solo se pueden medir
construyendo, y los diecinueve activos publicados se construyeron antes de que
esto existiera. Se llenan país a país con `centinela fijar-insumos <ISO3>` sobre
la medición de la proxima reconstrucción —la misma que ya alinea la versión del
activo—, y hasta entonces el lint lo reporta como aviso y el build lo registra
sin detenerse.

---

## 4 · El recurso escala con el tamaño del país

Brasil, tres diagnosticos: tiempo, disco, y por fin **memoria** — `src.read(1)`
traía 12,8 GB sobre un runner de 16.

| País | Píxeles | En RAM | ¿Cabe? |
|---|---|---|---|
| Colombia | 0,39 G | 1,9 GB | si |
| México | 0,86 G | 4,3 GB | si |
| Brasil | 2,57 G | 12,8 GB | no |

**Por que pasa.** Funciona en Colombia y en México, así que parece correcto.
Brasil es seis veces Colombia y solo entonces revienta. Y el mensaje con que
GitHub mata un runner sin recursos no distingue disco de memoria, lo que costo
dos diagnosticos equivocados.

**La regla.** *El pico no puede depender del tamaño del país.* Aplicada desde el
principio en WorldCover: 20 MB por tesela, igual para Colombia que para Brasil.

---

## 5 · El guardia se convierte en el fallo

`download_to` validaba el tamaño final contra `Content-Length`, que cuenta bytes
**en la red**. Con `Content-Encoding: gzip`, lo que llega a disco es mayor sin
que nada haya ido mal.

    airports.csv llegó incompleto: 12707477 bytes de 3882778

**Tumbo diez de diecinueve builds.** Y es peor que no tener guardia: el mensaje
"llegó incompleto" manda a investigar la red cuando el problema es el guardia.

**La regla.** Un guardia que puede fallar sobre datos correctos necesita su
propia prueba del caso bueno — no solo del malo.

---

## 6 · Se publica una cifra que no es una medición

| Caso | Lo que decía |
|---|---|
| `us7000abcd` | sismo inexistente, en vivo, latencia de 20,0 min |
| `pop = 0` sin activo cargado | se lee como "no hay nadie" |
| `lulc_*` a cero en activos viejos | se lee como "no hay bosque" |
| `manifest_id` sin subir | dos activos distintos, mismo identificador |

**Por que pasa.** Cero es un número perfectamente creíble, y un identificador
repetido no chirria.

**La regla, y sostiene media arquitectura del proyecto:** *ausencia de medición
no es medición de cero.* De ahí que `observados.json` tenga esquema propio sin
un solo campo de impacto, que el popup de incendios omita la población cuando es
cero, que `event_latencies` exija que exista el reporte, y que
`COLUMNAS_OPCIONALES` deje aviso de que sustituyo.

---

## 7 · Correcto y físicamente invisible

Los hexágonos H3 r8 a **0,05 píxeles** en la vista continental. La rampa de
fuego con seis colores y ninguna leyenda.

**Por que pasa.** Las pruebas comprueban que la capa se *declara*, y estaba
perfectamente declarada. La única forma de verlo es mirar.

**La regla.** Una capa nueva se abre en un navegador antes de darla por hecha, y
se comprueba en el zoom en el que la gente la va a mirar — no en el que la
escribiste.

---

## 8 · La fuente entera se cayó y la corrida salió en verde

P5 lee seis ficheros de FIRMS. Un fichero caído no puede tumbar los otros cinco
—perder una región entera es peor que publicar con cinco sextos del dato— así
que el fallo se anota en el log y se sigue. Correcto.

El 30-ago-2026 fallaron **los seis**:

    {"detecciones": 0, "utiles": 0, "ficheros_fallidos": [los seis]}

Cero detecciones, cero celdas, y el workflow **verde**. La capa publicada se
salvo porque el pipeline ya se niega a publicar ceros —la familia 6 hizo su
trabajo— pero nadie se entero de que ese día no se miro. Si FIRMS se cayera una
semana, el visor serviria fuego de hace siete días con el sello «revisado hace 5
min» que este mismo repositorio añade para que eso no pase.

**Y estaba en tres sitios.** La auditoría posterior lo encontró también en
`frescura` —el vigilante que existe porque el visor estuvo diecisiete horas
congelado en verde, apuntandose un verde cuando no podía leer la página— y en el
repaso de versiones, escrito ese mismo día para arreglar otro fallo de esta
misma familia.

**La regla.** Tolerar fallos parciales exige contar el denominador. Dos fallidos
de seis es un roce; dos de dos es no haber mirado, y eso no es «sin cambios».
Todo bucle que lee N fuentes y tolera que alguna falle necesita responder
**¿fallaron todas?** — y si la respuesta es si, salir en rojo.

**El corolario, que es el que costo.** Los tres sitios tenían su fallo parcial
bien pensado y documentado. La ceguera total no apareció en ninguna revisión
porque **nadie escribe la prueba del caso que cree imposible**. Si un bucle
tolera fallos, la prueba de «fallan todos» va con la de «falla uno».

---

## Lo que estas ocho comparten

Ninguna se detecta leyendo el código de la pieza. Todas se detectan preguntando
una de estas cuatro cosas:

1. **¿Quien llama a esto?** (familia 1)
2. **¿Que pasa si el dato de fuera cambia de forma?** (familias 3 y 5)
3. **¿Que pasa cuando el país es seis veces más grande?** (familia 4)
4. **¿Esto se puede leer como algo que no es?** (familias 2, 6 y 7)
5. **¿Y si falla todo a la vez, no solo una parte?** (familia 8)

Y la regla que las cubre todas, que es del dueño del proyecto: **el sistema tiene
que demostrar que funciona por si mismo, no porque alguien lo note y pregunte.**
Ante cualquier arreglo, la pregunta es *¿que lo vigila cuando nadie mira?* — una
prueba que falle en CI, un workflow programado que abra issue, o un dato
publicado que delate el problema. Un comentario no cuenta.
