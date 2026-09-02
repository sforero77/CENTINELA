# Exposición sísmica — M6,4 · 26 km al SO de Pocito, Argentina

**Evento USGS:** `us7000d18q` · **Origen:** 2021-01-19T02:46:22Z UTC · **Profundidad:** 20,8 km

> **Reconstrucción retrospectiva.** Este reporte se calculó después del evento, no en respuesta a él, y no cuenta para las métricas de latencia del sistema.
>
> La **población** corresponde a la época indicada en el manifiesto de exposición. Las **edificaciones, vías, sedes de salud y educativas son las actuales**: OpenStreetMap y Overture publican el estado presente, no el histórico. Léelas como "qué infraestructura de hoy caería en esa zona de intensidad", no como lo que había entonces.

## Exposición estimada

| Indicador | Estimado |
|---|---:|
| Población en MMI≥6 | 580 mil |
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
| 1 | Rawson | `AR070077` | 6,0 | 120 mil |
| 2 | Capital | `AR070028` | 6,0 | 120 mil |
| 3 | Chimbas | `AR070042` | 6,0 | 96 mil |
| 4 | Rivadavia | `AR070084` | 6,0 | 95 mil |
| 5 | Pocito | `AR070070` | 6,0 | 65 mil |
| 6 | Santa Lucía | `AR070098` | 6,0 | 51 mil |
| 7 | Sarmiento | `AR070105` | 6,5 | 21 mil |
| 8 | 9 de Julio | `AR070063` | 6,0 | 7.500 |
| 9 | 25 de Mayo | `AR070126` | 6,0 | 670 |
| 10 | Zonda | `AR070133` | 6,5 | 650 |
| 11 | Ullum | `AR070112` | 6,0 | 10 |
| 12 | Albardón | `AR070007` | 6,0 | 5 |

## Deslizamiento y licuefacción

- **Deslizamiento.** Población en celdas donde el modelo espera ≥ 0,10 de probabilidad de deslizamiento: **0**. USGS declara para este evento alerta **amarilla**, con 1 expuestas. El cero de arriba no dice que no haya exposición: dice que ninguna celda llega al umbral.
- **Licuefacción.** Población en celdas donde el modelo espera ≥ 0,10 de cobertura areal por licuefacción: **0**. USGS declara para este evento alerta **amarilla**, con 580 expuestas. El cero de arriba no dice que no haya exposición: dice que ninguna celda llega al umbral.

Las dos cifras se cuentan sobre las celdas del corte publicado (MMI≥6). **No son las de USGS y no se pueden comparar de frente**: aquí se cuenta la población entera de toda celda por encima del umbral, y USGS pondera la población de cada celda por el valor de esa celda. Son dos preguntas distintas sobre el mismo ráster.

Fuente: producto *Ground Failure* de USGS (v4), dominio público.

## Referencia cruzada

PAGER (USGS) estima para este evento una alerta **amarilla**. CENTINELA no estima víctimas; la cifra se incluye solo como contraste.

Las dos cifras **no se tabulan igual**: PAGER agrupa por MMI redondeado —su fila «7» es todo lo que cae entre 6,5 y 7,49— y CENTINELA usa bandas literales, donde MMI≥7 es MMI≥7. Comparadas de frente parecen discrepar; puestas en el mismo eje, cada cifra de aquí cae dentro del intervalo que las filas de PAGER acotan por arriba y por abajo.

## Incertidumbre y calidad

Discrepancia entre GHS-POP y WorldPop en las bandas MMI publicadas: **3,1 %**.

## Descargas

- [CSV por municipio](adm2.csv)
- [Mapa PNG](mapa_general.png)

## Procedencia

- ShakeMap consumido: **v8**
- Ground Failure consumido: **v4**
- Manifiesto de exposición: `arg-v0.2`
- Pipeline: `0.1.0` · Generado: 2026-09-02T02:46:39Z

## Advertencias

- Exposición estimada, no daño observado.
- Este sistema no es una alerta temprana ni una recomendación de evacuación.
- No reemplaza a los servicios geológicos ni a las unidades de gestión del riesgo.
- Fuentes, vintages y versiones consumidas: ver manifiesto enlazado.
