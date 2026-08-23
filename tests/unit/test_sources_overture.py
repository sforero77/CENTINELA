"""Seleccion de ficheros de Overture via STAC.

Los bboxes de las pruebas son los reales del release 2026-08-19.0, medidos
tanto en el catalogo como leyendo los ficheros con DuckDB.
"""

from __future__ import annotations

from typing import Any

import pytest

from pipelines.common.geo import BBox
from pipelines.common.http import FixtureFetcher
from pipelines.p0_exposure.sources.overture import (
    OvertureCatalogError,
    collection_url,
    parse_collection,
    pmtiles_url,
    select_files,
)

RELEASE = "2026-08-19.0"

#: Extension real de los primeros ficheros de `buildings/building`.
BBOXES_REALES = [
    [-180.00, -84.29, -86.85, 14.35],  # part-00000
    [-92.68, 14.35, -86.85, 14.99],  # part-00001
    [-169.54, 14.99, -92.13, 17.07],  # part-00002
    [-92.13, 14.99, -86.85, 17.07],  # part-00003
    [-81.33, -33.81, -77.20, -3.72],  # part-00004  toca Colombia
    [-81.08, -3.73, -77.20, -0.40],  # part-00005  toca Colombia
]


def _coleccion(bboxes: list[list[float]], n_items: int | None = None) -> dict[str, Any]:
    n = n_items if n_items is not None else len(bboxes)
    return {
        "type": "Collection",
        "id": "building",
        "extent": {"spatial": {"bbox": bboxes}},
        "links": [
            {"rel": "item", "href": f"https://stac.overturemaps.org/x/{i:05d}.json"}
            for i in range(n)
        ],
    }


def test_empareja_bbox_con_fichero_sin_desfase() -> None:
    """La trampa: el estandar STAC pondria la union en [0]; Overture no."""
    ficheros = parse_collection(_coleccion(BBOXES_REALES))
    assert len(ficheros) == len(BBOXES_REALES)
    assert ficheros[0].bbox == (-180.00, -84.29, -86.85, 14.35)
    assert ficheros[4].bbox == (-81.33, -33.81, -77.20, -3.72)


def test_un_desajuste_de_conteo_es_error_no_aviso() -> None:
    """Si el 1:1 se rompe, seguir significaria leer ficheros equivocados."""
    with pytest.raises(OvertureCatalogError, match="1:1"):
        parse_collection(_coleccion(BBOXES_REALES, n_items=len(BBOXES_REALES) + 1))


def test_catalogo_sin_extent() -> None:
    with pytest.raises(OvertureCatalogError, match="extent"):
        parse_collection({"links": [{"rel": "item", "href": "x"}]})


def test_catalogo_sin_items() -> None:
    with pytest.raises(OvertureCatalogError, match="item"):
        parse_collection({"extent": {"spatial": {"bbox": []}}, "links": []})


def test_selecciona_solo_lo_que_toca_colombia() -> None:
    colombia = BBox(lon_min=-82.0, lat_min=-4.3, lon_max=-66.8, lat_max=13.5)
    fetcher = FixtureFetcher(
        {collection_url(RELEASE, "buildings", "building"): _coleccion(BBOXES_REALES)}
    )
    ficheros = select_files(fetcher, colombia, release=RELEASE)
    # part-00004 y part-00005 caen sobre la costa pacifica colombiana; los otros
    # cuatro estan en Centroamerica o el Pacifico norte.
    assert len(ficheros) == 2
    assert all(f.url.endswith(("00004.json", "00005.json")) for f in ficheros)


def test_el_release_va_fijado_en_la_url() -> None:
    """Nunca 'latest': el catalogo tiene un alias que apunta al ultimo."""
    assert RELEASE in collection_url(RELEASE, "buildings", "building")
    assert RELEASE in pmtiles_url(RELEASE, "buildings")
