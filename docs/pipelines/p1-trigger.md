# P1 — Trigger

**Qué hace:** vigila el feed de USGS, decide qué merece un reporte, y deja
constancia de todo lo que vio.
**Cadencia:** cada 5 minutos.
**Comando:** `uv run centinela trigger [--dry-run]`
**Código:** `pipelines/p1_trigger/` (feed, filters, observados, run)

## El flujo

```mermaid
flowchart TB
  START(["corrida"]) --> F1["GET 4.5_hour"]
  START --> F2["GET 4.5_day<br/><i>respaldo</i>"]
  F1 --> DEDUP{"¿ya visto<br/>en esta corrida?"}
  F2 --> DEDUP
  DEDUP -->|sí| SKIP["descartar duplicado"]
  DEDUP -->|no| FILTRO["<b>evaluate()</b>"]

  FILTRO --> C1{"tipo == earthquake?"}
  C1 -->|no| OUT1["razón:<br/>tipo no sísmico"]
  C1 -->|sí| C2{"mag ≥ 5,5?"}
  C2 -->|no| OBS["<b>observado</b><br/>razón: M4.7 &lt; umbral M5.5"]
  C2 -->|sí| C3{"dentro del<br/>bbox LATAM?"}
  C3 -->|no| OUT2["razón:<br/>fuera del bbox"]
  C3 -->|sí| REL["<b>relevante</b>"]

  REL --> EST{"¿existe<br/>events/&lt;id&gt;.json?"}
  EST -->|no| NUEVO["nuevos[]"]
  EST -->|sí, no terminal| REVIS["revisitados[]<br/><i>por si hay versión nueva</i>"]
  EST -->|sí, descartado| NADA["no se re-despacha"]

  NUEVO --> DESP["despachar a P2"]
  REVIS --> DESP
  OBS --> PUBOBS[/"site/observados.json"/]

  style REL fill:#e8f0ea,stroke:#0f5636,color:#1c1b1a
  style OBS fill:#f4f1e8,stroke:#8a8578,color:#1c1b1a
```

## El filtro, en tres condiciones

`pipelines/p1_trigger/filters.py` — todas explícitas y testeables sin red:

```python
if candidate.tipo != "earthquake":        # explosiones, hielo, ruido
    return RelevanceDecision(False, f"tipo no sismico: {candidate.tipo}")
if candidate.mag < MIN_MAGNITUDE:         # 5.5
    return RelevanceDecision(False, f"M{candidate.mag} < umbral M{MIN_MAGNITUDE}")
if not bbox.contains(candidate.lon, candidate.lat):
    return RelevanceDecision(False, "fuera del bbox LATAM")
return RelevanceDecision(True, "dentro de alcance")
```

La decisión **siempre lleva su razón**, y esa razón se publica. El umbral M5,5
es la defensa principal contra el riesgo de "falso disparo / cifra alarmista"
del registro de riesgos (§7).

## Por qué dos feeds

| Feed | Papel |
|---|---|
| `4.5_hour` | El camino crítico. Ligero, se consulta primero |
| `4.5_day` | El respaldo. Cubre la demora del cron |

GitHub documenta demoras de 5 a 30 minutos en los crons programados —y este
repositorio ha medido hasta **12,8 horas**. Si el runner despierta tarde, el
feed horario ya no alcanza; el diario garantiza que no se pierda nada. Los
duplicados se descartan por `usgs_id`.

> `USGS_FDSN_EVENT` existe en las constantes pero **está prohibido en el camino
> crítico**: sólo para backtests e históricos. El propio USGS desaconseja el
> polling a FDSN para aplicaciones automatizadas (D7).

## Los observados: la prueba de que el vigía miró

Un sismo M4,7 en Chile no genera reporte. Pero si no se publicara en ningún
lado, nadie podría distinguir "el vigía miró y decidió que no" de "el vigía
estaba caído".

```json
{"usgs_id": "us7000tcwp", "mag": 4.7, "lon": -70.4392, "lat": -22.1794,
 "depth_km": 52.1, "lugar": "26 km al OSO de Tocopilla, Chile",
 "origen_utc": "2026-08-30T05:19:51Z", "razon": "M4.7 < umbral M5.5"}
```

Ventana móvil de 5 días. El visor los dibuja como estrellas huecas, con la
etiqueta *"Sismo visto, sin reporte — por debajo de M5,5. Se vio y no se midió
su impacto"*.

## Idempotencia (RF-02)

Correr P1 dos veces sobre el mismo feed no crea trabajo duplicado. El estado
vive en `events/<usgs_id>.json` y sólo `descartado` es terminal: un evento ya
publicado se **revisita** en cada corrida por si USGS sacó un ShakeMap nuevo,
y es P2 quien decide si hay trabajo real.

## La salida

```json
{"msg": "latido del trigger", "revisados": 14, "relevantes": 0,
 "observados": 2, "nuevos": [], "revisitados": [],
 "latido_utc": "2026-08-30T14:41:28Z"}
```

`--dry-run` corre todo esto pero no escribe `event_state`: es lo que usa el
simulacro mensual.
