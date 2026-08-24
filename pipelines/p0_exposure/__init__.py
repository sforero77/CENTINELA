"""P0 — EXPOSICION: construccion trimestral del activo ``exposure_h3`` por pais.

Fuera del camino critico de latencia. Su unico requisito duro es O4: cualquier
persona reconstruye el activo de un pais con ``make country ISO=COL`` desde
fuentes publicas, sin credenciales privadas.
"""

from .layers import LAYERS, LayerSpec

__all__ = ["LAYERS", "LayerSpec"]
