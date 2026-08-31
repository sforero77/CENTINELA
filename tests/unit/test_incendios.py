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

from pipelines.common.constants import H3_RES_COMPUTE
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

    lectura = fetch_focos(firms)

    assert len(firms.pedidas) == 6
    assert len(lectura.focos) == 5, "las cinco que si respondieron"
    assert lectura.fallidos == ["J1_VIIRS_C2/South_America"], (
        "la merma tiene que salir del log: sin esto, quien mira la corrida no "
        "sabe que se publico con cinco sextos del dato"
    )
    assert lectura.pedidos == 6
    assert not lectura.ciego, "cinco de seis no es quedarse a ciegas"


def test_si_fallan_todos_los_ficheros_la_corrida_no_sale_en_verde() -> None:
    """El fallo del 30-ago-2026, cazado en produccion validando el despliegue.

    Fallaron los seis ficheros —FIRMS tuvo un mal minuto—, el pipeline devolvio
    cero detecciones y cero celdas, y el workflow salio **verde**. La capa
    publicada se salvo porque ya se niega a publicar ceros, pero si FIRMS se
    cayera una semana el visor serviria fuego de hace siete dias sin una sola
    alarma.

    Que fallen algunos es tolerable y se sigue publicando; que fallen todos es
    quedarse a ciegas, y eso hay que decirlo.
    """
    # "VIIRS" esta en las seis URL: revientan todas.
    fila = "1.0,-70.0,305.0,0.4,0.4,2026-08-25,1230,N,nominal,2.0NRT,287.0,1.0,D"
    firms = _FirmsFalso(_csv(fila), revienta="VIIRS")

    lectura = fetch_focos(firms)

    assert lectura.focos == []
    assert len(lectura.fallidos) == 6
    assert lectura.ciego, "seis de seis es quedarse a ciegas"


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
        brillo_k=320.0,
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


def _celda(
    h3: str, *, pop: float = 0.0, frp: float = 1.0, ultima: str = "2026-08-25T12:00:00Z"
) -> CeldaConFuego:
    return CeldaConFuego(
        h3=h3,
        detecciones=1,
        detecciones_baja=0,
        frp_max=frp,
        frp_suma=frp,
        brillo_max_k=340.0,
        primera_utc="2026-08-25T12:00:00Z",
        ultima_utc=ultima,
        pop=pop,
    )


def test_ahora_se_publican_todas_las_celdas() -> None:
    """El tope estuvo en 4.000 por una razon que nadie habia medido.

    Decia: "publicarlas todas serian varios megabytes que el visor descarga en
    cada carga". GitHub Pages sirve el fichero comprimido, asi que no. Medido el
    31-ago-2026 por la red y en un navegador de verdad:

        13.031 celdas -> 203 KB por la red, 97 MB de memoria, 60 cuadros/s
        23.000 celdas -> 304 KB por la red, 109 MB, 60 cuadros/s

    Contra los 136 KB de las 4.000 de entonces. Publicarlo todo cuesta 67 KB.

    Importa porque los indicadores del tablero se cruzan contra lo publicado: con
    una muestra de 4.000 de 13.031, filtrar por pais daba cifras que no eran las
    del pais, sino las de la parte que cupo.
    """
    celdas = [_celda(f"88{i:013x}", pop=1.0) for i in range(13_031)]

    datos = build_incendios(celdas)

    assert datos["totales"]["celdas"] == 13_031
    assert datos["totales"]["celdas_publicadas"] == 13_031
    assert len(datos["celdas"]) == 13_031, "se recorto algo que cabia"


def test_los_totales_se_calculan_sobre_todas_las_celdas() -> None:
    """Ajustar la suma nacional para que cuadre con una lista recortada seria
    publicar una cifra falsa por comodidad.

    Sigue vigente aunque hoy no se recorte: el tope de seguridad existe, y el
    dia que muerda los totales tienen que seguir siendo los de verdad.
    """
    celdas = [_celda(f"88{i:013x}", pop=1.0) for i in range(20)]

    datos = build_incendios(celdas, max_celdas=12)

    assert datos["totales"]["celdas"] == 20
    assert datos["totales"]["celdas_publicadas"] == 12
    assert len(datos["celdas"]) == 12
    assert datos["totales"]["pop_en_celdas_con_fuego"] == 20, "el total no se recorta"


def test_el_tope_es_de_seguridad_y_esta_muy_por_encima_del_peor_dia() -> None:
    """22.701 celdas fue el peor dia visto. Un tope por debajo de eso volveria a
    convertir el fichero en una muestra sin que nadie se entere."""
    assert MAX_CELDAS >= 50_000


def test_si_el_tope_llegara_a_morder_se_dice_a_gritos(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Un recorte mudo convierte "esto es todo lo que arde" en una mentira sin
    que nada falle. Es la familia del cero silencioso."""
    import logging

    celdas = [_celda(f"88{i:013x}", pop=1.0) for i in range(20)]

    with caplog.at_level(logging.ERROR):
        build_incendios(celdas, max_celdas=5)

    assert any("NO es todo lo que arde" in r.message for r in caplog.records)


def test_el_json_va_sin_sangria(tmp_path: Path) -> None:
    """Con todas las celdas dentro, `indent=2` son unos 2 MB de espacios en un
    fichero que ninguna persona lee: lo consume el visor."""
    write_incendios([_celda("88abc", pop=1.0)], site_dir=tmp_path)

    crudo = (tmp_path / "incendios.json").read_text(encoding="utf-8")

    salto = chr(10)
    assert salto + "  " not in crudo, "el fichero sale sangrado"
    assert crudo.count(salto) == 1, "el JSON deberia ocupar una sola linea"


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


def test_los_servicios_bajo_fuego_son_un_total_publicado() -> None:
    """Un hospital dentro de una celda con fuego decide un traslado.

    Estaba solo en el popup de esa celda concreta, entre catorce mil. El mismo
    criterio que en el lado sismico: el orden de un tablero lo fija para que
    sirve, no cuanto abulta.
    """
    from dataclasses import replace

    from pipelines.p5_incendios.incendios import build_incendios

    con_hospital = replace(_celda("88a"), salud=2, edu=5, bld=40)
    sin_nada = _celda("88b")

    t = build_incendios([con_hospital, sin_nada])["totales"]

    assert t["salud_en_celdas_con_fuego"] == 2
    assert t["edu_en_celdas_con_fuego"] == 5
    assert t["bld_en_celdas_con_fuego"] == 40


def test_el_relleno_despoblado_va_por_energia() -> None:
    """El dia que las celdas con gente no llenen el cupo, el resto no puede
    entrar en el orden en que DuckDB las escupa.

    Encontrado el 30-ago-2026 auditando el artefacto E2E: `sin_gente` no se
    ordenaba antes del corte. Ese dia habia 5.244 celdas pobladas para 4.000
    puestos y el fallo no se manifestaba — que es exactamente cuando conviene
    arreglarlo, porque el dia tranquilo en que se manifieste nadie va a estar
    mirando.
    """
    from pipelines.p5_incendios.incendios import _prioridad

    sin_gente = [
        _celda("8928308280fffff", pop=0, frp=5.0),
        _celda("8928308280bffff", pop=0, frp=90.0),
        _celda("89283082807ffff", pop=0, frp=40.0),
    ]
    con_gente = [_celda("8928308283bffff", pop=120, frp=1.0)]

    publicadas = _prioridad([*sin_gente, *con_gente], max_celdas=3)

    assert publicadas[0].pop == 120, "la gente va primero, arda lo que arda"
    assert [c.frp_suma for c in publicadas[1:]] == [90.0, 40.0], (
        "el relleno despoblado tiene que entrar por energia, no por orden de llegada"
    )


def test_la_celda_publica_de_que_pais_es() -> None:
    """Sin `iso3` el visor no puede filtrar el fuego por país como filtra los sismos.

    El activo de exposición lo sabe —es una columna de `exposure_h3`— y el cruce
    no lo traía: la información existía y no llegaba a la pantalla. El mismo
    patrón que este repositorio ya cazó con `celdas_publicadas`.
    """
    from dataclasses import asdict

    from pipelines.p5_incendios.focos_h3 import CeldaConFuego

    celda = CeldaConFuego(
        h3="8866d32a65fffff",
        detecciones=3,
        detecciones_baja=0,
        frp_max=12.0,
        frp_suma=30.0,
        brillo_max_k=340.0,
        primera_utc="2026-08-30T00:00:00Z",
        ultima_utc="2026-08-30T06:00:00Z",
        iso3="BRA",
    )

    assert asdict(celda)["iso3"] == "BRA", "el país no llega al JSON publicado"


def test_una_celda_fuera_de_los_activos_no_finge_un_pais() -> None:
    """El fuego no respeta fronteras: una corrida regional siempre tiene celdas
    de países cuyo activo no está cargado.

    Cadena vacía y no un ISO3 por defecto: «no se sabe» tiene que poder
    distinguirse de «es de aquí», que es la misma regla por la que la población
    de esas celdas se omite en vez de publicarse como cero.
    """
    from pipelines.p5_incendios.focos_h3 import CeldaConFuego

    celda = CeldaConFuego(
        h3="8866d32a65fffff",
        detecciones=1,
        detecciones_baja=0,
        frp_max=4.9,
        frp_suma=4.9,
        brillo_max_k=340.0,
        primera_utc="2026-08-30T00:00:00Z",
        ultima_utc="2026-08-30T00:00:00Z",
    )

    assert celda.iso3 == ""
    assert celda.pop == 0.0


def test_la_temperatura_de_brillo_se_lee_del_csv() -> None:
    """FIRMS publica trece columnas y este pipeline leía ocho.

    `bright_ti4` estaba en cada fila desde el primer día y se tiraba: la única
    intensidad publicada era el FRP.
    """
    fila = "1.0,-70.0,305.13,0.66,0.73,2026-08-25,1230,N,nominal,2.0NRT,289.79,1.89,D"
    focos = parse_csv(_csv(fila))

    assert focos[0].brillo_k == 305.13


def test_la_temperatura_es_del_pixel_y_el_maximo_es_el_agregado_correcto() -> None:
    """Promediar el píxel más caliente de una celda con los tibios de al lado da
    un número que no describe nada.

    Y no es la temperatura de la llama: es la del píxel de 375 m, que mezcla el
    fuego con el terreno frío. Los valores reales van de 299 a 367 K —26 a 94 °C—
    mientras un incendio arde por encima de 600 °C. Publicarla como «temperatura
    del incendio» sería una cifra creíble y falsa.
    """
    import re
    from pathlib import Path

    fuente = (
        Path(__file__).parent.parent.parent / "pipelines" / "p5_incendios" / "focos_h3.py"
    ).read_text(encoding="utf-8")
    sql = re.search(r'SQL_CELDAS = """(.*?)"""', fuente, re.S)
    assert sql is not None
    assert "max(brillo_k)" in sql.group(1), "la celda no agrega por el máximo"
    assert "avg(brillo_k)" not in sql.group(1), "promediar diluye el píxel caliente"


def test_una_fila_sin_temperatura_no_revienta_la_lectura() -> None:
    """Un CSV al que le falte la columna sigue dando focos.

    Perder la región entera por un campo ausente sería peor que publicar sin él,
    que es la misma regla por la que un fichero caído no tumba los otros cinco.
    """
    fila = "1.0,-70.0,,0.66,0.73,2026-08-25,1230,N,nominal,2.0NRT,289.79,1.89,D"
    focos = parse_csv(_csv(fila))

    assert len(focos) == 1
    assert focos[0].brillo_k == 0.0


def test_el_fichero_no_publica_mas_horas_de_las_que_declara() -> None:
    """Declaraba 24 h y traia treinta y una.

    FIRMS publica un "active fire 24h" por satelite y por region, y los seis
    ficheros no cortan a la misma hora. Al unirlos, el span real medido el
    31-ago-2026 era de 30,9 h y nadie recortaba despues.

    Consecuencia sobre esa corrida: **425 de 4.000 celdas —10,6 %— quedaban
    fuera de las 24 h declaradas, y con ellas 130.754 personas**. La tarjeta
    decia "personas en celdas con fuego activo en 24 h" contando detecciones de
    hasta 31 horas antes.
    """
    dentro = _celda("88dentro", pop=10.0, ultima="2026-08-31T10:00:00Z")
    justo = _celda("88justo", pop=20.0, ultima="2026-08-30T10:30:00Z")
    fuera = _celda("88fuera", pop=1000.0, ultima="2026-08-30T03:00:00Z")

    datos = build_incendios([dentro, justo, fuera], ventana_horas=24)

    publicadas = {c["h3"] for c in datos["celdas"]}
    assert publicadas == {"88dentro", "88justo"}, "no se recorto a la ventana declarada"
    assert datos["totales"]["celdas"] == 2, "el total sigue contando lo que quedo fuera"
    assert datos["totales"]["pop_en_celdas_con_fuego"] == 30, (
        "las personas de una deteccion de hace 31 h siguen en la cifra de portada"
    )


def test_la_ventana_se_mide_desde_el_dato_y_no_desde_el_reloj() -> None:
    """Misma regla que `referenciaDelFuego` en el visor, y por el mismo motivo.

    Con el reloj, un fichero de FIRMS de hace cuatro horas dejaria la ventana de
    6 h completamente vacia aunque el dato estuviera perfecto. Ya paso una vez
    en el visor y se reporto como "el filtro de 6 h no muestra nada".
    """
    viejas = [
        _celda(f"88v{i}", pop=5.0, ultima=sello)
        for i, sello in enumerate(["2020-01-02T00:00:00Z", "2020-01-01T23:00:00Z"])
    ]

    datos = build_incendios(viejas, ventana_horas=24)

    assert len(datos["celdas"]) == 2, "se recorto contra el reloj y no contra el dato"


def test_un_sello_ilegible_no_tumba_la_corrida() -> None:
    """Publicar sin recortar es peor que no publicar nada, pero mucho mejor que
    reventar: es lo que se hacia hasta hoy."""
    c = _celda("88malo", pop=1.0, ultima="esto no es una fecha")

    datos = build_incendios([c], ventana_horas=24)

    assert len(datos["celdas"]) == 1


def test_una_celda_de_fuego_mide_lo_que_dice_el_visor() -> None:
    """SIETE VECES. Ese era el error, y estuvo publicado meses.

    D1 dice: computo en r8, agregado a r7/r6 para el visor. El lado sismico lo
    cumple —`p3_report/celdas.py` hace `h3_cell_to_parent(h3_08, 7)` y publica
    indices `87...`—. **P5 no agrega**: publica los `88...` de r8 tal cual.

    El visor aplicaba a esos r8 la constante `AREA_CELDA_KM2 = 5.2`, que es el
    area de r7. Cada foco se anunciaba con SIETE VECES su superficie: uno de
    cien celdas decia 520 km² cuando son 74. Y el rotulo de la capa prometia
    "hexagonos de 5,2 km²" sobre hexagonos de 0,74.

    Nadie lo caza salvo una prueba que compare la constante del visor contra la
    geometria de verdad, que es esta.
    """
    import re
    from pathlib import Path

    import h3

    real = h3.average_hexagon_area(H3_RES_COMPUTE, unit="km^2")
    app = (Path(__file__).parent.parent.parent / "site" / "assets" / "app.js").read_text(
        encoding="utf-8"
    )
    m = re.search(r"const AREA_CELDA_FUEGO_KM2 = ([\d.]+);", app)
    assert m is not None, "el visor ya no declara el area de una celda de fuego"
    declarada = float(m.group(1))

    assert abs(declarada - real) < 0.01, (
        f"el visor dice {declarada} km² por celda y una r{H3_RES_COMPUTE} mide {real:.3f}"
    )


def test_el_visor_no_usa_el_area_de_r7_para_el_fuego() -> None:
    """La constante equivocada sigue existiendo, y con razon: el lado sismico
    publica en r7 y ahi 5,2 km² es correcto. Lo que no puede es volver a
    aplicarse a un foco."""
    from pathlib import Path

    app = (Path(__file__).parent.parent.parent / "site" / "assets" / "app.js").read_text(
        encoding="utf-8"
    )

    assert "areaKm2: celdas.length * AREA_CELDA_FUEGO_KM2," in app, (
        "el area de un foco volvio a calcularse con la constante de r7"
    )
