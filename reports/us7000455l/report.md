# Exposición sísmica: M6,2 · 4 km al SE de Aserrío de Gariché, Panamá

**Evento USGS:** `us7000455l` · **Origen:** 2019-06-26T05:23:51Z UTC · **Profundidad:** 32,6 km

> **Reconstrucción retrospectiva.** Este reporte se calculó después del evento, no en respuesta a él, y no cuenta para las métricas de latencia del sistema.
>
> La **población** corresponde a la época indicada en el manifiesto de exposición. Las **edificaciones, vías, sedes de salud y educativas son las actuales**: OpenStreetMap y Overture publican el estado presente, no el histórico. Léelas como "qué infraestructura de hoy caería en esa zona de intensidad", no como lo que había entonces.

## Exposición estimada

| Indicador | Estimado |
|---|---:|
| Población en MMI≥VI | 190 mil |
| Población en MMI≥VII | el evento no llegó a esta banda |
| Población en MMI≥VIII | el evento no llegó a esta banda |
| Edificaciones en MMI≥VI | 120 mil |
| Sedes de salud en MMI≥VI | 39 |
| Sedes educativas en MMI≥VI | 124 |
| Vías primarias y secundarias en MMI≥VI | 400 km |
| Vías locales en MMI≥VI | 2.700 km |
| Superficie construida en MMI≥VI | 22,6 km² |

El satélite detecta **1,8 veces** más superficie construida de la que explicarían las 120 mil edificaciones registradas en MMI≥VI. La diferencia suele ser asentamiento informal o zona rural dispersa sin mapear: **el conteo de edificaciones se queda corto ahí, y la superficie construida no**.

Las cifras de esta tabla van redondeadas a dos cifras significativas, que es la precisión que un modelo de exposición sostiene. Las exactas están en el CSV municipal y en `report.json`.

De la población en intensidad MMI≥VI, alrededor de **22 mil** personas tienen 65 años o más.

## Municipios más expuestos, por población en MMI≥VI

| # | Municipio | Código | MMI max | Población MMI≥VI |
|---:|---|---|---:|---:|
| 1 | Bugaba | `PA0205` | 6,0 | 66 mil |
| 2 | Barú | `PA0202` | 6,0 | 63 mil |
| 3 | David | `PA0206` | 5,5 | 26 mil |
| 4 | Alanje | `PA0201` | 6,0 | 19 mil |
| 5 | Boquerón | `PA0203` | 5,5 | 15 mil |
| 6 | Renacimiento | `PA0210` | 6,0 | 5.600 |

## Deslizamiento y licuefacción

- **Deslizamiento.** Población en celdas de MMI≥VI donde el modelo espera ≥ 0,10 de probabilidad de deslizamiento según `nowicki_2014_global_model.tif`: **14**.
- **Licuefacción.** Población en celdas de MMI≥VI donde el modelo espera ≥ 0,10 de cobertura areal por licuefacción según `zhu_2017_general_model.tif`: **57 mil**. USGS declara para este evento alerta **naranja**, con 23 mil expuestas.

Las dos cifras se cuentan sobre las celdas del corte publicado (MMI≥VI). **No son las de USGS y no se pueden comparar de frente**: aquí se cuenta la población entera de toda celda por encima del umbral, y USGS pondera la población de cada celda por el valor de esa celda. Son dos preguntas distintas sobre el mismo ráster.

**Y el umbral se evalúa en un solo punto por celda: su centroide.** El píxel del ráster es más pequeño que la celda, así que ese punto decide si entra la población entera de la celda o no entra ninguna. No es una estadística areal, y el sesgo que introduce no está medido: puede quedarse corto o pasarse.

Fuente: producto *Ground Failure* de USGS (v8), dominio público.

## Referencia cruzada

PAGER (USGS) estima para este evento una alerta **amarilla**. CENTINELA no estima víctimas; la cifra se incluye solo como contraste.

Las dos cifras usan **la misma convención**: las clases de intensidad del USGS en números romanos (VI desde MMI 5,5, VII desde 6,5, VIII desde 7,5). Lo que puede separarlas es el insumo: este reporte declara en «Procedencia» qué versión del ShakeMap consumió, PAGER pudo correr sobre otra versión o sobre otro producto del mismo sismo, y los dos usan modelos de población distintos (GHS-POP aquí, LandScan en PAGER). El contraste clase a clase, hecho y comprobado para el sismo de San José del Palmar, está en `docs/PARA_INSTITUCIONES.md`.

## Incertidumbre y calidad

Discrepancia entre GHS-POP y WorldPop en las bandas MMI publicadas: **10,0 %**.

## Cambios frente a la versión anterior

- Recálculo con el mismo ShakeMap v1 (atlas) (cambió el cálculo o el activo de exposición, no USGS)
- Cambio de convención: las franjas son ahora las clases de intensidad del USGS (VI desde MMI 5,5, VII desde 6,5, VIII desde 7,5), no decimales literales (≥6,0 / ≥7,0 / ≥8,0). Las cifras cambian por la regla, no por los datos.
- Población en MMI≥VI: 55 mil → 190 mil
- Población en probabilidad alta de deslizamiento: 0 → 14
- Población en cobertura areal alta por licuefacción: 20 mil → 57 mil

## Descargas

- [CSV por municipio](adm2.csv)
- [Mapa PNG](mapa_general.png)

## Procedencia

- ShakeMap consumido: **v1** de `atlas`
- Ground Failure consumido: **v8** de `us`
- Manifiesto de exposición: [`pan-v0.5`](https://github.com/sforero77/CENTINELA/blob/main/data/manifests/PAN.yaml)
- Pipeline: `0.1.0` · Generado: 2026-11-21T16:30:20Z

## Advertencias

- Exposición estimada, no daño observado.
- Este sistema no es una alerta temprana ni una recomendación de evacuación.
- No reemplaza a los servicios geológicos ni a las unidades de gestión del riesgo.
- Fuentes, vintages y versiones consumidas: ver manifiesto enlazado.
