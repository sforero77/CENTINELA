"""El lugar de un sismo, en espanol (RF-06).

USGS describe donde ocurrio un sismo en ingles: ``20 km W of Catia La Mar,
Venezuela``. Esa cadena viaja tal cual al titulo del reporte, al hilo para
redes, al mapa y al visor — o sea que el producto entero, escrito en espanol
para America Latina, nombraba sus propios sismos en ingles.

RF-06 pide "reporte en espanol neutro con toponimos oficiales del pais". La
segunda mitad se cumplia; la primera no.

**Se traduce el andamiaje, nunca el toponimo.** ``Catia La Mar`` es un nombre
propio y se queda como esta; lo que cambia es ``W of`` -> ``al O de`` y
``Mexico`` -> ``México``. Traducir el nombre del sitio seria justo lo contrario
de lo que pide el requisito, y ademas produciria toponimos que no existen en
ningun mapa oficial.

**Ante una forma que no se reconoce, se devuelve el original.** Un lugar en
ingles se lee raro; un lugar mal traducido lleva a otro sitio. USGS no publica
una gramatica de este campo, asi que las formas de aqui son las que se han
visto de verdad en el catalogo de LATAM y nada mas.
"""

from __future__ import annotations

import re

#: Rosa de los vientos de USGS -> espanol. Solo cambia la W (west -> oeste) y
#: sus compuestos; el resto de letras coinciden en los dos idiomas.
RUMBOS: dict[str, str] = {
    "N": "N",
    "NNE": "NNE",
    "NE": "NE",
    "ENE": "ENE",
    "E": "E",
    "ESE": "ESE",
    "SE": "SE",
    "SSE": "SSE",
    "S": "S",
    "SSW": "SSO",
    "SW": "SO",
    "WSW": "OSO",
    "W": "O",
    "WNW": "ONO",
    "NW": "NO",
    "NNW": "NNO",
}

#: Nombre en espanol de los paises que USGS escribe distinto. Los que no estan
#: aqui se escriben igual en los dos idiomas (Chile, Ecuador, Guatemala...).
PAISES: dict[str, str] = {
    "Mexico": "México",
    "Peru": "Perú",
    "Panama": "Panamá",
    "Brazil": "Brasil",
    "Dominican Republic": "República Dominicana",
}

#: ``20 km W of Catia La Mar, Venezuela``. La forma mas comun con diferencia.
_DISTANCIA = re.compile(r"^(\d+)\s*km\s+([NSEW]{1,3})\s+of\s+(.+)$", re.IGNORECASE)

#: ``Near the coast of Bio-Bio, Chile`` y ``Off the coast of ...``.
_COSTA = re.compile(r"^(?:near|off)\s+the\s+coast\s+of\s+(.+)$", re.IGNORECASE)

#: ``Nicaragua region``, ``Chiapas, Mexico region``.
_REGION = re.compile(r"^(.+?)\s+region$", re.IGNORECASE)

#: ``2017 Tehuantepec, Mexico Earthquake``. USGS reserva esta forma para los
#: eventos que nombra, o sea los mas grandes — justo los que mas gente mira.
_CON_NOMBRE = re.compile(r"^(\d{4})\s+(.+?)\s+Earthquake$", re.IGNORECASE)


def traducir_pais(texto: str) -> str:
    """Traduce el nombre del pais al final de un lugar, si hace falta.

    Solo el ultimo segmento tras la coma: un toponimo puede contener la palabra
    ``Mexico`` —``Nuevo Mexico``, ``Ciudad de Mexico``— y ahi no es el pais.
    """
    partes = [p.strip() for p in texto.split(",")]
    if partes and partes[-1] in PAISES:
        partes[-1] = PAISES[partes[-1]]
    return ", ".join(partes)


def traducir_lugar(place: str) -> str:
    """El campo ``place`` de USGS, en espanol.

    Args:
        place: la cadena tal como la publica USGS.

    Returns:
        La misma descripcion en espanol, con el toponimo intacto. Si la forma
        no se reconoce, el original sin tocar mas que el nombre del pais.

    >>> traducir_lugar("20 km W of Catia La Mar, Venezuela")
    '20 km al O de Catia La Mar, Venezuela'
    >>> traducir_lugar("Acapulco, Mexico")
    'Acapulco, México'
    >>> traducir_lugar("Near the coast of Bio-Bio, Chile")
    'Cerca de la costa de Bio-Bio, Chile'
    """
    texto = place.strip()
    if not texto:
        return texto

    if (m := _DISTANCIA.match(texto)) is not None:
        km, rumbo, resto = m.group(1), m.group(2).upper(), m.group(3)
        # Un rumbo que no esta en la rosa no es un rumbo: se deja el original
        # antes que inventar una direccion.
        if rumbo in RUMBOS:
            return f"{km} km al {RUMBOS[rumbo]} de {traducir_pais(resto)}"
        return traducir_pais(texto)

    if (m := _COSTA.match(texto)) is not None:
        return f"Cerca de la costa de {traducir_pais(m.group(1))}"

    if (m := _REGION.match(texto)) is not None:
        return f"Región de {traducir_pais(m.group(1))}"

    if (m := _CON_NOMBRE.match(texto)) is not None:
        return f"Terremoto de {traducir_pais(m.group(2))} ({m.group(1)})"

    return traducir_pais(texto)
