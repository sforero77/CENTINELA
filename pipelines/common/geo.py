"""Primitivas geometricas ligeras del camino critico.

Deliberadamente sin dependencias geo pesadas: el job de trigger (P1) debe
arrancar en un runner frio en segundos, y lo unico que necesita es un test de
punto-en-bbox.
"""

from __future__ import annotations

import math
import os
from dataclasses import dataclass
from typing import Final

#: Radio medio de la Tierra (m), esfera de referencia WGS84.
EARTH_RADIUS_M: Final[float] = 6_371_008.8

#: Variables con las que un PROJ del sistema se impone sobre el empaquetado.
_PROJ_VARS: Final[tuple[str, ...]] = ("PROJ_LIB", "PROJ_DATA")

#: Escape hatch: quien de verdad necesite el PROJ del sistema —rejillas
#: geoidales nacionales, por ejemplo— lo declara y esto no toca nada.
RESPETAR_PROJ_DEL_SISTEMA: Final[str] = "CENTINELA_RESPETA_PROJ"


def ensure_bundled_proj() -> tuple[str, ...]:
    """Aparta el PROJ del sistema para que cada rueda use el suyo.

    `rasterio` y `pyproj` empaquetan cada una su propia base de datos de PROJ
    —es la mitad del peso de sus ruedas— y la encuentran solas. Una variable
    `PROJ_LIB` puesta en el sistema las tapa a las dos con una base que puede
    ser de otra version, y entonces **cualquier CRS deja de resolverse**.

    Pasa de verdad y sin que uno lo haya pedido: instalar PostgreSQL con
    PostGIS en Windows deja `PROJ_LIB` apuntando a su propio PROJ. Medido en
    una maquina asi: `proj.db contains DATABASE.LAYOUT.VERSION.MINOR = 2
    whereas a number >= 6 is expected`, y con el la reproyeccion de GHS-POP
    desde Mollweide. Es decir, `centinela country` inservible en un equipo
    que por lo demas cumple todos los requisitos.

    O4 dice que el sistema tiene que construir un pais desde un clon limpio
    sin dependencias del sistema. Un PROJ del sistema **es** una dependencia
    del sistema, y ademas una que nadie eligio.

    Hay que llamarla **antes** de importar `rasterio` o `pyproj`: GDAL fija su
    ruta de busqueda al inicializarse y despues ya no la relee. Por eso vive
    en este modulo, que no arrastra nada geo, y no en uno que ya los importe.

    Returns:
        Las variables que se apartaron. Vacio es el caso normal.
    """
    if os.environ.get(RESPETAR_PROJ_DEL_SISTEMA):
        return ()
    return tuple(var for var in _PROJ_VARS if os.environ.pop(var, None) is not None)


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
#: para cubrir Mexico completo; el sur llega mas alla de Cabo de Hornos.
#:
#: **Corregida el 23-ago-2026.** Al medir la caja de los diecinueve paises con
#: `division_area` de Overture salio que la ventana no cubria territorio de los
#: paises que el sistema dice cubrir, y el disparador filtra por ella:
#:
#: * Mexico llega a **118,65°W** (Isla Guadalupe y Revillagigedo) y la ventana
#:   cortaba en 118,0°W.
#: * Chile llega a **56,78°S** (Cabo de Hornos, Diego Ramirez) y cortaba en
#:   56,0°S — justo donde la zona de fractura de Shackleton produce sismos.
#:
#: Un sismo relevante ahi habria quedado fuera del filtro sin dejar rastro: no
#: es un fallo, es un evento que nunca existio para el sistema.
#:
#: El limite este pasa de 34°W a **32°W**: Fernando de Noronha esta en 32,42°W
#: con unos 3.000 habitantes y quedaba fuera. No llega hasta los 28,58°W que da
#: Brasil, y eso es deliberado: alli esta el archipielago de San Pedro y San
#: Pablo, que se asienta **sobre la dorsal mesoatlantica**. Estirar la ventana
#: hasta el mete sismicidad oceanica frecuente y sin poblacion a cambio de una
#: estacion cientifica con unas pocas personas. 32°W cubre a los habitantes y
#: deja la dorsal fuera.
LATAM_BBOX: Final[BBox] = BBox(lon_min=-119.0, lat_min=-57.5, lon_max=-32.0, lat_max=33.0)


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
