# Auditoría de septiembre de 2026: qué se cerró y qué queda

Auditoría integral del repositorio corrida el 5-sep-2026 con orquestación
multiagente. **187 hallazgos verificados**: 9 críticas, 48 altas, 83 medias y
47 bajas. Se reparó fallo por fallo, cada uno con su guardia, en la rama
`auditoria-2026-09` — 32 commits desde `b3d5557`.

Este documento existe porque el detalle de los hallazgos vivía fuera del
repositorio. Lo que queda pendiente está aquí abajo, con fichero y línea, para
que se pueda retomar sin volver a correr la auditoría.

---

## Lo cerrado

**Las 9 críticas y las 48 altas están cerradas**, todas con prueba que las fija.
De las medias y bajas se cerraron además las que caían dentro de esas mismas
familias, y las de documentación, seguridad y procedencia que se persiguieron
explícitamente.

Las familias, en el orden en que se repararon. Los asuntos van **verbatim**,
sin acentuar, porque son citas del historial y no prosa de este documento:

- `caac55e` — Las dos funciones geodesicas leian (lat, lon) y se las llamaba al reves
- `571dbd7` — Las bandas etarias eran conteos de otro modelo de poblacion metidos en la fila
- `03acaa0` — El activo publica veintiseis columnas y el guardia miraba diez expresiones
- `0ca1cc3` — Las veinte cifras nacionales se volcaban por posicion desde el SQL
- `4ff4309` — El serializador enumeraba doce claves de un modelo de diecinueve campos
- `d64fbd5` — Manta no salia en la tabla de municipios mas expuestos de su propio reporte
- `7302f94` — El CSV, la nota de superficie y el hilo seguian clavados en MMI>=7
- `8f80b2a` — El visor rodeaba en el mapa una banda que ninguna cifra del panel nombraba
- `3468397` — El vigia del visor podia salir en verde con la pagina caida y cerrar su alarma
- `f427707` — Seis ficheros vacios de FIRMS pasaban por corrida sana, y la merma no salia
- `af76067` — Un fallo tecnico se pintaba con el texto del cero legitimo
- `4bc49fa` — G4: el golden que recalcula. Los otros leian un JSON commiteado
- `01e0e55` — Cuatro pruebas verdes que no probaban lo que decian
- `1d46745` — El ancla del golden iba por otra version, y el digest no veia el .dbf
- `b0e1289` — Un guardia que pasaba por 16 caracteres, y un modulo cableado sin una prueba
- `0e08c88` — El numerador y el denominador eran de conjuntos distintos, en tres sitios
- `96a4a79` — FIRMS contaba dos veces la franja donde sus dos regiones se solapan
- `6cd5cea` — Una celda con 130 de 140 pixeles de roca publicaba «100 % pastizal»
- `6e5d703` — La lista de focos filtraba el foco entero y el mapa celda a celda
- `b5cc666` — La pagina de estado pintaba «incumple» comparando dos relojes distintos
- `64a5ba0` — Cuatro senales del vigia que se median y se quedaban en el log
- `75b3dbf` — Un codigo municipal repetido duplicaba toda la exposicion de su municipio
- `82bf779` — El sismo detectado se perdia por un fichero derivado, y dos alarmas nunca se abrieron (#99)
- `bbe9a6d` — El manifest prometia gobernar los bytes y el release de los vecinos estaba cableado (#100)
- `1ae0948` — El vintage publicado no habia tocado un solo byte, y el insumo caducaba antes que el cron (#101)
- `79d792d` — La licencia dejaba de existir en cuanto el dato salia del repositorio (#102)
- `2c65266` — El texto de un tercero podia ser un comando, y la documentacion enseñaba lo que no arranca (#103)
- `f5b1c20` — El visor rotulaba seis horas como veinticuatro y borraba capas que seguian dibujadas (#104)
- `594cbaf` — Agotar la ventana de seis horas borraba el sismo para siempre, y `pending` no es una alerta (#105)
- `5d492b5` — El esquema del detail no lo cargaba nadie, y el contraste con PAGER comparaba dos versiones (#106)
- `325102b` — Saca yang2021.html, que entro por un `git add -A` y no es del proyecto
- `f2dbade` — Un `jessee_2018_model.tif` podia ser en realidad un `godt_2008` (#107)

## Lo que queda abierto a propósito

Cuatro cosas necesitan algo que no se puede resolver desde dentro del
repositorio. Están en [`PENDIENTES.md`](../PENDIENTES.md) §2.0 con su porqué:

- **#52** · El arranque descarga y procesa entero el fichero de fuego —365 KB en el cable, 4,4 MB de JSON— y acto seguido 
  — sin tocar: diferirlo quita información de la tarjeta por defecto, y eso es decisión de producto
- **#57** · La tabla que va a instituciones enfrenta la cifra de CENTINELA del ShakeMap v8 contra la de PAGER del v7, y la
  — procedencia anotada y las dos tablas dicen de qué versión es cada columna; falta refrescarla
- **#67** · Doce workflows usan `astral-sh/setup-uv@v5` (etiqueta móvil de un tercero) en jobs cuyo GITHUB_TOKEN puede emp
  — mitigado con `persist-credentials: false` y dependabot; falta fijarlas por SHA
- **#132** · El visor carga maplibre y h3-js desde unpkg sin `integrity` (SRI) y sin CSP: quien controle esos dos ficheros 
  — CSP puesta y verificada en Chromium; falta `integrity` o servirlas desde `assets/`

Y la deuda que arrastra todo lo demás: **los diecinueve activos publicados se
construyeron con los fallos que esta auditoría arregló** — el bug de
coordenadas del esferoide, las bandas etarias sin reescalar, el denominador
corto de cobertura del suelo y el diccionario administrativo sin agrupar. Los
guardias nuevos detendrían hoy un build así, pero no arreglan los que ya están
publicados: hay que reconstruirlos con `exposure_quarterly.yml`.

## El apéndice: medias y bajas sin barrer

Quedan 105 hallazgos de severidad media o baja que **no se han
comprobado uno a uno**. Algunos cayeron dentro de las familias cerradas y ya no
aplican; la columna «fichero» dice si esa ruta se tocó en la rama, que es una
pista y no una respuesta. Es un punto de partida, no un inventario de lo que
sigue roto.

### Visor · interfaz (8)

| # | Sev | Dónde | Qué |
|---|---|---|---|
| 124 | media | `site/assets/app.js:3904`· | Si falla el estilo del mapa base, el aviso «Cargando el mapa» se retira a los 8 s y no queda ningun mensaje: rectangulo vacio y silencio |
| 125 | media | `site/assets/app.js:2065`· | «Área de afectación» nombra dos superficies distintas en el mismo panel, y la que se descarga no es la que se muestra |
| 128 | media | `site/assets/app.js:4632`· | En modo fuego, «no hay focos», «FIRMS no publico nada» y «incendios.json no se pudo leer» se dibujan exactamente igual: nada |
| 130 | media | `site/assets/status.js:104`· | En la página de estado, «se cumple» o «no se cumple» el objetivo se cifra solo en el color del número, y encima el valor va en horas contra un obje… |
| 131 | media | `site/assets/styles.css:1182`  | La tabla de cobertura pierde su semántica de tabla en móvil: `display: block` sobre el <table> tumba el rol y la asociación fila/columna |
| 184 | baja | `site/assets/status.js:105`· | El aviso de «la cadencia se come el objetivo» solo se pinta cuando no hay ningun reporte publicado; hoy ya hay dos, así que no puede aparecer nunca |
| 185 | baja | `site/index.html:200`· | La tarjeta «Ahora mismo» es una region aria-live completa que se reescribe entera en cada moveend del mapa |
| 186 | baja | `site/index.html:313`· | «El de Venezuela llegó a v14» esta escrito a mano en dos páginas y el reporte publicado va por v15 |

### hueco-4 (7)

| # | Sev | Dónde | Qué |
|---|---|---|---|
| 82 | media | `pipelines/common/status.py:211`· | RF-01 no se mide en ninguna parte, y la única cifra de latencia que se publica compara un tramo contra el objetivo de otro tramo |
| 94 | media | `pipelines/p2_impact/pipeline.py:765`· | `descargas` publica dos de los seis artefactos que el evento genera, y el esquema cierra la puerta a los otros: la malla H3 y los contornos no exis… |
| 100 | media | `pipelines/p3_report/changelog.py:66`  | El changelog de RF-04 es el diff de un solo paso y cualquier reproceso sin cambios lo borra: el reporte del Chocó publicó tres deltas y hoy publica… |
| 105 | media | `pipelines/p3_report/markdown.py:553`· | Los 27 reportes cierran diciendo «ver manifiesto enlazado» y no hay enlace en ninguna parte: `col-v0.6` es una cadena que no resuelve a ningún docu… |
| 129 | media | `site/assets/app.js:1910`· | RF-09 pide coropletas r7/r6, ficha por municipio y descarga por capa: r6 no existe en ninguna línea del repositorio y la ficha por municipio tampoco |
| 133 | media | `site/index.html:470`· | Los diecinueve manifiestos resuelven al cubo `odbl` y todo lo publicado es share-alike, pero el pie del visor y otros tres documentos ofrecen «dato… |
| 148 | baja | `Makefile:50`· | `make site` —el único comando para levantar el visor— lo sirve sin un solo reporte, y la pantalla resultante es idéntica a «todavía no hay nada pub… |

### Arquitectura (6)

| # | Sev | Dónde | Qué |
|---|---|---|---|
| 68 | media | `.github/workflows/trigger.yml:290`· | El manejador de conflictos de derivados está duplicado en dos workflows y ya divergió: el `checkout --theirs` que salva el historial de latidos sól… |
| 78 | media | `pipelines/common/constants.py:53`· | Siete constantes de `common/constants.py` no las lee nadie, en un módulo que promete que cambiar cualquiera de sus valores cambia el comportamiento… |
| 92 | media | `pipelines/p2_impact/pipeline.py:339`· | Diecinueve agregaciones escritas dos veces a mano en `SQL_IMPACT_ADM2` y `SQL_TOTALES`, con sólo dos vigiladas, y la fila se vuelca a `ImpactTotals… |
| 171 | baja | `pipelines/p3_report/csv_out.py:65`  | La misma lista de columnas vive en cinco sitios y el escritor del CSV descarta en silencio lo que no esté en el suyo |
| 175 | baja | `pipelines/p3_report/static_map.py:103`· | La rampa de intensidad está escrita en Python y en JavaScript, con la afirmación explícita de que son la misma y sin ninguna prueba que lo compruebe |
| 183 | baja | `site/assets/app.js:1040`· | La regla de la banda del ranking tiene cuatro implementaciones, tres de ellas en el visor y sin comentario que las ate a la del modelo |

### Numérico (6)

| # | Sev | Dónde | Qué |
|---|---|---|---|
| 104 | media | `pipelines/p3_report/markdown.py:272`· | El aviso de «hueco de mapeo» se mide sobre MMI>=7 mientras la tabla que anota publica MMI>=6: se calla en tres reportes que superan el mismo umbral… |
| 107 | media | `pipelines/p3_report/social.py:66`· | `hilo.txt` publica «Dentro de MMI>=7: 0. Edificaciones en MMI>=7: 0» en los trece eventos que no llegan a esa banda, contradiciendo el `report.md` … |
| 126 | media | `site/assets/app.js:5993`· | El globo de una celda con fuego omite arbustos y construido —las dos clases que P0 anadio por ser las decisivas en LATAM— y deja 373 celdas sin dec… |
| 166 | baja | `pipelines/p0_exposure/raster_categorico_h3.py:227`  | `lulc_*_pct` se publica como «porcentaje de la celda» pero el denominador excluye agua, suelo desnudo, nieve y musgo: una celda con 1 pixel de 148 … |
| 169 | baja | `pipelines/p1_trigger/observados.py:81`  | La capa de sismos observados redondea la magnitud a un decimal y puede publicar «M5,5» junto a la razon «M5.49 < umbral M5.5» |
| 173 | baja | `pipelines/p3_report/markdown.py:98`· | La tabla del reporte afirma que todas sus cifras van a dos cifras significativas y tres de sus filas no lo están |

### Actions · mantenimiento (5)

| # | Sev | Dónde | Qué |
|---|---|---|---|
| 58 | media | `.github/workflows/contract_drift.yml:40`· | contract_drift.yml abre una incidencia nueva cada noche y no cierra ninguna: es la única alarma del repositorio sin deduplicar ni auto-cerrar |
| 141 | baja | `.github/workflows/contraste.yml:87`· | contraste.yml interpola texto libre de workflow_dispatch dentro de `run:`, la clase de fallo que exposure_quarterly documenta y evita |
| 143 | baja | `.github/workflows/frescura.yml:96`· | La incidencia de frescura.yml culpa siempre a site.yml, aunque la causa sea un fichero congelado y republicar no arregle nada |
| 151 | baja | `docs/acciones/mantenimiento.md:17`· | Dos documentos de operación dibujan un paso de auto-republicación que frescura.yml no tiene y no puede tener |
| 157 | baja | `pipelines/common/frescura.py:306`  | El guardia de frescura calla si el fichero no esta: un fichero del visor que desaparece es invisible para la única alarma que lo vigila |

### CLI (5)

| # | Sev | Dónde | Qué |
|---|---|---|---|
| 75 | media | `pipelines/cli.py:793`· | El desempate por toponimo (`_emit_github_output("país", preferido)`) no lo lee ningun workflow: impact.yml sigue publicando con `candidatos[0]`, el… |
| 76 | media | `pipelines/cli.py:307`· | El código 2 de `contraste` no es exclusivo suyo: cualquier error de uso de argparse sale como «hay celdas sin activo» y contraste.yml se pone verde… |
| 153 | baja | `docs/pipelines/README.md:40`· | La documentación del pipeline ensena `centinela country --iso3 COL`, que no existe: el flag no esta declarado y el comando sale con 2 |
| 155 | baja | `pipelines/cli.py:57`· | `centinela trigger --dry-run` escribe `site/status.json`: el simulacro y `make trigger` reescriben la página de estado publicada y le añaden un lat… |
| 156 | baja | `pipelines/cli.py:321`· | `centinela reindexar` borra del índice publico los reportes ilegibles y devuelve 0: un reporte publicado desaparece del visor sin una sola alarma |

### Contratos (5)

| # | Sev | Dónde | Qué |
|---|---|---|---|
| 113 | media | `schemas/report-1.0.schema.json:103`· | El esquema del reporte no exige ni un solo campo en `totales`: `"totales": {}` es un report.json valido, y el contrato no distingue "nadie expuesto… |
| 114 | media | `schemas/report-1.0.schema.json:190`· | En top_municipios el esquema exige `pop_mmi7p` y deja `pop_banda` opcional; en 8 de 27 reportes la columna obligatoria vale cero y la opcional llev… |
| 152 | baja | `docs/arquitectura/contratos-de-datos.md:85`· | El documento que se declara "el contrato" describe un index.json de 21 entradas (hay 27) y omite `ground_failure_usgs` de las claves raíz de report… |
| 178 | baja | `schemas/report-1.0.schema.json:277`· | El esquema dice que `radios` solo aparece en reportes preliminares y que sustituye a `totales`; nueve reportes publicados lo traen con preliminar=f… |
| 179 | baja | `schemas/report-1.0.schema.json:297`· | `ground_failure_usgs` es el único objeto del esquema del reporte sin additionalProperties:false, en un contrato cerrado por todas partes |

### hueco-7 (5)

| # | Sev | Dónde | Qué |
|---|---|---|---|
| 61 | media | `.github/workflows/impact.yml:356`· | El único guardia automático contra «hay un sismo detectado y no hay reporte» sólo se dispara cuando SÍ hubo reporte |
| 62 | media | `.github/workflows/site.yml:92`· | site.yml es el único workflow que publica algo al público y el único sin camino de fallo: cuando el despliegue muere, no lo dice nadie |
| 73 | media | `docs/PUESTA_EN_MARCHA.md:253`  | El Paso 5 «probar el circuito completo» no es ejecutable en frío: sobre `events/` vacío el comando documentado falla y abre una incidencia automática |
| 150 | baja | `docs/PUESTA_EN_MARCHA.md:41`  | El único documento que describe el arranque está congelado en el 23-ago: su Paso 1 opera sobre un PR fusionado hace 1.181 commits y su cierre decla… |
| 165 | baja | `pipelines/p0_exposure/download.py:461`· | «Una descarga cortada no se repite» es falso para las dos rutas de ZIP: `extractall` escribe directo en el destino y la reanudación se conforma con… |

### P3 · mapas y topónimos (5)

| # | Sev | Dónde | Qué |
|---|---|---|---|
| 108 | media | `pipelines/p3_report/static_map.py:497`· | Un anillo anidado del mismo nivel —que el propio sistema define como un HUECO— se rellena otra vez y sale mas oscuro que la banda: 62 km² pintados … |
| 109 | media | `pipelines/p3_report/static_map.py:817`· | La separación de etiquetas se mide en 0,25 grados fijos e ignora el ancho del texto: dos municipios publicados salen con el nombre escrito uno enci… |
| 159 | baja | `pipelines/common/toponimos.py:122`  | Un toponimo que no encaja en ninguna forma se publica en inglés sin dejar rastro, y ya paso: «southern East Pacific Rise» esta en el titulo de un r… |
| 160 | baja | `pipelines/common/toponimos.py:117`  | `_REGION` fabrica un toponimo mitad español mitad inglés —«Región de Chile-Argentina border»— justo en la familia de lugares mas comun de los sismo… |
| 174 | baja | `pipelines/p3_report/static_map.py:776`· | La variante `prensa` no es 16:9 en 26 de los 27 eventos publicados: sigue siendo la misma imagen que `general` a 1,27x, que es la duplicación que e… |

### Pruebas · huecos (5)

| # | Sev | Dónde | Qué |
|---|---|---|---|
| 80 | media | `pipelines/common/http.py:108`  | HttpFetcher._get no se ejecuta en la suite: la traducción de 404 a RecursoAusenteError esta probada solo para download_to, no para get_json/get_byt… |
| 101 | media | `pipelines/p3_report/falla_de_terreno.py:35`· | pipelines/p3_report/falla_de_terreno.py: 43 sentencias, 0 % de cobertura — escribe en los 27 report.json publicados y traga cualquier excepción |
| 112 | media | `pipelines/p5_incendios/run.py:16`· | pipelines/p5_incendios/run.py: 56 sentencias, 0 % de cobertura, cero referencias en tests/ — es el módulo que publica site/incendios.json |
| 138 | media | `tests/unit/test_el_csv_cuadra_con_el_reporte.py:50`· | El guardia que verifica que el adm2.csv suma la cifra nacional solo mira 2 de las 25 columnas publicadas |
| 162 | baja | `pipelines/p0_exposure/crosswalk.py:294`· | load_admin_geometry no tiene prueba: las de geometría administrativa se montan su propia tabla admin_geom a mano, que es el fallo histórico de la c… |

### Visor · datos (5)

| # | Sev | Dónde | Qué |
|---|---|---|---|
| 119 | media | `site/assets/app.js:4935`· | La lista de focos filtra por foco entero y el mapa filtra celda a celda: con la ventana de 6 h anuncia 1.783 km2 ardiendo y dibuja 1.361 |
| 120 | media | `site/assets/app.js:3665`· | `cambiarEstiloBase` repone todas las capas menos el perímetro del foco: el panel sigue describiendo un incendio cuyo contorno el mapa acaba de perder |
| 121 | media | `site/assets/app.js:3381`· | Cada cambio de mapa base vuelve a registrar los oyentes de clic de epicentros, observados e incendios, que MapLibre conserva a traves de `setStyle` |
| 122 | media | `site/assets/app.js:4269`· | El filtro de país recorta la capa de sismos menores en el mapa pero no su tarjeta ni su lista: «10 sismos vistos» con un solo punto dibujado |
| 182 | baja | `site/assets/app.js:3140`· | El globo de la celda —la ficha que el fichero declara «el valor exacto»— redondea población y edificaciones al millar: 1.500 personas se publican c… |

### Actions · evento (4)

| # | Sev | Dónde | Qué |
|---|---|---|---|
| 65 | media | `.github/workflows/trigger.yml:316`· | El manejador de conflictos de trigger.yml no puede resolver NUNCA un conflicto en site/status.json: le falta el `git checkout --theirs` que impact.… |
| 66 | media | `.github/workflows/trigger.yml:144`· | `git log -1 -- <ruta>` sobre un checkout superficial ignora la ruta: el número de revisiones que publica /status se mide desde el commit de punta, … |
| 144 | baja | `.github/workflows/rezago.yml:157`· | El cuerpo de la incidencia de rezago.yml va indentado 10 espacios: GitHub lo renderiza como bloque de código y la receta de operación sale con las … |
| 145 | baja | `.github/workflows/simulacro.yml:45`· | La única alarma del simulacro mensual usa una etiqueta que ningun workflow crea y no tiene camino de respaldo: si el simulacro falla, no se abre la… |

### hueco-3 (4)

| # | Sev | Dónde | Qué |
|---|---|---|---|
| 81 | media | `pipelines/common/state.py:165`  | `needs_reprocessing` compara números de versión a través del eje contribuidor: si el preferido cambia de `us` v6 a Atlas v1, el reporte se congela … |
| 88 | media | `pipelines/p1_trigger/rezago.py:85`· | El vigía de rezago lee «el producto desapareció del detail» como «el reporte está al día»: `vigente=0` contra `publicado=11` no dispara nada y el e… |
| 95 | media | `pipelines/p2_impact/products.py:191`· | `_preferred` elige contribuidor y luego tira el `source`: «ShakeMap consumido: v1» no identifica ningún grid, y `us2000ahv0` está publicado sobre e… |
| 180 | baja | `scripts/freeze_event.py:30`· | El único script documentado para regenerar las fixtures golden no puede regenerarlas: su URL no lleva `includesuperseded`, escribe un fichero con o… |

### hueco-6 (4)

| # | Sev | Dónde | Qué |
|---|---|---|---|
| 115 | media | `scripts/freeze_event.py:30`· | La única herramienta documentada para crear una fixture golden pide el detail SIN `includesuperseded`: baja una sola versión y la prueba que la usa… |
| 117 | media | `scripts/freeze_event.py:39`· | El script escribe `detail.json` y ninguna prueba lee ese nombre; los cuatro ficheros que las fixtures golden sí usan no los produce ninguno |
| 118 | media | `scripts/freeze_event.py:51`· | Descarga los 116 contenidos del evento —241 MB solo el ShakeMap, con un `.hdf` de 62 MB— con `get_bytes`, y los escribe dentro del repositorio |
| 181 | baja | `scripts/freeze_event.py:52`· | Los nueve rásteres de Ground Failure que la herramienta descarga los borra `.gitignore` sin decir nada, y `hashes.json` los declara como parte de l… |

### P1 · vigía (4)

| # | Sev | Dónde | Qué |
|---|---|---|---|
| 87 | media | `pipelines/p1_trigger/feed.py:71`  | El dedupe es una comparación de cadenas: si USGS renumera el evento se publica un segundo reporte del mismo sismo, y un 'deleted' no se respeta |
| 154 | baja | `pipelines/cli.py:702`· | sin-país promete dejar el evento visible en observados y la poda lo tira si tiene mas de cinco días |
| 167 | baja | `pipelines/p1_trigger/feed.py:139`  | Una feature rota del feed desaparece sin dejar rastro publicado: parse_feed no devuelve cuantas descarto |
| 168 | baja | `pipelines/p1_trigger/observados.py:128`  | Tres módulos parsean el mismo sello ISO y solo uno normaliza la zona: un origen_utc sin Z tumba el trigger |

### P2 · impacto (4)

| # | Sev | Dónde | Qué |
|---|---|---|---|
| 60 | media | `.github/workflows/impact.yml:162`· | Cuando se agotan los candidatos, el reporte se publica contra el activo del primer país por área de caja: el CLI ya calcula el correcto y el workfl… |
| 93 | media | `pipelines/p2_impact/pipeline.py:374`· | El agregado municipal no aplica el corte MMI>=6 que si aplica el total nacional, y publica municipios por debajo del piso del reporte como si fuera… |
| 96 | media | `pipelines/p2_impact/run.py:701`· | Un municipio sin centroide se publica en el CSV con coordenadas (0, 0), justo lo contrario de lo que promete la docstring de la función |
| 98 | media | `pipelines/p2_impact/shakemap.py:85`  | El filtro que separa MMI de PGA/PGV lee una propiedad que el producto de USGS no tiene, así que no filtra nada |

### P3 · reporte (4)

| # | Sev | Dónde | Qué |
|---|---|---|---|
| 99 | media | `pipelines/p3_report/changelog.py:155`  | El changelog decide «que cambio» con un redondeo distinto del que la tabla publica: calla cambios visibles en salud y educación, y publica «68 → 68… |
| 102 | media | `pipelines/p3_report/markdown.py:272`· | El aviso «el conteo de edificaciones se queda corto» se calcula sobre MMI≥7 mientras la tabla publica MMI≥6: se silencia en los tres reportes donde… |
| 106 | media | `pipelines/p3_report/model.py:122`· | Cuatro personas y media cruzando MMI 7 tiran abajo el reporte entero: `banda_titular` decide con `> 0` y sin suelo |
| 172 | baja | `pipelines/p3_report/markdown.py:498`· | Un reporte preliminar publica ceros de deslizamiento y licuefacción y afirma haber contrastado WorldPop celda a celda, sin haber calculado ninguna … |

### Pruebas engañosas (4)

| # | Sev | Dónde | Qué |
|---|---|---|---|
| 137 | media | `tests/unit/test_csv_out.py:18`· | La prueba de la cabecera HXL compara el CSV escrito contra la misma constante con la que se escribió: ninguna etiqueta HXL esta fijada en toda la s… |
| 139 | media | `tests/unit/test_el_visor_se_republica.py:227`· | El guardia que debia avisar el día que un segundo workflow escriba reports/ pasa hoy por una coincidencia de 16 caracteres |
| 140 | media | `tests/unit/test_funciones_conectadas.py:124`· | El guardia contra funciones sin llamador indexa por nombre, así que tres pares de funciones homonimas se cubren mutuamente |
| 149 | baja | `PENDIENTES.md:55`· | PENDIENTES.md declara 21 pruebas saltadas y una sola causa; medido son al menos 75 y de dos ficheros distintos |

### Fallo silencioso (3)

| # | Sev | Dónde | Qué |
|---|---|---|---|
| 97 | media | `pipelines/p2_impact/run.py:443`· | Si falla la escritura de `celdas.json` el reporte se publica igual y el visor afirma "no hay nadie dentro que contar" al lado de un panel con millo… |
| 103 | media | `pipelines/p3_report/markdown.py:304`· | Dos reportes publicados explican sus ceros con una causa falsa: culpan a la geografía cuando lo que pasa es que el ShakeMap entero queda por debajo… |
| 170 | baja | `pipelines/p1_trigger/rezago.py:252`· | El vigilante de rezago convierte "no pude leer el manifiesto vigente" en "el activo esta al día" |

### hueco-2 (3)

| # | Sev | Dónde | Qué |
|---|---|---|---|
| 111 | media | `pipelines/p5_incendios/incendios.py:44`· | La única medición que justifica MAX_CELDAS = 60.000 quedó obsoleta el mismo día que se escribió: dice 13.031 celdas = 203 KB y hoy son 391 KB, y el… |
| 136 | media | `tests/integration/test_report_bundle.py:83`· | Dos pruebas verdes dicen «RNF-05» en su docstring y las dos cubren la mitad del requisito que si se cumple; la mitad del visor, que es la incumplid… |
| 177 | baja | `pipelines/p5_incendios/incendios.py:286`· | Si MAX_CELDAS llega a morder, el «grito» prometido es un _log.error que muere en el runner: no llega al código de salida, ni al resumen JSON, ni al… |

### P0 · activo (3)

| # | Sev | Dónde | Qué |
|---|---|---|---|
| 84 | media | `pipelines/p0_exposure/crosswalk.py:274`· | Nada obliga a que adm2_id sea único en admin_lookup, y el JOIN del ensamblaje duplica toda la población del municipio que se repita |
| 86 | media | `pipelines/p0_exposure/raster_categorico_h3.py:107`  | Los porcentajes de cobertura del suelo se renormalizan sobre seis clases y el suelo desnudo no es una de ellas: un pixel de matorral en el Altiplan… |
| 161 | baja | `pipelines/p0_exposure/build.py:150`· | El filtro final del activo ignora tres de las capas que carga: una celda con datos solo de WorldPop se descarta entera, y eso además estrecha la ba… |

### HTTP y estado (2)

| # | Sev | Dónde | Qué |
|---|---|---|---|
| 79 | media | `pipelines/common/frescura.py:310`  | Un `site/status.json` ilegible desaparece del informe de frescura en vez de ser la alarma: `revisar_vejez` traga el JSONDecodeError sin log ni hall… |
| 158 | baja | `pipelines/common/http.py:126`  | Los tres bucles de reintento de `http.py` duermen después del último intento: ocho segundos de espera antes de rendirse, sin nada que esperar |

### hueco-1 (2)

| # | Sev | Dónde | Qué |
|---|---|---|---|
| 135 | media | `tests/golden/test_g1_choco.py:226`· | La cifra congelada es del ShakeMap v7 y el fichero que la prueba lee va por v8: el golden ya absorbio en silencio el 70 % de su tolerancia, por un … |
| 187 | baja | `tests/golden/README.md:30`  | El README de los goldens sostiene que las aserciones numericas están saltadas a la espera del activo de Colombia y que falta congelar los contornos… |

### hueco-5 (1)

| # | Sev | Dónde | Qué |
|---|---|---|---|
| 134 | media | `site/index.html:470`· | El visor y la página de estado declaran «Datos del núcleo bajo CC BY 4.0» cuando el cubo core no tiene ni un solo artefacto publicado |

### P5 · incendios (1)

| # | Sev | Dónde | Qué |
|---|---|---|---|
| 176 | baja | `pipelines/p5_incendios/focos_h3.py:105`  | El 43 % de las detecciones de baja confianza desaparece sin dejar rastro, y `detecciones_baja` se lee como si fuera todo lo descartado |

`·` marca los ficheros que la rama tocó por otro motivo: conviene mirar si el
hallazgo sigue en pie antes de trabajarlo. Los títulos son los que emitió la
herramienta de auditoría, transcritos tal cual.

---

## Cómo se validó cada reparación

En este orden, sin saltarse ninguno:

```
uv run ruff format .
uv run ruff check .
uv run mypy pipelines
uv run pytest -q -p no:randomly
uv run pytest tests/visor -m visor      # 144 en Chromium
```

Y actualizar el recuento de pruebas en `README.md`, `PENDIENTES.md` y
`docs/CLEAN_CODE.md` — hay guardia sobre los tres.

## La lección que más se repitió

**Un guardia que empareja texto plano contra un fichero acaba aprobándolo por su
documentación.** Pasó siete veces durante esta auditoría. La última fue la más
instructiva: el comentario que explicaba el arreglo contenía la cadena que el
guardia buscaba, así que la lista de parámetros se quedó vacía — y pytest eso lo
enseña como un salto, no como un fallo. El guardia desaparecía sin ponerse rojo.

Antes de escribir un guardia textual: filtrar las líneas de comentario, y
comprobar que la lista de parámetros no puede quedarse vacía en silencio.
