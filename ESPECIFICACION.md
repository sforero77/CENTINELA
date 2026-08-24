# CENTINELA — Sistema de Exposición Sísmica Automatizada para LATAM
### Proyecto comunitario GeoAI LATAM · Especificación técnica v0.10
**Fecha:** 23 de agosto de 2026 · **Autor del borrador:** Sebastián Forero + Claude · **Nombre en clave provisional:** `centinela` (abierto a votación de la comunidad)

> **Cambios de v0.9 → v0.10.** Todas las fuentes del registro se probaron contra documentación primaria con peticiones reales. Seis correcciones al documento, cinco de ellas porque la realidad no coincidía con el supuesto:
>
> 1. **WorldPop sí publica estructura etaria para 2025** (release R2025A). Cae el supuesto de «proporciones de 2020 sobre totales de 2025» que se declaraba en cada reporte.
> 2. **REPS y sedes MEN no tienen coordenadas** y son CC BY-SA 4.0, copyleft incompatible con la ODbL de Overture. Salen del activo; salud y educación por celda pasan a extractos de HOTOSM publicados en HDX.
> 3. **Overture conserva solo dos releases** en su bucket: fijar el release da reproducibilidad del cálculo, no de la descarga.
> 4. **`includesuperseded=true` funciona directo en FDSN**: congelar el histórico de versiones no necesita `libcomcat`.
> 5. **T0.1 resuelta**: los `usgs_id` de Chocó y Venezuela están identificados y confirmados contra ComCat.
> 6. **COD-AB de OCHA cubre los siete países de Fase 1** con una licencia y una forma únicas.
>
> El registro completo, con método de verificación y evidencia, está en `VERIFICACIONES.md`.

---

## 0. Resumen ejecutivo

**Qué es.** Un sistema abierto, automatizado y en español que, ante cualquier sismo relevante en América Latina, publica en menos de una hora un **reporte de exposición**: cuántas personas, edificaciones, escuelas, hospitales y kilómetros de vía quedan dentro de cada franja de intensidad sísmica, por municipio y por celda H3, con datos descargables. Complementado por una **brigada de IA en imagen satelital** que se activa cuando hay imagen abierta post-evento, para evaluación de daño a nivel de edificación.

**Qué NO es.** No es un sistema de alerta temprana, no emite recomendaciones de evacuación, no reemplaza a los servicios geológicos nacionales ni a las unidades de gestión del riesgo. Informa exposición estimada; no dictamina daño ni habitabilidad.

**Por qué existe.** En el terremoto del Chocó (M7.4, 10-ago-2026) el país tardó días en saber cuánta población e infraestructura estaba en la zona de intensidad fuerte; las cifras oficiales oscilaron durante semanas; la única evaluación de daño con IA (Microsoft) cubrió solo Cali; y toda la capacidad analítica vino de fuera de la región. Siete semanas antes, en Venezuela (>6.000 muertos), pasó exactamente lo mismo. No existe memoria ni capacidad regional pre-posicionada. Este proyecto es esa capacidad.

**Principio de diseño rector:** ~95% pre-computado y automático, ~5% humano. Una comunidad no opera turnos; mantiene código y datos.

**Decisiones de arquitectura (resumen):**

| # | Decisión | Elección | Alternativa descartada y por qué |
|---|---|---|---|
| D1 | Unidad de análisis | H3 r8 (cómputo) + agregados r7/r6 (visor) + crosswalk a división político-administrativa | Solo municipios (pierde granularidad intra-urbana); grid propio (no interoperable) |
| D2 | Formato de datos | GeoParquet particionado + PMTiles para visor | PostGIS (requiere servidor vivo = costo y mantenimiento) |
| D3 | Cómputo | DuckDB (+ extensiones spatial y h3) en GitHub Actions | Spark/Sedona (sobredimensionado); GEE (dependencia de cuenta y ToS) |
| D4 | Orquestación | GitHub Actions (cron best-effort) + workflow_dispatch + keepalive | Servidor propio (costo/mantenimiento); se documenta upgrade path a cron externo |
| D5 | Publicación | GitHub Releases + GitHub Pages (Fase 0) → bucket público R2 (Fase 1) + HDX por evento | Servidor de mapas dinámico (mantenimiento) |
| D6 | Visor | Estático: MapLibre GL JS + PMTiles, cero llaves de API | Visor con backend (SLA imposible para comunidad). Nota: demo paralela con ArcGIS Maps SDK es bienvenida como contenido, no como dependencia |
| D7 | Disparo | Feeds GeoJSON en tiempo real de USGS (recomendación explícita de USGS para apps automatizadas), no consultas FDSN repetidas | Polling FDSN (peor rendimiento/disponibilidad según el propio USGS) |
| D8 | Separación de licencias | Núcleo redistribuible (dominio público / CC-BY / ODbL) separado físicamente de derivados NC | Mezclar (contaminaría el dataset y bloquearía reuso) |

---

## 1. Alcance y objetivos

### 1.1 Objetivos (medibles)

- **O1 — Latencia:** publicar el reporte de exposición v1 en ≤ 60 min (p50) / ≤ 90 min (p95) tras la disponibilidad del primer ShakeMap del evento. *(La latencia del cron de GitHub Actions es best-effort con demoras documentadas de 5–30 min; el SLO se define sobre lo controlable.)*
- **O2 — Cobertura Fase 0:** Colombia completa. **Fase 1:** CO, MX, PE, EC, CL, VE, GT. **Fase 2:** resto de LATAM hispanohablante + BR (reportes ES/PT).
  - *Validado el 23-ago-2026:* las cinco fuentes nacionales existen para **los 19 países** de LATAM hispanohablante más Brasil, y los 19 manifests están escritos. Lo que queda por país es construir y medir, no buscar datos.
  - *Corrección de RF-01 (23-ago-2026):* la ventana del disparador cortaba territorio de países cubiertos — México llega a 118,65°O y Chile a 56,78°S. Pasa a `lon -119,0..-32,0 / lat -57,5..33,0`. El límite este llega a Fernando de Noronha (32,42°O, habitada) y se detiene antes del archipiélago de San Pedro y San Pablo, que se asienta sobre la dorsal mesoatlántica.
- **O3 — Cadencia viva:** ≥ 2 reportes reales/mes con la sismicidad normal de la región (M≥5.5), garantizando que el pipeline nunca se oxida entre catástrofes.
- **O4 — Reproducibilidad:** cualquier persona reconstruye el activo de exposición de un país con `make country ISO=COL` desde fuentes públicas, sin credenciales privadas.
- **O5 — Backtest:** el sistema reproduce retrospectivamente el evento del 10-ago-2026 (Chocó) y el del 24-jun-2026 (Venezuela) como *golden tests* permanentes.
- **O6 — Brigada de imagen:** ante liberación de imagen abierta post-evento, publicar GeoPackage de daño a nivel de edificación en HDX en ≤ 7 días, con esquema interoperable con el de Microsoft AI for Good.

### 1.2 No-objetivos (línea roja, se documentan en el sitio)

- ❌ Alerta temprana o notificación de emergencia a población.
- ❌ Estimación de víctimas (eso es PAGER; solo lo referenciamos).
- ❌ Dictamen de daño estructural o habitabilidad (la brigada IA produce *priorización*, jamás veredicto).
- ❌ Datos personales de cualquier tipo (desaparecidos, censos nominales): fuera de alcance permanente.
- ❌ Operación 24/7 con humanos en el circuito crítico.

### 1.3 Usuarios objetivo

1. Salas de crisis y consejos territoriales de gestión del riesgo (consumen el PDF/mapa/cifras por municipio).
2. Periodistas de datos y medios regionales (consumen el hilo y el mapa embebible).
3. Comunidad geoespacial (consume GeoParquet/PMTiles y contribuye).
4. ONG humanitarias (consumen paquete HDX).

---

## 2. Registro de fuentes (validado)

Convención de estado: **✅ verificado** (contrastado contra documentación primaria el 23-ago-2026) · **⚠️ por confirmar** (fuente conocida; verificación pendiente asignada a tarea de Fase 0).

### 2.1 Datos de evento (dinámicos)

| Fuente | Acceso | Licencia | Estado | Notas de validación |
|---|---|---|---|---|
| USGS feeds GeoJSON tiempo real (`4.5_hour`, `4.5_day`) | `earthquake.usgs.gov/earthquakes/feed/v1.0/summary/…` | Dominio público (obra del gobierno de EE. UU.) | ✅ | El propio USGS indica que las aplicaciones automatizadas deben usar los feeds en tiempo real, no consultas FDSN repetidas, por rendimiento y disponibilidad. Los feeds siguen una política de ciclo de vida publicada. |
| USGS GeoJSON *detail* por evento | propiedad `detail` de cada feature | Dominio público | ✅ | Incluye objeto `products` con todos los productos aportados: `shakemap`, `losspager`, `ground-failure`, `origin`, `dyfi`, etc. Es la puerta única a los productos. |
| USGS FDSN Event (ComCat) | `earthquake.usgs.gov/fdsnws/event/1/query` | Dominio público | ✅ | Solo para backtests e históricos. **Verificado:** el parámetro `includesuperseded=true` funciona directamente sobre el endpoint FDSN y devuelve todas las versiones de cada producto — no hace falta `libcomcat`. No para polling. |
| ShakeMap (por evento) | vía `products.shakemap` → `grid.xml`, rásters, contornos GeoJSON (`cont_mmi`), `uncertainty` | Dominio público | ✅ | **Versionado**: un evento acumula múltiples versiones de ShakeMap (v1, v2, …). El sistema debe re-emitir reporte al detectar nueva versión y etiquetar cada salida con la versión consumida. |
| USGS Ground Failure (por evento) | vía `products.ground-failure` → rásters de probabilidad de deslizamiento y licuefacción | Dominio público | ✅ | Producto presente en el catálogo de productos de ComCat; también versionado. Diferenciador clave frente a GDACS: casi nadie lo integra. |
| PAGER | vía `products.losspager` | Dominio público | ✅ | Solo como referencia cruzada en el reporte ("PAGER estima: alerta X"); nunca como cifra propia. |
| Redes nacionales (SGC-CO, SSN-MX, CSN-CL, IGP-PE, IG-EPN-EC, Funvisis-VE) | APIs/scraping heterogéneo | Varía | ⚠️ | Fase 1. Uso: localización fina y eventos <M5.5 de interés nacional. Tarea T1.1: inventariar formatos y términos por país. |

### 2.2 Capas de exposición (activo pre-computado)

| Capa | Fuente | Vintage | Resolución | Licencia | Estado | Notas |
|---|---|---|---|---|---|---|
| Población total | GHS-POP R2023A (JRC/Copernicus) | Épocas 1975–2030 c/5 años; usar 2025 | 100 m (Mollweide) y 3″ (WGS84) | Reuso CE con atribución | ✅ | Derivado de GPWv4.11 + volumen construido GHSL. Descarga directa JRC y espejo en HDX. Citar Schiavina et al. 2023, doi:10.2905/2FF68A52. |
| Estructura etaria/sexo | WorldPop age-sex **constrained**, release **R2025A** | **2025** (anual 2015–2030) | 100 m | CC BY 4.0 | ✅ | **Corrige v0.9.** El release R2025A publica desglose por edad y sexo hasta 2026: 62 rásters por país para 2025. Se colapsan a 0-14 / 15-64 / 65+. **El supuesto de estructura etaria estable desaparece**: la cifra de 65+ en MMI≥7 deja de arrastrar cinco años de desfase. |
| Población total (contraste) | WorldPop constrained 2015–2030 (R2025) | anual | 100 m | CC BY 4.0 | ✅ | Solo para banda de discrepancia GHS-POP vs WorldPop por celda (métrica de incertidumbre publicada). |
| Edificaciones | Overture `theme=buildings/type=building` | Release mensual (fijar en manifest) | vector | **ODbL** (incluye OSM) | ✅ | GeoParquet nativo con columna `bbox` e IDs GERS estables. Fijar release explícito, nunca "latest". Usar `type=building`, **no** `type=building_part` (geometría auxiliar, inflaría `bld_count`). ⚠️ **El bucket conserva solo los dos releases más recientes**: ver §2.5. |
| Vías | Overture `theme=transportation/type=segment` | mensual | vector | ODbL | ✅ | km por clase (motorway→secondary) por celda. `type=connector` son nodos, no geometría lineal. |
| División político-administrativa | DANE MGN 2025 (CO) + **COD-AB de OCHA** (resto) + Overture `divisions/type=division_area` | vigente / COD 2025 / mensual | vector | **CC BY 4.0** / **CC BY-IGO** / ODbL | ✅ | **T0.4 resuelta:** el Geoportal DANE publica bajo CC BY 4.0 (uso comercial y redistribución permitidos; citar «Departamento Administrativo Nacional de Estadística - DANE: www.dane.gov.co»). **Hallazgo de Fase 1:** el patrón `cod-ab-<iso3>` existe verificado para los siete países con licencia y forma uniformes — evita pelear con siete geoportales nacionales. |
| Salud | **HOTOSM `hotosm_<iso>_health_facilities`** (HDX) + **healthsites.io vía HDX** | rolling | puntos | ODbL / ODbL | ✅ | **T0.5 resuelta en contra.** El REPS (`c36g-9fc2`, 76.821 sedes) **no publica coordenadas** — solo DIVIPOLA y dirección, el dataset entero, no «una parte» — y es **CC BY-SA 4.0**, copyleft incompatible con ODbL. Sale del activo: pasa a referencia de completitud municipal en tabla aparte. La **API** de healthsites.io exige API key y viola O4; su publicación en HDX no. |
| Educación | **HOTOSM `hotosm_<iso>_education_facilities`** (HDX) | rolling | puntos | ODbL | ✅ | **T0.6 resuelta en contra.** El directorio del MEN (`cfw5-qzt5`) tampoco publica coordenadas y también es CC BY-SA 4.0; además sus 588.334 filas son registros por establecimiento **y año**. Mismo tratamiento que el REPS. |
| Aeropuertos | OurAirports | rolling | puntos | Dominio público | ✅ | **T1.2 resuelta.** Disponibilidad verificada (HTTP 200, 12,7 MB) y dedicación citada: la página de datos declara «All data is released to the Public Domain», y el repositorio de descargas lleva The Unlicense íntegro. Matiz registrado en `VERIFICACIONES.md`: The Unlicense habla de *software*, y es la declaración de la página de datos la que cubre los datos. |
| Contexto: susceptibilidad a deslizamiento | SIMMA/SGC (CO); NASA LHASA global (resto) | estático | ráster/vector | por confirmar | ⚠️ | Capa de contexto del visor, no del reporte automático (el reporte usa Ground Failure por evento, que es específico y dominio público). |
| Amenaza sísmica de fondo | GEM Global Hazard Map | 2023 | ráster | **CC BY-NC-SA** | ✅ (licencia) | ⚠️ NC → solo visor/contexto, bucket NC, jamás mezclada en el núcleo redistribuible. |

### 2.3 Módulo brigada de imagen (Fase 2, activación por evento)

| Recurso | Licencia | Estado | Rol |
|---|---|---|---|
| Vantor (Maxar) Open Data (STAC) | CC BY-NC 4.0 | ✅ | Imagen VHR por evento. NC: derivados al bucket NC. |
| Copernicus EMS Rapid Mapping (vectores de grading) | Abierta (atribución CE) | ⚠️ (T2.1 confirmar cláusulas exactas) | **Etiquetas de entrenamiento y validación gratis por activación.** |
| OpenAerialMap | CC BY 4.0 (por defecto) | ✅ | Imagen aérea/dron comunitaria. |
| Umbra Open Data (SAR) | CC BY 4.0 | ⚠️ (T2.2) | Vía SAR sin problema de nubes ni de licencia NC. |
| Capella Open Data (SAR) | por confirmar | ⚠️ (T2.2) | Ídem. |
| Toolkit `microsoft/building-damage-assessment` | MIT (código) | ✅ | Pipeline semilla human-in-the-loop (etiquetado→máscaras→fine-tuning→inferencia); precisión 0.86 / recall 0.80 reportados en Rolling Fork con <2 h por escena. |
| GeoPackage Microsoft Cali (HDX) | ver metadatos HDX | ⚠️ (T2.3) | Referencia de esquema y validación cruzada. |
| xBD/xView2 (pre-entrenamiento) | **CC BY-NC-SA 4.0** | ✅ (licencia) | ⚠️ Contamina pesos: modelos fine-tuneados desde xBD heredan NC. Estrategia: rama de pesos "limpia" (entrenada solo con Copernicus EMS + etiquetas propias) y rama NC, documentadas por separado (T2.4). |

### 2.4 Reglas de licenciamiento (obligatorias)

1. **Tres cubos físicamente separados:** `core/` (dominio público + CC-BY + atribución CE), `odbl/` (todo lo que toque OSM/Overture buildings/transportation) y `nc/` (Vantor, GEM, xBD-derivados). El reporte automático consume `core/` + `odbl/`; el share-alike de ODbL se cumple publicando el derivado bajo ODbL (que es lo que ya hacemos).
2. **Atribución en cada artefacto** (pie de mapa, `ATTRIBUTION.md`, propiedades del GeoParquet): USGS, © OpenStreetMap contributors (ODbL), Overture Maps Foundation, JRC/Comisión Europea (GHSL), WorldPop (CC BY 4.0), y las que apliquen por evento.
3. **INSPOW no toca `nc/`.** La frontera comunidad↔empresa queda escrita en `GOVERNANCE.md`.
4. **Dos copyleft distintos no caben en el mismo derivado.** ODbL y CC BY-SA 4.0 son ambas share-alike y mutuamente incompatibles: cada una exige que el derivado se publique bajo ella y no existe licencia que satisfaga a las dos. La regla de los tres cubos no atrapa este caso, porque ambas caen del lado «redistribuible». `resolve_bucket()` rechaza la combinación con error explícito. El caso no es hipotético: es exactamente el que sacan REPS y MEN frente a Overture.

### 2.5 Restricciones operativas de las fuentes (verificadas)

Tres hechos que no son detalles de implementación, porque cambian lo que el sistema puede prometer.

**Overture conserva solo los dos releases más recientes.** Listado del bucket, no truncado: existen exactamente dos. Fijar el release explícito —decisión correcta, se mantiene— da reproducibilidad **del cálculo**, no **de la descarga**: pasados unos dos meses la URL del manifest deja de existir. **RNF-04 se sostiene por el Release propio del activo construido con su `sha256`, no por la URL de origen.** Es la copia publicada, y no la fuente, la que hace re-derivable un número de hace seis meses.

**La URL de un mismo dataset de HOTOSM cambia de forma según el país.** Para la capa `health_facilities` conviven al menos tres patrones (COL, MEX y PER difieren entre sí). El identificador estable es el **nombre del dataset**, y la URL se resuelve por la API de CKAN de HDX en cada build. Adivinar la ruta funciona hasta que Fase 1 agrega el país que no encaja — y ahí falla en producción, no en CI.

**Ninguna fuente puede exigir credenciales.** O4 lo pide y aquí muerde: la API de healthsites.io requiere API key, así que se consume su publicación en HDX. El criterio general de la auditoría de fuentes es más simple todavía: **una fuente sin geometría no sirve**, por buena que sea su cobertura. Un registro administrativo sin coordenadas no puede asignarse a una celda H3; sirve como referencia de completitud, nunca como conteo.

---

## 3. Modelo de datos

### 3.1 Identificadores y convenciones

- CRS de publicación: EPSG:4326. Cómputo de áreas: proyección equiárea local por país.
- `h3_08` como `UINT64`. Agregados publicados: r8 (análisis), r7 y r6 (visor).
- Llave administrativa: `adm2_id` (CO: código DIVIPOLA de 5 dígitos, `VARCHAR`), `adm1_id`, `iso3`.
- Todo timestamp en UTC ISO-8601; hora local solo en la capa de presentación.
- Particionado Hive: `iso3=COL/layer=exposure/…`.

### 3.2 Tablas del activo de exposición

**`exposure_h3`** (una fila por celda r8 · rebuild trimestral)

| Columna | Tipo | Fuente | Nota |
|---|---|---|---|
| h3_08 | UINT64 | — | PK |
| iso3, adm1_id, adm2_id | VARCHAR | crosswalk | asignación por centroide + tabla de fracciones para celdas fronterizas |
| pop_total | DOUBLE | GHS-POP 2025 | suma dasimétrica de píxeles → celda |
| pop_0_14, pop_15_64, pop_65p | DOUBLE | WorldPop **R2025A época 2025** (proporciones) × pop_total | sin supuesto de estructura estable (v0.10) |
| pop_alt_worldpop | DOUBLE | WorldPop total | banda de discrepancia |
| bld_count, bld_area_m2 | INT/DOUBLE | Overture buildings | |
| health_count, edu_count | INT | OSM+REPS / MEN+OSM | |
| road_km_primary, road_km_secondary, road_km_other | DOUBLE | Overture transportation | |
| src_manifest | VARCHAR | — | id del manifest de vintages |

**`crosswalk_h3_adm`**: `h3_08, adm2_id, frac_area` (para prorrateo exacto en frontera municipal).

**`admin_lookup`**: `adm2_id, nombre, adm1_id, departamento, iso3, centroide`.

### 3.3 Tablas por evento

**`event_state`** (JSON versionado en repo, uno por evento): `usgs_id, estado, versiones_procesadas{shakemap: n, groundfailure: n}, timestamps, hashes`.

**`impact_h3`** (una fila por celda alcanzada, por versión de ShakeMap): `usgs_id, shakemap_version, h3_08, mmi_mean, mmi_max, pga_g, ls_prob, lq_prob` + todas las columnas de exposición copiadas al momento del corte (inmutabilidad del reporte).

**`impact_adm2`** (agregado municipal, la tabla que consume el mundo): `usgs_id, shakemap_version, adm2_id, nombre, mmi_max, pop_mmi6p, pop_mmi7p, pop_65p_mmi7p, bld_mmi7p, health_mmi7p, edu_mmi7p, road_km_mmi7p, ls_pop_expuesta, flags_calidad`.

### 3.4 Esquema del reporte (`report.json` v1)

```json
{
  "schema": "centinela/report/1.0",
  "event": {"usgs_id": "", "mag": 0, "depth_km": 0, "utc": "", "lugar": "", "pager_alert": ""},
  "inputs": {"shakemap_version": 0, "groundfailure_version": 0, "exposure_manifest": ""},
  "totales": {"pop_mmi6p": 0, "pop_mmi7p": 0, "pop_mmi8p": 0, "bld_mmi7p": 0,
               "health_mmi7p": 0, "edu_mmi7p": 0, "road_km_mmi7p": 0,
               "pop_ls_alta": 0, "pop_lq_alta": 0},
  "top_municipios": [{"adm2_id": "", "nombre": "", "mmi_max": 0, "pop_mmi7p": 0}],
  "incertidumbre": {"pop_discrepancia_pct": 0, "notas": []},
  "descargas": {"geoparquet": "", "pmtiles": "", "csv_adm2": "", "mapa_png": ""},
  "disclaimers": ["exposición estimada, no daño", "no es alerta", "fuentes y vintages: manifest"],
  "generado_utc": "", "pipeline_version": ""
}
```

Salidas derivadas del JSON: `report.md` (ES), `mapa.png` (estático, 2 variantes: general y prensa), `hilo.txt` (borrador para redes, requiere click humano para publicar — único paso manual permitido), `adm2.csv`.

---

## 4. Arquitectura y stack

### 4.1 Diagrama lógico

```
[USGS feed 4.5_hour GeoJSON] ──(cron GH Actions */10, best-effort)──▶ P1 TRIGGER
   │ filtro bbox LATAM + M≥5.5 + dedupe vs event_state
   ▼
P1 crea/actualiza event_state ──▶ dispara P2 por repository_dispatch
   ▼
P2 IMPACTO (job por evento, idempotente por (usgs_id, shakemap_version)):
   detail feed → products{shakemap, ground-failure}
   cont_mmi GeoJSON → polyfill H3 r8  ──join── exposure_h3 (DuckDB + ext. h3/spatial)
   Ground Failure rásters → muestreo por celda
   ▼
P3 REPORTE: report.json → report.md + mapa.png + csv + parquet + pmtiles del evento
   commit a repo `reports/` + GitHub Release + página en visor + hilo.txt
   ▼ (re-ejecución automática si aparece ShakeMap v(n+1); reporte marcado "actualiza a v(n+1)")

[Trimestral] P0 EXPOSICIÓN: descarga fuentes → build exposure_h3 por país → Release versionado
[Por evento con imagen abierta] P4 BRIGADA: STAC → tiles → etiquetado HIL → fine-tune → inferencia → GeoPackage → HDX
```

### 4.2 Stack (fijado)

- **Lenguaje:** Python 3.12, gestionado con `uv`; `ruff` + `mypy` estricto en CI.
- **Geo-cómputo:** DuckDB ≥1.1 con extensiones `spatial` y `h3` (community); `rasterio` para grid/rásters de Ground Failure y GHS-POP; `h3` (python) para polyfill de contornos; `exactextract` opcional para agregación ráster→celda de alta fidelidad (T0.7: benchmark vs. muestreo simple; criterio: <1% de diferencia en pop nacional).
- **Tiles:** `tippecanoe` → **PMTiles** (un archivo, servible desde Pages/R2, cero servidor).
- **Visor:** MapLibre GL JS + `pmtiles` protocol, sitio estático (Astro o HTML plano), i18n ES primero. Sin llaves de API en el camino crítico. (Demo ArcGIS Maps SDK 5.0 + GeoParquet: bienvenida como pieza de divulgación separada.)
- **Mapa estático del reporte:** `matplotlib` + `contextily` con teselas de atribución compatible, o render headless de MapLibre (T0.8: elegir por calidad/tiempo).
- **Orquestación:** GitHub Actions. Reglas duras validadas: intervalo mínimo 5 min; demoras de 5–30 min documentadas y normales; **workflows programados se desactivan a los 60 días sin actividad** y quedan deshabilitados por defecto en forks; solo corren desde la rama por defecto. Mitigaciones obligatorias: `workflow_dispatch` en todos los workflows, workflow keepalive (commit/API antes del día 45), monitor externo tipo healthchecks.io con alerta si el trigger no reporta latido en 30 min. **Upgrade path documentado (no Fase 0):** cron externo (p. ej. Cloudflare Workers) → `repository_dispatch` para bajar latencia p95.
- **Estado:** archivos JSON en el repo (auditable por git) — no base de datos viva.
- **Publicación:** GitHub Releases (datasets), GitHub Pages (visor y reportes), HDX (paquete por evento mayor, con metadatos HXL en los CSV — T1.3 validar plantillas HDX).
- **Brigada (Fase 2):** toolkit `microsoft/building-damage-assessment` (MIT) + PyTorch; etiquetado distribuido con la herramienta del toolkit; cómputo de fine-tuning en Colab/Kaggle/donado (fuera del camino crítico del reporte automático).

### 4.3 Estructura del repositorio

```
centinela/
├─ pipelines/            # p0_exposure, p1_trigger, p2_impact, p3_report, p4_brigada
├─ schemas/              # JSON Schema del report + esquemas parquet + contratos USGS
├─ data/manifests/       # vintages por país (fuente, url, licencia, hash, fecha)
├─ events/               # event_state por evento (JSON, versionado)
├─ reports/              # salidas publicadas (md+json+png+csv)
├─ site/                 # visor estático
├─ tests/                # unit/, integration/, golden/ (10-ago CO, 24-jun VE), fixtures/
├─ .github/workflows/    # trigger.yml, impact.yml, exposure_quarterly.yml, keepalive.yml, site.yml
├─ ATTRIBUTION.md  LICENSES/  GOVERNANCE.md  DISCLAIMER.md  CONTRIBUTING.md
```

---

## 5. Requerimientos

### 5.1 Funcionales

- **RF-01** El sistema detecta todo evento M≥5.5 dentro del bbox LATAM (12°N ampliado a 33°N para MX; −56°S; −118°O; −34°E) en ≤ 30 min p95 desde su aparición en el feed.
- **RF-02** Deduplica por `usgs_id`; tolera reinicios (idempotencia por `(usgs_id, shakemap_version)`).
- **RF-03** Si no hay ShakeMap disponible aún, publica reporte "preliminar sin ShakeMap" (solo epicentro + exposición en radios de 25/50/100 km) y reintenta cada 30 min hasta 6 h.
- **RF-04** Al detectar nueva versión de ShakeMap o Ground Failure, re-emite el reporte con número de versión incremental y changelog de deltas ("pop MMI≥7: 340k → 355k").
- **RF-05** Todo reporte incluye: totales por banda MMI (≥6, ≥7, ≥8), desglose etario en MMI≥7, top-15 municipios, exposición a deslizamiento/licuefacción (Ground Failure), referencia PAGER, banda de discrepancia poblacional, versiones y vintages, disclaimers fijos, y enlaces de descarga.
- **RF-06** Reporte en español neutro con topónimos oficiales del país; cifras redondeadas con regla explícita (2 cifras significativas en prosa; exactas en CSV/parquet).
- **RF-07** El hilo para redes se genera como borrador; su publicación requiere acción humana (control editorial, evita alarmar con falsos disparos).
- **RF-08** `make country ISO=XXX` reconstruye el activo de exposición del país end-to-end desde URLs públicas del manifest.
- **RF-09** El visor lista eventos, muestra coropletas r7/r6 por MMI y exposición, ficha por municipio, y botón de descarga por capa; funciona sin backend.
- **RF-10** (Fase 2) La brigada produce GeoPackage con esquema por edificación: `gers_id, geom, damage_class{no_damage,damaged,cloud,unknown}, confidence, scene_id, model_version` — interoperable con el formato Microsoft/Overture.

### 5.2 No funcionales

- **RNF-01 Costo:** camino crítico operable con USD 0/mes (repos públicos: Actions gratis; Pages; Releases). Presupuesto opcional Fase 1: R2 (~USD 0 egress) para datasets grandes.
- **RNF-02 Latencia:** O1. Medida y publicada (página `/status` con historial de latidos y latencias — la transparencia es parte del producto).
- **RNF-03 Robustez a esquema:** contratos JSON Schema para las respuestas USGS consumidas; si el contrato falla, el pipeline degrada a reporte preliminar y abre issue automático, nunca publica datos corruptos.
- **RNF-04 Trazabilidad:** todo número publicado es re-derivable: reporte → manifest → hashes de insumos.
- **RNF-05 Accesibilidad:** reporte legible en móvil 3G (md + png < 500 KB); visor con presupuesto < 3 MB carga inicial.
- **RNF-06 Gobernanza:** licencias por cubo (§2.4); código Apache-2.0; datos derivados: núcleo CC BY 4.0, capas con OSM/Overture-buildings ODbL.
- **RNF-07 Seguridad:** sin secretos en el camino de lectura; tokens solo para publicar; forks no ejecutan schedules (comportamiento por defecto de GitHub, deseable aquí).

---

## 6. Plan de pruebas

### 6.1 Unitarias (pytest, cobertura objetivo ≥85% en `pipelines/`)

- Polyfill de contornos MMI → conjunto H3 (casos: polígono con hueco, multipolígono, antimeridiano no aplica pero frontera costera sí).
- Agregación ráster→H3: suma nacional GHS-POP vs. valor oficial JRC del país (tolerancia <1%).
- Prorrateo fronterizo hex↔adm2: la suma por municipios == suma nacional (invariante).
- Redondeo y formato de cifras del reporte.
- Parsers de `products.shakemap` y `products.ground-failure` contra fixtures reales congeladas.

### 6.2 Contrato e integración

- JSON Schema sobre respuestas grabadas (VCR/cassettes) de feed, detail y productos; test nocturno contra el feed vivo que solo alerta (no bloquea) ante drift.
- Pipeline P1→P3 completo contra fixtures en <10 min de CI.

### 6.3 Golden tests (regresión, corren en cada PR)

- **G1 — Chocó 10-ago-2026 · `us6000tjl2`:** M7.4, 2026-08-10T12:34:28Z, 5 km al S de San José del Palmar, **110 km de profundidad**, PAGER rojo. ShakeMap y Ground Failure con **7 versiones cada uno**, todas obtenibles con `includesuperseded=true` sobre FDSN. Aserciones: (a) el trigger habría disparado — **ya verificado contra el evento real**; (b) `pop_mmi7p` estable ±0.5% entre commits; (c) top-15 municipios estable; (d) el reporte v-final referencia la última versión de ShakeMap.
- **G2 — Venezuela 24-jun-2026 · `us6000t7zp` + `us6000t7zc`:** M7.5 (Catia La Mar, ShakeMap v14) y M7.2 (San Felipe, ShakeMap v9), ambos a 10 km de profundidad y **separados por 33 segundos**. Ídem G1; además valida bbox y el manejo de evento doble: dos `usgs_id` distintos, dos reportes, con áreas de intensidad que se solapan. El sistema no debe fusionarlos ni tratar el segundo como réplica.
- **G3 — Evento sin Ground Failure publicado:** el reporte omite la sección con nota explícita, no falla. (Nota: Chocó, pese a sus 110 km, **sí** tiene Ground Failure, así que G3 necesita otro evento o una fixture sintética.)

### 6.4 Calidad de datos (asserts SQL en DuckDB, corren en P0 y P2)

- Sin celdas con `pop_total < 0` ni `NULL` en columnas NOT NULL; `bld_count=0 ∧ pop_total>500` → flag `revisar` (posible hueco de Overture en asentamiento informal, se publica el flag, no se oculta).
- Discrepancia GHS-POP vs WorldPop por celda > 200% → flag.
- Totales país vs. referencia oficial del manifest (±1%).
- `impact_adm2`: todo municipio con `mmi_max≥6` existe en `admin_lookup` (crosswalk completo).

### 6.5 Operacionales / caos

- Simulacro mensual automatizado: `workflow_dispatch` con evento sintético M6.9 → verifica latencia interna y artefactos.
- Kill-test de idempotencia: matar P2 a mitad y relanzar → sin duplicados ni estado corrupto.
- Monitor externo: si el trigger no late en 30 min → alerta (correo/Telegram del equipo). Alerta también ante el correo de GitHub de desactivación por inactividad (aunque el keepalive debe impedirlo).
- Backtest de latencia trimestral: distribución real de demoras del cron publicada en `/status`.

### 6.6 Criterio de aceptación de la brigada (Fase 2)

- Sobre escena con vectores Copernicus EMS como verdad: precisión y recall ≥0.75 por clase binaria daño/no-daño antes de publicar; siempre publicar la matriz de confusión junto al GeoPackage. (Referencia alcanzable: 0.86/0.80 del flujo semilla.)

---

## 7. Plan de ejecución

> Calendario asumido: ~6–8 h/semana de Sebastián + contribuidores de la comunidad. Cada fase cierra con demo pública en la comunidad (el proyecto ES el contenido).

### Fase 0 — "Late" (semanas 1–4) · Colombia, reporte automático mínimo

| Semana | Entregables | Tareas de verificación pendientes |
|---|---|---|
| 1 | Repo + CI + esqueleto ✅; **T0.1** ✅ `usgs_id` identificados y confirmados; **T0.2** congelar productos (fixtures golden); contrato JSON Schema del feed ✅ | T0.4 ✅ CC BY 4.0 |
| 2 | P0 Colombia: `exposure_h3` (pop + etario + edificios + vías) + crosswalk DIVIPOLA + manifest ✅; Release `exposure-col-v0.1` | T0.5 ✅ y T0.6 ✅ resueltas en contra; T0.7 benchmark exactextract |
| 3 | P1 trigger + P2 impacto + G1/G2 en verde; keepalive + monitor externo | T0.8 render de mapa |
| 4 | P3 reporte (json/md/png/csv) + página estática mínima; **demo: backtest público del 10-ago** ("esto habría salido a las 08:3X") + primer reporte real con réplica/sismo de la región | — |

**Gate de salida F0:** G1 y G2 verdes; un reporte real publicado end-to-end sin intervención; latencia medida y publicada.

### Fase 1 — "Región" (meses 2–3)

- Países: MX, PE, EC, CL, VE, GT (modelo de **mantenedor por país**: una persona responsable de las capas nacionales y topónimos; CONTRIBUTING.md lo define).
- Visor completo (PMTiles r7/r6, ficha municipal, /status).
- Salud/educación nacionales donde existan; aeropuertos; HDX + HXL para eventos mayores (T1.3).
- Redes nacionales (T1.1) para contexto, sin tocar el disparador.
- **Gate F1:** 7 países reconstruibles con `make country`; ≥4 reportes reales publicados; 2+ mantenedores país activos que no sean Sebastián.

### Fase 2 — "Brigada" (meses 4–6)

- Pipeline semilla Pereira/Manizales sobre escenas Vantor "Clear" (el proyecto ya definido) como acta fundacional de la brigada; publicación en HDX + escrito en español con la auditoría como introducción.
- Protocolo de activación de brigada (quién decide, checklist, licencias por evento), rama de pesos limpia vs NC (T2.4), validación con Copernicus EMS (T2.1).
- Ejercicio de etiquetado comunitario (mapatón de etiquetas, con OSM-CO/YouthMappers invitados — puente natural con el ecosistema HOT ya activo en el país).
- **Gate F2:** un GeoPackage publicado con métricas; protocolo probado en simulacro.

### Fase 3 — "Institucional" (mes 6+, oportunista)

- Presentar el sistema a la Mesa Geomática de la UNGRD y pares regionales (CENAPRED, SENAPRED, INDECI) como insumo abierto, no como reemplazo.
- Puerta a embeddings: columnas de embedding por celda (AlphaEarth/Major TOM agregados a H3 como línea base; T3.1 verificar términos de redistribución) — la arquitectura ya lo permite sin refactor.

### Riesgos principales

| Riesgo | Prob. | Impacto | Mitigación |
|---|---|---|---|
| Abandono post-lanzamiento (riesgo #1 real) | Media | Alto | 95/5 automático; keepalive; mantenedores país; el simulacro mensual corre solo |
| Demoras del cron degradan O1 | Alta | Medio | SLO honesto publicado; upgrade path a cron externo documentado |
| Drift de esquema USGS | Baja | Alto | Contratos + degradación a preliminar + issue automático |
| Falso disparo / cifra alarmista | Media | Alto | Umbral M≥5.5; publicación de hilo con humano; lenguaje de exposición, nunca de daño |
| Huecos de exposición (Chocó rural, informalidad) | Alta | Medio | Flags de calidad publicados; banda GHS vs WorldPop; nunca ocultar el vacío |
| Contaminación de licencias | Media | Alto | Tres cubos físicos; CI que rechaza mezclas (lint de manifest); guardia extra contra dos copyleft incompatibles |
| Fuente upstream que retira el vintage fijado | **Alta** (confirmada en Overture) | Medio | El Release propio del activo con su `sha256` es la copia que sostiene RNF-04, no la URL de origen |
| Fuente que empieza a exigir credenciales | Media | Medio | O4 es criterio de admisión: una fuente con API key obligatoria no entra al camino crítico (caso healthsites.io) |
| Percepción de competir con SGC/UNGRD | Media | Medio | No-objetivos públicos; disclaimers; Fase 3 de acercamiento formal |

---

## 8. Pendientes de verificación (honestidad metodológica)

**Cerradas en v0.10** (evidencia y método en `VERIFICACIONES.md`): T0.1 `usgs_id` de Chocó y Venezuela · T0.4 MGN-DANE es CC BY 4.0 · T0.5 REPS resuelta en contra · T0.6 MEN resuelta en contra.

**Cerradas también:** T0.2 (productos de G1/G2 congelados, sin `libcomcat`) · T0.8 (**matplotlib solo, sin teselas de fondo**: evita una descarga en el camino crítico, una licencia de terceros dentro de un artefacto propio, y cualquier llave de API) · T0.9 (el shapefile municipal es `MGN_ADM_MPIO_GRAFICO.shp`, y se extrae del ZIP de 3,39 GB por peticiones de rango: 100 MB en 12 segundos).

**Abiertas:** T0.7 (benchmark exactextract), T1.1 (redes nacionales), T1.3 (HDX/HXL), T2.1–T2.4 (brigada), T3.1 (embeddings). Ninguna bloquea la operación.

**Cerrada el 23-ago-2026:** T1.2 (OurAirports), citando la declaración de la página de datos y The Unlicense del repositorio.

*Validación regional de fuentes, 23-ago-2026:* una petición real por fuente y país sobre **los 19 países de LATAM hispanohablante más Brasil**. Los cuatro insumos nacionales existen para todos: WorldPop age-sex (20 bandas cada uno), WorldPop total, `cod-ab-<iso3>` (CC BY-IGO) y los extractos `hotosm_<iso>_health_facilities` y `hotosm_<iso>_education_facilities` (ODbL). Irregularidades registradas: cinco países (COL, ARG, BRA, PRY, URY) no publican GeoJSON en su COD-AB y caen a SHP, y solo Colombia publica varios recursos SHP en el mismo dataset — de ahí el campo `hdx_resource` del manifest.

*Verificado con documentación primaria y peticiones reales el 23-ago-2026: productos USGS contra el evento real de Chocó (`us6000tjl2`, 7 versiones de ShakeMap y de Ground Failure, `includesuperseded` sobre FDSN); listado del bucket de Overture y sus subtipos; rásters de GHS-POP R2023A época 2025 en sus dos proyecciones; árbol completo de WorldPop hasta los 62 rásters age-sex de Colombia 2025; licencia del Geoportal DANE y descarga directa del MGN 2025; datasets REPS y MEN vía la API de Socrata de datos.gov.co (columnas y licencia); catálogo de HDX para HOTOSM, healthsites y COD-AB de los siete países de Fase 1. El registro con método y evidencia está en `VERIFICACIONES.md`; las restricciones de GitHub Actions siguen como en v0.9.*
