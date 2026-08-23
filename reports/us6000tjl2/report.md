# Exposicion sismica — M7.4 5 km al S de San José del Palmar, Chocó, Colombia

**Evento USGS:** `us6000tjl2` · **Origen:** 2026-08-10T12:34:28Z UTC · **Profundidad:** 110,3 km

## Exposicion estimada

| Indicador | Estimado |
|---|---:|
| Poblacion en MMI≥6 | 7 millones |
| Poblacion en MMI≥7 | 2,4 millones |
| Poblacion en MMI≥8 | 0 |
| Edificaciones en MMI≥7 | 440 mil |
| Sedes de salud en MMI≥7 | 0 |
| Sedes educativas en MMI≥7 | 0 |
| Kilometros de via en MMI≥7 | 0 km |

## Municipios mas expuestos (top 15)

| # | Municipio | DIVIPOLA | MMI max | Poblacion MMI≥7 |
|---:|---|---|---:|---:|
| 1 | Pereira | `66001` | 7,5 | 500 mil |
| 2 | Buenaventura | `76109` | 7,0 | 400 mil |
| 3 | Armenia | `63001` | 7,0 | 340 mil |
| 4 | Tuluá | `76834` | 7,0 | 260 mil |
| 5 | Dosquebradas | `66170` | 7,5 | 180 mil |
| 6 | Cartago | `76147` | 7,5 | 130 mil |
| 7 | Quibdó | `27001` | 7,0 | 110 mil |
| 8 | Santa Rosa De Cabal | `66682` | 7,0 | 68 mil |
| 9 | La Tebaida | `63401` | 7,0 | 54 mil |
| 10 | Zarzal | `76895` | 7,5 | 40 mil |
| 11 | Alcalá | `76020` | 7,0 | 37 mil |
| 12 | La Unión | `76400` | 7,5 | 35 mil |
| 13 | Montenegro | `63470` | 7,0 | 32 mil |
| 14 | Quimbaya | `63594` | 7,0 | 32 mil |
| 15 | Chinchiná | `17174` | 7,0 | 29 mil |

## Deslizamiento y licuefaccion

- Poblacion en celdas con probabilidad **alta de deslizamiento**: 4
- Poblacion en celdas con probabilidad **alta de licuefaccion**: 1,7 millones

Fuente: producto *Ground Failure* de USGS (v7), dominio publico.

## Referencia cruzada

PAGER (USGS) estima para este evento una alerta **red**. CENTINELA no estima victimas; la cifra se incluye solo como contraste.

## Incertidumbre y calidad

Discrepancia entre GHS-POP y WorldPop en el area afectada: **0,0 %**.

- BACKTEST: reconstruccion retrospectiva del evento, no un reporte emitido en su momento.
- Cobertura de salud, educacion, vias y desglose etario aun no incluida en el activo v0.4.
- Banda de discrepancia GHS-POP vs WorldPop pendiente de calcular.

## Descargas

- [GeoParquet (celdas H3 r8)](exposure_col.parquet)
- [CSV por municipio](adm2.csv)

## Procedencia

- ShakeMap consumido: **v7**
- Ground Failure consumido: **v7**
- Manifest de exposicion: `col-v0.4`
- Pipeline: `0.1.0` · Generado: 2026-08-23T15:07:06Z

## Advertencias

- Exposicion estimada, no dano observado.
- Este sistema no es una alerta temprana ni una recomendacion de evacuacion.
- No reemplaza a los servicios geologicos ni a las unidades de gestion del riesgo.
- Fuentes, vintages y versiones consumidas: ver manifest enlazado.
