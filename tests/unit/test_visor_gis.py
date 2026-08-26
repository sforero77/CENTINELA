"""Invariantes cartograficos del visor, de la auditoria de UX/UI del 25-ago-2026.

El visor no tiene suite propia —es una pagina estatica sin build— asi que lo
que se puede vigilar desde aqui es su **codigo fuente**: que las decisiones que
costo encontrar sigan escritas donde tienen que estar. No sustituye a mirar la
pantalla; impide que un cambio distraido deshaga lo que mirarla enseno.

Los cuatro hallazgos que fijan estas pruebas salieron de abrir el visor
publicado con datos reales, no de leerlo.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

RAIZ = Path(__file__).parent.parent.parent
APP = (RAIZ / "site" / "assets" / "app.js").read_text(encoding="utf-8")
REPORTS = RAIZ / "reports"


# --- El encuadre tiene que incluir el epicentro -----------------------------


def _epicentro_y_malla(usgs_id: str) -> tuple[tuple[float, float], list[str]] | None:
    """Epicentro del evento y los indices H3 de su malla."""
    reporte = REPORTS / usgs_id / "report.json"
    celdas = REPORTS / usgs_id / "celdas.json"
    if not (reporte.is_file() and celdas.is_file()):
        return None
    ev = json.loads(reporte.read_text(encoding="utf-8"))["event"]
    malla = json.loads(celdas.read_text(encoding="utf-8"))["celdas"]
    if not malla:
        return None
    return (float(ev["lon"]), float(ev["lat"])), [c[0] for c in malla]


def _eventos_con_malla() -> list[str]:
    return sorted(p.parent.name for p in REPORTS.glob("*/celdas.json"))


def test_hay_eventos_con_los_que_comprobar() -> None:
    """Sin catalogo, las pruebas de abajo pasarian vacias."""
    assert len(_eventos_con_malla()) >= 15


@pytest.mark.geo
def test_en_algun_evento_el_epicentro_cae_fuera_de_la_malla() -> None:
    """La prueba que documenta por que el encuadre no puede ser solo la malla.

    Medido sobre el catalogo: en Carupano, La Libertad y Bartolome Maso el
    epicentro cae fuera de la caja de la malla, y en Cuba salia cortado por el
    borde inferior de la pantalla. Son sismos mar adentro, que en esta region
    son la mitad.

    Si algun dia esto deja de fallar sera porque el catalogo cambio, no porque
    el problema desaparezca: basta un evento costero para que vuelva.
    """
    import h3

    fuera = []
    for usgs_id in _eventos_con_malla():
        datos = _epicentro_y_malla(usgs_id)
        if datos is None:
            continue
        (lon, lat), indices = datos
        pts = [h3.cell_to_latlng(i) for i in indices]
        lons = [p[1] for p in pts]
        lats = [p[0] for p in pts]
        if not (min(lons) <= lon <= max(lons) and min(lats) <= lat <= max(lats)):
            fuera.append(usgs_id)

    assert fuera, "ningun epicentro cae fuera: revisa si el encuadre sigue haciendo falta"


def test_el_encuadre_mete_el_epicentro_en_la_caja() -> None:
    """Ver la afectacion *desde el epicentro* empieza por ver el epicentro."""
    assert "lons.push(epiLon)" in APP, "el encuadre no incluye el epicentro"
    assert "lats.push(epiLat)" in APP
    assert "fitBounds" in APP


# --- La celda tiene que poder citarse ---------------------------------------


def test_el_indice_h3_viaja_hasta_la_ficha() -> None:
    """Un dato que no se puede referenciar es un dato que no se puede usar.

    El indice se excluia de las propiedades del hexagono, y con el se iba la
    unica forma de cruzar lo que se ve en el mapa con el `celdas.json` que el
    propio visor ofrece para descargar.
    """
    assert 'if (nombre !== "h3")' not in APP, "el indice H3 vuelve a excluirse"
    assert "ficha-h3" in APP, "la ficha de celda no publica el indice"


def test_el_indice_de_la_ficha_existe_en_el_fichero_descargable() -> None:
    """El indice que se ensena tiene que ser el mismo que se descarga."""
    for usgs_id in _eventos_con_malla()[:3]:
        datos = json.loads((REPORTS / usgs_id / "celdas.json").read_text(encoding="utf-8"))
        assert datos["columnas"][0] == "h3"
        assert all(isinstance(c[0], str) and len(c[0]) == 15 for c in datos["celdas"][:20])


# --- La distancia al epicentro ----------------------------------------------


def test_el_visor_mide_la_distancia_con_el_radio_del_pipeline() -> None:
    """Dos numeros distintos para la misma distancia serian lo peor.

    Uno en el mapa y otro en el reporte, sobre el mismo par de puntos, es la
    clase de discrepancia que destruye la confianza en todo lo demas.
    """
    from pipelines.common.geo import EARTH_RADIUS_M

    esperado = EARTH_RADIUS_M / 1000.0
    assert f"RADIO_TIERRA_KM = {esperado:.4f}" in APP, (
        f"el visor no usa el radio del pipeline ({esperado:.4f} km)"
    )
    assert "Al epicentro" in APP, "la ficha no dice a que distancia esta la celda"


def test_la_formula_del_visor_da_lo_mismo_que_la_del_pipeline() -> None:
    """Se reimplementa el haversine del visor y se compara con el de Python."""
    from pipelines.common.geo import EARTH_RADIUS_M, haversine_km

    radio = EARTH_RADIUS_M / 1000.0

    def como_el_visor(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
        rad = math.pi / 180
        dlat = (lat2 - lat1) * rad
        dlon = (lon2 - lon1) * rad
        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(lat1 * rad) * math.cos(lat2 * rad) * math.sin(dlon / 2) ** 2
        )
        return 2 * radio * math.asin(min(1.0, math.sqrt(a)))

    for lon1, lat1, lon2, lat2 in (
        (-76.24, 4.84, -75.69, 4.81),
        (-77.11, 19.86, -76.9, 20.1),
        (-67.22, 10.61, -66.9, 10.5),
    ):
        assert como_el_visor(lon1, lat1, lon2, lat2) == pytest.approx(
            haversine_km(lon1, lat1, lon2, lat2), rel=1e-9
        )


# --- La profundidad -------------------------------------------------------


def test_la_profundidad_se_publica_como_distintivo() -> None:
    """Es lo que explica un M8,2 con cero personas en MMI≥7.

    Estaba en una linea de metadatos entre la fecha y la version del ShakeMap.
    Un lector que ve "M8,2" y "0 personas" sin ver "47 km" no tiene con que
    entenderlo.
    """
    assert "claseDeProfundidad" in APP
    for etiqueta in ("superficial", "intermedio", "profundo"):
        assert etiqueta in APP, f"falta la clase de profundidad '{etiqueta}'"


def test_los_cortes_de_profundidad_son_los_de_sismologia() -> None:
    """70 y 300 km. No son elegidos aqui: son los estandar."""
    assert "km < 70" in APP
    assert "km <= 300" in APP


# --- La carrera que dejaba el mapa en blanco --------------------------------


def test_la_puerta_del_estilo_no_depende_de_un_evento_que_ya_paso() -> None:
    """`once("load")` dispara una vez; si ya paso, el aviso se pierde.

    Reproducido en el visor publicado: abrir un enlace compartido con la cache
    fria dejaba el mapa en blanco —sin base, sin malla, sin leyenda y sin un
    error en consola— mientras que el mismo enlace con la cache caliente
    funcionaba. Le tocaba justo a quien abria el enlace por primera vez.
    """
    assert 'm.once("load"' not in APP, "la puerta del estilo vuelve a usar once('load')"
    assert 'm.on("styledata"' in APP
    assert 'm.on("idle"' in APP


def test_la_puerta_se_desengancha_cuando_termina() -> None:
    """Un oyente que no se quita se acumula en cada evento abierto."""
    assert 'm.off("styledata"' in APP
    assert 'm.off("idle"' in APP


def test_nadie_espera_al_estilo_por_su_cuenta() -> None:
    """La prueba que habria cazado el segundo sitio con el mismo fallo.

    Se arreglo `cuandoElEstiloEsteListo` y no se miro quien mas resolvia lo
    mismo a mano: `dibujarEpicentros` tenia su propio `m.on("load", pintar)` y
    seguia perdiendose el aviso. En el sitio publicado, con la cache fria, salia
    el mapa base entero y ni una estrella encima.

    Es exactamente el patron que esta auditoria persigue —arreglar la funcion y
    no revisar a los llamadores— cometido dentro de la propia auditoria.

    La unica excepcion es el aviso de "cargando", que ademas lleva su propio
    `setTimeout` de red de seguridad: si el mapa no carga, hay que quitarlo
    igual.
    """
    lineas = [
        linea.strip()
        for linea in APP.splitlines()
        if ('m.on("load"' in linea or 'm.once("load"' in linea)
        and not linea.strip().startswith("//")
    ]
    fuera_del_ayudante = [linea for linea in lineas if "listo" not in linea]

    assert fuera_del_ayudante == [], (
        f"Estas esperan al estilo por su cuenta en vez de usar "
        f"`cuandoElEstiloEsteListo`: {fuera_del_ayudante}"
    )


# --- La capa de sismos vistos y no despachados ------------------------------


def test_los_observados_no_usan_la_rampa_de_mmi() -> None:
    """La rampa significa «impacto medido». Prestarsela la vaciaria de sentido.

    Es el riesgo §7 —«cifra alarmista»— en su forma visual: un punto pintado
    con los colores de la intensidad se lee como una intensidad medida, diga lo
    que diga el pie.
    """
    js = APP
    capa = js[js.index('id: "observados"') : js.index('id: "observados"') + 900]

    assert "OBSERVADO" in capa, "no usa el gris reservado para esta capa"
    for color in ("BANDAS", "RAMPA", "CAPAS[", "EPICENTRO"):
        assert color not in capa, f"la capa de observados toma color de {color}"


def test_los_observados_arrancan_apagados() -> None:
    """Quien abre el visor viene a ver impacto, no ruido sismico de fondo."""
    js = APP
    capa = js[js.index('id: "observados"') : js.index('id: "observados"') + 400]

    assert 'visibility: "none"' in capa


def test_el_popup_dice_que_no_hay_medicion() -> None:
    """Sin esta frase, un punto en el mapa se lee como impacto cero medido."""
    js = APP

    assert "No se midió su impacto" in js


def test_los_observados_no_llevan_etiqueta_de_magnitud() -> None:
    """Las etiquetas son de los eventos con reporte.

    Poner «M4,9» flotando junto a un punto gris lo equipara visualmente a una
    estrella con reporte, que es justo la jerarquia que hay que mantener.
    """
    js = APP
    capa = js[js.index('id: "observados"') : js.index('id: "observados"') + 900]

    assert "text-field" not in capa


def test_la_capa_se_carga_de_verdad() -> None:
    """Escrita y no llamada seria el patron que esta auditoria persigue."""
    js = APP

    assert "cargarObservados();" in js, "cargarObservados esta definida y nadie la llama"


def test_el_interruptor_solo_aparece_si_hay_algo() -> None:
    """Un control siempre vacio ensena a ignorar los controles."""
    js = APP

    assert "if (!eventos.length) return;" in js
