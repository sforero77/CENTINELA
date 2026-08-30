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
    pagina.get_by_label("Focos activos", exact=False).check()
    _esperar_capa(pagina, "incendios")
    marca = _ahora(pagina)
    pagina.select_option("select", "us6000tjl2")
    _esperar_capa(pagina, "celdas", desde=marca)
    pagina.wait_for_timeout(800)

    solapes = pagina.evaluate(SONDA_SOLAPES)

    assert solapes == [], f"en {etiqueta} ({ancho}x{alto}) hay texto encima de otro: {solapes}"


# --- Lo que un control promete tiene que ser lo que enciende -----------------


def test_el_interruptor_de_fuego_promete_lo_que_dibuja(pagina: Any) -> None:
    """La casilla decia 15.607 celdas y el mapa dibujaba 4.000.

    `p5_incendios` recorta a las 4.000 de mayor potencia radiativa para que el
    visor no descargue varios megabytes, calcula los totales sobre **todas** y
    publica `celdas_publicadas` justo para que el recorte se pueda decir. El
    visor no leia ese campo: rotulaba con el total, encendia el recorte, y lo
    mismo por el lector de pantalla.

    Es el modo de fallo que este proyecto persigue en todas partes —una cifra
    plausible que el dato de al lado no sostiene— y estaba en el propio visor.

    No se comprueba la redaccion sino la aritmetica: el numero que el control
    ensena tiene que ser uno que el mapa pueda respaldar.
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

    etiqueta = pagina.locator("#interruptor-incendios").inner_text()

    assert es(dibujadas) in etiqueta, (
        f"el interruptor no dice cuantas celdas dibuja ({es(dibujadas)}): {etiqueta!r}"
    )
    if publicadas < total:
        assert es(total) in etiqueta, (
            f"el interruptor esconde el total ({es(total)}) y solo ensena el recorte: {etiqueta!r}"
        )
        # El fallo original en su forma exacta: el total como unica cifra.
        assert not etiqueta.strip().startswith(f"Focos activos ({es(total)} celdas"), (
            f"el interruptor promete el total y enciende el recorte: {etiqueta!r}"
        )

        pagina.get_by_label("Focos activos", exact=False).check()
        leyenda = pagina.locator("#leyenda-fuego").inner_text()
        assert es(dibujadas) in leyenda and es(total) in leyenda, (
            f"la leyenda de fuego no dice que la capa esta recortada: {leyenda!r}"
        )


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

    pagina.locator('#orden-lista button[data-orden="mag"]').click()
    por_mag = pagina.evaluate(
        """() => [...document.querySelectorAll('#lista-eventos li')]
                   .filter(li => !li.hidden).map(li => Number(li.dataset.mag))"""
    )
    assert por_mag == sorted(por_mag, reverse=True), f"el orden por magnitud no baja: {por_mag}"

    pagina.locator('#orden-lista button[data-orden="pop"]').click()
    por_pop = pagina.evaluate(
        """() => [...document.querySelectorAll('#lista-eventos li')]
                   .filter(li => !li.hidden).map(li => Number(li.dataset.pop))"""
    )
    assert por_pop == sorted(por_pop, reverse=True), f"el orden por exposicion no baja: {por_pop}"

    assert _titulos_visibles(pagina) != [], "la lista se quedo vacia al reordenar"
    assert (
        pagina.locator('#orden-lista button[data-orden="pop"]').get_attribute("aria-pressed")
        == "true"
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
