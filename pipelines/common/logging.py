"""Logging estructurado (una linea JSON por evento).

Los runners de GitHub Actions son la unica consola del sistema; los logs son
la evidencia de latencia que alimenta la pagina ``/status`` (RNF-02).
"""

from __future__ import annotations

import json
import logging
import os
import sys
from typing import Any


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        extra = getattr(record, "context", None)
        if isinstance(extra, dict):
            payload |= extra
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def get_logger(name: str) -> logging.Logger:
    """Logger con salida JSON a **stderr**, idempotente entre llamadas.

    A stderr y no a stdout a proposito: varios subcomandos imprimen JSON por
    stdout para que otro proceso lo canalice —`centinela calibrar` alimenta un
    script, `paises-candidatos` alimenta al workflow— y una linea de log en medio
    lo vuelve imposible de parsear. Paso de verdad al recalibrar los diecinueve
    manifests: "Extra data: line 2 column 1".

    En GitHub Actions se ve igual, porque el runner mezcla los dos flujos en el
    log de la corrida.
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(_JsonFormatter())
        logger.addHandler(handler)
        logger.setLevel(os.environ.get("CENTINELA_LOG_LEVEL", "INFO").upper())
        logger.propagate = False
    return logger
