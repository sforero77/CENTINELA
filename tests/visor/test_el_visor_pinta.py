"""El visor, abierto en un navegador de verdad.

EL HUECO QUE CIERRA. El resto de la suite comprueba que `app.js` **declara** las
cosas: que la rampa es la acordada, que el epicentro es una estrella, que la
leyenda se construye con las clases del evento. Nada de eso ve la pantalla, y
los tres bugs de la auditoria de UX/UI —mapa en blanco al seleccionar un evento,
hexagonos a 0,05 pixeles, capa de fuego invisible— pasaron la suite entera.

POR QUE SE ESPERA AL REGISTRO Y NO AL RELOJ. El 28-ago-2026 se reviso el visor a
ojo y se dieron por rotas tres capas que estaban perfectamente: se habian medido
antes de que terminaran de pintar. La malla de un evento tarda ~5,7 s en local y
unos 10 s contra la pagina publicada.

Una prueba con `sleep(4)` habria "encontrado" los mismos tres bugs inexistentes,
y una con `sleep(15)` tardaria un minuto en cuatro comprobaciones y seguiria
fallando el dia que la red va lenta. Por eso `app.js` publica `window.CENTINELA`
—lo que ha pintado y cuantos rasgos— y aqui se espera a eso.

Cuenta rasgos y no un booleano a proposito: "la capa existe" no distingue una
malla dibujada de una malla vacia, que es el cero silencioso de siempre.
"""

from __future__ import annotations

import shutil
import threading
from collections.abc import Iterator
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import pytest

pytestmark = pytest.mark.visor

RAIZ = Path(__file__).parent.parent.parent

#: Cuanto se espera a que una capa aparezca en el registro. Holgado a proposito:
#: el fallo que esta prueba tiene que dar es "no se pinto", no "tarde mas de lo
#: que yo supuse". Si de verdad tarda 25 s, eso es un hallazgo y no un flake.
ESPERA_MS = 25_000


def _sitio(destino: Path) -> Path:
    """Arma `_site` igual que `site.yml`, que es lo que se publica.

    Se replica el workflow en vez de servir `site/` a secas porque los reportes
    viven en la raiz del repositorio y en la pagina cuelgan de `/reports`. Servir
    otra cosa comprobaria un visor que nadie usa.
    """
    shutil.copytree(RAIZ / "site", destino, dirs_exist_ok=True)
    shutil.copytree(RAIZ / "reports", destino / "reports", dirs_exist_ok=True)
    return destino


@pytest.fixture(scope="module")
def servidor(tmp_path_factory: pytest.TempPathFactory) -> Iterator[str]:
    """Sirve el sitio armado en un puerto libre."""
    raiz = _sitio(tmp_path_factory.mktemp("_site"))
    manejador = partial(SimpleHTTPRequestHandler, directory=str(raiz))
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), manejador)
    hilo = threading.Thread(target=httpd.serve_forever, daemon=True)
    hilo.start()
    try:
        yield f"http://127.0.0.1:{httpd.server_address[1]}"
    finally:
        httpd.shutdown()
        httpd.server_close()


@pytest.fixture(scope="module")
def navegador() -> Iterator[Any]:
    """Chromium, y **falla si no esta** en vez de saltarse.

    Un salto silencioso en el unico guardia que ve la pantalla es peor que no
    tenerlo — la misma leccion que dejo el nocturno de deriva de contrato.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:  # pragma: no cover - depende del entorno
        pytest.fail(
            "playwright no esta instalado y estas pruebas se pidieron con `-m visor`.\n"
            "  uv sync --extra visor && uv run playwright install chromium"
        )

    with sync_playwright() as pw:
        try:
            nav = pw.chromium.launch()
        except Exception as exc:  # pragma: no cover - depende del entorno
            pytest.fail(f"no se pudo abrir Chromium: {exc}\n  uv run playwright install chromium")
        try:
            yield nav
        finally:
            nav.close()


@pytest.fixture
def pagina(navegador: Any, servidor: str) -> Iterator[Any]:
    ctx = navegador.new_context(viewport={"width": 1400, "height": 900})
    pg = ctx.new_page()
    errores: list[str] = []
    pg.on("pageerror", lambda e: errores.append(str(e)))
    pg.goto(f"{servidor}/index.html")
    yield pg
    # Un error de JS no lanzado deja el visor a medias sin decir nada, que es
    # como se perdio la malla de un evento durante dos horas de diagnostico.
    assert not errores, f"la pagina lanzo errores de JavaScript: {errores}"
    ctx.close()


def _esperar_capa(pagina: Any, nombre: str, *, desde: str = "") -> dict[str, Any]:
    """Espera a que el visor declare esa capa pintada y devuelve su anotacion.

    ``desde`` permite exigir una anotacion **nueva**: al cambiar de evento la
    clave ya existe de la carga anterior, y sin comparar la marca de tiempo la
    espera devolveria al instante la malla del evento anterior.
    """
    pagina.wait_for_function(
        """([nombre, desde]) => {
             const p = window.CENTINELA && window.CENTINELA.pintado;
             return !!(p && p[nombre] && p[nombre].utc > desde);
           }""",
        arg=[nombre, desde],
        timeout=ESPERA_MS,
    )
    anotacion: dict[str, Any] = pagina.evaluate(f"window.CENTINELA.pintado[{nombre!r}]")
    return anotacion


def _ahora(pagina: Any) -> str:
    marca: str = pagina.evaluate("new Date().toISOString()")
    return marca


# --- El panorama ------------------------------------------------------------


def test_el_panorama_dibuja_los_epicentros(pagina: Any) -> None:
    """Veintiun reportes son veintiuna estrellas.

    Se dieron por ausentes al mirar la captura: a zoom continental un epicentro
    ocupa pocos pixeles. Contarlos no admite esa duda.
    """
    anotacion = _esperar_capa(pagina, "epicentros")

    assert anotacion["rasgos"] > 0, "el panorama no dibujo ni un epicentro"
    catalogo = pagina.evaluate(
        "fetch('reports/index.json').then(r => r.json()).then(e => e.length)"
    )
    assert anotacion["rasgos"] == catalogo, (
        f"el catalogo trae {catalogo} reportes y el mapa dibujo {anotacion['rasgos']}"
    )


def test_los_focos_activos_se_dibujan(pagina: Any) -> None:
    """La capa de fuego fue uno de los tres bugs invisibles de la auditoria.

    Y sigue siendo la mas fragil: sus hexagonos son subpixel a zoom continental,
    y por eso su fuente lleva `tolerance: 0` — con el valor por defecto la
    simplificacion los colapsa y desaparecen antes de dibujarse.
    """
    anotacion = _esperar_capa(pagina, "incendios")

    assert anotacion["rasgos"] > 0, "la capa de focos no dibujo ni una celda"
    publicadas = pagina.evaluate(
        "fetch('incendios.json').then(r => r.json()).then(d => d.celdas.length)"
    )
    assert anotacion["rasgos"] == publicadas, (
        f"incendios.json trae {publicadas} celdas y el mapa dibujo {anotacion['rasgos']}"
    )


# --- Un evento --------------------------------------------------------------


def test_seleccionar_un_evento_dibuja_su_malla(pagina: Any) -> None:
    """El bug: "el mapa en blanco al seleccionar un evento".

    Aqui no se mira si el mapa "parece" lleno: se exige que la malla declare
    rasgos y que los contornos tambien, que son las dos capas que el tablero
    promete al mostrar sus cifras de poblacion por franja.
    """
    marca = _ahora(pagina)
    pagina.select_option("select", "us6000tjl2")

    celdas = _esperar_capa(pagina, "celdas", desde=marca)
    contornos = _esperar_capa(pagina, "contornos", desde=marca)

    assert celdas["rasgos"] > 0, "se selecciono un evento y la malla salio vacia"
    assert contornos["rasgos"] > 0, "el area de afectacion no se dibujo"


def test_la_leyenda_y_la_malla_hablan_del_mismo_dato(pagina: Any) -> None:
    """Si no, se lee una cifra plausible y equivocada.

    Una malla coloreada por intensidad bajo una leyenda de poblacion no rompe
    nada: se ve bien, y quien la mire interpretara naranjas con una escala
    turquesa. Es el modo de fallo que este proyecto persigue en todas partes.

    NO se comprueba un repintado. Cambiar de capa **no** repinta la malla: la
    reestiliza con `setPaintProperty` y `setFilter` sobre la misma fuente, que es
    lo correcto. La primera version de esta prueba esperaba rasgos nuevos y
    agotaba los 25 s con el visor funcionando perfectamente.
    """
    marca = _ahora(pagina)
    pagina.select_option("select", "us6000tjl2")
    _esperar_capa(pagina, "celdas", desde=marca)

    antes = _ahora(pagina)
    # Por el rol `tab` y no por `button`: el selector de capas es un `tablist`
    # ARIA, y buscarlo asi comprueba de paso que ese contrato sigue en pie.
    # `role="tab"` sustituye al rol implicito, asi que `get_by_role("button")`
    # no encuentra nada.
    pagina.get_by_role("tab", name="Población").click()
    pagina.wait_for_function(
        """desde => {
             const c = window.CENTINELA.pintado.capa;
             return !!(c && c.utc > desde);
           }""",
        arg=antes,
        timeout=ESPERA_MS,
    )

    capa = pagina.evaluate("window.CENTINELA.pintado.capa")
    assert capa["id"] == "pop", f"se pulso Poblacion y la malla quedo en {capa['id']!r}"

    leyenda = pagina.locator("#leyenda").inner_text()
    assert "POBLACIÓN" in leyenda.upper(), (
        f"la malla se colorea por {capa['columna']!r} y la leyenda dice otra cosa: {leyenda[:60]!r}"
    )


def test_el_visor_no_se_traga_sus_errores(pagina: Any) -> None:
    """`cuandoElEstiloEsteListo` corre diferido y MapLibre se come lo que lance.

    Costo dos horas de diagnostico un fallo que no dejaba ni una linea en
    consola. Desde entonces se captura y se anota; esta prueba exige que el
    registro salga limpio en el camino normal.
    """
    marca = _ahora(pagina)
    pagina.select_option("select", "us6000tjl2")
    _esperar_capa(pagina, "celdas", desde=marca)

    errores = pagina.evaluate("window.CENTINELA.errores")
    assert errores == [], f"el visor anoto fallos al pintar: {errores}"


# --- Que el registro no se quede atras --------------------------------------


def test_el_registro_cubre_todas_las_capas_del_visor() -> None:
    """Una capa nueva sin anotar es una capa que esta prueba no puede vigilar.

    No hace falta navegador: lee `app.js`. Vive aqui, junto a lo que protege,
    porque separarla la volveria invisible para quien anada la siguiente capa.
    """
    app = (RAIZ / "site" / "assets" / "app.js").read_text(encoding="utf-8")

    for capa in ("celdas", "contornos", "epicentros", "incendios", "observados"):
        assert f'anotarPintado("{capa}"' in app, (
            f"la capa {capa!r} se dibuja y no se anota en window.CENTINELA: "
            f"las pruebas de visor no pueden esperarla"
        )


def test_el_registro_es_superficie_publica() -> None:
    """Sin `window.CENTINELA` no hay forma de esperar sin adivinar."""
    app = (RAIZ / "site" / "assets" / "app.js").read_text(encoding="utf-8")

    assert "window.CENTINELA = { pintado, errores: erroresAlPintar };" in app


# --- Lo que se oculta tiene que dejar de verse -------------------------------


def test_ningun_elemento_oculto_se_sigue_viendo(pagina: Any) -> None:
    """`[hidden]` es `display: none` con especificidad de elemento: lo pisa
    cualquier regla de clase.

    El filtro por pais marcaba `hidden` en dieciocho tarjetas, ponia la pastilla
    del pais en `aria-pressed="true"`, anunciaba "3 reportes en la lista" al
    lector de pantalla — y las veintiuna seguian en pantalla, porque
    `.lista-eventos li { display: flex }` gana. Nada fallaba: la funcion
    simplemente no hacia nada.

    La trampa ya se conocia —`.leyenda[hidden]` la guarda desde su propia
    regla— y no se habia aplicado aqui. Por eso esta prueba es generica: mira
    **todos** los `[hidden]` de la pagina, para que la proxima clase con
    `display` no repita el descuido.
    """
    _esperar_capa(pagina, "epicentros")
    # Acotado al filtro: "Venezuela" aparece tambien en las tarjetas de
    # evento y en la tabla de cobertura, y sin acotar son cuatro nodos.
    pagina.locator("#filtro-paises").get_by_role("button", name="Venezuela").click()

    visibles = pagina.evaluate("""() =>
        [...document.querySelectorAll('[hidden]')]
          .filter(e => getComputedStyle(e).display !== 'none')
          .map(e => `${e.tagName}${e.id ? '#' + e.id : ''}: ${(e.innerText||'').slice(0,40)}`)
    """)

    assert visibles == [], f"elementos con [hidden] que el CSS sigue mostrando: {visibles}"


def test_el_filtro_por_pais_deja_solo_los_suyos(pagina: Any) -> None:
    """Y el efecto visible, no solo el atributo."""
    _esperar_capa(pagina, "epicentros")
    contar = """() => [...document.querySelectorAll('#lista-eventos li')]
                   .filter(l => l.offsetParent !== null).length"""

    todos = pagina.evaluate(contar)
    # Acotado al filtro: "Venezuela" aparece tambien en las tarjetas de
    # evento y en la tabla de cobertura, y sin acotar son cuatro nodos.
    pagina.locator("#filtro-paises").get_by_role("button", name="Venezuela").click()
    filtrado = pagina.evaluate(contar)

    assert todos > filtrado > 0, f"el filtro no redujo la lista: {todos} -> {filtrado}"
    paises = pagina.evaluate("""() =>
        [...document.querySelectorAll('#lista-eventos li')]
          .filter(l => l.offsetParent !== null)
          .map(l => l.dataset.iso3)
    """)
    assert set(paises) == {"VEN"}, f"con Venezuela seleccionado quedan {set(paises)}"


# --- Los controles del mapa no pueden comerse los botones -------------------


def test_las_pestanas_de_capa_se_pueden_pulsar(pagina: Any) -> None:
    """El peor caso: evento seleccionado, focos encendidos, pantalla de portatil.

    La pila de leyendas esta anclada abajo y crece hacia arriba. Con la leyenda
    de simbolos y la de potencia radiativa puestas a la vez se salia del mapa,
    tapaba la banda de "Exposicion no es dano" y dejaba **tres pestañas
    inpulsables** —Intensidad entre ellas, que es la capa por defecto—.

    No basta con mirar si las cajas se solapan: hay que preguntar quien recibe
    el clic. Las dos son `absolute` con el mismo `z-index`, asi que el solape
    visual y el funcional no son el mismo problema.
    """
    # Ventana corta a proposito. Con 720 px de alto la pila cabe y la prueba
    # pasaba sobre el codigo roto — comprobado desactivando el arreglo. El
    # fallo se midio con 603 px utiles, que es un portatil de 768 px con su
    # barra de navegador: la ventana mas comun que existe.
    pagina.set_viewport_size({"width": 1280, "height": 620})
    marca = _ahora(pagina)
    pagina.select_option("select", "us6000tjl2")
    _esperar_capa(pagina, "celdas", desde=marca)
    pagina.get_by_label("Focos activos", exact=False).check()
    _esperar_capa(pagina, "incendios")

    tapadas = pagina.evaluate("""() =>
        [...document.querySelectorAll('#capas button')].filter(b => {
          const r = b.getBoundingClientRect();
          const e = document.elementFromPoint(r.left + r.width/2, r.top + r.height/2);
          return !(e && e.closest('#capas'));
        }).map(b => b.innerText)
    """)

    assert tapadas == [], f"pestañas que no reciben el clic: {tapadas}"


def test_los_controles_no_tapan_el_aviso_de_que_esto_no_es_dano(pagina: Any) -> None:
    """«Exposición no es daño» es el encuadre entero de este sistema.

    Taparlo con una leyenda no rompe nada y cambia lo que la pagina significa.
    """
    # Ventana corta a proposito. Con 720 px de alto la pila cabe y la prueba
    # pasaba sobre el codigo roto — comprobado desactivando el arreglo. El
    # fallo se midio con 603 px utiles, que es un portatil de 768 px con su
    # barra de navegador: la ventana mas comun que existe.
    pagina.set_viewport_size({"width": 1280, "height": 620})
    marca = _ahora(pagina)
    pagina.select_option("select", "us6000tjl2")
    _esperar_capa(pagina, "celdas", desde=marca)
    pagina.get_by_label("Focos activos", exact=False).check()
    _esperar_capa(pagina, "incendios")

    solapa = pagina.evaluate("""() => {
        const p = document.querySelector('.controles-mapa').getBoundingClientRect();
        const a = document.querySelector('.aviso').getBoundingClientRect();
        return p.top < a.bottom;
    }""")

    assert not solapa, "la pila de controles vuelve a montarse sobre el aviso"


# --- Movil ------------------------------------------------------------------

#: Un telefono corriente. Es donde se amontona todo lo que en escritorio cabe.
MOVIL = {"width": 390, "height": 844}


def test_la_atribucion_del_mapa_no_queda_debajo_de_nada(pagina: Any) -> None:
    """No es estetica: OpenStreetMap es ODbL y exige que su credito se vea.

    Medido el 28-ago-2026 en 390x844: la pila de interruptores caia justo sobre
    `.maplibregl-ctrl-attrib` y `elementFromPoint` sobre su centro devolvia el
    interruptor de sismos menores. Un proyecto que rechaza fuentes enteras por
    incompatibilidad de licencia no puede taparle el credito al mapa que usa.

    `maplibre-gl.css` declara `z-index: 2` en esa regla y se carga despues, asi
    que la nuestra necesita dos clases para ganarle.
    """
    pagina.set_viewport_size(MOVIL)
    _esperar_capa(pagina, "epicentros")
    pagina.get_by_label("Focos activos", exact=False).check()
    _esperar_capa(pagina, "incendios")

    encima = pagina.evaluate("""() => {
        const a = document.querySelector('.maplibregl-ctrl-attrib');
        const r = a.getBoundingClientRect();
        const e = document.elementFromPoint(r.left + r.width/2, r.top + r.height/2);
        return e && a.contains(e) ? null : (e ? (e.className || e.tagName).toString() : 'nada');
    }""")

    assert encima is None, f"algo tapa la atribucion del mapa base: {encima}"


def test_la_pagina_no_se_desplaza_en_horizontal_en_movil(pagina: Any) -> None:
    """La tabla de cobertura arrastraba a toda la pagina.

    Diecinueve filas de cuatro columnas no caben en 390 px: la tabla se salia
    96 px y con ella se movian de lado el mapa, el panel y las tarjetas. Que se
    desplace la tabla, no la pagina.
    """
    pagina.set_viewport_size(MOVIL)
    _esperar_capa(pagina, "epicentros")

    medida = pagina.evaluate("""() => ({
        scroll: document.documentElement.scrollWidth,
        visible: document.documentElement.clientWidth,
    })""")

    assert medida["scroll"] <= medida["visible"] + 1, (
        f"la pagina se desplaza en horizontal: {medida['scroll']}px sobre {medida['visible']}px"
    )
