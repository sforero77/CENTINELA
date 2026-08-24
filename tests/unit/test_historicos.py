"""Reconstrucciones retrospectivas: lo que pueden y no pueden afirmar.

Procesar un sismo del pasado funciona —el backtest del Chocó es exactamente
eso— y la poblacion puede ser de la epoca, porque GHS-POP publica de 1975 a
2030 en pasos de cinco anos. Lo que no retrocede es la infraestructura:
OpenStreetMap y Overture publican el estado presente.

Esa asimetria tiene que llegar al lector. Si no, "444.281 edificaciones
expuestas" se lee como si hubieran existido entonces.
"""

from __future__ import annotations

from dataclasses import replace

from pipelines.p3_report.markdown import render_markdown
from pipelines.p3_report.model import Report


def test_un_reporte_en_vivo_no_lleva_aviso(reporte: Report) -> None:
    assert "Reconstruccion retrospectiva" not in render_markdown(reporte)


def test_un_historico_lo_declara_arriba(reporte: Report) -> None:
    """El aviso va antes de las cifras, no en las advertencias del final."""
    md = render_markdown(replace(reporte, backtest=True))
    assert "Reconstruccion retrospectiva" in md
    assert md.index("Reconstruccion retrospectiva") < md.index("## Exposicion estimada")


def test_el_aviso_distingue_poblacion_de_infraestructura(reporte: Report) -> None:
    """Es el matiz entero: sin el, el aviso no dice nada util."""
    md = render_markdown(replace(reporte, backtest=True))
    assert "poblacion" in md.lower()
    assert "actuales" in md
    assert "no guardan el pasado" in md or "estado presente" in md


def test_el_flag_viaja_en_el_json(reporte: Report) -> None:
    """El visor lo lee de ahi para marcar la fila."""
    assert render_markdown(reporte) is not None
    assert replace(reporte, backtest=True).to_dict()["backtest"] is True
    assert reporte.to_dict()["backtest"] is False


def test_el_flag_sobrevive_al_roundtrip(reporte: Report) -> None:
    historico = replace(reporte, backtest=True)
    assert Report.from_dict(historico.to_dict()).backtest is True
