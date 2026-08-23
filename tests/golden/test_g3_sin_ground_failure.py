"""G3 — evento profundo sin Ground Failure publicado (§6.3).

A diferencia de G1 y G2, esta prueba no necesita fixtures congeladas: el caso
se reproduce con el feed detail sintetico que ya vive en ``tests/fixtures``.
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
        inputs=Inputs(shakemap_version=2, groundfailure_version=0, exposure_manifest="col-v0.1"),
        totales=Totales(pop_mmi6p=88_000, pop_mmi7p=4_100),
    )
    md = render_markdown(reporte)
    assert "Deslizamiento y licuefaccion" in md
    assert "no ha publicado el producto" in md
    assert "Advertencias" in md
