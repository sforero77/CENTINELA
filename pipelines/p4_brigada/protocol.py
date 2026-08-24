"""Protocolo de activacion de la brigada y criterio de publicacion (§6.6).

Dos guardias que no son negociables:

1. **Linaje de pesos.** Un modelo afinado desde xBD hereda CC BY-NC-SA. Hay
   dos ramas de pesos, y la rama que alimenta publicaciones redistribuibles
   solo puede entrenarse con Copernicus EMS y etiquetas propias (T2.4).
2. **Umbral de calidad.** Precision y recall ≥ 0.75 por clase binaria contra
   verdad de Copernicus EMS, y la matriz de confusion se publica **siempre**
   junto al GeoPackage.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

#: Umbral minimo por clase binaria dano/no-dano antes de publicar.
MIN_PRECISION = 0.75
MIN_RECALL = 0.75


class WeightsLineage(StrEnum):
    """Linaje de los pesos del modelo, que determina el cubo de publicacion."""

    #: Entrenado solo con Copernicus EMS + etiquetas propias. Redistribuible.
    LIMPIA = "limpia"
    #: Pre-entrenado con xBD/xView2. Hereda NC; va al cubo ``nc/``.
    NC = "nc"


@dataclass(frozen=True, slots=True)
class ValidationMetrics:
    """Metricas de la clase binaria dano/no-dano contra verdad EMS."""

    precision: float
    recall: float
    #: Matriz de confusion (tp, fp, fn, tn); se publica siempre.
    tp: int
    fp: int
    fn: int
    tn: int

    @property
    def cumple_umbral(self) -> bool:
        return self.precision >= MIN_PRECISION and self.recall >= MIN_RECALL


def gate_publication(metrics: ValidationMetrics, lineage: WeightsLineage) -> tuple[bool, str]:
    """¿Se puede publicar este GeoPackage, y en que cubo?

    Returns:
        ``(publicable, destino)``. ``destino`` es el cubo o la razon del bloqueo.
    """
    if not metrics.cumple_umbral:
        return False, (
            f"Bloqueado: precision {metrics.precision:.2f} / recall {metrics.recall:.2f} "
            f"por debajo del umbral {MIN_PRECISION:.2f}"
        )
    destino = "nc/" if lineage is WeightsLineage.NC else "core/"
    return True, destino
