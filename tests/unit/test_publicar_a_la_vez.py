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
    cuerpo = _manejador(workflow)

    assert "centinela resolver-derivados" in cuerpo, (
        f"{workflow} no resuelve el conflicto con el manejador compartido"
    )
    assert "git rebase --continue" in cuerpo


def _manejador(workflow: str) -> str:
    """El cuerpo de `regenerar_derivados()`, sin comentarios ni sangria."""
    texto = _texto(workflow)
    assert "regenerar_derivados() {" in texto, f"{workflow} no maneja el conflicto de derivados"
    bloque = texto[texto.index("regenerar_derivados() {") :]
    bloque = bloque[: bloque.index("\n          }")]
    return "\n".join(
        linea.strip()
        for linea in bloque.splitlines()
        if linea.strip() and not linea.strip().startswith("#")
    )


def test_el_manejador_es_el_mismo_en_los_dos_workflows() -> None:
    """Hallazgo #68 de la auditoria de septiembre de 2026.

    Eran dos copias en bash del mismo manejador, cada una con su lista de
    derivados, y ya habian divergido: `trigger.yml` no sabia del indice de
    reportes, `impact.yml` no sabia de `observados.json`, y el `checkout
    --theirs` que salva los latidos llego a una semanas despues que a la otra.
    El 2-sep-2026 la copia atrasada dejo los dos derivados corruptos en `main`.

    Ahora la logica vive en `pipelines/common/derivados.py` y lo que queda en
    cada workflow es la llamada. Tiene que ser identica: si alguien vuelve a
    meter logica en una sola copia, esto se pone rojo.
    """
    trigger, impacto = (_manejador(w) for w in QUE_EMPUJAN)

    assert trigger == impacto, f"los manejadores divergieron:\n{trigger}\n---\n{impacto}"


@pytest.mark.parametrize("workflow", QUE_EMPUJAN)
def test_ningun_workflow_lleva_su_propia_lista_de_derivados(workflow: str) -> None:
    """La lista vive en un solo sitio; una segunda copia es la que se queda atras."""
    comandos = [
        linea.strip()
        for linea in _texto(workflow).splitlines()
        if not linea.strip().startswith("#")
    ]

    assert not [x for x in comandos if x.startswith("DERIVADOS=")], workflow
    assert not [x for x in comandos if "checkout --theirs" in x], workflow


@pytest.mark.parametrize("workflow", QUE_EMPUJAN)
def test_todo_derivado_que_se_commitea_esta_en_la_lista_compartida(workflow: str) -> None:
    """La lista tiene que cubrir lo que cada workflow commitea.

    Si un workflow empieza a commitear otro fichero que el otro tambien
    reescribe y la lista no lo sabe, el manejador se niega a tocarlo —bien— y
    la publicacion muere en el conflicto —mal—. Lo que se mira son los
    ficheros sueltos de `site/` y el indice, que son los que se reescriben
    enteros.
    """
    from pipelines.common.derivados import DERIVADOS

    anadidos = {
        argumento
        for linea in _texto(workflow).splitlines()
        if (comando := linea.strip()).startswith("git add ")
        for argumento in comando.removeprefix("git add ").split()
        if argumento.endswith(".json")
    }

    assert anadidos, f"{workflow}: no se encontro ningun `git add` de un JSON"
    assert anadidos <= set(DERIVADOS), f"{workflow} commitea {anadidos - set(DERIVADOS)}"


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
