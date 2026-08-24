"""Render de ``report.md`` desde ``report.json``.

Restriccion de diseno (RNF-05): el reporte debe ser legible en un movil con 3G
en zona de desastre. Markdown plano, sin imagenes embebidas, md + png < 500 KB.
"""

from __future__ import annotations

from ..common.constants import DISCLAIMERS, TOP_ADM2_COUNT
from ..common.formatting import format_count_prose, format_number_es
from .model import Report

_ENCABEZADO_PRELIMINAR = (
    "> **Reporte preliminar sin ShakeMap.** El corte es por radios alrededor "
    "del epicentro, no por intensidad modelada. Se actualiza automaticamente "
    "en cuanto USGS publique el ShakeMap del evento."
)

#: Aviso de reconstruccion retrospectiva. No es un matiz menor: cambia lo que
#: las cifras significan. La poblacion puede ser de la epoca del sismo —GHS-POP
#: publica de 1975 a 2030 en pasos de cinco anos— pero las edificaciones, las
#: vias y el equipamiento son **los de hoy**, porque OpenStreetMap y Overture no
#: guardan el pasado. Un lector que no lo sepa leeria "444.281 edificaciones
#: expuestas" como si hubieran existido entonces.
_ENCABEZADO_BACKTEST = (
    "> **Reconstruccion retrospectiva.** Este reporte se calculo despues del "
    "evento, no en respuesta a el, y no cuenta para las metricas de latencia "
    "del sistema.\n"
    ">\n"
    "> La **poblacion** corresponde a la epoca indicada en el manifest de "
    "exposicion. Las **edificaciones, vias, sedes de salud y educativas son las "
    "actuales**: OpenStreetMap y Overture publican el estado presente, no el "
    'historico. Leelas como "que infraestructura de hoy caeria en esa zona de '
    'intensidad", no como lo que habia entonces.'
)


def render_markdown(report: Report) -> str:
    """Genera el markdown del reporte en espanol neutro (RF-06)."""
    ev = report.event
    tot = report.totales
    partes: list[str] = []

    partes.append(f"# Exposicion sismica — M{ev.mag} {ev.lugar}")
    partes.append(
        f"**Evento USGS:** `{ev.usgs_id}` · **Origen:** {ev.utc} UTC · "
        f"**Profundidad:** {format_number_es(ev.depth_km, 1)} km"
    )
    if report.preliminar:
        partes.append(_ENCABEZADO_PRELIMINAR)
    if report.backtest:
        partes.append(_ENCABEZADO_BACKTEST)

    partes.append("## Exposicion estimada")
    partes.append(_tabla_totales(report))

    if tot.pop_65p_mmi7p:
        partes.append(
            f"De la poblacion en intensidad MMI≥7, alrededor de "
            f"**{format_count_prose(tot.pop_65p_mmi7p)}** personas tienen 65 anos o mas."
        )

    if report.top_municipios:
        partes.append(f"## Municipios mas expuestos (top {TOP_ADM2_COUNT})")
        partes.append(_tabla_municipios(report))

    partes.append(_seccion_ground_failure(report))

    if ev.pager_alert:
        partes.append(
            f"## Referencia cruzada\n\n"
            f"PAGER (USGS) estima para este evento una alerta **{ev.pager_alert}**. "
            f"CENTINELA no estima victimas; la cifra se incluye solo como contraste."
        )

    partes.append(_seccion_incertidumbre(report))

    if report.changelog:
        partes.append(
            "## Cambios frente a la version anterior\n\n"
            + "\n".join(f"- {linea}" for linea in report.changelog)
        )

    partes.append(_seccion_descargas(report))
    partes.append(_seccion_procedencia(report))
    partes.append("## Advertencias\n\n" + "\n".join(f"- {d}" for d in DISCLAIMERS))

    return "\n\n".join(p for p in partes if p) + "\n"


def _tabla_totales(report: Report) -> str:
    tot = report.totales
    filas = [
        ("Poblacion en MMI≥6", format_count_prose(tot.pop_mmi6p)),
        ("Poblacion en MMI≥7", format_count_prose(tot.pop_mmi7p)),
        ("Poblacion en MMI≥8", format_count_prose(tot.pop_mmi8p)),
        ("Edificaciones en MMI≥7", format_count_prose(tot.bld_mmi7p)),
        ("Sedes de salud en MMI≥7", format_number_es(tot.health_mmi7p)),
        ("Sedes educativas en MMI≥7", format_number_es(tot.edu_mmi7p)),
    ]
    # Se publican por separado a proposito: no es lo mismo que quede cortada
    # una troncal que una calle de barrio, y la red principal es ademas la
    # cifra comparable con las estadisticas viales oficiales. Un solo numero
    # que las sume esconde las dos cosas.
    if tot.road_km_principal_mmi7p > 0:
        local = max(tot.road_km_mmi7p - tot.road_km_principal_mmi7p, 0.0)
        filas.append(
            (
                "Vias primarias y secundarias en MMI≥7",
                format_count_prose(tot.road_km_principal_mmi7p) + " km",
            )
        )
        filas.append(("Vias locales en MMI≥7", format_count_prose(local) + " km"))
    else:
        filas.append(("Kilometros de via en MMI≥7", format_count_prose(tot.road_km_mmi7p) + " km"))
    if tot.built_m2_mmi7p > 0:
        km2 = tot.built_m2_mmi7p / 1_000_000.0
        filas.append(("Superficie construida en MMI≥7", f"{format_number_es(km2, 1)} km²"))
    lineas = ["| Indicador | Estimado |", "|---|---:|"]
    lineas += [f"| {nombre} | {valor} |" for nombre, valor in filas]
    return "\n".join(lineas) + _nota_superficie(report)


#: Superficie media de una edificacion, en m², para contrastar el conteo de
#: Overture con la superficie que ve el satelite. Es un orden de magnitud
#: deliberadamente conservador: sirve para detectar un hueco de mapeo grande,
#: no para estimar edificaciones.
M2_POR_EDIFICACION = 100.0

#: A partir de que proporcion se considera que falta mapeo. 1,5 significa que el
#: satelite ve un 50 % mas de lo que explicarian las edificaciones registradas.
UMBRAL_HUECO_MAPEO = 1.5


def _nota_superficie(report: Report) -> str:
    """Advierte cuando el satelite ve mucho mas construido de lo mapeado.

    Es la unica forma que tiene el reporte de decir "esta cifra se queda corta"
    sin callarse ni inventar. El hueco de OSM se concentra en asentamientos
    informales y zona rural dispersa, o sea en la poblacion mas expuesta: darlo
    por bueno seria publicar una cobertura que no existe (§6.4).
    """
    tot = report.totales
    if tot.built_m2_mmi7p <= 0 or tot.bld_mmi7p <= 0:
        return ""
    esperado = tot.bld_mmi7p * M2_POR_EDIFICACION
    if tot.built_m2_mmi7p < esperado * UMBRAL_HUECO_MAPEO:
        return ""
    veces = tot.built_m2_mmi7p / esperado
    return (
        f"\n\nEl satelite detecta **{format_number_es(veces, 1)} veces** mas superficie "
        f"construida de la que explicarian las {format_count_prose(tot.bld_mmi7p)} "
        f"edificaciones registradas. La diferencia suele ser asentamiento informal o "
        f"zona rural dispersa sin mapear: **el conteo de edificaciones se queda corto "
        f"ahi, y la superficie construida no**."
    )


def _tabla_municipios(report: Report) -> str:
    lineas = [
        "| # | Municipio | DIVIPOLA | MMI max | Poblacion MMI≥7 |",
        "|---:|---|---|---:|---:|",
    ]
    for i, m in enumerate(report.top_municipios[:TOP_ADM2_COUNT], start=1):
        lineas.append(
            f"| {i} | {m.nombre} | `{m.adm2_id}` | "
            f"{format_number_es(m.mmi_max, 1)} | {format_count_prose(m.pop_mmi7p)} |"
        )
    return "\n".join(lineas)


def _seccion_ground_failure(report: Report) -> str:
    """Seccion de falla de terreno; se omite con nota si no hay producto (G3)."""
    if report.inputs.groundfailure_version == 0:
        return (
            "## Deslizamiento y licuefaccion\n\n"
            "USGS no ha publicado el producto *Ground Failure* para este evento. "
            "La seccion se omite; el reporte se re-emite automaticamente si aparece."
        )
    tot = report.totales
    return (
        "## Deslizamiento y licuefaccion\n\n"
        f"- Poblacion en celdas con probabilidad **alta de deslizamiento**: "
        f"{format_count_prose(tot.pop_ls_alta)}\n"
        f"- Poblacion en celdas con probabilidad **alta de licuefaccion**: "
        f"{format_count_prose(tot.pop_lq_alta)}\n\n"
        "Fuente: producto *Ground Failure* de USGS "
        f"(v{report.inputs.groundfailure_version}), dominio publico."
    )


def _seccion_incertidumbre(report: Report) -> str:
    inc = report.incertidumbre
    lineas = [
        "## Incertidumbre y calidad",
        "",
        f"Discrepancia entre GHS-POP y WorldPop en el area afectada: "
        f"**{format_number_es(inc.pop_discrepancia_pct, 1)} %**.",
    ]
    if inc.notas:
        lineas += ["", *[f"- {nota}" for nota in inc.notas]]
    return "\n".join(lineas)


def _seccion_descargas(report: Report) -> str:
    d = report.descargas
    enlaces = [
        ("GeoParquet (celdas H3 r8)", d.geoparquet),
        ("PMTiles (visor)", d.pmtiles),
        ("CSV por municipio", d.csv_adm2),
        ("Mapa PNG", d.mapa_png),
    ]
    disponibles = [f"- [{nombre}]({url})" for nombre, url in enlaces if url]
    if not disponibles:
        return ""
    return "## Descargas\n\n" + "\n".join(disponibles)


def _seccion_procedencia(report: Report) -> str:
    return (
        "## Procedencia\n\n"
        f"- ShakeMap consumido: **v{report.inputs.shakemap_version}**\n"
        f"- Ground Failure consumido: **v{report.inputs.groundfailure_version}**\n"
        f"- Manifest de exposicion: `{report.inputs.exposure_manifest}`\n"
        f"- Pipeline: `{report.pipeline_version}` · Generado: {report.generado_utc}"
    )
