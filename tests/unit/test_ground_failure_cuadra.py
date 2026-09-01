"""El CSV municipal y el `report.json` cuentan Ground Failure sobre las mismas celdas.

EL HUECO QUE CIERRA. `SQL_IMPACT_ADM2` sumaba la exposicion a deslizamiento y
licuefaccion sobre **toda** `impact_h3` —que arranca en MMI 5,0— mientras
`SQL_TOTALES` la sumaba bajo `WHERE mmi_max >= 6`. Todas las demas columnas
llevan su propio `CASE WHEN mmi_max >= N`, asi que las celdas de 5 a 5,5
aportaban cero a todas menos a esas dos.

Sumar la columna del `adm2.csv` daba mas que la cifra nacional del mismo evento.
Ninguna prueba lo veia: las dos cifras salian positivas y del orden correcto.
Quien bajara el CSV para repartir ayuda y lo contrastara contra la cifra
nacional encontraba una diferencia que nadie sabia explicar.
"""

from __future__ import annotations

from typing import Any

import pytest

from pipelines.common.constants import GROUND_FAILURE_HIGH_PROB, MMI_BAND_AGE_BREAKDOWN
from pipelines.p2_impact.pipeline import SQL_IMPACT_ADM2, SQL_TOTALES

pytestmark = pytest.mark.geo

#: Tres celdas del mismo municipio, todas con licuefaccion por encima del
#: umbral. La primera esta **por debajo** de MMI 6: es la que separaba las dos
#: cifras.
FIXTURE = """
CREATE OR REPLACE TABLE impact_h3 AS
SELECT * FROM (VALUES
    (1::UBIGINT, 'ev', 7, '05001', 5.5, 5.5, 1000.0, 900.0, 100.0,
     10.0, 5000.0, 1.0, 2.0, 1.0, 1.0, 1.0, 0.30, 0.30, NULL),
    (2::UBIGINT, 'ev', 7, '05001', 6.5, 6.5, 2000.0, 1900.0, 200.0,
     20.0, 9000.0, 2.0, 3.0, 2.0, 2.0, 2.0, 0.30, 0.30, NULL),
    (3::UBIGINT, 'ev', 7, '05001', 7.5, 7.5, 4000.0, 3900.0, 400.0,
     40.0, 9000.0, 4.0, 5.0, 4.0, 4.0, 4.0, 0.01, 0.01, NULL)
) AS t(h3_08, usgs_id, shakemap_version, adm2_id, mmi_mean, mmi_max,
       pop_total, pop_alt_worldpop, pop_65p, bld_count, built_m2,
       health_count, edu_count, road_km_primary, road_km_secondary,
       road_km_other, ls_prob, lq_prob, flags_calidad)
"""


@pytest.fixture
def con() -> Any:
    from pipelines.p2_impact.exposure_join import connect

    con = connect()
    con.execute(FIXTURE)
    con.execute(SQL_IMPACT_ADM2.format(edad=MMI_BAND_AGE_BREAKDOWN, gf=GROUND_FAILURE_HIGH_PROB))
    return con


def _nacional(con: Any) -> tuple[float, float]:
    fila = con.execute(
        SQL_TOTALES.format(edad=MMI_BAND_AGE_BREAKDOWN, gf=GROUND_FAILURE_HIGH_PROB)
    ).fetchone()
    # Las dos de Ground Failure son las penultimas: antes de la discrepancia.
    return float(fila[-3]), float(fila[-2])


def test_la_suma_municipal_de_licuefaccion_es_la_cifra_nacional(con: Any) -> None:
    municipal: float = con.execute("SELECT sum(lq_pop_expuesta_mmi6p) FROM impact_adm2").fetchone()[
        0
    ]
    _, nacional = _nacional(con)

    assert municipal == pytest.approx(nacional), (
        "El CSV municipal y el report.json cuentan licuefaccion sobre conjuntos "
        f"de celdas distintos: {municipal} contra {nacional}"
    )


def test_la_suma_municipal_de_deslizamiento_es_la_cifra_nacional(con: Any) -> None:
    municipal: float = con.execute("SELECT sum(ls_pop_expuesta_mmi6p) FROM impact_adm2").fetchone()[
        0
    ]
    nacional, _ = _nacional(con)

    assert municipal == pytest.approx(nacional)


def test_la_celda_por_debajo_de_mmi6_no_entra_en_ninguna_de_las_dos(con: Any) -> None:
    """El contrato que el sufijo `_mmi6p` declara: 2.000, no 3.000."""
    municipal: float = con.execute("SELECT sum(lq_pop_expuesta_mmi6p) FROM impact_adm2").fetchone()[
        0
    ]

    assert municipal == pytest.approx(2000.0)
