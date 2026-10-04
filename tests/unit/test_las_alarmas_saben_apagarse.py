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


def _despliegan_pages() -> list[str]:
    salida = []
    for ruta in sorted(WORKFLOWS.glob("*.yml")):
        datos = yaml.safe_load(ruta.read_text(encoding="utf-8"))
        for job in (datos.get("jobs") or {}).values():
            usos = [str(p.get("uses", "")) for p in job.get("steps") or [] if isinstance(p, dict)]
            if any(u.startswith("actions/deploy-pages@") for u in usos):
                salida.append(ruta.name)
    return sorted(set(salida))


def test_hay_quien_despliega_la_pagina() -> None:
    """Si la lista sale vacia, la prueba de abajo no comprueba nada."""
    assert _despliegan_pages(), "ningun workflow usa actions/deploy-pages"


@pytest.mark.parametrize("workflow", _despliegan_pages())
def test_un_despliegue_que_muere_lo_dice(workflow: str) -> None:
    """Hallazgo #62 de la auditoria de septiembre de 2026.

    `site.yml` es lo unico que publica algo al publico y era lo unico sin camino
    de fallo: la despacha un bot tras su push, asi que una corrida en rojo no la
    abria nadie. Se exige un job que dependa del despliegue, corra aunque este
    falle y abra la incidencia; que ademas sepa cerrarla lo exige la prueba de
    arriba.
    """
    datos = yaml.safe_load((WORKFLOWS / workflow).read_text(encoding="utf-8"))
    jobs = datos["jobs"]
    despliegan = {
        nombre
        for nombre, job in jobs.items()
        if any(
            str(p.get("uses", "")).startswith("actions/deploy-pages@")
            for p in job.get("steps") or []
            if isinstance(p, dict)
        )
    }
    vigilantes = [
        nombre
        for nombre, job in jobs.items()
        if despliegan
        & set([job.get("needs")] if isinstance(job.get("needs"), str) else job.get("needs") or [])
        and "always()" in str(job.get("if", ""))
        and any(
            "gh issue create" in _comandos(p) for p in job.get("steps") or [] if isinstance(p, dict)
        )
    ]

    assert vigilantes, f"{workflow} despliega la pagina y ningun job avisa si el despliegue muere"
