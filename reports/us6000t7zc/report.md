# Exposición sísmica: M7,2 · 20 km al E de San Felipe, Venezuela

**Evento USGS:** `us6000t7zc` · **Origen:** 2026-06-24T22:04:31Z UTC · **Profundidad:** 10,0 km

> **Reconstrucción retrospectiva.** Este reporte se calculó después del evento, no en respuesta a él, y no cuenta para las métricas de latencia del sistema.
>
> La **población** corresponde a la época indicada en el manifiesto de exposición. Las **edificaciones, vías, sedes de salud y educativas son las actuales**: OpenStreetMap y Overture publican el estado presente, no el histórico. Léelas como "qué infraestructura de hoy caería en esa zona de intensidad", no como lo que había entonces.

## Exposición estimada

| Indicador | Estimado |
|---|---:|
| Población en MMI≥VI | 5,2 millones |
| Población en MMI≥VII | 980 mil |
| Población en MMI≥VIII | 390 mil |
| Edificaciones en MMI≥VII | 330 mil |
| Sedes de salud en MMI≥VII | 49 |
| Sedes educativas en MMI≥VII | 175 |
| Vías primarias y secundarias en MMI≥VII | 840 km |
| Vías locales en MMI≥VII | 5.200 km |
| Superficie construida en MMI≥VII | 42,3 km² |

Las cifras de esta tabla van redondeadas a dos cifras significativas, que es la precisión que un modelo de exposición sostiene. Las exactas están en el CSV municipal y en `report.json`.

De la población en intensidad MMI≥VII, alrededor de **87 mil** personas tienen 65 años o más.

## Municipios más expuestos, por población en MMI≥VII

| # | Municipio | Código | MMI max | Población MMI≥VII |
|---:|---|---|---:|---:|
| 1 | Puerto Cabello | `VE0811` | 7,0 | 190 mil |
| 2 | San Felipe | `VE2211` | 8,0 | 140 mil |
| 3 | Veroes | `VE2214` | 8,0 | 100 mil |
| 4 | Crespo | `VE1302` | 6,5 | 63 mil |
| 5 | Juan José Mora | `VE0805` | 8,0 | 58 mil |
| 6 | Bruzual | `VE2203` | 7,0 | 50 mil |
| 7 | José Antonio Páez | `VE2206` | 6,5 | 49 mil |
| 8 | Urachiche | `VE2213` | 6,5 | 48 mil |
| 9 | Nirgua | `VE2209` | 7,5 | 38 mil |
| 10 | Bolívar | `VE2202` | 7,0 | 32 mil |
| 11 | Independencia | `VE2205` | 8,0 | 30 mil |
| 12 | Palmasola | `VE1116` | 7,0 | 30 mil |
| 13 | Arístides Bastidas | `VE2201` | 7,5 | 27 mil |
| 14 | Sucre | `VE2212` | 7,5 | 27 mil |
| 15 | Cocorote | `VE2204` | 7,5 | 25 mil |

## Deslizamiento y licuefacción

- **Deslizamiento.** Población en celdas de MMI≥VI donde el modelo espera ≥ 0,10 de probabilidad de deslizamiento según `jessee_2018_model.tif`: **0**. USGS declara para este evento alerta **naranja**, con 1.700 expuestas. El cero de arriba no dice que no haya exposición: dice que ninguna celda llega al umbral.
- **Licuefacción.** Población en celdas de MMI≥VI donde el modelo espera ≥ 0,10 de cobertura areal por licuefacción según `zhu_2017_general_model.tif`: **330 mil**. USGS declara para este evento alerta **naranja**, con 91 mil expuestas.

Las dos cifras se cuentan sobre las celdas del corte publicado (MMI≥VI). **No son las de USGS y no se pueden comparar de frente**: aquí se cuenta la población entera de toda celda por encima del umbral, y USGS pondera la población de cada celda por el valor de esa celda. Son dos preguntas distintas sobre el mismo ráster.

**Y el umbral se evalúa en un solo punto por celda: su centroide.** El píxel del ráster es más pequeño que la celda, así que ese punto decide si entra la población entera de la celda o no entra ninguna. No es una estadística areal, y el sesgo que introduce no está medido: puede quedarse corto o pasarse.

Fuente: producto *Ground Failure* de USGS (v7), dominio público.

## Referencia cruzada

PAGER (USGS) estima para este evento una alerta **roja**. CENTINELA no estima víctimas; la cifra se incluye solo como contraste.

Las dos cifras usan **la misma convención**: las clases de intensidad del USGS en números romanos (VI desde MMI 5,5, VII desde 6,5, VIII desde 7,5). Lo que puede separarlas es el insumo: este reporte declara en «Procedencia» qué versión del ShakeMap consumió, PAGER pudo correr sobre otra versión o sobre otro producto del mismo sismo, y los dos usan modelos de población distintos (GHS-POP aquí, LandScan en PAGER). El contraste clase a clase, hecho y comprobado para el sismo de San José del Palmar, está en `docs/PARA_INSTITUCIONES.md`.

## Incertidumbre y calidad

Discrepancia entre GHS-POP y WorldPop en las bandas MMI publicadas: **24,4 %**.

## Cambios frente a la versión anterior

- Recálculo con el mismo ShakeMap v9 (us) (cambió el cálculo o el activo de exposición, no USGS)
- Cambio de convención: las franjas son ahora las clases de intensidad del USGS (VI desde MMI 5,5, VII desde 6,5, VIII desde 7,5), no decimales literales (≥6,0 / ≥7,0 / ≥8,0). Las cifras cambian por la regla, no por los datos.
- Población en MMI≥VI: 2,8 millones → 5,2 millones
- Población en MMI≥VII: 490 mil → 980 mil
- Población en MMI≥VIII: 230 mil → 390 mil
- Población de 65 años o más en MMI≥VII: 41 mil → 87 mil
- Edificaciones en MMI≥VII: 190 mil → 330 mil
- Sedes de salud en MMI≥VII: 32 → 49
- Sedes educativas en MMI≥VII: 92 → 180
- Población en cobertura areal alta por licuefacción: 290 mil → 330 mil

## Descargas

- [CSV por municipio](adm2.csv)
- [Mapa PNG](mapa_general.png)

## Procedencia

- ShakeMap consumido: **v9** de `us`
- Ground Failure consumido: **v7** de `us`
- Manifiesto de exposición: [`ven-v0.5`](https://github.com/sforero77/CENTINELA/blob/main/data/manifests/VEN.yaml)
- Pipeline: `0.1.0` · Generado: 2026-11-21T16:29:39Z

## Advertencias

- Exposición estimada, no daño observado.
- Este sistema no es una alerta temprana ni una recomendación de evacuación.
- No reemplaza a los servicios geológicos ni a las unidades de gestión del riesgo.
- Fuentes, vintages y versiones consumidas: ver manifiesto enlazado.
