"""Parseo del feed y contrato USGS (RNF-03)."""

from __future__ import annotations

from typing import Any

import pytest

from pipelines.p1_trigger.feed import FeedContractError, parse_feed


def test_parsea_todas_las_features(feed_payload: dict[str, Any]) -> None:
    assert len(parse_feed(feed_payload)) == 5


def test_campos_del_candidato(feed_payload: dict[str, Any]) -> None:
    choco = parse_feed(feed_payload)[0]
    assert choco.usgs_id == "us7000sint"
    assert choco.mag == 6.9
    assert (choco.lon, choco.lat) == (-77.85, 6.42)
    assert choco.depth_km == 24.7
    assert choco.origen_utc.endswith("Z")
    assert "eventid=us7000sint" in choco.detail_url


def test_epoch_ms_se_convierte_a_utc(feed_payload: dict[str, Any]) -> None:
    choco = parse_feed(feed_payload)[0]
    assert choco.origen_utc == "2026-08-19T05:00:00Z"


def test_coleccion_de_tipo_incorrecto_rompe_el_contrato() -> None:
    with pytest.raises(FeedContractError, match="FeatureCollection"):
        parse_feed({"type": "Feature", "features": []})


def test_feed_sin_lista_features() -> None:
    with pytest.raises(FeedContractError, match="features"):
        parse_feed({"type": "FeatureCollection"})


def test_evento_sin_magnitud_no_se_cuela_como_candidato() -> None:
    """Nunca se acepta; lo que cambio es a quien se lleva por delante.

    Antes, una sola feature rota elevaba y tumbaba la pasada entera sobre un
    feed **mundial**. Ahora se descarta nombrandola y las demas valen — y si no
    se pudiera leer ninguna, eso si sube. Ver
    `test_feed_degrada_por_feature.py`.
    """
    payload = {
        "type": "FeatureCollection",
        "features": [
            {
                "id": "us0000null",
                "properties": {"mag": None, "place": "x", "time": 0, "detail": "u"},
                "geometry": {"type": "Point", "coordinates": [0, 0, 0]},
            },
            {
                "id": "us0000ok",
                "properties": {
                    "mag": 6.0,
                    "place": "x",
                    "time": 0,
                    "updated": 0,
                    "url": "u",
                    "detail": "u",
                },
                "geometry": {"type": "Point", "coordinates": [-75.0, 5.0, 30.0]},
            },
        ],
    }
    leidos = parse_feed(payload)

    assert [c.usgs_id for c in leidos] == ["us0000ok"]


def test_feature_incompleta_no_se_cuela_como_candidato() -> None:
    """Unica feature y esta rota: no se pudo leer ninguna, y eso sube."""
    payload = {
        "type": "FeatureCollection",
        "features": [{"id": "us0000bad", "properties": {"mag": 6.0}}],
    }
    with pytest.raises(FeedContractError):
        parse_feed(payload)
