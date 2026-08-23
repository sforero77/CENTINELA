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


def rings_to_geometry(contour: MmiContour) -> Any:
    """Convierte los anillos cerrados de un contorno en un area (shapely).

    Los anillos anidados del mismo nivel son huecos: un anillo de MMI 6 dentro
    de otro de MMI 6 delimita una zona que **no** alcanza MMI 6. La diferencia
    simetrica acumulada da exactamente esa semantica par/impar, y para anillos
    disjuntos se comporta como la union — que es lo que se quiere para las
    islas de intensidad separadas.

    Requiere el extra ``[geo]``.
    """
    from shapely.geometry import Polygon
    from shapely.ops import unary_union

    # buffer(0) repara autointersecciones: los contornos de ShakeMap traen
    # anillos que se tocan a si mismos donde la isolinea roza el borde de la
    # grilla, y shapely los rechaza sin esto.
    poligonos = [Polygon(anillo).buffer(0) for anillo in contour.rings if len(anillo) >= 4]
    poligonos = [p for p in poligonos if not p.is_empty]
    if not poligonos:
        return None
    # De mayor a menor: cada anillo interior recorta al que lo contiene.
    poligonos.sort(key=lambda p: p.area, reverse=True)
    area = poligonos[0]
    for p in poligonos[1:]:
        area = area.symmetric_difference(p)
    return unary_union(area)


def contours_to_h3(
    contours: list[MmiContour],
    *,
    resolution: int = H3_RES_COMPUTE,
    min_value: float = 0.0,
) -> dict[int, MmiCell]:
    """Convierte contornos de isointensidad en celdas H3 con MMI asignada.

    Contrato, fijado tras inspeccionar el ShakeMap real de Chocó:

    * La entrada son **isolineas**, no poligonos. Se cierran en anillos antes de
      rellenar. Los contornos de MMI>=5 —los unicos que el reporte publica—
      vienen cerrados; los de MMI bajo aparecen cortados por el borde de la
      grilla y sus lineas abiertas se descartan, porque cerrarlas a la brava
      inventaria area que el ShakeMap no afirma.
    * Un mismo nivel trae **muchas** lineas (76 para MMI 4,0 en Chocó): islas de
      intensidad separadas, no un anillo unico.
    * Los niveles son anidados. Se recorren de menor a mayor y cada celda
      conserva el **maximo** MMI de los contornos que la contienen.
    * ``mmi_mean`` se estima con el valor del contorno asignado. Refinarlo
      exigiria muestrear ``grid.xml``.

    Args:
        contours: contornos ya parseados.
        resolution: resolucion H3 de salida.
        min_value: ignora contornos por debajo de este MMI. El reporte publica
            desde MMI 6, y rellenar los niveles bajos multiplica el numero de
            celdas sin aportar nada al resultado.

    Returns:
        ``h3_08 -> MmiCell``, listo para join.
    """
    import h3

    celdas: dict[int, float] = {}
    for contorno in sorted(contours, key=lambda c: c.value):
        if contorno.value < min_value:
            continue
        area = rings_to_geometry(contorno)
        if area is None or area.is_empty:
            continue
        try:
            alcanzadas = h3.geo_to_cells(area.__geo_interface__, resolution)
        except Exception as exc:  # geometria degenerada del contorno
            raise ValueError(
                f"No se pudo rellenar el contorno MMI {contorno.value}: {exc}"
            ) from exc
        for celda in alcanzadas:
            entero = h3.str_to_int(celda) if isinstance(celda, str) else int(celda)
            # Recorrido de menor a mayor: el ultimo en escribir es el mayor MMI.
            celdas[entero] = contorno.value

    return {h: MmiCell(h3_08=h, mmi_mean=v, mmi_max=v) for h, v in celdas.items()}
