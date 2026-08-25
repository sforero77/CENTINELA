# Exposicion sismica — M6.7 10 km al SSO de Coquimbo, Chile

**Evento USGS:** `us2000j6hy` · **Origen:** 2019-01-20T01:32:52Z UTC · **Profundidad:** 63,0 km

> **Reconstruccion retrospectiva.** Este reporte se calculo despues del evento, no en respuesta a el, y no cuenta para las metricas de latencia del sistema.
>
> La **poblacion** corresponde a la epoca indicada en el manifest de exposicion. Las **edificaciones, vias, sedes de salud y educativas son las actuales**: OpenStreetMap y Overture publican el estado presente, no el historico. Leelas como "que infraestructura de hoy caeria en esa zona de intensidad", no como lo que habia entonces.

## Exposicion estimada

| Indicador | Estimado |
|---|---:|
| Poblacion en MMI≥6 | 700 mil |
| Poblacion en MMI≥7 | 470 mil |
| Poblacion en MMI≥8 | 0 |
| Edificaciones en MMI≥7 | 180 mil |
| Sedes de salud en MMI≥7 | 126 |
| Sedes educativas en MMI≥7 | 540 |
| Vias primarias y secundarias en MMI≥7 | 210 km |
| Vias locales en MMI≥7 | 1.400 km |
| Superficie construida en MMI≥7 | 19,5 km² |

De la poblacion en intensidad MMI≥7, alrededor de **56 mil** personas tienen 65 años o más.

## Municipios mas expuestos (top 15), por poblacion en MMI≥7

| # | Municipio | Codigo | MMI max | Poblacion MMI≥7 |
|---:|---|---|---:|---:|
| 1 | Elqui | `CL041` | 7,0 | 470 mil |
| 2 | Limarí | `CL043` | 6,5 | 0 |
| 3 | Huasco | `CL033` | 5,0 | 0 |

## Deslizamiento y licuefaccion

- Poblacion en celdas con probabilidad **alta de deslizamiento**: 1.200
- Poblacion en celdas con probabilidad **alta de licuefaccion**: 210

Fuente: producto *Ground Failure* de USGS (v2), dominio publico.

## Referencia cruzada

PAGER (USGS) estima para este evento una alerta **orange**. CENTINELA no estima victimas; la cifra se incluye solo como contraste.

## Incertidumbre y calidad

Discrepancia entre GHS-POP y WorldPop en el area afectada: **10,4 %**.

## Descargas

- [CSV por municipio](adm2.csv)
- [Mapa PNG](mapa_general.png)

## Procedencia

- ShakeMap consumido: **v1**
- Ground Failure consumido: **v2**
- Manifest de exposicion: `chl-v0.1`
- Pipeline: `0.1.0` · Generado: 2026-08-25T17:40:12Z

## Advertencias

- Exposicion estimada, no dano observado.
- Este sistema no es una alerta temprana ni una recomendacion de evacuacion.
- No reemplaza a los servicios geologicos ni a las unidades de gestion del riesgo.
- Fuentes, vintages y versiones consumidas: ver manifest enlazado.
