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


class RangeCapable(Protocol):
    """Cliente que ademas sabe pedir rangos de bytes.

    Lo usa la extraccion selectiva de ZIPs remotos: el MGN del DANE es un solo
    archivo de 3,39 GB del que P0 solo necesita ~100 MB.
    """

    def get_range(self, url: str, start: int, end: int) -> bytes: ...

    def content_length(self, url: str) -> int: ...


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

    def get_range(self, url: str, start: int, end: int) -> bytes:
        """Bytes ``[start, end]`` inclusive.

        Sobrevive a `zip_range`, el modulo que la usaba: aquel parseaba el
        directorio central de un ZIP remoto para bajar cinco ficheros del MGN
        nacional de 3,39 GB, y se borro en la auditoria del 25-ago-2026 porque
        el manifest paso al fichero municipal suelto de 68 MB y el geoportal
        dejo de servir rangos sobre ~1,5 GB. Esto se queda porque es una
        primitiva del cliente HTTP, no una estrategia de descarga, y sus dos
        modos de fallo —206 con cuerpo vacio, 200 con el archivo entero— estan
        medidos contra servidores reales y probados.

        Raises:
            RuntimeError: si el servidor ignora el ``Range`` y responde 200 con
                el archivo entero —aceptarlo en silencio significaria bajar
                gigas creyendo que se bajaron kilobytes—, o si acepta el rango y
                devuelve un cuerpo vacio.
        """
        for attempt in range(self._retries):
            try:
                response = httpx.get(
                    url,
                    timeout=self._timeout_s,
                    follow_redirects=True,
                    headers={"User-Agent": USER_AGENT, "Range": f"bytes={start}-{end}"},
                )
                response.raise_for_status()
                if response.status_code != 206:
                    raise RuntimeError(
                        f"El servidor ignoro el Range en {url} (HTTP "
                        f"{response.status_code}): no se puede extraer por rangos."
                    )
                if not response.content:
                    # Caso visto en el geoportal del DANE el 24-ago-2026: acepta
                    # el rango, responde 206 y cierra sin enviar un byte, pero
                    # solo por encima de ~1,5 GB de desplazamiento. Reintentar no
                    # sirve —falla igual las tres veces— y el mensaje generico de
                    # abajo mandaba a buscar un problema de red que no existia.
                    raise RuntimeError(
                        f"El servidor acepto el rango {start}-{end} de {url} "
                        f"(HTTP 206) y devolvio un cuerpo vacio. Suele ser un "
                        f"limite de desplazamiento del servidor, no un fallo de "
                        f"red: comprueba si sirve rangos pequenos al inicio del "
                        f"archivo y busca una entrega mas liviana de la fuente."
                    )
                return response.content
            except (httpx.HTTPError, httpx.StreamError):  # pragma: no cover - red
                time.sleep(self._sleep * (2**attempt))
        raise RuntimeError(f"No se pudo leer el rango {start}-{end} de {url}")

    def content_length(self, url: str) -> int:
        """Tamano total del recurso, por HEAD."""
        response = httpx.head(
            url,
            timeout=self._timeout_s,
            follow_redirects=True,
            headers={"User-Agent": USER_AGENT},
        )
        response.raise_for_status()
        return int(response.headers.get("content-length", 0))


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

    def get_range(self, url: str, start: int, end: int) -> bytes:
        """Rango sobre el contenido grabado, para probar la extraccion de ZIPs."""
        return self.get_bytes(url)[start : end + 1]

    def content_length(self, url: str) -> int:
        return len(self.get_bytes(url))
