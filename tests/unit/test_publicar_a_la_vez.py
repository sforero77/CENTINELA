"""Que dos workflows empujando a la vez no pierdan lo que ya calcularon.

`trigger.yml` e `impact.yml` empujan los dos a `main` y los dos reescriben
`site/status.json` **entero**. Cuando coinciden, el rebase conflicta siempre: un
derivado no se fusiona, se regenera.

La colision es rara —P2 solo corre con un sismo M>=5,5, unos ocho al mes— pero
ocurre exactamente cuando mas importa: mientras se publica un reporte real. Y
hasta el 27-ago-2026 `trigger.yml` no la manejaba, con el agravante de que sin
`git rebase --abort` el rebase se quedaba a medias y los tres reintentos
siguientes morian con "rebase in progress" sin llegar a intentar nada.
"""

from __future__ import annotations

from pathlib import Path

import pytest

WORKFLOWS = Path(__file__).parent.parent.parent / ".github" / "workflows"

#: Los que empujan a main y por tanto pueden chocar entre si.
QUE_EMPUJAN = ("trigger.yml", "impact.yml")


def _texto(nombre: str) -> str:
    return (WORKFLOWS / nombre).read_text(encoding="utf-8")


@pytest.mark.parametrize("workflow", QUE_EMPUJAN)
def test_un_rebase_fallido_se_aborta(workflow: str) -> None:
    """Sin abortar, el primer conflicto envenena todos los reintentos.

    `git pull --rebase` deja el rebase a medias; el intento siguiente falla al
    instante con "rebase in progress" y ni siquiera llega a la red. Cuatro
    intentos que en la practica son uno.
    """
    assert "git rebase --abort" in _texto(workflow), (
        f"{workflow} reintenta el push sin abortar el rebase fallido"
    )


@pytest.mark.parametrize("workflow", QUE_EMPUJAN)
def test_los_derivados_se_regeneran_en_vez_de_fusionarse(workflow: str) -> None:
    """`status.json` se reescribe entero en cada corrida: fusionarlo no significa nada.

    Se regenera desde los `event_state`, que son la fuente. Fusionar dos
    versiones completas de un derivado produce un fichero que no corresponde a
    ningun estado real del sistema.
    """
    texto = _texto(workflow)

    assert "regenerar_derivados" in texto, f"{workflow} no maneja el conflicto de derivados"
    assert "centinela status" in texto, f"{workflow} no regenera site/status.json"


@pytest.mark.parametrize("workflow", QUE_EMPUJAN)
def test_solo_se_regenera_lo_que_esta_en_la_lista(workflow: str) -> None:
    """Un conflicto fuera de la lista es real y no se toca.

    Regenerar a ciegas descartaria el trabajo del otro job, que es peor que
    fallar: fallar deja rastro, descartar no.
    """
    assert "grep -qvE" in _texto(workflow), (
        f"{workflow} podria regenerar sobre un conflicto que no es de un derivado"
    )


@pytest.mark.parametrize("workflow", QUE_EMPUJAN)
def test_cada_uno_declara_los_derivados_que_el_escribe(workflow: str) -> None:
    """La lista tiene que cubrir lo que ese workflow commitea, ni mas ni menos.

    `observados.json` nacio el 26-ago y solo lo escribe P1; si algun dia lo
    escribiera P2, su lista tendria que crecer. Esta prueba lo pilla.
    """
    texto = _texto(workflow)
    lista = texto[texto.index("DERIVADOS=") : texto.index("DERIVADOS=") + 200].splitlines()[0]

    for fichero in ("site/status.json", "site/observados.json", "reports/index.json"):
        if f"git add {fichero}" in texto or f" {fichero}" in texto.split("DERIVADOS=")[0]:
            if fichero == "reports/index.json":
                continue  # se genera, no se anade a mano
            assert fichero in lista, (
                f"{workflow} commitea {fichero} pero no lo regenera ante conflicto: {lista}"
            )


def test_el_monitor_externo_no_late_cuando_la_corrida_fallo() -> None:
    """Con `always()`, una corrida rota le decia al monitor "estoy vivo".

    Asi solo detectaba "no corrio" y nunca "corrio y se rompio" — que es justo
    el caso que el manejador de conflictos existe para cubrir. Con `success()`,
    un fallo se ve como silencio, y silencio es lo que el monitor sabe
    interpretar: alerta a los 30 min.
    """
    texto = _texto("trigger.yml")
    bloque = texto[texto.index("Latido al monitor externo") :][:200]

    assert "success()" in bloque, "el monitor late aunque la corrida haya fallado"
    assert "always()" not in bloque
