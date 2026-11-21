# Exposición sísmica: M6,9 · 2 km al SSO de San Pablo, Guatemala

**Evento USGS:** `us20009mbt` · **Origen:** 2017-06-14T07:29:04Z UTC · **Profundidad:** 93,0 km

> **Reconstrucción retrospectiva.** Este reporte se calculó después del evento, no en respuesta a él, y no cuenta para las métricas de latencia del sistema.
>
> La **población** corresponde a la época indicada en el manifiesto de exposición. Las **edificaciones, vías, sedes de salud y educativas son las actuales**: OpenStreetMap y Overture publican el estado presente, no el histórico. Léelas como "qué infraestructura de hoy caería en esa zona de intensidad", no como lo que había entonces.

## Exposición estimada

| Indicador | Estimado |
|---|---:|
| Población en MMI≥VI | 3,7 millones |
| Población en MMI≥VII | el evento no llegó a esta banda |
| Población en MMI≥VIII | el evento no llegó a esta banda |
| Edificaciones en MMI≥VI | 1,9 millones |
| Sedes de salud en MMI≥VI | 377 |
| Sedes educativas en MMI≥VI | 451 |
| Vías primarias y secundarias en MMI≥VI | 1.400 km |
| Vías locales en MMI≥VI | 24 mil km |
| Superficie construida en MMI≥VI | 243,4 km² |

Las cifras de esta tabla van redondeadas a dos cifras significativas, que es la precisión que un modelo de exposición sostiene. Las exactas están en el CSV municipal y en `report.json`.

De la población en intensidad MMI≥VI, alrededor de **190 mil** personas tienen 65 años o más.

## Municipios más expuestos, por población en MMI≥VI

| # | Municipio | Código | MMI max | Población MMI≥VI |
|---:|---|---|---:|---:|
| 1 | Quetzaltenango | `GT0901` | 6,0 | 210 mil |
| 2 | Momostenango | `GT0805` | 5,5 | 170 mil |
| 3 | Coatepeque | `GT0920` | 6,0 | 170 mil |
| 4 | Malacatán | `GT1215` | 6,0 | 130 mil |
| 5 | Mazatenango | `GT1001` | 5,5 | 120 mil |
| 6 | Retalhuleu | `GT1101` | 6,0 | 110 mil |
| 7 | Tacaná | `GT1207` | 5,5 | 90 mil |
| 8 | San Francisco el Alto | `GT0803` | 6,0 | 84 mil |
| 9 | San Marcos | `GT1201` | 6,0 | 73 mil |
| 10 | Comitancillo | `GT1204` | 6,0 | 73 mil |
| 11 | San Pedro Sacatepéquez | `GT1202` | 6,0 | 73 mil |
| 12 | Tajumulco | `GT1209` | 6,0 | 71 mil |
| 13 | San Pablo | `GT1219` | 6,0 | 68 mil |
| 14 | Concepción Tutuapa | `GT1206` | 6,0 | 67 mil |
| 15 | Totonicapán | `GT0801` | 5,5 | 61 mil |

## Deslizamiento y licuefacción

USGS no ha publicado el producto *Ground Failure* para este evento. La sección se omite; el reporte se re-emite automáticamente si aparece.

## Referencia cruzada

PAGER (USGS) estima para este evento una alerta **amarilla**. CENTINELA no estima víctimas; la cifra se incluye solo como contraste.

Las dos cifras usan **la misma convención**: las clases de intensidad del USGS en números romanos (VI desde MMI 5,5, VII desde 6,5, VIII desde 7,5). Lo que puede separarlas es el insumo: este reporte declara en «Procedencia» qué versión del ShakeMap consumió, PAGER pudo correr sobre otra versión o sobre otro producto del mismo sismo, y los dos usan modelos de población distintos (GHS-POP aquí, LandScan en PAGER). El contraste clase a clase, hecho y comprobado para el sismo de San José del Palmar, está en `docs/PARA_INSTITUCIONES.md`.

## Incertidumbre y calidad

Discrepancia entre GHS-POP y WorldPop en las bandas MMI publicadas: **1,8 %**.

## Cambios frente a la versión anterior

- Recálculo con el mismo ShakeMap v1 (atlas) (cambió el cálculo o el activo de exposición, no USGS)
- Cambio de convención: las franjas son ahora las clases de intensidad del USGS (VI desde MMI 5,5, VII desde 6,5, VIII desde 7,5), no decimales literales (≥6,0 / ≥7,0 / ≥8,0). Las cifras cambian por la regla, no por los datos.
- Población en MMI≥VI: 1,8 millones → 3,7 millones

## Descargas

- [CSV por municipio](adm2.csv)
- [Mapa PNG](mapa_general.png)

## Procedencia

- ShakeMap consumido: **v1** de `atlas`
- Ground Failure consumido: **ninguno** (no publicado aún)
- Manifiesto de exposición: [`gtm-v0.5`](https://github.com/sforero77/CENTINELA/blob/main/data/manifests/GTM.yaml)
- Pipeline: `0.1.0` · Generado: 2026-11-21T16:31:49Z

## Advertencias

- Exposición estimada, no daño observado.
- Este sistema no es una alerta temprana ni una recomendación de evacuación.
- No reemplaza a los servicios geológicos ni a las unidades de gestión del riesgo.
- Fuentes, vintages y versiones consumidas: ver manifiesto enlazado.
