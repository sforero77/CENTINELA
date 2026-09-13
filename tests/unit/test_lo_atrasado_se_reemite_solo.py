"""Lo que se quedo atras de sus fuentes se re-emite sin que nadie pulse nada.

Hasta el 13-sep-2026 `rezago.yml` informaba y una persona decidia, porque
re-emitir movia cifras que el README citaba a mano. Ese dia el README dejo de
publicar cifras y la indicacion fue la contraria: si hay versiones nuevas y hay
que re-emitir, que se ejecute solo. Estas pruebas vigilan que la corrida
programada no vuelva a quedarse en un aviso.

Y la trampa que este workflow ya cazo una vez: en un evento `schedule` el
contexto `inputs` no existe, asi que una condicion que solo mire el input se
evalua distinto de lo que parece. Por eso se comprueba la condicion literal, y
que cada salida que el workflow lee la escriba de verdad el comando: un nombre
mal copiado deja el paso saltandose en verde para siempre.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

RAIZ = Path(__file__).resolve().parents[2]
REZAGO = RAIZ / ".github" / "workflows" / "rezago.yml"
CLI = RAIZ / "pipelines" / "cli.py"


def _workflow() -> dict[Any, Any]:
    datos = yaml.safe_load(REZAGO.read_text(encoding="utf-8"))
    assert isinstance(datos, dict)
    return datos


def _comandos(paso: dict[str, Any]) -> str:
    cuerpo = paso.get("run")
    if not isinstance(cuerpo, str):
        return ""
    return "\n".join(x for x in cuerpo.splitlines() if not x.lstrip().startswith("#"))


def _paso_que_despacha() -> dict[str, Any]:
    pasos = [p for p in _workflow()["jobs"]["comprobar"]["steps"] if isinstance(p, dict)]
    despachan = [p for p in pasos if "gh workflow run impact.yml" in _comandos(p)]
    assert len(despachan) == 1, f"{len(despachan)} pasos despachan impact.yml; se esperaba uno"
    return despachan[0]


def test_rezago_tiene_reloj() -> None:
    datos = _workflow()
    # `on` es la palabra reservada `True` para el cargador de YAML.
    disparo = datos.get(True) or datos.get("on") or {}
    assert "schedule" in disparo, "sin cron, re-emitir vuelve a depender de que alguien se acuerde"


def test_la_corrida_programada_re_emite() -> None:
    condicion = str(_paso_que_despacha().get("if", ""))
    assert "github.event_name == 'schedule'" in condicion, (
        f"el paso que re-emite no se ejecuta en la corrida programada: `if: {condicion}`"
    )


def test_re_emite_con_reprocesar() -> None:
    """Sin `reprocesar=true`, un reporte atrasado solo en el activo no se recalcula.

    USGS no publico nada nuevo, asi que P2 sale con «misma version» y el
    despacho termina en verde sin haber cambiado nada.
    """
    assert "reprocesar=true" in _comandos(_paso_que_despacha())


def test_cada_salida_que_lee_el_workflow_la_escribe_el_comando() -> None:
    leidas = set(re.findall(r"steps\.comprobar\.outputs\.(\w+)", REZAGO.read_text("utf-8")))
    cli = CLI.read_text(encoding="utf-8")
    inicio = cli.index("def _cmd_rezagados(")
    cuerpo = cli[inicio : cli.index("\ndef ", inicio + 1)]
    escritas = set(re.findall(r'_emit_github_output\(\s*"(\w+)"', cuerpo))

    assert leidas, "rezago.yml ya no lee ninguna salida de `centinela rezagados`"
    faltan = sorted(leidas - escritas)
    assert not faltan, (
        f"rezago.yml lee {faltan} y `centinela rezagados` no las escribe: el paso "
        f"que depende de ellas se saltaria en verde"
    )
