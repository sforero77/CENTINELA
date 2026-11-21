# Exposición sísmica: M6,4 · 26 km al SO de Pocito, Argentina

**Evento USGS:** `us7000d18q` · **Origen:** 2021-01-19T02:46:22Z UTC · **Profundidad:** 20,8 km

> **Reconstrucción retrospectiva.** Este reporte se calculó después del evento, no en respuesta a él, y no cuenta para las métricas de latencia del sistema.
>
> La **población** corresponde a la época indicada en el manifiesto de exposición. Las **edificaciones, vías, sedes de salud y educativas son las actuales**: OpenStreetMap y Overture publican el estado presente, no el histórico. Léelas como "qué infraestructura de hoy caería en esa zona de intensidad", no como lo que había entonces.

## Exposición estimada

| Indicador | Estimado |
|---|---:|
| Población en MMI≥VI | 720 mil |
| Población en MMI≥VII | 330 |
| Población en MMI≥VIII | el evento no llegó a esta banda |
| Edificaciones en MMI≥VI | 500 mil |
| Sedes de salud en MMI≥VI | 449 |
| Sedes educativas en MMI≥VI | 1.945 |
| Vías primarias y secundarias en MMI≥VI | 940 km |
| Vías locales en MMI≥VI | 6.500 km |
| Superficie construida en MMI≥VI | 59,5 km² |

Las cifras de esta tabla van redondeadas a dos cifras significativas, que es la precisión que un modelo de exposición sostiene. Las exactas están en el CSV municipal y en `report.json`.

De la población en intensidad MMI≥VI, alrededor de **79 mil** personas tienen 65 años o más.

## Municipios más expuestos, por población en MMI≥VI

| # | Municipio | Código | MMI max | Población MMI≥VI |
|---:|---|---|---:|---:|
| 1 | Rawson | `AR070077` | 6,0 | 120 mil |
| 2 | Capital | `AR070028` | 6,0 | 120 mil |
| 3 | Chimbas | `AR070042` | 6,0 | 100 mil |
| 4 | Rivadavia | `AR070084` | 6,0 | 95 mil |
| 5 | Pocito | `AR070070` | 6,0 | 65 mil |
| 6 | Santa Lucía | `AR070098` | 6,0 | 53 mil |
| 7 | Caucete | `AR070035` | 5,5 | 43 mil |
| 8 | Albardón | `AR070007` | 6,0 | 28 mil |
| 9 | Sarmiento | `AR070105` | 6,5 | 26 mil |
| 10 | 25 de Mayo | `AR070126` | 6,0 | 19 mil |
| 11 | San Martín | `AR070091` | 5,5 | 13 mil |
| 12 | 9 de Julio | `AR070063` | 6,0 | 11 mil |
| 13 | Angaco | `AR070014` | 5,5 | 9.200 |
| 14 | Zonda | `AR070133` | 6,5 | 5.700 |
| 15 | Ullum | `AR070112` | 6,0 | 5.000 |

## Deslizamiento y licuefacción

- **Deslizamiento.** Población en celdas de MMI≥VI donde el modelo espera ≥ 0,10 de probabilidad de deslizamiento según `jessee_2018_model.tif`: **0**. USGS declara para este evento alerta **amarilla**, con 1 expuestas. El cero de arriba no dice que no haya exposición: dice que ninguna celda llega al umbral.
- **Licuefacción.** Población en celdas de MMI≥VI donde el modelo espera ≥ 0,10 de cobertura areal por licuefacción según `zhu_2017_general_model.tif`: **0**. USGS declara para este evento alerta **amarilla**, con 580 expuestas. El cero de arriba no dice que no haya exposición: dice que ninguna celda llega al umbral.

Las dos cifras se cuentan sobre las celdas del corte publicado (MMI≥VI). **No son las de USGS y no se pueden comparar de frente**: aquí se cuenta la población entera de toda celda por encima del umbral, y USGS pondera la población de cada celda por el valor de esa celda. Son dos preguntas distintas sobre el mismo ráster.

**Y el umbral se evalúa en un solo punto por celda: su centroide.** El píxel del ráster es más pequeño que la celda, así que ese punto decide si entra la población entera de la celda o no entra ninguna. No es una estadística areal, y el sesgo que introduce no está medido: puede quedarse corto o pasarse.

Fuente: producto *Ground Failure* de USGS (v4), dominio público.

## Referencia cruzada

PAGER (USGS) estima para este evento una alerta **amarilla**. CENTINELA no estima víctimas; la cifra se incluye solo como contraste.

Las dos cifras usan **la misma convención**: las clases de intensidad del USGS en números romanos (VI desde MMI 5,5, VII desde 6,5, VIII desde 7,5). Lo que puede separarlas es el insumo: este reporte declara en «Procedencia» qué versión del ShakeMap consumió, PAGER pudo correr sobre otra versión o sobre otro producto del mismo sismo, y los dos usan modelos de población distintos (GHS-POP aquí, LandScan en PAGER). El contraste clase a clase, hecho y comprobado para el sismo de San José del Palmar, está en `docs/PARA_INSTITUCIONES.md`.

## Incertidumbre y calidad

Discrepancia entre GHS-POP y WorldPop en las bandas MMI publicadas: **4,0 %**.

## Cambios frente a la versión anterior

- Recálculo con el mismo ShakeMap v8 (us) (cambió el cálculo o el activo de exposición, no USGS)
- Cambio de convención: las franjas son ahora las clases de intensidad del USGS (VI desde MMI 5,5, VII desde 6,5, VIII desde 7,5), no decimales literales (≥6,0 / ≥7,0 / ≥8,0). Las cifras cambian por la regla, no por los datos.
- Población en MMI≥VI: 580 mil → 720 mil
- Población en MMI≥VII: 0 → 330
- Población de 65 años o más en MMI≥VII: 0 → 28
- Edificaciones en MMI≥VII: 0 → 67

## Descargas

- [CSV por municipio](adm2.csv)
- [Mapa PNG](mapa_general.png)

## Procedencia

- ShakeMap consumido: **v8** de `us`
- Ground Failure consumido: **v4** de `us`
- Manifiesto de exposición: [`arg-v0.5`](https://github.com/sforero77/CENTINELA/blob/main/data/manifests/ARG.yaml)
- Pipeline: `0.1.0` · Generado: 2026-11-21T16:30:15Z

## Advertencias

- Exposición estimada, no daño observado.
- Este sistema no es una alerta temprana ni una recomendación de evacuación.
- No reemplaza a los servicios geológicos ni a las unidades de gestión del riesgo.
- Fuentes, vintages y versiones consumidas: ver manifiesto enlazado.
