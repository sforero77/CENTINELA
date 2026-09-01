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

- **Deslizamiento.** Población en celdas donde el modelo espera ≥ 0,10 de probabilidad de deslizamiento: **0**.
- **Licuefacción.** Población en celdas donde el modelo espera ≥ 0,10 de cobertura areal por licuefacción: **500 mil**. USGS declara para este evento alerta **roja**, con 150 mil expuestas.

Las dos cifras se cuentan sobre las celdas del corte publicado (MMI≥6). **No son las de USGS y no se pueden comparar de frente**: aquí se cuenta la población entera de toda celda por encima del umbral, y USGS pondera la población de cada celda por el valor de esa celda. Son dos preguntas distintas sobre el mismo ráster.

Fuente: producto *Ground Failure* de USGS (v9), dominio público.

## Referencia cruzada

PAGER (USGS) estima para este evento una alerta **naranja**. CENTINELA no estima víctimas; la cifra se incluye solo como contraste.

Las dos cifras **no se tabulan igual**: PAGER agrupa por MMI redondeado —su fila «7» es todo lo que cae entre 6,5 y 7,49— y CENTINELA usa bandas literales, donde MMI≥7 es MMI≥7. Comparadas de frente parecen discrepar; puestas en el mismo eje, cada cifra de aquí cae dentro del intervalo que las filas de PAGER acotan por arriba y por abajo.

## Incertidumbre y calidad

Discrepancia entre GHS-POP y WorldPop en las bandas MMI publicadas: **0,4 %**.

## Descargas

- [CSV por municipio](adm2.csv)
- [Mapa PNG](mapa_general.png)

## Procedencia

- ShakeMap consumido: **v7**
- Ground Failure consumido: **v9**
- Manifiesto de exposición: `ecu-v0.2`
- Pipeline: `0.1.0` · Generado: 2026-09-01T22:12:00Z

## Advertencias

- Exposición estimada, no daño observado.
- Este sistema no es una alerta temprana ni una recomendación de evacuación.
- No reemplaza a los servicios geológicos ni a las unidades de gestión del riesgo.
- Fuentes, vintages y versiones consumidas: ver manifiesto enlazado.
