"""Regla de cifras del reporte (RF-06): 2 significativas en prosa."""

from __future__ import annotations

import pytest

from pipelines.common.formatting import (
    format_count_prose,
    format_delta_prose,
    format_number_es,
    round_significant,
)


@pytest.mark.parametrize(
    ("valor", "esperado"),
    [(347_129, 350_000), (1_234_567, 1_200_000), (842, 840), (0.0432, 0.043), (0, 0.0)],
)
def test_redondeo_a_dos_significativas(valor: float, esperado: float) -> None:
    assert round_significant(valor) == pytest.approx(esperado)


def test_redondeo_conserva_signo() -> None:
    assert round_significant(-347_129) == pytest.approx(-350_000)


def test_redondeo_rechaza_digitos_invalidos() -> None:
    with pytest.raises(ValueError, match="digits"):
        round_significant(100, digits=0)


def test_separadores_es_co() -> None:
    assert format_number_es(1_234_567) == "1.234.567"
    assert format_number_es(12.345, decimals=1) == "12,3"


@pytest.mark.parametrize(
    ("valor", "esperado"),
    [
        (347_129, "350 mil"),
        (1_234_567, "1,2 millones"),
        (1_000_000, "1 millon"),
        (41_200, "41 mil"),
        (9_400, "9.400"),
        (1_820, "1.800"),
        (842, "840"),
        (0, "0"),
    ],
)
def test_prosa_legible(valor: float, esperado: str) -> None:
    assert format_count_prose(valor) == esperado


def test_delta_para_changelog() -> None:
    """RF-04: el changelog muestra 'pop MMI>=7: 340k -> 355k'."""
    assert format_delta_prose(340_000, 355_000) == "340 mil → 360 mil"
