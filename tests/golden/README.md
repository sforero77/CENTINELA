# Golden tests

Pruebas de regresion contra eventos reales congelados. Corren en cada PR (§6.3).

| Id | Evento | `usgs_id` | Estado |
|---|---|---|---|
| G1 | Chocó, M7.4, 10-ago-2026 | `us6000tjl2` | ✅ corre |
| G2 | Venezuela, doble mainshock, 24-jun-2026 | `us6000t7zp`, `us6000t7zc` | ✅ corre |
| G3 | Evento sin Ground Failure publicado | sintetico | ✅ corre |

## Que fija cada uno

**G1 — Chocó.** Que el trigger habria disparado (verificado contra el evento
real), los datos del evento, que se elige la version vigente del ShakeMap entre
las siete congeladas, y que un estado atrasado dispara re-emision mientras uno
al dia no (RF-04).

**G2 — Venezuela.** Lo mismo, mas el **evento doble**: dos mainshocks separados
por 32,2 segundos y 145 km deben producir dos `event_state` y dos reportes, nunca
uno tratado como replica del otro. Incluye la regresion del bug de seleccion de
version que esta fixture destapo.

**G3 — Sin Ground Failure.** Que el reporte omite la seccion con nota explicita
y no falla. Ojo: la espec v0.9 lo describia como «evento profundo», pero Chocó
fue a 110 km y si tiene Ground Failure — la profundidad no es el criterio.

## Lo que sigue pendiente

Las aserciones (b) `pop_mmi7p` estable ±0.5% y (c) top-15 municipios estable
estan marcadas `skip` con razon: **necesitan el activo `exposure_h3` de
Colombia**, que es P0 (Fase 0, semana 2). No estan bloqueadas por fixtures.

Falta tambien congelar los **contenidos** de los productos —`cont_mmi.json` y
los rasters de Ground Failure— que necesitara el polyfill H3. Las fixtures
actuales congelan la estructura de productos y su historial de versiones, que
es lo que el contrato de P2 consume hoy.

## Como congelar

Ver `tests/fixtures/golden/README.md`: comandos exactos, por que se recortan de
8,4 MB a 244 KB, y por que el feed se reconstruye con una consulta FDSN y no con
el detail del evento.
