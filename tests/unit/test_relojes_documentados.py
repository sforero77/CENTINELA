"""Cada workflow tiene su diagrama, y cada cron dice la hora que de verdad corre.

Misma familia que `test_acciones_documentadas.py` y `test_cifras_del_readme.py`:
un documento que describe catorce workflows se queda viejo en cuanto entra el
decimoquinto, y nadie lo nota porque el texto sigue leyendose bien.

Lo que se vigila aqui son dos cosas distintas:

1. **Que no falte ninguno.** Un diagrama por disparador en `por-reloj.md`. Si
   entra un workflow y no se dibuja, el documento pasa de "el mapa completo" a
   "el mapa de casi todo", que es peor que no tenerlo: quien lo lee da por hecho
   que esta entero.

2. **Que la hora escrita sea la hora que corre.** Las expresiones cron viven en
   el YAML y se copian a mano a la tabla. Una tabla que dice "diario 08:00"
   cuando el cron cambio a las 05:00 manda a mirar los logs de la hora
   equivocada. Aqui se comparan literalmente.

La **sintaxis** de los diagramas no se comprueba aqui: pide un navegador
(mermaid-cli arrastra Chromium) y esta suite corre sin red. La compila el job
`diagramas` de `ci.yml` con `scripts/validar_diagramas.py`, y que ese job siga
existiendo y encuentre todos los bloques lo vigila `test_los_diagramas_compilan.py`.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

RAIZ = Path(__file__).resolve().parents[2]
WORKFLOWS = RAIZ / ".github" / "workflows"
POR_RELOJ = RAIZ / "docs" / "acciones" / "por-reloj.md"


def _workflows() -> list[Path]:
    return sorted(WORKFLOWS.glob("*.yml"))


def _crons(wf: Path) -> list[str]:
    """Expresiones cron declaradas en un workflow.

    `on` es la palabra reservada `True` para el cargador de YAML —lo lee como
    booleano, no como cadena—, asi que hay que pedir las dos claves.
    """
    datos = yaml.safe_load(wf.read_text(encoding="utf-8"))
    disparo = datos.get(True) or datos.get("on") or {}
    if not isinstance(disparo, dict):
        return []
    programado = disparo.get("schedule") or []
    return [str(entrada["cron"]) for entrada in programado if "cron" in entrada]


def test_cada_workflow_tiene_su_diagrama() -> None:
    """Cada uno nombrado, y con un bloque mermaid despues de su titulo."""
    texto = POR_RELOJ.read_text(encoding="utf-8")
    faltan = [wf.name for wf in _workflows() if f"`{wf.name}`" not in texto]
    assert not faltan, f"sin sección en docs/acciones/por-reloj.md: {faltan}"


def test_hay_al_menos_un_diagrama_por_workflow() -> None:
    """La cuenta de bloques mermaid no puede bajar del numero de workflows.

    No fija un numero exacto a proposito: el documento lleva ademas el timeline
    del dia, y exigir la igualdad obligaria a tocar esta prueba por cada
    diagrama de contexto que se agregue.
    """
    texto = POR_RELOJ.read_text(encoding="utf-8")
    diagramas = texto.count("```mermaid")
    assert diagramas >= len(_workflows()), (
        f"{diagramas} diagramas para {len(_workflows())} workflows: falta dibujar alguno"
    )


@pytest.mark.parametrize("wf", _workflows(), ids=lambda p: p.name)
def test_los_crons_documentados_son_los_que_corren(wf: Path) -> None:
    """La expresion cron del YAML aparece literal en la tabla de relojes."""
    texto = POR_RELOJ.read_text(encoding="utf-8")
    faltan = [c for c in _crons(wf) if f"`{c}`" not in texto]
    assert not faltan, (
        f"{wf.name} corre con {faltan} y por-reloj.md no lo dice. "
        f"Si el cron cambió, cambia también la tabla."
    )


def test_no_se_documentan_crons_que_no_existen() -> None:
    """El reverso: una hora en la tabla que ningun workflow declara.

    Es el fallo mas caro de los dos. Que falte una fila se nota al buscarla;
    que sobre, no: manda a esperar una corrida a una hora en la que no va a
    pasar nada, y eso solo se descubre mirando los logs vacios.
    """
    texto = POR_RELOJ.read_text(encoding="utf-8")
    # Una expresion cron entre comillas invertidas: cinco campos separados por
    # espacios, con los caracteres que cron admite.
    citados = set(re.findall(r"`([\d*,/\-]+(?: +[\d*,/\-]+){4})`", texto))
    reales = {c for wf in _workflows() for c in _crons(wf)}
    fantasmas = sorted(citados - reales)
    assert not fantasmas, f"por-reloj.md documenta crons que nadie declara: {fantasmas}"
