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

from ..common.formatting import format_count_prose, format_delta_prose
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
    ("pop_ls_alta", "Población en deslizamiento alto"),
    ("pop_lq_alta", "Población en licuefacción alta"),
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
    cifras = _cambios_de_cifras(anterior, nuevo)

    if not versiones and not cifras:
        return ()

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
