# Cada reloj, de principio a fin

Los otros documentos de esta carpeta explican **por qué** cada workflow está
escrito como está: el latido que no se publicaba, las diecisiete horas del
visor congelado, la trampa del `GITHUB_TOKEN`. Este explica otra cosa, y es la
que hace falta a las tres de la mañana: **qué corre, qué comprueba, y qué pasa
cuando la comprobación dice que no**.

Un diagrama por disparador. Catorce workflows y nueve relojes.
Cada diagrama lleva sus puertas de decisión, sus códigos de salida y quién
recibe la alarma.

Las puertas rojas detienen o avisan; las verdes son el camino que publica.

## Los nueve relojes

| Reloj | UTC | Workflow | Qué comprueba | Si falla |
|---|---|---|---|---|
| `repository_dispatch` cada 5 min | continuo | `trigger.yml` | ¿Hay un sismo M≥5,5 en LATAM? | healthchecks.io a los 30 min sin latido |
| `*/30 * * * *` | cada 30 min | `trigger.yml` | Lo mismo, de respaldo | — |
| `17 */3 * * *` | cada 3 h | `frescura.yml` | ¿La página sirve lo que hay en el repo? | Republica e informa en una incidencia |
| `40 */6 * * *` | cada 6 h | `incendios.yml` | Focos VIIRS de las últimas 24 h | La corrida sale roja |
| `37 5 * * *` | 05:37 diario | `repaso.yml` | ¿Hay versión de producto más nueva a 90 días? | Código 1 si fallaron **todos** |
| `0 8 * * *` | 08:00 diario | `contract_drift.yml` | ¿Derivaron los contratos de las fuentes? | Incidencia automática |
| `23 7 * * 1` | lunes 07:23 | `rezago.yml` | ¿Algún reporte publicado quedó atrás? | Informa; rezago **no** es fallo |
| `0 9 5 * *` | día 5, 09:00 | `simulacro.yml` | Que el pipeline no se oxide entre catástrofes | Incidencia automática |
| `0 7 1,15 * *` | días 1 y 15 | `keepalive.yml` | Que GitHub no apague los crons | — |
| `0 6 1 1,4,7,10 *` | trimestral | `exposure_quarterly.yml` | Reconstruye el activo de cada país | Incidencia **por país** |

Y cinco disparadores que no son reloj: `impact.yml` y `site.yml` (los llama
otro workflow), `ci.yml` y `visor.yml` (push y PR), `contraste.yml` (a mano).

```mermaid
timeline
  title Un día del sistema, en UTC
  section Relojes fijos
    05h37 : repaso.yml — RF-04 a 90 días
    06h00 : exposure_quarterly.yml — sólo 1 ene/abr/jul/oct
    07h00 : keepalive.yml — sólo días 1 y 15
    07h23 : rezago.yml — sólo lunes
    08h00 : contract_drift.yml — contratos de fuentes
    09h00 : simulacro.yml — sólo día 5
  section Relojes continuos
    cada 5 min : trigger.yml por repository_dispatch
    cada 30 min : trigger.yml por cron de GitHub, de respaldo
    cada 3 h : frescura.yml, al minuto 17
    cada 6 h : incendios.yml, al minuto 40
```

Las horas están repartidas a propósito y ninguna cae en punta: un cron a las
`0 0` compite con todos los repositorios del planeta y GitHub concede los
programados según carga. Ver [`el-vigia.md`](el-vigia.md).

---

## `trigger.yml` · el vigía

Cada 5 minutos por `repository_dispatch`, cada 30 por el cron de GitHub. Es el
único que corre siempre, y el reloj del que cuelgan otros tres.

El filtro de relevancia son **tres condiciones**, y las tres son la defensa
contra el riesgo número uno del proyecto: publicar una cifra alarmista por un
evento que no lo merecía.

```mermaid
flowchart TB
  D5(["repository_dispatch · 5 min"]) --> GUARD
  C30(["cron GitHub · 30 min · respaldo"]) -.-> GUARD

  GUARD{"github.repository<br/>== sforero77/CENTINELA?"}
  GUARD -->|no| FORK(["fin · un fork no despacha reportes"])
  GUARD -->|sí| FEED["<b>centinela trigger</b><br/>GET 4.5_hour + 4.5_day<br/>deduplicados"]

  FEED --> CONTR{"¿el feed cumple<br/>su contrato?"}
  CONTR -->|no| DEG["FeedContractError<br/>degrada, no publica basura"]
  CONTR -->|sí| F1

  F1{"tipo == earthquake?"}
  F1 -->|no| OBS["a observados.json<br/>con la razón"]
  F1 -->|sí| F2{"M &gt;= 5,5?"}
  F2 -->|no| OBS
  F2 -->|sí| F3{"dentro del bbox LATAM<br/>lon -119..-32 · lat -57,5..33?"}
  F3 -->|no| OBS
  F3 -->|sí| NUEVO{"¿ya tiene<br/>event_state?"}

  NUEVO -->|no| CREA["crear event_state<br/>estado: detectado"]
  NUEVO -->|"sí, y USGS lo actualizó"| REVIS["revisitado"]
  NUEVO -->|"sí, sin cambios"| NADA["ni nuevo ni revisitado"]

  CREA --> HAY
  REVIS --> HAY
  HAY["hay_trabajo = true"] --> JOB2["<b>job: despachar</b><br/>gh workflow run impact.yml<br/>uno por usgs_id"]

  FEED --> EDAD["<b>Despacho por edad</b><br/>gh run list --limit 1"]
  EDAD --> E1{"frescura.yml<br/>&gt; 3 h?"}
  EDAD --> E2{"incendios.yml<br/>&gt; 6 h?"}
  EDAD --> E3{"repaso.yml<br/>&gt; 24 h?"}
  E1 -->|sí| DISP1["despachar"]
  E2 -->|sí| DISP2["despachar"]
  E3 -->|sí| DISP3["despachar"]

  OBS --> EST
  NADA --> EST
  EST["<b>centinela observados + status</b><br/>site/observados.json<br/>site/status.json"] --> FRENO{"¿hubo evento,<br/>o pasó 1 h<br/>desde el último latido?"}
  FRENO -->|no| SINCOMMIT["sin commit<br/><i>288 al día serían ilegibles</i>"]
  FRENO -->|sí| COMMIT["commit del latido"]
  COMMIT --> SITE["gh workflow run site.yml"]

  EST --> HC["curl healthchecks.io<br/><i>se ejecuta pase lo que pase</i>"]

  style FEED fill:#e8f0ea,stroke:#0f5636,color:#1c1b1a
  style JOB2 fill:#e8f0ea,stroke:#0f5636,color:#1c1b1a
  style DEG fill:#f4e8e8,stroke:#8c1d64,color:#1c1b1a
  style FORK fill:#f4f1e8,stroke:#8a8578,color:#1c1b1a
```

Un fallo al despachar **no tumba al vigía**: se avisa con `::warning::` y la
corrida sigue, porque su trabajo —revisar el feed y commitear— ya está hecho.
El porqué de cada una de esas decisiones está en [`el-vigia.md`](el-vigia.md).

---

## `impact.yml` · P2 y P3, el camino crítico

No tiene reloj: lo despacha el vigía, o `repaso.yml`, o `rezago.yml`, o una
persona. Es lo que mide el objetivo de latencia.

Su validación más rara es la del **país**: un sismo no trae el suyo en el feed,
las cajas envolventes se solapan y ordenarlas por área no basta —la de Chile
mide 1.719 grados cuadrados por Rapa Nui—, así que el desempate real lo da el
join y hay que poder reintentar con el candidato siguiente.

```mermaid
flowchart TB
  IN(["repository_dispatch centinela-evento<br/>· workflow_dispatch<br/>con usgs_id"]) --> SETUP["checkout + uv sync<br/>--extra geo --extra render"]
  SETUP --> CAND["<b>centinela paises-candidatos</b><br/>ISO3 ordenados por el epicentro"]

  CAND --> SALIDA4{"código 4:<br/>¿fuera de toda<br/>caja de país?"}
  SALIDA4 -->|sí| MAR["<b>centinela sin-pais</b><br/>se cierra y queda en observados"]
  SALIDA4 -->|no| LOOP

  LOOP["<b>por cada ISO3 candidato</b>"] --> REL{"¿hay Release<br/>exposure-iso3-*?"}
  REL -->|no| SIG["siguiente candidato"]
  REL -->|sí| BAJA["gh release download<br/>exposure_h3 + admin_lookup + medicion"]
  BAJA --> IMPACT["<b>centinela impact</b>"]

  IMPACT --> SALIDA3{"código 3:<br/>¿el activo no alcanza<br/>ninguna celda?"}
  SALIDA3 -->|sí| SIG
  SIG --> LOOP
  SALIDA3 -->|no| DEC

  DEC{"<b>decide</b><br/>¿versión nueva<br/>de ShakeMap?"}
  DEC -->|"no, misma versión"| OMITIR(["omitir · sale sin escribir"])
  DEC -->|"aún no hay ShakeMap"| PRELIM["<b>preliminar</b><br/>radios 25/50/100 km<br/>reintenta 30 min, hasta 6 h"]
  DEC -->|sí| P2

  P2["<b>P2</b><br/>cont_mmi → anillos → H3 r8<br/>join contra el activo<br/>+ ground failure si existe"] --> ESQ{"<b>validar_contra_esquema</b><br/>report-1.0.schema.json"}
  ESQ -->|no| FALLA["no se escribe nada"]
  ESQ -->|sí| P3["<b>P3</b><br/>report.json · adm2.csv · celdas<br/>contornos · 2 PNG · hilo · md"]

  P3 --> IDX["<b>centinela reindexar</b><br/>+ status"]
  IDX --> COMMIT{"¿commiteó algo?"}
  COMMIT -->|sí| POST

  POST["gh workflow run site.yml"] --> CI["gh workflow run ci.yml<br/><i>comprobar lo recién publicado</i>"]
  CI --> VIS["gh workflow run visor.yml<br/><i>abrirlo en un navegador</i>"]

  LOOP -->|"agotados todos<br/>los candidatos"| CEROS{"--aunque-no-alcance"}
  CEROS -->|sí| P3
  CEROS -->|no| ISSUE["incidencia:<br/>qué país falta y cómo construirlo"]

  FALLA --> ISSUE2["incidencia con el traceback"]

  style P2 fill:#e8f0ea,stroke:#0f5636,color:#1c1b1a
  style P3 fill:#e8f0ea,stroke:#0f5636,color:#1c1b1a
  style ISSUE fill:#f4e8e8,stroke:#8c1d64,color:#1c1b1a
  style ISSUE2 fill:#f4e8e8,stroke:#8c1d64,color:#1c1b1a
  style FALLA fill:#f4e8e8,stroke:#8c1d64,color:#1c1b1a
```

**Se comprueba a sí mismo después de publicar.** Los dos últimos pasos llaman a
`ci.yml` y a `visor.yml` sobre lo que se acaba de commitear: un `report.json`
fuera de contrato o un visor que no pinta se detectan en minutos y no el día
que alguien mire. El detalle del enrutado y de la idempotencia está en
[`cadena-de-evento.md`](cadena-de-evento.md).

---

## `site.yml` · la publicación

Push a `site/` o `reports/`, o `gh workflow run` desde cualquiera de los cuatro
workflows que commitean algo publicable.

```mermaid
flowchart TB
  T1(["push a site/ o reports/"]) --> COB
  T2(["gh workflow run desde<br/>trigger · impact · incendios · frescura"]) --> COB

  COB["<b>centinela cobertura</b><br/>recalcula la cobertura regional"] --> PREP["Preparar sitio<br/>copiar reports/ dentro de site/"]
  PREP --> OG["Reescribir og:image<br/>al evento más reciente"]
  OG --> ART["upload-pages-artifact"]
  ART --> DEP["deploy-pages"]
  DEP --> PAGES(["sforero77.github.io/CENTINELA"])

  style DEP fill:#e8f0ea,stroke:#0f5636,color:#1c1b1a
  style PAGES fill:#e8eef4,stroke:#3a5a78,color:#1c1b1a
```

> **Un push hecho con `GITHUB_TOKEN` no dispara otros workflows.** Por eso todo
> el que commitea termina llamando a este a mano. Es la causa del incidente de
> las diecisiete horas y la razón de que exista `frescura.yml`.

---

## `frescura.yml` · cada 3 horas

Compara el `generado_utc` de la página **publicada** contra el del repositorio.
Es la red de seguridad del párrafo de arriba.

```mermaid
flowchart TB
  R(["cron 17 */3 · o el vigía a las 3 h"]) --> GET["GET a la página publicada<br/>status.json · incendios.json · observados.json"]

  GET --> CIEGO{"¿se pudo comparar<br/><b>alguno</b>?"}
  CIEGO -->|no| C1["<b>código 1</b><br/>no poder mirar<br/>no es estar al día"]
  CIEGO -->|"sí, alguno falló"| ANOTA["se anota y sigue<br/><i>un 404 en fichero recién nacido<br/>es normal</i>"]
  CIEGO -->|sí| CMP

  ANOTA --> CMP
  CMP{"¿generado_utc de la página<br/>&lt; el del repositorio?"}
  CMP -->|no| OK(["todo al día"])
  CMP -->|sí| DESF["<b>desfase detectado</b>"]

  DESF --> REPUB["gh workflow run site.yml"]
  DESF --> DEDUP{"¿ya hay incidencia<br/>con este título?"}
  DEDUP -->|no| NUEVA["abrir incidencia"]
  DEDUP -->|sí| COMENT["comentar en la existente"]
  REPUB --> CIERRE["si al final todo está al día,<br/>cerrar la incidencia sola"]
  OK --> CIERRE

  style DESF fill:#f4e8e8,stroke:#8c1d64,color:#1c1b1a
  style C1 fill:#f4e8e8,stroke:#8c1d64,color:#1c1b1a
```

La deduplicación y el auto-cierre no son cortesía: una alarma que abre una
incidencia cada 3 horas deja de leerse a la semana.

---

## `incendios.yml` · cada 6 horas

P5. El mismo activo de exposición que usa P2, cruzado con los focos de calor de
las últimas 24 h.

```mermaid
flowchart TB
  R(["cron 40 */6 · o el vigía a las 6 h"]) --> BAJA["gh release download<br/>los activos publicados"]
  BAJA --> FIRMS["<b>centinela incendios</b><br/>NASA FIRMS · 3 satélites VIIRS<br/>SUOMI · NOAA-20 · NOAA-21"]

  FIRMS --> AGG["agrupar por celda H3 r8<br/><i>confianza baja se cuenta aparte</i>"]
  AGG --> JOIN["LEFT JOIN contra exposure_h3"]
  JOIN --> PRIO["ordenar: primero las celdas con gente"]
  PRIO --> CUT["recorte a 4.000 celdas"]
  CUT --> OUT[/"site/incendios.json"/]

  OUT --> PUB{"¿cambió el fichero?"}
  PUB -->|no| FIN(["nada que publicar"])
  PUB -->|sí| COMMIT["commit"]
  COMMIT --> SITE["gh workflow run site.yml"]

  style JOIN fill:#e8f0ea,stroke:#0f5636,color:#1c1b1a
  style PRIO fill:#f4e8e8,stroke:#8c1d64,color:#1c1b1a
```

El recorte a 4.000 es lo que hace que la capa quepa en el visor. El orden por
población es lo que hace que el recorte no tire justo lo que importa.

---

## `repaso.yml` · diario, 05:37

RF-04 más allá de las 24 h del feed. Pregunta por identificador, no por feed:
la mediana hasta la última revisión de un ShakeMap son **63 días**.

```mermaid
flowchart TB
  R(["cron 37 5 · o el vigía a las 24 h"]) --> LEE["Leer events/"]

  LEE --> F1{"¿descartado?"}
  F1 -->|sí| FUERA["queda fuera · es terminal"]
  F1 -->|no| F2{"¿backtest?"}
  F2 -->|sí| FUERA
  F2 -->|no| F3{"¿origen dentro<br/>de 90 días?"}
  F3 -->|no| FUERA
  F3 -->|sí| PIDE["GET detail por eventid<br/><i>el mismo endpoint que usa P2</i>"]

  PIDE --> RED{"¿respondió?"}
  RED -->|no| FALLIDO["se cuenta como <b>fallido</b>,<br/>no como sin cambios"]
  RED -->|sí| CMP{"¿shakemap o ground_failure<br/>más nuevos que<br/>versiones_procesadas?"}

  CMP -->|no| NADA(["sin cambios"])
  CMP -->|sí| DESP["<b>job: despachar</b><br/>gh workflow run impact.yml"]

  FALLIDO --> TODOS{"¿fallaron <b>todos</b>?"}
  TODOS -->|sí| C1["<b>código 1</b><br/>no es sin cambios:<br/>es no haber repasado"]
  TODOS -->|no| SIGUE["aviso y la corrida sigue"]

  style CMP fill:#e8f0ea,stroke:#0f5636,color:#1c1b1a
  style C1 fill:#f4e8e8,stroke:#8c1d64,color:#1c1b1a
  style FALLIDO fill:#f4e8e8,stroke:#8c1d64,color:#1c1b1a
```

Cero revisados con cero fallidos **sale en verde**: hoy los eventos publicados
son casi todos backtests y quedan fuera por diseño. Confundir «no había nada que
repasar» con «no se pudo repasar» pondría el workflow en rojo todos los días.

---

## `contract_drift.yml` · diario, 08:00

Las fuentes públicas cambian de formato sin avisar. Este es el único workflow
cuyas pruebas **exigen red**: `pytest -m network`, que el resto de la suite
excluye por defecto.

```mermaid
flowchart TB
  R(["cron 0 8 diario"]) --> SYNC["uv sync --extra dev --extra geo"]
  SYNC --> RUN["<b>pytest -m network</b>"]

  RUN --> T1["test_feed_contract_live<br/><i>el feed resumen contra<br/>schemas/usgs/feed</i>"]
  RUN --> T2["test_detail_contract_live<br/><i>los productos del detail:<br/>status · preferredWeight · updateTime<br/>· contents · properties.version</i>"]
  RUN --> T3["test_overture_contract_live<br/><i>el release fijado sigue existiendo</i>"]
  RUN --> T4["test_silencio_de_paises_live<br/><i>las cajas de los países</i>"]

  T1 --> V{"¿derivó algo?"}
  T2 --> V
  T3 --> V
  T4 --> V

  V -->|no| OK(["los contratos aguantan"])
  V -->|sí| ISSUE["<b>incidencia automática</b><br/>con el contrato que cambió"]

  style V fill:#e8f0ea,stroke:#0f5636,color:#1c1b1a
  style ISSUE fill:#f4e8e8,stroke:#8c1d64,color:#1c1b1a
```

`test_overture_contract_live` es el que más caro sale ignorar: los manifests
fijan un release de Overture y Overture conserva **dos** —unos dos meses—.
Cuando ese release desaparece, el país no se puede reconstruir desde sus
propias fuentes. Es también la razón de que el trimestral reconstruya **todos**
los países publicados y no uno.

---

## `rezago.yml` · lunes, 07:23

Lo contrario de `repaso.yml`: en vez de preguntar por los eventos, pregunta por
los **reportes ya publicados**. ¿Lo que se está sirviendo sigue siendo lo que
las fuentes dicen hoy?

```mermaid
flowchart TB
  R(["cron 23 7 · lunes"]) --> CMP["<b>centinela rezagados</b><br/>cada reporte publicado contra<br/>lo que sus fuentes sirven hoy"]

  CMP --> C1{"shakemap<br/>publicado vs vigente"}
  CMP --> C2{"ground_failure<br/>publicado vs vigente"}
  CMP --> C3{"manifiesto de exposición<br/>publicado vs vigente"}

  C1 --> SEP
  C2 --> SEP
  C3 --> SEP

  SEP["<b>se separan en dos listas</b>"]
  SEP --> SOLO["ids_exposicion<br/><i>sólo cambió el activo:<br/>casi no mueve cifras</i>"]
  SEP --> PROD["ids_productos<br/><i>cambió ShakeMap o GF:<br/>mueve las cifras que el README cita</i>"]

  SOLO --> AUTO["re-emitir solo<br/>gh workflow run impact.yml<br/>--reprocesar"]
  PROD --> MANO["<b>incidencia</b><br/>los mira una persona<br/>antes de re-emitir"]

  CMP --> CIEGO{"¿no se pudo consultar<br/><b>ninguno</b>?"}
  CIEGO -->|sí| EXIT1["<b>código 1</b>"]
  CIEGO -->|no| VERDE["hay rezago <b>no</b> es fallo:<br/>sale 0 a propósito"]

  style SEP fill:#e8f0ea,stroke:#0f5636,color:#1c1b1a
  style MANO fill:#f4e8e8,stroke:#8c1d64,color:#1c1b1a
  style EXIT1 fill:#f4e8e8,stroke:#8c1d64,color:#1c1b1a
```

Que salga 0 cuando hay rezago es deliberado: convertir «hay trabajo pendiente»
en «algo se rompió» hace que en dos semanas nadie mire el aviso.

---

## `simulacro.yml` · día 5, 09:00

Dos jobs, porque el pipeline tiene dos mitades y se oxidan por separado.

```mermaid
flowchart TB
  R(["cron 0 9 · día 5"]) --> J1
  R --> J2

  subgraph J1["job: simulacro · la mitad de arriba"]
    A1["<b>centinela trigger --dry-run</b><br/>contra el feed vivo de USGS"] --> A2["mide latencia_p1_s"]
    A2 --> A3["<b>pytest -m golden</b><br/>63 pruebas · Chocó M7,4<br/>Venezuela M7,5 y M7,2"]
  end

  subgraph J2["job: poblacion · la mitad de abajo"]
    B1["gh release download<br/>activo de COL"] --> B2["<b>scripts/simulacro_sismo.py</b><br/>ShakeMap real del Chocó<br/><b>mudado</b> sobre Cali"]
    B2 --> B3["run_impact completo<br/>P2 + P3 contra el activo real"]
    B3 --> B4{"¿alcanza 1.000.000<br/>en MMI&gt;=6?"}
    B4 -->|no| BF["<b>código 1</b><br/>un simulacro en ceros<br/>no ensayó nada"]
    B4 -->|sí| B5["<b>pytest</b> test_ningun_simulacro_publicado"]
    B5 --> B6{"git status de<br/>events · reports · site<br/>¿vacío?"}
    B6 -->|no| BG["<b>error</b><br/>el guardarrail falló"]
  end

  A3 --> ISS{"¿algo en rojo?"}
  B6 -->|sí| ISS
  ISS -->|sí| ISSUE["<b>incidencia automática</b><br/>el pipeline se oxidó<br/>entre catástrofes"]
  ISS -->|no| OK(["ensayo superado"])

  style B3 fill:#e8f0ea,stroke:#0f5636,color:#1c1b1a
  style BF fill:#f4e8e8,stroke:#8c1d64,color:#1c1b1a
  style BG fill:#f4e8e8,stroke:#8c1d64,color:#1c1b1a
  style ISSUE fill:#f4e8e8,stroke:#8c1d64,color:#1c1b1a
```

Ninguno de los dos jobs escribe estado ni publica nada, y los dos van con
`persist-credentials: false`: el checkout se queda sin token porque ninguno
necesita empujar. El segundo escribe en `work/simulacro/`, y hay dos cierres
independientes para que no pueda escribir en otro sitio — ver
[`mantenimiento.md`](mantenimiento.md) y
[`../../scripts/README.md`](../../scripts/README.md).

---

## `keepalive.yml` · días 1 y 15, 07:00

El workflow más corto del repositorio, y no es prescindible: **GitHub desactiva
los workflows programados de un repositorio sin actividad durante 60 días.**

```mermaid
flowchart LR
  R(["cron 0 7 · días 1 y 15"]) --> W["fecha UTC a .keepalive"]
  W --> Q{"¿cambió?"}
  Q -->|no| FIN(["nada"])
  Q -->|sí| C["commit + push<br/><i>como centinela-bot</i>"]
  C --> RESET(["el contador de 60 días<br/>vuelve a cero"])

  style RESET fill:#e8f0ea,stroke:#0f5636,color:#1c1b1a
```

Si esto fallara callado, el sistema entero se apagaría sin una sola alarma: los
nueve relojes dejarían de sonar a la vez. Es el único caso que ninguna otra
comprobación cubriría, porque todas dependen de un cron.

---

## `exposure_quarterly.yml` · 1 de enero, abril, julio y octubre, 06:00

P0. El único que reconstruye el denominador de todo lo demás. Dos jobs: uno
decide qué países, otro los construye en paralelo de a cuatro.

```mermaid
flowchart TB
  R(["cron trimestral · o -f iso3=XXX"]) --> EL

  subgraph EL["job: elegir"]
    E1{"¿llegó iso3<br/>por input?"}
    E1 -->|sí| E2{"¿coincide con<br/>^[A-Z]{3}$?"}
    E2 -->|no| EX(["error · texto libre<br/>no se interpola en un run"])
    E2 -->|sí| E3["ese país"]
    E1 -->|no| E4["<b>todos los que tienen<br/>Release publicado</b><br/><i>los que el sistema sirve</i>"]
  end

  E3 --> MTX
  E4 --> MTX
  MTX["<b>job: construir</b><br/>matrix · max-parallel 4 · fail-fast false"]

  MTX --> V0["<b>centinela lint-manifests</b><br/>licencias y vintages<br/><i>antes de descargar nada</i>"]
  V0 --> V1{"¿el código de país<br/>es válido?"}
  V1 -->|no| STOP(["falla este país"])
  V1 -->|sí| BUILD["<b>centinela country</b><br/>P0 completo"]

  BUILD --> P1{"validate_bbox<br/>¿la caja cubre el país?"}
  P1 -->|no| STOP
  P1 -->|sí| P2{"validate_layer_coverage<br/>¿alguna capa requerida<br/>suma cero?"}
  P2 -->|sí| STOP
  P2 -->|no| P3{"validate_national_total<br/>¿dentro de la tolerancia?"}
  P3 -->|no| STOP
  P3 -->|sí| REL[("Release<br/>exposure-iso3-fecha")]

  REL --> CAL["<b>centinela calibrar</b><br/>anota la medición en el manifest"]
  CAL --> COB["<b>centinela cobertura</b><br/>recalcula y commitea"]
  COB --> SITE["gh workflow run site.yml"]

  STOP --> ISS["<b>incidencia por país</b><br/>fail-fast false: un país roto<br/>no puede tumbar a los otros 18"]
  SITE --> CIERRA["si el país volvió,<br/>cerrar su incidencia"]

  style REL fill:#e8f0ea,stroke:#0f5636,color:#1c1b1a
  style ISS fill:#f4e8e8,stroke:#8c1d64,color:#1c1b1a
  style STOP fill:#f4e8e8,stroke:#8c1d64,color:#1c1b1a
```

**Reconstruye todos los países publicados, no uno.** Lo hacía con uno, heredado
de cuando sólo existía Colombia, y eso dejaba diecisiete países a un trimestre
de quedarse sin camino de vuelta a sus fuentes: los manifests fijan un release
de Overture y Overture sólo conserva dos. Las tres validaciones internas están
en [`../pipelines/p0-exposicion.md`](../pipelines/p0-exposicion.md).

---

## `ci.yml` y `visor.yml` · push y pull request

No son relojes, son la puerta. Las dos tienen que estar verdes para fusionar, y
`impact.yml` las llama además **después de publicar**.

```mermaid
flowchart TB
  PR(["push · pull_request"]) --> CI
  PR --> DIAG
  PR --> VIS

  subgraph CI["ci.yml · job check"]
    C1["ruff check"] --> C2["ruff format --check"]
    C2 --> C3["<b>mypy --strict</b>"]
    C3 --> C4["<b>pytest</b> -m 'not network and not visor'<br/>sin red · con cobertura"]
    C4 --> C5["<b>centinela lint-manifests</b><br/>regla de los tres cubos"]
  end

  subgraph DIAG["ci.yml · job diagramas"]
    D1["<b>scripts/validar_diagramas.py</b><br/>cada bloque mermaid<br/>de los .md versionados"] --> D2{"¿encontró alguno?"}
    D2 -->|no| D0["<b>código 2</b><br/>cero diagramas no es<br/>que compilen todos"]
    D2 -->|sí| D3["<b>mermaid-cli</b><br/>todos juntos · un solo Chromium"]
    D3 --> D4{"¿compilan?"}
    D4 -->|no| D5["<b>código 1</b><br/>recompila uno por uno:<br/>fichero:línea de cada roto"]
  end

  subgraph VIS["visor.yml"]
    W1["cache de Chromium<br/>por versión de Playwright"] --> W2["<b>pytest tests/visor -m visor</b><br/>pruebas de navegador"]
    W2 --> W3["lee window.CENTINELA.pintado<br/><i>qué capas se pintaron y con<br/>cuántos rasgos · no una captura</i>"]
  end

  C5 --> M{"¿todo verde?"}
  D4 -->|sí| M
  W3 --> M
  M -->|no| NO(["no se fusiona"])
  M -->|sí| SI(["se puede fusionar"])

  style M fill:#e8f0ea,stroke:#0f5636,color:#1c1b1a
  style NO fill:#f4e8e8,stroke:#8c1d64,color:#1c1b1a
  style D0 fill:#f4e8e8,stroke:#8c1d64,color:#1c1b1a
  style D5 fill:#f4e8e8,stroke:#8c1d64,color:#1c1b1a
```

`visor.yml` comprueba lo que ninguna prueba unitaria ve: que las pestañas
reciben el clic, que ningún texto se pisa con otro en los tres tamaños de
pantalla, que la leyenda promete lo que el mapa dibuja.

El job `diagramas` comprueba lo que ninguna de las dos ve: que los diagramas de
la documentación, este incluido, se dibujan. Uno roto se publica en GitHub como
un recuadro de error. No va en `visor.yml`, aunque ya tenga Chromium, porque
aquel no se dispara con un cambio en `docs/`.

---

## `contraste.yml` · a mano

Fase 2. Es el único que compara las cifras del sistema contra una **evaluación
de daño externa**, que es la única manera de saber si el modelo de exposición
sirve para algo.

```mermaid
flowchart TB
  R(["workflow_dispatch<br/>evento + fuente de daño + CRS"]) --> CAND["<b>centinela paises-candidatos</b>"]
  CAND --> BAJA["gh release download<br/>activo del país"]
  BAJA --> DANO["descargar la evaluación<br/>de daño externa"]
  DANO --> CRS["<b>--crs obligatorio</b><br/><i>no se adivina el EPSG<br/>de un vector ajeno</i>"]
  CRS --> CONTR["<b>centinela contraste</b><br/>cada edificación evaluada<br/>a su celda r8 por el centroide"]
  CONTR --> ART["upload-artifact<br/><i>no se publica en el visor</i>"]

  style CONTR fill:#e8f0ea,stroke:#0f5636,color:#1c1b1a
```

El resultado sube como artefacto de la corrida y **no** entra en la página: un
contraste es una medición del sistema, no un producto para quien responde a una
emergencia.

---

## Lo que ningún reloj cubre

| Fallo | Quién lo notaría |
|---|---|
| El cron externo se para | healthchecks.io, a los 30 min sin latido |
| GitHub desactiva los schedules | `keepalive.yml` lo impide; si fallara, **nadie** |
| Un sismo en vivo que alcance población | Nunca ha ocurrido. Lo ensaya `simulacro.yml` job `poblacion` |
| La página miente pero el repo también | `frescura.yml` compara los dos; si los dos se congelan a la vez, el latido |
| Una cifra publicada está mal | `rezago.yml` semanal, y el contraste de Fase 2 a mano |

**Nada se da por arreglado si depende de que alguien lo note.** Es la regla que
ordena el proyecto, y esta tabla es la lista de los sitios donde todavía no se
cumple del todo.
