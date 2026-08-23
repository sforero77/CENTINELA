# Golden tests

Pruebas de regresion contra eventos reales congelados. Corren en cada PR (§6.3).

| Id | Evento | Que fija |
|---|---|---|
| G1 | Choco, M7.4, 10-ago-2026 | Que el trigger habria disparado; `pop_mmi7p` estable ±0.5 % entre commits; top-15 municipal estable; el reporte final referencia la ultima version de ShakeMap |
| G2 | Venezuela, 24-jun-2026 | Idem, mas bbox y manejo de evento doble (dos mainshocks) |
| G3 | Evento profundo sin Ground Failure | Que el reporte omite la seccion con nota explicita y **no falla** |

## Estado

G1 y G2 estan **bloqueados por fixtures**: requieren T0.1 (obtener los `usgs_id`
oficiales de ambos eventos) y T0.2 (descargar y congelar los productos con
`includesuperseded` via `libcomcat`). Hasta entonces se saltan con razon
explicita — nunca se marcan como verdes.

G3 ya corre: su parte de render vive en `tests/unit/test_report.py`.

## Como congelar una fixture

```bash
# T0.2 — requiere libcomcat instalado localmente, no en CI
uv run --extra dev python scripts/freeze_event.py <usgs_id> --out tests/fixtures/golden/<usgs_id>
```

Las fixtures congeladas se versionan: son la unica forma de que el sistema
pueda decir "esto habria salido a las 08:3X" del 10 de agosto.
