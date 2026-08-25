"""Overture: seleccion de ficheros parquet por pais, via el catalogo STAC.

El tema ``buildings`` del release vigente son **512 ficheros, 277 GB y 2.529
millones de edificaciones**. Colombia toca once. Averiguar cuales sin leer los
datos es la diferencia entre un build de minutos y uno imposible.

El catalogo STAC de la coleccion (155 KB) trae el bbox de cada fichero en
``extent.spatial.bbox``. Con eso se seleccionan los once ficheros, y dentro de
cada uno el filtro sobre la columna ``bbox`` poda a nivel de row-group: contar
las edificaciones de Quibdó en un fichero remoto de 5 millones de filas toma
**2,2 segundos**.

**Trampa verificada.** El estandar STAC dice que ``extent.spatial.bbox[0]`` es
la union de todas las sub-extensiones y que las reales empiezan en el indice 1.
Overture **no** hace eso: publica 512 entradas para 512 ficheros, y la entrada
``[0]`` es el bbox del primer fichero, no una union. Aplicar la lectura del
estandar —saltarse la primera— desplaza todo un puesto y hace leer los ficheros
equivocados, en silencio y con resultados plausibles. El emparejamiento 1:1 esta
comprobado contra la extension real medida de varios ficheros.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Final

from ...common.geo import BBox
from ...common.http import Fetcher

STAC_ROOT: Final[str] = "https://stac.overturemaps.org"

#: Temas y subtipos que consume el activo de exposicion. El subtipo importa:
#: ``building_part`` es geometria auxiliar y contarla inflaria ``bld_count``.
THEME_BUILDINGS: Final[tuple[str, str]] = ("buildings", "building")
THEME_TRANSPORTATION: Final[tuple[str, str]] = ("transportation", "segment")
THEME_DIVISIONS: Final[tuple[str, str]] = ("divisions", "division_area")


class OvertureCatalogError(Exception):
    """El catalogo STAC no tiene la forma que el pipeline espera."""


@dataclass(frozen=True, slots=True)
class ParquetFile:
    """Un fichero parquet del release, con su extension espacial."""

    url: str
    bbox: tuple[float, float, float, float]

    def intersects(self, other: BBox) -> bool:
        xmin, ymin, xmax, ymax = self.bbox
        return not (
            xmax < other.lon_min
            or xmin > other.lon_max
            or ymax < other.lat_min
            or ymin > other.lat_max
        )


def collection_url(release: str, theme: str, type_: str) -> str:
    """URL del ``collection.json`` de un tema y subtipo en un release fijado."""
    return f"{STAC_ROOT}/{release}/{theme}/{type_}/collection.json"


def parse_collection(payload: dict[str, Any]) -> list[ParquetFile]:
    """Extrae los ficheros y su bbox de un ``collection.json``.

    Raises:
        OvertureCatalogError: si el numero de bboxes no coincide con el de
            ficheros. Es la unica senal de que el emparejamiento 1:1 dejo de
            valer, y seguir adelante significaria leer los ficheros equivocados.
    """
    try:
        bboxes = payload["extent"]["spatial"]["bbox"]
    except (KeyError, TypeError) as exc:
        raise OvertureCatalogError(f"collection.json sin extent.spatial.bbox: {exc}") from exc

    items = [
        str(link["href"])
        for link in payload.get("links", [])
        if link.get("rel") == "item" and link.get("href")
    ]
    if not items:
        raise OvertureCatalogError("collection.json sin enlaces 'item'")
    if len(bboxes) != len(items):
        raise OvertureCatalogError(
            f"El catalogo trae {len(bboxes)} bboxes para {len(items)} ficheros. "
            f"El emparejamiento 1:1 dejo de valer y la seleccion seria incorrecta; "
            f"revisar si Overture adopto la lectura estandar de STAC "
            f"(bbox[0] = union) antes de tocar nada."
        )

    ficheros: list[ParquetFile] = []
    for href, bbox in zip(items, bboxes, strict=True):
        if len(bbox) < 4:
            raise OvertureCatalogError(f"bbox mal formado en el catalogo: {bbox!r}")
        ficheros.append(
            ParquetFile(
                url=href, bbox=(float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3]))
            )
        )
    return ficheros


def select_files(
    fetcher: Fetcher,
    bbox: BBox,
    *,
    release: str,
    theme: str = THEME_BUILDINGS[0],
    type_: str = THEME_BUILDINGS[1],
) -> list[ParquetFile]:
    """Ficheros del tema que intersecan la caja del pais."""
    payload = fetcher.get_json(collection_url(release, theme, type_))
    return [f for f in parse_collection(payload) if f.intersects(bbox)]


#: Filtro que se aplica dentro de cada fichero. Va sobre la columna ``bbox``
#: —no sobre la geometria— porque es la que tiene estadisticas por row-group y
#: por tanto la que permite podar sin descomprimir.
BBOX_PREDICATE = (
    "bbox.xmin BETWEEN {lon_min} AND {lon_max} AND bbox.ymin BETWEEN {lat_min} AND {lat_max}"
)

#: El mismo filtro, pero por **interseccion** en vez de contencion.
#:
#: :data:`BBOX_PREDICATE` mira solo la esquina inferior izquierda del rasgo, y
#: eso vale mientras el rasgo sea pequeno frente a la caja: un edificio o un
#: tramo de via que empieza dentro del pais, esta dentro del pais.
#:
#: **Deja de valer en cuanto el rasgo es mas grande que la caja.** Al cargar los
#: paises limitrofes de Paraguay no devolvio ninguno: la esquina de Brasil esta
#: en -73,99, muy al oeste de la caja paraguena, aunque Brasil ocupe media caja.
#: La consulta corrio, devolvio cero filas y el build siguio sin avisar de nada
#: —el modo de fallo que este proyecto persigue— hasta que el log de vecinos
#: dijo ``poligonos: 0``.
BBOX_INTERSECTS_PREDICATE = (
    "bbox.xmin <= {lon_max} AND bbox.xmax >= {lon_min} "
    "AND bbox.ymin <= {lat_max} AND bbox.ymax >= {lat_min}"
)


def bbox_predicate(bbox: BBox, *, intersecta: bool = False) -> str:
    """Predicado SQL de poda para DuckDB.

    Args:
        intersecta: usa interseccion en vez de contencion. Obligatorio cuando el
            rasgo puede ser mayor que la caja —un pais, una region—; innecesario
            y mas caro de podar para edificaciones y vias.
    """
    plantilla = BBOX_INTERSECTS_PREDICATE if intersecta else BBOX_PREDICATE
    return plantilla.format(
        lon_min=bbox.lon_min,
        lon_max=bbox.lon_max,
        lat_min=bbox.lat_min,
        lat_max=bbox.lat_max,
    )


#: Clave del asset preferido dentro de un item STAC. Overture publica el mismo
#: parquet en AWS y en Azure; ``aws`` es el que sirve por HTTPS desde la region
#: donde vive el bucket, y es el que DuckDB lee mas rapido con ``httpfs``.
PREFERRED_ASSET: Final[str] = "aws"

#: Tipo MIME con el que el catalogo marca los ficheros de datos.
PARQUET_MEDIA_TYPE: Final[str] = "application/vnd.apache.parquet"


def item_data_url(payload: dict[str, Any], *, prefer: str = PREFERRED_ASSET) -> str:
    """URL del parquet de un item STAC.

    Los enlaces ``item`` del ``collection.json`` apuntan a un JSON por fichero,
    no al parquet: el nombre real lleva un UUID que no se puede deducir. Hay que
    abrir el item y leer su asset.

    Raises:
        OvertureCatalogError: si el item no publica ningun asset de datos.
    """
    assets = payload.get("assets") or {}
    candidatos = {
        nombre: asset
        for nombre, asset in assets.items()
        if isinstance(asset, dict)
        and asset.get("href")
        and (asset.get("type") == PARQUET_MEDIA_TYPE or "data" in (asset.get("roles") or []))
    }
    if not candidatos:
        raise OvertureCatalogError(
            f"El item {payload.get('id', '?')!r} no publica ningun asset de datos"
        )
    elegido = candidatos.get(prefer) or next(iter(candidatos.values()))
    return str(elegido["href"])


def resolve_data_urls(
    fetcher: Fetcher, ficheros: list[ParquetFile], *, prefer: str = PREFERRED_ASSET
) -> list[str]:
    """Abre cada item seleccionado y devuelve la URL de su parquet.

    Una peticion por fichero, pero solo por los que tocan el pais: once para
    Colombia, no 512.
    """
    return [item_data_url(fetcher.get_json(f.url), prefer=prefer) for f in ficheros]
