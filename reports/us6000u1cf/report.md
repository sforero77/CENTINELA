# Exposición sísmica: M6,0 · 3 km al NO de La Tronosa, Panamá

**Evento USGS:** `us6000u1cf` · **Origen:** 2026-10-10T04:14:01Z UTC · **Profundidad:** 10,0 km

## Exposición estimada

| Indicador | Estimado |
|---|---:|
| Población en MMI≥VI | 19 mil |
| Población en MMI≥VII | 3.100 |
| Población en MMI≥VIII | el evento no llegó a esta banda |
| Edificaciones en MMI≥VII | 2.400 |
| Sedes de salud en MMI≥VII | 0 |
| Sedes educativas en MMI≥VII | 2 |
| Vías primarias y secundarias en MMI≥VII | 28 km |
| Vías locales en MMI≥VII | 160 km |
| Superficie construida en MMI≥VII | 0,3 km² |

Las cifras de esta tabla van redondeadas a dos cifras significativas, que es la precisión que un modelo de exposición sostiene. Las exactas están en el CSV municipal y en `report.json`.

De la población en intensidad MMI≥VII, alrededor de **600** personas tienen 65 años o más.

## Municipios más expuestos, por población en MMI≥VII

| # | Municipio | Código | MMI max | Población MMI≥VII |
|---:|---|---|---:|---:|
| 1 | Tonosí | `PA0907` | 7,0 | 2.700 |
| 2 | Macaracas | `PA0904` | 7,0 | 400 |

## Deslizamiento y licuefacción

- **Deslizamiento.** Población en celdas de MMI≥VI donde el modelo espera ≥ 0,10 de probabilidad de deslizamiento según `jessee_2018_model.tif`: **0**. USGS declara para este evento alerta **amarilla**, con 5 expuestas. El cero de arriba no dice que no haya exposición: dice que ninguna celda llega al umbral.
- **Licuefacción.** Población en celdas de MMI≥VI donde el modelo espera ≥ 0,10 de cobertura areal por licuefacción según `zhu_2017_general_model.tif`: **3.900**. USGS declara para este evento alerta **amarilla**, con 1.000 expuestas.

Las dos cifras se cuentan sobre las celdas del corte publicado (MMI≥VI). **No son las de USGS y no se pueden comparar de frente**: aquí se cuenta la población entera de toda celda por encima del umbral, y USGS pondera la población de cada celda por el valor de esa celda. Son dos preguntas distintas sobre el mismo ráster.

**Y el umbral se evalúa en un solo punto por celda: su centroide.** El píxel del ráster es más pequeño que la celda, así que ese punto decide si entra la población entera de la celda o no entra ninguna. No es una estadística areal, y el sesgo que introduce no está medido: puede quedarse corto o pasarse.

Fuente: producto *Ground Failure* de USGS (v4), dominio público.

## Referencia cruzada

PAGER (USGS) estima para este evento una alerta **amarilla**. CENTINELA no estima víctimas; la cifra se incluye solo como contraste.

Las dos cifras usan **la misma convención**: las clases de intensidad del USGS en números romanos (VI desde MMI 5,5, VII desde 6,5, VIII desde 7,5). Lo que puede separarlas es el insumo: este reporte declara en «Procedencia» qué versión del ShakeMap consumió, PAGER pudo correr sobre otra versión o sobre otro producto del mismo sismo, y los dos usan modelos de población distintos (GHS-POP aquí, LandScan en PAGER). El contraste clase a clase, hecho y comprobado para el sismo de San José del Palmar, está en `docs/PARA_INSTITUCIONES.md`.

## Incertidumbre y calidad

Discrepancia entre GHS-POP y WorldPop en las bandas MMI publicadas: **17,5 %**.

## Cambios frente a la versión anterior

- ShakeMap: v5 (us) → v6 (us)
- Epicentro: reubicado 4 km
- Población en MMI≥VI: 20 mil → 19 mil
- Población en MMI≥VII: 5.600 → 3.100
- Población de 65 años o más en MMI≥VII: 1.000 → 600
- Edificaciones en MMI≥VII: 4.200 → 2.400
- Sedes educativas en MMI≥VII: 3 → 2
- Población en cobertura areal alta por licuefacción: 3.600 → 3.900
- Recálculo con el mismo ShakeMap v5 (us) (cambió el cálculo o el activo de exposición, no USGS)
- Cambio de convención: las franjas son ahora las clases de intensidad del USGS (VI desde MMI 5,5, VII desde 6,5, VIII desde 7,5), no decimales literales (≥6,0 / ≥7,0 / ≥8,0). Las cifras cambian por la regla, no por los datos.
- Población en MMI≥VI: 10 mil → 20 mil
- Población en MMI≥VII: 1.700 → 5.600
- Población de 65 años o más en MMI≥VII: 340 → 1.000
- Edificaciones en MMI≥VII: 1.200 → 4.200
- Sedes educativas en MMI≥VII: 1 → 3
- Población en cobertura areal alta por licuefacción: 3.400 → 3.600
- ShakeMap: v4 (us) → v5 (us)
- Ground Failure: v3 (us) → v4 (us)
- Epicentro: reubicado 4 km
- Población en MMI≥6: 12 mil → 10 mil
- Población en MMI≥7: 1.500 → 1.700
- Población de 65 años o más en MMI≥7: 290 → 340
- Edificaciones en MMI≥7: 1.000 → 1.200
- ShakeMap: v3 (us) → v4 (us)
- Ground Failure: v2 (us) → v3 (us)
- Ninguna cifra publicada cambia frente a la versión anterior.
- ShakeMap: v2 (us) → v3 (us)
- Ground Failure: v1 (us) → v2 (us)
- Ninguna cifra publicada cambia frente a la versión anterior.
- ShakeMap: v1 (us) → v2 (us)
- Ground Failure: v0 → v1 (us)
- Población en cobertura areal alta por licuefacción: 0 → 3.400
- ShakeMap: v0 → v1 (us)
- Población en MMI≥6: 0 → 12 mil
- Población en MMI≥7: 0 → 1.500
- Población de 65 años o más en MMI≥7: 0 → 290
- Edificaciones en MMI≥7: 0 → 1.000
- Sedes educativas en MMI≥7: 0 → 1

## Descargas

- [CSV por municipio](adm2.csv)
- [Mapa PNG](mapa_general.png)

## Procedencia

- ShakeMap consumido: **v6** de `us`
- Ground Failure consumido: **v4** de `us`
- Manifiesto de exposición: [`pan-v0.5`](https://github.com/sforero77/CENTINELA/blob/main/data/manifests/PAN.yaml)
- Pipeline: `0.1.0` · Generado: 2026-11-22T13:34:01Z

## Advertencias

- Exposición estimada, no daño observado.
- Este sistema no es una alerta temprana ni una recomendación de evacuación.
- No reemplaza a los servicios geológicos ni a las unidades de gestión del riesgo.
- Fuentes, vintages y versiones consumidas: ver manifiesto enlazado.
