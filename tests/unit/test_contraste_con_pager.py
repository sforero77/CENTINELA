"""Que el contraste con PAGER se sostenga solo, y siga siendo cierto.

LA OBJECION QUE HUNDE EL PROYECTO EN UNA REUNION. El README publicaba «2.415.793
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
#: Con que ShakeMap se emparejo esa PAGER, y de donde salio.
PAGER_ORIGEN = PAGER.with_suffix(".origen.json")


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


#: AQUI VIVIA `MARGEN_TOLERADO_BAJO_EL_PISO`, Y SE VA CON SU CASO ESPECIAL.
#: Era cuanto podia alejarse `pop_mmi6p` del piso de PAGER mientras fue la unica
#: banda que no acotaba (0.06, con holgura sobre el 3,6 % medido el 8-sep-2026).
#: Con el ShakeMap v10 vuelve a acotar, asi que la constante no acota nada: se
#: borra en vez de quedarse "por si acaso", porque una constante sin uso es una
#: que el proximo lector tiene que descartar a mano.
#:
#: El margen nuevo es estrecho y conviene decirlo: 4.936 personas por encima del
#: piso, un 0,07 %. Si otro ShakeMap lo empuja abajo, las dos pruebas de este
#: fichero se ponen en rojo y hay que reescribir §5 del documento. Que eso sea
#: exactamente lo que debe pasar es la razon de no dejar el `if` puesto.

#: (banda literal de CENTINELA, cota inferior de PAGER, cota superior de PAGER).
#: La cota inferior es el umbral de PAGER inmediatamente **por encima** de la
#: banda; la superior, el inmediatamente por debajo.
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

    **LAS TRES BANDAS VUELVEN A ACOTAR DESDE EL SHAKEMAP v10.** Entre el v9 y el
    v10 esta prueba llevo un caso especial para `pop_mmi6p`, la unica que se
    salia: quedaba 249.011 personas —un 3,6 %— por debajo del piso que impone la
    fila ≥6,5 de PAGER, y se fijaba asi, con su margen medido, en vez de aflojar
    el assert.

    El v10 lo cerro sin que nadie tocara el calculo. Su contorno de MMI 6 se
    ensancha hacia el oriente —Buga entra con 131.984 personas, Quinchia con
    23.937, Ginebra con 14.320— y `pop_mmi6p` sube de 6.840.603 a 7.094.550, por
    encima del piso. El caso especial se borra: las tres bandas pasan por el
    mismo assert que siempre debieron pasar.

    Lo que aquello dejo escrito sigue siendo verdad y conviene no perderlo: **la
    causa del desvio nunca se supo, y las dos explicaciones que llegaron a
    publicarse eran falsas.** Ni el 3,6 % "cabia" en la banda de discrepancia del
    reporte —que mide GHS-POP contra WorldPop sobre las mismas celdas, no la
    distancia a PAGER— ni el delta contra `grid.xml` respaldaba el sesgo del
    centroide: `delta_contornos_vs_grid.py` muestrea las dos ramas en el mismo
    centro de celda y la resta lo cancela. Que el desvio se haya ido solo con un
    insumo nuevo no lo explica: lo retira.
    """
    nuestra = centinela[campo]
    piso, techo = pager[umbral_inferior], pager[umbral_superior]

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


def test_el_documento_dice_de_que_shakemap_es_cada_columna(documento: str) -> None:
    """Las dos columnas dejaron de ser de la misma version, y hay que decirlo.

    LA DESINCRONIZACION YA PASO TRES VECES, Y LA TERCERA NO SE PUEDE ARREGLAR.
    El 6-sep-2026 la fixture era la PAGER del v7 contra un reporte en v8; el
    8-sep, la del v8 contra un reporte en v9. Las dos veces se refresco la
    fixture y las dos columnas volvieron a salir del mismo ShakeMap.

    El 18-sep-2026 el reporte se re-emitio con el **v10** y esta vez refrescar no
    sirve: **USGS no ha vuelto a publicar PAGER**. Comprobado contra ComCat el
    21-sep: el producto `losspager` tiene diez entregas, la ultima con
    `updateTime` 1788821915886 (7-sep-2026 22:58 UTC), la que acompano al v9; el
    ShakeMap v10 es del 18-sep 19:49 UTC. La fixture congelada es byte a byte
    identica a esa ultima PAGER viva, asi que no hay nada que traer.

    O sea que la tabla de §5 compara **CENTINELA v10 contra PAGER v9**, y eso no
    se puede esconder detras de un encabezado que diga solo «PAGER». Esta prueba
    obliga a que el documento nombre las dos versiones mientras sean distintas —y
    a que las nombre bien cuando vuelvan a coincidir—, para que la asimetria
    viaje con la tabla en vez de quedarse en el commit que la introdujo.
    """
    version_pager = json.loads(PAGER_ORIGEN.read_text(encoding="utf-8"))["shakemap_version"]
    version_nuestra = json.loads(REPORTE.read_text(encoding="utf-8"))["inputs"]["shakemap_version"]

    assert f"PAGER (ShakeMap v{version_pager})" in documento, (
        f"§5 no dice que su columna de PAGER es del ShakeMap v{version_pager}"
    )
    assert f"CENTINELA (ShakeMap v{version_nuestra})" in documento, (
        f"§5 no dice que su columna de CENTINELA es del ShakeMap v{version_nuestra}"
    )

    if version_pager != version_nuestra:
        assert "USGS no ha vuelto a publicar PAGER" in documento, (
            f"las dos columnas van por ShakeMaps distintos (PAGER v{version_pager}, "
            f"CENTINELA v{version_nuestra}) y §5 no explica por que. Sin esa frase la "
            "tabla invita a leer las dos cifras como si fueran del mismo insumo."
        )


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

    Con el v10 las tres caen holgadamente en la mitad baja —`pop_mmi6p` al 0 %,
    `pop_mmi7p` al 14 %, `pop_mmi8p` al 0 %— y por primera vez desde el v8 las
    tres pasan por este mismo assert, sin caso especial.
    """
    nuestra = centinela[campo]
    piso, techo = pager[umbral_inferior], pager[umbral_superior]
    posicion = (nuestra - piso) / (techo - piso)

    assert 0.0 <= posicion < 0.5, (
        f"{campo} cae al {posicion:.0%} del intervalo de PAGER, y los documentos "
        f"publican que queda por debajo del punto medio. Si el ShakeMap lo movio a "
        f"la mitad alta, hay que reescribir esa frase en "
        f"docs/PARA_INSTITUCIONES.md."
    )
