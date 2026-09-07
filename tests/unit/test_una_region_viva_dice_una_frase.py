"""Una región `aria-live` anuncia una frase, no un panel entero.

La tarjeta «Ahora mismo» era `aria-live="polite"` y se reescribe entera —
`caja.innerHTML = ...` — cada vez que cambia un filtro y, con «solo lo que se
ve» puesto, en **cada `moveend` del mapa**. Como región viva, eso significa que
un lector de pantalla interrumpe y lee las cuatro métricas completas cada vez que
alguien arrastra el mapa: entre siete y diez frases por gesto.

Una región que interrumpe siempre acaba silenciada por quien la usa, y entonces
no avisa de nada — que es el mismo fallo que este proyecto persigue en las
alarmas del pipeline, aquí en la interfaz.

La regla que fija este guardia: **las regiones vivas son párrafos**. Un `<p>` no
puede contener un panel; un `<div>` sí, y en cuanto lo contiene el anuncio deja
de ser un anuncio. Los cambios que merecen voz siguen saliendo por `#anuncio`,
que es `role="status"` y publica una frase.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
PAGINAS = ("index.html", "status.html")


def _regiones_vivas(pagina: str) -> list[tuple[str, str]]:
    """(etiqueta, atributos) de cada elemento con `aria-live` o `role="status"`.

    Se lee la etiqueta de apertura entera, que es lo que hay que juzgar. No se
    filtran comentarios porque el `aria-live` que explica este arreglo aparece
    dentro de uno: se descartan primero.
    """
    html = (RAIZ / "site" / pagina).read_text(encoding="utf-8")
    sin_comentarios = re.sub(r"<!--.*?-->", "", html, flags=re.S)
    return [
        (m.group(1), m.group(0))
        for m in re.finditer(r"<(\w+)\b([^>]*)>", sin_comentarios)
        if "aria-live" in m.group(2) or 'role="status"' in m.group(2)
    ]


def test_hay_regiones_vivas_que_vigilar() -> None:
    """La red de seguridad: sin regiones que mirar, la prueba de abajo pasa sola."""
    todas = [r for p in PAGINAS for r in _regiones_vivas(p)]
    assert todas, (
        "el visor no declara ninguna región viva: o se perdió el anuncio para "
        "lectores de pantalla, o este guardia dejó de encontrarlas"
    )


@pytest.mark.parametrize("pagina", PAGINAS)
def test_las_regiones_vivas_son_parrafos(pagina: str) -> None:
    """Un `<div>` vivo es un panel que interrumpe; un `<p>` vivo es una frase."""
    culpables = [
        (etiqueta, apertura) for etiqueta, apertura in _regiones_vivas(pagina) if etiqueta != "p"
    ]
    assert not culpables, (
        f"site/{pagina} declara región viva sobre {[c[0] for c in culpables]}: "
        f"{[c[1][:90] for c in culpables]}. Una región que se reescribe entera "
        f"—y la tarjeta viva se reescribe en cada `moveend`— lee el panel completo "
        f"cada vez. Los anuncios van por `#anuncio`, que es una frase"
    )
