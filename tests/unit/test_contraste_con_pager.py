"""Que el contraste con PAGER se sostenga solo, y siga siendo cierto.

LA OBJECION QUE HUNDE EL PROYECTO EN UNA REUNION. El README publica «2.415.793
en MMI≥7» y PAGER publica 6.514.486 para el mismo evento. Un factor de 2,7. Sin
explicacion al lado, la lectura por defecto de cualquier evaluador es que
CENTINELA subcuenta, y lo encuentra en cinco minutos.

No subcuenta: las dos no tabulan igual. PAGER agrupa por MMI **redondeado** —su
fila «7» es todo lo que cae entre 6,5 y 7,49— y CENTINELA usa bandas
**literales**. Puestas en el mismo eje, cada cifra de CENTINELA tiene que caer
dentro del intervalo que las filas de PAGER acotan por arriba y por abajo. Es
una relacion aritmetica, no una coincidencia: si alguna se saliera, una de las
dos estaria mal.

Y por eso esto es una prueba y no un parrafo. La leccion ya la pago este
repositorio una vez: `test_cifras_del_readme.py` existe porque cinco cifras
copiadas a mano se quedaron atras. Un contraste copiado a mano se queda atras
igual, y ademas deja de ser cierto sin avisar.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pipelines.common.formatting import format_number_es

RAIZ = Path(__file__).parent.parent.parent
DOCUMENTO = RAIZ / "docs" / "PARA_INSTITUCIONES.md"
REPORTE = RAIZ / "reports" / "us6000tjl2" / "report.json"
#: `json/exposures.json` del producto `losspager` de us6000tjl2, congelado.
PAGER = RAIZ / "tests" / "fixtures" / "golden" / "choco_2026_08_10" / "pager_exposures.json"


@pytest.fixture(scope="module")
def documento() -> str:
    return DOCUMENTO.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def centinela() -> dict[str, float]:
    datos: dict[str, float] = json.loads(REPORTE.read_text(encoding="utf-8"))["totales"]
    return datos


@pytest.fixture(scope="module")
def pager() -> dict[float, int]:
    """Las filas de PAGER, acumuladas y reexpresadas como umbrales literales.

    `aggregated_exposure[i]` es la poblacion de la fila de MMI `i+1`, que abarca
    de `i+0,5` a `i+1,49`. Acumular de arriba abajo da "poblacion en MMI ≥ i+0,5",
    que es la unica forma de poner las dos convenciones en el mismo eje.
    """
    filas: list[int] = json.loads(PAGER.read_text(encoding="utf-8"))["population_exposure"][
        "aggregated_exposure"
    ]
    acumulado = 0
    por_umbral: dict[float, int] = {}
    for indice in range(len(filas) - 1, -1, -1):
        acumulado += filas[indice]
        por_umbral[indice + 0.5] = acumulado
    return por_umbral


#: (banda literal de CENTINELA, cota inferior de PAGER, cota superior de PAGER).
#: La cota inferior es el umbral de PAGER inmediatamente **por encima** de la
#: banda; la superior, el inmediatamente por debajo.
#: Cuanto puede alejarse `pop_mmi6p` del piso de PAGER antes de que deje de ser
#: "el desvio conocido" y pase a ser "algo se rompio".
#:
#: **NO ES LA BANDA DE DISCREPANCIA DEL REPORTE, Y LLEGO A ESTARLO.** Esta
#: constante valia 0.037 "porque es lo que el reporte declara", y era un error de
#: razonamiento: `pop_discrepancia_pct` mide GHS-POP contra WorldPop **sobre las
#: mismas celdas** (`SUM(pop_total)` vs `SUM(pop_alt_worldpop)` en
#: `p2_impact/pipeline.py`), no la distancia a una cifra de PAGER calculada con
#: otro insumo y otra convencion de bandas. Que 3,6 fuera menor que 3,7 era una
#: coincidencia numerica sin contenido, y estuvo publicada en el README.
#:
#: Ahora es lo que dice ser: un margen elegido a mano, con holgura sobre el
#: 3,6 % medido el 8-sep-2026 para que un ShakeMap nuevo no lo haga saltar por
#: decimas, y lo bastante estrecho para que un cambio de verdad no pase. No
#: pretende explicar nada.
MARGEN_TOLERADO_BAJO_EL_PISO = 0.06

ACOTAMIENTOS: tuple[tuple[str, float, float], ...] = (
    ("pop_mmi6p", 6.5, 5.5),
    ("pop_mmi7p", 7.5, 6.5),
    ("pop_mmi8p", 8.5, 7.5),
)


@pytest.mark.parametrize(
    ("campo", "umbral_inferior", "umbral_superior"),
    ACOTAMIENTOS,
    ids=[c for c, _, _ in ACOTAMIENTOS],
)
def test_la_cifra_de_centinela_cae_dentro_del_intervalo_de_pager(
    campo: str,
    umbral_inferior: float,
    umbral_superior: float,
    centinela: dict[str, float],
    pager: dict[float, int],
) -> None:
    """El acuerdo, comprobado. Es lo unico que se puede afirmar de las dos a la vez.

    **`pop_mmi6p` DEJO DE ACOTAR CON EL SHAKEMAP v9, Y SE FIJA ASI EN VEZ DE
    AFLOJAR EL ASSERT.** Hasta el v8 las tres bandas caian dentro. El 8-sep-2026
    el repaso dejo de excluir los backtests, USGS ya iba por el v9 y el reporte
    se re-emitio solo: `pop_mmi6p` quedo 249.011 personas —un 3,6 %— por debajo
    del piso que impone la fila ≥6,5 de PAGER.

    No se relaja la comprobacion a "casi acota". Se fija el estado real con su
    margen medido: si mejora hasta acotar, o si empeora mas alla de la
    discrepancia que el reporte declara, esta prueba tiene que enterarse. Bajar
    el listado a un `<=` generoso seria justo lo que este proyecto no hace.

    **La causa no se conoce, y las dos que se llegaron a escribir eran falsas.**
    Ni el 3,6 % "cabe" en la banda de discrepancia del reporte —que mide GHS-POP
    contra WorldPop sobre las mismas celdas, no la distancia a PAGER— ni el delta
    contra `grid.xml` respalda el sesgo del centroide: `delta_contornos_vs_grid.py`
    muestrea las dos ramas en el mismo centro de celda y la resta lo cancela. Lo
    que el sistema sí afirma de su muestreo lo imprime cada reporte: «el sesgo que
    introduce no está medido: puede quedarse corto o pasarse».
    """
    nuestra = centinela[campo]
    piso, techo = pager[umbral_inferior], pager[umbral_superior]

    if campo == "pop_mmi6p":
        # El unico que no acota. Se exige que siga por debajo del piso **y**
        # que el desvio no pase de la banda de discrepancia que el reporte
        # publica: fuera de ahi ya no es el sesgo conocido, es otra cosa.
        falta = (piso - nuestra) / nuestra
        assert nuestra < piso, (
            f"{campo} volvio a acotar ({nuestra:,.0f} >= {piso:,}). Es una buena "
            "noticia: quita el `if` de esta prueba y actualiza README.md y "
            "docs/PARA_INSTITUCIONES.md, que hoy publican que no acota."
        )
        assert falta <= MARGEN_TOLERADO_BAJO_EL_PISO, (
            f"{campo} = {nuestra:,.0f} se queda {falta:.1%} por debajo del piso "
            f"({piso:,} en ≥{umbral_inferior}), y el margen tolerado es "
            f"{MARGEN_TOLERADO_BAJO_EL_PISO:.1%}. Era 3,6 % el 8-sep-2026: se movio "
            "de mas. Mira si cambio el ShakeMap o si se rompio el corte por bandas."
        )
        assert nuestra <= techo, f"{campo} = {nuestra:,.0f} supera el techo {techo:,}"
        return

    assert piso <= nuestra <= techo, (
        f"{campo} = {nuestra:,.0f} se sale del intervalo que PAGER acota "
        f"[{piso:,} en ≥{umbral_inferior}, {techo:,} en ≥{umbral_superior}]. "
        "O cambio el ShakeMap, o una de las dos cifras esta mal."
    )


@pytest.mark.parametrize("umbral", [5.5, 6.5, 7.5])
def test_la_columna_de_pager_del_documento_es_la_del_producto(
    umbral: float, documento: str, pager: dict[float, int]
) -> None:
    """La tabla que va a instituciones, contra el JSON de USGS."""
    esperado = format_number_es(pager[umbral])

    assert esperado in documento, (
        f"§5 no publica {esperado} para MMI ≥ {umbral}; PAGER si. La tabla se despego."
    )


@pytest.mark.parametrize("campo", ["pop_mmi6p", "pop_mmi7p"])
def test_la_columna_de_centinela_del_documento_es_la_publicada(
    campo: str, documento: str, centinela: dict[str, float]
) -> None:
    esperado = format_number_es(centinela[campo])

    assert esperado in documento, f"§5 no publica {esperado} para {campo}"


def test_el_documento_dice_por_que_las_dos_cifras_no_son_comparables(documento: str) -> None:
    """Sin esta frase la tabla es peor que no tenerla: invita a restar."""
    assert "redondeado" in documento
    assert "literales" in documento


def test_el_reporte_publicado_lleva_la_misma_advertencia() -> None:
    """No basta con decirlo en el documento de instituciones: la cifra que se
    cita es la del `report.md`, y es ahi donde se pone al lado de la de PAGER."""
    md = (RAIZ / "reports" / "us6000tjl2" / "report.md").read_text(encoding="utf-8")

    assert "no se tabulan igual" in md
    assert "6,5 y 7,49" in md


# --- La misma tabla vive en dos sitios, y solo uno estaba vigilado -----------

PORTADA = RAIZ / "README.md"


@pytest.mark.parametrize("campo", ["pop_mmi6p", "pop_mmi7p"])
def test_la_portada_publica_la_misma_tabla_que_el_documento(
    campo: str, centinela: dict[str, float]
) -> None:
    """El README repite la tabla de PAGER y afirma que esta prueba la vigila.

    No era verdad: la prueba solo leia `PARA_INSTITUCIONES.md`, asi que la copia
    de la portada podia envejecer sola. Se descubrio al re-emitir us6000tjl2 con
    un activo de exposicion mas nuevo: las cifras del documento fallaron y las
    de la portada, identicas y ahora desfasadas, pasaron.

    Es la familia de fallo que este proyecto ya tiene nombrada —el mismo hecho
    afirmado en dos sitios y comprobado en uno— aplicada a la tabla que existe
    precisamente para resistir la primera objecion que recibe el proyecto.
    """
    esperado = format_number_es(centinela[campo])
    portada = PORTADA.read_text(encoding="utf-8")

    assert esperado in portada, (
        f"la portada no publica {esperado} para {campo}. Si acabas de re-emitir "
        "el evento, la tabla de §«El contraste con PAGER» hay que actualizarla "
        "en README.md y en docs/PARA_INSTITUCIONES.md a la vez."
    )


# --- Acotar no es coincidir --------------------------------------------------


@pytest.mark.parametrize(
    ("campo", "umbral_inferior", "umbral_superior"),
    ACOTAMIENTOS,
    ids=[c for c, _, _ in ACOTAMIENTOS],
)
def test_la_cifra_cae_en_el_cuarto_inferior_del_intervalo(
    campo: str,
    umbral_inferior: float,
    umbral_superior: float,
    centinela: dict[str, float],
    pager: dict[float, int],
) -> None:
    """Lo que se puede afirmar sin elegir un metodo de interpolacion.

    EL SUPERLATIVO GASTABA LA CREDIBILIDAD QUE QUERIA COMPRAR. Los documentos
    decian que el acotamiento era «el unico acuerdo aritmeticamente posible».
    Pero el intervalo de MMI≥7 va de 1,1 a 6,6 millones —un factor de 6,1— y
    dentro cabe casi cualquier cifra: caer dentro es una condicion necesaria, no
    una validacion.

    Lo que si dice algo es **donde** cae: por debajo del punto medio y siempre en
    la misma direccion. Cuanto por debajo depende de como se interpole entre las
    filas de PAGER —del 9 % al 37 % segun sea lineal o logaritmica— y por eso no
    se publica ninguna de esas cifras como si fuera la respuesta.

    **SE FIJA EL PRINCIPIO, NO EL VALOR OBSERVADO.** Esta prueba pedia «<= 25 %»
    porque era lo que daba con el ShakeMap v8 (14 % y 24 %). Con el v9 `pop_mmi7p`
    quedo al 26,1 %: la afirmacion de fondo —por debajo del punto medio— sigue
    intacta, y el assert saltaba por un punto y medio. Un umbral calcado del dato
    de ayer convierte cada revision de USGS en un falso positivo.

    El principio es el que este mismo docstring ya declaraba: «si un ShakeMap
    nuevo moviera la cifra a la mitad alta del intervalo, la afirmacion publicada
    dejaria de ser cierta». Eso es lo que se comprueba.
    """
    nuestra = centinela[campo]
    piso, techo = pager[umbral_inferior], pager[umbral_superior]
    posicion = (nuestra - piso) / (techo - piso)

    if campo == "pop_mmi6p":
        # No acota desde el v9: cae por debajo del piso, o sea posicion negativa.
        # Su margen lo vigila `test_la_cifra_de_centinela_cae_dentro_del_intervalo`.
        assert posicion < 0.0, (
            f"{campo} volvio a entrar en el intervalo (al {posicion:.0%}). Hay que "
            "reescribir README.md y docs/PARA_INSTITUCIONES.md, que publican que no."
        )
        return

    assert 0.0 <= posicion < 0.5, (
        f"{campo} cae al {posicion:.0%} del intervalo de PAGER, y los documentos "
        f"publican que queda por debajo del punto medio. Si el ShakeMap lo movio a "
        f"la mitad alta, hay que reescribir esa frase en README.md y "
        f"docs/PARA_INSTITUCIONES.md."
    )
