# Exposición sísmica: M6,0 · 7 km al N de La Tronosa, Panamá

**Evento USGS:** `us6000u1cf` · **Origen:** 2026-10-10T04:14:01Z UTC · **Profundidad:** 10,0 km

## Exposición estimada

| Indicador | Estimado |
|---|---:|
| Población en MMI≥6 | 12 mil |
| Población en MMI≥7 | 1.500 |
| Población en MMI≥8 | el evento no llegó a esta banda |
| Edificaciones en MMI≥7 | 1.000 |
| Sedes de salud en MMI≥7 | 0 |
| Sedes educativas en MMI≥7 | 1 |
| Vías primarias y secundarias en MMI≥7 | 16 km |
| Vías locales en MMI≥7 | 48 km |
| Superficie construida en MMI≥7 | 0,2 km² |

El satélite detecta **1,7 veces** más superficie construida de la que explicarían las 1.000 edificaciones registradas en MMI≥7. La diferencia suele ser asentamiento informal o zona rural dispersa sin mapear: **el conteo de edificaciones se queda corto ahí, y la superficie construida no**.

Las cifras de esta tabla van redondeadas a dos cifras significativas, que es la precisión que un modelo de exposición sostiene. Las exactas están en el CSV municipal y en `report.json`.

De la población en intensidad MMI≥7, alrededor de **290** personas tienen 65 años o más.

## Municipios más expuestos, por población en MMI≥7

| # | Municipio | Código | MMI max | Población MMI≥7 |
|---:|---|---|---:|---:|
| 1 | Tonosí | `PA0907` | 7,0 | 1.300 |
| 2 | Macaracas | `PA0904` | 7,0 | 150 |

## Deslizamiento y licuefacción

USGS no ha publicado el producto *Ground Failure* para este evento. La sección se omite; el reporte se re-emite automáticamente si aparece.

## Referencia cruzada

PAGER (USGS) estima para este evento una alerta **amarilla**. CENTINELA no estima víctimas; la cifra se incluye solo como contraste.

Las dos cifras **no se tabulan igual** y no se pueden leer una contra otra: PAGER agrupa por MMI redondeado (su fila «7» es todo lo que cae entre 6,5 y 7,49) y CENTINELA usa bandas literales, donde MMI≥7 es MMI≥7. Puede además que no hablen del mismo ShakeMap: este reporte declara en «Procedencia» qué versión consumió, y PAGER pudo correr sobre otra versión o sobre otro producto del mismo sismo. El contraste banda a banda, hecho y comprobado para el sismo de San José del Palmar, está en `docs/PARA_INSTITUCIONES.md`.

## Incertidumbre y calidad

Discrepancia entre GHS-POP y WorldPop en las bandas MMI publicadas: **17,7 %**.

## Cambios frente a la versión anterior

- ShakeMap: v0 → v1 (us)
- Población en MMI≥6: 0 → 12 mil
- Población en MMI≥7: 0 → 1.500
- Población de 65 años o más en MMI≥7: 0 → 290
- Edificaciones en MMI≥7: 0 → 1.000
- Sedes educativas en MMI≥7: 0 → 1

## Descargas

- [CSV por municipio](adm2.csv)
- [Mapa PNG](mapa_general.png)

## Procedencia

- ShakeMap consumido: **v1** de `us`
- Ground Failure consumido: **ninguno** (no publicado aún)
- Manifiesto de exposición: [`pan-v0.4`](https://github.com/sforero77/CENTINELA/blob/main/data/manifests/PAN.yaml)
- Pipeline: `0.1.0` · Generado: 2026-10-10T04:35:55Z

## Advertencias

- Exposición estimada, no daño observado.
- Este sistema no es una alerta temprana ni una recomendación de evacuación.
- No reemplaza a los servicios geológicos ni a las unidades de gestión del riesgo.
- Fuentes, vintages y versiones consumidas: ver manifiesto enlazado.
