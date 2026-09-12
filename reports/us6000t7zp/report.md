# Exposición sísmica: M7,5 · 20 km al O de Catia La Mar, Venezuela

**Evento USGS:** `us6000t7zp` · **Origen:** 2026-06-24T22:05:04Z UTC · **Profundidad:** 10,0 km

> **Reconstrucción retrospectiva.** Este reporte se calculó después del evento, no en respuesta a él, y no cuenta para las métricas de latencia del sistema.
>
> La **población** corresponde a la época indicada en el manifiesto de exposición. Las **edificaciones, vías, sedes de salud y educativas son las actuales**: OpenStreetMap y Overture publican el estado presente, no el histórico. Léelas como "qué infraestructura de hoy caería en esa zona de intensidad", no como lo que había entonces.

## Exposición estimada

| Indicador | Estimado |
|---|---:|
| Población en MMI≥6 | 7,5 millones |
| Población en MMI≥7 | 2,6 millones |
| Población en MMI≥8 | 700 mil |
| Edificaciones en MMI≥7 | 560 mil |
| Sedes de salud en MMI≥7 | 770 |
| Sedes educativas en MMI≥7 | 1.034 |
| Vías primarias y secundarias en MMI≥7 | 1.300 km |
| Vías locales en MMI≥7 | 6.500 km |
| Superficie construida en MMI≥7 | 85,4 km² |

El satélite detecta **1,5 veces** más superficie construida de la que explicarían las 560 mil edificaciones registradas en MMI≥7. La diferencia suele ser asentamiento informal o zona rural dispersa sin mapear: **el conteo de edificaciones se queda corto ahí, y la superficie construida no**.

Las cifras de esta tabla van redondeadas a dos cifras significativas, que es la precisión que un modelo de exposición sostiene. Las exactas están en el CSV municipal y en `report.json`.

De la población en intensidad MMI≥7, alrededor de **320 mil** personas tienen 65 años o más.

## Municipios más expuestos, por población en MMI≥7

| # | Municipio | Código | MMI max | Población MMI≥7 |
|---:|---|---|---:|---:|
| 1 | Libertador | `VE0101` | 7,5 | 990 mil |
| 2 | Vargas | `VE2401` | 8,0 | 380 mil |
| 3 | Sucre | `VE1519` | 7,5 | 360 mil |
| 4 | Puerto Cabello | `VE0811` | 8,0 | 210 mil |
| 5 | Baruta | `VE1503` | 7,0 | 140 mil |
| 6 | San Felipe | `VE2211` | 8,0 | 140 mil |
| 7 | Veroes | `VE2214` | 8,5 | 100 mil |
| 8 | Chacao | `VE1507` | 7,5 | 88 mil |
| 9 | Juan José Mora | `VE0805` | 8,5 | 58 mil |
| 10 | Palmasola | `VE1116` | 7,5 | 30 mil |
| 11 | Independencia | `VE2205` | 7,0 | 30 mil |
| 12 | Silva | `VE1120` | 8,0 | 13 mil |
| 13 | Manuel Monge | `VE2208` | 7,5 | 12 mil |
| 14 | Ocumare de la Costa de Oro | `VE0518` | 8,0 | 11 mil |
| 15 | El Hatillo | `VE1509` | 7,0 | 3.600 |

## Deslizamiento y licuefacción

- **Deslizamiento.** Población en celdas de MMI≥6 donde el modelo espera ≥ 0,10 de probabilidad de deslizamiento según `jessee_2018_model.tif`: **29 mil**. USGS declara para este evento alerta **roja**, con 16 mil expuestas.
- **Licuefacción.** Población en celdas de MMI≥6 donde el modelo espera ≥ 0,10 de cobertura areal por licuefacción según `zhu_2017_general_model.tif`: **350 mil**. USGS declara para este evento alerta **roja**, con 170 mil expuestas.

Las dos cifras se cuentan sobre las celdas del corte publicado (MMI≥6). **No son las de USGS y no se pueden comparar de frente**: aquí se cuenta la población entera de toda celda por encima del umbral, y USGS pondera la población de cada celda por el valor de esa celda. Son dos preguntas distintas sobre el mismo ráster.

**Y el umbral se evalúa en un solo punto por celda: su centroide.** El píxel del ráster es más pequeño que la celda, así que ese punto decide si entra la población entera de la celda o no entra ninguna. No es una estadística areal, y el sesgo que introduce no está medido: puede quedarse corto o pasarse.

Fuente: producto *Ground Failure* de USGS (v13), dominio público.

## Referencia cruzada

PAGER (USGS) estima para este evento una alerta **roja**. CENTINELA no estima víctimas; la cifra se incluye solo como contraste.

Las dos cifras **no se tabulan igual** y no se pueden leer una contra otra: PAGER agrupa por MMI redondeado (su fila «7» es todo lo que cae entre 6,5 y 7,49) y CENTINELA usa bandas literales, donde MMI≥7 es MMI≥7. Puede además que no hablen del mismo ShakeMap: este reporte declara en «Procedencia» qué versión consumió, y PAGER pudo correr sobre otra versión o sobre otro producto del mismo sismo. El contraste banda a banda, hecho y comprobado para el sismo de San José del Palmar, está en `docs/PARA_INSTITUCIONES.md`.

## Incertidumbre y calidad

Discrepancia entre GHS-POP y WorldPop en las bandas MMI publicadas: **12,8 %**.

## Cambios frente a la versión anterior

- Ground Failure: v12 → v13
- Población en cobertura areal alta por licuefacción: 340 mil → 350 mil

## Descargas

- [CSV por municipio](adm2.csv)
- [Mapa PNG](mapa_general.png)

## Procedencia

- ShakeMap consumido: **v16**
- Ground Failure consumido: **v13**
- Manifiesto de exposición: [`ven-v0.3`](https://github.com/sforero77/CENTINELA/blob/main/data/manifests/VEN.yaml)
- Pipeline: `0.1.0` · Generado: 2026-09-12T09:33:28Z

## Advertencias

- Exposición estimada, no daño observado.
- Este sistema no es una alerta temprana ni una recomendación de evacuación.
- No reemplaza a los servicios geológicos ni a las unidades de gestión del riesgo.
- Fuentes, vintages y versiones consumidas: ver manifiesto enlazado.
