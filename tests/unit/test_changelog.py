"""El changelog de deltas de RF-04, que estaba escrito a medias y sin conectar.

`Report.changelog` existia, `markdown.py` lo renderizaba, `format_delta_prose`
daba el formato exacto del ejemplo de la espec — y ninguna linea del pipeline lo
llenaba, asi que la seccion no salio en un solo reporte publicado.

Importa durante una emergencia: un ShakeMap se revisa muchas veces —el de
Venezuela llego a v14— y quien ya leyo la version anterior necesita saber que
cambio, no releerla entera.
"""

from __future__ import annotations

from dataclasses import replace

from pipelines.p3_report.changelog import build_changelog
from pipelines.p3_report.model import Report


def _con(reporte: Report, *, version: int | None = None, **totales: float) -> Report:
    """El mismo reporte con otra version y/u otras cifras."""
    nuevo = reporte
    if version is not None:
        nuevo = replace(nuevo, inputs=replace(nuevo.inputs, shakemap_version=version))
    if totales:
        nuevo = replace(nuevo, totales=replace(nuevo.totales, **totales))
    return nuevo


def test_la_primera_emision_no_tiene_con_que_compararse(reporte: Report) -> None:
    """Sin reporte anterior, un changelog seria inventado."""
    assert build_changelog(None, reporte) == ()


def test_una_version_nueva_de_shakemap_se_anuncia(reporte: Report) -> None:
    lineas = build_changelog(reporte, _con(reporte, version=8))

    assert "ShakeMap: v7 → v8" in lineas


def test_el_delta_sale_en_la_prosa_del_ejemplo_de_la_espec(reporte: Report) -> None:
    """RF-04 lo escribe asi: "pop MMI≥7: 340k → 355k"."""
    lineas = build_changelog(reporte, _con(reporte, version=8, pop_mmi7p=2_800_000))

    assert "Poblacion en MMI≥7: 2,4 millones → 2,8 millones" in lineas


def test_un_cambio_que_no_se_ve_publicado_no_se_anuncia(reporte: Report) -> None:
    """Se compara la cifra **redondeada**, que es la que el lector ve.

    Si un ShakeMap nuevo mueve la poblacion de 2.415.793 a 2.415.802, el
    reporte dice "2,4 millones" en los dos sitios. Anunciarlo como cambio seria
    inventar una diferencia que nadie puede observar — y llenar de ruido la
    unica seccion que alguien lee con prisa.
    """
    lineas = build_changelog(reporte, _con(reporte, version=8, pop_mmi7p=2_415_802))

    assert not any("Poblacion en MMI≥7" in linea for linea in lineas)
    assert lineas == (
        "ShakeMap: v7 → v8",
        "Ninguna cifra publicada cambia frente a la version anterior.",
    )


def test_un_shakemap_nuevo_que_no_mueve_nada_lo_dice(reporte: Report) -> None:
    """Que la revision de USGS no cambie nada tambien es informacion.

    Devolver un changelog vacio dejaria la seccion fuera del reporte, y el
    lector no sabria si es que nada cambio o si nadie lo calculo.
    """
    igual = replace(reporte, inputs=replace(reporte.inputs, shakemap_version=8))
    lineas = build_changelog(reporte, igual)

    assert lineas == (
        "ShakeMap: v7 → v8",
        "Ninguna cifra publicada cambia frente a la version anterior.",
    )


def test_ground_failure_tambien_motiva_una_reemision(reporte: Report) -> None:
    """RF-04 nombra las dos: ShakeMap **o** Ground Failure."""
    nuevo = replace(reporte, inputs=replace(reporte.inputs, groundfailure_version=9))

    assert "Ground Failure: v7 → v9" in build_changelog(reporte, nuevo)


def test_se_listan_todas_las_cifras_que_cambiaron(reporte: Report) -> None:
    nuevo = _con(reporte, version=8, pop_mmi7p=3_000_000, bld_mmi7p=600_000)

    lineas = build_changelog(reporte, nuevo)

    assert any("Poblacion en MMI≥7" in linea for linea in lineas)
    assert any("Edificaciones en MMI≥7" in linea for linea in lineas)


def test_el_changelog_llega_al_markdown(reporte: Report) -> None:
    """La seccion se renderizaba desde el principio y nunca recibio nada."""
    from pipelines.p3_report.markdown import render_markdown

    nuevo = _con(reporte, version=8, pop_mmi7p=2_800_000)
    texto = render_markdown(replace(nuevo, changelog=build_changelog(reporte, nuevo)))

    assert "## Cambios frente a la version anterior" in texto
    assert "2,4 millones → 2,8 millones" in texto


def test_dos_reportes_identicos_no_producen_ruido(reporte: Report) -> None:
    """Sin cambio de version ni de cifras, no hay nada que contar.

    Es el caso de un reproceso forzado porque cambio el pipeline y no los
    productos: la seccion no debe aparecer.
    """
    assert build_changelog(reporte, reporte) == ()
