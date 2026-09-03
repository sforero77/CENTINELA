# El viaje del dato

Dos caminos distintos comparten el mismo denominador. Este documento sigue
ambos hasta el píxel.

## Camino A — un sismo, de la fuente al reporte

```mermaid
sequenceDiagram
  autonumber
  participant CRON as Cron externo<br/>(cada 5 min desde el 31-ago-2026)
  participant GH as GitHub Actions
  participant P1 as P1 trigger
  participant USGS as USGS
  participant P2 as P2 impacto
  participant P3 as P3 reporte
  participant PAGES as GitHub Pages

  CRON->>GH: POST /dispatches {"event_type":"vigilar"}
  GH->>P1: trigger.yml
  P1->>USGS: GET 4.5_hour + 4.5_day (GeoJSON)
  USGS-->>P1: candidatos
  Note over P1: filtro: tipo=earthquake<br/>M ≥ 5,5 · dentro del bbox LATAM
  P1->>P1: dedupe contra events/[usgs_id].json
  alt hay evento nuevo o revisitado
    P1->>GH: gh workflow run impact.yml -f usgs_id=…
    GH->>P2: impact.yml
    P2->>USGS: detail → ShakeMap (cont_mmi) + Ground Failure
    Note over P2: contornos MMI → celdas H3 r8<br/>⋈ activo del país<br/>muestreo de licuefacción/deslizamiento
    P2->>P3: Report (modelo validado)
    P3->>P3: report.json · md · adm2.csv · celdas.json<br/>contornos.json · 2 mapas PNG · hilo.txt
    P3->>PAGES: commit + gh workflow run site.yml
  else nada relevante
    P1->>PAGES: sólo latido y observados
  end
```

**La decisión que evita el falso disparo** está en tres condiciones explícitas
y testeables sin red (`pipelines/p1_trigger/filters.py`): es un terremoto (no
explosión ni evento de hielo), es M ≥ 5,5, y cae dentro de la ventana LATAM.
El umbral de magnitud es la defensa principal contra la "cifra alarmista" del
registro de riesgos.

**Por qué dos feeds.** `4.5_hour` es el feed del camino crítico. `4.5_day` es
el respaldo: GitHub documenta demoras de 5 a 30 minutos en los crons
programados, y si el runner despierta tarde el feed horario ya no alcanza.
Los duplicados entre ambos se descartan por `usgs_id`.

## Camino B — el fuego, cada seis horas

```mermaid
flowchart LR
  F1[("FIRMS<br/>3 satélites VIIRS<br/>× 2 regiones")] -->|"CSV 24 h<br/>sin MAP_KEY"| F2["parseo<br/>detecciones"]
  F2 --> F3["agregación<br/>a celda H3 r8"]
  F3 --> F4{"⋈ activo<br/>de exposición"}
  F4 --> F5["recorte<br/>4.000 celdas"]
  F5 --> F6[/"site/incendios.json"/]
  F6 --> F7(["Visor · modo Fuego"])

  style F4 fill:#f4e8e8,stroke:#8c1d64,color:#1c1b1a
```

Lo que se cuenta son **detecciones, no incendios**: los tres satélites
sobrevuelan el mismo fuego y producen tres filas. Medido el 26-ago-2026, antes
del pico de temporada: 66.806 detecciones en 24 h → 22.701 celdas, o sea 2,9
detecciones por celda. Llamarlas "focos" invitaría a leer el número como
cantidad de fuegos, que es el triple de los que hay.

**El recorte a 4.000 celdas** no es por potencia: entran primero todas las que
tienen gente debajo, ordenadas por población, y el resto se rellena por
potencia radiativa. El visor lo dice con esas palabras porque durante un tiempo
dijo otra cosa —"las 4.000 celdas de mayor energía"— y era falso.

## El denominador común

```mermaid
flowchart TB
  subgraph activo["Activo de exposición · H3 r8 · trimestral"]
    AC["<b>exposure_h3</b><br/>pop_total · pop_0_14 · pop_15_64 · pop_65p<br/>bld_count · built_m2 · road_km_*<br/>health_count · edu_count · lulc_*"]
  end

  SISMO["Contornos MMI<br/>de ShakeMap"] --> J1{"⋈ celda"}
  FUEGO["Detecciones<br/>VIIRS"] --> J2{"⋈ celda"}
  AC --> J1
  AC --> J2
  J1 --> R1["Personas en MMI ≥ 7<br/>edificaciones · vías · sedes"]
  J2 --> R2["Personas en celdas<br/>con fuego activo"]

  style activo fill:#e8f0ea,stroke:#0f5636,color:#1c1b1a
```

Este es el motivo de que el visor tenga un selector de amenaza y no dos mapas:
cambia la amenaza, no el denominador. Cualquier amenaza futura que sepa
resolverse a celda H3 —inundación, ceniza volcánica— entra por el mismo join.

## Qué se dispara con qué reloj

| Pipeline | Cadencia | Quién lo dispara |
|---|---|---|
| **P1 trigger** | cron GH `*/30` | el cron externo → `repository_dispatch` está declarado y sin conectar; lo que corre hoy es el interno |
| **P2 + P3** | por evento | el propio P1, cuando el filtro deja pasar algo |
| **P5 incendios** | cada 6 h | cron propio, y P1 lo despierta si lleva más de 6 h |
| **Frescura** | cada 3 h | cron propio, y P1 lo despierta si lleva más de 3 h |
| **Deriva de contrato** | diaria, 08:00 UTC | cron |
| **Simulacro** | mensual, día 5 | cron |
| **Keepalive** | días 1 y 15 | cron |
| **P0 exposición** | trimestral | cron (1 de ene, abr, jul, oct) |

El detalle de cada reloj y de quién lo dispara está en
[`../acciones/`](../acciones/).
