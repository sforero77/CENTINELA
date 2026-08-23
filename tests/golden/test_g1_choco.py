"""G1 — Choco, M7.4, 10 de agosto de 2026 (§6.3).

Es el evento que motiva el proyecto: el pais tardo dias en saber cuanta
poblacion estaba en la zona de intensidad fuerte. La prueba fija que el sistema
habria respondido, y que la respuesta no cambia al refactorizar.
"""

from __future__ import annotations

from pathlib import Path

import pytest

FIXTURE_DIR = Path(__file__).parent.parent / "fixtures" / "golden" / "choco_2026_08_10"

pytestmark = [
    pytest.mark.golden,
    pytest.mark.skipif(
        not FIXTURE_DIR.exists(),
        reason=(
            "Fixture pendiente: T0.1 (usgs_id oficial) y T0.2 (congelar productos "
            "con includesuperseded via libcomcat)."
        ),
    ),
]

#: Tolerancia de la asercion (b): la cifra puede moverse ±0.5 % entre commits.
TOLERANCIA_POP = 0.005


def test_el_trigger_habria_disparado() -> None:
    """Asercion (a): M7.4 en el bbox LATAM entra por el umbral M>=5.5."""
    pytest.fail("Pendiente de fixture (T0.1/T0.2)")


def test_pop_mmi7p_estable() -> None:
    """Asercion (b): la cifra principal no se mueve mas de ±0.5 % entre commits."""
    pytest.fail("Pendiente de fixture (T0.1/T0.2)")


def test_top15_municipios_estable() -> None:
    """Asercion (c): el ranking municipal es estable."""
    pytest.fail("Pendiente de fixture (T0.1/T0.2)")


def test_referencia_la_ultima_version_de_shakemap() -> None:
    """Asercion (d): el reporte v-final consume la ultima version del evento."""
    pytest.fail("Pendiente de fixture (T0.1/T0.2)")
