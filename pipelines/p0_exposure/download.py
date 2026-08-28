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
MGN del DANE         3,39 GB         68 MB (el municipal suelto)
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
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from ..common.geo import BBox
from ..common.hdx import dataset_license, map_license, resolve_attempts
from ..common.http import PARTIAL_SUFFIX, HttpFetcher, RecursoAusenteError
from ..common.licensing import LicenseViolationError
from ..common.logging import get_logger
from ..common.manifest import Manifest, Source
from .sources import ghsl, worldpop

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


#: ISO 3166-1 alfa-2 de cada pais cubierto. Overture etiqueta sus divisiones con
#: el codigo de dos letras; el resto del sistema usa el de tres.
ISO3_A_ISO2: dict[str, str] = {
    "ARG": "AR",
    "BOL": "BO",
    "BRA": "BR",
    "CHL": "CL",
    "COL": "CO",
    "CRI": "CR",
    "CUB": "CU",
    "DOM": "DO",
    "ECU": "EC",
    "GTM": "GT",
    "HND": "HN",
    "MEX": "MX",
    "NIC": "NI",
    "PAN": "PA",
    "PER": "PE",
    "PRY": "PY",
    "SLV": "SV",
    "URY": "UY",
    "VEN": "VE",
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


def write_atomic(path: Path, contenido: bytes) -> Path:
    """Escribe en un temporal y renombra al final.

    La reconstruccion de un pais baja del orden de 700 MB, y todas las rutas de
    descarga saltan lo que ya esta en disco. Escribiendo directo sobre el
    destino, un corte de red —o un Ctrl+C— deja un archivo truncado que la
    siguiente corrida da por bueno: un raster de poblacion a medias no falla al
    abrirse, simplemente le faltan filas al sur del pais. El rename solo ocurre
    cuando el contenido esta entero.

    Para lo que ya esta en memoria. Un fichero que llega de la red se baja con
    `HttpFetcher.download_to`, que da la misma garantia sin pasar por RAM.
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

    UN FALLO DE DESCARGA NO ES ESO, y confundirlos costo tres horas el
    27-ago-2026. Esta funcion capturaba `RuntimeError`, que era lo mismo para un
    404 que para un timeout; con el JRC caido, las 24 teselas de Peru se
    contaron como oceano y el pais se ensamblo con poblacion 0. Solo
    `RecursoAusenteError` significa "no esta"; lo demas sube.
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
            fetcher.download_to(tesela.url, zip_path)
        except RecursoAusenteError:
            _log.info(
                "tesela ausente en el servidor: solo oceano",
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
LANDCOVER_LAYER = "landcover"
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
                # Por streaming y reanudable: los rasters de un pais grande
                # pasan de 450 MB cada uno, y son veinte.
                fetcher.download_to(worldpop.raster_url(url_directorio, nombre), path)
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


def verificar_licencia_declarada(source: Source, *, fetcher: HttpFetcher) -> None:
    """Contrasta la licencia que publica HDX con la que fija el manifest.

    La docstring de `dataset_license` decia desde el principio que esto «se
    consulta en cada build y se contrasta con lo que dice el manifest: si el
    publicador cambia la licencia, queremos enterarnos por un fallo del lint y
    no por un reclamo». **No se consultaba nunca**: ni `dataset_license` ni
    `map_license` tenian un solo llamador en produccion.

    Es el peor sitio donde tener ese hueco. La contaminacion entre cubos es el
    riesgo que la espec clasifica de impacto alto (§7), el manifest fija la
    licencia una vez y a mano, y un publicador que la cambie —de CC BY a
    CC BY-NC, por ejemplo— dejaria el activo con una fuente que el reporte no
    puede consumir, con todo pasando en verde.

    **Falla el build, no avisa.** Descargar sabiendo que la licencia no es la
    declarada es justo lo que no se puede hacer: el archivo entra al activo y
    el activo se publica como Release.

    Raises:
        LicenseViolationError: si HDX declara una licencia distinta de la del
            manifest, o una que el registro interno no sabe traducir.
    """
    declarada = dataset_license(fetcher, source.hdx_dataset)
    if not declarada:
        # HDX deja el campo vacio en algunos datasets. No es una licencia
        # distinta: es ausencia de dato, y el manifest sigue mandando.
        _log.warning(
            "HDX no declara licencia para el dataset; se conserva la del manifest",
            extra={"context": {"source": source.id, "manifest": source.license}},
        )
        return

    traducida = map_license(declarada)  # lanza ante una licencia sin traduccion
    if traducida != source.license:
        raise LicenseViolationError(
            f"[{source.id}] HDX publica {source.hdx_dataset!r} bajo {traducida} "
            f"({declarada!r}) y el manifest fija {source.license}. El publicador "
            f"cambio la licencia, o el manifest esta mal. Revisalo a mano antes "
            f"de que este archivo entre al activo: la regla de los tres cubos "
            f"depende de que esta cifra sea cierta (§2.4)."
        )


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
    verificar_licencia_declarada(source, fetcher=fetcher)
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

    Una peticion en vez de muchas, y sin depender de que el servidor sirva
    rangos. Es la unica ruta para ZIP desde que se retiro la extraccion
    selectiva por rangos.

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


class InsumoCambiadoError(RuntimeError):
    """Un insumo fijado en el manifest ya no es el que se fijo.

    Es un fallo de reproducibilidad, no de red: la descarga fue bien y lo que
    llego no es lo que el manifest declara. Se lanza en cuanto los ficheros de
    esa fuente estan en disco, antes de agregar una sola celda H3.
    """


class InsumoAusenteError(RuntimeError):
    """Una fuente que si descarga volvio sin un solo fichero.

    Distinta de :class:`InsumoCambiadoError` a proposito: alli el insumo llego y
    era otro, aqui no llego nada. La primera es un problema de reproducibilidad
    y la segunda es la puerta de entrada del cero silencioso —la capa se crea
    vacia, el LEFT JOIN la vuelve ceros y el activo se publica sin que nada
    falle—, asi que quien lea el log tiene que poder distinguirlas sin leer el
    mensaje entero.
    """


def digest_de_insumos(descargados: Iterable[Descargado]) -> str:
    """sha256 sobre la lista canonica ``nombre  sha256`` de una fuente.

    UNA FUENTE DEL MANIFEST NO ES UN FICHERO, y por eso el campo escalar
    ``sha256`` llevaba vacio desde el primer dia en las 194 fuentes de los
    diecinueve manifests: no habia un fichero al que pertenecer. GHS-POP son
    nueve u once teselas, el desglose etario de WorldPop veinte rasters, un
    COD-AB el shapefile con su ``.dbf`` y su ``.prj``, y Overture no baja
    ninguno.

    El digest si existe para los tres casos porque no habla de un fichero sino
    del conjunto: una linea por fichero, ordenadas por nombre, hash de todo.
    Anadir una tesela, perder un ``.prj`` o que cambie un solo byte dan digests
    distintos.

    El nombre se hashea junto al contenido a proposito. Dos teselas GHSL que
    intercambian su contenido son un fallo del selector, y sin el nombre en la
    linea el digest no lo veria.
    """
    lineas = sorted(f"{d.path.name}  {d.sha256}" for d in descargados)
    return hashlib.sha256("\n".join(lineas).encode("utf-8")).hexdigest()


def _verificar_insumos(source: Source, descargados: Sequence[Descargado]) -> None:
    """Compara lo que llego contra lo que el manifest fijo. Falla si difiere.

    Esta es la puerta que le faltaba al sistema. El caso real: un dataset de
    HDX republicado —misma URL estable, mismo nombre, geometria distinta— dejo
    a un pais entero fuera durante horas, y el fallo aparecio al final de la
    cadena disfrazado de error de geometria. Con el digest fijado aparece aqui,
    a los minutos de empezar, diciendo exactamente que fuente se movio.
    """
    if not descargados:
        if source.se_lee_en_remoto:
            # Overture y la cobertura del suelo no pasan por disco: DuckDB y
            # los rangos HTTP los leen remotos. No hay bytes que hashear, y
            # fingir un digest seria peor que no tener ninguno. Lo que fija
            # esas fuentes es el release del vintage, que el lint ya obliga a
            # ser explicito.
            return

        # VACIO NO ES LO MISMO QUE REMOTO, y suponerlo era el agujero de la
        # primera version de esta funcion. Una fuente que SI descarga y vuelve
        # con cero ficheros es el cero silencioso: `ensure_layer_tables` crea
        # la tabla vacia, el LEFT JOIN la convierte en ceros y el activo se
        # escribe sin que nada falle.
        #
        # Medido el 27-ago-2026 con Peru: el JRC estuvo caido tres horas, las
        # teselas GHSL se contaron como "probablemente solo oceano" y el pais
        # se ensamblo con poblacion 0. Lo detuvo el assert de §6.4, pero al
        # final —despues de agregar 24 millones de edificaciones y 549 millones
        # de pixeles de cobertura—. Aqui se detiene al terminar esa descarga.
        raise InsumoAusenteError(
            f"[{source.id}] la fuente no aporto ningun fichero.\n"
            f"  capa    : {source.layer}\n"
            f"  url     : {source.url}\n"
            f"  No se lee en remoto, asi que cero ficheros no es una respuesta valida:\n"
            f"  o el servidor de origen esta caido, o cambio la ruta, o el selector\n"
            f"  dejo de encajar. Construir igual daria esa capa a cero en todo el\n"
            f"  pais, en silencio y con toda la pinta de una cifra correcta."
        )

    medido = digest_de_insumos(descargados)
    if not source.insumos_sha256:
        _log.warning(
            "insumo sin digest fijado; volcalo al manifest con `centinela fijar-insumos`",
            extra={
                "context": {
                    "source": source.id,
                    "insumos_sha256": medido,
                    "ficheros": len(descargados),
                }
            },
        )
        return

    if medido != source.insumos_sha256:
        detalle = "\n    ".join(
            f"{d.path.name}  {d.sha256}" for d in sorted(descargados, key=lambda x: x.path.name)
        )
        raise InsumoCambiadoError(
            f"[{source.id}] el insumo cambio desde que se fijo el manifest.\n"
            f"  fijado : {source.insumos_sha256}\n"
            f"  medido : {medido}\n"
            f"  vintage declarado: {source.vintage}\n"
            f"  lo que hay ahora ({len(descargados)} ficheros):\n    {detalle}\n"
            f"  El tercero republico la fuente. Compara con el bloque `insumos` de la\n"
            f"  medicion.json del Release anterior antes de decidir: si el cambio es\n"
            f"  legitimo, fija el digest medido; si no, el activo publicado sigue\n"
            f"  siendo el bueno y este build no debe reemplazarlo."
        )


def _descargar_fuente(
    source: Source,
    destino: Path,
    *,
    bbox: BBox,
    fetcher: HttpFetcher,
) -> list[Descargado]:
    """Trae a disco los ficheros de una sola fuente, sea cual sea su forma.

    Estaba en linea dentro de ``download_manifest``. Sale aparte para que exista
    el momento en que los ficheros de UNA fuente estan completos y todavia no se
    han mezclado con los de las demas: ese es el momento de verificar el digest.
    """
    carpeta = destino / source.layer

    if source.hdx_dataset:
        return [_registrar(source, path) for path in download_hdx(source, carpeta, fetcher=fetcher)]

    if source.se_lee_en_remoto:
        # Overture (DuckDB con poda por bbox) y la cobertura del suelo (rangos
        # HTTP sobre las overviews del COG). El criterio vive en `Source` y no
        # aqui a proposito: el lint necesita el mismo, y dos copias del mismo
        # criterio es como el lint acaba avisando de lo que nadie puede
        # resolver.
        _log.info(
            "fuente leida en remoto, sin descarga",
            extra={"context": {"source": source.id, "url": source.url}},
        )
        return []

    if source.layer == WORLDPOP_AGESEX_LAYER:
        return [
            _registrar(source, tif)
            for tif in download_worldpop_agesex(source.url, carpeta, fetcher=fetcher)
        ]

    if (slug := _producto_ghsl(source.url)) is not None:
        return [
            _registrar(source, tif)
            for tif in download_ghsl(carpeta, bbox, fetcher=fetcher, slug=slug)
        ]

    if source.url.endswith(".zip"):
        return [
            _registrar(source, capa)
            for capa in download_zip_completo(source.url, carpeta / source.id, fetcher=fetcher)
        ]

    if source.url.endswith((".tif", ".csv")):
        carpeta.mkdir(parents=True, exist_ok=True)
        path = carpeta / Path(source.url).name
        # Como el resto de rutas: lo que ya esta no se vuelve a pedir. Aqui son
        # 60 MB de WorldPop y 12,7 de OurAirports en cada reintento.
        if not path.exists():
            fetcher.download_to(source.url, path)
        return [_registrar(source, path)]

    _log.warning(
        "fuente sin estrategia de descarga automatica",
        extra={"context": {"source": source.id, "url": source.url}},
    )
    return []


class OrigenCaidoError(RuntimeError):
    """Un servidor de origen no contesta, y el build no ha empezado."""


def comprobar_origenes(manifest: Manifest, *, fetcher: HttpFetcher) -> None:
    """Pregunta a cada origen distinto si esta en pie, antes de bajar nada.

    Cuesta un HEAD por host —cuatro o cinco por pais, unos segundos— y evita la
    forma mas cara de fallar que tiene este sistema: enterarse de que un origen
    esta caido despues de horas intentandolo. El 27-ago-2026 el JRC estuvo caido
    tres, y la corrida de Peru lo descubrio en la cuarta.

    Se agrupa por host y no por fuente porque lo que se cae es el servidor: las
    dos fuentes de GHSL viven en el mismo, y preguntar dos veces solo alarga el
    chequeo. Se saltan las que se leen en remoto: su disponibilidad la comprueba
    DuckDB cuando toca, y un HEAD contra un prefijo ``s3://`` no significa nada.
    """
    representante: dict[str, str] = {}
    for source in manifest.sources:
        if source.se_lee_en_remoto:
            continue
        host = urlparse(source.url).netloc
        if host:
            representante.setdefault(host, source.url)

    caidos = sorted(host for host, url in representante.items() if not fetcher.responde(url))
    if caidos:
        raise OrigenCaidoError(
            f"Origenes que no contestan: {', '.join(caidos)}.\n"
            f"  No se ha descargado nada todavia. Construir ahora gastaria horas de\n"
            f"  runner para acabar con las capas de ese origen vacias — que es como\n"
            f"  Peru se ensamblo con poblacion 0 el 27-ago-2026.\n"
            f"  Reintenta el pais cuando el origen vuelva."
        )
    _log.info(
        "origenes en pie",
        extra={"context": {"hosts": sorted(representante), "iso3": manifest.iso3}},
    )


def download_manifest(
    manifest: Manifest,
    destino: Path,
    *,
    fetcher: HttpFetcher | None = None,
) -> list[Descargado]:
    """Descarga todo lo que el manifest declara y devuelve el inventario.

    Cada fuente se verifica contra su ``insumos_sha256`` en cuanto sus ficheros
    estan en disco, no al final: si un tercero republico algo, el build se
    detiene ahi y no despues de dos horas de agregacion.

    Y antes de la primera descarga se pregunta a cada origen si esta vivo, que
    son unos segundos y ahorra las horas de descubrirlo bajando.
    """
    cliente = fetcher or HttpFetcher(timeout_s=300.0)
    bbox = COUNTRY_BBOX.get(manifest.iso3)
    if bbox is None:
        raise KeyError(
            f"Sin caja envolvente declarada para {manifest.iso3}. "
            f"Agregala a COUNTRY_BBOX antes de construir el pais."
        )

    comprobar_origenes(manifest, fetcher=cliente)

    inventario: list[Descargado] = []
    for source in manifest.sources:
        de_la_fuente = _descargar_fuente(source, destino, bbox=bbox, fetcher=cliente)
        _verificar_insumos(source, de_la_fuente)
        inventario.extend(de_la_fuente)
    return inventario


def resumen_de_insumos(manifest: Manifest, inventario: Sequence[Descargado]) -> dict[str, Any]:
    """Lo que entro al build, fuente por fuente, para publicar junto al activo.

    Los sha256 se calculaban en cada corrida y se tiraban: del inventario solo
    sobrevivian al log un conteo de ficheros y un total de bytes. Este es el
    bloque que los conserva, y viaja en ``medicion.json`` —que ya se publica en
    el Release al lado del parquet— por reparto de tamanos: el manifest se queda
    con el digest, que es una linea por fuente, y el detalle por fichero queda a
    un clic sin volver a construir ni descargar nada.

    Sin este bloque, un digest que no cuadra solo puede decir *que* la fuente
    cambio. Con el, se puede decir *que fichero*.
    """
    por_fuente: dict[str, list[Descargado]] = {}
    for item in inventario:
        por_fuente.setdefault(item.source_id, []).append(item)

    resumen: dict[str, Any] = {}
    for source in manifest.sources:
        de_la_fuente = por_fuente.get(source.id, [])
        if not de_la_fuente:
            # Se declara igual: que no toque el disco no lo saca del activo.
            resumen[source.id] = {"remoto": True, "vintage": source.vintage}
            continue
        resumen[source.id] = {
            "insumos_sha256": digest_de_insumos(de_la_fuente),
            "vintage": source.vintage,
            "bytes": sum(d.bytes for d in de_la_fuente),
            "ficheros": {
                d.path.name: d.sha256 for d in sorted(de_la_fuente, key=lambda x: x.path.name)
            },
        }
    return resumen
