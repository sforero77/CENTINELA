# scripts/

Utilidades que se corren a mano, no en el camino crítico.

| Script | Qué hace |
|---|---|
| `freeze_event.py` | Congela los productos de un evento real como fixture golden (T0.2) |

Estos scripts si pueden tocar la red y pueden depender de herramientas que no
están en CI (`libcomcat`). Nada de lo que hacen bloquea un reporte.

## `delta_contornos_vs_grid.py`

Mide cuánto se separa el método de contornos del campo continuo de `grid.xml`,
replicando el cómputo real de P2 por los dos caminos sobre el mismo activo.

```
uv run --extra dev python scripts/delta_contornos_vs_grid.py us6000tjl2 COL
```

Descarga ~50 MB por evento, así que vive aquí y no en la suite: es una medición
que se corre cuando se cuestiona el método, no en cada commit. El resultado
sobre el Chocó está en `PENDIENTES.md` §2.1.sexies.
