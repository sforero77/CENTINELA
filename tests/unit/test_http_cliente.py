"""`HttpFetcher` de verdad, sin red: con el transporte simulado de httpx.

DOS HUECOS QUE CERRO LA AUDITORIA DEL 5-SEP-2026.

**#80.** `HttpFetcher._get` —por donde pasan `get_json` y `get_bytes`, o sea
todos los feeds de USGS, la API de HDX y FIRMS— no se ejecutaba en la suite.
La traduccion de 404 a `RecursoAusenteError`, que es lo que separa "la tesela
GHSL es oceano" de "el JRC esta caido" (tres horas de runner el 27-ago-2026),
estaba probada para `download_to` y para nada mas. Una regresion en `_get`
habria salido verde.

**#158.** Los tres bucles de reintento dormian tambien despues del ultimo
intento: con los valores por defecto, ocho segundos de siesta antes de un
`raise` que ya estaba decidido.

`httpx.MockTransport` y no un servidor en localhost como en
`test_descarga_streaming.py`: aqui no hace falta cortar una transferencia a
mitad, solo decidir que contesta el servidor, y asi cada prueba dice en una
linea que respuesta recibe. El parche va sobre `httpx.get` y `httpx.stream`,
que es exactamente lo que llama el codigo de produccion: todo lo de dentro
—`raise_for_status`, cabeceras, redirecciones, reintentos— es el real.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import httpx
import pytest

from pipelines.common.http import USER_AGENT, HttpFetcher, RecursoAusenteError

URL = "https://origen.example/recurso"


class _Origen:
    """Servidor simulado: anota cada peticion y contesta lo que se le diga."""

    def __init__(self, respuestas: list[httpx.Response | Exception]) -> None:
        self._respuestas = respuestas
        self.peticiones: list[httpx.Request] = []

    def __call__(self, peticion: httpx.Request) -> httpx.Response:
        self.peticiones.append(peticion)
        # La ultima se repite: "siempre 500" se escribe con una sola.
        respuesta = self._respuestas[min(len(self.peticiones), len(self._respuestas)) - 1]
        if isinstance(respuesta, Exception):
            raise respuesta
        return respuesta


@pytest.fixture
def siestas(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    """Lo que el cliente habria dormido, sin dormirlo."""
    anotadas: list[float] = []
    # Por ruta y no por `modulo.time`: es el `time.sleep` que ve `http.py`.
    monkeypatch.setattr("pipelines.common.http.time.sleep", anotadas.append)
    return anotadas


@pytest.fixture
def servir(monkeypatch: pytest.MonkeyPatch) -> Iterator[Callable[[_Origen], None]]:
    clientes: list[httpx.Client] = []

    def montar(origen: _Origen) -> None:
        cliente = httpx.Client(transport=httpx.MockTransport(origen))
        clientes.append(cliente)
        monkeypatch.setattr(httpx, "get", lambda url, **kw: cliente.get(url, **kw))
        monkeypatch.setattr(
            httpx, "stream", lambda metodo, url, **kw: cliente.stream(metodo, url, **kw)
        )

    yield montar
    for cliente in clientes:
        cliente.close()


def _fetcher(**kw: Any) -> HttpFetcher:
    return HttpFetcher(**{"retries": 3, "sleep": 2.0, **kw})


# --- #80: `_get`, por fin ejecutado -------------------------------------------


def test_get_json_lee_el_cuerpo_y_se_identifica(servir: Any, siestas: list[float]) -> None:
    origen = _Origen([httpx.Response(200, json={"type": "FeatureCollection"})])
    servir(origen)

    assert _fetcher().get_json(URL) == {"type": "FeatureCollection"}
    # La cortesia minima con USGS, que sirve estos feeds gratis.
    assert origen.peticiones[0].headers["User-Agent"] == USER_AGENT
    assert siestas == []


@pytest.mark.parametrize("codigo", [404, 410])
def test_get_json_traduce_ausente_y_no_reintenta(
    servir: Any, siestas: list[float], codigo: int
) -> None:
    """Un "no existe" es una respuesta, y definitiva: ni reintento ni siesta."""
    origen = _Origen([httpx.Response(codigo)])
    servir(origen)

    with pytest.raises(RecursoAusenteError, match=str(codigo)):
        _fetcher().get_json(URL)
    assert len(origen.peticiones) == 1
    assert siestas == []


@pytest.mark.parametrize("codigo", [404, 410])
def test_get_bytes_traduce_ausente_y_no_reintenta(
    servir: Any, siestas: list[float], codigo: int
) -> None:
    origen = _Origen([httpx.Response(codigo)])
    servir(origen)

    with pytest.raises(RecursoAusenteError):
        _fetcher().get_bytes(URL)
    assert len(origen.peticiones) == 1


def test_un_500_no_es_ausente(servir: Any, siestas: list[float]) -> None:
    """La otra mitad de la distincion: un servidor roto NO es "no existe".

    Es la confusion que ensamblo Peru con poblacion 0: si un 500 se tradujera a
    `RecursoAusenteError`, `download_ghsl` lo contaria como tesela oceanica.
    """
    servir(_Origen([httpx.Response(500)]))

    with pytest.raises(RuntimeError) as exc:
        _fetcher().get_bytes(URL)
    assert not isinstance(exc.value, RecursoAusenteError)


def test_un_fallo_pasajero_se_reintenta_hasta_que_contesta(
    servir: Any, siestas: list[float]
) -> None:
    origen = _Origen(
        [httpx.Response(503), httpx.ConnectError("caido"), httpx.Response(200, content=b"ok")]
    )
    servir(origen)

    assert _fetcher().get_bytes(URL) == b"ok"
    assert len(origen.peticiones) == 3
    assert siestas == [2.0, 4.0]


def test_sigue_las_redirecciones(servir: Any, siestas: list[float]) -> None:
    """HDX y los buckets de S3 redirigen; sin `follow_redirects` llegaria un 302."""
    origen = _Origen(
        [
            httpx.Response(302, headers={"Location": "https://espejo.example/x"}),
            httpx.Response(200, content=b"datos"),
        ]
    )
    servir(origen)

    assert _fetcher().get_bytes(URL) == b"datos"
    assert str(origen.peticiones[-1].url) == "https://espejo.example/x"


# --- #158: ninguna siesta despues del ultimo intento -------------------------


@pytest.mark.parametrize(
    "fallo", [httpx.Response(500), httpx.ConnectError("caido")], ids=["http_500", "red"]
)
def test_get_no_duerme_despues_del_ultimo_intento(
    servir: Any, siestas: list[float], fallo: Any
) -> None:
    """Tres intentos son dos esperas. Eran tres: 2 + 4 + **8** segundos."""
    origen = _Origen([fallo])
    servir(origen)

    with pytest.raises(RuntimeError, match="tras 3 intentos"):
        _fetcher().get_bytes(URL)
    assert len(origen.peticiones) == 3
    assert siestas == [2.0, 4.0]


def test_get_range_no_duerme_despues_del_ultimo_intento(servir: Any, siestas: list[float]) -> None:
    servir(_Origen([httpx.ConnectError("caido")]))

    with pytest.raises(RuntimeError, match="rango"):
        _fetcher().get_range(URL, 0, 9)
    assert siestas == [2.0, 4.0]


def test_download_to_no_duerme_despues_del_ultimo_intento(
    servir: Any, siestas: list[float], tmp_path: Path
) -> None:
    origen = _Origen([httpx.Response(500)])
    servir(origen)

    with pytest.raises(RuntimeError, match="tras 3 intentos"):
        _fetcher().download_to(URL, tmp_path / "raster.tif")
    assert len(origen.peticiones) == 3
    assert siestas == [2.0, 4.0]


def test_un_solo_intento_no_duerme_nada(servir: Any, siestas: list[float]) -> None:
    servir(_Origen([httpx.Response(500)]))

    with pytest.raises(RuntimeError):
        _fetcher(retries=1).get_bytes(URL)
    assert siestas == []


def test_download_to_tambien_traduce_ausente(
    servir: Any, siestas: list[float], tmp_path: Path
) -> None:
    """Ya estaba probado contra un servidor real; aqui se fija por el mismo
    camino que las otras dos, para que las tres rutas se lean juntas."""
    servir(_Origen([httpx.Response(404)]))

    with pytest.raises(RecursoAusenteError):
        _fetcher().download_to(URL, tmp_path / "tesela.zip")
    assert not (tmp_path / "tesela.zip").exists()
    assert siestas == []
