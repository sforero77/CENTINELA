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

**Pero devolverlo no puede ser silencioso** (auditoria del 5-sep-2026, #159).
Lejos de la costa USGS no escribe ``X km W of`` sino la region de
Flinn-Engdahl: ``southern East Pacific Rise``, ``Chile-Argentina border
region``. Ninguna forma las reconocia y salian en ingles en el titulo de un
reporte publicado (us7000tdms) sin que nadie lo supiera. Ahora se traducen las
que se han visto, y la que siga sin encajar deja un aviso en el log con la
cadena exacta, que es lo que hace falta para anadir su forma.

Esas regiones son la excepcion a "nunca el toponimo": ``East Pacific Rise`` no
es un nombre oficial de ningun pais sino un exonimo ingles de un rasgo del
fondo marino, y en espanol tiene el suyo (dorsal del Pacifico Oriental). Solo
se traducen las del diccionario cerrado de abajo, nunca por regla.
"""

from __future__ import annotations

import re

from .logging import get_logger

_log = get_logger(__name__)

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
    "Haiti": "Haití",
    "Belize": "Belice",
    "Trinidad and Tobago": "Trinidad y Tobago",
    "French Guiana": "Guayana Francesa",
    "Suriname": "Surinam",
}

#: Paises que se escriben igual en los dos idiomas. Hace falta listarlos porque
#: las formas de zona (``southern Peru``, ``Peru-Ecuador border region``) solo
#: se traducen sobre un nombre conocido: ``northern Algo`` con ``Algo``
#: desconocido es justo lo que no se sabe leer.
PAISES_IGUALES: frozenset[str] = frozenset(
    {
        "Argentina",
        "Bolivia",
        "Chile",
        "Colombia",
        "Costa Rica",
        "Cuba",
        "Ecuador",
        "El Salvador",
        "Guatemala",
        "Guyana",
        "Honduras",
        "Jamaica",
        "Nicaragua",
        "Paraguay",
        "Puerto Rico",
        "Uruguay",
        "Venezuela",
    }
)

#: Regiones de Flinn-Engdahl que USGS usa en LATAM, con su nombre en espanol y
#: el articulo que lleva detras de "de" (``sur de la dorsal...``). Clave en
#: minusculas: USGS escribe ``southern East Pacific Rise`` y ``Southern East
#: Pacific Rise`` segun el dia. Diccionario cerrado a proposito (ver arriba).
RASGOS: dict[str, tuple[str, str]] = {
    "east pacific rise": ("la", "dorsal del Pacífico Oriental"),
    "mid-atlantic ridge": ("la", "dorsal mesoatlántica"),
    "west chile rise": ("la", "dorsal de Chile"),
    "chile rise": ("la", "dorsal de Chile"),
    "pacific-antarctic ridge": ("la", "dorsal Pacífico-Antártica"),
    "galapagos triple junction": ("el", "punto triple de Galápagos"),
    "galapagos islands": ("las", "islas Galápagos"),
    "easter island": ("la", "isla de Pascua"),
    "juan fernandez islands": ("las", "islas Juan Fernández"),
    "revilla gigedo islands": ("las", "islas Revillagigedo"),
    "south sandwich islands": ("las", "islas Sandwich del Sur"),
    "south georgia island": ("la", "isla Georgia del Sur"),
    "falkland islands": ("las", "islas Malvinas"),
    "drake passage": ("el", "pasaje de Drake"),
    "scotia sea": ("el", "mar de Escocia"),
    "caribbean sea": ("el", "mar Caribe"),
    "cayman islands": ("las", "islas Caimán"),
    "leeward islands": ("las", "islas de Sotavento"),
    "windward islands": ("las", "islas de Barlovento"),
    "mona passage": ("el", "canal de la Mona"),
    "gulf of california": ("el", "golfo de California"),
    "gulf of mexico": ("el", "golfo de México"),
    "gulf of honduras": ("el", "golfo de Honduras"),
    "central america": ("", "Centroamérica"),
    "south america": ("", "Sudamérica"),
}

#: ``southern Peru``, ``central East Pacific Rise``. Se traducen a un sustantivo
#: con articulo para que encajen detras de otra forma (``la costa del norte de
#: Chile``).
_MODIFICADORES: dict[str, str] = {
    "northern": "norte",
    "southern": "sur",
    "central": "centro",
    "eastern": "este",
    "western": "oeste",
    "northeastern": "noreste",
    "northwestern": "noroeste",
    "southeastern": "sureste",
    "southwestern": "suroeste",
}

#: ``south of Panama``: los cuatro puntos cardinales en palabras.
_PUNTOS: dict[str, str] = {"north": "norte", "south": "sur", "east": "este", "west": "oeste"}

#: Palabras inglesas que no pueden aparecer en un lugar en espanol. Si alguna
#: sobrevive a la traduccion, la forma no se reconocio. Sin ``central`` ni
#: ``zone``: ``Valle Central`` es un toponimo espanol de verdad.
PALABRAS_INGLESAS: frozenset[str] = frozenset(
    {
        "of",
        "the",
        "near",
        "off",
        "coast",
        "region",
        "border",
        "northern",
        "southern",
        "eastern",
        "western",
        "north",
        "south",
        "east",
        "west",
        "rise",
        "ridge",
        "island",
        "islands",
        "sea",
        "gulf",
        "passage",
        "junction",
        "trench",
        "fracture",
        "earthquake",
    }
)

#: ``20 km W of Catia La Mar, Venezuela``. La forma mas comun con diferencia.
_DISTANCIA = re.compile(r"^(\d+)\s*km\s+([NSEW]{1,3})\s+of\s+(.+)$", re.IGNORECASE)

#: ``Near the coast of Bio-Bio, Chile`` y ``Off the coast of ...``.
_COSTA = re.compile(r"^(?:near|off)\s+the\s+coast\s+of\s+(.+)$", re.IGNORECASE)

#: ``Chile-Argentina border region``. Va antes que ``_REGION``: esa la
#: atrapaba entera y publicaba «Región de Chile-Argentina border», mitad en
#: cada idioma (auditoria del 5-sep-2026, #160), en la familia de lugares mas
#: comun de los sismos andinos.
_FRONTERA = re.compile(r"^(.+?)\s*-\s*(.+?)\s+border\s+region$", re.IGNORECASE)

#: ``Nicaragua region``, ``Chiapas, Mexico region``.
_REGION = re.compile(r"^(.+?)\s+region$", re.IGNORECASE)

#: ``south of Panama``.
_AL_PUNTO = re.compile(r"^(north|south|east|west)\s+of\s+(.+)$", re.IGNORECASE)

#: Una palabra: letras, con tilde o sin ella.
_PALABRA = re.compile(r"[^\W\d_]+")

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


def huellas_en_ingles(texto: str) -> list[str]:
    """Las palabras inglesas evidentes que quedan en un lugar, en orden.

    >>> huellas_en_ingles("southern East Pacific Rise")
    ['southern', 'Rise']
    >>> huellas_en_ingles("20 km al O de Catia La Mar, Venezuela")
    []
    """
    return [p for p in _PALABRA.findall(texto) if p.lower() in PALABRAS_INGLESAS]


def _de(articulo: str, nombre: str) -> str:
    """``de`` + articulo + nombre, con la contraccion: ``del norte``."""
    if articulo == "el":
        return f"del {nombre}"
    return f"de {articulo} {nombre}" if articulo else f"de {nombre}"


def _mayuscula(texto: str) -> str:
    return texto[:1].upper() + texto[1:]


def _zona(texto: str) -> tuple[str, str] | None:
    """Un pais, una region de Flinn-Engdahl o un modificador sobre ellos.

    Devuelve ``(articulo, nombre)`` para poder encajarla detras de otra forma,
    o ``None`` si no se reconoce: quien llama decide entonces no tocar nada.
    """
    texto = texto.strip()
    if texto in PAISES:
        return "", PAISES[texto]
    if texto in PAISES_IGUALES:
        return "", texto
    if texto.lower() in RASGOS:
        return RASGOS[texto.lower()]
    # ``Galapagos Islands, Ecuador``: un rasgo seguido de su pais.
    if "," in texto:
        cabeza, _, pais = texto.rpartition(",")
        rasgo, pais_es = _zona(cabeza), _zona(pais)
        if rasgo is not None and pais_es is not None:
            return rasgo[0], f"{rasgo[1]}, {pais_es[1]}"
    primera, _, resto = texto.partition(" ")
    if primera.lower() in _MODIFICADORES and resto:
        interior = _zona(resto)
        if interior is not None:
            return "el", f"{_MODIFICADORES[primera.lower()]} {_de(*interior)}"
    return None


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
    >>> traducir_lugar("southern East Pacific Rise")
    'Sur de la dorsal del Pacífico Oriental'
    """
    texto = place.strip()
    if not texto:
        return texto
    salida = _traducir(texto)
    if huellas := huellas_en_ingles(salida):
        # El lugar sale igual —uno en ingles se lee raro; uno mal traducido
        # lleva a otro sitio—, pero ya no en silencio: la cadena exacta es lo
        # que hace falta para anadir su forma.
        _log.warning(
            "lugar de USGS sin forma reconocida: se publica en ingles",
            extra={"context": {"place": texto, "huellas": huellas}},
        )
    return salida


def _de_zona_o_pais(texto: str) -> str:
    """``de`` + la zona traducida, o + el texto con solo el pais traducido."""
    zona = _zona(texto)
    return _de(*zona) if zona is not None else f"de {traducir_pais(texto)}"


def _traducir(texto: str) -> str:
    if (m := _DISTANCIA.match(texto)) is not None:
        km, rumbo, resto = m.group(1), m.group(2).upper(), m.group(3)
        # Un rumbo que no esta en la rosa no es un rumbo: se deja el original
        # antes que inventar una direccion.
        if rumbo in RUMBOS:
            return f"{km} km al {RUMBOS[rumbo]} de {traducir_pais(resto)}"
        return traducir_pais(texto)

    if (m := _COSTA.match(texto)) is not None:
        return f"Cerca de la costa {_de_zona_o_pais(m.group(1))}"

    if (m := _FRONTERA.match(texto)) is not None:
        lados = []
        for lado in (m.group(1), m.group(2)):
            zona = _zona(lado)
            lados.append(zona[1] if zona is not None else traducir_pais(lado))
        return f"Zona fronteriza {lados[0]}-{lados[1]}"

    if (m := _REGION.match(texto)) is not None:
        return f"Región {_de_zona_o_pais(m.group(1))}"

    if (m := _AL_PUNTO.match(texto)) is not None:
        return f"Al {_PUNTOS[m.group(1).lower()]} {_de_zona_o_pais(m.group(2))}"

    if (m := _CON_NOMBRE.match(texto)) is not None:
        return f"Terremoto de {traducir_pais(m.group(2))} ({m.group(1)})"

    if (zona := _zona(texto)) is not None:
        return _mayuscula(zona[1])

    return traducir_pais(texto)
