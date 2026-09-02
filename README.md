# CENTINELA

**Sistema abierto de exposición sísmica automatizada para América Latina.**

Ante cualquier sismo relevante en la región, CENTINELA publica un reporte de
**exposición**: cuántas personas, edificaciones, escuelas, hospitales y
kilómetros de vía quedan dentro de cada franja de intensidad sísmica, por
municipio y por celda H3, con datos descargables y en español.

> **Exposición no es daño.** Este sistema no es una alerta temprana, no estima
> víctimas, no dictamina habitabilidad y no reemplaza a los servicios
> geológicos ni a las unidades de gestión del riesgo. Ver
> [`DISCLAIMER.md`](DISCLAIMER.md).

**[Ver el visor](https://sforero77.github.io/CENTINELA/)** · [un reporte de
ejemplo](https://sforero77.github.io/CENTINELA/reports/us6000tjl2/) ·
[`DISCLAIMER.md`](DISCLAIMER.md)

### Dos palabras que este documento usa todo el rato

**MMI** es la escala **Mercalli Modificada**, de I a XII, y mide **la sacudida
en un sitio**: lo que se sintió y lo que puede romperse allí. No es la magnitud.
La magnitud —M7,4— es una sola cifra para el sismo entero, y la intensidad es un
mapa: el mismo M7,4 deja MMI 8 en un valle y MMI 5 a cien kilómetros. Confundir
las dos es el error de lectura más caro que este sistema puede provocar, porque
lleva a repartir ayuda por la cifra equivocada. Aquí las bandas se escriben
literales: **MMI≥7** significa intensidad 7 o más, no «alrededor de 7».

Un **activo de exposición** es el otro término: una tabla ya construida, celda a
celda, de cuánta gente e infraestructura hay en cada punto del país. Es lo que
permite que un mapa de intensidad se convierta en cifras el mismo día en vez de
en semanas, y construirlo es la mitad del trabajo de este proyecto.

## Por qué existe

En el sismo de San José del Palmar (M7,4, 10 de agosto de 2026) el país supo
pronto **cuánta** gente estaba en la zona de intensidad fuerte: PAGER lo estimó
en media hora. Lo que tardó días fue saber **dónde**, con qué infraestructura y
por municipio. Las cifras oficiales oscilaron durante semanas. Siete semanas
antes, en Venezuela, pasó lo mismo.

Capacidad regional hay, y conviene decirlo bien: el SGC calcula y publica sus
propios mapas de intensidad instrumental de forma automática, el IGAC voló
ortofoto de 10 cm, FUNVISIS habilitó reporte ciudadano de daño, el hub LAC de
HOT coordinó con OSM Colombia desde el primer día, y GEM SARA se construyó con
más de cincuenta expertos de diecisiete instituciones de la región.

Y GEM no se quedó en SARA: el **23 de junio de 2026** liberó su modelo global
2026, con el primer análisis global de vías cruzadas con licuefacción. Conviene
decirlo antes que nadie, porque es lo más parecido a este proyecto que existe.
Lo que sigue faltando es el encaje: la versión abierta de GEM llega a **Adm1**,
es **CC BY-NC-SA** —no reutilizable comercialmente ni por muchas agencias—, es
**probabilística** —riesgo esperado, no un evento concreto— y no cuenta salud ni
educación. CENTINELA publica **Adm2 por evento ocurrido**, bajo CC BY y ODbL, y
con la vigencia del dato declarada en cada celda.

**Lo que no hay es la pieza del medio**: un activo de exposición ya construido,
por municipio y por celda, que convierta la intensidad en cuánta gente e
infraestructura —el mismo día, con el dato descargable y en español—. Este
proyecto es esa pieza.

### Qué añade sobre lo que ya existe

Tres cosas, y las tres se pueden citar de documentos del propio USGS:

* **PAGER no publica el corte.** Estima población por banda de MMI
  *redondeada* y pérdidas, para el país entero: sin municipio, sin celda y sin
  equipamiento. Su insumo de población —LandScan Global— es abierto desde 2022
  (CC BY 4.0, ORNL), así que el argumento nunca fue la licencia del dato: es que
  la cadena de PAGER no la rehace nadie de fuera. El activo de CENTINELA se
  reconstruye entero desde fuentes abiertas, sin credenciales, con un comando, y
  sale cortado por el código administrativo nacional.
* **PAGER no cuenta escuelas, hospitales ni vías.** No aparecen ni en su FAQ ni
  en su *Scientific Background*: estima población y pérdidas, y el equipamiento
  expuesto no es su pregunta.
* **PAGER no considera deslizamiento ni licuefacción _en sus estimaciones de pérdida_.** Cita literal de
  onePAGER: *«PAGER does not consider secondary effects such as landslides,
  liquefaction, and tsunami in loss estimates at this time»*. CENTINELA sí
  consume el producto Ground Failure — con las cautelas que cada reporte
  imprime en su sección «Deslizamiento y licuefacción», que no son pocas.

Y una honestidad que el proyecto se debe a sí mismo: **la malla H3 no es la
novedad**. [Kontur Population](https://data.humdata.org/dataset/kontur-population-dataset)
publica hexágonos H3 globales de la misma resolución, CC BY, en HDX; y
[Disaster Ninja](https://disaster.ninja/) hace exposición H3 disparada por
GDACS, gratis y con el backend abierto. H3 aquí es un detalle de
implementación, no un argumento. Lo que CENTINELA añade sobre eso es el activo
por país reconstruible desde cero, el corte por municipio con el código
administrativo nacional, el equipamiento de salud y educación, y el reporte en
español con su procedencia.

## La evidencia

### El backtest de San José del Palmar

[`reports/us6000tjl2/`](reports/us6000tjl2/) es la respuesta a la pregunta que
motiva el proyecto: **esto es lo que el país habría sabido el 10 de agosto**, en
vez de esperar días.

| Indicador | Cifra |
|---|---:|
| Personas en MMI≥6 | **7.194.540** |
| Personas en MMI≥7 | **2.424.287** |
| De ellas, 65 años o más | **289.947** |
| Edificaciones en MMI≥7 | **448.789** |
| Sedes de salud en MMI≥7 | **516** |
| Sedes educativas en MMI≥7 | **1.003** |
| Kilómetros de vía en MMI≥7 | **8.791** |
| De ellos, primarias y secundarias | **1.015** |
| Personas en celdas con cobertura areal por licuefacción ≥ 0,10 | **1.602.162** |
| Municipios alcanzados | **299** |

Las cifras salen de `reports/us6000tjl2/report.json`, y
`tests/unit/test_cifras_del_readme.py` falla si esta tabla se separa de él.
Cinco de estas filas estuvieron desactualizadas hasta el 25-ago-2026 —los km de
vía, por un factor de seis— porque se copiaron a mano y el activo se reconstruyó
después. Una tabla de cifras escrita a mano se desincroniza; una tabla con
prueba, no.

**Dos cautelas sobre la tabla, que valen más que las cifras.**

*Sobre la precisión.* Siete dígitos significativos sobre un modelo interpolado
fingen una exactitud que no existe: el mismo reporte publica una banda de
discrepancia del 2,3 %, o sea 7.194.540 ± ~165.000. La tabla reproduce el JSON
al dígito porque su trabajo es ser trazable; **en prosa, estas cifras son «7,2
millones» y «2,4 millones»**, que es como las escribe el `report.md` generado.

*Sobre la licuefacción.* 1,6 millones **no es la cifra de USGS y no se puede
comparar con ella**. El modelo de Zhu (2017) entrega **cobertura areal** —la
fracción del área de la celda que se espera cubierta—, no probabilidad; aquí se
cuenta la población entera de toda celda por encima de 0,10, y USGS pondera la
población de cada celda por esa cobertura, con lo que publica **~460 mil** para
el mismo evento y el mismo producto. Son dos preguntas distintas sobre el mismo
ráster. El reporte lo dice ahora en cada emisión.

### El contraste con PAGER, en las mismas bandas

Es la objeción que el proyecto recibe primero, y conviene resolverla antes de
que la haga nadie. PAGER tabula por **MMI redondeado** —su fila «7» es todo lo
que cae entre 6,5 y 7,49— y CENTINELA usa **bandas literales**. Puestas en el
mismo eje, cada cifra de CENTINELA cae dentro del intervalo que las filas de
PAGER acotan por arriba y por abajo:

| Umbral literal | PAGER | CENTINELA |
|---|---:|---:|
| MMI ≥ 5,5 | 10.487.959 | — |
| MMI ≥ 6,0 | — | **7.194.540** |
| MMI ≥ 6,5 | 6.514.486 | — |
| MMI ≥ 7,0 | — | **2.424.287** |
| MMI ≥ 7,5 | 1.126.902 | — |

El acotamiento se cumple, y `tests/unit/test_contraste_con_pager.py` falla si
deja de cumplirse. Pero **acotar no es coincidir**: el intervalo de MMI≥7 va de
1,1 a 6,5 millones, un factor de 5,8, y casi cualquier cifra cabría dentro.

**En los dos casos CENTINELA queda en el cuarto inferior del intervalo** —al
17 % y al 24 % contando desde abajo—, es decir sistemáticamente por debajo del
punto medio y siempre en la misma dirección. Eso es lo que se puede afirmar sin
elegir un método: cuánto por debajo depende de cómo se interpole entre las filas
de PAGER, y la respuesta va del 11 % al 37 % según se haga lineal o logarítmica.
Publicar una sola de esas cifras sería elegir la que conviene. El detalle,
con la fuente de cada columna, está en
[`docs/PARA_INSTITUCIONES.md`](docs/PARA_INSTITUCIONES.md).

### La validación externa

El Microsoft AI for Good Lab publicó evaluación de daño por imagen satelital
para dos de los sismos que CENTINELA reconstruyó, usando además **las mismas
huellas de edificación de Overture**. De las celdas que Microsoft evaluó,
**ninguna falta del activo**, en dos países y dos sismos distintos. La lista de
celdas la puso otro, así que es la verificación de cobertura más exigente que se
le ha hecho a este sistema.

Y la evaluación **no cubrió una sola ciudad**: corrió sobre Cali (imagen Airbus)
y sobre Pereira (imagen Vantor), que es además el municipio más expuesto del
evento según este mismo reporte. El gradiente entre las tres zonas evaluadas es
la respuesta corta a por qué una cifra de exposición no se lee como una cifra de
daño.

### El catálogo histórico regional

San José del Palmar no es una demostración aislada. El sistema reconstruyó
**21 sismos de 15 países** del catálogo real de USGS, cada uno con los productos
que USGS publicó entonces, cada uno contra el activo de su país:

| | |
|---|---|
| Reportes publicados | **21**, en **15 países** |
| Países con activo construido y medido | **19 de 19** |
| Personas ya en la malla hexagonal | **649,8 millones** |
| Peor desvío contra la cifra oficial de un país | **+4,94 %** (Venezuela, y está explicado) |

**Los 21 son reconstrucciones.** El sistema no ha disparado todavía un reporte
en vivo: `site/status.json` publica `eventos_publicados: 0` y
`backtests_excluidos: 21`, y por eso la latencia medida extremo a extremo sigue
en `null`. Decirlo es más útil que dejarlo ambiguo — el catálogo demuestra que
el cálculo funciona sobre veintiún eventos reales, no que la cadena en vivo se
haya ejercitado.

Lo que enseña ese catálogo importa más que su tamaño: **once de los veintiún
eventos no alcanzan MMI≥7 sobre población**, y tres de ellos tampoco MMI≥6. Son
los profundos y los de mar adentro, que en esta región son la mitad.
Tehuantepec 2017 —M8,2, 98 muertos— es uno de ellos: su máximo sobre población
mexicana es MMI 6,5.

Hasta que se corrieron, el producto entero daba por supuesto que MMI≥7 era *la*
banda, y para esos once publicaba un titular de «0 personas» con una tabla de
municipios ordenada alfabéticamente. Ahora se titula con la banda que el evento
alcanzó de verdad. Ninguna cantidad de pruebas sintéticas habría encontrado eso:
hizo falta correr la región entera.

### Los cuatro países sin reporte

Bolivia, Brasil, Paraguay y Uruguay **tienen su activo construido**. No son
huecos del sistema, y no lo son por el mismo motivo. Se buscó para los cuatro,
y `tests/integration/test_silencio_de_paises_live.py` vuelve a comprobarlo
contra USGS:

* **Paraguay y Uruguay** no registran un solo sismo M≥5,5 desde el año 2000. Su
  activo está construido y esperando, que para un sistema de preparación es el
  estado que se persigue, no una carencia.
* **Brasil** tiene doce sismos M≥5,5 desde 2000, **todos entre 534 y 645 km de
  profundidad** y todos en Acre. El ShakeMap de USGS no modela MMI≥5 en
  superficie para ninguno —su máximo modelado es 3,0—, aunque el DYFI recoja
  reportes de personas de hasta CDI 5,6. Un sistema que calcula sobre `cont_mmi`
  no tiene ahí nada que calcular.
* **Bolivia no es el caso de Brasil, y este README decía que sí.** Sus veintidós
  sismos M≥5,5 desde 2000 no están «todos entre 359 y 596 km»: van **de 33 a
  608 km**. El más somero es un M6,2 del 4-jul-2001 cerca de Colomi, con MMI
  modelada de **6,4** y `cont_mmi.json` publicado. Bolivia no está en silencio
  por profundidad: **tiene un reporte pendiente de construir**, y está en
  [`PENDIENTES.md`](PENDIENTES.md). El error venía de una búsqueda ordenada por
  relevancia sobre una caja envolvente que se llena de sismos chilenos — el
  mismo sesgo que la auditoría del 25-ago-2026 ya había documentado para
  Argentina y República Dominicana, y que en Bolivia no se notó.

## Cómo funciona

```
[Feed GeoJSON de USGS] ──(cron GH `*/30` + repository_dispatch)──▶ P1 TRIGGER
     filtro bbox LATAM + M≥5.5 + dedupe por event_state
         │
         ▼
     P2 IMPACTO   contornos MMI → celdas H3 r8 ⋈ activo de exposición
                  ráster de Ground Failure → muestreo por celda
         │
         ▼
     P3 REPORTE   report.json → md + mapa + CSV + parquet + PMTiles + hilo
                  (se re-emite solo cuando aparece ShakeMap v(n+1))

[Trimestral]   P0 EXPOSICIÓN  construye el activo por país desde fuentes públicas
[Continuo]     P5 INCENDIOS   focos activos FIRMS ⋈ el mismo activo, con cobertura del suelo
[Por evento]   P4 BRIGADA     daño por edificación con IA, cuando hay imagen abierta
```

El principio rector es **~95 % automático, ~5 % humano**: una comunidad no opera
turnos, mantiene código y datos. El único paso manual permitido en todo el
sistema es dar clic para publicar el hilo en redes.

**El mismo activo sirve para fuego.** P5 cruza los focos activos de FIRMS con la
malla y con la cobertura del suelo de ESA WorldCover, y publica la capa en el
visor con su propio selector de amenaza. Un activo de exposición no es un
producto sísmico: es la base sobre la que se responde «cuánta gente y qué hay
aquí», sea cual sea la amenaza que llegue.

### Sobre la latencia, con los números medidos

El cálculo de un evento es la parte corta. La larga es enterarse. Con el cron
de GitHub Actions solo —declara diez minutos y entrega mucho menos—, medido
entre el 25 y el 30 de agosto sobre 23 latidos, la detección daba **p50 157 min,
p90 462 y peor caso 766 min (12,8 h)**: con un objetivo de 60 minutos extremo a
extremo, **la detección sola se comía el presupuesto entero**. Por eso desde el
31-ago-2026 un cron externo dispara `repository_dispatch` cada cinco minutos y
el cron de GitHub quedó de respaldo.

La cadencia nueva se está volviendo a medir desde cero: el historial de latidos
se reinició el 1-sep-2026 al re-emitir el catálogo entero, así que
[`/status`](https://sforero77.github.io/CENTINELA/status.json) publica hoy la
cadencia vacía y se rellena solo. Este README no promete «menos de una hora»:
promete el contraste que sí controla —de días a segundos de cómputo— y publica
en `/status` la latencia real, incluida la que todavía no tiene.

## Arranque

```bash
make setup                 # instala todo con uv (Python 3.12)
make check                 # lint + mypy + pruebas
make trigger               # P1 en seco contra el feed vivo de USGS
make country ISO=COL       # reconstruye el activo de exposición de Colombia
```

Sin credenciales, sin servidor, sin cuenta en ningún servicio. Si algo del
arranque no funciona en tu máquina, eso es un bug.

## Estructura

```
pipelines/       p0_exposure, p1_trigger, p2_impact, p3_report, p4_brigada, p5_incendios, common
schemas/         JSON Schema del reporte, del estado y de los contratos USGS
data/manifests/  vintages por país (fuente, url, licencia, hash, fecha) — los 19 de LATAM
events/          event_state por evento — la base de datos del sistema, en git
reports/         salidas publicadas (json + md + csv + png)
site/            visor estático (MapLibre + PMTiles, cero llaves de API)
tests/           unit/, integration/, golden/, fixtures/
```

## Estado del proyecto

El sistema está operando. Desde el 24-ago-2026 el trigger vigila el feed de USGS
y el visor está publicado en <https://sforero77.github.io/CENTINELA/>. Lo que
falta:

| Pendiente | Estado |
|---|---|
| Reporte en vivo (los 21 son reconstrucciones) | ⏳ esperando el primer evento |
| Cadencia real del disparador externo | ⏳ remidiéndose desde el 1-sep |
| Reporte de Bolivia (`usp000ahzc`, M6,2, 2001) | ⏳ el activo está; falta correrlo |
| Coropletas r7/r6 del visor en PMTiles | ⏳ el resto del visor funciona |
| P4 brigada de imagen | ⏳ Fase 2 |

Lo que ya funciona está en [`docs/`](docs/), componente por componente, y en
[`docs/GARANTIAS.md`](docs/GARANTIAS.md), que además dice qué **no** está
garantizado.

**1.426 pruebas** sin red, más **101 de navegador** que abren el visor en un
Chromium de verdad y **13 contra fuentes vivas** que corren en el nocturno,
`ruff` y `mypy --strict` limpios. Medido el 1-sep-2026.

Las etapas pendientes fallan de forma ruidosa y explícita — nunca devuelven un
cero que acabaría publicado como cifra. `tests/unit/test_pendientes.py` es el
inventario vivo de esa deuda, y hoy está vacío.

Y hay una segunda guardia, de otra clase.
`tests/unit/test_funciones_conectadas.py` recorre el grafo de llamadas y falla
si una función pública se queda **sin llamador**. Existe porque el fallo que más
veces ha cazado este proyecto no es un cálculo mal hecho sino una pieza correcta
que nadie invoca: el reporte preliminar, el epicentro del mapa estático, tres
capas del activo, los asserts de §6.4. Todas estaban probadas —por eso la
cobertura las daba por verdes— y ninguna estaba conectada.

El cero silencioso tiene además su propia guardia. Una capa que no se construye
entra vacía al ensamblaje, el `LEFT JOIN` la vuelve ceros y el activo se
escribiría sin que nada proteste: el assert de total nacional solo mira
población. `validate_layer_coverage` detiene el build si **cualquier** capa
requerida suma cero en todo el país — es preferible no publicar activo que
publicar uno que informa cero donde no midió nada.

Los golden tests corren contra **productos reales congelados** de los dos
eventos que motivan el proyecto: San José del Palmar (`us6000tjl2`) y el doble
mainshock de Venezuela (`us6000t7zp`, `us6000t7zc`). Ya cazaron dos bugs que
ninguna prueba sintética habría encontrado — ver
[`tests/fixtures/golden/README.md`](tests/fixtures/golden/README.md).

### El activo del que salen las cifras

Release `exposure-col-20260824` (manifest `col-v0.6`, el que declaran los
reportes): **559.103 celdas**,
52.620.466 habitantes, 15,3 millones de edificaciones, 9.888 sedes de salud,
45.710 sedes educativas y 307.314 km de vía, en los 1.122 municipios del país.
Su desvío contra la referencia del DANE es **−0,72 %**, y solo el 0,32 % de la
población entra por celdas rescatadas.

Y el dato que cambia la conversación: los municipios más expuestos no estaban en
el Chocó sino en el Eje Cafetero y el Valle — Pereira, Buenaventura, Armenia,
Tuluá, Dosquebradas. Por eso este README dejó de llamarlo «el terremoto del
Chocó»: el nombre contradecía la tesis del propio reporte.

## Documentación

**Empieza por [`docs/`](docs/)**, que es el mapa completo del sistema, con
diagramas de cada componente:

| Carpeta | Qué explica |
|---|---|
| [`docs/arquitectura/`](docs/arquitectura/) | La vista de conjunto, el viaje del dato y el contrato de cada fichero |
| [`docs/acciones/`](docs/acciones/) | Las doce GitHub Actions: quién dispara a quién y con qué reloj |
| [`docs/pipelines/`](docs/pipelines/) | Los seis pipelines: qué extrae, qué calcula y qué escribe cada uno |
| [`docs/datos/`](docs/datos/) | Fuentes, licencias, agregaciones y el esquema del activo |
| [`docs/visor/`](docs/visor/) | Qué consume el visor, cómo pinta y cómo se valida |

Y los transversales:

- [`docs/PARA_INSTITUCIONES.md`](docs/PARA_INSTITUCIONES.md) — **el documento de presentación, con las cifras y su procedencia**
- [`docs/OPERACION.md`](docs/OPERACION.md) — qué vigilar ahora que el sistema opera
- [`PENDIENTES.md`](PENDIENTES.md) — qué falta, quién puede hacerlo y en qué orden
- [`docs/GARANTIAS.md`](docs/GARANTIAS.md) — qué está probado y qué no
- [`docs/AUDITORIA.md`](docs/AUDITORIA.md) — la auditoría del 25-ago-2026: qué se encontró y cómo se cerró
- [`docs/FAMILIAS_DE_FALLO.md`](docs/FAMILIAS_DE_FALLO.md) — las once formas en que este sistema falla
- [`docs/CLEAN_CODE.md`](docs/CLEAN_CODE.md) — las reglas de código del proyecto, con el caso real de cada una
- [`ESPECIFICACION.md`](ESPECIFICACION.md) — especificación técnica v0.10
- [`docs/PUBLICAR_ACTIVO.md`](docs/PUBLICAR_ACTIVO.md) — cómo publicar el activo y por qué no va en git
- [`VERIFICACIONES.md`](VERIFICACIONES.md) — cierre de las tareas ⚠️ de §8, con método y hallazgos
- [`DISCLAIMER.md`](DISCLAIMER.md) — qué informa y qué no informa el sistema
- [`CONTRIBUTING.md`](CONTRIBUTING.md) — cómo ayudar (incluye rol de mantenedor por país)
- [`GOVERNANCE.md`](GOVERNANCE.md) — roles, decisiones, frontera comunidad ↔ empresa
- [`ATTRIBUTION.md`](ATTRIBUTION.md) — créditos obligatorios de cada fuente
- [`LICENSES/`](LICENSES/) — la regla de los tres cubos

## Licencia

Código: **Apache-2.0**. Datos derivados: **CC BY 4.0** en el núcleo, **ODbL**
donde entra OpenStreetMap u Overture. Detalle en [`LICENSES/`](LICENSES/).
