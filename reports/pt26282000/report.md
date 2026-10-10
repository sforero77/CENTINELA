# Exposición sísmica: M7,7 · 12 km al OSO de Pitaloza Arriba, Panamá

**Evento USGS:** `pt26282000` · **Origen:** 2026-10-09T17:56:08Z UTC · **Profundidad:** 12,6 km

## Exposición estimada

| Indicador | Estimado |
|---|---:|
| Población en MMI≥6 | 710 mil |
| Población en MMI≥7 | 370 mil |
| Población en MMI≥8 | 34 mil |
| Edificaciones en MMI≥7 | 250 mil |
| Sedes de salud en MMI≥7 | 184 |
| Sedes educativas en MMI≥7 | 611 |
| Vías primarias y secundarias en MMI≥7 | 890 km |
| Vías locales en MMI≥7 | 8.000 km |
| Superficie construida en MMI≥7 | 47,4 km² |

El satélite detecta **1,9 veces** más superficie construida de la que explicarían las 250 mil edificaciones registradas en MMI≥7. La diferencia suele ser asentamiento informal o zona rural dispersa sin mapear: **el conteo de edificaciones se queda corto ahí, y la superficie construida no**.

Las cifras de esta tabla van redondeadas a dos cifras significativas, que es la precisión que un modelo de exposición sostiene. Las exactas están en el CSV municipal y en `report.json`.

De la población en intensidad MMI≥7, alrededor de **54 mil** personas tienen 65 años o más.

## Municipios más expuestos, por población en MMI≥7

| # | Municipio | Código | MMI max | Población MMI≥7 |
|---:|---|---|---:|---:|
| 1 | Santiago | `PA1311` | 8,5 | 95 mil |
| 2 | Chitré | `PA0701` | 7,0 | 53 mil |
| 3 | Las Tablas | `PA0902` | 8,5 | 28 mil |
| 4 | Los Santos | `PA0903` | 7,5 | 27 mil |
| 5 | Soná | `PA1312` | 8,0 | 23 mil |
| 6 | Ocú | `PA0704` | 8,0 | 16 mil |
| 7 | Pesé | `PA0706` | 7,5 | 13 mil |
| 8 | Atalaya | `PA1301` | 7,5 | 11 mil |
| 9 | Guararé | `PA0901` | 7,5 | 11 mil |
| 10 | Tonosí | `PA0907` | 9,0 | 10 mil |
| 11 | Macaracas | `PA0904` | 8,5 | 9.500 |
| 12 | Parita | `PA0705` | 7,0 | 9.400 |
| 13 | Aguadulce | `PA0301` | 7,0 | 9.100 |
| 14 | Los Pozos | `PA0703` | 8,5 | 8.000 |
| 15 | Las Minas | `PA0702` | 8,5 | 7.900 |

## Deslizamiento y licuefacción

- **Deslizamiento.** Población en celdas de MMI≥6 donde el modelo espera ≥ 0,10 de probabilidad de deslizamiento según `jessee_2018_model.tif`: **970**. USGS declara para este evento alerta **roja**, con 860 expuestas.
- **Licuefacción.** Población en celdas de MMI≥6 donde el modelo espera ≥ 0,10 de cobertura areal por licuefacción según `zhu_2017_general_model.tif`: **100 mil**. USGS declara para este evento alerta **naranja**, con 36 mil expuestas.

Las dos cifras se cuentan sobre las celdas del corte publicado (MMI≥6). **No son las de USGS y no se pueden comparar de frente**: aquí se cuenta la población entera de toda celda por encima del umbral, y USGS pondera la población de cada celda por el valor de esa celda. Son dos preguntas distintas sobre el mismo ráster.

**Y el umbral se evalúa en un solo punto por celda: su centroide.** El píxel del ráster es más pequeño que la celda, así que ese punto decide si entra la población entera de la celda o no entra ninguna. No es una estadística areal, y el sesgo que introduce no está medido: puede quedarse corto o pasarse.

Fuente: producto *Ground Failure* de USGS (v8), dominio público.

## Referencia cruzada

PAGER (USGS) estima para este evento una alerta **roja**. CENTINELA no estima víctimas; la cifra se incluye solo como contraste.

Las dos cifras **no se tabulan igual** y no se pueden leer una contra otra: PAGER agrupa por MMI redondeado (su fila «7» es todo lo que cae entre 6,5 y 7,49) y CENTINELA usa bandas literales, donde MMI≥7 es MMI≥7. Puede además que no hablen del mismo ShakeMap: este reporte declara en «Procedencia» qué versión consumió, y PAGER pudo correr sobre otra versión o sobre otro producto del mismo sismo. El contraste banda a banda, hecho y comprobado para el sismo de San José del Palmar, está en `docs/PARA_INSTITUCIONES.md`.

## Incertidumbre y calidad

Discrepancia entre GHS-POP y WorldPop en las bandas MMI publicadas: **12,6 %**.

## Cambios frente a la versión anterior

- Ground Failure: v7 (us) → v8 (us)
- Población en probabilidad alta de deslizamiento: 720 → 970
- Población en cobertura areal alta por licuefacción: 89 mil → 100 mil
- ShakeMap: v7 (us) → v8 (us)
- Población en MMI≥6: 620 mil → 710 mil
- Población en MMI≥7: 240 mil → 370 mil
- Población en MMI≥8: 21 mil → 34 mil
- Población de 65 años o más en MMI≥7: 36 mil → 54 mil
- Edificaciones en MMI≥7: 180 mil → 250 mil
- Sedes de salud en MMI≥7: 160 → 180
- Sedes educativas en MMI≥7: 530 → 610
- Ground Failure: v6 (us) → v7 (us)
- Población en probabilidad alta de deslizamiento: 150 → 720
- Población en cobertura areal alta por licuefacción: 86 mil → 89 mil
- ShakeMap: v6 (us) → v7 (us)
- Población en MMI≥6: 630 mil → 620 mil
- Población en MMI≥7: 150 mil → 240 mil
- Población en MMI≥8: 14 mil → 21 mil
- Población de 65 años o más en MMI≥7: 25 mil → 36 mil
- Edificaciones en MMI≥7: 110 mil → 180 mil
- Sedes de salud en MMI≥7: 44 → 160
- Sedes educativas en MMI≥7: 180 → 530
- Población en cobertura areal alta por licuefacción: 90 mil → 86 mil
- ShakeMap: v5 (us) → v6 (us)
- Ground Failure: v5 (us) → v6 (us)
- Población en MMI≥6: 560 mil → 630 mil
- Sedes de salud en MMI≥7: 43 → 44
- Población en cobertura areal alta por licuefacción: 85 mil → 90 mil
- ShakeMap: v4 (us) → v5 (us)
- Ground Failure: v4 (us) → v5 (us)
- Población en MMI≥6: 640 mil → 560 mil
- Población en MMI≥7: 350 mil → 150 mil
- Población en MMI≥8: 1.800 → 14 mil
- Población de 65 años o más en MMI≥7: 50 mil → 25 mil
- Edificaciones en MMI≥7: 240 mil → 110 mil
- Sedes de salud en MMI≥7: 180 → 43
- Sedes educativas en MMI≥7: 600 → 180
- Población en probabilidad alta de deslizamiento: 16 → 150
- Población en cobertura areal alta por licuefacción: 110 mil → 85 mil
- ShakeMap: v2 (us) → v4 (us)
- Ground Failure: v2 (us) → v4 (us)
- Población en MMI≥6: 600 mil → 640 mil
- Población en MMI≥7: 260 mil → 350 mil
- Población en MMI≥8: 710 → 1.800
- Población de 65 años o más en MMI≥7: 39 mil → 50 mil
- Edificaciones en MMI≥7: 180 mil → 240 mil
- Sedes de salud en MMI≥7: 75 → 180
- Sedes educativas en MMI≥7: 350 → 600
- Población en cobertura areal alta por licuefacción: 94 mil → 110 mil
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

- ShakeMap consumido: **v8** de `us`
- Ground Failure consumido: **v8** de `us`
- Manifiesto de exposición: [`pan-v0.4`](https://github.com/sforero77/CENTINELA/blob/main/data/manifests/PAN.yaml)
- Pipeline: `0.1.0` · Generado: 2026-10-10T00:11:14Z

## Advertencias

- Exposición estimada, no daño observado.
- Este sistema no es una alerta temprana ni una recomendación de evacuación.
- No reemplaza a los servicios geológicos ni a las unidades de gestión del riesgo.
- Fuentes, vintages y versiones consumidas: ver manifiesto enlazado.
