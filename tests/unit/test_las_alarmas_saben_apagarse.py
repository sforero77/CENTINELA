"""Toda alarma que se enciende sola tiene que saber apagarse sola.

Paso con la misma forma en tres workflows distintos. `frescura.yml` abria una
incidencia en cada corrida en rojo y no cerraba ninguna: el 30-ago-2026 habia
dos abiertas por desfases resueltos horas antes. `impact.yml` dejo abiertas las
veinte del 2-sep describiendo una condicion que ya no existia. Y
`contract_drift.yml` siguio con la suya del 7-sep abierta cuando las fuentes
llevaban dias cumpliendo su contrato: sabia comentar «sigue derivando» y no
sabia decir «ya paso».

Una alarma que solo sabe encenderse deja de leerse, y entonces la siguiente que
importe tampoco se ve. Aqui no se mira cada workflow a mano: a todo job que abre
incidencias se le exige que, en el mismo job, sepa cerrarlas.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

RAIZ = Path(__file__).resolve().parents[2]
WORKFLOWS = RAIZ / ".github" / "workflows"


def _comandos(paso: dict[str, Any]) -> str:
    """Las lineas de `run:` que ejecutan algo: un comentario que cite el comando no."""
    cuerpo = paso.get("run")
    if not isinstance(cuerpo, str):
        return ""
    return "\n".join(x for x in cuerpo.splitlines() if not x.lstrip().startswith("#"))


def _jobs_que_abren_incidencias() -> list[tuple[str, str, list[dict[str, Any]]]]:
    salida: list[tuple[str, str, list[dict[str, Any]]]] = []
    for ruta in sorted(WORKFLOWS.glob("*.yml")):
        datos = yaml.safe_load(ruta.read_text(encoding="utf-8"))
        for nombre, job in (datos.get("jobs") or {}).items():
            pasos = [p for p in job.get("steps") or [] if isinstance(p, dict)]
            if any("gh issue create" in _comandos(p) for p in pasos):
                salida.append((ruta.name, nombre, pasos))
    return salida


JOBS = _jobs_que_abren_incidencias()


def test_hay_jobs_que_abren_incidencias() -> None:
    """Si la lista sale vacia, la prueba de abajo pasa en vacio y pytest lo enseña como salto."""
    assert len(JOBS) >= 6, f"solo {len(JOBS)} jobs abren incidencias: algo dejo de encontrarlos"


@pytest.mark.parametrize(("workflow", "job", "pasos"), JOBS, ids=[f"{w}:{j}" for w, j, _ in JOBS])
def test_quien_abre_una_incidencia_sabe_cerrarla(
    workflow: str, job: str, pasos: list[dict[str, Any]]
) -> None:
    cierran = [p for p in pasos if "gh issue close" in _comandos(p)]
    assert cierran, (
        f"{workflow}, job {job}: abre incidencias y ningun paso las cierra. Anade uno que "
        f"busque la abierta por titulo y la cierre cuando la condicion vuelva a estar bien."
    )
