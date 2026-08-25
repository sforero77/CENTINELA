# Exposicion sismica — M6.6 32 km al S de La Libertad, El Salvador

**Evento USGS:** `us70003t2n` · **Origen:** 2019-05-30T09:03:32Z UTC · **Profundidad:** 57,9 km

> **Reconstruccion retrospectiva.** Este reporte se calculo despues del evento, no en respuesta a el, y no cuenta para las metricas de latencia del sistema.
>
> La **poblacion** corresponde a la epoca indicada en el manifest de exposicion. Las **edificaciones, vias, sedes de salud y educativas son las actuales**: OpenStreetMap y Overture publican el estado presente, no el historico. Leelas como "que infraestructura de hoy caeria en esa zona de intensidad", no como lo que habia entonces.

## Exposicion estimada

| Indicador | Estimado |
|---|---:|
| Poblacion en MMI≥6 | 66 mil |
| Poblacion en MMI≥7 | 0 |
| Poblacion en MMI≥8 | 0 |
| Edificaciones en MMI≥7 | 0 |
| Sedes de salud en MMI≥7 | 0 |
| Sedes educativas en MMI≥7 | 0 |
| Kilometros de via en MMI≥7 | 0 km |

## Municipios mas expuestos (top 15), por poblacion en MMI≥6

| # | Municipio | Codigo | MMI max | Poblacion MMI≥6 |
|---:|---|---|---:|---:|
| 1 | La Paz Oeste | `SV06003` | 6,0 | 45 mil |
| 2 | La Libertad Costa | `SV05002` | 6,0 | 10 mil |
| 3 | La Paz Centro | `SV06001` | 6,0 | 7.400 |
| 4 | San Salvador Sur | `SV10005` | 6,0 | 3.500 |
| 5 | Cuscatlán Norte | `SV04001` | 5,5 | 0 |
| 6 | San Salvador Este | `SV10002` | 5,5 | 0 |
| 7 | Cabañas Oeste | `SV02002` | 5,5 | 0 |
| 8 | La Libertad Sur | `SV05006` | 5,5 | 0 |
| 9 | La Paz Este | `SV06002` | 5,5 | 0 |
| 10 | Cuscatlán Sur | `SV04002` | 5,5 | 0 |
| 11 | La Libertad Este | `SV05003` | 5,5 | 0 |
| 12 | San Salvador Centro | `SV10001` | 5,5 | 0 |
| 13 | Lago De Llopango | `SV10899` | 5,5 | 0 |
| 14 | San Vicente Norte | `SV11001` | 5,5 | 0 |
| 15 | San Vicente Sur | `SV11002` | 5,5 | 0 |

## Deslizamiento y licuefaccion

- Poblacion en celdas con probabilidad **alta de deslizamiento**: 1.100
- Poblacion en celdas con probabilidad **alta de licuefaccion**: 21 mil

Fuente: producto *Ground Failure* de USGS (v6), dominio publico.

## Referencia cruzada

PAGER (USGS) estima para este evento una alerta **yellow**. CENTINELA no estima victimas; la cifra se incluye solo como contraste.

## Incertidumbre y calidad

Discrepancia entre GHS-POP y WorldPop en el area afectada: **13,1 %**.

## Descargas

- [CSV por municipio](adm2.csv)
- [Mapa PNG](mapa_general.png)

## Procedencia

- ShakeMap consumido: **v1**
- Ground Failure consumido: **v6**
- Manifest de exposicion: `slv-v0.1`
- Pipeline: `0.1.0` · Generado: 2026-08-25T17:54:04Z

## Advertencias

- Exposicion estimada, no dano observado.
- Este sistema no es una alerta temprana ni una recomendacion de evacuacion.
- No reemplaza a los servicios geologicos ni a las unidades de gestion del riesgo.
- Fuentes, vintages y versiones consumidas: ver manifest enlazado.
