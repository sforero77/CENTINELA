"""Prorrateo hex <-> municipio (§6.1: la suma municipal == la nacional)."""

from __future__ import annotations

from pipelines.p0_exposure.crosswalk import CrosswalkRow, prorate, validate_fractions


def test_celda_completa_en_un_municipio() -> None:
    assert validate_fractions([CrosswalkRow(1, "05001", 1.0)]) == []


def test_celda_partida_entre_dos_municipios() -> None:
    filas = [CrosswalkRow(1, "05001", 0.6), CrosswalkRow(1, "05002", 0.4)]
    assert validate_fractions(filas) == []


def test_fracciones_que_no_suman_uno_son_error() -> None:
    filas = [CrosswalkRow(1, "05001", 0.6), CrosswalkRow(1, "05002", 0.3)]
    problemas = validate_fractions(filas)
    assert len(problemas) == 1
    assert "no 1" in problemas[0]


def test_fraccion_fuera_de_rango() -> None:
    assert validate_fractions([CrosswalkRow(1, "05001", 1.4)])


def test_el_prorrateo_conserva_el_total() -> None:
    """El invariante que importa: nada de poblacion se pierde en la frontera."""
    filas = [CrosswalkRow(1, "05001", 0.6), CrosswalkRow(1, "05002", 0.4)]
    reparto = prorate(1000.0, filas)
    assert sum(reparto.values()) == 1000.0
    assert reparto == {"05001": 600.0, "05002": 400.0}
