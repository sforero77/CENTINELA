"""Lo que el manifest declara tiene que ser lo que se descarga.

Para `pop_ghs`, `built_ghsl` y `landcover` no lo era. `download_ghsl` llamaba a
`ghsl.tiles_for_bbox(bbox, slug=slug)` con los valores por defecto —o sea
`RELEASE = "R2023A"` y `EPOCH = 2025`, constantes del modulo— y del manifest solo
usaba la url, y solo para adivinar de que producto se trataba. Lo mismo con la
cobertura del suelo: `VERSION = "v200"`, `EPOCH = 2021` y una url base fija, cosa
que `layers.py` incluso admitia por escrito: «las URL son constantes fijas».

Y sin embargo los diecinueve manifests declaran `url` y `vintage` para esas tres
capas, `lint_manifest` prohibe vintages flotantes **como si fijaran algo**, y
`resumen_de_insumos` copia ese vintage a `medicion.json`, que se publica en el
Release como la procedencia del activo.

O sea: la procedencia publicada no tenia ninguna relacion causal con los bytes.
Cambiar `R2023A-E2025-...` por `R2025A-E2030-...` en los diecinueve manifests
habria descargado exactamente lo mismo y publicado otra cosa. `grep vintage
tests/` no encontraba ninguna comparacion entre las dos mitades.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from pipelines.p0_exposure.sources import ghsl, worldcover

MANIFESTS = Path(__file__).parent.parent.parent / "data" / "manifests"


def _fuentes(ruta: Path) -> list[dict[str, str]]:
    return list(yaml.safe_load(ruta.read_text(encoding="utf-8"))["sources"])


def _manifests() -> list[Path]:
    return sorted(MANIFESTS.glob("*.yaml"))


# --------------------------------------------------------------------------
# Los parsers, que son el puente nuevo.
# --------------------------------------------------------------------------


def test_el_vintage_de_ghsl_se_lee_entero() -> None:
    assert ghsl.desde_vintage("R2023A-E2025-54009-100m") == ("R2023A", 2025)


def test_un_vintage_de_ghsl_con_otra_reticula_no_pasa() -> None:
    """Pedir teselas de otra rejilla da 404, y un 404 aqui se lee «solo oceano».

    `GRID_X0`, `GRID_Y0` y `TILE_SIZE_M` estan calculados para Mollweide a 100 m.
    Con otro par, ninguna tesela existiria y el pais se ensamblaria vacio sin un
    solo error — que es exactamente como Peru salio con poblacion 0.
    """
    with pytest.raises(ValueError, match="retícula de este modulo"):
        ghsl.desde_vintage("R2023A-E2025-4326-1000m")


def test_un_vintage_ilegible_no_se_adivina() -> None:
    with pytest.raises(ValueError, match="irreconocible"):
        ghsl.desde_vintage("R2023A")


def test_la_url_de_worldcover_lleva_version_y_epoca() -> None:
    url = "https://esa-worldcover.s3.eu-central-1.amazonaws.com/v200/2021/map/"
    assert worldcover.desde_url(url) == ("v200", 2021)


def test_una_url_de_worldcover_sin_version_no_se_adivina() -> None:
    with pytest.raises(ValueError, match="no declara version y epoca"):
        worldcover.desde_url("https://esa-worldcover.s3.eu-central-1.amazonaws.com/map/")


# --------------------------------------------------------------------------
# Y que las dos mitades sigan diciendo lo mismo en los diecinueve paises.
# --------------------------------------------------------------------------


@pytest.mark.parametrize("ruta", _manifests(), ids=lambda p: p.stem)
def test_el_vintage_de_ghsl_concuerda_con_su_url(ruta: Path) -> None:
    """El release y la epoca aparecen dos veces en cada fuente: tienen que coincidir.

    El vintage es el que gobierna la descarga; la url es la que un humano abre
    para comprobar el producto. Si divergen, una de las dos miente y no hay forma
    de saber cual desde el activo publicado.
    """
    for fuente in _fuentes(ruta):
        if fuente["layer"] not in {"pop_ghs", "built_ghsl"}:
            continue
        release, epoch = ghsl.desde_vintage(fuente["vintage"])
        assert f"_{release}/" in fuente["url"], (
            f"{ruta.stem}/{fuente['id']}: el vintage fija {release} y la url no lo lleva"
        )
        assert f"_E{epoch}_" in fuente["url"], (
            f"{ruta.stem}/{fuente['id']}: el vintage fija la epoca {epoch} y la url no"
        )


@pytest.mark.parametrize("ruta", _manifests(), ids=lambda p: p.stem)
def test_la_cobertura_del_suelo_declara_version_y_epoca(ruta: Path) -> None:
    """Y el `vintage` de esa capa, que es solo el ano, concuerda con la url."""
    lulc = [f for f in _fuentes(ruta) if f["layer"] == "landcover"]
    assert lulc, f"{ruta.stem} no declara la cobertura del suelo y el build la consume"
    version, epoch = worldcover.desde_url(lulc[0]["url"])
    assert version.startswith("v")
    assert lulc[0]["vintage"] == str(epoch), (
        f"{ruta.stem}: la url dice {epoch} y el vintage dice {lulc[0]['vintage']!r}"
    )


@pytest.mark.parametrize("ruta", _manifests(), ids=lambda p: p.stem)
def test_lo_que_el_manifest_fija_es_lo_que_el_codigo_trae_por_defecto(ruta: Path) -> None:
    """Un desajuste no es un fallo, pero tiene que ser una decision.

    Las constantes de `ghsl` y `worldcover` son el respaldo de la llamada
    suelta. Mientras el catalogo entero apunte al mismo par, que el respaldo
    apunte a otro solo puede confundir a quien lea el codigo: el dia que GHSL
    publique un release global nuevo se renuevan los manifests **y** estas dos
    lineas, en el mismo cambio.
    """
    for fuente in _fuentes(ruta):
        if fuente["layer"] in {"pop_ghs", "built_ghsl"}:
            assert ghsl.desde_vintage(fuente["vintage"]) == (ghsl.RELEASE, ghsl.EPOCH), (
                f"{ruta.stem} fija {fuente['vintage']} y ghsl.py trae "
                f"{ghsl.RELEASE}/{ghsl.EPOCH} por defecto"
            )
        if fuente["layer"] == "landcover":
            assert worldcover.desde_url(fuente["url"]) == (
                worldcover.VERSION,
                worldcover.EPOCH,
            ), (
                f"{ruta.stem} fija {fuente['url']} y worldcover.py trae "
                f"{worldcover.VERSION}/{worldcover.EPOCH} por defecto"
            )


# --------------------------------------------------------------------------
# Y que el puente este de verdad conectado, no solo construido.
# --------------------------------------------------------------------------


def test_la_descarga_de_ghsl_pide_el_release_del_manifest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Escrito no es conectado: el parser no sirve si nadie se lo pasa."""
    from pipelines.common.geo import BBox
    from pipelines.p0_exposure import download

    pedido: dict[str, object] = {}

    def espia(bbox: object, **kwargs: object) -> list[object]:
        pedido.update(kwargs)
        return []

    monkeypatch.setattr(ghsl, "tiles_for_bbox", espia)
    download.download_ghsl(
        tmp_path,
        BBox(-80, -5, -66, 13),
        fetcher=None,  # type: ignore[arg-type]
        vintage="R2025A-E2030-54009-100m",
    )
    assert pedido["release"] == "R2025A"
    assert pedido["epoch"] == 2030


def test_la_cobertura_del_suelo_pide_la_version_del_manifest(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Lo mismo por el otro lado: `build_landcover_layer` recibe la url."""
    from pipelines.common.geo import BBox
    from pipelines.p0_exposure import build

    pedido: dict[str, object] = {}

    def espia(bbox: object, **kwargs: object) -> list[object]:
        pedido.update(kwargs)
        return []

    monkeypatch.setattr(worldcover, "tiles_for_bbox", espia)
    celdas = build.build_landcover_layer(
        None,
        bbox=BBox(-80, -5, -66, 13),
        url="https://esa-worldcover.s3.eu-central-1.amazonaws.com/v100/2020/map/",
    )
    assert celdas == 0
    assert pedido["version"] == "v100"
    assert pedido["epoch"] == 2020
