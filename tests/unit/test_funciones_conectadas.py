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
import collections
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
#: Las claves llevan el modulo (`paquete.modulo.funcion`) desde que el guardia
#: dejo de indexar por nombre suelto: dos funciones homonimas en modulos
#: distintos se cubrian la una a la otra.
SIN_LLAMADOR_JUSTIFICADO: dict[str, str] = {
    "p0_exposure.crosswalk.prorate": (
        "Mitad del reparto fraccionario que el modulo documenta y no toma: con "
        "el reparto por contencion, `frac_area` vale siempre 1,0. Se conserva "
        "como puerta de entrada al reparto exacto si alguna vez hace falta."
    ),
    "p0_exposure.crosswalk.validate_fractions": (
        "Igual que `prorate`. El invariante equivalente lo verifica "
        "`SQL_ASSERT_SIN_DUPLICADOS` en SQL, sobre la tabla entera."
    ),
    "p4_brigada.protocol.gate_publication": (
        "Contrato de la brigada de imagen (P4), que es Fase 2. El modulo entero "
        "es contrato todavia sin pipeline detras."
    ),
    "common.hdx.limpiar_cache_hdx": (
        "Vacia el cache de `package_show` de la corrida. En produccion no hace "
        "falta —un build es un proceso y un dataset no cambia de licencia a "
        "mitad—, pero la suite son dos mil pruebas en el mismo proceso y sin "
        "esto la primera que resuelve un dataset decide lo que ven las demas. "
        "Lo llama la fixture autouse `_cache_de_hdx_limpio` de tests/conftest.py."
    ),
    "p0_exposure.sources.ghsl.global_url": (
        "Mosaico global de GHSL, 5,25 GB. Su propia docstring dice que hay que "
        "preferir `tiles_for_bbox`, que baja 93 MB para Colombia. Se conserva "
        "como escape para un pais cuya caja acabara cubriendo casi todo."
    ),
}


def _funciones_publicas() -> dict[str, Path]:
    """Funciones publicas de modulo definidas en `pipelines/`.

    LA CLAVE LLEVA EL MODULO, Y NO LO LLEVABA.

    `encontradas[nodo.name] = ruta` sobrescribia, asi que de dos funciones con
    el mismo nombre en modulos distintos solo quedaba la ultima, y una llamada a
    cualquiera de las dos satisfacia a las dos. Tres nombres estaban duplicados
    —`feed_url` en p1_trigger/feed y p5_incendios/firms, `leer` en
    p1_trigger/observados y p5_incendios/incendios, `tiles_for_bbox` en
    sources/ghsl y sources/worldcover— y el guardia escondia un huerfano real:
    `p5_incendios.incendios.leer` no la llamaba nadie en produccion, solo dos
    pruebas que la ejercitaban a ella misma.

    Un guardia de codigo muerto que se deja engañar por un nombre repetido es
    justo el escondite que existe para iluminar.
    """
    encontradas: dict[str, Path] = {}
    for ruta in sorted(PIPELINES.rglob("*.py")):
        arbol = ast.parse(ruta.read_text(encoding="utf-8"))
        modulo = ruta.relative_to(PIPELINES).with_suffix("").as_posix().replace("/", ".")
        for nodo in arbol.body:  # solo nivel de modulo: los metodos no cuentan
            if isinstance(nodo, ast.FunctionDef) and not nodo.name.startswith("_"):
                encontradas[f"{modulo}.{nodo.name}"] = ruta.relative_to(RAIZ)
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
    """Funciones publicas que solo aparecen en su propia definicion.

    Para un nombre unico basta contar apariciones. Para uno **repetido** no: dos
    definiciones dejan dos apariciones aunque solo se llame a una, asi que se
    exige ademas que el modulo que la define este alcanzado —importado o
    nombrado— en produccion. Sin eso, la duplicada muerta viaja gratis a costa
    de la viva.
    """
    produccion = _texto_de_produccion()
    calificadas = _funciones_publicas()
    definiciones = collections.Counter(clave.rsplit(".", 1)[1] for clave in calificadas)

    huerfanas: dict[str, Path] = {}
    for clave, ruta in calificadas.items():
        modulo, nombre = clave.rsplit(".", 1)
        apariciones = len(re.findall(rf"\b{re.escape(nombre)}\b", produccion))
        # Cada definicion se cuenta a si misma.
        if apariciones <= definiciones[nombre]:
            huerfanas[clave] = ruta
            continue
        if definiciones[nombre] > 1:
            hoja = modulo.rsplit(".", 1)[-1]
            # `from .firms import feed_url`, `ghsl.tiles_for_bbox(...)`: el
            # modulo tiene que aparecer al lado del nombre en alguna parte.
            juntos = re.search(
                rf"\b{re.escape(hoja)}\b[^\n]{{0,120}}\b{re.escape(nombre)}\b"
                rf"|\b{re.escape(nombre)}\b[^\n]{{0,120}}\b{re.escape(hoja)}\b",
                produccion,
            )
            if not juntos:
                huerfanas[clave] = ruta
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


def test_dos_funciones_homonimas_se_cuentan_por_separado() -> None:
    """La propiedad que hacia inutil al guardia con los nombres repetidos.

    Con la clave sin modulo, `encontradas[nodo.name] = ruta` sobrescribia: de
    `feed_url` solo sobrevivia una, y una llamada a cualquiera de las dos
    satisfacia a las dos. Escondio un huerfano real —`incendios.leer`, con dos
    pruebas que solo la ejercitaban a ella— hasta la auditoria del 5-sep.
    """
    calificadas = _funciones_publicas()
    por_nombre = collections.Counter(clave.rsplit(".", 1)[1] for clave in calificadas)
    repetidos = {n for n, veces in por_nombre.items() if veces > 1}

    assert repetidos, (
        "ya no hay nombres repetidos en pipelines/; si es a proposito, esta "
        "prueba pierde su sujeto y se puede quitar"
    )
    for nombre in repetidos:
        claves = [c for c in calificadas if c.rsplit(".", 1)[1] == nombre]
        assert len(claves) == por_nombre[nombre], f"se perdio una definicion de {nombre}"
        assert len({calificadas[c] for c in claves}) == len(claves), (
            f"dos definiciones de {nombre} apuntan al mismo fichero"
        )
