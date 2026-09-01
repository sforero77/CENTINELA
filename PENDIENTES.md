# Pendientes y hoja de ruta

Estado al **28 de agosto de 2026**. El sistema se encendio el 24. Este
documento es el traspaso: que queda por hacer, quien puede hacerlo, y en que
orden.

Se revisa contra la realidad, no de memoria: cada cifra de aquí se volvio a
medir el 28-ago contra los Releases publicados, las corridas de Actions y la
página viva. Varias estaban desfasadas y se corrigen abajo — un documento de
traspaso que envejece en silencio es peor que no tenerlo.

Ya no hay pasos bloqueados por permisos: la puesta en marcha se completo (§1) y
**todo lo que queda es código, abordable desde un clon**. Para vigilar el
sistema ya operando, la referencia es
[`docs/OPERACION.md`](docs/OPERACION.md).

---

## 0. Donde estamos

El sistema **funciona de punta a punta y corre solo**:

```bash
centinela impact us6000tjl2   --detail-url "https://earthquake.usgs.gov/fdsnws/event/1/query?eventid=us6000tjl2&format=geojson"   --exposure data/build/exposure_h3.parquet --manifest col-v0.6
# 24,7 s -> 2.415.793 personas en MMI>=7, reporte publicado en reports/
```

| Componente | Estado |
|---|---|
| P1 trigger (feed, filtro, dedupe, estado) | ✅ operando, y publicando su latido |
| Visor y `/status` publicados | ✅ https://sforero77.github.io/CENTINELA/ |
| P0 activo de exposición (descarga → parquet) | ✅ **publicado en los 19 países** |
| P2 impacto (contornos → celdas → GF → join) | ✅ funcional, con reintento por país |
| P3 reporte (json, md, csv, hilo, 2 mapas, malla, contornos) | ✅ funcional |
| **Catálogo histórico** | ✅ **21 reportes en 15 países** — todos backtest |
| Asserts de calidad §6.4, en P0 y en P2 | ✅ funcional |
| Topónimos en español (RF-06) y changelog de deltas (RF-04) | ✅ funcional |
| Golden G1 (Chocó), G2 (Venezuela) y G3 | ✅ corren, ninguna saltada |
| Verificación de insumos (`insumos_sha256`) | ✅ mide y detiene · digests sin fijar, §2.6 |
| Cobertura que **ve la pantalla** | ✅ `tests/visor`, 7 pruebas en un navegador real |
| Coropletas r7/r6 del visor | ⏳ §2.2 |
| P4 brigada de imagen | ⏳ Fase 2, solo contrato |

**948 pruebas** sin red y sin navegador (más 8 nocturnas contra las fuentes
vivas y 7 del visor, que abren Chromium), `ruff` y `mypy --strict` limpios,
arranque verificado desde clon vacío. Medido el 28-ago-2026. Eran 431 antes de
la auditoría, 523 al empezarla y 686 el 26-ago.

**El visor ya no depende de que alguien lo mire.** `tests/visor` lo abre en un
navegador de verdad y espera a `window.CENTINELA` —el registro de lo que ha
pintado, con el recuento de rasgos de cada capa— en vez de esperar N segundos.
Corre en `visor.yml` cuando cambia `site/`, no por cron: los turnos que GitHub
concede al repositorio los necesita el vigía.

Se saltan 21, y todas por la misma razón legítima:
`test_el_visor_se_republica` esta parametrizada por workflow y omite los que no
publican nada que el visor lea. No hay ninguna saltada por estar rota.

**El cron declara `*/30` y no corre cada treinta minutos.** La cabecera de
[`trigger.yml`](.github/workflows/trigger.yml) lleva la medición buena y el
mecanismo: GitHub no concede un turno por workflow sino **unos pocos por
repositorio**, y aquí hay cinco programados compitiendo.

Medido de nuevo el 28-ago-2026 sobre las 86 corridas programadas de cuatro días:

| | |
|---|---|
| declarado | 30 min |
| mediana | 45,6 min |
| media | 57,8 min |
| **máximo** | **663 min (11,1 h)** |
| huecos > 2 h | 4 de 85 |

La cifra que este documento traía —«máximo 73,3» sobre 22 corridas— era del
24-ago y se quedó corta en un orden de magnitud. **Y no lo causan nuestros
propios builds saturando la cola:** los dos peores huecos tuvieron 2 % y 0 % de
solape con corridas de exposición. Es el planificador, y la salida es el reloj
externo — ver §2.8.

### El cero silencioso que casi se publica

`build_country` cerraba sin construir tres capas. Edificaciones y vías tenían
el selector de ficheros de Overture escrito y probado, pero **nadie lo
llamaba**; el desglose etario tampoco se descargaba, porque su url apunta a un
directorio de 62 rasters y la descarga caía en la rama "sin estrategia". Las
cifras del backtest del Chocó salieron de orquestar esas piezas a mano.

Nada fallaba. `ensure_layer_tables` crea vacía la tabla de una capa ausente, el
`LEFT JOIN` la convierte en ceros y el activo se escribe; el assert de §6.4
solo mira población, así que pasaba. La proxima corrida de
`exposure_quarterly.yml` habría reemplazado el activo bueno por uno con **cero
edificaciones, cero kilómetros de vía y cero adultos mayores**, publicado como
Release, en silencio.

Cerrado en tres piezas: el cableado de las capas que faltaban,
`validate_layer_coverage` —que detiene el build si cualquier capa requerida
suma cero en todo el país— y las pruebas nocturnas contra Overture y WorldPop,
que avisan cuando el contrato de la fuente se mueve en vez de esperar al
trimestre.

### Lo que impide cerrar Fase 0

La puerta de salida de la espec pide cuatro cosas:

| Requisito | Estado |
|---|---|
| G1 verde | ✅ |
| G2 verde | ✅ cerrado el 24-ago-2026: los dos mainshocks reconstruidos, cifras congeladas |
| Un reporte real publicado end-to-end **sin intervención** | ⏳ falta que ocurra un sismo |
| Latencia medida y publicada | ⏳ falta que ocurra un sismo |

**Las dos que quedan esperan lo mismo, y hasta el 25-ago no era así.** La de
latencia estaba bloqueada por un bug, no por la sismicidad: `impact.yml`
publicaba `events/` y `reports/` y **no** `site/status.json`, de modo que el
sistema calculaba la latencia correctamente y no la publicaba nunca. Un `git
add` incompleto llevaba semanas haciendo pasar por «esperando un sismo» algo que
no dependia de ningún sismo.

Cerrado eso, las dos las cierra el primer M≥5,5 en LATAM. El camino esta probado
sobre 21 eventos históricos en 15 países: cuando ocurra, lo único manual sera
publicar el hilo.

---

## 1. ✅ La puesta en marcha, hecha el 24-ago-2026

Los cinco pasos que desbloqueaban la operación están cerrados. Se dejan
anotados porque son el registro de que el sistema arranco, y porque hay que
rehacerlos si alguna vez se migra el repositorio.

| | Paso | Resultado |
|---|---|---|
| 1.1 | Fusionar el PR #1 | `main` = `e67390c`, 100 archivos, CI en verde |
| 1.2 | Publicar el activo | `exposure_quarterly.yml`, que construye y publica en un paso |
| 1.3 | Habilitar Pages | https://sforero77.github.io/CENTINELA/ sirviendo visor, `/status` y reportes |
| 1.4 | Monitor externo | `HEALTHCHECK_URL` guardado como secreto |
| 1.5 | Probar el circuito | Trigger contra el feed vivo (18 sismos revisados, 0 relevantes) y simulacro, ambos verdes |

**El repositorio pasó a público** en el mismo movimiento. No fue solo para que
Pages fuera gratis: un sistema cuyo objetivo declarado es servir de insumo
abierto a la UNGRD y a pares regionales, con rol de mantenedor por país y guarda
anti-fork en los workflows, no puede vivir en privado.

**A partir de aquí la referencia es
[`docs/OPERACION.md`](docs/OPERACION.md)**: que vigilar, que caduca solo, y que
esperar del primer sismo real. El procedimiento de arranque, por si hay que
repetirlo, sigue en
[`docs/PUESTA_EN_MARCHA.md`](docs/PUESTA_EN_MARCHA.md).

---

## 2. Lo que falta

Ordenado por lo que más desbloquea. Lo ya cerrado esta en §3, en una línea cada
cosa, porque este documento es la lista de trabajo y no el registro de lo hecho.

### 2.1 ✅ Brasil, el país 19 · cerrado el 28-ago-2026

Fue el último de los diecinueve en tener activo, y no por falta de intento:
fallo dos veces, el 25 y el 26 de agosto. Se deja el diagnóstico entero porque
la lección —el pico de memoria no puede depender del tamaño del país— vale para
cada país que entre en Fase 1.

**Brasil es el país más caro con diferencia:**

| | Colombia | Brasil |
|---|---|---|
| Teselas GHS-POP | 9 | **36** |
| Serie age-sex de WorldPop | ~600 MB | **9,1 GB** (20 rasters de 453 MB) |
| Celdas H3 con población | 519.735 | **4.293.218** |

**Lo que dice el log de la corrida del 25-ago**, que fallo tras 1 h 43 m:

| | |
|---|---|
| 00:59 · 01:02 | GHS-POP y GHS-BUILT-S descargados (437 MB) |
| 02:26 | WorldPop age-sex descargado — los 9,1 GB, en 90 min |
| 02:36 | HDX descargado. **Todo bajado, sin un fallo** |
| 02:38 | Población agregada a H3: 4.293.218 celdas, 401 M habitantes |
| **02:39** | `The runner has received a shutdown signal` |

O sea que **no fallo la descarga ni el timeout** —quedaban 16 minutos de los
120— sino que el runner se murió durante el cómputo, tres minutos después de
terminar de bajar.

**Era la memoria, y costo tres diagnosticos llegar.** La segunda corrida, con
300 minutos en vez de 120, murió **en el mismo sitio**: 4.293.218 celdas,
401.451.273 habitantes, y treinta y ocho segundos después el mismo mensaje. La
anterior tardo 36. Determinista, con 194 minutos de margen sin usar.

Justo después de `pop_h3` viene `pop_alt_h3` — el WorldPop **total** del país, un
único fichero— y `raster_to_arrow` hacia `src.read(1)`, que trae la banda entera
a memoria. Eso es lineal en el área:

| País | Píxeles | Banda + máscara en RAM | ¿Construye? |
|---|---|---|---|
| Colombia | 0,39 G | 1,9 GB | ✅ |
| México | 0,86 G | 4,3 GB | ✅ |
| **Brasil** | **2,57 G** | **12,8 GB** | ❌ |

Un runner de GitHub tiene **16 GB**. No había forma de que Brasil cupiera.

**Cerrado leyendo por ventanas de filas** (`raster_blocks_to_arrow`): el pico
deja de depender del país —son los mismos ~128 MB para Colombia que para
Brasil— y de paso abarata los diecisiete restantes. Una prueba comprueba sobre
el AST que ninguna lectura vuelva a ser sin `window`, y otra que partir en
bloques no mueva un solo píxel: `filas` es relativa a la ventana y sin sumarle
el origen cada bloque caería sobre el anterior.

**Los dos arreglos anteriores se quedan**, aunque no fueran el bloqueo:
`--liberar-rasters` en CI, que evita tener 9,6 GB de rasters puestos cuando
DuckDB derrama; el `timeout-minutes` en 300; y el registro del **disco libre**
en cada paso, que es lo que faltaba para no tener que deducir esto tres veces
—el mensaje con que GitHub mata un runner sin recursos no distingue disco de
memoria.

**Construido y publicado el 26-ago-2026**, y reconstruido el 27. Midió
**218.881.538 habitantes**, un desvío del 2,85 % frente a la referencia de la
ONU. Los diecinueve países tienen activo.

**Pero pasó dos días vigilado por una tolerancia del 25 %**, y eso no fue
descuido: `calibrar.aplicar` solo reescribia `medido_ghs_pop` si la clave ya
existía y **nunca la creaba**, así que un manifest recién escrito no la recibia
por muchos builds correctos que acumulara. Con ese margen, el assert de §6.4
aceptaba a Brasil con 55 millones de habitantes de menos.

Y como `construido` se deriva de esa clave, la página pública de cobertura
declaraba `paises_construidos: 18` y a Brasil como `poblacion_medida: 0` — **219
millones de personas de menos en una cifra pública**, con el activo en el Release
desde el 26. Cerrado el 28-ago-2026: la clave se inserta si falta, Brasil quedó
en 3,35 % y la cobertura publicada pasa a 19 países y 649.793.406 personas.

**Y aunque este construido, Brasil no puede producir un reporte** con el pipeline
actual. Sus doce sismos M≥5,5 desde 2000 están entre 534 y **645** km de
profundidad —el tope decía 603 y estaba mal; el más profundo es `usp000fgsv`, a
644,9 km— todos en Acre, y el máximo de MMI que USGS modela para cualquiera de
ellos es 3,0. Se construye por preparación —un somero raro en la costa cambiaria
eso en un día— no para obtener un backtest.

### 2.1.bis Bolivia si puede producir un reporte, y no lo tiene

**Abierto el 1-sep-2026.** Este documento, el README y `docs/AUDITORIA.md`
decian que Bolivia era el caso de Brasil: sus veintidós sismos M≥5,5 desde 2000
«entre 359 y 596 km», sin intensidad de superficie que medir.

Es falso, y el error tiene la misma causa que el de Argentina y Republica
Dominicana que la auditoría ya documento: la búsqueda se hizo ordenando por
relevancia sobre una caja envolvente que se llena de sismos chilenos, y la lista
se leyó truncada. Recontado contra el catálogo de USGS, los veintidós van **de
33 a 608 km**.

El más somero es **`usp000ahzc`, M6,2 del 4-jul-2001, a 33 km cerca de Colomi**,
con MMI modelada de **6,4** y `download/cont_mmi.json` publicado. Es un evento
que este pipeline puede calcular hoy: el activo boliviano esta construido y
medido.

Lo que falta es correrlo:

```
uv run centinela impact usp000ahzc
```

`tests/integration/test_silencio_de_paises_live.py` vuelve a comprobar contra
USGS que Paraguay y Uruguay siguen sin un solo sismo, que los de Brasil siguen
siendo todos profundos, y que el somero de Bolivia sigue ahí con sus contornos.
Es la única de las cuatro afirmaciones del README sobre países en silencio que
no era cierta, y ahora las cuatro tienen prueba.

### 2.1.ter La tabla del contraste con Microsoft, sin fuente

**Abierto el 1-sep-2026.** `docs/PARA_INSTITUCIONES.md` §6 publicaba una tabla
con edificaciones evaluadas, dañadas y celdas fuera del activo para Cali y La
Guaira. De ahí salía el argumento del "factor de trece", que es de los más
citables del proyecto.

Ninguna de esas cifras apuntaba a un fichero del repositorio. `centinela
contraste` imprimía su resultado por stdout y lo perdía, así que la sección no
decía que subconjunto de celdas tomo ni contra que versión del vector. En un
documento que abre con «todo lo que afirma esta medido, y dice donde esta la
medida», y que además va a instituciones, eso no se sostiene.

Hecho: el comando ya persiste con `--salida`. Falta correrlo y comprometer el
resultado:

```
uv run centinela contraste <url-del-vector> --exposure 'data/exposure/COL/*.parquet' \
  --crs EPSG:32618 --etiqueta "Microsoft AI for Good · Cali" \
  --salida data/contrastes/cali.json
```

La tabla vuelve al documento cuando cada fila pueda enlazar su
`data/contrastes/*.json`. Mientras tanto, §6 explica el método y no publica
cifras.

### 2.1.quater Ocho de las diez capas no se contrastan contra nada externo

**Abierto el 1-sep-2026.** `validate_layer_coverage` comprueba que ninguna capa
requerida sume cero, y `validate_national_total` contrasta **solo la población**
contra una referencia oficial del manifest. Las otras ocho capas pasan por
«distinto de cero y finito» y nada más.

Un error sistemático del 20 % en `road_km` pasaria entero. Y son cifras
publicadas y contrastables: Colombia sale con **307.314 km de vía** y **9.888
sedes de salud**, y hay referencias nacionales para las dos —INVIAS para la red
vial, el REPS de MinSalud para los prestadores— que este mismo repositorio ya
nombra: `layers.py` describe el REPS como «referencia de completitud municipal
en una tabla aparte».

El mecanismo esta a mano: `referencia_oficial` del manifest ya tiene la forma
(`valor`, `fuente`, `tolerancia_pct`) y `centinela calibrar` ya sabe estrechar
una tolerancia con lo medido. Falta generalizarla a
`referencias_por_capa: {capa: {valor, fuente, tolerancia_pct}}` y que
`validate_national_total` recorra las que existan.

**Lo que NO se hace hasta que haya mantenedor de país:** poner cifras de
referencia inventadas o copiadas sin verificar. Una tolerancia contra un número
que nadie comprobo es peor que no tener alarma, porque parece que la hay. La
mecánica se construye cuando haya al menos un par (capa, referencia) verificado
por alguien que responda por el.

### 2.1.quinquies `mmi_max` no es un máximo

**Abierto el 1-sep-2026.** `contours_to_h3` asigna el mismo valor a `mmi_mean` y
a `mmi_max`: el de la isolínea que contiene el **centro** de la celda. Eso hace
de `mmi_max` una cota inferior de la intensidad máxima dentro de la celda —una
celda de 0,74 km² cuyo centro cae en la banda de 7,0 puede tener una esquina
dentro de la de 7,5— y sale publicado con ese nombre y con la etiqueta HXL
`#indicator+mmi+max` en `adm2.csv`, en `celdas.json` y en el ranking municipal.

El sesgo va en una sola dirección: nunca sobreestima. Eso lo hace tolerable
mientras este declarado —lo esta, en la docstring de `MmiCell`— y no lo hace
correcto.

Arreglarlo pide muestrear la celda y no su centro: los siete vertices, o el
máximo de las isolíneas que la intersecan. Cambia las veintiuna cifras
publicadas a la vez, así que se hace con el catálogo entero y publicando el
delta, igual que se hizo con `col-v0.5`.

### 2.1.sexies Medir el delta entre `cont_mmi.json` y `grid.xml`

**Abierto el 1-sep-2026.** El sistema calcula sobre las isolíneas del ShakeMap y
no sobre su malla. La justificación escrita es de rendimiento —las isolíneas son
órdenes de magnitud menos geometría— y esa es una razón de ingeniería, no una de
método.

Rellenar entre isolíneas de paso 0,5 le da a cada celda el valor de la banda que
contiene su centro. `grid.xml` trae el campo continuo, así que produciría otra
cifra. **Cuánto otra no está medido**, y es la primera pregunta que hará
cualquiera que revise esto con criterio.

Correr las dos sobre el mismo evento —el Chocó, que tiene todo congelado en
golden— y publicar el delta. Si es menor del 3 %, la decisión queda defendida
con un número en vez de con un argumento. Si es mayor, es un hallazgo y hay que
cambiar el método. Los dos resultados valen más que la situación actual.

### 2.1.septies El arreglo de A1 está en el código y no en el dato publicado

`SQL_IMPACT_ADM2` ya lleva el corte de MMI≥6 y la columna se llama
`lq_pop_expuesta_mmi6p`, pero **ningún `adm2.csv` se regeneró**: los veintiún
publicados siguen sirviendo la columna vieja, calculada desde MMI 5,0.

Medido contra la página publicada el 1-sep-2026, sumando la columna del CSV
contra la cifra nacional del mismo evento:

| Evento | Suma del CSV | Nacional | Diferencia |
|---|---:|---:|---:|
| Tehuantepec | 590.431 | 360.767 | **+229.663** |
| Muisne | 1.348.531 | 1.160.483 | **+188.048** |
| Chocó | 1.660.190 | 1.600.028 | +60.162 |

**Quince de los veintiún** no cuadran. Quien baje el CSV para repartir ayuda y
lo contraste contra la cifra nacional del reporte sigue encontrando hoy una
diferencia que nadie sabe explicar — que es exactamente el problema que A1
identificó.

No se regeneraron porque rehacer un `adm2.csv` exige correr P2 entero por
evento, y eso necesita el activo de exposición del país, que no vive en el
repositorio. `regenerar-textos` y `regenerar-mapas` no llegan: los dos son
derivados del `report.json`, y esta columna no.

**Lo que lo cierra:** un despacho de `impact.yml` por evento con `backtest` y
`reprocesar`. La receta está en `docs/OPERACION.md`, §3.bis.

**Lo que lo vigila mientras tanto:**
`tests/unit/test_el_csv_cuadra_con_el_reporte.py` suma la columna de cada CSV
publicado y la compara con `pop_lq_alta` y `pop_ls_alta` del `report.json` de al
lado. Los quince pendientes están **enumerados** en `PENDIENTES_DE_REEMITIR`, no
escondidos tras un margen, y hay una segunda prueba que falla si alguno ya cuadra
y sigue en la lista. Cada evento re-emitido sale de ahí; cuando quede vacía, la
guardia es total.

`test_ground_failure_cuadra.py` vigila el SQL. Esta vigila el artefacto, que es
lo que faltaba.

---

### 2.2 Coropletas r7/r6 del visor

**Hecho el 24-ago-2026:** el mapa ya dibuja. El fondo salió primero de las
PMTiles que Overture publica por release y **se cambio a OpenFreeMap (estilo
Positron)** el mismo día: una tesela de Overture a zoom 4 pesa 4,3 MB y no trae
una sola etiqueta; una de OpenFreeMap a zoom 6 pesa 101 KB y trae topónimos,
vías y agua. Sigue sin llaves ni cuota (D6). Ya no hay `OVERTURE_RELEASE` en
`site/assets/app.js` y no hay nada que subir cada trimestre por el lado del
mapa base.

**Falta:** las coropletas r7/r6 de exposición e impacto. Son datos nuestros y
necesitan `tippecanoe`, y son la última pieza de RF-09 — el resto del visor
(lista de eventos, ficha municipal, descargas, malla por celda, área de
afectación y filtro por país) ya funciona.

### 2.3 Simbología del visor · quedan dos cosas

Hecho: la rampa de intensidad del visor es ya la misma que la del mapa estático
—se había introducido la de ShakeMap sin ver que el proyecto tenía una decidida
y argumentada, y el mismo evento salía de dos colores según donde se mirara—, la
leyenda se construye con las clases que trae el evento en vez de rotular siempre
las seis, el epicentro es una estrella en vez de un círculo proporcional que se
leia como radio de afectación, y `salud` y `edu` son capas del selector: estaban
en `celdas.json` desde el principio y solo se veian abriendo celda por celda.

**Falta:**

* A zoom continental, dos eventos del mismo día a 150 km comparten sitio y
  MapLibre oculta una de las dos etiquetas. Se ve en los dos de Venezuela.
* Los cortes de `salud` y `edu` están medidos sobre 1.691 celdas de tres eventos
  en dos países. Cuando entre un país con más equipamiento mapeado hay que
  volver a medirlos, igual que se hizo con los de población y vías.

### 2.4 ✅ Los diecinueve países, construidos y medidos

**Cerrado.** Comprobado el 31-ago-2026 contra `site/cobertura.json`: los 19
`construido: true`, **649.793.406 personas en la malla** y **4,94 % de peor
desvío** contra las referencias de la ONU, dentro de la tolerancia declarada.

Esta sección decía "hace falta construir y medir" mucho después de que ambas
cosas estuvieran hechas, que es la misma clase de nota vencida que una vez
produjo un rótulo falso en el visor. Lo que sigue es el procedimiento, que
mantiene su valor para cualquier país nuevo.

Los **19 manifests están escritos** y sus cajas envolventes medidas sobre
`division_area` de Overture con un solo criterio. Por país ya no hace falta
buscar datos: hace falta **construir y medir**, más un mantenedor que valide los
topónimos.

Lo que cada país nuevo necesita, en orden:

1. `uv run centinela country <ISO3>` — unos 800 MB y una hora larga por país.
2. Anotar `medido_ghs_pop` en su manifest y **ajustar `tolerancia_pct`**, con
   `centinela calibrar <medicion.json>`. Hecho para los diecinueve: las
   tolerancias van de 0,59 % (Paraguay) a 5,44 % (Venezuela).

   **Este paso no es opcional y el sistema no lo hacia solo.** `calibrar` solo
   reescribia `medido_ghs_pop` si la clave ya estaba, y un manifest recién
   escrito no la trae: Brasil acumulo dos builds correctos vigilado por su 25 %
   provisional. Arreglado el 28-ago-2026 —la clave se inserta si falta— y hay
   una prueba que exige que los diecinueve declaren lo que midieron. Aun así,
   **`calibrar` hay que ejecutarlo**: el build publica `medicion.json` en el
   Release y no toca el manifest.
3. Fijar los digests con `centinela fijar-insumos <ISO3>` sobre esa misma
   medición. Sin eso, la fuente del país no queda verificada contra
   republicaciones — §2.6.
4. Validar los topónimos. (La codificacion de Venezuela estaba anotada como
   rota —«Falc?n»— y **no lo esta**: era la consola de Windows. Verificado
   byte a byte sobre el parquet publicado.)
5. Publicar el activo como Release.

Ojo con el coste de las cajas insulares: Chile llega a 109,7°O por Rapa Nui,
México a 118,6°O por Guadalupe y Revillagigedo, Ecuador a 92,3°O por Galapagos.
Son muchas teselas de GHS-POP por poca población, pero el sistema no puede
decidir que una isla habitada no cuenta.

### 2.5 T0.7: benchmark de `exactextract` · bajo esfuerzo

Comparar el muestreo actual (suma de píxeles por celda) contra `exactextract`.
Criterio de la espec: menos de 1 % de diferencia en la población nacional. Si
cumple, se documenta y se cierra; si no, se cambia el método.

### 2.6 Deuda menor

- **✅ Los digests de insumos, fijados el 28-ago-2026.** Las 194 fuentes de los
  diecinueve manifiestos llevaban `insumos_sha256` vacío, y esta línea decía que
  "se llenan solos en la primera corrida de `make country`" — falso en dos
  sitios: el inventario se devolvia y se **tiraba**, y el campo era escalar
  cuando una fuente aporta cero, uno o veinte ficheros.

  Hoy están fijados: **136 con digest y 58 sin el**, y esos 58 son exactamente
  las fuentes que se leen en remoto (Overture y la cobertura del suelo), que no
  pasan por disco y no tienen bytes que hashear. El lint sale sin un solo aviso
  por primera vez. En total, **664 ficheros y 18,6 GB de insumos verificados**.

  El circuito, para el próximo país: el build mide y publica el bloque `insumos`
  en `medicion.json`, y `centinela fijar-insumos <ISO3>` lo vuelca al manifest
  sin tocar la prosa. A partir de ahí, un insumo republicado por un tercero
  **detiene el build en la descarga** en vez de fallar dos horas después.
- `overture_divisions` esta declarado en `COL.yaml` y no se usa: la geometría
  sale del MGN. No cuesta nada (las fuentes `s3://` no se descargan) pero
  induce a pensar que participa.
- **T0.10**: la referencia de población del DANE es la cifra redondeada de su
  nota técnica (53.000.000). Sustituirla por el valor exacto del anexo en Excel
  haría que el assert compare contra un número y no contra un redondeo.
- `admin_lookup` guarda el centroide como WKT en texto. Funciona, pero
  `GEOMETRY` sería más limpio.
- **✅ Ortografía del generador de reportes, cerrada el 31-ago-2026.** El
  generador ya estaba acentuado; lo que estaba rancio era lo **publicado**. Los
  veintiún `report.md` y `hilo.txt` se emitieron el 25-ago-2026, antes de esa
  corrección, y nadie volvia a tocarlos: el hilo para redes —el único artefacto
  que un humano publica a mano— abría con "Reporte automático de Exposición
  estimada" y cerraba con "Exposición no es daño", que en español no es una
  frase.

  Quedaban tres restos reales en el código: "Intensidad máxima" en la leyenda
  del PNG, "no estima víctimas" en el markdown, y `format_count_prose`
  escribiendo "1 millón". Corregidos.

  El circuito, para la proxima: `centinela regenerar-textos` rehace los dos
  ficheros de cada reporte publicado sin recomputar el impacto —el gemelo de
  `regenerar-mapas`— y `tests/unit/test_textos_publicados.py` vigila el
  generador con una lista negra de las formas que se colaron.
- **El mapa base tarda 8-10 s en pintar teselas desde frío.** Ninguna cifra
  depende de ellas y el tablero es usable antes, pero la primera pantalla se
  siente lenta. Precargar el estilo o servir un encuadre estático mientras
  llegan las teselas son las dos salidas obvias.
- Las etiquetas largas del mapa estático se pisan entre si: la separación minima
  es de 0,25° y "Ocumare De La Costa De Oro" mide bastante más.
- **La tolerancia por país no se ensena, y es una decisión tomada.** El visor
  publicaba "peor desvío vs. cifra oficial: +4,94 % — el de Venezuela, y esta
  explicado" sin que la explicación existiera en ninguna parte, y remataba la
  nota de cobertura con "una tolerancia que nadie ve no vigila nada" en una
  tabla que era justo lo único que no enseñaba la tolerancia. Las dos frases se
  quitaron del visor el 31-ago-2026.

  El dato sigue publicado en `cobertura.json` (`tolerancia_pct` por país) y en
  cada manifiesto. Su sitio es un documento metodológico que explique de donde
  sale —`centinela calibrar`, que estrecha con lo medido y nunca ensancha sola—
  y por que el desvío de GHS-POP frente a una proyección demografica es
  esperable. Ese documento esta sin escribir.
### 2.6.1 Lo que dejó abierto el recorrido del visor (1-sep-2026)

Salió de usar la página publicada como usuario final. Lo grave se arregló y está
en `VERIFICACIONES.md`, ronda 6; esto es lo que **sigue abierto**, en orden de
cuánto molesta.

- **✅ La cadencia del vigía, cerrada el 1-sep-2026.** La portada prometía «menos
  de una hora» mientras `/status` medía 74,4 min de mediana **solo en detectar**:
  el objetivo de 60 min de RNF-02 no se podía cumplir aunque el resto del
  pipeline fuera instantáneo. La revisión cruzada quitó la promesa de la portada
  y el aviso de `/status` pasó a aparecer sólo si la cadencia supera el objetivo.

  Y la causa se cerró desde fuera: el cron externo arrancó ese mismo día a las
  05:01 UTC y lleva 196 revisiones por `repository_dispatch` cada cinco minutos.
  **La mediana bajó de 74,4 a 5,0 min**, seis veces por debajo de los 30
  declarados. El p90 sigue en 445 min porque arrastra las corridas viejas, que
  las concedía la cola de GitHub; se limpiará solo.
- **`/status` no cubre el fuego.** El panel de fuego enlazaba a Estado
  prometiendo «la cadencia real»; se le quitó el enlace porque Estado solo
  publica latencia sísmica y las revisiones del vigía. La frescura de P5 no se
  publica en ningún sitio.
- **`/status` publica «latencia 5346 d»** para las reconstrucciones, con una nota
  debajo diciendo que no significa nada. La tabla se lee como un muro de
  fracasos; la distancia sismo-reproceso merece su propia columna, más callada.
- **Un foco de fuego no dice dónde está.** Ni país, ni región, ni el municipio
  más cercano: se pulsa un incendio, el mapa vuela a un río sin nombre del
  Amazonas y el panel dice «2 celdas contiguas ardiendo».
- **El globo de una celda de fuego se recorta** contra los controles y la barra
  de escala cuando el foco cae cerca del borde derecho del mapa. El dato está en
  el DOM y no se lee en pantalla.
- **La holgura entre la barra de escala y la leyenda es de 1 px** en 390 px con
  un evento abierto. Sin solape, pero cualquier control nuevo en esa esquina —o
  un cuerpo de letra mayor— la vuelve negativa.
  `test_la_barra_de_escala_no_cae_dentro_de_la_leyenda` la vigila.
- **Las etiquetas de las métricas miden 10,5–11,5 px.** Medido: contraste 5,2:1,
  pasa AA. El problema es el tamaño, y son justo las que dicen qué es cada
  número.
- **La malla del evento se ve apolillada.** Los huecos blancos dentro de la
  mancha son celdas sin exposición —honesto— pero se leen como un fallo de
  render.
- **En móvil la fila de filtros es una tira con `overflow-x: auto`** y no hay
  ninguna señal visual de que hay más a la derecha. El control se alcanza
  deslizando; comprobado.
- **El área de un símbolo del mapa estático está muy comprimida.** `_tamano` es
  `12 + 4·sqrt(pop/1000)`: entre mil y 333.000 personas el área del círculo solo
  se multiplica por 5,3. Ahora que el PNG lleva leyenda de tamaño la compresión
  se ve. Un escalado proporcional al valor —área ∝ población, con mínimo
  visible— sería lo correcto.

---

### 2.7 Haití · FUERA DE ALCANCE por decisión del 31-ago-2026

**Decidido: no se hace.** Esta sección se conserva —en vez de borrarla— porque
la omisión es lo bastante llamativa como para que alguien la vuelva a proponer
cada vez que lea este documento, y para que quien la vea sepa que no es un
descuido sino una decisión tomada. Lo que sigue es el análisis original.

**No tiene manifiesto, no estaba en esta lista, y no aparecia en la auditoría.**
Se cayó de la lista de los veinte en algún momento y nadie lo noto — yo tampoco,
en toda la auditoría del 25-ago.

Y es la omisión más grave posible en esta región. Puerto Príncipe 2010, M7,0:
entre 100.000 y 300.000 muertos, el terremoto más letal de la historia de
América. Nippes 2021, M7,2: 2.200 más. Haití esta sobre la falla de
Enriquillo-Plantain Garden y comparte isla con Republica Dominicana, que **si**
tenemos. Un sistema de exposición sísmica para LATAM que cubre la mitad de La
Española es difícil de defender.

Haría falta `data/manifests/HTI.yaml` y una corrida de `exposure_quarterly`.
No se va a hacer.

### 2.8 ✅ El reloj externo, montado y midiendo

**Cerrado el 31-ago-2026.** El cron externo despacha `repository_dispatch` y se
midió sobre 60 corridas reales de `P1 · Trigger USGS` en cinco horas:

    hueco mediano 5,0 min · p90 5,1 · peor 5,1

Contra los 87,6 min de mediana y los 765,9 del peor hueco que dejaba el
planificador de GitHub. Era "lo único que rompe la promesa del sistema" y ya no
la rompe.

**Ojo con la cifra publicada:** `status.json` sigue mostrando `p50_min: 87,6`
porque promedia toda la historia, incluidos los meses sin cron. No es un fallo
—es la mediana real de lo vivido— pero describe un problema que ya no existe, y
bajara sola conforme se acumulen latidos. Separar "cadencia histórica" de
"cadencia de los últimos 7 días" esta sin hacer.

Lo que sigue es el diagnóstico original, que explica por que hizo falta.

**Es el pendiente más caro de la lista, y el único que no se puede cerrar desde
un clon.** El objetivo O1 es p50 <= 60 min desde el origen hasta el reporte
publicado. La detección sola tiene una mediana de 45,6 min y un máximo medido de
**11,1 h**: el presupuesto entero se lo puede comer el primer paso.

La causa esta cerrada y no admite arreglo interno. GitHub concede unos pocos
turnos de cron **por repositorio**, no por workflow, y los reparte cuando quiere.
Se comprobo lo obvio y no era: los dos peores huecos tuvieron 2 % y 0 % de solape
con builds de exposición, así que **no es que nuestras propias corridas saturen
la cola**. Es el planificador.

Lo que ya esta puesto y funciona:

* El vigía es el reloj del repositorio: despacha `frescura` e `incendios` por
  `workflow_dispatch`, que no pasa por esa cola.
* Los dos conservan su `schedule` **a propósito**, como respaldo por si el paso
  de despacho deja de correr. Hay una prueba que lo exige; quitarselo para
  liberar turnos se intento el 28-ago-2026 y se revirtio.
* El monitor externo (healthchecks.io) alerta a los 30 min de silencio, y
  **alerta de verdad**: confirmado por el mantenedor sobre los huecos del
  27-ago. El sistema no estuvo ciego sin saberlo.

Lo que falta es la parte que necesita credenciales, y por eso vive aquí y no en
el código:

1. Un PAT *fine-grained* con `actions: write` sobre este repositorio.
2. Un disparador externo —Cloudflare Workers, cron-job.org, lo que sea— que
   llame a `workflow_dispatch` de `trigger.yml` cada 10 min.

La espec ya lo contempla como *upgrade path* documentado (§ "Orquestación").
`trigger.yml` acepta `workflow_dispatch` desde el primer día, así que del lado
del repositorio no hay nada que escribir: es puramente una tarea de
infraestructura.

**Mientras no este, el objetivo publicado y la infraestructura no coinciden.**
Las dos salidas honestas son montarlo o publicar el objetivo real; sostener 60
min con una detección cuya mediana son 45,6 es la clase de cifra que este
proyecto no se permite en ningún otro sitio.

### 2.9 Viento para el fuego · decidido A, sin escribir

**Esto tenía que estar escrito hace días y no lo estaba.** Se investigo, se
llegó a una conclusión con consecuencias de licencia, y se quedó en la
conversación. Que es justo lo que esta sección existe para evitar.

**Que falta.** El panel de un foco dice cuanto arde y sobre quien, pero no hacia
donde va. Velocidad y dirección del viento, y humedad relativa, son las
variables que convierten "hay fuego aquí" en "va hacia allá" — es lo que hace
útil al Wildfire Aware de Living Atlas, que fue de donde salió la idea.

**Por que no Open-Meteo, que era el camino obvio.** Su nivel gratuito es **no
comercial**. Meterlo haría del cubo NC de D8 —hoy vacío a propósito— el primer
cubo con algo dentro, y contaminaría el activo publicado: el mismo dataset que
hoy se puede redistribuir bajo CC BY 4.0 dejaria de poderse. La regla de los
tres cubos no tiene excepción para "es solo una variable más".

**Decidido: NOAA GFS directo.** Es **dominio público**, o sea cubo núcleo, sin
llave —lo que respeta D6— y con cobertura global cada 6 h. El coste es que hay
que leer GRIB2 en vez de un JSON, y elegir la retícula: GFS va a 0,25°, unos 27
km, contra los 5,2 km² de una celda H3 r8. **Una dirección de viento de 27 km
aplicada a una celda de 5 km es una interpolación, y hay que rotularla como
tal** o sera otra cifra creíble y falsa, como lo habría sido publicar la
temperatura de brillo en grados.

**Sin empezar.** Lo único hecho es descartar Open-Meteo y elegir la fuente.

---

## 3. Cerrado, y donde esta el detalle

Lo que este documento listaba como pendiente y ya no lo esta. Cada línea tiene
su historia completa —evidencia, criterio de aceptación y como se cerro— en
[`docs/AUDITORIA.md`](docs/AUDITORIA.md); aquí solo quedan los titulares para
que nadie lo vuelva a abrir por costumbre.

**Cerrado el 24-ago-2026**

- La ventana del disparador cortaba territorio de México, Chile y Brasil.
- El impacto usaba el activo de Colombia para toda LATAM.
- G2: los dos mainshocks de Venezuela, publicados.
- RF-03: el reporte preliminar sin ShakeMap, que estaba escrito y sin llamador.

**Cerrado el 25-ago-2026, en la auditoría** — A1 a A21

- El latido de `/status` no se publicaba nunca, y la latencia se calculaba sin
  guardarse: dos requisitos de Fase 0 bloqueados por un `git add`.
- El trimestral reconstruia un país de dieciocho.
- El README publicaba cifras de un activo anterior; los km de vía, por un
  factor de seis.
- `cli.py`, `raster_h3.py` y `celdas.py` no tenían ni una prueba.
- Los asserts de §6.4 no corrian en P2, y la licencia de la fuente no se
  contrastaba nunca.
- RF-04 renderizaba un changelog que nadie calculaba.
- Un PROJ del sistema —el que instala PostGIS— dejaba inservible el pipeline geo.
- Chile no habría tenido reporte nunca: su caja mide 1.719 grados cuadrados por
  Rapa Nui y un sismo en Coquimbo se ordenaba como argentino.
- El 44 % de los sismos reales no llega a MMI≥7 sobre población, y el producto
  entero titulaba con MMI≥7. Tehuantepec salía con «0 personas».
- Los topónimos salían en inglés, incumpliendo RF-06.

**Cerrado el 26-ago-2026, auditando el visor** — A22 a A27

- El mapa se quedaba en blanco al abrir un enlace compartido con la caché fría.
- Los epicentros no se dibujaban: el mismo fallo, en un segundo sitio.
- El epicentro se salía del encuadre en los sismos mar adentro.
- La celda no se podía citar: el índice H3 no llegaba a la ficha.
- El tablero enseñaba la exposición y la llamaba afectación; los contornos del
  ShakeMap se descargaban en cada evento y se tiraban.

---

### 3.x Sismos vistos y no despachados · cerrado el 26-ago-2026

El caso que lo motivo fue real: un **M4,9 a 160 km bajo Jordán, Santander**, el
26-ago a las 16:45 UTC, sentido en media Colombia. El sistema lo vio a las
16:57:38 —**doce minutos y cuarenta y un segundos después**— lo evaluo, y
decidió bien: `M4.9 < umbral M5.5`.

Pero esa decisión solo existía en un log de CI. Desde el visor, **«lo vi y es
inofensivo» y «estoy roto» se veian exactamente igual**. Un vigía que no puede
demostrar que estuvo mirando no se distingue de uno apagado.

**El umbral no se toco.** M5.5 sigue siendo lo que dispara un reporte. Lo que
cambia es que por debajo se *registra* en vez de *olvidar*: `site/observados.json`,
ventana móvil de **5 días**, y una capa gris apagable en el visor.

Tres reglas lo sostienen, y cada una tiene pruebas:

1. **Esquema aparte, no un reporte degradado.** `EventoObservado` no tiene un
   solo campo de impacto, y una prueba lo comprueba campo por campo. Publicar
   `pop_mmi7p: 0` sería un falso negativo con aspecto de dato: ausencia de
   medición no es medición de cero.
2. **Peso visual de «esto no es una alarma».** Gris fuera de la rampa de MMI,
   hueco, pequeño, sin etiqueta, sin halo, y apagado de entrada. La rampa
   significa «impacto medido»; prestarsela lo vaciaria de sentido — es el riesgo
   §7 en su forma visual.
3. **Solo LATAM, y caduca.** Los feeds del USGS son mundiales: sin filtro, la
   capa sería un sismografo global. Se registran solo los sismos que el filtro
   descarto **unicamente por tamaño**, preguntandole otra vez con el umbral en
   cero.

Medido antes de decidir: **277 sismos M4,5-5,5 en LATAM en 90 días** (~3,1/día,
~15 puntos a la vez con la ventana de 5 días) frente a 23 M≥5,5 — de los cuales
**los 23 tuvieron ShakeMap**, así que el caso «pasa el umbral y no hay producto»
que RF-03 ya cubre por radios es raro de verdad.

**La ventana se rellena desde el histórico.** Recién encendida solo sabia lo que
había visto —un sismo— y su etiqueta decía «1 en 5 días» cuando en LATAM había
habido **nueve**. Un número falso sobre el mundo es peor que no dar ninguno.
`centinela observados` reconstruye la ventana desde FDSN, que D7 reserva para
históricos: se llama a mano, no desde el cron. Sirve también de reparación si el
vigía se cae más de un día, que es lo que cubre el feed en vivo.

**Rareza que se ve en el mapa:** `LATAM_BBOX` es un rectángulo, así que se cuela
océano abierto — en la primera ventana entro un M4,9 en la dorsal
medioatlantica. Es el mismo bbox que gobierna el despacho, así que no se toca
aquí, pero explica un punto gris en medio del Atlántico.

**Límite conocido, escrito para no descubrirlo después:** el piso real es
**M4,5**, porque es lo que dan `4.5_hour` y `4.5_day`. Un M4,2 superficial bajo
una ciudad hace más daño que el M4,9 a 160 km de Jordán, y ese no se veria.
Bajar de 4,5 obliga a `all_hour` y multiplica el volumen; no se hace ahora.

---

### 3.y El visor llevaba 17 horas congelado · cerrado el 26-ago-2026

Salió de tirar del hilo de por que el M4,9 de Jordán no se veía. **Un push hecho
con `GITHUB_TOKEN` no dispara otros workflows** — regla de GitHub contra los
bucles infinitos.

`site.yml` escucha `push` sobre `site/**`, `reports/**` y `data/manifests/**`.
Los dos workflows que escriben ahí empujan con ese token. Resultado: el último
despliegue del visor era de las **04:03**, con siete latidos posteriores ya
commiteados, y `/status` en vivo mostrando el de las **02:53**.

**Lo caro no era el latido.** P2 commitea `reports/` con el mismo token: **un
reporte de un sismo real se habría publicado en el repositorio sin llegar nunca
a la página**. No se había notado porque ningún sismo había llegado a reporte por
esa vía — los veintiuno del catálogo se reconstruyeron a mano.

Los dos workflows en verde, el artefacto correcto en su sitio, y el fallo
viviendo en el hueco entre ellos: la misma forma que el resto de esta auditoría.

Cerrado con `gh workflow run site.yml` tras el push —`workflow_dispatch` es la
excepción documentada a la regla, y es el mismo mecanismo con el que P1 ya
dispara P2— más `actions: write` en los dos jobs. Sin PAT.

El guardia esta en `tests/unit/test_el_visor_se_republica.py`, y **deriva las
rutas del propio `site.yml`**: escritas a mano se quedan viejas, y un guardia con
la lista desactualizada da un verde peor que no tener guardia.

---

### 3.z El vigilante del vigilante · cerrado el 26-ago-2026

Lo pidio el usuario y es la regla del proyecto: **el sistema tiene que demostrar
que funciona por si mismo, no porque alguien note algo y pregunte.**

El visor congelado diecisiete horas salió a la luz porque una persona sintió un
sismo y fue a mirar. Eso no puede ser el mecanismo de detección de un sistema de
vigilancia.

`frescura.yml` corre cada tres horas, compara la página **publicada** contra el
repositorio y abre issue si se quedó atrás. Detecta un desfase real como mucho
seis horas después, frente a las diecisiete que costo la primera vez.

**Vigila una cosa sola**: que el repositorio avance y la página no. Si el vigía
muriera, los dos se quedarían quietos a la vez y esto pasaria — de eso se ocupa
el latido al monitor externo (§6.5). Son dos fallos distintos y merecen dos
alarmas distintas: una que no sabe decir cual se rompió obliga a investigar
desde cero.

El caso bueno **también se imprime**. Un vigilante callado cuando todo va bien
es indistinguible de uno apagado, que es como estaba el sistema esa mañana.

---

## 4. Fases siguientes

### 4.0 Donde están las puertas, medido el 28-ago-2026

Las puertas las fija `ESPECIFICACION.md` §"Plan por fases". Contrastadas contra
el estado real:

| Fase | Puerta | Estado |
|---|---|---|
| **F0** | G1 y G2 verdes | ✅ |
| **F0** | Un reporte real publicado end-to-end **sin intervención** | ❌ **0 de 1** |
| **F0** | Latencia medida y publicada | ⚠️ el mecanismo publica; no hay dato |
| **F1** | 7 países reconstruibles con `make country` | ✅ **19**, muy por encima |
| **F1** | >= 4 reportes reales publicados | ❌ **0 de 4** |
| **F1** | 2+ mantenedores país activos que no sean Sebastián | ❌ **0 de 2** |
| **F2** | Un GeoPackage publicado con métricas | ❌ falta T2.4 |
| **F2** | Protocolo probado en simulacro | ⚠️ `simulacro.yml` corre; el protocolo de brigada no esta escrito |

**Los 21 reportes del catálogo son backtest, los 21.** `/status` los excluye a
propósito del cálculo de latencia —`eventos_publicados: 0`,
`backtests_excluidos: 21`, `p50_min: null`— y hace bien: un backtest se procesa
sobre productos de USGS ya asentados, así que su latencia no dice nada sobre lo
que tardaria un evento vivo. La cifra honesta es que **todavía no hay ninguna**.

**El proyecto esta desbalanceado, y conviene verlo claro.** El trabajo de datos
de Fase 1 esta hecho al 271 % —diecinueve países donde la puerta pedia siete— y
las tres puertas que quedan abiertas no dependen de código:

* Dos esperan a que ocurra un sismo M>=5,5 en LATAM. No se pueden forzar y no
  tiene sentido intentarlo.
* Una espera a que haya otras personas. Es la única que se puede empujar hoy, y
  es la que lleva más tiempo sin moverse: `CONTRIBUTING.md` define el rol de
  mantenedor por país y no hay ninguno.

Dicho de otro modo: **el sistema esta terminado para lo que puede terminarse
solo.** Lo que queda es sismicidad y comunidad.


**Fase 2 — Brigada de imagen.** T2.1, T2.2 y T2.3 cerradas el 24-ago-2026 con
las licencias citadas literalmente: Copernicus EMS permite reproducir, adaptar y
combinar sin restricción comercial; Umbra y Capella publican SAR en CC BY 4.0
desde buckets sin credenciales.

Y el orden de la fase cambio. Buscando el GeoPackage de Cali aparecieron
evaluaciones de daño abiertas de **los dos sismos golden**, del Microsoft AI for
Good Lab y usando huellas de Overture — la misma fuente de este proyecto. Así
que el primer hito no es entrenar un modelo, es **contrastar**, y ya esta hecho:
`centinela contraste` compara sobre las mismas celdas H3 y hay un workflow que
lo corre en CI. Medido, la cobertura del activo es completa en los dos eventos
y la fracción dañada va de 0,27 % a 3,69 %.

Queda T2.4: la rama de pesos limpia, que ya tiene de que alimentarse (EMS para
etiquetas, Umbra y Capella para imagen, todas CC BY) pero no esta construida.

**Fase 3 — Institucional.** T3.1 cerrada: AlphaEarth Foundations es CC-BY 4.0 y
puede agregarse al activo con su atribución; Major TOM es CC-BY-SA 4.0 y no
puede sin arrastrar el cubo entero. El contrato de esquema declara la extensión
y **ahora hay una prueba que lo compara contra el activo real**, porque no lo
miraba nadie y había derivado.

Queda lo que no es código: presentar el sistema. Para eso esta
[`docs/PARA_INSTITUCIONES.md`](docs/PARA_INSTITUCIONES.md), escrito con las
cifras medidas y con los limites publicados al lado de lo que el sistema hace
bien.

---

## 5. Trabajar en local

```bash
git clone https://github.com/sforero77/CENTINELA
cd CENTINELA
make setup     # uv, Python 3.12, todo
make check     # lint + mypy + pruebas: lo mismo que corre CI
```

**En Windows no hay `make`.** Ni en `cmd`, ni en PowerShell, ni en el Git Bash
que trae Git for Windows. Los objetivos del Makefile son atajos de una línea,
así que se corren sueltos:

```powershell
uv sync --python 3.12 --extra dev --extra geo --extra render
uv run ruff check . ; uv run ruff format --check . ; uv run mypy ; uv run pytest -m "not network"
```

**Y `print` de Python emite CRLF.** Si automatizas el CLI desde bash —un lote
de backtests, por ejemplo— y lees ids con `mapfile -t`, cada id se queda con un
`
` pegado: `mapfile -t` quita el LF y no el CR. La URL del detail sale
invalida y **falla en silencio, evento por evento**. Se arregla con
`| tr -d '
'` y costo dos intentos encontrarlo.

Si `uv` no tiene Python 3.12 lo descarga solo, pero baja ~21 MB de GitHub y con
una conexión lenta agota el tiempo de espera. `uv python install 3.12` por
separado deja el problema aislado y no hay que repetir el resto.

**Los extras importan.** `make setup` instala `[dev]`, pero el código geo
necesita `[geo]` y los mapas `[render]`:

```bash
uv sync --python 3.12 --extra dev --extra geo --extra render
```

Sin ellos las pruebas correspondientes **se saltan con razón explicita** en vez
de fallar — pero `mypy` si falla, porque necesita ver `numpy` de verdad. Es
justo el fallo que tumbo la primera corrida de CI.

Comandos utiles:

```bash
make country ISO=COL   # reconstruye el activo (~20 min)
make trigger           # P1 en seco contra el feed vivo
make manifests         # lint de licencias y vintages
make test-golden       # solo regresion
uv run centinela status  # recalcula site/status.json
```

---

## 6. Lo que no hay que romper

Invariantes que costaron encontrar. Cada uno tiene su prueba de regresión, y
casi todos comparten forma: **producen una cifra plausible y equivocada**, que
es el único modo de fallo que este sistema no puede permitirse.

**Una función escrita no es una función conectada.** Es la causa raíz de
veintitantos hallazgos de la auditoría, repetida: el latido, la latencia, los
asserts de §6.4, la licencia de la fuente, el changelog de RF-04, el enrutado
por país, los epicentros del visor, los contornos del ShakeMap. **Todas estaban
probadas**, por eso la cobertura las daba por verdes: una prueba llama a la
función y eso no dice nada sobre si la llama alguien más.
→ `tests/unit/test_funciones_conectadas.py`, sobre el grafo de llamadas

**Casi la mitad de los sismos reales no llega a MMI≥7 sobre población.** Ocho de
los veintiuno del catálogo, y son los profundos y los de mar adentro, que en
esta región son la mitad. Fijar MMI≥7 como *la* banda publica «0 personas» para
ellos y ordena la tabla municipal por una columna de ceros.
→ `tests/unit/test_banda_titular.py`, `Totales.banda_titular`

**El área de afectación no es el área de exposición.** La malla H3 llega hasta
donde hay gente; los contornos del ShakeMap, hasta donde llegó el sismo. En
Baláo el área sentida mide cuatro veces más que la cuantificada.
→ `tests/unit/test_contornos.py`

**Ordenar los países candidatos por área de su caja no acierta siempre.** La de
Chile mide 1.719 grados cuadrados por Rapa Nui y la de Argentina 671, así que un
sismo en Coquimbo sale como argentino. El desempate lo da el join, y por eso
hace falta poder reintentar con el siguiente candidato.
→ `tests/unit/test_enrutado_latam.py`, código de salida 3

**`preferredWeight` desempata contribuyentes, no versiones.** Ordenar por peso
elige un ShakeMap obsoleto sin que nada falle.
→ `tests/golden/test_g2_venezuela.py::test_no_se_elige_una_version_obsoleta`

**El rescate de celdas costeras necesita cota de distancia.** Sin ella reclama
el continente entero: la población nacional pasó de 52,6 a 167 millones.
→ `pipelines/p0_exposure/crosswalk.py`, constante `RESCUE_MAX_DEGREES`

**El catálogo STAC de Overture no sigue el estándar.** Publica 512 bboxes para
512 ficheros; el estándar pondría la unión en `[0]`. Leerlo como manda el
estándar desplaza la selección un puesto y da resultados plausibles y erroneos.
→ `pipelines/p0_exposure/sources/overture.py::parse_collection`

**Dos copyleft distintos no caben en el mismo derivado.** ODbL y CC BY-SA 4.0
son ambas share-alike e incompatibles entre si.
→ `pipelines/common/licensing.py::resolve_bucket`

**WorldPop publica tres series de edad, no una.** El mismo directorio trae
`col_f_65`, `col_m_65` y la combinada `col_t_65`. Sumar todo lo que termina en
`.tif` cuenta a cada persona dos veces, y la cifra resultante sigue pareciendo
plausible.
→ `pipelines/p0_exposure/sources/worldpop.py`, solo la serie `_t_`

**La geometría de Overture llega tipada, no como BLOB.** La receta publicada
usa `ST_GeomFromWKB(geometry)` y aquí revienta con "no function matches",
porque el parquet declara `GEOMETRY('OGC:CRS84')`. Y cada tema particiona sus
ficheros por su cuenta: el `00013` de edificaciones y el de transporte cubren
áreas distintas.
→ `pipelines/p0_exposure/overture_h3.py` · `tests/integration/test_overture_contract_live.py`

**Una capa vacía se publica como cero.** No hace falta un bug para llegar ahí:
basta con no cablear la capa. El activo se escribe igual y el reporte informa
"0 edificaciones en MMI≥7" con la misma cara que una cifra medida.
→ `pipelines/p0_exposure/build.py::validate_layer_coverage`

**HOTOSM y healthsites.io son la misma gente contada dos veces.** Las dos
derivan de OSM: el 96,6 % de los puntos de healthsites cae a menos de 20 m de
uno de HOTOSM. Sumarlas da 18.061 sedes de salud en Colombia donde hay ~9.900,
y la cifra parece perfectamente sana.
→ `pipelines/p0_exposure/vector_h3.py::aggregate_points_to_h3`, `DEDUPE_METERS`

**Un dataset de HDX puede publicar varios recursos del mismo formato.** El
COD-AB de Colombia publica cuatro SHP y el primero son secciones urbanas, no
municipios. Tomar "el primero del formato preferido" descarga 48 MB del archivo
equivocado sin quejarse.
→ `hdx_resource` en el manifest · `pipelines/common/hdx.py::resolve_resource`

**Colombia tiene dos fuentes municipales y solo una manda.** El MGN del DANE es
la fuente de verdad del código DIVIPOLA; el COD-AB es el mismo MGN
reempaquetado. El empate se deshace por las columnas que el país declara, no
por orden de llegada.
→ `pipelines/p0_exposure/build.py::pick_admin_source`

**La caja del país se declara antes de poder medirla.** Es el único dato del
pipeline que empieza siendo una afirmación: hace falta *antes* de descargar el
límite administrativo. Una caja corta no falla — recorta teselas y ficheros, y
el activo sale con una punta del país sin población ni edificaciones. Cuadra
todo y falta territorio. Por eso el build la comprueba contra la geometría real
en cuanto la carga.
→ `pipelines/p0_exposure/build.py::validate_bbox_covers_country`

**Más resolución no es más información.** El HRSL de Meta esta a 30 m frente a
los 100 m de GHS-POP, pero su vintage es 2019 y a celda r8 el detalle extra se
promedia. Cambiar sería regalar seis años de vigencia a cambio de nada.
→ `VERIFICACIONES.md`, ronda 4

**Los plazos por defecto de DuckDB no sirven para leer Overture.**
`http_timeout` viene en 30 s y un fichero tarda minutos en conexión domestica.
Peor: la lectura de Overture va al final del build, así que el timeout mata la
corrida con la hora de descargas ya pagada.
→ `pipelines/p0_exposure/overture_h3.py::HTTPFS_SETTINGS`

**Un build de un país falla tarde, así que reanudar tiene que ser barato.**
Son ~1 GB y el paso que más falla es el último. Las seis rutas de descarga
saltan lo que ya esta en disco, y escriben en `.parcial` para que un corte no
deje un ráster truncado que la siguiente corrida de por bueno.
→ `pipelines/p0_exposure/download.py::write_atomic` · `_hdx_en_disco`

Y una regla de producto: **exposición no es daño**. Todo artefacto sale con sus
disclaimers, y el hilo para redes se genera pero **no se publica solo**.

---

## 7. Documentos

- [docs/Garantías.md](docs/GARANTIAS.md) — que garantiza este sistema y que no,
  separando lo probado de lo supuesto. Es el documento que hay que leer antes de
  decir que esto está en producción.
- [docs/FAMILIAS_DE_FALLO.md](docs/FAMILIAS_DE_FALLO.md) — las once formas en
  que este sistema se rompe sin ponerse rojo, con sus casos reales y la regla
  que cierra cada una. Es el resumen útil de tres días de auditoría.

| | |
|---|---|
| [`docs/OPERACION.md`](docs/OPERACION.md) | **Que vigilar ahora que el sistema corre: relojes, fallos silenciosos, deuda por país** |
| [`docs/AUDITORIA.md`](docs/AUDITORIA.md) | **La auditoría del 25 y 26 de agosto: los 27 hallazgos, con evidencia y criterio de aceptación** |
| [`docs/CLEAN_CODE.md`](docs/CLEAN_CODE.md) | Las reglas de código del proyecto, con el caso real que justifica cada una |
| [`docs/PUESTA_EN_MARCHA.md`](docs/PUESTA_EN_MARCHA.md) | Los pasos de arranque, por si hay que repetirlos |
| [`ESPECIFICACION.md`](ESPECIFICACION.md) | Espec técnica v0.10 |
| [`VERIFICACIONES.md`](VERIFICACIONES.md) | Como se verifico cada fuente, con evidencia |
| [`docs/PUBLICAR_ACTIVO.md`](docs/PUBLICAR_ACTIVO.md) | Publicar el activo y por que no va en git |
| [`DISCLAIMER.md`](DISCLAIMER.md) | Que informa y que no informa el sistema |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | Como contribuir, rol de mantenedor por país |
| [`GOVERNANCE.md`](GOVERNANCE.md) | Roles, decisiones, frontera comunidad ↔ empresa |
| [`LICENSES/`](LICENSES/) | La regla de los tres cubos |
