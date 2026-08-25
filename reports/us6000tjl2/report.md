# Exposicion sismica — M7.4 5 km al S de San José del Palmar, Colombia

**Evento USGS:** `us6000tjl2` · **Origen:** 2026-08-10T12:34:28Z UTC · **Profundidad:** 110,3 km

> **Reconstruccion retrospectiva.** Este reporte se calculo despues del evento, no en respuesta a el, y no cuenta para las metricas de latencia del sistema.
>
> La **poblacion** corresponde a la epoca indicada en el manifest de exposicion. Las **edificaciones, vias, sedes de salud y educativas son las actuales**: OpenStreetMap y Overture publican el estado presente, no el historico. Leelas como "que infraestructura de hoy caeria en esa zona de intensidad", no como lo que habia entonces.

## Exposicion estimada

| Indicador | Estimado |
|---|---:|
| Poblacion en MMI≥6 | 7 millones |
| Poblacion en MMI≥7 | 2,4 millones |
| Poblacion en MMI≥8 | 0 |
| Edificaciones en MMI≥7 | 440 mil |
| Sedes de salud en MMI≥7 | 518 |
| Sedes educativas en MMI≥7 | 998 |
| Vias primarias y secundarias en MMI≥7 | 980 km |
| Vias locales en MMI≥7 | 7.500 km |
| Superficie construida en MMI≥7 | 69,8 km² |

El satelite detecta **1,6 veces** mas superficie construida de la que explicarian las 440 mil edificaciones registradas. La diferencia suele ser asentamiento informal o zona rural dispersa sin mapear: **el conteo de edificaciones se queda corto ahi, y la superficie construida no**.

De la poblacion en intensidad MMI≥7, alrededor de **290 mil** personas tienen 65 años o más.

## Municipios mas expuestos (top 15), por poblacion en MMI≥7

| # | Municipio | Codigo | MMI max | Poblacion MMI≥7 |
|---:|---|---|---:|---:|
| 1 | Pereira | `66001` | 7,5 | 500 mil |
| 2 | Buenaventura | `76109` | 7,0 | 400 mil |
| 3 | Armenia | `63001` | 7,0 | 340 mil |
| 4 | Tuluá | `76834` | 7,0 | 260 mil |
| 5 | Dosquebradas | `66170` | 7,5 | 180 mil |
| 6 | Cartago | `76147` | 7,5 | 130 mil |
| 7 | Quibdó | `27001` | 7,0 | 110 mil |
| 8 | Santa Rosa De Cabal | `66682` | 7,0 | 68 mil |
| 9 | La Tebaida | `63401` | 7,0 | 54 mil |
| 10 | Zarzal | `76895` | 7,5 | 40 mil |
| 11 | Alcalá | `76020` | 7,0 | 37 mil |
| 12 | La Unión | `76400` | 7,5 | 35 mil |
| 13 | Montenegro | `63470` | 7,0 | 32 mil |
| 14 | Quimbaya | `63594` | 7,0 | 32 mil |
| 15 | Chinchiná | `17174` | 7,0 | 29 mil |

## Deslizamiento y licuefaccion

- Poblacion en celdas con probabilidad **alta de deslizamiento**: 0
- Poblacion en celdas con probabilidad **alta de licuefaccion**: 1,6 millones

Fuente: producto *Ground Failure* de USGS (v7), dominio publico.

## Referencia cruzada

PAGER (USGS) estima para este evento una alerta **red**. CENTINELA no estima victimas; la cifra se incluye solo como contraste.

## Incertidumbre y calidad

Discrepancia entre GHS-POP y WorldPop en el area afectada: **3,1 %**.

## Descargas

- [CSV por municipio](adm2.csv)
- [Mapa PNG](mapa_general.png)

## Procedencia

- ShakeMap consumido: **v7**
- Ground Failure consumido: **v7**
- Manifest de exposicion: `col-v0.5`
- Pipeline: `0.1.0` · Generado: 2026-08-25T17:40:39Z

## Advertencias

- Exposicion estimada, no dano observado.
- Este sistema no es una alerta temprana ni una recomendacion de evacuacion.
- No reemplaza a los servicios geologicos ni a las unidades de gestion del riesgo.
- Fuentes, vintages y versiones consumidas: ver manifest enlazado.
