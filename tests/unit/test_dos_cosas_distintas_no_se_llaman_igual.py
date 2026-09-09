"""Dos cosas distintas no pueden llamarse igual en la misma pantalla.

«Área de afectación» rotulaba dos superficies a la vez en el panel del evento:

* el bloque `#bloque-area`, que publica la superficie de la **malla contada** y
  cuyo subtítulo se ocupa de aclarar «no la del ShakeMap: llega hasta donde hay
  algo expuesto, y por eso no entra en el mar»;
* y el enlace de descargas que sirve `contornos.json`, que es exactamente la del
  ShakeMap — la superficie que el bloque de arriba dice que no es.

O sea que la que se descargaba no era la que se estaba leyendo, y el propio
subtítulo que existía para evitar la confusión la producía.

Este guardia compara los rótulos de las descargas con los títulos de los bloques
del panel. No prohíbe que una palabra se repita: prohíbe que un **título
completo** de bloque sea también el nombre de un fichero descargable, que es
cuando el lector no tiene forma de saber cuál de los dos está mirando.
"""

from __future__ import annotations

import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
APP = RAIZ / "site" / "assets" / "app.js"
INDEX = RAIZ / "site" / "index.html"


def _rotulos_de_descarga() -> list[str]:
    """Los nombres que `pintarDescargas` da a cada artefacto del evento."""
    codigo = APP.read_text(encoding="utf-8")
    inicio = codigo.index("function pintarDescargas(")
    cuerpo = codigo[inicio : codigo.index("\n}", inicio)]
    # Solo las entradas de la lista `[texto, url]`, y no cualquier cadena del
    # cuerpo: el comentario que explica este mismo arreglo cita el rótulo viejo.
    return [texto for texto, _ in re.findall(r'\["([^"]+)",\s*`\$\{base\}/([^`]+)`\]', cuerpo)]


def _titulos_de_bloque() -> list[str]:
    """Los `<h3 class="eyebrow">` de los bloques del panel del evento."""
    html = INDEX.read_text(encoding="utf-8")
    return [t.strip() for t in re.findall(r'<h3 class="eyebrow"[^>]*>([^<]+)</h3>', html)]


def test_hay_rotulos_y_titulos_que_comparar() -> None:
    """La red de seguridad: dos listas vacías no chocan nunca."""
    descargas = _rotulos_de_descarga()
    titulos = _titulos_de_bloque()
    assert len(descargas) >= 6, f"solo se leyeron {len(descargas)} descargas: {descargas}"
    assert len(titulos) >= 4, f"solo se leyeron {len(titulos)} títulos de bloque: {titulos}"


def test_ninguna_descarga_se_llama_como_un_bloque_del_panel() -> None:
    """El nombre de un fichero no puede ser el título de otra cosa que se lee al lado."""
    descargas = _rotulos_de_descarga()
    titulos = {t.casefold() for t in _titulos_de_bloque()}

    chocan = [d for d in descargas if d.casefold() in titulos]
    assert not chocan, (
        f"{chocan} nombra a la vez un bloque del panel y un fichero descargable. "
        f"Quien lo pulse se llevará algo distinto de lo que está leyendo, que es "
        f"lo que pasaba con «Área de afectación»: el bloque publica la superficie "
        f"de la malla contada y el fichero son los contornos del ShakeMap"
    )
