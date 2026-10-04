"""Deltas entre dos versiones del reporte de un mismo evento (RF-04).

RF-04 pide que al aparecer un ShakeMap nuevo el reporte se re-emita **con
changelog de deltas**, y da hasta el ejemplo: `pop MMI≥7: 340k → 355k`.

Estaba escrito casi entero y no lo calculaba nadie. `Report.changelog` existia,
`markdown.py` lo renderizaba si venia con algo, `format_delta_prose` daba
exactamente el formato del ejemplo — y ninguna linea del pipeline lo llenaba,
asi que la seccion no aparecio jamas en un reporte. El mismo patron que el
reporte preliminar y que las tres capas del activo: piezas correctas, sin nadie
que las una.

Importa más de lo que parece. Un ShakeMap se revisa muchas veces —el de
Venezuela llego a v14— y quien ya leyo la versión anterior necesita saber
**que cambio**, no volver a leerlo entero durante una emergencia.
"""

from __future__ import annotations

from ..common.formatting import (
    format_count_prose,
    format_delta_prose,
    format_number_es,
)
from ..common.state import identidad_de_version
from .model import Report

#: Cifras que se comparan, con su etiqueta. Es un subconjunto deliberado de
#: `Totales`: el changelog se lee durante una emergencia y trece filas de
#: deltas no se leen. Van las que cambian una decision.
CIFRAS_COMPARADAS: tuple[tuple[str, str], ...] = (
    ("pop_mmi6p", "Población en MMI≥6"),
    ("pop_mmi7p", "Población en MMI≥7"),
    ("pop_mmi8p", "Población en MMI≥8"),
    ("pop_65p_mmi7p", "Población de 65 años o más en MMI≥7"),
    ("bld_mmi7p", "Edificaciones en MMI≥7"),
    ("health_mmi7p", "Sedes de salud en MMI≥7"),
    ("edu_mmi7p", "Sedes educativas en MMI≥7"),
    # La palabra importa y son dos unidades distintas: deslizamiento es
    # probabilidad y licuefaccion es cobertura areal. `GF_UNIDAD` en
    # `markdown.py` ya las separa; aqui decian las dos "alto" a secas.
    ("pop_ls_alta", "Población en probabilidad alta de deslizamiento"),
    ("pop_lq_alta", "Población en cobertura areal alta por licuefacción"),
)


def build_changelog(anterior: Report | None, nuevo: Report) -> tuple[str, ...]:
    """Que cambio entre dos emisiones del mismo evento.

    Args:
        anterior: el reporte ya publicado. ``None`` en la primera emision, que
            no tiene con que compararse.
        nuevo: el que esta a punto de publicarse.

    Returns:
        Las lineas del changelog, **lo nuevo delante y lo ya publicado
        detras**. Vacio solo en la primera emision o si nunca cambio nada.
    """
    if anterior is None:
        return ()

    # EL CHANGELOG ES UN REGISTRO, NO EL DIFF DEL ULTIMO PASO.
    #
    # Hasta el 3-oct-2026 cada emision lo reemplazaba por su propio diff, y el
    # diff de un reproceso sin cambios es vacio. El Choco (`us6000tjl2`) lo
    # vivio entero: el 19-sep publico "ShakeMap: v9 → v10" con la poblacion en
    # MMI≥7 bajando de 3,1 a 2,4 millones y las sedes de salud de 970 a 500; el
    # 28-sep un reproceso por el activo de exposicion —el mismo ShakeMap v10—
    # lo sustituyo por una sola linea de edificaciones. El cambio que movia las
    # cifras de una emergencia solo sobrevivia en el historial de git, y RF-04
    # existe para que quien leyo la version anterior no tenga que ir a buscarlo.
    return (*_cambios_del_paso(anterior, nuevo), *anterior.changelog)


def _cambios_del_paso(anterior: Report, nuevo: Report) -> tuple[str, ...]:
    """Las lineas de esta emision frente a la anterior, vacio si nada cambio."""
    versiones = _cambios_de_version(anterior, nuevo)
    solucion = _cambios_de_solucion(anterior, nuevo)
    cifras = _cambios_de_cifras(anterior, nuevo)

    if not versiones and not solucion and not cifras:
        return ()

    # Un paso sin version nueva necesita su propia cabecera ahora que el
    # registro se acumula: sin ella, las cifras de un reproceso quedarian
    # pegadas debajo de las del ShakeMap anterior y se leerian como suyas. Si
    # USGS reviso la solucion sin version nueva, esa linea ya dice quien cambio.
    # La cabecera nombra la version con su contribuidor, igual que las lineas
    # de `_cambios_de_version`: "el mismo v10" solo es el mismo grid si es del
    # mismo contribuidor (#95).
    if not versiones and not solucion:
        mismo = identidad_de_version(nuevo.inputs.shakemap_fuente, nuevo.inputs.shakemap_version)
        versiones = [
            f"Recálculo con el mismo ShakeMap {mismo} "
            f"(cambió el cálculo o el activo de exposición, no USGS)"
        ]

    versiones = [*versiones, *solucion]

    # Una version nueva sin ninguna cifra debajo se lee como un changelog a
    # medias. Que la revision de USGS no mueva nada publicable **es** el
    # resultado, y decirlo cuesta una linea: sin ella, quien lee no sabe si es
    # que nada cambio o si nadie lo calculo.
    if not cifras:
        return (*versiones, "Ninguna cifra publicada cambia frente a la versión anterior.")

    return (*versiones, *cifras)


def _cambios_de_version(anterior: Report, nuevo: Report) -> list[str]:
    """Las versiones de producto que motivaron la re-emision."""
    # Se compara la identidad entera, contribuidor incluido: `us` v6 -> `atlas`
    # v6 es otro grid aunque el numero coincida (#95). Un reporte anterior sin
    # contribuidor registrado no cuenta como cambio de contribuidor: es una
    # ausencia, no un `source` distinto.
    a, n = anterior.inputs, nuevo.inputs
    cambios: list[str] = []
    for etiqueta, v_antes, f_antes, v_ahora, f_ahora in (
        ("ShakeMap", a.shakemap_version, a.shakemap_fuente, n.shakemap_version, n.shakemap_fuente),
        (
            "Ground Failure",
            a.groundfailure_version,
            a.groundfailure_fuente,
            n.groundfailure_version,
            n.groundfailure_fuente,
        ),
    ):
        otra_fuente = bool(f_antes and f_ahora and f_antes != f_ahora)
        if v_antes != v_ahora or otra_fuente:
            antes = identidad_de_version(f_antes, v_antes)
            ahora = identidad_de_version(f_ahora, v_ahora)
            cambios.append(f"{etiqueta}: {antes} → {ahora}")
    return cambios


def _cambios_de_solucion(anterior: Report, nuevo: Report) -> list[str]:
    """Magnitud, profundidad y epicentro, cuando USGS los revisa.

    EL REPORTE PODIA TITULARSE M6,6 CON INTENSIDADES DE UN M7,2.

    `mag`, `depth_km`, `lon` y `lat` no se refrescaban a proposito, y el motivo
    escrito en `_refrescar_lugar` es bueno: reescribirlos en silencio borraria
    el registro de que el sistema alguna vez dijo otra cosa. Pero no
    refrescarlos deja el artefacto **internamente incoherente** —el titular de
    una solucion y las cifras de otra— y eso es peor, porque nadie puede verlo.

    La salida no es elegir entre las dos: es refrescar **y** registrarlo aqui,
    que es exactamente para lo que existe el changelog. Asi el titular es el
    vigente y el registro de que cambio sigue publicado.
    """
    cambios: list[str] = []
    a, n = anterior.event, nuevo.event
    if abs(a.mag - n.mag) >= 0.05:
        cambios.append(f"Magnitud: M{format_number_es(a.mag, 1)} → M{format_number_es(n.mag, 1)}")
    if abs(a.depth_km - n.depth_km) >= 0.5:
        cambios.append(
            f"Profundidad: {format_number_es(a.depth_km, 0)} → {format_number_es(n.depth_km, 0)} km"
        )
    # El epicentro se mide en km y no en grados: "0,03°" no le dice nada a
    # nadie, y a esta latitud son tres kilometros.
    dkm = _distancia_km(a.lat, a.lon, n.lat, n.lon)
    if dkm >= 1.0:
        cambios.append(f"Epicentro: reubicado {format_number_es(dkm, 0)} km")
    return cambios


def _distancia_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Haversine. Solo para decir cuanto se movio un epicentro."""
    import math

    r = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    )
    return 2 * r * math.asin(math.sqrt(a))


def _cambios_de_cifras(anterior: Report, nuevo: Report) -> list[str]:
    """Deltas de las cifras, en la misma prosa con que se publican.

    **Se compara la cifra ya redondeada, no la exacta.** Si un ShakeMap nuevo
    mueve la población de 2.415.793 a 2.415.802, el reporte sigue diciendo
    "2,4 millones" en los dos sitios: anunciarlo como cambio seria inventar una
    diferencia que ningun lector puede ver. La regla de RF-06 —dos cifras
    significativas en prosa— decide también que cuenta como cambio.
    """
    antes, ahora = anterior.totales, nuevo.totales
    cambios: list[str] = []
    for campo, etiqueta in CIFRAS_COMPARADAS:
        valor_antes = float(getattr(antes, campo))
        valor_ahora = float(getattr(ahora, campo))
        if format_count_prose(valor_antes) == format_count_prose(valor_ahora):
            continue
        cambios.append(f"{etiqueta}: {format_delta_prose(valor_antes, valor_ahora)}")
    return cambios
