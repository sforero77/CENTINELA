# Pendientes y hoja de ruta

Estado al **23 de agosto de 2026**. Este documento es el traspaso: que queda por
hacer, quien puede hacerlo, y en que orden.

La regla para leerlo: **lo que solo puede hacer alguien con permisos de
administracion del repositorio o cuentas de terceros esta marcado 🔑**. Todo lo
demas es codigo y se puede abordar desde un clon.

---

## 0. Donde estamos

El sistema **funciona de punta a punta y corre solo**:

```bash
centinela impact us6000tjl2 \
  --detail-url "https://earthquake.usgs.gov/fdsnws/event/1/query?eventid=us6000tjl2&format=geojson" \
  --exposure data/build/exposure_h3.parquet --manifest col-v0.4
# 24,7 s -> 2.415.793 personas en MMI>=7, reporte publicado en reports/
```

| Componente | Estado |
|---|---|
| P1 trigger (feed, filtro, dedupe, estado) | ✅ verificado contra el feed vivo |
| P0 activo de exposicion (descarga → parquet) | ✅ funcional |
| P2 impacto (contornos → celdas → GF → join) | ✅ funcional |
| P3 reporte (json, md, csv, hilo, 2 mapas) | ✅ funcional |
| Pagina `/status` con latencia real | ✅ funcional |
| Golden G1 (Chocó) y G3 | ✅ corren |
| P4 brigada de imagen | ⏳ Fase 2, solo contrato |

**210 pruebas**, `ruff` y `mypy --strict` limpios, arranque verificado desde clon vacio.

### Lo que impide cerrar Fase 0

La puerta de salida de la espec pide cuatro cosas:

| Requisito | Estado |
|---|---|
| G1 verde | ✅ |
| G2 verde | ⚠️ una asercion saltada: necesita el activo de Venezuela |
| Un reporte real publicado end-to-end **sin intervencion** | ❌ el pipeline nunca ha corrido dentro del workflow, solo en local |
| Latencia medida y publicada | ⚠️ la pagina existe; faltan datos reales |

Las dos que faltan se cierran **con el primer sismo M≥5.5 en LATAM**, que con la
sismicidad normal de la region es cuestion de dias. O antes, disparando el
simulacro de §6.5.

---

## 1. 🔑 Tuyo — desbloquea la operacion

Sin estos cuatro pasos el sistema **no puede operar**. Estan en orden.

### 1.1 Fusionar el PR

https://github.com/sforero77/CENTINELA/pull/1 — CI en verde, sin conflictos.

### 1.2 Publicar el activo de exposicion

`impact.yml` **falla a proposito** si no encuentra un Release `exposure-col-*`:
operar sin activo produciria un reporte vacio en vez de un error.

```bash
# Renombra el parquet a exposure_h3.parquet: es el nombre que busca el workflow.
gh release create exposure-col-20260823 exposure_h3.parquet \
  --title "Activo de exposicion COL — 2026-08-23" \
  --notes-file data/manifests/COL.yaml
```

Detalle, cifras y `sha256` en [`docs/PUBLICAR_ACTIVO.md`](docs/PUBLICAR_ACTIVO.md).

Si perdiste el archivo, se reconstruye con `make country ISO=COL` — tarda unos
20 minutos, casi todo descarga.

### 1.3 Habilitar GitHub Pages

`Settings → Pages → Source: GitHub Actions`. Sin esto el visor y `/status` no se
publican, y `site.yml` fallara en cada push.

### 1.4 Monitor externo

Crea un check en [healthchecks.io](https://healthchecks.io) (gratis), periodo 30
min, y guarda su URL en `Settings → Secrets and variables → Actions` como
`HEALTHCHECK_URL`.

Importa mas de lo que parece. **GitHub desactiva los workflows programados tras
60 dias sin actividad en el repositorio**, y para un sistema que puede pasar
meses sin un sismo mayor esa desactivacion silenciosa es el modo de falla mas
probable de todo el proyecto. El `keepalive.yml` lo previene; el monitor avisa
si falla igual.

### 1.5 Probar el circuito

Tras fusionar: `Actions → Simulacro mensual → Run workflow`. Verifica el
circuito completo antes de que llegue un sismo de verdad.

---

## 2. Codigo — cualquiera puede tomarlo

Ordenado por lo que mas desbloquea.

### 2.1 Cerrar G2: activo de Venezuela · **alto valor, esfuerzo medio**

Es el pendiente mas valioso. Requiere:

1. Anadir `VEN` a `COUNTRY_BBOX` en `pipelines/p0_exposure/download.py`.
2. Crear `data/manifests/VEN.yaml`. El patron `cod-ab-ven` de OCHA ya esta
   verificado, igual que `hotosm_ven_*`.
3. Encontrar la referencia oficial de poblacion para el assert de §6.4.
4. Correr `make country ISO=VEN` y activar la asercion saltada en
   `tests/golden/test_g2_venezuela.py`.

Cierra la puerta de salida de Fase 0 y valida que el sistema es multi-pais de
verdad, no solo en teoria.

### 2.2 T0.7: benchmark de `exactextract` · **bajo esfuerzo**

Comparar el muestreo actual (suma de pixeles por celda) contra `exactextract`.
Criterio de la espec: menos de 1 % de diferencia en la poblacion nacional. Si
cumple, se documenta y se cierra; si no, se cambia el metodo.

### 2.3 PMTiles del visor · **medio**

El visor tiene el mapa vacio. Hace falta generar teselas de las coropletas r7/r6
con `tippecanoe` y publicarlas. **Ojo**: las capas de *contexto* no hacen falta
generarlas — Overture publica sus propias PMTiles por release en
`https://tiles.overturemaps.org/<release>/<tema>.pmtiles`. Solo son propias las
coropletas de exposicion e impacto, que son datos nuestros.

### 2.4 Reporte preliminar sin ShakeMap (RF-03) · **medio**

`compute_preliminary()` calcula la poblacion por radios de 25/50/100 km, pero
`run_impact` todavia no arma el reporte con ella: solo cuenta el intento y
transiciona el estado. Falta la rama que emite el reporte preliminar.

Importa porque un M7 sin ShakeMap durante media hora es exactamente el caso en
que alguien necesita una cifra.

### 2.5 Fase 1: seis paises mas · **alto esfuerzo**

MX, PE, EC, CL, GT (VE sale en 2.1). El camino esta despejado: `cod-ab-<iso3>` y
`hotosm_<iso>_*` existen verificados para los siete. Por pais hace falta el
manifest, la caja envolvente y un mantenedor que valide los toponimos.

### 2.6 Deuda menor

- `data/manifests/COL.yaml` tiene los `sha256` vacios. Se llenan solos en la
  primera corrida de `make country`, que devuelve el inventario con hashes.
- **T0.10**: la referencia de poblacion del DANE es la cifra redondeada de su
  nota tecnica (53.000.000). Sustituirla por el valor exacto del anexo en Excel
  haria que el assert compare contra un numero y no contra un redondeo.
- `admin_lookup` guarda el centroide como WKT en texto. Funciona, pero
  `GEOMETRY` seria mas limpio.

---

## 3. Fases siguientes

**Fase 2 — Brigada de imagen.** Solo existe el contrato (`p4_brigada/`) con el
esquema del GeoPackage y las guardias de publicacion: umbral de 0,75 en
precision y recall, y la separacion entre pesos limpios y pesos contaminados por
xBD. Pendientes T2.1–T2.4.

**Fase 3 — Institucional.** Presentar el sistema a la UNGRD y pares regionales
como insumo abierto. La arquitectura ya admite columnas de embedding por celda
sin refactor (T3.1).

---

## 4. Trabajar en local

```bash
git clone https://github.com/sforero77/CENTINELA
cd CENTINELA
make setup     # uv, Python 3.12, todo
make check     # lint + mypy + pruebas: lo mismo que corre CI
```

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

## 5. Lo que no hay que romper

Cuatro invariantes que costaron encontrar. Cada uno tiene su prueba de regresion.

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

Y una regla de producto: **exposicion no es dano**. Todo artefacto sale con sus
disclaimers, y el hilo para redes se genera pero **no se publica solo**.

---

## 6. Documentos

| | |
|---|---|
| [`ESPECIFICACION.md`](ESPECIFICACION.md) | Espec tecnica v0.10 |
| [`VERIFICACIONES.md`](VERIFICACIONES.md) | Como se verifico cada fuente, con evidencia |
| [`docs/PUBLICAR_ACTIVO.md`](docs/PUBLICAR_ACTIVO.md) | Publicar el activo y por que no va en git |
| [`DISCLAIMER.md`](DISCLAIMER.md) | Que informa y que no informa el sistema |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | Como contribuir, rol de mantenedor por pais |
| [`GOVERNANCE.md`](GOVERNANCE.md) | Roles, decisiones, frontera comunidad ↔ empresa |
| [`LICENSES/`](LICENSES/) | La regla de los tres cubos |
