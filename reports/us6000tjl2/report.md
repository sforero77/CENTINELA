# Exposición sísmica: M7,4 · 4 km al SSO de San José del Palmar, Colombia

**Evento USGS:** `us6000tjl2` · **Origen:** 2026-08-10T12:34:28Z UTC · **Profundidad:** 116,1 km

> **Reconstrucción retrospectiva.** Este reporte se calculó después del evento, no en respuesta a él, y no cuenta para las métricas de latencia del sistema.
>
> La **población** corresponde a la época indicada en el manifiesto de exposición. Las **edificaciones, vías, sedes de salud y educativas son las actuales**: OpenStreetMap y Overture publican el estado presente, no el histórico. Léelas como "qué infraestructura de hoy caería en esa zona de intensidad", no como lo que había entonces.

## Exposición estimada

| Indicador | Estimado |
|---|---:|
| Población en MMI≥VI | 7,9 millones |
| Población en MMI≥VII | 6,4 millones |
| Población en MMI≥VIII | 890 mil |
| Edificaciones en MMI≥VII | 1 millón |
| Sedes de salud en MMI≥VII | 1.860 |
| Sedes educativas en MMI≥VII | 2.087 |
| Vías primarias y secundarias en MMI≥VII | 3.800 km |
| Vías locales en MMI≥VII | 29 mil km |
| Superficie construida en MMI≥VII | 164,7 km² |

El satélite detecta **1,6 veces** más superficie construida de la que explicarían las 1 millón de edificaciones registradas en MMI≥VII. La diferencia suele ser asentamiento informal o zona rural dispersa sin mapear: **el conteo de edificaciones se queda corto ahí, y la superficie construida no**.

Las cifras de esta tabla van redondeadas a dos cifras significativas, que es la precisión que un modelo de exposición sostiene. Las exactas están en el CSV municipal y en `report.json`.

De la población en intensidad MMI≥VII, alrededor de **760 mil** personas tienen 65 años o más.

## Municipios más expuestos, por población en MMI≥VII

| # | Municipio | Código | MMI max | Población MMI≥VII |
|---:|---|---|---:|---:|
| 1 | Santiago de Cali | `76001` | 6,5 | 2,5 millones |
| 2 | Pereira | `66001` | 7,5 | 510 mil |
| 3 | Buenaventura | `76109` | 7,0 | 450 mil |
| 4 | Manizales | `17001` | 7,0 | 400 mil |
| 5 | Armenia | `63001` | 7,5 | 340 mil |
| 6 | Tuluá | `76834` | 7,0 | 270 mil |
| 7 | Dosquebradas | `66170` | 7,5 | 180 mil |
| 8 | Guadalajara de Buga | `76111` | 6,5 | 130 mil |
| 9 | Cartago | `76147` | 7,5 | 130 mil |
| 10 | Quibdó | `27001` | 7,0 | 110 mil |
| 11 | Santa Rosa de Cabal | `66682` | 7,5 | 73 mil |
| 12 | Calarcá | `63130` | 7,0 | 73 mil |
| 13 | Yumbo | `76892` | 6,5 | 61 mil |
| 14 | La Tebaida | `63401` | 7,0 | 54 mil |
| 15 | Villamaría | `17873` | 7,0 | 54 mil |

## Deslizamiento y licuefacción

- **Deslizamiento.** Población en celdas de MMI≥VI donde el modelo espera ≥ 0,10 de probabilidad de deslizamiento según `jessee_2018_model.tif`: **26**. USGS declara para este evento alerta **naranja**, con 5.800 expuestas.
- **Licuefacción.** Población en celdas de MMI≥VI donde el modelo espera ≥ 0,10 de cobertura areal por licuefacción según `zhu_2017_general_model.tif`: **1,9 millones**. USGS declara para este evento alerta **roja**, con 520 mil expuestas.

Las dos cifras se cuentan sobre las celdas del corte publicado (MMI≥VI). **No son las de USGS y no se pueden comparar de frente**: aquí se cuenta la población entera de toda celda por encima del umbral, y USGS pondera la población de cada celda por el valor de esa celda. Son dos preguntas distintas sobre el mismo ráster.

**Y el umbral se evalúa en un solo punto por celda: su centroide.** El píxel del ráster es más pequeño que la celda, así que ese punto decide si entra la población entera de la celda o no entra ninguna. No es una estadística areal, y el sesgo que introduce no está medido: puede quedarse corto o pasarse.

Fuente: producto *Ground Failure* de USGS (v10), dominio público.

## Referencia cruzada

PAGER (USGS) estima para este evento una alerta **roja**. CENTINELA no estima víctimas; la cifra se incluye solo como contraste.

Las dos cifras usan **la misma convención**: las clases de intensidad del USGS en números romanos (VI desde MMI 5,5, VII desde 6,5, VIII desde 7,5). Lo que puede separarlas es el insumo: este reporte declara en «Procedencia» qué versión del ShakeMap consumió, PAGER pudo correr sobre otra versión o sobre otro producto del mismo sismo, y los dos usan modelos de población distintos (GHS-POP aquí, LandScan en PAGER). El contraste clase a clase, hecho y comprobado para el sismo de San José del Palmar, está en `docs/PARA_INSTITUCIONES.md`.

## Incertidumbre y calidad

Discrepancia entre GHS-POP y WorldPop en las bandas MMI publicadas: **0,2 %**.

## Cambios frente a la versión anterior

- Recálculo con el mismo ShakeMap v11 (us) (cambió el cálculo o el activo de exposición, no USGS)
- Cambio de convención: las franjas son ahora las clases de intensidad del USGS (VI desde MMI 5,5, VII desde 6,5, VIII desde 7,5), no decimales literales (≥6,0 / ≥7,0 / ≥8,0). Las cifras cambian por la regla, no por los datos.
- Población en MMI≥VI: 7,1 millones → 7,9 millones
- Población en MMI≥VII: 2,4 millones → 6,4 millones
- Población en MMI≥VIII: 0 → 890 mil
- Población de 65 años o más en MMI≥VII: 300 mil → 760 mil
- Edificaciones en MMI≥VII: 620 mil → 1 millón
- Sedes de salud en MMI≥VII: 520 → 1.900
- Sedes educativas en MMI≥VII: 1.100 → 2.100
- Población en probabilidad alta de deslizamiento: 0 → 26
- Población en cobertura areal alta por licuefacción: 1,8 millones → 1,9 millones
- ShakeMap: v10 → v11 (us)
- Profundidad: 108 → 116 km
- Epicentro: reubicado 5 km
- Población de 65 años o más en MMI≥7: 290 mil → 300 mil
- Edificaciones en MMI≥7: 600 mil → 620 mil
- Sedes de salud en MMI≥7: 500 → 520
- Edificaciones en MMI≥7: 530 mil → 600 mil

## Descargas

- [CSV por municipio](adm2.csv)
- [Mapa PNG](mapa_general.png)

## Procedencia

- ShakeMap consumido: **v11** de `us`
- Ground Failure consumido: **v10** de `us`
- Manifiesto de exposición: [`col-v0.9`](https://github.com/sforero77/CENTINELA/blob/main/data/manifests/COL.yaml)
- Pipeline: `0.1.0` · Generado: 2026-11-21T16:29:19Z

## Advertencias

- Exposición estimada, no daño observado.
- Este sistema no es una alerta temprana ni una recomendación de evacuación.
- No reemplaza a los servicios geológicos ni a las unidades de gestión del riesgo.
- Fuentes, vintages y versiones consumidas: ver manifiesto enlazado.
