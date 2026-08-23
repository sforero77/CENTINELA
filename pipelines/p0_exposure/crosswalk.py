"""Crosswalk hex <-> division politico-administrativa (§3.2).

Dos tablas, dos usos distintos:

* ``exposure_h3.adm2_id`` — asignacion **por centroide**, para etiquetar cada
  celda con un municipio y poder filtrar rapido.
* ``crosswalk_h3_adm`` — tabla ``(h3_08, adm2_id, frac_area)``, para prorratear
  con exactitud las celdas que cruzan frontera municipal.

El invariante que verifica la prueba unitaria (§6.1): la suma de poblacion por
municipio, prorrateada, debe igualar la suma nacional.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

#: Tolerancia relativa del invariante de suma (suma municipal vs nacional).
SUM_TOLERANCE = 1e-6


@dataclass(frozen=True, slots=True)
class CrosswalkRow:
    """Fraccion del area de una celda que cae en un municipio."""

    h3_08: int
    adm2_id: str
    frac_area: float


def validate_fractions(rows: Iterable[CrosswalkRow]) -> list[str]:
    """Verifica que las fracciones de cada celda sumen 1.

    Devuelve la lista de celdas problematicas. Una celda cuyas fracciones no
    suman 1 significa que parte de su poblacion se perderia o se contaria dos
    veces al prorratear: es un error de construccion, no un aviso.
    """
    totals: dict[int, float] = {}
    for row in rows:
        if not 0.0 <= row.frac_area <= 1.0:
            return [f"h3={row.h3_08} adm2={row.adm2_id}: frac_area fuera de [0,1]"]
        totals[row.h3_08] = totals.get(row.h3_08, 0.0) + row.frac_area

    return [
        f"h3={h3}: las fracciones suman {total:.9f}, no 1"
        for h3, total in sorted(totals.items())
        if abs(total - 1.0) > SUM_TOLERANCE
    ]


def prorate(value: float, rows: Iterable[CrosswalkRow]) -> dict[str, float]:
    """Reparte el valor de una celda entre municipios segun ``frac_area``."""
    return {row.adm2_id: value * row.frac_area for row in rows}


def build_crosswalk(iso3: str) -> list[CrosswalkRow]:
    """Construye el crosswalk de un pais.

    Contrato: interseccion de las celdas r8 del pais con los poligonos adm2
    vigentes, calculada en proyeccion equiarea local (§3.1), normalizando las
    fracciones para que sumen 1 aun donde el poligono municipal no cubre la
    celda completa (costa, frontera internacional).

    Implementacion pendiente (Fase 0, semana 2). En Colombia la fuente de
    verdad es el MGN del DANE (codigo DIVIPOLA de 5 digitos, VARCHAR — nunca
    entero: los codigos con cero inicial se corromperian).
    """
    raise NotImplementedError(
        f"Pendiente: construccion del crosswalk para {iso3} (Fase 0 semana 2)."
    )
