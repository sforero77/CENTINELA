"""Texto que escribe otro no puede acabar siendo un comando.

`${{ inputs.x }}` dentro de un `run:` **no** es una variable: GitHub lo sustituye
antes de que bash vea el script, asi que el valor deja de ser un argumento y pasa
a ser codigo. `contraste.yml` interpolaba asi cuatro entradas de texto libre
—`fuente`, `etiqueta`, `crs` y `columna`—, de modo que cualquiera con permiso
para lanzarlo ejecutaba lo que quisiera en el runner. `usgs_id` ya iba por `env`
desde el principio; las otras cuatro se habian quedado atras.

Y la variante de la misma familia en `site.yml`: el segundo argumento de
`re.sub` es una **plantilla**, no un texto. El paso que reescribe la vista previa
social lo construia con el toponimo que publica USGS, asi que un `place` con una
barra invertida seguida de N reventaba con `re.error: bad escape`. `html.escape`
no escapa la barra invertida.

El tercer hueco es de donde viene el codigo que corre: ninguna accion del
repositorio esta fijada por SHA, y una etiqueta de git se puede reapuntar. Eso
no se puede cerrar sin resolver catorce digests contra la red —queda anotado— y
lo que si se puede es que el token no ande suelto donde no hace falta.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

RAIZ = Path(__file__).parent.parent.parent
WORKFLOWS = RAIZ / ".github" / "workflows"

#: Lo que un tercero escribe y este repositorio lee. `github.event.*` cubre
#: titulos y cuerpos de issue; `inputs.*`, los formularios de `workflow_dispatch`.
INTERPOLA_TEXTO_AJENO = re.compile(
    r"\$\{\{\s*(inputs\.[A-Za-z0-9_]+|github\.event\.[A-Za-z0-9_.]*"
    r"(?:title|body|name|label|message|email)[A-Za-z0-9_.]*)\s*\}\}"
)


def _workflows() -> list[Path]:
    return sorted(WORKFLOWS.glob("*.yml"))


def _pasos(datos: dict) -> list[dict]:
    pasos: list[dict] = []
    for job in (datos.get("jobs") or {}).values():
        for paso in job.get("steps") or []:
            if isinstance(paso, dict):
                pasos.append(paso)
    return pasos


@pytest.mark.parametrize("ruta", _workflows(), ids=lambda p: p.name)
def test_ninguna_entrada_de_texto_libre_se_interpola_en_un_run(ruta: Path) -> None:
    """Via `env:` el valor es dato; interpolado es codigo."""
    datos = yaml.safe_load(ruta.read_text(encoding="utf-8"))
    for paso in _pasos(datos):
        cuerpo = paso.get("run")
        if not isinstance(cuerpo, str):
            continue
        # Solo las lineas de comando: un comentario que cite la forma no
        # ejecuta nada, y es justo lo que este fichero explica arriba.
        codigo = "\n".join(x for x in cuerpo.splitlines() if not x.lstrip().startswith("#"))
        encontrados = INTERPOLA_TEXTO_AJENO.findall(codigo)
        assert not encontrados, (
            f"{ruta.name}, paso {paso.get('name')!r}: interpola {sorted(set(encontrados))} "
            f"dentro de un `run:`. GitHub lo sustituye antes de que bash vea el "
            f"script, asi que ese texto se ejecuta. Pasalo por `env:` y usalo "
            f'citado como "$VARIABLE".'
        )


def test_contraste_pasa_sus_cuatro_entradas_por_env() -> None:
    """El caso concreto, para que el guardia de arriba no pase en vacio."""
    datos = yaml.safe_load((WORKFLOWS / "contraste.yml").read_text(encoding="utf-8"))
    entorno = datos["jobs"]["contrastar"]["env"]
    for clave in ("FUENTE", "ETIQUETA", "CRS", "COLUMNA", "USGS_ID"):
        assert clave in entorno, f"{clave} no viaja por env"


def test_la_fuente_del_contraste_tiene_que_ser_https() -> None:
    """`curl` acepta `file://`, `scp://` y una docena mas de esquemas.

    La entrada la escribe una persona y el runner tiene el checkout delante.
    """
    texto = (WORKFLOWS / "contraste.yml").read_text(encoding="utf-8")
    assert "https://*) ;;" in texto


def _empuja(ruta: Path) -> bool:
    """¿Este workflow **ejecuta** un push, o solo lo menciona?

    SEPTIMA VEZ EN ESTA AUDITORIA QUE UN GUARDIA LEE PROSA.

    Y la primera en la que el falso positivo lo causo el propio arreglo: el
    comentario que explica `persist-credentials: false` dice «el trabajo de este
    workflow no incluye un `git push`», asi que la version anterior de esta
    funcion —un `in` sobre el fichero entero— daba `True` para los nueve que
    acababa de arreglar. La lista de parametros se quedaba vacia y pytest lo
    reportaba como un salto, no como un fallo: el guardia desaparecia sin
    ponerse rojo.
    """
    lineas = ruta.read_text(encoding="utf-8").splitlines()
    return any("git push" in x for x in lineas if not x.lstrip().startswith("#"))


@pytest.mark.parametrize("ruta", [p for p in _workflows() if not _empuja(p)], ids=lambda p: p.name)
def test_quien_no_empuja_no_se_queda_el_token(ruta: Path) -> None:
    """`actions/checkout` deja el GITHUB_TOKEN en `.git/config` por defecto.

    Cualquier paso posterior —o cualquier accion de tercero que corra despues—
    puede usarlo. Es la mitigacion barata del hueco que sigue abierto: ninguna
    accion esta fijada por SHA y una etiqueta de git se puede reapuntar.
    """
    datos = yaml.safe_load(ruta.read_text(encoding="utf-8"))
    checkouts = [p for p in _pasos(datos) if str(p.get("uses", "")).startswith("actions/checkout")]
    if not checkouts:
        pytest.skip("no hace checkout")
    for paso in checkouts:
        conf = paso.get("with") or {}
        assert conf.get("persist-credentials") is False, (
            f"{ruta.name} no empuja nada y conserva el token del checkout: "
            f"anade `with: persist-credentials: false`"
        )


def test_hay_workflows_que_no_empujan() -> None:
    """Si la lista se queda vacia, la pagina de arriba pasa en vacio.

    Paso: un `in` sobre el fichero entero contaba el comentario del arreglo como
    un push y dejaba los nueve fuera. pytest lo enseña como un salto.
    """
    assert [p for p in _workflows() if not _empuja(p)]


def test_los_bumps_de_acciones_llegan_como_pr() -> None:
    """No cierra el hueco de las etiquetas moviles, pero evita congelarlo."""
    datos = yaml.safe_load((RAIZ / ".github" / "dependabot.yml").read_text(encoding="utf-8"))
    ecosistemas = {u["package-ecosystem"] for u in datos["updates"]}
    assert "github-actions" in ecosistemas


def test_la_vista_previa_social_comprueba_que_sustituyo_algo() -> None:
    """El paso existia porque `og:image` «se rompia en silencio», y se rompia igual.

    `re.sub` devuelve la cadena sin cambios cuando el patron no casa, y el
    `print` de despues se ejecutaba igual: el log afirmaba haber actualizado la
    vista previa sin haber tocado un byte.
    """
    texto = (WORKFLOWS / "site.yml").read_text(encoding="utf-8")
    codigo = "\n".join(x for x in texto.splitlines() if not x.lstrip().startswith("#"))
    assert "re.subn(" in codigo, "sigue usando `re.sub`, que no dice si sustituyo"
    assert "raise SystemExit(" in codigo, "no convierte el cero en un fallo"
    # Y el reemplazo es una funcion, no una plantilla: el toponimo de USGS no se
    # interpreta.
    assert "lambda m: m.group(1)" in codigo


# --------------------------------------------------------------------------
# Y el otro origen del codigo que corre: el navegador de quien mira.
# --------------------------------------------------------------------------

PAGINAS = ("index.html", "status.html")


@pytest.mark.parametrize("pagina", PAGINAS)
def test_cada_pagina_declara_su_politica_de_contenido(pagina: str) -> None:
    """GitHub Pages no deja fijar cabeceras: la etiqueta es la unica defensa.

    Por aqui entran dos librerias de terceros sin verificar: h3-js convierte los
    indices H3 en la geometria de cada hexagono y maplibre decide donde cae cada
    poligono en la pantalla.
    """
    html = (RAIZ / "site" / pagina).read_text(encoding="utf-8")
    assert 'http-equiv="Content-Security-Policy"' in html, (
        f"site/{pagina} no declara CSP y carga codigo de un tercero"
    )
    politica = html.split('Content-Security-Policy" content="', 1)[1].split('"', 1)[0]
    assert "default-src 'self'" in politica
    assert "script-src 'self' https://unpkg.com" in politica
    # Nada de comodines: una CSP con `*` en script-src no acota nada.
    assert "*" not in politica.split("script-src", 1)[1].split(";", 1)[0]


@pytest.mark.parametrize("pagina", PAGINAS)
def test_la_politica_no_declara_lo_que_el_navegador_ignora(pagina: str) -> None:
    """`frame-ancestors` en un `<meta>` no se aplica, y el navegador lo dice.

    Dejarla escrita seria publicar una proteccion que no protege — la forma de
    fallo que esta auditoria persigue desde el primer dia.
    """
    html = (RAIZ / "site" / pagina).read_text(encoding="utf-8")
    politica = html.split('Content-Security-Policy" content="', 1)[1].split('"', 1)[0]
    assert "frame-ancestors" not in politica


def test_el_visor_no_declara_cero_focos_cuando_no_pudo_agruparlos() -> None:
    """`agruparFocos` devuelve `[]` sin h3, y eso se anotaba como cero.

    En el registro publico de este visor, `anotarPintado(capa, 0)` significa «se
    miro y no habia nada». El fichero habia llegado con sus celdas dentro, y la
    frase que se publica —«ningun foco activo»— afirma algo sobre el mundo.
    """
    app = (RAIZ / "site" / "assets" / "app.js").read_text(encoding="utf-8")
    codigo = "\n".join(x for x in app.splitlines() if not x.lstrip().startswith("//"))
    assert 'anotarFallo("focos", "h3-js no cargo' in codigo, (
        "el camino de focos sin h3-js sigue anotando un cero que no midio nadie"
    )
