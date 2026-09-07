"""El globo de una celda con fuego nombraba cuatro clases de seis.

`cuadroDeIncendio` listaba arbolado, pastizal, cultivo y humedal. Faltaban
**arbustos** y **construido**, que son justamente las dos que P0 añadió por ser
decisivas en América Latina: el matorral es la cobertura del Cerrado, el Chaco y
la Caatinga, y `construido` es la interfaz urbano-forestal, que es donde un foco
deja de ser rutina agrícola.

Medido sobre el `incendios.json` del 6-sep-2026: 74 celdas salían sin una sola
línea de reparto teniendo una de esas dos por encima del 5 %, y hay celdas de
matorral al 100 % que se describían como si no se hubiera medido nada.

La tarjeta «Ahora mismo» ya las nombraba desde el 3-sep. Este guardia existe para
que las dos listas no vuelvan a separarse: **el contrato es el fichero
publicado**, no una constante en el visor.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
APP = RAIZ / "site" / "assets" / "app.js"
INCENDIOS = RAIZ / "site" / "incendios.json"


def _sin_comentarios(codigo: str) -> str:
    """Quita bloques `/* */` y líneas que empiezan por `//`.

    Sin esto, el comentario que explica este mismo arreglo —y que nombra las seis
    clases— haría pasar el guardia con el código roto. Ha pasado ocho veces en
    este repositorio.
    """
    sin_bloque = re.sub(r"/\*.*?\*/", "", codigo, flags=re.S)
    return "\n".join(
        linea for linea in sin_bloque.splitlines() if not linea.strip().startswith("//")
    )


def _clases_del_globo() -> list[str]:
    """Las clases que `cuadroDeIncendio` nombra, en el orden en que las pinta."""
    codigo = _sin_comentarios(APP.read_text(encoding="utf-8"))
    inicio = codigo.index("function cuadroDeIncendio(")
    # Hasta el `}` a columna cero, que es donde acaba la funcion. Cortar por el
    # primer `]` no vale: el primero es el de la primera entrada de la lista.
    cuerpo = codigo[inicio : codigo.index("\n}", inicio)]
    pares = re.findall(r'\["(\w+)",\s*p\.(\w+)_pct\]', cuerpo)
    # Se exige que el rotulo y la clave del dato coincidan: `["pastizal",
    # p.cultivo_pct]` pintaria la cifra equivocada bajo el nombre correcto, y
    # comparar solo los nombres no lo veria.
    for rotulo, clave in pares:
        assert rotulo == clave, f"el globo rotula «{rotulo}» sobre el dato de «{clave}»"
    return [rotulo for rotulo, _ in pares]


def _clases_publicadas() -> set[str]:
    """Las clases que P5 publica por celda en `incendios.json`."""
    datos = json.loads(INCENDIOS.read_text(encoding="utf-8"))
    celdas = datos.get("celdas") or []
    assert celdas, "incendios.json no trae celdas: el contrato no se puede leer"
    return {k[: -len("_pct")] for k in celdas[0] if k.endswith("_pct")}


def test_el_globo_lee_alguna_clase() -> None:
    """La red de seguridad: una lista vacía aprobaría cualquier cosa."""
    assert _clases_del_globo(), (
        "no se pudo extraer ninguna clase de `cuadroDeIncendio`: el guardia "
        "estaría comparando dos conjuntos vacíos y pasaría siempre"
    )


def test_el_globo_nombra_todas_las_clases_publicadas() -> None:
    """Lo que el activo mide y P5 publica, el globo lo dice."""
    del_globo = set(_clases_del_globo())
    publicadas = _clases_publicadas()

    faltan = publicadas - del_globo
    assert not faltan, (
        f"P5 publica {sorted(faltan)} por celda y el globo no lo nombra: sobre una "
        f"celda de matorral al 100 % el panel queda mudo, como si no se hubiera "
        f"medido nada debajo del fuego"
    )

    sobran = del_globo - publicadas
    assert not sobran, (
        f"el globo nombra {sorted(sobran)}, que no está en `incendios.json`: "
        f"leería siempre `undefined` y no se pintaría nunca"
    )
