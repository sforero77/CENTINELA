# Exposición sísmica — M6,2 · 4 km al SE de Aserrío de Gariché, Panamá

**Evento USGS:** `us7000455l` · **Origen:** 2019-06-26T05:23:51Z UTC · **Profundidad:** 32,6 km

> **Reconstrucción retrospectiva.** Este reporte se calculó después del evento, no en respuesta a él, y no cuenta para las métricas de latencia del sistema.
>
> La **población** corresponde a la época indicada en el manifiesto de exposición. Las **edificaciones, vías, sedes de salud y educativas son las actuales**: OpenStreetMap y Overture publican el estado presente, no el histórico. Léelas como "qué infraestructura de hoy caería en esa zona de intensidad", no como lo que había entonces.

## Exposición estimada

| Indicador | Estimado |
|---|---:|
| Población en MMI≥6 | 55 mil |
| Población en MMI≥7 | 0 |
| Población en MMI≥8 | 0 |
| Edificaciones en MMI≥7 | 0 |
| Sedes de salud en MMI≥7 | 0 |
| Sedes educativas en MMI≥7 | 0 |
| Kilómetros de vía en MMI≥7 | 0 km |

Las cifras de esta tabla van redondeadas a dos cifras significativas, que es la precisión que un modelo de exposición sostiene. Las exactas están en el CSV municipal y en `report.json`.

## Municipios más expuestos, por población en MMI≥6

| # | Municipio | Código | MMI max | Población MMI≥6 |
|---:|---|---|---:|---:|
| 1 | Bugaba | `PA0205` | 6,0 | 27 mil |
| 2 | Barú | `PA0202` | 6,0 | 23 mil |
| 3 | Alanje | `PA0201` | 6,0 | 5.200 |
| 4 | Renacimiento | `PA0210` | 6,0 | 270 |

## Deslizamiento y licuefacción

- **Deslizamiento.** Población en celdas donde el modelo espera ≥ 0,10 de probabilidad de deslizamiento: **0**.
- **Licuefacción.** Población en celdas donde el modelo espera ≥ 0,10 de cobertura areal por licuefacción: **20 mil**. USGS declara para este evento alerta **naranja**, con 23 mil expuestas.

Las dos cifras se cuentan sobre las celdas del corte publicado (MMI≥6). **No son las de USGS y no se pueden comparar de frente**: aquí se cuenta la población entera de toda celda por encima del umbral, y USGS pondera la población de cada celda por el valor de esa celda. Son dos preguntas distintas sobre el mismo ráster.

Fuente: producto *Ground Failure* de USGS (v8), dominio público.

## Referencia cruzada

PAGER (USGS) estima para este evento una alerta **amarilla**. CENTINELA no estima víctimas; la cifra se incluye solo como contraste.

Las dos cifras **no se tabulan igual** y no se pueden leer una contra otra: PAGER agrupa por MMI redondeado —su fila «7» es todo lo que cae entre 6,5 y 7,49— y CENTINELA usa bandas literales, donde MMI≥7 es MMI≥7. Puede además que no hablen del mismo ShakeMap: este reporte declara en «Procedencia» qué versión consumió, y PAGER pudo correr sobre otra versión o sobre otro producto del mismo sismo. El contraste banda a banda, hecho y comprobado para el sismo de San José del Palmar, está en `docs/PARA_INSTITUCIONES.md`.

## Incertidumbre y calidad

Discrepancia entre GHS-POP y WorldPop en las bandas MMI publicadas: **1,0 %**.

## Descargas

- [CSV por municipio](adm2.csv)
- [Mapa PNG](mapa_general.png)

## Procedencia

- ShakeMap consumido: **v1**
- Ground Failure consumido: **v8**
- Manifiesto de exposición: `pan-v0.2`
- Pipeline: `0.1.0` · Generado: 2026-09-02T02:46:10Z

## Advertencias

- Exposición estimada, no daño observado.
- Este sistema no es una alerta temprana ni una recomendación de evacuación.
- No reemplaza a los servicios geológicos ni a las unidades de gestión del riesgo.
- Fuentes, vintages y versiones consumidas: ver manifiesto enlazado.
