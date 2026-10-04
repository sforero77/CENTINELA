"""`SQL_IMPACT_ADM2` y `SQL_TOTALES` agregan lo mismo, y el CSV publica lo que agregan.

DIECINUEVE AGREGACIONES ESCRITAS DOS VECES A MANO. Cada cifra nacional del
`report.json` tiene su gemela municipal en el `adm2.csv`, y las dos se escriben
por separado: un `CASE WHEN mmi_max >= 6` en una y `>= 7` en la otra, o una via
que suma `road_km_other` en un sitio y no en el otro, deja dos cifras positivas
y del orden correcto que no cuadran. Solo las dos de Ground Failure estaban
vigiladas (`test_ground_failure_cuadra.py`), porque fue ahi donde ya habia
pasado. `test_el_csv_cuadra_con_el_reporte.py` mira las diecinueve, pero en los
ficheros publicados: ve el fallo despues de haberlo publicado.

Aqui se comprueba la propiedad en el SQL, sin reescribirlo: las dos consultas
corren sobre la misma malla y la suma municipal de cada columna tiene que dar
la cifra nacional. Los pares salen de los cursores, no de una lista: una
agregacion que se anade a una consulta y no a la otra rompe la prueba.

Y LA MISMA LISTA DE COLUMNAS VIVIA EN CINCO SITIOS —el SQL, `HXL_HEADERS`,
`schemas/parquet/tables.yaml`, el enriquecimiento de P2 y las pruebas— y el
escritor del CSV descartaba en silencio lo que no estuviera en el suyo. El
contrato de `tables.yaml` llevaba desde el 3-sep sin las siete columnas de la
banda 6 ni el centroide, y seguia llamando `ls_pop_expuesta` a la columna que
ya se publicaba como `ls_pop_expuesta_mmi6p`.
"""

from __future__ import annotations

from dataclasses import fields
from pathlib import Path
from typing import Any

import pytest
import yaml

from pipelines.common.constants import GROUND_FAILURE_HIGH_PROB, MMI_BAND_AGE_BREAKDOWN
from pipelines.p2_impact.pipeline import SQL_IMPACT_ADM2, SQL_TOTALES
from pipelines.p3_report.csv_out import HXL_HEADERS
from pipelines.p3_report.model import Totales

pytestmark = pytest.mark.geo

RAIZ = Path(__file__).parent.parent.parent

#: Dos municipios, una celda por banda y una por debajo de MMI 6. **Cada columna
#: lleva valores propios** —no hay dos columnas con la misma serie—, para que
#: intercambiar dos alias, o sumar la columna equivocada, mueva la cifra.
#: Deslizamiento y licuefaccion van cruzados entre celdas por la misma razon.
FIXTURE = """
CREATE OR REPLACE TABLE impact_h3 AS
SELECT * FROM (VALUES
    (1::UBIGINT, 'ev', 7, '05001', 5.5, 5.5, 1000.0, 900.0, 101.0,
     11.0, 5003.0, 1.0, 3.0, 1.5, 2.25, 4.125, 0.30, 0.02, NULL),
    (2::UBIGINT, 'ev', 7, '05001', 6.5, 6.5, 2000.0, 1900.0, 203.0,
     23.0, 9007.0, 5.0, 7.0, 3.5, 5.25, 8.125, 0.02, 0.40, 'borde'),
    (3::UBIGINT, 'ev', 7, '05001', 7.5, 7.5, 4000.0, 3900.0, 407.0,
     47.0, 9011.0, 11.0, 13.0, 7.5, 11.25, 16.125, 0.50, 0.03, NULL),
    (4::UBIGINT, 'ev', 7, '05002', 8.5, 8.5, 8000.0, 7900.0, 809.0,
     89.0, 9013.0, 17.0, 19.0, 15.5, 23.25, 32.125, 0.04, 0.60, NULL),
    (5::UBIGINT, 'ev', 7, '05002', 6.0, 6.0, 300.0, 290.0, 31.0,
     3.0, 307.0, 23.0, 29.0, 0.5, 0.75, 1.125, 0.70, 0.80, NULL)
) AS t(h3_08, usgs_id, shakemap_version, adm2_id, mmi_mean, mmi_max,
       pop_total, pop_alt_worldpop, pop_65p, bld_count, built_m2,
       health_count, edu_count, road_km_primary, road_km_secondary,
       road_km_other, ls_prob, lq_prob, flags_calidad)
"""

#: Las dos unicas columnas que no se llaman igual en las dos consultas. El CSV
#: lleva el corte de MMI en el nombre; `Totales` conserva el nombre publicado.
NOMBRE_MUNICIPAL: dict[str, str] = {
    "pop_ls_alta": "ls_pop_expuesta_mmi6p",
    "pop_lq_alta": "lq_pop_expuesta_mmi6p",
}

#: Columnas de `impact_adm2` que no son agregaciones con gemela nacional.
NO_AGREGADAS = frozenset({"usgs_id", "shakemap_version", "adm2_id", "mmi_max", "flags_calidad"})

#: Lo que P2 anade a cada fila antes de escribir el CSV (`_enriquecer_con_admin`).
ENRIQUECIDAS = frozenset({"nombre", "lon", "lat"})


@pytest.fixture(scope="module")
def con() -> Any:
    from pipelines.p2_impact.exposure_join import connect

    con = connect()
    con.execute(FIXTURE)
    con.execute(SQL_IMPACT_ADM2.format(edad=MMI_BAND_AGE_BREAKDOWN, gf=GROUND_FAILURE_HIGH_PROB))
    return con


def _nacionales(con: Any) -> dict[str, float]:
    cursor = con.execute(
        SQL_TOTALES.format(edad=MMI_BAND_AGE_BREAKDOWN, gf=GROUND_FAILURE_HIGH_PROB)
    )
    nombres = [d[0] for d in cursor.description]
    fila = dict(zip(nombres, cursor.fetchone(), strict=True))
    fila.pop("discrepancia_pct")
    return {k: float(v) for k, v in fila.items()}


def _columnas_municipales(con: Any) -> list[str]:
    return [d[0] for d in con.execute("SELECT * FROM impact_adm2 LIMIT 0").description]


def test_toda_agregacion_tiene_su_gemela(con: Any) -> None:
    """Ninguna de las dos consultas puede agregar algo que la otra no."""
    nacionales = set(_nacionales(con))
    assert nacionales == {c.name for c in fields(Totales)}, "SQL_TOTALES ya no da las cifras"

    gemelas = {NOMBRE_MUNICIPAL.get(n, n) for n in nacionales}
    municipales = set(_columnas_municipales(con)) - NO_AGREGADAS

    assert municipales == gemelas, (
        f"solo en SQL_IMPACT_ADM2: {sorted(municipales - gemelas)}; "
        f"solo en SQL_TOTALES: {sorted(gemelas - municipales)}"
    )


def test_la_suma_municipal_de_cada_cifra_es_la_nacional(con: Any) -> None:
    """Las diecinueve, no dos."""
    nacionales = _nacionales(con)
    assert len(nacionales) == len(fields(Totales))

    descuadres = {}
    for nombre, nacional in nacionales.items():
        columna = NOMBRE_MUNICIPAL.get(nombre, nombre)
        municipal = float(con.execute(f"SELECT sum({columna}) FROM impact_adm2").fetchone()[0])
        if municipal != pytest.approx(nacional):
            descuadres[nombre] = (municipal, nacional)
        # Que la fixture distinga: una cifra en cero no prueba nada.
        assert nacional > 0, f"la fixture no ejercita {nombre}"

    assert not descuadres, f"municipal contra nacional: {descuadres}"


def test_el_csv_publica_exactamente_lo_que_se_agrega(con: Any) -> None:
    """`HXL_HEADERS` es lo que se escribe; lo que P2 entrega tiene que ser eso."""
    entregadas = set(_columnas_municipales(con)) | ENRIQUECIDAS

    assert entregadas == set(HXL_HEADERS), (
        f"P2 entrega sin publicar: {sorted(entregadas - set(HXL_HEADERS))}; "
        f"el CSV espera sin recibir: {sorted(set(HXL_HEADERS) - entregadas)}"
    )


def test_el_contrato_de_la_tabla_es_el_csv() -> None:
    """`tables.yaml` llama a `impact_adm2` "la tabla que consume el mundo"."""
    contrato = yaml.safe_load((RAIZ / "schemas" / "parquet" / "tables.yaml").read_text("utf-8"))
    declaradas = [c["nombre"] for c in contrato["impact_adm2"]["columnas"]]

    assert declaradas == list(HXL_HEADERS)
