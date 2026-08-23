"""Ground Failure -> probabilidad de deslizamiento y licuefaccion por celda.

Diferenciador clave del sistema (§2.1): USGS publica rasters de probabilidad de
deslizamiento y licuefaccion por evento, versionados como el ShakeMap, y casi
nadie los integra. Cuando el producto no existe para un evento, el reporte
omite la seccion con nota explicita y **no falla** (golden test G3).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..common.constants import GROUND_FAILURE_HIGH_PROB


@dataclass(frozen=True, slots=True)
class GroundFailureCell:
    """Probabilidades de falla de terreno en una celda."""

    h3_08: int
    #: Probabilidad de deslizamiento (landslide), 0-1.
    ls_prob: float
    #: Probabilidad de licuefaccion, 0-1.
    lq_prob: float

    @property
    def ls_alta(self) -> bool:
        return self.ls_prob >= GROUND_FAILURE_HIGH_PROB

    @property
    def lq_alta(self) -> bool:
        return self.lq_prob >= GROUND_FAILURE_HIGH_PROB


def sample_rasters(
    landslide_tif: Path | None,
    liquefaction_tif: Path | None,
    cells: list[int],
) -> dict[int, GroundFailureCell]:
    """Muestrea los rasters de Ground Failure en el centroide de cada celda.

    Contrato:
        * ``cells`` son ids H3 r8; el muestreo se hace en el centroide, que a
          r8 (~0.46 km² por celda) es suficiente frente a la resolucion nativa
          del producto.
        * Un raster ausente (``None``) produce probabilidad 0.0 en su columna,
          y el reporte marca la seccion como no disponible — nunca la inventa.

    Implementacion pendiente (Fase 0, semana 3): ``rasterio.sample`` sobre los
    GeoTIFF del producto. Requiere el extra ``[geo]``.
    """
    raise NotImplementedError(
        "Pendiente: muestreo de rasters Ground Failure (Fase 0 semana 3). "
        "Contrato definido y cubierto por tests/unit/test_ground_failure.py"
    )
