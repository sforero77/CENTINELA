"""`load_admin_geometry` contra un fichero de verdad, por `ST_Read`.

AUDITORIA #162 (5-sep-2026). Ninguna prueba ejecutaba esta funcion. Las de
geometria administrativa —`test_geometria_administrativa.py`,
`test_rescate_frontera.py`, `test_cobertura_latam.py`— se montan su propia
tabla `admin_geom` con un `CREATE TABLE` escrito a mano, asi que todo lo que
hace la funcion de verdad quedaba sin probar: que `ST_Read` abra el fichero,
que las columnas se busquen sin distinguir mayusculas (HDX las escribe en
mayusculas y el SQL las nombra en minusculas), que se elija la nomenclatura
que el fichero trae y que el error diga que hay cuando no encaja ninguna.

Es la familia del fallo historico de la cobertura: una prueba que construye a
mano lo que produccion no puede producir pasa en verde mirando otra cosa.

Un GeoJSON minimo en `tmp_path` y DuckDB con la extension spatial, la misma
conexion que usa el build.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

pytestmark = pytest.mark.geo


@pytest.fixture
def con() -> Any:
    from pipelines.p2_impact.exposure_join import connect

    return connect()


def _cuadrado(x: float, y: float) -> dict[str, Any]:
    return {
        "type": "Polygon",
        "coordinates": [[[x, y], [x + 1, y], [x + 1, y + 1], [x, y + 1], [x, y]]],
    }


def _geojson(ruta: Path, filas: list[dict[str, str]]) -> Path:
    ruta.write_text(
        json.dumps(
            {
                "type": "FeatureCollection",
                "features": [
                    {"type": "Feature", "properties": p, "geometry": _cuadrado(i, 0)}
                    for i, p in enumerate(filas)
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return ruta


def test_carga_un_cod_ab_con_las_columnas_en_mayusculas(con: Any, tmp_path: Path) -> None:
    """Como lo publica HDX: `ADM2_PCODE`, `ADM2_ES`... y el SQL pide minusculas."""
    from pipelines.p0_exposure.crosswalk import load_admin_geometry

    fuente = _geojson(
        tmp_path / "ecu_admbnda_adm2.geojson",
        [
            {
                "ADM2_PCODE": "EC0901",
                "ADM2_ES": "Guayaquil",
                "ADM1_PCODE": "EC09",
                "ADM1_ES": "Guayas",
            },
            {
                "ADM2_PCODE": "EC1701",
                "ADM2_ES": "Quito",
                "ADM1_PCODE": "EC17",
                "ADM1_ES": "Pichincha",
            },
        ],
    )

    assert load_admin_geometry(con, fuente, iso3="ECU") == 2

    filas = con.execute(
        "SELECT adm2_id, nombre, adm1_id, departamento, round(ST_Area(geom), 6) "
        "FROM admin_geom ORDER BY adm2_id"
    ).fetchall()
    assert filas == [
        ("EC0901", "Guayaquil", "EC09", "Guayas", 1.0),
        ("EC1701", "Quito", "EC17", "Pichincha", 1.0),
    ]


def test_elige_la_nomenclatura_que_trae_el_fichero(con: Any, tmp_path: Path) -> None:
    """Brasil entrega `_pt`; la primera variante (`_name`) no encaja y se prueba la siguiente."""
    from pipelines.p0_exposure.crosswalk import load_admin_geometry

    fuente = _geojson(
        tmp_path / "bra.geojson",
        [
            {
                "adm2_pcode": "BR3550308",
                "adm2_pt": "São Paulo",
                "adm1_pcode": "BR35",
                "adm1_pt": "SP",
            }
        ],
    )

    assert load_admin_geometry(con, fuente, iso3="BRA") == 1
    assert con.execute("SELECT nombre FROM admin_geom").fetchone() == ("São Paulo",)


def test_colombia_lee_el_mgn_del_dane(con: Any, tmp_path: Path) -> None:
    """La excepcion por pais de `ADMIN_COLUMNS`, por el camino real."""
    from pipelines.p0_exposure.crosswalk import load_admin_geometry

    fuente = _geojson(
        tmp_path / "MGN_ADM_MPIO_GRAFICO.geojson",
        [
            {
                "mpio_cdpmp": "05001",
                "mpio_cnmbr": "Medellín",
                "dpto_ccdgo": "05",
                "dpto_cnmbr": "Antioquia",
            }
        ],
    )

    assert load_admin_geometry(con, fuente, iso3="COL") == 1
    assert con.execute("SELECT adm2_id, departamento FROM admin_geom").fetchone() == (
        "05001",
        "Antioquia",
    )


def test_sin_las_columnas_falla_antes_de_agregar_y_dice_que_hay(con: Any, tmp_path: Path) -> None:
    """Fallar aqui es barato; descubrirlo despues de agregar nueve capas no."""
    from pipelines.p0_exposure.crosswalk import load_admin_geometry

    fuente = _geojson(tmp_path / "raro.geojson", [{"codigo": "1", "municipio": "X"}])

    with pytest.raises(ValueError, match="municipio") as exc:
        load_admin_geometry(con, fuente, iso3="ECU")
    assert "COD_AB_VARIANTES" in str(exc.value)
    assert con.execute(
        "SELECT count(*) FROM information_schema.tables WHERE table_name = 'admin_geom'"
    ).fetchone() == (0,), "no puede quedar una admin_geom a medias"
