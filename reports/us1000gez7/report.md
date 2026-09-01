# Exposición sísmica — M7,3 · 40 km al ENE de Carúpano, Venezuela

**Evento USGS:** `us1000gez7` · **Origen:** 2018-08-21T21:31:47Z UTC · **Profundidad:** 146,8 km

> **Reconstrucción retrospectiva.** Este reporte se calculó después del evento, no en respuesta a él, y no cuenta para las métricas de latencia del sistema.
>
> La **población** corresponde a la época indicada en el manifiesto de exposición. Las **edificaciones, vías, sedes de salud y educativas son las actuales**: OpenStreetMap y Overture publican el estado presente, no el histórico. Léelas como "qué infraestructura de hoy caería en esa zona de intensidad", no como lo que había entonces.

## Exposición estimada

| Indicador | Estimado |
|---|---:|
| Población en MMI≥6 | 3.400 |
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
| 1 | Cajigal | `VE1907` | 6,0 | 2.500 |
| 2 | Libertador | `VE1909` | 6,0 | 950 |

## Deslizamiento y licuefacción

- Población en celdas con probabilidad **alta de deslizamiento**: 0
- Población en celdas con probabilidad **alta de licuefacción**: 31

Fuente: producto *Ground Failure* de USGS (v1), dominio público.

## Referencia cruzada

PAGER (USGS) estima para este evento una alerta **amarilla**. CENTINELA no estima víctimas; la cifra se incluye solo como contraste.

## Incertidumbre y calidad

Discrepancia entre GHS-POP y WorldPop en el área afectada: **416,9 %**.

## Descargas

- [CSV por municipio](adm2.csv)
- [Mapa PNG](mapa_general.png)

## Procedencia

- ShakeMap consumido: **v1**
- Ground Failure consumido: **v1**
- Manifiesto de exposición: `ven-v0.1`
- Pipeline: `0.1.0` · Generado: 2026-08-25T18:40:56Z

## Advertencias

- Exposición estimada, no daño observado.
- Este sistema no es una alerta temprana ni una recomendación de evacuación.
- No reemplaza a los servicios geológicos ni a las unidades de gestión del riesgo.
- Fuentes, vintages y versiones consumidas: ver manifiesto enlazado.
