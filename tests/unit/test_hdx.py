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


# --- Fijar el recurso, no solo el formato ---------------------------------

#: Forma real de `cod-ab-col`: cuatro recursos SHP, y el primero NO es el que
#: se quiere. Verificado contra la API el 23-ago-2026.
COD_AB_COL: dict[str, Any] = {
    "success": True,
    "result": {
        "resources": [
            {"name": "MGN2024_URB_SECCION.zip", "format": "SHP", "url": "https://x/urb.zip"},
            {"name": "Admin 3 level-vereda.zip", "format": "SHP", "url": "https://x/vereda.zip"},
            {
                "name": "COL Administrative Divisions Shapefiles.zip",
                "format": "SHP",
                "url": "https://x/adm.zip",
            },
            {"name": "MGN2024_RUR_SECCION.zip", "format": "SHP", "url": "https://x/rur.zip"},
        ]
    },
}


def _fetcher_col() -> FixtureFetcher:
    return FixtureFetcher({HDX_PACKAGE_SHOW.format(dataset="cod-ab-col"): COD_AB_COL})


def test_sin_recurso_se_toma_el_primero_del_formato() -> None:
    """El comportamiento heredado, que aqui elige el archivo equivocado."""
    _, url = resolve_resource(_fetcher_col(), "cod-ab-col")
    assert url.endswith("urb.zip"), "secciones urbanas, no municipios"


def test_con_recurso_se_toma_el_declarado() -> None:
    """Es la razon de existir de `hdx_resource` en el manifest."""
    formato, url = resolve_resource(
        _fetcher_col(), "cod-ab-col", resource="COL Administrative Divisions Shapefiles"
    )
    assert formato == "SHP"
    assert url.endswith("adm.zip")


def test_el_recurso_no_distingue_mayusculas() -> None:
    _, url = resolve_resource(_fetcher_col(), "cod-ab-col", resource="administrative divisions")
    assert url.endswith("adm.zip")


def test_un_recurso_ambiguo_es_error() -> None:
    """Elegir uno de dos en silencio es como no haberlo fijado."""
    with pytest.raises(HdxResolutionError, match="identifica 2 recursos"):
        resolve_resource(_fetcher_col(), "cod-ab-col", resource="SECCION")


def test_un_recurso_inexistente_es_error() -> None:
    """Si el publicador renombra, hay que enterarse en el build, no despues."""
    with pytest.raises(HdxResolutionError, match="identifica 0 recursos"):
        resolve_resource(_fetcher_col(), "cod-ab-col", resource="no-existe")


def test_el_error_lista_lo_que_si_hay() -> None:
    """El mensaje tiene que decir con que reemplazarlo."""
    with pytest.raises(HdxResolutionError, match="MGN2024_URB_SECCION"):
        resolve_resource(_fetcher_col(), "cod-ab-col", resource="no-existe")


# --- Una capa partida por tipo de geometria --------------------------------

#: Forma real de `hotosm_per_health_facilities`: el GeoPackage combinado apunta
#: a un export efimero de export.hotosm.org que ya devuelve 404, y los mismos
#: datos siguen vivos en S3 partidos en puntos y poligonos.
PERU_SALUD: dict[str, Any] = {
    "success": True,
    "result": {
        "resources": [
            {
                "name": "hotosm_per_health_facilities_gpkg.zip",
                "format": "Geopackage",
                "url": "https://export.hotosm.org/downloads/uuid/combinado.zip",
            },
            {
                "name": "hotosm_per_health_facilities_points_gpkg.zip",
                "format": "Geopackage",
                "url": "https://s3/puntos.zip",
            },
            {
                "name": "hotosm_per_health_facilities_polygons_gpkg.zip",
                "format": "Geopackage",
                "url": "https://s3/poligonos.zip",
            },
        ]
    },
}

#: Colombia: un solo GeoPackage combinado.
COL_SALUD: dict[str, Any] = {
    "success": True,
    "result": {
        "resources": [
            {
                "name": "hotosm_col_health_facilities_osm_gpkg.zip",
                "format": "Geopackage",
                "url": "https://s3/col.zip",
            }
        ]
    },
}


def test_un_dataset_combinado_da_un_solo_intento() -> None:
    from pipelines.common.hdx import resolve_attempts

    f = FixtureFetcher({HDX_PACKAGE_SHOW.format(dataset="col"): COL_SALUD})
    intentos = resolve_attempts(f, "col")
    assert intentos == [("Geopackage", ["https://s3/col.zip"])]


def test_el_combinado_va_antes_que_los_parciales() -> None:
    """Si los tres estuvieran vivos, bajarlos todos contaria cada sede dos veces."""
    from pipelines.common.hdx import resolve_attempts

    f = FixtureFetcher({HDX_PACKAGE_SHOW.format(dataset="per"): PERU_SALUD})
    intentos = resolve_attempts(f, "per")
    assert intentos[0][1] == ["https://export.hotosm.org/downloads/uuid/combinado.zip"]


def test_los_parciales_van_juntos_y_completos() -> None:
    """Quedarse con los puntos perderia los hospitales grandes.

    El extracto mezcla POINT, POLYGON y MULTIPOLYGON porque un hospital grande
    esta mapeado en OSM como edificio y no como nodo.
    """
    from pipelines.common.hdx import resolve_attempts

    f = FixtureFetcher({HDX_PACKAGE_SHOW.format(dataset="per"): PERU_SALUD})
    _, urls = resolve_attempts(f, "per")[1]
    assert urls == ["https://s3/puntos.zip", "https://s3/poligonos.zip"]


def test_fijar_el_recurso_sigue_dando_uno_solo() -> None:
    """`hdx_resource` manda sobre todo lo demas: lo necesita el COD-AB de COL."""
    from pipelines.common.hdx import resolve_attempts

    f = _fetcher_col()
    intentos = resolve_attempts(f, "cod-ab-col", resource="COL Administrative Divisions")
    assert len(intentos) == 1
    assert intentos[0][1] == ["https://x/adm.zip"]
