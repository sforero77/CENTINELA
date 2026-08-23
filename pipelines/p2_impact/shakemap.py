"""ShakeMap -> conjunto de celdas H3 r8 con intensidad.

Camino elegido: **contornos** (``cont_mmi.json``) y no el raster ``grid.xml``.
Los contornos son poligonos de isointensidad ya suavizados por USGS, pesan
ordenes de magnitud menos y se convierten a H3 con ``polyfill`` sin necesidad
de rasterio en el camino critico.

Casos que las pruebas unitarias deben cubrir (§6.1): poligono con hueco,
multipoligono y frontera costera. El antimeridiano no aplica a LATAM.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..common.constants import H3_RES_COMPUTE


@dataclass(frozen=True, slots=True)
class MmiCell:
    """Intensidad asignada a una celda H3."""

    h3_08: int
    mmi_mean: float
    mmi_max: float


@dataclass(frozen=True, slots=True)
class MmiContour:
    """Un contorno de isointensidad del ShakeMap."""

    value: float
    #: Geometria GeoJSON (``Polygon`` o ``MultiPolygon``).
    geometry: dict[str, Any]


def parse_contours(payload: dict[str, Any]) -> list[MmiContour]:
    """Extrae los contornos MMI del GeoJSON ``cont_mmi``.

    USGS publica en el mismo archivo contornos de MMI y, segun version, de PGA
    y PGV. Filtramos por la propiedad ``paramvalue`` bajo el tipo ``mmi``.
    """
    features = payload.get("features")
    if not isinstance(features, list):
        raise ValueError("cont_mmi sin lista 'features'")

    contours: list[MmiContour] = []
    for feature in features:
        props = feature.get("properties") or {}
        if str(props.get("type", "mmi")).lower() != "mmi":
            continue
        value = props.get("value", props.get("paramvalue"))
        geometry = feature.get("geometry")
        if value is None or not isinstance(geometry, dict):
            continue
        contours.append(MmiContour(value=float(value), geometry=geometry))
    return sorted(contours, key=lambda c: c.value)


def contours_to_h3(
    contours: list[MmiContour],
    *,
    resolution: int = H3_RES_COMPUTE,
) -> dict[int, MmiCell]:
    """Convierte contornos de isointensidad en celdas H3 con MMI asignada.

    Contrato:
        * Los contornos son anidados (MMI 8 dentro de MMI 7 dentro de MMI 6).
          Se recorren de menor a mayor y la celda conserva el **maximo** MMI
          de los contornos que la contienen.
        * ``mmi_mean`` se estima como el valor del contorno asignado; una
          version futura puede refinarlo muestreando ``grid.xml``.
        * Devuelve un diccionario ``h3_08 -> MmiCell`` para join directo.

    Implementacion pendiente (Fase 0, semana 3): ``h3.polygon_to_cells`` sobre
    cada anillo, restando huecos, con ``shapely`` para la validacion de
    geometria. Requiere el extra ``[geo]``.
    """
    raise NotImplementedError(
        "Pendiente: polyfill H3 de contornos MMI (Fase 0 semana 3). "
        "Contrato definido y cubierto por tests/unit/test_shakemap_polyfill.py"
    )
