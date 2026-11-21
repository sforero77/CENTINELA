# Exposición sísmica: M7,1 · 37 km al O de Atiquipa, Perú

**Evento USGS:** `us2000cjfy` · **Origen:** 2018-01-14T09:18:45Z UTC · **Profundidad:** 39,0 km

> **Reconstrucción retrospectiva.** Este reporte se calculó después del evento, no en respuesta a él, y no cuenta para las métricas de latencia del sistema.
>
> La **población** corresponde a la época indicada en el manifiesto de exposición. Las **edificaciones, vías, sedes de salud y educativas son las actuales**: OpenStreetMap y Overture publican el estado presente, no el histórico. Léelas como "qué infraestructura de hoy caería en esa zona de intensidad", no como lo que había entonces.

## Exposición estimada

| Indicador | Estimado |
|---|---:|
| Población en MMI≥VI | 55 mil |
| Población en MMI≥VII | 9.600 |
| Población en MMI≥VIII | el evento no llegó a esta banda |
| Edificaciones en MMI≥VII | 13 mil |
| Sedes de salud en MMI≥VII | 5 |
| Sedes educativas en MMI≥VII | 17 |
| Vías primarias y secundarias en MMI≥VII | 160 km |
| Vías locales en MMI≥VII | 340 km |
| Superficie construida en MMI≥VII | 0,7 km² |

Las cifras de esta tabla van redondeadas a dos cifras significativas, que es la precisión que un modelo de exposición sostiene. Las exactas están en el CSV municipal y en `report.json`.

De la población en intensidad MMI≥VII, alrededor de **990** personas tienen 65 años o más.

## Municipios más expuestos, por población en MMI≥VII

| # | Municipio | Código | MMI max | Población MMI≥VII |
|---:|---|---|---:|---:|
| 1 | Caraveli | `PE0403` | 6,5 | 9.600 |

## Deslizamiento y licuefacción

USGS no ha publicado el producto *Ground Failure* para este evento. La sección se omite; el reporte se re-emite automáticamente si aparece.

## Referencia cruzada

PAGER (USGS) estima para este evento una alerta **verde**. CENTINELA no estima víctimas; la cifra se incluye solo como contraste.

Las dos cifras usan **la misma convención**: las clases de intensidad del USGS en números romanos (VI desde MMI 5,5, VII desde 6,5, VIII desde 7,5). Lo que puede separarlas es el insumo: este reporte declara en «Procedencia» qué versión del ShakeMap consumió, PAGER pudo correr sobre otra versión o sobre otro producto del mismo sismo, y los dos usan modelos de población distintos (GHS-POP aquí, LandScan en PAGER). El contraste clase a clase, hecho y comprobado para el sismo de San José del Palmar, está en `docs/PARA_INSTITUCIONES.md`.

## Incertidumbre y calidad

Discrepancia entre GHS-POP y WorldPop en las bandas MMI publicadas: **16,8 %**.

## Cambios frente a la versión anterior

- Recálculo con el mismo ShakeMap v1 (atlas) (cambió el cálculo o el activo de exposición, no USGS)
- Cambio de convención: las franjas son ahora las clases de intensidad del USGS (VI desde MMI 5,5, VII desde 6,5, VIII desde 7,5), no decimales literales (≥6,0 / ≥7,0 / ≥8,0). Las cifras cambian por la regla, no por los datos.
- Población en MMI≥VI: 37 mil → 55 mil
- Población en MMI≥VII: 0 → 9.600
- Población de 65 años o más en MMI≥VII: 0 → 990
- Edificaciones en MMI≥VII: 0 → 13 mil
- Sedes de salud en MMI≥VII: 0 → 5
- Sedes educativas en MMI≥VII: 0 → 17

## Descargas

- [CSV por municipio](adm2.csv)
- [Mapa PNG](mapa_general.png)

## Procedencia

- ShakeMap consumido: **v1** de `atlas`
- Ground Failure consumido: **ninguno** (no publicado aún)
- Manifiesto de exposición: [`per-v0.5`](https://github.com/sforero77/CENTINELA/blob/main/data/manifests/PER.yaml)
- Pipeline: `0.1.0` · Generado: 2026-11-21T16:31:24Z

## Advertencias

- Exposición estimada, no daño observado.
- Este sistema no es una alerta temprana ni una recomendación de evacuación.
- No reemplaza a los servicios geológicos ni a las unidades de gestión del riesgo.
- Fuentes, vintages y versiones consumidas: ver manifiesto enlazado.
