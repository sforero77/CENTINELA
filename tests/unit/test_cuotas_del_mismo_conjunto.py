"""Una cuota necesita que el numerador y el denominador sean del mismo conjunto.

`pop_ls_alta` y `pop_lq_alta` se cuentan sobre las celdas de **MMI≥6** —lo dice
su propio SQL— y el visor las dividia entre `pop_mmi7p`. El razonamiento estaba
escrito y era razonable: «la cuota se mide sobre los expuestos a MMI≥7, que es
la banda con la que se rotula el resto del panel». La cifra no lo era.

Medido sobre los veintisiete reportes publicados:

    us7000nr0v   36.844 / 3.291     = 1.119 %
    us2000bmhe   13.255 / 7.401     =   179 %
    us60003sc0  334.308 / 247.720   =   135 %

y en otros seis el denominador era **cero**, asi que la cuota desaparecia de la
pantalla sin decir por que.

Ninguna de las dos mitades estaba mal por separado. Lo que estaba mal era el
conjunto sobre el que se calculaba cada una, y eso no se ve leyendo ninguna de
las dos.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

RAIZ = Path(__file__).parent.parent.parent
APP = (RAIZ / "site" / "assets" / "app.js").read_text(encoding="utf-8")
#: Sin comentarios: la nota que explica el fallo nombra el denominador viejo, y
#: un guardia que no distingue la explicacion del codigo ya ha fallado aqui
#: cuatro veces.
CODIGO = chr(10).join(linea for linea in APP.splitlines() if not linea.lstrip().startswith("//"))
REPORTES = sorted(p for p in (RAIZ / "reports").glob("*/report.json"))


def _ids(reporte: Path) -> str:
    return reporte.parent.name


def test_la_cuota_de_terreno_se_divide_por_su_propia_banda() -> None:
    """El denominador, en el codigo."""
    assert "cuotaDe(f.valor, t.pop_mmi6p)" in CODIGO, (
        "la cuota de falla de terreno ya no se divide por su propia banda"
    )
    assert "cuotaDe(f.valor, t.pop_mmi7p)" not in CODIGO, (
        "la cuota de falla de terreno vuelve a dividirse por otra banda"
    )


def test_la_etiqueta_nombra_el_universo_de_la_cuota() -> None:
    """Una cuota sin su universo escrito al lado es media cifra."""
    assert "de los expuestos en MMI≥6" in APP


@pytest.mark.parametrize("reporte", REPORTES, ids=_ids)
def test_ninguna_cuota_publicada_pasa_del_cien_por_cien(reporte: Path) -> None:
    """Con el denominador bueno, la cuota es una cuota en los veintisiete."""
    totales = json.loads(reporte.read_text(encoding="utf-8"))["totales"]
    base = totales["pop_mmi6p"]
    for clave in ("pop_ls_alta", "pop_lq_alta"):
        valor = totales[clave]
        if valor <= 0:
            continue
        assert base > 0, (
            f"{clave} vale {valor:,.0f} y la poblacion en MMI>=6 es cero: "
            f"el numerador no puede salir de un conjunto vacio"
        )
        assert valor <= base * 1.000001, (
            f"{clave} = {valor:,.0f} supera a los {base:,.0f} expuestos en MMI>=6, "
            f"que es el conjunto del que se cuenta"
        )


def test_el_conteo_de_terreno_sale_de_la_banda_seis() -> None:
    """La premisa del arreglo, leida del SQL que produce la cifra."""
    from pipelines.common.constants import GROUND_FAILURE_HIGH_PROB, MMI_BAND_AGE_BREAKDOWN
    from pipelines.p2_impact.pipeline import SQL_TOTALES

    sql = SQL_TOTALES.format(edad=MMI_BAND_AGE_BREAKDOWN, gf=GROUND_FAILURE_HIGH_PROB)
    for alias in ("pop_ls_alta", "pop_lq_alta"):
        linea = next(line for line in sql.splitlines() if alias in line)
        # La expresion ocupa dos lineas; se busca el `WHEN` de la anterior.
        indice = sql.splitlines().index(linea)
        expresion = "\n".join(sql.splitlines()[max(0, indice - 1) : indice + 1])
        assert "mmi_max >= 6" in expresion, (
            f"{alias} ya no se cuenta sobre MMI>=6; la cuota del visor divide por esa banda"
        )


def test_el_reporte_dice_sobre_que_banda_cuenta() -> None:
    """El markdown publicaba la cifra sin nombrar su banda."""
    from pipelines.p3_report.markdown import _linea_ground_failure
    from pipelines.p3_report.model import Evento, Inputs, Report, Totales

    reporte = Report(
        event=Evento(usgs_id="us0000x", mag=7.0, depth_km=10.0, utc="", lugar=""),
        inputs=Inputs(shakemap_version=1, groundfailure_version=1, exposure_manifest="x"),
        totales=Totales(pop_mmi6p=1000.0, pop_lq_alta=100.0),
    )
    assert "celdas de MMI≥6" in _linea_ground_failure(reporte, "lq", 100.0)
