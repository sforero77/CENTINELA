"""Un comando que la documentacion enseña tiene que arrancar.

Cuatro documentos enseñaban formas que salen con `SystemExit 2`:

    centinela: error: unrecognized arguments: --iso3
    centinela impact: error: the following arguments are required:
        --detail-url, --exposure

`p_country.add_argument("iso3")` es **posicional**: la forma correcta es
`centinela country COL`, que es la que si usan `OPERACION.md`,
`PUESTA_EN_MARCHA.md`, `PARA_INSTITUCIONES.md` y `CONTRIBUTING.md`. La forma con
`--iso3` vivia en la linea «Comando:» de la cabecera del documento de P0 — o sea
en la afirmacion principal de la pagina.

Y `centinela impact <usgs_id>` a secas aparecia en la cabecera del documento de
P2, en el indice de pipelines y —lo que mas duele— en `PENDIENTES.md`, donde era
la instruccion operativa concreta para cerrar un pendiente. La forma completa y
correcta estaba escrita doscientas lineas mas arriba en ese mismo fichero.

Son veintiun subcomandos repartidos en cinco documentos: mantenerlos
sincronizados a mano no es tedioso, es que no ocurre. Aqui se pasan por el
parser de verdad.
"""

from __future__ import annotations

import re
import shlex
from pathlib import Path

import pytest

from pipelines.cli import build_parser

RAIZ = Path(__file__).parent.parent.parent


#: Documentos que enseñan comandos. No es una lista a mano: son los `.md` del
#: repositorio que nombran el CLI.
def _documentos() -> list[Path]:
    rutas = list(RAIZ.glob("*.md"))
    rutas += list((RAIZ / "docs").rglob("*.md"))
    return sorted(p for p in rutas if "centinela " in p.read_text(encoding="utf-8"))


#: `uv run centinela <sub> ...` o `centinela <sub> ...`, en una linea.
INVOCACION = re.compile(r"(?:uv run )?centinela ([a-z0-9-]+(?:[^\n`]*))")

#: Marcadores de que el comando **no** es una invocacion literal.
#:
#: `<iso3>` es un hueco que el lector rellena, y `$(...)` o `(Get-ChildItem ...)`
#: son sustituciones del shell: pasarlos por argparse probaria que `<usgs_id>` no
#: es un id valido, que no es lo que este guardia pregunta.
PLANTILLA = re.compile(r"[<>{}()]|\.\.\.|\$")


def _invocaciones(texto: str) -> list[str]:
    """Las lineas de comando, sin la prosa que las nombra.

    Se descartan las que llevan un hueco `<asi>`: son plantillas, y pasarlas por
    el parser probaria que `<usgs_id>` no es un id valido, que no es lo que este
    guardia pregunta. Lo que si se comprueba de ellas es que el **subcomando**
    exista, unas lineas mas abajo.
    """
    fuera: list[str] = []
    for linea in texto.splitlines():
        cuerpo = linea.strip().lstrip("$").strip()
        # Solo lineas que **son** el comando, no frases que lo mencionan: la
        # prosa de este repositorio cita comandos entre comillas invertidas
        # constantemente, y un guardia que las lea comprobaria la documentacion
        # contra si misma. Es la septima vez que aparece esta trampa aqui.
        if not (cuerpo.startswith(("centinela ", "uv run centinela "))):
            continue
        hallado = INVOCACION.match(cuerpo)
        if not hallado:
            continue
        invocacion = hallado.group(1)
        # Un comentario al final de la linea es documentacion, no argumento:
        # `centinela trigger --dry-run   # P1 sin escribir estado`.
        invocacion = invocacion.split("#", 1)[0]
        fuera.append(invocacion.strip().rstrip("`"))
    return fuera


DOCUMENTOS = _documentos()


def test_hay_documentos_que_ensenan_comandos() -> None:
    """Si la lista se queda vacia, la pagina de abajo pasa en vacio."""
    assert DOCUMENTOS
    assert any(_invocaciones(p.read_text(encoding="utf-8")) for p in DOCUMENTOS)


@pytest.mark.parametrize("ruta", DOCUMENTOS, ids=lambda p: str(p.relative_to(RAIZ)))
def test_todo_comando_documentado_lo_acepta_el_parser(ruta: Path) -> None:
    """Se pasa por `build_parser()`, que es el mismo que corre en produccion."""
    parser = build_parser()
    subparsers = next(
        a for a in parser._actions if isinstance(a.choices, dict) and "country" in a.choices
    )

    for invocacion in _invocaciones(ruta.read_text(encoding="utf-8")):
        argumentos = shlex.split(invocacion, posix=False)
        sub = argumentos[0]
        assert sub in subparsers.choices, (
            f"{ruta.relative_to(RAIZ)} enseña `centinela {sub}` y ese subcomando no existe"
        )
        if PLANTILLA.search(invocacion):
            # Plantilla: el subcomando existe y eso es lo comprobable.
            continue
        try:
            parser.parse_args(argumentos)
        except SystemExit as exc:
            raise AssertionError(
                f"{ruta.relative_to(RAIZ)} enseña `centinela {invocacion}` y el parser "
                f"sale con {exc.code}. Un comando que la documentacion enseña tiene "
                f"que arrancar: son veintiun subcomandos en cinco ficheros y a mano "
                f"esto se desincroniza solo."
            ) from exc


def test_la_forma_posicional_de_country_es_la_que_se_documenta() -> None:
    """`--iso3` no existe, y estaba en la cabecera del documento de P0.

    OCTAVA VEZ QUE UN GUARDIA IBA A LEER PROSA.

    La primera version buscaba la cadena en el fichero entero, y se puso roja en
    cuanto `docs/AUDITORIA-2026-09.md` **cito el hallazgo** que describe el
    fallo. Un guardia que confunde la mencion con el uso obliga a no poder
    escribir sobre lo que vigila.

    La pregunta correcta es si alguna **invocacion documentada** usa esa forma,
    que es justo lo que `_invocaciones` sabe distinguir.
    """
    for ruta in DOCUMENTOS:
        for invocacion in _invocaciones(ruta.read_text(encoding="utf-8")):
            assert not invocacion.startswith("country --iso3"), (
                f"{ruta.relative_to(RAIZ)}: `--iso3` no existe; la forma es `centinela country COL`"
            )
