# Registro de verificaciones

Cierre de las tareas ⚠️ de §8 de la especificacion. Cada entrada dice **como**
se verifico, no solo el resultado: una verificacion que no se puede repetir no
sirve de nada dentro de seis meses.

Fecha de esta ronda: **23 de agosto de 2026**. Metodo: peticiones reales a las
fuentes primarias (listados S3, indices HTTP, API de Socrata de datos.gov.co,
paginas de licencia de los publicadores).

---

## Resumen

| Tarea | Estado | Resultado |
|---|---|---|
| T0.4 MGN-DANE | ✅ resuelta | **CC BY 4.0**, uso comercial y redistribucion permitidos |
| T0.5 REPS | ⚠️ resuelta en contra | Sin coordenadas y **CC BY-SA 4.0**: fuera del activo |
| T0.6 MEN | ⚠️ resuelta en contra | Idem REPS |
| T1.2 OurAirports | 🟡 parcial | Disponibilidad verificada; texto de licencia sin citar |
| Overture release | ✅ corregida | `2026-08-19.0`; el bucket solo guarda **dos** releases |
| WorldPop age-sex | ✅ mejora | Hay desglose **para 2025**: cae un supuesto de la espec |
| WorldPop total | ✅ corregida | Ruta real hallada |
| GHS-POP | ✅ confirmada | Ambas variantes sirven |

---

## Hallazgos que cambian el diseno

### 1. WorldPop publica estructura etaria para 2025 (mejora)

**Lo que decia la espec (§2.2):** el desglose por edad y sexo solo existe para
2020, de donde salia la limitacion documentada *«proporciones de 2020 aplicadas
sobre totales 2025 de GHS-POP (supuesto de estructura estable)»*, declarada en
los metadatos de cada reporte.

**Lo verificado:** el release `Global_2015_2030/R2025A` publica age-sex
constrained por epoca anual hasta 2026. Para Colombia, 2025, 100 m constrained
hay **62 rasters** (`col_f_00`…`col_m_80`, mas los totales `col_T_F` y
`col_T_M`).

```
https://data.worldpop.org/GIS/AgeSex_structures/Global_2015_2030/R2025A/2025/COL/v1/100m/constrained/
```

**Consecuencia:** el supuesto de estructura etaria estable desaparece. Es una
limitacion menos que declarar en cada reporte, y la cifra de poblacion de 65+
en MMI≥7 —una de las mas sensibles del producto— deja de arrastrar cinco anos
de desfase.

### 2. Overture conserva solo dos releases (riesgo nuevo)

**Lo verificado:** el listado del bucket, no truncado, contiene exactamente dos
prefijos: `release/2026-07-22.0/` y `release/2026-08-19.0/`.

**Consecuencia:** fijar el release explicito —decision correcta y que se
mantiene— da reproducibilidad **del calculo**, no **de la descarga**. Pasados
unos dos meses la URL del manifest deja de existir y nadie puede rehacer el
build desde cero. RNF-04 se sostiene solo si el activo construido se publica
como Release propio con su `sha256`; esa copia, no la URL de Overture, es la
que hace re-derivable un numero publicado.

Subtipos correctos, tambien verificados: `theme=buildings/type=building` (no
`building_part`, que inflaria `bld_count`), `theme=transportation/type=segment`
y `theme=divisions/type=division_area`.

### 3. REPS y MEN no pueden entrar al activo (dos bloqueos independientes)

| | REPS salud | MEN educacion |
|---|---|---|
| Dataset | `c36g-9fc2` | `cfw5-qzt5` |
| Filas | 76.821 sedes | 588.334 (multi-anio) |
| Actualizado | 2026-04-17 | 2025-11-13 |
| Coordenadas | **ninguna** | **ninguna** |
| Llave geografica | `municipiosede` (DIVIPOLA) + direccion | `cod_dane_municipio` + direccion |
| Licencia | **CC BY-SA 4.0** | **CC BY-SA 4.0** |

**Bloqueo (a) — sin geometria.** Ninguno de los dos publica latitud/longitud.
Sin coordenadas no hay celda H3 a la que asignarlos. La espec preveia
geocodificar «la parte del REPS que viene sin coordenadas»; en realidad es el
dataset entero, y geocodificar 76.821 direcciones no es una tarea de la semana 2.

**Bloqueo (b) — copyleft incompatible.** Ambos son CC BY-SA 4.0, no «abierta
gov» como asumia la espec. CC BY-SA 4.0 y ODbL son **ambas** share-alike y
**mutuamente incompatibles**: cada una exige que el derivado se publique bajo
ella, y no existe licencia que satisfaga a las dos. Meter REPS en la misma
tabla que las edificaciones de Overture produce un `exposure_h3` que no se
puede licenciar bajo ninguna licencia.

**Decision aplicada:** `health_count` y `edu_count` por celda salen de
OpenStreetMap, la unica fuente con coordenadas. REPS y MEN pasan a ser
referencia de **completitud municipal** —cuantas sedes dice el registro oficial
que hay en el municipio X frente a cuantas tiene OSM— en una tabla aparte bajo
CC BY-SA. Esa comparacion es ademas mas honesta que un conteo: convierte el
hueco de OSM en una cifra publicada en vez de en un silencio.

**Guardia en codigo:** `resolve_bucket()` ahora rechaza la combinacion
ODbL + CC BY-SA 4.0 con un error explicito. La regla de los tres cubos por si
sola no atrapaba este caso, porque ambas licencias caen del lado
«redistribuible».

---

## Detalle por tarea

### T0.4 — Marco Geoestadistico Nacional (DANE) · resuelta

El Geoportal DANE publica su informacion geografica bajo **CC BY 4.0**: permite
uso comercial y redistribucion «en todos los medios y formatos actualmente
conocidos o por crearse», y pide citar *«Departamento Administrativo Nacional
de Estadistica - DANE: www.dane.gov.co»*.

Descarga directa verificada (HTTP 206, `application/zip`):

```
https://geoportal.dane.gov.co/descargas/mgn_2025/MGN2025_00_COLOMBIA.zip   3,39 GB
https://geoportal.dane.gov.co/descargas/mgn_2025/MGN2025_DPTO_POLITICO.zip 12,5 MB
https://geoportal.dane.gov.co/descargas/mgn_2025/MGN2025_CLASE.zip          120 MB
```

**Pendiente acotado:** existen entregas por nivel mucho mas livianas que el
archivo nacional, pero el nombre exacto del nivel municipal no se deduce
probando (`MPIO`, `MPIO_POLITICO`, `MUNICIPIO`… todos 404). Hay que leerlo del
geoportal antes del primer build: bajar 3,4 GB cada trimestre para quedarse con
1.100 poligonos municipales es desperdicio puro.

### T0.5 — REPS · resuelta en contra

Ver «Hallazgos» arriba. Dataset correcto identificado (`c36g-9fc2`,
*Registro Especial de Prestadores y Sedes de Servicios de Salud*), pero no
sirve para el proposito que la espec le daba.

### T0.6 — Sedes educativas MEN · resuelta en contra

Dataset nacional identificado (`cfw5-qzt5`,
*MEN_ESTABLECIMIENTOS_EDUCATIVOS_PREESCOLAR_BASICA_Y_MEDIA*). Ademas de los dos
bloqueos, tiene columna `a_o`: las 588.334 filas son registros por
establecimiento **y anio**, asi que habria que filtrar por el anio vigente
antes de contar nada.

### T1.2 — OurAirports · parcial

`https://davidmegginson.github.io/ourairports-data/airports.csv` responde
HTTP 200 con 12,7 MB. Falta citar el texto exacto de la declaracion de dominio
publico del proyecto; el manifest lo dice asi en vez de darlo por hecho.

### GHS-POP · confirmada

Ambas variantes de la epoca 2025 sirven (HTTP 206): Mollweide 100 m
(`…_54009_100_V1_0.zip`, la del manifest) y WGS84 3 segundos de arco
(`…_4326_3ss_V1_0.zip`), esta ultima util si reproyectar desde Mollweide
resulta ser el cuello de botella de P0.

---

## Sigue abierto

| Tarea | Que falta |
|---|---|
| T0.1 / T0.2 | `usgs_id` oficiales de Choco y Venezuela; congelar productos |
| T0.7 | Benchmark `exactextract` vs muestreo simple (<1 % en poblacion nacional) |
| T0.8 | Motor del mapa estatico: matplotlib+contextily vs MapLibre headless |
| T0.4 (resto) | Nombre del archivo MGN a nivel municipal |
| T1.1 | Formatos y terminos de las redes sismologicas nacionales |
| T1.3 | Plantillas HDX y validacion de las cabeceras HXL |
| T2.1–T2.4 | Todo lo de la brigada de imagen (Fase 2) |
| T3.1 | Redistribucion de embeddings (Fase 3) |
