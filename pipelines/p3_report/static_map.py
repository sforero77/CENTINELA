"""Mapa estatico del reporte.

**T0.8 resuelta: matplotlib solo, sin teselas de fondo.** Las tres opciones en
evaluacion eran matplotlib+contextily, un render headless de MapLibre, y
matplotlib a secas. Gana la tercera, por razones que no son de calidad grafica:

* **Sin dependencia de red en el camino critico.** Un basemap es una descarga
  de teselas más durante el minuto en que hay que publicar. Si el proveedor
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

Restriccion dura: el PNG más el markdown deben sumar menos de 500 KB (RNF-05).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

from ..common.formatting import format_count_prose, format_number_es, titulo_es
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


#: Las dos variantes tenian el mismo alto, la misma tipografia y el mismo
#: contenido: solo cambiaba el ancho maximo, y con `tight_layout` recortando al
#: dato ni eso se notaba. Los dos PNG publicados de cada evento salian
#: practicamente identicos, ofrecidos como dos descargas distintas.
#:
#: Ahora `general` es la del panel y el markdown —compacta, para leerse dentro de
#: otra cosa— y `prensa` es 16:9 con tipografia grande, que es lo que se pega en
#: una nota o se proyecta en una sala.
SPECS: dict[MapVariant, MapSpec] = {
    MapVariant.GENERAL: MapSpec(MapVariant.GENERAL, 1100, 900, 110),
    MapVariant.PRENSA: MapSpec(MapVariant.PRENSA, 1920, 1080, 140),
}

#: Atribucion obligatoria al pie de todo mapa (§2.4 regla 2).
ATTRIBUTION_LINE = (
    "Intensidad: USGS ShakeMap (dominio público) · "
    "Población: GHS-POP, JRC/Comisión Europea · "
    "Edificaciones y vías: Overture Maps, © OpenStreetMap contributors (ODbL) · "
    "CENTINELA — exposición estimada, no daño"
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
#:
#: **Faltaba la banda 8,5** y el evento de Catia La Mar la alcanza: sin ella,
#: `color_for_mmi` devolvia el color de 8,0 para las dos y el mapa no distinguia
#: la sacudida mas fuerte que ha publicado el sistema. Al anadirla, toda la
#: rampa se desplaza un paso hacia el claro. Luminancias relativas resultantes:
#: 0,581 > 0,405 > 0,281 > 0,167 > 0,096 > 0,045, estrictamente descendente.
#:
#: Es la misma rampa que usa el visor (`site/assets/app.js`): el mismo evento no
#: puede salir de dos colores distintos segun se mire el PNG o la pagina.
MMI_COLORS: dict[float, str] = {
    6.0: "#fdbb84",
    6.5: "#fc8d59",
    7.0: "#ef6548",
    7.5: "#d7301f",
    8.0: "#b30000",
    8.5: "#7f0000",
}

#: Por debajo de esto no se dibuja nada en el mapa.
MMI_MIN_MAPPED = 6.0

#: Separacion minima entre etiquetas, en grados, para no apilarlas.
LABEL_MIN_SEPARATION = 0.25


def banda_de_mmi(valor: float) -> float:
    """Banda de la rampa a la que pertenece un MMI."""
    aplicables = [v for v in sorted(MMI_COLORS) if v <= valor]
    return aplicables[-1] if aplicables else MMI_MIN_MAPPED


def color_for_mmi(valor: float) -> str:
    """Color de la banda a la que pertenece un MMI."""
    return MMI_COLORS[banda_de_mmi(valor)]


def render_map(
    report: Report,
    variant: MapVariant,
    path: Path,
    *,
    municipios: Sequence[Mapping[str, Any]] | None = None,
    contornos: Mapping[str, Any] | None = None,
) -> Path:
    """Renderiza una variante del mapa.

    Args:
        report: reporte ya calculado; de el salen el epicentro y los totales.
        variant: ``general`` o ``prensa``.
        path: destino del PNG.
        municipios: filas con ``nombre``, ``mmi_max``, ``pop_mmi7p`` y
            ``centroide`` (WKT ``POINT``). Sin ellas se dibuja solo el
            epicentro y la leyenda, que es el caso del reporte preliminar.
        contornos: el GeoJSON de ``contornos.json``, si esta. Es lo que
            convierte esto en un mapa y no en una dispersion: sin el, el lector
            ve puntos de colores flotando sobre una reticula de grados
            decimales y no tiene forma de saber que esta mirando. Se pasa ya
            leido para no meter E/S aqui, y es opcional porque los reportes
            emitidos antes de que ese fichero existiera no lo traen.

    Requiere el extra ``[render]``. **No** requiere ``[geo]``: la forma del
    evento sale de los contornos, que son coordenadas planas en el JSON. Meter
    ``h3`` aqui para dibujar la malla ataria el render del reporte al extra
    pesado, y este modulo existe para no depender de nada que pueda faltar.
    """
    import matplotlib

    matplotlib.use("Agg")  # sin servidor grafico en un runner
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch

    spec = SPECS[variant]
    puntos = [p for p in _puntos_municipales(municipios or []) if p[2] >= MMI_MIN_MAPPED]
    epicentro = _epicentro(report)

    # La figura se dimensiona a partir de la extension de los datos, no al
    # reves. Fijar 16:9 y luego imponer proporcion geografica deja el mapa
    # flotando entre dos franjas vacias que no dicen nada.
    limites = _limites(puntos, epicentro)
    fig, ax = plt.subplots(figsize=_figsize(limites, spec), dpi=spec.dpi)

    # LA FORMA DEL EVENTO, DEBAJO DE TODO.
    #
    # Es lo que faltaba para que esto fuera un mapa. Sin ella el lector veia
    # circulos de colores sobre una reticula rotulada en grados decimales
    # —"-79.5", "0.5"— y no habia manera de saber que pais era ni donde estaba
    # el mar. Con los contornos rellenos, la mancha del ShakeMap da la silueta
    # que el ojo reconoce y cada municipio queda dentro de su franja.
    _dibujar_contornos(ax, contornos)

    if puntos:
        # UNA VARIABLE POR CANAL.
        #
        # Los circulos iban coloreados por intensidad **sobre** un fondo que
        # ahora ya es la intensidad: un municipio en MMI 8 salia rojo oscuro
        # encima de la banda roja oscura y desaparecia. El color pasa a ser del
        # fondo —donde cayo la sacudida— y el tamano del circulo queda como
        # unica variable del simbolo: cuanta gente quedo dentro. Que es la
        # pregunta del mapa.
        #
        # Anillo blanco sobre el marcador: donde dos municipios quedan encima,
        # el borde los separa en vez de fundirlos en una mancha.
        ax.scatter(
            [p[0] for p in puntos],
            [p[1] for p in puntos],
            s=[_tamano(p[3]) for p in puntos],
            c="#1c1b1a",
            alpha=0.82,
            edgecolors="white",
            linewidths=0.9,
            zorder=3,
        )
        for lon, lat, _mmi, _pob, nombre in _etiquetables(puntos, n_max=6):
            ax.annotate(
                titulo_es(nombre),
                (lon, lat),
                fontsize=9 if variant is MapVariant.PRENSA else 8,
                color="#1c1b1a",
                xytext=(7, 5),
                textcoords="offset points",
                zorder=4,
            )

    if epicentro is not None:
        ax.plot(
            epicentro[0],
            epicentro[1],
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
            epicentro,
            fontsize=8,
            color="#55524e",
            xytext=(9, -13),
            textcoords="offset points",
            zorder=5,
        )

    _encuadrar(ax, limites)

    prensa = variant is MapVariant.PRENSA
    escala_fuente = 9 if prensa else 7

    # EL TITULAR Y SU SUBTITULO, LOS DOS EN LA FIGURA.
    #
    # `ax.set_title` los pisaba: dos llamadas seguidas dejan solo la segunda, y
    # el mapa salio publicado sin decir de que sismo era. Y el subtitulo vivia
    # antes en `set_xlabel` —el sitio donde va la unidad del eje—, debajo de una
    # fila de grados decimales, asi que se leia como si esos numeros fueran
    # poblacion.
    fig.text(
        0.012,
        0.975,
        f"M{format_number_es(report.event.mag, 1)} · {report.event.lugar}",
        fontsize=19 if prensa else 12,
        color="#1c1b1a",
        va="top",
        ha="left",
        weight="bold",
    )
    fig.text(
        0.012,
        0.932 if prensa else 0.925,
        f"Población en MMI≥7 por municipio · ShakeMap v{report.inputs.shakemap_version}"
        " · exposición estimada, no daño",
        fontsize=11 if prensa else 8,
        color="#55524e",
        va="top",
        ha="left",
    )
    ax.set_xlabel("")
    ax.set_ylabel("")

    # FUERA LOS GRADOS DECIMALES.
    #
    # Nadie lee "-79.5" en un mapa de prensa, y una reticula de coordenadas
    # sugiere una precision de posicion que este producto no publica. Lo que
    # hace falta —cuanto mide esto, y hacia donde esta el norte— lo pone
    # `_barra_de_escala`.
    ax.set_axis_off()
    # Un marco fino en su lugar. Sin ejes ni marco, el recorte de las bandas
    # queda como un corte al aire y el mapa parece una imagen rota.
    from matplotlib.patches import Rectangle

    ax.add_patch(
        Rectangle(
            (limites[0], limites[1]),
            limites[2] - limites[0],
            limites[3] - limites[1],
            fill=False,
            edgecolor="#dedad4",
            linewidth=1.0,
            zorder=7,
        )
    )
    _barra_de_escala(ax, limites, fuente=escala_fuente)

    # Las bandas presentes, no una lista fija. La version anterior rotulaba
    # siempre MMI 6 / 6,5 / 7 / 7,5: en el evento de Catia La Mar, que llega a
    # 8,5, la leyenda se quedaba corta por dos clases, y en cualquier evento que
    # no pase de 7 sobraban dos muestras de color que no estaban en el mapa.
    bandas = sorted({banda_de_mmi(p[2]) for p in puntos})
    leyenda: list[Any] = [
        Patch(facecolor=MMI_COLORS[v], edgecolor="white", alpha=0.55, label=f"MMI {v:g}")
        for v in bandas
    ]
    if epicentro is not None:
        leyenda.append(
            Line2D(
                [],
                [],
                marker="*",
                color="#1c1b1a",
                linestyle="none",
                markersize=11,
                label="epicentro",
            )
        )
    if leyenda:
        # Arriba a la derecha: abajo a la izquierda es ahora de la barra de
        # escala, y la leyenda se le montaba encima.
        primera = ax.legend(
            handles=leyenda,
            loc="upper right",
            fontsize=escala_fuente,
            framealpha=0.95,
            edgecolor="#dedad4",
            # Ya no rotula el color de los circulos —que son neutros— sino el
            # del fondo: las franjas del ShakeMap.
            title="Intensidad (ShakeMap)",
            title_fontsize=escala_fuente,
        )
        ax.add_artist(primera)

    # Y la escala de tamano, que es la variable principal del mapa.
    tamanos = _leyenda_de_tamano(puntos, fuente=escala_fuente)
    if tamanos:
        ax.legend(
            handles=tamanos,
            loc="lower right",
            fontsize=escala_fuente,
            framealpha=0.95,
            edgecolor="#dedad4",
            title="Personas expuestas",
            title_fontsize=escala_fuente,
            labelspacing=1.1,
            borderpad=0.9,
        )

    fig.text(
        0.01,
        0.012,
        ATTRIBUTION_LINE,
        fontsize=7 if prensa else 5.5,
        color="#8a857e",
        wrap=True,
    )
    fig.tight_layout(rect=(0, 0.035, 1, 0.905 if prensa else 0.9))

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


def _anillos(geometria: Mapping[str, Any]) -> list[list[tuple[float, float]]]:
    """Los anillos cerrados de una geometria de contorno, para poder rellenarla.

    ShakeMap publica sus contornos como **lineas**, no como areas: cada banda es
    un `MultiLineString` de lazos alrededor del epicentro. El visor las dibuja
    tal cual, encima de la malla de hexagonos, y ahi tiene sentido. El PNG no
    tiene malla debajo: si dibujara solo lineas seguiria sin haber una forma que
    el ojo reconozca, que es justo lo que le faltaba.

    Rellenarlas es correcto porque los lazos vienen cerrados —comprobado sobre
    los contornos publicados: los nueve, y todos sus lazos secundarios— y porque
    las bandas estan anidadas, asi que pintar de menor a mayor reproduce
    exactamente la estructura sin recortar geometria.

    Un lazo **abierto** se descarta: cerrarlo a la fuerza inventaria area
    atravesando el mapa en linea recta, que es peor que no dibujarlo.
    """
    tipo = geometria.get("type")
    coords = geometria.get("coordinates") or []
    if tipo == "Polygon":
        # Solo el exterior: un agujero de un contorno es una isla de intensidad
        # menor, y la banda de encima ya vuelve a pintar por su cuenta.
        lazos = [anillo[0] for anillo in [coords] if anillo]
    elif tipo == "MultiPolygon":
        lazos = [poligono[0] for poligono in coords if poligono]
    elif tipo == "LineString":
        lazos = [coords]
    elif tipo == "MultiLineString":
        lazos = list(coords)
    else:
        return []

    anillos: list[list[tuple[float, float]]] = []
    for lazo in lazos:
        if len(lazo) < 4:
            continue
        puntos = [(float(x), float(y)) for x, y, *_ in lazo]
        if puntos[0] != puntos[-1]:
            continue
        anillos.append(puntos)
    return anillos


def _dibujar_contornos(ax: Any, contornos: Mapping[str, Any] | None) -> None:
    """Pinta las bandas de intensidad como areas, de la mas suave a la mas fuerte.

    De menor a mayor **a proposito**: los contornos de ShakeMap son anidados
    —el de MMI 8 esta dentro del de 7— asi que pintar en ese orden deja cada
    banda encima de la anterior sin tener que recortar geometria.
    """
    if not contornos:
        return
    from matplotlib.patches import Polygon as ParchePoligono

    rasgos = [
        (float(r.get("properties", {}).get("mmi", 0)), r.get("geometry") or {})
        for r in contornos.get("features", [])
    ]
    # Las bandas por debajo de MMI 6 no se dibujan, por la misma razon que en la
    # rampa: su contraste contra el fondo es de 1,2:1 y el reporte no las cita.
    dibujables = sorted(
        ((mmi, geom) for mmi, geom in rasgos if mmi >= MMI_MIN_MAPPED and geom),
        key=lambda par: par[0],
    )
    for mmi, geometria in dibujables:
        color = color_for_mmi(mmi)
        for anillo in _anillos(geometria):
            ax.add_patch(
                ParchePoligono(
                    anillo,
                    closed=True,
                    facecolor=color,
                    edgecolor="white",
                    linewidth=0.4,
                    # Translucido: los circulos de municipio van encima y tienen
                    # que seguir leyendose sobre el rojo oscuro de MMI 8.
                    alpha=0.55,
                    zorder=1,
                )
            )


def _barra_de_escala(ax: Any, limites: tuple[float, float, float, float], *, fuente: int) -> None:
    """Una barra en kilometros, y el norte.

    Los ejes en grados decimales —"-80.5", "1.0"— no los lee nadie fuera de un
    SIG, y sin escala no hay forma de juzgar una distancia en un mapa cuyo
    encuadre cambia con cada evento. Se quitan los ejes y se pone lo que un
    lector necesita: cuanto mide esto y hacia donde esta el norte.
    """
    import math

    lon_min, lat_min, lon_max, lat_max = limites
    lat_media = (lat_min + lat_max) / 2
    km_por_grado = 111.32 * max(math.cos(math.radians(lat_media)), 0.05)
    ancho_km = (lon_max - lon_min) * km_por_grado
    if ancho_km <= 0:
        return

    # Una longitud redonda que ocupe alrededor de un cuarto del ancho: 1, 2 o 5
    # por una potencia de diez. Un "137 km" de barra no se lee de un vistazo.
    objetivo = ancho_km / 4
    exponente = math.floor(math.log10(objetivo)) if objetivo > 0 else 0
    base = 10**exponente
    for paso in (1, 2, 5, 10):
        largo_km = paso * base
        if largo_km >= objetivo:
            break
    largo_grados = largo_km / km_por_grado

    x0 = lon_min + (lon_max - lon_min) * 0.045
    y0 = lat_min + (lat_max - lat_min) * 0.055
    ax.plot(
        [x0, x0 + largo_grados],
        [y0, y0],
        color="#1c1b1a",
        linewidth=2.2,
        solid_capstyle="butt",
        zorder=6,
    )
    tope = y0 + (lat_max - lat_min) * 0.012
    for x in (x0, x0 + largo_grados):
        ax.plot([x, x], [y0, tope], color="#1c1b1a", linewidth=2.2, zorder=6)
    ax.annotate(
        f"{format_number_es(largo_km)} km",
        (x0 + largo_grados / 2, y0),
        fontsize=fuente,
        color="#1c1b1a",
        ha="center",
        va="bottom",
        xytext=(0, 4),
        textcoords="offset points",
        zorder=6,
    )

    # El norte, encima del extremo izquierdo de la barra. La proyeccion es
    # plate carree con la proporcion corregida, asi que el norte es exactamente
    # hacia arriba y una flecha recta no miente.
    #
    # Estuvo abajo a la derecha y se metia dentro de la leyenda de tamano, que
    # vive en esa esquina: la flecha salia atravesando la palabra "expuestas".
    # Aqui comparte esquina con la escala, que es su familia —las dos dicen como
    # se mide este mapa— y no tapa nada.
    alto = lat_max - lat_min
    ax.annotate(
        "",
        xy=(x0, y0 + alto * 0.155),
        xytext=(x0, y0 + alto * 0.055),
        arrowprops={"arrowstyle": "-|>", "color": "#1c1b1a", "linewidth": 1.2},
        zorder=6,
    )
    ax.annotate(
        "N",
        (x0, y0 + alto * 0.16),
        fontsize=fuente + 1,
        color="#1c1b1a",
        ha="center",
        va="bottom",
        zorder=6,
    )


def _leyenda_de_tamano(
    puntos: list[tuple[float, float, float, float, str]], *, fuente: int
) -> list[Any]:
    """Tres circulos de referencia para el tamano de los marcadores.

    El area del circulo **es** la variable principal de este mapa —cuanta gente
    quedo dentro— y no habia forma de traducirla a una cifra: la unica leyenda
    era la de color. Un simbolo proporcional sin escala de tamano es un simbolo
    decorativo.
    """
    from matplotlib.lines import Line2D

    if not puntos:
        return []
    mayor = max(p[3] for p in puntos)
    referencias: list[float] = [
        float(v) for v in (10_000, 100_000, 1_000_000) if v <= max(mayor, 1.0)
    ]
    # Un evento pequeno puede no llegar ni a la primera referencia: se rotula con
    # su propio maximo, que sigue siendo una escala util.
    if not referencias:
        referencias = [mayor]
    return [
        Line2D(
            [],
            [],
            marker="o",
            linestyle="none",
            # El mismo gris tinta que los marcadores del mapa: una leyenda de
            # tamano con otro color no rotula lo que hay dibujado.
            markerfacecolor="#1c1b1a",
            markeredgecolor="white",
            markeredgewidth=0.9,
            alpha=0.82,
            # `_tamano` da area en puntos²; `markersize` es diametro en puntos.
            markersize=(_tamano(v) ** 0.5),
            label=format_count_prose(v),
        )
        for v in referencias
    ]


def _limites(
    puntos: list[tuple[float, float, float, float, str]],
    epicentro: tuple[float, float] | None,
) -> tuple[float, float, float, float]:
    """``(lon_min, lat_min, lon_max, lat_max)`` con margen."""
    lons = [p[0] for p in puntos] + ([epicentro[0]] if epicentro else [])
    lats = [p[1] for p in puntos] + ([epicentro[1]] if epicentro else [])
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
    zona más afectada, que es donde el lector mira. Se recorren de mayor a
    menor población y se salta el que caiga demasiado cerca de otro ya puesto.
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


def _epicentro(report: Report) -> tuple[float, float] | None:
    """Coordenadas del epicentro, o ``None`` si el reporte no las trae.

    Antes salian de un registro de modulo, ``_EPICENTRO``, que se rellenaba con
    ``set_epicenter()`` — **una funcion que no llamaba nadie**. El registro
    estaba siempre vacio y el ``.get`` caia en su valor por defecto, ``(0, 0)``:
    los tres reportes publicados llevan la estrella del epicentro clavada en el
    golfo de Guinea, con los ejes en decimas de grado alrededor del meridiano
    cero. Mismo patron que la P1 preliminar y que las capas del activo: una
    funcion escrita no es una funcion conectada.

    ``report.event`` lleva ``lon`` y ``lat`` desde que se anadieron para el
    visor, asi que la via indirecta ya no hacia falta para nada.
    """
    lon = float(report.event.lon or 0.0)
    lat = float(report.event.lat or 0.0)
    return (lon, lat) if lon or lat else None


def _puntos_municipales(
    filas: Sequence[Mapping[str, Any]],
) -> list[tuple[float, float, float, float, str]]:
    """``(lon, lat, mmi, pop, nombre)`` de cada municipio.

    Las filas municipales traen ``lon`` y ``lat`` —son las columnas del CSV que
    se publica—, pero esta funcion solo sabia leer un ``centroide`` en WKT que
    ninguna las trae. El resultado era una lista vacia en cada evento y un mapa
    sin un solo municipio dibujado. Se lee el par de columnas y se deja el WKT
    como respaldo, por si alguna fuente futura lo entrega asi.
    """
    puntos = []
    for fila in filas:
        coord = _coordenada(fila)
        if coord is None:
            continue
        puntos.append(
            (
                coord[0],
                coord[1],
                float(fila.get("mmi_max") or 0),
                float(fila.get("pop_mmi7p") or 0),
                str(fila.get("nombre") or ""),
            )
        )
    return puntos


def _coordenada(fila: Mapping[str, Any]) -> tuple[float, float] | None:
    """Centroide de un municipio, del par ``lon``/``lat`` o del WKT."""
    lon_bruto = fila.get("lon")
    lat_bruto = fila.get("lat")
    if lon_bruto is not None and lat_bruto is not None:
        try:
            lon, lat = float(lon_bruto), float(lat_bruto)
        except (TypeError, ValueError):
            lon = lat = 0.0
        if lon or lat:
            return (lon, lat)

    wkt = str(fila.get("centroide") or "")
    if not wkt.startswith("POINT"):
        return None
    try:
        x, y = (float(v) for v in wkt[wkt.index("(") + 1 : wkt.index(")")].split())
    except (ValueError, IndexError):
        return None
    return (x, y)


def _tamano(poblacion: float) -> float:
    """Area del circulo proporcional a la poblacion, con minimo visible."""
    import math

    return 12.0 + 4.0 * math.sqrt(max(poblacion, 0.0) / 1000.0)
