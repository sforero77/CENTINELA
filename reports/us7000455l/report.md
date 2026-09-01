# Exposición sísmica — M6,2 · 4 km al SE de Aserrío de Gariché, Panamá

**Evento USGS:** `us7000455l` · **Origen:** 2019-06-26T05:23:51Z UTC · **Profundidad:** 32,6 km

> **Reconstrucción retrospectiva.** Este reporte se calculó después del evento, no en respuesta a él, y no cuenta para las métricas de latencia del sistema.
>
> La **población** corresponde a la época indicada en el manifiesto de exposición. Las **edificaciones, vías, sedes de salud y educativas son las actuales**: OpenStreetMap y Overture publican el estado presente, no el histórico. Léelas como "qué infraestructura de hoy caería en esa zona de intensidad", no como lo que había entonces.

## Exposición estimada

| Indicador | Estimado |
|---|---:|
| Población en MMI≥6 | 55 mil |
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
| 1 | Bugaba | `PA0205` | 6,0 | 27 mil |
| 2 | Barú | `PA0202` | 6,0 | 23 mil |
| 3 | Alanje | `PA0201` | 6,0 | 5.200 |
| 4 | Renacimiento | `PA0210` | 6,0 | 270 |

## Deslizamiento y licuefacción

- Población en celdas con probabilidad **alta de deslizamiento**: 0
- Población en celdas con probabilidad **alta de licuefacción**: 20 mil

Fuente: producto *Ground Failure* de USGS (v8), dominio público.

## Referencia cruzada

PAGER (USGS) estima para este evento una alerta **amarilla**. CENTINELA no estima víctimas; la cifra se incluye solo como contraste.

## Incertidumbre y calidad

Discrepancia entre GHS-POP y WorldPop en el área afectada: **1,0 %**.

## Descargas

- [CSV por municipio](adm2.csv)
- [Mapa PNG](mapa_general.png)

## Procedencia

- ShakeMap consumido: **v1**
- Ground Failure consumido: **v8**
- Manifiesto de exposición: `pan-v0.1`
- Pipeline: `0.1.0` · Generado: 2026-08-25T17:45:03Z

## Advertencias

- Exposición estimada, no daño observado.
- Este sistema no es una alerta temprana ni una recomendación de evacuación.
- No reemplaza a los servicios geológicos ni a las unidades de gestión del riesgo.
- Fuentes, vintages y versiones consumidas: ver manifiesto enlazado.
