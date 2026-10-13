# Exposición sísmica: M6,1 · 17 km al O de Río Grande, Panamá

**Evento USGS:** `us6000u1wn` · **Origen:** 2026-10-12T23:20:36Z UTC · **Profundidad:** 11,0 km

## Exposición estimada

| Indicador | Estimado |
|---|---:|
| Población en MMI≥6 | 4.200 |
| Población en MMI≥7 | 37 |
| Población en MMI≥8 | el evento no llegó a esta banda |
| Edificaciones en MMI≥6 | 3.100 |
| Sedes de salud en MMI≥6 | 0 |
| Sedes educativas en MMI≥6 | 2 |
| Vías primarias y secundarias en MMI≥6 | 11 km |
| Vías locales en MMI≥6 | 62 km |
| Superficie construida en MMI≥6 | 0,3 km² |

Las cifras de esta tabla van redondeadas a dos cifras significativas, que es la precisión que un modelo de exposición sostiene. Las exactas están en el CSV municipal y en `report.json`.

De la población en intensidad MMI≥6, alrededor de **500** personas tienen 65 años o más.

## Municipios más expuestos, por población en MMI≥6

| # | Municipio | Código | MMI max | Población MMI≥6 |
|---:|---|---|---:|---:|
| 1 | Soná | `PA1312` | 7,0 | 4.200 |
| 2 | Las Palmas | `PA1305` | 6,0 | 5 |

## Deslizamiento y licuefacción

- **Deslizamiento.** Población en celdas de MMI≥6 donde el modelo espera ≥ 0,10 de probabilidad de deslizamiento según `jessee_2018_model.tif`: **0**.
- **Licuefacción.** Población en celdas de MMI≥6 donde el modelo espera ≥ 0,10 de cobertura areal por licuefacción según `zhu_2017_general_model.tif`: **820**. USGS declara para este evento alerta **amarilla**, con 1.100 expuestas.

Las dos cifras se cuentan sobre las celdas del corte publicado (MMI≥6). **No son las de USGS y no se pueden comparar de frente**: aquí se cuenta la población entera de toda celda por encima del umbral, y USGS pondera la población de cada celda por el valor de esa celda. Son dos preguntas distintas sobre el mismo ráster.

**Y el umbral se evalúa en un solo punto por celda: su centroide.** El píxel del ráster es más pequeño que la celda, así que ese punto decide si entra la población entera de la celda o no entra ninguna. No es una estadística areal, y el sesgo que introduce no está medido: puede quedarse corto o pasarse.

Fuente: producto *Ground Failure* de USGS (v2), dominio público.

## Referencia cruzada

PAGER (USGS) estima para este evento una alerta **verde**. CENTINELA no estima víctimas; la cifra se incluye solo como contraste.

Las dos cifras **no se tabulan igual** y no se pueden leer una contra otra: PAGER agrupa por MMI redondeado (su fila «7» es todo lo que cae entre 6,5 y 7,49) y CENTINELA usa bandas literales, donde MMI≥7 es MMI≥7. Puede además que no hablen del mismo ShakeMap: este reporte declara en «Procedencia» qué versión consumió, y PAGER pudo correr sobre otra versión o sobre otro producto del mismo sismo. El contraste banda a banda, hecho y comprobado para el sismo de San José del Palmar, está en `docs/PARA_INSTITUCIONES.md`.

## Incertidumbre y calidad

Discrepancia entre GHS-POP y WorldPop en las bandas MMI publicadas: **10,5 %**.

## Cambios frente a la versión anterior

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

- ShakeMap consumido: **v4** de `us`
- Ground Failure consumido: **v2** de `us`
- Manifiesto de exposición: [`pan-v0.4`](https://github.com/sforero77/CENTINELA/blob/main/data/manifests/PAN.yaml)
- Pipeline: `0.1.0` · Generado: 2026-10-13T01:40:52Z

## Advertencias

- Exposición estimada, no daño observado.
- Este sistema no es una alerta temprana ni una recomendación de evacuación.
- No reemplaza a los servicios geológicos ni a las unidades de gestión del riesgo.
- Fuentes, vintages y versiones consumidas: ver manifiesto enlazado.
