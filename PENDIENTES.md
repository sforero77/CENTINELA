# Pendientes y hoja de ruta

Estado al **24 de agosto de 2026**, el dia que el sistema se encendio. Este
documento es el traspaso: que queda por hacer, quien puede hacerlo, y en que
orden.

Ya no hay pasos bloqueados por permisos: la puesta en marcha se completo (§1) y
**todo lo que queda es codigo, abordable desde un clon**. Para vigilar el
sistema ya operando, la referencia es
[`docs/OPERACION.md`](docs/OPERACION.md).

---

## 0. Donde estamos

El sistema **funciona de punta a punta y corre solo**:

```bash
centinela impact us6000tjl2   --detail-url "https://earthquake.usgs.gov/fdsnws/event/1/query?eventid=us6000tjl2&format=geojson"   --exposure data/build/exposure_h3.parquet --manifest col-v0.5
# 24,7 s -> 2.415.793 personas en MMI>=7, reporte publicado en reports/
```

| Componente | Estado |
|---|---|
| P1 trigger (feed, filtro, dedupe, estado) | ✅ operando, y publicando su latido |
| Visor y `/status` publicados | ✅ https://sforero77.github.io/CENTINELA/ |
| P0 activo de exposicion (descarga → parquet) | ✅ **publicado en 18 de 19 paises** |
| P2 impacto (contornos → celdas → GF → join) | ✅ funcional, con reintento por pais |
| P3 reporte (json, md, csv, hilo, 2 mapas, malla, contornos) | ✅ funcional |
| **Catalogo historico** | ✅ **21 reportes en 15 paises** |
| Asserts de calidad §6.4, en P0 y en P2 | ✅ funcional |
| Toponimos en espanol (RF-06) y changelog de deltas (RF-04) | ✅ funcional |
| Golden G1 (Chocó), G2 (Venezuela) y G3 | ✅ corren, ninguna saltada |
| Activo de Brasil | ⏳ en curso · §2.1 |
| Coropletas r7/r6 del visor | ⏳ §2.2 |
| P4 brigada de imagen | ⏳ Fase 2, solo contrato |

**686 pruebas** sin red (mas 8 nocturnas contra las fuentes vivas), ninguna
saltada, `ruff` y `mypy --strict` limpios, arranque verificado desde clon vacio.
Medido el 26-ago-2026. Eran 431 antes de la auditoria y 523 al empezarla.

**El cron declara `*/10` y no corre cada diez minutos.** Medido sobre 22
corridas: mediana 45,7 min, maximo 73,3. La demora la pone la cola de GitHub y
no el intervalo, asi que subir la frecuencia no arregla nada — ver
[`docs/OPERACION.md`](docs/OPERACION.md) §1.

### El cero silencioso que casi se publica

`build_country` cerraba sin construir tres capas. Edificaciones y vias tenian
el selector de ficheros de Overture escrito y probado, pero **nadie lo
llamaba**; el desglose etario tampoco se descargaba, porque su url apunta a un
directorio de 62 rasters y la descarga caia en la rama "sin estrategia". Las
cifras del backtest del Chocó salieron de orquestar esas piezas a mano.

Nada fallaba. `ensure_layer_tables` crea vacia la tabla de una capa ausente, el
`LEFT JOIN` la convierte en ceros y el activo se escribe; el assert de §6.4
solo mira poblacion, asi que pasaba. La proxima corrida de
`exposure_quarterly.yml` habria reemplazado el activo bueno por uno con **cero
edificaciones, cero kilometros de via y cero adultos mayores**, publicado como
Release, en silencio.

Cerrado en tres piezas: el cableado de las capas que faltaban,
`validate_layer_coverage` —que detiene el build si cualquier capa requerida
suma cero en todo el pais— y las pruebas nocturnas contra Overture y WorldPop,
que avisan cuando el contrato de la fuente se mueve en vez de esperar al
trimestre.

### Lo que impide cerrar Fase 0

La puerta de salida de la espec pide cuatro cosas:

| Requisito | Estado |
|---|---|
| G1 verde | ✅ |
| G2 verde | ✅ cerrado el 24-ago-2026: los dos mainshocks reconstruidos, cifras congeladas |
| Un reporte real publicado end-to-end **sin intervencion** | ⏳ falta que ocurra un sismo |
| Latencia medida y publicada | ⏳ falta que ocurra un sismo |

**Las dos que quedan esperan lo mismo, y hasta el 25-ago no era asi.** La de
latencia estaba bloqueada por un bug, no por la sismicidad: `impact.yml`
publicaba `events/` y `reports/` y **no** `site/status.json`, de modo que el
sistema calculaba la latencia correctamente y no la publicaba nunca. Un `git
add` incompleto llevaba semanas haciendo pasar por «esperando un sismo» algo que
no dependia de ningun sismo.

Cerrado eso, las dos las cierra el primer M≥5,5 en LATAM. El camino esta probado
sobre 21 eventos historicos en 15 paises: cuando ocurra, lo unico manual sera
publicar el hilo.

---

## 1. ✅ La puesta en marcha, hecha el 24-ago-2026

Los cinco pasos que desbloqueaban la operacion estan cerrados. Se dejan
anotados porque son el registro de que el sistema arranco, y porque hay que
rehacerlos si alguna vez se migra el repositorio.

| | Paso | Resultado |
|---|---|---|
| 1.1 | Fusionar el PR #1 | `main` = `e67390c`, 100 archivos, CI en verde |
| 1.2 | Publicar el activo | `exposure_quarterly.yml`, que construye y publica en un paso |
| 1.3 | Habilitar Pages | https://sforero77.github.io/CENTINELA/ sirviendo visor, `/status` y reportes |
| 1.4 | Monitor externo | `HEALTHCHECK_URL` guardado como secreto |
| 1.5 | Probar el circuito | Trigger contra el feed vivo (18 sismos revisados, 0 relevantes) y simulacro, ambos verdes |

**El repositorio paso a publico** en el mismo movimiento. No fue solo para que
Pages fuera gratis: un sistema cuyo objetivo declarado es servir de insumo
abierto a la UNGRD y a pares regionales, con rol de mantenedor por pais y guarda
anti-fork en los workflows, no puede vivir en privado.

**A partir de aqui la referencia es
[`docs/OPERACION.md`](docs/OPERACION.md)**: que vigilar, que caduca solo, y que
esperar del primer sismo real. El procedimiento de arranque, por si hay que
repetirlo, sigue en
[`docs/PUESTA_EN_MARCHA.md`](docs/PUESTA_EN_MARCHA.md).

---

## 2. Lo que falta

Ordenado por lo que mas desbloquea. Lo ya cerrado esta en §3, en una linea cada
cosa, porque este documento es la lista de trabajo y no el registro de lo hecho.

### 2.1 Brasil, el pais 19

Es el unico de los diecinueve sin activo, y no por falta de intento: fallo dos
veces, el 25 y el 26 de agosto. **La causa esta confirmada y arreglada; falta
volver a lanzarlo.**

**Brasil es el pais mas caro con diferencia:**

| | Colombia | Brasil |
|---|---|---|
| Teselas GHS-POP | 9 | **36** |
| Serie age-sex de WorldPop | ~600 MB | **9,1 GB** (20 rasters de 453 MB) |
| Celdas H3 con poblacion | 519.735 | **4.293.218** |

**Lo que dice el log de la corrida del 25-ago**, que fallo tras 1 h 43 m:

| | |
|---|---|
| 00:59 · 01:02 | GHS-POP y GHS-BUILT-S descargados (437 MB) |
| 02:26 | WorldPop age-sex descargado — los 9,1 GB, en 90 min |
| 02:36 | HDX descargado. **Todo bajado, sin un fallo** |
| 02:38 | Poblacion agregada a H3: 4.293.218 celdas, 401 M habitantes |
| **02:39** | `The runner has received a shutdown signal` |

O sea que **no fallo la descarga ni el timeout** —quedaban 16 minutos de los
120— sino que el runner se murio durante el computo, tres minutos despues de
terminar de bajar.

**Era la memoria, y costo tres diagnosticos llegar.** La segunda corrida, con
300 minutos en vez de 120, murio **en el mismo sitio**: 4.293.218 celdas,
401.451.273 habitantes, y treinta y ocho segundos despues el mismo mensaje. La
anterior tardo 36. Determinista, con 194 minutos de margen sin usar.

Justo despues de `pop_h3` viene `pop_alt_h3` — el WorldPop **total** del pais, un
unico fichero— y `raster_to_arrow` hacia `src.read(1)`, que trae la banda entera
a memoria. Eso es lineal en el area:

| Pais | Pixeles | Banda + mascara en RAM | ¿Construye? |
|---|---|---|---|
| Colombia | 0,39 G | 1,9 GB | ✅ |
| Mexico | 0,86 G | 4,3 GB | ✅ |
| **Brasil** | **2,57 G** | **12,8 GB** | ❌ |

Un runner de GitHub tiene **16 GB**. No habia forma de que Brasil cupiera.

**Cerrado leyendo por ventanas de filas** (`raster_blocks_to_arrow`): el pico
deja de depender del pais —son los mismos ~128 MB para Colombia que para
Brasil— y de paso abarata los diecisiete restantes. Una prueba comprueba sobre
el AST que ninguna lectura vuelva a ser sin `window`, y otra que partir en
bloques no mueva un solo pixel: `filas` es relativa a la ventana y sin sumarle
el origen cada bloque caeria sobre el anterior.

**Los dos arreglos anteriores se quedan**, aunque no fueran el bloqueo:
`--liberar-rasters` en CI, que evita tener 9,6 GB de rasters puestos cuando
DuckDB derrama; el `timeout-minutes` en 300; y el registro del **disco libre**
en cada paso, que es lo que faltaba para no tener que deducir esto tres veces
—el mensaje con que GitHub mata un runner sin recursos no distingue disco de
memoria.

**Queda volver a lanzarlo:**

    gh workflow run exposure_quarterly.yml -f iso3=BRA

**Y aunque se construya, Brasil no puede producir un reporte** con el pipeline
actual. Sus doce sismos M≥5,5 desde 2000 estan entre 534 y 603 km de
profundidad, y USGS no publica contornos MMI para ninguno. Se construye por
preparacion —un somero raro en la costa cambiaria eso en un dia— no para obtener
un backtest.

### 2.2 Coropletas r7/r6 del visor

**Hecho el 24-ago-2026:** el mapa ya dibuja. El fondo salio primero de las
PMTiles que Overture publica por release y **se cambio a OpenFreeMap (estilo
Positron)** el mismo dia: una tesela de Overture a zoom 4 pesa 4,3 MB y no trae
una sola etiqueta; una de OpenFreeMap a zoom 6 pesa 101 KB y trae toponimos,
vias y agua. Sigue sin llaves ni cuota (D6). Ya no hay `OVERTURE_RELEASE` en
`site/assets/app.js` y no hay nada que subir cada trimestre por el lado del
mapa base.

**Falta:** las coropletas r7/r6 de exposicion e impacto. Son datos nuestros y
necesitan `tippecanoe`, y son la ultima pieza de RF-09 — el resto del visor
(lista de eventos, ficha municipal, descargas, malla por celda, area de
afectacion y filtro por pais) ya funciona.

### 2.3 Simbologia del visor · quedan dos cosas

Hecho: la rampa de intensidad del visor es ya la misma que la del mapa estatico
—se habia introducido la de ShakeMap sin ver que el proyecto tenia una decidida
y argumentada, y el mismo evento salia de dos colores segun donde se mirara—, la
leyenda se construye con las clases que trae el evento en vez de rotular siempre
las seis, el epicentro es una estrella en vez de un circulo proporcional que se
leia como radio de afectacion, y `salud` y `edu` son capas del selector: estaban
en `celdas.json` desde el principio y solo se veian abriendo celda por celda.

**Falta:**

* A zoom continental, dos eventos del mismo dia a 150 km comparten sitio y
  MapLibre oculta una de las dos etiquetas. Se ve en los dos de Venezuela.
* Los cortes de `salud` y `edu` estan medidos sobre 1.691 celdas de tres eventos
  en dos paises. Cuando entre un pais con mas equipamiento mapeado hay que
  volver a medirlos, igual que se hizo con los de poblacion y vias.

### 2.4 Los paises que quedan por medir

Los **19 manifests estan escritos** y sus cajas envolventes medidas sobre
`division_area` de Overture con un solo criterio. Por pais ya no hace falta
buscar datos: hace falta **construir y medir**, mas un mantenedor que valide los
toponimos.

Lo que cada pais nuevo necesita, en orden:

1. `uv run centinela country <ISO3>` — unos 800 MB y una hora larga por pais.
2. Anotar `medido_ghs_pop` en su manifest y **ajustar `tolerancia_pct`**.
   Hecho ya para los dieciocho construidos: `centinela calibrar` las estrecho
   con lo medido y hoy van de 0,59 % (Paraguay) a 5,44 % (Venezuela). Brasil
   sigue con el 5 % provisional porque es el unico sin construir — su manifest
   lleva 25 % y no tiene `medido_ghs_pop`.
3. Validar los toponimos. (La codificacion de Venezuela estaba anotada como
   rota —«Falc?n»— y **no lo esta**: era la consola de Windows. Verificado
   byte a byte sobre el parquet publicado.)
4. Publicar el activo como Release.

Ojo con el coste de las cajas insulares: Chile llega a 109,7°O por Rapa Nui,
Mexico a 118,6°O por Guadalupe y Revillagigedo, Ecuador a 92,3°O por Galapagos.
Son muchas teselas de GHS-POP por poca poblacion, pero el sistema no puede
decidir que una isla habitada no cuenta.

### 2.5 T0.7: benchmark de `exactextract` · bajo esfuerzo

Comparar el muestreo actual (suma de pixeles por celda) contra `exactextract`.
Criterio de la espec: menos de 1 % de diferencia en la poblacion nacional. Si
cumple, se documenta y se cierra; si no, se cambia el metodo.

### 2.6 Deuda menor

- `data/manifests/COL.yaml` tiene los `sha256` vacios. Se llenan solos en la
  primera corrida de `make country`, que devuelve el inventario con hashes.
- `overture_divisions` esta declarado en `COL.yaml` y no se usa: la geometria
  sale del MGN. No cuesta nada (las fuentes `s3://` no se descargan) pero
  induce a pensar que participa.
- **T0.10**: la referencia de poblacion del DANE es la cifra redondeada de su
  nota tecnica (53.000.000). Sustituirla por el valor exacto del anexo en Excel
  haria que el assert compare contra un numero y no contra un redondeo.
- `admin_lookup` guarda el centroide como WKT en texto. Funciona, pero
  `GEOMETRY` seria mas limpio.
- **Ortografia del generador de reportes.** El visor se acentuo entero en la
  auditoria de UX/UI; `pipelines/p3_report/` sigue escribiendo sin tildes
  ("Exposicion estimada", "Municipios mas expuestos"). Solo se corrigio ahi una
  palabra: decia "65 anos o mas", que no es lo mismo que "65 años o mas" y salia
  en un documento publico. Acentuar el resto cambia todos los `report.md` ya
  emitidos y es una decision editorial, no una correccion tecnica: esta sin
  tomar.
- **El mapa base tarda 8-10 s en pintar teselas desde frio.** Ninguna cifra
  depende de ellas y el tablero es usable antes, pero la primera pantalla se
  siente lenta. Precargar el estilo o servir un encuadre estatico mientras
  llegan las teselas son las dos salidas obvias.
- Las etiquetas largas del mapa estatico se pisan entre si: la separacion minima
  es de 0,25° y "Ocumare De La Costa De Oro" mide bastante mas.

---

### 2.7 Haiti no existe en este proyecto

**No tiene manifiesto, no estaba en esta lista, y no aparecia en la auditoria.**
Se cayo de la lista de los veinte en algun momento y nadie lo noto — yo tampoco,
en toda la auditoria del 25-ago.

Y es la omision mas grave posible en esta region. Puerto Principe 2010, M7,0:
entre 100.000 y 300.000 muertos, el terremoto mas letal de la historia de
America. Nippes 2021, M7,2: 2.200 mas. Haiti esta sobre la falla de
Enriquillo-Plantain Garden y comparte isla con Republica Dominicana, que **si**
tenemos. Un sistema de exposicion sismica para LATAM que cubre la mitad de La
Espanola es dificil de defender.

Hace falta `data/manifests/HTI.yaml` y una corrida de `exposure_quarterly`.

---

## 3. Cerrado, y donde esta el detalle

Lo que este documento listaba como pendiente y ya no lo esta. Cada linea tiene
su historia completa —evidencia, criterio de aceptacion y como se cerro— en
[`docs/AUDITORIA.md`](docs/AUDITORIA.md); aqui solo quedan los titulares para
que nadie lo vuelva a abrir por costumbre.

**Cerrado el 24-ago-2026**

- La ventana del disparador cortaba territorio de Mexico, Chile y Brasil.
- El impacto usaba el activo de Colombia para toda LATAM.
- G2: los dos mainshocks de Venezuela, publicados.
- RF-03: el reporte preliminar sin ShakeMap, que estaba escrito y sin llamador.

**Cerrado el 25-ago-2026, en la auditoria** — A1 a A21

- El latido de `/status` no se publicaba nunca, y la latencia se calculaba sin
  guardarse: dos requisitos de Fase 0 bloqueados por un `git add`.
- El trimestral reconstruia un pais de dieciocho.
- El README publicaba cifras de un activo anterior; los km de via, por un
  factor de seis.
- `cli.py`, `raster_h3.py` y `celdas.py` no tenian ni una prueba.
- Los asserts de §6.4 no corrian en P2, y la licencia de la fuente no se
  contrastaba nunca.
- RF-04 renderizaba un changelog que nadie calculaba.
- Un PROJ del sistema —el que instala PostGIS— dejaba inservible el pipeline geo.
- Chile no habria tenido reporte nunca: su caja mide 1.719 grados cuadrados por
  Rapa Nui y un sismo en Coquimbo se ordenaba como argentino.
- El 44 % de los sismos reales no llega a MMI≥7 sobre poblacion, y el producto
  entero titulaba con MMI≥7. Tehuantepec salia con «0 personas».
- Los toponimos salian en ingles, incumpliendo RF-06.

**Cerrado el 26-ago-2026, auditando el visor** — A22 a A27

- El mapa se quedaba en blanco al abrir un enlace compartido con la cache fria.
- Los epicentros no se dibujaban: el mismo fallo, en un segundo sitio.
- El epicentro se salia del encuadre en los sismos mar adentro.
- La celda no se podia citar: el indice H3 no llegaba a la ficha.
- El tablero enseñaba la exposicion y la llamaba afectacion; los contornos del
  ShakeMap se descargaban en cada evento y se tiraban.

---

### 3.x Sismos vistos y no despachados · cerrado el 26-ago-2026

El caso que lo motivo fue real: un **M4,9 a 160 km bajo Jordan, Santander**, el
26-ago a las 16:45 UTC, sentido en media Colombia. El sistema lo vio a las
16:57:38 —**doce minutos y cuarenta y un segundos despues**— lo evaluo, y
decidio bien: `M4.9 < umbral M5.5`.

Pero esa decision solo existia en un log de CI. Desde el visor, **«lo vi y es
inofensivo» y «estoy roto» se veian exactamente igual**. Un vigia que no puede
demostrar que estuvo mirando no se distingue de uno apagado.

**El umbral no se toco.** M5.5 sigue siendo lo que dispara un reporte. Lo que
cambia es que por debajo se *registra* en vez de *olvidar*: `site/observados.json`,
ventana movil de **5 dias**, y una capa gris apagable en el visor.

Tres reglas lo sostienen, y cada una tiene pruebas:

1. **Esquema aparte, no un reporte degradado.** `EventoObservado` no tiene un
   solo campo de impacto, y una prueba lo comprueba campo por campo. Publicar
   `pop_mmi7p: 0` seria un falso negativo con aspecto de dato: ausencia de
   medicion no es medicion de cero.
2. **Peso visual de «esto no es una alarma».** Gris fuera de la rampa de MMI,
   hueco, pequeno, sin etiqueta, sin halo, y apagado de entrada. La rampa
   significa «impacto medido»; prestarsela lo vaciaria de sentido — es el riesgo
   §7 en su forma visual.
3. **Solo LATAM, y caduca.** Los feeds del USGS son mundiales: sin filtro, la
   capa seria un sismografo global. Se registran solo los sismos que el filtro
   descarto **unicamente por tamano**, preguntandole otra vez con el umbral en
   cero.

Medido antes de decidir: **277 sismos M4,5-5,5 en LATAM en 90 dias** (~3,1/dia,
~15 puntos a la vez con la ventana de 5 dias) frente a 23 M≥5,5 — de los cuales
**los 23 tuvieron ShakeMap**, asi que el caso «pasa el umbral y no hay producto»
que RF-03 ya cubre por radios es raro de verdad.

**La ventana se rellena desde el historico.** Recien encendida solo sabia lo que
habia visto —un sismo— y su etiqueta decia «1 en 5 dias» cuando en LATAM habia
habido **nueve**. Un numero falso sobre el mundo es peor que no dar ninguno.
`centinela observados` reconstruye la ventana desde FDSN, que D7 reserva para
historicos: se llama a mano, no desde el cron. Sirve tambien de reparacion si el
vigia se cae mas de un dia, que es lo que cubre el feed en vivo.

**Rareza que se ve en el mapa:** `LATAM_BBOX` es un rectangulo, asi que se cuela
oceano abierto — en la primera ventana entro un M4,9 en la dorsal
medioatlantica. Es el mismo bbox que gobierna el despacho, asi que no se toca
aqui, pero explica un punto gris en medio del Atlantico.

**Limite conocido, escrito para no descubrirlo despues:** el piso real es
**M4,5**, porque es lo que dan `4.5_hour` y `4.5_day`. Un M4,2 superficial bajo
una ciudad hace mas dano que el M4,9 a 160 km de Jordan, y ese no se veria.
Bajar de 4,5 obliga a `all_hour` y multiplica el volumen; no se hace ahora.

---

### 3.y El visor llevaba 17 horas congelado · cerrado el 26-ago-2026

Salio de tirar del hilo de por que el M4,9 de Jordan no se veia. **Un push hecho
con `GITHUB_TOKEN` no dispara otros workflows** — regla de GitHub contra los
bucles infinitos.

`site.yml` escucha `push` sobre `site/**`, `reports/**` y `data/manifests/**`.
Los dos workflows que escriben ahi empujan con ese token. Resultado: el ultimo
despliegue del visor era de las **04:03**, con siete latidos posteriores ya
commiteados, y `/status` en vivo mostrando el de las **02:53**.

**Lo caro no era el latido.** P2 commitea `reports/` con el mismo token: **un
reporte de un sismo real se habria publicado en el repositorio sin llegar nunca
a la pagina**. No se habia notado porque ningun sismo habia llegado a reporte por
esa via — los veintiuno del catalogo se reconstruyeron a mano.

Los dos workflows en verde, el artefacto correcto en su sitio, y el fallo
viviendo en el hueco entre ellos: la misma forma que el resto de esta auditoria.

Cerrado con `gh workflow run site.yml` tras el push —`workflow_dispatch` es la
excepcion documentada a la regla, y es el mismo mecanismo con el que P1 ya
dispara P2— mas `actions: write` en los dos jobs. Sin PAT.

El guardia esta en `tests/unit/test_el_visor_se_republica.py`, y **deriva las
rutas del propio `site.yml`**: escritas a mano se quedan viejas, y un guardia con
la lista desactualizada da un verde peor que no tener guardia.

---

### 3.z El vigilante del vigilante · cerrado el 26-ago-2026

Lo pidio el usuario y es la regla del proyecto: **el sistema tiene que demostrar
que funciona por si mismo, no porque alguien note algo y pregunte.**

El visor congelado diecisiete horas salio a la luz porque una persona sintio un
sismo y fue a mirar. Eso no puede ser el mecanismo de deteccion de un sistema de
vigilancia.

`frescura.yml` corre cada tres horas, compara la pagina **publicada** contra el
repositorio y abre issue si se quedo atras. Detecta un desfase real como mucho
seis horas despues, frente a las diecisiete que costo la primera vez.

**Vigila una cosa sola**: que el repositorio avance y la pagina no. Si el vigia
muriera, los dos se quedarian quietos a la vez y esto pasaria — de eso se ocupa
el latido al monitor externo (§6.5). Son dos fallos distintos y merecen dos
alarmas distintas: una que no sabe decir cual se rompio obliga a investigar
desde cero.

El caso bueno **tambien se imprime**. Un vigilante callado cuando todo va bien
es indistinguible de uno apagado, que es como estaba el sistema esa manana.

---

## 4. Fases siguientes

**Fase 2 — Brigada de imagen.** T2.1, T2.2 y T2.3 cerradas el 24-ago-2026 con
las licencias citadas literalmente: Copernicus EMS permite reproducir, adaptar y
combinar sin restriccion comercial; Umbra y Capella publican SAR en CC BY 4.0
desde buckets sin credenciales.

Y el orden de la fase cambio. Buscando el GeoPackage de Cali aparecieron
evaluaciones de dano abiertas de **los dos sismos golden**, del Microsoft AI for
Good Lab y usando huellas de Overture — la misma fuente de este proyecto. Asi
que el primer hito no es entrenar un modelo, es **contrastar**, y ya esta hecho:
`centinela contraste` compara sobre las mismas celdas H3 y hay un workflow que
lo corre en CI. Medido, la cobertura del activo es completa en los dos eventos
y la fraccion danada va de 0,27 % a 3,69 %.

Queda T2.4: la rama de pesos limpia, que ya tiene de que alimentarse (EMS para
etiquetas, Umbra y Capella para imagen, todas CC BY) pero no esta construida.

**Fase 3 — Institucional.** T3.1 cerrada: AlphaEarth Foundations es CC-BY 4.0 y
puede agregarse al activo con su atribucion; Major TOM es CC-BY-SA 4.0 y no
puede sin arrastrar el cubo entero. El contrato de esquema declara la extension
y **ahora hay una prueba que lo compara contra el activo real**, porque no lo
miraba nadie y habia derivado.

Queda lo que no es codigo: presentar el sistema. Para eso esta
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
que trae Git for Windows. Los objetivos del Makefile son atajos de una linea,
asi que se corren sueltos:

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
una conexion lenta agota el tiempo de espera. `uv python install 3.12` por
separado deja el problema aislado y no hay que repetir el resto.

**Los extras importan.** `make setup` instala `[dev]`, pero el codigo geo
necesita `[geo]` y los mapas `[render]`:

```bash
uv sync --python 3.12 --extra dev --extra geo --extra render
```

Sin ellos las pruebas correspondientes **se saltan con razon explicita** en vez
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

Invariantes que costaron encontrar. Cada uno tiene su prueba de regresion, y
casi todos comparten forma: **producen una cifra plausible y equivocada**, que
es el unico modo de fallo que este sistema no puede permitirse.

**Una funcion escrita no es una funcion conectada.** Es la causa raiz de
veintitantos hallazgos de la auditoria, repetida: el latido, la latencia, los
asserts de §6.4, la licencia de la fuente, el changelog de RF-04, el enrutado
por pais, los epicentros del visor, los contornos del ShakeMap. **Todas estaban
probadas**, por eso la cobertura las daba por verdes: una prueba llama a la
funcion y eso no dice nada sobre si la llama alguien mas.
→ `tests/unit/test_funciones_conectadas.py`, sobre el grafo de llamadas

**Casi la mitad de los sismos reales no llega a MMI≥7 sobre poblacion.** Ocho de
los veintiuno del catalogo, y son los profundos y los de mar adentro, que en
esta region son la mitad. Fijar MMI≥7 como *la* banda publica «0 personas» para
ellos y ordena la tabla municipal por una columna de ceros.
→ `tests/unit/test_banda_titular.py`, `Totales.banda_titular`

**El area de afectacion no es el area de exposicion.** La malla H3 llega hasta
donde hay gente; los contornos del ShakeMap, hasta donde llego el sismo. En
Balao el area sentida mide cuatro veces mas que la cuantificada.
→ `tests/unit/test_contornos.py`

**Ordenar los paises candidatos por area de su caja no acierta siempre.** La de
Chile mide 1.719 grados cuadrados por Rapa Nui y la de Argentina 671, asi que un
sismo en Coquimbo sale como argentino. El desempate lo da el join, y por eso
hace falta poder reintentar con el siguiente candidato.
→ `tests/unit/test_enrutado_latam.py`, codigo de salida 3

**`preferredWeight` desempata contribuyentes, no versiones.** Ordenar por peso
elige un ShakeMap obsoleto sin que nada falle.
→ `tests/golden/test_g2_venezuela.py::test_no_se_elige_una_version_obsoleta`

**El rescate de celdas costeras necesita cota de distancia.** Sin ella reclama
el continente entero: la poblacion nacional paso de 52,6 a 167 millones.
→ `pipelines/p0_exposure/crosswalk.py`, constante `RESCUE_MAX_DEGREES`

**El catalogo STAC de Overture no sigue el estandar.** Publica 512 bboxes para
512 ficheros; el estandar pondria la union en `[0]`. Leerlo como manda el
estandar desplaza la seleccion un puesto y da resultados plausibles y erroneos.
→ `pipelines/p0_exposure/sources/overture.py::parse_collection`

**Dos copyleft distintos no caben en el mismo derivado.** ODbL y CC BY-SA 4.0
son ambas share-alike e incompatibles entre si.
→ `pipelines/common/licensing.py::resolve_bucket`

**WorldPop publica tres series de edad, no una.** El mismo directorio trae
`col_f_65`, `col_m_65` y la combinada `col_t_65`. Sumar todo lo que termina en
`.tif` cuenta a cada persona dos veces, y la cifra resultante sigue pareciendo
plausible.
→ `pipelines/p0_exposure/sources/worldpop.py`, solo la serie `_t_`

**La geometria de Overture llega tipada, no como BLOB.** La receta publicada
usa `ST_GeomFromWKB(geometry)` y aqui revienta con "no function matches",
porque el parquet declara `GEOMETRY('OGC:CRS84')`. Y cada tema particiona sus
ficheros por su cuenta: el `00013` de edificaciones y el de transporte cubren
areas distintas.
→ `pipelines/p0_exposure/overture_h3.py` · `tests/integration/test_overture_contract_live.py`

**Una capa vacia se publica como cero.** No hace falta un bug para llegar ahi:
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
la fuente de verdad del codigo DIVIPOLA; el COD-AB es el mismo MGN
reempaquetado. El empate se deshace por las columnas que el pais declara, no
por orden de llegada.
→ `pipelines/p0_exposure/build.py::pick_admin_source`

**La caja del pais se declara antes de poder medirla.** Es el unico dato del
pipeline que empieza siendo una afirmacion: hace falta *antes* de descargar el
limite administrativo. Una caja corta no falla — recorta teselas y ficheros, y
el activo sale con una punta del pais sin poblacion ni edificaciones. Cuadra
todo y falta territorio. Por eso el build la comprueba contra la geometria real
en cuanto la carga.
→ `pipelines/p0_exposure/build.py::validate_bbox_covers_country`

**Mas resolucion no es mas informacion.** El HRSL de Meta esta a 30 m frente a
los 100 m de GHS-POP, pero su vintage es 2019 y a celda r8 el detalle extra se
promedia. Cambiar seria regalar seis anos de vigencia a cambio de nada.
→ `VERIFICACIONES.md`, ronda 4

**Los plazos por defecto de DuckDB no sirven para leer Overture.**
`http_timeout` viene en 30 s y un fichero tarda minutos en conexion domestica.
Peor: la lectura de Overture va al final del build, asi que el timeout mata la
corrida con la hora de descargas ya pagada.
→ `pipelines/p0_exposure/overture_h3.py::HTTPFS_SETTINGS`

**Un build de un pais falla tarde, asi que reanudar tiene que ser barato.**
Son ~1 GB y el paso que mas falla es el ultimo. Las seis rutas de descarga
saltan lo que ya esta en disco, y escriben en `.parcial` para que un corte no
deje un raster truncado que la siguiente corrida de por bueno.
→ `pipelines/p0_exposure/download.py::write_atomic` · `_hdx_en_disco`

Y una regla de producto: **exposicion no es dano**. Todo artefacto sale con sus
disclaimers, y el hilo para redes se genera pero **no se publica solo**.

---

## 7. Documentos

| | |
|---|---|
| [`docs/OPERACION.md`](docs/OPERACION.md) | **Que vigilar ahora que el sistema corre: relojes, fallos silenciosos, deuda por pais** |
| [`docs/AUDITORIA.md`](docs/AUDITORIA.md) | **La auditoria del 25 y 26 de agosto: los 27 hallazgos, con evidencia y criterio de aceptacion** |
| [`docs/CLEAN_CODE.md`](docs/CLEAN_CODE.md) | Las reglas de codigo del proyecto, con el caso real que justifica cada una |
| [`docs/PUESTA_EN_MARCHA.md`](docs/PUESTA_EN_MARCHA.md) | Los pasos de arranque, por si hay que repetirlos |
| [`ESPECIFICACION.md`](ESPECIFICACION.md) | Espec tecnica v0.10 |
| [`VERIFICACIONES.md`](VERIFICACIONES.md) | Como se verifico cada fuente, con evidencia |
| [`docs/PUBLICAR_ACTIVO.md`](docs/PUBLICAR_ACTIVO.md) | Publicar el activo y por que no va en git |
| [`DISCLAIMER.md`](DISCLAIMER.md) | Que informa y que no informa el sistema |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | Como contribuir, rol de mantenedor por pais |
| [`GOVERNANCE.md`](GOVERNANCE.md) | Roles, decisiones, frontera comunidad ↔ empresa |
| [`LICENSES/`](LICENSES/) | La regla de los tres cubos |
