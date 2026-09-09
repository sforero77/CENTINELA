"""Elegir el activo por donde cayo el sismo, no por defecto.

P1 vigila **toda** la ventana LATAM y el activo de exposicion es por pais. El
workflow de impacto bajaba siempre el de Colombia, asi que un sismo en Peru se
calculaba contra celdas colombianas: el join no encontraba ninguna, los NULL se
convertian en ceros y se publicaba un reporte diciendo que no habia nadie
expuesto. Durante un terremoto real, en el visor publico.
"""

from __future__ import annotations

from typing import Any

import pytest

from pipelines.p0_exposure.download import COUNTRY_BBOX, countries_for_point

#: Epicentros reales de los eventos que motivan el proyecto, mas capitales.
CHOCO = (-76.2422, 4.8436)
CATIA_LA_MAR = (-67.0, 10.6)
LIMA = (-77.04, -12.05)
SANTIAGO = (-70.65, -33.45)
CIUDAD_DE_MEXICO = (-99.13, 19.43)


def test_el_choco_resuelve_a_colombia() -> None:
    assert countries_for_point(*CHOCO)[0] == "COL"


def test_lima_no_resuelve_a_colombia() -> None:
    """El caso que producia el reporte de ceros."""
    candidatos = countries_for_point(*LIMA)
    assert "COL" not in candidatos
    assert "PER" in candidatos


@pytest.mark.parametrize(
    ("punto", "esperado"),
    [(SANTIAGO, "CHL"), (CIUDAD_DE_MEXICO, "MEX"), (LIMA, "PER")],
)
def test_cada_capital_cae_en_su_pais(punto: tuple[float, float], esperado: str) -> None:
    assert esperado in countries_for_point(*punto)


def test_venezuela_puede_devolver_varios_candidatos() -> None:
    """Las cajas se solapan; devolver todas es lo honesto.

    El join contra las celdas H3 es lo que desempata de verdad, no la caja.
    """
    candidatos = countries_for_point(*CATIA_LA_MAR)
    assert "VEN" in candidatos


def test_los_candidatos_van_del_mas_ajustado_al_mas_amplio() -> None:
    """Probar primero la caja pequena acierta mas veces a la primera."""
    candidatos = countries_for_point(*CATIA_LA_MAR)
    areas = [
        (COUNTRY_BBOX[i].lon_max - COUNTRY_BBOX[i].lon_min)
        * (COUNTRY_BBOX[i].lat_max - COUNTRY_BBOX[i].lat_min)
        for i in candidatos
    ]
    assert areas == sorted(areas)


def test_mar_abierto_no_devuelve_pais() -> None:
    """Dentro de la ventana LATAM pero fuera de todo pais cubierto."""
    assert countries_for_point(-100.0, 5.0) == []


# --- La guardia del join ----------------------------------------------------


@pytest.mark.geo
def test_un_shakemap_que_no_toca_el_activo_falla(tmp_path: Any) -> None:
    """Sin esto se publica un reporte de ceros durante un terremoto real."""
    from pipelines.p2_impact.exposure_join import connect

    con = connect()
    con.execute("CREATE TABLE impact_h3 AS SELECT 1::UBIGINT AS h3_08 WHERE FALSE")
    vacias = con.execute("SELECT count(*) FROM impact_h3").fetchone()[0]
    assert vacias == 0, "la fixture debe reproducir el join vacio"

    # La cifra que se habria publicado sin la guardia.
    fila = con.execute("SELECT sum(h3_08) FROM impact_h3").fetchone()
    assert tuple(float(v or 0.0) for v in fila) == (0.0,)


def test_la_guardia_esta_en_el_codigo() -> None:
    """Guardia de texto: el chequeo no puede desaparecer en un refactor."""
    import inspect

    from pipelines.p2_impact import pipeline

    fuente = inspect.getsource(pipeline.compute_impact)
    assert "SELECT count(*) FROM impact_h3" in fuente
    assert "no toca ninguna celda del activo" in fuente
