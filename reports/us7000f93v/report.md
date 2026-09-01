# Exposición sísmica — M7,0 · Acapulco, México

**Evento USGS:** `us7000f93v` · **Origen:** 2021-09-08T01:47:47Z UTC · **Profundidad:** 20,0 km

> **Reconstrucción retrospectiva.** Este reporte se calculó después del evento, no en respuesta a él, y no cuenta para las métricas de latencia del sistema.
>
> La **población** corresponde a la época indicada en el manifiesto de exposición. Las **edificaciones, vías, sedes de salud y educativas son las actuales**: OpenStreetMap y Overture publican el estado presente, no el histórico. Léelas como "qué infraestructura de hoy caería en esa zona de intensidad", no como lo que había entonces.

## Exposición estimada

| Indicador | Estimado |
|---|---:|
| Población en MMI≥6 | 1,1 millones |
| Población en MMI≥7 | 910 mil |
| Población en MMI≥8 | 0 |
| Edificaciones en MMI≥7 | 330 mil |
| Sedes de salud en MMI≥7 | 152 |
| Sedes educativas en MMI≥7 | 3.132 |
| Kilometros de via en MMI≥7 | 0 km |
| Superficie construida en MMI≥7 | 46,8 km² |

Las cifras de esta tabla van redondeadas a dos cifras significativas, que es la precisión que un modelo de exposición sostiene. Las exactas están en el CSV municipal y en `report.json`.

De la población en intensidad MMI≥7, alrededor de **81 mil** personas tienen 65 años o más.

## Municipios más expuestos, por población en MMI≥7

| # | Municipio | Código | MMI max | Población MMI≥7 |
|---:|---|---|---:|---:|
| 1 | Acapulco De Juárez | `MX12001` | 7,5 | 880 mil |
| 2 | Coyuca De Benítez | `MX12021` | 7,0 | 30 mil |
| 3 | San Marcos | `MX12053` | 7,0 | 5.100 |
| 4 | Juan R. Escudero | `MX12039` | 7,0 | 4 |

## Deslizamiento y licuefacción

- Población en celdas con probabilidad **alta de deslizamiento**: 2.400
- Población en celdas con probabilidad **alta de licuefacción**: 67 mil

Fuente: producto *Ground Failure* de USGS (v3), dominio público.

## Referencia cruzada

PAGER (USGS) estima para este evento una alerta **roja**. CENTINELA no estima víctimas; la cifra se incluye solo como contraste.

## Incertidumbre y calidad

Discrepancia entre GHS-POP y WorldPop en el área afectada: **9,9 %**.

## Descargas

- [CSV por municipio](adm2.csv)
- [Mapa PNG](mapa_general.png)

## Procedencia

- ShakeMap consumido: **v7**
- Ground Failure consumido: **v3**
- Manifiesto de exposición: `mex-v0.1`
- Pipeline: `0.1.0` · Generado: 2026-08-25T18:31:59Z

## Advertencias

- Exposición estimada, no daño observado.
- Este sistema no es una alerta temprana ni una recomendación de evacuación.
- No reemplaza a los servicios geológicos ni a las unidades de gestión del riesgo.
- Fuentes, vintages y versiones consumidas: ver manifiesto enlazado.
