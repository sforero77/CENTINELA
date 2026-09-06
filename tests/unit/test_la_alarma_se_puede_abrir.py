"""Una alarma que no se puede abrir no es una alarma.

`gh issue create --label X` **aborta** si `X` no existe en el repositorio. No
avisa, no crea el issue sin etiqueta, no degrada: sale con error y no queda
nada. Y como el paso que la abre corre siempre bajo `if: failure()`, el fallo
del `gh` se suma al fallo que se queria denunciar y el resultado es un workflow
rojo sin ni una sola pista de por que.

`contract_drift.yml` pedia `contrato,automatico` y `simulacro.yml` pedia
`operacion,automatico`. Ninguna de las tres etiquetas existia, y ningun workflow
las creaba: las dos alarmas nocturnas estaban muertas desde que se escribieron.
`frescura.yml` si tenia el patron completo —crear la etiqueta antes, y un camino
de respaldo sin etiquetas por si `gh label` tampoco puede— y de ahi sale este
guardia.

Va contra **todo el catalogo** y no contra los dos ficheros del hallazgo. Es la
leccion que este repositorio ya aprendio con el cero legitimo y con la
republicacion del visor: el tercer workflow que abra un issue lo va a olvidar
igual, y para entonces nadie se acordara de esta pagina.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

WORKFLOWS = Path(__file__).parent.parent.parent / ".github" / "workflows"

#: `gh issue create ... --label "a,b"` — se queda con lo de dentro de las comillas.
PIDE_ETIQUETAS = re.compile(r"--label\s+\"([^\"]+)\"")

#: `gh label create nombre ...` — el nombre es el primer argumento.
CREA_ETIQUETA = re.compile(r"gh label create\s+([A-Za-z0-9_.\-]+)")


def _lineas_de_comando(ruta: Path) -> list[str]:
    """El cuerpo de los pasos, sin los comentarios.

    UN GUARDIA QUE LEE PROSA DA FALSOS POSITIVOS Y FALSOS NEGATIVOS.

    Ya paso cinco veces en esta auditoria: el comentario que explica el arreglo
    contiene el texto que el guardia busca, asi que el guardia aprueba un
    fichero por su documentacion. Aqui el riesgo es el simetrico —un comentario
    que menciona `--label` haria fallar a un workflow que no abre issues— y se
    corta igual: solo se miran lineas que no empiezan por `#`.
    """
    return [
        linea
        for linea in ruta.read_text(encoding="utf-8").splitlines()
        if not linea.lstrip().startswith("#")
    ]


def _workflows_que_etiquetan() -> list[Path]:
    return sorted(
        p
        for p in WORKFLOWS.glob("*.yml")
        if PIDE_ETIQUETAS.search("\n".join(_lineas_de_comando(p)))
    )


def test_hay_workflows_que_etiquetan() -> None:
    """Si un dia no queda ninguno, esta pagina entera pasaria en vacio."""
    assert _workflows_que_etiquetan(), "ningun workflow pide etiquetas: revisar el guardia"


@pytest.mark.parametrize("ruta", _workflows_que_etiquetan(), ids=lambda p: p.name)
def test_las_etiquetas_que_se_piden_se_crean_antes(ruta: Path) -> None:
    """Nadie puede pedir una etiqueta que este repositorio no crea."""
    lineas = _lineas_de_comando(ruta)
    cuerpo = "\n".join(lineas)

    pedidas = {
        etiqueta.strip()
        for grupo in PIDE_ETIQUETAS.findall(cuerpo)
        for etiqueta in grupo.split(",")
        if etiqueta.strip()
    }
    creadas = set(CREA_ETIQUETA.findall(cuerpo))

    faltan = pedidas - creadas
    assert not faltan, (
        f"{ruta.name} pide {sorted(faltan)} y no las crea. `gh issue create --label` "
        f"aborta con una etiqueta inexistente, asi que la alarma no llega a abrirse: "
        f"anadir `gh label create <nombre> --color ... --force >/dev/null 2>&1 || true` "
        f"antes, como hace frescura.yml."
    )


@pytest.mark.parametrize("ruta", _workflows_que_etiquetan(), ids=lambda p: p.name)
def test_la_alarma_tiene_camino_sin_etiquetas(ruta: Path) -> None:
    """Y si `gh label` tampoco puede, el issue se abre igual.

    Crear etiquetas necesita permiso de escritura sobre issues y puede chocar
    con la cuota de la API. Ese fallo no puede costar la alarma entera: mas vale
    un issue sin clasificar que ninguno. `|| gh issue create` sin `--label` es
    el respaldo, y va en la misma linea logica que la creacion.
    """
    cuerpo = "\n".join(_lineas_de_comando(ruta))
    # Se normalizan las continuaciones de linea para poder mirar el comando
    # entero de una pieza.
    plano = cuerpo.replace("\\\n", " ")
    for linea in plano.splitlines():
        if "--label" not in linea or "gh issue create" not in linea:
            continue
        assert "|| gh issue create" in linea, (
            f"{ruta.name}: `gh issue create --label` sin camino de respaldo. Si la "
            f"etiqueta no se pudo crear, la alarma desaparece entera en vez de "
            f"abrirse sin clasificar."
        )
        # Y el respaldo tiene que ser de verdad: sin `--label` detras, repite el
        # mismo comando que acaba de fallar.
        respaldo = linea.split("|| gh issue create", 1)[1]
        assert "--label" not in respaldo, (
            f"{ruta.name}: el camino de respaldo vuelve a pedir etiquetas, asi que "
            f"falla por lo mismo que el intento principal."
        )
