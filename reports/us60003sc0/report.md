# Exposicion sismica — M8.0 78 km al NE de Navarro, Perú

**Evento USGS:** `us60003sc0` · **Origen:** 2019-05-26T07:41:15Z UTC · **Profundidad:** 122,6 km

> **Reconstruccion retrospectiva.** Este reporte se calculo despues del evento, no en respuesta a el, y no cuenta para las metricas de latencia del sistema.
>
> La **poblacion** corresponde a la epoca indicada en el manifest de exposicion. Las **edificaciones, vias, sedes de salud y educativas son las actuales**: OpenStreetMap y Overture publican el estado presente, no el historico. Leelas como "que infraestructura de hoy caeria en esa zona de intensidad", no como lo que habia entonces.

## Exposicion estimada

| Indicador | Estimado |
|---|---:|
| Poblacion en MMI≥6 | 1,1 millones |
| Poblacion en MMI≥7 | 250 mil |
| Poblacion en MMI≥8 | 0 |
| Edificaciones en MMI≥7 | 130 mil |
| Sedes de salud en MMI≥7 | 123 |
| Sedes educativas en MMI≥7 | 1.303 |
| Vias primarias y secundarias en MMI≥7 | 130 km |
| Vias locales en MMI≥7 | 1.300 km |
| Superficie construida en MMI≥7 | 8,3 km² |

De la poblacion en intensidad MMI≥7, alrededor de **15 mil** personas tienen 65 años o más.

## Municipios mas expuestos (top 15), por poblacion en MMI≥7

| # | Municipio | Codigo | MMI max | Poblacion MMI≥7 |
|---:|---|---|---:|---:|
| 1 | Alto Amazonas | `PE1602` | 7,5 | 110 mil |
| 2 | Ucayali | `PE1606` | 7,5 | 38 mil |
| 3 | Requena | `PE1605` | 7,5 | 29 mil |
| 4 | Datem Del Marañon | `PE1607` | 7,5 | 24 mil |
| 5 | Loreto | `PE1603` | 7,5 | 17 mil |
| 6 | San Martin | `PE2209` | 7,5 | 15 mil |
| 7 | Lamas | `PE2205` | 7,5 | 11 mil |
| 8 | Coronel Portillo | `PE2501` | 6,5 | 0 |
| 9 | El Dorado | `PE2203` | 6,5 | 0 |
| 10 | Picota | `PE2207` | 6,5 | 0 |
| 11 | Bellavista | `PE2202` | 6,5 | 0 |
| 12 | Maynas | `PE1601` | 6,0 | 0 |
| 13 | Moyobamba | `PE2201` | 6,0 | 0 |
| 14 | Rioja | `PE2208` | 6,0 | 0 |
| 15 | Huallaga | `PE2204` | 6,0 | 0 |

## Deslizamiento y licuefaccion

- Poblacion en celdas con probabilidad **alta de deslizamiento**: 36
- Poblacion en celdas con probabilidad **alta de licuefaccion**: 330 mil

Fuente: producto *Ground Failure* de USGS (v8), dominio publico.

## Referencia cruzada

PAGER (USGS) estima para este evento una alerta **orange**. CENTINELA no estima victimas; la cifra se incluye solo como contraste.

## Incertidumbre y calidad

Discrepancia entre GHS-POP y WorldPop en el area afectada: **3,0 %**.

## Descargas

- [CSV por municipio](adm2.csv)
- [Mapa PNG](mapa_general.png)

## Procedencia

- ShakeMap consumido: **v1**
- Ground Failure consumido: **v8**
- Manifest de exposicion: `per-v0.1`
- Pipeline: `0.1.0` · Generado: 2026-08-25T17:53:38Z

## Advertencias

- Exposicion estimada, no dano observado.
- Este sistema no es una alerta temprana ni una recomendacion de evacuacion.
- No reemplaza a los servicios geologicos ni a las unidades de gestion del riesgo.
- Fuentes, vintages y versiones consumidas: ver manifest enlazado.
