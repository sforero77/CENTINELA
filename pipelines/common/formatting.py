"""Formato de cifras del reporte (RF-06).

Regla explicita de la espec: **2 cifras significativas en prosa, exactas en
CSV/parquet**. Se implementa una sola vez aqui para que el markdown, el hilo y
el mapa no puedan divergir entre si.
"""

from __future__ import annotations

import math

from .constants import PROSE_SIGNIFICANT_DIGITS


def round_significant(value: float, digits: int = PROSE_SIGNIFICANT_DIGITS) -> float:
    """Redondea a ``digits`` cifras significativas.

    >>> round_significant(347_129)
    350000.0
    >>> round_significant(0.0432)
    0.043
    >>> round_significant(0)
    0.0
    """
    if digits < 1:
        raise ValueError("digits debe ser >= 1")
    if value == 0 or not math.isfinite(value):
        return float(value)
    # Via formato %g en vez de multiplicar y dividir por potencias de 10: el
    # camino aritmetico devuelve 999999.9999999999 para 1e6, y esa cifra se
    # publicaria como "1.000,0 mil" en lugar de "1 millón".
    return float(f"{value:.{digits}g}")


def format_number_es(value: float, decimals: int = 0) -> str:
    """Formatea con separador de miles y decimal en convencion es-CO.

    >>> format_number_es(1234567)
    '1.234.567'
    >>> format_number_es(12.345, decimals=1)
    '12,3'
    """
    formatted = f"{value:,.{decimals}f}"
    # en-US -> es: intercambio via marcador temporal para no pisar separadores.
    return formatted.replace(",", "\x00").replace(".", ",").replace("\x00", ".")


def format_count_prose(value: float) -> str:
    """Cifra de poblacion/conteo para prosa: 2 significativas y escala legible.

    Por debajo de diez mil se escribe la cifra completa: "1,8 mil km" se lee
    peor que "1.800 km", y a esa escala el separador de miles ya es legible.

    >>> format_count_prose(347_129)
    '350 mil'
    >>> format_count_prose(1_234_567)
    '1,2 millones'
    >>> format_count_prose(1_820)
    '1.800'
    >>> format_count_prose(842)
    '840'
    """
    rounded = round_significant(value)
    if abs(rounded) >= 1_000_000:
        millions = rounded / 1_000_000
        decimals = 0 if millions == int(millions) else 1
        # Con tilde: es la unica palabra de todo el generador que salia sin
        # ella, y sale en la fila mas leida de la tabla de exposicion.
        unit = "millón" if abs(millions) == 1 else "millones"
        return f"{format_number_es(millions, decimals)} {unit}"
    if abs(rounded) >= 10_000:
        # A dos cifras significativas, todo numero de cinco digitos o mas es
        # un multiplo exacto de mil: nunca hacen falta decimales aqui.
        return f"{format_number_es(rounded / 1_000)} mil"
    return format_number_es(rounded)


def format_delta_prose(before: float, after: float) -> str:
    """Delta entre versiones de ShakeMap para el changelog (RF-04).

    >>> format_delta_prose(340_000, 355_000)
    '340 mil → 360 mil'
    """
    return f"{format_count_prose(before)} → {format_count_prose(after)}"


#: Palabras que en un toponimo espanol van en minuscula salvo al principio.
#: `str.title()` no lo sabe y publica "Santa Rosa De Cabal", "Villa De Leyva",
#: "San Andres Y Providencia".
_ATONAS: frozenset[str] = frozenset(
    {"de", "del", "la", "las", "el", "los", "y", "e", "da", "do", "dos", "en"}
)


def titulo_es(nombre: str) -> str:
    """Titula un toponimo respetando las particulas.

    `str.title()` pone en mayuscula toda palabra, y los nombres municipales de
    LATAM estan llenos de particulas: salia "Santa Rosa De Cabal". Tambien
    rompe los apostrofos y los guiones, pero eso no aparece en el catalogo.

    La primera palabra siempre va en mayuscula, aunque sea atona: "Las Vegas"
    no es "las Vegas".
    """
    palabras = nombre.strip().split()
    if not palabras:
        return ""
    salida = []
    for i, palabra in enumerate(palabras):
        # Las abreviaturas se quedan como estan: "BOGOTA, D.C." no es
        # "Bogota, D.c.". Se reconocen por el punto interior.
        if "." in palabra.rstrip("."):
            salida.append(palabra.upper())
            continue
        baja = palabra.lower()
        salida.append(baja if i and baja in _ATONAS else baja.capitalize())
    return " ".join(salida)
