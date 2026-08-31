"""Viento y humedad para los focos, desde NOAA GFS.

El panel de un foco dice cuanto arde y sobre quien, pero no **hacia donde va**.
Velocidad y direccion del viento, y humedad relativa, son las tres variables que
convierten "hay fuego aqui" en "va hacia alla".

## Por que GFS y no Open-Meteo, que era el camino obvio

El nivel gratuito de Open-Meteo es **no comercial**. Meterlo haria del cubo NC
de D8 —hoy vacio a proposito— el primer cubo con algo dentro, y contaminaria el
activo entero: el mismo dataset que hoy se redistribuye bajo CC BY 4.0 dejaria
de poderse. La regla de los tres cubos no tiene excepcion para "es una variable
mas". GFS es **dominio publico**: cubo nucleo, sin arrastre.

## Por que el filtro GRIB y no OPeNDAP

Porque OPeNDAP ya no existe. NOAA lo retiro (Service Change Notice 25-81) y
`nomads.ncep.noaa.gov/dods/...` responde 301 a una pagina que lo anuncia.
Comprobado el 31-ago-2026. El camino que quedaba era el filtro GRIB, que
recorta por variable y por region y **no pide llave**, lo que respeta D6.

## Por que no hace falta `eccodes` ni ninguna libreria C

Porque los mensajes vienen con **empaque simple** —plantilla 5.0—, no JPEG2000.
Verificado leyendo la seccion 5 del fichero real: `empaque = 0`. Eso se
decodifica con `struct` y aritmetica entera, que es lo que hace este modulo.
Meter `eccodes` en los runners por tres numeros habria sido el mayor salto de
dependencias del proyecto.

## La reticula es de 27 km y una celda H3 r8 son 5

GFS va a 0,25 grados. **El viento que se publica para una celda es el del punto
de reticula mas cercano, no el de la celda**, y por eso viaja rotulado como
aproximado hasta el visor. Sin ese rotulo seria otra cifra creible y falsa, del
mismo genero que habria sido publicar la temperatura de brillo en grados
centigrados.
"""

from __future__ import annotations

import math
import struct
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Final

from ..common.http import Fetcher
from ..common.logging import get_logger

_log = get_logger(__name__)

_FILTRO: Final[str] = "https://nomads.ncep.noaa.gov/cgi-bin/filter_gfs_0p25.pl"

#: La caja que cubre los 19 paises, con margen. Pedir el mundo entero traeria
#: decenas de megas para leer tres numeros por celda.
CAJA: Final[tuple[float, float, float, float]] = (-120.0, -30.0, 35.0, -60.0)

#: Las corridas de GFS. Cada una tarda entre tres y cinco horas en estar
#: completa, asi que la mas reciente por reloj no suele ser la mas reciente
#: disponible: hay que ir hacia atras hasta encontrar una que responda.
_CICLOS: Final[tuple[int, ...]] = (18, 12, 6, 0)

#: Cuantas corridas se prueban antes de rendirse. Cuatro son 24 h de margen;
#: mas atras el viento ya no describe el fuego de ahora.
MAX_CICLOS: Final[int] = 4

#: Identificadores GRIB2 de lo que se pide: (disciplina, categoria, parametro).
_UGRD: Final[tuple[int, int, int]] = (0, 2, 2)
_VGRD: Final[tuple[int, int, int]] = (0, 2, 3)
_RH: Final[tuple[int, int, int]] = (0, 1, 1)

#: Marca de "no se pudo medir". Se distingue de 0,0 —que es una humedad real y
#: un viento en calma— porque confundirlos publicaria calma donde hay ignorancia.
SIN_DATO: Final[float] = -1.0


class GribIlegibleError(ValueError):
    """El fichero no es un GRIB2 que este modulo sepa leer.

    Se distingue de un fallo de red a proposito: que NOMADS no conteste es
    tolerable y se reintenta con otra corrida; que conteste algo que no
    entendemos significa que el formato cambio, y eso hay que verlo.
    """


@dataclass(frozen=True, slots=True)
class Rejilla:
    """Una malla regular de lat/lon con un valor por punto."""

    ni: int
    nj: int
    lat1: float
    lon1: float
    di: float
    dj: float
    #: `True` si las filas van de norte a sur.
    #:
    #: NO SE DA POR SUPUESTO, Y NO ES ACADEMICO: el GFS global manda las filas
    #: de norte a sur, pero **el recorte del filtro las manda del sur al norte**
    #: —comprobado, `lat1 = -60`—. Darlo por hecho habria volteado el mapa
    #: entero sin que ningun numero dejara de ser plausible: el viento del
    #: Caribe habria salido correcto en magnitud y aplicado a la Patagonia.
    hacia_el_sur: bool
    valores: tuple[float, ...]

    def en(self, lat: float, lon: float) -> float | None:
        """El valor del punto de reticula mas cercano.

        NO interpola entre los cuatro vecinos. Con 27 km de paso, interpolar
        daria una precision aparente que el dato no tiene; el vecino mas
        cercano es igual de aproximado y no lo disimula.
        """
        paso_lon = (lon % 360.0) - (self.lon1 % 360.0)
        if paso_lon < -180.0:
            paso_lon += 360.0
        i = round(paso_lon / self.di)
        j = (
            round((self.lat1 - lat) / self.dj)
            if self.hacia_el_sur
            else round((lat - self.lat1) / self.dj)
        )
        if not (0 <= i < self.ni and 0 <= j < self.nj):
            return None
        valor = self.valores[j * self.ni + i]
        return None if math.isnan(valor) else valor


@dataclass(frozen=True, slots=True)
class Viento:
    """Lo que se publica de una celda."""

    #: Metros por segundo.
    velocidad_ms: float
    #: Grados desde los que **sopla**, no hacia los que va. Ver `_direccion`.
    direccion_grados: int
    #: Humedad relativa a 2 m, en por ciento. `SIN_DATO` si no se pudo leer.
    humedad_pct: float


@dataclass(slots=True)
class Lectura:
    """Que se pudo leer de GFS.

    Misma forma que la lectura de FIRMS y que el repaso, y por el mismo motivo:
    un fallo tiene que poder distinguirse de un cero.
    """

    rejillas: dict[str, Rejilla] = field(default_factory=dict)
    ciclo: str = ""
    fallidos: list[str] = field(default_factory=list)

    @property
    def ciego(self) -> bool:
        """No se consiguio ninguna corrida.

        Sin esto, P5 publicaria todas las celdas sin viento y la corrida saldria
        en verde: el cero silencioso, en version meteorologica.
        """
        return not self.rejillas

    def viento_en(self, lat: float, lon: float) -> Viento | None:
        u = self.rejillas.get("UGRD")
        v = self.rejillas.get("VGRD")
        rh = self.rejillas.get("RH")
        if u is None or v is None:
            return None
        vu, vv = u.en(lat, lon), v.en(lat, lon)
        if vu is None or vv is None:
            return None
        humedad = rh.en(lat, lon) if rh is not None else None
        return Viento(
            velocidad_ms=round(math.hypot(vu, vv), 1),
            direccion_grados=_direccion(vu, vv),
            humedad_pct=round(humedad, 1) if humedad is not None else SIN_DATO,
        )


def _direccion(u: float, v: float) -> int:
    """De donde sopla, en grados, contando 0 = norte y creciendo al este.

    ES LA CONVENCION METEOROLOGICA Y ES LA CONTRARIA A LA INTUITIVA. Un "viento
    del norte" va **hacia** el sur. `u` y `v` son las componentes del vector de
    movimiento, asi que hay que darles la vuelta:

        direccion = (270 - atan2(v, u) en grados) mod 360

    Publicar la direccion del vector sin invertir daria un numero perfectamente
    plausible y exactamente al reves, que en un mapa de incendios significa
    mandar a alguien hacia el fuego.

    El modulo va DESPUES de redondear, no antes: 359,7 grados redondea a 360, y
    360 no existe en una escala de rumbos que empieza en 0. Salio en la primera
    corrida contra datos reales.
    """
    return round((270.0 - math.degrees(math.atan2(v, u))) % 360.0) % 360


def url_del_ciclo(dia: str, hora: int) -> str:
    """El filtro GRIB, recortado a las tres variables y a la caja de LATAM."""
    izq, der, arriba, abajo = CAJA
    return (
        f"{_FILTRO}?dir=%2Fgfs.{dia}%2F{hora:02d}%2Fatmos"
        f"&file=gfs.t{hora:02d}z.pgrb2.0p25.f000"
        "&var_UGRD=on&var_VGRD=on&var_RH=on"
        "&lev_10_m_above_ground=on&lev_2_m_above_ground=on"
        f"&subregion=&leftlon={izq}&rightlon={der}&toplat={arriba}&bottomlat={abajo}"
    )


def ciclos_recientes(ahora: datetime | None = None) -> list[tuple[str, int]]:
    """Las corridas a probar, de la mas reciente a la mas vieja."""
    momento = ahora or datetime.now(UTC)
    salida: list[tuple[str, int]] = []
    for atras in range(2):
        dia = (momento - timedelta(days=atras)).strftime("%Y%m%d")
        for hora in _CICLOS:
            if atras == 0 and hora > momento.hour:
                continue
            salida.append((dia, hora))
    return salida[:MAX_CICLOS]


def descargar(fetcher: Fetcher, *, ahora: datetime | None = None) -> Lectura:
    """La corrida completa mas reciente que responda."""
    lectura = Lectura()
    for dia, hora in ciclos_recientes(ahora):
        etiqueta = f"{dia}/{hora:02d}z"
        try:
            rejillas = leer_grib2(fetcher.get_bytes(url_del_ciclo(dia, hora)))
        except (OSError, ValueError) as error:
            lectura.fallidos.append(etiqueta)
            _log.warning(
                "corrida de GFS no disponible",
                extra={"context": {"ciclo": etiqueta, "error": str(error)}},
            )
            continue
        if "UGRD" not in rejillas or "VGRD" not in rejillas:
            lectura.fallidos.append(etiqueta)
            _log.warning(
                "la corrida no trae viento",
                extra={"context": {"ciclo": etiqueta, "trae": sorted(rejillas)}},
            )
            continue
        lectura.rejillas = rejillas
        lectura.ciclo = etiqueta
        _log.info(
            "viento leido",
            extra={"context": {"ciclo": etiqueta, "variables": sorted(rejillas)}},
        )
        return lectura
    return lectura


# --- El lector de GRIB2 -----------------------------------------------------
#
# Solo lo que hace falta: plantilla de reticula 3.0 (lat/lon regular) y empaque
# simple 5.0. Cualquier otra cosa levanta `GribIlegible` en vez de devolver
# numeros inventados.


def leer_grib2(crudo: bytes) -> dict[str, Rejilla]:
    """Decodifica los mensajes que reconoce y descarta el resto."""
    salida: dict[str, Rejilla] = {}
    nombres = {_UGRD: "UGRD", _VGRD: "VGRD", _RH: "RH"}
    off = 0
    while True:
        inicio = crudo.find(b"GRIB", off)
        if inicio < 0 or inicio + 16 > len(crudo):
            break
        disciplina = crudo[inicio + 6]
        largo = struct.unpack(">Q", crudo[inicio + 8 : inicio + 16])[0]
        if largo <= 0 or inicio + largo > len(crudo):
            break
        nombre, rejilla = _leer_mensaje(crudo[inicio : inicio + largo], disciplina, nombres)
        if nombre and rejilla is not None:
            salida.setdefault(nombre, rejilla)
        off = inicio + largo
    if not salida:
        raise GribIlegibleError("ningun mensaje reconocible en el fichero")
    return salida


def _leer_mensaje(
    msg: bytes, disciplina: int, nombres: dict[tuple[int, int, int], str]
) -> tuple[str, Rejilla | None]:
    p = 16
    nombre = ""
    forma: dict[str, float] = {}
    empaque: tuple[float, int, int, int] | None = None
    mascara: bytes | None = None
    datos = b""
    while p < len(msg) - 4:
        largo = struct.unpack(">I", msg[p : p + 4])[0]
        if largo <= 0 or p + largo > len(msg):
            break
        seccion = msg[p + 4]
        if seccion == 3:
            forma = _seccion_reticula(msg, p)
        elif seccion == 4:
            nombre = nombres.get((disciplina, msg[p + 9], msg[p + 10]), "")
        elif seccion == 5:
            empaque = _seccion_empaque(msg, p)
        elif seccion == 6:
            mascara = None if msg[p + 5] == 255 else msg[p + 6 : p + largo]
        elif seccion == 7:
            datos = msg[p + 5 : p + largo]
        p += largo

    if not nombre or not forma or empaque is None:
        return nombre, None

    referencia, escala_bin, escala_dec, bits = empaque
    total = int(forma["ni"]) * int(forma["nj"])
    return nombre, Rejilla(
        ni=int(forma["ni"]),
        nj=int(forma["nj"]),
        lat1=forma["lat1"],
        lon1=forma["lon1"],
        di=forma["di"],
        dj=forma["dj"],
        hacia_el_sur=bool(forma["hacia_el_sur"]),
        valores=_desempaquetar(datos, bits, referencia, escala_bin, escala_dec, total, mascara),
    )


def _grados(crudo: bytes) -> float:
    """Lat/lon de GRIB2: microgrados, y el signo va en el bit alto.

    No es complemento a dos. Leerlo como tal da -2.087 grados de latitud, que
    fue exactamente el primer resultado al escribir esto.
    """
    bruto = int(struct.unpack(">I", crudo)[0])
    valor = (bruto & 0x7FFFFFFF) / 1e6
    return -valor if bruto & 0x80000000 else valor


def _entero_con_signo(crudo: bytes) -> int:
    """Igual que `_grados`, pero para los factores de escala de dos octetos."""
    bruto = int(struct.unpack(">H", crudo)[0])
    valor = bruto & 0x7FFF
    return -valor if bruto & 0x8000 else valor


def _seccion_reticula(msg: bytes, p: int) -> dict[str, float]:
    plantilla = struct.unpack(">H", msg[p + 12 : p + 14])[0]
    if plantilla != 0:
        raise GribIlegibleError(
            f"plantilla de reticula {plantilla}, se esperaba 0 (lat/lon regular)"
        )
    lat1 = _grados(msg[p + 46 : p + 50])
    lat2 = _grados(msg[p + 55 : p + 59])
    return {
        "ni": float(struct.unpack(">I", msg[p + 30 : p + 34])[0]),
        "nj": float(struct.unpack(">I", msg[p + 34 : p + 38])[0]),
        "lat1": lat1,
        "lon1": _grados(msg[p + 50 : p + 54]),
        "di": struct.unpack(">I", msg[p + 63 : p + 67])[0] / 1e6,
        "dj": struct.unpack(">I", msg[p + 67 : p + 71])[0] / 1e6,
        # El modo de barrido lleva un bit para esto, pero se corrobora con
        # lat1 > lat2 en vez de fiarse de el: es el mismo dato dicho dos veces
        # y aqui equivocarse voltea el mapa entero.
        "hacia_el_sur": float(lat1 > lat2),
    }


def _seccion_empaque(msg: bytes, p: int) -> tuple[float, int, int, int]:
    plantilla = struct.unpack(">H", msg[p + 9 : p + 11])[0]
    if plantilla != 0:
        raise GribIlegibleError(
            f"empaque {plantilla}, se esperaba 0 (simple). JPEG2000 o complejo "
            "exigirian una libreria C que este proyecto no tiene."
        )
    return (
        struct.unpack(">f", msg[p + 11 : p + 15])[0],
        _entero_con_signo(msg[p + 15 : p + 17]),
        _entero_con_signo(msg[p + 17 : p + 19]),
        msg[p + 19],
    )


def _desempaquetar(
    datos: bytes,
    bits: int,
    referencia: float,
    escala_bin: int,
    escala_dec: int,
    total: int,
    mascara: bytes | None,
) -> tuple[float, ...]:
    """`valor = (referencia + entero * 2^E) / 10^D`, bit a bit.

    Con `bits == 0` el campo es constante: todos los puntos valen la
    referencia. No es un caso raro —una humedad uniforme lo produce— y tratarlo
    como "sin datos" borraria la region entera.
    """
    factor_bin = 2.0**escala_bin
    factor_dec = 10.0**escala_dec
    presentes = _puntos_presentes(mascara, total)
    cuantos = sum(presentes)

    if bits == 0:
        constante = referencia / factor_dec
        return tuple(constante if hay else math.nan for hay in presentes)

    entero = int.from_bytes(datos, "big")
    # El ultimo octeto se rellena con ceros hasta cerrar byte; sin descartarlos
    # todos los valores salen corridos.
    sobran = len(datos) * 8 - cuantos * bits
    if sobran > 0:
        entero >>= sobran
    tope = (1 << bits) - 1

    crudos = [0] * cuantos
    for k in range(cuantos - 1, -1, -1):
        crudos[k] = entero & tope
        entero >>= bits

    salida: list[float] = []
    leidos = 0
    for hay in presentes:
        if hay:
            salida.append((referencia + crudos[leidos] * factor_bin) / factor_dec)
            leidos += 1
        else:
            salida.append(math.nan)
    return tuple(salida)


def _puntos_presentes(mascara: bytes | None, total: int) -> list[bool]:
    if mascara is None:
        return [True] * total
    return [bool(mascara[i >> 3] & (0x80 >> (i & 7))) for i in range(total)]
