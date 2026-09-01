"""P1 — TRIGGER: vigilancia del feed USGS y creacion del ``event_state``.

Corre por cron ``*/30`` (best-effort, §4.2), por ``repository_dispatch`` desde un
cron externo cuando lo haya, y por ``workflow_dispatch``. Declaraba ``*/10`` y bajo
a ``*/30`` el 27-ago-2026: GitHub reparte unos pocos turnos **por repositorio**, no
uno por workflow, y pedir el triple no consigue el triple. Lo medido esta en la
cabecera de ``.github/workflows/trigger.yml``.
Es el unico pipeline en el camino critico de latencia: se mantiene sin
dependencias geo pesadas para arrancar en un runner frio en segundos.
"""

from .feed import EventCandidate, parse_feed
from .filters import is_relevant
from .run import TriggerResult, run_trigger

__all__ = ["EventCandidate", "TriggerResult", "is_relevant", "parse_feed", "run_trigger"]
