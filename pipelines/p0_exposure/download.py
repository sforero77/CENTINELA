"""Descarga de las capas de un pais, guiada por el manifest.

Cada fuente tiene su propia forma de acotar lo que hay que traer, y el
conocimiento de *como* acotarla vive en ``sources/``. Este modulo solo
orquesta: lee el manifest, pide a cada resolutor la lista exacta de archivos, y
los deja en disco con su hash.

Los numeros que justifican todo esto, medidos sobre Colombia:

===================  ==============  ==========================
Fuente               Global          Colombia
===================  ==============  ==========================
GHS-POP              5,25 GB         93 MB (9 de 375 teselas)
Overture buildings   277 GB          0 (se lee en remoto)
MGN del DANE         3,39 GB         100 MB (5 entradas del ZIP)
WorldPop age-sex     --              600 MB (10 de 62 rasters)
===================  ==============  ==========================

WorldPop es la unica que no se puede acotar: sus rasters ya vienen recortados al
pais y hacen falta enteros, asi que domina el tiempo de un build (~600 MB de los
~800 totales). Por eso todas las rutas de descarga saltan lo ya bajado y
escriben via :func:`write_atomic`: reanudar tiene que ser barato y seguro.
"""

from __future__ import annotations

import hashlib
import zipfile
from dataclasses import dataclass
from pathlib import Path

from ..common.geo import BBox
from ..common.hdx import resolve_attempts
from ..common.http import HttpFetcher
from ..common.logging import get_logger
from ..common.manifest import Manifest, Source
from .sources import ghsl, worldpop
from .sources.zip_range import extract_entry, find_entries, list_entries

_log = get_logger(__name__)

#: Cajas envolventes por pais. Se declaran a mano en vez de derivarlas del
#: limite administrativo porque hacen falta *antes* de descargarlo.
#:
#: La de Venezuela esta **medida** sobre ``ven_admin2.shp`` del COD-AB
#: (-73,3691..-59,7411 / 0,6346..12,4988) y redondeada hacia afuera. El extremo
#: norte lo pone Dependencias Federales, no la peninsula de Paraguaná: el
#: COD-AB no incluye la Isla de Aves, asi que la caja tampoco — estirarla hasta
#: 15,7°N arrastraria teselas de GHS-POP y ficheros de Overture enteros por una
#: isla con una estacion naval y nadie mas.
#: Las diecisiete restantes salen de ``division_area`` de Overture
#: (``subtype='country'``, release 2026-08-19.0), redondeadas hacia afuera. Se
#: midieron todas con un solo criterio en vez de recopilarlas pais por pais.
#:
#: **Varias son mucho mas anchas que el continente** por territorio insular, y
#: eso cuesta teselas de GHS-POP en cada build: Chile llega a 109,7°W por Rapa
#: Nui, Mexico a 118,6°W por Guadalupe y Revillagigedo, Ecuador a 92,3°W por
#: Galapagos, Brasil a 28,6°W por San Pedro y San Pablo. Se dejan completas: el
#: sistema no puede decidir que una isla habitada no cuenta.
COUNTRY_BBOX: dict[str, BBox] = {
    "COL": BBox(lon_min=-82.0, lat_min=-4.3, lon_max=-66.8, lat_max=13.5),
    "VEN": BBox(lon_min=-73.4, lat_min=0.6, lon_max=-59.7, lat_max=12.6),
    "ARG": BBox(lon_min=-73.61, lat_min=-55.24, lon_max=-53.59, lat_max=-21.73),
    "BOL": BBox(lon_min=-69.7, lat_min=-22.95, lon_max=-57.4, lat_max=-9.62),
    "BRA": BBox(lon_min=-74.03, lat_min=-33.92, lon_max=-28.58, lat_max=5.32),
    "CHL": BBox(lon_min=-109.73, lat_min=-56.78, lon_max=-66.03, lat_max=-17.45),
    "CRI": BBox(lon_min=-87.15, lat_min=5.45, lon_max=-82.38, lat_max=11.27),
    "CUB": BBox(lon_min=-85.22, lat_min=19.58, lon_max=-73.87, lat_max=23.53),
    "DOM": BBox(lon_min=-72.12, lat_min=17.22, lon_max=-68.06, lat_max=21.34),
    "ECU": BBox(lon_min=-92.26, lat_min=-5.07, lon_max=-75.14, lat_max=1.93),
    "GTM": BBox(lon_min=-92.41, lat_min=13.51, lon_max=-88.16, lat_max=17.87),
    "HND": BBox(lon_min=-89.41, lat_min=12.93, lon_max=-82.13, lat_max=17.67),
    "MEX": BBox(lon_min=-118.65, lat_min=14.33, lon_max=-86.44, lat_max=32.77),
    "NIC": BBox(lon_min=-87.95, lat_min=10.66, lon_max=-82.43, lat_max=15.14),
    "PAN": BBox(lon_min=-83.1, lat_min=6.95, lon_max=-77.11, lat_max=9.9),
    "PER": BBox(lon_min=-84.69, lat_min=-20.25, lon_max=-68.6, lat_max=0.01),
    "PRY": BBox(lon_min=-62.69, lat_min=-27.66, lon_max=-54.21, lat_max=-19.24),
    "SLV": BBox(lon_min=-90.27, lat_min=12.9, lon_max=-87.55, lat_max=14.5),
    "URY": BBox(lon_min=-58.54, lat_min=-35.83, lon_max=-53.03, lat_max=-30.04),
}


def countries_for_point(lon: float, lat: float) -> list[str]:
    """Paises cuya caja envolvente contiene el punto, del mas ajustado al menos.

    Las cajas se solapan —la de Colombia y la de Venezuela comparten miles de
    km²— asi que un epicentro puede caer en varias. Devolverlas todas, ordenadas
    por area, es lo honesto: quien elige el activo prueba en ese orden y el join
    contra las celdas H3 desempata de verdad.

    Una lista vacia significa que el sismo esta dentro de la ventana LATAM pero
    fuera de todos los paises con caja declarada — mar abierto, o un pais que el
    sistema todavia no cubre.
    """

    def area(iso3: str) -> float:
        caja = COUNTRY_BBOX[iso3]
        return (caja.lon_max - caja.lon_min) * (caja.lat_max - caja.lat_min)

    dentro = [iso3 for iso3, caja in COUNTRY_BBOX.items() if caja.contains(lon, lat)]
    return sorted(dentro, key=area)


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


#: Sufijo del archivo a medio bajar.
PARTIAL_SUFFIX = ".parcial"


def write_atomic(path: Path, contenido: bytes) -> Path:
    """Escribe en un temporal y renombra al final.

    La reconstruccion de un pais baja del orden de 700 MB, y todas las rutas de
    descarga saltan lo que ya esta en disco. Escribiendo directo sobre el
    destino, un corte de red —o un Ctrl+C— deja un archivo truncado que la
    siguiente corrida da por bueno: un raster de poblacion a medias no falla al
    abrirse, simplemente le faltan filas al sur del pais. El rename solo ocurre
    cuando el contenido esta entero.
    """
    parcial = path.with_name(path.name + PARTIAL_SUFFIX)
    parcial.write_bytes(contenido)
    parcial.replace(path)
    return path


def download_ghsl(
    destino: Path, bbox: BBox, *, fetcher: HttpFetcher, slug: str = ghsl.POP.slug
) -> list[Path]:
    """Descarga y descomprime las teselas de un producto GHSL sobre la caja.

    ``slug`` elige el producto: ``POP`` (poblacion) o ``BUILT_S`` (superficie
    construida). Comparten retícula, asi que el mismo calculo de teselas sirve
    para los dos.

    Las teselas que solo cubren oceano no existen en el servidor: un 404 aqui
    no es un fallo, es la respuesta correcta.
    """
    destino.mkdir(parents=True, exist_ok=True)
    rutas: list[Path] = []
    for tesela in ghsl.tiles_for_bbox(bbox, slug=slug):
        tif = destino / f"{tesela.name}.tif"
        if tif.exists():
            rutas.append(tif)
            continue
        zip_path = destino / f"{tesela.name}.zip"
        try:
            write_atomic(zip_path, fetcher.get_bytes(tesela.url))
        except RuntimeError:
            _log.info(
                "tesela ausente, probablemente solo oceano",
                extra={"context": {"tesela": tesela.name}},
            )
            continue
        with zipfile.ZipFile(zip_path) as z:
            for nombre in z.namelist():
                if nombre.endswith(".tif"):
                    write_atomic(tif, z.read(nombre))
                    rutas.append(tif)
        zip_path.unlink()
    _log.info(
        "producto GHSL descargado",
        extra={
            "context": {
                "producto": slug,
                "titulo": ghsl.PRODUCTS[slug].titulo,
                "teselas": len(rutas),
                "bytes": sum(p.stat().st_size for p in rutas),
            }
        },
    )
    return rutas


def _producto_ghsl(url: str) -> str | None:
    """Producto GHSL al que apunta una URL, o ``None`` si no es del GHSL.

    Se prueba del slug mas largo al mas corto: ``GHS_BUILT_S`` contiene
    ``GHS_BUILT``, y varios productos del GHSL comparten prefijo.
    """
    for slug in sorted(ghsl.PRODUCTS, key=len, reverse=True):
        if f"GHS_{slug}" in url:
            return slug
    return None


#: Capa cuyo manifest apunta a un directorio de release, no a un fichero.
WORLDPOP_AGESEX_LAYER = "pop_worldpop_agesex"


def download_worldpop_agesex(
    url_directorio: str, destino: Path, *, fetcher: HttpFetcher
) -> list[Path]:
    """Descarga los rasters de edad que alimentan ``pop_0_14`` y ``pop_65p``.

    Solo la serie combinada por edad. El directorio tambien publica la serie por
    sexo y los totales, y bajarlo entero contaria cada persona dos veces ademas
    de triplicar la descarga (ver :mod:`pipelines.p0_exposure.sources.worldpop`).

    Raises:
        FileNotFoundError: si el listado no ofrece alguna de las bandas
            declaradas. Un hueco silencioso aqui publica menos adultos mayores
            de los que hay, con una cifra que sigue pareciendo plausible.
    """
    destino.mkdir(parents=True, exist_ok=True)
    nombres = worldpop.parse_listing(fetcher.get_bytes(url_directorio).decode("utf-8", "replace"))
    if not nombres:
        raise FileNotFoundError(f"El indice de WorldPop no lista ningun .tif: {url_directorio}")

    faltantes = worldpop.missing_bands(worldpop.select_age_rasters(nombres), nombres)
    if faltantes:
        raise FileNotFoundError(
            f"WorldPop no publica las bandas {faltantes} en {url_directorio}. "
            f"El desglose etario saldria incompleto sin que ninguna cifra lo delate."
        )

    rutas: list[Path] = []
    for columna, ficheros in sorted(worldpop.select_age_rasters(nombres).items()):
        for nombre in ficheros:
            path = destino / nombre
            if not path.exists():
                write_atomic(path, fetcher.get_bytes(worldpop.raster_url(url_directorio, nombre)))
            rutas.append(path)
        _log.info(
            "banda etaria descargada",
            extra={"context": {"columna": columna, "rasters": len(ficheros)}},
        )
    return rutas


#: Extension por formato de HDX. Importa: GDAL elige el driver por extension, y
#: un GeoPackage llamado ``.geopackage`` no siempre se abre.
HDX_SUFFIX: dict[str, str] = {
    "geopackage": ".gpkg",
    "geojson": ".geojson",
    "shp": ".shp",
    "csv": ".csv",
    "xlsx": ".xlsx",
}

#: Extensiones que ``ST_Read`` sabe abrir directamente.
#:
#: ``.json`` a secas queda **fuera** a proposito: los extractos de HOTOSM traen
#: un ``metadata.json`` junto al GeoPackage, y aceptarlo hace que el agregador
#: intente abrir como capa un archivo que no lo es. Un GeoJSON de verdad se
#: llama ``.geojson`` en todas las fuentes del manifest, verificado.
GEOMETRY_SUFFIXES: tuple[str, ...] = (".shp", ".gpkg", ".geojson")

#: Firma de un ZIP. HDX publica el formato logico ("SHP", "GeoJSON") aunque el
#: recurso venga comprimido —``ven_admin_boundaries.shp.zip``—, asi que el
#: formato declarado no basta para saber que hay dentro del archivo.
_ZIP_MAGIC = b"PK\x03\x04"


def _hdx_en_disco(source: Source, destino: Path) -> list[Path]:
    """Lo que una descarga previa de este recurso dejo, si dejo algo.

    Dos formas segun como venga el recurso: un ZIP se extrae a un directorio con
    el id de la fuente, y un archivo suelto se guarda como ``<id>.<ext>``.
    """
    carpeta = destino / source.id
    if carpeta.is_dir():
        capas = sorted(
            p for p in carpeta.rglob("*") if p.suffix.lower() in GEOMETRY_SUFFIXES and p.is_file()
        )
        if capas:
            return capas
    sueltos = sorted(
        p
        for p in destino.glob(f"{source.id}.*")
        if p.is_file() and not p.name.endswith(PARTIAL_SUFFIX)
    )
    return sueltos


def download_hdx(source: Source, destino: Path, *, fetcher: HttpFetcher) -> list[Path]:
    """Descarga un recurso de HDX resolviendo su URL por la API.

    Nunca por patron de ruta: la de un mismo dataset de HOTOSM cambia de forma
    segun el pais (ver :mod:`pipelines.common.hdx`).

    Reanudable como el resto de descargas: si el resultado ya esta en disco no
    se vuelve a pedir. Sin esto, cada reintento de un build repetia unos 200 MB
    —el COD-AB de Colombia solo son 117— aunque el fallo hubiera ocurrido mucho
    despues, en el computo.

    Returns:
        Los archivos utilizables. Normalmente uno; varios cuando el recurso es
        un ZIP, como el COD-AB de Venezuela, que trae los cuatro niveles
        administrativos mas lineas y puntos en un solo descargable.
    """
    if ya_estan := _hdx_en_disco(source, destino):
        _log.info(
            "recurso de HDX ya en disco, no se vuelve a pedir",
            extra={"context": {"dataset": source.hdx_dataset, "archivos": len(ya_estan)}},
        )
        return ya_estan

    destino.mkdir(parents=True, exist_ok=True)
    intentos = resolve_attempts(fetcher, source.hdx_dataset, resource=source.hdx_resource)

    fallos: list[str] = []
    for formato, urls in intentos:
        try:
            contenidos = [(url, fetcher.get_bytes(url)) for url in urls]
        except RuntimeError as exc:
            # Un recurso muerto no invalida el dataset: HDX cataloga exports de
            # `export.hotosm.org` que caducan, mientras los mismos datos siguen
            # vivos en S3 partidos por tipo de geometria. Se prueba el siguiente.
            fallos.append(str(exc).split(" tras ")[0])
            continue

        rutas: list[Path] = []
        for i, (_url, contenido) in enumerate(contenidos):
            if contenido[:4] == _ZIP_MAGIC:
                sufijo = f"{source.id}" if len(contenidos) == 1 else f"{source.id}_{i}"
                rutas.extend(_extraer_zip(contenido, destino / sufijo))
            else:
                ext = HDX_SUFFIX.get(formato.lower(), "." + formato.lower())
                nombre = f"{source.id}{ext}" if len(contenidos) == 1 else f"{source.id}_{i}{ext}"
                rutas.append(write_atomic(destino / nombre, contenido))

        _log.info(
            "recurso de HDX descargado",
            extra={
                "context": {
                    "dataset": source.hdx_dataset,
                    "formato": formato,
                    "partes": len(urls),
                    "archivos": len(rutas),
                    "descartados": fallos,
                }
            },
        )
        return rutas

    raise RuntimeError(
        f"Ningun recurso de {source.hdx_dataset!r} se pudo descargar. "
        f"Se probaron {len(intentos)} formas y todas fallaron: {fallos}"
    )


def _extraer_zip(contenido: bytes, destino: Path) -> list[Path]:
    """Descomprime en ``destino`` y devuelve las capas que ``ST_Read`` abre.

    Se extrae todo, no solo los ``.shp``: un shapefile sin su ``.dbf`` no tiene
    atributos y sin su ``.prj`` no tiene CRS, y GDAL los busca al lado.
    """
    import io

    destino.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(contenido)) as z:
        z.extractall(destino)
    return sorted(
        p for p in destino.rglob("*") if p.suffix.lower() in GEOMETRY_SUFFIXES and p.is_file()
    )


def download_zip_completo(url: str, destino: Path, *, fetcher: HttpFetcher) -> list[Path]:
    """Baja un ZIP entero y devuelve las capas que ``ST_Read`` sabe abrir.

    Para archivos pequenos es mejor que :func:`download_zip_entries`: una
    peticion en vez de muchas, y sin depender de que el servidor sirva rangos.

    Existe por una caida real. El geoportal del DANE dejo de servir rangos por
    encima de ~1,5 GB —responde 206 y cierra sin enviar nada—, y el nivel
    municipal se extraia por rango del archivo nacional de 3,39 GB, cuyo
    directorio central esta al final. El mismo shapefile se publica suelto en
    68 MB, asi que ya no hace falta ni el rango ni los 3,39 GB.
    """
    carpeta = destino / "zip"
    if carpeta.is_dir():
        ya_estan = sorted(
            p for p in carpeta.rglob("*") if p.suffix.lower() in GEOMETRY_SUFFIXES and p.is_file()
        )
        if ya_estan:
            return ya_estan
    rutas = _extraer_zip(fetcher.get_bytes(url), carpeta)
    _log.info(
        "ZIP descargado y extraido",
        extra={"context": {"url": url, "capas": [p.name for p in rutas]}},
    )
    return rutas


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
            write_atomic(path, extract_entry(fetcher, url, entrada))
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
            for path in download_hdx(source, carpeta, fetcher=cliente):
                inventario.append(_registrar(source, path))
        elif source.url.startswith("s3://"):
            # Overture no se descarga: DuckDB lo lee remoto con poda por bbox.
            _log.info(
                "fuente leida en remoto, sin descarga",
                extra={"context": {"source": source.id, "url": source.url}},
            )
        elif source.layer == WORLDPOP_AGESEX_LAYER:
            for tif in download_worldpop_agesex(source.url, carpeta, fetcher=cliente):
                inventario.append(_registrar(source, tif))
        elif (slug := _producto_ghsl(source.url)) is not None:
            for tif in download_ghsl(carpeta, bbox, fetcher=cliente, slug=slug):
                inventario.append(_registrar(source, tif))
        elif source.url.endswith(".zip"):
            for capa in download_zip_completo(source.url, carpeta / source.id, fetcher=cliente):
                inventario.append(_registrar(source, capa))
        elif source.url.endswith((".tif", ".csv")):
            carpeta.mkdir(parents=True, exist_ok=True)
            path = carpeta / Path(source.url).name
            # Como el resto de rutas: lo que ya esta no se vuelve a pedir. Aqui
            # son 60 MB de WorldPop y 12,7 de OurAirports en cada reintento.
            if not path.exists():
                write_atomic(path, cliente.get_bytes(source.url))
            inventario.append(_registrar(source, path))
        else:
            _log.warning(
                "fuente sin estrategia de descarga automatica",
                extra={"context": {"source": source.id, "url": source.url}},
            )
    return inventario
