"""Contrato vivo de Overture (§6.2, nocturno).

Overture publica un release nuevo cada mes y su forma ya se movio una vez bajo
los pies del proyecto: el catalogo STAC no numera los bboxes como manda el
estandar, y leerlo "bien" desplazaria la seleccion un puesto sin fallar. Estas
pruebas contrastan contra el release **fijado en el manifest**, que es el que
usaria un build hoy.

No corren en CI de PR: van marcadas ``network`` y las ejecuta el workflow
nocturno, que solo alerta.
"""

from __future__ import annotations

from typing import Any

import pytest

from pipelines.common.geo import BBox
from pipelines.common.http import HttpFetcher
from pipelines.common.manifest import Manifest
from pipelines.p0_exposure.download import COUNTRY_BBOX
from pipelines.p0_exposure.sources.overture import (
    THEME_BUILDINGS,
    THEME_TRANSPORTATION,
    resolve_data_urls,
    select_files,
)

pytestmark = [pytest.mark.network, pytest.mark.geo]

#: Caja de Quibdó. Pequena a proposito: la prueba mide el contrato, no el pais.
QUIBDO = BBox(lon_min=-76.75, lat_min=5.6, lon_max=-76.55, lat_max=5.8)


@pytest.fixture(scope="module")
def manifest() -> Manifest:
    return Manifest.load("COL")


@pytest.fixture(scope="module")
def fetcher() -> HttpFetcher:
    return HttpFetcher(timeout_s=300.0)


def _release(manifest: Manifest, capa: str) -> str:
    return manifest.by_layer(capa)[0].vintage


def test_el_release_fijado_sigue_publicado(manifest: Manifest, fetcher: HttpFetcher) -> None:
    """Overture solo conserva dos releases: el fijado caduca en ~2 meses.

    Que falle aqui no corrompe nada —el activo publicado sigue sirviendo— pero
    avisa de que el proximo ``make country`` no podra reconstruirlo.
    """
    ficheros = select_files(
        fetcher,
        COUNTRY_BBOX["COL"],
        release=_release(manifest, "buildings"),
        theme=THEME_BUILDINGS[0],
        type_=THEME_BUILDINGS[1],
    )
    assert len(ficheros) == 11, f"Colombia toca {len(ficheros)} ficheros, no 11"


def test_cada_tema_particiona_por_su_cuenta(manifest: Manifest, fetcher: HttpFetcher) -> None:
    """Reutilizar la seleccion de un tema para otro leeria ficheros ajenos."""
    edificios = select_files(
        fetcher,
        QUIBDO,
        release=_release(manifest, "buildings"),
        theme=THEME_BUILDINGS[0],
        type_=THEME_BUILDINGS[1],
    )
    vias = select_files(
        fetcher,
        QUIBDO,
        release=_release(manifest, "roads"),
        theme=THEME_TRANSPORTATION[0],
        type_=THEME_TRANSPORTATION[1],
    )
    assert edificios and vias
    assert {f.url.rsplit("/", 1)[-1] for f in edificios} != {
        f.url.rsplit("/", 1)[-1] for f in vias
    }, "los dos temas devolvieron los mismos indices: revisar la seleccion por tema"


@pytest.fixture(scope="module")
def con() -> Any:
    from pipelines.p2_impact.exposure_join import connect

    return connect()


def test_la_geometria_llega_tipada_no_como_blob(
    con: Any, manifest: Manifest, fetcher: HttpFetcher
) -> None:
    """El contrato que rompe la receta publicada de Overture.

    Si algun dia ``geometry`` vuelve a ser ``BLOB``, ``ST_Centroid`` deja de
    aplicar y el conteo de edificaciones se cae. Mejor enterarse de noche.
    """
    from pipelines.p0_exposure.overture_h3 import ensure_httpfs

    ensure_httpfs(con)
    ficheros = select_files(
        fetcher,
        QUIBDO,
        release=_release(manifest, "buildings"),
        theme=THEME_BUILDINGS[0],
        type_=THEME_BUILDINGS[1],
    )
    url = resolve_data_urls(fetcher, ficheros)[0]
    tipos = {
        fila[0]: fila[1]
        for fila in con.execute(f"DESCRIBE SELECT * FROM read_parquet('{url}')").fetchall()
    }
    assert tipos["geometry"].startswith("GEOMETRY")
    assert tipos["bbox"].startswith("STRUCT")


def test_quibdo_tiene_edificaciones(con: Any, manifest: Manifest, fetcher: HttpFetcher) -> None:
    """Cifra de referencia del build: si cae a cero, la capa dejo de llegar."""
    from pipelines.p0_exposure.overture_h3 import aggregate_buildings_to_h3

    ficheros = select_files(
        fetcher,
        QUIBDO,
        release=_release(manifest, "buildings"),
        theme=THEME_BUILDINGS[0],
        type_=THEME_BUILDINGS[1],
    )
    resumen = aggregate_buildings_to_h3(
        con, resolve_data_urls(fetcher, ficheros), bbox=QUIBDO, tabla="bld_quibdo"
    )
    assert resumen.total > 10_000, f"Quibdó devolvio {resumen.total} edificaciones"
    assert resumen.celdas > 50


def test_quibdo_tiene_vias_de_las_tres_clases(
    con: Any, manifest: Manifest, fetcher: HttpFetcher
) -> None:
    """Valida el filtro de subtipo y el reparto de longitud a la vez."""
    from pipelines.p0_exposure.overture_h3 import aggregate_roads_to_h3

    ficheros = select_files(
        fetcher,
        QUIBDO,
        release=_release(manifest, "roads"),
        theme=THEME_TRANSPORTATION[0],
        type_=THEME_TRANSPORTATION[1],
    )
    resumen = aggregate_roads_to_h3(
        con, resolve_data_urls(fetcher, ficheros), bbox=QUIBDO, tabla="roads_quibdo"
    )
    assert resumen.total > 0, "ningun kilometro de via en Quibdó"
    fila = con.execute(
        "SELECT sum(road_km_primary), sum(road_km_secondary), sum(road_km_other) FROM roads_quibdo"
    ).fetchone()
    assert sum(v or 0.0 for v in fila) == pytest.approx(resumen.total, rel=1e-6)


def test_el_listado_de_worldpop_sigue_teniendo_las_bandas(manifest: Manifest) -> None:
    """Un 404 o un renombrado aqui vaciaria el desglose etario del activo."""
    from pipelines.p0_exposure.sources.worldpop import (
        missing_bands,
        parse_listing,
        select_age_rasters,
    )

    url = manifest.by_layer("pop_worldpop_agesex")[0].url
    nombres = parse_listing(HttpFetcher(timeout_s=300.0).get_bytes(url).decode("utf-8", "replace"))
    assert nombres, f"WorldPop no lista ningun .tif en {url}"
    assert missing_bands(select_age_rasters(nombres), nombres) == {}
