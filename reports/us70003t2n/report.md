# Exposición sísmica: M6,6 · 32 km al S de La Libertad, El Salvador

**Evento USGS:** `us70003t2n` · **Origen:** 2019-05-30T09:03:32Z UTC · **Profundidad:** 57,9 km

> **Reconstrucción retrospectiva.** Este reporte se calculó después del evento, no en respuesta a él, y no cuenta para las métricas de latencia del sistema.
>
> La **población** corresponde a la época indicada en el manifiesto de exposición. Las **edificaciones, vías, sedes de salud y educativas son las actuales**: OpenStreetMap y Overture publican el estado presente, no el histórico. Léelas como "qué infraestructura de hoy caería en esa zona de intensidad", no como lo que había entonces.

## Exposición estimada

| Indicador | Estimado |
|---|---:|
| Población en MMI≥VI | 1,4 millones |
| Población en MMI≥VII | el evento no llegó a esta banda |
| Población en MMI≥VIII | el evento no llegó a esta banda |
| Edificaciones en MMI≥VI | 540 mil |
| Sedes de salud en MMI≥VI | 499 |
| Sedes educativas en MMI≥VI | 604 |
| Vías primarias y secundarias en MMI≥VI | 820 km |
| Vías locales en MMI≥VI | 5.600 km |
| Superficie construida en MMI≥VI | 76,8 km² |

Las cifras de esta tabla van redondeadas a dos cifras significativas, que es la precisión que un modelo de exposición sostiene. Las exactas están en el CSV municipal y en `report.json`.

De la población en intensidad MMI≥VI, alrededor de **130 mil** personas tienen 65 años o más.

## Municipios más expuestos, por población en MMI≥VI

| # | Municipio | Código | MMI max | Población MMI≥VI |
|---:|---|---|---:|---:|
| 1 | San Salvador Centro | `SV10001` | 5,5 | 380 mil |
| 2 | Cuscatlán Sur | `SV04002` | 5,5 | 160 mil |
| 3 | La Paz Centro | `SV06001` | 6,0 | 140 mil |
| 4 | San Salvador Sur | `SV10005` | 6,0 | 140 mil |
| 5 | La Paz Oeste | `SV06003` | 6,0 | 130 mil |
| 6 | La Libertad Este | `SV05003` | 5,5 | 120 mil |
| 7 | La Paz Este | `SV06002` | 5,5 | 110 mil |
| 8 | San Salvador Este | `SV10002` | 5,5 | 99 mil |
| 9 | La Libertad Costa | `SV05002` | 6,0 | 88 mil |
| 10 | San Vicente Sur | `SV11002` | 5,5 | 22 mil |
| 11 | San Vicente Norte | `SV11001` | 5,5 | 20 mil |
| 12 | La Libertad Sur | `SV05006` | 5,5 | 20 mil |
| 13 | Cuscatlán Norte | `SV04001` | 5,5 | 6.600 |
| 14 | Usulután Oeste | `SV14003` | 5,5 | 1.800 |
| 15 | Cabañas Oeste | `SV02002` | 5,5 | 1.600 |

## Deslizamiento y licuefacción

- **Deslizamiento.** Población en celdas de MMI≥VI donde el modelo espera ≥ 0,10 de probabilidad de deslizamiento según `nowicki_2014_global_model.tif`: **3.000**.
- **Licuefacción.** Población en celdas de MMI≥VI donde el modelo espera ≥ 0,10 de cobertura areal por licuefacción según `zhu_2017_general_model.tif`: **54 mil**. USGS declara para este evento alerta **naranja**, con 17 mil expuestas.

Las dos cifras se cuentan sobre las celdas del corte publicado (MMI≥VI). **No son las de USGS y no se pueden comparar de frente**: aquí se cuenta la población entera de toda celda por encima del umbral, y USGS pondera la población de cada celda por el valor de esa celda. Son dos preguntas distintas sobre el mismo ráster.

**Y el umbral se evalúa en un solo punto por celda: su centroide.** El píxel del ráster es más pequeño que la celda, así que ese punto decide si entra la población entera de la celda o no entra ninguna. No es una estadística areal, y el sesgo que introduce no está medido: puede quedarse corto o pasarse.

Fuente: producto *Ground Failure* de USGS (v6), dominio público.

## Referencia cruzada

PAGER (USGS) estima para este evento una alerta **amarilla**. CENTINELA no estima víctimas; la cifra se incluye solo como contraste.

Las dos cifras usan **la misma convención**: las clases de intensidad del USGS en números romanos (VI desde MMI 5,5, VII desde 6,5, VIII desde 7,5). Lo que puede separarlas es el insumo: este reporte declara en «Procedencia» qué versión del ShakeMap consumió, PAGER pudo correr sobre otra versión o sobre otro producto del mismo sismo, y los dos usan modelos de población distintos (GHS-POP aquí, LandScan en PAGER). El contraste clase a clase, hecho y comprobado para el sismo de San José del Palmar, está en `docs/PARA_INSTITUCIONES.md`.

## Incertidumbre y calidad

Discrepancia entre GHS-POP y WorldPop en las bandas MMI publicadas: **6,1 %**.

## Cambios frente a la versión anterior

- Recálculo con el mismo ShakeMap v1 (atlas) (cambió el cálculo o el activo de exposición, no USGS)
- Cambio de convención: las franjas son ahora las clases de intensidad del USGS (VI desde MMI 5,5, VII desde 6,5, VIII desde 7,5), no decimales literales (≥6,0 / ≥7,0 / ≥8,0). Las cifras cambian por la regla, no por los datos.
- Población en MMI≥VI: 66 mil → 1,4 millones
- Población en probabilidad alta de deslizamiento: 1.100 → 3.000
- Población en cobertura areal alta por licuefacción: 21 mil → 54 mil

## Descargas

- [CSV por municipio](adm2.csv)
- [Mapa PNG](mapa_general.png)

## Procedencia

- ShakeMap consumido: **v1** de `atlas`
- Ground Failure consumido: **v6** de `us`
- Manifiesto de exposición: [`slv-v0.5`](https://github.com/sforero77/CENTINELA/blob/main/data/manifests/SLV.yaml)
- Pipeline: `0.1.0` · Generado: 2026-11-21T16:30:26Z

## Advertencias

- Exposición estimada, no daño observado.
- Este sistema no es una alerta temprana ni una recomendación de evacuación.
- No reemplaza a los servicios geológicos ni a las unidades de gestión del riesgo.
- Fuentes, vintages y versiones consumidas: ver manifiesto enlazado.
