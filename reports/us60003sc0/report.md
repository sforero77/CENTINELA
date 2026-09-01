# Exposición sísmica — M8,0 · 78 km al NE de Navarro, Perú

**Evento USGS:** `us60003sc0` · **Origen:** 2019-05-26T07:41:15Z UTC · **Profundidad:** 122,6 km

> **Reconstrucción retrospectiva.** Este reporte se calculó después del evento, no en respuesta a él, y no cuenta para las métricas de latencia del sistema.
>
> La **población** corresponde a la época indicada en el manifiesto de exposición. Las **edificaciones, vías, sedes de salud y educativas son las actuales**: OpenStreetMap y Overture publican el estado presente, no el histórico. Léelas como "qué infraestructura de hoy caería en esa zona de intensidad", no como lo que había entonces.

## Exposición estimada

| Indicador | Estimado |
|---|---:|
| Población en MMI≥6 | 1,1 millones |
| Población en MMI≥7 | 250 mil |
| Población en MMI≥8 | 0 |
| Edificaciones en MMI≥7 | 130 mil |
| Sedes de salud en MMI≥7 | 123 |
| Sedes educativas en MMI≥7 | 1.303 |
| Vías primarias y secundarias en MMI≥7 | 130 km |
| Vías locales en MMI≥7 | 1.300 km |
| Superficie construida en MMI≥7 | 8,3 km² |

Las cifras de esta tabla van redondeadas a dos cifras significativas, que es la precisión que un modelo de exposición sostiene. Las exactas están en el CSV municipal y en `report.json`.

De la población en intensidad MMI≥7, alrededor de **15 mil** personas tienen 65 años o más.

## Municipios más expuestos, por población en MMI≥7

| # | Municipio | Código | MMI max | Población MMI≥7 |
|---:|---|---|---:|---:|
| 1 | Alto Amazonas | `PE1602` | 7,5 | 110 mil |
| 2 | Ucayali | `PE1606` | 7,5 | 38 mil |
| 3 | Requena | `PE1605` | 7,5 | 29 mil |
| 4 | Datem Del Marañon | `PE1607` | 7,5 | 24 mil |
| 5 | Loreto | `PE1603` | 7,5 | 17 mil |
| 6 | San Martin | `PE2209` | 7,5 | 15 mil |
| 7 | Lamas | `PE2205` | 7,5 | 11 mil |

## Deslizamiento y licuefacción

- Población en celdas con probabilidad **alta de deslizamiento**: 36
- Población en celdas con probabilidad **alta de licuefacción**: 330 mil

Fuente: producto *Ground Failure* de USGS (v8), dominio público.

## Referencia cruzada

PAGER (USGS) estima para este evento una alerta **naranja**. CENTINELA no estima víctimas; la cifra se incluye solo como contraste.

## Incertidumbre y calidad

Discrepancia entre GHS-POP y WorldPop en el área afectada: **3,0 %**.

## Descargas

- [CSV por municipio](adm2.csv)
- [Mapa PNG](mapa_general.png)

## Procedencia

- ShakeMap consumido: **v1**
- Ground Failure consumido: **v8**
- Manifiesto de exposición: `per-v0.1`
- Pipeline: `0.1.0` · Generado: 2026-08-25T17:53:38Z

## Advertencias

- Exposición estimada, no daño observado.
- Este sistema no es una alerta temprana ni una recomendación de evacuación.
- No reemplaza a los servicios geológicos ni a las unidades de gestión del riesgo.
- Fuentes, vintages y versiones consumidas: ver manifiesto enlazado.
