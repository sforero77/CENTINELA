"""ESA WorldCover: que hay en el suelo de cada celda.

Once clases a 10 m para todo el globo, de Sentinel-1 y Sentinel-2, CC-BY-4.0.
Es la capa que convierte "hay fuego en esta celda" en "arde bosque, pastizal o
cultivo" — y de paso sirve al lado sismico, donde saber que el area afectada es
mayormente cultivo cambia como se lee la cifra de poblacion.

**No se descarga.** Se lee en remoto por rangos HTTP, como ya hace Overture. Una
tesela pesa 96 MB a 10 m y hacen falta 858 para los diecinueve paises; bajarlas
serian 82 GB y un runner de CI tiene ~14 GB libres. Pero los ficheros son COG
con overviews internas [2, 4, 8, 16, 32, 64], asi que se lee la piramide a /8
—unos 80 m— y la tesela entera cabe en 20 MB de RAM y 1,4 segundos.

Esa eleccion no es solo comodidad: **el pico de memoria deja de depender del
tamano del pais**, que es exactamente la leccion que costo tres intentos con el
build de Brasil. Colombia y Brasil cuestan lo mismo por tesela.

A /8 una celda H3 r8 (0,74 km²) recibe ~140 pixeles, de sobra para una
distribucion de clases con sentido: medido en el Choco, una celda de borde dio
51 % arbolado y 49 % pastizal, que es justo la frontera que importa.

Rejilla: teselas de 3°x3° nombradas por su esquina **suroeste**, con latitud y
longitud multiplos de tres. Verificado contra el bucket: ``N03W075`` responde
200 y ``S12W077`` responde 404, porque 77 no es multiplo de 3.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from ...common.geo import BBox

#: Version del producto. ``v200`` es la epoca 2021; ``v100`` fue la de 2020.
VERSION: Final[str] = "v200"
#: Ano del mapa. El producto no se actualiza desde 2021.
EPOCH: Final[int] = 2021

#: Lado de la tesela en grados.
TILE_DEG: Final[int] = 3

#: Cobertura latitudinal del producto. Fuera de aqui no hay tesela que pedir, y
#: preguntar cuesta un 404 y varios segundos de reintentos de GDAL.
LAT_MIN: Final[int] = -60
LAT_MAX: Final[int] = 81

#: Nivel de piramide que se lee. 10 m / 8 = 80 m, con ~140 pixeles por celda r8.
#: Subir a /4 cuadruplica el dato para afinar unos porcentajes que ya son
#: estables; bajar a /16 deja ~35 pixeles y los porcentajes empiezan a saltar.
OVERVIEW: Final[int] = 8

_BASE: Final[str] = "https://esa-worldcover.s3.eu-central-1.amazonaws.com"


@dataclass(frozen=True, slots=True)
class Clase:
    """Una clase de cobertura del suelo."""

    #: Codigo en el raster.
    codigo: int
    #: Nombre de la columna que se publica, sin el sufijo de porcentaje.
    nombre: str
    #: Que es, para leyendas y metadatos.
    titulo: str


#: Las clases que se publican. **Solo las que arden o las que importan para
#: leer un incendio**: agua, nieve, suelo desnudo y musgo se quedan fuera a
#: proposito, porque nombrar once columnas en el contrato publicado para que
#: cuatro sean siempre cero es ensanchar el parquet sin anadir informacion.
#:
#: Humedal y manglar van juntos: los dos son suelo organico, los dos arden mal y
#: largo, y separarlos daria dos columnas casi vacias en dieciocho de los
#: diecinueve paises.
CLASES: Final[tuple[Clase, ...]] = (
    Clase(10, "arbolado", "Cobertura arborea"),
    Clase(20, "arbustos", "Matorral"),
    Clase(30, "pastizal", "Pastizal"),
    Clase(40, "cultivo", "Cultivo"),
    Clase(50, "construido", "Superficie construida"),
    Clase(90, "humedal", "Humedal herbaceo y manglar"),
)

#: Codigos que se suman a cada columna publicada.
AGRUPACION: Final[dict[int, str]] = {
    10: "arbolado",
    20: "arbustos",
    30: "pastizal",
    40: "cultivo",
    50: "construido",
    90: "humedal",
    95: "humedal",  # manglar
}

#: Valor de fuera de dato. El producto usa 0 y no declara nodata en el GeoTIFF.
NODATA: Final[int] = 0


@dataclass(frozen=True, slots=True)
class Tile:
    """Una tesela de 3°x3°, identificada por su esquina suroeste."""

    #: Latitud de la esquina sur, multiplo de 3.
    lat: int
    #: Longitud de la esquina oeste, multiplo de 3.
    lon: int
    version: str = VERSION
    epoch: int = EPOCH

    @property
    def name(self) -> str:
        """``N03W075``. Latitud con dos digitos, longitud con tres."""
        ns = "N" if self.lat >= 0 else "S"
        ew = "E" if self.lon >= 0 else "W"
        return f"{ns}{abs(self.lat):02d}{ew}{abs(self.lon):03d}"

    @property
    def url(self) -> str:
        return (
            f"{_BASE}/{self.version}/{self.epoch}/map/"
            f"ESA_WorldCover_10m_{self.epoch}_{self.version}_{self.name}_Map.tif"
        )

    @property
    def vsicurl(self) -> str:
        """Ruta que entiende GDAL para leerla sin descargarla."""
        return f"/vsicurl/{self.url}"

    @property
    def bounds(self) -> tuple[float, float, float, float]:
        """``(lon_min, lat_min, lon_max, lat_max)`` en grados."""
        return (
            float(self.lon),
            float(self.lat),
            float(self.lon + TILE_DEG),
            float(self.lat + TILE_DEG),
        )


def _piso(valor: float) -> int:
    """Multiplo de 3 inmediatamente inferior, tambien para negativos.

    En Python ``//`` ya redondea hacia abajo con negativos, que es justo lo que
    hace falta: ``-76,7`` tiene que caer en la tesela ``W078`` y no en ``W075``.
    Con truncamiento hacia cero, media Colombia se leeria de la tesela vecina.
    """
    return int(valor // TILE_DEG) * TILE_DEG


def tiles_for_bbox(bbox: BBox, *, version: str = VERSION, epoch: int = EPOCH) -> list[Tile]:
    """Teselas que cubren una caja en grados.

    Sin reproyeccion: la rejilla del producto ya esta en EPSG:4326, asi que esto
    es aritmetica entera y no necesita PROJ. Es la diferencia con
    :func:`..ghsl.tiles_for_bbox`, que tiene que cruzar a Mollweide y muestrear
    el ecuador porque alli los meridianos se curvan.

    Se recorta a la cobertura del producto: pedir una tesela que no existe
    cuesta un 404 y varios segundos de reintentos de GDAL, y la Antartida
    aparece en mas de una bbox nacional por el sur de Chile y Argentina.
    """
    lat_min = max(_piso(bbox.lat_min), LAT_MIN)
    lat_max = min(_piso(bbox.lat_max), LAT_MAX - TILE_DEG)
    if lat_min > lat_max:
        return []

    return [
        Tile(lat=lat, lon=lon, version=version, epoch=epoch)
        for lat in range(lat_min, lat_max + 1, TILE_DEG)
        for lon in range(_piso(bbox.lon_min), _piso(bbox.lon_max) + 1, TILE_DEG)
    ]
