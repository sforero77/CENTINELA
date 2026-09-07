# Exposición sísmica: M7,5 · 20 km al O de Catia La Mar, Venezuela

**Evento USGS:** `us6000t7zp` · **Origen:** 2026-06-24T22:05:04Z UTC · **Profundidad:** 10,0 km

> **Reconstrucción retrospectiva.** Este reporte se calculó después del evento, no en respuesta a él, y no cuenta para las métricas de latencia del sistema.
>
> La **población** corresponde a la época indicada en el manifiesto de exposición. Las **edificaciones, vías, sedes de salud y educativas son las actuales**: OpenStreetMap y Overture publican el estado presente, no el histórico. Léelas como "qué infraestructura de hoy caería en esa zona de intensidad", no como lo que había entonces.

## Exposición estimada

| Indicador | Estimado |
|---|---:|
| Población en MMI≥6 | 9,2 millones |
| Población en MMI≥7 | 2,3 millones |
| Población en MMI≥8 | 740 mil |
| Edificaciones en MMI≥7 | 500 mil |
| Sedes de salud en MMI≥7 | 577 |
| Sedes educativas en MMI≥7 | 815 |
| Vías primarias y secundarias en MMI≥7 | 1.200 km |
| Vías locales en MMI≥7 | 5.800 km |
| Superficie construida en MMI≥7 | 74,8 km² |

Las cifras de esta tabla van redondeadas a dos cifras significativas, que es la precisión que un modelo de exposición sostiene. Las exactas están en el CSV municipal y en `report.json`.

De la población en intensidad MMI≥7, alrededor de **270 mil** personas tienen 65 años o más.

## Municipios más expuestos, por población en MMI≥7

| # | Municipio | Código | MMI max | Población MMI≥7 |
|---:|---|---|---:|---:|
| 1 | Libertador | `VE0101` | 7,5 | 650 mil |
| 2 | Vargas | `VE2401` | 8,0 | 380 mil |
| 3 | Sucre | `VE1519` | 7,5 | 350 mil |
| 4 | Puerto Cabello | `VE0811` | 8,0 | 210 mil |
| 5 | Plaza | `VE1517` | 7,0 | 170 mil |
| 6 | San Felipe | `VE2211` | 8,0 | 140 mil |
| 7 | Veroes | `VE2214` | 8,5 | 100 mil |
| 8 | Chacao | `VE1507` | 7,5 | 83 mil |
| 9 | Juan José Mora | `VE0805` | 8,5 | 58 mil |
| 10 | Palmasola | `VE1116` | 7,5 | 31 mil |
| 11 | Independencia | `VE2205` | 7,0 | 30 mil |
| 12 | Cocorote | `VE2204` | 7,0 | 25 mil |
| 13 | Manuel Monge | `VE2208` | 7,5 | 13 mil |
| 14 | Ocumare de la Costa de Oro | `VE0518` | 8,0 | 11 mil |
| 15 | Silva | `VE1120` | 8,0 | 10 mil |

## Deslizamiento y licuefacción

- **Deslizamiento.** Población en celdas de MMI≥6 donde el modelo espera ≥ 0,10 de probabilidad de deslizamiento según `jessee_2018_model.tif`: **29 mil**. USGS declara para este evento alerta **roja**, con 13 mil expuestas.
- **Licuefacción.** Población en celdas de MMI≥6 donde el modelo espera ≥ 0,10 de cobertura areal por licuefacción según `zhu_2017_general_model.tif`: **560 mil**. USGS declara para este evento alerta **roja**, con 190 mil expuestas.

Las dos cifras se cuentan sobre las celdas del corte publicado (MMI≥6). **No son las de USGS y no se pueden comparar de frente**: aquí se cuenta la población entera de toda celda por encima del umbral, y USGS pondera la población de cada celda por el valor de esa celda. Son dos preguntas distintas sobre el mismo ráster.

**Y el umbral se evalúa en un solo punto por celda: su centroide.** El píxel del ráster es más pequeño que la celda, así que ese punto decide si entra la población entera de la celda o no entra ninguna. No es una estadística areal, y el sesgo que introduce no está medido: puede quedarse corto o pasarse.

Fuente: producto *Ground Failure* de USGS (v12), dominio público.

## Referencia cruzada

PAGER (USGS) estima para este evento una alerta **roja**. CENTINELA no estima víctimas; la cifra se incluye solo como contraste.

Las dos cifras **no se tabulan igual** y no se pueden leer una contra otra: PAGER agrupa por MMI redondeado (su fila «7» es todo lo que cae entre 6,5 y 7,49) y CENTINELA usa bandas literales, donde MMI≥7 es MMI≥7. Puede además que no hablen del mismo ShakeMap: este reporte declara en «Procedencia» qué versión consumió, y PAGER pudo correr sobre otra versión o sobre otro producto del mismo sismo. El contraste banda a banda, hecho y comprobado para el sismo de San José del Palmar, está en `docs/PARA_INSTITUCIONES.md`.

## Incertidumbre y calidad

Discrepancia entre GHS-POP y WorldPop en las bandas MMI publicadas: **11,8 %**.

## Cambios frente a la versión anterior

- Población de 65 años o más en MMI≥7: 230 mil → 270 mil
- Sedes educativas en MMI≥7: 810 → 820

## Descargas

- [CSV por municipio](adm2.csv)
- [Mapa PNG](mapa_general.png)

## Procedencia

- ShakeMap consumido: **v15**
- Ground Failure consumido: **v12**
- Manifiesto de exposición: [`ven-v0.3`](https://github.com/sforero77/CENTINELA/blob/main/data/manifests/VEN.yaml)
- Pipeline: `0.1.0` · Generado: 2026-09-07T16:30:41Z

## Advertencias

- Exposición estimada, no daño observado.
- Este sistema no es una alerta temprana ni una recomendación de evacuación.
- No reemplaza a los servicios geológicos ni a las unidades de gestión del riesgo.
- Fuentes, vintages y versiones consumidas: ver manifiesto enlazado.
