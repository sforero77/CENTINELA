# Golden tests

Pruebas de regresión contra eventos reales congelados. Corren en cada PR (§6.3).

| Id | Evento | `usgs_id` | Estado |
|---|---|---|---|
| G1 | Chocó, M7.4, 10-ago-2026 | `us6000tjl2` | ✅ corre |
| G2 | Venezuela, doble mainshock, 24-jun-2026 | `us6000t7zp`, `us6000t7zc` | ✅ corre |
| G3 | Evento sin Ground Failure publicado | sintético | ✅ corre |
| G4 | Chocó, recalculado desde sus insumos | `us6000tjl2` | ✅ corre (extra `geo`) |

## Qué fija cada uno

**G1 — Chocó.** Que el trigger habría disparado (verificado contra el evento
real), los datos del evento, que se elige la versión vigente del ShakeMap entre
las siete congeladas, y que un estado atrasado dispara re-emisión mientras uno
al día no (RF-04). Además, las aserciones (b) y (c) contra el `report.json`
publicado: `pop_mmi7p` estable ±0,5 % y el top-15 municipal estable. El ancla
lleva la versión de ShakeMap a la que corresponde (`SHAKEMAP_DEL_ANCLA`): si el
reporte se re-emite con otra, la prueba pide reanclar en vez de comerse la
tolerancia con un insumo nuevo.

**G2 — Venezuela.** Lo mismo, más el **evento doble**: dos mainshocks separados
por 32,2 segundos y 145 km deben producir dos `event_state` y dos reportes, nunca
uno tratado como réplica del otro. Incluye la regresión del bug de selección de
versión que esta fixture destapó, y la aserción (b) sobre los dos reportes
publicados.

**G3 — Sin Ground Failure.** Que el reporte omite la sección con nota explícita
y no falla. Ojo: la espec v0.9 lo describía como «evento profundo», pero Chocó
fue a 110 km y sí tiene Ground Failure — la profundidad no es el criterio.

**G4 — El que recalcula.** G1 y G2 comprueban que el artefacto publicado no
derive; G4 comprueba que el **código** no mueva una cifra. Corre la cadena
entera —contornos, activo, impacto, reporte, `report.json`— contra
`cont_mmi_v7.json` y `exposure_recortado.parquet`, y fija las cifras nacionales
y el top-15 con sus decimales.

## Lo que decía este documento y ya no es cierto

Hasta el 3-oct-2026 aquí ponía que (b) y (c) estaban saltadas a la espera del
activo de Colombia, y que faltaba congelar los contenidos de los productos. Lo
comprobó la auditoría del 5-sep (hallazgo 187) y ninguna de las dos cosas era
verdad:

- (b) y (c) corren contra los reportes publicados. Solo se saltan **solas** si
  falta el `report.json` del evento, que es la forma de que un evento nuevo no
  necesite que alguien recuerde quitar un decorador.
- `cont_mmi_v7.json` está congelado y lo leen G1 y G4. Los rásteres de Ground
  Failure no se congelan, y es a propósito: ninguna prueba los lee, y
  `.gitignore` descarta todos los `.tif` del repositorio.

## Cómo congelar

`scripts/freeze_event.py` escribe los ficheros que leen estas pruebas, con sus
nombres; el activo recortado de G4 sale de `scripts/fixture_golden.py`. Ver
`tests/fixtures/golden/README.md` para los comandos, por qué se recortan y por
qué el feed se reconstruye con una consulta FDSN y no con el detail del evento.
