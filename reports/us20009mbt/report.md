# Exposición sísmica — M6,9 · 2 km al SSO de San Pablo, Guatemala

**Evento USGS:** `us20009mbt` · **Origen:** 2017-06-14T07:29:04Z UTC · **Profundidad:** 93,0 km

> **Reconstrucción retrospectiva.** Este reporte se calculó después del evento, no en respuesta a él, y no cuenta para las métricas de latencia del sistema.
>
> La **población** corresponde a la época indicada en el manifiesto de exposición. Las **edificaciones, vías, sedes de salud y educativas son las actuales**: OpenStreetMap y Overture publican el estado presente, no el histórico. Léelas como "qué infraestructura de hoy caería en esa zona de intensidad", no como lo que había entonces.

## Exposición estimada

| Indicador | Estimado |
|---|---:|
| Población en MMI≥6 | 1,8 millones |
| Población en MMI≥7 | 0 |
| Población en MMI≥8 | 0 |
| Edificaciones en MMI≥7 | 0 |
| Sedes de salud en MMI≥7 | 0 |
| Sedes educativas en MMI≥7 | 0 |
| Kilómetros de vía en MMI≥7 | 0 km |

Las cifras de esta tabla van redondeadas a dos cifras significativas, que es la precisión que un modelo de exposición sostiene. Las exactas están en el CSV municipal y en `report.json`.

## Municipios más expuestos, por población en MMI≥6

| # | Municipio | Código | MMI max | Población MMI≥6 |
|---:|---|---|---:|---:|
| 1 | Quetzaltenango | `GT0901` | 6,0 | 190 mil |
| 2 | Coatepeque | `GT0920` | 6,0 | 170 mil |
| 3 | Malacatán | `GT1215` | 6,0 | 130 mil |
| 4 | San Pedro Sacatepéquez | `GT1202` | 6,0 | 70 mil |
| 5 | San Marcos | `GT1201` | 6,0 | 63 mil |
| 6 | San Pablo | `GT1219` | 6,0 | 62 mil |
| 7 | Comitancillo | `GT1204` | 6,0 | 57 mil |
| 8 | Ostuncalco | `GT0909` | 6,0 | 55 mil |
| 9 | El Asintal | `GT1109` | 6,0 | 51 mil |
| 10 | Ayutla | `GT1217` | 6,0 | 50 mil |
| 11 | Génova | `GT0921` | 6,0 | 48 mil |
| 12 | Colomba | `GT0917` | 6,0 | 48 mil |
| 13 | Catarina | `GT1216` | 6,0 | 47 mil |
| 14 | El Tumbador | `GT1213` | 6,0 | 47 mil |
| 15 | La Blanca | `GT1230` | 6,0 | 41 mil |

## Deslizamiento y licuefacción

USGS no ha publicado el producto *Ground Failure* para este evento. La sección se omite; el reporte se re-emite automáticamente si aparece.

## Referencia cruzada

PAGER (USGS) estima para este evento una alerta **amarilla**. CENTINELA no estima víctimas; la cifra se incluye solo como contraste.

Las dos cifras **no se tabulan igual** y no se pueden leer una contra otra: PAGER agrupa por MMI redondeado —su fila «7» es todo lo que cae entre 6,5 y 7,49— y CENTINELA usa bandas literales, donde MMI≥7 es MMI≥7. Puede además que no hablen del mismo ShakeMap: este reporte declara en «Procedencia» qué versión consumió, y PAGER pudo correr sobre otra versión o sobre otro producto del mismo sismo. El contraste banda a banda, hecho y comprobado para el sismo de San José del Palmar, está en `docs/PARA_INSTITUCIONES.md`.

## Incertidumbre y calidad

Discrepancia entre GHS-POP y WorldPop en las bandas MMI publicadas: **3,1 %**.

## Descargas

- [CSV por municipio](adm2.csv)
- [Mapa PNG](mapa_general.png)

## Procedencia

- ShakeMap consumido: **v1**
- Ground Failure consumido: **v0**
- Manifiesto de exposición: `gtm-v0.2`
- Pipeline: `0.1.0` · Generado: 2026-09-02T02:42:11Z

## Advertencias

- Exposición estimada, no daño observado.
- Este sistema no es una alerta temprana ni una recomendación de evacuación.
- No reemplaza a los servicios geológicos ni a las unidades de gestión del riesgo.
- Fuentes, vintages y versiones consumidas: ver manifiesto enlazado.
