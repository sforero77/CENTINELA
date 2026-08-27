"""Ingesta de focos de calor de NASA FIRMS.

Se leen los CSV regionales de 24 h, que estan **abiertos y no piden `MAP_KEY`**
— verificado el 26-ago-2026: HTTP 200 para las seis combinaciones de tres
satelites VIIRS por dos regiones. La API por bbox si exige clave y ademas
raciona a 5.000 peticiones por diez minutos; estos ficheros son un GET plano.

Medido ese mismo dia, antes del pico de la temporada de quemas:

    66.806 detecciones en LATAM en 24 h  ->  22.701 celdas H3 r8
    2,9 detecciones por celda (los tres satelites ven el mismo fuego)

Esa ultima linea es la que fija el vocabulario de todo el modulo. Lo que se
cuenta son **detecciones**, no incendios: tres satelites sobrevolando el mismo
fuego producen tres filas. Llamarlas "focos" invitaria a leer el numero como
cantidad de fuegos, que es tres veces mas de los que hay.
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from typing import Any, Final

from ..common.http import Fetcher
from ..common.logging import get_logger

_log = get_logger(__name__)

_BASE: Final[str] = "https://firms.modaps.eosdis.nasa.gov/data/active_fire"

#: Satelites VIIRS: (segmento de ruta, prefijo del fichero). Los tres llevan el
#: mismo sensor a 375 m y se reparten las horas de paso, asi que usar los tres
#: no es redundancia: es cobertura temporal.
SATELITES: Final[tuple[tuple[str, str], ...]] = (
    ("suomi-npp-viirs-c2", "SUOMI_VIIRS_C2"),
    ("noaa-20-viirs-c2", "J1_VIIRS_C2"),
    ("noaa-21-viirs-c2", "J2_VIIRS_C2"),
)

#: Regiones de FIRMS que cubren los diecinueve paises. Mexico y el Caribe caen
#: en "Central_America" segun la particion del proveedor, no la geografica.
REGIONES: Final[tuple[str, ...]] = ("South_America", "Central_America")

#: Ventana del fichero. Hay tambien 48h y 7d; 24h es lo que se publica.
VENTANA: Final[str] = "24h"

#: Confianza que **no** se cuenta como deteccion util. FIRMS documenta que las
#: bajas suelen ser reflejo solar sobre agua o superficies calientes que no
#: arden. Fueron 5.621 de 66.806 el dia de la medicion.
#:
#: No se tiran: se publican aparte. Descartarlas en silencio seria decidir por
#: quien lee, y este sistema publica lo que descarta desde que un M4,9 sentido
#: en media Colombia solo existia en un log de CI.
CONFIANZA_BAJA: Final[str] = "low"


@dataclass(frozen=True, slots=True)
class Foco:
    """Una deteccion de un satelite en una pasada.

    No es un incendio. Es "este sensor vio algo caliente aqui a esta hora".
    """

    lon: float
    lat: float
    #: ``low`` / ``nominal`` / ``high``.
    confianza: str
    #: Potencia radiativa del fuego, en megavatios. Lo mas cercano a una
    #: intensidad que da el producto, y aun asi depende del angulo de vista.
    frp: float
    adquirido_utc: str
    satelite: str
    #: ``D`` o ``N``. Las detecciones nocturnas tienen menos falso positivo por
    #: reflejo solar, que es justo el modo de error de la confianza baja.
    dia_noche: str

    @property
    def util(self) -> bool:
        return self.confianza != CONFIANZA_BAJA


def feed_url(satelite: tuple[str, str], region: str, ventana: str = VENTANA) -> str:
    """URL del CSV regional. Sin clave: son ficheros estaticos."""
    ruta, prefijo = satelite
    return f"{_BASE}/{ruta}/csv/{prefijo}_{region}_{ventana}.csv"


def _instante(fecha: str, hora: str) -> str:
    """``2026-08-25`` + ``0406`` -> ``2026-08-25T04:06:00Z``.

    La hora viene sin ceros a la izquierda cuando es pequena: las 04:06 llegan
    como ``406`` y la medianoche como ``0``. Sin rellenar, ``406`` se leeria
    como 40:6 y el evento saltaria a otro dia.
    """
    hhmm = hora.strip().zfill(4)
    return f"{fecha.strip()}T{hhmm[:2]}:{hhmm[2:]}:00Z"


def parse_csv(texto: str) -> list[Foco]:
    """Parsea un CSV de FIRMS. Sin red, para poder probarlo con fixtures.

    Una fila ilegible se salta en vez de tumbar la corrida: son decenas de miles
    por fichero y un solo campo corrupto no puede dejar sin capa a la region.
    """
    focos: list[Foco] = []
    saltadas = 0

    for fila in csv.DictReader(io.StringIO(texto)):
        try:
            focos.append(
                Foco(
                    lon=float(fila["longitude"]),
                    lat=float(fila["latitude"]),
                    confianza=str(fila.get("confidence", "")).strip().lower(),
                    frp=float(fila.get("frp") or 0.0),
                    adquirido_utc=_instante(fila["acq_date"], fila["acq_time"]),
                    satelite=str(fila.get("satellite", "")).strip(),
                    dia_noche=str(fila.get("daynight", "")).strip().upper(),
                )
            )
        except (KeyError, ValueError, TypeError):
            saltadas += 1

    if saltadas:
        _log.warning("filas ilegibles en el CSV de FIRMS", extra={"context": {"filas": saltadas}})
    return focos


def fetch_focos(
    fetcher: Any,
    *,
    satelites: tuple[tuple[str, str], ...] = SATELITES,
    regiones: tuple[str, ...] = REGIONES,
    ventana: str = VENTANA,
) -> list[Foco]:
    """Descarga y parsea las seis combinaciones de satelite y region.

    **Un fichero que falla no tumba los otros cinco.** Son seis peticiones a un
    servicio de la NASA y basta con que una tenga un mal minuto; perder una
    region entera es peor que publicar con cinco sextos del dato, y el conteo
    queda en el log para que la merma no sea invisible.
    """
    todos: list[Foco] = []
    fallidos: list[str] = []

    for satelite in satelites:
        for region in regiones:
            url = feed_url(satelite, region, ventana)
            try:
                texto = fetcher.get_bytes(url).decode("utf-8")
            except Exception as error:
                _log.warning(
                    "fichero de FIRMS no disponible",
                    extra={"context": {"url": url, "error": str(error)}},
                )
                fallidos.append(f"{satelite[1]}/{region}")
                continue
            todos.extend(parse_csv(texto))

    _log.info(
        "focos leidos de FIRMS",
        extra={
            "context": {
                "detecciones": len(todos),
                "utiles": sum(1 for f in todos if f.util),
                "ficheros_fallidos": fallidos,
            }
        },
    )
    return todos


def _fetcher_por_defecto() -> Fetcher:
    from ..common.http import HttpFetcher

    return HttpFetcher()
