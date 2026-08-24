# Operacion

El sistema **ya esta operando**. Este documento es lo que hay que vigilar a
partir de ahora, ordenado por lo que mas dano hace si se descuida.

La idea rectora: en un sistema que puede pasar meses sin trabajo, **el fallo
peligroso no es el que rompe, es el que calla**. Casi todo lo que sigue existe
para detectar cosas que no producen ningun error.

---

## 1. Los cuatro relojes

Cuatro cosas caducan solas, sin avisar. Estan por orden de cercania.

| Cada | Que caduca | Que pasa si se pasa | Quien avisa |
|---|---|---|---|
| **~2 meses** | El release de Overture fijado en los manifests | `make country` deja de poder reconstruir: Overture solo conserva **dos** releases y la URL desaparece | La prueba nocturna de contrato abre un issue |
| **60 dias** | Los workflows programados, si no hay actividad en el repo | El trigger **deja de mirar**, en silencio. Es el modo de falla mas probable del proyecto | `keepalive.yml` late el dia 1 y el 15; healthchecks.io avisa si aun asi se cae |
| **Trimestral** | El activo de exposicion | Los datos envejecen; no falla nada | `exposure_quarterly.yml` lo reconstruye solo |
| **Anual** | Las epocas de GHS-POP y WorldPop | Las cifras se alejan de la realidad | Nadie. Revisar a mano si sale un release nuevo |

**El reloj que no es un reloj: el cron.** `trigger.yml` declara `*/10` y no
corre cada diez minutos. Medido el 24-ago-2026 sobre 22 corridas programadas en
dieciseis horas seguidas:

| | Minutos entre corridas |
|---|---|
| Declarado | 10 |
| Real | min **25,0** · mediana **45,7** · p90 **56,9** · max **73,3** |

Entre cuatro y siete veces lo declarado, y peor que el rango de 5-30 min que
documenta GitHub. Importa porque el objetivo es p50 ≤ 60 min desde el origen del
sismo hasta el reporte publicado: **la deteccion sola puede comerse la mitad del
presupuesto, y en el peor caso todo**.

Subir la frecuencia del cron no arregla nada — la demora la pone la cola de
GitHub, no el intervalo. Las salidas reales son dos, y las dos son decisiones de
quien opera, no del codigo:

1. **Cron externo** que dispare `repository_dispatch`. Es la ruta limpia y ya
   estaba anotada como upgrade path. Necesita un servicio fuera de GitHub.
2. **Aceptar el objetivo como esta** y medirlo con el primer sismo real, que es
   lo unico que dira si la cola se comporta distinto a las horas en punto.

Mientras tanto el feed de respaldo `4.5_day` cubre la demora sin perder eventos:
se detecta tarde, pero no se pierde nada.

**El release de Overture es el mas urgente y el menos obvio.** Cuando la prueba
nocturna abra el issue, hay que actualizar el `vintage` en los manifests de los
paises construidos. No corre prisa para *operar* —el activo publicado sigue
sirviendo— pero si para *reconstruir*.

---

## 2. Que revisar y cada cuanto

### Semanal, un minuto

```bash
gh run list --limit 10          # nada en rojo
```

Mira sobre todo que el **trigger siga corriendo cada 10 minutos**. Si dejo de
aparecer, el cron se desactivo.

### Ante un issue automatico

El sistema abre issues solo. Cada etiqueta significa algo distinto:

| Etiqueta | Que paso | Urgencia |
|---|---|---|
| `contrato` | Una fuente cambio de forma: USGS, Overture o WorldPop | Antes del proximo sismo |
| `pipeline` | P2 fallo procesando un evento **real** | Inmediata: hay un sismo sin reporte |

### Cuando llegue el primer sismo M≥5.5 en LATAM

Es lo que cierra Fase 0. Que esperar:

1. El trigger lo detecta en la siguiente corrida (≤10 min, mas la demora del
   cron de GitHub, que su documentacion situa entre 5 y 30 min).
2. `impact.yml` baja el activo del Release y calcula.
3. Aparece `reports/<usgs_id>/` con json, md, csv, dos mapas y el hilo.
4. `site.yml` publica el visor actualizado.
5. `/status` empieza a mostrar latencia real.

**Lo unico manual de todo el sistema:** publicar el hilo de
`reports/<id>/hilo.txt` en redes. Se genera solo y **no se publica solo**, a
proposito.

Y lo primero que hay que mirar del reporte no es la cifra grande: es si hay
`construido_no_mapeado` en las banderas. Significa que el satelite ve
edificacion donde OSM no mapeo nada, o sea que el conteo de edificaciones se
queda corto justo donde vive la poblacion mas expuesta.

---

## 3. Lo que puede salir mal y no lo parece

Diez cosas que producen cifras plausibles y equivocadas. Cada una tiene ya su
guardia; estan aqui para que se reconozcan si alguna vez fallan.

**Una capa vacia se publica como cero.** No hace falta un bug: basta con no
cablear la capa. `validate_layer_coverage` detiene el build si cualquier capa
requerida suma cero en todo el pais.

**Dos fuentes de lo mismo cuentan doble.** HOTOSM y healthsites.io derivan las
dos de OSM: el 96,6 % de los puntos de la segunda son la misma sede. La
deduplicacion por proximidad (20 m) esta en `aggregate_points_to_h3`, y el
orden del manifest importa — la principal va primera.

**Una caja envolvente corta pierde territorio en silencio.** Recorta teselas y
ficheros, y el activo sale con una punta del pais sin poblacion. Cuadra todo.
`validate_bbox_covers_country` lo comprueba en cuanto carga la geometria.

**Un dataset de HDX puede publicar varios recursos del mismo formato.** El
COD-AB de Colombia publica cuatro SHP y el primero son secciones urbanas. Por
eso existe `hdx_resource`. De los 19 paises, solo Colombia lo necesita.

**Un activo viejo con el codigo nuevo.** Entre actualizar el codigo y
republicar el activo hay una ventana. La vista de exposicion rellena las
columnas que falten para que el reporte salga igual, con una **ausencia** y no
un cero.

**El rescate de frontera reclamaba gente del pais vecino.** Fue el origen del
sesgo de poblacion: en Paraguay el 6,1 % del total entraba por celdas rescatadas
y explicaba el 93 % de su desvio frente a la ONU.

**La magnitud no es la senal.** Chile rescata el **31 %** de su poblacion y su
cifra es correcta, porque su rescate es mar: sin el perderia 6,1 millones de
personas. Lo que distingue lo correcto de lo contaminado no es cuanto se rescata
sino **sobre que esta la celda** — agua, o tierra de otro pais. Corregido
cargando los poligonos de los paises limitrofes desde Overture y excluyendo las
celdas que caen dentro de ellos.

Si Overture no responde, el rescate degrada al comportamiento anterior en vez de
tumbar el build: correcto para una isla, generoso para un pais con frontera
terrestre. El log lo dice — y **hay que mirarlo**, porque el primer intento de
este arreglo cargo cero poligonos y siguio adelante sin quejarse. La linea
`paises vecinos cargados` publica el embudo entero: candidatas, junto al pais,
descartadas por vecino. Cero vecinos es ahora un WARNING: en LATAM solo Cuba no
toca a nadie por tierra, y hasta su caja alcanza a Haiti.

**Solo cuenta la tierra del vecino, no su mar.** Overture publica dos poligonos
por pais —`is_land` e `is_territorial`— y cargar los dos rompe el caso costero:
las aguas peruanas llegan hasta la frontera de Arica, asi que una celda del
Pacifico frente a Chile caeria "dentro de Peru".

**Una tolerancia ancha no vigila nada.** Las de los diecinueve manifests se
fijaron para acomodar desvios que resultaron ser el fallo del rescate: la de
Paraguay estaba en 7,5 % y su desvio real es +0,035 %. `centinela calibrar` las
estrecha con lo que midio el ultimo build. **Ensancharlas no es automatico**: si
el desvio se sale de la tolerancia vigente, el comando lo dice y no toca nada.
Aflojar la alarma para que deje de sonar es lo que uno hace con prisa, y lo que
no debe automatizarse.

**Una funcion escrita no es una funcion conectada.** El calculo del reporte
preliminar (RF-03) estaba escrito, comentado y probado, y no lo llamaba nadie:
el evento pasaba a estado `preliminar` y no se publicaba nada. Ninguna prueba lo
veia porque todas probaban la funcion, no el camino. Mismo patron que las tres
capas del activo que se agregaban a tablas que nadie leia. Cuando algo "ya esta
hecho", conviene comprobar quien lo llama.

**Un NaN pasa por donde un cero no pasa.** `bool(float('nan'))` es `True`, asi
que cualquier guardia escrita como `if not valor` lo deja pasar. Ecuador
publico un activo con `road_km: NaN` por eso, y bastaba **una** geometria
degenerada para envenenar el total del pais: la suma propaga el NaN a todo.
`validate_layer_coverage` comprueba ahora que el valor sea finito, no solo que
no sea cero, y la agregacion de vias descarta longitudes infinitas o mayores de
2.000 km.

**Un sismo fuera del pais del activo.** P1 vigila toda LATAM y el activo es por
pais. Si se calcula un sismo peruano contra celdas colombianas, el join no
encuentra nada y todas las cifras salen en cero — publicadas, durante un
terremoto. El activo se elige ahora por el epicentro, y `compute_impact` falla
si el join queda vacio. **Si ves un issue que dice "no hay activo de exposicion
publicado para X", eso es el sistema funcionando**: construye el pais con
`gh workflow run exposure_quarterly.yml -f iso3=X`.

---

## 4. Deuda por pais

Los 19 manifests estan escritos y sus fuentes verificadas, pero **solo Colombia
esta medida**. Lo que arrastra cada pais no construido:

- **`tolerancia_pct` es 5 % y es una expectativa, no una medicion.** Colombia,
  medida, usa 1 %. Al construir un pais hay que anotar `medido_ghs_pop` y
  ajustar la tolerancia, explicando el cambio en el PR.
- **Los toponimos hay que validarlos.** En Venezuela el COD-AB los devuelve mal
  codificados («Falc?n» por «Falcón») y esos nombres se imprimen en el reporte y
  en el hilo.
- **La referencia de poblacion puede mejorarse.** Todos usan World Population
  Prospects por uniformidad regional; un instituto nacional con censo reciente
  es mejor para su propio pais, como hace Colombia con el DANE.

Venezuela ademas tiene una advertencia propia: GHS-POP deriva de la ronda censal
de 2010 y no modela la emigracion posterior. **Que el assert de poblacion falle
ahi seria un hallazgo publicable, no un bug.**

---

## 5. Rutas: donde vive cada cosa

```
data/manifests/<ISO3>.yaml   Que version de que fuente entro al activo. Nunca "latest".
events/<usgs_id>.json        El estado del sistema. Es la base de datos, y esta en git.
reports/<usgs_id>/           Lo publicado: json, md, csv, 2 png, hilo.
site/                        El visor. Sin backend, sin llaves de API.
data/build/                  Efimero, NO va en git. Se pierde en cada clon.
```

**El activo de exposicion no esta en el repositorio.** Vive en los Releases
(`exposure-col-<fecha>`) porque pesa 17 MB por pais y crecera. Esa copia, con su
`sha256`, es la que sostiene la reproducibilidad — no la URL de origen, que
caduca.

Comandos:

```bash
uv run centinela trigger --dry-run      # P1 sin escribir estado
uv run centinela country COL            # reconstruir un pais (~1 GB)
uv run centinela lint-manifests         # licencias y vintages
uv run centinela status                 # recalcular site/status.json
```

En Windows no hay `make`; los objetivos del Makefile son atajos de una linea.

---

## 6. Lo que queda de Fase 0

| Requisito de la puerta de salida | Estado |
|---|---|
| G1 (Chocó) verde | ✅ |
| G2 (Venezuela) verde | ⚠️ falta el **reporte**: el activo ya existe, falta correr el backtest de los dos mainshocks |
| Un reporte real publicado sin intervencion | ⏳ lo cierra el primer sismo |
| Latencia medida y publicada | ⏳ idem |

Los dos ultimos no dependen de nadie: llegan con el primer M≥5.5 en la region.

Lo demas abierto, sin bloquear: **T0.7** (benchmark de `exactextract`),
**T0.10** (la cifra exacta del DANE en vez del redondeo), **PMTiles del visor**
(hoy el mapa esta vacio; las capas de contexto no hay que generarlas, Overture
publica las suyas) y **RF-03** (el reporte preliminar sin ShakeMap: se calcula
por radios pero no se emite).

Detalle y orden en [`PENDIENTES.md`](../PENDIENTES.md).
