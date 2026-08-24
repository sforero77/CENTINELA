"""G3 — evento sin Ground Failure publicado (§6.3).

No necesita fixture congelada: el caso se reproduce con el detail sintetico de
``tests/fixtures/usgs``.

Nota de v0.10: la espec describia G3 como «evento profundo». Chocó fue a 110 km
y **si** tiene Ground Failure (v7), asi que la profundidad no es el criterio.
Lo que hay que probar es la ausencia del producto, venga de donde venga.
"""

from __future__ import annotations

from typing import Any

import pytest

from pipelines.p2_impact.products import parse_products
from pipelines.p3_report.markdown import render_markdown
from pipelines.p3_report.model import Evento, Inputs, Report, Totales

pytestmark = pytest.mark.golden


def test_un_evento_sin_productos_no_rompe_el_parseo(
    detail_sin_shakemap: dict[str, Any],
) -> None:
    productos = parse_products(detail_sin_shakemap)
    assert productos.ground_failure is None
    assert productos.groundfailure_version == 0


def test_el_reporte_omite_la_seccion_con_nota_y_no_falla() -> None:
    reporte = Report(
        event=Evento("us7000deep", 6.4, 210.0, "2026-05-02T11:00:00Z", "Norte de Chile"),
        inputs=Inputs(shakemap_version=2, groundfailure_version=0, exposure_manifest="col-v0.3"),
        totales=Totales(pop_mmi6p=88_000, pop_mmi7p=4_100),
    )
    md = render_markdown(reporte)
    assert "Deslizamiento y licuefaccion" in md
    assert "no ha publicado el producto" in md
    assert "Advertencias" in md


def test_la_profundidad_no_predice_la_ausencia_de_ground_failure(
    choco_detail: dict[str, Any],
) -> None:
    """Chocó, a 110 km, si tiene Ground Failure: G3 no puede basarse en eso."""
    assert parse_products(choco_detail).groundfailure_version == 7
