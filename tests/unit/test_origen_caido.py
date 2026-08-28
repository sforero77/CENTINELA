"""Distinguir «no existe» de «no pude preguntar».

El 27-ago-2026 el JRC estuvo caido tres horas. `download_ghsl` captura el fallo
de descarga para tratar un caso legitimo —las teselas GHSL que solo cubren
oceano no existen, y ahi un 404 *es* la respuesta correcta—, pero la unica
excepcion que llegaba era un `RuntimeError` generico que significaba lo mismo
para un 404 que para un timeout. Las 24 teselas de Peru se contaron una a una
como "probablemente solo oceano" y el pais se ensamblo con poblacion 0.

Medido sobre las dos corridas de aquel dia:

=====================  ======================  ==================
                       Tesela oceanica (404)   Origen caido
=====================  ======================  ==================
por intento            instantaneo             ~133 s
intentos                3                       3
espera entre intentos   2+4+8 = 14 s            14 s
coste por tesela        ~16 s                   ~6,7 min
en Peru                 4 teselas -> 1 min      24 -> 2 h 40 min
desenlace               correcto                "oceano" — falso
=====================  ======================  ==================

Estas pruebas levantan un servidor real en localhost, como el resto de las de
descarga: una fixture no puede negarse a aceptar una conexion.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

from pipelines.common.geo import BBox
from pipelines.common.http import HttpFetcher, RecursoAusenteError
from pipelines.common.manifest import Manifest
from pipelines.p0_exposure.download import (
    OrigenCaidoError,
    comprobar_origenes,
    download_ghsl,
)


class _Servidor(BaseHTTPRequestHandler):
    """Contesta con el codigo que le pida cada prueba."""

    codigo = 404
    #: Cuenta cuantas veces se ha pedido algo, para ver si hubo reintentos.
    peticiones = 0

    def log_message(self, *_: object) -> None:
        pass

    def _responder(self) -> None:
        type(self).peticiones += 1
        self.send_response(self.codigo)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self) -> None:  # el nombre lo fija BaseHTTPRequestHandler
        self._responder()

    def do_HEAD(self) -> None:
        self._responder()


@pytest.fixture
def servidor() -> Iterator[str]:
    _Servidor.peticiones = 0
    httpd = HTTPServer(("127.0.0.1", 0), _Servidor)
    hilo = threading.Thread(target=httpd.serve_forever, daemon=True)
    hilo.start()
    try:
        yield f"http://127.0.0.1:{httpd.server_address[1]}"
    finally:
        httpd.shutdown()
        httpd.server_close()


# --- Un 404 es una respuesta, no un fallo -----------------------------------


def test_un_404_no_se_reintenta(servidor: str, tmp_path: Path) -> None:
    """Volver a preguntar tres veces algo ya contestado son 14 s de dormir.

    Sobre la corrida sana de Peru: cuatro teselas oceanicas, dieciseis segundos
    cada una, y catorce de los dieciseis eran esperar entre reintentos para
    reconfirmar un no.
    """
    _Servidor.codigo = 404
    fetcher = HttpFetcher(timeout_s=5.0, sleep=1.0)

    arranque = time.monotonic()
    with pytest.raises(RecursoAusenteError):
        fetcher.download_to(f"{servidor}/no_existe.tif", tmp_path / "x.tif")
    transcurrido = time.monotonic() - arranque

    assert _Servidor.peticiones == 1, "un 404 definitivo se pidio mas de una vez"
    # Con reintentos serian 1+2+4 = 7 s de espera como minimo.
    assert transcurrido < 2.0, f"tardo {transcurrido:.1f}s: sigue durmiendo entre intentos"


def test_un_500_si_se_reintenta(servidor: str, tmp_path: Path) -> None:
    """Lo contrario tambien importa: un fallo del servidor puede ser pasajero.

    Si el cambio de arriba se llevara por delante el reintento, cualquier hipo
    de un origen tumbaria un build de cuatro horas.
    """
    _Servidor.codigo = 500
    fetcher = HttpFetcher(timeout_s=5.0, retries=3, sleep=0.01)

    with pytest.raises(RuntimeError) as exc:
        fetcher.download_to(f"{servidor}/roto.tif", tmp_path / "x.tif")

    assert not isinstance(exc.value, RecursoAusenteError)
    assert _Servidor.peticiones == 3, "un 500 dejo de reintentarse"


#: Caja de Peru, la del fallo real.
CAJA_PER = BBox(lon_min=-84.69, lat_min=-20.25, lon_max=-68.6, lat_max=0.01)


class _FetcherQueFalla:
    """Un origen que siempre falla, con la excepcion que se le indique."""

    def __init__(self, excepcion: Exception) -> None:
        self._excepcion = excepcion
        self.intentos = 0

    def download_to(self, url: str, destino: Path) -> Path:
        self.intentos += 1
        raise self._excepcion


def test_un_origen_roto_no_se_concluye_como_oceano(tmp_path: Path) -> None:
    """El fallo de Peru, en una prueba.

    Con el origen fallando por algo que no es "no existe", `download_ghsl` no
    puede concluir "solo oceano". Antes devolvia la lista vacia, `pop_h3` se
    creaba vacia, el LEFT JOIN la volvia ceros y el pais se ensamblaba con
    poblacion 0 — sin que nada fallara hasta el assert final.
    """
    fetcher = _FetcherQueFalla(RuntimeError("No se pudo descargar tras 3 intentos"))

    with pytest.raises(RuntimeError) as exc:
        download_ghsl(tmp_path, CAJA_PER, fetcher=fetcher)  # type: ignore[arg-type]

    assert not isinstance(exc.value, RecursoAusenteError)
    assert fetcher.intentos == 1, "no se detuvo en la primera tesela que fallo"


def test_una_tesela_que_de_verdad_no_existe_sigue_siendo_oceano(tmp_path: Path) -> None:
    """Y el caso legitimo tiene que seguir funcionando.

    Peru tiene teselas que solo cubren mar: en la corrida sana fueron cuatro. Si
    esto fallara, ningun pais con costa se podria construir.
    """
    fetcher = _FetcherQueFalla(RecursoAusenteError("no existe (HTTP 404)"))

    assert download_ghsl(tmp_path, CAJA_PER, fetcher=fetcher) == []  # type: ignore[arg-type]
    assert fetcher.intentos > 1, "se detuvo en la primera, y un 404 no es motivo"


# --- El chequeo previo de origenes ------------------------------------------


def _manifest(url: str) -> Manifest:
    return Manifest.from_dict(
        {
            "manifest_id": "per-v0.6",
            "iso3": "PER",
            "generated_utc": "2026-08-23T00:00:00Z",
            "sources": [
                {
                    "id": "ghs_pop_2025",
                    "layer": "pop_ghs",
                    "url": url,
                    "license": "EC-reuse-attribution",
                    "vintage": "R2023A-E2025",
                },
                {
                    "id": "overture_buildings",
                    "layer": "buildings",
                    "url": "s3://overturemaps-us-west-2/release/2026-08-19.0/theme=buildings/type=building",
                    "license": "ODbL-1.0",
                    "vintage": "2026-08-19.0",
                },
            ],
        }
    )


def test_un_origen_que_no_contesta_para_el_build_antes_de_empezar() -> None:
    """Diez segundos en vez de cuatro horas.

    El puerto 1 de localhost no escucha nadie: la conexion se rechaza, que es
    justo lo que hay que distinguir de un servidor que contesta.
    """
    with pytest.raises(OrigenCaidoError) as exc:
        comprobar_origenes(
            _manifest("http://127.0.0.1:1/tile.zip"), fetcher=HttpFetcher(timeout_s=2.0)
        )
    assert "127.0.0.1:1" in str(exc.value)


def test_un_404_no_es_un_origen_caido(servidor: str) -> None:
    """La pregunta es si el servidor esta en pie, no si el recurso existe.

    Un chequeo que tratara un 404 como caida seria un generador de falsos
    positivos —las URL del manifest son paginas de dataset y mosaicos globales
    que nadie pide entera— y estaria desactivado en una semana.
    """
    _Servidor.codigo = 404
    comprobar_origenes(_manifest(f"{servidor}/lo_que_sea.zip"), fetcher=HttpFetcher(timeout_s=2.0))


def test_un_405_tampoco(servidor: str) -> None:
    """Hay servidores que no aceptan HEAD. Siguen estando vivos."""
    _Servidor.codigo = 405
    comprobar_origenes(_manifest(f"{servidor}/lo_que_sea.zip"), fetcher=HttpFetcher(timeout_s=2.0))


def test_las_fuentes_remotas_no_se_comprueban() -> None:
    """Un HEAD contra un prefijo `s3://` no significa nada.

    Overture y la cobertura del suelo se leen en remoto y su disponibilidad la
    comprueba DuckDB cuando toca. El manifest de arriba trae una de cada: si el
    chequeo intentara la de Overture, esta prueba fallaria por otra razon.
    """
    solo_remota = Manifest.from_dict(
        {
            "manifest_id": "per-v0.6",
            "iso3": "PER",
            "generated_utc": "2026-08-23T00:00:00Z",
            "sources": [
                {
                    "id": "overture_buildings",
                    "layer": "buildings",
                    "url": "s3://overturemaps-us-west-2/release/2026-08-19.0/theme=buildings/type=building",
                    "license": "ODbL-1.0",
                    "vintage": "2026-08-19.0",
                }
            ],
        }
    )
    comprobar_origenes(solo_remota, fetcher=HttpFetcher(timeout_s=2.0))


# --- El codigo de salida y el reintento del workflow ------------------------


def test_un_origen_caido_sale_con_su_propio_codigo(monkeypatch: pytest.MonkeyPatch) -> None:
    """Un activo que no pasa los asserts y un origen caido no son lo mismo.

    Los dos salian como exit 1 el 27-ago-2026, y distinguirlos exigia leer
    cuatro horas de log. Ante el primero hay que mirar el manifest; ante el
    segundo hay que reintentar mas tarde y ya esta.
    """
    import argparse

    from pipelines import cli

    def _cae(*_a: object, **_k: object) -> None:
        raise OrigenCaidoError("Origenes que no contestan: jeodpp.jrc.ec.europa.eu")

    monkeypatch.setattr(cli, "build_country", _cae)
    args = argparse.Namespace(iso3="PER", out=None, liberar_rasters=True)
    assert cli._cmd_country(args) == cli.EXIT_ORIGEN_CAIDO


def test_el_workflow_solo_reintenta_el_origen_caido() -> None:
    """Reintentar un fallo determinista solo retrasa el diagnostico.

    Un activo que no pasa los asserts de calidad falla igual las tres veces: lo
    unico que cambia es que el operador se entera media hora mas tarde.
    """
    from pipelines.common.paths import REPO_ROOT

    workflow = (REPO_ROOT / ".github" / "workflows" / "exposure_quarterly.yml").read_text("utf-8")

    assert 'if [ "$CODIGO" -ne 4 ]' in workflow, "el workflow reintenta cualquier fallo"
    assert "no se reintenta" in workflow
    # Y el 4 tiene que ser el mismo que emite el CLI, no un numero suelto.
    from pipelines.cli import EXIT_ORIGEN_CAIDO

    assert EXIT_ORIGEN_CAIDO == 4
