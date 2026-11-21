# Exposición sísmica: M7,7 · 10 km al OSO de Pitaloza Arriba, Panamá

**Evento USGS:** `pt26282000` · **Origen:** 2026-10-09T17:56:08Z UTC · **Profundidad:** 10,0 km

## Exposición estimada

| Indicador | Estimado |
|---|---:|
| Población en MMI≥VI | 540 mil |
| Población en MMI≥VII | 70 mil |
| Población en MMI≥VIII | 9.000 |
| Edificaciones en MMI≥VII | 56 mil |
| Sedes de salud en MMI≥VII | 15 |
| Sedes educativas en MMI≥VII | 76 |
| Vías primarias y secundarias en MMI≥VII | 230 km |
| Vías locales en MMI≥VII | 2.200 km |
| Superficie construida en MMI≥VII | 8,6 km² |

El satélite detecta **1,5 veces** más superficie construida de la que explicarían las 56 mil edificaciones registradas en MMI≥VII. La diferencia suele ser asentamiento informal o zona rural dispersa sin mapear: **el conteo de edificaciones se queda corto ahí, y la superficie construida no**.

Las cifras de esta tabla van redondeadas a dos cifras significativas, que es la precisión que un modelo de exposición sostiene. Las exactas están en el CSV municipal y en `report.json`.

De la población en intensidad MMI≥VII, alrededor de **12 mil** personas tienen 65 años o más.

## Municipios más expuestos, por población en MMI≥VII

| # | Municipio | Código | MMI max | Población MMI≥VII |
|---:|---|---|---:|---:|
| 1 | Soná | `PA1312` | 7,5 | 22 mil |
| 2 | Las Tablas | `PA0902` | 7,0 | 12 mil |
| 3 | Tonosí | `PA0907` | 7,5 | 9.700 |
| 4 | Los Santos | `PA0903` | 6,5 | 6.200 |
| 5 | Mariato | `PA1306` | 7,5 | 5.100 |
| 6 | Río de Jesús | `PA1308` | 6,5 | 4.900 |
| 7 | Pedasí | `PA0905` | 7,0 | 4.200 |
| 8 | Montijo | `PA1307` | 7,5 | 2.100 |
| 9 | Pocrí | `PA0906` | 6,5 | 1.900 |
| 10 | Santiago | `PA1311` | 7,0 | 1.000 |
| 11 | Guararé | `PA0901` | 6,5 | 650 |
| 12 | Macaracas | `PA0904` | 6,5 | 340 |
| 13 | Las Minas | `PA0702` | 6,5 | 290 |
| 14 | Ocú | `PA0704` | 6,5 | 210 |
| 15 | La Mesa | `PA1304` | 6,5 | 8 |

## Deslizamiento y licuefacción

- **Deslizamiento.** Población en celdas de MMI≥VI donde el modelo espera ≥ 0,10 de probabilidad de deslizamiento según `jessee_2018_model.tif`: **34**. USGS declara para este evento alerta **naranja**, con 230 expuestas.
- **Licuefacción.** Población en celdas de MMI≥VI donde el modelo espera ≥ 0,10 de cobertura areal por licuefacción según `zhu_2017_general_model.tif`: **78 mil**. USGS declara para este evento alerta **naranja**, con 51 mil expuestas.

Las dos cifras se cuentan sobre las celdas del corte publicado (MMI≥VI). **No son las de USGS y no se pueden comparar de frente**: aquí se cuenta la población entera de toda celda por encima del umbral, y USGS pondera la población de cada celda por el valor de esa celda. Son dos preguntas distintas sobre el mismo ráster.

**Y el umbral se evalúa en un solo punto por celda: su centroide.** El píxel del ráster es más pequeño que la celda, así que ese punto decide si entra la población entera de la celda o no entra ninguna. No es una estadística areal, y el sesgo que introduce no está medido: puede quedarse corto o pasarse.

Fuente: producto *Ground Failure* de USGS (v14), dominio público.

## Referencia cruzada

PAGER (USGS) estima para este evento una alerta **naranja**. CENTINELA no estima víctimas; la cifra se incluye solo como contraste.

Las dos cifras usan **la misma convención**: las clases de intensidad del USGS en números romanos (VI desde MMI 5,5, VII desde 6,5, VIII desde 7,5). Lo que puede separarlas es el insumo: este reporte declara en «Procedencia» qué versión del ShakeMap consumió, PAGER pudo correr sobre otra versión o sobre otro producto del mismo sismo, y los dos usan modelos de población distintos (GHS-POP aquí, LandScan en PAGER). El contraste clase a clase, hecho y comprobado para el sismo de San José del Palmar, está en `docs/PARA_INSTITUCIONES.md`.

## Incertidumbre y calidad

Discrepancia entre GHS-POP y WorldPop en las bandas MMI publicadas: **14,2 %**.

## Cambios frente a la versión anterior

- Recálculo con el mismo ShakeMap v15 (us) (cambió el cálculo o el activo de exposición, no USGS)
- Cambio de convención: las franjas son ahora las clases de intensidad del USGS (VI desde MMI 5,5, VII desde 6,5, VIII desde 7,5), no decimales literales (≥6,0 / ≥7,0 / ≥8,0). Las cifras cambian por la regla, no por los datos.
- Población en MMI≥VI: 300 mil → 540 mil
- Población en MMI≥VII: 20 mil → 70 mil
- Población en MMI≥VIII: 0 → 9.000
- Población de 65 años o más en MMI≥VII: 3.000 → 12 mil
- Edificaciones en MMI≥VII: 17 mil → 56 mil
- Sedes de salud en MMI≥VII: 6 → 15
- Sedes educativas en MMI≥VII: 17 → 76
- Población en cobertura areal alta por licuefacción: 50 mil → 78 mil
- ShakeMap: v14 (us) → v15 (us)
- Ninguna cifra publicada cambia frente a la versión anterior.
- ShakeMap: v12 (us) → v14 (us)
- Ground Failure: v12 (us) → v14 (us)
- Profundidad: 13 → 10 km
- Epicentro: reubicado 3 km
- Población en MMI≥6: 290 mil → 300 mil
- Sedes educativas en MMI≥7: 18 → 17
- Población en probabilidad alta de deslizamiento: 36 → 34
- Población en cobertura areal alta por licuefacción: 49 mil → 50 mil
- ShakeMap: v11 (us) → v12 (us)
- Ground Failure: v11 (us) → v12 (us)
- Población en MMI≥6: 420 mil → 290 mil
- Población en MMI≥7: 18 mil → 20 mil
- Población de 65 años o más en MMI≥7: 2.900 → 3.000
- Edificaciones en MMI≥7: 15 mil → 17 mil
- Sedes de salud en MMI≥7: 5 → 6
- Sedes educativas en MMI≥7: 15 → 18
- Población en probabilidad alta de deslizamiento: 0 → 36
- Población en cobertura areal alta por licuefacción: 57 mil → 49 mil
- ShakeMap: v10 (us) → v11 (us)
- Ground Failure: v10 (us) → v11 (us)
- Población en MMI≥6: 210 mil → 420 mil
- Población en MMI≥7: 8.700 → 18 mil
- Población de 65 años o más en MMI≥7: 1.300 → 2.900
- Edificaciones en MMI≥7: 8.000 → 15 mil
- Sedes de salud en MMI≥7: 1 → 5
- Sedes educativas en MMI≥7: 8 → 15
- Población en cobertura areal alta por licuefacción: 29 mil → 57 mil
- ShakeMap: v9 (us) → v10 (us)
- Ground Failure: v9 (us) → v10 (us)
- Población en MMI≥6: 660 mil → 210 mil
- Población en MMI≥7: 270 mil → 8.700
- Población en MMI≥8: 27 mil → 0
- Población de 65 años o más en MMI≥7: 42 mil → 1.300
- Edificaciones en MMI≥7: 200 mil → 8.000
- Sedes de salud en MMI≥7: 73 → 1
- Sedes educativas en MMI≥7: 360 → 8
- Población en probabilidad alta de deslizamiento: 600 → 0
- Población en cobertura areal alta por licuefacción: 96 mil → 29 mil
- ShakeMap: v8 (us) → v9 (us)
- Ground Failure: v8 (us) → v9 (us)
- Población en MMI≥6: 710 mil → 660 mil
- Población en MMI≥7: 370 mil → 270 mil
- Población en MMI≥8: 34 mil → 27 mil
- Población de 65 años o más en MMI≥7: 54 mil → 42 mil
- Edificaciones en MMI≥7: 250 mil → 200 mil
- Sedes de salud en MMI≥7: 180 → 73
- Sedes educativas en MMI≥7: 610 → 360
- Población en probabilidad alta de deslizamiento: 970 → 600
- Población en cobertura areal alta por licuefacción: 100 mil → 96 mil
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

- ShakeMap consumido: **v15** de `us`
- Ground Failure consumido: **v14** de `us`
- Manifiesto de exposición: [`pan-v0.5`](https://github.com/sforero77/CENTINELA/blob/main/data/manifests/PAN.yaml)
- Pipeline: `0.1.0` · Generado: 2026-11-21T16:28:56Z

## Advertencias

- Exposición estimada, no daño observado.
- Este sistema no es una alerta temprana ni una recomendación de evacuación.
- No reemplaza a los servicios geológicos ni a las unidades de gestión del riesgo.
- Fuentes, vintages y versiones consumidas: ver manifiesto enlazado.
