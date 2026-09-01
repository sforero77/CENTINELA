# Exposición sísmica — M8,2 · Terremoto de Tehuantepec, México (2017)

**Evento USGS:** `us2000ahv0` · **Origen:** 2017-09-08T04:49:19Z UTC · **Profundidad:** 47,4 km

> **Reconstrucción retrospectiva.** Este reporte se calculó después del evento, no en respuesta a él, y no cuenta para las métricas de latencia del sistema.
>
> La **población** corresponde a la época indicada en el manifiesto de exposición. Las **edificaciones, vías, sedes de salud y educativas son las actuales**: OpenStreetMap y Overture publican el estado presente, no el histórico. Léelas como "qué infraestructura de hoy caería en esa zona de intensidad", no como lo que había entonces.

## Exposición estimada

| Indicador | Estimado |
|---|---:|
| Población en MMI≥6 | 760 mil |
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
| 1 | Heroica Ciudad De Juchitán De Zaragoza | `MX20043` | 6,5 | 110 mil |
| 2 | Salina Cruz | `MX20079` | 6,0 | 100 mil |
| 3 | Tonalá | `MX07097` | 6,0 | 77 mil |
| 4 | Santo Domingo Tehuantepec | `MX20515` | 6,0 | 71 mil |
| 5 | Pijijiapan | `MX07069` | 6,5 | 64 mil |
| 6 | Mapastepec | `MX07051` | 6,5 | 54 mil |
| 7 | Arriaga | `MX07009` | 6,5 | 51 mil |
| 8 | Acapetahua | `MX07003` | 6,0 | 38 mil |
| 9 | San Blas Atempa | `MX20124` | 6,0 | 20 mil |
| 10 | San Mateo Del Mar | `MX20248` | 6,0 | 18 mil |
| 11 | Unión Hidalgo | `MX20557` | 6,0 | 17 mil |
| 12 | San Pedro Tapanatepec | `MX20327` | 6,5 | 17 mil |
| 13 | Santa María Huatulco | `MX20413` | 6,0 | 14 mil |
| 14 | Chahuites | `MX20025` | 6,0 | 14 mil |
| 15 | Santo Domingo Zanatepec | `MX20525` | 6,0 | 14 mil |

## Deslizamiento y licuefacción

- **Deslizamiento.** Población en celdas donde el modelo espera ≥ 0,10 de probabilidad de deslizamiento: **2.100**. USGS declara para este evento alerta **naranja**, con 210 expuestas.
- **Licuefacción.** Población en celdas donde el modelo espera ≥ 0,10 de cobertura areal por licuefacción: **360 mil**. USGS declara para este evento alerta **roja**, con 150 mil expuestas.

Las dos cifras se cuentan sobre las celdas del corte publicado (MMI≥6). **No son las de USGS y no se pueden comparar de frente**: aquí se cuenta la población entera de toda celda por encima del umbral, y USGS pondera la población de cada celda por el valor de esa celda. Son dos preguntas distintas sobre el mismo ráster.

Fuente: producto *Ground Failure* de USGS (v1), dominio público.

## Referencia cruzada

PAGER (USGS) estima para este evento una alerta **roja**. CENTINELA no estima víctimas; la cifra se incluye solo como contraste.

Las dos cifras **no se tabulan igual**: PAGER agrupa por MMI redondeado —su fila «7» es todo lo que cae entre 6,5 y 7,49— y CENTINELA usa bandas literales, donde MMI≥7 es MMI≥7. Comparadas de frente parecen discrepar; puestas en el mismo eje, cada cifra de aquí cae dentro del intervalo que las filas de PAGER acotan por arriba y por abajo.

## Incertidumbre y calidad

Discrepancia entre GHS-POP y WorldPop en las bandas MMI publicadas: **12,1 %**.

## Descargas

- [CSV por municipio](adm2.csv)
- [Mapa PNG](mapa_general.png)

## Procedencia

- ShakeMap consumido: **v1**
- Ground Failure consumido: **v1**
- Manifiesto de exposición: `mex-v0.1`
- Pipeline: `0.1.0` · Generado: 2026-08-25T18:33:28Z

## Advertencias

- Exposición estimada, no daño observado.
- Este sistema no es una alerta temprana ni una recomendación de evacuación.
- No reemplaza a los servicios geológicos ni a las unidades de gestión del riesgo.
- Fuentes, vintages y versiones consumidas: ver manifiesto enlazado.
