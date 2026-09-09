"""`freeze_event.py` prometia «todas las versiones» y bajaba una por tipo.

Su docstring lo dice desde el primer dia —«descarga el feed detail y **todas**
las versiones de ShakeMap y Ground Failure del evento»— y unas lineas mas abajo
explica para que: «sin ellas no se puede reconstruir la secuencia v1 -> v2 -> v3
que los golden tests necesitan para verificar el changelog de RF-04».

El bucle era::

    for producto in (productos.shakemap, productos.ground_failure, productos.losspager):

y `parse_products` devuelve un `ProductSet` con **tres `ProductRef | None`**, uno
por tipo, ya reducidos por `_preferred` a la version vigente de un solo
contribuidor. `productos.shakemap` es un objeto, no una lista. El bucle daba como
mucho tres vueltas y creaba como mucho tres carpetas: ningun camino del script
llegaba a la entrada `i > 0` de un tipo.

El detail congelado de Chocó trae siete ShakeMap, siete de ground-failure y ocho
de PAGER. El script se quedaba con tres.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from scripts.freeze_event import DETAIL_URL, congelar, nombre_de_carpeta

CHOCO = Path(__file__).parent.parent / "fixtures" / "golden" / "choco_2026_08_10"


def _detail() -> dict[str, Any]:
    datos: dict[str, Any] = json.loads(
        (CHOCO / "detail_superseded.json").read_text(encoding="utf-8")
    )
    return datos


class _FetcherFalso:
    """Devuelve el detail congelado y bytes de mentira para cada contenido."""

    def __init__(self, detail: dict[str, Any]) -> None:
        self.detail = detail
        self.bytes_pedidos: list[str] = []

    def get_json(self, url: str) -> dict[str, Any]:
        assert "includesuperseded=true" in url, (
            "sin `includesuperseded` USGS devuelve una sola entrada por "
            "contribuidor: la secuencia no existe ni aunque se recorra entera"
        )
        return self.detail

    def get_bytes(self, url: str) -> bytes:
        self.bytes_pedidos.append(url)
        return url.encode("utf-8")


@pytest.fixture
def congelado(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, _FetcherFalso]:
    import scripts.freeze_event as fe

    fetcher = _FetcherFalso(_detail())
    monkeypatch.setattr(fe, "HttpFetcher", lambda *_a, **_k: fetcher)
    congelar("us7000sint", tmp_path)
    return tmp_path, fetcher


def test_se_congela_una_carpeta_por_version_y_no_una_por_tipo(
    congelado: tuple[Path, _FetcherFalso],
) -> None:
    destino, _ = congelado
    manifiesto = json.loads((destino / "congelado.json").read_text(encoding="utf-8"))

    assert len(manifiesto["versiones"]["shakemap"]) == 7
    assert len(manifiesto["versiones"]["ground-failure"]) == 7
    assert len(manifiesto["versiones"]["losspager"]) == 8

    carpetas = {p.name for p in destino.iterdir() if p.is_dir()}
    assert len(carpetas) == 22, f"solo se crearon {len(carpetas)} carpetas: {sorted(carpetas)}"


def test_dos_entradas_distintas_no_se_pisan(congelado: tuple[Path, _FetcherFalso]) -> None:
    """En `us20005j32` hay dos entradas ambas rotuladas v1 de contribuidores distintos.

    Con la carpeta nombrada solo por tipo y version, la segunda sobrescribia a la
    primera y la fixture salia con una version de menos y sin decirlo.
    """
    destino, _ = congelado
    manifiesto = json.loads((destino / "congelado.json").read_text(encoding="utf-8"))
    todas = [c for lista in manifiesto["versiones"].values() for c in lista]
    assert len(todas) == len(set(todas))

    entrada = {"source": "atlas", "properties": {"version": "1"}, "updateTime": 123}
    otra = {"source": "us", "properties": {"version": "1"}, "updateTime": 123}
    assert nombre_de_carpeta("shakemap", entrada) != nombre_de_carpeta("shakemap", otra)


def test_queda_anotado_cual_era_la_preferida(congelado: tuple[Path, _FetcherFalso]) -> None:
    """El criterio de `_preferred` ya cambio una vez, y puede cambiar otra.

    Ordenar por `preferredWeight` elegia un ShakeMap de mes y medio antes en
    Venezuela. Sin esta anotacion, una fixture que empieza a dar otro resultado
    no distingue «el codigo elige otra» de «USGS publico otra».
    """
    destino, _ = congelado
    manifiesto = json.loads((destino / "congelado.json").read_text(encoding="utf-8"))
    preferida = manifiesto["preferidas_al_congelar"]["shakemap"]
    assert preferida is not None
    assert preferida["version"] == 7


def test_se_bajan_los_contenidos_de_todas_las_versiones(
    congelado: tuple[Path, _FetcherFalso],
) -> None:
    """Congelar la carpeta sin su contenido seria peor que no congelarla."""
    destino, fetcher = congelado
    hashes = json.loads((destino / "hashes.json").read_text(encoding="utf-8"))
    assert len(hashes) == len(fetcher.bytes_pedidos)
    # Y son de mas de tres carpetas distintas, que era el techo anterior.
    carpetas = {Path(ruta).parts[0] for ruta in hashes}
    assert len(carpetas) > 3


def test_la_url_pide_las_versiones_superadas() -> None:
    """La nota del script lo pedia y la url no lo llevaba."""
    assert "includesuperseded=true" in DETAIL_URL
