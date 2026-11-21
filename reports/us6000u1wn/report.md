# Exposición sísmica: M6,1 · 15 km al O de Río Grande, Panamá

**Evento USGS:** `us6000u1wn` · **Origen:** 2026-10-12T23:20:36Z UTC · **Profundidad:** 11,0 km

## Exposición estimada

| Indicador | Estimado |
|---|---:|
| Población en MMI≥VI | 13 mil |
| Población en MMI≥VII | 1.600 |
| Población en MMI≥VIII | el evento no llegó a esta banda |
| Edificaciones en MMI≥VII | 980 |
| Sedes de salud en MMI≥VII | 0 |
| Sedes educativas en MMI≥VII | 1 |
| Kilómetros de vía en MMI≥VII | 12 km |
| Superficie construida en MMI≥VII | 0,1 km² |

Las cifras de esta tabla van redondeadas a dos cifras significativas, que es la precisión que un modelo de exposición sostiene. Las exactas están en el CSV municipal y en `report.json`.

De la población en intensidad MMI≥VII, alrededor de **160** personas tienen 65 años o más.

## Municipios más expuestos, por población en MMI≥VII

| # | Municipio | Código | MMI max | Población MMI≥VII |
|---:|---|---|---:|---:|
| 1 | Soná | `PA1312` | 7,0 | 1.600 |

## Deslizamiento y licuefacción

- **Deslizamiento.** Población en celdas de MMI≥VI donde el modelo espera ≥ 0,10 de probabilidad de deslizamiento según `jessee_2018_model.tif`: **0**. USGS declara para este evento alerta **amarilla**, con 2 expuestas. El cero de arriba no dice que no haya exposición: dice que ninguna celda llega al umbral.
- **Licuefacción.** Población en celdas de MMI≥VI donde el modelo espera ≥ 0,10 de cobertura areal por licuefacción según `zhu_2017_general_model.tif`: **1.300**. USGS declara para este evento alerta **amarilla**, con 1.300 expuestas.

Las dos cifras se cuentan sobre las celdas del corte publicado (MMI≥VI). **No son las de USGS y no se pueden comparar de frente**: aquí se cuenta la población entera de toda celda por encima del umbral, y USGS pondera la población de cada celda por el valor de esa celda. Son dos preguntas distintas sobre el mismo ráster.

**Y el umbral se evalúa en un solo punto por celda: su centroide.** El píxel del ráster es más pequeño que la celda, así que ese punto decide si entra la población entera de la celda o no entra ninguna. No es una estadística areal, y el sesgo que introduce no está medido: puede quedarse corto o pasarse.

Fuente: producto *Ground Failure* de USGS (v3), dominio público.

## Referencia cruzada

PAGER (USGS) estima para este evento una alerta **amarilla**. CENTINELA no estima víctimas; la cifra se incluye solo como contraste.

Las dos cifras usan **la misma convención**: las clases de intensidad del USGS en números romanos (VI desde MMI 5,5, VII desde 6,5, VIII desde 7,5). Lo que puede separarlas es el insumo: este reporte declara en «Procedencia» qué versión del ShakeMap consumió, PAGER pudo correr sobre otra versión o sobre otro producto del mismo sismo, y los dos usan modelos de población distintos (GHS-POP aquí, LandScan en PAGER). El contraste clase a clase, hecho y comprobado para el sismo de San José del Palmar, está en `docs/PARA_INSTITUCIONES.md`.

## Incertidumbre y calidad

Discrepancia entre GHS-POP y WorldPop en las bandas MMI publicadas: **0,5 %**.

## Cambios frente a la versión anterior

- Recálculo con el mismo ShakeMap v5 (us) (cambió el cálculo o el activo de exposición, no USGS)
- Cambio de convención: las franjas son ahora las clases de intensidad del USGS (VI desde MMI 5,5, VII desde 6,5, VIII desde 7,5), no decimales literales (≥6,0 / ≥7,0 / ≥8,0). Las cifras cambian por la regla, no por los datos.
- Población en MMI≥VI: 5.500 → 13 mil
- Población en MMI≥VII: 660 → 1.600
- Población de 65 años o más en MMI≥VII: 60 → 160
- Edificaciones en MMI≥VII: 200 → 980
- Sedes educativas en MMI≥VII: 0 → 1
- Población en cobertura areal alta por licuefacción: 820 → 1.300
- ShakeMap: v4 (us) → v5 (us)
- Ground Failure: v2 (us) → v3 (us)
- Epicentro: reubicado 3 km
- Población en MMI≥6: 4.200 → 5.500
- Población en MMI≥7: 37 → 660
- Población de 65 años o más en MMI≥7: 3 → 60
- Edificaciones en MMI≥7: 36 → 200
- ShakeMap: v3 (us) → v4 (us)
- Ground Failure: v1 (us) → v2 (us)
- Población en MMI≥6: 4.700 → 4.200
- Población en MMI≥7: 620 → 37
- Población de 65 años o más en MMI≥7: 57 → 3
- Edificaciones en MMI≥7: 200 → 36
- Población en cobertura areal alta por licuefacción: 800 → 820
- ShakeMap: v2 (us) → v3 (us)
- Profundidad: 10 → 11 km
- Epicentro: reubicado 2 km
- Ninguna cifra publicada cambia frente a la versión anterior.
- ShakeMap: v1 (us) → v2 (us)
- Ninguna cifra publicada cambia frente a la versión anterior.
- ShakeMap: v0 → v1 (us)
- Ground Failure: v0 → v1 (us)
- Población en MMI≥6: 0 → 4.700
- Población en MMI≥7: 0 → 620
- Población de 65 años o más en MMI≥7: 0 → 57
- Edificaciones en MMI≥7: 0 → 200
- Población en cobertura areal alta por licuefacción: 0 → 800

## Descargas

- [CSV por municipio](adm2.csv)
- [Mapa PNG](mapa_general.png)

## Procedencia

- ShakeMap consumido: **v5** de `us`
- Ground Failure consumido: **v3** de `us`
- Manifiesto de exposición: [`pan-v0.5`](https://github.com/sforero77/CENTINELA/blob/main/data/manifests/PAN.yaml)
- Pipeline: `0.1.0` · Generado: 2026-11-21T16:28:31Z

## Advertencias

- Exposición estimada, no daño observado.
- Este sistema no es una alerta temprana ni una recomendación de evacuación.
- No reemplaza a los servicios geológicos ni a las unidades de gestión del riesgo.
- Fuentes, vintages y versiones consumidas: ver manifiesto enlazado.
