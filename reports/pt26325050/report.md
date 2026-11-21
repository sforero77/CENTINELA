# Exposición sísmica: M6,7 · 9 km al NE de Carhuamayo, Perú

**Evento USGS:** `pt26325050` · **Origen:** 2026-11-21T00:09:17Z UTC · **Profundidad:** 108,0 km

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

> **Todas las cifras en cero es un resultado, no un fallo.** El ShakeMap sí alcanza territorio habitado del país, con intensidad máxima **MMI 5,5** sobre municipio. Este sistema publica cifras desde MMI≥6, así que por debajo de ese umbral las tablas van en cero. El cálculo corrió entero.

Las cifras de esta tabla van redondeadas a dos cifras significativas, que es la precisión que un modelo de exposición sostiene. Las exactas están en el CSV municipal y en `report.json`.

### Población por distancia al epicentro

Ninguna banda de intensidad alcanza población, así que la única cifra que dimensiona este evento es la distancia:

| Radio desde el epicentro | Población |
|---|---:|
| 25 km | 36 mil |
| 50 km | 190 mil |
| 100 km | 690 mil |

Los radios **no son bandas de intensidad**. Aquí no hay modelo de sacudida, solo distancia: un sismo superficial y uno profundo de la misma magnitud tienen el mismo circulo y no se parecen en nada. La cifra sirve para dimensionar, no para priorizar.

## Municipios más expuestos, por población en MMI≥6

Ningún municipio del país alcanza población dentro de MMI≥6. No es que falte el dato: la intensidad que el ShakeMap dibuja para este evento no llega a esa banda sobre territorio habitado.

## Deslizamiento y licuefacción

- **Deslizamiento.** Población en celdas de MMI≥6 donde el modelo espera ≥ 0,10 de probabilidad de deslizamiento según `jessee_2018_model.tif`: **0**.
- **Licuefacción.** Población en celdas de MMI≥6 donde el modelo espera ≥ 0,10 de cobertura areal por licuefacción según `zhu_2017_general_model.tif`: **0**. USGS declara para este evento alerta **amarilla**, con 300 expuestas. El cero de arriba no dice que no haya exposición: dice que ninguna celda llega al umbral.

Las dos cifras se cuentan sobre las celdas del corte publicado (MMI≥6). **No son las de USGS y no se pueden comparar de frente**: aquí se cuenta la población entera de toda celda por encima del umbral, y USGS pondera la población de cada celda por el valor de esa celda. Son dos preguntas distintas sobre el mismo ráster.

**Y el umbral se evalúa en un solo punto por celda: su centroide.** El píxel del ráster es más pequeño que la celda, así que ese punto decide si entra la población entera de la celda o no entra ninguna. No es una estadística areal, y el sesgo que introduce no está medido: puede quedarse corto o pasarse.

Fuente: producto *Ground Failure* de USGS (v2), dominio público.

## Referencia cruzada

PAGER (USGS) estima para este evento una alerta **verde**. CENTINELA no estima víctimas; la cifra se incluye solo como contraste.

Las dos cifras **no se tabulan igual** y no se pueden leer una contra otra: PAGER agrupa por MMI redondeado (su fila «7» es todo lo que cae entre 6,5 y 7,49) y CENTINELA usa bandas literales, donde MMI≥7 es MMI≥7. Puede además que no hablen del mismo ShakeMap: este reporte declara en «Procedencia» qué versión consumió, y PAGER pudo correr sobre otra versión o sobre otro producto del mismo sismo. El contraste banda a banda, hecho y comprobado para el sismo de San José del Palmar, está en `docs/PARA_INSTITUCIONES.md`.

## Incertidumbre y calidad

Discrepancia entre GHS-POP y WorldPop: **no se pudo medir**. Ninguna celda dentro de las bandas publicadas tiene población de WorldPop con la que contrastar.

## Cambios frente a la versión anterior

- ShakeMap: v1 (us) → v2 (us)
- Ground Failure: v1 (us) → v2 (us)
- Ninguna cifra publicada cambia frente a la versión anterior.
- ShakeMap: v0 → v1 (us)
- Ground Failure: v0 → v1 (us)
- Ninguna cifra publicada cambia frente a la versión anterior.

## Descargas

- [CSV por municipio](adm2.csv)
- [Mapa PNG](mapa_general.png)

## Procedencia

- ShakeMap consumido: **v2** de `us`
- Ground Failure consumido: **v2** de `us`
- Manifiesto de exposición: [`per-v0.5`](https://github.com/sforero77/CENTINELA/blob/main/data/manifests/PER.yaml)
- Pipeline: `0.1.0` · Generado: 2026-11-21T02:31:03Z

## Advertencias

- Exposición estimada, no daño observado.
- Este sistema no es una alerta temprana ni una recomendación de evacuación.
- No reemplaza a los servicios geológicos ni a las unidades de gestión del riesgo.
- Fuentes, vintages y versiones consumidas: ver manifiesto enlazado.
