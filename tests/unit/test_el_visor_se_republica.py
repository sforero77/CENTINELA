"""Quien commitea lo que el visor lee, tiene que republicar el visor.

**Un push hecho con `GITHUB_TOKEN` no dispara otros workflows.** Es una regla de
GitHub contra los bucles infinitos, y rompia la cadena sin que nada fallara:
`site.yml` escucha `push` sobre `site/**` y `reports/**`, los dos workflows que
escriben ahi empujan con ese token, y la pagina no se enteraba.

Se descubrio el 26-ago-2026 tirando del hilo de por que un M4,9 sentido en
Colombia no aparecia en el visor. `/status` en vivo llevaba diecisiete horas
congelado —ultimo latido 02:53, con siete commits posteriores ya en el
repositorio— y nadie lo habia notado.

Lo caro no era el latido. Era que **un reporte de un sismo real se habria
publicado en el repositorio sin llegar nunca a la pagina**: P2 commitea
`reports/` con el mismo token. No se habia visto porque hasta ese dia ningun
sismo habia llegado a reporte por esa via — los veintiuno del catalogo se
reconstruyeron a mano.

Es la misma forma que el resto de esta auditoria: los dos workflows en verde, el
artefacto correcto en su sitio, y el fallo viviendo en el hueco entre ellos. Por
eso esto es una prueba y no un comentario: el tercer workflow que commitee en
`site/` lo va a olvidar igual.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

WORKFLOWS = Path(__file__).parent.parent.parent / ".github" / "workflows"

#: El que publica la pagina: se dispara a si mismo, no puede exigirselo.
PUBLICADOR = "site.yml"


def _workflows() -> list[Path]:
    return sorted(p for p in WORKFLOWS.glob("*.yml") if p.name != PUBLICADOR)


def _texto(ruta: Path) -> str:
    return ruta.read_text(encoding="utf-8")


#: El comando que republica el visor, tal como se escribe en un paso.
REPUBLICAR = "gh workflow run site.yml"


def republica(ruta: Path) -> bool:
    """¿Este workflow *ejecuta* el comando, o solo lo menciona?

    La primera version emparejaba texto plano y dio un falso positivo el mismo
    dia: `frescura.yml` cita el comando **en el cuerpo del issue**, como la
    reparacion que debe intentar quien lea la alarma. Un guardia que confunde la
    prosa con el codigo exige permisos a quien no los necesita, y de paso ensena
    a desactivarlo.

    Se pide que sea el comando entero de una linea —con o sin el `run:` del
    paso delante— y no una frase que lo nombra entre comillas.
    """
    return any(
        linea.strip().removeprefix("run:").strip() == REPUBLICAR
        for linea in _texto(ruta).splitlines()
    )


def rutas_del_visor() -> tuple[str, ...]:
    """Los directorios cuyo cambio republica la pagina, **leidos de site.yml**.

    Escritas a mano se quedan viejas: la primera version de esta prueba decia
    `("site/", "reports/")` y no sabia de `data/manifests/`, que `site.yml`
    vigila desde que la cobertura regional se recalcula al publicar. Un guardia
    con una lista desactualizada da un verde peor que no tener guardia.
    """
    # `yaml` convierte la clave `on:` en el booleano `True`. Es la rareza mas
    # conocida de YAML 1.1 y aqui no hay forma de evitarla.
    disparadores = yaml.safe_load(_texto(WORKFLOWS / PUBLICADOR))[True]
    rutas = disparadores["push"]["paths"]
    return tuple(
        r.split("**")[0]
        for r in rutas
        # El workflow se lista a si mismo para redesplegarse al tocarlo; eso no
        # es contenido que nadie mas commitee.
        if not r.startswith(".github/")
    )


RUTAS_DEL_VISOR = rutas_del_visor()


def test_las_rutas_salen_de_site_yml_y_son_las_que_creemos() -> None:
    """Que la derivacion funcione, y que no se haya quedado vacia en silencio.

    Si `rutas_del_visor()` devolviera `()` —por un cambio de forma del YAML—
    todas las pruebas de abajo se saltarian y el guardia desapareceria sin que
    nada se pusiera rojo.
    """
    assert set(RUTAS_DEL_VISOR) >= {"site/", "reports/"}, (
        f"site.yml ya no republica ante site/ o reports/: {RUTAS_DEL_VISOR}"
    )


@pytest.mark.parametrize("workflow", _workflows(), ids=lambda p: p.name)
def test_quien_commitea_para_el_visor_lo_republica(workflow: Path) -> None:
    """La regla, aplicada a cada workflow que empuja algo que la pagina lee."""
    texto = _texto(workflow)

    escribe = [r for r in RUTAS_DEL_VISOR if f"git add {r}" in texto or f" {r}" in texto]
    if "git push" not in texto or not escribe:
        pytest.skip("no publica nada que el visor lea")

    assert republica(workflow), (
        f"{workflow.name} commitea {escribe} y empuja con GITHUB_TOKEN, que **no** "
        "dispara site.yml. Lo que publique no llegara nunca a la pagina. "
        'Anade un paso "Republicar el visor" con `gh workflow run site.yml`.'
    )


@pytest.mark.parametrize("workflow", _workflows(), ids=lambda p: p.name)
def test_republicar_necesita_permiso_para_hacerlo(workflow: Path) -> None:
    """`gh workflow run` sin `actions: write` falla en tiempo de ejecucion.

    Y falla **despues** del push, con el artefacto ya publicado: el workflow
    sale en rojo aunque su trabajo salio bien, y quien lo mire buscara el error
    en el sitio equivocado.
    """
    if not republica(workflow):
        pytest.skip("no republica el visor")
    texto = _texto(workflow)

    assert "actions: write" in texto, (
        f"{workflow.name} republica el visor sin `permissions: actions: write`"
    )


@pytest.mark.parametrize("workflow", _workflows(), ids=lambda p: p.name)
def test_solo_se_republica_si_hubo_push(workflow: Path) -> None:
    """Republicar sin haber empujado gasta una corrida en no cambiar nada.

    Y peor: enmascara el caso que importa. Si la pagina se reconstruye siempre,
    que se reconstruya deja de ser senal de que algo se publico.
    """
    if not republica(workflow):
        pytest.skip("no republica el visor")
    texto = _texto(workflow)

    assert "outputs.publicado == 'true'" in texto, (
        f"{workflow.name} republica el visor sin condicionarlo a que el push ocurriera"
    )


def test_mencionar_el_comando_no_es_ejecutarlo() -> None:
    """El falso positivo que este guardia tuvo el primer dia.

    `frescura.yml` cita `gh workflow run site.yml` en el cuerpo del issue, como
    la reparacion que debe intentar quien lea la alarma. No lo ejecuta, no
    commitea nada, y no necesita `actions: write`.
    """
    frescura = WORKFLOWS / "frescura.yml"

    assert REPUBLICAR in _texto(frescura), "ya no explica como repararlo"
    assert not republica(frescura), "el guardia volvio a confundir la prosa con el codigo"


def test_la_vista_previa_apunta_al_ultimo_evento() -> None:
    """`og:image` iba clavada en el HTML a un evento concreto.

    Funcionaba hoy y se rompia en silencio el dia que ese reporte se retirara —
    y un tablero de crisis compartido por WhatsApp enseñaria siempre el sismo de
    agosto de 2026, tuviera lo que tuviera delante. El despliegue es el unico
    sitio que sabe que se publica, asi que la reescritura vive ahi.
    """
    texto = (WORKFLOWS / "site.yml").read_text(encoding="utf-8")

    assert "og:image" in texto, "el despliegue ya no actualiza la vista previa"
    assert "reports/index.json" in texto, (
        "la vista previa no sale del indice de reportes, que es quien sabe cual es el ultimo"
    )
    # Y el HTML conserva un valor fijo de respaldo para quien sirva site/ a secas.
    html = (WORKFLOWS.parent.parent / "site" / "index.html").read_text(encoding="utf-8")
    assert 'property="og:image" content="https://' in html, (
        "el HTML se quedo sin og:image de respaldo"
    )


# --- La otra mitad del mismo hueco -------------------------------------------
#
# El push del bot no dispara `site.yml`, y por eso existe todo lo de arriba.
# Tampoco dispara `ci.yml`, y eso no se habia mirado: la suite no corre nunca
# sobre lo que el bot publica. Medido el 4-sep-2026 sobre `gh run list`: el bot
# commiteo a las 09:54 y no hubo una sola corrida de CI; las diez ultimas son
# todas de un PR humano.
#
# Importa porque parte de la suite vigila **artefactos publicados**, no codigo:
# `test_lo_publicado_se_ve.py` mide los PNG de `reports/` pixel a pixel, y
# `test_ningun_evento_se_queda_sin_reporte.py` mira el hueco entre lo detectado
# y lo publicado. Los dos son guardias sobre lo que este camino escribe.

#: El comando que dispara la suite sobre lo recien publicado.
COMPROBAR = "gh workflow run ci.yml"

#: Lo que ningun otro guardia mira: los reportes. Es el artefacto que la suite
#: mide por su contenido y no por el codigo que lo produjo.
RUTA_DE_LOS_REPORTES = "reports/"


def comprueba(ruta: Path) -> bool:
    """Como `republica`, con el mismo cuidado de no confundir prosa con codigo."""
    return any(
        linea.strip() in {COMPROBAR, f"run: {COMPROBAR}"} for linea in _texto(ruta).splitlines()
    )


def test_solo_un_workflow_escribe_reportes() -> None:
    """Si aparece un segundo, la regla de abajo tiene que alcanzarle.

    La prueba siguiente esta escrita contra `impact.yml` a proposito —no es
    parametrica sobre todos— porque la regla NO puede ser "todo el que commitea
    dispara CI": `trigger.yml` late cada cinco minutos y eso serian casi
    trescientas corridas al dia. El corte esta en quien escribe `reports/`, y
    hoy es uno solo. Esto avisa el dia que deje de serlo.
    """
    escriben = sorted(
        p.name
        for p in WORKFLOWS.glob("*.yml")
        if "git add" in _texto(p) and RUTA_DE_LOS_REPORTES in _texto(p).split("git add", 1)[1][:80]
    )

    assert escriben == ["impact.yml"], (
        f"estos workflows commitean reports/: {escriben}. La regla de "
        "`test_quien_publica_un_reporte_dispara_la_suite` solo cubre impact.yml; "
        "amplíala o el nuevo publicara sin que la suite lo mire."
    )


def test_quien_publica_un_reporte_dispara_la_suite() -> None:
    """Publicar sin que nada lo compruebe es publicar a ciegas.

    Va **despues** del push y no antes: publicar es el camino critico de un
    sismo real y no puede depender de una suite. La regla de P3 es que un fallo
    de derivado no tumba el reporte, que ya esta en disco. Esto no bloquea,
    delata.
    """
    impacto = WORKFLOWS / "impact.yml"

    assert comprueba(impacto), (
        "impact.yml commitea reports/ y empuja con GITHUB_TOKEN, que **no** "
        "dispara ci.yml. La suite no correra sobre el reporte publicado, y "
        "parte de ella —los PNG, el hueco entre detectado y publicado— solo "
        "sabe mirar lo publicado. Anade `gh workflow run ci.yml` tras el push."
    )


def test_la_suite_se_deja_disparar() -> None:
    """`gh workflow run ci.yml` sobre un workflow sin `workflow_dispatch` falla.

    Y falla en el paso de despues de publicar, con el reporte ya en su sitio:
    rojo donde el trabajo salio bien.
    """
    import yaml as _yaml

    ci = _yaml.safe_load(_texto(WORKFLOWS / "ci.yml"))
    # `on` en YAML 1.1 se interpreta como el booleano True.
    disparadores = ci.get("on", ci.get(True, {}))

    assert "workflow_dispatch" in disparadores, (
        "ci.yml perdio `workflow_dispatch` e impact.yml no puede dispararlo"
    )


def test_no_se_comprueba_si_no_hubo_push() -> None:
    """Una corrida de CI por un despacho que no publico nada no mira nada nuevo."""
    texto = _texto(WORKFLOWS / "impact.yml")
    bloque = texto[texto.index("Comprobar lo que se acaba de publicar") :]

    assert "steps.publicar.outputs.publicado == 'true'" in bloque[:400], (
        "el disparo de ci.yml no esta condicionado a haber publicado"
    )
