# Clean Code en CENTINELA

Lo que el proyecto adopta de *Clean Code* (Robert C. Martin) y de su lectura
moderna en Python, **traducido a este repositorio**. No es un resumen del libro:
es la lista de reglas que aquí tienen consecuencias, cada una con el caso real
que la justifica.

Se escribió durante la [auditoría del 25-ago-2026](AUDITORIA.md), donde se
aplicó entera.

---

## La regla que manda: *always find root cause*

Es una regla general del libro y aquí es **la** regla, porque este proyecto
tiene una causa raíz que reaparece:

> Una función escrita no es una función conectada.

Cinco hallazgos de la auditoría son la misma causa en cinco sitios: el reporte
preliminar de RF-03, el epicentro del mapa estático, tres capas del activo, los
asserts de calidad de §6.4, la comprobación de licencia de la fuente. Y dos más
aparecieron mientras se arreglaban: el changelog de RF-04 y la guarda de
licencias del reporte.

Todas estaban **probadas**. Ese es el detalle: la cobertura las marcaba en
verde, porque una prueba llama a la función y eso no dice nada sobre si la llama
alguien más.

Arreglarlas una a una habría dejado la siguiente para la proxima auditoría. Por
eso el arreglo de verdad no es ninguno de los siete parches sino
`tests/unit/test_funciones_conectadas.py`, que recorre el grafo de llamadas y
falla si una función pública se queda sin llamador. **La regla se vigila; no se
recuerda.**

---

## Nombres

| Regla | Qué significa aquí |
|---|---|
| Nombres descriptivos y sin ambigüedad | El código, los comentarios y las docstrings están **en español**, como los reportes. Un mantenedor por país no debería tener que leer inglés para revisar la cifra de su municipio. |
| Distinciones con sentido | Prohibido lo que pasó con `SQL_IMPACT_H3`: dos constantes con **el mismo nombre**, en dos módulos del mismo paquete, con cuerpos distintos y una de las dos muerta. |
| Nombres buscables | Los identificadores de la espec (`RF-04`, `§6.4`, `T0.7`) se citan literalmente en el código. `grep RF-04` tiene que llevar al sitio. |
| Constantes con nombre en vez de números magicos | `RESCUE_MAX_DEGREES`, `DEDUPE_METERS`, `MMI_MIN_POLYFILL`, `MAX_LATIDOS`. Cada una es una decisión con consecuencias medidas, no un número. |

---

## Funciones

| Regla | Qué significa aquí |
|---|---|
| Pequenas, y una sola cosa | `write_report_bundle` tenía el render de mapas dentro. Se extrajo `render_maps`, y por eso `regenerar-mapas` puede reusar **exactamente** el camino de la publicación en vez de reimplementarlo. |
| Sin efectos secundarios sorprendentes | `ensure_bundled_proj()` los tiene (toca el entorno) y por eso es explicita, se llama a mano, lleva escape (`CENTINELA_RESPETA_PROJ`) y devuelve lo que aparto. Un efecto secundario que se declara deja de ser una sorpresa. |
| Sin argumentos bandera | `check_quality` no recibe un `bloqueante: bool`. La severidad vive con cada assert, en `QUALITY_ASSERTIONS`, donde se puede leer y discutir. |
| Pocos argumentos | Los que crecen usan objetos: `JoinInputs`, `QualityReport`, `Calibracion`. |

---

## Comentarios

Aquí el proyecto **se aparta del libro a propósito**, y conviene decirlo.

Martin desconfia de los comentarios: «el mejor comentario es el que no tuviste
que escribir». La regla que se conserva entera es la de no comentar lo obvio ni
dejar código comentado. La que se relaja es la del volumen, porque este
repositorio tiene una condición rara:

**Casi todos sus bugs producen cifras plausibles.** Sumar el nodata de GHS-POP
da población negativa; sumar las tres series de WorldPop cuenta a cada persona
dos veces; leer el catálogo STAC de Overture como manda el estándar desplaza la
selección un puesto. Ninguno revienta. Todos publican un número que parece bien.

El código puede explicar *que* hace. No puede explicar que el geoportal del DANE
dejo de servir rangos por encima de 1,5 GB el 24-ago-2026, ni que el 96,6 % de
los puntos de healthsites caen a menos de 20 m de uno de HOTOSM. Eso son
**hallazgos medidos**, y perderlos significa volver a pagarlos.

La regla de este repositorio, entonces:

> Un comentario justifica una decisión con evidencia, o sobra.

Lo que sigue prohibido: repetir lo que dice la línea de abajo, dejar código
comentado (para eso esta git), y firmar con nombres o fechas de edición.

---

## Código muerto

> Borralo. Git se acuerda.

En la auditoría se borraron `hdx.resolve_resource` (reemplazada por
`resolve_attempts`), `products.fetch_products`, `paths.report_dir`,
`paths.ensure_workspace`, `overture.pmtiles_url`,
`download.download_zip_entries`, el módulo `sources/zip_range.py` entero, y las
copias muertas de `SQL_IMPACT_H3`, `SQL_IMPACT_ADM2`, `run_join` y
`QUALITY_FLAGS`.

Dos matices que este proyecto anadio:

**Probada no es viva.** `hdx.resolve_resource` tenía once referencias en
pruebas y cero llamadores. `assert_publishable_in_report` estaba probada y solo
se ejecutaba de rebote, dentro de un f-string. Código muerto con pruebas se lee
como código vivo y la cobertura lo confirma: es el mejor disfraz que hay.

**Una prueba que cubre código muerto no cubre nada.** El invariante de que
reanudar un build sea barato se estuvo verificando sobre `download_zip_entries`,
que ya no corría. Daba la misma sensación de seguridad.

Cuando se conserva algo sin llamador, se **declara** en
`SIN_LLAMADOR_JUSTIFICADO` con su motivo, y hay una prueba que exige que el
motivo tenga sustancia y otra que borra la entrada en cuanto sobra. Lo que no
vale como motivo: «está probada», «la usaremos pronto», «es API pública». Las
tres describen justo el código que hay que borrar o cablear.

---

## DRY, con cuidado

Repetir una regla en dos sitios es como divergen. Casos de la auditoría:

- **Los ficheros derivados.** `reports/index.json` y `site/status.json` se
  regeneran en vez de fusionarse ante un conflicto de rebase. El manejador
  conocia solo el primero; el segundo habría tumbado la publicación del segundo
  evento exactamente igual. La lista esta ahora **una vez**.
- **Las banderas de calidad.** `build.SQL_FLAGS` (viva) y
  `exposure_join.QUALITY_FLAGS` (muerta) eran la misma regla escrita dos veces.
  Identicas ese día; solo podían divergir.
- **El formato del CSV municipal.** `read_adm2_csv` vive al lado de
  `write_adm2_csv` porque la peculiaridad del formato (que la **segunda** fila
  no son datos sino etiquetas HXL) es conocimiento del formato.

El cuidado: **no todo lo que se parece es lo mismo.** Los asserts de calidad de
P0 y de P2 se parecen y preguntan cosas distintas (el activo entero contra el
corte de un evento) así que viven separados a propósito.

---

## Pruebas

Del libro se toman «legibles, rapidas, independientes, repetibles». Un assert
por prueba se sigue **casi** siempre; donde no, es porque los dos asserts
describen el mismo hecho.

Lo que este repositorio añade:

**El docstring dice por que existe la prueba, no que hace.** «Verifica que el
nodata se enmascara» no ayuda a nadie. «GHS-POP marca el mar con -200 y son ~22
millones de píxeles por tesela; sumarlos da población negativa y el assert de
§6.4 marcaria como corruptos unos datos que están perfectos» dice si la prueba
puede borrarse y que se pierde con ella.

**Una prueba puede vigilar un patrón, no solo un caso.**
`test_funciones_conectadas.py`, `test_pendientes.py` y
`test_cifras_del_readme.py` no prueban comportamiento: vigilan clases enteras de
error que ya ocurrieron.

**Nada de verde por orden de ejecución.** Si una prueba pasa en la suite y falla
sola, no esta pasando: esta heredando el efecto de otra.

---

## Diseño

| Regla | Qué significa aquí |
|---|---|
| Configuracion en los niveles altos | Los vintages, licencias y hashes viven en `data/manifests/*.yaml`, nunca en el código. Regla dura: **nunca `latest`**. |
| Evitar la sobre-configurabilidad | La reconstrucción trimestral no lee una lista de países de ningún sitio: pregunta que Releases hay publicados. Una lista que mantener a mano es una lista que se desincroniza. |
| Inyección de dependencias | Todo lo que toca la red recibe un `Fetcher`; `FixtureFetcher` es lo que hace que 601 pruebas corran sin red. Las raices de `events/` y `reports/` se inyectan para que las pruebas no escriban en el repositorio. |
| Simple mejor que ingenioso | El manejador de conflictos de `impact.yml` se escribió con una función y un `grep -qvE` legible en vez de una línea con `comm` y sustitución de procesos. Un `run:` que nadie puede leer a las 3 de la mañana durante un terremoto no es código limpio, por corto que sea. |

---

## Los olores que aquí son fatales

De la lista del libro, los tres que en este proyecto no son cuestión de estilo:

**Opacidad.** Una cifra plausible y equivocada es indistinguible de una
correcta. Todo lo que pueda producir una lleva su guardia y su comentario con la
medición que lo motivo.

**Repeticion innecesaria.** Dos copias de una regla de calidad, de licencias o
de simbología acaban divergiendo, y la divergencia se publica.

**Fragilidad.** Un cambio en un sitio no puede romper otro en silencio. Por eso
`test_cli.py` comprueba que los workflows solo llamen a subcomandos que existen,
y `test_cifras_del_readme.py` que la portada no se separe de los artefactos.

---

## Herramientas, que hacen cumplir lo que se pueda

```bash
uv run ruff check .          # lint
uv run ruff format --check . # formato
uv run mypy                  # tipos, estricto
uv run pytest -m "not network"
```

Los cuatro corren en CI y ninguno admite excepciones locales. `ruff` va
configurado con `E, F, W, I, N, UP, B, A, C4, SIM, PTH, RUF` y solo ignora las
tres reglas que se pelean con los acentos del español.

Lo que ninguna herramienta puede comprobar (si un comentario justifica su
decisión, si un nombre dice la verdad, si una función esta conectada) se revisa
a mano, salvo lo último, que ya tiene su prueba.
