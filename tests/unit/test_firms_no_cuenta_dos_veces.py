"""FIRMS: dos regiones que se solapan, y una ventana que se aplicaba tarde.

**El solape.** «South_America» y «Central_America» son la particion del
proveedor, no la geografica: su caja comun cubre el norte de Colombia y
Venezuela, Panama, Costa Rica y Trinidad. Los seis ficheros se concatenaban sin
mas, asi que cada deteccion de esa franja llegaba **dos veces**, del mismo
satelite y con los mismos valores. No se cae nada: sube el conteo, el FRP se
suma dos veces y esas celdas publican el doble de fuego. Medido el dia de la
auditoria: 1.885 claves con exactamente dos copias, 889 celdas con el conteo
duplicado y **11.930 MW inventados**.

**La ventana.** El recorte a 24 h vivia sobre las celdas ya agregadas y
conservaba la celda entera si su deteccion mas reciente entraba. Una celda con
una deteccion de hace dos horas y otra de hace treinta y nueve se publicaba con
las dos dentro. Medido: **5.158 detecciones fuera de ventana, 66.794 MW**, en un
fichero que declara `ventana_horas: 24`.
"""

from __future__ import annotations

import pytest

from pipelines.p5_incendios.firms import (
    REGIONES,
    VENTANA,
    Foco,
    clave_de_deteccion,
    en_la_ventana,
    fetch_focos,
)
from pipelines.p5_incendios.incendios import VENTANA_HORAS

CABECERA = "latitude,longitude,bright_ti4,acq_date,acq_time,satellite,confidence,frp,daynight\n"


def _fila(lat: float, lon: float, hora: str, sat: str = "N", frp: float = 10.0) -> str:
    return f"{lat},{lon},320.5,2026-09-05,{hora},{sat},nominal,{frp},D\n"


def _foco(lat: float, lon: float, utc: str, sat: str = "N", frp: float = 10.0) -> Foco:
    return Foco(
        lon=lon,
        lat=lat,
        confianza="nominal",
        frp=frp,
        adquirido_utc=utc,
        satelite=sat,
        brillo_k=320.5,
        dia_noche="D",
    )


# --- El solape entre regiones ----------------------------------------------


def test_la_misma_deteccion_en_dos_regiones_cuenta_una_vez() -> None:
    """El caso exacto: una deteccion del norte de Colombia en los dos ficheros."""

    class _Solapado:
        """Sirve la misma deteccion a las dos regiones de cada satelite.

        La columna `satellite` sale del propio fichero, como en FIRMS: los tres
        satelites publican nombres distintos y las dos regiones del mismo
        satelite publican el mismo. Es justo lo que hace que el duplicado sea
        indistinguible de una deteccion buena si no se mira la clave entera.
        """

        def get_bytes(self, url: str) -> bytes:
            sat = "N" if "suomi" in url else ("N20" if "noaa-20" in url else "N21")
            return (CABECERA + _fila(10.5, -74.8, "1830", sat=sat)).encode("utf-8")

        def get_json(self, url: str) -> dict[str, object]:  # pragma: no cover
            raise NotImplementedError

    lectura = fetch_focos(_Solapado())

    assert lectura.pedidos == 6, "tres satelites por dos regiones"
    # Tres satelites ven el mismo fuego: son tres detecciones de verdad. Lo que
    # no puede es haber seis.
    assert len(lectura.focos) == 3, (
        f"la deteccion se cuenta {len(lectura.focos)} veces; hay tres satelites "
        f"y {len(REGIONES)} regiones solapadas"
    )


def test_dos_satelites_sobre_el_mismo_fuego_siguen_contando_dos_veces() -> None:
    """No es un duplicado: son dos sensores que vieron lo mismo.

    El modulo entero se apoya en esto —«2,9 detecciones por celda»— y una
    deduplicacion por (lon, lat, hora) a secas se lo cargaria.
    """
    focos = [
        _foco(10.5, -74.8, "2026-09-05T18:30:00Z", sat="N"),
        _foco(10.5, -74.8, "2026-09-05T18:30:00Z", sat="N21"),
    ]
    assert len({clave_de_deteccion(f) for f in focos}) == 2


def test_la_clave_distingue_hora_y_sitio() -> None:
    base = _foco(10.5, -74.8, "2026-09-05T18:30:00Z")
    otra_hora = _foco(10.5, -74.8, "2026-09-05T19:30:00Z")
    otro_sitio = _foco(10.6, -74.8, "2026-09-05T18:30:00Z")

    assert clave_de_deteccion(base) != clave_de_deteccion(otra_hora)
    assert clave_de_deteccion(base) != clave_de_deteccion(otro_sitio)


def test_la_deduplicacion_conserva_el_orden_de_lectura() -> None:
    """El fichero publicado tiene que ser estable entre corridas."""
    from pipelines.p5_incendios.firms import _sin_duplicados

    focos = [
        _foco(1.0, -70.0, "2026-09-05T10:00:00Z", frp=1.0),
        _foco(2.0, -70.0, "2026-09-05T10:00:00Z", frp=2.0),
        _foco(1.0, -70.0, "2026-09-05T10:00:00Z", frp=99.0),  # duplicada de la primera
    ]
    unicos = _sin_duplicados(focos)

    assert [f.frp for f in unicos] == [1.0, 2.0], "se conserva la primera aparicion"


# --- La ventana -------------------------------------------------------------


def test_una_deteccion_vieja_no_viaja_por_ir_en_una_celda_con_una_reciente() -> None:
    """EL CASO QUE EL RECORTE POR CELDA DEJABA PASAR."""
    focos = [
        _foco(1.0, -70.0, "2026-09-05T20:00:00Z", frp=5.0),
        # Misma zona, 39 h antes: la celda entraba y esta se colaba con ella.
        _foco(1.0, -70.0, "2026-09-04T05:00:00Z", frp=95.0),
    ]
    dentro = en_la_ventana(focos, VENTANA_HORAS)

    assert [f.frp for f in dentro] == [5.0]
    assert sum(f.frp for f in dentro) == 5.0, "los 95 MW de fuera de ventana ya no suman"


def test_la_referencia_es_el_dato_y_no_el_reloj() -> None:
    """Con el reloj, un fichero de FIRMS de hace cuatro horas saldria vacio."""
    focos = [
        _foco(1.0, -70.0, "2020-01-02T00:00:00Z"),
        _foco(2.0, -70.0, "2020-01-01T23:00:00Z"),
    ]
    assert len(en_la_ventana(focos, 24)) == 2


def test_un_sello_ilegible_no_tumba_la_corrida() -> None:
    focos = [_foco(1.0, -70.0, "el martes"), _foco(2.0, -70.0, "tambien el martes")]
    assert len(en_la_ventana(focos, 24)) == 2


def test_sin_detecciones_no_revienta() -> None:
    assert en_la_ventana([], 24) == []


# --- Que las dos ventanas hablen de lo mismo --------------------------------


def test_la_ventana_es_la_misma_en_los_dos_sitios() -> None:
    """`firms.VENTANA` elige el fichero y `VENTANA_HORAS` lo recorta.

    Dos definiciones del mismo umbral divergen en cuanto nadie las compara: si
    algun dia se pide el fichero de 48 h y el recorte sigue en 24, la mitad del
    dato descargado se tira en silencio.
    """
    assert f"{VENTANA_HORAS}h" == VENTANA


def test_el_recorte_corre_antes_de_agregar() -> None:
    """Si volviera a correr solo sobre celdas, el conteo de la celda mentiria."""
    import inspect

    from pipelines.p5_incendios import run

    fuente = inspect.getsource(run.run_incendios)
    assert fuente.index("en_la_ventana(focos") < fuente.index("focos_en(bbox"), (
        "la ventana tiene que aplicarse a las detecciones antes de agruparlas"
    )


@pytest.mark.parametrize("horas", [6, 24, 48])
def test_la_ventana_nunca_devuelve_mas_de_lo_que_recibe(horas: int) -> None:
    focos = [_foco(1.0, -70.0, f"2026-09-0{d}T00:00:00Z") for d in (1, 2, 3, 4, 5)]
    assert len(en_la_ventana(focos, horas)) <= len(focos)
