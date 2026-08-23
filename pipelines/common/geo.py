"""Primitivas geometricas ligeras del camino critico.

Deliberadamente sin dependencias geo pesadas: el job de trigger (P1) debe
arrancar en un runner frio en segundos, y lo unico que necesita es un test de
punto-en-bbox.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Final

#: Radio medio de la Tierra (m), esfera de referencia WGS84.
EARTH_RADIUS_M: Final[float] = 6_371_008.8


@dataclass(frozen=True, slots=True)
class BBox:
    """Caja envolvente en EPSG:4326, grados decimales."""

    lon_min: float
    lat_min: float
    lon_max: float
    lat_max: float

    def __post_init__(self) -> None:
        if self.lon_min >= self.lon_max:
            raise ValueError(f"lon_min debe ser < lon_max: {self.lon_min} >= {self.lon_max}")
        if self.lat_min >= self.lat_max:
            raise ValueError(f"lat_min debe ser < lat_max: {self.lat_min} >= {self.lat_max}")

    def contains(self, lon: float, lat: float) -> bool:
        """¿El punto cae dentro de la caja (bordes incluidos)?"""
        return self.lon_min <= lon <= self.lon_max and self.lat_min <= lat <= self.lat_max

    def as_tuple(self) -> tuple[float, float, float, float]:
        """Orden (lon_min, lat_min, lon_max, lat_max), convencion GeoJSON."""
        return (self.lon_min, self.lat_min, self.lon_max, self.lat_max)


#: Ventana de interes del sistema (RF-01). El limite norte se estira a 33°N
#: para cubrir Mexico completo; el sur llega a 56°S (Cabo de Hornos).
LATAM_BBOX: Final[BBox] = BBox(lon_min=-118.0, lat_min=-56.0, lon_max=-34.0, lat_max=33.0)


def haversine_km(lon_a: float, lat_a: float, lon_b: float, lat_b: float) -> float:
    """Distancia de circulo maximo en km.

    Usada solo por el reporte preliminar sin ShakeMap (RF-03), donde la
    exposicion se corta por radios de 25/50/100 km alrededor del epicentro.
    """
    phi_a, phi_b = math.radians(lat_a), math.radians(lat_b)
    d_phi = phi_b - phi_a
    d_lambda = math.radians(lon_b - lon_a)
    h = math.sin(d_phi / 2) ** 2 + math.cos(phi_a) * math.cos(phi_b) * math.sin(d_lambda / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(h)) / 1000.0
