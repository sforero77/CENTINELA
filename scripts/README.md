# scripts/

Utilidades que se corren a mano, no en el camino critico.

| Script | Que hace |
|---|---|
| `freeze_event.py` | Congela los productos de un evento real como fixture golden (T0.2) |

Estos scripts si pueden tocar la red y pueden depender de herramientas que no
estan en CI (`libcomcat`). Nada de lo que hacen bloquea un reporte.
