"""Borrador de hilo para redes (RF-07).

El unico paso manual permitido en todo el sistema: el hilo se **genera**
automaticamente pero **no se publica**. Un falso disparo tuiteado solo es peor
que un falso disparo silencioso, y el control editorial cuesta un clic.
"""

from __future__ import annotations

from ..common.formatting import format_count_prose, format_number_es
from .model import Report

#: Limite conservador por publicacion, compatible con la mayoria de redes.
MAX_CHARS = 280


def render_thread(report: Report) -> list[str]:
    """Genera el hilo como lista de publicaciones."""
    ev = report.event
    tot = report.totales
    posts: list[str] = []

    cabeza = (
        f"Sismo M{ev.mag} en {ev.lugar} ({ev.utc} UTC, "
        f"{format_number_es(ev.depth_km, 0)} km de profundidad). "
        f"Reporte automático de EXPOSICIÓN estimada de CENTINELA. "
        f"No es un reporte de daños."
    )
    posts.append(cabeza)

    if report.preliminar:
        posts.append(
            "Aun no hay ShakeMap publicado. Estas cifras son un corte preliminar "
            "por radios alrededor del epicentro y se actualizan solas cuando USGS "
            "publique el ShakeMap."
        )
    else:
        posts.append(
            f"Personas dentro de intensidad MMI≥6: {format_count_prose(tot.pop_mmi6p)}. "
            f"Dentro de MMI≥7: {format_count_prose(tot.pop_mmi7p)}. "
            f"Edificaciones en MMI≥7: {format_count_prose(tot.bld_mmi7p)}."
        )

    if report.top_municipios:
        top = report.top_municipios[:3]
        nombres = ", ".join(m.nombre for m in top)
        posts.append(f"Municipios más expuestos: {nombres}.")

    posts.append(
        "Exposición no es daño. CENTINELA no es alerta temprana ni reemplaza a los "
        "servicios geológicos ni a las unidades de gestión del riesgo. "
        "Datos abiertos y metodología: "
        "ver el reporte completo."
    )

    return [_truncate(p) for p in posts]


def render_thread_text(report: Report) -> str:
    """El hilo como ``hilo.txt``, separado por lineas en blanco dobles."""
    posts = render_thread(report)
    total = len(posts)
    numerados = [f"{i}/{total} {post}" for i, post in enumerate(posts, start=1)]
    return "\n\n".join(numerados) + "\n"


def _truncate(text: str) -> str:
    if len(text) <= MAX_CHARS:
        return text
    return text[: MAX_CHARS - 1].rstrip() + "…"
