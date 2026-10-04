"""`freeze_event.py` tiene que producir la fixture golden que las pruebas leen.

DOS VECES PROMETIO UNA COSA E HIZO OTRA.

La primera, «todas las versiones»: el bucle recorria el `ProductSet` de
`parse_products`, tres `ProductRef | None` ya reducidos a la vigente, y la
fixture salia con tres versiones de las veintidos que trae el detail de Choco.

La segunda la dejo la propia reparacion, y la vio la auditoria del 5-sep-2026
(hallazgos 117, 118 y 181): el script escribia `detail.json`, que ninguna prueba
abre; bajaba los contenidos de **todas** las versiones —241 MB solo del
ShakeMap, con un `.hdf` de 62 MB— dentro del repositorio; los `.tif` de Ground
Failure los descartaba `.gitignore` en silencio mientras `hashes.json` los
declaraba; y ninguno de los ficheros que `tests/golden/` si lee salia de el.

Estas pruebas corren el script entero sin red, con un fetcher que sirve lo ya
congelado, y comparan lo que escribe con lo que esta versionado: si el script y
la fixture divergen, la herramienta de T0.2 ya no sirve para regenerar T0.2.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

import pytest
from scripts.freeze_event import DETAIL_URL, congelar, url_del_feed, ventana_del_feed

RAIZ = Path(__file__).parent.parent.parent
GOLDEN = RAIZ / "tests" / "fixtures" / "golden"
CHOCO = GOLDEN / "choco_2026_08_10"
VENEZUELA = GOLDEN / "venezuela_2026_06_24"

#: Los que escribe el script sin que una prueba golden los lea: procedencia.
MANIFIESTOS = {"congelado.json", "hashes.json"}


def _json(path: Path) -> dict[str, Any]:
    datos: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return datos


def _bytes_versionados(path: Path) -> bytes:
    """El fichero como esta en el indice: `core.autocrlf` le pone CRLF al sacarlo."""
    return path.read_bytes().replace(b"\r\n", b"\n")


def _con_lastre(detail: dict[str, Any]) -> dict[str, Any]:
    """El detail como lo sirve USGS: con productos y contenidos que nadie lee."""
    gordo: dict[str, Any] = json.loads(json.dumps(detail))
    productos = gordo["properties"]["products"]
    productos["phase-data"] = [{"contents": {"quakeml.xml": {"url": "https://x/q.xml"}}}]
    for entrada in productos["shakemap"]:
        entrada["contents"]["download/shake_result.hdf"] = {"url": "https://x/r.hdf"}
        entrada["contents"]["download/intensity.jpg"] = {"url": "https://x/i.jpg"}
    return gordo


class _FetcherFalso:
    """Sirve el detail con lastre por id, y los bytes congelados por url."""

    def __init__(self, details: dict[str, dict[str, Any]], bytes_por_url: dict[str, bytes]):
        self.details = details
        self.bytes_por_url = bytes_por_url
        self.bytes_pedidos: list[str] = []

    def get_json(self, url: str) -> dict[str, Any]:
        assert "includesuperseded=true" in url, (
            "sin `includesuperseded` USGS devuelve una sola entrada por "
            "contribuidor: la secuencia no existe"
        )
        usgs_id = parse_qs(urlparse(url).query)["eventid"][0]
        return _con_lastre(self.details[usgs_id])

    def get_bytes(self, url: str) -> bytes:
        self.bytes_pedidos.append(url)
        if url in self.bytes_por_url:
            return self.bytes_por_url[url]
        assert "fdsnws/event/1/query" in url, f"se pidio un contenido que nadie lee: {url}"
        return b'{"type":"FeatureCollection","features":[]}'


def _url_contornos_v7() -> str:
    for entrada in _json(CHOCO / "detail_superseded.json")["properties"]["products"]["shakemap"]:
        if entrada["properties"]["version"] == "7":
            url: str = entrada["contents"]["download/cont_mmi.json"]["url"]
            return url
    raise AssertionError("el detail de Choco no trae el ShakeMap v7")


@pytest.fixture
def choco(tmp_path: Path) -> tuple[Path, _FetcherFalso, dict[str, str]]:
    fetcher = _FetcherFalso(
        {"us6000tjl2": _json(CHOCO / "detail_superseded.json")},
        {_url_contornos_v7(): (CHOCO / "cont_mmi_v7.json").read_bytes()},
    )
    hashes = congelar(["us6000tjl2"], tmp_path, fetcher=fetcher)
    return tmp_path, fetcher, hashes


def test_escribe_los_ficheros_que_leen_los_golden(
    choco: tuple[Path, _FetcherFalso, dict[str, str]],
) -> None:
    """Ni `detail.json`, que no lee nadie, ni carpetas por version."""
    destino, _, _ = choco
    escritos = {p.name for p in destino.iterdir()}
    assert not [p for p in destino.iterdir() if p.is_dir()]
    datos = escritos - MANIFIESTOS
    assert datos == {"detail_superseded.json", "cont_mmi_v7.json", "feed_reconstruido.json"}
    versionados = {p.name for p in CHOCO.iterdir()}
    assert datos <= versionados, f"nombres que la fixture no tiene: {datos - versionados}"


def test_el_detail_sale_igual_que_el_versionado(
    choco: tuple[Path, _FetcherFalso, dict[str, str]],
) -> None:
    """El recorte deja el detail de USGS igual, byte a byte, al congelado a mano."""
    destino, _, _ = choco
    escrito = (destino / "detail_superseded.json").read_bytes()
    assert escrito == _bytes_versionados(CHOCO / "detail_superseded.json")
    assert (destino / "cont_mmi_v7.json").read_bytes() == (CHOCO / "cont_mmi_v7.json").read_bytes()


def test_se_conserva_la_secuencia_entera_de_versiones(
    choco: tuple[Path, _FetcherFalso, dict[str, str]],
) -> None:
    """El recorte es por contenido, nunca por entrada: RF-04 necesita v1 -> v7."""
    destino, _, _ = choco
    productos = _json(destino / "detail_superseded.json")["properties"]["products"]
    assert {tipo: len(v) for tipo, v in productos.items()} == {
        "ground-failure": 7,
        "losspager": 8,
        "shakemap": 7,
    }


def test_solo_se_bajan_los_contornos_vigentes_y_el_feed(
    choco: tuple[Path, _FetcherFalso, dict[str, str]],
) -> None:
    """Dos descargas, no 116: ni el `.hdf`, ni los `.tif`, ni versiones superadas."""
    _, fetcher, _ = choco
    assert len(fetcher.bytes_pedidos) == 2
    assert fetcher.bytes_pedidos[0] == _url_contornos_v7()
    assert "fdsnws/event/1/query" in fetcher.bytes_pedidos[1]


def test_hashes_declara_solo_lo_que_se_versiona(
    choco: tuple[Path, _FetcherFalso, dict[str, str]],
) -> None:
    """Cada fichero declarado tiene que sobrevivir a `.gitignore` dentro de la fixture.

    `hashes.json` declaraba los `.tif` de Ground Failure, que `*.tif` descarta
    sin excepcion para `tests/fixtures`: un manifiesto de ficheros que ningun
    clon iba a tener.
    """
    destino, _, hashes = choco
    assert hashes == _json(destino / "hashes.json")
    assert set(hashes) == {p.name for p in destino.iterdir()} - {"hashes.json"}

    rutas = [f"tests/fixtures/golden/choco_2026_08_10/{nombre}" for nombre in hashes]
    # El testigo: si `check-ignore` no marcara un `.tif`, la comprobacion de
    # abajo pasaria por no mirar nada.
    testigo = "tests/fixtures/golden/choco_2026_08_10/zhu_2017_general_model.tif"
    # En bytes y no con `text=True`: en Windows el modo texto convierte cada
    # salto en CRLF, git lee `ruta\r` y no la reconoce como ignorada.
    resultado = subprocess.run(
        ["git", "check-ignore", "--no-index", "--stdin"],
        input=("\n".join([*rutas, testigo]) + "\n").encode("utf-8"),
        capture_output=True,
        cwd=RAIZ,
        check=False,
    )
    ignorados = set(resultado.stdout.decode("utf-8").split())
    assert testigo in ignorados
    assert ignorados == {testigo}, f"declarados y descartados por .gitignore: {ignorados}"


def test_queda_anotado_cual_era_la_preferida(
    choco: tuple[Path, _FetcherFalso, dict[str, str]],
) -> None:
    """El criterio de `_preferred` ya cambio una vez, y puede cambiar otra.

    Ordenar por `preferredWeight` elegia un ShakeMap de mes y medio antes en
    Venezuela. Sin esta anotacion, una fixture que empieza a dar otro resultado
    no distingue «el codigo elige otra» de «USGS publico otra».
    """
    destino, _, _ = choco
    manifiesto = _json(destino / "congelado.json")
    assert manifiesto["preferidas_al_congelar"]["us6000tjl2"]["shakemap"]["version"] == 7


def test_un_evento_doble_nombra_cada_detail_por_su_id(tmp_path: Path) -> None:
    """Venezuela: dos ids, una carpeta, un feed, los nombres que lee su conftest."""
    details = {
        usgs_id: _json(VENEZUELA / f"detail_{usgs_id}_superseded.json")
        for usgs_id in ("us6000t7zp", "us6000t7zc")
    }
    contornos = {
        e["contents"]["download/cont_mmi.json"]["url"]: b"{}"
        for d in details.values()
        for e in d["properties"]["products"]["shakemap"]
    }
    congelar(list(details), tmp_path, fetcher=_FetcherFalso(details, contornos))

    for usgs_id in details:
        nombre = f"detail_{usgs_id}_superseded.json"
        assert (tmp_path / nombre).read_bytes() == _bytes_versionados(VENEZUELA / nombre)
    assert (tmp_path / "feed_reconstruido.json").exists()
    assert not (tmp_path / "detail_superseded.json").exists()
    # Los contornos llevan el id: dos `cont_mmi_v14.json` se pisarian. La
    # fixture de Venezuela es anterior y no los trae porque ningun golden
    # recalcula ese evento; si uno lo hace, este es el nombre que leera.
    assert {p.name for p in tmp_path.glob("cont_mmi_*.json")} == {
        "cont_mmi_us6000t7zp_v14.json",
        "cont_mmi_us6000t7zc_v9.json",
    }


@pytest.mark.parametrize(
    ("feed", "details"),
    [
        (CHOCO / "feed_reconstruido.json", [CHOCO / "detail_superseded.json"]),
        (
            VENEZUELA / "feed_reconstruido.json",
            [
                VENEZUELA / "detail_us6000t7zp_superseded.json",
                VENEZUELA / "detail_us6000t7zc_superseded.json",
            ],
        ),
    ],
    ids=["choco", "venezuela"],
)
def test_la_ventana_del_feed_es_la_de_las_fixtures(feed: Path, details: list[Path]) -> None:
    """La ventana se deriva del origen igual que se reconstruyeron a mano los feeds."""
    consulta = parse_qs(urlparse(_json(feed)["metadata"]["url"]).query)
    origenes = [int(_json(d)["properties"]["time"]) for d in details]
    desde, hasta = ventana_del_feed(origenes)
    assert desde.strftime("%Y-%m-%dT%H:%M:%S") == consulta["starttime"][0]
    assert hasta.strftime("%Y-%m-%dT%H:%M:%S") == consulta["endtime"][0]
    assert "minmagnitude=5.5" in url_del_feed(origenes)


def test_la_url_pide_las_versiones_superadas() -> None:
    assert "includesuperseded=true" in DETAIL_URL
