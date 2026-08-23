"""Mapa estatico del reporte (T0.8: decidir motor por calidad/tiempo).

Dos variantes obligatorias:

* ``general`` — contexto amplio, contornos MMI, municipios etiquetados.
* ``prensa`` — recorte cerrado, tipografia grande, pensado para captura.

Restriccion dura: el PNG mas el markdown deben sumar menos de 500 KB (RNF-05),
y la teselas de fondo deben tener atribucion compatible con el cubo ``core``.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from .model import Report


class MapVariant(StrEnum):
    GENERAL = "general"
    PRENSA = "prensa"


@dataclass(frozen=True, slots=True)
class MapSpec:
    """Parametros de render de una variante."""

    variant: MapVariant
    width_px: int
    height_px: int
    dpi: int
    #: Presupuesto de peso del archivo final.
    max_bytes: int = 400_000


SPECS: dict[MapVariant, MapSpec] = {
    MapVariant.GENERAL: MapSpec(MapVariant.GENERAL, 1200, 900, 110),
    MapVariant.PRENSA: MapSpec(MapVariant.PRENSA, 1600, 900, 130),
}

#: Atribucion obligatoria al pie de todo mapa (§2.4 regla 2).
ATTRIBUTION_LINE = (
    "Intensidad: USGS ShakeMap (dominio publico) · "
    "Poblacion: GHS-POP, JRC/Comision Europea · "
    "Edificaciones y vias: Overture Maps, © OpenStreetMap contributors (ODbL) · "
    "CENTINELA — exposicion estimada, no dano"
)


def render_map(report: Report, variant: MapVariant, path: Path) -> Path:
    """Renderiza una variante del mapa.

    Implementacion pendiente (Fase 0, semana 3, tras T0.8). Las dos opciones
    en evaluacion son ``matplotlib`` + ``contextily`` y un render headless de
    MapLibre; el criterio de decision es calidad tipografica frente a tiempo
    de render dentro del presupuesto de latencia.
    """
    raise NotImplementedError(
        f"Pendiente: render del mapa '{variant}' (Fase 0 semana 3, decision T0.8)."
    )
