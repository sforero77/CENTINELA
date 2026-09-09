"""Deriva de contrato contra el feed vivo de USGS (§6.2).

Marcado ``network``: excluido de CI de PR, lo corre solo el workflow nocturno.
Su unico trabajo es **alertar**, nunca bloquear un reporte.
"""

from __future__ import annotations

import json

import pytest
from jsonschema import Draft202012Validator

from pipelines.common.constants import USGS_FEED_PRIMARY
from pipelines.common.http import HttpFetcher
from pipelines.common.paths import SCHEMAS_DIR
from pipelines.p1_trigger.feed import feed_url, parse_feed

pytestmark = pytest.mark.network


def test_el_feed_vivo_cumple_el_contrato() -> None:
    payload = HttpFetcher().get_json(feed_url(USGS_FEED_PRIMARY))
    schema = json.loads(
        (SCHEMAS_DIR / "usgs" / "feed-summary.schema.json").read_text(encoding="utf-8")
    )
    errores = [e.message for e in Draft202012Validator(schema).iter_errors(payload)]
    assert errores == [], f"El feed derivo del contrato: {errores[:5]}"


def test_el_feed_vivo_se_parsea_sin_error() -> None:
    """El contrato puede pasar y el parseo fallar igual: probamos los dos."""
    payload = HttpFetcher().get_json(feed_url(USGS_FEED_PRIMARY))
    parse_feed(payload)
