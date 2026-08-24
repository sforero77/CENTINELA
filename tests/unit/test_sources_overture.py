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
    item_data_url,
    parse_collection,
    pmtiles_url,
    resolve_data_urls,
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


# --- Resolucion del parquet detras de cada item ----------------------------

#: Forma real del item 00013 de `buildings/building` en el release 2026-08-19.0.
#: El nombre del parquet lleva un UUID: no se puede deducir, hay que leerlo.
ITEM_REAL: dict[str, Any] = {
    "id": "00013",
    "assets": {
        "aws": {
            "href": (
                "https://overturemaps-us-west-2.s3.us-west-2.amazonaws.com/release/"
                "2026-08-19.0/theme=buildings/type=building/"
                "part-00013-f54530cc-76c0-5ff4-8e72-6b2b9b844f62-c000.zstd.parquet"
            ),
            "type": "application/vnd.apache.parquet",
            "roles": ["data"],
        },
        "azure": {
            "href": (
                "https://overturemapswestus2.blob.core.windows.net/release/2026-08-19.0/"
                "theme=buildings/type=building/"
                "part-00013-f54530cc-76c0-5ff4-8e72-6b2b9b844f62-c000.zstd.parquet"
            ),
            "type": "application/vnd.apache.parquet",
            "roles": ["data"],
        },
    },
}


def test_se_prefiere_el_asset_de_aws() -> None:
    """Los dos sirven el mismo parquet; AWS es el que lee httpfs mas rapido."""
    assert "s3.us-west-2.amazonaws.com" in item_data_url(ITEM_REAL)


def test_se_puede_pedir_azure() -> None:
    assert "blob.core.windows.net" in item_data_url(ITEM_REAL, prefer="azure")


def test_un_asset_desconocido_cae_en_el_que_haya() -> None:
    """Si Overture renombra el asset, mejor leer el otro que no leer nada."""
    assert item_data_url(ITEM_REAL, prefer="gcs").endswith(".parquet")


def test_un_item_sin_datos_es_error() -> None:
    """Seguir devolveria una lista corta y un activo incompleto en silencio."""
    with pytest.raises(OvertureCatalogError, match="asset"):
        item_data_url({"id": "00013", "assets": {"thumbnail": {"href": "x.png"}}})


def test_resolver_abre_un_item_por_fichero() -> None:
    colombia = BBox(lon_min=-82.0, lat_min=-4.3, lon_max=-66.8, lat_max=13.5)
    coleccion = _coleccion(BBOXES_REALES)
    items = {str(link["href"]): ITEM_REAL for link in coleccion["links"] if link["rel"] == "item"}
    fetcher = FixtureFetcher({collection_url(RELEASE, "buildings", "building"): coleccion, **items})
    ficheros = select_files(fetcher, colombia, release=RELEASE)
    urls = resolve_data_urls(fetcher, ficheros)
    assert len(urls) == len(ficheros)
    assert all(u.endswith(".parquet") for u in urls)
