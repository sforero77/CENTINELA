"""El ritual que la documentación manda correr tiene que ser el que corre CI.

`docs/AUDITORIA-2026-09.md` escribió el ritual de validación con
`uv run mypy pipelines` —solo el paquete del pipeline— mientras `ci.yml` corre
`uv run mypy`, que es el repositorio entero. Durante toda la auditoría de
septiembre se validó con el comando corto, así que **dieciocho errores de tipos
se acumularon en siete ficheros de `tests/`** sin que ninguna corrida local los
viera: aparecieron todos juntos en la primera corrida de CI de la rama.

Un ritual documentado más flojo que el de CI es peor que no documentarlo: da la
señal de «esto ya está comprobado» sobre lo que no se ha comprobado.

Este guardia lee los dos sitios y exige que las herramientas coincidan. No
compara cadenas enteras —CI añade `--cov` a pytest y eso no tiene por qué estar
en el ritual de mano— sino la **invocación de cada herramienta**, que es donde
estaba la diferencia que importaba.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

RAIZ = Path(__file__).resolve().parents[2]
DOC = RAIZ / "docs" / "AUDITORIA-2026-09.md"
CI = RAIZ / ".github" / "workflows" / "ci.yml"

#: Herramientas cuya invocación tiene que ser idéntica en los dos sitios.
#:
#: `pytest` queda fuera a propósito: CI le añade `--cov --cov-report`, que en
#: local no aporta nada y alarga la corrida. Lo que no puede diferir es **qué se
#: revisa**, y eso lo fijan `ruff` y `mypy`.
HERRAMIENTAS = ("mypy", "ruff check", "ruff format")


def _comandos_del_ritual() -> list[str]:
    """Las líneas `uv run ...` del bloque de código del ritual.

    Se lee el bloque cercado que sigue al encabezado, no el documento entero:
    la prosa de alrededor cita comandos como ejemplo y confundirlos con el
    ritual es exactamente la clase de falso positivo que este repositorio ya se
    ha comido ocho veces.
    """
    texto = DOC.read_text(encoding="utf-8")
    corte = texto.split("## Cómo se validó cada reparación", 1)
    assert len(corte) == 2, f"{DOC.name} ya no tiene el encabezado del ritual"
    bloques = re.findall(r"```\n(.*?)```", corte[1], re.S)
    assert bloques, f"{DOC.name} no trae ningún bloque de código tras el ritual"
    return [
        linea.split("#", 1)[0].strip()
        for linea in bloques[0].splitlines()
        if linea.strip().startswith("uv run")
    ]


def _comandos_de_ci() -> list[str]:
    """Los `run:` del job que revisa, con las variables sin resolver.

    Se parsea el YAML en vez de buscar cadenas: un comentario que mencione
    `uv run mypy` —y `ci.yml` tiene varios explicando justo esto— no es un
    comando, y un guardia que no distinga las dos cosas aprueba por la
    documentación del fichero que vigila.
    """
    datos = yaml.safe_load(CI.read_text(encoding="utf-8"))
    comandos: list[str] = []
    for job in (datos.get("jobs") or {}).values():
        for paso in job.get("steps") or []:
            if isinstance(paso, dict) and isinstance(paso.get("run"), str):
                comandos.extend(
                    linea.strip()
                    for linea in paso["run"].splitlines()
                    if linea.strip().startswith("uv run")
                )
    return comandos


def test_el_ritual_y_ci_corren_las_mismas_herramientas() -> None:
    """Ni el ritual manda menos de lo que CI exige, ni al revés."""
    ritual = _comandos_del_ritual()
    assert ritual, "el bloque del ritual quedó vacío: el guardia no estaría mirando nada"


@pytest.mark.parametrize("herramienta", HERRAMIENTAS)
def test_cada_herramienta_se_invoca_igual_en_los_dos_sitios(herramienta: str) -> None:
    """`mypy pipelines` en el ritual y `mypy` en CI es como se coló esto."""
    del_ritual = [c for c in _comandos_del_ritual() if f"uv run {herramienta}" in c]
    de_ci = [c for c in _comandos_de_ci() if f"uv run {herramienta}" in c]

    assert del_ritual, (
        f"{DOC.name} documenta el ritual sin `{herramienta}`, que CI sí corre: "
        f"quien siga el ritual creerá haber comprobado algo que no comprobó"
    )
    assert de_ci, f"{CI.name} dejó de correr `{herramienta}`; el ritual todavía lo manda"

    # `ruff format --check` en CI y `ruff format .` en el ritual son el mismo
    # trabajo con distinto final: uno avisa, el otro arregla. Se comparan sin
    # esa cola.
    def normaliza(comando: str) -> str:
        return comando.replace(" --check", "").replace(" .", "").strip()

    assert {normaliza(c) for c in del_ritual} == {normaliza(c) for c in de_ci}, (
        f"el ritual corre {del_ritual} y CI corre {de_ci}: el más flojo de los dos "
        f"es el que se acaba usando, y lo que no revisa se acumula hasta el primer PR"
    )
