"""Como sale publicada la falla de terreno, que es donde estaba el enganio.

DOS COSAS QUE EL REPORTE AFIRMABA Y NO ERAN CIERTAS.

**Una.** «Población en celdas con probabilidad **alta** de licuefacción:
1,6 millones». El producto Ground Failure de USGS entrega, para el modelo de
Zhu (2017), **cobertura areal**: la fraccion del area de la celda que se espera
cubierta. Un 0,10 no es "una probabilidad del 10 %", y "alta" no es una
categoria que USGS publique a ese valor. USGS ademas calcula su exposicion como
poblacion **ponderada** por esa cobertura, y publica ~460 mil para el mismo
evento y el mismo producto. Dos preguntas distintas sobre el mismo raster, y el
reporte publicaba la nuestra sola.

**Dos.** «Deslizamiento: 0», en un M7,4 sobre la cordillera Occidental cuyo
mismo producto trae alerta **naranja** con ~1.400 personas expuestas. El cero es
cierto —ninguna celda llega al umbral— y se lee como "no hay exposicion a
deslizamiento". La guardia que ya existia tapa el NaN de fuera de la huella del
modelo; el cero por debajo del umbral es el que enganiaba.
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from pipelines.p3_report.markdown import render_markdown
from pipelines.p3_report.model import GroundFailureUSGS, Report, Totales

CHOCO = GroundFailureUSGS(
    ls_alerta_usgs="orange",
    ls_pop_usgs="1400",
    lq_alerta_usgs="red",
    lq_pop_usgs="460000",
)


def test_la_licuefaccion_no_se_publica_como_probabilidad(reporte_completo: Report) -> None:
    md = render_markdown(replace(reporte_completo, ground_failure_usgs=CHOCO))

    assert "cobertura areal por licuefacción" in md
    assert "probabilidad **alta de licuefacción**" not in md


def test_el_deslizamiento_si_es_probabilidad(reporte_completo: Report) -> None:
    """La otra mitad: Jessee (2018) si entrega probabilidad. No son lo mismo."""
    md = render_markdown(replace(reporte_completo, ground_failure_usgs=CHOCO))

    assert "probabilidad de deslizamiento" in md


def test_la_cifra_propia_dice_en_que_se_diferencia_de_la_de_usgs(
    reporte_completo: Report,
) -> None:
    md = render_markdown(replace(reporte_completo, ground_failure_usgs=CHOCO))

    assert "No son las de USGS" in md
    assert "pondera" in md


def test_un_cero_junto_a_una_alerta_viva_imprime_la_alerta(reporte_completo: Report) -> None:
    """El caso del Chocó: nuestro conteo da 0 y USGS dice naranja."""
    sin_deslizamiento = replace(
        reporte_completo,
        totales=replace(reporte_completo.totales, pop_ls_alta=0.0),
        ground_failure_usgs=CHOCO,
    )

    md = render_markdown(sin_deslizamiento)

    assert "alerta **naranja**" in md, "el cero sigue saliendo pelado"
    assert "1.400" in md
    assert "no dice que no haya exposición" in md


def test_una_alerta_verde_no_se_imprime(reporte_completo: Report) -> None:
    """Solo se cita a USGS cuando USGS dice algo. Verde no anade nada."""
    verde = replace(
        reporte_completo,
        ground_failure_usgs=GroundFailureUSGS(ls_alerta_usgs="green", lq_alerta_usgs="green"),
    )

    md = render_markdown(verde)

    assert "alerta **verde**" not in md


def test_sin_producto_de_usgs_la_seccion_sigue_saliendo(reporte_completo: Report) -> None:
    """Un reporte antiguo no trae el bloque nuevo y tiene que renderizar igual."""
    md = render_markdown(replace(reporte_completo, totales=Totales()))

    assert "## Deslizamiento y licuefacción" in md


def test_el_bloque_de_usgs_viaja_al_json_y_vuelve(reporte_completo: Report) -> None:
    ida = replace(reporte_completo, ground_failure_usgs=CHOCO)

    vuelta = Report.from_dict(ida.to_dict())

    assert vuelta.ground_failure_usgs == CHOCO


def test_un_reporte_sin_el_bloque_se_relee_sin_romperse(reporte_completo: Report) -> None:
    """Los veintiun reportes publicados antes del 1-sep-2026 no lo traen."""
    crudo = reporte_completo.to_dict()
    del crudo["ground_failure_usgs"]

    vuelta = Report.from_dict(crudo)

    assert vuelta.ground_failure_usgs.vacio


@pytest.mark.geo
def test_un_raster_en_otro_crs_no_publica_ceros(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """Sin esta guardia, `sample` devolvia nodata para todo y `nan_to_num` lo
    convertia en 0.0: "0 personas en zona de licuefacción" con la misma cara que
    una cifra real, y sin ningun assert de cobertura detras que lo cazara."""
    import numpy as np
    import rasterio
    from rasterio.transform import from_origin

    from pipelines.p2_impact.ground_failure import sample_rasters

    ruta = tmp_path / "proyectado.tif"
    with rasterio.open(
        ruta,
        "w",
        driver="GTiff",
        height=4,
        width=4,
        count=1,
        dtype="float32",
        crs="EPSG:3857",
        transform=from_origin(-8_500_000, 600_000, 250, 250),
    ) as dst:
        dst.write(np.full((4, 4), 0.5, dtype="float32"), 1)

    with pytest.raises(ValueError, match="no llega en coordenadas geograficas"):
        sample_rasters(None, ruta, [614_299_631_221_735_423])
