# Exposición sísmica: M7,8 · 27 km al SSE de Muisne, Ecuador

**Evento USGS:** `us20005j32` · **Origen:** 2016-04-16T23:58:36Z UTC · **Profundidad:** 20,6 km

> **Reconstrucción retrospectiva.** Este reporte se calculó después del evento, no en respuesta a él, y no cuenta para las métricas de latencia del sistema.
>
> La **población** corresponde a la época indicada en el manifiesto de exposición. Las **edificaciones, vías, sedes de salud y educativas son las actuales**: OpenStreetMap y Overture publican el estado presente, no el histórico. Léelas como "qué infraestructura de hoy caería en esa zona de intensidad", no como lo que había entonces.

## Exposición estimada

| Indicador | Estimado |
|---|---:|
| Población en MMI≥6 | 4,3 millones |
| Población en MMI≥7 | 2,3 millones |
| Población en MMI≥8 | 110 mil |
| Edificaciones en MMI≥7 | 1 millón |
| Sedes de salud en MMI≥7 | 552 |
| Sedes educativas en MMI≥7 | 2.442 |
| Vías primarias y secundarias en MMI≥7 | 2.600 km |
| Vías locales en MMI≥7 | 34 mil km |
| Superficie construida en MMI≥7 | 131,0 km² |

Las cifras de esta tabla van redondeadas a dos cifras significativas, que es la precisión que un modelo de exposición sostiene. Las exactas están en el CSV municipal y en `report.json`.

De la población en intensidad MMI≥7, alrededor de **180 mil** personas tienen 65 años o más.

## Municipios más expuestos, por población en MMI≥7

| # | Municipio | Código | MMI max | Población MMI≥7 |
|---:|---|---|---:|---:|
| 1 | Portoviejo | `EC1301` | 7,5 | 330 mil |
| 2 | Esmeraldas | `EC0801` | 7,5 | 300 mil |
| 3 | Manta | `EC1308` | 7,0 | 270 mil |
| 4 | Quinindé | `EC0804` | 7,5 | 160 mil |
| 5 | Chone | `EC1303` | 7,5 | 150 mil |
| 6 | El Carmen | `EC1304` | 7,5 | 130 mil |
| 7 | El Empalme | `EC0908` | 7,0 | 87 mil |
| 8 | Montecristi | `EC1309` | 7,0 | 78 mil |
| 9 | Sucre | `EC1314` | 8,0 | 68 mil |
| 10 | Pedernales | `EC1317` | 8,0 | 66 mil |
| 11 | Santo Domingo | `EC2301` | 7,0 | 59 mil |
| 12 | Atacames | `EC0806` | 8,0 | 55 mil |
| 13 | La Concordia | `EC2302` | 7,5 | 54 mil |
| 14 | Bolívar | `EC1302` | 7,5 | 48 mil |
| 15 | Tosagua | `EC1315` | 7,5 | 46 mil |

## Deslizamiento y licuefacción

- **Deslizamiento.** Población en celdas de MMI≥6 donde el modelo espera ≥ 0,10 de probabilidad de deslizamiento según `nowicki_2014_global_model.tif`: **210 mil**. USGS declara para este evento alerta **naranja**, con 2.200 expuestas.
- **Licuefacción.** Población en celdas de MMI≥6 donde el modelo espera ≥ 0,10 de cobertura areal por licuefacción según `zhu_2017_general_model.tif`: **1,2 millones**. USGS declara para este evento alerta **roja**, con 260 mil expuestas.

Las dos cifras se cuentan sobre las celdas del corte publicado (MMI≥6). **No son las de USGS y no se pueden comparar de frente**: aquí se cuenta la población entera de toda celda por encima del umbral, y USGS pondera la población de cada celda por el valor de esa celda. Son dos preguntas distintas sobre el mismo ráster.

Fuente: producto *Ground Failure* de USGS (v1), dominio público.

## Referencia cruzada

PAGER (USGS) estima para este evento una alerta **naranja**. CENTINELA no estima víctimas; la cifra se incluye solo como contraste.

Las dos cifras **no se tabulan igual** y no se pueden leer una contra otra: PAGER agrupa por MMI redondeado (su fila «7» es todo lo que cae entre 6,5 y 7,49) y CENTINELA usa bandas literales, donde MMI≥7 es MMI≥7. Puede además que no hablen del mismo ShakeMap: este reporte declara en «Procedencia» qué versión consumió, y PAGER pudo correr sobre otra versión o sobre otro producto del mismo sismo. El contraste banda a banda, hecho y comprobado para el sismo de San José del Palmar, está en `docs/PARA_INSTITUCIONES.md`.

## Incertidumbre y calidad

Discrepancia entre GHS-POP y WorldPop en las bandas MMI publicadas: **3,1 %**.

## Cambios frente a la versión anterior

- Población de 65 años o más en MMI≥7: 170 mil → 180 mil
- Sedes de salud en MMI≥7: 530 → 550

## Descargas

- [CSV por municipio](adm2.csv)
- [Mapa PNG](mapa_general.png)

## Procedencia

- ShakeMap consumido: **v1**
- Ground Failure consumido: **v1**
- Manifiesto de exposición: [`ecu-v0.3`](https://github.com/sforero77/CENTINELA/blob/main/data/manifests/ECU.yaml)
- Pipeline: `0.1.0` · Generado: 2026-09-07T16:52:12Z

## Advertencias

- Exposición estimada, no daño observado.
- Este sistema no es una alerta temprana ni una recomendación de evacuación.
- No reemplaza a los servicios geológicos ni a las unidades de gestión del riesgo.
- Fuentes, vintages y versiones consumidas: ver manifiesto enlazado.
