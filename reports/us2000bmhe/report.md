# Exposición sísmica — M6,5 · 18 km al O de Parrita, Costa Rica

**Evento USGS:** `us2000bmhe` · **Origen:** 2017-11-13T02:28:23Z UTC · **Profundidad:** 19,4 km

> **Reconstrucción retrospectiva.** Este reporte se calculó después del evento, no en respuesta a él, y no cuenta para las métricas de latencia del sistema.
>
> La **población** corresponde a la época indicada en el manifiesto de exposición. Las **edificaciones, vías, sedes de salud y educativas son las actuales**: OpenStreetMap y Overture publican el estado presente, no el histórico. Léelas como "qué infraestructura de hoy caería en esa zona de intensidad", no como lo que había entonces.

## Exposición estimada

| Indicador | Estimado |
|---|---:|
| Población en MMI≥6 | 28 mil |
| Población en MMI≥7 | 7.400 |
| Población en MMI≥8 | 0 |
| Edificaciones en MMI≥7 | 4.400 |
| Sedes de salud en MMI≥7 | 4 |
| Sedes educativas en MMI≥7 | 8 |
| Vías primarias y secundarias en MMI≥7 | 8 km |
| Vías locales en MMI≥7 | 63 km |
| Superficie construida en MMI≥7 | 0,9 km² |

El satélite detecta **1,9 veces** más superficie construida de la que explicarían las 4.400 edificaciones registradas. La diferencia suele ser asentamiento informal o zona rural dispersa sin mapear: **el conteo de edificaciones se queda corto ahí, y la superficie construida no**.

Las cifras de esta tabla van redondeadas a dos cifras significativas, que es la precisión que un modelo de exposición sostiene. Las exactas están en el CSV municipal y en `report.json`.

De la población en intensidad MMI≥7, alrededor de **710** personas tienen 65 años o más.

## Municipios más expuestos, por población en MMI≥7

| # | Municipio | Código | MMI max | Población MMI≥7 |
|---:|---|---|---:|---:|
| 1 | Parrita | `CR609` | 7,0 | 7.400 |

## Deslizamiento y licuefacción

- Población en celdas con probabilidad **alta de deslizamiento**: 0
- Población en celdas con probabilidad **alta de licuefacción**: 13 mil

Fuente: producto *Ground Failure* de USGS (v2), dominio público.

## Referencia cruzada

PAGER (USGS) estima para este evento una alerta **verde**. CENTINELA no estima víctimas; la cifra se incluye solo como contraste.

## Incertidumbre y calidad

Discrepancia entre GHS-POP y WorldPop en el área afectada: **1,8 %**.

## Descargas

- [CSV por municipio](adm2.csv)
- [Mapa PNG](mapa_general.png)

## Procedencia

- ShakeMap consumido: **v1**
- Ground Failure consumido: **v2**
- Manifiesto de exposición: `cri-v0.1`
- Pipeline: `0.1.0` · Generado: 2026-08-25T17:40:45Z

## Advertencias

- Exposición estimada, no daño observado.
- Este sistema no es una alerta temprana ni una recomendación de evacuación.
- No reemplaza a los servicios geológicos ni a las unidades de gestión del riesgo.
- Fuentes, vintages y versiones consumidas: ver manifiesto enlazado.
