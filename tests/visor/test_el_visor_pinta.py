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

import re
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

    assert "window.CENTINELA = {" in app
    for clave in ("pintado,", "errores: erroresAlPintar,"):
        assert clave in app, f"el registro publico perdio {clave!r}"


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
    pagina.select_option("#filtro-paises", _iso_de(pagina, "Venezuela"))

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
    pagina.select_option("#filtro-paises", _iso_de(pagina, "Venezuela"))
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
    tapaba la banda de "Exposición no es daño" y dejaba **tres pestañas
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
    # Ya no se enciende el fuego encima: con el selector de amenaza, "evento +
    # focos" dejo de existir — entrar a fuego cierra el evento. El peor estado
    # del modo sismos es el evento con su leyenda y el conmutador delante.

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
    _esperar_capa(pagina, "incendios")
    pagina.locator('#amenazas button[data-amenaza="fuego"]').click()
    pagina.wait_for_timeout(600)

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


#: Detecta texto visible que se pisa con otro texto visible. Devuelve los pares.
#:
#: `checkVisibility` y no `offsetParent`: un `<details>` cerrado usa
#: `content-visibility`, asi que su contenido conserva caja y no se pinta. Sin
#: eso la sonda reportaba solapes que nadie ve — paso, y costo media hora
#: perseguir un fallo inexistente entre la leyenda y la atribucion.
SONDA_SOLAPES = """
() => {
  // `getBoundingClientRect` devuelve la posicion SIN recortar: un hijo dentro
  // de un contenedor con scroll se reporta donde estaria si el contenedor no
  // recortara, aunque no se pinte ahi. Sin esto la sonda daba por solapada la
  // leyenda de simbolos con la de intensidad — y el texto estaba recortado.
  const visibleTrasRecorte = e => {
    let r = e.getBoundingClientRect();
    for (let p = e.parentElement; p; p = p.parentElement) {
      const s = getComputedStyle(p);
      if (s.overflowY === 'visible' && s.overflowX === 'visible') continue;
      const c = p.getBoundingClientRect();
      if (r.bottom <= c.top + 1 || r.top >= c.bottom - 1) return false;
      if (r.right <= c.left + 1 || r.left >= c.right - 1) return false;
    }
    return true;
  };

  const conTexto = [...document.querySelectorAll('body *')].filter(e => {
    if (!e.checkVisibility({ contentVisibilityAuto: true, opacityProperty: true,
                             visibilityProperty: true })) return false;
    const r = e.getBoundingClientRect();
    if (r.width < 2 || r.height < 2) return false;
    if (r.bottom < 0 || r.top > innerHeight) return false;
    if (!visibleTrasRecorte(e)) return false;
    return [...e.childNodes].some(n => n.nodeType === 3 && n.textContent.trim().length > 1);
  });
  const pares = [];
  for (let i = 0; i < conTexto.length; i++) {
    for (let j = i + 1; j < conTexto.length; j++) {
      const a = conTexto[i], b = conTexto[j];
      if (a.contains(b) || b.contains(a)) continue;
      const ra = a.getBoundingClientRect(), rb = b.getBoundingClientRect();
      const ix = Math.min(ra.right, rb.right) - Math.max(ra.left, rb.left);
      const iy = Math.min(ra.bottom, rb.bottom) - Math.max(ra.top, rb.top);
      if (ix > 3 && iy > 3) pares.push(
        `«${a.textContent.trim().slice(0,24)}» sobre «${b.textContent.trim().slice(0,24)}»`);
    }
  }
  return pares;
}
"""


@pytest.mark.parametrize(
    ("etiqueta", "ancho", "alto"),
    [("movil", 390, 844), ("portatil", 1280, 620), ("escritorio", 1600, 900)],
)
def test_ningun_texto_se_pisa_con_otro(pagina: Any, etiqueta: str, ancho: int, alto: int) -> None:
    """El pie del mapa se apilaba sobre si mismo en un telefono.

    Medido el 28-ago-2026 en 390x844 con evento y focos: leyenda de intensidad
    553-708, interruptores 599-728, atribucion 706-730 — las tres cajas sobre el
    mismo rincon de 506 px de mapa. La leyenda, que es la que explica los
    colores, quedaba ilegible debajo de los interruptores.

    Se comprueba en los tres tamanos y con el peor estado (evento + focos)
    porque el fallo no existia en escritorio: el hueco solo aparece cuando el
    mapa se estrecha.
    """
    pagina.set_viewport_size({"width": ancho, "height": alto})
    _esperar_capa(pagina, "epicentros")
    _esperar_capa(pagina, "incendios")

    # Peor estado del modo sismos: un evento abierto, con leyenda y pestañas.
    marca = _ahora(pagina)
    pagina.select_option("select", "us6000tjl2")
    _esperar_capa(pagina, "celdas", desde=marca)
    pagina.wait_for_timeout(800)

    solapes = pagina.evaluate(SONDA_SOLAPES)
    assert solapes == [], f"en {etiqueta} ({ancho}x{alto}), modo sismos: {solapes}"

    # Y el modo fuego, que es un estado nuevo con su propia leyenda grande.
    pagina.locator('#amenazas button[data-amenaza="fuego"]').click()
    pagina.wait_for_selector("#leyenda:not([hidden])", timeout=ESPERA_MS)
    pagina.wait_for_timeout(800)

    solapes = pagina.evaluate(SONDA_SOLAPES)
    assert solapes == [], f"en {etiqueta} ({ancho}x{alto}), modo fuego: {solapes}"


# --- Lo que un control promete tiene que ser lo que enciende -----------------


def test_el_modo_fuego_promete_lo_que_dibuja(pagina: Any) -> None:
    """La casilla decia 15.607 celdas y el mapa dibujaba 4.000.

    El control cambio —el checkbox de esquina es hoy el selector de amenaza—
    pero la invariante que esta prueba guarda es la misma: el numero que la
    interfaz ensena tiene que ser uno que el mapa pueda respaldar, y el recorte
    tiene que decir su criterio.
    """
    anotacion = _esperar_capa(pagina, "incendios")
    totales = pagina.evaluate("fetch('incendios.json').then(r => r.json()).then(d => d.totales)")
    dibujadas = anotacion["rasgos"]
    publicadas = totales["celdas_publicadas"]
    total = totales["celdas"]

    assert dibujadas == publicadas, (
        f"el mapa dibujo {dibujadas} celdas y el JSON declara {publicadas} publicadas"
    )

    def es(n: int) -> str:
        # Agrupado siempre, como lo hace el visor con este par de cifras: por
        # defecto el español no separa los millares hasta cinco digitos y
        # "4000 de 15.607" parece una errata.
        texto: str = pagina.evaluate(
            "n => new Intl.NumberFormat('es', { useGrouping: 'always' }).format(n)", n
        )
        return texto

    pagina.locator('#amenazas button[data-amenaza="fuego"]').click()
    pagina.wait_for_selector("#leyenda:not([hidden])", timeout=ESPERA_MS)

    # `inner_text` devuelve versalitas (la trampa de siempre) y la nota vive
    # dentro del <details> plegado: se abre, que ademas comprueba que la
    # explicacion es alcanzable.
    pagina.locator("#leyenda .leyenda-detalle summary").click()
    leyenda = pagina.locator("#leyenda").inner_text()
    assert "potencia radiativa" in leyenda.lower(), f"el modo fuego no trae su leyenda: {leyenda!r}"
    if publicadas < total:
        assert es(dibujadas) in leyenda and es(total) in leyenda, (
            f"la leyenda no dice el recorte ({es(dibujadas)} de {es(total)}): {leyenda!r}"
        )
        assert "gente debajo" in leyenda, f"la leyenda no dice el criterio del recorte: {leyenda!r}"


# --- Sin libreria de mapas ---------------------------------------------------


def test_sin_libreria_de_mapas_el_aviso_no_se_queda_eterno(navegador: Any, servidor: str) -> None:
    """«Cargando el mapa» giraba para siempre si unpkg no respondia.

    La red de seguridad existia —`setTimeout(listo, 8000)`— pero vivia dentro de
    `iniciarMapa()`, **despues** del `return` temprano que se dispara cuando
    `maplibregl` es `undefined`: justo el caso que tenia que cubrir era el unico
    que no cubria. Medido el 28-ago-2026 con los `<script>` de unpkg apuntando a
    404: treinta y un segundos girando.

    Lo que hace grave a un aviso eterno es lo que hay debajo: los veintiun
    reportes, la cobertura y el panel de un evento entero funcionaban. La pagina
    servia y parecia rota.
    """
    ctx = navegador.new_context(viewport={"width": 1400, "height": 900})
    pg = ctx.new_page()
    errores: list[str] = []
    pg.on("pageerror", lambda e: errores.append(str(e)))
    # El CDN, caido. Se corta la libreria de mapas y se deja todo lo demas.
    pg.route("**/maplibre-gl.js*", lambda ruta: ruta.abort())
    try:
        pg.goto(f"{servidor}/index.html")
        pg.wait_for_function(
            "() => document.querySelectorAll('#lista-eventos li').length > 0", timeout=ESPERA_MS
        )

        aviso = pg.locator("#cargando")
        # `inner_text` devuelve el texto **renderizado** y `.mono` va en
        # versalitas, asi que aqui llega "CARGANDO EL MAPA". Comparar sin
        # normalizar la caja dejaba pasar la prueba por el motivo equivocado.
        texto = aviso.inner_text()

        assert "cargando" not in texto.lower(), (
            f"el aviso de carga sigue puesto sin libreria de mapas: {texto!r}"
        )
        assert texto.strip(), "el aviso se quito sin decir que el mapa no esta"
        assert "mapa" in texto.lower(), (
            f"el aviso no explica que lo que falta es el mapa: {texto!r}"
        )
        assert aviso.locator(".giro").count() == 0, (
            "el girito sigue girando sobre un mapa que no va a existir"
        )

        # Y lo de debajo, intacto: es la mitad del argumento para no alarmar.
        eventos = pg.evaluate("document.querySelectorAll('#lista-eventos li').length")
        catalogo = pg.evaluate(
            "fetch('reports/index.json').then(r => r.json()).then(e => e.length)"
        )
        assert eventos == catalogo, f"sin mapa la lista quedo en {eventos} de {catalogo}"
        assert pg.evaluate("document.querySelectorAll('#tabla-cobertura tbody tr').length") > 0, (
            "sin mapa la cobertura regional no se pinto"
        )

        assert not errores, f"la pagina lanzo errores de JavaScript: {errores}"
    finally:
        ctx.close()


# --- Cuanto territorio, no solo cuanta gente --------------------------------


def test_el_area_de_afectacion_cuadra_con_la_malla(pagina: Any) -> None:
    """El tablero contaba gente y no decia nunca sobre que superficie.

    "2,4 M de personas en MMI≥7" describe igual de bien una ciudad sacudida que
    media cordillera, y son dos emergencias distintas. El area sale de contar
    las celdas que ya se dibujan, asi que se puede comprobar contra el registro
    de pintado: si el bloque dice mas km² de los que hay celdas, esta inventando.
    """
    marca = _ahora(pagina)
    pagina.select_option("select", "us6000tjl2")
    celdas = _esperar_capa(pagina, "celdas", desde=marca)

    bloque = pagina.locator("#bloque-area")
    assert bloque.is_visible(), "el evento trae malla y el bloque de area no salio"

    # El total de la malla que declara el panel no puede exceder el de la capa.
    dibujadas = celdas["rasgos"]
    area = pagina.locator("#detalle-area").inner_text()
    numeros = [
        int(n.replace(".", "")) for n in re.findall(r"([\d.]+) km²", area.replace("KM²", "km²"))
    ]
    assert numeros, f"el bloque de area no publica ninguna cifra: {area!r}"
    assert max(numeros) <= dibujadas * 5.2 + 1, (
        f"el area declarada ({max(numeros)} km²) supera la de las {dibujadas} celdas dibujadas"
    )


def test_las_cifras_vulnerables_llevan_su_proporcion(pagina: Any) -> None:
    """Un conteo no dice si es mucho.

    "289.000 personas de 65 anos o mas" no significa nada hasta saber que son el
    12 % de los expuestos, y "1,6 M sobre suelo licuable" tampoco hasta saber que
    son dos de cada tres. La division se podia hacer con los numeros que el
    reporte ya trae y no se hacia.
    """
    marca = _ahora(pagina)
    pagina.select_option("select", "us6000tjl2")
    _esperar_capa(pagina, "celdas", desde=marca)

    metricas = pagina.locator("#detalle-metricas").inner_text()
    assert "de los expuestos" in metricas, (
        f"la cifra de mayores de 65 sigue sin su proporcion: {metricas!r}"
    )

    terreno = pagina.locator("#detalle-terreno").inner_text()
    assert "de los expuestos" in terreno, f"la licuefaccion sigue sin su proporcion: {terreno!r}"


# --- El area de afectacion tiene forma, no solo cifra ------------------------


def test_el_perimetro_encierra_exactamente_lo_que_se_cuenta(pagina: Any) -> None:
    """A escala regional 890 hexagonos no se leen como una zona: se leen como
    textura. La pregunta "¿que area quedo dentro?" tenia cifra y no tenia forma.

    Lo que hace honesto a este perimetro es que sale de disolver **las mismas
    celdas que se cuentan**, no de una isolinea de otro producto: el borde y el
    "4.628 km²" del panel son el mismo objeto. Por eso la prueba compara el
    numero de celdas disueltas con las que el panel declara.
    """
    marca = _ahora(pagina)
    pagina.select_option("select", "us6000tjl2")
    _esperar_capa(pagina, "celdas", desde=marca)
    perimetro = _esperar_capa(pagina, "perimetro", desde=marca)

    assert perimetro["rasgos"] > 0, "la malla se dibujo y el perimetro salio vacio"

    area = pagina.locator("#detalle-area").inner_text()
    encaje = re.search(r"([\d.]+) celdas", area)
    assert encaje, f"el bloque de area no dice cuantas celdas hay detras: {area!r}"
    celdas_panel = int(encaje.group(1).replace(".", ""))
    assert perimetro["rasgos"] == celdas_panel, (
        f"el panel dice {celdas_panel} celdas y el perimetro disolvio {perimetro['rasgos']}"
    )


def test_volver_al_panorama_no_deja_capas_del_evento(pagina: Any) -> None:
    """`cerrarDetalle` quitaba la malla y se dejaba los contornos.

    No se notaba porque las isolineas son palidas sobre un mapa continental. Al
    anadir el perimetro —tinta oscura— quedo a la vista: al volver al panorama
    flotaba el borde de un area cuyo panel ya no existia.
    """
    marca = _ahora(pagina)
    pagina.select_option("select", "us6000tjl2")
    _esperar_capa(pagina, "celdas", desde=marca)
    _esperar_capa(pagina, "perimetro", desde=marca)

    pagina.locator("#volver").click()
    pagina.wait_for_function(
        """() => {
             const p = window.CENTINELA.pintado;
             return ['celdas', 'contornos', 'perimetro'].every((c) => p[c] && p[c].rasgos === 0);
           }""",
        timeout=ESPERA_MS,
    )

    quedan = pagina.evaluate(
        "['celdas','contornos','perimetro'].filter(c => window.CENTINELA.pintado[c].rasgos > 0)"
    )
    assert quedan == [], f"al volver al panorama quedaron capas del evento: {quedan}"


# --- La lista responde a mas de una pregunta --------------------------------


def _titulos_visibles(pagina: Any) -> list[str]:
    titulos: list[str] = pagina.evaluate(
        """() => [...document.querySelectorAll('#lista-eventos li')]
                   .filter(li => !li.hidden)
                   .map(li => li.querySelector('a').textContent)"""
    )
    return titulos


def test_la_lista_se_ordena_por_lo_que_se_le_pide(pagina: Any) -> None:
    """Iba siempre por fecha, que responde "¿que ha pasado ultimamente?".

    Las otras dos preguntas no tenian respuesta sin leer las veintiuna tarjetas,
    y no son la misma: el M8 de Peru deja 248.000 personas en MMI≥7 y el M7,4 del
    Choco deja 2,4 millones. Ordenar por magnitud y por exposicion tiene que dar
    listas distintas, y esa diferencia es justamente el hallazgo.
    """
    _esperar_capa(pagina, "epicentros")

    pagina.select_option("#orden-lista", "mag")
    por_mag = pagina.evaluate(
        """() => [...document.querySelectorAll('#lista-eventos li')]
                   .filter(li => !li.hidden).map(li => Number(li.dataset.mag))"""
    )
    assert por_mag == sorted(por_mag, reverse=True), f"el orden por magnitud no baja: {por_mag}"

    pagina.select_option("#orden-lista", "pop")
    por_pop = pagina.evaluate(
        """() => [...document.querySelectorAll('#lista-eventos li')]
                   .filter(li => !li.hidden).map(li => Number(li.dataset.pop))"""
    )
    assert por_pop == sorted(por_pop, reverse=True), f"el orden por exposicion no baja: {por_pop}"

    assert _titulos_visibles(pagina) != [], "la lista se quedo vacia al reordenar"
    assert pagina.locator("#orden-lista").input_value() == "pop", (
        "el control no refleja el orden puesto"
    )


def test_la_lista_se_recorta_al_encuadre_del_mapa(pagina: Any) -> None:
    """El mapa ensenaba dos epicentros y la lista seguia ensenando veintiuno.

    Es el gesto de Wildfire Aware —"138 incendios a la vista", y uno solo al
    acercarse— y aqui vale igual: mapa y lista son el mismo conjunto mirado de
    dos maneras, y no lo eran.
    """
    _esperar_capa(pagina, "epicentros")
    todos = len(_titulos_visibles(pagina))
    assert todos > 1, "hacen falta varios reportes para que esta prueba diga algo"

    marca = _ahora(pagina)
    pagina.select_option("select", "us6000tjl2")
    _esperar_capa(pagina, "celdas", desde=marca)

    pagina.locator("#solo-en-vista").check()
    pagina.wait_for_function(
        "(n) => document.querySelectorAll('#lista-eventos li:not([hidden])').length < n",
        arg=todos,
        timeout=ESPERA_MS,
    )

    en_vista = _titulos_visibles(pagina)
    assert 0 < len(en_vista) < todos, (
        f"con el mapa sobre el Choco la lista deberia recortarse; "
        f"quedo en {len(en_vista)} de {todos}"
    )
    assert "encuadre" in pagina.locator("#cuenta-lista").inner_text().lower(), (
        "el contador no dice que la lista esta recortada al encuadre"
    )


# --- Lo que la sonda de solapes no veia -------------------------------------


#: Solapes **dentro de una seccion**, ignorando la barra fija.
#:
#: `SONDA_SOLAPES` recorre la pantalla entera, y en cuanto se desplaza la pagina
#: la barra pegajosa queda sobre el contenido y da siete pares que no son un
#: fallo: para eso lleva fondo. Esta sonda mira una sola seccion.
SONDA_SOLAPES_EN = """
(sel) => {
  const raiz = document.querySelector(sel);
  const conTexto = [...raiz.querySelectorAll('*'), raiz].filter(e => {
    if (!e.checkVisibility({ visibilityProperty: true, opacityProperty: true })) return false;
    const r = e.getBoundingClientRect();
    if (r.width < 2 || r.height < 2) return false;
    return [...e.childNodes].some(n => n.nodeType === 3 && n.textContent.trim().length > 1);
  });
  const pares = [];
  for (let i = 0; i < conTexto.length; i++) {
    for (let j = i + 1; j < conTexto.length; j++) {
      const a = conTexto[i], b = conTexto[j];
      if (a.contains(b) || b.contains(a)) continue;
      const ra = a.getBoundingClientRect(), rb = b.getBoundingClientRect();
      const ox = Math.min(ra.right, rb.right) - Math.max(ra.left, rb.left);
      const oy = Math.min(ra.bottom, rb.bottom) - Math.max(ra.top, rb.top);
      if (ox > 2 && oy > 2) {
        const corta = (e) => e.textContent.trim().slice(0, 22);
        pares.push(`«${corta(a)}» sobre «${corta(b)}»`);
      }
    }
  }
  return pares;
}
"""


@pytest.mark.parametrize("ancho", [360, 390, 768, 1024, 1280, 1600])
def test_la_reticula_no_se_pisa_con_el_titular(pagina: Any, ancho: int) -> None:
    """La sonda de solapes solo mira lo que cabe en pantalla, y esta seccion vive
    bajo el pliegue: por eso paso desapercibido durante toda una auditoria.

    La etiqueta "12°N" iba clavada a 0,85rem del borde y terminaba en el pixel
    41; el titular de "Reportes publicados" empieza en el 28. Se pisaban de 360 a
    1200 px —cualquier telefono y casi cualquier portatil— y solo se libraba a
    partir de 1440, cuando el contenedor se centra y deja hueco.
    """
    pagina.set_viewport_size({"width": ancho, "height": 800})
    _esperar_capa(pagina, "epicentros")
    pagina.locator("#eventos h2").scroll_into_view_if_needed()
    pagina.wait_for_timeout(400)

    solapes = pagina.evaluate(SONDA_SOLAPES_EN, "#eventos")

    assert solapes == [], f"a {ancho} px hay texto encima de otro en la lista: {solapes}"


@pytest.mark.parametrize("ancho", [320, 344, 360, 390])
def test_la_pagina_no_se_desplaza_de_lado_en_pantallas_estrechas(pagina: Any, ancho: int) -> None:
    """La rejilla de tarjetas pedia columnas de 20rem que no encogian.

    En un iPhone SE de 320 px la lista empujaba 35 px fuera de la ventana y
    arrastraba a toda la pagina, mapa incluido. Medido: 320 -> 35, 344 -> 11,
    360 -> 0. La prueba que ya habia solo miraba 390, justo por encima del
    umbral donde el fallo empieza.
    """
    pagina.set_viewport_size({"width": ancho, "height": 780})
    _esperar_capa(pagina, "epicentros")

    medida = pagina.evaluate("""() => ({
        scroll: document.documentElement.scrollWidth,
        visible: document.documentElement.clientWidth,
    })""")

    assert medida["scroll"] <= medida["visible"] + 1, (
        f"a {ancho} px la pagina se desplaza de lado: {medida['scroll']} sobre {medida['visible']}"
    )


# --- Que se sepa de cuando es cada cifra ------------------------------------


def test_las_cifras_en_vivo_dicen_cuando_se_revisaron(pagina: Any) -> None:
    """El comentario de `pintarEnVivo` lo prometia desde que se escribio —"por
    eso llevan la hora de la ultima revision: sin ella, «14.984 celdas con
    fuego» podria ser de hace un mes"— y no lo cumplia.

    Un tablero que se presenta como vigilancia en vivo y no fecha sus cifras
    pide una confianza que no ha ganado.
    """
    _esperar_capa(pagina, "incendios")
    vivo = pagina.locator("#en-vivo")

    assert vivo.is_visible(), "la tarjeta en vivo no salio"
    texto = vivo.inner_text()
    assert "revisado" in texto.lower(), f"ninguna cifra dice cuando se reviso: {texto!r}"

    # Y la marca exacta, para quien la quiera, en el `title`.
    sellos = pagina.locator("#en-vivo .revisado")
    assert sellos.count() > 0
    assert sellos.first.get_attribute("title"), "el sello no lleva la fecha exacta"


# --- El globo no puede sobrevivir a lo que describe -------------------------


def test_el_globo_de_una_celda_se_va_con_su_evento(pagina: Any) -> None:
    """Se abria una celda, se pulsaba "Volver al panorama" y el globo se quedaba
    flotando sobre el mapa continental: describia una celda de un evento cerrado
    sobre una malla que ya no estaba, y era el unico de los tres popups sin
    boton de cerrar.
    """
    marca = _ahora(pagina)
    pagina.select_option("select", "us6000tjl2")
    _esperar_capa(pagina, "celdas", desde=marca)

    # Se espera a que el vuelo al evento termine: pulsar mientras la camara se
    # mueve es pulsar sobre una malla que todavia no esta donde se ve.
    pagina.wait_for_timeout(2000)

    # Y la malla tiene huecos —son ausencia de gente, no de sacudida— asi que el
    # centro del mapa no siempre cae sobre una celda. Se barre una rejilla.
    caja = pagina.locator("#mapa").bounding_box()
    assert caja
    abierto = False
    for fy in (0.35, 0.45, 0.55, 0.65):
        for fx in (0.35, 0.45, 0.55):
            pagina.mouse.click(caja["x"] + caja["width"] * fx, caja["y"] + caja["height"] * fy)
            pagina.wait_for_timeout(320)
            if pagina.locator(".maplibregl-popup").count():
                abierto = True
                break
        if abierto:
            break
    assert abierto, "no se pudo abrir el globo de ninguna celda de la malla"

    assert pagina.locator(".maplibregl-popup-close-button").count() > 0, (
        "el globo de celda sigue sin boton de cerrar"
    )

    pagina.locator("#volver").click()
    pagina.wait_for_selector(".maplibregl-popup", state="detached", timeout=ESPERA_MS)

    assert pagina.locator(".maplibregl-popup").count() == 0, (
        "al volver al panorama quedo un globo describiendo un evento cerrado"
    )


# --- Un enlace roto tiene que decir que lo esta -----------------------------


def test_un_enlace_a_un_reporte_que_no_existe_lo_dice(navegador: Any, servidor: str) -> None:
    """`?evento=NO_EXISTE` caia al panorama en silencio, con el parametro todavia
    en la barra. Quien llega desde un enlace compartido a un reporte retirado
    cree que pulso mal.
    """
    ctx = navegador.new_context(viewport={"width": 1400, "height": 900})
    pg = ctx.new_page()
    try:
        pg.goto(f"{servidor}/index.html?evento=NO_EXISTE")
        pg.wait_for_function(
            "() => document.querySelectorAll('#lista-eventos li').length > 0",
            timeout=ESPERA_MS,
        )

        aviso = pg.locator("#estado-lista")
        assert aviso.is_visible(), "no se dijo nada sobre el reporte que no existe"
        assert "NO_EXISTE" in aviso.inner_text(), (
            f"el aviso no nombra el identificador pedido: {aviso.inner_text()!r}"
        )
        # Y el panorama entero sigue delante, que es lo que hay que ofrecer.
        assert pg.locator("#lateral-detalle").is_hidden()
        assert "evento=" not in pg.url, (
            "el parametro roto sigue en la barra: recargar repite el error"
        )
    finally:
        ctx.close()


def test_un_enlace_profundo_deja_la_camara_sobre_su_evento(navegador: Any, servidor: str) -> None:
    """El encuadre de apertura le robaba la camara al enlace profundo.

    `cuandoElEstiloEsteListo` se dispara con `isStyleLoaded()`, que llega antes
    que `load`: con `?evento=...` la secuencia real era volar al evento y luego
    que el encuadre de apertura lo devolviera al panorama. Se veia la malla del
    sismo del tamano de un sello en mitad de America Latina.

    Las otras pruebas abren el evento con `select_option` **despues** de cargar,
    y por ese camino no hay carrera: esta entra por la URL, que es como llega
    quien recibe un enlace compartido.

    Se comprueba con el recorte al encuadre, que ya existe: si la camara esta
    sobre el Choco solo cae un reporte dentro; si volvio al panorama, los 21.
    """
    ctx = navegador.new_context(viewport={"width": 1400, "height": 900})
    pg = ctx.new_page()
    try:
        # La carrera solo aparece cuando `load` llega **tarde**, y en local no
        # llega tarde: el servidor esta a un milisegundo. Se retrasan las teselas
        # —no el estilo— para reproducir el orden de la pagina publicada.
        #
        # Sin esto la prueba pasaba con el fallo puesto, que es una prueba que no
        # prueba nada. Comprobado: sin el arreglo da "21 de 21 en el encuadre".
        def _lento(ruta: Any) -> None:
            import time

            time.sleep(1.2)
            ruta.continue_()

        pg.route("**/tiles.openfreemap.org/**/*.pbf", _lento)

        pg.goto(f"{servidor}/index.html?evento=us6000tjl2")
        pg.wait_for_function(
            """() => {
                 const p = window.CENTINELA && window.CENTINELA.pintado;
                 return !!(p && p.celdas && p.celdas.rasgos > 0);
               }""",
            timeout=ESPERA_MS,
        )
        # El vuelo dura `VUELO` ms, y hay que dejar que `load` llegue y haga —o
        # no haga— lo suyo.
        pg.wait_for_timeout(5000)

        pg.locator("#solo-en-vista").check()
        pg.wait_for_timeout(600)

        en_vista = pg.evaluate(
            "document.querySelectorAll('#lista-eventos li:not([hidden])').length"
        )
        total = pg.evaluate("document.querySelectorAll('#lista-eventos li').length")

        assert en_vista < total, (
            f"con un enlace profundo la camara se quedo en el panorama: "
            f"{en_vista} de {total} reportes en el encuadre"
        )
    finally:
        ctx.close()


# --- La pagina de estado hace la resta --------------------------------------


def test_estado_dice_que_la_cadencia_se_come_el_objetivo(navegador: Any, servidor: str) -> None:
    """El objetivo y la cadencia real vivian en dos bloques distintos de la
    pagina y nadie los ponia uno al lado del otro.

    La conclusion sale de datos que ya se publican: si el vigia tarda 157 min de
    mediana solo en **mirar** el feed, un objetivo de 60 min desde que hay
    ShakeMap no se puede cumplir aunque el resto del pipeline fuera instantaneo.

    Decirlo es lo mismo que hace el resto del sistema con el desvio de poblacion
    —publicarlo aunque incomode— y es lo que impide que un objetivo se quede de
    adorno.
    """
    ctx = navegador.new_context(viewport={"width": 1200, "height": 900})
    pg = ctx.new_page()
    try:
        pg.goto(f"{servidor}/status.html")
        pg.wait_for_selector("#resumen:not(.cargando)", timeout=ESPERA_MS)

        datos = pg.evaluate(
            "fetch('status.json').then(r => r.json())"
            ".then(d => ({objetivo: d.objetivo.p50_min, cadencia: d.cadencia.p50_min}))"
        )
        se_come = datos["cadencia"] is not None and datos["cadencia"] > datos["objetivo"]

        aviso = pg.locator(".nota-alarma")
        if se_come:
            assert aviso.count() == 1, (
                f"la cadencia ({datos['cadencia']} min) supera el objetivo "
                f"({datos['objetivo']} min) y la pagina no lo dice"
            )
            texto = aviso.inner_text()
            assert "vigía" in texto and "objetivo" in texto
        else:
            assert aviso.count() == 0, "la cadencia cumple el objetivo y la pagina avisa igualmente"
    finally:
        ctx.close()


# --- El globo de un foco de fuego -------------------------------------------


def test_el_globo_de_un_foco_dice_que_arde_y_sobre_quien(pagina: Any) -> None:
    """El ultimo eslabon del E2E de fuego que faltaba por ejercitar.

    La cadena FIRMS -> P5 -> JSON -> capa dibujada ya esta cubierta; el globo
    del foco —`cuadroDeIncendio`, el unico sitio donde una celda de fuego
    concreta cuenta su potencia y su gente— no lo estaba. Y no es plumbing
    duplicado: su handler cuelga de capas propias ("incendios",
    "incendios-punto") y su contenido tiene logica —omitir la poblacion cero
    para no venderla como medicion— que nadie mas ejercita.

    Se busca un foco barriendo el cursor por el interior este del continente
    —Amazonia y cerrado, donde arde y no hay epicentros— y se exige el rotulo
    propio del globo de fuego, no cualquier globo.
    """
    _esperar_capa(pagina, "incendios")
    pagina.locator('#amenazas button[data-amenaza="fuego"]').click()
    pagina.wait_for_timeout(1200)

    caja = pagina.locator("#mapa").bounding_box()
    assert caja

    abierto = False
    for fy in (0.52, 0.56, 0.6, 0.64, 0.68, 0.72, 0.76):
        for fx in (0.56, 0.6, 0.64, 0.68, 0.72, 0.76, 0.8):
            x = caja["x"] + caja["width"] * fx
            y = caja["y"] + caja["height"] * fy
            pagina.mouse.move(x, y)
            cursor = pagina.evaluate("document.querySelector('#mapa canvas').style.cursor")
            if cursor == "pointer":
                pagina.mouse.click(x, y)
                pagina.wait_for_timeout(500)
                if pagina.locator(".popup-incendio").count():
                    abierto = True
                    break
                # Era otra cosa pulsable (un epicentro despistado): se cierra y
                # se sigue barriendo.
                pagina.keyboard.press("Escape")
                pagina.wait_for_timeout(300)
        if abierto:
            break

    assert abierto, "no se pudo abrir el globo de ningun foco en la zona de quemas"

    # `inner_text` devuelve el texto renderizado y el eyebrow va en versalitas
    # por CSS — la misma trampa que ya mordio en "CARGANDO EL MAPA".
    texto = pagina.locator(".popup-incendio").inner_text()
    assert "celda con fuego activo" in texto.lower(), f"el globo no se rotula como fuego: {texto!r}"
    assert "Potencia radiativa" in texto and "MW" in texto, (
        f"el globo no dice la energia medida: {texto!r}"
    )
    assert "Detecciones" in texto, f"el globo no dice cuantas veces se vio: {texto!r}"


# --- El selector de amenaza --------------------------------------------------


def test_el_selector_de_amenaza_cambia_el_lente(pagina: Any) -> None:
    """El fuego deja de ser un checkbox: es un modo con el mismo rango que los
    sismos, con su leyenda en el hueco grande y su URL compartible.
    """
    _esperar_capa(pagina, "incendios")

    boton_fuego = pagina.locator('#amenazas button[data-amenaza="fuego"]')
    boton_sismos = pagina.locator('#amenazas button[data-amenaza="sismos"]')
    assert boton_sismos.get_attribute("aria-pressed") == "true", "sismos es el defecto"

    boton_fuego.click()
    pagina.wait_for_selector("#leyenda:not([hidden])", timeout=ESPERA_MS)

    assert boton_fuego.get_attribute("aria-pressed") == "true"
    assert "amenaza=fuego" in pagina.url, "el modo no viaja en la URL"
    assert "potencia radiativa" in pagina.locator("#leyenda").inner_text().lower()
    assert pagina.locator("#interruptor-observados").is_hidden(), (
        "el control de sismos menores es del modo sismos y sigue a la vista"
    )

    # Y de vuelta: el hueco grande se libera y la URL queda limpia.
    boton_sismos.click()
    pagina.wait_for_selector("#leyenda[hidden]", state="attached", timeout=ESPERA_MS)
    assert "amenaza" not in pagina.url
    assert pagina.locator("#interruptor-observados").is_visible()


def test_abrir_un_evento_desde_el_modo_fuego_vuelve_a_sismos(pagina: Any) -> None:
    """Un evento abierto es contenido del modo sismos, llegue de donde llegue.

    Sin esta regla, elegir un reporte en modo fuego dejaria el panel contando
    poblacion por franja de intensidad sobre un mapa que dibuja potencia
    radiativa: dos amenazas hablando a la vez, que es justo lo que el selector
    existe para impedir.
    """
    _esperar_capa(pagina, "incendios")
    pagina.locator('#amenazas button[data-amenaza="fuego"]').click()
    pagina.wait_for_selector("#leyenda:not([hidden])", timeout=ESPERA_MS)

    marca = _ahora(pagina)
    pagina.select_option("select", "us6000tjl2")
    _esperar_capa(pagina, "celdas", desde=marca)

    assert (
        pagina.locator('#amenazas button[data-amenaza="sismos"]').get_attribute("aria-pressed")
        == "true"
    ), "el evento se abrio y el fuego sigue al mando"
    assert "intensidad" in pagina.locator("#leyenda").inner_text().lower(), (
        "la leyenda no volvio a la variable de la malla"
    )
    assert "evento=us6000tjl2" in pagina.url and "amenaza" not in pagina.url


def test_el_enlace_profundo_al_modo_fuego(navegador: Any, servidor: str) -> None:
    """?amenaza=fuego abre con el fuego al mando aunque sus capas carguen tarde.

    Las capas llegan en paralelo y el modo se aplica cuando cada una termina de
    dibujarse: sin eso, un enlace compartido en modo fuego abriria en sismos
    con el fuego invisible, que es el estado que el enlace venia a evitar.
    """
    ctx = navegador.new_context(viewport={"width": 1400, "height": 900})
    pg = ctx.new_page()
    try:
        pg.goto(f"{servidor}/index.html?amenaza=fuego")
        pg.wait_for_function(
            """() => {
                 const p = window.CENTINELA && window.CENTINELA.pintado;
                 return !!(p && p.incendios && p.incendios.rasgos > 0);
               }""",
            timeout=ESPERA_MS,
        )
        pg.wait_for_selector("#leyenda:not([hidden])", timeout=ESPERA_MS)

        assert (
            pg.locator('#amenazas button[data-amenaza="fuego"]').get_attribute("aria-pressed")
            == "true"
        )
        assert "potencia radiativa" in pg.locator("#leyenda").inner_text().lower()
    finally:
        ctx.close()


# --- Focos de incendio (30-ago-2026) ----------------------------------------
#
# Cinco pruebas para lo que el visor no sabia hacer: un incendio era una celda
# suelta con un globo, la tarjeta daba el total de America Latina sin decirlo, y
# el panel mezclaba las dos amenazas.


def test_las_celdas_contiguas_se_agrupan_en_focos(pagina: Any) -> None:
    """Un incendio no es un hexagono de 5,2 km²: es el grupo que arde junto.

    Sin agrupar, la unica respuesta a "¿que tan grande es este fuego?" era el
    total regional o una celda. Ninguna de las dos es un incendio.
    """
    pagina.locator('#amenazas button[data-amenaza="fuego"]').click()
    celdas = _esperar_capa(pagina, "incendios")["rasgos"]
    focos = _esperar_capa(pagina, "focos")["rasgos"]

    assert focos > 0, "no se agrupo ni un foco"
    assert focos < celdas, (
        f"{focos} focos para {celdas} celdas: si no hay ninguna celda contigua "
        "a otra, el agrupado no esta uniendo nada"
    )


def test_abrir_un_foco_dice_su_area_y_dibuja_su_perimetro(pagina: Any) -> None:
    """La pregunta que el visor no respondia: cuanta superficie cubre esto.

    El area sale de contar celdas, asi que tiene que cuadrar con el numero de
    celdas que el propio panel declara. Publicar un area que no se deduce de lo
    que se ve al lado seria una cifra sin respaldo.
    """
    pagina.locator('#amenazas button[data-amenaza="fuego"]').click()
    _esperar_capa(pagina, "incendios")
    _esperar_capa(pagina, "focos")

    foco = pagina.evaluate("() => window.CENTINELA.abrirFoco(0)")
    assert foco and foco["celdas"] >= 1

    pagina.wait_for_selector("#detalle-fuego:not([hidden])", timeout=ESPERA_MS)
    _esperar_capa(pagina, "foco-perimetro")

    texto = pagina.locator("#fuego-area").inner_text().lower()
    esperado = round(foco["celdas"] * 5.2)
    assert f"{esperado:,}".replace(",", ".") in texto or str(esperado) in texto, (
        f"el panel deberia decir {esperado} km² para {foco['celdas']} celdas: {texto!r}"
    )


def test_en_modo_sismos_no_queda_rastro_de_incendios(pagina: Any) -> None:
    """El fallo que se veia de un vistazo en el panel.

    En modo fuego el lateral seguia mostrando "9 sismos vistos y no despachados"
    y debajo el panorama sismico entero. Al reves, en modo sismos seguia la
    tarjeta de fuego. Dos amenazas hablando a la vez es lo que el selector
    existe para evitar.
    """
    pagina.locator('#amenazas button[data-amenaza="fuego"]').click()
    _esperar_capa(pagina, "incendios")
    # `wait_for_selector` espera a que sea VISIBLE por defecto, y un elemento
    # oculto no lo es nunca: hay que pedir el estado explicitamente.
    pagina.wait_for_selector("#bloque-panorama[hidden]", state="attached", timeout=ESPERA_MS)

    pagina.locator('#amenazas button[data-amenaza="sismos"]').click()
    pagina.wait_for_selector("#bloque-panorama:not([hidden])", timeout=ESPERA_MS)
    pagina.wait_for_timeout(600)

    lateral = pagina.locator("#lateral").inner_text().lower()
    intrusos = [p for p in ("fuego", "incendio", "ardiendo", "radiativa") if p in lateral]
    assert not intrusos, f"el panel de sismos habla de incendios: {intrusos}"


def test_volver_de_un_foco_devuelve_el_panorama(pagina: Any) -> None:
    """La regresion que se introdujo al arreglar esto, cazada en el navegador.

    `cerrarFoco` restauraba el panel solo si la amenaza seguia siendo fuego, y
    `aplicarAmenaza` lo llama **despues** de cambiar de modo: al pasar a sismos
    la condicion ya era falsa, y volver a fuego dejaba el lateral en blanco.
    """
    pagina.locator('#amenazas button[data-amenaza="fuego"]').click()
    _esperar_capa(pagina, "focos")
    pagina.evaluate("() => window.CENTINELA.abrirFoco(0)")
    pagina.wait_for_selector("#detalle-fuego:not([hidden])", timeout=ESPERA_MS)

    # El camino largo: salir por el cambio de modo, no por el boton.
    pagina.locator('#amenazas button[data-amenaza="sismos"]').click()
    pagina.wait_for_timeout(700)
    pagina.locator('#amenazas button[data-amenaza="fuego"]').click()
    pagina.wait_for_timeout(700)

    assert pagina.locator("#lateral-vacio").is_visible(), "el lateral se quedo en blanco"
    assert "ahora mismo" in pagina.locator("#lateral").inner_text().lower()


def test_la_cifra_viva_ocupa_la_fila_y_no_se_sale(pagina: Any) -> None:
    """El "no tiene margen" que se ve en cuanto alguien mira el panel.

    `.metricas` es una rejilla de dos columnas. `.metrica-suelo` y
    `.metrica-servicios` declaran `grid-column: 1 / -1`; a `.metrica-viva` se le
    olvido, asi que el titular vivia en media columna de 148 px y su
    `margin: -8px` sacaba el fondo fuera de la tarjeta.
    """
    pagina.locator('#amenazas button[data-amenaza="fuego"]').click()
    _esperar_capa(pagina, "incendios")
    pagina.wait_for_timeout(700)

    medidas = pagina.evaluate(
        """() => {
        const b = document.querySelector('.metrica-viva:not([hidden])');
        const g = document.querySelector('#en-vivo .metricas');
        if (!b || !g) return null;
        const rb = b.getBoundingClientRect(), rg = g.getBoundingClientRect();
        return { bx: rb.left, br: rb.right, bw: rb.width, gx: rg.left, gr: rg.right, gw: rg.width };
    }"""
    )

    assert medidas, "no hay cifra viva que medir"
    assert medidas["bx"] >= medidas["gx"] - 1, "la cifra se sale por la izquierda"
    assert medidas["br"] <= medidas["gr"] + 1, "la cifra se sale por la derecha"
    assert abs(medidas["bw"] - medidas["gw"]) <= 3, (
        f"la cifra ocupa {medidas['bw']:.0f} px de {medidas['gw']:.0f}: "
        "deberia ocupar la fila entera"
    )


def test_la_tarjeta_viva_dice_de_donde_es_la_cifra(pagina: Any) -> None:
    """ "586.000 personas en celdas con fuego activo" — ¿de donde?

    Se podia leer como un incendio, como un pais o como la region entera. Es la
    suma de toda America Latina, y sin decirlo la cifra no significa nada.
    """
    pagina.locator('#amenazas button[data-amenaza="fuego"]').click()
    _esperar_capa(pagina, "incendios")
    pagina.wait_for_timeout(600)

    texto = pagina.locator('.metrica-viva[data-capa="incendios"]').inner_text().lower()
    assert "américa latina" in texto, f"la cifra no declara su alcance: {texto!r}"


# --- "Ver en el mapa" tiene que llevar al sitio (31-ago-2026) ----------------


def _iso_de(pagina: Any, nombre: str) -> str:
    """El valor (ISO3) de la opción que empieza por ese nombre.

    Se elige por valor y no por etiqueta porque la etiqueta lleva la cuenta
    entre paréntesis —«Venezuela (3)»— y esa cuenta cambia con los datos.
    """
    iso: str = pagina.evaluate(
        """(nombre) => {
          const sel = document.getElementById('filtro-paises');
          const o = [...sel.options].find(x => x.text.startsWith(nombre));
          return o ? o.value : '';
        }""",
        nombre,
    )
    assert iso, f"no hay una opción para {nombre}"
    return iso


def _escala(pagina: Any) -> str:
    """Lo que dice la barra de escala. Es la lectura fiable de la cámara.

    En una pestaña oculta `requestAnimationFrame` va a ~1 fps y el lienzo puede
    parecer congelado; la barra de escala sí refleja el zoom.
    """
    texto: str = pagina.locator(".maplibregl-ctrl-scale").first.inner_text()
    return texto.strip()


def _km(texto: str) -> float:
    """La misma conversión, para una escala ya capturada."""
    numero_, unidad = texto.replace(" ", " ").split()
    return float(numero_.replace(",", ".")) * (1.0 if unidad == "km" else 0.001)


def _camara_quieta(pagina: Any, intentos: int = 40) -> float:
    """Espera a que el vuelo termine y devuelve la escala en km.

    Dos trampas, las dos aprendidas aquí:

    1. Los vuelos de MapLibre llevan duración. Medir a mitad da una lectura
       intermedia —1.000 km cuando la cámara va camino de 5— y un
       `wait_for_timeout` fijo hace fallar la prueba por la máquina y no por el
       fallo que busca.
    2. Con la pestaña de fondo, `requestAnimationFrame` cae a ~1 fps y el vuelo
       **se para**: dos lecturas seguidas salen iguales a mitad de camino y una
       espera ingenua las toma por el final. Por eso aquí se empuja con un
       `resize` entre lecturas —lo mismo que hace falta para validar a mano— y
       se exigen tres iguales, no dos.
    """
    estables = 0
    anterior = _escala_km(pagina)
    for _ in range(intentos):
        pagina.evaluate("() => window.dispatchEvent(new Event('resize'))")
        pagina.wait_for_timeout(350)
        ahora = _escala_km(pagina)
        estables = estables + 1 if ahora == anterior else 0
        anterior = ahora
        if estables >= 3:
            return ahora
    return anterior


def _escala_km(pagina: Any) -> float:
    """La escala como número, para poder comparar cuánto se alejó la cámara.

    Comparar las cadenas obliga a acertar el encuadre exacto, y no es lo que
    interesa: «volvió al panorama» es «se alejó un orden de magnitud», no «dice
    2000 km». La barra salta entre valores redondos, así que exigir uno concreto
    hace la prueba frágil por un motivo que no es el fallo que busca.
    """
    texto = _escala(pagina).replace(" ", " ")
    numero_, unidad = texto.split()
    return float(numero_.replace(",", ".")) * (1.0 if unidad == "km" else 0.001)


def test_ver_en_el_mapa_encuadra_los_sismos_vistos(pagina: Any) -> None:
    """El botón decía «Ver en el mapa» y no llevaba a ninguna parte.

    Encendía nueve estrellas huecas repartidas por un continente, sin mover la
    cámara y sin decir nada. En un portátil, donde el mapa ya se ve entero, el
    `scrollIntoView` tampoco hacía nada: para quien lo pulsa, el botón está roto.
    """
    _esperar_capa(pagina, "observados")
    boton = pagina.locator('.metrica-viva[data-capa="observados"]')
    boton.wait_for(state="visible", timeout=ESPERA_MS)
    antes = _escala(pagina)

    boton.click()
    pagina.wait_for_timeout(600)
    _camara_quieta(pagina)

    casilla = pagina.locator("#interruptor-observados input")
    assert casilla.is_checked(), "la capa que el botón promete encender sigue apagada"
    assert _escala(pagina) != antes, (
        f"la cámara no se movió: sigue en {antes}. «Ver en el mapa» tiene que llevar al sitio"
    )


def test_ver_en_el_mapa_no_es_un_boton_de_un_solo_uso(pagina: Any) -> None:
    """La segunda pulsación no hacía literalmente nada.

    `cambiarAmenaza` sale temprano si el modo ya es ese, y la casilla solo se
    marcaba `if (!casilla.checked)`. Encendida la capa, el botón quedaba mudo.
    """
    _esperar_capa(pagina, "observados")
    boton = pagina.locator('.metrica-viva[data-capa="observados"]')
    boton.wait_for(state="visible", timeout=ESPERA_MS)

    boton.click()
    pagina.wait_for_timeout(600)
    _camara_quieta(pagina)
    encuadrado = _escala(pagina)

    # Alejarse a mano, como haría cualquiera que se mueva por el mapa.
    pagina.locator(".maplibregl-ctrl-zoom-out").click()
    pagina.locator(".maplibregl-ctrl-zoom-out").click()
    _camara_quieta(pagina)
    assert _escala(pagina) != encuadrado, "el zoom manual no movió la cámara"

    boton.click()
    pagina.wait_for_timeout(600)
    _camara_quieta(pagina)

    assert _escala(pagina) == encuadrado, (
        "la segunda pulsación no devolvió el encuadre: el botón sigue siendo de un solo uso"
    )


def test_volver_a_los_focos_devuelve_tambien_la_camara(pagina: Any) -> None:
    """El botón dice «Volver a los focos», en plural, y dejaba uno solo delante.

    Cerraba el panel y quitaba el perímetro, pero la vista se quedaba clavada
    sobre el foco recién cerrado, a cinco kilómetros de escala: el panel decía
    una cosa y el mapa otra. «Volver al panorama» de un sismo sí devolvía la
    cámara desde el primer día.

    Se comprueba sobre `window.CENTINELA.camara`, no sobre la barra de escala, y
    por el mismo motivo que las capas se comprueban sobre `pintado`: en esta
    pestaña los vuelos de MapLibre se paran a medias, así que el píxel no
    distingue «no se pidió mover la cámara» de «se pidió y no avanzó».
    """
    pagina.locator('#amenazas button[data-amenaza="fuego"]').click()
    _esperar_capa(pagina, "focos")
    pagina.evaluate("() => window.CENTINELA.abrirFoco(0)")
    pagina.wait_for_selector("#detalle-fuego:not([hidden])", timeout=ESPERA_MS)
    pagina.evaluate("() => { window.CENTINELA.camara.motivo = null; }")

    pagina.locator("#volver-fuego").click()
    pagina.wait_for_timeout(900)

    assert pagina.locator("#detalle-fuego").is_hidden()
    assert (
        pagina.evaluate("() => window.CENTINELA.camara.motivo") == "panorama:volver-a-los-focos"
    ), "cerrar el foco no pidió devolver la vista"


def test_ver_en_el_mapa_del_fuego_devuelve_el_panorama(pagina: Any) -> None:
    """La cifra habla de toda América Latina, así que el encuadre es ese."""
    pagina.locator('#amenazas button[data-amenaza="fuego"]').click()
    _esperar_capa(pagina, "focos")
    boton = pagina.locator('.metrica-viva[data-capa="incendios"]')
    boton.wait_for(state="visible", timeout=ESPERA_MS)
    pagina.evaluate("() => { window.CENTINELA.camara.motivo = null; }")

    boton.click()
    pagina.wait_for_timeout(900)

    assert pagina.evaluate("() => window.CENTINELA.camara.motivo") == "panorama:fuego", (
        "el botón no pidió devolver el panorama"
    )


# --- Filtros de tiempo y país (31-ago-2026) ---------------------------------


def test_la_ventana_temporal_recorta_la_lista_de_reportes(pagina: Any) -> None:
    """El catálogo cubre catorce años y la lista los daba todos de golpe.

    «¿Qué ha pasado últimamente?» obligaba a leerla entera o a fiarse del orden.
    """
    pagina.wait_for_function(
        "() => document.querySelectorAll('#lista-eventos li').length > 0", timeout=ESPERA_MS
    )

    def visibles() -> int:
        n: int = pagina.locator("#lista-eventos li:not([hidden])").count()
        return n

    todos = visibles()
    assert todos > 0

    pagina.select_option("#ventana-lista", "ano")
    pagina.wait_for_timeout(700)
    ultimo_ano = visibles()

    assert ultimo_ano < todos, f"la ventana de 12 meses no recortó nada: {ultimo_ano} de {todos}"

    pagina.select_option("#ventana-lista", "todo")
    pagina.wait_for_timeout(700)
    assert visibles() == todos, "volver a «Todo» no devolvió la lista entera"


def test_cada_amenaza_tiene_su_indice_y_solo_uno_a_la_vez(pagina: Any) -> None:
    """El fuego tenía mapa y panel de detalle pero ningún índice.

    Para saber cuáles son los focos más recientes había que buscar hexágonos a
    ojo entre cuatro mil. Y leer «Reportes publicados» con el mapa lleno de fuego
    es la misma mezcla que el selector de amenaza existe para evitar.
    """
    _esperar_capa(pagina, "focos")
    assert pagina.locator("#eventos").is_visible(), "en sismos falta el índice de reportes"
    assert pagina.locator("#focos").is_hidden(), "la lista de focos está en modo sismos"

    pagina.locator('#amenazas button[data-amenaza="fuego"]').click()
    pagina.wait_for_timeout(900)

    assert pagina.locator("#focos").is_visible(), "en fuego falta el índice de focos"
    assert pagina.locator("#eventos").is_hidden(), "la lista de reportes está en modo fuego"
    assert pagina.locator("#lista-focos li").count() > 0


def test_los_focos_se_listan_por_lo_mas_reciente(pagina: Any) -> None:
    """La pregunta que trae a alguien a un mapa de fuego es qué arde AHORA.

    Por eso «Reciente» es el orden por defecto y no la energía, que es lo que
    ordena la capa del mapa.
    """
    pagina.locator('#amenazas button[data-amenaza="fuego"]').click()
    _esperar_capa(pagina, "focos")
    pagina.wait_for_selector("#lista-focos li", timeout=ESPERA_MS)

    assert pagina.locator("#orden-focos").input_value() == "reciente", (
        "no ordena por reciente al abrir"
    )

    sellos = pagina.eval_on_selector_all(
        "#lista-focos li", "els => els.map(e => e.dataset.utc).filter(Boolean)"
    )
    assert sellos == sorted(sellos, reverse=True), "las filas no van de lo más reciente a lo menos"


def test_la_ventana_del_fuego_es_de_horas_y_lo_dice_cuando_vacia(pagina: Any) -> None:
    """El fuego es una foto de 24 h, no un archivo de catorce años.

    Y cuando la ventana no deja nada, el aviso dice **cuándo se revisó**: con un
    fichero de hace once horas «últimas 6 h» sale vacío siempre, y sin ese
    apunte se lee como «no hay fuego» cuando lo cierto es «no lo hemos vuelto a
    mirar».
    """
    pagina.locator('#amenazas button[data-amenaza="fuego"]').click()
    _esperar_capa(pagina, "focos")
    pagina.wait_for_selector("#lista-focos li", timeout=ESPERA_MS)

    etiquetas = pagina.eval_on_selector_all(
        "#ventana-focos option", "els => els.map(e => e.textContent.trim())"
    )
    assert etiquetas == ["24 h", "12 h", "6 h"], f"la ventana del fuego no es de horas: {etiquetas}"

    pagina.select_option("#ventana-focos", "h6")
    pagina.wait_for_timeout(700)

    vacio = pagina.locator("#sin-focos")
    if vacio.is_visible():
        texto = vacio.inner_text().lower()
        assert "se revisó" in texto or "se reviso" in texto, (
            f"el aviso no dice cuándo se miró por última vez: {texto!r}"
        )


def test_el_filtro_de_pais_recorta_el_mapa_y_no_solo_la_lista(pagina: Any) -> None:
    """Los filtros vivían debajo, dentro de la lista, y solo recortaban filas.

    Elegir «Colombia» dejaba la lista con los suyos y el mapa con veintiún
    epicentros repartidos por el continente: el filtro diciendo una cosa y el
    mapa otra, que es la misma contradicción que el selector de amenaza existe
    para evitar.
    """
    _esperar_capa(pagina, "epicentros")
    pagina.wait_for_selector("#campo-pais:not([hidden])", timeout=ESPERA_MS)

    def en_la_lista() -> int:
        n: int = pagina.locator("#lista-eventos li:not([hidden])").count()
        return n

    todos = en_la_lista()
    pagina.select_option("#filtro-paises", "COL")
    pagina.wait_for_timeout(1500)

    # La expresión que MapLibre tiene puesta sobre la capa: es la prueba de que
    # el mapa está filtrado y no solo la lista. Contar hexágonos en una captura
    # no distingue «filtrado» de «la animación no avanzó».
    expresion = pagina.evaluate("() => JSON.stringify(window.CENTINELA.filtroDeCapa('epicentros'))")
    assert expresion and "COL" in expresion, (
        f"la capa de epicentros no lleva el filtro del país: {expresion}"
    )
    assert en_la_lista() < todos, "la lista tampoco se recortó"


def test_los_filtros_son_desplegables_y_estan_arriba(pagina: Any) -> None:
    """Diecinueve países en una fila de pastillas son dos líneas de ruido que
    empujan el mapa fuera de la pantalla.

    Un desplegable ocupa lo mismo con uno que con cincuenta, y en un teléfono
    abre el selector nativo. Y arriba, no debajo: un filtro que gobierna el mapa
    tiene que verse junto al mapa.
    """
    barra = pagina.locator("#barra-filtros")
    assert barra.is_visible()

    orden = pagina.evaluate(
        """() => {
          const b = document.getElementById('barra-filtros').getBoundingClientRect();
          const m = document.getElementById('mapa').getBoundingClientRect();
          return b.top < m.top;
        }"""
    )
    assert orden, "la barra de filtros está por debajo del mapa"

    for campo in ("#filtro-paises", "#ventana-lista", "#orden-lista"):
        assert pagina.locator(campo).evaluate("e => e.tagName") == "SELECT", (
            f"{campo} no es un desplegable"
        )


def test_solo_se_ven_los_filtros_de_la_amenaza_al_mando(pagina: Any) -> None:
    """Dos «País» uno al lado del otro serían dos amenazas hablando a la vez.

    Pasó: el campo de la otra amenaza dependía de que su pintor corriera, y al
    cambiar a fuego se quedaban Colombia y Brasil compitiendo en la misma barra.
    """
    _esperar_capa(pagina, "epicentros")
    visibles = "() => [...document.querySelectorAll('#barra-filtros > *')]"
    visibles += ".filter(e => e.offsetParent !== null).map(e => e.id).filter(Boolean)"

    en_sismos = pagina.evaluate(visibles)
    assert "campo-ventana" in en_sismos
    assert "campo-ventana-fuego" not in en_sismos
    assert "campo-pais-fuego" not in en_sismos

    pagina.locator('#amenazas button[data-amenaza="fuego"]').click()
    _esperar_capa(pagina, "focos")
    pagina.wait_for_timeout(1200)

    en_fuego = pagina.evaluate(visibles)
    assert "campo-ventana-fuego" in en_fuego
    assert "campo-ventana" not in en_fuego, "el período de sismos sigue en modo fuego"
    assert "campo-pais" not in en_fuego, "dos «País» a la vez"


def test_quitar_filtros_aparece_solo_cuando_hay_algo_que_quitar(pagina: Any) -> None:
    """Un botón de limpiar siempre visible no informa.

    Visible solo cuando un filtro está actuando es además la señal de que lo
    está — que es justo lo que se pierde de vista cuando los controles viven
    lejos del mapa.
    """
    _esperar_capa(pagina, "epicentros")
    boton = pagina.locator("#limpiar-filtros")
    assert boton.is_hidden(), "sin filtros puestos ya ofrece quitarlos"

    pagina.select_option("#ventana-lista", "ano")
    pagina.wait_for_timeout(900)
    assert boton.is_visible(), "con un filtro puesto no ofrece quitarlo"

    boton.click()
    pagina.wait_for_timeout(1200)

    assert boton.is_hidden()
    assert pagina.locator("#ventana-lista").input_value() == "todo", (
        "el control se quedó enseñando el filtro que acaba de quitarse"
    )


def test_los_sismos_menores_obedecen_al_filtro_de_pais(pagina: Any) -> None:
    """Con «Colombia» puesto el mapa dejaba un epicentro y seguían los diez
    menores repartidos por el continente.

    El primer arreglo fue apagar la capa entera al elegir país, con la excusa de
    que «de estos no se sabe de qué país son». Era falso: el país estaba en el
    dato, al final del topónimo que publica USGS. Apagar una capa porque no
    supimos leer lo que ya teníamos es peor que no filtrarla.
    """
    _esperar_capa(pagina, "observados")
    pagina.wait_for_selector("#campo-pais:not([hidden])", timeout=ESPERA_MS)

    casilla = pagina.locator("#interruptor-observados input")
    casilla.check()
    pagina.wait_for_timeout(1200)

    sin_filtro = pagina.evaluate("() => window.CENTINELA.filtroDeCapa('observados')")
    assert sin_filtro in (None, ["all"]), f"sin país elegido no debería filtrar: {sin_filtro}"

    pagina.select_option("#filtro-paises", _iso_de(pagina, "Chile"))
    pagina.wait_for_timeout(1500)

    con_filtro = pagina.evaluate(
        "() => JSON.stringify(window.CENTINELA.filtroDeCapa('observados'))"
    )
    assert con_filtro and "iso3" in con_filtro, (
        f"la capa de menores no filtra por país: {con_filtro}"
    )
    assert "__ninguno__" not in con_filtro, (
        "la capa se apaga entera en vez de filtrarse: el país está en el dato"
    )


def test_el_filtro_de_pais_del_fuego_llega_a_las_tres_capas(pagina: Any) -> None:
    """Lo mismo que se le exige a los sismos, y por el mismo motivo.

    El fuego se dibuja en tres capas —relleno, punto y borde— y filtrar solo una
    dejaría el contorno de celdas que ya no están, o puntos sin su hexágono.
    """
    # La capa del mapa, no la anotacion de la lista. Ver el comentario
    # largo en `test_el_filtro_del_fuego_por_pais_se_construye_bien`.
    _esperar_capa(pagina, "incendios")
    pagina.locator('#amenazas button[data-amenaza="fuego"]').click()
    # Esperar a la condición y no al reloj: las capas nacen cuando llegan sus
    # datos, que es después de la primera pasada de filtros.
    pagina.wait_for_function(
        "() => window.CENTINELA.filtroDeCapa('incendios-borde') != null",
        timeout=ESPERA_MS,
    )

    expresiones = pagina.evaluate(
        """() => ['incendios', 'incendios-punto', 'incendios-borde']
                   .map(c => JSON.stringify(window.CENTINELA.filtroDeCapa(c)))"""
    )
    assert len(set(expresiones)) == 1, (
        f"las tres capas del fuego no llevan el mismo filtro: {expresiones}"
    )
    assert "ultima_utc" in (expresiones[0] or ""), (
        f"el filtro del fuego no acota por hora de detección: {expresiones[0]}"
    )


def test_la_ventana_del_fuego_mueve_el_filtro_del_mapa(pagina: Any) -> None:
    """Que la lista y el mapa cuenten desde el mismo sitio.

    Si contaran desde referencias distintas, uno enseñaría focos que el otro dice
    que no existen — y la ventana se mide desde la detección más reciente del
    fichero, no desde el reloj.
    """
    # La capa del mapa, no la anotacion de la lista. Ver el comentario
    # largo en `test_el_filtro_del_fuego_por_pais_se_construye_bien`.
    _esperar_capa(pagina, "incendios")
    pagina.locator('#amenazas button[data-amenaza="fuego"]').click()
    pagina.wait_for_timeout(1000)

    def corte() -> str:
        crudo: str = pagina.evaluate(
            "() => JSON.stringify(window.CENTINELA.filtroDeCapa('incendios'))"
        )
        return crudo

    de_24 = corte()
    pagina.select_option("#ventana-focos", "h6")
    pagina.wait_for_timeout(1500)
    de_6 = corte()

    assert de_24 != de_6, "cambiar la ventana no movió el filtro del mapa"

    # Y la lista no se queda vacía: la ventana se cuenta desde el dato, no desde
    # el reloj. Con un fichero de once horas, «6 h» desde ahora sería siempre
    # cero — que es exactamente el fallo que esto arregla.
    assert pagina.locator("#lista-focos li").count() > 0, (
        "«6 h» dejó la lista vacía: la ventana volvió a contarse desde el reloj"
    )


def test_el_filtro_del_fuego_por_pais_se_construye_bien(pagina: Any) -> None:
    """El desplegable de país sólo aparece cuando el dato trae `iso3`.

    Hasta que P5 corra con la columna nueva no hay países que ofrecer, y un
    control que no filtra nada es ruido con aspecto de control. Lo que sí se
    puede comprobar hoy es que, en cuanto los haya, la expresión sale bien.
    """
    # SE ESPERA "incendios", NO "focos", Y LA DIFERENCIA NO ES COSMETICA.
    #
    # `pintado.focos` lo anota la LISTA, que no necesita mapa; las capas del
    # mapa las crea `dibujarIncendios` cuando el estilo esta listo, mas tarde.
    # Esperando "focos" esta prueba afirmaba sobre `getFilter('incendios')`
    # antes de que la capa existiera: `filtroDeCapa` devolvia `null` y el
    # assert de mas abajo comparaba contra la nada.
    #
    # Pasaba igualmente porque `pagina` es de ambito modulo y arrastraba las
    # capas de una prueba anterior. Un verde prestado, que es la peor clase:
    # esta prueba existe para vigilar que el filtro de pais toca el MAPA —el
    # fallo que se reporto— y durante un tiempo no vigilo nada.
    _esperar_capa(pagina, "incendios")
    pagina.locator('#amenazas button[data-amenaza="fuego"]').click()
    pagina.wait_for_timeout(1000)

    expresion = pagina.evaluate(
        """() => {
          const antes = window.CENTINELA.filtroDeCapa('incendios');
          return JSON.stringify(antes);
        }"""
    )
    campo = pagina.locator("#campo-pais-fuego")
    hay_paises = pagina.evaluate(
        "() => document.getElementById('filtro-paises-fuego').options.length > 1"
    )

    if not hay_paises:
        assert campo.is_hidden(), "el desplegable de país aparece sin países que ofrecer"
        assert "iso3" not in (expresion or ""), "filtra por un país que el dato no trae"
        return

    valor = pagina.evaluate("() => document.getElementById('filtro-paises-fuego').options[1].value")
    pagina.select_option("#filtro-paises-fuego", valor)
    pagina.wait_for_timeout(1500)

    despues = pagina.evaluate("() => JSON.stringify(window.CENTINELA.filtroDeCapa('incendios'))")
    assert valor in despues, f"la capa de fuego no filtra por {valor}: {despues}"


# --- La marca de quien lo hace ----------------------------------------------


@pytest.mark.visor
def test_el_sello_de_geoai_latam_carga_de_verdad(pagina: Any) -> None:
    """Una ruta rota aqui no se ve: el `alt` esta vacio a proposito.

    El globo es decorativo —el nombre "GeoAI LATAM" va al lado en texto—, asi
    que lleva `alt=""` para que un lector de pantalla no lo lea dos veces. El
    precio de esa decision es que si el PNG desaparece o cambia de sitio no
    aparece ningun icono roto ni ningun texto: queda un hueco de veinte pixeles
    y la cabecera se ve perfectamente normal. Es el mismo fallo mudo que el cero
    silencioso de los pipelines, en version tipografica.

    Durante toda la vida del visor aqui hubo un emoji, que cada sistema dibuja a
    su manera —azul en Windows, verde plano en Android, ausente en algun Linux—.
    Se comprueba tambien que no haya vuelto.
    """
    globos = pagina.locator("img.globo")
    assert globos.count() >= 1, "no queda ningun sello de GeoAI LATAM en la pagina"

    cargados = pagina.evaluate(
        """() => [...document.querySelectorAll('img.globo')].map((g) => ({
             ok: g.complete && g.naturalWidth > 0,
             src: g.getAttribute('src'),
             ancho: Math.round(g.getBoundingClientRect().width),
           }))"""
    )
    for globo in cargados:
        assert globo["ok"], f"el sello no carga: {globo['src']}"
        assert globo["ancho"] >= 12, f"el sello se pinta a {globo['ancho']}px, invisible"

    assert "🌎" not in pagina.content(), "volvio el emoji en vez del sello de la marca"


# --- El viento del panel de un foco -----------------------------------------


@pytest.mark.visor
def test_la_flecha_del_viento_apunta_a_donde_empuja_y_no_de_donde_viene(pagina: Any) -> None:
    """La comprobacion mas importante de la capa de viento.

    `dir_grados` es la convencion meteorologica: DE DONDE sopla. Un viento de 90
    grados —del este— empuja el fuego HACIA EL OESTE. La flecha tiene que girar
    `dir + 180`.

    Equivocarse aqui no rompe nada, no saca ningun valor de rango, no aparece en
    ningun log y pone todas las flechas exactamente al reves. En un mapa de
    incendios eso significa alejarse en la direccion del fuego. Es el unico
    sitio del visor donde un signo cambiado tiene esa consecuencia, y por eso se
    comprueba contra el JSON publicado en vez de contra una constante.
    """
    pagina.locator('#amenazas button[data-amenaza="fuego"]').click()
    _esperar_capa(pagina, "focos")
    pagina.wait_for_timeout(1200)

    rejilla = pagina.evaluate(
        """() => fetch('incendios.json').then((r) => r.json()).then((d) => d.viento || null)"""
    )
    if not rejilla:
        pytest.skip("el incendios.json publicado aun no trae viento (hace falta P5 con GFS)")

    assert pagina.evaluate("() => window.CENTINELA.abrirFoco(0)")
    pagina.wait_for_timeout(600)

    ambiente = pagina.locator("#fuego-ambiente")
    html = ambiente.inner_html()
    if not html.strip():
        pytest.skip("el primer foco cae lejos de todo punto de la reticula")

    giro = pagina.evaluate(
        r"""() => {
             const r = document.querySelector('#fuego-ambiente .rosa');
             if (!r) return null;
             const m = /rotate\(([-0-9.]+)deg\)/.exec(r.style.transform || '');
             return m ? Math.round(parseFloat(m[1])) : null;
           }"""
    )
    assert giro is not None, "la flecha no lleva giro: apuntaria siempre al norte"

    # El punto que el visor debio elegir: el mas cercano al centro del foco.
    esperado = pagina.evaluate(
        """() => {
             const p = window.CENTINELA.vientoDelFocoAbierto();
             return p ? p.dir_grados : null;
           }"""
    )
    if esperado is not None:
        assert giro == (esperado + 180) % 360, (
            f"la flecha gira {giro} para un viento de {esperado}: "
            "apunta a de donde viene, no a donde empuja"
        )

    # El giro tiene que ser uno de los rumbos publicados, invertido. Sin el
    # gancho anterior esto sigue atrapando una flecha sin invertir.
    rumbos = {(p["dir_grados"] + 180) % 360 for p in rejilla["puntos"]}
    assert giro in rumbos, f"giro {giro} que no corresponde a ningun punto invertido"

    # Y el rotulo tiene que decir con letras lo mismo que la flecha: una flecha
    # girada se lee mal, y aqui leerla al reves es el fallo que importa.
    assert "empuja hacia el" in html, "la flecha va sola, sin rumbo escrito"
    assert "27" in html, "falta el aviso de que son 27 km de reticula, no la celda"


@pytest.mark.visor
def test_sin_viento_publicado_el_bloque_queda_vacio_y_no_en_cero(pagina: Any) -> None:
    """Que no se pudiera leer GFS no es "no hace viento".

    Pintar 0 km/h cuando falta el dato seria el cero silencioso otra vez, esta
    vez en la cara del usuario: una calma inventada junto a un incendio.
    """
    pagina.locator('#amenazas button[data-amenaza="fuego"]').click()
    _esperar_capa(pagina, "focos")
    pagina.wait_for_timeout(800)

    vacio = pagina.evaluate(
        r"""() => {
             const antes = document.getElementById('fuego-ambiente').innerHTML;
             return { tieneCero: /">0<\/span>/.test(antes) && !/[1-9]/.test(antes) };
           }"""
    )
    assert not vacio["tieneCero"], "se pinto un cero donde falta el dato"


# --- El tablero se cruza con los filtros ------------------------------------


@pytest.mark.visor
def test_sin_filtros_el_tablero_da_lo_mismo_que_el_pipeline(pagina: Any) -> None:
    """LA PRUEBA QUE SOSTIENE TODO LO DEMAS.

    Las cifras de la tarjeta se calculaban antes copiando el bloque `totales`
    del JSON. Ahora se suman en el navegador desde las celdas que pasan los
    filtros, que es lo que permite cruzarlas. El precio es que hay **dos
    implementaciones de la misma suma** —una en Python y otra en JavaScript— y
    dos implementaciones divergen en cuanto nadie las compara.

    Sin filtros tienen que dar exactamente lo mismo. Si algun dia no coinciden,
    una de las dos esta mal y da igual cual.

    **Solo se puede comparar si el fichero trae todas las celdas.** Con un
    `incendios.json` recortado en origen —los publicados antes del 31-ago-2026
    traian 4.000 de 13.031— la suma del navegador daria 3.575 donde el pipeline
    dice 13.031, y no porque ninguna este mal: es que no miran lo mismo. Ese
    caso lo cubre la prueba siguiente.
    """
    _esperar_capa(pagina, "incendios")
    pagina.locator('#amenazas button[data-amenaza="fuego"]').click()
    pagina.wait_for_timeout(1200)

    if not pagina.evaluate("() => window.CENTINELA.ficheroCompleto()"):
        pytest.skip("el incendios.json servido viene recortado; hace falta P5 con el tope nuevo")

    comparacion = pagina.evaluate(
        """async () => {
             const pub = (await (await fetch('incendios.json')).json()).totales;
             const mio = window.CENTINELA.sumaDelVisor();
             const campos = [
               'celdas', 'detecciones', 'detecciones_baja', 'celdas_con_poblacion',
               'pop_en_celdas_con_fuego', 'salud_en_celdas_con_fuego',
               'edu_en_celdas_con_fuego', 'bld_en_celdas_con_fuego',
             ];
             return campos.map((k) => ({ campo: k, pipeline: pub[k], visor: mio[k] }));
           }"""
    )
    for fila in comparacion:
        # La poblacion sale de redondear una suma de flotantes, y ahi las dos
        # lenguas no coinciden por convencion: `round` de Python redondea al par
        # y `Math.round` de JavaScript hacia arriba. Sobre 435.782 personas la
        # diferencia medida es de UNA, y forzar un redondeo identico entre
        # lenguajes no arregla nada que importe. Los enteros si tienen que
        # cuadrar exactos, porque ahi no hay convencion que valga.
        margen = 1 if fila["campo"] == "pop_en_celdas_con_fuego" else 0
        assert abs(fila["pipeline"] - fila["visor"]) <= margen, (
            f"{fila['campo']}: el pipeline dice {fila['pipeline']} y el visor {fila['visor']}"
        )


@pytest.mark.visor
def test_con_un_fichero_recortado_no_se_encogen_las_cifras(pagina: Any) -> None:
    """El regreso que este cambio estuvo a punto de introducir.

    Al pasar las cifras a calcularse en el navegador, un `incendios.json`
    recortado en origen —4.000 celdas de 13.031— las habria hecho caer a la
    suma de la muestra: 566.535 personas pasaban a ser las de 3.575 celdas, sin
    que nada fallara ni nadie se enterara. Lo cazo esta prueba antes de subirlo.

    La regla: **sin filtros mandan los totales del pipeline**, que son exactos
    aunque el fichero llegue recortado. Solo al filtrar se suma en el navegador,
    y entonces el rotulo dice sobre cuantas celdas se sumo.
    """
    _esperar_capa(pagina, "incendios")
    pagina.locator('#amenazas button[data-amenaza="fuego"]').click()
    pagina.wait_for_timeout(1200)

    estado = pagina.evaluate(
        """async () => {
             const pub = (await (await fetch('incendios.json')).json()).totales;
             return {
               completo: window.CENTINELA.ficheroCompleto(),
               ensenado: window.CENTINELA.totalesDelTablero(),
               publicado: pub,
             };
           }"""
    )
    # Con o sin recorte, sin filtros la tarjeta ensena lo que publica el
    # pipeline. Es la unica cifra que siempre es cierta.
    assert estado["ensenado"]["celdas"] == estado["publicado"]["celdas"]
    assert (
        estado["ensenado"]["pop_en_celdas_con_fuego"]
        == estado["publicado"]["pop_en_celdas_con_fuego"]
    )


@pytest.mark.visor
def test_al_filtrar_por_pais_las_cifras_del_tablero_bajan(pagina: Any) -> None:
    """El fallo que se reporto: "567.000 personas" no se movia al filtrar.

    Elegir Brasil recortaba la lista y el mapa, y la tarjeta seguia diciendo la
    suma de America Latina entera. El numero y el mapa contaban cosas distintas
    a la vez.
    """
    _esperar_capa(pagina, "incendios")
    pagina.locator('#amenazas button[data-amenaza="fuego"]').click()
    pagina.wait_for_timeout(1200)

    opciones = pagina.evaluate(
        "() => [...document.getElementById('filtro-paises-fuego').options].map((o) => o.value)"
    )
    if len(opciones) < 2:
        pytest.skip("no hay paises que ofrecer en el filtro de fuego")

    antes = pagina.evaluate("() => window.CENTINELA.totalesDelTablero()")
    pagina.select_option("#filtro-paises-fuego", opciones[1])
    pagina.wait_for_timeout(1200)
    despues = pagina.evaluate("() => window.CENTINELA.totalesDelTablero()")

    assert despues["celdas"] < antes["celdas"], "el filtro de pais no recorto las celdas"
    assert despues["pop_en_celdas_con_fuego"] <= antes["pop_en_celdas_con_fuego"]

    # Y el rotulo tiene que dejar de decir "toda America Latina", que con un
    # pais elegido pasa de aclaracion a mentira.
    apunte = pagina.locator("#en-vivo .metrica-viva .apunte").first.inner_text()
    assert "toda América Latina" not in apunte, f"el rotulo sigue diciendo: {apunte}"


@pytest.mark.visor
def test_la_ventana_temporal_tambien_mueve_las_cifras(pagina: Any) -> None:
    """Mismo fallo por el otro filtro: 24 h -> 6 h dejaba las cifras quietas."""
    _esperar_capa(pagina, "incendios")
    pagina.locator('#amenazas button[data-amenaza="fuego"]').click()
    pagina.wait_for_timeout(1200)

    antes = pagina.evaluate("() => window.CENTINELA.totalesDelTablero().celdas")
    pagina.select_option("#ventana-focos", "h6")
    pagina.wait_for_timeout(1200)
    despues = pagina.evaluate("() => window.CENTINELA.totalesDelTablero().celdas")

    assert despues < antes, "pasar de 24 h a 6 h no recorto ninguna celda"


@pytest.mark.visor
def test_la_extension_del_mapa_ya_filtra_el_fuego(pagina: Any) -> None:
    """Estaba escondida en modo fuego: mover el mapa no recortaba nada.

    Es el filtro mas natural de un tablero de mapa —lo que veo es de lo que me
    hablan— y era el unico que faltaba.
    """
    _esperar_capa(pagina, "incendios")
    pagina.locator('#amenazas button[data-amenaza="fuego"]').click()
    pagina.wait_for_timeout(1000)

    assert pagina.locator("#etiqueta-en-vista").is_visible(), (
        "la casilla de extension sigue oculta en modo fuego"
    )

    antes = pagina.evaluate("() => window.CENTINELA.totalesDelTablero().celdas")
    pagina.evaluate(
        """() => {
             const c = document.getElementById('solo-en-vista');
             c.checked = true;
             c.dispatchEvent(new Event('change', { bubbles: true }));
           }"""
    )
    pagina.wait_for_timeout(1500)
    despues = pagina.evaluate("() => window.CENTINELA.totalesDelTablero().celdas")

    assert despues <= antes
    apunte = pagina.locator("#en-vivo .metrica-viva .apunte").first.inner_text()
    assert "encuadre" in apunte, f"el rotulo no dice que se esta recortando: {apunte}"


@pytest.mark.visor
def test_ver_en_el_mapa_dice_algo_aunque_la_vista_no_cambie(pagina: Any) -> None:
    """El boton volvia siempre al encuadre general.

    Si ya estabas en fuego mirando el panorama —que es cuando lees esa tarjeta—
    no cambiaba ni un pixel y no anunciaba nada: se leia como roto, y a efectos
    practicos lo estaba.
    """
    _esperar_capa(pagina, "incendios")
    pagina.locator('#amenazas button[data-amenaza="fuego"]').click()
    pagina.wait_for_timeout(1200)

    boton = pagina.locator('#en-vivo .metrica-viva[data-capa="incendios"]')
    if not boton.count():
        pytest.skip("no hay tarjeta de incendios que pulsar")

    boton.first.click()
    pagina.wait_for_timeout(1500)

    anuncio = pagina.locator("#anuncio").inner_text()
    assert "celdas con fuego en el mapa" in anuncio, f"el boton no anuncio nada util: {anuncio!r}"
