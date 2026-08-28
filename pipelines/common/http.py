"""Cliente HTTP unico del sistema.

Centralizado por tres razones: poner un ``User-Agent`` identificable (cortesia
minima hacia USGS, que sirve estos feeds gratis), tener un unico lugar donde
vive la politica de reintentos, y poder sustituirlo por fixtures en tests sin
parchear ``httpx`` a mano.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Protocol

import httpx

from .logging import get_logger

_log = get_logger(__name__)

USER_AGENT = "centinela/0.1 (+https://github.com/sforero77/CENTINELA) comunidad GeoAI LATAM"

DEFAULT_TIMEOUT_S = 30.0
DEFAULT_RETRIES = 3

#: Codigos con los que el servidor afirma que el recurso no esta. No son un
#: fallo de red: son una respuesta, y una definitiva.
_AUSENTE = frozenset({404, 410})

#: Timeout del chequeo previo de origenes. Corto porque su unico valor es ser
#: rapido: si hay que esperar treinta segundos por host, deja de compensar.
_PREFLIGHT_TIMEOUT_S = 15.0


class RecursoAusenteError(RuntimeError):
    """El servidor contesto que el recurso no existe.

    SEPARARLA DE UN FALLO DE RED NO ES COSMETICA, y costo tres horas de runner
    el 27-ago-2026. `download_ghsl` captura el fallo de descarga para tratar un
    caso legitimo —las teselas GHSL que solo cubren oceano no existen, y ahi un
    404 *es* la respuesta correcta—, pero hasta hoy la unica excepcion que
    llegaba era un `RuntimeError` generico que significaba lo mismo para un 404
    que para un timeout. Con el JRC caido, las 24 teselas de Peru agotaron sus
    reintentos y se contaron una a una como "probablemente solo oceano": el pais
    se ensamblo con poblacion 0.

    Hereda de `RuntimeError` para no romper a quien ya captura eso —HDX prueba
    el siguiente formato cuando un recurso esta muerto, y esa sigue siendo la
    conducta correcta—.

    Ademas **no se reintenta**. Volver a preguntar tres veces, con esperas de 2,
    4 y 8 segundos, algo que el servidor ya contesto sin ambiguedad son catorce
    segundos por tesela para reconfirmar un no. Medido sobre la corrida sana de
    Peru: cuatro teselas oceanicas, dieciseis segundos cada una, y catorce de
    los dieciseis eran dormir.
    """


#: Sufijo del archivo a medio bajar. Un corte de red, o un Ctrl+C, no puede
#: dejar en su sitio un raster truncado: la siguiente corrida lo daria por bueno
#: y el activo saldria sin filas al sur del pais, cuadrando todo.
PARTIAL_SUFFIX = ".parcial"

#: Trozos por delante del fichero, para no cerrar el hueco por el que se
#: reanuda. `iter_bytes(N)` **acumula hasta N antes de ceder**, asi que un corte
#: por debajo de N pierde todo lo que ya habia llegado; sin argumento cede lo que
#: hay en cuanto hay algo. Lo cazo la prueba del corte a mitad.
#:
#: El coste de escribir a menudo lo absorbe el buffer del sistema de archivos, y
#: el beneficio es que un corte a 300 MB de un fichero de 453 conserva los 300.


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
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code in _AUSENTE:
                    raise RecursoAusenteError(
                        f"{url} no existe (HTTP {exc.response.status_code})"
                    ) from exc
                last = exc
                time.sleep(self._sleep * (2**attempt))
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

    def responde(self, url: str) -> bool:
        """¿Contesta algo el servidor de esta URL?

        LA PREGUNTA NO ES SI EL RECURSO EXISTE, es si el origen esta en pie.
        Por eso **cualquier codigo de estado cuenta como vivo**, 404 y 403 y 405
        incluidos: un servidor que contesta "no lo tengo" o "ese metodo no" esta
        funcionando, y tratarlo como caido convertiria este chequeo en un
        generador de falsos positivos que habria que desactivar a la semana.
        Solo cuenta como caido lo que impide obtener respuesta: conexion
        rechazada, DNS que no resuelve, timeout.

        Sin reintentos y con timeout corto a proposito. Esto tiene que costar
        segundos: su unico valor es descubrir en diez lo que el 27-ago-2026 se
        descubrio en cuatro horas.
        """
        try:
            httpx.head(
                url,
                timeout=_PREFLIGHT_TIMEOUT_S,
                follow_redirects=True,
                headers={"User-Agent": USER_AGENT},
            )
        except (httpx.HTTPError, httpx.StreamError):
            return False
        return True

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

    def download_to(self, url: str, destino: Path) -> Path:
        """Descarga a disco **sin cargar el fichero en memoria**, y reanudable.

        `get_bytes` sirve para un feed de USGS y no para un raster. La serie
        age-sex de WorldPop de Brasil son **9,1 GB en veinte ficheros de 453 MB**
        —la de Colombia son 600 MB— y bajarlos con `get_bytes` significa tener
        453 MB en RAM por fichero, veinte veces, ademas de no escribir un solo
        byte hasta que el ultimo llega. Medido: el build de Brasil paso 55
        minutos sin tocar el disco y sin decir nada.

        Tres cosas que hacen esto viable en una conexion real:

        **Se escribe segun llega**, a un `.parcial`, y solo se renombra al
        destino cuando el fichero esta entero. Es la misma garantia de
        `write_atomic` —un corte no deja un raster truncado que la siguiente
        corrida de por bueno— sostenida sin pasar por memoria.

        **Se reanuda.** Si el `.parcial` de una corrida anterior sigue ahi, se
        pide el resto con `Range` en vez de volver a empezar. El proyecto ya
        dice que reanudar tiene que ser barato porque un build falla tarde; con
        ficheros de 453 MB eso deja de valer a nivel de fichero y tiene que
        valer dentro de el.

        **Se comprueba el tamano final** contra `Content-Length`. Un servidor
        que ignora el `Range` y responde 200 con el archivo entero produciria,
        anadiendo, un fichero con el principio duplicado: pesa mas de la cuenta
        y GDAL lo abre igual. Es justo la clase de fallo que este repositorio
        persigue — plausible y equivocado.

        Raises:
            RuntimeError: si tras los reintentos no se pudo completar, o si el
                tamano final no coincide con el declarado.
        """
        destino.parent.mkdir(parents=True, exist_ok=True)
        parcial = destino.with_name(destino.name + PARTIAL_SUFFIX)
        esperado = 0
        last: Exception | None = None

        for attempt in range(self._retries):
            try:
                desde = parcial.stat().st_size if parcial.exists() else 0
                cabeceras = {"User-Agent": USER_AGENT}
                if desde:
                    cabeceras["Range"] = f"bytes={desde}-"

                with httpx.stream(
                    "GET",
                    url,
                    timeout=self._timeout_s,
                    follow_redirects=True,
                    headers=cabeceras,
                ) as respuesta:
                    respuesta.raise_for_status()
                    # El servidor puede ignorar el Range: entonces manda el
                    # archivo entero y hay que empezar de cero, no anadir.
                    reanuda = desde > 0 and respuesta.status_code == 206
                    if desde and not reanuda:
                        desde = 0
                    # `Content-Length` cuenta bytes **en la red**. Si el
                    # servidor comprime, httpx descomprime al vuelo y lo que
                    # acaba en disco es mayor — sin que nada haya ido mal.
                    #
                    # Tumbo diez de diecinueve builds el 27-ago-2026:
                    # "airports.csv llego incompleto: 12707477 bytes de
                    # 3882778", que es exactamente el ratio de un CSV gzipado.
                    # El guardia de integridad convertido en el fallo.
                    comprimido = respuesta.headers.get("content-encoding", "")
                    esperado = (
                        0 if comprimido else desde + int(respuesta.headers.get("content-length", 0))
                    )

                    modo = "ab" if reanuda else "wb"
                    with parcial.open(modo) as fh:
                        for trozo in respuesta.iter_bytes():
                            fh.write(trozo)

                escrito = parcial.stat().st_size
                if esperado and escrito != esperado:
                    # Un corte deja **menos** bytes de los anunciados, y esos
                    # bytes son un prefijo valido: se conservan y el reintento
                    # sigue desde ahi. Borrarlos —como hacia la primera version
                    # de esto, y lo cazo su prueba— deja el reanudado inservible
                    # justo en los ficheros de 453 MB que lo motivan.
                    #
                    # De **mas** bytes no se puede reanudar: lo que hay en disco
                    # ya no es prefijo de nada conocido, asi que se descarta.
                    if escrito > esperado:
                        parcial.unlink(missing_ok=True)
                    raise RuntimeError(f"{url} llego incompleto: {escrito} bytes de {esperado}.")
                parcial.replace(destino)
                _log.info(
                    "descarga completa",
                    extra={
                        "context": {
                            "destino": destino.name,
                            "mb": round(escrito / 1e6, 1),
                            "reanudada_desde_mb": round(desde / 1e6, 1) if desde else 0,
                        }
                    },
                )
                return destino

            except httpx.HTTPStatusError as exc:
                # Un 404 aqui no deja `.parcial` que reanudar ni tiene sentido
                # reintentar: el recurso no esta y el servidor lo dijo.
                if exc.response.status_code in _AUSENTE:
                    parcial.unlink(missing_ok=True)
                    raise RecursoAusenteError(
                        f"{url} no existe (HTTP {exc.response.status_code})"
                    ) from exc
                last = exc
                time.sleep(self._sleep * (2**attempt))
            except (httpx.HTTPError, httpx.StreamError, RuntimeError) as exc:  # pragma: no cover
                last = exc
                delay = self._sleep * (2**attempt)
                _log.warning(
                    "reintento de descarga",
                    extra={
                        "context": {
                            "url": url,
                            "intento": attempt + 1,
                            "espera_s": delay,
                            # Lo ya bajado se conserva: el reintento sigue desde ahi.
                            "bajado_mb": round(parcial.stat().st_size / 1e6, 1)
                            if parcial.exists()
                            else 0,
                        }
                    },
                )
                time.sleep(delay)

        raise RuntimeError(f"No se pudo descargar {url} tras {self._retries} intentos") from last


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

    def responde(self, url: str) -> bool:
        """En pruebas no hay origen que pueda estar caido."""
        return True

    def get_range(self, url: str, start: int, end: int) -> bytes:
        """Rango sobre el contenido grabado, para probar la extraccion de ZIPs."""
        return self.get_bytes(url)[start : end + 1]

    def content_length(self, url: str) -> int:
        return len(self.get_bytes(url))

    def download_to(self, url: str, destino: Path) -> Path:
        """Vuelca el contenido grabado, con el mismo contrato que el real.

        Pasa por `.parcial` a proposito, aunque aqui no haya red que se corte:
        una fixture que escribe directo al destino no ejercitaria la garantia
        que hace segura la ruta real, y la prueba estaria mirando otra cosa.
        """
        destino.parent.mkdir(parents=True, exist_ok=True)
        parcial = destino.with_name(destino.name + PARTIAL_SUFFIX)
        parcial.write_bytes(self.get_bytes(url))
        parcial.replace(destino)
        return destino
