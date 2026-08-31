"""El viento de GFS: el lector de GRIB2 y lo que se publica.

Las pruebas arman GRIB2 sinteticos byte a byte en vez de guardar un fichero de
NOMADS. No es purismo: un fichero real de 600 KB en el repo seria un dato de
prueba —justo lo que este proyecto saco a proposito— y ademas no permitiria
comprobar los casos que importan, como un empaque JPEG2000 o una reticula
volteada, porque NOMADS no los sirve.
"""

from __future__ import annotations

import math
import struct
from datetime import UTC, datetime

import pytest

from pipelines.p5_incendios.viento import (
    MAX_CICLOS,
    SIN_DATO,
    GribIlegibleError,
    Lectura,
    Rejilla,
    _direccion,
    ciclos_recientes,
    descargar,
    leer_grib2,
    url_del_ciclo,
)

UGRD = (0, 2, 2)
VGRD = (0, 2, 3)
RH = (0, 1, 1)


def _grados(valor: float) -> bytes:
    """Microgrados con el signo en el bit alto, como manda GRIB2."""
    bruto = round(abs(valor) * 1e6)
    if valor < 0:
        bruto |= 0x80000000
    return struct.pack(">I", bruto)


def _mensaje(
    valores: list[float],
    *,
    ni: int,
    nj: int,
    variable: tuple[int, int, int] = UGRD,
    lat1: float = 10.0,
    lon1: float = -80.0,
    lat2: float = 0.0,
    di: float = 0.25,
    dj: float = 0.25,
    bits: int = 12,
    plantilla_empaque: int = 0,
    plantilla_reticula: int = 0,
    mascara: list[bool] | None = None,
) -> bytes:
    """Un mensaje GRIB2 con empaque simple, armado a mano."""
    disciplina, categoria, parametro = variable
    npts = ni * nj

    presentes = [v for v, hay in zip(valores, mascara or [True] * npts, strict=True) if hay]
    referencia = min(presentes) if presentes else 0.0
    if bits > 0 and presentes:
        span = max(presentes) - referencia
        # Se elige la escala binaria para que el mayor valor quepa en `bits`.
        escala = 0
        while span / (2.0**escala) > (1 << bits) - 1:
            escala += 1
    else:
        escala = 0

    bruto = 0
    for v in presentes:
        entero = round((v - referencia) / (2.0**escala))
        bruto = (bruto << bits) | entero
    octetos = (len(presentes) * bits + 7) // 8
    if bits > 0:
        bruto <<= octetos * 8 - len(presentes) * bits
    datos = bruto.to_bytes(octetos, "big") if bits > 0 else b""

    sec1 = struct.pack(">IB", 21, 1) + b"\x00" * 16

    sec3 = b"".join(
        [
            struct.pack(">IB", 72, 3),
            b"\x00",  # fuente
            struct.pack(">I", npts),
            b"\x00\x00",
            struct.pack(">H", plantilla_reticula),
            b"\x00" * 16,  # forma de la Tierra
            struct.pack(">II", ni, nj),
            b"\x00" * 8,  # angulo basico
            _grados(lat1),
            _grados(lon1),
            b"\x30",  # banderas de resolucion
            _grados(lat2),
            _grados(lon1 + di * (ni - 1)),
            struct.pack(">I", int(di * 1e6)),
            struct.pack(">I", int(dj * 1e6)),
            b"\x00",  # modo de barrido
        ]
    )

    sec4 = (
        struct.pack(">IB", 34, 4)
        + b"\x00\x00"
        + struct.pack(">H", 0)
        + bytes([categoria, parametro])
        + b"\x00" * 23
    )

    sec5 = b"".join(
        [
            struct.pack(">IB", 21, 5),
            struct.pack(">I", npts),
            struct.pack(">H", plantilla_empaque),
            struct.pack(">f", referencia),
            struct.pack(">H", escala),
            struct.pack(">H", 0),  # escala decimal
            bytes([bits, 0]),
        ]
    )

    if mascara is None:
        sec6 = struct.pack(">IB", 6, 6) + b"\xff"
    else:
        bits_mascara = bytearray((npts + 7) // 8)
        for i, hay in enumerate(mascara):
            if hay:
                bits_mascara[i >> 3] |= 0x80 >> (i & 7)
        sec6 = struct.pack(">IB", 6 + len(bits_mascara), 6) + b"\x00" + bytes(bits_mascara)

    sec7 = struct.pack(">IB", 5 + len(datos), 7) + datos
    sec8 = b"7777"

    cuerpo = sec1 + sec3 + sec4 + sec5 + sec6 + sec7 + sec8
    total = 16 + len(cuerpo)
    sec0 = b"GRIB" + b"\x00\x00" + bytes([disciplina, 2]) + struct.pack(">Q", total)
    return sec0 + cuerpo


# --- La direccion del viento -------------------------------------------------
#
# La prueba mas importante del modulo. Un signo cambiado aqui no rompe nada, no
# saca ningun valor de rango y pone las flechas exactamente al reves.


@pytest.mark.parametrize(
    ("u", "v", "esperado", "nombre"),
    [
        (0.0, -5.0, 0, "del norte: el aire va hacia el sur"),
        (-5.0, 0.0, 90, "del este: el aire va hacia el oeste"),
        (0.0, 5.0, 180, "del sur"),
        (5.0, 0.0, 270, "del oeste"),
        (-5.0, -5.0, 45, "del nordeste"),
    ],
)
def test_la_direccion_es_de_donde_sopla_no_hacia_donde_va(
    u: float, v: float, esperado: int, nombre: str
) -> None:
    """Convencion meteorologica, que es la contraria a la intuitiva.

    Un "viento del norte" **va hacia el sur**. Publicar la direccion del vector
    sin invertir daria un numero plausible y exactamente al reves, que en un
    mapa de incendios significa mandar a alguien hacia el fuego.
    """
    assert _direccion(u, v) == esperado, nombre


def test_la_direccion_nunca_es_360() -> None:
    """360 y 0 son el mismo rumbo, y solo uno existe en la escala.

    Salio en la primera corrida contra datos reales: `round(359.7)` da 360. El
    modulo tiene que ir despues de redondear, no antes.
    """
    for angulo in range(0, 3600):
        u = math.cos(math.radians(angulo / 10))
        v = math.sin(math.radians(angulo / 10))
        assert 0 <= _direccion(u, v) <= 359


# --- El lector de GRIB2 ------------------------------------------------------


def test_ida_y_vuelta_de_un_campo_conocido() -> None:
    valores = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]
    rejillas = leer_grib2(_mensaje(valores, ni=3, nj=2))

    leidos = rejillas["UGRD"].valores
    assert len(leidos) == 6
    for esperado, leido in zip(valores, leidos, strict=True):
        assert leido == pytest.approx(esperado, abs=0.01)


def test_los_tres_campos_salen_por_su_nombre() -> None:
    crudo = (
        _mensaje([1.0] * 4, ni=2, nj=2, variable=UGRD)
        + _mensaje([2.0] * 4, ni=2, nj=2, variable=VGRD)
        + _mensaje([80.0] * 4, ni=2, nj=2, variable=RH)
    )

    assert sorted(leer_grib2(crudo)) == ["RH", "UGRD", "VGRD"]


def test_un_campo_constante_no_es_un_campo_vacio() -> None:
    """Con `bits == 0` GRIB2 no escribe datos: todos los puntos valen la
    referencia. Tratarlo como "sin dato" borraria la region entera, y una
    humedad uniforme lo produce de verdad."""
    rejillas = leer_grib2(_mensaje([7.5] * 4, ni=2, nj=2, bits=0))

    assert rejillas["UGRD"].valores == (7.5, 7.5, 7.5, 7.5)


def test_los_puntos_sin_dato_quedan_como_nan_y_no_como_cero() -> None:
    """Cero es un viento en calma, que es un dato. La ausencia no lo es."""
    rejillas = leer_grib2(
        _mensaje([1.0, 2.0, 3.0, 4.0], ni=2, nj=2, mascara=[True, False, True, True])
    )

    valores = rejillas["UGRD"].valores
    assert math.isnan(valores[1])
    assert valores[0] == pytest.approx(1.0, abs=0.01)


def test_un_empaque_que_no_sabemos_leer_se_dice_en_vez_de_inventarse() -> None:
    """JPEG2000 exigiria una libreria C. Devolver ceros en su lugar seria el
    cero silencioso otra vez."""
    with pytest.raises(GribIlegibleError, match="empaque 40"):
        leer_grib2(_mensaje([1.0] * 4, ni=2, nj=2, plantilla_empaque=40))


def test_una_reticula_que_no_es_lat_lon_regular_tambien() -> None:
    with pytest.raises(GribIlegibleError, match="plantilla de reticula 30"):
        leer_grib2(_mensaje([1.0] * 4, ni=2, nj=2, plantilla_reticula=30))


def test_un_fichero_que_no_es_grib_no_devuelve_una_reticula_vacia() -> None:
    with pytest.raises(GribIlegibleError):
        leer_grib2(b"esto no es un GRIB")


# --- Buscar un punto ---------------------------------------------------------


def _rejilla(hacia_el_sur: bool) -> Rejilla:
    # 3x3 empezando en (10, -80) con paso 1 grado.
    return Rejilla(
        ni=3,
        nj=3,
        lat1=10.0 if hacia_el_sur else 8.0,
        lon1=-80.0,
        di=1.0,
        dj=1.0,
        hacia_el_sur=hacia_el_sur,
        valores=tuple(float(i) for i in range(9)),
    )


def test_se_toma_el_punto_mas_cercano_y_no_se_interpola() -> None:
    """Con 27 km de paso, interpolar daria una precision que el dato no tiene."""
    r = _rejilla(hacia_el_sur=True)

    assert r.en(10.0, -80.0) == 0.0
    assert r.en(9.9, -79.9) == 0.0, "casi encima del primer punto"
    assert r.en(9.0, -79.0) == 4.0, "el del centro"


def test_la_reticula_volteada_se_lee_al_derecho() -> None:
    """El recorte del filtro manda las filas del sur al norte, al reves que el
    GFS global. Darlo por supuesto habria aplicado el viento del Caribe a la
    Patagonia sin que ningun numero dejara de ser plausible."""
    norte = _rejilla(hacia_el_sur=True)
    sur = _rejilla(hacia_el_sur=False)

    assert norte.en(10.0, -80.0) == 0.0, "empezando por el norte, arriba es la fila 0"
    assert sur.en(8.0, -80.0) == 0.0, "empezando por el sur, abajo es la fila 0"
    assert norte.en(8.0, -80.0) == 6.0
    assert sur.en(10.0, -80.0) == 6.0


def test_fuera_de_la_caja_no_se_inventa_un_valor() -> None:
    r = _rejilla(hacia_el_sur=True)

    assert r.en(51.5, 0.0) is None, "Londres no esta en la caja de LATAM"
    assert r.en(10.0, 100.0) is None


# --- La lectura completa -----------------------------------------------------


class _FetcherFalso:
    def __init__(self, respuestas: dict[str, bytes]) -> None:
        self.respuestas = respuestas
        self.pedidos: list[str] = []

    def get_bytes(self, url: str) -> bytes:
        self.pedidos.append(url)
        for clave, cuerpo in self.respuestas.items():
            if clave in url:
                return cuerpo
        raise OSError("404")

    def get_json(self, url: str) -> dict[str, object]:
        raise AssertionError("el viento viene en GRIB2, no en JSON")


def _corrida(**kw: object) -> bytes:
    return (
        _mensaje([-5.0] * 4, ni=2, nj=2, variable=UGRD, **kw)  # type: ignore[arg-type]
        + _mensaje([0.0] * 4, ni=2, nj=2, variable=VGRD, **kw)  # type: ignore[arg-type]
        + _mensaje([40.0] * 4, ni=2, nj=2, variable=RH, **kw)  # type: ignore[arg-type]
    )


def test_se_coge_la_corrida_mas_reciente_que_responda() -> None:
    """La mas reciente por reloj no suele estar completa: GFS tarda entre tres y
    cinco horas. Hay que ir hacia atras."""
    ahora = datetime(2026, 8, 31, 20, 0, tzinfo=UTC)
    fetcher = _FetcherFalso({"gfs.20260831%2F06": _corrida()})

    lectura = descargar(fetcher, ahora=ahora)

    assert lectura.ciclo == "20260831/06z"
    assert not lectura.ciego
    assert lectura.fallidos == ["20260831/18z", "20260831/12z"]


def test_si_no_responde_ninguna_la_lectura_es_ciega() -> None:
    """Y eso tiene que poder distinguirse de "no hace viento".

    Sin esto, P5 publicaria el fuego sin viento y la corrida saldria en verde:
    el cero silencioso, en version meteorologica.
    """
    lectura = descargar(_FetcherFalso({}), ahora=datetime(2026, 8, 31, 20, 0, tzinfo=UTC))

    assert lectura.ciego
    assert len(lectura.fallidos) == MAX_CICLOS


def test_una_corrida_sin_viento_no_vale_aunque_traiga_humedad() -> None:
    """El viento es lo que se vino a buscar. Aceptar la corrida por la humedad
    dejaria `viento_en` devolviendo `None` en todas las celdas con la lectura
    diciendo que fue bien."""
    solo_hr = _mensaje([40.0] * 4, ni=2, nj=2, variable=RH)
    lectura = descargar(
        _FetcherFalso({"gfs.20260831": solo_hr}), ahora=datetime(2026, 8, 31, 20, 0, tzinfo=UTC)
    )

    assert lectura.ciego


def test_de_la_lectura_sale_velocidad_direccion_y_humedad() -> None:
    fetcher = _FetcherFalso({"gfs.": _corrida(lat1=10.0, lon1=-80.0)})

    lectura = descargar(fetcher, ahora=datetime(2026, 8, 31, 20, 0, tzinfo=UTC))
    viento = lectura.viento_en(10.0, -80.0)

    assert viento is not None
    assert viento.velocidad_ms == pytest.approx(5.0, abs=0.1)
    assert viento.direccion_grados == 90, "u negativa es viento del este"
    assert viento.humedad_pct == pytest.approx(40.0, abs=0.1)


def test_sin_humedad_se_marca_y_no_se_pone_cero() -> None:
    """Cero por ciento de humedad es un desierto extremo, no una ausencia."""
    sin_hr = _mensaje([-5.0] * 4, ni=2, nj=2, variable=UGRD) + _mensaje(
        [0.0] * 4, ni=2, nj=2, variable=VGRD
    )
    lectura = descargar(
        _FetcherFalso({"gfs.": sin_hr}), ahora=datetime(2026, 8, 31, 20, 0, tzinfo=UTC)
    )

    viento = lectura.viento_en(10.0, -80.0)
    assert viento is not None
    assert viento.humedad_pct == SIN_DATO


def test_una_lectura_vacia_no_da_viento() -> None:
    assert Lectura().viento_en(0.0, 0.0) is None


# --- Los ciclos y la URL -----------------------------------------------------


def test_los_ciclos_van_del_mas_reciente_al_mas_viejo() -> None:
    ciclos = ciclos_recientes(datetime(2026, 8, 31, 13, 0, tzinfo=UTC))

    assert ciclos[0] == ("20260831", 12), "a las 13 UTC la de las 12 es la ultima emitida"
    assert ciclos == [
        ("20260831", 12),
        ("20260831", 6),
        ("20260831", 0),
        ("20260830", 18),
    ]


def test_de_madrugada_se_baja_al_dia_anterior() -> None:
    ciclos = ciclos_recientes(datetime(2026, 8, 31, 1, 0, tzinfo=UTC))

    assert ciclos[0] == ("20260831", 0)
    assert ciclos[1] == ("20260830", 18)


def test_la_url_pide_solo_las_tres_variables_y_solo_latam() -> None:
    """Pedir el mundo entero traeria decenas de megas para leer tres numeros."""
    url = url_del_ciclo("20260831", 6)

    assert "var_UGRD=on" in url and "var_VGRD=on" in url and "var_RH=on" in url
    assert "lev_10_m_above_ground=on" in url
    assert "leftlon=-120.0" in url and "rightlon=-30.0" in url
    assert "gfs.20260831" in url and "t06z" in url


def test_no_hay_llave_en_la_url() -> None:
    """D6: el sistema no tiene llaves. GFS es publico y asi tiene que seguir."""
    url = url_del_ciclo("20260831", 6).lower()

    for sospechoso in ("key", "token", "api", "secret", "auth"):
        assert sospechoso not in url, f"aparece '{sospechoso}' en la URL de GFS"
