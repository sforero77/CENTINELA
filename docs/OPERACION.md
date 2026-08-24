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

Cinco cosas que producen cifras plausibles y equivocadas. Cada una tiene ya su
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
| G2 (Venezuela) verde | ⚠️ falta construir el activo de VEN |
| Un reporte real publicado sin intervencion | ⏳ lo cierra el primer sismo |
| Latencia medida y publicada | ⏳ idem |

Los dos ultimos no dependen de nadie: llegan con el primer M≥5.5 en la region.

Lo demas abierto, sin bloquear: **T0.7** (benchmark de `exactextract`),
**T0.10** (la cifra exacta del DANE en vez del redondeo), **PMTiles del visor**
(hoy el mapa esta vacio; las capas de contexto no hay que generarlas, Overture
publica las suyas) y **RF-03** (el reporte preliminar sin ShakeMap: se calcula
por radios pero no se emite).

Detalle y orden en [`PENDIENTES.md`](../PENDIENTES.md).
