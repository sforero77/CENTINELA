"""Cliente HTTP unico del sistema.

Centralizado por tres razones: poner un ``User-Agent`` identificable (cortesia
minima hacia USGS, que sirve estos feeds gratis), tener un unico lugar donde
vive la politica de reintentos, y poder sustituirlo por fixtures en tests sin
parchear ``httpx`` a mano.
"""

from __future__ import annotations

import json
import time
from typing import Any, Protocol

import httpx

from .logging import get_logger

_log = get_logger(__name__)

USER_AGENT = "centinela/0.1 (+https://github.com/sforero77/CENTINELA) comunidad GeoAI LATAM"

DEFAULT_TIMEOUT_S = 30.0
DEFAULT_RETRIES = 3


class Fetcher(Protocol):
    """Contrato minimo que consumen los pipelines."""

    def get_json(self, url: str) -> dict[str, Any]: ...

    def get_bytes(self, url: str) -> bytes: ...


class HttpFetcher:
    """Implementacion real, con reintento exponencial ante fallo de red."""

    def __init__(
        self,
        *,
        timeout_s: float = DEFAULT_TIMEOUT_S,
        retries: int = DEFAULT_RETRIES,
        sleep: float = 2.0,
    ) -> None:
        self._timeout_s = timeout_s
        self._retries = retries
        self._sleep = sleep

    def _get(self, url: str) -> httpx.Response:
        last: Exception | None = None
        for attempt in range(self._retries):
            try:
                response = httpx.get(
                    url,
                    timeout=self._timeout_s,
                    follow_redirects=True,
                    headers={"User-Agent": USER_AGENT},
                )
                response.raise_for_status()
                return response
            except (httpx.HTTPError, httpx.StreamError) as exc:  # pragma: no cover - red
                last = exc
                delay = self._sleep * (2**attempt)
                _log.warning(
                    "reintento de descarga",
                    extra={"context": {"url": url, "intento": attempt + 1, "espera_s": delay}},
                )
                time.sleep(delay)
        raise RuntimeError(f"No se pudo descargar {url} tras {self._retries} intentos") from last

    def get_json(self, url: str) -> dict[str, Any]:
        payload: dict[str, Any] = self._get(url).json()
        return payload

    def get_bytes(self, url: str) -> bytes:
        return self._get(url).content


class FixtureFetcher:
    """Fetcher de pruebas: sirve respuestas grabadas por URL.

    Es el mecanismo de "cassettes" de §6.2: los golden tests corren sin red y
    el test nocturno contra el feed vivo usa ``HttpFetcher``.
    """

    def __init__(self, responses: dict[str, Any]) -> None:
        self._responses = responses

    def get_json(self, url: str) -> dict[str, Any]:
        try:
            value = self._responses[url]
        except KeyError:
            raise AssertionError(f"URL no grabada en la fixture: {url}") from None
        if isinstance(value, bytes | str):
            parsed: dict[str, Any] = json.loads(value)
            return parsed
        assert isinstance(value, dict)
        return value

    def get_bytes(self, url: str) -> bytes:
        value = self._responses[url]
        if isinstance(value, bytes):
            return value
        if isinstance(value, str):
            return value.encode("utf-8")
        return json.dumps(value).encode("utf-8")
