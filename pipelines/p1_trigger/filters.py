"""Criterio de relevancia del disparador (RF-01).

Tres condiciones, todas explicitas y todas testeables sin red: es un sismo, es
lo bastante grande, y cae en la ventana LATAM. El umbral de magnitud es la
principal defensa contra el "falso disparo / cifra alarmista" del registro de
riesgos.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..common.constants import MIN_MAGNITUDE
from ..common.geo import LATAM_BBOX, BBox
from .feed import EventCandidate

#: Tipos de evento del catalogo USGS que ignoramos (explosiones, eventos de
#: hielo, ruido). Solo procesamos terremotos.
RELEVANT_EVENT_TYPE = "earthquake"


@dataclass(frozen=True, slots=True)
class RelevanceDecision:
    """Resultado del filtro, con la razon del descarte para el log."""

    relevante: bool
    razon: str

    def __bool__(self) -> bool:
        return self.relevante


def evaluate(
    candidate: EventCandidate,
    *,
    bbox: BBox = LATAM_BBOX,
    min_magnitude: float = MIN_MAGNITUDE,
) -> RelevanceDecision:
    """Evalua un candidato y explica la decision."""
    if candidate.tipo != RELEVANT_EVENT_TYPE:
        return RelevanceDecision(False, f"tipo no sismico: {candidate.tipo}")
    if candidate.mag < min_magnitude:
        return RelevanceDecision(False, f"M{candidate.mag} < umbral M{min_magnitude}")
    if not bbox.contains(candidate.lon, candidate.lat):
        return RelevanceDecision(False, "fuera del bbox LATAM")
    return RelevanceDecision(True, "dentro de alcance")


def is_relevant(
    candidate: EventCandidate,
    *,
    bbox: BBox = LATAM_BBOX,
    min_magnitude: float = MIN_MAGNITUDE,
) -> bool:
    """Version booleana de :func:`evaluate`."""
    return bool(evaluate(candidate, bbox=bbox, min_magnitude=min_magnitude))
