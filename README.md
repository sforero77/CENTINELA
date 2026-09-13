# CENTINELA

**Sistema abierto de exposición sísmica automatizada para América Latina.**

Cuando ocurre un sismo relevante en la región, CENTINELA publica un reporte de
**exposición**: cuántas personas, edificaciones, escuelas, hospitales y
kilómetros de vía quedan dentro de cada franja de intensidad sísmica, por
municipio y por celda, con los datos descargables y en español.

> **Exposición no es daño.** Este sistema no es una alerta temprana, no estima
> víctimas, no dictamina habitabilidad y no reemplaza a los servicios
> geológicos ni a las unidades de gestión del riesgo. Ver
> [`DISCLAIMER.md`](DISCLAIMER.md).

**[Ver el visor](https://sforero77.github.io/CENTINELA/)** · [un reporte de
ejemplo](https://sforero77.github.io/CENTINELA/?evento=us6000tjl2) ·
[estado del sistema](https://sforero77.github.io/CENTINELA/status.html)

## Dos conceptos

**MMI** es la escala **Mercalli Modificada** y mide **la sacudida en un sitio**:
lo que se sintió y lo que puede romperse allí. No es la magnitud. La magnitud es
una sola cifra para el sismo entero; la intensidad es un mapa, y un mismo sismo
sacude mucho más un valle cercano que una ciudad lejana. Confundir las dos es el
error de lectura más caro que este sistema puede provocar, porque lleva a
repartir ayuda por la cifra equivocada. Aquí las bandas se escriben literales:
**MMI≥7** significa intensidad 7 o más, no «alrededor de 7».

Un **activo de exposición** es una tabla ya construida, celda a celda, de cuánta
gente e infraestructura hay en cada punto de un país. Es lo que permite
convertir un mapa de intensidad en un reporte el mismo día en vez de en semanas,
y construirlo es la mitad del trabajo de este proyecto.

## Qué hace

1. **Vigila.** Revisa sin parar el catálogo de sismos de USGS y se queda con los
   de magnitud 5,5 o más dentro de América Latina.
2. **Calcula.** Cruza el mapa de intensidad del sismo (ShakeMap) y el de
   deslizamiento y licuefacción (Ground Failure) con el activo de exposición del
   país afectado.
3. **Publica.** Escribe el reporte —JSON, Markdown, CSV por municipio, mapas y
   un texto para redes— y lo muestra en el visor.
4. **Se mantiene al día.** Cuando USGS revisa el ShakeMap de un sismo, o cambia
   la receta del activo de un país, vuelve a calcular el reporte sin que nadie
   lo pida.

Además construye el activo de cada país desde fuentes públicas y abiertas, sin
credenciales, y usa ese mismo activo para cruzar los focos de incendio activos
que detecta NASA FIRMS. Un activo de exposición no es un producto sísmico: es la
base para responder «cuánta gente y qué hay aquí», sea cual sea la amenaza.

El principio rector es que casi todo sea automático: una comunidad no opera
turnos, mantiene código y datos. El único paso manual previsto es dar clic para
publicar el texto en redes.

## Por qué existe

Tras un sismo fuerte, el país suele saber pronto **cuánta** gente estaba en la
zona de sacudida fuerte: PAGER, de USGS, lo estima enseguida. Lo que tarda días
es saber **dónde**: por municipio, con qué hospitales, escuelas y vías.

Capacidad regional hay, y conviene decirlo con nombres: el SGC calcula y publica
sus propios mapas de intensidad instrumental de forma automática, el IGAC voló
ortofoto de alta resolución tras el sismo de San José del Palmar, el hub LAC de
HOT se activó con OSM Colombia en los días siguientes, y GEM SARA se construyó
con expertos de instituciones de toda la región. Lo que falta es **la pieza del
medio**: un activo de exposición ya construido, por municipio y por celda, que
convierta la intensidad en cuánta gente e infraestructura el mismo día, con el
dato descargable y en español. Este proyecto es esa pieza.

Sobre lo que ya existe, añade tres cosas:

* **El corte por municipio.** PAGER estima población por banda de intensidad
  para el país entero y tabula una lista corta de ciudades cercanas, pero no
  publica una partición por código administrativo que se pueda sumar.
* **El equipamiento.** PAGER no cuenta escuelas, hospitales ni vías.
* **Deslizamiento y licuefacción.** PAGER no los considera en sus estimaciones
  de pérdida. CENTINELA consume el producto Ground Failure, con las cautelas que
  cada reporte imprime.

La malla hexagonal H3 no es la novedad: [Kontur
Population](https://data.humdata.org/dataset/kontur-population-dataset) y
[Disaster Ninja](https://disaster.ninja/) ya publican exposición en H3. Lo que
CENTINELA añade es un activo por país que cualquiera puede reconstruir desde
cero, cortado por el código administrativo nacional, con salud y educación, y un
reporte en español con su procedencia. La evidencia, con sus cifras y de dónde
sale cada una, está en [`docs/PARA_INSTITUCIONES.md`](docs/PARA_INSTITUCIONES.md).

## Cómo funciona

```
[Catálogo de USGS] ──▶ P1 VIGÍA      filtra por región y magnitud, sin repetir eventos
                          │
                          ▼
                       P2 IMPACTO   contornos de intensidad → celdas H3 ⋈ activo de exposición
                                    Ground Failure → muestreo por celda
                          │
                          ▼
                       P3 REPORTE   report.json → md + mapas + CSV + texto para redes

[Periódico]  P0 EXPOSICIÓN  construye el activo de cada país desde fuentes públicas
[Continuo]   P5 INCENDIOS   focos activos de FIRMS ⋈ el mismo activo
[Fase 2]     P4 BRIGADA     daño por edificación con IA, cuando hay imagen abierta
```

Todo corre en GitHub Actions y se publica en GitHub Pages: sin servidor propio
ni llaves de API. Qué dispara cada workflow y qué comprueba está dibujado en
[`docs/acciones/`](docs/acciones/).

## Cómo se valida

Las etapas fallan de forma ruidosa y explícita, y nunca devuelven un cero que
acabaría publicado como cifra. Las pruebas corren contra productos reales de
USGS congelados, abren el visor en un navegador de verdad, contrastan cada noche
las fuentes vivas contra su contrato y fallan si una función pública se queda
sin nadie que la llame. Qué está garantizado, y sobre todo qué **no**, está en
[`docs/GARANTIAS.md`](docs/GARANTIAS.md).

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
data/manifests/  vintages por país: fuente, url, licencia, hash y fecha
events/          event_state por evento · la base de datos del sistema, en git
reports/         salidas publicadas (json + md + csv + png)
site/            visor estático (MapLibre + PMTiles, cero llaves de API)
scripts/         utilidades que se corren a mano, y el validador de diagramas
tests/           unit/, integration/, golden/, fixtures/, visor/
```

## Documentación

**Empieza por [`docs/`](docs/)**, que es el mapa completo del sistema, con
diagramas de cada componente:

| Carpeta | Qué explica |
|---|---|
| [`docs/arquitectura/`](docs/arquitectura/) | La vista de conjunto, el viaje del dato y el contrato de cada fichero |
| [`docs/acciones/`](docs/acciones/) | Las GitHub Actions: quién dispara a quién, con qué reloj y qué comprueba cada una |
| [`docs/pipelines/`](docs/pipelines/) | Los pipelines: qué extrae, qué calcula y qué escribe cada uno |
| [`docs/datos/`](docs/datos/) | Fuentes, licencias, agregaciones y el esquema del activo |
| [`docs/visor/`](docs/visor/) | Qué consume el visor, cómo pinta y cómo se valida |

Y los transversales:

- [`docs/PARA_INSTITUCIONES.md`](docs/PARA_INSTITUCIONES.md): **el documento de presentación, con las cifras y su procedencia**
- [`docs/OPERACION.md`](docs/OPERACION.md): qué vigilar ahora que el sistema opera
- [`docs/GARANTIAS.md`](docs/GARANTIAS.md): qué está probado y qué no
- [`ESPECIFICACION.md`](ESPECIFICACION.md): especificación técnica
- [`docs/PUBLICAR_ACTIVO.md`](docs/PUBLICAR_ACTIVO.md): cómo publicar el activo y por qué no va en git
- [`VERIFICACIONES.md`](VERIFICACIONES.md): cierre de las verificaciones de la especificación, con método y hallazgos
- [`DISCLAIMER.md`](DISCLAIMER.md): qué informa y qué no informa el sistema
- [`CONTRIBUTING.md`](CONTRIBUTING.md): cómo ayudar (incluye rol de mantenedor por país)
- [`GOVERNANCE.md`](GOVERNANCE.md): roles, decisiones, frontera comunidad ↔ empresa
- [`ATTRIBUTION.md`](ATTRIBUTION.md): créditos obligatorios de cada fuente
- [`LICENSES/`](LICENSES/): la regla de los tres cubos

## Licencia

Código: **Apache-2.0**. Datos derivados: **CC BY 4.0** en el núcleo, **ODbL**
donde entra OpenStreetMap u Overture. Detalle en [`LICENSES/`](LICENSES/).
