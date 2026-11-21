# Exposición sísmica: M7,5 · 20 km al O de Catia La Mar, Venezuela

**Evento USGS:** `us6000t7zp` · **Origen:** 2026-06-24T22:05:04Z UTC · **Profundidad:** 10,0 km

> **Reconstrucción retrospectiva.** Este reporte se calculó después del evento, no en respuesta a él, y no cuenta para las métricas de latencia del sistema.
>
> La **población** corresponde a la época indicada en el manifiesto de exposición. Las **edificaciones, vías, sedes de salud y educativas son las actuales**: OpenStreetMap y Overture publican el estado presente, no el histórico. Léelas como "qué infraestructura de hoy caería en esa zona de intensidad", no como lo que había entonces.

## Exposición estimada

| Indicador | Estimado |
|---|---:|
| Población en MMI≥VI | 9,6 millones |
| Población en MMI≥VII | 4,5 millones |
| Población en MMI≥VIII | 900 mil |
| Edificaciones en MMI≥VII | 930 mil |
| Sedes de salud en MMI≥VII | 952 |
| Sedes educativas en MMI≥VII | 1.436 |
| Vías primarias y secundarias en MMI≥VII | 1.900 km |
| Vías locales en MMI≥VII | 11 mil km |
| Superficie construida en MMI≥VII | 144,6 km² |

El satélite detecta **1,6 veces** más superficie construida de la que explicarían las 930 mil edificaciones registradas en MMI≥VII. La diferencia suele ser asentamiento informal o zona rural dispersa sin mapear: **el conteo de edificaciones se queda corto ahí, y la superficie construida no**.

Las cifras de esta tabla van redondeadas a dos cifras significativas, que es la precisión que un modelo de exposición sostiene. Las exactas están en el CSV municipal y en `report.json`.

De la población en intensidad MMI≥VII, alrededor de **560 mil** personas tienen 65 años o más.

## Municipios más expuestos, por población en MMI≥VII

| # | Municipio | Código | MMI max | Población MMI≥VII |
|---:|---|---|---:|---:|
| 1 | Libertador | `VE0101` | 7,5 | 1,5 millones |
| 2 | Sucre | `VE1519` | 7,5 | 720 mil |
| 3 | Vargas | `VE2401` | 8,0 | 390 mil |
| 4 | Baruta | `VE1503` | 7,0 | 310 mil |
| 5 | Plaza | `VE1517` | 7,0 | 220 mil |
| 6 | Puerto Cabello | `VE0811` | 8,0 | 210 mil |
| 7 | Zamora | `VE1521` | 7,0 | 210 mil |
| 8 | San Felipe | `VE2211` | 8,0 | 140 mil |
| 9 | Veroes | `VE2214` | 8,5 | 100 mil |
| 10 | Chacao | `VE1507` | 7,5 | 88 mil |
| 11 | El Hatillo | `VE1509` | 7,0 | 72 mil |
| 12 | Bolivariano Guaicaipuro | `VE1510` | 6,5 | 62 mil |
| 13 | Los Salías | `VE1513` | 6,5 | 60 mil |
| 14 | Juan José Mora | `VE0805` | 8,5 | 58 mil |
| 15 | Silva | `VE1120` | 8,0 | 34 mil |

## Deslizamiento y licuefacción

- **Deslizamiento.** Población en celdas de MMI≥VI donde el modelo espera ≥ 0,10 de probabilidad de deslizamiento según `jessee_2018_model.tif`: **29 mil**. USGS declara para este evento alerta **roja**, con 16 mil expuestas.
- **Licuefacción.** Población en celdas de MMI≥VI donde el modelo espera ≥ 0,10 de cobertura areal por licuefacción según `zhu_2017_general_model.tif`: **460 mil**. USGS declara para este evento alerta **roja**, con 170 mil expuestas.

Las dos cifras se cuentan sobre las celdas del corte publicado (MMI≥VI). **No son las de USGS y no se pueden comparar de frente**: aquí se cuenta la población entera de toda celda por encima del umbral, y USGS pondera la población de cada celda por el valor de esa celda. Son dos preguntas distintas sobre el mismo ráster.

**Y el umbral se evalúa en un solo punto por celda: su centroide.** El píxel del ráster es más pequeño que la celda, así que ese punto decide si entra la población entera de la celda o no entra ninguna. No es una estadística areal, y el sesgo que introduce no está medido: puede quedarse corto o pasarse.

Fuente: producto *Ground Failure* de USGS (v13), dominio público.

## Referencia cruzada

PAGER (USGS) estima para este evento una alerta **roja**. CENTINELA no estima víctimas; la cifra se incluye solo como contraste.

Las dos cifras usan **la misma convención**: las clases de intensidad del USGS en números romanos (VI desde MMI 5,5, VII desde 6,5, VIII desde 7,5). Lo que puede separarlas es el insumo: este reporte declara en «Procedencia» qué versión del ShakeMap consumió, PAGER pudo correr sobre otra versión o sobre otro producto del mismo sismo, y los dos usan modelos de población distintos (GHS-POP aquí, LandScan en PAGER). El contraste clase a clase, hecho y comprobado para el sismo de San José del Palmar, está en `docs/PARA_INSTITUCIONES.md`.

## Incertidumbre y calidad

Discrepancia entre GHS-POP y WorldPop en las bandas MMI publicadas: **12,4 %**.

## Cambios frente a la versión anterior

- Recálculo con el mismo ShakeMap v16 (us) (cambió el cálculo o el activo de exposición, no USGS)
- Cambio de convención: las franjas son ahora las clases de intensidad del USGS (VI desde MMI 5,5, VII desde 6,5, VIII desde 7,5), no decimales literales (≥6,0 / ≥7,0 / ≥8,0). Las cifras cambian por la regla, no por los datos.
- Población en MMI≥VI: 7,5 millones → 9,6 millones
- Población en MMI≥VII: 2,6 millones → 4,5 millones
- Población en MMI≥VIII: 700 mil → 900 mil
- Población de 65 años o más en MMI≥VII: 320 mil → 560 mil
- Edificaciones en MMI≥VII: 560 mil → 930 mil
- Sedes de salud en MMI≥VII: 770 → 950
- Sedes educativas en MMI≥VII: 1.000 → 1.400
- Población en cobertura areal alta por licuefacción: 350 mil → 460 mil

## Descargas

- [CSV por municipio](adm2.csv)
- [Mapa PNG](mapa_general.png)

## Procedencia

- ShakeMap consumido: **v16** de `us`
- Ground Failure consumido: **v13** de `us`
- Manifiesto de exposición: [`ven-v0.5`](https://github.com/sforero77/CENTINELA/blob/main/data/manifests/VEN.yaml)
- Pipeline: `0.1.0` · Generado: 2026-11-21T16:29:30Z

## Advertencias

- Exposición estimada, no daño observado.
- Este sistema no es una alerta temprana ni una recomendación de evacuación.
- No reemplaza a los servicios geológicos ni a las unidades de gestión del riesgo.
- Fuentes, vintages y versiones consumidas: ver manifiesto enlazado.
