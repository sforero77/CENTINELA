"""Toda constante de `common/constants.py` la lee alguien.

El modulo promete que "cambiar cualquiera cambia el comportamiento publicado".
La auditoria del 5-sep-2026 (#78) encontro siete que no leia nadie —bandas MMI,
resoluciones del visor, paises por fase, el CRS, la cadencia de RF-03— y al
medirlo de nuevo el 3-oct-2026 salio una octava: `MMI_BANDS_INFRAESTRUCTURA`,
que aparecia en cuatro modulos y por eso **parecia viva**. Las cuatro eran
comentarios del tipo "ver `MMI_BANDS_INFRAESTRUCTURA`".

De ahi la forma del guardia: se recorre el AST, no el texto. Un comentario no es
un nodo y un docstring es una cadena, asi que ninguno de los dos puede aprobar
una constante. Y cuentan solo las lecturas desde `pipelines/`: una constante que
solo leen las pruebas tampoco cambia lo que el sistema publica.
"""

from __future__ import annotations

import ast
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
CONSTANTES = RAIZ / "pipelines" / "common" / "constants.py"


def _declaradas() -> list[str]:
    arbol = ast.parse(CONSTANTES.read_text(encoding="utf-8"))
    return [
        nodo.target.id
        for nodo in arbol.body
        if isinstance(nodo, ast.AnnAssign) and isinstance(nodo.target, ast.Name)
    ]


def _lecturas(fuente: str) -> set[str]:
    """Nombres que un fuente LEE como codigo: `X` o `modulo.X`."""
    leidas: set[str] = set()
    for nodo in ast.walk(ast.parse(fuente)):
        if isinstance(nodo, ast.Name) and isinstance(nodo.ctx, ast.Load):
            leidas.add(nodo.id)
        elif isinstance(nodo, ast.Attribute) and isinstance(nodo.ctx, ast.Load):
            leidas.add(nodo.attr)
    return leidas


def _leidas_en_pipelines() -> set[str]:
    """Nombres que el codigo de `pipelines/` lee, fuera del propio modulo."""
    leidas: set[str] = set()
    for ruta in (RAIZ / "pipelines").rglob("*.py"):
        if ruta != CONSTANTES:
            leidas |= _lecturas(ruta.read_text(encoding="utf-8"))
    return leidas


def test_el_guardia_ve_las_constantes() -> None:
    """Sin esto, un cambio en la forma de declararlas (sin anotacion, por
    ejemplo) dejaria la lista vacia y la prueba de abajo pasaria sin mirar nada.
    """
    declaradas = _declaradas()
    assert len(declaradas) >= 15, declaradas
    assert "H3_RES_COMPUTE" in declaradas


def test_ninguna_constante_se_queda_sin_lector() -> None:
    leidas = _leidas_en_pipelines()
    huerfanas = [nombre for nombre in _declaradas() if nombre not in leidas]
    assert not huerfanas, (
        f"{huerfanas} no las lee ningun modulo de pipelines/: cambiarlas no cambia "
        f"nada, en el modulo que promete lo contrario. Conectalas o borralas."
    )


def test_un_comentario_no_cuenta_como_lectura() -> None:
    """El caso exacto de `MMI_BANDS_INFRAESTRUCTURA`, para que el guardia no
    pueda degradarse a una busqueda de texto sin que esto lo diga."""
    salto = chr(10)
    comentado = salto.join(['"""Ver `ZETA`."""', "# Ver `ZETA` en constants.py", "x = 1", ""])
    leido = salto.join(["from m import ZETA", "y = ZETA + constants.OMEGA", ""])

    assert "ZETA" not in _lecturas(comentado)
    assert {"ZETA", "OMEGA"} <= _lecturas(leido)
