# Exposición sísmica: M5,8 · 79 km al OSO de Changuillo, Perú

**Evento USGS:** `us7000ty1a` · **Origen:** 2026-11-13T16:43:02Z UTC · **Profundidad:** 10,0 km

## Exposición estimada

| Indicador | Estimado |
|---|---:|
| Población en MMI≥6 | el evento no llegó a esta banda |
| Población en MMI≥7 | el evento no llegó a esta banda |
| Población en MMI≥8 | el evento no llegó a esta banda |
| Edificaciones en MMI≥6 | 0 |
| Sedes de salud en MMI≥6 | 0 |
| Sedes educativas en MMI≥6 | 0 |
| Kilómetros de vía en MMI≥6 | 0 km |

> **Todas las cifras en cero es un resultado, no un fallo.** El ShakeMap de este evento sí dibuja intensidad, pero no alcanza MMI≥6 sobre territorio habitado del país: la sacudida quedó mar adentro o sobre zona despoblada. El cálculo corrió entero.

Las cifras de esta tabla van redondeadas a dos cifras significativas, que es la precisión que un modelo de exposición sostiene. Las exactas están en el CSV municipal y en `report.json`.

### Población por distancia al epicentro

Ninguna banda de intensidad alcanza población, así que la única cifra que dimensiona este evento es la distancia:

| Radio desde el epicentro | Población |
|---|---:|
| 25 km | 0 |
| 50 km | 510 |
| 100 km | 89 mil |

Los radios **no son bandas de intensidad**. Aquí no hay modelo de sacudida, solo distancia: un sismo superficial y uno profundo de la misma magnitud tienen el mismo circulo y no se parecen en nada. La cifra sirve para dimensionar, no para priorizar.

## Deslizamiento y licuefacción

- **Deslizamiento.** Población en celdas de MMI≥6 donde el modelo espera ≥ 0,10 de probabilidad de deslizamiento según `jessee_2018_model.tif`: **0**.
- **Licuefacción.** Población en celdas de MMI≥6 donde el modelo espera ≥ 0,10 de cobertura areal por licuefacción según `zhu_2017_general_model.tif`: **0**.

Las dos cifras se cuentan sobre las celdas del corte publicado (MMI≥6). **No son las de USGS y no se pueden comparar de frente**: aquí se cuenta la población entera de toda celda por encima del umbral, y USGS pondera la población de cada celda por el valor de esa celda. Son dos preguntas distintas sobre el mismo ráster.

**Y el umbral se evalúa en un solo punto por celda: su centroide.** El píxel del ráster es más pequeño que la celda, así que ese punto decide si entra la población entera de la celda o no entra ninguna. No es una estadística areal, y el sesgo que introduce no está medido: puede quedarse corto o pasarse.

Fuente: producto *Ground Failure* de USGS (v1), dominio público.

## Incertidumbre y calidad

Discrepancia entre GHS-POP y WorldPop: **no se pudo medir**. Ninguna celda dentro de las bandas publicadas tiene población de WorldPop con la que contrastar.

- El epicentro está a 28 km de la población más cercana del país con la que se comparó. La sacudida no alcanzó territorio habitado.

## Cambios frente a la versión anterior

- Ground Failure: v0 → v1 (us)
- Ninguna cifra publicada cambia frente a la versión anterior.

## Descargas

- [CSV por municipio](adm2.csv)
- [Mapa PNG](mapa_general.png)

## Procedencia

- ShakeMap consumido: **v1** de `us`
- Ground Failure consumido: **v1** de `us`
- Manifiesto de exposición: [`per-v0.5`](https://github.com/sforero77/CENTINELA/blob/main/data/manifests/PER.yaml)
- Pipeline: `0.1.0` · Generado: 2026-11-13T17:11:04Z

## Advertencias

- Exposición estimada, no daño observado.
- Este sistema no es una alerta temprana ni una recomendación de evacuación.
- No reemplaza a los servicios geológicos ni a las unidades de gestión del riesgo.
- Fuentes, vintages y versiones consumidas: ver manifiesto enlazado.
