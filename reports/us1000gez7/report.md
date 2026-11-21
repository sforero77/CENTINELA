# Exposición sísmica: M7,3 · 40 km al ENE de Carúpano, Venezuela

**Evento USGS:** `us1000gez7` · **Origen:** 2018-08-21T21:31:47Z UTC · **Profundidad:** 146,8 km

> **Reconstrucción retrospectiva.** Este reporte se calculó después del evento, no en respuesta a él, y no cuenta para las métricas de latencia del sistema.
>
> La **población** corresponde a la época indicada en el manifiesto de exposición. Las **edificaciones, vías, sedes de salud y educativas son las actuales**: OpenStreetMap y Overture publican el estado presente, no el histórico. Léelas como "qué infraestructura de hoy caería en esa zona de intensidad", no como lo que había entonces.

## Exposición estimada

| Indicador | Estimado |
|---|---:|
| Población en MMI≥VI | 500 mil |
| Población en MMI≥VII | el evento no llegó a esta banda |
| Población en MMI≥VIII | el evento no llegó a esta banda |
| Edificaciones en MMI≥VI | 210 mil |
| Sedes de salud en MMI≥VI | 54 |
| Sedes educativas en MMI≥VI | 243 |
| Vías primarias y secundarias en MMI≥VI | 580 km |
| Vías locales en MMI≥VI | 3.200 km |
| Superficie construida en MMI≥VI | 26,0 km² |

Las cifras de esta tabla van redondeadas a dos cifras significativas, que es la precisión que un modelo de exposición sostiene. Las exactas están en el CSV municipal y en `report.json`.

De la población en intensidad MMI≥VI, alrededor de **41 mil** personas tienen 65 años o más.

## Municipios más expuestos, por población en MMI≥VI

| # | Municipio | Código | MMI max | Población MMI≥VI |
|---:|---|---|---:|---:|
| 1 | Bermúdez | `VE1905` | 5,5 | 160 mil |
| 2 | Arismendi | `VE1903` | 5,5 | 52 mil |
| 3 | Bolívar | `VE1603` | 5,5 | 45 mil |
| 4 | Valdez | `VE1915` | 5,5 | 40 mil |
| 5 | Ribero | `VE1913` | 5,5 | 39 mil |
| 6 | Andrés Eloy Blanco | `VE1901` | 5,5 | 38 mil |
| 7 | Punceres | `VE1610` | 5,5 | 26 mil |
| 8 | Cajigal | `VE1907` | 6,0 | 23 mil |
| 9 | Benítez | `VE1904` | 6,0 | 22 mil |
| 10 | Mariño | `VE1910` | 5,5 | 22 mil |
| 11 | Libertador | `VE1909` | 6,0 | 18 mil |
| 12 | Andrés Mata | `VE1902` | 5,5 | 10 mil |
| 13 | Maturín | `VE1608` | 5,5 | 3.200 |
| 14 | Dependencias Federales | `VE2501` | 5,5 | 1.300 |

## Deslizamiento y licuefacción

- **Deslizamiento.** Población en celdas de MMI≥VI donde el modelo espera ≥ 0,10 de probabilidad de deslizamiento según `nowicki_2014_global_model.tif`: **51 mil**.
- **Licuefacción.** Población en celdas de MMI≥VI donde el modelo espera ≥ 0,10 de cobertura areal por licuefacción según `zhu_2017_general_model.tif`: **7.500**. USGS declara para este evento alerta **roja**, con 28 mil expuestas.

Las dos cifras se cuentan sobre las celdas del corte publicado (MMI≥VI). **No son las de USGS y no se pueden comparar de frente**: aquí se cuenta la población entera de toda celda por encima del umbral, y USGS pondera la población de cada celda por el valor de esa celda. Son dos preguntas distintas sobre el mismo ráster.

**Y el umbral se evalúa en un solo punto por celda: su centroide.** El píxel del ráster es más pequeño que la celda, así que ese punto decide si entra la población entera de la celda o no entra ninguna. No es una estadística areal, y el sesgo que introduce no está medido: puede quedarse corto o pasarse.

Fuente: producto *Ground Failure* de USGS (v1), dominio público.

## Referencia cruzada

PAGER (USGS) estima para este evento una alerta **amarilla**. CENTINELA no estima víctimas; la cifra se incluye solo como contraste.

Las dos cifras usan **la misma convención**: las clases de intensidad del USGS en números romanos (VI desde MMI 5,5, VII desde 6,5, VIII desde 7,5). Lo que puede separarlas es el insumo: este reporte declara en «Procedencia» qué versión del ShakeMap consumió, PAGER pudo correr sobre otra versión o sobre otro producto del mismo sismo, y los dos usan modelos de población distintos (GHS-POP aquí, LandScan en PAGER). El contraste clase a clase, hecho y comprobado para el sismo de San José del Palmar, está en `docs/PARA_INSTITUCIONES.md`.

## Incertidumbre y calidad

Discrepancia entre GHS-POP y WorldPop en las bandas MMI publicadas: **87,8 %**.

## Cambios frente a la versión anterior

- Recálculo con el mismo ShakeMap v1 (atlas) (cambió el cálculo o el activo de exposición, no USGS)
- Cambio de convención: las franjas son ahora las clases de intensidad del USGS (VI desde MMI 5,5, VII desde 6,5, VIII desde 7,5), no decimales literales (≥6,0 / ≥7,0 / ≥8,0). Las cifras cambian por la regla, no por los datos.
- Población en MMI≥VI: 3.400 → 500 mil
- Población en probabilidad alta de deslizamiento: 0 → 51 mil
- Población en cobertura areal alta por licuefacción: 31 → 7.500

## Descargas

- [CSV por municipio](adm2.csv)
- [Mapa PNG](mapa_general.png)

## Procedencia

- ShakeMap consumido: **v1** de `atlas`
- Ground Failure consumido: **v1** de `us`
- Manifiesto de exposición: [`ven-v0.5`](https://github.com/sforero77/CENTINELA/blob/main/data/manifests/VEN.yaml)
- Pipeline: `0.1.0` · Generado: 2026-11-21T16:31:19Z

## Advertencias

- Exposición estimada, no daño observado.
- Este sistema no es una alerta temprana ni una recomendación de evacuación.
- No reemplaza a los servicios geológicos ni a las unidades de gestión del riesgo.
- Fuentes, vintages y versiones consumidas: ver manifiesto enlazado.
