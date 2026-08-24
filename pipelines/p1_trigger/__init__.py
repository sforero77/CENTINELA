"""P1 — TRIGGER: vigilancia del feed USGS y creacion del ``event_state``.

Corre por cron cada 10 min (best-effort, §4.2) y por ``workflow_dispatch``.
Es el unico pipeline en el camino critico de latencia: se mantiene sin
dependencias geo pesadas para arrancar en un runner frio en segundos.
"""

from .feed import EventCandidate, parse_feed
from .filters import is_relevant
from .run import TriggerResult, run_trigger

__all__ = ["EventCandidate", "TriggerResult", "is_relevant", "parse_feed", "run_trigger"]
