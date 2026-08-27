"""La capa de focos activos: de FIRMS a celdas H3 y al visor.

El activo de exposicion es agnostico a la amenaza. Lo unico sismico del sistema
es el campo que se cruza contra el, asi que cambiarlo por fuego reutiliza casi
todo. Lo que **no** se reutiliza es el vocabulario, y ahi estan estas pruebas:
un sismo ocurre en un instante y tiene identidad; un incendio arde dias, y tres
satelites sobre el mismo fuego producen tres filas.

Medido el 26-ago-2026 contra el feed en vivo: 66.806 detecciones en LATAM en
24 h que colapsan a 22.701 celdas r8 — 2,9 detecciones por celda. Llamarlas
"incendios" multiplicaria por tres el numero de fuegos del continente.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from pipelines.p5_incendios.firms import (
    CONFIANZA_BAJA,
    REGIONES,
    SATELITES,
    Foco,
    feed_url,
    fetch_focos,
    parse_csv,
)
from pipelines.p5_incendios.focos_h3 import CeldaConFuego
from pipelines.p5_incendios.incendios import MAX_CELDAS, build_incendios, leer, write_incendios

#: La cabecera exacta que sirve FIRMS, copiada del fichero real.
CABECERA = (
    "latitude,longitude,bright_ti4,scan,track,acq_date,acq_time,satellite,"
    "confidence,version,bright_ti5,frp,daynight"
)


def _csv(*filas: str) -> str:
    return "\n".join([CABECERA, *filas]) + "\n"


# --- Lectura del CSV --------------------------------------------------------


def test_una_fila_real_se_parsea_entera() -> None:
    """Copiada tal cual del fichero de FIRMS del 26-ago-2026."""
    focos = parse_csv(
        _csv("-3.00846,-51.05265,305.35,0.71,0.75,2026-08-25,0406,N,nominal,2.0NRT,287.2,1.03,N")
    )

    assert len(focos) == 1
    f = focos[0]
    assert (f.lat, f.lon) == (-3.00846, -51.05265)
    assert f.confianza == "nominal"
    assert f.frp == 1.03
    assert f.adquirido_utc == "2026-08-25T04:06:00Z"
    assert f.dia_noche == "N"


def test_la_hora_sin_ceros_a_la_izquierda_no_salta_de_dia() -> None:
    """FIRMS manda las 04:06 como `406` y la medianoche como `0`.

    Sin rellenar a cuatro digitos, `406` se leeria como las 40:06 — una hora que
    no existe— y la deteccion acabaria fuera de la ventana de 24 h que se
    publica, o en el dia siguiente.
    """
    focos = parse_csv(
        _csv(
            "1.0,-70.0,305.0,0.4,0.4,2026-08-25,406,N,nominal,2.0NRT,287.0,1.0,N",
            "1.0,-70.0,305.0,0.4,0.4,2026-08-25,0,N,nominal,2.0NRT,287.0,1.0,N",
            "1.0,-70.0,305.0,0.4,0.4,2026-08-25,1230,N,nominal,2.0NRT,287.0,1.0,D",
        )
    )

    assert [f.adquirido_utc for f in focos] == [
        "2026-08-25T04:06:00Z",
        "2026-08-25T00:00:00Z",
        "2026-08-25T12:30:00Z",
    ]


def test_una_fila_corrupta_no_tumba_el_fichero() -> None:
    """Son decenas de miles de filas por region.

    Perder una capa continental entera por un campo mal escrito seria un fallo
    total con una causa trivial.
    """
    focos = parse_csv(
        _csv(
            "1.0,-70.0,305.0,0.4,0.4,2026-08-25,1230,N,nominal,2.0NRT,287.0,1.0,D",
            "esto,no,es,una,fila,valida,,,,,,,",
            "2.0,-71.0,305.0,0.4,0.4,2026-08-25,1230,N,high,2.0NRT,287.0,9.0,D",
        )
    )

    assert len(focos) == 2


def test_un_frp_vacio_no_revienta() -> None:
    """El campo llega vacio cuando el algoritmo no pudo estimarlo."""
    focos = parse_csv(_csv("1.0,-70.0,305.0,0.4,0.4,2026-08-25,1230,N,nominal,2.0NRT,287.0,,D"))

    assert focos[0].frp == 0.0


# --- Las URLs ---------------------------------------------------------------


def test_la_url_es_la_del_fichero_abierto() -> None:
    """Verificado el 26-ago-2026: HTTP 200 y sin `MAP_KEY`.

    La API por bbox si exige clave y raciona a 5.000 peticiones cada diez
    minutos; estos ficheros son un GET plano.
    """
    url = feed_url(("suomi-npp-viirs-c2", "SUOMI_VIIRS_C2"), "South_America")

    assert url == (
        "https://firms.modaps.eosdis.nasa.gov/data/active_fire/"
        "suomi-npp-viirs-c2/csv/SUOMI_VIIRS_C2_South_America_24h.csv"
    )


def test_se_leen_los_tres_satelites() -> None:
    """No es redundancia: los tres VIIRS se reparten las horas de paso.

    Con uno solo, media jornada queda sin cobertura.
    """
    assert len(SATELITES) == 3
    assert len(REGIONES) == 2


# --- Resistencia de la ingesta ----------------------------------------------


class _FirmsFalso:
    """Sirve lo que se le diga; revienta para las URL que se le marquen."""

    def __init__(self, texto: str, revienta: str = "") -> None:
        self.texto = texto
        self.revienta = revienta
        self.pedidas: list[str] = []

    def get_bytes(self, url: str) -> bytes:
        self.pedidas.append(url)
        if self.revienta and self.revienta in url:
            raise TimeoutError("la red")
        return self.texto.encode("utf-8")

    def get_json(self, url: str) -> Any:  # pragma: no cover - no se usa
        raise NotImplementedError


def test_un_fichero_caido_no_se_lleva_los_otros_cinco() -> None:
    """Seis peticiones a un servicio de la NASA; basta un mal minuto.

    Perder una region entera es peor que publicar con cinco sextos del dato.
    """
    fila = "1.0,-70.0,305.0,0.4,0.4,2026-08-25,1230,N,nominal,2.0NRT,287.0,1.0,D"
    firms = _FirmsFalso(_csv(fila), revienta="J1_VIIRS_C2_South_America")

    focos = fetch_focos(firms)

    assert len(firms.pedidas) == 6
    assert len(focos) == 5, "las cinco que si respondieron"


def test_la_confianza_baja_se_distingue_de_la_util() -> None:
    """FIRMS documenta que suelen ser reflejo solar, no fuego.

    Fueron 5.621 de 66.806 el dia de la medicion: no es un caso raro.
    """
    focos = parse_csv(
        _csv(
            "1.0,-70.0,305.0,0.4,0.4,2026-08-25,1230,N,low,2.0NRT,287.0,1.0,D",
            "2.0,-71.0,305.0,0.4,0.4,2026-08-25,1230,N,high,2.0NRT,287.0,9.0,D",
        )
    )

    assert [f.util for f in focos] == [False, True]
    assert focos[0].confianza == CONFIANZA_BAJA


# --- Agregacion a celdas ----------------------------------------------------


@pytest.fixture
def con() -> Any:
    from pipelines.p2_impact.exposure_join import connect

    return connect()


def _foco(
    lon: float,
    lat: float,
    *,
    conf: str = "nominal",
    frp: float = 5.0,
    hora: str = "12:00",
) -> Foco:
    return Foco(
        lon=lon,
        lat=lat,
        confianza=conf,
        frp=frp,
        adquirido_utc=f"2026-08-25T{hora}:00Z",
        satelite="N",
        dia_noche="D",
    )


@pytest.mark.geo
def test_tres_satelites_sobre_el_mismo_fuego_son_una_celda(con: Any) -> None:
    """El colapso que hace viable todo el pipeline.

    66.806 detecciones se convierten en 22.701 celdas. La unidad correcta no es
    la deteccion: es la celda, que es donde este sistema ya sabe medir.
    """
    from pipelines.p5_incendios.focos_h3 import registrar_focos

    celdas = registrar_focos(con, [_foco(-70.0, 1.0) for _ in range(3)])
    fila = con.execute("SELECT detecciones, frp_suma FROM focos_h3").fetchone()

    assert celdas == 1
    assert fila == (3, 15.0)


@pytest.mark.geo
def test_la_confianza_baja_se_cuenta_aparte_y_no_crea_celda(con: Any) -> None:
    """Publicar lo que se descarta es regla del proyecto.

    Pero una celda **solo** con detecciones dudosas no se publica: seria pintar
    fuego donde probablemente no lo hay, que es el riesgo de "cifra alarmista"
    en su forma visual.
    """
    from pipelines.p5_incendios.focos_h3 import registrar_focos

    celdas = registrar_focos(
        con,
        [
            _foco(-70.0, 1.0, conf="low"),
            _foco(-60.0, 2.0, conf="nominal"),
            _foco(-60.0, 2.0, conf="low"),
        ],
    )
    fila = con.execute("SELECT detecciones, detecciones_baja FROM focos_h3").fetchone()

    assert celdas == 1, "la celda solo con baja confianza no entra"
    assert fila == (1, 1), "pero la baja del otro sitio si se cuenta"


@pytest.mark.geo
def test_se_guarda_cuando_empezo_y_cuando_se_vio_por_ultima_vez(con: Any) -> None:
    """Es lo unico que insinua duracion sin fingir identidad de incendio."""
    from pipelines.p5_incendios.focos_h3 import registrar_focos

    registrar_focos(con, [_foco(-70.0, 1.0, hora="03:00"), _foco(-70.0, 1.0, hora="21:00")])
    fila = con.execute("SELECT primera_utc, ultima_utc FROM focos_h3").fetchone()

    assert fila == ("2026-08-25T03:00:00Z", "2026-08-25T21:00:00Z")


# --- Lo que se publica ------------------------------------------------------


def _celda(h3: str, *, pop: float = 0.0, frp: float = 1.0) -> CeldaConFuego:
    return CeldaConFuego(
        h3=h3,
        detecciones=1,
        detecciones_baja=0,
        frp_max=frp,
        frp_suma=frp,
        primera_utc="2026-08-25T12:00:00Z",
        ultima_utc="2026-08-25T12:00:00Z",
        pop=pop,
    )


def test_los_totales_se_calculan_sobre_todas_las_celdas() -> None:
    """Recortar la lista para que quepa es razonable; recortar la suma, no.

    Con 21.459 celdas en un dia normal, publicarlas todas serian megabytes que
    el visor descarga en cada carga. Pero ajustar el total nacional para que
    cuadre con la lista recortada seria publicar una cifra falsa por comodidad.
    """
    celdas = [_celda(f"88{i:013x}", pop=1.0) for i in range(MAX_CELDAS + 500)]

    datos = build_incendios(celdas)

    assert datos["totales"]["celdas"] == MAX_CELDAS + 500
    assert datos["totales"]["celdas_publicadas"] == MAX_CELDAS
    assert len(datos["celdas"]) == MAX_CELDAS
    assert datos["totales"]["pop_en_celdas_con_fuego"] == MAX_CELDAS + 500


def test_la_nota_dice_que_no_es_area_quemada() -> None:
    """El propio FIRMS desaconseja estimar area quemada con focos activos.

    Sin esta linea, "celda con fuego" se lee como "celda quemada", y de ahi a
    hectareas hay un paso que nadie deberia poder dar con este dato.
    """
    nota = build_incendios([])["nota"]

    assert "NO se estima area quemada" in nota
    assert "no es un incendio" in nota


def test_la_nota_avisa_de_que_cero_poblacion_puede_ser_falta_de_activo() -> None:
    """Diecinueve activos y el fuego no respeta fronteras.

    Una corrida regional siempre tendra celdas de paises sin activo cargado.
    Publicarlas como cero medido seria el falso negativo de siempre.
    """
    assert "no vacia" in build_incendios([])["nota"]


def test_el_fichero_trae_generado_utc_para_frescura(tmp_path: Path) -> None:
    """Es el contrato con `frescura.py`, que compara repo contra pagina."""
    write_incendios([_celda("88a86dc5abfffff")], site_dir=tmp_path)
    datos = json.loads((tmp_path / "incendios.json").read_text(encoding="utf-8"))

    assert datos["generado_utc"].endswith("Z")
    assert datos["schema"] == "centinela/incendios/1.0"


def test_sin_fichero_no_es_un_fallo(tmp_path: Path) -> None:
    assert leer(tmp_path) == {}


def test_un_fichero_corrupto_se_reconstruye(tmp_path: Path) -> None:
    (tmp_path / "incendios.json").write_text("{roto", encoding="utf-8")

    assert leer(tmp_path) == {}


def test_incendios_json_lo_vigila_frescura() -> None:
    """Escrito y no vigilado seria el patron que esta auditoria persigue."""
    from pipelines.common.frescura import FICHEROS_CON_FECHA

    assert "incendios.json" in FICHEROS_CON_FECHA


def test_ninguna_celda_con_gente_se_cae_del_recorte() -> None:
    """El fallo que solo aparecio al correr los diecinueve activos.

    Ordenando solo por potencia radiativa, de 14.984 celdas con fuego solo 636
    de las 3.760 con poblacion llegaban a publicarse: las desplazaban incendios
    enormes en Amazonia deshabitada. Este es un sistema de **exposicion**; un
    fuego con tres mil personas debajo no puede caerse de la lista porque arda
    menos que otro sin nadie.
    """
    con_gente = [_celda(f"88{i:013x}", pop=10.0, frp=1.0) for i in range(50)]
    sin_gente = [_celda(f"89{i:013x}", pop=0.0, frp=9999.0) for i in range(MAX_CELDAS)]

    datos = build_incendios([*sin_gente, *con_gente])
    publicadas = {c["h3"] for c in datos["celdas"]}

    assert all(c.h3 in publicadas for c in con_gente), "se perdio una celda con poblacion"


def test_entre_celdas_con_gente_manda_la_poblacion() -> None:
    """Si hay que cortar, se corta por quien tiene menos gente detras."""
    datos = build_incendios(
        [_celda("88a", pop=5.0, frp=900.0), _celda("88b", pop=500.0, frp=1.0)],
        max_celdas=1,
    )

    assert [c["h3"] for c in datos["celdas"]] == ["88b"]


# --- Sobre que arde ---------------------------------------------------------


def test_el_reparto_del_suelo_pondera_por_energia() -> None:
    """Mil detecciones debiles sobre cultivo no son cincuenta intensas sobre bosque.

    Contar celdas las igualaria. Lo que importa es donde cayo la energia.
    """
    from dataclasses import replace

    from pipelines.p5_incendios.incendios import build_incendios

    debil = replace(_celda("88a", frp=1.0), cultivo_pct=100.0)
    fuerte = replace(_celda("88b", frp=99.0), arbolado_pct=100.0)

    suelo = build_incendios([debil, fuerte])["suelo"]

    assert suelo["arbolado"] == 99.0
    assert suelo["cultivo"] == 1.0


def test_sin_cobertura_del_suelo_no_se_publica_un_reparto() -> None:
    """Los activos anteriores a la Fase 1 no la traen.

    Publicar ceros diria "no hay bosque" donde lo honesto es no decir nada. Es
    la misma regla que sostiene el resto del sistema: ausencia de medicion no es
    medicion de cero.
    """
    from pipelines.p5_incendios.incendios import build_incendios

    assert build_incendios([_celda("88a", frp=10.0)])["suelo"] == {}


def test_se_dice_cuantas_celdas_no_tienen_cobertura() -> None:
    """Un reparto sobre la mitad de las celdas y otro sobre todas no valen igual.

    Sin el conteo, los porcentajes parecen del total y no lo son.
    """
    from dataclasses import replace

    from pipelines.p5_incendios.incendios import build_incendios

    con = replace(_celda("88a", frp=5.0), arbolado_pct=80.0)
    sin = _celda("88b", frp=5.0)

    suelo = build_incendios([con, sin])["suelo"]

    assert suelo["celdas_medidas"] == 1
    assert suelo["celdas_sin_medir"] == 1
