# Exposición sísmica: M7,0 · Acapulco, México

**Evento USGS:** `us7000f93v` · **Origen:** 2021-09-08T01:47:47Z UTC · **Profundidad:** 20,0 km

> **Reconstrucción retrospectiva.** Este reporte se calculó después del evento, no en respuesta a él, y no cuenta para las métricas de latencia del sistema.
>
> La **población** corresponde a la época indicada en el manifiesto de exposición. Las **edificaciones, vías, sedes de salud y educativas son las actuales**: OpenStreetMap y Overture publican el estado presente, no el histórico. Léelas como "qué infraestructura de hoy caería en esa zona de intensidad", no como lo que había entonces.

## Exposición estimada

| Indicador | Estimado |
|---|---:|
| Población en MMI≥VI | 1,3 millones |
| Población en MMI≥VII | 1 millón |
| Población en MMI≥VIII | 60 mil |
| Edificaciones en MMI≥VII | 390 mil |
| Sedes de salud en MMI≥VII | 176 |
| Sedes educativas en MMI≥VII | 3.383 |
| Vías primarias y secundarias en MMI≥VII | 840 km |
| Vías locales en MMI≥VII | 5.300 km |
| Superficie construida en MMI≥VII | 53,3 km² |

Las cifras de esta tabla van redondeadas a dos cifras significativas, que es la precisión que un modelo de exposición sostiene. Las exactas están en el CSV municipal y en `report.json`.

De la población en intensidad MMI≥VII, alrededor de **99 mil** personas tienen 65 años o más.

## Municipios más expuestos, por población en MMI≥VII

| # | Municipio | Código | MMI max | Población MMI≥VII |
|---:|---|---|---:|---:|
| 1 | Acapulco de Juárez | `MX12001` | 7,5 | 880 mil |
| 2 | Coyuca de Benítez | `MX12021` | 7,0 | 64 mil |
| 3 | San Marcos | `MX12053` | 7,0 | 33 mil |
| 4 | Juan R. Escudero | `MX12039` | 7,0 | 24 mil |
| 5 | Tecoanapa | `MX12056` | 6,5 | 3.400 |
| 6 | Chilpancingo de los Bravo | `MX12029` | 6,5 | 1.100 |

## Deslizamiento y licuefacción

- **Deslizamiento.** Población en celdas de MMI≥VI donde el modelo espera ≥ 0,10 de probabilidad de deslizamiento según `jessee_2018_model.tif`: **2.700**. USGS declara para este evento alerta **naranja**, con 2.200 expuestas.
- **Licuefacción.** Población en celdas de MMI≥VI donde el modelo espera ≥ 0,10 de cobertura areal por licuefacción según `zhu_2017_general_model.tif`: **73 mil**. USGS declara para este evento alerta **naranja**, con 12 mil expuestas.

Las dos cifras se cuentan sobre las celdas del corte publicado (MMI≥VI). **No son las de USGS y no se pueden comparar de frente**: aquí se cuenta la población entera de toda celda por encima del umbral, y USGS pondera la población de cada celda por el valor de esa celda. Son dos preguntas distintas sobre el mismo ráster.

**Y el umbral se evalúa en un solo punto por celda: su centroide.** El píxel del ráster es más pequeño que la celda, así que ese punto decide si entra la población entera de la celda o no entra ninguna. No es una estadística areal, y el sesgo que introduce no está medido: puede quedarse corto o pasarse.

Fuente: producto *Ground Failure* de USGS (v3), dominio público.

## Referencia cruzada

PAGER (USGS) estima para este evento una alerta **roja**. CENTINELA no estima víctimas; la cifra se incluye solo como contraste.

Las dos cifras usan **la misma convención**: las clases de intensidad del USGS en números romanos (VI desde MMI 5,5, VII desde 6,5, VIII desde 7,5). Lo que puede separarlas es el insumo: este reporte declara en «Procedencia» qué versión del ShakeMap consumió, PAGER pudo correr sobre otra versión o sobre otro producto del mismo sismo, y los dos usan modelos de población distintos (GHS-POP aquí, LandScan en PAGER). El contraste clase a clase, hecho y comprobado para el sismo de San José del Palmar, está en `docs/PARA_INSTITUCIONES.md`.

## Incertidumbre y calidad

Discrepancia entre GHS-POP y WorldPop en las bandas MMI publicadas: **10,2 %**.

## Cambios frente a la versión anterior

- Recálculo con el mismo ShakeMap v7 (us) (cambió el cálculo o el activo de exposición, no USGS)
- Cambio de convención: las franjas son ahora las clases de intensidad del USGS (VI desde MMI 5,5, VII desde 6,5, VIII desde 7,5), no decimales literales (≥6,0 / ≥7,0 / ≥8,0). Las cifras cambian por la regla, no por los datos.
- Población en MMI≥VI: 1,1 millones → 1,3 millones
- Población en MMI≥VII: 910 mil → 1 millón
- Población en MMI≥VIII: 0 → 60 mil
- Población de 65 años o más en MMI≥VII: 89 mil → 99 mil
- Edificaciones en MMI≥VII: 330 mil → 390 mil
- Sedes de salud en MMI≥VII: 160 → 180
- Sedes educativas en MMI≥VII: 3.300 → 3.400
- Población en probabilidad alta de deslizamiento: 2.400 → 2.700
- Población en cobertura areal alta por licuefacción: 67 mil → 73 mil
- Recálculo con el mismo ShakeMap v7 (us) (cambió el cálculo o el activo de exposición, no USGS)
- Sedes de salud en MMI≥7: 150 → 160
- Sedes educativas en MMI≥7: 3.100 → 3.300

## Descargas

- [CSV por municipio](adm2.csv)
- [Mapa PNG](mapa_general.png)

## Procedencia

- ShakeMap consumido: **v7** de `us`
- Ground Failure consumido: **v3** de `us`
- Manifiesto de exposición: [`mex-v0.5`](https://github.com/sforero77/CENTINELA/blob/main/data/manifests/MEX.yaml)
- Pipeline: `0.1.0` · Generado: 2026-11-21T16:30:09Z

## Advertencias

- Exposición estimada, no daño observado.
- Este sistema no es una alerta temprana ni una recomendación de evacuación.
- No reemplaza a los servicios geológicos ni a las unidades de gestión del riesgo.
- Fuentes, vintages y versiones consumidas: ver manifiesto enlazado.
