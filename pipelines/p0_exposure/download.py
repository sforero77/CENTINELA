"""Descarga de las capas de un pais, guiada por el manifest.

Cada fuente tiene su propia forma de acotar lo que hay que traer, y el
conocimiento de *como* acotarla vive en ``sources/``. Este modulo solo
orquesta: lee el manifest, pide a cada resolutor la lista exacta de archivos, y
los deja en disco con su hash.

Los numeros que justifican todo esto, medidos sobre Colombia:

===================  ==============  =============
Fuente               Global          Colombia
===================  ==============  =============
GHS-POP              5,25 GB         93 MB (9 de 375 teselas)
Overture buildings   277 GB          11 de 512 ficheros
MGN del DANE         3,39 GB         100 MB (5 entradas del ZIP)
===================  ==============  =============
"""

from __future__ import annotations

import hashlib
import zipfile
from dataclasses import dataclass
from pathlib import Path

from ..common.geo import BBox
from ..common.hdx import resolve_resource
from ..common.http import HttpFetcher
from ..common.logging import get_logger
from ..common.manifest import Manifest, Source
from .sources import ghsl
from .sources.zip_range import extract_entry, find_entries, list_entries

_log = get_logger(__name__)

#: Cajas envolventes por pais. Se declaran a mano en vez de derivarlas del
#: limite administrativo porque hacen falta *antes* de descargarlo.
COUNTRY_BBOX: dict[str, BBox] = {
    "COL": BBox(lon_min=-82.0, lat_min=-4.3, lon_max=-66.8, lat_max=13.5),
}


@dataclass(frozen=True, slots=True)
class Descargado:
    """Un archivo ya en disco, con su procedencia."""

    source_id: str
    layer: str
    path: Path
    sha256: str
    bytes: int


def sha256_of(path: Path, *, chunk: int = 1 << 20) -> str:
    """Hash del archivo, leido por trozos para no cargarlo entero en memoria."""
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while bloque := fh.read(chunk):
            h.update(bloque)
    return h.hexdigest()


def _registrar(source: Source, path: Path) -> Descargado:
    return Descargado(
        source_id=source.id,
        layer=source.layer,
        path=path,
        sha256=sha256_of(path),
        bytes=path.stat().st_size,
    )


def download_ghsl(destino: Path, bbox: BBox, *, fetcher: HttpFetcher) -> list[Path]:
    """Descarga y descomprime las teselas de GHS-POP que cubren la caja.

    Las teselas que solo cubren oceano no existen en el servidor: un 404 aqui
    no es un fallo, es la respuesta correcta.
    """
    destino.mkdir(parents=True, exist_ok=True)
    rutas: list[Path] = []
    for tesela in ghsl.tiles_for_bbox(bbox):
        tif = destino / f"{tesela.name}.tif"
        if tif.exists():
            rutas.append(tif)
            continue
        zip_path = destino / f"{tesela.name}.zip"
        try:
            zip_path.write_bytes(fetcher.get_bytes(tesela.url))
        except RuntimeError:
            _log.info(
                "tesela ausente, probablemente solo oceano",
                extra={"context": {"tesela": tesela.name}},
            )
            continue
        with zipfile.ZipFile(zip_path) as z:
            for nombre in z.namelist():
                if nombre.endswith(".tif"):
                    tif.write_bytes(z.read(nombre))
                    rutas.append(tif)
        zip_path.unlink()
    _log.info("GHS-POP descargado", extra={"context": {"teselas": len(rutas)}})
    return rutas


def download_hdx(source: Source, destino: Path, *, fetcher: HttpFetcher) -> Path:
    """Descarga un recurso de HDX resolviendo su URL por la API.

    Nunca por patron de ruta: la de un mismo dataset de HOTOSM cambia de forma
    segun el pais (ver :mod:`pipelines.common.hdx`).
    """
    destino.mkdir(parents=True, exist_ok=True)
    formato, url = resolve_resource(fetcher, source.hdx_dataset)
    path = destino / f"{source.id}.{formato.lower()}"
    path.write_bytes(fetcher.get_bytes(url))
    _log.info(
        "recurso de HDX descargado",
        extra={"context": {"dataset": source.hdx_dataset, "formato": formato, "url": url}},
    )
    return path


def download_zip_entries(
    url: str, destino: Path, *, patron: str, fetcher: HttpFetcher
) -> list[Path]:
    """Extrae de un ZIP remoto solo las entradas cuyo nombre contiene ``patron``.

    Pensado para el MGN del DANE: 3,39 GB de los que P0 necesita 100 MB.
    """
    destino.mkdir(parents=True, exist_ok=True)
    entradas = list_entries(fetcher, url)
    quiero = [
        e
        for e in find_entries(entradas, ".shp", ".shx", ".dbf", ".prj", ".cpg")
        if patron in e.name
    ]
    if not quiero:
        raise FileNotFoundError(f"El ZIP no contiene entradas con {patron!r}: {url}")

    rutas: list[Path] = []
    for entrada in quiero:
        path = destino / Path(entrada.name).name
        if not path.exists():
            path.write_bytes(extract_entry(fetcher, url, entrada))
        rutas.append(path)
    _log.info(
        "entradas extraidas de ZIP remoto",
        extra={
            "context": {
                "url": url,
                "entradas": len(rutas),
                "bytes": sum(p.stat().st_size for p in rutas),
            }
        },
    )
    return rutas


def download_manifest(
    manifest: Manifest,
    destino: Path,
    *,
    fetcher: HttpFetcher | None = None,
) -> list[Descargado]:
    """Descarga todo lo que el manifest declara y devuelve el inventario.

    Los ``sha256`` del resultado son los que hay que volcar al manifest para
    cerrar la trazabilidad de RNF-04.
    """
    cliente = fetcher or HttpFetcher(timeout_s=300.0)
    bbox = COUNTRY_BBOX.get(manifest.iso3)
    if bbox is None:
        raise KeyError(
            f"Sin caja envolvente declarada para {manifest.iso3}. "
            f"Agregala a COUNTRY_BBOX antes de construir el pais."
        )

    inventario: list[Descargado] = []
    for source in manifest.sources:
        carpeta = destino / source.layer
        if source.hdx_dataset:
            inventario.append(_registrar(source, download_hdx(source, carpeta, fetcher=cliente)))
        elif source.url.startswith("s3://"):
            # Overture no se descarga: DuckDB lo lee remoto con poda por bbox.
            _log.info(
                "fuente leida en remoto, sin descarga",
                extra={"context": {"source": source.id, "url": source.url}},
            )
        elif "GHS_POP" in source.url:
            for tif in download_ghsl(carpeta, bbox, fetcher=cliente):
                inventario.append(_registrar(source, tif))
        elif source.url.endswith(".zip") and "geoportal.dane.gov.co" in source.url:
            for shp in download_zip_entries(
                source.url, carpeta, patron="MPIO_GRAFICO", fetcher=cliente
            ):
                inventario.append(_registrar(source, shp))
        elif source.url.endswith((".tif", ".csv")):
            carpeta.mkdir(parents=True, exist_ok=True)
            path = carpeta / Path(source.url).name
            path.write_bytes(cliente.get_bytes(source.url))
            inventario.append(_registrar(source, path))
        else:
            _log.warning(
                "fuente sin estrategia de descarga automatica",
                extra={"context": {"source": source.id, "url": source.url}},
            )
    return inventario
