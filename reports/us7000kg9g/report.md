# Exposición sísmica: M6,6 · 19 km al SE de Loncopué, Argentina

**Evento USGS:** `us7000kg9g` · **Origen:** 2023-07-17T03:05:11Z UTC · **Profundidad:** 186,0 km

> **Reconstrucción retrospectiva.** Este reporte se calculó después del evento, no en respuesta a él, y no cuenta para las métricas de latencia del sistema.
>
> La **población** corresponde a la época indicada en el manifiesto de exposición. Las **edificaciones, vías, sedes de salud y educativas son las actuales**: OpenStreetMap y Overture publican el estado presente, no el histórico. Léelas como "qué infraestructura de hoy caería en esa zona de intensidad", no como lo que había entonces.

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
| 25 km | 7.200 |
| 50 km | 16 mil |
| 100 km | 83 mil |

Los radios **no son bandas de intensidad**. Aquí no hay modelo de sacudida, solo distancia: un sismo superficial y uno profundo de la misma magnitud tienen el mismo circulo y no se parecen en nada. La cifra sirve para dimensionar, no para priorizar.

## Deslizamiento y licuefacción

- **Deslizamiento.** Población en celdas donde el modelo espera ≥ 0,10 de probabilidad de deslizamiento: **0**.
- **Licuefacción.** Población en celdas donde el modelo espera ≥ 0,10 de cobertura areal por licuefacción: **0**.

Las dos cifras se cuentan sobre las celdas del corte publicado (MMI≥6). **No son las de USGS y no se pueden comparar de frente**: aquí se cuenta la población entera de toda celda por encima del umbral, y USGS pondera la población de cada celda por el valor de esa celda. Son dos preguntas distintas sobre el mismo ráster.

Fuente: producto *Ground Failure* de USGS (v11), dominio público.

## Referencia cruzada

PAGER (USGS) estima para este evento una alerta **verde**. CENTINELA no estima víctimas; la cifra se incluye solo como contraste.

Las dos cifras **no se tabulan igual** y no se pueden leer una contra otra: PAGER agrupa por MMI redondeado (su fila «7» es todo lo que cae entre 6,5 y 7,49) y CENTINELA usa bandas literales, donde MMI≥7 es MMI≥7. Puede además que no hablen del mismo ShakeMap: este reporte declara en «Procedencia» qué versión consumió, y PAGER pudo correr sobre otra versión o sobre otro producto del mismo sismo. El contraste banda a banda, hecho y comprobado para el sismo de San José del Palmar, está en `docs/PARA_INSTITUCIONES.md`.

## Incertidumbre y calidad

Discrepancia entre GHS-POP y WorldPop: **no se pudo medir**. Ninguna celda dentro de las bandas publicadas tiene población de WorldPop con la que contrastar.

- El epicentro está a 4 km de la población más cercana del país con la que se comparó. La sacudida no alcanzó territorio habitado.

## Descargas

- [CSV por municipio](adm2.csv)
- [Mapa PNG](mapa_general.png)

## Procedencia

- ShakeMap consumido: **v11**
- Ground Failure consumido: **v11**
- Manifiesto de exposición: `arg-v0.2`
- Pipeline: `0.1.0` · Generado: 2026-09-05T01:25:41Z

## Advertencias

- Exposición estimada, no daño observado.
- Este sistema no es una alerta temprana ni una recomendación de evacuación.
- No reemplaza a los servicios geológicos ni a las unidades de gestión del riesgo.
- Fuentes, vintages y versiones consumidas: ver manifiesto enlazado.
