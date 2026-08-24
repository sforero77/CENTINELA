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
centinela impact us6000tjl2 \
  --detail-url "https://earthquake.usgs.gov/fdsnws/event/1/query?eventid=us6000tjl2&format=geojson" \
  --exposure data/build/exposure_h3.parquet --manifest col-v0.4
# 24,7 s -> 2.415.793 personas en MMI>=7, reporte publicado en reports/
```

| Componente | Estado |
|---|---|
| P1 trigger (feed, filtro, dedupe, estado) | ✅ **operando cada 10 min** |
| Visor y `/status` publicados | ✅ https://sforero77.github.io/CENTINELA/ |
| P0 activo de exposicion (descarga → parquet) | ✅ funcional, nueve capas |
| P2 impacto (contornos → celdas → GF → join) | ✅ funcional, con activo elegido por epicentro |
| P3 reporte (json, md, csv, hilo, 2 mapas) | ✅ funcional |
| Pagina `/status` con latencia real | ✅ funcional |
| Golden G1 (Chocó) y G3 | ✅ corren |
| P4 brigada de imagen | ⏳ Fase 2, solo contrato |

**431 pruebas** sin red (mas 8 nocturnas contra las fuentes vivas), `ruff` y
`mypy --strict` limpios, arranque verificado desde clon vacio.

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
| G2 verde | ⚠️ una asercion saltada: necesita el **reporte** de Venezuela. El activo ya existe; falta correr el backtest de los dos mainshocks con `centinela impact --backtest` |
| Un reporte real publicado end-to-end **sin intervencion** | ⏳ el sistema ya opera; falta que ocurra un sismo |
| Latencia medida y publicada | ⏳ la pagina esta publicada y espera datos reales |

Desde el 24-ago-2026 el sistema **esta encendido**: el trigger vigila el feed
cada 10 minutos y el visor esta en linea. Las dos que faltan ya no dependen de
nadie — las cierra el primer sismo M≥5.5 en LATAM, que con la sismicidad normal
de la region es cuestion de dias.

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

## 2. Codigo — cualquiera puede tomarlo

Ordenado por lo que mas desbloquea.

### 2.0 🔴 La ventana del disparador cortaba paises cubiertos

Corregido, pero conviene saberlo. `LATAM_BBOX` —el filtro de RF-01— iba de
118,0°O a 34,0°O y de 56,0°S a 33,0°N. Al medir las cajas de los 19 paises
salio que **no cubria territorio de paises que el sistema dice cubrir**:

| | Llega a | La ventana cortaba en |
|---|---|---|
| Mexico (Isla Guadalupe, Revillagigedo) | 118,65°O | 118,0°O |
| Chile (Cabo de Hornos, Diego Ramirez) | 56,78°S | 56,0°S |
| Brasil (Fernando de Noronha, ~3.000 hab.) | 32,42°O | 34,0°O |

Un sismo relevante ahi no habria fallado: **habria dejado de existir para el
sistema**. Chile importa especialmente, porque la zona de fractura de
Shackleton produce sismos justo en ese margen.

Nueva ventana: `lon -119,0..-32,0 / lat -57,5..33,0`. El limite este llega a
Fernando de Noronha y se detiene antes del archipielago de San Pedro y San
Pablo, que se asienta sobre la dorsal mesoatlantica: estirarlo hasta alli
compraria sismicidad oceanica frecuente y sin poblacion a cambio de una
estacion cientifica.
→ `tests/unit/test_cobertura_latam.py`

### 2.0b 🔴 El impacto usaba el activo de Colombia para toda LATAM

Corregido, y era el peor de los ceros silenciosos. P1 vigila **toda** la ventana
LATAM; `impact.yml` tenia Colombia fija en dos sitios. Un M6.8 en Peru: el
trigger lo detecta, dispara el impacto, baja el activo **colombiano**, el join
no encuentra una sola celda H3, `SQL_TOTALES` devuelve NULL en cada columna,
`float(v or 0.0)` los convierte en ceros — y se publica un reporte diciendo que
**no hay nadie expuesto**, en el visor publico, durante un terremoto real.

Los demas ceros silenciosos salian en un build repetible. Este salia en el peor
momento posible y decia exactamente lo contrario de la verdad.

Dos arreglos:

- **Guardia.** Si el join no produce ninguna celda, `compute_impact` falla. Un
  reporte que no sale es un problema; uno que dice "0 personas" es una mentira.
- **Enrutado por pais.** `centinela paises-candidatos <usgs_id>` resuelve el
  pais desde el epicentro y el workflow busca el Release de ese pais. Si no hay
  activo, falla con el comando exacto para construirlo y abre un issue. El
  hueco se vuelve una tarea visible en vez de una cifra falsa.

→ `tests/unit/test_pais_del_evento.py`

### 2.1 Cerrar G2: reporte de Venezuela · **falta correr el backtest**

El codigo ya esta hecho: `data/manifests/VEN.yaml`, `COUNTRY_BBOX["VEN"]`
—medida sobre el COD-AB, no estimada—, el mapeo de columnas del COD-AB y las
aserciones de G2, que se saltan solas mientras no exista el reporte y se
activan sin tocar nada cuando exista.

El activo ya esta construido y publicado (`exposure-ven-20260824`). Lo que
falta es el **reporte** de los dos mainshocks del 24-jun-2026, que ademas
estrena el camino P2→P3 en CI: hasta ahora `impact.yml` nunca ha calculado
nada, solo ha devuelto `omitir: ya procesado`.

    gh workflow run impact.yml -f usgs_id=us6000t7zp -f backtest=true
    gh workflow run impact.yml -f usgs_id=us6000t7zc -f backtest=true

`--backtest` reconstruye el `event_state` que P1 nunca creo —el feed que vigila
es el de la ultima hora— y lo marca como retrospectivo, para que su latencia de
dos meses no entre en el p50/p95 y el reporte lleve el aviso de que las
edificaciones y las vias son las de hoy.

**Antes hay que reconstruir el activo de VEN con el rescate corregido.** El
publicado se construyo con el rescate que invadia al vecino, y Venezuela se
desvia +6,30 % — el mismo orden que Paraguay antes del arreglo. Congelar
`POP_MMI7P_ESPERADO` contra un activo contaminado seria fijar el error.

La tolerancia esta en 5 % contra la ONU (28.516.896 para 2025) y es una
expectativa, no una verificacion: GHS-POP deriva de la ronda censal de 2010 y
no modela la emigracion venezolana. Que el assert falle seria un hallazgo, no
un bug. Procedimiento en [`docs/PUESTA_EN_MARCHA.md`](docs/PUESTA_EN_MARCHA.md).

### 2.1b Fuentes de LATAM: validadas las 19, manifests escritos

Revisado el 23-ago-2026 con una peticion real por fuente y pais. **Los 19
paises de LATAM hispanohablante mas Brasil tienen las cuatro fuentes
nacionales**: WorldPop age-sex (20 bandas cada uno), WorldPop total,
`cod-ab-<iso3>` (CC BY-IGO) y los extractos `hotosm_<iso>_health_facilities` y
`hotosm_<iso>_education_facilities` (ODbL). No hay ningun pais sin camino.

Dos irregularidades que conviene saber antes de Fase 1:

- **Cinco paises no publican GeoJSON** en su COD-AB y caen a SHP: COL, ARG,
  BRA, PRY, URY.
- **Colombia publica cuatro recursos SHP** y el resolutor tomaba el primero,
  que son secciones urbanas del MGN (48 MB), no municipios. Por eso existe
  ahora `hdx_resource` en el manifest: un dataset con varios recursos del mismo
  formato tiene que fijar cual, igual que fija el vintage.

### 2.2 T0.7: benchmark de `exactextract` · **bajo esfuerzo**

Comparar el muestreo actual (suma de pixeles por celda) contra `exactextract`.
Criterio de la espec: menos de 1 % de diferencia en la poblacion nacional. Si
cumple, se documenta y se cierra; si no, se cambia el metodo.

### 2.3 PMTiles del visor · **mapa base hecho, faltan las coropletas**

**Hecho el 24-ago-2026:** el mapa ya dibuja. Tierra, agua, fronteras y vias
principales salen de las PMTiles que Overture publica por release, sin generar
nada ni servir nada desde Pages. Las fronteras en disputa van punteadas y en
otro color en vez de elegir un lado. Los epicentros de los reportes publicados
se dibujan como circulos que escalan con la **poblacion expuesta a MMI≥7**, no
con la magnitud: dos sismos de la misma magnitud sobre poblaciones distintas no
son el mismo evento para quien responde.

Para eso hubo que meter `lon`/`lat` en `report.json`: estaban en el
`event_state` y se quedaban ahi, asi que el artefacto publico no decia donde
fue el sismo y ni el propio visor podia situarlo.

**Ojo con el release.** `OVERTURE_RELEASE` en `site/assets/app.js` esta fijado
a mano y hay que subirlo cada trimestre con el activo: Overture solo conserva
dos releases. Cuando caduque, el mapa se queda gris y los reportes siguen bien,
porque las cifras no dependen de las teselas — pero hay que verlo venir.

**Falta:** las coropletas r7/r6 de exposicion e impacto, que si son datos
nuestros y necesitan `tippecanoe`.

### 2.4 ✅ Reporte preliminar sin ShakeMap (RF-03) · cerrado el 24-ago-2026

`compute_preliminary()` estaba escrita, comentada y probada desde el principio,
y **no la llamaba nadie**: el evento pasaba a estado `preliminar`, se guardaba
el estado y no se publicaba nada. Durante las primeras horas —las unicas en que
un preliminar sirve— el sistema callaba.

Mismo patron que las tres capas del activo que se agregaban a tablas que nadie
leia: una funcion escrita no es una funcion conectada, y ninguna prueba lo veia
porque todas probaban la funcion, no el camino.

El preliminar publica la tabla por radios **en lugar** de la de intensidad, no
ademas. Sin ShakeMap todas las cifras por MMI valen cero, y "poblacion en
MMI≥7: 0" bajo el titulo "Exposicion estimada" es una respuesta falsa y
creible. Lleva ademas su propia advertencia: un radio no es una banda de
intensidad —un M6 superficial y uno a 200 km tienen el mismo circulo de 50 km—
y la cifra sirve para dimensionar, no para priorizar.

→ `tests/unit/test_reporte_preliminar.py`

### 2.5 Fase 1: construir los paises · **el camino ya esta hecho**

Los **19 manifests estan escritos** y sus cajas envolventes medidas sobre
`division_area` de Overture con un solo criterio. Por pais ya no hace falta
buscar datos: hace falta **construir y medir**, mas un mantenedor que valide los
toponimos.

Lo que cada pais nuevo necesita, en orden:

1. `uv run centinela country <ISO3>` — unos 800 MB y una hora larga por pais.
2. Anotar `medido_ghs_pop` en su manifest y **ajustar `tolerancia_pct`**: hoy
   todos los nuevos llevan un 5 % provisional que no es una medicion. Colombia,
   que si esta medida, usa 1 %.
3. Validar los toponimos. (La codificacion de Venezuela estaba anotada como
   rota —«Falc?n»— y **no lo esta**: era la consola de Windows. Verificado
   byte a byte sobre el parquet publicado.)
4. Publicar el activo como Release.

Ojo con el coste de las cajas insulares: Chile llega a 109,7°O por Rapa Nui,
Mexico a 118,6°O por Guadalupe y Revillagigedo, Ecuador a 92,3°O por Galapagos.
Son muchas teselas de GHS-POP por poca poblacion, pero el sistema no puede
decidir que una isla habitada no cuenta.

### 2.6 Deuda menor

- `data/manifests/COL.yaml` tiene los `sha256` vacios. Se llenan solos en la
  primera corrida de `make country`, que devuelve el inventario con hashes.
- `overture_divisions` esta declarado en `COL.yaml` y no se usa: la geometria
  sale del MGN. No cuesta nada (las fuentes `s3://` no se descargan) pero
  induce a pensar que participa.
- **T0.7** sigue abierta: falta comparar el muestreo actual contra
  `exactextract`. Criterio de la espec: menos de 1 % de diferencia en la
  poblacion nacional.
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

**En Windows no hay `make`.** Ni en `cmd`, ni en PowerShell, ni en el Git Bash
que trae Git for Windows. Los objetivos del Makefile son atajos de una linea,
asi que se corren sueltos:

```powershell
uv sync --python 3.12 --extra dev --extra geo --extra render
uv run ruff check . ; uv run ruff format --check . ; uv run mypy ; uv run pytest -m "not network"
```

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

## 6. Documentos

| | |
|---|---|
| [`docs/OPERACION.md`](docs/OPERACION.md) | **Que vigilar ahora que el sistema corre: relojes, fallos silenciosos, deuda por pais** |
| [`docs/PUESTA_EN_MARCHA.md`](docs/PUESTA_EN_MARCHA.md) | Los pasos de arranque, por si hay que repetirlos |
| [`ESPECIFICACION.md`](ESPECIFICACION.md) | Espec tecnica v0.10 |
| [`VERIFICACIONES.md`](VERIFICACIONES.md) | Como se verifico cada fuente, con evidencia |
| [`docs/PUBLICAR_ACTIVO.md`](docs/PUBLICAR_ACTIVO.md) | Publicar el activo y por que no va en git |
| [`DISCLAIMER.md`](DISCLAIMER.md) | Que informa y que no informa el sistema |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | Como contribuir, rol de mantenedor por pais |
| [`GOVERNANCE.md`](GOVERNANCE.md) | Roles, decisiones, frontera comunidad ↔ empresa |
| [`LICENSES/`](LICENSES/) | La regla de los tres cubos |
