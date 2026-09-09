"""Los workflows que existen son los que la documentacion dice que existen.

LA CUENTA SE QUEDO VIEJA DOS VECES, Y EN EL MISMO DOCUMENTO. `docs/acciones/
README.md` abria con "Trece workflows" y tres lineas mas abajo titulaba la tabla
"Las doce, de un vistazo", con catorce ficheros en `.github/workflows/`. Y
`docs/README.md` y el `README.md` raiz decian "las doce GitHub Actions".

Es la misma familia que `test_cifras_del_readme.py`: una cuenta copiada a mano se
desincroniza en cuanto entra un fichero, y nadie lo nota porque el documento
sigue leyendose bien. La diferencia entre una cuenta y una cuenta con prueba.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).parent.parent.parent
WORKFLOWS = RAIZ / ".github" / "workflows"
INDICE = RAIZ / "docs" / "acciones" / "README.md"

#: Los numeros escritos en prosa, en los tres documentos que los citan.
EN_PROSA = (
    ("docs/acciones/README.md", "**Catorce workflows.**"),
    ("docs/acciones/README.md", "## Las catorce, de un vistazo"),
    ("docs/README.md", "Las catorce GitHub Actions:"),
    ("README.md", "Las catorce GitHub Actions:"),
)


def _workflows() -> list[str]:
    return sorted(p.name for p in WORKFLOWS.glob("*.yml"))


def test_son_catorce() -> None:
    """Si entra o sale un workflow, esta prueba lo dice antes que un lector."""
    encontrados = _workflows()
    assert len(encontrados) == 14, (
        f"hay {len(encontrados)} workflows y la documentacion dice catorce: "
        f"{encontrados}. Actualiza los cuatro sitios de EN_PROSA y esta prueba."
    )


@pytest.mark.parametrize(("documento", "frase"), EN_PROSA)
def test_los_documentos_dicen_la_cuenta(documento: str, frase: str) -> None:
    texto = (RAIZ / documento).read_text(encoding="utf-8")
    assert frase in texto, f"{documento} ya no dice «{frase}»"


def test_cada_workflow_esta_en_la_tabla() -> None:
    """Una tabla que no los lista todos es peor que no tener tabla.

    Quien la lee da por hecho que esta completa, y el que falta es justo el que
    nadie sabe que existe.
    """
    indice = INDICE.read_text(encoding="utf-8")
    faltan = [w for w in _workflows() if f"`{w}`" not in indice]
    assert not faltan, f"sin fila en docs/acciones/README.md: {faltan}"


def test_la_tabla_no_lista_workflows_que_ya_no_existen() -> None:
    """El reverso: una fila para un fichero borrado manda a buscar un fantasma."""
    indice = INDICE.read_text(encoding="utf-8")
    citados = set(re.findall(r"`([a-z_]+\.yml)`", indice))
    fantasmas = sorted(citados - set(_workflows()))
    assert not fantasmas, f"la tabla cita workflows que ya no existen: {fantasmas}"
