# Exposicion sismica — M6.5 18 km al O de Parrita, Costa Rica

**Evento USGS:** `us2000bmhe` · **Origen:** 2017-11-13T02:28:23Z UTC · **Profundidad:** 19,4 km

> **Reconstruccion retrospectiva.** Este reporte se calculo despues del evento, no en respuesta a el, y no cuenta para las metricas de latencia del sistema.
>
> La **poblacion** corresponde a la epoca indicada en el manifest de exposicion. Las **edificaciones, vias, sedes de salud y educativas son las actuales**: OpenStreetMap y Overture publican el estado presente, no el historico. Leelas como "que infraestructura de hoy caeria en esa zona de intensidad", no como lo que habia entonces.

## Exposicion estimada

| Indicador | Estimado |
|---|---:|
| Poblacion en MMI≥6 | 28 mil |
| Poblacion en MMI≥7 | 7.400 |
| Poblacion en MMI≥8 | 0 |
| Edificaciones en MMI≥7 | 4.400 |
| Sedes de salud en MMI≥7 | 4 |
| Sedes educativas en MMI≥7 | 8 |
| Vias primarias y secundarias en MMI≥7 | 8 km |
| Vias locales en MMI≥7 | 63 km |
| Superficie construida en MMI≥7 | 0,9 km² |

El satelite detecta **1,9 veces** mas superficie construida de la que explicarian las 4.400 edificaciones registradas. La diferencia suele ser asentamiento informal o zona rural dispersa sin mapear: **el conteo de edificaciones se queda corto ahi, y la superficie construida no**.

De la poblacion en intensidad MMI≥7, alrededor de **710** personas tienen 65 años o más.

## Municipios mas expuestos (top 15), por poblacion en MMI≥7

| # | Municipio | Codigo | MMI max | Poblacion MMI≥7 |
|---:|---|---|---:|---:|
| 1 | Parrita | `CR609` | 7,0 | 7.400 |
| 2 | Puriscal | `CR104` | 6,5 | 0 |
| 3 | Turrubares | `CR116` | 6,5 | 0 |
| 4 | Acosta | `CR112` | 6,0 | 0 |
| 5 | Quepos | `CR606` | 6,0 | 0 |
| 6 | Garabito | `CR611` | 6,0 | 0 |
| 7 | Aserrí | `CR106` | 5,5 | 0 |
| 8 | Orotina | `CR209` | 5,0 | 0 |
| 9 | Cartago | `CR301` | 5,0 | 0 |
| 10 | Desamparados | `CR103` | 5,0 | 0 |
| 11 | El Guarco | `CR308` | 5,0 | 0 |
| 12 | Tarrazú | `CR105` | 5,0 | 0 |
| 13 | León Cortés Castro | `CR120` | 5,0 | 0 |
| 14 | Esparza | `CR602` | 5,0 | 0 |

## Deslizamiento y licuefaccion

- Poblacion en celdas con probabilidad **alta de deslizamiento**: 0
- Poblacion en celdas con probabilidad **alta de licuefaccion**: 13 mil

Fuente: producto *Ground Failure* de USGS (v2), dominio publico.

## Referencia cruzada

PAGER (USGS) estima para este evento una alerta **green**. CENTINELA no estima victimas; la cifra se incluye solo como contraste.

## Incertidumbre y calidad

Discrepancia entre GHS-POP y WorldPop en el area afectada: **1,8 %**.

## Descargas

- [CSV por municipio](adm2.csv)
- [Mapa PNG](mapa_general.png)

## Procedencia

- ShakeMap consumido: **v1**
- Ground Failure consumido: **v2**
- Manifest de exposicion: `cri-v0.1`
- Pipeline: `0.1.0` · Generado: 2026-08-25T17:40:45Z

## Advertencias

- Exposicion estimada, no dano observado.
- Este sistema no es una alerta temprana ni una recomendacion de evacuacion.
- No reemplaza a los servicios geologicos ni a las unidades de gestion del riesgo.
- Fuentes, vintages y versiones consumidas: ver manifest enlazado.
