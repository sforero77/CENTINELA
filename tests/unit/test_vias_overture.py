"""Agregacion de vias de Overture, con parquet locales que imitan el contrato.

El reparto de longitud por celda ya esta probado; lo que aqui se cubre es lo que
Overture anade encima: el filtro por `subtype`, el mapeo de `class` a las tres
columnas del reporte, y **la consolidacion entre ficheros**. Esto ultimo es el
riesgo real: los ficheros se procesan uno a uno, y una celda en el borde de dos
tiene que recibir los kilometros de ambos, no los del ultimo.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from pipelines.common.geo import BBox
from pipelines.p0_exposure.overture_h3 import aggregate_roads_to_h3

CAJA = BBox(lon_min=-76.8, lat_min=5.6, lon_max=-76.4, lat_max=5.9)


@pytest.fixture
def con() -> Any:
    from pipelines.p2_impact.exposure_join import connect

    return connect()


def _parquet(con: Any, destino: Path, filas: list[tuple[str, str, str]]) -> str:
    """Parquet con la forma real de `transportation/segment` de Overture.

    `geometry` va tipada como GEOMETRY —no como BLOB— y `bbox` es el STRUCT que
    usa la poda por row-group. Las dos cosas verificadas contra el release real.
    """
    valores = ",\n".join(
        f"""(ST_GeomFromText('{wkt}'), '{subtype}', '{clase}',
             {{'xmin': ST_XMin(ST_GeomFromText('{wkt}')),
               'xmax': ST_XMax(ST_GeomFromText('{wkt}')),
               'ymin': ST_YMin(ST_GeomFromText('{wkt}')),
               'ymax': ST_YMax(ST_GeomFromText('{wkt}'))}})"""
        for wkt, subtype, clase in filas
    )
    con.execute(
        f"""
        COPY (SELECT * FROM (VALUES {valores}) AS t(geometry, subtype, "class", bbox))
        TO '{destino.as_posix()}' (FORMAT PARQUET)
        """
    )
    return destino.as_posix()


#: Un tramo corto dentro de la caja, de cada clase que el reporte separa.
TRONCAL = "LINESTRING(-76.70 5.70, -76.65 5.70)"
SECUNDARIA = "LINESTRING(-76.60 5.75, -76.58 5.75)"
VECINAL = "LINESTRING(-76.55 5.80, -76.54 5.80)"


@pytest.mark.geo
def test_las_tres_clases_caen_en_su_columna(con: Any, tmp_path: Path) -> None:
    ruta = _parquet(
        con,
        tmp_path / "a.parquet",
        [
            (TRONCAL, "road", "motorway"),
            (SECUNDARIA, "road", "secondary"),
            (VECINAL, "road", "residential"),
        ],
    )
    aggregate_roads_to_h3(con, [ruta], bbox=CAJA, tabla="vias")
    fila = con.execute(
        "SELECT sum(road_km_primary), sum(road_km_secondary), sum(road_km_other) FROM vias"
    ).fetchone()
    assert all(v > 0 for v in fila), f"alguna clase quedo en cero: {fila}"


@pytest.mark.geo
def test_el_ferrocarril_no_cuenta_como_via(con: Any, tmp_path: Path) -> None:
    """`transportation` publica rail y water; sumarlos inflaria los kilometros."""
    ruta = _parquet(
        con, tmp_path / "a.parquet", [(TRONCAL, "rail", "rail"), (SECUNDARIA, "water", "ferry")]
    )
    resumen = aggregate_roads_to_h3(con, [ruta], bbox=CAJA, tabla="vias")
    assert resumen.total == 0.0


@pytest.mark.geo
def test_los_kilometros_de_dos_ficheros_se_suman(con: Any, tmp_path: Path) -> None:
    """El riesgo del troceado: quedarse con el ultimo fichero en vez de sumar."""
    a = _parquet(con, tmp_path / "a.parquet", [(TRONCAL, "road", "motorway")])
    b = _parquet(con, tmp_path / "b.parquet", [(SECUNDARIA, "road", "secondary")])

    solo_a = aggregate_roads_to_h3(con, [a], bbox=CAJA, tabla="via_a").total
    solo_b = aggregate_roads_to_h3(con, [b], bbox=CAJA, tabla="via_b").total
    juntos = aggregate_roads_to_h3(con, [a, b], bbox=CAJA, tabla="vias").total

    assert juntos == pytest.approx(solo_a + solo_b, rel=1e-9)


@pytest.mark.geo
def test_una_celda_compartida_recibe_de_los_dos(con: Any, tmp_path: Path) -> None:
    """Si dos ficheros tocan la misma celda, la consolidacion tiene que sumar."""
    mismo_sitio = "LINESTRING(-76.70 5.70, -76.699 5.70)"
    a = _parquet(con, tmp_path / "a.parquet", [(mismo_sitio, "road", "motorway")])
    b = _parquet(con, tmp_path / "b.parquet", [(mismo_sitio, "road", "motorway")])

    una = aggregate_roads_to_h3(con, [a], bbox=CAJA, tabla="via_a")
    dos = aggregate_roads_to_h3(con, [a, b], bbox=CAJA, tabla="vias")

    assert dos.celdas == una.celdas, "la misma via no puede crear celdas nuevas"
    assert dos.total == pytest.approx(2 * una.total, rel=1e-9)


@pytest.mark.geo
def test_no_quedan_tablas_intermedias(con: Any, tmp_path: Path) -> None:
    """Un build de 19 paises no puede ir dejando tablas por el camino."""
    a = _parquet(con, tmp_path / "a.parquet", [(TRONCAL, "road", "motorway")])
    b = _parquet(con, tmp_path / "b.parquet", [(SECUNDARIA, "road", "secondary")])
    aggregate_roads_to_h3(con, [a, b], bbox=CAJA, tabla="vias")

    tablas = {r[0] for r in con.execute("SELECT table_name FROM duckdb_tables()").fetchall()}
    assert not any(t.startswith("_vias_p") for t in tablas), f"quedaron partes: {tablas}"


@pytest.mark.geo
def test_lo_de_fuera_de_la_caja_no_entra(con: Any, tmp_path: Path) -> None:
    """La poda por bbox es lo que hace viable leer 277 GB en remoto."""
    lejos = "LINESTRING(-70.0 2.0, -69.9 2.0)"
    ruta = _parquet(con, tmp_path / "a.parquet", [(lejos, "road", "motorway")])
    assert aggregate_roads_to_h3(con, [ruta], bbox=CAJA, tabla="vias").total == 0.0
