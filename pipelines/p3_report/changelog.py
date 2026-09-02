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
        Las lineas del changelog, vacio si es la primera emision o si nada
        cambio de forma publicable.
    """
    if anterior is None:
        return ()

    versiones = _cambios_de_version(anterior, nuevo)
    solucion = _cambios_de_solucion(anterior, nuevo)
    cifras = _cambios_de_cifras(anterior, nuevo)

    if not versiones and not solucion and not cifras:
        return ()

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
    cambios: list[str] = []
    for etiqueta, antes, ahora in (
        ("ShakeMap", anterior.inputs.shakemap_version, nuevo.inputs.shakemap_version),
        (
            "Ground Failure",
            anterior.inputs.groundfailure_version,
            nuevo.inputs.groundfailure_version,
        ),
    ):
        if antes != ahora:
            cambios.append(f"{etiqueta}: v{antes} → v{ahora}")
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
