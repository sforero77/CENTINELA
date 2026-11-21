"""Que el contraste con PAGER se sostenga solo, y siga siendo cierto.

LA OBJECION QUE HUNDE EL PROYECTO EN UNA REUNION. Hasta `report/2.0` el README
publicaba «2.415.793 en MMI≥7» y PAGER 6.514.486 para el mismo evento: un factor
de 2,7, porque PAGER agrupa por MMI **redondeado** —su fila «7» es todo lo que
cae entre 6,5 y 7,49— y CENTINELA cortaba en decimales **literales**. Lo unico
que se podia comprobar era que cada cifra cayera *entre* dos filas de PAGER.

Desde la 2.0 (21-nov-2026) las bandas son clases USGS con el mismo corte (VI
≥5,5, VII ≥6,5, VIII ≥7,5) y la comparacion es clase contra clase. Lo que se fija
aqui es lo que §5 de `docs/PARA_INSTITUCIONES.md` afirma: CENTINELA no supera a
PAGER en ninguna clase —su intensidad por celda es una cota inferior— y en VI y
VII queda cerca.

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


#: (clase de CENTINELA, umbral de PAGER acumulado que es su pareja exacta,
#: desvio maximo hacia abajo que §5 da por explicado).
#:
#: VIII lleva mas margen y no es un descuido: es la franja mas estrecha, la que
#: mas mueve la cota inferior por celda y el cambio de ShakeMap (CENTINELA v11
#: contra PAGER v9). Medido el 21-nov-2026: VI −15 %, VII −10 %, VIII −46 %.
PAREJAS: tuple[tuple[str, float, float], ...] = (
    ("pop_mmi6p", 5.5, 0.25),
    ("pop_mmi7p", 6.5, 0.25),
    ("pop_mmi8p", 7.5, 0.60),
)


@pytest.mark.parametrize(
    ("campo", "umbral", "desvio_maximo"), PAREJAS, ids=[c for c, _, _ in PAREJAS]
)
def test_la_clase_de_centinela_queda_por_debajo_y_cerca_de_la_de_pager(
    campo: str,
    umbral: float,
    desvio_maximo: float,
    centinela: dict[str, float],
    pager: dict[float, int],
) -> None:
    """Clase contra clase: nunca por encima, y no mas lejos de lo que §5 explica."""
    nuestra = centinela[campo]
    suya = pager[umbral]

    assert nuestra <= suya, (
        f"{campo} = {nuestra:,.0f} supera a PAGER ({suya:,} en ≥{umbral}). La "
        "intensidad por celda es una cota inferior: si se pasa, algo esta mal."
    )
    assert nuestra >= suya * (1 - desvio_maximo), (
        f"{campo} = {nuestra:,.0f} queda mas de un {desvio_maximo:.0%} por debajo de "
        f"PAGER ({suya:,} en ≥{umbral}). §5 de PARA_INSTITUCIONES.md no lo explica."
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


@pytest.mark.parametrize("campo", ["pop_mmi6p", "pop_mmi7p", "pop_mmi8p"])
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


def test_el_documento_dice_que_la_convencion_es_la_misma(documento: str) -> None:
    """Y por que antes no lo era: sin eso, la cifra vieja citada en cualquier
    otro sitio parece contradecir la nueva."""
    assert "misma convención" in documento
    assert "redondeado" in documento
    assert "literales" in documento


def test_el_reporte_publicado_lleva_la_misma_advertencia() -> None:
    """La cifra que se cita es la del `report.md`, y es ahi donde se pone al lado
    de la de PAGER: tiene que decir que la convencion es la misma."""
    md = (RAIZ / "reports" / "us6000tjl2" / "report.md").read_text(encoding="utf-8")

    assert "la misma convención" in md
    assert "VI desde MMI 5,5" in md
