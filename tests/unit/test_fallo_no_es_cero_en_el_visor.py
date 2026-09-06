"""En el visor, «no pude leer» y «no hay» son dos frases distintas.

El proyecto arreglo una direccion: que un cero medido no parezca un fallo. La
contraria seguia abierta, y es la peligrosa, porque **afirma algo sobre el
mundo**: cuando una libreria no cargaba o un fichero devolvia 404, el codigo
entraba en la misma rama que el cero legitimo y publicaba una frase afirmativa.

Los cuatro casos que se cierran, medidos:

* h3-js sirviendo 404 desde unpkg (paso el 28-ago-2026): «no hay nadie dentro
  que contar, y por eso las tablas van en cero» junto a un panel que decia 2,4
  millones de personas — y `pintado.celdas` declarando 0.
* `reports/index.json` con 404: «Aún no hay índice de reportes publicado. El
  primer reporte real lo genera», con veintisiete publicados.
* `incendios.json` caido: leyenda completa de potencia radiativa y nota de
  lectura sobre un mapa sin un solo foco.
* El estilo base sin llegar: el temporizador de 8 s retiraba el aviso de carga
  incondicionalmente y no quedaba ningun mensaje.

Se comprueba sobre el fuente porque el fallo es de RAMA, no de render: lo que
hay que fijar es que la decision se tome mirando la causa. Las pruebas de
navegador de `tests/visor/` ejercitan el resultado.
"""

from __future__ import annotations

from pathlib import Path

import pytest

RAIZ = Path(__file__).parent.parent.parent
APP = (RAIZ / "site" / "assets" / "app.js").read_text(encoding="utf-8")

#: `app.js` sin sus comentarios. Es la cuarta vez que un guardia de texto de
#: este repositorio confunde la explicacion con el codigo: antes fue
#: `src.read(1)` citado en un docstring, `gh workflow run site.yml` citado en el
#: cuerpo de un issue, y la palabra WHERE de un comentario del SQL. Una nota que
#: explica **por que se quito** una frase no puede hacer fallar la prueba de que
#: se quito.
CODIGO = chr(10).join(linea for linea in APP.splitlines() if not linea.lstrip().startswith("//"))


def _cuerpo(nombre: str) -> str:
    """El texto de una funcion de `app.js`, hasta la siguiente."""
    inicio = APP.index(f"function {nombre}(")
    resto = APP.index("\nfunction ", inicio + 1)
    return APP[inicio:resto]


def test_existe_la_primitiva_que_distingue_las_dos_causas() -> None:
    assert "function anotarFallo(" in APP
    assert "function listaVacia(" in APP


def test_un_fallo_no_se_registra_como_cero() -> None:
    """`rasgos: null` es la marca. Un cero dice «se miro y no habia nada»."""
    cuerpo = _cuerpo("anotarFallo")
    assert "rasgos: null" in cuerpo
    assert "erroresAlPintar.push" in cuerpo, "un fallo tiene que quedar en la telemetria"


def test_la_malla_distingue_h3_ausente_de_malla_vacia() -> None:
    """Las dos salian por el mismo `null` de `celdasAGeoJson`."""
    cuerpo = _cuerpo("pintarCeldas") if "function pintarCeldas(" in APP else APP
    assert 'const sinH3 = typeof h3 === "undefined"' in APP
    assert 'anotarFallo("celdas"' in APP
    # Y el texto del cero legitimo sigue existiendo, para cuando lo sea.
    assert "no hay nadie dentro que contar" in APP
    assert cuerpo is not None


def test_el_indice_distingue_ilegible_de_vacio() -> None:
    cuerpo = _cuerpo("cargarEventos")
    assert "listaVacia(eventos)" in cuerpo, "el vacio legitimo se comprueba mirando la lista"
    assert "No se pudo leer el índice de reportes" in cuerpo
    assert 'anotarFallo("indice"' in cuerpo


def test_un_indice_ilegible_no_esconde_los_otros_productos() -> None:
    """Se salia por `return` antes de cargar observados, focos y cobertura."""
    cuerpo = _cuerpo("cargarEventos")
    ilegible = cuerpo[cuerpo.index("No se pudo leer el índice") :]
    for carga in ("cargarObservados()", "cargarIncendios()", "cargarCobertura("):
        assert carga in ilegible, f"con el indice ilegible ya no se carga {carga}"

    vacio = cuerpo[cuerpo.index("listaVacia(eventos)") : cuerpo.index("aviso.hidden = true")]
    for carga in ("cargarObservados()", "cargarIncendios()", "cargarCobertura("):
        assert carga in vacio, f"el dia uno ya no ensena {carga}"


def test_los_focos_distinguen_ilegible_de_sin_fuego() -> None:
    cuerpo = _cuerpo("cargarIncendios")
    assert 'anotarFallo("focos"' in cuerpo
    assert "El mapa está vacío porque" in cuerpo, "falta el texto del fallo tecnico"
    assert "Ninguna celda con fuego activo" in cuerpo, "falta el texto del cero legitimo"
    assert "console.info(" not in cuerpo, "un fichero caido no se cuenta en voz baja"


def test_el_estilo_base_que_no_llega_deja_un_mensaje() -> None:
    """El `setTimeout` retiraba el aviso pasara lo que pasara."""
    assert "setTimeout(listoOSinEstilo, 8000)" in APP
    assert "El mapa base no cargó" in APP
    assert 'anotarFallo("mapa-base"' in APP


@pytest.mark.parametrize(
    "frase",
    [
        "Aún no hay índice de reportes publicado",
    ],
)
def test_las_frases_que_afirmaban_de_mas_ya_no_estan(frase: str) -> None:
    assert frase not in CODIGO, f"sigue publicandose una afirmacion que no se midio: {frase!r}"
    # Y sigue explicada en un comentario, que es donde tiene que estar.
    assert frase in APP, "se borro tambien la nota que dice por que estaba mal"
