"""P2 — IMPACTO: cruce de productos USGS por evento contra el activo de exposicion.

Idempotente por ``(usgs_id, shakemap_version)``: relanzarlo tras un kill a mitad
de camino no duplica filas ni corrompe estado (RF-02, §6.5).
"""

from .products import ProductRef, ProductSet, parse_products

__all__ = ["ProductRef", "ProductSet", "parse_products"]
