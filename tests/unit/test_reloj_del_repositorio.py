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
DEPENDIENTES = ("frescura.yml", "incendios.yml", "repaso.yml")

#: Cadencia que cada uno declara, en horas.
CADENCIAS = {"frescura.yml": 3, "incendios.yml": 6, "repaso.yml": 24}


def _horas_del_cron(expresion: str) -> int | None:
    """Cada cuantas horas corre un cron. Entiende `*/N` y la hora fija.

    `repaso.yml` corre una vez al dia y su cron es `37 5 * * *`: no hay `*/N`
    que leer, y la cadencia son 24 h. Sin esto, anadir un workflow diario
    obligaria a escribir `*/24` —que en el campo de horas significa "la hora
    cero" y se lee como un error— solo para que la prueba encaje.
    """
    campos = expresion.split()
    if len(campos) != 5:
        return None
    hora = campos[1]
    if (cada := re.match(r"^\*/(\d+)$", hora)) is not None:
        return int(cada.group(1))
    if re.match(r"^\d+$", hora) and campos[2] == "*" and campos[4] == "*":
        return 24
    return None


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
    for workflow, esperado in CADENCIAS.items():
        cron = yaml.safe_load((WORKFLOWS / workflow).read_text(encoding="utf-8"))[True]
        # Los dos pueden no encajar, y ese caso no es un detalle de tipos: si el
        # cron deja de declarar una cadencia legible o el trigger deja de nombrar
        # el workflow, esta prueba tiene que decirlo con esas palabras en vez de
        # reventar con un AttributeError sobre None.
        declarado_o_no = _horas_del_cron(cron["schedule"][0]["cron"])
        assert declarado_o_no is not None, f"{workflow}: su cron ya no declara una cadencia legible"
        en_trigger = re.search(rf"despachar_si_toca {re.escape(workflow)} (\d+)", TRIGGER)
        assert en_trigger is not None, f"{workflow}: el reloj ya no lo despacha"

        declarado = declarado_o_no
        despachado = int(en_trigger.group(1))

        assert despachado == declarado == esperado, (
            f"{workflow}: cron cada {declarado} h, despachado cada {despachado} h"
        )


def test_el_reloj_despacha_antes_de_publicar() -> None:
    """El orden no es cosmetico: costo el primer fallo de `frescura`.

    Despachando al final, el vigia commiteaba, republicaba el visor, y
    `frescura` arrancaba quince segundos despues. El despliegue de Pages tarda
    unos veintiseis, asi que lo reviso **a medias**: reporto 7,4 h de desfase
    que eran ciertas en ese instante y falsas medio minuto despues.

    Un vigilante que da falsos positivos por diseno se aprende a ignorar, y
    entonces no avisa el dia que importa.

    Aqui mira el estado anterior, que esta asentado. Lo que acaba de commitearse
    lo vera en la pasada siguiente, que es cuando ya es comprobable.
    """
    despacho = TRIGGER.index("- name: Despachar los workflows que dependen del reloj")
    publicacion = TRIGGER.index("- name: Publicar estado y latido")

    assert despacho < publicacion, "el reloj volvio a despachar dentro de la ventana de despliegue"


def test_el_vigia_acepta_un_disparo_externo() -> None:
    """El cron interno no puede ganar la cola que comparte, y esta medido.

    Entre el 25 y el 30-ago-2026, con 23 latidos: p50 157 min entre revisiones,
    p90 462 y peor 766 (12,8 h). El cron pide 48 turnos al dia y consigue entre
    dos y cuatro. Con el objetivo en 60 min p50 desde que hay ShakeMap, la
    deteccion sola se come el presupuesto entero.

    `repository_dispatch` deja que un cron externo dispare el vigia sin pasar por
    esa cola. Es el upgrade path que este fichero llevaba documentado desde el
    principio, ahora con las cifras que pedia antes de montarlo.
    """
    disparadores = yaml.safe_load(TRIGGER)
    # PyYAML lee la clave `on:` como el booleano `True`.
    sobre = disparadores.get(True) or disparadores.get("on")

    assert "repository_dispatch" in sobre, (
        "el vigia sigue atado a la cola de cron que no puede ganar"
    )
    assert "vigilar" in sobre["repository_dispatch"]["types"]

    # Y el cron interno SE QUEDA: si el servicio externo cae, esto sigue
    # corriendo mal pero corriendo. Un unico punto de fallo fuera del
    # repositorio seria peor que la cola.
    assert "schedule" in sobre, (
        "se quito el cron interno: sin el, si el disparo externo cae no queda nada"
    )


def test_el_disparo_externo_lleva_instrucciones() -> None:
    """Un trigger declarado y sin nadie que lo llame no arregla nada.

    Lo que falta —el token y el servicio de cron— no se puede hacer desde el
    repositorio, asi que tiene que quedar escrito donde se encuentra: al lado
    del trigger, no en un chat.
    """
    assert "/dispatches" in TRIGGER, "falta el endpoint que hay que llamar"
    assert '"event_type": "vigilar"' in TRIGGER, "falta el cuerpo de la llamada"
    assert "healthchecks.io" in TRIGGER, "falta decir que pasa si el disparador externo se muere"
