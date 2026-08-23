"""Fixtures compartidas.

Regla del proyecto: **ninguna prueba toca la red**. El unico test que consulta
el feed vivo es el nocturno de drift de contrato (§6.2), marcado ``network`` y
excluido de CI de PR.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from pipelines.common.constants import USGS_FEED_BACKFILL, USGS_FEED_PRIMARY
from pipelines.common.http import FixtureFetcher
from pipelines.p1_trigger.feed import feed_url

FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture(*parts: str) -> Any:
    """Carga un JSON de ``tests/fixtures``."""
    return json.loads((FIXTURES.joinpath(*parts)).read_text(encoding="utf-8"))


@pytest.fixture
def feed_payload() -> dict[str, Any]:
    payload: dict[str, Any] = load_fixture("usgs", "feed_4.5_hour.json")
    return payload


@pytest.fixture
def detail_con_productos() -> dict[str, Any]:
    payload: dict[str, Any] = load_fixture("usgs", "detail_with_products.json")
    return payload


@pytest.fixture
def detail_sin_shakemap() -> dict[str, Any]:
    payload: dict[str, Any] = load_fixture("usgs", "detail_no_shakemap.json")
    return payload


@pytest.fixture
def fetcher(feed_payload: dict[str, Any]) -> FixtureFetcher:
    """Fetcher que sirve el mismo feed en ambas URLs consultadas por P1."""
    vacio = {"type": "FeatureCollection", "features": []}
    return FixtureFetcher(
        {
            feed_url(USGS_FEED_PRIMARY): feed_payload,
            feed_url(USGS_FEED_BACKFILL): vacio,
        }
    )


@pytest.fixture
def events_dir(tmp_path: Path) -> Path:
    """Directorio temporal de ``event_state``, aislado por prueba."""
    directory = tmp_path / "events"
    directory.mkdir()
    return directory
