"""Descarga a disco por streaming y reanudable.

`get_bytes` sirve para un feed de USGS y no para un raster. La serie age-sex de
WorldPop de Brasil son **9,1 GB en veinte ficheros de 453 MB** —la de Colombia
son 600 MB— y bajarlos cargandolos en memoria significa 453 MB de RAM por
fichero y ni un byte en disco hasta que llega el ultimo. Medido: el build de
Brasil paso 55 minutos sin tocar el disco y sin decir nada.

Estas pruebas levantan un **servidor HTTP de verdad** en localhost. Es la unica
forma de ejercitar lo que importa: que el `Range` se pida, que el servidor lo
honre o no, y que un corte a mitad deje algo reanudable en vez de un fichero
truncado en su sitio. Una fixture no puede fallar a mitad de la transferencia.

No estan marcadas `network`: no salen de la maquina.
"""

from __future__ import annotations

import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

from pipelines.common.http import PARTIAL_SUFFIX, HttpFetcher

#: Contenido servido. Varios megas, para que un corte a mitad deje detras algo
#: que de verdad se pueda reanudar y no un buffer sin ceder.
CUERPO = bytes(range(256)) * 20_000  # 5,1 MB


class _Servidor(BaseHTTPRequestHandler):
    """Sirve `CUERPO`, con o sin soporte de `Range` segun se le pida."""

    #: Lo fija cada prueba antes de arrancar.
    honra_rangos = True
    #: Corta la respuesta tras estos bytes, simulando una caida.
    corta_en: int | None = None
    #: Sirve el cuerpo comprimido, anunciando el tamano **comprimido** en
    #: `Content-Length` — que es lo que hace cualquier servidor con gzip.
    comprime = False

    def log_message(self, *_: object) -> None:  # silencio en la salida del test
        pass

    def do_GET(self) -> None:
        rango = self.headers.get("Range")
        desde = 0
        if rango and self.honra_rangos:
            desde = int(rango.removeprefix("bytes=").split("-")[0])
            self.send_response(206)
            self.send_header("Content-Range", f"bytes {desde}-{len(CUERPO) - 1}/{len(CUERPO)}")
        else:
            self.send_response(200)

        trozo = CUERPO[desde:]
        if self.comprime:
            import gzip

            empaquetado = gzip.compress(trozo)
            self.send_header("Content-Encoding", "gzip")
            self.send_header("Content-Length", str(len(empaquetado)))
            self.end_headers()
            self.wfile.write(empaquetado)
            return

        if self.corta_en is not None:
            # Se anuncia el tamano completo y se envia menos: es como se ve un
            # corte de red desde el cliente.
            self.send_header("Content-Length", str(len(trozo)))
            self.end_headers()
            self.wfile.write(trozo[: self.corta_en])
            return

        self.send_header("Content-Length", str(len(trozo)))
        self.end_headers()
        self.wfile.write(trozo)


@pytest.fixture
def servidor() -> Iterator[type[_Servidor]]:
    _Servidor.honra_rangos = True
    _Servidor.corta_en = None
    _Servidor.comprime = False
    httpd = HTTPServer(("127.0.0.1", 0), _Servidor)
    hilo = threading.Thread(target=httpd.serve_forever, daemon=True)
    hilo.start()
    _Servidor.puerto = httpd.server_address[1]  # type: ignore[attr-defined]
    try:
        yield _Servidor
    finally:
        httpd.shutdown()
        httpd.server_close()


def _url(servidor: type[_Servidor]) -> str:
    return f"http://127.0.0.1:{servidor.puerto}/raster.tif"  # type: ignore[attr-defined]


def _cliente() -> HttpFetcher:
    # `sleep=0`: los reintentos de estas pruebas no tienen por que esperar.
    return HttpFetcher(timeout_s=10.0, retries=3, sleep=0.0)


# --- El caso normal ---------------------------------------------------------


def test_descarga_entera_y_deja_el_fichero_en_su_sitio(
    servidor: type[_Servidor], tmp_path: Path
) -> None:
    destino = tmp_path / "raster.tif"

    _cliente().download_to(_url(servidor), destino)

    assert destino.read_bytes() == CUERPO


def test_no_queda_ningun_parcial_tras_una_descarga_limpia(
    servidor: type[_Servidor], tmp_path: Path
) -> None:
    """Un `.parcial` olvidado hace que la siguiente corrida intente reanudar."""
    destino = tmp_path / "raster.tif"

    _cliente().download_to(_url(servidor), destino)

    assert not (tmp_path / f"raster.tif{PARTIAL_SUFFIX}").exists()


def test_crea_el_directorio_de_destino(servidor: type[_Servidor], tmp_path: Path) -> None:
    destino = tmp_path / "capas" / "pop" / "raster.tif"

    _cliente().download_to(_url(servidor), destino)

    assert destino.is_file()


# --- El corte a mitad -------------------------------------------------------
#
# `download_to` reintenta por dentro, asi que ante un servidor que corta una vez
# **la descarga termina**: reanuda y completa. Para observar el estado que deja
# un unico intento fallido hace falta un cliente sin reintentos.


def _cliente_de_un_intento() -> HttpFetcher:
    return HttpFetcher(timeout_s=10.0, retries=1, sleep=0.0)


def test_un_corte_no_deja_el_fichero_truncado_en_su_sitio(
    servidor: type[_Servidor], tmp_path: Path
) -> None:
    """Es la garantia entera de `write_atomic`, sostenida sin pasar por memoria.

    Un raster de poblacion a medias **no falla al abrirse**: simplemente le
    faltan filas al sur del pais, y el activo sale cuadrando todo. Por eso lo
    incompleto no puede llevar nunca el nombre del destino.
    """
    servidor.corta_en = 2_000_000
    destino = tmp_path / "raster.tif"

    with pytest.raises(RuntimeError):
        _cliente_de_un_intento().download_to(_url(servidor), destino)

    assert not destino.exists(), "un fichero incompleto llego a su nombre final"


def test_lo_ya_bajado_sobrevive_para_reanudar(servidor: type[_Servidor], tmp_path: Path) -> None:
    """Reanudar tiene que ser barato: es la regla del proyecto para los builds.

    Con ficheros de 453 MB deja de valer a nivel de fichero y tiene que valer
    dentro de el. Borrar el parcial al fallar —como hacia la primera version de
    esto— deja el reanudado inservible justo donde hace falta.
    """
    servidor.corta_en = 2_000_000
    destino = tmp_path / "raster.tif"

    with pytest.raises(RuntimeError):
        _cliente_de_un_intento().download_to(_url(servidor), destino)

    parcial = tmp_path / f"raster.tif{PARTIAL_SUFFIX}"
    assert parcial.exists()
    assert parcial.stat().st_size == 2_000_000, "no se conservo lo ya bajado"


def test_la_segunda_llamada_sigue_donde_quedo_la_primera(
    servidor: type[_Servidor], tmp_path: Path
) -> None:
    """Y no vuelve a pedir desde el byte cero."""
    servidor.corta_en = 2_000_000
    destino = tmp_path / "raster.tif"
    with pytest.raises(RuntimeError):
        _cliente_de_un_intento().download_to(_url(servidor), destino)

    servidor.corta_en = None
    _cliente_de_un_intento().download_to(_url(servidor), destino)

    assert destino.read_bytes() == CUERPO


def test_reintenta_por_dentro_hasta_completar(servidor: type[_Servidor], tmp_path: Path) -> None:
    """El comportamiento que de verdad hace viable bajar 9,1 GB.

    Un servidor que corta cada dos megas no impide terminar: cada intento
    reanuda desde donde quedo el anterior. Sin reanudado, los mismos tres
    intentos se quedarian los tres en el mismo sitio.
    """
    servidor.corta_en = 2_000_000
    destino = tmp_path / "raster.tif"

    _cliente().download_to(_url(servidor), destino)

    assert destino.read_bytes() == CUERPO


# --- El servidor que ignora el Range ----------------------------------------


def test_un_servidor_que_ignora_el_range_no_duplica_el_principio(
    servidor: type[_Servidor], tmp_path: Path
) -> None:
    """El fallo plausible y equivocado que esta ruta tiene que evitar.

    Si el servidor responde 200 con el archivo entero y el cliente **anade** a
    lo que ya tenia, sale un fichero con el principio repetido: pesa mas de la
    cuenta y GDAL lo abre igual, con filas duplicadas. Hay que empezar de cero.
    """
    servidor.corta_en = 2_000_000
    destino = tmp_path / "raster.tif"
    with pytest.raises(RuntimeError):
        _cliente_de_un_intento().download_to(_url(servidor), destino)
    assert (tmp_path / f"raster.tif{PARTIAL_SUFFIX}").stat().st_size == 2_000_000

    servidor.corta_en = None
    servidor.honra_rangos = False
    _cliente_de_un_intento().download_to(_url(servidor), destino)

    assert destino.stat().st_size == len(CUERPO), "el principio se duplico"
    assert destino.read_bytes() == CUERPO


# --- Que de verdad no pase por memoria --------------------------------------


def test_no_carga_el_fichero_entero_en_memoria() -> None:
    """La razon de existir de este metodo, leida en su codigo.

    Se comprueba sobre el fuente porque el sintoma —453 MB de RAM por fichero—
    no se puede observar con un cuerpo de prueba de un mega. Lo que se fija es
    la decision: se itera la respuesta y se escribe por trozos, no se pide
    `.content`.
    """
    import inspect

    fuente = inspect.getsource(HttpFetcher.download_to)

    assert "iter_bytes" in fuente, "la descarga volvio a leer la respuesta entera"
    assert ".content" not in fuente
    assert "httpx.stream" in fuente


def test_las_rutas_pesadas_bajan_por_streaming() -> None:
    """Las dos que motivaron el cambio, y la generica del manifest.

    Escribir el metodo y no llamarlo desde donde estan los 9,1 GB seria
    exactamente el fallo que este repositorio persigue.
    """
    import inspect

    from pipelines.p0_exposure import download

    for funcion in (
        download.download_ghsl,
        download.download_worldpop_agesex,
        download.download_manifest,
    ):
        assert "download_to" in inspect.getsource(funcion), (
            f"{funcion.__name__} sigue bajando con get_bytes"
        )


def test_una_respuesta_comprimida_no_se_toma_por_truncada(
    servidor: type[_Servidor], tmp_path: Path
) -> None:
    """`Content-Length` cuenta bytes **en la red**, no en disco.

    Si el servidor comprime, httpx descomprime al vuelo y lo escrito es mayor
    que lo anunciado sin que nada haya ido mal. El 27-ago-2026 esto tumbo diez
    de diecinueve builds de pais:

        airports.csv llego incompleto: 12707477 bytes de 3882778

    que es exactamente el ratio de un CSV gzipado. Un guardia de integridad
    convertido en el fallo — y peor que no tenerlo, porque parecia un problema
    de red y mandaba a mirar al sitio equivocado.
    """
    servidor.comprime = True
    destino = tmp_path / "airports.csv"

    _cliente().download_to(_url(servidor), destino)

    assert destino.read_bytes() == CUERPO
    assert not destino.with_suffix(destino.suffix + PARTIAL_SUFFIX).exists()


def test_sin_compresion_el_guardia_sigue_vivo(servidor: type[_Servidor], tmp_path: Path) -> None:
    """El arreglo no puede desactivar la comprobacion en el caso normal.

    Sin `Content-Encoding`, el tamano anunciado si describe lo que se escribe, y
    una descarga corta sigue siendo una descarga corta.
    """
    servidor.corta_en = 1024
    destino = tmp_path / "raster.tif"

    # El mensaje final es el del envoltorio de reintentos; el "llego incompleto"
    # queda dentro, encadenado. Lo que importa aqui es que **falle**.
    with pytest.raises(RuntimeError, match="No se pudo descargar"):
        _cliente_de_un_intento().download_to(_url(servidor), destino)

    assert not destino.exists(), "un fichero corto no puede quedar en su sitio"
