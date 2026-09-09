"""P4 — BRIGADA: evaluacion de dano por edificacion con IA (Fase 2).

Se activa **por evento**, solo cuando hay imagen abierta post-evento, y corre
completamente fuera del camino critico del reporte automatico. Produce
*priorizacion*, jamas veredicto: el sistema no dictamina dano estructural ni
habitabilidad (§1.2).
"""

from .schema import GEOPACKAGE_FIELDS, DamageClass, DamageFeature

__all__ = ["GEOPACKAGE_FIELDS", "DamageClass", "DamageFeature"]
