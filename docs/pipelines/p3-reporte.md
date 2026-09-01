# P3 — Reporte

**Qué hace:** convierte el modelo `Report` en los ocho artefactos publicables.
**Cadencia:** por evento, justo después de P2.
**Código:** `pipelines/p3_report/` (model, markdown, csv_out, static_map,
contornos, celdas, changelog, run)

## Lo que emite

```mermaid
flowchart LR
  R["<b>Report</b><br/>modelo validado"] --> J[/"report.json"/]
  R --> M[/"report.md"/]
  R --> C[/"adm2.csv"/]
  R --> CE[/"celdas.json"/]
  R --> CO[/"contornos.json"/]
  R --> P1[/"mapa_general.png<br/>1200×900"/]
  R --> P2[/"mapa_prensa.png<br/>1600×900"/]
  R --> H[/"hilo.txt"/]
  R --> IDX[/"reports/index.json"/]

  J --> V(["Visor"])
  CE --> V
  CO --> V
  C --> V
  IDX --> V
  H --> RED(["el único<br/>paso manual"])

  style R fill:#e8f0ea,stroke:#0f5636,color:#1c1b1a
  style RED fill:#f4f1e8,stroke:#8a8578,color:#1c1b1a
```

| Artefacto | Para quién |
|---|---|
| `report.json` | El visor y cualquier tercero. Validado contra [`schemas/report-1.0.schema.json`](../../schemas/report-1.0.schema.json) |
| `report.md` | Personas. Prosa en español con cifras redondeadas a 2 cifras significativas |
| `adm2.csv` | Analistas. Una fila por municipio, **cifras exactas** |
| `celdas.json` | El visor: la malla H3 del evento con sus columnas |
| `contornos.json` | El visor: las líneas de isointensidad |
| `mapa_general.png` | Uso general |
| `mapa_prensa.png` | Redes y prensa, con tipografía mayor |
| `hilo.txt` | El hilo listo para publicar — **el único paso manual permitido en todo el sistema** |

## El modelo

```mermaid
classDiagram
  class Report {
    schema
    generado_utc
    pipeline_version
    disclaimers
  }
  class Evento {
    usgs_id
    mag
    lugar
    lon
    lat
    profundidad_km
  }
  class Inputs {
    shakemap_version
    manifest_id
    productos
  }
  class Totales {
    pop_mmi6p
    pop_mmi7p
    pop_mmi8p
    bld_count
    road_km
    health_count
    edu_count
  }
  class MunicipioTop {
    adm2_id
    nombre
    pop_mmi7p
    mmi_max
  }
  class Incertidumbre {
    banda_discrepancia
    notas
  }
  class Descargas {
    rutas_de_artefactos
  }
  class PoblacionEnRadio {
    radio_km
    pop
  }

  Report --> Evento
  Report --> Inputs
  Report --> Totales
  Report --> "0..15" MunicipioTop
  Report --> Incertidumbre
  Report --> Descargas
  Report --> "0..3" PoblacionEnRadio
```

Todos son `@dataclass(frozen=True, slots=True)`: el reporte es inmutable una
vez construido.

## Prosa contra datos

`PROSE_SIGNIFICANT_DIGITS = 2`. En el markdown y el hilo, las cifras van
redondeadas: *"2,4 millones de personas"*. En CSV y parquet van **exactas**:
`2415793`.

No es inconsistencia. Una cifra con siete dígitos significativos en prosa
finge una precisión que el modelo no tiene; la misma cifra exacta en el CSV es
lo que necesita quien va a recalcular.

## El changelog de deltas (RF-04)

Un ShakeMap se revisa muchas veces —el de Venezuela llegó a **v14**—. Quien ya
leyó la versión anterior necesita saber qué cambió, no volver a leerlo entero
durante una emergencia.

```
pop MMI≥7: 340k → 355k
```

> Este módulo estaba escrito casi entero y **no lo llamaba nadie**.
> `Report.changelog` existía, `markdown.py` lo renderizaba si venía con algo,
> `format_delta_prose` daba exactamente ese formato — y ninguna línea del
> pipeline lo llenaba, así que la sección no apareció jamás en un reporte.
> El mismo patrón que el reporte preliminar y que tres capas del activo:
> piezas correctas, sin nadie que las una. Es el fallo que motivó
> `test_funciones_conectadas.py`.

## Los mapas estáticos

Dos variantes, y ahora distintas de verdad:

| Variante | Píxeles | DPI | Para |
|---|---|---|---|
| `general` | 1100 × 900 | 110 | El panel y el markdown: compacta, para leerse dentro de otra cosa |
| `prensa` | 1920 × 1080 | 140 | 16:9 y tipografía grande: una nota o una proyección |

Antes sólo cambiaba el ancho máximo, y con `tight_layout` recortando al dato ni
eso se notaba: los dos PNG de cada evento salían prácticamente idénticos,
ofrecidos como dos descargas distintas.

**Y no eran un mapa.** Eran una dispersión de matplotlib con los ejes en grados
decimales —«−79.5», «0.5»—, sin costa, sin escala, sin norte y sin leyenda de
tamaño, cuando el tamaño del círculo *es* la variable principal. Hoy llevan:

- **La forma del evento**, de `contornos.json`. ShakeMap publica sus contornos
  como líneas, no como áreas, pero los lazos vienen cerrados y las bandas están
  anidadas: pintar de menor a mayor reproduce la estructura sin recortar
  geometría. Un lazo abierto se descarta antes que inventar área.
- **Barra de escala en km y flecha de norte**, en lugar de los ejes. Nadie lee
  «−79.5» en un mapa de prensa, y una retícula de coordenadas sugiere una
  precisión de posición que este producto no publica.
- **Leyenda de tamaño**, con tres círculos de referencia.
- **Marcadores en tinta neutra.** Iban coloreados por intensidad *sobre* un fondo
  que ahora ya es la intensidad, así que un municipio en MMI 8 desaparecía. Una
  variable por canal: el color es del fondo, el tamaño es del símbolo.

No se toca T0.8: matplotlib solo, sin teselas, sin red y sin llaves. Y **sin
`h3`**: la forma sale de los contornos, que son coordenadas planas en el JSON,
para no atar el render del reporte al extra pesado `[geo]`.

`centinela regenerar-mapas` los rehace sin recalcular el impacto.

## Rehacer los textos de un reporte publicado

`centinela regenerar-textos` es el gemelo de `regenerar-mapas`: rehace
`report.md` y `hilo.txt` de un reporte publicado, o de todos, desde su
`report.json` y su `adm2.csv`. No recomputa el impacto, que costaría bajar el
activo de cada país.

Existe por un descubrimiento incómodo. El generador llevaba las tildes puestas en
el repositorio y **lo publicado no**: los veintiún paquetes se emitieron antes de
esa corrección y nada volvía a tocarlos, así que el hilo para redes —el único
artefacto que un humano publica a mano— abría con «Reporte automatico de
EXPOSICION estimada» y cerraba con «Exposicion no es dano».

Un texto rancio no se distingue de uno recién generado mirándolo.
`tests/unit/test_textos_publicados.py` vigila el generador con una lista negra de
las formas que se colaron; comprobado que detecta las trece que estaban
publicadas.

## El índice

`rebuild_index()` recorre `reports/` y escribe `reports/index.json`: 21
entradas con `usgs_id`, `mag`, `lugar`, `iso3`, `lon`, `lat`, `pop_mmi7p`,
`pop_mmi6p`, `utc`, `shakemap_version`, `preliminar`, `backtest` y
`generado_utc`. Es lo primero que descarga el visor.

El campo `backtest` importa: separa los 21 reportes reconstruidos del catálogo
histórico de los que salgan en vivo. `site/status.json` los cuenta aparte
(`backtests_excluidos: 21`) para que no contaminen la latencia medida.

## Los disclaimers

Cuatro líneas fijas, obligatorias en **todo** artefacto (§1.2), definidas en
`constants.py`:

1. Exposición estimada, no daño observado.
2. Este sistema no es una alerta temprana ni una recomendación de evacuación.
3. No reemplaza a los servicios geológicos ni a las unidades de gestión del riesgo.
4. Fuentes, vintages y versiones consumidas: ver manifest enlazado.
