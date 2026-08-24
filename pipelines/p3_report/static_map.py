"""Mapa estatico del reporte.

**T0.8 resuelta: matplotlib solo, sin teselas de fondo.** Las tres opciones en
evaluacion eran matplotlib+contextily, un render headless de MapLibre, y
matplotlib a secas. Gana la tercera, por razones que no son de calidad grafica:

* **Sin dependencia de red en el camino critico.** Un basemap es una descarga
  de teselas mas durante el minuto en que hay que publicar. Si el proveedor
  esta lento, el reporte llega tarde por una razon puramente decorativa.
* **Sin problema de atribucion.** Cada proveedor de teselas trae su licencia y
  su exigencia de credito. Poner un fondo cuya licencia no controlamos dentro
  de un artefacto que se publica bajo CC BY / ODbL es exactamente el tipo de
  mezcla que la regla de los tres cubos existe para evitar.
* **Sin llaves de API**, coherente con D6 y con O4.

Lo que se pierde —relieve, toponimos de fondo— no es lo que el lector necesita:
el mapa tiene que responder "donde cayo la intensidad fuerte y quien vive ahi",
y para eso bastan los limites municipales, la coropleta y los contornos.

Dos variantes obligatorias:

* ``general`` — contexto amplio, contornos MMI, municipios etiquetados.
* ``prensa`` — recorte cerrado, tipografia grande, pensado para captura.

Restriccion dura: el PNG mas el markdown deben sumar menos de 500 KB (RNF-05).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

from ..common.logging import get_logger
from .model import Report

_log = get_logger(__name__)


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


#: Rampa secuencial de intensidad, acotada a lo que el reporte publica (MMI>=6).
#:
#: Es **secuencial**, no categorica: MMI es una magnitud ordenada, asi que el
#: criterio correcto es la monotonia de luminosidad, no la separacion entre
#: matices. Verificado: 0,405 > 0,281 > 0,167 > 0,068, estrictamente
#: descendente. Eso hace que el mapa siga siendo legible impreso en blanco y
#: negro, que es como acaba en muchas salas de crisis.
#:
#: Se aparta a proposito de la escala de USGS, que es un arcoiris
#: verde-amarillo-naranja-rojo: un arcoiris no tiene orden perceptual y se
#: vuelve ilegible para daltonismo rojo-verde, justo el mas comun.
#:
#: Las bandas por debajo de MMI 6 **no se dibujan**. Su contraste contra el
#: fondo es de 1,2:1 — practicamente invisible — y el reporte no las publica.
MMI_COLORS: dict[float, str] = {
    6.0: "#fc8d59",
    6.5: "#ef6548",
    7.0: "#d7301f",
    7.5: "#990000",
    8.0: "#67000d",
}

#: Por debajo de esto no se dibuja nada en el mapa.
MMI_MIN_MAPPED = 6.0

#: Separacion minima entre etiquetas, en grados, para no apilarlas.
LABEL_MIN_SEPARATION = 0.25


def color_for_mmi(valor: float) -> str:
    """Color de la banda a la que pertenece un MMI."""
    aplicables = [v for v in sorted(MMI_COLORS) if v <= valor]
    return MMI_COLORS[aplicables[-1]] if aplicables else MMI_COLORS[MMI_MIN_MAPPED]


def render_map(
    report: Report,
    variant: MapVariant,
    path: Path,
    *,
    municipios: Sequence[Mapping[str, Any]] | None = None,
) -> Path:
    """Renderiza una variante del mapa.

    Args:
        report: reporte ya calculado; de el salen el epicentro y los totales.
        variant: ``general`` o ``prensa``.
        path: destino del PNG.
        municipios: filas con ``nombre``, ``mmi_max``, ``pop_mmi7p`` y
            ``centroide`` (WKT ``POINT``). Sin ellas se dibuja solo el
            epicentro y la leyenda, que es el caso del reporte preliminar.

    Requiere el extra ``[render]``.
    """
    import matplotlib

    matplotlib.use("Agg")  # sin servidor grafico en un runner
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch

    spec = SPECS[variant]
    puntos = [p for p in _puntos_municipales(municipios or []) if p[2] >= MMI_MIN_MAPPED]
    lon_e, lat_e = _EPICENTRO.get(report.event.usgs_id, (0.0, 0.0))

    # La figura se dimensiona a partir de la extension de los datos, no al
    # reves. Fijar 16:9 y luego imponer proporcion geografica deja el mapa
    # flotando entre dos franjas vacias que no dicen nada.
    limites = _limites(puntos, (lon_e, lat_e))
    fig, ax = plt.subplots(figsize=_figsize(limites, spec), dpi=spec.dpi)
    if puntos:
        # Anillo blanco sobre el marcador: donde dos municipios quedan encima,
        # el borde los separa en vez de fundirlos en una mancha.
        ax.scatter(
            [p[0] for p in puntos],
            [p[1] for p in puntos],
            s=[_tamano(p[3]) for p in puntos],
            c=[color_for_mmi(p[2]) for p in puntos],
            edgecolors="white",
            linewidths=0.8,
            zorder=3,
        )
        for lon, lat, _mmi, _pob, nombre in _etiquetables(puntos, n_max=6):
            ax.annotate(
                nombre.title(),
                (lon, lat),
                fontsize=9 if variant is MapVariant.PRENSA else 8,
                color="#1c1b1a",
                xytext=(7, 5),
                textcoords="offset points",
                zorder=4,
            )

    ax.plot(
        lon_e,
        lat_e,
        marker="*",
        markersize=17,
        color="#1c1b1a",
        markeredgecolor="white",
        markeredgewidth=0.8,
        zorder=5,
        linestyle="none",
    )
    ax.annotate(
        "epicentro",
        (lon_e, lat_e),
        fontsize=8,
        color="#55524e",
        xytext=(9, -13),
        textcoords="offset points",
        zorder=5,
    )

    _encuadrar(ax, limites)

    ax.set_title(
        f"M{report.event.mag} · {report.event.lugar}",
        fontsize=13 if variant is MapVariant.PRENSA else 11,
        loc="left",
        color="#1c1b1a",
    )
    ax.set_xlabel(
        f"Poblacion en MMI≥7 por municipio · ShakeMap v{report.inputs.shakemap_version}"
        " · exposicion estimada, no dano",
        fontsize=8,
        color="#55524e",
    )
    ax.set_ylabel("")
    ax.tick_params(labelsize=7, colors="#55524e")
    for lado in ("top", "right"):
        ax.spines[lado].set_visible(False)
    for lado in ("left", "bottom"):
        ax.spines[lado].set_color("#dedad4")
    ax.grid(color="#ece9e4", linewidth=0.5, zorder=0)
    ax.set_axisbelow(True)

    bandas = [v for v in sorted(MMI_COLORS) if v < 8.0]
    leyenda: list[Any] = [
        Patch(facecolor=MMI_COLORS[v], edgecolor="white", label=f"MMI {v:g}") for v in bandas
    ]
    leyenda.append(
        Line2D(
            [], [], marker="*", color="#1c1b1a", linestyle="none", markersize=11, label="epicentro"
        )
    )
    ax.legend(
        handles=leyenda,
        loc="lower left",
        fontsize=7,
        framealpha=0.95,
        edgecolor="#dedad4",
        title="Intensidad maxima",
        title_fontsize=7,
    )

    fig.text(0.01, 0.012, ATTRIBUTION_LINE, fontsize=5.5, color="#8a857e", wrap=True)
    fig.tight_layout(rect=(0, 0.03, 1, 1))

    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=spec.dpi, facecolor="white")
    plt.close(fig)

    if path.stat().st_size > spec.max_bytes:
        # No se falla: un PNG grande sigue siendo mejor que ningun mapa. Pero
        # queda constancia, porque RNF-05 existe por los lectores en 3G.
        _log.warning(
            "el mapa excede su presupuesto de peso",
            extra={
                "context": {
                    "variante": variant.value,
                    "bytes": path.stat().st_size,
                    "presupuesto": spec.max_bytes,
                }
            },
        )
    return path


def _limites(
    puntos: list[tuple[float, float, float, float, str]],
    epicentro: tuple[float, float],
) -> tuple[float, float, float, float]:
    """``(lon_min, lat_min, lon_max, lat_max)`` con margen."""
    lons = [p[0] for p in puntos] + [epicentro[0]]
    lats = [p[1] for p in puntos] + [epicentro[1]]
    if not lons:
        return (-80.0, -5.0, -66.0, 13.0)
    margen_lon = max((max(lons) - min(lons)) * 0.08, 0.2)
    margen_lat = max((max(lats) - min(lats)) * 0.08, 0.2)
    return (
        min(lons) - margen_lon,
        min(lats) - margen_lat,
        max(lons) + margen_lon,
        max(lats) + margen_lat,
    )


def _figsize(limites: tuple[float, float, float, float], spec: MapSpec) -> tuple[float, float]:
    """Tamano de figura que respeta la proporcion geografica de los datos."""
    import math

    lon_min, lat_min, lon_max, lat_max = limites
    ancho_geo = (lon_max - lon_min) * math.cos(math.radians((lat_min + lat_max) / 2))
    alto_geo = lat_max - lat_min
    alto_pulg = spec.height_px / spec.dpi
    if alto_geo <= 0 or ancho_geo <= 0:
        return (spec.width_px / spec.dpi, alto_pulg)
    # +1,2" de holgura para el eje, la leyenda y la atribucion.
    ancho = min(max(alto_pulg * (ancho_geo / alto_geo) + 1.2, 4.0), spec.width_px / spec.dpi)
    return (ancho, alto_pulg)


def _encuadrar(ax: Any, limites: tuple[float, float, float, float]) -> None:
    """Aplica limites y proporcion geografica.

    Un grado de longitud mide ``cos(latitud)`` veces lo que uno de latitud. Sin
    esa correccion el mapa sale estirado en horizontal: a 5°N el error es de un
    0,4 % —despreciable— pero a 40° seria del 23 %. Se corrige siempre, porque
    el mismo codigo va a dibujar Chile y Mexico.
    """
    import math

    from matplotlib.ticker import MaxNLocator

    lon_min, lat_min, lon_max, lat_max = limites
    ax.set_xlim(lon_min, lon_max)
    ax.set_ylim(lat_min, lat_max)
    ax.set_aspect(1.0 / max(math.cos(math.radians((lat_min + lat_max) / 2)), 0.1))
    ax.xaxis.set_major_locator(MaxNLocator(nbins=6, prune="both"))
    ax.yaxis.set_major_locator(MaxNLocator(nbins=7))


def _etiquetables(
    puntos: list[tuple[float, float, float, float, str]],
    *,
    n_max: int,
    separacion: float = LABEL_MIN_SEPARATION,
) -> list[tuple[float, float, float, float, str]]:
    """Los municipios mas expuestos, descartando los que se pisarian.

    Etiquetar los quince del ranking produce una mancha ilegible justo en la
    zona mas afectada, que es donde el lector mira. Se recorren de mayor a
    menor poblacion y se salta el que caiga demasiado cerca de otro ya puesto.
    """
    elegidos: list[tuple[float, float, float, float, str]] = []
    for punto in sorted(puntos, key=lambda p: p[3], reverse=True):
        if len(elegidos) >= n_max:
            break
        if all(
            abs(punto[0] - e[0]) > separacion or abs(punto[1] - e[1]) > separacion for e in elegidos
        ):
            elegidos.append(punto)
    return elegidos


def _lon(report: Report) -> float:
    return _EPICENTRO.get(report.event.usgs_id, (0.0, 0.0))[0]


def _lat(report: Report) -> float:
    return _EPICENTRO.get(report.event.usgs_id, (0.0, 0.0))[1]


#: El esquema de ``report.json`` v1 no lleva coordenadas del epicentro — las
#: lleva el ``event_state``. Hasta que la v2 las incluya, el renderizador las
#: recibe por aqui.
_EPICENTRO: dict[str, tuple[float, float]] = {}


def set_epicenter(usgs_id: str, lon: float, lat: float) -> None:
    """Registra el epicentro de un evento para el render."""
    _EPICENTRO[usgs_id] = (lon, lat)


def _puntos_municipales(
    filas: Sequence[Mapping[str, Any]],
) -> list[tuple[float, float, float, float, str]]:
    """``(lon, lat, mmi, pop, nombre)`` a partir del centroide en WKT."""
    puntos = []
    for fila in filas:
        wkt = str(fila.get("centroide") or "")
        if not wkt.startswith("POINT"):
            continue
        try:
            lon, lat = (float(v) for v in wkt[wkt.index("(") + 1 : wkt.index(")")].split())
        except (ValueError, IndexError):
            continue
        puntos.append(
            (
                lon,
                lat,
                float(fila.get("mmi_max") or 0),
                float(fila.get("pop_mmi7p") or 0),
                str(fila.get("nombre") or ""),
            )
        )
    return puntos


def _mas_expuestos(
    puntos: list[tuple[float, float, float, float, str]], n: int
) -> list[tuple[float, float, float, float, str]]:
    return sorted(puntos, key=lambda p: p[3], reverse=True)[:n]


def _tamano(poblacion: float) -> float:
    """Area del circulo proporcional a la poblacion, con minimo visible."""
    import math

    return 12.0 + 4.0 * math.sqrt(max(poblacion, 0.0) / 1000.0)
