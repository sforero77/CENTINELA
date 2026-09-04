"""Lo que un reporte calcula tiene que poder mirarse.

EL FALLO. `us7000tdmp` —M5,6 a 71 km mar adentro de Puerto Madero, el primer
sismo en vivo del sistema— se publico con su `contornos.json` calculado,
servido y descargable, y **ni el visor ni el PNG dibujaban una sola linea de
el**. En pantalla quedaba una estrella sobre un mapa vacio, indistinguible de
un reporte que no se proceso. La unica pregunta que ese evento existe para
contestar —donde estuvo la sacudida y por que no toco a nadie— era justo la que
no se podia mirar.

Eran dos desconexiones distintas con el mismo sintoma:

* En `app.js`, la rama "sin malla" de `dibujarCeldas` volvia veinte lineas
  antes de la llamada a `dibujarContornos`. Las isolineas se tiraban a la
  basura junto con la malla que efectivamente no existe.
* En `static_map.py`, dos cosas: las bandas por debajo de MMI 6 no se dibujaban
  de ninguna forma —asi que un evento que topa en MMI 5 salia en hoja blanca— y
  el encuadre se calculaba sobre los municipios y el epicentro, sin mirar el
  contorno. Sin municipios quedaba **un punto**, y el margen minimo montaba una
  caja de 44 km: en `us1000c2zy`, un M7,5 mar adentro, esa caja cae entera
  dentro de la banda de MMI 8 y el mapa salia como un muro rojo de borde a
  borde con una escala de 20 km.

POR QUE VA CONTRA EL CATALOGO Y NO CONTRA UN CASO. No era un evento: son cinco
de los veintitres publicados, y el peor no es el M5,6 sino ese M7,5 con
isolineas hasta MMI 8. Un guardia escrito contra un `usgs_id` fijo pasaria
verde el dia que llegue el sexto. Estas pruebas recorren `reports/`, asi que el
evento que se publique manana entra solo — que es lo que se pidio: que se vea
lo que hay y lo que venga.

El cero es un resultado legitimo y estas pruebas no lo discuten: las cifras de
esos reportes van en cero porque la sacudida no alcanzo MMI 6 sobre poblacion,
y eso lo defiende `test_sacudida_sin_llegar_a_tierra.py`. Lo que se exige aqui
es lo otro: que un reporte en cero **no se vea igual que un reporte roto**.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest

from pipelines.p3_report.static_map import (
    MMI_MIN_MAPPED,
    _bandas_dibujadas,
    _dibujar_contornos,
    _extremos_de_contorno,
    _limites,
    banda_de_mmi,
)

RAIZ = Path(__file__).parent.parent.parent
REPORTS = RAIZ / "reports"
APP = (RAIZ / "site" / "assets" / "app.js").read_text(encoding="utf-8")

#: Por debajo de esto, el PNG no ensena la sacudida.
#:
#: Se cuentan los pixeles **con color** —saturacion >= 12— y no la tinta total:
#: el titulo, la barra de escala, el marco y la estrella son todos neutros, asi
#: que lo que queda son las bandas y las isolineas, que es lo que este guardia
#: mira. Medido: el mapa del M5,6, que es el mas pobre del catalogo porque son
#: tres circulos grises finos, da 3.417 pixeles; ese mismo mapa renderizado sin
#: contornos —el fallo, exactamente— da 43. El umbral cae en el hueco.
COLOR_MINIMO = 1_500


def _eventos_publicados() -> list[str]:
    return sorted(p.parent.name for p in REPORTS.glob("*/report.json"))


def _contornos(usgs_id: str) -> dict[str, Any] | None:
    ruta = REPORTS / usgs_id / "contornos.json"
    if not ruta.is_file():
        return None
    datos: dict[str, Any] = json.loads(ruta.read_text(encoding="utf-8"))
    return datos if datos.get("features") else None


def _niveles(contornos: dict[str, Any]) -> list[float]:
    return [float(r["properties"]["mmi"]) for r in contornos["features"]]


def _eventos_sin_malla() -> list[str]:
    """Los publicados cuya sacudida no dejo ni una celda debajo.

    Es la lista que estas pruebas vigilan, y sale del catalogo en cada corrida
    en vez de estar escrita: los cinco de hoy fueron uno solo hace una semana.
    """
    sin = []
    for usgs_id in _eventos_publicados():
        celdas = REPORTS / usgs_id / "celdas.json"
        if not celdas.is_file():
            continue
        if json.loads(celdas.read_text(encoding="utf-8")).get("celdas"):
            continue
        if _contornos(usgs_id):
            sin.append(usgs_id)
    return sin


# --- Que haya con que comprobar ---------------------------------------------


def test_hay_eventos_sin_malla_en_el_catalogo() -> None:
    """Sin ellos, todo lo de abajo pasaria en vacio y nadie lo notaria.

    Es el modo de fallo que este proyecto persigue: un guardia que no falla
    porque no mira nada. Si algun dia el catalogo no tiene ni uno sera porque
    cambio el catalogo, no porque el problema desaparezca — basta un sismo mar
    adentro, que en esta region es la mitad.
    """
    assert _eventos_sin_malla(), (
        "ningun reporte publicado se quedo sin malla: estas pruebas no estan comprobando nada"
    )


# --- El PNG -----------------------------------------------------------------


@pytest.mark.parametrize("usgs_id", _eventos_publicados())
def test_ningun_mapa_publicado_sale_en_blanco(usgs_id: str) -> None:
    """El PNG de cada reporte ensena su sacudida, tenga o no gente debajo.

    Contra el fichero publicado y no contra un render nuevo: lo que se sirve en
    la pagina es este PNG, y un arreglo en `static_map.py` que nadie aplique al
    catalogo deja el mapa roto donde se mira.
    """
    contornos = _contornos(usgs_id)
    if contornos is None:
        pytest.skip(f"{usgs_id} es anterior a contornos.json: su mapa no puede dibujarlos")

    np = pytest.importorskip("numpy")
    imagen = pytest.importorskip("PIL.Image")

    ruta = REPORTS / usgs_id / "mapa_general.png"
    assert ruta.is_file(), f"{usgs_id} no tiene mapa_general.png"

    pixeles = np.asarray(imagen.open(ruta).convert("RGB")).astype(int)
    con_color = int((pixeles.max(axis=2) - pixeles.min(axis=2) >= 12).sum())

    assert con_color >= COLOR_MINIMO, (
        f"el mapa de {usgs_id} tiene {con_color} pixeles con color: su "
        f"contornos.json trae {len(contornos['features'])} isolineas y el PNG "
        f"no dibuja ninguna. Rehazlo con `centinela regenerar-mapas {usgs_id}`"
    )


@pytest.mark.parametrize("usgs_id", _eventos_publicados())
def test_el_encuadre_del_png_no_deja_fuera_la_isolinea(usgs_id: str) -> None:
    """La caja del mapa contiene lo que el mapa dibuja.

    Se calculaba sobre municipios y epicentro. Con los cinco eventos sin
    municipios eso es un punto, y el mapa quedaba encuadrado en 44 km alrededor
    del epicentro: dentro de la banda mas intensa, sin una sola linea visible y
    con una barra de escala que mentia sobre lo que se estaba mirando.
    """
    contornos = _contornos(usgs_id)
    if contornos is None:
        pytest.skip(f"{usgs_id} es anterior a contornos.json")

    evento = json.loads((REPORTS / usgs_id / "report.json").read_text(encoding="utf-8"))["event"]
    epicentro = (float(evento["lon"]), float(evento["lat"]))

    lons, lats = _extremos_de_contorno(contornos)
    assert lons, f"{usgs_id} trae isolineas y no se le midio ni una coordenada"

    # Sin municipios a proposito: es el caso que fallaba, y el que tiene que
    # sostenerse por si solo.
    lon_min, lat_min, lon_max, lat_max = _limites([], epicentro, contornos)

    assert lon_min <= min(lons) and max(lons) <= lon_max, (
        f"la caja de {usgs_id} corta la isolinea en longitud: "
        f"caja [{lon_min:.3f}, {lon_max:.3f}], linea [{min(lons):.3f}, {max(lons):.3f}]"
    )
    assert lat_min <= min(lats) and max(lats) <= lat_max, (
        f"la caja de {usgs_id} corta la isolinea en latitud: "
        f"caja [{lat_min:.3f}, {lat_max:.3f}], linea [{min(lats):.3f}, {max(lats):.3f}]"
    )


def test_el_encuadre_prefiere_la_banda_que_se_cuantifica() -> None:
    """La de MMI 6, no la de MMI 4.

    El respaldo a "todas las isolineas" existe para los eventos que no llegan a
    MMI 6 en ningun punto. Aplicarlo siempre seria peor que el fallo que
    arregla: la isolinea de MMI 4 de un M8 abarca medio continente y dejaria la
    mancha del evento del tamano de un sello.
    """
    contornos = {
        "features": [
            {
                "properties": {"mmi": 4.0},
                "geometry": {"type": "LineString", "coordinates": [[-100.0, 0.0], [-60.0, 20.0]]},
            },
            {
                "properties": {"mmi": 6.0},
                "geometry": {"type": "LineString", "coordinates": [[-80.0, 5.0], [-79.0, 6.0]]},
            },
        ]
    }

    lons, _lats = _extremos_de_contorno(contornos)

    assert max(lons) - min(lons) == pytest.approx(1.0), (
        "el encuadre se fue a la isolinea de MMI 4 teniendo una de MMI 6"
    )


def test_sin_ninguna_banda_cuantificable_se_encuadra_lo_que_haya() -> None:
    """Y aqui si: es lo unico que el evento dibujo."""
    contornos = {
        "features": [
            {
                "properties": {"mmi": 5.0},
                "geometry": {"type": "LineString", "coordinates": [[-93.0, 14.0], [-92.0, 15.0]]},
            }
        ]
    }

    lons, lats = _extremos_de_contorno(contornos)

    assert (min(lons), max(lons)) == (-93.0, -92.0)
    assert (min(lats), max(lats)) == (14.0, 15.0)


def test_un_evento_que_no_alcanza_mmi6_dibuja_igual_sus_isolineas() -> None:
    """La hoja en blanco, en una prueba.

    Las bandas por debajo de 6 no se **rellenan** —su contraste contra el fondo
    es de 1,2:1— y esa decision sigue en pie. Lo que no puede ser es que
    entonces no se dibujen de ninguna forma: se trazan como linea, que es
    ademas lo que son en el ShakeMap y lo que el visor dibuja.
    """
    matplotlib = pytest.importorskip("matplotlib")
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    contornos = {
        "features": [
            {
                "properties": {"mmi": nivel},
                "geometry": {
                    "type": "MultiLineString",
                    "coordinates": [[[-93.0, 14.0], [-92.9, 14.1], [-93.0, 14.2], [-93.0, 14.0]]],
                },
            }
            for nivel in (4.0, 4.5, 5.0)
        ]
    }

    fig, ax = plt.subplots()
    try:
        _dibujar_contornos(ax, contornos)
        trazos = len(ax.lines)
        parches = len(ax.patches)
    finally:
        plt.close(fig)

    assert trazos == 3, f"tres isolineas por debajo de MMI 6 y se trazaron {trazos}"
    assert parches == 0, "una banda por debajo de MMI 6 no se rellena, solo se traza"


def test_un_lazo_abierto_de_banda_alta_se_traza_aunque_no_se_pueda_rellenar() -> None:
    """Cerrarlo inventaria area; descartarlo pierde por donde paso la sacudida.

    `_anillos` lo descarta con razon —un lazo abierto rellenado atraviesa el
    mapa en linea recta— y esa geometria seguia siendo la unica noticia de
    hasta donde llego el evento en ese borde.
    """
    matplotlib = pytest.importorskip("matplotlib")
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    contornos = {
        "features": [
            {
                "properties": {"mmi": 7.0},
                "geometry": {
                    "type": "LineString",
                    "coordinates": [[-93.0, 14.0], [-92.5, 14.5], [-92.0, 14.2]],
                },
            }
        ]
    }

    fig, ax = plt.subplots()
    try:
        _dibujar_contornos(ax, contornos)
        trazos = len(ax.lines)
        parches = len(ax.patches)
    finally:
        plt.close(fig)

    assert parches == 0, "un lazo abierto no se puede rellenar sin inventar area"
    assert trazos == 1, "y aun asi tiene que verse: se traza como linea"


@pytest.mark.parametrize("usgs_id", _eventos_publicados())
def test_la_leyenda_del_png_rotula_lo_que_el_mapa_pinta(usgs_id: str) -> None:
    """Las bandas salian de los municipios, y los municipios no son lo dibujado.

    `us1000c2zy` pinta MMI 6, 6,5, 7, 7,5 y 8 sobre el Caribe y no tiene un solo
    municipio expuesto: su leyenda decia "epicentro" y nada mas, encima de un
    mapa lleno de color sin explicar.
    """
    contornos = _contornos(usgs_id)
    if contornos is None:
        pytest.skip(f"{usgs_id} es anterior a contornos.json")

    niveles = _niveles(contornos)
    bandas, hay_bajas = _bandas_dibujadas(contornos, [])

    esperadas = sorted({banda_de_mmi(v) for v in niveles if v >= MMI_MIN_MAPPED})
    assert bandas == esperadas, f"{usgs_id} pinta {esperadas} y la leyenda rotula {bandas}"
    assert hay_bajas == any(v < MMI_MIN_MAPPED for v in niveles), (
        f"{usgs_id}: la entrada de la isolinea gris no sigue a lo que se dibuja"
    )


# --- El visor ---------------------------------------------------------------
#
# Las pruebas que abren un navegador viven en `tests/visor/` y estan fuera del
# job principal de CI —arrastran 115 MB de Chromium—, asi que el guardia de la
# desconexion que causo todo esto tiene que poder correr aqui. Lee `app.js`:
# no ve la pantalla, pero impide que el `return` vuelva a colarse delante de la
# llamada.


def _sin_comentarios(js: str) -> str:
    """El mismo cuidado que `sin_comentarios_js` en `test_visor_gis.py`.

    Un guardia de texto que no quita los comentarios encuentra la explicacion
    en vez de la regla, y cuanto mejor documentado este el arreglo mas probable
    es que su propia prueba lo de por bueno. Esta rama lleva doce lineas de
    comentario que nombran `dibujarContornos` para contar que **no** se
    llamaba: sin esto, borrar la llamada seguiria dando verde.
    """
    return "\n".join(linea for linea in js.splitlines() if not linea.lstrip().startswith("//"))


def _rama_sin_malla() -> str:
    """El cuerpo de la rama "no hay celdas" de `dibujarCeldas`, hasta su return."""
    ini = APP.index("function dibujarCeldas")
    guarda = APP.index("if (!geo || !geo.features.length) {", ini)
    return _sin_comentarios(APP[guarda : APP.index("return;", guarda)])


def test_el_visor_dibuja_los_contornos_cuando_no_hay_malla() -> None:
    """La desconexion original, y la que mas facil vuelve.

    `dibujarContornos` se llama veinte lineas mas abajo, ya dentro del camino
    que monta la malla. Cualquier salida temprana que se ponga antes se lleva
    por delante la unica capa que estos eventos tienen.
    """
    rama = _rama_sin_malla()

    assert "dibujarContornos(" in rama, (
        "la rama sin malla vuelve antes de dibujar los contornos: el evento "
        "trae isolineas calculadas y el mapa no pinta ninguna"
    )


def test_el_visor_nombra_las_isolineas_que_deja_solas() -> None:
    """Una linea palida sobre el mar, sin leyenda, no es informacion.

    La caja de la leyenda se ocultaba en esta rama porque describe la malla.
    Ahora describe lo que hay: los niveles que este ShakeMap trae.
    """
    rama = _rama_sin_malla()

    assert "pintarLeyendaDeContornos(" in rama, "se dibujan las isolineas y no se rotulan"
    assert '$("leyenda").hidden = true' not in rama, (
        "la rama sin malla sigue ocultando la leyenda a ciegas: quien decide es "
        "pintarLeyendaDeContornos, que sabe si hay algo que rotular"
    )


def test_el_visor_encuadra_por_el_contorno_y_no_por_un_zoom_a_ojo() -> None:
    """Habia un `zoom: 7.5` fijo que no habia mirado el evento.

    En Puerto Madero deja fuera media isolinea; en Barra Patuca encuadra una
    franja de mar dentro de una mancha de 400 km. Es el mismo error del PNG.
    """
    rama = _rama_sin_malla()

    assert "encuadrarSinMalla(" in rama, "la rama sin malla no encuadra por el contorno"
    assert "zoom: 7.5" not in rama, "sigue el zoom fijo puesto a ojo"


def test_el_visor_y_el_png_encuadran_con_la_misma_regla() -> None:
    """MMI 6 si existe; si no, todo. El mismo sismo no puede enmarcarse de dos
    formas segun se mire el PNG o la pagina."""
    cuerpo = APP[APP.index("function encuadrarSinMalla") :]
    cuerpo = cuerpo[: cuerpo.index("\n}")]

    assert "[6, -Infinity]" in cuerpo, (
        "el visor perdio el respaldo a todas las isolineas, o dejo de preferir "
        f"la de MMI {MMI_MIN_MAPPED:g}"
    )


def test_las_dos_reglas_de_color_de_isolinea_leen_la_misma_tabla() -> None:
    """`colorDeContorno` da una expresion de MapLibre y `colorDeIsolinea` un
    color, y las dos tienen que decir lo mismo: la leyenda que explica una linea
    gris no puede estar junto a una linea naranja en el mapa.

    Ninguna lleva tabla propia — las dos leen `CAPAS.mmi`. Un hexadecimal
    escrito dentro de cualquiera de las dos es el principio de la deriva.
    """
    for nombre in ("colorDeContorno", "colorDeIsolinea"):
        ini = APP.index(f"function {nombre}")
        cuerpo = APP[ini : APP.index("\n}", ini)]
        assert "CAPAS.mmi.cortes" in cuerpo, f"{nombre} dejo de leer los cortes de CAPAS.mmi"
        assert "CAPAS.mmi.colores" in cuerpo, f"{nombre} dejo de leer los colores de CAPAS.mmi"
        assert "COLOR_CONTORNO_BAJO" in cuerpo, f"{nombre} dejo de compartir el gris de los bajos"
        assert not re.search(r"#[0-9a-fA-F]{6}", cuerpo), (
            f"{nombre} lleva un color escrito a mano: tiene que salir de CAPAS.mmi"
        )


# --- Lo que cambio al reprocesar --------------------------------------------
#
# El mismo hueco que las isolineas, en otro dato. `changelog.py` calcula los
# deltas entre dos versiones del reporte —RF-04 los exige— y su cabecera dice
# para quien: "un ShakeMap se revisa muchas veces y quien ya leyo la version
# anterior necesita saber que cambio, no volver a leerlo entero durante una
# emergencia". Van en `report.json`, `markdown.py` les da su seccion, y el
# visor —que es donde se lee esto en una emergencia— pintaba `shakemap_version`
# a secas. Un numero que cambia sin decir que cambio no se distingue de uno que
# siempre fue ese.


def _reportes_con_changelog() -> list[str]:
    """Los publicados que ya traen deltas. Sale del catalogo, como el resto."""
    con = []
    for usgs_id in _eventos_publicados():
        datos = json.loads((REPORTS / usgs_id / "report.json").read_text(encoding="utf-8"))
        if datos.get("changelog"):
            con.append(usgs_id)
    return con


def test_hay_reportes_con_changelog_en_el_catalogo() -> None:
    """Sin ellos, el guardia de navegador pasaria en vacio.

    Aparecen solos: basta que USGS revise un ShakeMap y que P1 lo vea. Si algun
    dia no hay ninguno sera porque el catalogo es nuevo, no porque el reproceso
    dejara de pasar.
    """
    assert _reportes_con_changelog(), (
        "ningun reporte publicado trae changelog: nada esta comprobando que el visor lo pinte"
    )


def test_el_visor_pinta_el_changelog_del_reporte() -> None:
    """Estaba calculado, servido y descargable, y nadie lo llamaba.

    Es literalmente la misma forma que el `return` que se llevaba las
    isolineas: la pieza correcta, sin conexion.
    """
    assert "pintarCambios(" in _sin_comentarios(APP), (
        "app.js no pinta el changelog en ninguna parte: el reporte publica "
        "'que cambio' y el visor solo ensena el numero de version"
    )

    ini = APP.index("function pintarCambios")
    cuerpo = _sin_comentarios(APP[ini : APP.index("\n}", ini)])
    assert "reporte.changelog" in cuerpo, "pintarCambios no lee el changelog del reporte"
    assert "escapar(" in cuerpo, (
        "el changelog se inyecta como HTML sin escapar: viene de un fichero "
        "generado, pero es texto que acaba en innerHTML"
    )


def test_el_bloque_de_cambios_nace_oculto() -> None:
    """La primera emision de un reporte no tiene version anterior.

    Un bloque vacio que dice "sin cambios" en veintiuno de veintitres reportes
    ensena a no leer el bloque.
    """
    html = (RAIZ / "site" / "index.html").read_text(encoding="utf-8")

    assert 'id="bloque-cambios" hidden' in html, (
        "el bloque de cambios no arranca oculto: aparecera vacio en todo "
        "reporte que solo se haya publicado una vez"
    )


def test_el_bloque_de_cambios_se_puede_ocultar_de_verdad() -> None:
    """`[hidden]` es `display:none` con especificidad de elemento, y `.bloque`
    puede pisarlo — la trampa que ya costo dieciocho tarjetas visibles con el
    filtro puesto."""
    css = (RAIZ / "site" / "assets" / "styles.css").read_text(encoding="utf-8")
    reglas = re.findall(r"\.bloque\s*\{[^}]*\}", css)
    con_display = [r for r in reglas if "display" in r]

    if not con_display:
        return
    assert "[hidden]" in css and ".bloque[hidden]" in css, (
        f".bloque fija display ({con_display[0][:60]}...) y nada devuelve el "
        "efecto a [hidden]: el bloque de cambios se vera aunque este oculto"
    )
