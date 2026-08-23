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

PENDIENTES: list[tuple[str, Callable[[], object]]] = [
    ("P0 build de exposure_h3", lambda: build_country("COL", out_dir=Path("/tmp/x"))),
]


@pytest.mark.parametrize(("etapa", "llamada"), PENDIENTES, ids=[nombre for nombre, _ in PENDIENTES])
def test_las_etapas_pendientes_fallan_ruidosamente(
    etapa: str, llamada: Callable[[], object]
) -> None:
    with pytest.raises(NotImplementedError, match="Pendiente"):
        llamada()
