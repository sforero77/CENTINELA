# Clean Code en CENTINELA

Lo que el proyecto adopta de *Clean Code* (Robert C. Martin) y de su lectura
moderna en Python, **traducido a este repositorio**. No es un resumen del libro:
es la lista de reglas que aqui tienen consecuencias, cada una con el caso real
que la justifica.

Se escribio durante la [auditoria del 25-ago-2026](AUDITORIA.md), donde se
aplico entera.

---

## La regla que manda: *always find root cause*

Es una regla general del libro y aqui es **la** regla, porque este proyecto
tiene una causa raiz que reaparece:

> Una funcion escrita no es una funcion conectada.

Cinco hallazgos de la auditoria son la misma causa en cinco sitios: el reporte
preliminar de RF-03, el epicentro del mapa estatico, tres capas del activo, los
asserts de calidad de §6.4, la comprobacion de licencia de la fuente. Y dos mas
aparecieron mientras se arreglaban: el changelog de RF-04 y la guarda de
licencias del reporte.

Todas estaban **probadas**. Ese es el detalle: la cobertura las marcaba en
verde, porque una prueba llama a la funcion y eso no dice nada sobre si la llama
alguien mas.

Arreglarlas una a una habria dejado la siguiente para la proxima auditoria. Por
eso el arreglo de verdad no es ninguno de los siete parches sino
`tests/unit/test_funciones_conectadas.py`, que recorre el grafo de llamadas y
falla si una funcion publica se queda sin llamador. **La regla se vigila; no se
recuerda.**

---

## Nombres

| Regla | Que significa aqui |
|---|---|
| Nombres descriptivos y sin ambiguedad | El codigo, los comentarios y las docstrings estan **en espanol**, como los reportes. Un mantenedor por pais no deberia tener que leer ingles para revisar la cifra de su municipio. |
| Distinciones con sentido | Prohibido lo que paso con `SQL_IMPACT_H3`: dos constantes con **el mismo nombre**, en dos modulos del mismo paquete, con cuerpos distintos y una de las dos muerta. |
| Nombres buscables | Los identificadores de la espec —`RF-04`, `§6.4`, `T0.7`— se citan literalmente en el codigo. `grep RF-04` tiene que llevar al sitio. |
| Constantes con nombre en vez de numeros magicos | `RESCUE_MAX_DEGREES`, `DEDUPE_METERS`, `MMI_MIN_POLYFILL`, `MAX_LATIDOS`. Cada una es una decision con consecuencias medidas, no un numero. |

---

## Funciones

| Regla | Que significa aqui |
|---|---|
| Pequenas, y una sola cosa | `write_report_bundle` tenia el render de mapas dentro. Se extrajo `render_maps`, y por eso `regenerar-mapas` puede reusar **exactamente** el camino de la publicacion en vez de reimplementarlo. |
| Sin efectos secundarios sorprendentes | `ensure_bundled_proj()` los tiene —toca el entorno— y por eso es explicita, se llama a mano, lleva escape (`CENTINELA_RESPETA_PROJ`) y devuelve lo que aparto. Un efecto secundario que se declara deja de ser una sorpresa. |
| Sin argumentos bandera | `check_quality` no recibe un `bloqueante: bool`. La severidad vive con cada assert, en `QUALITY_ASSERTIONS`, donde se puede leer y discutir. |
| Pocos argumentos | Los que crecen usan objetos: `JoinInputs`, `QualityReport`, `Calibracion`. |

---

## Comentarios

Aqui el proyecto **se aparta del libro a proposito**, y conviene decirlo.

Martin desconfia de los comentarios: «el mejor comentario es el que no tuviste
que escribir». La regla que se conserva entera es la de no comentar lo obvio ni
dejar codigo comentado. La que se relaja es la del volumen, porque este
repositorio tiene una condicion rara:

**Casi todos sus bugs producen cifras plausibles.** Sumar el nodata de GHS-POP
da poblacion negativa; sumar las tres series de WorldPop cuenta a cada persona
dos veces; leer el catalogo STAC de Overture como manda el estandar desplaza la
seleccion un puesto. Ninguno revienta. Todos publican un numero que parece bien.

El codigo puede explicar *que* hace. No puede explicar que el geoportal del DANE
dejo de servir rangos por encima de 1,5 GB el 24-ago-2026, ni que el 96,6 % de
los puntos de healthsites caen a menos de 20 m de uno de HOTOSM. Eso son
**hallazgos medidos**, y perderlos significa volver a pagarlos.

La regla de este repositorio, entonces:

> Un comentario justifica una decision con evidencia, o sobra.

Lo que sigue prohibido: repetir lo que dice la linea de abajo, dejar codigo
comentado (para eso esta git), y firmar con nombres o fechas de edicion.

---

## Codigo muerto

> Borralo. Git se acuerda.

En la auditoria se borraron `hdx.resolve_resource` (reemplazada por
`resolve_attempts`), `products.fetch_products`, `paths.report_dir`,
`paths.ensure_workspace`, `overture.pmtiles_url`,
`download.download_zip_entries`, el modulo `sources/zip_range.py` entero, y las
copias muertas de `SQL_IMPACT_H3`, `SQL_IMPACT_ADM2`, `run_join` y
`QUALITY_FLAGS`.

Dos matices que este proyecto anadio:

**Probada no es viva.** `hdx.resolve_resource` tenia once referencias en
pruebas y cero llamadores. `assert_publishable_in_report` estaba probada y solo
se ejecutaba de rebote, dentro de un f-string. Codigo muerto con pruebas se lee
como codigo vivo y la cobertura lo confirma: es el mejor disfraz que hay.

**Una prueba que cubre codigo muerto no cubre nada.** El invariante de que
reanudar un build sea barato se estuvo verificando sobre `download_zip_entries`,
que ya no corria. Daba la misma sensacion de seguridad.

Cuando se conserva algo sin llamador, se **declara** en
`SIN_LLAMADOR_JUSTIFICADO` con su motivo, y hay una prueba que exige que el
motivo tenga sustancia y otra que borra la entrada en cuanto sobra. Lo que no
vale como motivo: «esta probada», «la usaremos pronto», «es API publica». Las
tres describen justo el codigo que hay que borrar o cablear.

---

## DRY, con cuidado

Repetir una regla en dos sitios es como divergen. Casos de la auditoria:

- **Los ficheros derivados.** `reports/index.json` y `site/status.json` se
  regeneran en vez de fusionarse ante un conflicto de rebase. El manejador
  conocia solo el primero; el segundo habria tumbado la publicacion del segundo
  evento exactamente igual. La lista esta ahora **una vez**.
- **Las banderas de calidad.** `build.SQL_FLAGS` (viva) y
  `exposure_join.QUALITY_FLAGS` (muerta) eran la misma regla escrita dos veces.
  Identicas ese dia; solo podian divergir.
- **El formato del CSV municipal.** `read_adm2_csv` vive al lado de
  `write_adm2_csv` porque la peculiaridad del formato —que la **segunda** fila
  no son datos sino etiquetas HXL— es conocimiento del formato.

El cuidado: **no todo lo que se parece es lo mismo.** Los asserts de calidad de
P0 y de P2 se parecen y preguntan cosas distintas — el activo entero contra el
corte de un evento— asi que viven separados a proposito.

---

## Pruebas

Del libro se toman «legibles, rapidas, independientes, repetibles». Un assert
por prueba se sigue **casi** siempre; donde no, es porque los dos asserts
describen el mismo hecho.

Lo que este repositorio anade:

**El docstring dice por que existe la prueba, no que hace.** «Verifica que el
nodata se enmascara» no ayuda a nadie. «GHS-POP marca el mar con -200 y son ~22
millones de pixeles por tesela; sumarlos da poblacion negativa y el assert de
§6.4 marcaria como corruptos unos datos que estan perfectos» dice si la prueba
puede borrarse y que se pierde con ella.

**Una prueba puede vigilar un patron, no solo un caso.**
`test_funciones_conectadas.py`, `test_pendientes.py` y
`test_cifras_del_readme.py` no prueban comportamiento: vigilan clases enteras de
error que ya ocurrieron.

**Nada de verde por orden de ejecucion.** Si una prueba pasa en la suite y falla
sola, no esta pasando: esta heredando el efecto de otra.

---

## Diseno

| Regla | Que significa aqui |
|---|---|
| Configuracion en los niveles altos | Los vintages, licencias y hashes viven en `data/manifests/*.yaml`, nunca en el codigo. Regla dura: **nunca `latest`**. |
| Evitar la sobre-configurabilidad | La reconstruccion trimestral no lee una lista de paises de ningun sitio: pregunta que Releases hay publicados. Una lista que mantener a mano es una lista que se desincroniza. |
| Inyeccion de dependencias | Todo lo que toca la red recibe un `Fetcher`; `FixtureFetcher` es lo que hace que 601 pruebas corran sin red. Las raices de `events/` y `reports/` se inyectan para que las pruebas no escriban en el repositorio. |
| Simple mejor que ingenioso | El manejador de conflictos de `impact.yml` se escribio con una funcion y un `grep -qvE` legible en vez de una linea con `comm` y sustitucion de procesos. Un `run:` que nadie puede leer a las 3 de la manana durante un terremoto no es codigo limpio, por corto que sea. |

---

## Los olores que aqui son fatales

De la lista del libro, los tres que en este proyecto no son cuestion de estilo:

**Opacidad.** Una cifra plausible y equivocada es indistinguible de una
correcta. Todo lo que pueda producir una lleva su guardia y su comentario con la
medicion que lo motivo.

**Repeticion innecesaria.** Dos copias de una regla de calidad, de licencias o
de simbologia acaban divergiendo, y la divergencia se publica.

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
tres reglas que se pelean con los acentos del espanol.

Lo que ninguna herramienta puede comprobar —si un comentario justifica su
decision, si un nombre dice la verdad, si una funcion esta conectada— se revisa
a mano, salvo lo ultimo, que ya tiene su prueba.
