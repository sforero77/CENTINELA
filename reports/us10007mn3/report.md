# Exposición sísmica: M7,6 · 41 km al SO de Quellón, Chile

**Evento USGS:** `us10007mn3` · **Origen:** 2016-12-25T14:22:27Z UTC · **Profundidad:** 38,0 km

> **Reconstrucción retrospectiva.** Este reporte se calculó después del evento, no en respuesta a él, y no cuenta para las métricas de latencia del sistema.
>
> La **población** corresponde a la época indicada en el manifiesto de exposición. Las **edificaciones, vías, sedes de salud y educativas son las actuales**: OpenStreetMap y Overture publican el estado presente, no el histórico. Léelas como "qué infraestructura de hoy caería en esa zona de intensidad", no como lo que había entonces.

## Exposición estimada

| Indicador | Estimado |
|---|---:|
| Población en MMI≥VI | 220 mil |
| Población en MMI≥VII | 92 mil |
| Población en MMI≥VIII | 490 |
| Edificaciones en MMI≥VII | 95 mil |
| Sedes de salud en MMI≥VII | 39 |
| Sedes educativas en MMI≥VII | 92 |
| Vías primarias y secundarias en MMI≥VII | 170 km |
| Vías locales en MMI≥VII | 3.300 km |
| Superficie construida en MMI≥VII | 8,9 km² |

Las cifras de esta tabla van redondeadas a dos cifras significativas, que es la precisión que un modelo de exposición sostiene. Las exactas están en el CSV municipal y en `report.json`.

De la población en intensidad MMI≥VII, alrededor de **11 mil** personas tienen 65 años o más.

## Municipios más expuestos, por población en MMI≥VII

| # | Municipio | Código | MMI max | Población MMI≥VII |
|---:|---|---|---:|---:|
| 1 | Chiloe | `CL102` | 7,5 | 89 mil |
| 2 | Aysén | `CL112` | 7,0 | 2.600 |
| 3 | Palena | `CL104` | 6,5 | 340 |

## Deslizamiento y licuefacción

USGS no ha publicado el producto *Ground Failure* para este evento. La sección se omite; el reporte se re-emite automáticamente si aparece.

## Referencia cruzada

PAGER (USGS) estima para este evento una alerta **amarilla**. CENTINELA no estima víctimas; la cifra se incluye solo como contraste.

Las dos cifras usan **la misma convención**: las clases de intensidad del USGS en números romanos (VI desde MMI 5,5, VII desde 6,5, VIII desde 7,5). Lo que puede separarlas es el insumo: este reporte declara en «Procedencia» qué versión del ShakeMap consumió, PAGER pudo correr sobre otra versión o sobre otro producto del mismo sismo, y los dos usan modelos de población distintos (GHS-POP aquí, LandScan en PAGER). El contraste clase a clase, hecho y comprobado para el sismo de San José del Palmar, está en `docs/PARA_INSTITUCIONES.md`.

## Incertidumbre y calidad

Discrepancia entre GHS-POP y WorldPop en las bandas MMI publicadas: **33,5 %**.

## Cambios frente a la versión anterior

- Recálculo con el mismo ShakeMap v1 (atlas) (cambió el cálculo o el activo de exposición, no USGS)
- Cambio de convención: las franjas son ahora las clases de intensidad del USGS (VI desde MMI 5,5, VII desde 6,5, VIII desde 7,5), no decimales literales (≥6,0 / ≥7,0 / ≥8,0). Las cifras cambian por la regla, no por los datos.
- Población en MMI≥VI: 200 mil → 220 mil
- Población en MMI≥VII: 57 mil → 92 mil
- Población en MMI≥VIII: 0 → 490
- Población de 65 años o más en MMI≥VII: 5.800 → 11 mil
- Edificaciones en MMI≥VII: 46 mil → 95 mil
- Sedes de salud en MMI≥VII: 23 → 39
- Sedes educativas en MMI≥VII: 50 → 92
- Edificaciones en MMI≥7: 45 mil → 46 mil

## Descargas

- [CSV por municipio](adm2.csv)
- [Mapa PNG](mapa_general.png)

## Procedencia

- ShakeMap consumido: **v1** de `atlas`
- Ground Failure consumido: **ninguno** (no publicado aún)
- Manifiesto de exposición: [`chl-v0.5`](https://github.com/sforero77/CENTINELA/blob/main/data/manifests/CHL.yaml)
- Pipeline: `0.1.0` · Generado: 2026-11-21T16:31:53Z

## Advertencias

- Exposición estimada, no daño observado.
- Este sistema no es una alerta temprana ni una recomendación de evacuación.
- No reemplaza a los servicios geológicos ni a las unidades de gestión del riesgo.
- Fuentes, vintages y versiones consumidas: ver manifiesto enlazado.
