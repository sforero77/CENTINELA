"""P3 — REPORTE: ``report.json`` y todos sus derivados.

El JSON es la fuente de verdad; markdown, CSV, PNG e hilo se derivan de el.
Ningun renderizador recalcula cifras: si el markdown y el hilo pudieran
divergir, tarde o temprano divergirian en el peor momento.
"""

from .markdown import render_markdown
from .model import Descargas, Evento, Incertidumbre, Inputs, MunicipioTop, Report, Totales

__all__ = [
    "Descargas",
    "Evento",
    "Incertidumbre",
    "Inputs",
    "MunicipioTop",
    "Report",
    "Totales",
    "render_markdown",
]
