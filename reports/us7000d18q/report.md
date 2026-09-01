# Exposición sísmica — M6,4 · 26 km al SO de Pocito, Argentina

**Evento USGS:** `us7000d18q` · **Origen:** 2021-01-19T02:46:22Z UTC · **Profundidad:** 20,8 km

> **Reconstrucción retrospectiva.** Este reporte se calculó después del evento, no en respuesta a él, y no cuenta para las métricas de latencia del sistema.
>
> La **población** corresponde a la época indicada en el manifiesto de exposición. Las **edificaciones, vías, sedes de salud y educativas son las actuales**: OpenStreetMap y Overture publican el estado presente, no el histórico. Léelas como "qué infraestructura de hoy caería en esa zona de intensidad", no como lo que había entonces.

## Exposición estimada

| Indicador | Estimado |
|---|---:|
| Población en MMI≥6 | 580 mil |
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
| 1 | Rawson | `AR070077` | 6,0 | 120 mil |
| 2 | Capital | `AR070028` | 6,0 | 120 mil |
| 3 | Chimbas | `AR070042` | 6,0 | 96 mil |
| 4 | Rivadavia | `AR070084` | 6,0 | 95 mil |
| 5 | Pocito | `AR070070` | 6,0 | 65 mil |
| 6 | Santa Lucía | `AR070098` | 6,0 | 51 mil |
| 7 | Sarmiento | `AR070105` | 6,5 | 21 mil |
| 8 | 9 De Julio | `AR070063` | 6,0 | 7.500 |
| 9 | 25 De Mayo | `AR070126` | 6,0 | 670 |
| 10 | Zonda | `AR070133` | 6,5 | 650 |
| 11 | Ullum | `AR070112` | 6,0 | 10 |
| 12 | Albardón | `AR070007` | 6,0 | 5 |

## Deslizamiento y licuefacción

- Población en celdas con probabilidad **alta de deslizamiento**: 0
- Población en celdas con probabilidad **alta de licuefacción**: 0

Fuente: producto *Ground Failure* de USGS (v4), dominio público.

## Referencia cruzada

PAGER (USGS) estima para este evento una alerta **amarilla**. CENTINELA no estima víctimas; la cifra se incluye solo como contraste.

## Incertidumbre y calidad

Discrepancia entre GHS-POP y WorldPop en el área afectada: **2,9 %**.

## Descargas

- [CSV por municipio](adm2.csv)
- [Mapa PNG](mapa_general.png)

## Procedencia

- ShakeMap consumido: **v8**
- Ground Failure consumido: **v4**
- Manifiesto de exposición: `arg-v0.1`
- Pipeline: `0.1.0` · Generado: 2026-08-25T19:03:50Z

## Advertencias

- Exposición estimada, no daño observado.
- Este sistema no es una alerta temprana ni una recomendación de evacuación.
- No reemplaza a los servicios geológicos ni a las unidades de gestión del riesgo.
- Fuentes, vintages y versiones consumidas: ver manifiesto enlazado.
