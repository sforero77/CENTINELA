"""Orquestacion de P2.

La parte decisoria — ¿hay trabajo? ¿preliminar o completo? ¿que version? — es
codigo puro y testeable sin red ni geo. El computo pesado se delega a
:mod:`shakemap`, :mod:`ground_failure` y :mod:`exposure_join`.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from ..common.constants import PRELIMINARY_MAX_HOURS, PRELIMINARY_RETRY_MINUTES
from ..common.http import Fetcher
from ..common.logging import get_logger
from ..common.state import EventState, EventStatus
from .products import ProductSet, fetch_products

_log = get_logger(__name__)

#: Cuantos reintentos preliminares caben en la ventana de RF-03.
MAX_PRELIMINARY_ATTEMPTS = PRELIMINARY_MAX_HOURS * 60 // PRELIMINARY_RETRY_MINUTES


class Action(StrEnum):
    """Que debe hacer P2 con un evento en esta corrida."""

    #: Nada cambio desde la ultima corrida: misma version de todos los productos.
    OMITIR = "omitir"
    #: Aun no hay ShakeMap: reporte por radios (RF-03).
    PRELIMINAR = "preliminar"
    #: Hay ShakeMap nuevo (o el primero): reporte completo.
    COMPLETO = "completo"
    #: Se agoto la ventana de 6 h sin ShakeMap; se deja de reintentar.
    AGOTADO = "agotado"


@dataclass(frozen=True, slots=True)
class Decision:
    """Accion elegida y su justificacion, para el log y el changelog."""

    action: Action
    razon: str
    shakemap_version: int = 0
    groundfailure_version: int = 0


def decide(state: EventState, products: ProductSet) -> Decision:
    """Decide la accion a partir del estado persistido y los productos vivos.

    Esta funcion es el corazon de la idempotencia (RF-02): dos corridas sobre
    el mismo par ``(estado, productos)`` devuelven la misma decision.
    """
    if state.estado is EventStatus.DESCARTADO:
        return Decision(Action.OMITIR, "evento descartado")

    if not products.has_shakemap:
        if state.intentos_preliminar >= MAX_PRELIMINARY_ATTEMPTS:
            return Decision(
                Action.AGOTADO,
                f"sin ShakeMap tras {PRELIMINARY_MAX_HOURS} h de reintentos",
            )
        return Decision(Action.PRELIMINAR, "sin ShakeMap disponible aun")

    sm_version = products.shakemap_version
    gf_version = products.groundfailure_version

    if state.needs_reprocessing(sm_version, gf_version):
        previa = state.versiones_procesadas
        razon = (
            f"ShakeMap v{previa.shakemap} -> v{sm_version}"
            if sm_version > previa.shakemap
            else f"Ground Failure v{previa.groundfailure} -> v{gf_version}"
        )
        return Decision(Action.COMPLETO, razon, sm_version, gf_version)

    return Decision(
        Action.OMITIR,
        f"ya procesado en ShakeMap v{sm_version}",
        sm_version,
        gf_version,
    )


def run_impact(
    usgs_id: str,
    fetcher: Fetcher,
    *,
    detail_url: str,
    events_dir: Path | None = None,
) -> Decision:
    """Procesa un evento: resuelve productos, decide y ejecuta.

    El cuerpo del computo (polyfill, muestreo, join) esta pendiente de Fase 0
    semana 3; la resolucion de productos y la decision ya son funcionales, que
    es lo que permite escribir los golden tests antes que el computo.
    """
    state = EventState.load(usgs_id, events_dir)
    if state is None:
        raise FileNotFoundError(f"No existe event_state para {usgs_id}; P1 debe crearlo primero")

    products = fetch_products(fetcher, detail_url)
    decision = decide(state, products)
    _log.info(
        "decision de impacto",
        extra={
            "context": {
                "usgs_id": usgs_id,
                "accion": decision.action.value,
                "razon": decision.razon,
                "shakemap_version": decision.shakemap_version,
            }
        },
    )

    if decision.action in (Action.OMITIR, Action.AGOTADO):
        return decision

    raise NotImplementedError(
        "Pendiente: ejecucion del computo de impacto (Fase 0 semana 3). "
        "La resolucion de productos y la decision ya son funcionales."
    )
