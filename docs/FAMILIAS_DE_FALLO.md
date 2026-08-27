# Siete formas de romper este sistema sin que nada se ponga rojo

Escrito el 27-ago-2026, tras tres dias de auditoria y unos cuarenta fallos
encontrados. `AUDITORIA.md` los lista uno a uno; esto los agrupa por **causa**,
que es lo que sirve para reconocer el siguiente antes de que muerda.

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

**Por que pasa.** Dependemos de HDX, USGS, JRC, ESA, Overture. Ninguno avisa. Y
lo mas fino del caso argentino: el filtro `ST_GeometryType(...) = 'POLYGON'`
**parecia cubrirlo y no podia**, porque devuelve `POLYGON` tanto para el tipo 3
como para el 1003 — borra la dimension al contestar.

**Lo que falta.** Los `sha256` vacios de los manifiestos. Son exactamente lo que
convertiria esto en un aviso —"este fichero cambio"— en vez de en un fallo a las
dos horas de build.

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

## Lo que estas siete comparten

Ninguna se detecta leyendo el codigo de la pieza. Todas se detectan preguntando
una de estas cuatro cosas:

1. **¿Quien llama a esto?** (familia 1)
2. **¿Que pasa si el dato de fuera cambia de forma?** (familias 3 y 5)
3. **¿Que pasa cuando el pais es seis veces mas grande?** (familia 4)
4. **¿Esto se puede leer como algo que no es?** (familias 2, 6 y 7)

Y la regla que las cubre todas, que es del dueno del proyecto: **el sistema tiene
que demostrar que funciona por si mismo, no porque alguien lo note y pregunte.**
Ante cualquier arreglo, la pregunta es *¿que lo vigila cuando nadie mira?* — una
prueba que falle en CI, un workflow programado que abra issue, o un dato
publicado que delate el problema. Un comentario no cuenta.
