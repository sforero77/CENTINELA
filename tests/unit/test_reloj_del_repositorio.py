"""El vigia es el reloj de los demas workflows.

GitHub no concede un turno de cron por workflow: concede unos pocos por
**repositorio**. Medido el 27-ago-2026: cinco turnos en veinticuatro horas
repartidos entre cinco workflows programados.

    incendios.yml   pedia 4 al dia   corrio 0
    frescura.yml    pedia 8 al dia   corrio 2
    trigger.yml     pedia 144        corrio ~19

Eso dejaba a los vigilantes dependiendo de la misma cola que vigilan, que era el
punto debil estructural del sistema entero: `frescura` tardaba trece horas en
detectar una pagina congelada, no tres.

`workflow_dispatch` no pasa por esa cola. Asi que el repositorio pide **un**
turno de cron y desde ahi salen los demas.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

WORKFLOWS = Path(__file__).parent.parent.parent / ".github" / "workflows"
TRIGGER = (WORKFLOWS / "trigger.yml").read_text(encoding="utf-8")

#: `workflow -> cada cuantas horas debe despacharse`, leido del propio paso.
DEPENDIENTES = ("frescura.yml", "incendios.yml")


def test_el_vigia_despacha_a_los_que_dependen_del_reloj() -> None:
    """Si no, siguen compitiendo por turnos que no hay."""
    assert "despachar_si_toca" in TRIGGER

    for workflow in DEPENDIENTES:
        assert f"despachar_si_toca {workflow}" in TRIGGER, f"{workflow} sigue solo con su cron"


@pytest.mark.parametrize("workflow", DEPENDIENTES)
def test_el_despachado_conserva_su_propio_cron(workflow: str) -> None:
    """Respaldo: si el paso del vigia deja de correr, siguen teniendo una via.

    Mala —es la cola estrangulada— pero una via. Quitarles el `schedule` los
    dejaria dependiendo por completo de un solo workflow.
    """
    disparadores = yaml.safe_load((WORKFLOWS / workflow).read_text(encoding="utf-8"))[True]

    assert "schedule" in disparadores, f"{workflow} se quedo sin respaldo propio"
    assert "workflow_dispatch" in disparadores, f"{workflow} no se puede despachar"


def test_no_se_despacha_a_ciegas() -> None:
    """Sin comprobar cuanto hace que corrio, un turno concedido a los dos
    relojes duplicaria la corrida.

    Y en `incendios.yml` eso son diecinueve activos bajados dos veces.
    """
    assert "gh run list --workflow=" in TRIGGER
    assert 'edad_h" -lt "$cada_horas' in TRIGGER


def test_un_despacho_fallido_no_tumba_al_vigia() -> None:
    """Cuando llega aqui, el latido ya esta commiteado y empujado.

    Perder eso por no poder lanzar un workflow secundario seria cambiar un
    problema pequeno por uno grande.
    """
    paso = TRIGGER[TRIGGER.index("despachar_si_toca() {") :]

    assert '|| echo "::warning::no se pudo despachar' in paso


def test_el_reloj_corre_aunque_el_vigia_no_publique() -> None:
    """El paso de publicar sale pronto cuando el latido es reciente.

    Si el despacho colgara de el, `frescura` e `incendios` solo saldrian en las
    corridas que ademas commitean — que son una fraccion.
    """
    bloque = TRIGGER[TRIGGER.index("Despachar los workflows que dependen del reloj") :][:300]

    assert "if: always()" in bloque


def test_las_cadencias_declaradas_coinciden_con_los_crones() -> None:
    """Despachar `frescura` cada seis horas cuando su cron dice tres seria
    empeorarla en silencio."""
    for workflow, esperado in (("frescura.yml", 3), ("incendios.yml", 6)):
        cron = yaml.safe_load((WORKFLOWS / workflow).read_text(encoding="utf-8"))[True]
        declarado = int(re.search(r"\*/(\d+)", cron["schedule"][0]["cron"]).group(1))
        despachado = int(
            re.search(rf"despachar_si_toca {re.escape(workflow)} (\d+)", TRIGGER).group(1)
        )

        assert despachado == declarado == esperado, (
            f"{workflow}: cron cada {declarado} h, despachado cada {despachado} h"
        )
