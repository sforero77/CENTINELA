"""Fixtures congeladas de los dos eventos que motivan el proyecto."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

GOLDEN = Path(__file__).parent.parent / "fixtures" / "golden"
CHOCO = GOLDEN / "choco_2026_08_10"
VENEZUELA = GOLDEN / "venezuela_2026_06_24"


def _cargar(path: Path) -> dict[str, Any]:
    payload: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return payload


@pytest.fixture
def choco_detail() -> dict[str, Any]:
    return _cargar(CHOCO / "detail_superseded.json")


@pytest.fixture
def choco_contornos() -> dict[str, Any]:
    """Contornos MMI reales del ShakeMap v7 de Chocó."""
    return _cargar(CHOCO / "cont_mmi_v7.json")


@pytest.fixture
def choco_feed() -> dict[str, Any]:
    return _cargar(CHOCO / "feed_reconstruido.json")


@pytest.fixture
def venezuela_feed() -> dict[str, Any]:
    return _cargar(VENEZUELA / "feed_reconstruido.json")


@pytest.fixture
def venezuela_details() -> dict[str, dict[str, Any]]:
    return {
        "us6000t7zp": _cargar(VENEZUELA / "detail_us6000t7zp_superseded.json"),
        "us6000t7zc": _cargar(VENEZUELA / "detail_us6000t7zc_superseded.json"),
    }
