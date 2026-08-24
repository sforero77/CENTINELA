"""Decision de P2: la funcion que garantiza idempotencia (RF-02, RF-04)."""

from __future__ import annotations

from typing import Any

import pytest

from pipelines.common.state import EventState, EventStatus, ProcessedVersions
from pipelines.p2_impact.products import parse_products
from pipelines.p2_impact.run import MAX_PRELIMINARY_ATTEMPTS, Action, decide


def _estado(**kwargs: object) -> EventState:
    base: dict[str, object] = {
        "usgs_id": "us7000sint",
        "estado": EventStatus.DETECTADO,
        "mag": 6.9,
        "lon": -77.85,
        "lat": 6.42,
        "depth_km": 24.7,
        "lugar": "Choco, Colombia",
        "origen_utc": "2026-08-19T05:00:00Z",
    }
    base.update(kwargs)
    return EventState(**base)  # type: ignore[arg-type]


def test_primer_shakemap_dispara_reporte_completo(detail_con_productos: dict[str, Any]) -> None:
    decision = decide(_estado(), parse_products(detail_con_productos))
    assert decision.action is Action.COMPLETO
    assert decision.shakemap_version == 3


def test_version_ya_procesada_se_omite(detail_con_productos: dict[str, Any]) -> None:
    estado = _estado(
        estado=EventStatus.PUBLICADO,
        versiones_procesadas=ProcessedVersions(shakemap=3, groundfailure=2),
    )
    decision = decide(estado, parse_products(detail_con_productos))
    assert decision.action is Action.OMITIR


def test_version_nueva_reemite(detail_con_productos: dict[str, Any]) -> None:
    estado = _estado(
        estado=EventStatus.PUBLICADO,
        versiones_procesadas=ProcessedVersions(shakemap=2, groundfailure=2),
    )
    decision = decide(estado, parse_products(detail_con_productos))
    assert decision.action is Action.COMPLETO
    assert decision.razon == "ShakeMap v2 -> v3"


def test_ground_failure_nuevo_tambien_reemite(detail_con_productos: dict[str, Any]) -> None:
    estado = _estado(
        estado=EventStatus.PUBLICADO,
        versiones_procesadas=ProcessedVersions(shakemap=3, groundfailure=1),
    )
    decision = decide(estado, parse_products(detail_con_productos))
    assert decision.action is Action.COMPLETO
    assert "Ground Failure" in decision.razon


def test_sin_shakemap_va_a_preliminar(detail_sin_shakemap: dict[str, Any]) -> None:
    decision = decide(_estado(), parse_products(detail_sin_shakemap))
    assert decision.action is Action.PRELIMINAR


def test_la_ventana_de_reintentos_se_agota(detail_sin_shakemap: dict[str, Any]) -> None:
    """RF-03: se reintenta cada 30 min hasta 6 h, y no mas."""
    estado = _estado(estado=EventStatus.PRELIMINAR, intentos_preliminar=MAX_PRELIMINARY_ATTEMPTS)
    assert decide(estado, parse_products(detail_sin_shakemap)).action is Action.AGOTADO


def test_ventana_de_reintentos_es_de_seis_horas() -> None:
    assert MAX_PRELIMINARY_ATTEMPTS == 12


def test_evento_descartado_nunca_se_procesa(detail_con_productos: dict[str, Any]) -> None:
    estado = _estado(estado=EventStatus.DESCARTADO)
    assert decide(estado, parse_products(detail_con_productos)).action is Action.OMITIR


@pytest.mark.parametrize("repeticiones", [2, 3])
def test_la_decision_es_estable(detail_con_productos: dict[str, Any], repeticiones: int) -> None:
    """Dos corridas sobre el mismo (estado, productos) deciden lo mismo."""
    estado, productos = _estado(), parse_products(detail_con_productos)
    decisiones = {decide(estado, productos).action for _ in range(repeticiones)}
    assert len(decisiones) == 1
