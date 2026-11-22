# Exposición sísmica: M6,7 · 9 km al NE de Carhuamayo, Perú

**Evento USGS:** `pt26325050` · **Origen:** 2026-11-21T00:09:17Z UTC · **Profundidad:** 108,0 km

## Exposición estimada

| Indicador | Estimado |
|---|---:|
| Población en MMI≥VI | 1.800 |
| Población en MMI≥VII | el evento no llegó a esta banda |
| Población en MMI≥VIII | el evento no llegó a esta banda |
| Edificaciones en MMI≥VI | 3.200 |
| Sedes de salud en MMI≥VI | 2 |
| Sedes educativas en MMI≥VI | 7 |
| Vías primarias y secundarias en MMI≥VI | 13 km |
| Vías locales en MMI≥VI | 90 km |
| Superficie construida en MMI≥VI | 0,4 km² |

Las cifras de esta tabla van redondeadas a dos cifras significativas, que es la precisión que un modelo de exposición sostiene. Las exactas están en el CSV municipal y en `report.json`.

De la población en intensidad MMI≥VI, alrededor de **200** personas tienen 65 años o más.

## Municipios más expuestos, por población en MMI≥VI

| # | Municipio | Código | MMI max | Población MMI≥VI |
|---:|---|---|---:|---:|
| 1 | Pasco | `PE1901` | 5,5 | 1.600 |
| 2 | Junin | `PE1205` | 5,5 | 200 |

## Deslizamiento y licuefacción

- **Deslizamiento.** Población en celdas de MMI≥VI donde el modelo espera ≥ 0,10 de probabilidad de deslizamiento según `jessee_2018_model.tif`: **0**.
- **Licuefacción.** Población en celdas de MMI≥VI donde el modelo espera ≥ 0,10 de cobertura areal por licuefacción según `zhu_2017_general_model.tif`: **11**. USGS declara para este evento alerta **amarilla**, con 300 expuestas.

Las dos cifras se cuentan sobre las celdas del corte publicado (MMI≥VI). **No son las de USGS y no se pueden comparar de frente**: aquí se cuenta la población entera de toda celda por encima del umbral, y USGS pondera la población de cada celda por el valor de esa celda. Son dos preguntas distintas sobre el mismo ráster.

**Y el umbral se evalúa en un solo punto por celda: su centroide.** El píxel del ráster es más pequeño que la celda, así que ese punto decide si entra la población entera de la celda o no entra ninguna. No es una estadística areal, y el sesgo que introduce no está medido: puede quedarse corto o pasarse.

Fuente: producto *Ground Failure* de USGS (v3), dominio público.

## Referencia cruzada

PAGER (USGS) estima para este evento una alerta **verde**. CENTINELA no estima víctimas; la cifra se incluye solo como contraste.

Las dos cifras usan **la misma convención**: las clases de intensidad del USGS en números romanos (VI desde MMI 5,5, VII desde 6,5, VIII desde 7,5). Lo que puede separarlas es el insumo: este reporte declara en «Procedencia» qué versión del ShakeMap consumió, PAGER pudo correr sobre otra versión o sobre otro producto del mismo sismo, y los dos usan modelos de población distintos (GHS-POP aquí, LandScan en PAGER). El contraste clase a clase, hecho y comprobado para el sismo de San José del Palmar, está en `docs/PARA_INSTITUCIONES.md`.

## Incertidumbre y calidad

Discrepancia entre GHS-POP y WorldPop en las bandas MMI publicadas: **30,7 %**.

## Cambios frente a la versión anterior

- ShakeMap: v2 (us) → v3 (us)
- Ground Failure: v2 (us) → v3 (us)
- Ninguna cifra publicada cambia frente a la versión anterior.
- Recálculo con el mismo ShakeMap v2 (us) (cambió el cálculo o el activo de exposición, no USGS)
- Cambio de convención: las franjas son ahora las clases de intensidad del USGS (VI desde MMI 5,5, VII desde 6,5, VIII desde 7,5), no decimales literales (≥6,0 / ≥7,0 / ≥8,0). Las cifras cambian por la regla, no por los datos.
- Población en MMI≥VI: 0 → 1.800
- Población en cobertura areal alta por licuefacción: 0 → 11
- ShakeMap: v1 (us) → v2 (us)
- Ground Failure: v1 (us) → v2 (us)
- Ninguna cifra publicada cambia frente a la versión anterior.
- ShakeMap: v0 → v1 (us)
- Ground Failure: v0 → v1 (us)
- Ninguna cifra publicada cambia frente a la versión anterior.

## Descargas

- [CSV por municipio](adm2.csv)
- [Mapa PNG](mapa_general.png)

## Procedencia

- ShakeMap consumido: **v3** de `us`
- Ground Failure consumido: **v3** de `us`
- Manifiesto de exposición: [`per-v0.5`](https://github.com/sforero77/CENTINELA/blob/main/data/manifests/PER.yaml)
- Pipeline: `0.1.0` · Generado: 2026-11-22T13:34:01Z

## Advertencias

- Exposición estimada, no daño observado.
- Este sistema no es una alerta temprana ni una recomendación de evacuación.
- No reemplaza a los servicios geológicos ni a las unidades de gestión del riesgo.
- Fuentes, vintages y versiones consumidas: ver manifiesto enlazado.
