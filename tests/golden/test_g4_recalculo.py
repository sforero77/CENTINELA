"""G4 — el golden que RECALCULA. Chocó, M7,4, `us6000tjl2`.

LOS OTROS GOLDEN NO RECALCULAN NADA.

`_reporte_publicado()` abre un `report.json` versionado y comprueba que sigue
diciendo lo que decía. Es un checksum de un artefacto, no una prueba de
regresión numérica: contando llamadas durante la suite completa, `build_report`
y `run_impact` tenían **cero**. La costura

    compute_impact -> ImpactTotals -> Report -> to_dict -> report.json

no la atravesaba ninguna prueba, y por ahí se colaron las siete columnas de la
banda MMI≥6 que nunca llegaban al JSON, y el `LIMIT 15` que seleccionaba por
una columna distinta de la que publicaba.

Esto ejecuta la cadena entera contra insumos congelados —el `cont_mmi_v7.json`
que ya estaba versionado, más el activo de Colombia recortado a las 69.545
celdas que ese ShakeMap toca— y fija las diecinueve cifras y el top-15. Tarda
1,8 s.

**Qué fija y qué no.** Fija que un cambio de código no mueva una cifra
publicada. NO certifica que el activo esté bien: el recorte viene del activo de
Colombia tal como está publicado hoy, que se construyó con las funciones
geodésicas llamadas al revés, así que sus kilómetros de vía son los de entonces.
Cuando el activo se reconstruya, estas cifras se moverán y esta prueba lo dirá
— y la respuesta correcta será regenerar la fixture con
`scripts/fixture_golden.py`, que existe para que eso cueste un comando.

Las bandas etarias del recorte sí se reescalaron con la regla vigente, para que
la fixture sea un activo que `validate_age_bands` acepte.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from pipelines.p2_impact.pipeline import build_report, compute_impact
from pipelines.p2_impact.products import parse_products
from pipelines.p3_report.model import Report

pytestmark = [pytest.mark.golden, pytest.mark.geo]

CHOCO = Path(__file__).parent.parent / "fixtures" / "golden" / "choco_2026_08_10"
ACTIVO = CHOCO / "exposure_recortado.parquet"

#: Las diecinueve cifras nacionales, recalculadas. No se copian de ningún
#: artefacto publicado: salen de correr el pipeline sobre la fixture.
#:
#: CAMBIARON EL 21-NOV-2026 POR LA REGLA, NO POR LOS DATOS (`report/2.0`): las
#: bandas son clases USGS (VI ≥5,5, VII ≥6,5, VIII ≥7,5). Contra las filas de
#: PAGER de `pager_exposures.json` —que usan ese mismo corte— la clase VII pasa
#: de 2,4 a 5,2 millones (PAGER: 6,5) y Cali entra en el ranking con 1,8
#: millones en clase VII, donde antes no figuraba.
TOTALES_ESPERADOS: dict[str, float] = {
    "pop_mmi6p": 8190627.714915011,
    "pop_mmi7p": 5164740.703187234,
    "pop_mmi8p": 473703.2813903894,
    "pop_65p_mmi7p": 613536.5516233541,
    "pop_65p_mmi6p": 958813.3491521424,
    "bld_mmi6p": 1617433.0,
    "built_m2_mmi6p": 244725199.0,
    "health_mmi6p": 2109.0,
    "edu_mmi6p": 3383.0,
    "road_km_mmi6p": 39886.73552676969,
    "road_km_principal_mmi6p": 3853.7415012738866,
    "bld_mmi7p": 774567.0,
    "built_m2_mmi7p": 133639352.0,
    "health_mmi7p": 1548.0,
    "edu_mmi7p": 1793.0,
    "road_km_mmi7p": 17248.555252650014,
    "road_km_principal_mmi7p": 1911.0002640505024,
    "pop_ls_alta": 0.0,
    "pop_lq_alta": 0.0,
}

#: El ranking municipal, por código DIVIPOLA. Por código y no por nombre: el
#: código es el identificador y el nombre depende del diccionario administrativo,
#: que es otra pieza y tiene sus propias pruebas.
TOP_ESPERADO: list[tuple[str, float]] = [
    ("76001", 1803170.3542415611),
    ("66001", 507893.18319610506),
    ("76109", 443236.81375339534),
    ("63001", 339900.03362934757),
    ("17001", 305395.40249430016),
    ("76834", 264722.73849685676),
    ("66170", 181223.86692177504),
    ("76147", 129910.50064553693),
    ("27001", 112430.19337610714),
    ("66682", 71016.91261530947),
    ("63130", 54810.41255925223),
    ("63401", 54278.832213515416),
    ("17873", 44080.377973821014),
    ("76130", 41716.96294990182),
    ("76895", 39669.865389760584),
]

CELDAS_ALCANZADAS = 69_545
MUNICIPIOS_ALCANZADOS = 297


def _correr() -> tuple[Report, Any]:
    """La cadena entera: contornos + activo -> impacto -> reporte."""
    from pipelines.p2_impact.exposure_join import connect
    from pipelines.p2_impact.run import _cargar_admin_lookup, reconstruct_backtest_state

    detail = json.loads((CHOCO / "detail_superseded.json").read_text(encoding="utf-8"))
    products = parse_products(detail)
    state = reconstruct_backtest_state(detail)
    glob = str(ACTIVO)

    con = connect()
    _cargar_admin_lookup(con, glob, None)
    totales = compute_impact(
        con,
        products,
        exposure_glob=glob,
        contornos=CHOCO / "cont_mmi_v7.json",
        deslizamiento=None,
        licuefaccion=None,
    )
    return build_report(con, state, products, totales, manifest_id="col-v0.6"), con


@pytest.fixture(scope="module")
def recalculado() -> Report:
    reporte, _ = _correr()
    return reporte


def test_la_fixture_existe_y_pesa_lo_que_dice() -> None:
    """Sin el activo recortado esta prueba no prueba nada, y hay que notarlo."""
    assert ACTIVO.exists(), "falta el activo recortado; regenerarlo con scripts/fixture_golden.py"
    assert ACTIVO.stat().st_size < 6_000_000, "la fixture creció; no debe versionarse un activo"


@pytest.mark.parametrize("campo", sorted(TOTALES_ESPERADOS))
def test_cada_cifra_nacional_se_recalcula_igual(recalculado: Report, campo: str) -> None:
    """Una por una: así el fallo dice cuál se movió, no que 'algo cambió'."""
    obtenido = recalculado.totales.to_dict()[campo]
    assert obtenido == pytest.approx(TOTALES_ESPERADOS[campo], rel=1e-9)


def test_las_diecinueve_cifras_estan_fijadas(recalculado: Report) -> None:
    """Una cifra nueva sin ancla es una cifra sin vigilancia."""
    assert set(recalculado.totales.to_dict()) == set(TOTALES_ESPERADOS)


def test_el_ranking_municipal_se_recalcula_igual(recalculado: Report) -> None:
    obtenido = [(m.adm2_id, m.pop_mmi7p) for m in recalculado.top_municipios]
    assert [c for c, _ in obtenido] == [c for c, _ in TOP_ESPERADO]
    for (codigo, esperado), (_, real) in zip(TOP_ESPERADO, obtenido, strict=True):
        assert real == pytest.approx(esperado, rel=1e-9), f"se movió {codigo}"


def test_el_ranking_va_de_mas_a_menos(recalculado: Report) -> None:
    """La propiedad que el `LIMIT 15` por otra columna rompía."""
    cifras = [m.pop_mmi7p for m in recalculado.top_municipios]
    assert cifras == sorted(cifras, reverse=True)


def test_el_corte_alcanza_las_celdas_y_municipios_esperados() -> None:
    _, con = _correr()
    assert con.execute("SELECT count(*) FROM impact_h3").fetchone()[0] == CELDAS_ALCANZADAS
    assert con.execute("SELECT count(*) FROM impact_adm2").fetchone()[0] == MUNICIPIOS_ALCANZADOS


def test_el_reporte_sobrevive_a_ida_y_vuelta_por_json(recalculado: Report, tmp_path: Path) -> None:
    """La costura completa, incluido `write_report_bundle`.

    Es el tramo que no ejercitaba nadie y por donde se perdieron siete columnas.
    """
    from pipelines.p3_report.run import write_report_bundle

    escritos = write_report_bundle(recalculado, [], reports_root=tmp_path)
    en_disco = json.loads((tmp_path / "us6000tjl2" / "report.json").read_text(encoding="utf-8"))

    assert "report_json" in " ".join(escritos)
    for campo, esperado in TOTALES_ESPERADOS.items():
        assert en_disco["totales"][campo] == pytest.approx(esperado, rel=1e-9), (
            f"{campo} no llegó al report.json"
        )

    vuelta = Report.from_dict(en_disco)
    assert vuelta.totales == recalculado.totales


def test_la_discrepancia_se_mide_y_no_es_cero(recalculado: Report) -> None:
    """`None` significa "no se pudo medir" y 0,0 "coinciden": no son lo mismo."""
    assert recalculado.incertidumbre.pop_discrepancia_pct == pytest.approx(0.4, abs=0.05)


# --- Que este golden tenga dientes ------------------------------------------


def test_una_mutacion_del_sql_mueve_las_cifras() -> None:
    """EL CRITERIO DE ACEPTACION: romper el arreglo y comprobar que falla.

    Nueve mutaciones del SQL que produce las cifras nacionales sobrevivieron con
    la suite entera en verde, entre ellas mover el corte de MMI≥7 a MMI≥8. Con
    este golden puesto, esa mutación tiene que moverlas.

    Se comprueba aquí y no en un documento: una prueba de regresión que nadie ha
    intentado romper es una prueba de la que no se sabe nada.
    """
    import pipelines.p2_impact.pipeline as modulo

    original = modulo.SQL_TOTALES
    try:
        modulo.SQL_TOTALES = original.replace(
            "SUM(CASE WHEN mmi_max >= 6.5 THEN pop_total ELSE 0 END)      AS pop_mmi7p",
            "SUM(CASE WHEN mmi_max >= 7.5 THEN pop_total ELSE 0 END)      AS pop_mmi7p",
        )
        assert original != modulo.SQL_TOTALES, "la mutación no se aplicó"
        mutado, _ = _correr()
    finally:
        modulo.SQL_TOTALES = original

    assert mutado.totales.pop_mmi7p != pytest.approx(TOTALES_ESPERADOS["pop_mmi7p"], rel=1e-9), (
        "mover el corte de MMI≥7 a MMI≥8 no movió la cifra: el golden no vigila nada"
    )
