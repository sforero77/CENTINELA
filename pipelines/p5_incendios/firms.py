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

#: Satelites VIIRS: (segmento de ruta, prefijo del fichero).
#:
#: NO SE REPARTEN LAS HORAS DEL DIA, y este comentario decia que si. Los tres
#: van en el mismo plano heliosincrono y cruzan el ecuador a la **misma hora
#: solar** —13:30 ascendente, 01:30 descendente—, separados por cuartos de
#: orbita: S-NPP y NOAA-21 unos 25 min, S-NPP y NOAA-20 unos 50. `docs/pipelines/
#: p5-incendios.md` ya lo decia bien; alguien corrigio el doc y no volvio al
#: codigo.
#:
#: Lo que aportan de verdad: se pasa de 2 miradas al dia a **6** (tres de dia,
#: tres de noche), todas agrupadas en esas dos ventanas. Eso son mas
#: oportunidades de atravesar nube y humo y de atrapar un fuego corto, no
#: cobertura horaria: sigue habiendo un hueco ciego de unas 11 h en cada mitad
#: del dia. Fuente: NOAA VLAB TOWR-S, VIIRS Imagery.
SATELITES: Final[tuple[tuple[str, str], ...]] = (
    # NASA cesa Suomi-NPP el 1-nov-2026 a las 13:00 UTC. Cuando deje de
    # responder hay que quitarlo de aqui y corregir la documentacion de P5,
    # que afirma que se usan tres satelites. Ver PENDIENTES 2.1.decies.
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
    #: Temperatura de brillo del canal I-4 (3,55-3,93 um), en kelvin.
    #:
    #: FIRMS la publica en cada fila y este pipeline la tiraba: se leian ocho de
    #: las trece columnas del CSV y `bright_ti4` no era una de ellas. Es el otro
    #: numero que da el producto —la potencia radiativa dice cuanta energia, esta
    #: cuanto calienta— y sin ella la unica intensidad publicada era el FRP.
    #:
    #: NO ES LA TEMPERATURA DEL FUEGO, y confundirlas es facil. Es la del pixel
    #: entero de 375 m, que mezcla la llama con el terreno frio de alrededor: un
    #: fuego de 900 K ocupando una centesima del pixel se lee como ~350 K.
    #: Publicarla como "temperatura del incendio" seria una cifra creible y
    #: falsa, que es lo que este sistema evita por encima de todo.
    brillo_k: float
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
                    brillo_k=float(fila.get("bright_ti4") or 0.0),
                    dia_noche=str(fila.get("daynight", "")).strip().upper(),
                )
            )
        except (KeyError, ValueError, TypeError):
            saltadas += 1

    if saltadas:
        _log.warning("filas ilegibles en el CSV de FIRMS", extra={"context": {"filas": saltadas}})
    return focos


@dataclass(frozen=True, slots=True)
class Lectura:
    """Lo leido de FIRMS, y lo que no se pudo leer.

    Los fallidos viajan con los focos, no solo en el log. El 30-ago-2026
    fallaron **los seis ficheros** —FIRMS tuvo un mal minuto— y la corrida salio
    verde: cero detecciones, cero celdas, y nada que lo dijera. La capa
    publicada se salvo porque el pipeline ya se niega a publicar ceros, pero si
    FIRMS se cayera una semana el visor serviria fuego de hace siete dias con
    todo en verde. Que es, exactamente, la familia de fallo que este proyecto
    persigue.
    """

    focos: list[Foco]
    #: Que ficheros no se pudieron leer, como "J1_VIIRS_C2/South_America".
    fallidos: list[str]
    #: Cuantos se pidieron. Sin esto, "dos fallidos" no dice si fue un roce o
    #: una caida: dos de seis es un roce, dos de dos es quedarse a ciegas.
    pedidos: int
    #: Cuantos trajeron **al menos una deteccion**. No es `pedidos - fallidos`:
    #: un HTTP 200 con el cuerpo vacio, o con la cabecera renombrada, se
    #: descarga sin error y se parsea a cero filas.
    leidos: int = 0

    @property
    def ciego(self) -> bool:
        """¿No se leyo nada util? Entonces no se miro, y hay que decirlo.

        Decia "¿fallaron TODOS?", que es una pregunta sobre el transporte y no
        sobre el dato. Seis HTTP 200 con el cuerpo vacio o con la cabecera
        renombrada dan `focos=0, fallidos=0` y pasaban por corrida sana: P5
        salia por el retorno temprano, el workflow quedaba verde, y el visor
        seguia sirviendo el fuego de la corrida anterior.

        Que FIRMS devuelva seis ficheros vacios a la vez para dos continentes en
        una ventana de 24 h no es un dia tranquilo: es no haber leido.
        """
        if self.pedidos <= 0:
            return False
        return len(self.fallidos) >= self.pedidos or self.leidos == 0


def fetch_focos(
    fetcher: Any,
    *,
    satelites: tuple[tuple[str, str], ...] = SATELITES,
    regiones: tuple[str, ...] = REGIONES,
    ventana: str = VENTANA,
) -> Lectura:
    """Descarga y parsea las seis combinaciones de satelite y region.

    **Un fichero que falla no tumba los otros cinco.** Son seis peticiones a un
    servicio de la NASA y basta con que una tenga un mal minuto; perder una
    region entera es peor que publicar con cinco sextos del dato, y el conteo
    queda en el log para que la merma no sea invisible.
    """
    todos: list[Foco] = []
    fallidos: list[str] = []
    vacios: list[str] = []
    leidos = 0

    for satelite in satelites:
        for region in regiones:
            url = feed_url(satelite, region, ventana)
            nombre = f"{satelite[1]}/{region}"
            try:
                texto = fetcher.get_bytes(url).decode("utf-8")
            except Exception as error:
                _log.warning(
                    "fichero de FIRMS no disponible",
                    extra={"context": {"url": url, "error": str(error)}},
                )
                fallidos.append(nombre)
                continue
            # Un 200 con el cuerpo vacio no es un fallo de transporte y tampoco
            # es una lectura: se cuenta aparte, porque es lo que distingue "hoy
            # no ardio nada ahi" de "no lei nada en ninguna parte".
            leidas = parse_csv(texto)
            if leidas:
                leidos += 1
            else:
                vacios.append(nombre)
            todos.extend(leidas)

    # LAS DOS REGIONES DE FIRMS SE SOLAPAN Y SE CONCATENABAN SIN MAS.
    #
    # "South_America" y "Central_America" son la particion del proveedor, no la
    # geografica, y su caja comun cubre el norte de Colombia y Venezuela,
    # Panama, Costa Rica y Trinidad. Cada deteccion de esa franja llega **dos
    # veces**, una por cada fichero regional, del mismo satelite y con los
    # mismos valores.
    #
    # No se cae nada y no hay nada que revise: el conteo de detecciones sube, el
    # FRP se suma dos veces, y las celdas de esa franja publican el doble de
    # fuego. Medido el dia de la auditoria: 1.885 claves con exactamente dos
    # copias, 889 celdas con el conteo duplicado y 11.930 MW inventados.
    #
    # La clave es lo que identifica una deteccion: **donde, cuando y que
    # sensor**. Dos satelites que ven el mismo fuego a la misma hora son dos
    # detecciones de verdad y tienen que seguir contando dos veces.
    antes = len(todos)
    todos = _sin_duplicados(todos)
    duplicadas = antes - len(todos)

    _log.info(
        "focos leidos de FIRMS",
        extra={
            "context": {
                "detecciones": len(todos),
                "duplicadas_entre_regiones": duplicadas,
                "utiles": sum(1 for f in todos if f.util),
                "ficheros_fallidos": fallidos,
                "ficheros_vacios": vacios,
                "ficheros_leidos": leidos,
                "ficheros_pedidos": len(satelites) * len(regiones),
            }
        },
    )
    return Lectura(
        focos=todos,
        fallidos=fallidos,
        pedidos=len(satelites) * len(regiones),
        leidos=leidos,
    )


def clave_de_deteccion(foco: Foco) -> tuple[str, str, str, str]:
    """Lo que identifica una deteccion: donde, cuando y que sensor.

    Las coordenadas se comparan como texto con la precision que publica FIRMS
    —cinco decimales, unos 30 cm— y no como flotantes: el mismo pixel llega en
    los dos ficheros regionales con la misma cadena, y compararlo como numero
    metera al redondeo en una decision que no lo necesita.
    """
    return (f"{foco.lon:.5f}", f"{foco.lat:.5f}", foco.adquirido_utc, foco.satelite)


def _sin_duplicados(focos: list[Foco]) -> list[Foco]:
    """Conserva la primera aparicion de cada deteccion, en orden de lectura."""
    vistas: set[tuple[str, str, str, str]] = set()
    unicos: list[Foco] = []
    for foco in focos:
        clave = clave_de_deteccion(foco)
        if clave in vistas:
            continue
        vistas.add(clave)
        unicos.append(foco)
    return unicos


def en_la_ventana(focos: list[Foco], horas: int) -> list[Foco]:
    """Descarta las detecciones anteriores a la ventana declarada.

    SE RECORTABA POR CELDA Y NO POR DETECCION.

    El recorte vivia en `incendios._en_la_ventana`, sobre las celdas ya
    agregadas, y conservaba la celda entera si su deteccion **mas reciente**
    entraba en la ventana. Una celda cuya ultima deteccion es de hace dos horas
    y la primera de hace treinta y nueve se publicaba con las dos dentro: su
    conteo, su potencia radiativa acumulada y su reparto por satelite incluian
    detecciones que el fichero declara no cubrir.

    Medido el dia de la auditoria: **5.158 detecciones fuera de la ventana de
    24 h, con 66.794 MW**. El fichero decia `ventana_horas: 24` y traia
    detecciones de hasta 39 h.

    Los seis ficheros regionales de FIRMS no cortan a la misma hora, asi que al
    unirlos el span real supera siempre las 24 h declaradas. La referencia es
    **la deteccion mas reciente del propio dato** y no el reloj: es la misma
    regla que aplica el visor, y con el reloj un fichero de FIRMS de hace cuatro
    horas dejaria la ventana vacia.
    """
    sellos = [f.adquirido_utc for f in focos if f.adquirido_utc]
    if not sellos:
        return focos
    from datetime import datetime, timedelta

    try:
        corte = (
            datetime.fromisoformat(max(sellos).replace("Z", "+00:00")) - timedelta(hours=horas)
        ).strftime("%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        # Un sello ilegible no puede tirar la corrida: se publica sin recortar,
        # que es lo que se hacia antes de que este recorte existiera.
        _log.warning("sello de tiempo ilegible; no se recorta la ventana", extra={"context": {}})
        return focos

    dentro = [f for f in focos if not f.adquirido_utc or f.adquirido_utc >= corte]
    if len(dentro) < len(focos):
        fuera = [f for f in focos if f.adquirido_utc and f.adquirido_utc < corte]
        _log.info(
            "detecciones fuera de la ventana declarada",
            extra={
                "context": {
                    "horas": horas,
                    "descartadas": len(fuera),
                    "frp_descartado_mw": round(sum(f.frp for f in fuera), 1),
                    "mas_antigua": min((f.adquirido_utc for f in fuera), default=""),
                }
            },
        )
    return dentro


def _fetcher_por_defecto() -> Fetcher:
    from ..common.http import HttpFetcher

    return HttpFetcher()
