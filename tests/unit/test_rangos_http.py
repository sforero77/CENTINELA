"""Lectura por rangos: los dos modos de fallo que no se distinguen solos.

Un servidor puede sabotear una extraccion por rangos de dos formas silenciosas:
ignorando la cabecera y mandando el archivo entero, o aceptandola y no mandando
nada. La primera cuesta gigabytes; la segunda manda a depurar la red cuando el
problema esta en el servidor.
"""

from __future__ import annotations

from typing import Any

import httpx
import pytest

from pipelines.common.http import HttpFetcher

URL = "https://ejemplo/archivo.zip"


def _fetcher_que_responde(monkeypatch: pytest.MonkeyPatch, **kwargs: Any) -> HttpFetcher:
    def falso_get(url: str, **_: Any) -> httpx.Response:
        return httpx.Response(request=httpx.Request("GET", url), **kwargs)

    monkeypatch.setattr(httpx, "get", falso_get)
    return HttpFetcher(retries=1, sleep=0.0)


def test_un_rango_servido_se_devuelve(monkeypatch: pytest.MonkeyPatch) -> None:
    f = _fetcher_que_responde(monkeypatch, status_code=206, content=b"datos")
    assert f.get_range(URL, 0, 4) == b"datos"


def test_ignorar_el_range_es_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Un 200 aqui significa el archivo entero: pueden ser gigabytes."""
    f = _fetcher_que_responde(monkeypatch, status_code=200, content=b"x" * 1000)
    with pytest.raises(RuntimeError, match="ignoro el Range"):
        f.get_range(URL, 0, 4)


def test_un_206_vacio_es_error_y_lo_dice(monkeypatch: pytest.MonkeyPatch) -> None:
    """El caso del geoportal del DANE: acepta el rango y cierra sin enviar nada.

    Solo ocurria por encima de ~1,5 GB de desplazamiento. El mensaje generico
    de "no se pudo leer el rango" mandaba a buscar un fallo de red inexistente.
    """
    f = _fetcher_que_responde(monkeypatch, status_code=206, content=b"")
    with pytest.raises(RuntimeError, match="cuerpo vacio") as exc:
        f.get_range(URL, 3_389_848_331, 3_389_918_330)
    assert "limite de desplazamiento" in str(exc.value)
    assert "entrega mas liviana" in str(exc.value)
