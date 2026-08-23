"""Criterio de relevancia del disparador (RF-01)."""

from __future__ import annotations

from typing import Any

from pipelines.p1_trigger.feed import parse_feed
from pipelines.p1_trigger.filters import evaluate, is_relevant


def test_solo_pasan_los_eventos_en_alcance(feed_payload: dict[str, Any]) -> None:
    relevantes = [c.usgs_id for c in parse_feed(feed_payload) if is_relevant(c)]
    assert relevantes == ["us7000sint", "us7000mxmid"]


def test_razones_de_descarte(feed_payload: dict[str, Any]) -> None:
    razones = {c.usgs_id: evaluate(c).razon for c in parse_feed(feed_payload)}
    assert "umbral" in razones["us7000small"]
    assert razones["us7000faraway"] == "fuera del bbox LATAM"
    assert "no sismico" in razones["us7000quarry"]


def test_el_umbral_es_inclusivo(feed_payload: dict[str, Any]) -> None:
    """M5.5 exacto dispara: el umbral de la espec es M>=5.5."""
    mx = next(c for c in parse_feed(feed_payload) if c.usgs_id == "us7000mxmid")
    assert mx.mag == 5.5
    assert is_relevant(mx)
