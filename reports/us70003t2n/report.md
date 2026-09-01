# Exposición sísmica — M6,6 · 32 km al S de La Libertad, El Salvador

**Evento USGS:** `us70003t2n` · **Origen:** 2019-05-30T09:03:32Z UTC · **Profundidad:** 57,9 km

> **Reconstrucción retrospectiva.** Este reporte se calculó después del evento, no en respuesta a él, y no cuenta para las métricas de latencia del sistema.
>
> La **población** corresponde a la época indicada en el manifiesto de exposición. Las **edificaciones, vías, sedes de salud y educativas son las actuales**: OpenStreetMap y Overture publican el estado presente, no el histórico. Léelas como "qué infraestructura de hoy caería en esa zona de intensidad", no como lo que había entonces.

## Exposición estimada

| Indicador | Estimado |
|---|---:|
| Población en MMI≥6 | 66 mil |
| Población en MMI≥7 | 0 |
| Población en MMI≥8 | 0 |
| Edificaciones en MMI≥7 | 0 |
| Sedes de salud en MMI≥7 | 0 |
| Sedes educativas en MMI≥7 | 0 |
| Kilometros de via en MMI≥7 | 0 km |

Las cifras de esta tabla van redondeadas a dos cifras significativas, que es la precisión que un modelo de exposición sostiene. Las exactas están en el CSV municipal y en `report.json`.

## Municipios más expuestos, por población en MMI≥6

| # | Municipio | Código | MMI max | Población MMI≥6 |
|---:|---|---|---:|---:|
| 1 | La Paz Oeste | `SV06003` | 6,0 | 45 mil |
| 2 | La Libertad Costa | `SV05002` | 6,0 | 10 mil |
| 3 | La Paz Centro | `SV06001` | 6,0 | 7.400 |
| 4 | San Salvador Sur | `SV10005` | 6,0 | 3.500 |

## Deslizamiento y licuefacción

- **Deslizamiento.** Población en celdas donde el modelo espera ≥ 0,10 de probabilidad de deslizamiento: **1.100**.
- **Licuefacción.** Población en celdas donde el modelo espera ≥ 0,10 de cobertura areal por licuefacción: **21 mil**. USGS declara para este evento alerta **naranja**, con 17 mil expuestas.

Las dos cifras se cuentan sobre las celdas del corte publicado (MMI≥6). **No son las de USGS y no se pueden comparar de frente**: aquí se cuenta la población entera de toda celda por encima del umbral, y USGS pondera la población de cada celda por el valor de esa celda. Son dos preguntas distintas sobre el mismo ráster.

Fuente: producto *Ground Failure* de USGS (v6), dominio público.

## Referencia cruzada

PAGER (USGS) estima para este evento una alerta **amarilla**. CENTINELA no estima víctimas; la cifra se incluye solo como contraste.

Las dos cifras **no se tabulan igual**: PAGER agrupa por MMI redondeado —su fila «7» es todo lo que cae entre 6,5 y 7,49— y CENTINELA usa bandas literales, donde MMI≥7 es MMI≥7. Comparadas de frente parecen discrepar; puestas en el mismo eje, cada cifra de aquí cae dentro del intervalo que las filas de PAGER acotan por arriba y por abajo.

## Incertidumbre y calidad

Discrepancia entre GHS-POP y WorldPop en las bandas MMI publicadas: **13,1 %**.

## Descargas

- [CSV por municipio](adm2.csv)
- [Mapa PNG](mapa_general.png)

## Procedencia

- ShakeMap consumido: **v1**
- Ground Failure consumido: **v6**
- Manifiesto de exposición: `slv-v0.2`
- Pipeline: `0.1.0` · Generado: 2026-09-01T22:10:49Z

## Advertencias

- Exposición estimada, no daño observado.
- Este sistema no es una alerta temprana ni una recomendación de evacuación.
- No reemplaza a los servicios geológicos ni a las unidades de gestión del riesgo.
- Fuentes, vintages y versiones consumidas: ver manifiesto enlazado.
