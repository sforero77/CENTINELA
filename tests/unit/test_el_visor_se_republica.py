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
