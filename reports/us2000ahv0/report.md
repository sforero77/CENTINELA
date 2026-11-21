# Exposición sísmica: M8,2 · Terremoto de Tehuantepec, México (2017)

**Evento USGS:** `us2000ahv0` · **Origen:** 2017-09-08T04:49:19Z UTC · **Profundidad:** 47,4 km

> **Reconstrucción retrospectiva.** Este reporte se calculó después del evento, no en respuesta a él, y no cuenta para las métricas de latencia del sistema.
>
> La **población** corresponde a la época indicada en el manifiesto de exposición. Las **edificaciones, vías, sedes de salud y educativas son las actuales**: OpenStreetMap y Overture publican el estado presente, no el histórico. Léelas como "qué infraestructura de hoy caería en esa zona de intensidad", no como lo que había entonces.

## Exposición estimada

| Indicador | Estimado |
|---|---:|
| Población en MMI≥VI | 1,5 millones |
| Población en MMI≥VII | 65 mil |
| Población en MMI≥VIII | el evento no llegó a esta banda |
| Edificaciones en MMI≥VII | 46 mil |
| Sedes de salud en MMI≥VII | 5 |
| Sedes educativas en MMI≥VII | 8 |
| Vías primarias y secundarias en MMI≥VII | 66 km |
| Vías locales en MMI≥VII | 1.200 km |
| Superficie construida en MMI≥VII | 7,5 km² |

El satélite detecta **1,6 veces** más superficie construida de la que explicarían las 46 mil edificaciones registradas en MMI≥VII. La diferencia suele ser asentamiento informal o zona rural dispersa sin mapear: **el conteo de edificaciones se queda corto ahí, y la superficie construida no**.

Las cifras de esta tabla van redondeadas a dos cifras significativas, que es la precisión que un modelo de exposición sostiene. Las exactas están en el CSV municipal y en `report.json`.

De la población en intensidad MMI≥VII, alrededor de **6.500** personas tienen 65 años o más.

## Municipios más expuestos, por población en MMI≥VII

| # | Municipio | Código | MMI max | Población MMI≥VII |
|---:|---|---|---:|---:|
| 1 | Pijijiapan | `MX07069` | 6,5 | 52 mil |
| 2 | San Francisco Ixhuatán | `MX20143` | 6,5 | 3.500 |
| 3 | San Pedro Tapanatepec | `MX20327` | 6,5 | 3.200 |
| 4 | Mapastepec | `MX07051` | 6,5 | 2.800 |
| 5 | Arriaga | `MX07009` | 6,5 | 2.000 |
| 6 | San Francisco del Mar | `MX20141` | 6,5 | 1.900 |

## Deslizamiento y licuefacción

- **Deslizamiento.** Población en celdas de MMI≥VI donde el modelo espera ≥ 0,10 de probabilidad de deslizamiento según `nowicki_2014_global_model.tif`: **3.700**. USGS declara para este evento alerta **naranja**, con 210 expuestas.
- **Licuefacción.** Población en celdas de MMI≥VI donde el modelo espera ≥ 0,10 de cobertura areal por licuefacción según `zhu_2017_general_model.tif`: **550 mil**. USGS declara para este evento alerta **roja**, con 150 mil expuestas.

Las dos cifras se cuentan sobre las celdas del corte publicado (MMI≥VI). **No son las de USGS y no se pueden comparar de frente**: aquí se cuenta la población entera de toda celda por encima del umbral, y USGS pondera la población de cada celda por el valor de esa celda. Son dos preguntas distintas sobre el mismo ráster.

**Y el umbral se evalúa en un solo punto por celda: su centroide.** El píxel del ráster es más pequeño que la celda, así que ese punto decide si entra la población entera de la celda o no entra ninguna. No es una estadística areal, y el sesgo que introduce no está medido: puede quedarse corto o pasarse.

Fuente: producto *Ground Failure* de USGS (v1), dominio público.

## Referencia cruzada

PAGER (USGS) estima para este evento una alerta **roja**. CENTINELA no estima víctimas; la cifra se incluye solo como contraste.

Las dos cifras usan **la misma convención**: las clases de intensidad del USGS en números romanos (VI desde MMI 5,5, VII desde 6,5, VIII desde 7,5). Lo que puede separarlas es el insumo: este reporte declara en «Procedencia» qué versión del ShakeMap consumió, PAGER pudo correr sobre otra versión o sobre otro producto del mismo sismo, y los dos usan modelos de población distintos (GHS-POP aquí, LandScan en PAGER). El contraste clase a clase, hecho y comprobado para el sismo de San José del Palmar, está en `docs/PARA_INSTITUCIONES.md`.

## Incertidumbre y calidad

Discrepancia entre GHS-POP y WorldPop en las bandas MMI publicadas: **13,1 %**.

## Cambios frente a la versión anterior

- Recálculo con el mismo ShakeMap v1 (atlas) (cambió el cálculo o el activo de exposición, no USGS)
- Cambio de convención: las franjas son ahora las clases de intensidad del USGS (VI desde MMI 5,5, VII desde 6,5, VIII desde 7,5), no decimales literales (≥6,0 / ≥7,0 / ≥8,0). Las cifras cambian por la regla, no por los datos.
- Población en MMI≥VI: 760 mil → 1,5 millones
- Población en MMI≥VII: 0 → 65 mil
- Población de 65 años o más en MMI≥VII: 0 → 6.500
- Edificaciones en MMI≥VII: 0 → 46 mil
- Sedes de salud en MMI≥VII: 0 → 5
- Sedes educativas en MMI≥VII: 0 → 8
- Población en probabilidad alta de deslizamiento: 2.100 → 3.700
- Población en cobertura areal alta por licuefacción: 360 mil → 550 mil

## Descargas

- [CSV por municipio](adm2.csv)
- [Mapa PNG](mapa_general.png)

## Procedencia

- ShakeMap consumido: **v1** de `atlas`
- Ground Failure consumido: **v1** de `us`
- Manifiesto de exposición: [`mex-v0.5`](https://github.com/sforero77/CENTINELA/blob/main/data/manifests/MEX.yaml)
- Pipeline: `0.1.0` · Generado: 2026-11-21T16:31:45Z

## Advertencias

- Exposición estimada, no daño observado.
- Este sistema no es una alerta temprana ni una recomendación de evacuación.
- No reemplaza a los servicios geológicos ni a las unidades de gestión del riesgo.
- Fuentes, vintages y versiones consumidas: ver manifiesto enlazado.
