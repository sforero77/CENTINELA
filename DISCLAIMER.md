# Advertencias · CENTINELA

Este documento es parte del producto, no un anexo legal. Si algo de lo que
sigue deja de ser cierto, el sistema está mal.

## Qué informa CENTINELA

**Exposición estimada.** Cuántas personas, edificaciones, escuelas, hospitales
y kilómetros de vía quedan **dentro** de cada franja de intensidad sísmica
modelada por el ShakeMap de USGS. Es una estimación basada en datos abiertos de
población y edificaciones, cruzada con un modelo de intensidad.

## Qué NO informa

- ❌ **No es alerta temprana.** El reporte se publica *después* del sismo. No
  notifica a la población ni recomienda evacuar.
- ❌ **No estima víctimas.** Eso lo hace PAGER (USGS), y este sistema solo lo referencia.
- ❌ **No dictamina daño.** Exposición no es daño. Una edificación dentro de
  MMI≥7 está *expuesta*; si se dañó o no, este sistema no lo sabe.
- ❌ **No dictamina habitabilidad.** La brigada de imagen produce
  *priorización* para inspección, jamás un veredicto estructural.
- ❌ **No reemplaza** a los servicios geológicos nacionales (SGC, SSN, CSN,
  IGP, IG-EPN, Funvisis) ni a las unidades de gestión del riesgo. Es un insumo
  abierto y complementario.
- ❌ **No maneja datos personales.** Ni desaparecidos, ni censos nominales, ni
  nada que identifique a una persona. Fuera de alcance de forma permanente.

## Limitaciones conocidas que se publican en cada reporte

1. **Población modelada, no censal.** GHS-POP es un producto derivado. La banda
   de discrepancia contra WorldPop se publica en cada reporte precisamente para
   que el lector vea el tamaño de la incertidumbre.
2. **Dos modelos de población en la misma celda.** Los totales vienen de
   GHS-POP y el desglose por edad de WorldPop age-sex R2025A, época 2025 —no de
   una estructura de 2020 proyectada, como decía esta limitación hasta el
   1-sep-2026. Los extremos (0-14 y 65+) son conteos de WorldPop; la banda
   central de 15-64 es el residuo de `pop_total`, así que absorbe la diferencia
   entre ambos modelos. La banda de discrepancia publicada acota ese desvío.
3. **Huecos de edificaciones.** Overture y OSM tienen cobertura desigual en
   asentamientos informales y zona rural dispersa. Las celdas sospechosas se
   marcan en `flags_calidad` —`revisar_sin_edificios`, `construido_no_mapeado`,
   `discrepancia_poblacional`— y se publican así: **nunca se oculta el vacío**.
4. **ShakeMap versionado.** Las cifras cambian entre versiones del ShakeMap.
   Cada reporte declara que versión consumió, y se re-emite con changelog
   cuando aparece una nueva.
5. **Latencia dependiente de terceros, y hoy por encima del objetivo.** La
   detección la dispara un cron externo cada cinco minutos; el cron de GitHub
   Actions —con demoras documentadas de 5 a 30 minutos— queda como respaldo.
   Sobre los dos primeros sismos en vivo, del 2-sep-2026, la latencia de punta
   a punta medida es **p50 92,1 min**, más del doble del objetivo de 60. La
   detección no es el cuello de botella —veintitantos minutos, la mayor parte
   esperando a que USGS liste el evento—: lo que se lleva el resto es esperar
   el ShakeMap, que publica USGS y no depende de este sistema. Las dos cifras,
   con su fecha, están en `/status`.

## Cómo citar una cifra de este sistema

Siempre con las tres cosas: el número, la versión de ShakeMap que lo produjo, y
la palabra **expuesta**.

> «Según CENTINELA, unas 350 mil personas se encontraban en zonas de intensidad
> MMI≥7 (ShakeMap v3). Es exposición estimada, no un conteo de afectados.»
