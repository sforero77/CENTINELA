"""El lugar del sismo, en espanol (RF-06).

Todo el producto esta en espanol y nombraba sus sismos en ingles, porque el
campo `place` de USGS llega asi y viajaba tal cual al titulo del reporte, al
hilo para redes, al mapa estatico y al visor. RF-06 pide "reporte en espanol
neutro con toponimos oficiales del pais": la segunda mitad se cumplia, la
primera no.

La regla que estas pruebas fijan es la que hace que la traduccion sea segura:
**se traduce el andamiaje, nunca el toponimo**. Traducir el nombre del sitio
produciria lugares que no existen en ningun mapa oficial, que es exactamente lo
contrario de lo que pide el requisito.
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from pipelines.common import toponimos
from pipelines.common.paths import EVENTS_DIR, REPORTS_DIR, SITE_DIR
from pipelines.common.toponimos import RUMBOS, huellas_en_ingles, traducir_lugar, traducir_pais


@pytest.mark.parametrize(
    ("ingles", "espanol"),
    [
        ("20 km W of Catia La Mar, Venezuela", "20 km al O de Catia La Mar, Venezuela"),
        ("10 km SSW of Coquimbo, Chile", "10 km al SSO de Coquimbo, Chile"),
        ("41 km SW of Quellón, Chile", "41 km al SO de Quellón, Chile"),
        ("27 km SSE of Muisne, Ecuador", "27 km al SSE de Muisne, Ecuador"),
        ("78 km NE of Navarro, Peru", "78 km al NE de Navarro, Perú"),
        ("4 km SE of Aserrío de Garichá, Panama", "4 km al SE de Aserrío de Garichá, Panamá"),
    ],
)
def test_la_forma_mas_comun_se_traduce_entera(ingles: str, espanol: str) -> None:
    """Cadenas reales del catalogo de USGS para LATAM, no ejemplos inventados."""
    assert traducir_lugar(ingles) == espanol


def test_el_toponimo_no_se_toca() -> None:
    """`Catia La Mar` es un nombre propio y no se traduce.

    Es la regla que hace segura toda la traduccion: si algun dia esto empieza a
    fallar, el sistema estara publicando lugares que no existen.
    """
    salida = traducir_lugar("20 km W of Catia La Mar, Venezuela")

    assert "Catia La Mar" in salida


def test_la_costa_y_la_region_tambien_tienen_forma_propia() -> None:
    assert (
        traducir_lugar("Near the coast of Bio-Bio, Chile") == "Cerca de la costa de Bio-Bio, Chile"
    )
    assert traducir_lugar("Off the coast of Peru") == "Cerca de la costa de Perú"
    assert traducir_lugar("Nicaragua region") == "Región de Nicaragua"


def test_los_eventos_con_nombre_propio_se_reescriben() -> None:
    """USGS reserva esta forma para los sismos que nombra: los mas grandes."""
    assert traducir_lugar("2017 Tehuantepec, Mexico Earthquake") == (
        "Terremoto de Tehuantepec, México (2017)"
    )


def test_un_pais_a_secas_no_cambia_de_forma() -> None:
    assert traducir_lugar("Nicaragua") == "Nicaragua"
    assert traducir_lugar("Peru") == "Perú"


def test_una_forma_desconocida_se_devuelve_intacta() -> None:
    """Un lugar en ingles se lee raro; uno mal traducido lleva a otro sitio.

    USGS no publica una gramatica de este campo, asi que ante algo que no se
    reconoce lo unico honesto es no tocarlo.
    """
    raro = "Somewhere odd USGS has not published before"

    assert traducir_lugar(raro) == raro


def test_un_rumbo_que_no_existe_no_se_inventa() -> None:
    """`SWW` no esta en la rosa de los vientos. Antes el original que una direccion falsa."""
    original = "12 km SWW of Algun Sitio, Chile"

    assert traducir_lugar(original) == original


def test_el_pais_solo_se_traduce_al_final() -> None:
    """Un toponimo puede contener el nombre de un pais sin ser el pais.

    `Nuevo Mexico` y `Ciudad de Mexico` son nombres de sitio; el pais es el
    ultimo segmento tras la coma y solo ese se traduce.
    """
    assert traducir_pais("Ciudad de Mexico, Mexico") == "Ciudad de Mexico, México"


def test_un_lugar_vacio_no_revienta() -> None:
    """USGS publica eventos sin `place`, y el reporte tiene que salir igual."""
    assert traducir_lugar("") == ""
    assert traducir_lugar("   ") == ""


def test_la_rosa_de_los_vientos_esta_completa() -> None:
    """Los dieciseis rumbos. Uno que falte devuelve el original en ingles."""
    assert len(RUMBOS) == 16
    assert RUMBOS["W"] == "O", "west es oeste; es el unico que de verdad cambia"
    assert RUMBOS["N"] == "N"


def test_los_lugares_se_traducen_al_entrar_al_sistema() -> None:
    """Un solo punto de entrada, o el reporte y el estado se contradicen.

    `lugar` se guarda en el `event_state` y de ahi lo copia el reporte, el
    indice, el hilo y el mapa. Traducirlo en la presentacion dejaria el estado
    en ingles y la pantalla en espanol, diciendo cosas distintas del mismo
    evento.
    """
    import inspect

    from pipelines.p1_trigger.feed import EventCandidate
    from pipelines.p2_impact.run import reconstruct_backtest_state

    for funcion in (EventCandidate.from_feature, reconstruct_backtest_state):
        assert "traducir_lugar" in inspect.getsource(funcion), (
            f"{funcion.__qualname__} guarda el lugar sin traducir"
        )


@pytest.mark.parametrize(
    ("ingles", "espanol"),
    [
        # Los tres que estaban publicados en ingles el 3-oct-2026.
        ("southern East Pacific Rise", "Sur de la dorsal del Pacífico Oriental"),
        ("northern Mid-Atlantic Ridge", "Norte de la dorsal mesoatlántica"),
        ("West Chile Rise", "Dorsal de Chile"),
        ("Central East Pacific Rise", "Centro de la dorsal del Pacífico Oriental"),
        ("Drake Passage", "Pasaje de Drake"),
        ("Easter Island region", "Región de la isla de Pascua"),
        ("Galapagos Islands, Ecuador region", "Región de las islas Galápagos, Ecuador"),
        ("south of Panama", "Al sur de Panamá"),
        ("southern Peru", "Sur de Perú"),
        ("off the coast of Central America", "Cerca de la costa de Centroamérica"),
        ("Near the coast of northern Chile", "Cerca de la costa del norte de Chile"),
    ],
)
def test_las_regiones_de_mar_abierto_tambien_se_traducen(ingles: str, espanol: str) -> None:
    """Lejos de la costa USGS escribe la region de Flinn-Engdahl, no `X km W of`.

    Ninguna forma las reconocia y salian en ingles: «southern East Pacific
    Rise» llego al titulo de us7000tdms (auditoria del 5-sep-2026, #159).
    """
    assert traducir_lugar(ingles) == espanol


def test_la_frontera_no_sale_mitad_en_cada_idioma() -> None:
    """`_REGION` atrapaba la forma entera: «Región de Chile-Argentina border» (#160)."""
    assert traducir_lugar("Chile-Argentina border region") == "Zona fronteriza Chile-Argentina"
    assert traducir_lugar("Peru-Ecuador border region") == "Zona fronteriza Perú-Ecuador"


def test_un_modificador_sobre_algo_desconocido_no_se_traduce_a_medias() -> None:
    """`northern Algo` con `Algo` desconocido saldria «Norte de Algo» inventado."""
    assert traducir_lugar("northern Atlantis Fracture") == "northern Atlantis Fracture"


def test_lo_que_no_se_reconoce_deja_rastro(monkeypatch: pytest.MonkeyPatch) -> None:
    """Devolver el original esta bien; hacerlo en silencio era el fallo (#159).

    El logger no propaga (salida JSON a stderr), asi que `caplog` no lo ve: se
    intercepta el metodo.
    """
    avisos: list[dict[str, Any]] = []
    monkeypatch.setattr(
        toponimos._log, "warning", lambda msg, **kw: avisos.append(kw["extra"]["context"])
    )

    traducir_lugar("12 km WSW of Somewhere, Chile")  # se reconoce: sin aviso
    assert avisos == []

    traducir_lugar("Somewhere off the Atlantis Trench")
    assert [a["place"] for a in avisos] == ["Somewhere off the Atlantis Trench"]
    assert avisos[0]["huellas"] == ["off", "the", "Trench"]


def _lugares(objeto: Any) -> list[str]:
    if isinstance(objeto, dict):
        propios = [v for k, v in objeto.items() if k == "lugar" and isinstance(v, str)]
        return propios + [x for v in objeto.values() for x in _lugares(v)]
    if isinstance(objeto, list):
        return [x for v in objeto for x in _lugares(v)]
    return []


def test_ningun_lugar_publicado_queda_en_ingles_con_el_codigo_de_hoy() -> None:
    """Todo `lugar` publicado, pasado por `traducir_lugar`, sale sin ingles.

    Mide el codigo, no el dato del dia: lo publicado guarda el `place` de USGS
    tal cual cuando no se reconocia, y volver a traducirlo es lo que hara la
    reemision (`run._refrescar_lugar` traduce el `place` del detail). Asi el
    corpus real de LATAM es la prueba de las formas, y un lugar nuevo que no
    encaje la pone en rojo con la cadena exacta.
    """
    fuentes = [REPORTS_DIR / "index.json", SITE_DIR / "observados.json"]
    fuentes += sorted(EVENTS_DIR.glob("*.json"))
    lugares = {
        lugar
        for fuente in fuentes
        for lugar in _lugares(json.loads(fuente.read_text(encoding="utf-8")))
    }
    # Sin esto, un cambio de clave dejaria la prueba recorriendo nada, en verde.
    assert len(lugares) >= 10, f"solo {len(lugares)} lugares: ¿cambio la clave `lugar`?"

    en_ingles = {
        lugar: huellas for lugar in lugares if (huellas := huellas_en_ingles(traducir_lugar(lugar)))
    }

    assert en_ingles == {}
