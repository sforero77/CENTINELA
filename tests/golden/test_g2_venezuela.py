"""G2 — Venezuela, 24 de junio de 2026 (§6.3).

Ademas de las aserciones de G1, valida el bbox y el manejo de **evento doble**:
dos mainshocks que el sistema debe tratar como dos eventos, no como uno con
replica.
"""

from __future__ import annotations

from pathlib import Path

import pytest

FIXTURE_DIR = Path(__file__).parent.parent / "fixtures" / "golden" / "venezuela_2026_06_24"

pytestmark = [
    pytest.mark.golden,
    pytest.mark.skipif(
        not FIXTURE_DIR.exists(),
        reason="Fixture pendiente: T0.1 (usgs_id oficiales) y T0.2 (congelar productos).",
    ),
]


def test_ambos_mainshocks_generan_evento_propio() -> None:
    pytest.fail("Pendiente de fixture (T0.1/T0.2)")


def test_pop_mmi7p_estable() -> None:
    pytest.fail("Pendiente de fixture (T0.1/T0.2)")
