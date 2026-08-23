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
    """Un contorno de isointensidad del ShakeMap.

    **La geometria es ``MultiLineString``, no poligonos.** Verificado contra el
    ShakeMap real de Chocó: `cont_mmi.json` publica *isolineas*, y convertirlas
    en areas es trabajo nuestro.
    """

    value: float
    #: Geometria GeoJSON. En la practica siempre ``MultiLineString``.
    geometry: dict[str, Any]

    @property
    def rings(self) -> list[list[list[float]]]:
        """Lineas que cierran sobre si mismas, utilizables como anillo."""
        lineas = self.geometry.get("coordinates", [])
        return [linea for linea in lineas if linea and linea[0] == linea[-1]]

    @property
    def open_lines(self) -> list[list[list[float]]]:
        """Lineas abiertas, cortadas por el borde de la grilla del ShakeMap."""
        lineas = self.geometry.get("coordinates", [])
        return [linea for linea in lineas if linea and linea[0] != linea[-1]]


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

    Contrato, corregido tras inspeccionar el ShakeMap real de Chocó:

    * La entrada son **isolineas**, no poligonos. Hay que cerrarlas en anillos
      antes de rellenar. Los contornos de MMI≥5 —los unicos que el reporte
      publica— vienen cerrados; los de MMI bajo aparecen cortados por el borde
      de la grilla y hay que recortarlos contra ese borde o descartarlos.
    * Un mismo nivel trae **muchas lineas** (el ShakeMap de Chocó tiene 76 para
      MMI 4.0): islas de intensidad separadas, no un anillo unico.
    * Los niveles son anidados: MMI 7,5 dentro de 7,0 dentro de 6,5. Se
      recorren de menor a mayor y la celda conserva el **maximo** MMI de los
      contornos que la contienen.
    * Un anillo dentro de otro del mismo nivel es un hueco, y hay que restarlo.
    * ``mmi_mean`` se estima con el valor del contorno asignado; refinarlo
      exige muestrear ``grid.xml``, que es la alternativa raster si el cierre
      de isolineas resulta demasiado fragil.
    * Devuelve ``h3_08 -> MmiCell`` para join directo.

    Implementacion pendiente (Fase 0, semana 3): ``shapely.polygonize`` sobre
    las lineas cerradas, jerarquia de contencion para huecos, y
    ``h3.polygon_to_cells`` por anillo. Requiere el extra ``[geo]``.
    """
    raise NotImplementedError(
        "Pendiente: polyfill H3 de contornos MMI (Fase 0 semana 3). "
        "Contrato definido contra el ShakeMap real de Chocó."
    )
