# Exposición sísmica — M6,8 · 14 km al NNO de Baláo, Ecuador

**Evento USGS:** `us7000jl3s` · **Origen:** 2023-03-18T17:12:52Z UTC · **Profundidad:** 68,0 km

> **Reconstrucción retrospectiva.** Este reporte se calculó después del evento, no en respuesta a él, y no cuenta para las métricas de latencia del sistema.
>
> La **población** corresponde a la época indicada en el manifiesto de exposición. Las **edificaciones, vías, sedes de salud y educativas son las actuales**: OpenStreetMap y Overture publican el estado presente, no el histórico. Léelas como "qué infraestructura de hoy caería en esa zona de intensidad", no como lo que había entonces.

## Exposición estimada

| Indicador | Estimado |
|---|---:|
| Población en MMI≥6 | 4,8 millones |
| Población en MMI≥7 | 0 |
| Población en MMI≥8 | 0 |
| Edificaciones en MMI≥7 | 0 |
| Sedes de salud en MMI≥7 | 0 |
| Sedes educativas en MMI≥7 | 0 |
| Kilometros de via en MMI≥7 | 0 km |

Las cifras de esta tabla van redondeadas a dos cifras significativas, que es la precisión que un modelo de exposición sostiene. Las exactas están en el CSV municipal y en `report.json`.

## Municipios más expuestos, por población en MMI≥6

| # | Municipio | Código | MMI max | Población MMI≥6 |
|---:|---|---|---:|---:|
| 1 | Guayaquil | `EC0901` | 6,5 | 3,1 millones |
| 2 | Durán | `EC0907` | 6,5 | 290 mil |
| 3 | Machala | `EC0701` | 6,5 | 290 mil |
| 4 | Milagro | `EC0910` | 6,0 | 210 mil |
| 5 | Naranjal | `EC0911` | 6,5 | 89 mil |
| 6 | Pasaje | `EC0709` | 6,5 | 82 mil |
| 7 | San Jacinto De Yaguachi | `EC0920` | 6,5 | 75 mil |
| 8 | Samborondón | `EC0916` | 6,0 | 74 mil |
| 9 | Santa Rosa | `EC0712` | 6,5 | 74 mil |
| 10 | Huaquillas | `EC0707` | 6,5 | 60 mil |
| 11 | El Triunfo | `EC0909` | 6,5 | 60 mil |
| 12 | El Guabo | `EC0706` | 6,5 | 57 mil |
| 13 | La Troncal | `EC0304` | 6,5 | 55 mil |
| 14 | Playas | `EC0921` | 6,5 | 54 mil |
| 15 | Naranjito | `EC0912` | 6,0 | 46 mil |

## Deslizamiento y licuefacción

- Población en celdas con probabilidad **alta de deslizamiento**: 0
- Población en celdas con probabilidad **alta de licuefacción**: 500 mil

Fuente: producto *Ground Failure* de USGS (v9), dominio público.

## Referencia cruzada

PAGER (USGS) estima para este evento una alerta **naranja**. CENTINELA no estima víctimas; la cifra se incluye solo como contraste.

## Incertidumbre y calidad

Discrepancia entre GHS-POP y WorldPop en el área afectada: **0,4 %**.

## Descargas

- [CSV por municipio](adm2.csv)
- [Mapa PNG](mapa_general.png)

## Procedencia

- ShakeMap consumido: **v7**
- Ground Failure consumido: **v9**
- Manifiesto de exposición: `ecu-v0.1`
- Pipeline: `0.1.0` · Generado: 2026-08-25T17:41:04Z

## Advertencias

- Exposición estimada, no daño observado.
- Este sistema no es una alerta temprana ni una recomendación de evacuación.
- No reemplaza a los servicios geológicos ni a las unidades de gestión del riesgo.
- Fuentes, vintages y versiones consumidas: ver manifiesto enlazado.
