"""`celdas.json`, la malla que el visor dibuja. Tampoco tenia pruebas.

Es el mismo sitio en el que estaba `static_map.py` una semana antes de que se
descubriera que llevaba tres reportes publicando seis PNG vacios: un modulo que
solo se importa desde dentro de una funcion, que escribe un derivado, y que
nadie ejercita. La diferencia entre un PNG vacio y un `celdas.json` vacio es que
el segundo no se ve — el visor simplemente no pinta nada, igual que cuando el
evento no tiene celdas.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from pipelines.p3_report.celdas import COLUMNAS, MMI_MINIMO, RES_VISOR, write_cells_json

pytestmark = pytest.mark.geo

#: Un punto en Quibdo. Sirve para fabricar celdas r8 vecinas de verdad.
LON, LAT = -76.66, 5.69


@pytest.fixture
def con() -> Any:
    """Conexion con un `impact_h3` sintetico y celdas H3 reales."""
    from pipelines.p2_impact.exposure_join import connect

    con = connect()
    con.execute(
        f"""
        CREATE OR REPLACE TABLE impact_h3 AS
        SELECT
            h3_latlng_to_cell({LAT} + i * 0.002, {LON} + i * 0.002, 8) AS h3_08,
            6.0 + (i % 3) * 0.5      AS mmi_max,
            100.0 * (i + 1)          AS pop_total,
            10                       AS bld_count,
            2500.0                   AS built_m2,
            1.5                      AS road_km_primary,
            0.5                      AS road_km_secondary,
            0.25                     AS road_km_other,
            1                        AS health_count,
            2                        AS edu_count
        FROM range(0, 12) AS t(i)
        """
    )
    return con


def test_las_columnas_salen_en_el_orden_que_el_visor_espera(con: Any, tmp_path: Path) -> None:
    """El visor lee por indice, no por nombre: el orden **es** el contrato.

    Las celdas viajan como listas y no como objetos para no repetir ocho
    nombres de campo decenas de miles de veces. El precio es que reordenar una
    columna aqui repinta el mapa con los datos cambiados de sitio, en silencio.
    """
    datos = json.loads(write_cells_json(con, tmp_path / "celdas.json").read_text("utf-8"))

    assert datos["columnas"] == list(COLUMNAS)
    assert all(len(celda) == len(COLUMNAS) for celda in datos["celdas"])


def test_no_se_publica_lo_que_el_reporte_no_afirma(con: Any, tmp_path: Path) -> None:
    """Color en el mapa se lee como "aqui pasa algo".

    El reporte no dice nada por debajo de MMI 6, asi que dibujarlo seria pintar
    zonas sobre las que el sistema no se pronuncia.
    """
    con.execute(
        "INSERT INTO impact_h3 SELECT h3_08, 4.5, 999.0, 0, 0, 0, 0, 0, 0, 0 FROM impact_h3 LIMIT 1"
    )

    datos = json.loads(write_cells_json(con, tmp_path / "celdas.json").read_text("utf-8"))

    assert datos["mmi_minimo"] == MMI_MINIMO
    assert all(celda[1] >= MMI_MINIMO for celda in datos["celdas"])


def test_la_malla_se_agrega_a_r7_sin_perder_poblacion(con: Any, tmp_path: Path) -> None:
    """r7 es lo que se dibuja; r8 sigue siendo lo que se calcula.

    Agregar tiene que ser exactamente eso: la suma de los hijos. Si el
    `GROUP BY` se hiciera sobre la celda equivocada, el mapa saldria plausible
    y con la poblacion repartida mal.
    """
    esperado = con.execute(
        f"SELECT sum(pop_total) FROM impact_h3 WHERE mmi_max >= {MMI_MINIMO}"
    ).fetchone()[0]

    datos = json.loads(write_cells_json(con, tmp_path / "celdas.json").read_text("utf-8"))

    assert datos["resolucion"] == RES_VISOR
    assert sum(celda[2] for celda in datos["celdas"]) == pytest.approx(esperado, rel=1e-9)


def test_varias_celdas_r8_caen_en_el_mismo_padre(con: Any, tmp_path: Path) -> None:
    """Si no se agregaran, habria una fila por celda r8 y el fichero pesaria siete veces."""
    celdas_r8 = con.execute(
        f"SELECT count(DISTINCT h3_08) FROM impact_h3 WHERE mmi_max >= {MMI_MINIMO}"
    ).fetchone()[0]

    datos = json.loads(write_cells_json(con, tmp_path / "celdas.json").read_text("utf-8"))

    assert 0 < len(datos["celdas"]) < celdas_r8


def test_el_indice_h3_viaja_como_texto_no_como_entero(con: Any, tmp_path: Path) -> None:
    """`h3-js` reconstruye el hexagono desde la cadena hexadecimal.

    Un UBIGINT de DuckDB pasa de los 2^53 que JSON garantiza en JavaScript: el
    navegador lo redondearia y pediria un hexagono que no existe.
    """
    datos = json.loads(write_cells_json(con, tmp_path / "celdas.json").read_text("utf-8"))

    h3 = datos["celdas"][0][0]
    assert isinstance(h3, str)
    assert h3.startswith("87"), "un indice r7 empieza por 87"


def test_los_enteros_no_se_escriben_como_decimales(con: Any, tmp_path: Path) -> None:
    """`1234.0` ocupa dos caracteres mas que `1234`, decenas de miles de veces.

    Se mira dentro de las celdas, no del fichero entero: `mmi_minimo` es un
    umbral y `6.0` ahi es correcto.
    """
    datos = json.loads(write_cells_json(con, tmp_path / "celdas.json").read_text("utf-8"))

    enteros_como_float = [
        valor
        for celda in datos["celdas"]
        for valor in celda[1:]
        if isinstance(valor, float) and valor.is_integer()
    ]
    assert enteros_como_float == []


def test_el_json_va_sin_espacios(con: Any, tmp_path: Path) -> None:
    """El fichero se sirve tal cual a un navegador; el sangrado es peso puro."""
    texto = write_cells_json(con, tmp_path / "celdas.json").read_text("utf-8")

    assert ", " not in texto
    assert "\n" not in texto


def test_un_evento_sin_celdas_produce_una_malla_vacia_valida(con: Any, tmp_path: Path) -> None:
    """Sin celdas por encima del umbral, el visor tiene que poder leer el fichero.

    Escribir un JSON invalido —o no escribirlo— dejaria al visor con un error
    de red donde deberia ver "este evento no alcanza MMI 6".
    """
    con.execute("DELETE FROM impact_h3")

    datos = json.loads(write_cells_json(con, tmp_path / "celdas.json").read_text("utf-8"))

    assert datos["celdas"] == []
    assert datos["columnas"] == list(COLUMNAS)


def test_las_vias_se_publican_sumadas_no_por_clase(con: Any, tmp_path: Path) -> None:
    """El activo guarda tres clases de via; el visor pinta una sola cifra."""
    datos = json.loads(write_cells_json(con, tmp_path / "celdas.json").read_text("utf-8"))

    esperado = con.execute(
        f"""
        SELECT round(sum(road_km_primary + road_km_secondary + road_km_other), 1)
        FROM impact_h3 WHERE mmi_max >= {MMI_MINIMO}
        """
    ).fetchone()[0]
    indice = COLUMNAS.index("vias_km")

    assert sum(celda[indice] for celda in datos["celdas"]) == pytest.approx(esperado, abs=0.5)
