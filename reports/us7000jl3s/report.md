# Exposición sísmica: M6,8 · 14 km al NNO de Baláo, Ecuador

**Evento USGS:** `us7000jl3s` · **Origen:** 2023-03-18T17:12:52Z UTC · **Profundidad:** 68,0 km

> **Reconstrucción retrospectiva.** Este reporte se calculó después del evento, no en respuesta a él, y no cuenta para las métricas de latencia del sistema.
>
> La **población** corresponde a la época indicada en el manifiesto de exposición. Las **edificaciones, vías, sedes de salud y educativas son las actuales**: OpenStreetMap y Overture publican el estado presente, no el histórico. Léelas como "qué infraestructura de hoy caería en esa zona de intensidad", no como lo que había entonces.

## Exposición estimada

| Indicador | Estimado |
|---|---:|
| Población en MMI≥VI | 6,1 millones |
| Población en MMI≥VII | 750 mil |
| Población en MMI≥VIII | el evento no llegó a esta banda |
| Edificaciones en MMI≥VII | 250 mil |
| Sedes de salud en MMI≥VII | 279 |
| Sedes educativas en MMI≥VII | 240 |
| Vías primarias y secundarias en MMI≥VII | 580 km |
| Vías locales en MMI≥VII | 8.000 km |
| Superficie construida en MMI≥VII | 38,1 km² |

El satélite detecta **1,5 veces** más superficie construida de la que explicarían las 250 mil edificaciones registradas en MMI≥VII. La diferencia suele ser asentamiento informal o zona rural dispersa sin mapear: **el conteo de edificaciones se queda corto ahí, y la superficie construida no**.

Las cifras de esta tabla van redondeadas a dos cifras significativas, que es la precisión que un modelo de exposición sostiene. Las exactas están en el CSV municipal y en `report.json`.

De la población en intensidad MMI≥VII, alrededor de **55 mil** personas tienen 65 años o más.

## Municipios más expuestos, por población en MMI≥VII

| # | Municipio | Código | MMI max | Población MMI≥VII |
|---:|---|---|---:|---:|
| 1 | Machala | `EC0701` | 6,5 | 290 mil |
| 2 | Guayaquil | `EC0901` | 6,5 | 110 mil |
| 3 | Naranjal | `EC0911` | 6,5 | 83 mil |
| 4 | Santa Rosa | `EC0712` | 6,5 | 66 mil |
| 5 | Pasaje | `EC0709` | 6,5 | 65 mil |
| 6 | El Guabo | `EC0706` | 6,5 | 55 mil |
| 7 | Balao | `EC0903` | 6,5 | 26 mil |
| 8 | Arenillas | `EC0702` | 6,5 | 24 mil |
| 9 | Camilo Ponce Enríquez | `EC0115` | 6,5 | 16 mil |
| 10 | Durán | `EC0907` | 6,5 | 1.600 |
| 11 | Cuenca | `EC0101` | 6,5 | 1.400 |
| 12 | El Triunfo | `EC0909` | 6,5 | 1.200 |
| 13 | La Troncal | `EC0304` | 6,5 | 1.100 |
| 14 | Santa Isabel | `EC0108` | 6,5 | 610 |
| 15 | San Jacinto de Yaguachi | `EC0920` | 6,5 | 330 |

## Deslizamiento y licuefacción

- **Deslizamiento.** Población en celdas de MMI≥VI donde el modelo espera ≥ 0,10 de probabilidad de deslizamiento según `jessee_2018_model.tif`: **0**.
- **Licuefacción.** Población en celdas de MMI≥VI donde el modelo espera ≥ 0,10 de cobertura areal por licuefacción según `zhu_2017_general_model.tif`: **500 mil**. USGS declara para este evento alerta **roja**, con 150 mil expuestas.

Las dos cifras se cuentan sobre las celdas del corte publicado (MMI≥VI). **No son las de USGS y no se pueden comparar de frente**: aquí se cuenta la población entera de toda celda por encima del umbral, y USGS pondera la población de cada celda por el valor de esa celda. Son dos preguntas distintas sobre el mismo ráster.

**Y el umbral se evalúa en un solo punto por celda: su centroide.** El píxel del ráster es más pequeño que la celda, así que ese punto decide si entra la población entera de la celda o no entra ninguna. No es una estadística areal, y el sesgo que introduce no está medido: puede quedarse corto o pasarse.

Fuente: producto *Ground Failure* de USGS (v9), dominio público.

## Referencia cruzada

PAGER (USGS) estima para este evento una alerta **naranja**. CENTINELA no estima víctimas; la cifra se incluye solo como contraste.

Las dos cifras usan **la misma convención**: las clases de intensidad del USGS en números romanos (VI desde MMI 5,5, VII desde 6,5, VIII desde 7,5). Lo que puede separarlas es el insumo: este reporte declara en «Procedencia» qué versión del ShakeMap consumió, PAGER pudo correr sobre otra versión o sobre otro producto del mismo sismo, y los dos usan modelos de población distintos (GHS-POP aquí, LandScan en PAGER). El contraste clase a clase, hecho y comprobado para el sismo de San José del Palmar, está en `docs/PARA_INSTITUCIONES.md`.

## Incertidumbre y calidad

Discrepancia entre GHS-POP y WorldPop en las bandas MMI publicadas: **0,7 %**.

## Cambios frente a la versión anterior

- Recálculo con el mismo ShakeMap v7 (us) (cambió el cálculo o el activo de exposición, no USGS)
- Cambio de convención: las franjas son ahora las clases de intensidad del USGS (VI desde MMI 5,5, VII desde 6,5, VIII desde 7,5), no decimales literales (≥6,0 / ≥7,0 / ≥8,0). Las cifras cambian por la regla, no por los datos.
- Población en MMI≥VI: 4,8 millones → 6,1 millones
- Población en MMI≥VII: 0 → 750 mil
- Población de 65 años o más en MMI≥VII: 0 → 55 mil
- Edificaciones en MMI≥VII: 0 → 250 mil
- Sedes de salud en MMI≥VII: 0 → 280
- Sedes educativas en MMI≥VII: 0 → 240

## Descargas

- [CSV por municipio](adm2.csv)
- [Mapa PNG](mapa_general.png)

## Procedencia

- ShakeMap consumido: **v7** de `us`
- Ground Failure consumido: **v9** de `us`
- Manifiesto de exposición: [`ecu-v0.5`](https://github.com/sforero77/CENTINELA/blob/main/data/manifests/ECU.yaml)
- Pipeline: `0.1.0` · Generado: 2026-11-21T16:29:59Z

## Advertencias

- Exposición estimada, no daño observado.
- Este sistema no es una alerta temprana ni una recomendación de evacuación.
- No reemplaza a los servicios geológicos ni a las unidades de gestión del riesgo.
- Fuentes, vintages y versiones consumidas: ver manifiesto enlazado.
