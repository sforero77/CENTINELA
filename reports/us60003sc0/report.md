# Exposición sísmica: M8,0 · 78 km al NE de Navarro, Perú

**Evento USGS:** `us60003sc0` · **Origen:** 2019-05-26T07:41:15Z UTC · **Profundidad:** 122,6 km

> **Reconstrucción retrospectiva.** Este reporte se calculó después del evento, no en respuesta a él, y no cuenta para las métricas de latencia del sistema.
>
> La **población** corresponde a la época indicada en el manifiesto de exposición. Las **edificaciones, vías, sedes de salud y educativas son las actuales**: OpenStreetMap y Overture publican el estado presente, no el histórico. Léelas como "qué infraestructura de hoy caería en esa zona de intensidad", no como lo que había entonces.

## Exposición estimada

| Indicador | Estimado |
|---|---:|
| Población en MMI≥VI | 2,1 millones |
| Población en MMI≥VII | 520 mil |
| Población en MMI≥VIII | 88 mil |
| Edificaciones en MMI≥VII | 260 mil |
| Sedes de salud en MMI≥VII | 239 |
| Sedes educativas en MMI≥VII | 2.440 |
| Vías primarias y secundarias en MMI≥VII | 570 km |
| Vías locales en MMI≥VII | 4.700 km |
| Superficie construida en MMI≥VII | 17,5 km² |

Las cifras de esta tabla van redondeadas a dos cifras significativas, que es la precisión que un modelo de exposición sostiene. Las exactas están en el CSV municipal y en `report.json`.

De la población en intensidad MMI≥VII, alrededor de **31 mil** personas tienen 65 años o más.

## Municipios más expuestos, por población en MMI≥VII

| # | Municipio | Código | MMI max | Población MMI≥VII |
|---:|---|---|---:|---:|
| 1 | Alto Amazonas | `PE1602` | 7,5 | 130 mil |
| 2 | San Martin | `PE2209` | 7,5 | 76 mil |
| 3 | Ucayali | `PE1606` | 7,5 | 74 mil |
| 4 | Requena | `PE1605` | 7,5 | 63 mil |
| 5 | Picota | `PE2207` | 6,5 | 52 mil |
| 6 | Datem del Marañon | `PE1607` | 7,5 | 40 mil |
| 7 | Bellavista | `PE2202` | 6,5 | 36 mil |
| 8 | Loreto | `PE1603` | 7,5 | 31 mil |
| 9 | Lamas | `PE2205` | 7,5 | 17 mil |
| 10 | El Dorado | `PE2203` | 6,5 | 5.400 |

## Deslizamiento y licuefacción

- **Deslizamiento.** Población en celdas de MMI≥VI donde el modelo espera ≥ 0,10 de probabilidad de deslizamiento según `nowicki_2014_global_model.tif`: **36**. USGS declara para este evento alerta **amarilla**, con 5 expuestas.
- **Licuefacción.** Población en celdas de MMI≥VI donde el modelo espera ≥ 0,10 de cobertura areal por licuefacción según `zhu_2017_general_model.tif`: **340 mil**. USGS declara para este evento alerta **roja**, con 75 mil expuestas.

Las dos cifras se cuentan sobre las celdas del corte publicado (MMI≥VI). **No son las de USGS y no se pueden comparar de frente**: aquí se cuenta la población entera de toda celda por encima del umbral, y USGS pondera la población de cada celda por el valor de esa celda. Son dos preguntas distintas sobre el mismo ráster.

**Y el umbral se evalúa en un solo punto por celda: su centroide.** El píxel del ráster es más pequeño que la celda, así que ese punto decide si entra la población entera de la celda o no entra ninguna. No es una estadística areal, y el sesgo que introduce no está medido: puede quedarse corto o pasarse.

Fuente: producto *Ground Failure* de USGS (v8), dominio público.

## Referencia cruzada

PAGER (USGS) estima para este evento una alerta **naranja**. CENTINELA no estima víctimas; la cifra se incluye solo como contraste.

Las dos cifras usan **la misma convención**: las clases de intensidad del USGS en números romanos (VI desde MMI 5,5, VII desde 6,5, VIII desde 7,5). Lo que puede separarlas es el insumo: este reporte declara en «Procedencia» qué versión del ShakeMap consumió, PAGER pudo correr sobre otra versión o sobre otro producto del mismo sismo, y los dos usan modelos de población distintos (GHS-POP aquí, LandScan en PAGER). El contraste clase a clase, hecho y comprobado para el sismo de San José del Palmar, está en `docs/PARA_INSTITUCIONES.md`.

## Incertidumbre y calidad

Discrepancia entre GHS-POP y WorldPop en las bandas MMI publicadas: **6,7 %**.

## Cambios frente a la versión anterior

- Recálculo con el mismo ShakeMap v1 (atlas) (cambió el cálculo o el activo de exposición, no USGS)
- Cambio de convención: las franjas son ahora las clases de intensidad del USGS (VI desde MMI 5,5, VII desde 6,5, VIII desde 7,5), no decimales literales (≥6,0 / ≥7,0 / ≥8,0). Las cifras cambian por la regla, no por los datos.
- Población en MMI≥VI: 1,1 millones → 2,1 millones
- Población en MMI≥VII: 250 mil → 520 mil
- Población en MMI≥VIII: 0 → 88 mil
- Población de 65 años o más en MMI≥VII: 15 mil → 31 mil
- Edificaciones en MMI≥VII: 130 mil → 260 mil
- Sedes de salud en MMI≥VII: 120 → 240
- Sedes educativas en MMI≥VII: 1.300 → 2.400
- Población en cobertura areal alta por licuefacción: 330 mil → 340 mil

## Descargas

- [CSV por municipio](adm2.csv)
- [Mapa PNG](mapa_general.png)

## Procedencia

- ShakeMap consumido: **v1** de `atlas`
- Ground Failure consumido: **v8** de `us`
- Manifiesto de exposición: [`per-v0.5`](https://github.com/sforero77/CENTINELA/blob/main/data/manifests/PER.yaml)
- Pipeline: `0.1.0` · Generado: 2026-11-21T16:30:57Z

## Advertencias

- Exposición estimada, no daño observado.
- Este sistema no es una alerta temprana ni una recomendación de evacuación.
- No reemplaza a los servicios geológicos ni a las unidades de gestión del riesgo.
- Fuentes, vintages y versiones consumidas: ver manifiesto enlazado.
