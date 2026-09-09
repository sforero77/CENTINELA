"""Deduplicacion por proximidad de las capas de puntos.

Existe por una medicion, no por una intuicion. Colombia, 23-ago-2026: HOTOSM
publica 9.618 sedes de salud y healthsites.io 8.443, y el **96,6 %** de las
segundas cae a menos de 20 m de una de las primeras, porque las dos derivan de
OpenStreetMap. Sumarlas daba 18.061 sedes —casi el doble de las que hay— y
ninguna guardia lo habria notado: el numero es positivo y del orden correcto.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from pipelines.p0_exposure.vector_h3 import (
    DEDUPE_METERS,
    DEGREES_PER_METER,
    aggregate_points_to_h3,
)


@pytest.fixture
def con() -> Any:
    from pipelines.p2_impact.exposure_join import connect

    return connect()


def _geojson(tmp_path: Path, nombre: str, puntos: list[tuple[float, float]]) -> str:
    """GeoJSON de puntos, en el formato que publica HDX."""
    import json

    rasgos = [
        {
            "type": "Feature",
            "properties": {"n": i},
            "geometry": {"type": "Point", "coordinates": [lon, lat]},
        }
        for i, (lon, lat) in enumerate(puntos)
    ]
    ruta = tmp_path / nombre
    ruta.write_text(json.dumps({"type": "FeatureCollection", "features": rasgos}), encoding="utf-8")
    return str(ruta.as_posix())


#: Cuatro sedes en Quibdó, separadas lo suficiente para no confundirse.
PRIMARIA = [(-76.6500, 5.6900), (-76.6600, 5.7000), (-76.6700, 5.7100), (-76.6800, 5.7200)]

#: Un metro son ~9e-6 grados: este desplazamiento son ~2 m.
CASI_IGUAL = 2.0 * DEGREES_PER_METER


@pytest.mark.geo
def test_una_sola_fuente_entra_entera(con: Any, tmp_path: Path) -> None:
    fuente = _geojson(tmp_path, "a.geojson", PRIMARIA)
    r = aggregate_points_to_h3(con, [fuente], tabla="h", columna="health_count")
    assert r.total == len(PRIMARIA)


@pytest.mark.geo
def test_la_segunda_fuente_no_duplica_lo_que_ya_esta(con: Any, tmp_path: Path) -> None:
    """El caso real: healthsites repitiendo lo que HOTOSM ya trae."""
    a = _geojson(tmp_path, "a.geojson", PRIMARIA)
    b = _geojson(tmp_path, "b.geojson", [(lon + CASI_IGUAL, lat) for lon, lat in PRIMARIA])
    r = aggregate_points_to_h3(con, [a, b], tabla="h", columna="health_count")
    assert r.total == len(PRIMARIA), "las cuatro de la segunda fuente eran las mismas"


@pytest.mark.geo
def test_la_segunda_fuente_si_aporta_lo_que_es_nuevo(con: Any, tmp_path: Path) -> None:
    """Deduplicar no puede convertirse en descartar la fuente entera."""
    a = _geojson(tmp_path, "a.geojson", PRIMARIA)
    nuevas = [(-76.5000, 5.5000), (-76.4000, 5.4000)]
    b = _geojson(tmp_path, "b.geojson", [(lon + CASI_IGUAL, lat) for lon, lat in PRIMARIA] + nuevas)
    r = aggregate_points_to_h3(con, [a, b], tabla="h", columna="health_count")
    assert r.total == len(PRIMARIA) + len(nuevas)


@pytest.mark.geo
def test_dos_sedes_distintas_y_cercanas_sobreviven(con: Any, tmp_path: Path) -> None:
    """A 200 m son dos establecimientos, no uno mal ubicado."""
    a = _geojson(tmp_path, "a.geojson", [PRIMARIA[0]])
    lejos = (PRIMARIA[0][0] + 200 * DEGREES_PER_METER, PRIMARIA[0][1])
    b = _geojson(tmp_path, "b.geojson", [lejos])
    r = aggregate_points_to_h3(con, [a, b], tabla="h", columna="health_count")
    assert r.total == 2


@pytest.mark.geo
def test_la_primera_fuente_conserva_sus_propios_vecinos(con: Any, tmp_path: Path) -> None:
    """La deduplicacion es *entre* fuentes, no dentro de la principal.

    Un complejo hospitalario mapeado con varios nodos en OSM son varias sedes, y
    la fuente principal es la que manda sobre su propio contenido.
    """
    pegados = [PRIMARIA[0], (PRIMARIA[0][0] + CASI_IGUAL, PRIMARIA[0][1])]
    fuente = _geojson(tmp_path, "a.geojson", pegados)
    r = aggregate_points_to_h3(con, [fuente], tabla="h", columna="health_count")
    assert r.total == 2


@pytest.mark.geo
def test_se_puede_desactivar(con: Any, tmp_path: Path) -> None:
    a = _geojson(tmp_path, "a.geojson", PRIMARIA)
    b = _geojson(tmp_path, "b.geojson", [(lon + CASI_IGUAL, lat) for lon, lat in PRIMARIA])
    r = aggregate_points_to_h3(con, [a, b], tabla="h", columna="health_count", dedupe_m=0)
    assert r.total == 2 * len(PRIMARIA)


def test_el_umbral_es_el_medido() -> None:
    """20 m: subirlo a 50 o 100 apenas mueve el solape (96,9 % y 97,1 %)."""
    assert DEDUPE_METERS == 20.0


def test_la_conversion_a_grados_es_la_del_meridiano() -> None:
    assert pytest.approx(111_320.0) == 1.0 / DEGREES_PER_METER
