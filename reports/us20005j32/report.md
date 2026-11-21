# Exposición sísmica: M7,8 · 27 km al SSE de Muisne, Ecuador

**Evento USGS:** `us20005j32` · **Origen:** 2016-04-16T23:58:36Z UTC · **Profundidad:** 20,6 km

> **Reconstrucción retrospectiva.** Este reporte se calculó después del evento, no en respuesta a él, y no cuenta para las métricas de latencia del sistema.
>
> La **población** corresponde a la época indicada en el manifiesto de exposición. Las **edificaciones, vías, sedes de salud y educativas son las actuales**: OpenStreetMap y Overture publican el estado presente, no el histórico. Léelas como "qué infraestructura de hoy caería en esa zona de intensidad", no como lo que había entonces.

## Exposición estimada

| Indicador | Estimado |
|---|---:|
| Población en MMI≥VI | 8,6 millones |
| Población en MMI≥VII | 3,4 millones |
| Población en MMI≥VIII | 1 millón |
| Edificaciones en MMI≥VII | 1,4 millones |
| Sedes de salud en MMI≥VII | 849 |
| Sedes educativas en MMI≥VII | 3.323 |
| Vías primarias y secundarias en MMI≥VII | 4.100 km |
| Vías locales en MMI≥VII | 44 mil km |
| Superficie construida en MMI≥VII | 185,5 km² |

Las cifras de esta tabla van redondeadas a dos cifras significativas, que es la precisión que un modelo de exposición sostiene. Las exactas están en el CSV municipal y en `report.json`.

De la población en intensidad MMI≥VII, alrededor de **260 mil** personas tienen 65 años o más.

## Municipios más expuestos, por población en MMI≥VII

| # | Municipio | Código | MMI max | Población MMI≥VII |
|---:|---|---|---:|---:|
| 1 | Santo Domingo | `EC2301` | 7,0 | 480 mil |
| 2 | Portoviejo | `EC1301` | 7,5 | 330 mil |
| 3 | Esmeraldas | `EC0801` | 7,5 | 300 mil |
| 4 | Manta | `EC1308` | 7,0 | 270 mil |
| 5 | Quevedo | `EC1205` | 7,0 | 220 mil |
| 6 | Quinindé | `EC0804` | 7,5 | 160 mil |
| 7 | Chone | `EC1303` | 7,5 | 150 mil |
| 8 | El Carmen | `EC1304` | 7,5 | 130 mil |
| 9 | El Empalme | `EC0908` | 7,0 | 90 mil |
| 10 | Montecristi | `EC1309` | 7,0 | 81 mil |
| 11 | Buena Fe | `EC1210` | 7,0 | 78 mil |
| 12 | Sucre | `EC1314` | 8,0 | 68 mil |
| 13 | Balzar | `EC0904` | 7,0 | 67 mil |
| 14 | Pedernales | `EC1317` | 8,0 | 66 mil |
| 15 | Jipijapa | `EC1306` | 6,5 | 64 mil |

## Deslizamiento y licuefacción

- **Deslizamiento.** Población en celdas de MMI≥VI donde el modelo espera ≥ 0,10 de probabilidad de deslizamiento según `nowicki_2014_global_model.tif`: **210 mil**. USGS declara para este evento alerta **naranja**, con 2.200 expuestas.
- **Licuefacción.** Población en celdas de MMI≥VI donde el modelo espera ≥ 0,10 de cobertura areal por licuefacción según `zhu_2017_general_model.tif`: **1,3 millones**. USGS declara para este evento alerta **roja**, con 260 mil expuestas.

Las dos cifras se cuentan sobre las celdas del corte publicado (MMI≥VI). **No son las de USGS y no se pueden comparar de frente**: aquí se cuenta la población entera de toda celda por encima del umbral, y USGS pondera la población de cada celda por el valor de esa celda. Son dos preguntas distintas sobre el mismo ráster.

**Y el umbral se evalúa en un solo punto por celda: su centroide.** El píxel del ráster es más pequeño que la celda, así que ese punto decide si entra la población entera de la celda o no entra ninguna. No es una estadística areal, y el sesgo que introduce no está medido: puede quedarse corto o pasarse.

Fuente: producto *Ground Failure* de USGS (v1), dominio público.

## Referencia cruzada

PAGER (USGS) estima para este evento una alerta **naranja**. CENTINELA no estima víctimas; la cifra se incluye solo como contraste.

Las dos cifras usan **la misma convención**: las clases de intensidad del USGS en números romanos (VI desde MMI 5,5, VII desde 6,5, VIII desde 7,5). Lo que puede separarlas es el insumo: este reporte declara en «Procedencia» qué versión del ShakeMap consumió, PAGER pudo correr sobre otra versión o sobre otro producto del mismo sismo, y los dos usan modelos de población distintos (GHS-POP aquí, LandScan en PAGER). El contraste clase a clase, hecho y comprobado para el sismo de San José del Palmar, está en `docs/PARA_INSTITUCIONES.md`.

## Incertidumbre y calidad

Discrepancia entre GHS-POP y WorldPop en las bandas MMI publicadas: **2,5 %**.

## Cambios frente a la versión anterior

- Recálculo con el mismo ShakeMap v1 (atlas) (cambió el cálculo o el activo de exposición, no USGS)
- Cambio de convención: las franjas son ahora las clases de intensidad del USGS (VI desde MMI 5,5, VII desde 6,5, VIII desde 7,5), no decimales literales (≥6,0 / ≥7,0 / ≥8,0). Las cifras cambian por la regla, no por los datos.
- Población en MMI≥VI: 4,3 millones → 8,6 millones
- Población en MMI≥VII: 2,3 millones → 3,4 millones
- Población en MMI≥VIII: 110 mil → 1 millón
- Población de 65 años o más en MMI≥VII: 180 mil → 260 mil
- Edificaciones en MMI≥VII: 990 mil → 1,4 millones
- Sedes de salud en MMI≥VII: 570 → 850
- Sedes educativas en MMI≥VII: 2.400 → 3.300
- Población en cobertura areal alta por licuefacción: 1,2 millones → 1,3 millones
- Edificaciones en MMI≥7: 1 millón → 990 mil
- Sedes de salud en MMI≥7: 550 → 570

## Descargas

- [CSV por municipio](adm2.csv)
- [Mapa PNG](mapa_general.png)

## Procedencia

- ShakeMap consumido: **v1** de `atlas`
- Ground Failure consumido: **v1** de `us`
- Manifiesto de exposición: [`ecu-v0.5`](https://github.com/sforero77/CENTINELA/blob/main/data/manifests/ECU.yaml)
- Pipeline: `0.1.0` · Generado: 2026-11-21T16:32:10Z

## Advertencias

- Exposición estimada, no daño observado.
- Este sistema no es una alerta temprana ni una recomendación de evacuación.
- No reemplaza a los servicios geológicos ni a las unidades de gestión del riesgo.
- Fuentes, vintages y versiones consumidas: ver manifiesto enlazado.
