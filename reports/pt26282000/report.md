# Exposición sísmica: M7,7 · 12 km al OSO de Pitaloza Arriba, Panamá

**Evento USGS:** `pt26282000` · **Origen:** 2026-10-09T17:56:08Z UTC · **Profundidad:** 12,6 km

## Exposición estimada

| Indicador | Estimado |
|---|---:|
| Población en MMI≥6 | 600 mil |
| Población en MMI≥7 | 260 mil |
| Población en MMI≥8 | 710 |
| Edificaciones en MMI≥7 | 180 mil |
| Sedes de salud en MMI≥7 | 75 |
| Sedes educativas en MMI≥7 | 350 |
| Vías primarias y secundarias en MMI≥7 | 580 km |
| Vías locales en MMI≥7 | 5.900 km |
| Superficie construida en MMI≥7 | 33,9 km² |

El satélite detecta **1,9 veces** más superficie construida de la que explicarían las 180 mil edificaciones registradas en MMI≥7. La diferencia suele ser asentamiento informal o zona rural dispersa sin mapear: **el conteo de edificaciones se queda corto ahí, y la superficie construida no**.

Las cifras de esta tabla van redondeadas a dos cifras significativas, que es la precisión que un modelo de exposición sostiene. Las exactas están en el CSV municipal y en `report.json`.

De la población en intensidad MMI≥7, alrededor de **39 mil** personas tienen 65 años o más.

## Municipios más expuestos, por población en MMI≥7

| # | Municipio | Código | MMI max | Población MMI≥7 |
|---:|---|---|---:|---:|
| 1 | Chitré | `PA0701` | 7,0 | 53 mil |
| 2 | Santiago | `PA1311` | 7,5 | 32 mil |
| 3 | Los Santos | `PA0903` | 7,5 | 27 mil |
| 4 | Las Tablas | `PA0902` | 7,0 | 26 mil |
| 5 | Ocú | `PA0704` | 7,5 | 16 mil |
| 6 | Pesé | `PA0706` | 7,5 | 13 mil |
| 7 | Atalaya | `PA1301` | 7,0 | 11 mil |
| 8 | Guararé | `PA0901` | 7,0 | 11 mil |
| 9 | Macaracas | `PA0904` | 7,5 | 9.500 |
| 10 | Parita | `PA0705` | 7,0 | 9.400 |
| 11 | Los Pozos | `PA0703` | 8,0 | 8.000 |
| 12 | Tonosí | `PA0907` | 7,5 | 8.000 |
| 13 | Las Minas | `PA0702` | 8,0 | 7.900 |
| 14 | Santa María | `PA0707` | 7,0 | 7.500 |
| 15 | Montijo | `PA1307` | 7,0 | 5.800 |

## Deslizamiento y licuefacción

- **Deslizamiento.** Población en celdas de MMI≥6 donde el modelo espera ≥ 0,10 de probabilidad de deslizamiento según `jessee_2018_model.tif`: **16**. USGS declara para este evento alerta **naranja**, con 350 expuestas.
- **Licuefacción.** Población en celdas de MMI≥6 donde el modelo espera ≥ 0,10 de cobertura areal por licuefacción según `zhu_2017_general_model.tif`: **94 mil**. USGS declara para este evento alerta **naranja**, con 33 mil expuestas.

Las dos cifras se cuentan sobre las celdas del corte publicado (MMI≥6). **No son las de USGS y no se pueden comparar de frente**: aquí se cuenta la población entera de toda celda por encima del umbral, y USGS pondera la población de cada celda por el valor de esa celda. Son dos preguntas distintas sobre el mismo ráster.

**Y el umbral se evalúa en un solo punto por celda: su centroide.** El píxel del ráster es más pequeño que la celda, así que ese punto decide si entra la población entera de la celda o no entra ninguna. No es una estadística areal, y el sesgo que introduce no está medido: puede quedarse corto o pasarse.

Fuente: producto *Ground Failure* de USGS (v2), dominio público.

## Incertidumbre y calidad

Discrepancia entre GHS-POP y WorldPop en las bandas MMI publicadas: **13,4 %**.

## Cambios frente a la versión anterior

- ShakeMap: v0 → v2 (us)
- Ground Failure: v0 → v2 (us)
- Magnitud: M8,0 → M7,7
- Profundidad: 33 → 13 km
- Epicentro: reubicado 6 km
- Población en MMI≥6: 0 → 600 mil
- Población en MMI≥7: 0 → 260 mil
- Población en MMI≥8: 0 → 710
- Población de 65 años o más en MMI≥7: 0 → 39 mil
- Edificaciones en MMI≥7: 0 → 180 mil
- Sedes de salud en MMI≥7: 0 → 75
- Sedes educativas en MMI≥7: 0 → 350
- Población en probabilidad alta de deslizamiento: 0 → 16
- Población en cobertura areal alta por licuefacción: 0 → 94 mil

## Descargas

- [CSV por municipio](adm2.csv)
- [Mapa PNG](mapa_general.png)

## Procedencia

- ShakeMap consumido: **v2** de `us`
- Ground Failure consumido: **v2** de `us`
- Manifiesto de exposición: [`pan-v0.4`](https://github.com/sforero77/CENTINELA/blob/main/data/manifests/PAN.yaml)
- Pipeline: `0.1.0` · Generado: 2026-10-09T18:31:17Z

## Advertencias

- Exposición estimada, no daño observado.
- Este sistema no es una alerta temprana ni una recomendación de evacuación.
- No reemplaza a los servicios geológicos ni a las unidades de gestión del riesgo.
- Fuentes, vintages y versiones consumidas: ver manifiesto enlazado.
