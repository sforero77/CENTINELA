# Exposición sísmica — M6,8 · 42 km al SSO de Bartolomé Masó, Cuba

**Evento USGS:** `us7000nr0v` · **Origen:** 2024-11-10T16:49:50Z UTC · **Profundidad:** 14,0 km

> **Reconstrucción retrospectiva.** Este reporte se calculó después del evento, no en respuesta a él, y no cuenta para las métricas de latencia del sistema.
>
> La **población** corresponde a la época indicada en el manifiesto de exposición. Las **edificaciones, vías, sedes de salud y educativas son las actuales**: OpenStreetMap y Overture publican el estado presente, no el histórico. Léelas como "qué infraestructura de hoy caería en esa zona de intensidad", no como lo que había entonces.

## Exposición estimada

| Indicador | Estimado |
|---|---:|
| Población en MMI≥6 | 170 mil |
| Población en MMI≥7 | 3.300 |
| Población en MMI≥8 | 0 |
| Edificaciones en MMI≥7 | 2.000 |
| Sedes de salud en MMI≥7 | 1 |
| Sedes educativas en MMI≥7 | 7 |
| Vías primarias y secundarias en MMI≥7 | 28 km |
| Vías locales en MMI≥7 | 28 km |
| Superficie construida en MMI≥7 | 0,1 km² |

Las cifras de esta tabla van redondeadas a dos cifras significativas, que es la precisión que un modelo de exposición sostiene. Las exactas están en el CSV municipal y en `report.json`.

De la población en intensidad MMI≥7, alrededor de **380** personas tienen 65 años o más.

## Municipios más expuestos, por población en MMI≥7

| # | Municipio | Código | MMI max | Población MMI≥7 |
|---:|---|---|---:|---:|
| 1 | Pilón | `CU0511` | 7,0 | 3.000 |
| 2 | Guamá | `CU1502` | 7,0 | 280 |
| 3 | Bartolomé Masó | `CU0501` | 7,0 | 55 |

## Deslizamiento y licuefacción

- Población en celdas con probabilidad **alta de deslizamiento**: 0
- Población en celdas con probabilidad **alta de licuefacción**: 37 mil

Fuente: producto *Ground Failure* de USGS (v9), dominio público.

## Referencia cruzada

PAGER (USGS) estima para este evento una alerta **amarilla**. CENTINELA no estima víctimas; la cifra se incluye solo como contraste.

## Incertidumbre y calidad

Discrepancia entre GHS-POP y WorldPop en el área afectada: **0,8 %**.

## Descargas

- [CSV por municipio](adm2.csv)
- [Mapa PNG](mapa_general.png)

## Procedencia

- ShakeMap consumido: **v9**
- Ground Failure consumido: **v9**
- Manifiesto de exposición: `cub-v0.1`
- Pipeline: `0.1.0` · Generado: 2026-08-25T17:40:54Z

## Advertencias

- Exposición estimada, no daño observado.
- Este sistema no es una alerta temprana ni una recomendación de evacuación.
- No reemplaza a los servicios geológicos ni a las unidades de gestión del riesgo.
- Fuentes, vintages y versiones consumidas: ver manifiesto enlazado.
