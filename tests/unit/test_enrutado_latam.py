"""Que el sistema sirva a los diecinueve paises, no solo a los faciles.

P1 vigila **toda** la ventana LATAM y el activo de exposicion es por pais, asi
que cada evento hay que enrutarlo. El enrutado se hace por caja envolvente, las
cajas se solapan, y ordenarlas por area es un criterio que falla justo donde mas
duele.

**El caso Chile.** Su caja mide 1.719 grados cuadrados porque llega a Rapa Nui,
a 109,7°O. La de Argentina mide 671. Un sismo en Coquimbo cae dentro de las dos
y sale ordenado como argentino primero. El workflow se quedaba con el primer
candidato que tuviera Release: bajaba el activo de Argentina, el join no
encontraba una sola celda y el evento se quedaba sin reporte. Chile es de los
paises mas sismicos de la region.

No es exclusivo de Chile: cualquier par de cajas solapadas produce lo mismo.
Ecuador y Colombia se solapan, Venezuela y Colombia tambien, y el archipielago
de Mexico estira su caja hasta 118,6°O.

El desempate honesto lo da el join contra las celdas H3, como dicen las
docstrings de `countries_for_point` y de `paises-candidatos` desde el principio.
Estas pruebas fijan que el codigo permita ese reintento.
"""

from __future__ import annotations

import pytest

from pipelines.cli import EXIT_ACTIVO_DE_OTRO_PAIS
from pipelines.p0_exposure.download import COUNTRY_BBOX, countries_for_point
from pipelines.p2_impact.pipeline import ExposureCountryMismatchError

#: Epicentros reales de sismos M≥6 del catalogo de USGS, con el pais al que
#: pertenecen de verdad. Son el caso de uso, no un ejemplo inventado.
EPICENTROS_REALES: tuple[tuple[str, str, float, float], ...] = (
    ("us10007mn3", "CHL", -73.79, -43.42),  # M7,6 Quellon
    ("us2000j6hy", "CHL", -71.42, -30.04),  # M6,7 Coquimbo — el caso dificil
    ("us2000cjfy", "PER", -74.74, -15.78),  # M7,1 Atiquipa
    ("us20005j32", "ECU", -79.92, 0.38),  # M7,8 Muisne
    ("us7000f93v", "MEX", -99.78, 16.75),  # M7,0 Acapulco
    ("us6000t7zp", "VEN", -67.22, 10.61),  # M7,5 Catia La Mar
    ("us6000tjl2", "COL", -76.24, 4.84),  # M7,4 Choco
)


@pytest.mark.parametrize(
    ("usgs_id", "iso3", "lon", "lat"), EPICENTROS_REALES, ids=[e[0] for e in EPICENTROS_REALES]
)
def test_el_pais_real_esta_entre_los_candidatos(
    usgs_id: str, iso3: str, lon: float, lat: float
) -> None:
    """Lo minimo: que el pais correcto aparezca en la lista.

    Si no apareciera, ningun reintento podria salvarlo — el evento se quedaria
    sin reporte hiciera lo que hiciera el workflow.
    """
    candidatos = countries_for_point(lon, lat)

    assert iso3 in candidatos, f"{usgs_id} ocurrio en {iso3} y no esta en {candidatos}"


def test_el_orden_por_area_no_siempre_acierta() -> None:
    """La prueba que documenta por que hace falta reintentar.

    Si algun dia esto empieza a fallar sera porque alguien encontro un criterio
    de orden mejor. Seria una buena noticia y habria que venir aqui a
    celebrarlo — pero el reintento se queda igual, porque ninguna heuristica
    sobre cajas puede acertar siempre.
    """
    candidatos = countries_for_point(-71.42, -30.04)  # Coquimbo, Chile

    assert candidatos[0] != "CHL", "si esto cambia, revisa el comentario de arriba"
    assert "CHL" in candidatos


def test_la_caja_de_chile_es_mayor_que_la_de_argentina() -> None:
    """La causa concreta, medida, del caso de Coquimbo.

    Rapa Nui esta a 3.500 km del continente y es territorio chileno habitado:
    la caja no se puede recortar. Lo que hay que arreglar es el enrutado.
    """

    def area(iso3: str) -> float:
        c = COUNTRY_BBOX[iso3]
        return (c.lon_max - c.lon_min) * (c.lat_max - c.lat_min)

    assert area("CHL") > area("ARG")


def test_el_descarte_por_pais_no_es_un_fallo_cualquiera() -> None:
    """Quien orquesta tiene que poder distinguirlo del resto de errores.

    Ante un fallo hay que abrir un issue; ante un descarte hay que reintentar
    con el siguiente candidato. Tratarlos igual significa o bien no reintentar
    nunca, o bien esconder fallos reales tras un reintento.
    """
    assert issubclass(ExposureCountryMismatchError, ValueError)
    assert EXIT_ACTIVO_DE_OTRO_PAIS not in (0, 1, 2), "choca con exito, error o 'mira esto'"


def test_el_workflow_reintenta_con_el_siguiente_candidato() -> None:
    """El bucle tiene que estar en `impact.yml`, no solo en la docstring.

    Es exactamente el fallo que esta auditoria persigue: el diseno correcto
    escrito en un comentario y no implementado en ningun sitio. `countries_for_point`
    llevaba desde el principio prometiendo que "el join desempata de verdad", y
    el workflow se quedaba con el primer candidato.
    """
    from pathlib import Path

    workflow = (
        Path(__file__).parent.parent.parent / ".github" / "workflows" / "impact.yml"
    ).read_text(encoding="utf-8")

    assert "for ISO3 in $PAISES" in workflow, "el workflow no recorre los candidatos"
    assert f"-ne {EXIT_ACTIVO_DE_OTRO_PAIS} ]" in workflow, (
        "el workflow no distingue el descarte por pais de un fallo real"
    )
    assert "continue" in workflow or "se prueba el siguiente" in workflow


def test_todo_pais_cubierto_tiene_caja_declarada() -> None:
    """Un pais sin caja es invisible para el enrutado.

    `countries_for_point` solo puede devolver paises que esten en
    `COUNTRY_BBOX`: uno que falte no se enruta nunca, aunque tenga manifest y
    activo publicado.
    """
    from pathlib import Path

    manifests = Path(__file__).parent.parent.parent / "data" / "manifests"
    declarados = {p.stem for p in manifests.glob("*.yaml")}

    assert declarados <= set(COUNTRY_BBOX), (
        f"Paises con manifest y sin caja envolvente: {sorted(declarados - set(COUNTRY_BBOX))}"
    )
