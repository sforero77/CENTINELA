# Exposición sísmica — M7,4 · 2 km al SE de San José del Palmar, Colombia

**Evento USGS:** `us6000tjl2` · **Origen:** 2026-08-10T12:34:28Z UTC · **Profundidad:** 108,2 km

> **Reconstrucción retrospectiva.** Este reporte se calculó después del evento, no en respuesta a él, y no cuenta para las métricas de latencia del sistema.
>
> La **población** corresponde a la época indicada en el manifiesto de exposición. Las **edificaciones, vías, sedes de salud y educativas son las actuales**: OpenStreetMap y Overture publican el estado presente, no el histórico. Léelas como "qué infraestructura de hoy caería en esa zona de intensidad", no como lo que había entonces.

## Exposición estimada

| Indicador | Estimado |
|---|---:|
| Población en MMI≥6 | 7,2 millones |
| Población en MMI≥7 | 2,4 millones |
| Población en MMI≥8 | — el evento no llegó a esta banda |
| Edificaciones en MMI≥7 | 450 mil |
| Sedes de salud en MMI≥7 | 516 |
| Sedes educativas en MMI≥7 | 1.003 |
| Vías primarias y secundarias en MMI≥7 | 1.000 km |
| Vías locales en MMI≥7 | 7.800 km |
| Superficie construida en MMI≥7 | 70,3 km² |

El satélite detecta **1,6 veces** más superficie construida de la que explicarían las 450 mil edificaciones registradas. La diferencia suele ser asentamiento informal o zona rural dispersa sin mapear: **el conteo de edificaciones se queda corto ahí, y la superficie construida no**.

Las cifras de esta tabla van redondeadas a dos cifras significativas, que es la precisión que un modelo de exposición sostiene. Las exactas están en el CSV municipal y en `report.json`.

De la población en intensidad MMI≥7, alrededor de **290 mil** personas tienen 65 años o más.

## Municipios más expuestos, por población en MMI≥7

| # | Municipio | Código | MMI max | Población MMI≥7 |
|---:|---|---|---:|---:|
| 1 | Pereira | `66001` | 7,5 | 500 mil |
| 2 | Buenaventura | `76109` | 7,0 | 400 mil |
| 3 | Armenia | `63001` | 7,0 | 340 mil |
| 4 | Tuluá | `76834` | 7,0 | 260 mil |
| 5 | Dosquebradas | `66170` | 7,5 | 180 mil |
| 6 | Cartago | `76147` | 7,5 | 130 mil |
| 7 | Quibdó | `27001` | 7,0 | 110 mil |
| 8 | Santa Rosa de Cabal | `66682` | 7,0 | 68 mil |
| 9 | La Tebaida | `63401` | 7,0 | 54 mil |
| 10 | Zarzal | `76895` | 7,5 | 40 mil |
| 11 | Alcalá | `76020` | 7,0 | 37 mil |
| 12 | La Unión | `76400` | 7,5 | 35 mil |
| 13 | Montenegro | `63470` | 7,0 | 32 mil |
| 14 | Quimbaya | `63594` | 7,0 | 32 mil |
| 15 | Chinchiná | `17174` | 7,0 | 30 mil |

## Deslizamiento y licuefacción

- **Deslizamiento.** Población en celdas donde el modelo espera ≥ 0,10 de probabilidad de deslizamiento: **0**. USGS declara para este evento alerta **naranja**, con 1.700 expuestas. El cero de arriba no dice que no haya exposición: dice que ninguna celda llega al umbral.
- **Licuefacción.** Población en celdas donde el modelo espera ≥ 0,10 de cobertura areal por licuefacción: **1,6 millones**. USGS declara para este evento alerta **roja**, con 460 mil expuestas.

Las dos cifras se cuentan sobre las celdas del corte publicado (MMI≥6). **No son las de USGS y no se pueden comparar de frente**: aquí se cuenta la población entera de toda celda por encima del umbral, y USGS pondera la población de cada celda por el valor de esa celda. Son dos preguntas distintas sobre el mismo ráster.

Fuente: producto *Ground Failure* de USGS (v8), dominio público.

## Referencia cruzada

PAGER (USGS) estima para este evento una alerta **roja**. CENTINELA no estima víctimas; la cifra se incluye solo como contraste.

Las dos cifras **no se tabulan igual** y no se pueden leer una contra otra: PAGER agrupa por MMI redondeado —su fila «7» es todo lo que cae entre 6,5 y 7,49— y CENTINELA usa bandas literales, donde MMI≥7 es MMI≥7. Puede además que no hablen del mismo ShakeMap: este reporte declara en «Procedencia» qué versión consumió, y PAGER pudo correr sobre otra versión o sobre otro producto del mismo sismo. El contraste banda a banda, hecho y comprobado para el sismo de San José del Palmar, está en `docs/PARA_INSTITUCIONES.md`.

## Incertidumbre y calidad

Discrepancia entre GHS-POP y WorldPop en las bandas MMI publicadas: **2,3 %**.

## Descargas

- [CSV por municipio](adm2.csv)
- [Mapa PNG](mapa_general.png)

## Procedencia

- ShakeMap consumido: **v8**
- Ground Failure consumido: **v8**
- Manifiesto de exposición: `col-v0.6`
- Pipeline: `0.1.0` · Generado: 2026-09-03T03:25:30Z

## Advertencias

- Exposición estimada, no daño observado.
- Este sistema no es una alerta temprana ni una recomendación de evacuación.
- No reemplaza a los servicios geológicos ni a las unidades de gestión del riesgo.
- Fuentes, vintages y versiones consumidas: ver manifiesto enlazado.
