# Operación

El sistema **ya esta operando**. Este documento es lo que hay que vigilar a
partir de ahora, ordenado por lo que más daño hace si se descuida.

La idea rectora: en un sistema que puede pasar meses sin trabajo, **el fallo
peligroso no es el que rompe, es el que calla**. Casi todo lo que sigue existe
para detectar cosas que no producen ningún error.

---

## 1. Los cuatro relojes

Cuatro cosas caducan solas, sin avisar. Están por orden de cercanía.

| Cada | Que caduca | Que pasa si se pasa | Quien avisa |
|---|---|---|---|
| **~2 meses** | El release de Overture fijado en los manifests | `make country` deja de poder reconstruir: Overture solo conserva **dos** releases y la URL desaparece | La prueba nocturna de contrato abre un issue |
| **60 días** | Los workflows programados, si no hay actividad en el repo | El trigger **deja de mirar**, en silencio. Es el modo de falla más probable del proyecto | `keepalive.yml` late el día 1 y el 15; healthchecks.io avisa si aun así se cae |
| **Trimestral** | El activo de exposición | Los datos envejecen; no falla nada | `exposure_quarterly.yml` lo reconstruye solo |
| **Anual** | Las épocas de GHS-POP y WorldPop | Las cifras se alejan de la realidad | Nadie. Revisar a mano si sale un release nuevo |

**El reloj que no es un reloj: el cron.** `trigger.yml` declaraba `*/10` y no
corría cada diez minutos. Medido el 24-ago-2026 sobre 22 corridas programadas en
dieciséis horas seguidas:

| | Minutos entre corridas |
|---|---|
| Declarado | 10 |
| Real | min **25,0** · mediana **45,7** · p90 **56,9** · max **73,3** |

Bajo a `*/30` el 27-ago-2026, cuando se vio que GitHub reparte unos pocos turnos
**por repositorio** y no uno por workflow. Vuelto a medir entre el 25 y el 30 de
agosto sobre 23 latidos: **p50 157 min · p90 462 · peor 766 (12,8 h)**. La cifra
que vale es esa; la tabla de arriba se conserva porque es la que explica por que
se bajo el intervalo.

Entre cuatro y siete veces lo declarado, y peor que el rango de 5-30 min que
documenta GitHub. Importa porque el objetivo es p50 ≤ 60 min desde el origen del
sismo hasta el reporte publicado: **la detección sola puede comerse la mitad del
presupuesto, y en el peor caso todo**.

Subir la frecuencia del cron no arregla nada — la demora la pone la cola de
GitHub, no el intervalo. Las salidas reales son dos, y las dos son decisiones de
quien opera, no del código:

1. **Cron externo** que dispare `repository_dispatch`. Es la ruta limpia y ya
   estaba anotada como upgrade path. Necesita un servicio fuera de GitHub.
2. **Aceptar el objetivo como esta** y medirlo con el primer sismo real, que es
   lo único que dirá si la cola se comporta distinto a las horas en punto.

Mientras tanto el feed de respaldo `4.5_day` cubre la demora sin perder eventos:
se detecta tarde, pero no se pierde nada.

**El release de Overture es el más urgente y el menos obvio.** Cuando la prueba
nocturna abra el issue, hay que actualizar el `vintage` en los manifests de los
países construidos. No corre prisa para *operar* —el activo publicado sigue
sirviendo— pero si para *reconstruir*.

---

## 2. Que revisar y cada cuanto

### Semanal, un minuto

```bash
gh run list --limit 10          # nada en rojo
```

Mira sobre todo que el **trigger siga latiendo**. Declara `*/30` y entrega mucho
menos; lo que importa es que no se pare del todo. Si dejó de
aparecer, el cron se desactivo.

### Ante un issue automático

El sistema abre issues solo. Cada etiqueta significa algo distinto:

| Etiqueta | Qué pasó | Urgencia |
|---|---|---|
| `contrato` | Una fuente cambio de forma: USGS, Overture o WorldPop | Antes del próximo sismo |
| `pipeline` | P2 fallo procesando un evento **real** | Inmediata: hay un sismo sin reporte |

### Cuando llegue el primer sismo M≥5.5 en LATAM

Es lo que cierra Fase 0. Que esperar:

1. El trigger lo detecta en la siguiente corrida (≤10 min, más la demora del
   cron de GitHub, que su documentación situa entre 5 y 30 min).
2. `impact.yml` baja el activo del Release y calcula.
3. Aparece `reports/<usgs_id>/` con json, md, csv, dos mapas y el hilo.
4. `site.yml` publica el visor actualizado.
5. `/status` empieza a mostrar latencia real.

**Lo único manual de todo el sistema:** publicar el hilo de
`reports/<id>/hilo.txt` en redes. Se genera solo y **no se publica solo**, a
propósito.

Y lo primero que hay que mirar del reporte no es la cifra grande: es si hay
`construido_no_mapeado` en las banderas. Significa que el satélite ve
edificación donde OSM no mapeo nada, o sea que el conteo de edificaciones se
queda corto justo donde vive la población más expuesta.

---

## 3. Lo que puede salir mal y no lo parece

Diez cosas que producen cifras plausibles y equivocadas. Cada una tiene ya su
guardia; están aquí para que se reconozcan si alguna vez fallan.

**Una capa vacía se publica como cero.** No hace falta un bug: basta con no
cablear la capa. `validate_layer_coverage` detiene el build si cualquier capa
requerida suma cero en todo el país.

**Dos fuentes de lo mismo cuentan doble.** HOTOSM y healthsites.io derivan las
dos de OSM: el 96,6 % de los puntos de la segunda son la misma sede. La
deduplicacion por proximidad (20 m) esta en `aggregate_points_to_h3`, y el
orden del manifest importa — la principal va primera.

**Una caja envolvente corta pierde territorio en silencio.** Recorta teselas y
ficheros, y el activo sale con una punta del país sin población. Cuadra todo.
`validate_bbox_covers_country` lo comprueba en cuanto carga la geometría.

**Un dataset de HDX puede publicar varios recursos del mismo formato.** El
COD-AB de Colombia publica cuatro SHP y el primero son secciones urbanas. Por
eso existe `hdx_resource`. De los 19 países, solo Colombia lo necesita.

**Un activo viejo con el código nuevo.** Entre actualizar el código y
republicar el activo hay una ventana. La vista de exposición rellena las
columnas que falten para que el reporte salga igual, con una **ausencia** y no
un cero.

**El rescate de frontera reclamaba gente del país vecino.** Fue el origen del
sesgo de población: en Paraguay el 6,1 % del total entraba por celdas rescatadas
y explicaba el 93 % de su desvío frente a la ONU.

**La magnitud no es la señal.** Chile rescata el **31 %** de su población y su
cifra es correcta, porque su rescate es mar: sin el perderia 6,1 millones de
personas. Lo que distingue lo correcto de lo contaminado no es cuanto se rescata
sino **sobre que esta la celda** — agua, o tierra de otro país. Corregido
cargando los polígonos de los países limitrofes desde Overture y excluyendo las
celdas que caen dentro de ellos.

Si Overture no responde, el rescate degrada al comportamiento anterior en vez de
tumbar el build: correcto para una isla, generoso para un país con frontera
terrestre. El log lo dice — y **hay que mirarlo**, porque el primer intento de
este arreglo cargo cero polígonos y siguio adelante sin quejarse. La línea
`paises vecinos cargados` publica el embudo entero: candidatas, junto al país,
descartadas por vecino. Cero vecinos es ahora un WARNING: en LATAM solo Cuba no
toca a nadie por tierra, y hasta su caja alcanza a Haití.

**Solo cuenta la tierra del vecino, no su mar.** Overture publica dos polígonos
por país —`is_land` e `is_territorial`— y cargar los dos rompe el caso costero:
las aguas peruanas llegan hasta la frontera de Arica, así que una celda del
Pacífico frente a Chile caería "dentro de Perú".

**Una tolerancia ancha no vigila nada.** Las de los diecinueve manifests se
fijaron para acomodar desvios que resultaron ser el fallo del rescate: la de
Paraguay estaba en 7,5 % y su desvío real es +0,035 %. `centinela calibrar` las
estrecha con lo que midió el último build. **Ensancharlas no es automático**: si
el desvío se sale de la tolerancia vigente, el comando lo dice y no toca nada.
Aflojar la alarma para que deje de sonar es lo que uno hace con prisa, y lo que
no debe automatizarse.

**Una función escrita no es una función conectada.** El cálculo del reporte
preliminar (RF-03) estaba escrito, comentado y probado, y no lo llamaba nadie:
el evento pasaba a estado `preliminar` y no se publicaba nada. Ninguna prueba lo
veia porque todas probaban la función, no el camino. Mismo patrón que las tres
capas del activo que se agregaban a tablas que nadie leia. Cuando algo "ya esta
hecho", conviene comprobar quien lo llama.

**Un NaN pasa por donde un cero no pasa.** `bool(float('nan'))` es `True`, así
que cualquier guardia escrita como `if not valor` lo deja pasar. Ecuador
publicó un activo con `road_km: NaN` por eso, y bastaba **una** geometría
degenerada para envenenar el total del país: la suma propaga el NaN a todo.
`validate_layer_coverage` comprueba ahora que el valor sea finito, no solo que
no sea cero, y la agregación de vías descarta longitudes infinitas o mayores de
2.000 km.

**Un sismo fuera del país del activo.** P1 vigila toda LATAM y el activo es por
país. Si se calcula un sismo peruano contra celdas colombianas, el join no
encuentra nada y todas las cifras salen en cero — publicadas, durante un
terremoto. El activo se elige ahora por el epicentro, y `compute_impact` falla
si el join queda vacío. **Si ves un issue que dice "no hay activo de exposición
publicado para X", eso es el sistema funcionando**: construye el país con
`gh workflow run exposure_quarterly.yml -f iso3=X`.

---

## 3.bis Re-emitir el catálogo cuando cambia el pipeline

Ha hecho falta tres veces: al arreglar la simbología del mapa estático, al
acentuar los textos y al corregir el corte de MMI de Ground Failure. Las tres
veces la pregunta fue la misma —«el código está bien, ¿y lo publicado?»— y las
tres veces la respuesta dependió de **qué artefacto** cambia.

| Qué cambió | Con qué se rehace | Cuesta |
|---|---|---|
| Simbología del PNG | `centinela regenerar-mapas` | Segundos, en local |
| Prosa del `.md` o del hilo | `centinela regenerar-textos` | Segundos, en local |
| **Cualquier cifra** | Volver a correr P2 por evento | Un despacho de `impact.yml` cada uno |

Los dos primeros son derivados del `report.json`, que ya está en el repositorio.
El tercero no: las cifras salen del join contra el activo de exposición del país,
que **no vive en git** —unos 19 MB por país— y se publica como Release. Por eso
no hay un `regenerar-cifras`: rehacerlas es correr el pipeline, no re-renderizar.

### Cómo se re-emite

`impact.yml` ya hace todo lo que hace falta: elige el país por el epicentro
probando los candidatos contra el join, descarga el Release de su activo, corre
P2/P3 y empuja con rebase —endurecido para empujes concurrentes desde el doble
mainshock de Venezuela—.

```bash
# Uno:
gh workflow run impact.yml -f usgs_id=us6000tjl2 -f backtest=true -f reprocesar=true

# El catálogo entero, uno por uno. `sleep` no por prudencia con el push —el
# workflow ya rebasa— sino para no encolar veintiún runners a la vez.
for ID in $(jq -r '.[].usgs_id' reports/index.json); do
  gh workflow run impact.yml -f usgs_id="$ID" -f backtest=true -f reprocesar=true
  sleep 20
done
```

`reprocesar=true` es obligatorio: sin él el pipeline no reemite nada, porque
USGS no ha publicado ninguna versión nueva del producto. `backtest=true` mantiene
los veintiuno fuera de la estadística de latencia, que es lo que ya son.

Cada corrida empuja a `main` y eso dispara `site.yml`, que republica la página.

### Qué comprobar después

```bash
uv run pytest tests/unit/test_el_csv_cuadra_con_el_reporte.py
```

Esa prueba lleva la lista `PENDIENTES_DE_REEMITIR` con los eventos cuyo
`adm2.csv` todavía arrastra el corte viejo. **Cada evento re-emitido hay que
sacarlo de la lista**, y hay una segunda prueba que falla si alguno ya cuadra y
sigue dentro — para que una excepción temporal no se vuelva permanente sin que
nadie lo decida. Cuando la lista quede vacía, la guardia es total.

---

## 4. Deuda por país

Los 19 manifests están escritos y sus fuentes verificadas, y **18 países están
construidos, publicados y medidos**. El único sin activo es **Brasil**.

- **Las tolerancias ya no son expectativas.** `centinela calibrar` las estrecho
  con lo que midió cada build: van de 0,59 % (Paraguay) a 5,44 % (Venezuela).
  Brasil conserva el 25 % provisional y no tiene `medido_ghs_pop`, porque no se
  ha construido. Al construirlo hay que anotar los dos, explicando el cambio en
  el PR.
- **Los topónimos hay que validarlos.** En Venezuela el COD-AB los devuelve mal
  codificados («Falc?n» por «Falcón») y esos nombres se imprimen en el reporte y
  en el hilo.
- **La referencia de población puede mejorarse.** Todos usan World Population
  Prospects por uniformidad regional; un instituto nacional con censo reciente
  es mejor para su propio país, como hace Colombia con el DANE.

Venezuela además tiene una advertencia propia: GHS-POP deriva de la ronda censal
de 2010 y no modela la emigración posterior. **Que el assert de población falle
ahí sería un hallazgo publicable, no un bug.**

---

## 5. Rutas: donde vive cada cosa

```
data/manifests/<ISO3>.yaml   Que version de que fuente entro al activo. Nunca "latest".
events/<usgs_id>.json        El estado del sistema. Es la base de datos, y esta en git.
reports/<usgs_id>/           Lo publicado: json, md, csv, 2 png, hilo.
site/                        El visor. Sin backend, sin llaves de API.
data/build/                  Efimero, NO va en git. Se pierde en cada clon.
```

**El activo de exposición no esta en el repositorio.** Vive en los Releases
(`exposure-col-<fecha>`) porque pesa 17 MB por país y crecera. Esa copia, con su
`sha256`, es la que sostiene la reproducibilidad — no la URL de origen, que
caduca.

Comandos:

```bash
uv run centinela trigger --dry-run      # P1 sin escribir estado
uv run centinela country COL            # reconstruir un pais (~1 GB)
uv run centinela lint-manifests         # licencias y vintages
uv run centinela status                 # recalcular site/status.json
```

En Windows no hay `make`; los objetivos del Makefile son atajos de una línea.

---

## 6. Lo que queda de Fase 0

| Requisito de la puerta de salida | Estado |
|---|---|
| G1 (Chocó) verde | ✅ |
| G2 (Venezuela) verde | ✅ cerrado el 24-ago-2026 |
| Un reporte real publicado sin intervención | ⏳ lo cierra el primer sismo |
| Latencia medida y publicada | ⏳ ídem |

Los dos últimos no dependen de nadie: llegan con el primer M≥5.5 en la región.

Lo demás abierto, sin bloquear: **T0.7** (benchmark de `exactextract`),
**T0.10** (la cifra exacta del DANE en vez del redondeo), las **coropletas
r7/r6 del visor** en PMTiles —el mapa base y la malla por celda ya dibujan; lo
que falta son las teselas propias, que si necesitan `tippecanoe`— y el **activo
de Brasil**.

**RF-03 y RF-04 están cerradas.** El reporte preliminar sin ShakeMap se emite
desde el 24-ago-2026, y el changelog de deltas al re-emitir por una versión
nueva, desde el 25-ago. Las dos estaban escritas y sin conectar.

Detalle y orden en [`PENDIENTES.md`](../PENDIENTES.md).
