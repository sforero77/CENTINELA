"""GHSL: seleccion de teselas por pais.

Sirve a los dos productos del GHSL que usa el activo, porque **comparten
retícula**: ``GHS_POP`` (poblacion) y ``GHS_BUILT_S`` (superficie construida).
Las teselas de uno y otro se llaman igual salvo por el nombre del producto,
cubren la misma extension y se seleccionan con el mismo calculo — verificado
pidiendo la misma R9_C11 de ambos.

El raster global de 100 m de GHS-POP pesa **5,25 GB** comprimido. El JRC tambien publica
el mismo producto en **375 teselas**, y Colombia necesita nueve, que suman
93 MB. La diferencia entre bajar 5,25 GB o 93 MB en cada rebuild trimestral es
lo que hace que ``make country ISO=COL`` sea algo que alguien vaya a correr de
verdad (O4).

Esquema de teselado, derivado y **verificado** contra la georreferenciacion real
de la tesela R9_C11:

* Proyeccion Mollweide (``ESRI:54009``).
* Origen de la retícula en ``x = -18.041.000``, ``y = 9.000.000``.
* Teselas de 1.000.000 m de lado, 10.000 x 10.000 px a 100 m.
* Nomenclatura ``R{fila}_C{columna}``, con la fila 1 arriba y la columna 1 a la
  izquierda.

Las teselas que solo cubren oceano no existen: de las 648 posiciones posibles
(18 x 36) hay 375 publicadas. Por eso la seleccion se comprueba contra el
servidor antes de descargar.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from ...common.geo import BBox

#: Release global vigente. Verificado: R2023A sigue siendo el ultimo para el
#: globo — el R2025A que aparece en el FTP del JRC es solo del Artico.
RELEASE: Final[str] = "R2023A"
#: Epoca usada por el sistema. El producto publica 1975-2030 cada 5 anos.
EPOCH: Final[int] = 2025


@dataclass(frozen=True, slots=True)
class Product:
    """Un producto del GHSL sobre la retícula comun."""

    #: Fragmento que identifica al producto en rutas y nombres de fichero.
    slug: str
    #: Que mide, para el log y los metadatos publicados.
    titulo: str
    #: Valor de nodata declarado por el producto.
    nodata: float


#: Poblacion residente por pixel. La cifra principal del sistema.
POP = Product(slug="POP", titulo="Poblacion residente", nodata=-200.0)

#: Superficie construida por pixel, en m². Derivada de Sentinel-2 y Landsat, no
#: de mapeo colaborativo: es la unica capa del activo que **no** hereda los
#: huecos de OSM en asentamientos informales y zona rural dispersa, que es
#: justo donde vive la poblacion mas expuesta. Complementa a Overture, no lo
#: sustituye: mide cuanto hay construido, no cuantas edificaciones son.
BUILT_S = Product(slug="BUILT_S", titulo="Superficie construida (m²)", nodata=-200.0)

PRODUCTS: Final[dict[str, Product]] = {p.slug: p for p in (POP, BUILT_S)}

#: Valor de nodata del raster. **Critico**: aparece como -200 en ~22 millones de
#: celdas por tesela (todo el oceano). Sumar sin enmascararlo da poblaciones
#: negativas y dispara el assert de calidad de §6.4 sobre datos sanos.
NODATA: Final[float] = -200.0

#: Origen de la retícula en Mollweide, en metros.
GRID_X0: Final[float] = -18_041_000.0
GRID_Y0: Final[float] = 9_000_000.0
#: Lado de la tesela en metros.
TILE_SIZE_M: Final[float] = 1_000_000.0

_BASE = (
    "https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/GHSL/GHS_{slug}_GLOBE_{release}"
    "/GHS_{slug}_E{epoch}_GLOBE_{release}_54009_100/V1-0"
)


@dataclass(frozen=True, slots=True)
class Tile:
    """Una tesela del mosaico de GHS-POP."""

    row: int
    col: int
    release: str = RELEASE
    epoch: int = EPOCH
    slug: str = POP.slug

    @property
    def name(self) -> str:
        return (
            f"GHS_{self.slug}_E{self.epoch}_GLOBE_{self.release}"
            f"_54009_100_V1_0_R{self.row}_C{self.col}"
        )

    @property
    def url(self) -> str:
        base = _BASE.format(slug=self.slug, release=self.release, epoch=self.epoch)
        return f"{base}/tiles/{self.name}.zip"

    @property
    def bounds_mollweide(self) -> tuple[float, float, float, float]:
        """``(xmin, ymin, xmax, ymax)`` en metros Mollweide."""
        xmin = GRID_X0 + (self.col - 1) * TILE_SIZE_M
        ymax = GRID_Y0 - (self.row - 1) * TILE_SIZE_M
        return (xmin, ymax - TILE_SIZE_M, xmin + TILE_SIZE_M, ymax)


def global_url(release: str = RELEASE, epoch: int = EPOCH, slug: str = POP.slug) -> str:
    """URL del mosaico global. 5,25 GB — preferir :func:`tiles_for_bbox`."""
    base = _BASE.format(slug=slug, release=release, epoch=epoch)
    return f"{base}/GHS_{slug}_E{epoch}_GLOBE_{release}_54009_100_V1_0.zip"


def tiles_for_mollweide_bbox(
    xmin: float,
    ymin: float,
    xmax: float,
    ymax: float,
    *,
    release: str = RELEASE,
    epoch: int = EPOCH,
    slug: str = POP.slug,
) -> list[Tile]:
    """Teselas que intersecan una caja ya proyectada a Mollweide."""
    col_min = int((xmin - GRID_X0) // TILE_SIZE_M) + 1
    col_max = int((xmax - GRID_X0) // TILE_SIZE_M) + 1
    row_min = int((GRID_Y0 - ymax) // TILE_SIZE_M) + 1
    row_max = int((GRID_Y0 - ymin) // TILE_SIZE_M) + 1
    return [
        Tile(row=r, col=c, release=release, epoch=epoch, slug=slug)
        for r in range(row_min, row_max + 1)
        for c in range(col_min, col_max + 1)
    ]


def tiles_for_bbox(
    bbox: BBox,
    *,
    release: str = RELEASE,
    epoch: int = EPOCH,
    slug: str = POP.slug,
) -> list[Tile]:
    """Teselas que cubren una caja en grados (EPSG:4326).

    Requiere el extra ``[geo]`` por la reproyeccion.
    """
    from pyproj import Transformer

    to_mw = Transformer.from_crs("EPSG:4326", "ESRI:54009", always_xy=True)
    xs: list[float] = []
    ys: list[float] = []
    # Mollweide curva los meridianos: muestrear solo las esquinas subestima la
    # extension. Se anade el ecuador, donde la proyeccion es mas ancha.
    latitudes = [bbox.lat_min, bbox.lat_max]
    if bbox.lat_min < 0.0 < bbox.lat_max:
        latitudes.append(0.0)
    for lon in (bbox.lon_min, bbox.lon_max):
        for lat in latitudes:
            x, y = to_mw.transform(lon, lat)
            xs.append(x)
            ys.append(y)
    return tiles_for_mollweide_bbox(
        min(xs), min(ys), max(xs), max(ys), release=release, epoch=epoch, slug=slug
    )
