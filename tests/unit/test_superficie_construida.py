"""La nota de superficie construida en el reporte (§6.4).

El sistema publica cifras que sabe incompletas: el conteo de edificaciones de
Overture tiene huecos en asentamientos informales y zona rural dispersa, que es
donde vive la poblacion mas expuesta. GHS-BUILT-S ve por satelite lo que OSM no
mapeo, y esta nota es la unica forma que tiene el reporte de decir "esta cifra
mia se queda corta" sin callarse ni inventar.
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from pipelines.p3_report.markdown import (
    M2_POR_EDIFICACION,
    UMBRAL_HUECO_MAPEO,
    render_markdown,
)
from pipelines.p3_report.model import (
    Descargas,
    Evento,
    Incertidumbre,
    Inputs,
    MunicipioTop,
    Report,
    Totales,
)


@pytest.fixture
def reporte() -> Report:
    """Reporte minimo. Las cifras de cada prueba se sobrescriben con _con()."""
    return Report(
        event=Evento(
            usgs_id="us7000sint",
            mag=6.9,
            depth_km=24.7,
            utc="2026-08-19T05:00:00Z",
            lugar="38 km al W de Bahia Solano, Choco, Colombia",
        ),
        inputs=Inputs(shakemap_version=3, groundfailure_version=2, exposure_manifest="col-v0.5"),
        totales=Totales(pop_mmi6p=1_240_000, pop_mmi7p=347_129, bld_mmi7p=96_500),
        top_municipios=(MunicipioTop("27001", "Quibdo", 7.4, 118_000),),
        incertidumbre=Incertidumbre(pop_discrepancia_pct=14.2),
        descargas=Descargas(csv_adm2="adm2.csv"),
    )


def _con(reporte: Report, **totales: float) -> Report:
    return replace(reporte, totales=replace(reporte.totales, **totales))


def test_sin_dato_de_satelite_no_aparece_la_fila(reporte: Report) -> None:
    """Un activo viejo, sin la columna, no debe ensuciar el reporte."""
    md = render_markdown(_con(reporte, built_m2_mmi7p=0.0))
    assert "Superficie construida" not in md


def test_con_dato_aparece_en_km2(reporte: Report) -> None:
    """m² por pais son numeros ilegibles; el reporte se lee en km²."""
    md = render_markdown(_con(reporte, built_m2_mmi7p=12_500_000.0, bld_mmi7p=200_000.0))
    assert "Superficie construida en MMI≥7" in md
    assert "12,5 km²" in md


def test_cuando_cuadra_no_se_advierte_nada(reporte: Report) -> None:
    """Si el satelite ve lo que explican las edificaciones, no hay hueco."""
    bld = 1_000.0
    md = render_markdown(_con(reporte, bld_mmi7p=bld, built_m2_mmi7p=bld * M2_POR_EDIFICACION))
    assert "se queda corto" not in md


def test_un_hueco_grande_se_advierte(reporte: Report) -> None:
    """El caso que motiva la capa: mucho construido y pocas edificaciones."""
    bld = 1_000.0
    md = render_markdown(_con(reporte, bld_mmi7p=bld, built_m2_mmi7p=bld * M2_POR_EDIFICACION * 3))
    assert "3,0 veces" in md
    assert "se queda corto" in md


@pytest.mark.parametrize("factor", [1.0, UMBRAL_HUECO_MAPEO - 0.01])
def test_por_debajo_del_umbral_no_se_advierte(reporte: Report, factor: float) -> None:
    """Advertir siempre convertiria la nota en ruido que nadie lee."""
    bld = 1_000.0
    md = render_markdown(
        _con(reporte, bld_mmi7p=bld, built_m2_mmi7p=bld * M2_POR_EDIFICACION * factor)
    )
    assert "se queda corto" not in md


def test_sin_edificaciones_no_se_divide_por_cero(reporte: Report) -> None:
    """Un evento en zona sin nada mapeado no puede tumbar el render."""
    md = render_markdown(_con(reporte, bld_mmi7p=0.0, built_m2_mmi7p=500_000.0))
    assert "se queda corto" not in md
    assert md


def test_la_advertencia_dice_donde_esta_el_hueco(reporte: Report) -> None:
    """Sin el porque, la cifra parece un error del sistema y no del mapa."""
    md = render_markdown(_con(reporte, bld_mmi7p=1_000.0, built_m2_mmi7p=400_000.0))
    assert "asentamiento informal" in md


# --- Desglose de vias -------------------------------------------------------


def test_con_desglose_se_publican_dos_filas(reporte: Report) -> None:
    """No es lo mismo que quede cortada una troncal que una calle de barrio."""
    md = render_markdown(_con(reporte, road_km_mmi7p=1000.0, road_km_principal_mmi7p=300.0))
    assert "Vias primarias y secundarias en MMI≥7" in md
    assert "Vias locales en MMI≥7" in md
    assert "Kilometros de via en MMI≥7" not in md


def test_la_via_local_es_el_resto(reporte: Report) -> None:
    md = render_markdown(_con(reporte, road_km_mmi7p=1000.0, road_km_principal_mmi7p=300.0))
    assert "700 km" in md


def test_un_activo_sin_desglose_publica_el_total(reporte: Report) -> None:
    """Compatibilidad: un reporte anterior no tiene la columna nueva."""
    md = render_markdown(_con(reporte, road_km_mmi7p=1000.0, road_km_principal_mmi7p=0.0))
    assert "Kilometros de via en MMI≥7" in md
    assert "Vias locales" not in md


def test_la_local_nunca_sale_negativa(reporte: Report) -> None:
    """Si por redondeo la principal supera al total, no se publica un negativo."""
    md = render_markdown(_con(reporte, road_km_mmi7p=100.0, road_km_principal_mmi7p=120.0))
    assert "-" not in md.split("Vias locales en MMI≥7")[1].split("|")[1]
