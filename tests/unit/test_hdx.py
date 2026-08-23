"""Resolucion de recursos en HDX.

El modulo existe porque la URL de un mismo dataset de HOTOSM cambia de forma
segun el pais; estas pruebas fijan que resolvemos por nombre de dataset y no
por patron de ruta.
"""

from __future__ import annotations

from typing import Any

import pytest

from pipelines.common.hdx import (
    HDX_PACKAGE_SHOW,
    HdxResolutionError,
    dataset_license,
    map_license,
    resolve_resource,
)
from pipelines.common.http import FixtureFetcher


def _paquete(nombre: str, recursos: list[dict[str, str]], licencia: str) -> dict[str, Any]:
    return {
        "success": True,
        "result": {"name": nombre, "license_id": licencia, "resources": recursos},
    }


def _fetcher(dataset: str, payload: dict[str, Any]) -> FixtureFetcher:
    return FixtureFetcher({HDX_PACKAGE_SHOW.format(dataset=dataset): payload})


def test_prefiere_geopackage() -> None:
    """Un solo archivo, CRS declarado y sin el limite de 10 chars del shapefile."""
    ds = "hotosm_col_health_facilities"
    fetcher = _fetcher(
        ds,
        _paquete(
            ds,
            [
                {"format": "SHP", "url": "https://x/shp.zip"},
                {"format": "Geopackage", "url": "https://x/gpkg.zip"},
                {"format": "GeoJSON", "url": "https://x/geojson.zip"},
            ],
            "hdx-odc-odbl",
        ),
    )
    assert resolve_resource(fetcher, ds) == ("Geopackage", "https://x/gpkg.zip")


def test_cae_al_siguiente_formato_disponible() -> None:
    ds = "cod-ab-ecu"
    fetcher = _fetcher(ds, _paquete(ds, [{"format": "SHP", "url": "https://x/s.zip"}], "cc-by-igo"))
    assert resolve_resource(fetcher, ds) == ("SHP", "https://x/s.zip")


def test_dataset_inexistente() -> None:
    ds = "no_existe"
    fetcher = FixtureFetcher({HDX_PACKAGE_SHOW.format(dataset=ds): {"success": False}})
    with pytest.raises(HdxResolutionError, match="no reconoce"):
        resolve_resource(fetcher, ds)


def test_sin_formato_utilizable() -> None:
    """Un dataset solo tabular no sirve: sin geometria no hay celda que llenar."""
    ds = "solo_csv"
    fetcher = _fetcher(ds, _paquete(ds, [{"format": "CSV", "url": "https://x/a.csv"}], "cc-by"))
    with pytest.raises(HdxResolutionError, match="CSV"):
        resolve_resource(fetcher, ds)


def test_lee_la_licencia_declarada() -> None:
    ds = "hotosm_col_roads"
    fetcher = _fetcher(ds, _paquete(ds, [], "hdx-odc-odbl"))
    assert dataset_license(fetcher, ds) == "hdx-odc-odbl"


@pytest.mark.parametrize(
    ("hdx_id", "interno"),
    [
        ("hdx-odc-odbl", "ODbL-1.0"),
        ("cc-by-igo", "CC-BY-IGO"),
        ("cc-by-sa", "CC-BY-SA-4.0"),
        ("CC-BY", "CC-BY-4.0"),
    ],
)
def test_traduccion_de_licencias(hdx_id: str, interno: str) -> None:
    assert map_license(hdx_id) == interno


def test_hdx_other_no_recibe_default_permisivo() -> None:
    """'hdx-other' es el cajon de sastre de HDX: exige revision humana."""
    with pytest.raises(HdxResolutionError, match="sin traduccion"):
        map_license("hdx-other")
