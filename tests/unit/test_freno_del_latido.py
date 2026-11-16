"""El freno del latido mide la edad del latido ANTERIOR, no del recien escrito.

`centinela trigger` anade el latido de la corrida a `site/status.json`, y el
paso «Publicar estado y latido» volvia a leer ese fichero para decidir si ya
habia pasado una hora: la edad salia siempre en segundos y el latido solo se
publicaba cuando habia sismo u observados nuevos. El 16-nov-2026 `status.json`
llego a 13,6 h sin publicarse y la frescura del visor abrio #218.

Se ejecuta el fragmento de bash real del workflow, no se busca texto: lo que
importa es la decision que toma.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
import yaml

WORKFLOW = Path(__file__).parent.parent.parent / ".github" / "workflows" / "trigger.yml"


def _pasos() -> list[dict[str, Any]]:
    datos = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    return list(datos["jobs"]["vigilar"]["steps"])


def _paso(nombre: str) -> dict[str, Any]:
    return next(p for p in _pasos() if p.get("name") == nombre)


def test_el_sello_se_toma_antes_de_revisar_el_feed() -> None:
    nombres = [p.get("name") for p in _pasos()]
    revisiones = nombres.index("Contar las revisiones desde el ultimo latido")
    feed = nombres.index("Revisar el feed")
    assert revisiones < feed, "el sello tiene que leerse antes de que trigger reescriba status.json"
    assert "ultimo_utc=" in _paso("Contar las revisiones desde el ultimo latido")["run"]

    publicar = _paso("Publicar estado y latido")
    assert publicar["env"]["ULTIMO_UTC"] == "${{ steps.revisiones.outputs.ultimo_utc }}"
    assert ".latidos[-1]" not in publicar["run"], "releer status.json da el latido recien escrito"


def _freno() -> str:
    """El bloque del workflow que decide, hasta el `exit 0` del freno."""
    run = str(_paso("Publicar estado y latido")["run"])
    inicio = run.index("ULTIMO=0")
    fin = run.index("exit 0", inicio) + len("exit 0")
    return run[inicio:fin] + "\nfi\necho PUBLICA\n"


@pytest.mark.skipif(
    shutil.which("bash") is None or sys.platform == "win32",
    reason="en Windows `bash` es el de WSL; el workflow corre en Linux y CI tambien",
)
@pytest.mark.parametrize(
    ("ultimo_utc", "publica"),
    [
        ("2026-11-15T15:25:20Z", True),  # 13,6 h: el caso de #218
        ("", True),  # sin latido previo
        ("2099-01-01T00:00:00Z", False),  # reciente (en el futuro: edad negativa)
    ],
)
def test_un_latido_viejo_se_publica(ultimo_utc: str, publica: bool) -> None:
    salida = subprocess.run(
        ["bash", "-c", _freno()],
        env={
            "PATH": "/usr/bin:/bin",
            "ULTIMO_UTC": ultimo_utc,
            "HAY_TRABAJO": "false",
            "OBSERVADOS_CAMBIO": "false",
        },
        capture_output=True,
        text=True,
        check=False,
    )
    assert ("PUBLICA" in salida.stdout) is publica, salida.stdout + salida.stderr
