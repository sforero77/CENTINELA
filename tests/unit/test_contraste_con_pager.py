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
    """El acuerdo, comprobado. Es lo unico que se puede afirmar de las dos a la vez."""
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
