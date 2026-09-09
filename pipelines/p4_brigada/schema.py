"""Esquema del GeoPackage de dano por edificacion (RF-10).

Interoperable a proposito con el formato de Microsoft AI for Good / Overture:
la validacion cruzada contra el GeoPackage de Cali solo es posible si las
columnas coinciden (T2.3).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class DamageClass(StrEnum):
    """Clases publicadas.

    ``cloud`` y ``unknown`` son clases de primera categoria, no huecos: decir
    "no se pudo ver" es informacion util para quien planifica una inspeccion.
    """

    NO_DAMAGE = "no_damage"
    DAMAGED = "damaged"
    CLOUD = "cloud"
    UNKNOWN = "unknown"


#: Columnas del GeoPackage, en orden.
GEOPACKAGE_FIELDS: tuple[tuple[str, str], ...] = (
    ("gers_id", "TEXT"),  # id estable de Overture GERS
    ("geom", "POLYGON"),
    ("damage_class", "TEXT"),
    ("confidence", "REAL"),
    ("scene_id", "TEXT"),
    ("model_version", "TEXT"),
)


@dataclass(frozen=True, slots=True)
class DamageFeature:
    """Una edificacion clasificada."""

    gers_id: str
    damage_class: DamageClass
    confidence: float
    scene_id: str
    model_version: str

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence fuera de [0,1]: {self.confidence}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "gers_id": self.gers_id,
            "damage_class": self.damage_class.value,
            "confidence": self.confidence,
            "scene_id": self.scene_id,
            "model_version": self.model_version,
        }
