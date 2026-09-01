# Exposición sísmica — M7,8 · 27 km al SSE de Muisne, Ecuador

**Evento USGS:** `us20005j32` · **Origen:** 2016-04-16T23:58:36Z UTC · **Profundidad:** 20,6 km

> **Reconstrucción retrospectiva.** Este reporte se calculó después del evento, no en respuesta a él, y no cuenta para las métricas de latencia del sistema.
>
> La **población** corresponde a la época indicada en el manifiesto de exposición. Las **edificaciones, vías, sedes de salud y educativas son las actuales**: OpenStreetMap y Overture publican el estado presente, no el histórico. Léelas como "qué infraestructura de hoy caería en esa zona de intensidad", no como lo que había entonces.

## Exposición estimada

| Indicador | Estimado |
|---|---:|
| Población en MMI≥6 | 4,3 millones |
| Población en MMI≥7 | 2,3 millones |
| Población en MMI≥8 | 110 mil |
| Edificaciones en MMI≥7 | 1 millón |
| Sedes de salud en MMI≥7 | 527 |
| Sedes educativas en MMI≥7 | 2.412 |
| Vías primarias y secundarias en MMI≥7 | 1.700 km |
| Vías locales en MMI≥7 | 22 mil km |
| Superficie construida en MMI≥7 | 131,0 km² |

Las cifras de esta tabla van redondeadas a dos cifras significativas, que es la precisión que un modelo de exposición sostiene. Las exactas están en el CSV municipal y en `report.json`.

De la población en intensidad MMI≥7, alrededor de **170 mil** personas tienen 65 años o más.

## Municipios más expuestos, por población en MMI≥7

| # | Municipio | Código | MMI max | Población MMI≥7 |
|---:|---|---|---:|---:|
| 1 | Portoviejo | `EC1301` | 7,5 | 330 mil |
| 2 | Esmeraldas | `EC0801` | 7,5 | 300 mil |
| 3 | Quinindé | `EC0804` | 7,5 | 160 mil |
| 4 | Chone | `EC1303` | 7,5 | 150 mil |
| 5 | Sucre | `EC1314` | 8,0 | 68 mil |
| 6 | Pedernales | `EC1317` | 8,0 | 66 mil |
| 7 | Atacames | `EC0806` | 8,0 | 55 mil |
| 8 | Muisne | `EC0803` | 8,0 | 38 mil |
| 9 | Pichincha | `EC1311` | 7,5 | 36 mil |
| 10 | Rioverde | `EC0807` | 7,5 | 33 mil |
| 11 | Flavio Alfaro | `EC1305` | 7,5 | 29 mil |
| 12 | Jama | `EC1320` | 8,0 | 27 mil |
| 13 | San Vicente | `EC1322` | 8,0 | 27 mil |
| 14 | Junín | `EC1307` | 7,5 | 23 mil |
| 15 | Eloy Alfaro | `EC0802` | 7,5 | 6.600 |

## Deslizamiento y licuefacción

- Población en celdas con probabilidad **alta de deslizamiento**: 210 mil
- Población en celdas con probabilidad **alta de licuefacción**: 1,2 millones

Fuente: producto *Ground Failure* de USGS (v1), dominio público.

## Referencia cruzada

PAGER (USGS) estima para este evento una alerta **naranja**. CENTINELA no estima víctimas; la cifra se incluye solo como contraste.

## Incertidumbre y calidad

Discrepancia entre GHS-POP y WorldPop en el área afectada: **3,2 %**.

## Descargas

- [CSV por municipio](adm2.csv)
- [Mapa PNG](mapa_general.png)

## Procedencia

- ShakeMap consumido: **v1**
- Ground Failure consumido: **v1**
- Manifiesto de exposición: `ecu-v0.1`
- Pipeline: `0.1.0` · Generado: 2026-08-25T17:41:50Z

## Advertencias

- Exposición estimada, no daño observado.
- Este sistema no es una alerta temprana ni una recomendación de evacuación.
- No reemplaza a los servicios geológicos ni a las unidades de gestión del riesgo.
- Fuentes, vintages y versiones consumidas: ver manifiesto enlazado.
