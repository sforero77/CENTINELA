"""Inventario vivo de las etapas pendientes.

Estas pruebas no verifican comportamiento: verifican **honestidad**. Cada
etapa sin implementar debe fallar de forma ruidosa y explicita, no devolver
silenciosamente un cero que acabaria publicado como cifra.

Cuando una etapa se implemente, su entrada aqui se borra y se reemplaza por
pruebas reales. La lista encogiendo es el indicador de avance de la Fase 0.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from pipelines.p0_exposure.build import build_country
from pipelines.p3_report.static_map import MapVariant, render_map

PENDIENTES: list[tuple[str, Callable[[], object]]] = [
    ("P0 build de exposure_h3", lambda: build_country("COL", out_dir=Path("/tmp/x"))),
]


@pytest.mark.parametrize(("etapa", "llamada"), PENDIENTES, ids=[nombre for nombre, _ in PENDIENTES])
def test_las_etapas_pendientes_fallan_ruidosamente(
    etapa: str, llamada: Callable[[], object]
) -> None:
    with pytest.raises(NotImplementedError, match="Pendiente"):
        llamada()


def test_render_de_mapa_pendiente(tmp_path: Path) -> None:
    from pipelines.p3_report.model import Evento, Inputs, Report, Totales

    reporte = Report(
        event=Evento("us1", 6.0, 10.0, "2026-01-01T00:00:00Z", "x"),
        inputs=Inputs(1, 0, "m"),
        totales=Totales(),
    )
    with pytest.raises(NotImplementedError, match="Pendiente"):
        render_map(reporte, MapVariant.GENERAL, tmp_path / "m.png")
