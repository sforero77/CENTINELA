# Exposición sísmica — M7,2 · 20 km al E de San Felipe, Venezuela

**Evento USGS:** `us6000t7zc` · **Origen:** 2026-06-24T22:04:31Z UTC · **Profundidad:** 10,0 km

> **Reconstrucción retrospectiva.** Este reporte se calculó después del evento, no en respuesta a él, y no cuenta para las métricas de latencia del sistema.
>
> La **población** corresponde a la época indicada en el manifiesto de exposición. Las **edificaciones, vías, sedes de salud y educativas son las actuales**: OpenStreetMap y Overture publican el estado presente, no el histórico. Léelas como "qué infraestructura de hoy caería en esa zona de intensidad", no como lo que había entonces.

## Exposición estimada

| Indicador | Estimado |
|---|---:|
| Población en MMI≥6 | 2,8 millones |
| Población en MMI≥7 | 490 mil |
| Población en MMI≥8 | 230 mil |
| Edificaciones en MMI≥7 | 190 mil |
| Sedes de salud en MMI≥7 | 31 |
| Sedes educativas en MMI≥7 | 92 |
| Vías primarias y secundarias en MMI≥7 | 420 km |
| Vías locales en MMI≥7 | 1.900 km |
| Superficie construida en MMI≥7 | 23,6 km² |

Las cifras de esta tabla van redondeadas a dos cifras significativas, que es la precisión que un modelo de exposición sostiene. Las exactas están en el CSV municipal y en `report.json`.

De la población en intensidad MMI≥7, alrededor de **29 mil** personas tienen 65 años o más.

## Municipios más expuestos, por población en MMI≥7

| # | Municipio | Código | MMI max | Población MMI≥7 |
|---:|---|---|---:|---:|
| 1 | San Felipe | `VE2211` | 8,0 | 130 mil |
| 2 | Veroes | `VE2214` | 8,0 | 100 mil |
| 3 | Juan José Mora | `VE0805` | 8,0 | 58 mil |
| 4 | Bruzual | `VE2203` | 7,0 | 44 mil |
| 5 | Independencia | `VE2205` | 8,0 | 30 mil |
| 6 | Arístides Bastidas | `VE2201` | 7,5 | 27 mil |
| 7 | Sucre | `VE2212` | 7,5 | 27 mil |
| 8 | Cocorote | `VE2204` | 7,5 | 25 mil |
| 9 | La Trinidad | `VE2207` | 7,5 | 25 mil |
| 10 | Puerto Cabello | `VE0811` | 7,0 | 15 mil |
| 11 | Palmasola | `VE1116` | 7,0 | 1.700 |
| 12 | Silva | `VE1120` | 7,5 | 1.600 |
| 13 | Bejuma | `VE0801` | 7,5 | 1.500 |

## Deslizamiento y licuefacción

- Población en celdas con probabilidad **alta de deslizamiento**: 0
- Población en celdas con probabilidad **alta de licuefacción**: 290 mil

Fuente: producto *Ground Failure* de USGS (v7), dominio público.

## Referencia cruzada

PAGER (USGS) estima para este evento una alerta **roja**. CENTINELA no estima víctimas; la cifra se incluye solo como contraste.

## Incertidumbre y calidad

Discrepancia entre GHS-POP y WorldPop en el área afectada: **27,0 %**.

## Descargas

- [CSV por municipio](adm2.csv)
- [Mapa PNG](mapa_general.png)

## Procedencia

- ShakeMap consumido: **v9**
- Ground Failure consumido: **v7**
- Manifiesto de exposición: `ven-v0.1`
- Pipeline: `0.1.0` · Generado: 2026-08-25T17:54:34Z

## Advertencias

- Exposición estimada, no daño observado.
- Este sistema no es una alerta temprana ni una recomendación de evacuación.
- No reemplaza a los servicios geológicos ni a las unidades de gestión del riesgo.
- Fuentes, vintages y versiones consumidas: ver manifiesto enlazado.
