# Exposición sísmica — M5,5 · 5 km al NNO de Baní, República Dominicana

**Evento USGS:** `usp000jd2q` · **Origen:** 2012-01-05T09:35:32Z UTC · **Profundidad:** 39,8 km

> **Reconstrucción retrospectiva.** Este reporte se calculó después del evento, no en respuesta a él, y no cuenta para las métricas de latencia del sistema.
>
> La **población** corresponde a la época indicada en el manifiesto de exposición. Las **edificaciones, vías, sedes de salud y educativas son las actuales**: OpenStreetMap y Overture publican el estado presente, no el histórico. Léelas como "qué infraestructura de hoy caería en esa zona de intensidad", no como lo que había entonces.

## Exposición estimada

| Indicador | Estimado |
|---|---:|
| Población en MMI≥6 | 0 |
| Población en MMI≥7 | 0 |
| Población en MMI≥8 | 0 |
| Edificaciones en MMI≥7 | 0 |
| Sedes de salud en MMI≥7 | 0 |
| Sedes educativas en MMI≥7 | 0 |
| Kilómetros de vía en MMI≥7 | 0 km |

> **Todas las cifras en cero es un resultado, no un fallo.** El ShakeMap de este evento sí dibuja intensidad, pero no alcanza MMI≥6 sobre territorio habitado del país: la sacudida quedó mar adentro o sobre zona despoblada. El cálculo corrió entero.

Las cifras de esta tabla van redondeadas a dos cifras significativas, que es la precisión que un modelo de exposición sostiene. Las exactas están en el CSV municipal y en `report.json`.

## Municipios más expuestos, por población en MMI≥6

Ningún municipio del país alcanza población dentro de MMI≥6. No es que falte el dato: la intensidad que el ShakeMap dibuja para este evento no llega a esa banda sobre territorio habitado.

## Deslizamiento y licuefacción

USGS no ha publicado el producto *Ground Failure* para este evento. La sección se omite; el reporte se re-emite automáticamente si aparece.

## Incertidumbre y calidad

Discrepancia entre GHS-POP y WorldPop: **no se pudo medir**. Ninguna celda dentro de las bandas publicadas tiene población de WorldPop con la que contrastar.

## Descargas

- [CSV por municipio](adm2.csv)
- [Mapa PNG](mapa_general.png)

## Procedencia

- ShakeMap consumido: **v1**
- Ground Failure consumido: **v0**
- Manifiesto de exposición: `dom-v0.2`
- Pipeline: `0.1.0` · Generado: 2026-09-02T02:48:02Z

## Advertencias

- Exposición estimada, no daño observado.
- Este sistema no es una alerta temprana ni una recomendación de evacuación.
- No reemplaza a los servicios geológicos ni a las unidades de gestión del riesgo.
- Fuentes, vintages y versiones consumidas: ver manifiesto enlazado.
