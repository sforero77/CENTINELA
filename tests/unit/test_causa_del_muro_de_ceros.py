"""La nota del muro de ceros dice la causa que midió, no la que suele ser.

Afirmaba siempre «la sacudida quedó mar adentro o sobre zona despoblada». Es
una de las tres causas posibles y no siempre la cierta:

* `reports/us1000jg5z` la publica para un sismo **bajo Bolivia**, país sin mar,
  a 359 km de profundidad. La causa es la profundidad.
* `reports/usp000jd2q` la publicaba con el epicentro a 5 km de Baní, tierra
  adentro, y con tres municipios alcanzados a MMI 5. La causa es que la
  intensidad llegó a poblado por debajo del umbral desde el que se publica.

Afirmar de menos cuesta una frase; afirmar de más cuesta la credibilidad de
todo lo demás que el reporte dice — que es la lección que el `hilo.txt` ya se
había aplicado con este mismo caso y el `report.md` no.
"""

from __future__ import annotations

from pipelines.p3_report.markdown import _nota_del_muro_de_ceros
from pipelines.p3_report.model import Evento, Inputs, MunicipioTop, Report, Totales


def _reporte(
    *, depth_km: float, municipios: tuple[MunicipioTop, ...] = (), totales: Totales | None = None
) -> Report:
    return Report(
        event=Evento(
            usgs_id="us0000test",
            mag=6.3,
            depth_km=depth_km,
            utc="2026-09-05T00:00:00Z",
            lugar="en algún sitio",
        ),
        inputs=Inputs(shakemap_version=1, groundfailure_version=0, exposure_manifest="x-v1"),
        totales=totales or Totales(),
        top_municipios=municipios,
    )


def test_con_intensidad_sobre_poblado_se_nombra_el_umbral_y_no_el_mar() -> None:
    """El caso de Baní: epicentro tierra adentro, MMI 5 sobre municipio."""
    nota = _nota_del_muro_de_ceros(
        _reporte(
            depth_km=39.8,
            municipios=(MunicipioTop("DO01", "Baní", 5.0, pop_mmi7p=0.0),),
        )
    )
    assert "MMI 5,0" in nota
    assert "territorio habitado" in nota
    assert "mar adentro" not in nota, "sigue afirmando una causa que no midió"


def test_un_sismo_profundo_nombra_la_profundidad() -> None:
    """El caso de Bolivia: 359 km, país sin mar, ningún municipio alcanzado."""
    nota = _nota_del_muro_de_ceros(_reporte(depth_km=359.0))
    assert "359 km de profundidad" in nota
    assert "mar adentro" not in nota, "Bolivia no tiene mar"


def test_un_sismo_somero_sin_municipios_si_puede_decir_mar_adentro() -> None:
    """La causa original sigue siendo cierta cuando lo es, y se conserva."""
    nota = _nota_del_muro_de_ceros(_reporte(depth_km=10.0))
    assert "mar adentro o sobre zona despoblada" in nota


def test_el_umbral_de_profundidad_es_el_de_la_clasificacion_estandar() -> None:
    """70 km: superficial por debajo, intermedio por encima. Lo dice el visor."""
    from pipelines.common.constants import PROFUNDIDAD_INTERMEDIA_KM

    assert PROFUNDIDAD_INTERMEDIA_KM == 70.0
    assert "profundidad" in _nota_del_muro_de_ceros(_reporte(depth_km=70.0))
    assert "mar adentro" in _nota_del_muro_de_ceros(_reporte(depth_km=69.9))


def test_un_reporte_con_cifras_no_lleva_la_nota() -> None:
    """La nota existe para el muro de ceros y solo para él."""
    assert _nota_del_muro_de_ceros(_reporte(depth_km=10.0, totales=Totales(pop_mmi6p=1000.0))) == ""


def test_un_preliminar_no_lleva_la_nota() -> None:
    """Un preliminar publica radios; sus ceros por MMI no son un resultado."""
    from dataclasses import replace

    assert _nota_del_muro_de_ceros(replace(_reporte(depth_km=10.0), preliminar=True)) == ""


def test_ninguna_de_las_tres_ramas_promete_lo_que_no_midio() -> None:
    """Las tres dicen que el cálculo corrió: es lo que el cero significa."""
    for reporte in (
        _reporte(depth_km=39.8, municipios=(MunicipioTop("X", "X", 5.0, pop_mmi7p=0.0),)),
        _reporte(depth_km=359.0),
        _reporte(depth_km=10.0),
    ):
        nota = _nota_del_muro_de_ceros(reporte)
        assert "El cálculo corrió entero." in nota
        assert "no un fallo" in nota


# --- Lo que un preliminar puede afirmar -------------------------------------


def test_un_preliminar_no_dice_que_intento_contrastar_worldpop() -> None:
    """Un preliminar publica radios: no corta por bandas ni calcula una celda.

    Salia con «Ninguna celda dentro de las bandas publicadas tiene población de
    WorldPop con la que contrastar», que describe un contraste intentado y
    vacío. No se intentó.
    """
    from dataclasses import replace

    from pipelines.p3_report.markdown import _linea_discrepancia

    linea = _linea_discrepancia(replace(_reporte(depth_km=25.0), preliminar=True))
    assert "no se calcula en un reporte preliminar" in linea
    assert "Ninguna celda" not in linea


def test_un_reporte_completo_sin_worldpop_si_dice_que_no_habia_con_que_comparar() -> None:
    """La frase original sigue siendo cierta donde lo es."""
    from pipelines.p3_report.markdown import _linea_discrepancia

    linea = _linea_discrepancia(_reporte(depth_km=25.0))
    assert "no se pudo medir" in linea
    assert "Ninguna celda" in linea


def test_la_version_cero_no_se_publica_como_version() -> None:
    """«Ground Failure consumido: v0» se lee como que se consumió algo."""
    from pipelines.p3_report.markdown import _seccion_procedencia

    texto = _seccion_procedencia(_reporte(depth_km=25.0))
    assert "v0" not in texto
    assert "ninguno" in texto


def test_una_version_de_verdad_si_se_publica_como_version() -> None:
    from dataclasses import replace

    from pipelines.p3_report.markdown import _seccion_procedencia
    from pipelines.p3_report.model import Inputs

    reporte = replace(
        _reporte(depth_km=25.0),
        inputs=Inputs(shakemap_version=11, groundfailure_version=3, exposure_manifest="col-v0.6"),
    )
    texto = _seccion_procedencia(reporte)
    assert "**v11**" in texto and "**v3**" in texto
