"""El chequeo previo tiene que preguntarle al host que sirve los bytes.

`comprobar_origenes` existe para evitar la forma mas cara de fallar que tiene
este sistema: enterarse de que un origen esta caido despues de horas
intentandolo. El 27-ago-2026 el JRC estuvo caido tres y la corrida de Peru lo
descubrio en la cuarta.

Pero agrupaba por el `netloc` de `source.url`, y para las fuentes de HDX esa url
es —por contrato explicito del propio manifest— la **pagina del catalogo**:

    url: https://data.humdata.org/dataset/cod-ab-col
    hdx_dataset: cod-ab-col

Los bytes salen de otra parte: `production-raw-data-api.s3.amazonaws.com`,
`s3.dualstack.us-east-1.amazonaws.com` o `export.hotosm.org`. Ninguno de los
tres se comprobaba jamas. El chequeo daba el visto bueno con el origen real
caido, que es exactamente lo que existe para no dejar pasar.

Y la otra mitad, del mismo modulo: la unica verificacion de licencia viva del
sistema estaba **debajo** del retorno anticipado por cache, asi que solo corria
la primera vez que el fichero no estaba en disco. En la ruta con cache —la
normal: cada reintento de un build pasa por ella— el archivo entraba al activo
sin consultar nada, justo lo que su docstring dice que no se puede hacer.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from pipelines.common.hdx import HDX_PACKAGE_SHOW, limpiar_cache_hdx, package_show
from pipelines.common.manifest import Manifest, Source
from pipelines.p0_exposure import download

#: Como responde HDX a `package_show` para un dataset del COD-AB.
PAQUETE: dict[str, Any] = {
    "success": True,
    "result": {
        "license_id": "cc-by-igo",
        "resources": [
            {
                "name": "COL Administrative Divisions Shapefiles",
                "format": "SHP",
                "url": "https://production-raw-data-api.s3.amazonaws.com/ISO3/COL/adm.zip",
            }
        ],
    },
}


class _Fetcher:
    """Cuenta las peticiones y registra a que hosts se pregunto si estan vivos."""

    def __init__(self, paquete: dict[str, Any] | None = None) -> None:
        self.paquete = paquete if paquete is not None else PAQUETE
        self.json_pedidos: list[str] = []
        self.preguntados: list[str] = []

    def get_json(self, url: str) -> dict[str, Any]:
        self.json_pedidos.append(url)
        return self.paquete

    def get_bytes(self, url: str) -> bytes:  # pragma: no cover - no se llega
        raise AssertionError(f"el chequeo previo no descarga nada: {url}")

    def responde(self, url: str) -> bool:
        self.preguntados.append(url)
        return True


def _manifest_hdx() -> Manifest:
    return Manifest(
        manifest_id="col-v0.6",
        iso3="COL",
        generated_utc="2026-08-23T00:00:00Z",
        sources=(
            Source(
                id="cod_ab_col",
                layer="divisions",
                url="https://data.humdata.org/dataset/cod-ab-col",
                license="CC-BY-IGO",
                vintage="COD-AB-2025-05-27",
                hdx_dataset="cod-ab-col",
            ),
        ),
    )


def test_se_pregunta_al_host_de_los_bytes_no_al_del_catalogo() -> None:
    """`data.humdata.org` puede estar en pie con el S3 de los datos caido."""
    fetcher = _Fetcher()
    download.comprobar_origenes(_manifest_hdx(), fetcher=fetcher)  # type: ignore[arg-type]

    hosts = {url.split("/")[2] for url in fetcher.preguntados}
    assert hosts == {"production-raw-data-api.s3.amazonaws.com"}, (
        f"el chequeo previo pregunto por {hosts}: la pagina del catalogo esta "
        f"siempre en pie y no dice nada de si los bytes se pueden bajar"
    )


def test_si_no_se_puede_resolver_se_cae_al_catalogo_y_no_se_detiene() -> None:
    """Un chequeo previo no es sitio para tumbar un build.

    Si HDX no contesta al `package_show`, el error de verdad saldra al
    descargar, con su mensaje y su contexto. Aqui basta con no quedarse sin
    representante y no reventar.
    """

    class _Roto(_Fetcher):
        def get_json(self, url: str) -> dict[str, Any]:
            raise RuntimeError("HDX no contesta")

    fetcher = _Roto()
    download.comprobar_origenes(_manifest_hdx(), fetcher=fetcher)  # type: ignore[arg-type]

    hosts = {url.split("/")[2] for url in fetcher.preguntados}
    assert hosts == {"data.humdata.org"}


def test_un_dataset_se_pregunta_una_vez_por_corrida() -> None:
    """Resolver y verificar la licencia piden el mismo documento.

    Desde que la verificacion corre tambien en el camino con cache, un pais con
    tres fuentes HDX hacia hasta seis peticiones identicas por build. HDX es un
    servicio publico y gratuito.
    """
    limpiar_cache_hdx()
    fetcher = _Fetcher()

    primero = package_show(fetcher, "cod-ab-col")  # type: ignore[arg-type]
    segundo = package_show(fetcher, "cod-ab-col")  # type: ignore[arg-type]

    assert primero == segundo
    assert fetcher.json_pedidos == [HDX_PACKAGE_SHOW.format(dataset="cod-ab-col")]


def test_la_licencia_se_comprueba_tambien_con_el_fichero_ya_en_disco(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """La ruta con cache es la normal, y era la que no comprobaba nada.

    Se simula el caso real que la comprobacion existe para atrapar: el
    publicador cambio la licencia de CC BY-IGO a CC BY-SA, que es copyleft e
    incompatible con la ODbL de Overture. Con el fichero ya en disco, antes esto
    pasaba en verde y el archivo entraba al activo.
    """
    source = _manifest_hdx().sources[0]
    (tmp_path / f"{source.id}.shp").write_bytes(b"ya estaba")

    cambiado = {
        "success": True,
        "result": {"license_id": "cc-by-sa", "resources": PAQUETE["result"]["resources"]},
    }
    fetcher = _Fetcher(cambiado)

    with pytest.raises(download.LicenseViolationError, match="cambio la licencia"):
        download.download_hdx(source, tmp_path, fetcher=fetcher)  # type: ignore[arg-type]


def test_con_la_licencia_correcta_el_atajo_por_cache_sigue_funcionando(
    tmp_path: Path,
) -> None:
    """Y no se rompe la reanudacion, que es para lo que existe el atajo.

    Sin el, cada reintento de un build repetia unos 200 MB aunque el fallo
    hubiera ocurrido mucho despues, en el computo.
    """
    source = _manifest_hdx().sources[0]
    ya = tmp_path / f"{source.id}.shp"
    ya.write_bytes(b"ya estaba")

    fetcher = _Fetcher()
    rutas = download.download_hdx(source, tmp_path, fetcher=fetcher)  # type: ignore[arg-type]

    assert rutas == [ya]
    # Se pregunto la licencia, y nada mas: no se resolvieron urls de descarga.
    assert fetcher.json_pedidos == [HDX_PACKAGE_SHOW.format(dataset="cod-ab-col")]
