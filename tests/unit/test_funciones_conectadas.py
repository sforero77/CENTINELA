"""La guardia contra el fallo que este proyecto repite: escribir sin conectar.

Cinco de los nueve hallazgos de la auditoria del 25-ago-2026 son **la misma
causa raiz** apareciendo en cinco sitios:

* `compute_preliminary` — escrita, comentada y probada. Sin llamador. El
  sistema callaba durante las primeras horas, las unicas en que sirve.
* `set_epicenter` en `static_map` — sin llamador. Seis PNG publicados con la
  estrella del epicentro clavada en (0, 0).
* Tres capas del activo — agregadas a tablas que nadie leia. El siguiente build
  trimestral habria publicado cero edificaciones y cero km de via.
* `check_quality` — los asserts de §6.4 de P2, en una funcion sin llamador,
  invocada desde otra funcion sin llamador cuya docstring afirmaba que si.
* `assert_publishable_in_report` — la guarda de licencias del reporte,
  comprobada solo de rebote dentro de un f-string.

Todas estaban **probadas**. Ese es el detalle que importa: la cobertura las
marcaba en verde, porque una prueba llama a la funcion y eso no dice nada sobre
si la llama alguien mas. Contra ese punto ciego no sirve otra prueba de la
funcion; sirve esta, que mira el grafo de llamadas.

Arreglarlos uno a uno sin nombrar el patron habria dejado el sexto para la
proxima auditoria.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

RAIZ = Path(__file__).parent.parent.parent
PIPELINES = RAIZ / "pipelines"

#: Donde se busca a quien llama. Los workflows y `pyproject.toml` cuentan: un
#: `entry_points` o una linea de `run:` son llamadores tan reales como un
#: `import`, y de hecho son los unicos que tienen varias funciones de aqui.
FUENTES_DE_LLAMADA: tuple[tuple[str, str], ...] = (
    ("pipelines", "*.py"),
    ("scripts", "*.py"),
    (".github/workflows", "*.yml"),
    (".", "pyproject.toml"),
)

#: Funciones publicas que **a proposito** no tienen llamador en produccion, con
#: el motivo. Anadir una entrada aqui es una decision, no un tramite: significa
#: afirmar que este codigo no esta en ningun camino y que aun asi se conserva.
#:
#: Lo que NO vale como motivo: "esta probada", "la usaremos pronto", "es API
#: publica". Las tres describen justo el codigo que hay que borrar o cablear.
SIN_LLAMADOR_JUSTIFICADO: dict[str, str] = {
    "prorate": (
        "Mitad del reparto fraccionario que el modulo documenta y no toma: con "
        "el reparto por contencion, `frac_area` vale siempre 1,0. Se conserva "
        "como puerta de entrada al reparto exacto si alguna vez hace falta."
    ),
    "validate_fractions": (
        "Igual que `prorate`. El invariante equivalente lo verifica "
        "`SQL_ASSERT_SIN_DUPLICADOS` en SQL, sobre la tabla entera."
    ),
    "gate_publication": (
        "Contrato de la brigada de imagen (P4), que es Fase 2. El modulo entero "
        "es contrato todavia sin pipeline detras."
    ),
    "global_url": (
        "Mosaico global de GHSL, 5,25 GB. Su propia docstring dice que hay que "
        "preferir `tiles_for_bbox`, que baja 93 MB para Colombia. Se conserva "
        "como escape para un pais cuya caja acabara cubriendo casi todo."
    ),
}


def _funciones_publicas() -> dict[str, Path]:
    """Funciones publicas de modulo definidas en `pipelines/`."""
    encontradas: dict[str, Path] = {}
    for ruta in sorted(PIPELINES.rglob("*.py")):
        arbol = ast.parse(ruta.read_text(encoding="utf-8"))
        for nodo in arbol.body:  # solo nivel de modulo: los metodos no cuentan
            if isinstance(nodo, ast.FunctionDef) and not nodo.name.startswith("_"):
                encontradas[nodo.name] = ruta.relative_to(RAIZ)
    return encontradas


def _identificadores(fuente: str) -> str:
    """Los nombres que aparecen en el **codigo**, sin docstrings ni comentarios.

    Una mencion en prosa no es una llamada. Sin este filtro, dos funciones
    muertas que se citen entre si en sus docstrings se cubren la una a la otra
    y desaparecen del radar — que es exactamente el escondite que esta prueba
    existe para iluminar.
    """
    import io
    import tokenize

    nombres: list[str] = []
    try:
        for token in tokenize.generate_tokens(io.StringIO(fuente).readline):
            if token.type == tokenize.NAME:
                nombres.append(token.string)
    except (tokenize.TokenError, IndentationError, SyntaxError):  # pragma: no cover
        return fuente
    return " ".join(nombres)


def _texto_de_produccion() -> str:
    """Todo el codigo y la configuracion que podria llamar a algo."""
    partes: list[str] = []
    for directorio, patron in FUENTES_DE_LLAMADA:
        base = RAIZ / directorio
        rutas = sorted(set(base.glob(patron)) | set(base.rglob(patron)))
        for ruta in rutas:
            texto = ruta.read_text(encoding="utf-8")
            # Los `.yml` y el `.toml` van enteros: ahi una cadena **si** es una
            # invocacion (`run: uv run centinela ...`, `entry_points`).
            partes.append(_identificadores(texto) if ruta.suffix == ".py" else texto)
    return "\n".join(partes)


def _sin_llamador() -> dict[str, Path]:
    """Funciones publicas que solo aparecen en su propia definicion."""
    produccion = _texto_de_produccion()
    huerfanas: dict[str, Path] = {}
    for nombre, ruta in _funciones_publicas().items():
        apariciones = len(re.findall(rf"\b{re.escape(nombre)}\b", produccion))
        if apariciones <= 1:  # la definicion se cuenta a si misma
            huerfanas[nombre] = ruta
    return huerfanas


def test_ninguna_funcion_publica_se_queda_sin_llamador() -> None:
    """Una funcion escrita no es una funcion conectada.

    Si esta prueba falla con un nombre nuevo, hay dos salidas honestas —
    **cablearla** o **borrarla**— y una tercera que hay que argumentar:
    anadirla a `SIN_LLAMADOR_JUSTIFICADO` explicando por que se conserva codigo
    que no esta en ningun camino.

    Dejarla como esta no es una salida. Es como se publicaron seis mapas
    vacios.
    """
    sin_justificar = {
        nombre: str(ruta)
        for nombre, ruta in _sin_llamador().items()
        if nombre not in SIN_LLAMADOR_JUSTIFICADO
    }
    assert sin_justificar == {}, (
        f"Funciones publicas sin llamador en produccion: {sin_justificar}. "
        f"Cablealas, borralas, o declaralas en SIN_LLAMADOR_JUSTIFICADO con su motivo."
    )


def test_la_lista_de_excepciones_no_acumula_fantasmas() -> None:
    """Una excepcion que sobra convierte la lista en un cajon de sastre.

    Si una funcion justificada se cablea o se borra, su entrada tiene que irse
    con ella: si no, la proxima que use ese nombre entra exenta sin que nadie
    lo decida.
    """
    huerfanas = set(_sin_llamador())
    sobran = sorted(set(SIN_LLAMADOR_JUSTIFICADO) - huerfanas)

    assert sobran == [], (
        f"Estas ya tienen llamador (o no existen) y sobran de SIN_LLAMADOR_JUSTIFICADO: {sobran}"
    )


def test_cada_excepcion_explica_por_que() -> None:
    """Un motivo de tres palabras es un motivo que nadie reviso."""
    flojas = [n for n, motivo in SIN_LLAMADOR_JUSTIFICADO.items() if len(motivo.split()) < 8]

    assert flojas == [], f"Motivos demasiado escuetos para poder discutirse: {flojas}"
