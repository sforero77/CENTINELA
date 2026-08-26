"""Orquestacion de P1: feed -> filtro -> dedupe -> ``event_state`` -> dispatch.

Contrato de salida: una lista de ``usgs_id`` a despachar hacia P2 por
``repository_dispatch``. El pipeline es idempotente (RF-02): correrlo dos veces
sobre el mismo feed no crea trabajo duplicado.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from ..common.constants import USGS_FEED_BACKFILL, USGS_FEED_PRIMARY
from ..common.geo import LATAM_BBOX, BBox
from ..common.http import Fetcher
from ..common.logging import get_logger
from ..common.state import EventState, EventStatus, utcnow_iso
from .feed import EventCandidate, fetch_feed
from .filters import evaluate
from .observados import EventoObservado

_log = get_logger(__name__)


@dataclass(slots=True)
class TriggerResult:
    """Resumen de una corrida del disparador."""

    revisados: int = 0
    relevantes: int = 0
    #: Eventos nuevos, que P2 debe procesar por primera vez.
    nuevos: list[str] = field(default_factory=list)
    #: Eventos ya conocidos, re-verificados por si hay nueva version de
    #: producto. P2 decide si hay trabajo real (RF-04).
    revisitados: list[str] = field(default_factory=list)
    #: Sismos de LATAM vistos y no despachados por quedar bajo el umbral. No se
    #: despachan, pero se publican: el vigia tiene que poder demostrar que
    #: estuvo mirando.
    observados: list[EventoObservado] = field(default_factory=list)
    latido_utc: str = field(default_factory=utcnow_iso)

    @property
    def a_despachar(self) -> list[str]:
        """Eventos que se envian a P2 en esta corrida."""
        return [*self.nuevos, *self.revisitados]


#: Estados terminales: no se re-despachan.
_TERMINAL = frozenset({EventStatus.DESCARTADO})


def run_trigger(
    fetcher: Fetcher,
    *,
    feeds: tuple[str, ...] = (USGS_FEED_PRIMARY, USGS_FEED_BACKFILL),
    bbox: BBox = LATAM_BBOX,
    events_dir: Path | None = None,
    dry_run: bool = False,
) -> TriggerResult:
    """Ejecuta una pasada del disparador.

    Args:
        fetcher: cliente HTTP (real o de fixtures).
        feeds: feeds a consultar. El segundo cubre la demora del cron: si el
            runner desperto 25 min tarde, ``4.5_hour`` sigue alcanzando, pero
            ``4.5_day`` garantiza que no se pierda nada.
        bbox: ventana geografica de interes.
        events_dir: directorio de ``event_state`` (tests lo redirigen).
        dry_run: no escribe estado; util para el simulacro mensual.
    """
    result = TriggerResult()
    vistos: set[str] = set()

    for feed in feeds:
        for candidate in fetch_feed(fetcher, feed):
            if candidate.usgs_id in vistos:
                continue  # el mismo evento aparece en ambos feeds
            vistos.add(candidate.usgs_id)
            result.revisados += 1

            decision = evaluate(candidate, bbox=bbox)
            if not decision:
                _log.debug(
                    "evento descartado",
                    extra={"context": {"usgs_id": candidate.usgs_id, "razon": decision.razon}},
                )
                if _solo_le_falto_magnitud(candidate, bbox):
                    result.observados.append(
                        EventoObservado.desde_candidato(candidate, decision.razon)
                    )
                continue
            result.relevantes += 1
            _classify(candidate, result, events_dir=events_dir, dry_run=dry_run)

    _log.info(
        "latido del trigger",
        extra={
            "context": {
                "revisados": result.revisados,
                "relevantes": result.relevantes,
                "observados": len(result.observados),
                "nuevos": result.nuevos,
                "revisitados": result.revisitados,
            }
        },
    )
    return result


def _solo_le_falto_magnitud(candidate: EventCandidate, bbox: BBox) -> bool:
    """¿Es un sismo de LATAM que solo se descarto por ser pequeno?

    Los feeds del USGS son **mundiales**: de los catorce candidatos de una
    corrida tipica, la mayoria se descartan por caer fuera del bbox. Publicar
    esos convertiria la capa en un sismografo global y taparia lo unico que le
    importa a este sistema.

    Se resuelve volviendo a preguntarle al filtro con el umbral en cero. Si asi
    pasa, lo unico que le sobraba era el tamano. Preferible a inspeccionar el
    texto de la razon, que es prosa para un log y puede cambiar.
    """
    return bool(evaluate(candidate, bbox=bbox, min_magnitude=0.0))


def _classify(
    candidate: EventCandidate,
    result: TriggerResult,
    *,
    events_dir: Path | None,
    dry_run: bool,
) -> None:
    """Decide si el evento es nuevo, revisita o terminal, y persiste el estado."""
    existing = EventState.load(candidate.usgs_id, events_dir)

    if existing is None:
        state = EventState(
            usgs_id=candidate.usgs_id,
            estado=EventStatus.DETECTADO,
            mag=candidate.mag,
            lon=candidate.lon,
            lat=candidate.lat,
            depth_km=candidate.depth_km,
            lugar=candidate.lugar,
            origen_utc=candidate.origen_utc,
            timestamps={"detectado": utcnow_iso(), "usgs_origen": candidate.origen_utc},
        )
        if not dry_run:
            state.save(events_dir)
        result.nuevos.append(candidate.usgs_id)
        _log.info(
            "evento nuevo detectado",
            extra={
                "context": {
                    "usgs_id": candidate.usgs_id,
                    "mag": candidate.mag,
                    "lugar": candidate.lugar,
                }
            },
        )
        return

    if existing.estado in _TERMINAL:
        return

    # Ya conocido: P2 decide si la version de ShakeMap avanzo (RF-04). El
    # trigger no descarga productos — eso lo hace P2 con el feed detail.
    result.revisitados.append(candidate.usgs_id)
