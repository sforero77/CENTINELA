"""Ninguna acción de GitHub puede ir por etiqueta móvil.

`actions/checkout@v4` no nombra un commit: nombra una etiqueta de git, y una
etiqueta se puede reapuntar. El precedente concreto es **tj-actions/changed-files
(CVE-2025-30066, marzo de 2025)**: alguien reescribió las etiquetas de una acción
usada por miles de repositorios para que volcaran secretos al log. Quien la usaba
por etiqueta se lo llevó sin cambiar una línea.

Aquí son catorce workflows y treinta y dos usos, y trece de ellos son
`astral-sh/setup-uv`, que ni siquiera es de GitHub. Varios corren en jobs cuyo
`GITHUB_TOKEN` puede empujar a `main`.

Desde el 6-sep-2026 van todas por SHA de 40 hex, con la versión legible en el
comentario de al lado —``@11d5960…  # v4.4.0``— para que se pueda saber de qué
versión se habla sin resolver el digest. Dependabot sigue proponiendo los bumps:
reescribe el SHA y el comentario a la vez.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

RAIZ = Path(__file__).resolve().parents[2]
WORKFLOWS = RAIZ / ".github" / "workflows"

#: `owner/repo@<40 hex>`, opcionalmente con subdirectorio.
FIJADA = re.compile(r"^[\w.-]+/[\w.-]+(?:/[\w./-]+)?@[0-9a-f]{40}$")

#: Las acciones locales (`./.github/actions/...`) no llevan SHA: son de este
#: repositorio y viajan con el commit que las usa.
LOCAL = re.compile(r"^\./")


def _workflows() -> list[Path]:
    return sorted(WORKFLOWS.glob("*.yml"))


def _usos(ruta: Path) -> list[str]:
    """Los `uses:` de un workflow, sacados del YAML y no de una búsqueda de texto.

    Estos ficheros están llenos de comentarios que citan `actions/checkout@v4`
    para explicar justamente por qué no hay que escribirlo así. Un guardia que
    empareje cadenas los cuenta como usos y se pone rojo por su propia
    documentación —o, peor, verde por ella—, que es el fallo que este
    repositorio ya se ha comido ocho veces.
    """
    datos = yaml.safe_load(ruta.read_text(encoding="utf-8"))
    usos: list[str] = []
    for job in (datos.get("jobs") or {}).values():
        if isinstance(job.get("uses"), str):  # job que reutiliza otro workflow
            usos.append(job["uses"])
        for paso in job.get("steps") or []:
            if isinstance(paso, dict) and isinstance(paso.get("uses"), str):
                usos.append(paso["uses"])
    return usos


def test_hay_acciones_que_vigilar() -> None:
    """La red de seguridad: si esto sale vacío, el guardia no está mirando nada.

    Sin esta prueba, un cambio que rompiera `_usos` —un formato de YAML nuevo,
    un `jobs:` renombrado— dejaría la lista de parámetros de abajo vacía, y
    pytest enseña eso como un salto, no como un fallo. El guardia desaparecería
    sin ponerse rojo.
    """
    todos = [u for ruta in _workflows() for u in _usos(ruta)]
    assert len(todos) >= 30, f"solo se encontraron {len(todos)} usos de acciones; se esperaban ~32"


@pytest.mark.parametrize("ruta", _workflows(), ids=lambda p: p.name)
def test_cada_accion_va_por_sha(ruta: Path) -> None:
    """Ni una etiqueta móvil, en ningún workflow."""
    moviles = [u for u in _usos(ruta) if not LOCAL.match(u) and not FIJADA.match(u)]
    assert not moviles, (
        f"{ruta.name} usa {moviles} por etiqueta. Una etiqueta de git se reapunta; "
        f"un SHA no. Resuelve el digest con "
        f"`gh api repos/<owner>/<repo>/git/ref/tags/<tag> --jq .object.sha` y "
        f"deja la version en un comentario al lado"
    )


@pytest.mark.parametrize("ruta", _workflows(), ids=lambda p: p.name)
def test_cada_sha_dice_de_que_version_es(ruta: Path) -> None:
    """Un digest sin versión al lado es ilegible, y lo ilegible no se revisa.

    Se lee la línea cruda porque el comentario no sobrevive al `yaml.safe_load`:
    es la única parte de este guardia que mira texto, y solo mira las líneas que
    **empiezan** por `uses:` tras el guion, nunca un comentario.
    """
    sin_version = []
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        limpia = linea.strip().lstrip("- ").strip()
        if not limpia.startswith("uses:"):
            continue
        if "@" in limpia and re.search(r"@[0-9a-f]{40}", limpia) and "#" not in limpia:
            sin_version.append(limpia)
    assert not sin_version, (
        f"{ruta.name} fija por SHA sin decir de qué versión: {sin_version}. "
        f"El comentario `# v4.4.0` es lo que hace revisable el bump de dependabot"
    )
