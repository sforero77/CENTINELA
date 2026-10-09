# Exposición sísmica: M7,7 · 12 km al OSO de Pitaloza Arriba, Panamá

**Evento USGS:** `pt26282000` · **Origen:** 2026-10-09T17:56:08Z UTC · **Profundidad:** 12,6 km

## Exposición estimada

| Indicador | Estimado |
|---|---:|
| Población en MMI≥6 | 640 mil |
| Población en MMI≥7 | 350 mil |
| Población en MMI≥8 | 1.800 |
| Edificaciones en MMI≥7 | 240 mil |
| Sedes de salud en MMI≥7 | 176 |
| Sedes educativas en MMI≥7 | 602 |
| Vías primarias y secundarias en MMI≥7 | 780 km |
| Vías locales en MMI≥7 | 7.500 km |
| Superficie construida en MMI≥7 | 44,9 km² |

El satélite detecta **1,9 veces** más superficie construida de la que explicarían las 240 mil edificaciones registradas en MMI≥7. La diferencia suele ser asentamiento informal o zona rural dispersa sin mapear: **el conteo de edificaciones se queda corto ahí, y la superficie construida no**.

Las cifras de esta tabla van redondeadas a dos cifras significativas, que es la precisión que un modelo de exposición sostiene. Las exactas están en el CSV municipal y en `report.json`.

De la población en intensidad MMI≥7, alrededor de **50 mil** personas tienen 65 años o más.

## Municipios más expuestos, por población en MMI≥7

| # | Municipio | Código | MMI max | Población MMI≥7 |
|---:|---|---|---:|---:|
| 1 | Santiago | `PA1311` | 7,5 | 92 mil |
| 2 | Chitré | `PA0701` | 7,0 | 53 mil |
| 3 | Las Tablas | `PA0902` | 7,0 | 28 mil |
| 4 | Los Santos | `PA0903` | 7,5 | 27 mil |
| 5 | Ocú | `PA0704` | 7,5 | 16 mil |
| 6 | Aguadulce | `PA0301` | 7,0 | 14 mil |
| 7 | Pesé | `PA0706` | 7,5 | 13 mil |
| 8 | Atalaya | `PA1301` | 7,0 | 11 mil |
| 9 | Guararé | `PA0901` | 7,0 | 11 mil |
| 10 | Macaracas | `PA0904` | 7,5 | 9.500 |
| 11 | Parita | `PA0705` | 7,5 | 9.400 |
| 12 | Tonosí | `PA0907` | 7,5 | 9.200 |
| 13 | Los Pozos | `PA0703` | 8,0 | 8.000 |
| 14 | Las Minas | `PA0702` | 8,0 | 7.900 |
| 15 | Santa María | `PA0707` | 7,0 | 7.500 |

## Deslizamiento y licuefacción

- **Deslizamiento.** Población en celdas de MMI≥6 donde el modelo espera ≥ 0,10 de probabilidad de deslizamiento según `jessee_2018_model.tif`: **16**. USGS declara para este evento alerta **naranja**, con 470 expuestas.
- **Licuefacción.** Población en celdas de MMI≥6 donde el modelo espera ≥ 0,10 de cobertura areal por licuefacción según `zhu_2017_general_model.tif`: **110 mil**. USGS declara para este evento alerta **naranja**, con 36 mil expuestas.

Las dos cifras se cuentan sobre las celdas del corte publicado (MMI≥6). **No son las de USGS y no se pueden comparar de frente**: aquí se cuenta la población entera de toda celda por encima del umbral, y USGS pondera la población de cada celda por el valor de esa celda. Son dos preguntas distintas sobre el mismo ráster.

**Y el umbral se evalúa en un solo punto por celda: su centroide.** El píxel del ráster es más pequeño que la celda, así que ese punto decide si entra la población entera de la celda o no entra ninguna. No es una estadística areal, y el sesgo que introduce no está medido: puede quedarse corto o pasarse.

Fuente: producto *Ground Failure* de USGS (v4), dominio público.

## Referencia cruzada

PAGER (USGS) estima para este evento una alerta **roja**. CENTINELA no estima víctimas; la cifra se incluye solo como contraste.

Las dos cifras **no se tabulan igual** y no se pueden leer una contra otra: PAGER agrupa por MMI redondeado (su fila «7» es todo lo que cae entre 6,5 y 7,49) y CENTINELA usa bandas literales, donde MMI≥7 es MMI≥7. Puede además que no hablen del mismo ShakeMap: este reporte declara en «Procedencia» qué versión consumió, y PAGER pudo correr sobre otra versión o sobre otro producto del mismo sismo. El contraste banda a banda, hecho y comprobado para el sismo de San José del Palmar, está en `docs/PARA_INSTITUCIONES.md`.

## Incertidumbre y calidad

Discrepancia entre GHS-POP y WorldPop en las bandas MMI publicadas: **13,3 %**.

## Cambios frente a la versión anterior

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

- ShakeMap consumido: **v4** de `us`
- Ground Failure consumido: **v4** de `us`
- Manifiesto de exposición: [`pan-v0.4`](https://github.com/sforero77/CENTINELA/blob/main/data/manifests/PAN.yaml)
- Pipeline: `0.1.0` · Generado: 2026-10-09T18:51:10Z

## Advertencias

- Exposición estimada, no daño observado.
- Este sistema no es una alerta temprana ni una recomendación de evacuación.
- No reemplaza a los servicios geológicos ni a las unidades de gestión del riesgo.
- Fuentes, vintages y versiones consumidas: ver manifiesto enlazado.
