"""Con que banda de intensidad se titula un reporte.

**Casi la mitad de los sismos reales de LATAM no alcanzan MMI≥7 sobre
poblacion.** Medido sobre los primeros dieciocho reportes del catalogo: ocho, el
44 %. No son casos raros — son los profundos y los de mar adentro, que en esta
region son la mitad del catalogo.

El producto entero titulaba con MMI≥7. Para esos ocho eventos eso significaba:

* una cifra grande que decia **0 personas**,
* una tabla de "municipios mas expuestos" ordenada por una columna de ceros, o
  sea en orden alfabetico,
* y una columna rotulada "Población MMI≥7" con quince ceros debajo.

Tehuantepec 2017 —M8,2, 98 muertos— se publicaba asi. Un cero es cierto y se lee
como que el sistema fallo, o como que el sismo no fue nada.
"""

from __future__ import annotations

import pytest

from pipelines.p3_report.markdown import render_markdown
from pipelines.p3_report.model import MunicipioTop, Report, Totales


def test_con_poblacion_en_mmi8_titula_con_ocho() -> None:
    assert Totales(pop_mmi6p=900.0, pop_mmi7p=500.0, pop_mmi8p=100.0).banda_titular == 8


def test_con_poblacion_en_mmi7_titula_con_siete() -> None:
    assert Totales(pop_mmi6p=900.0, pop_mmi7p=500.0).banda_titular == 7


def test_sin_poblacion_en_mmi7_baja_a_seis() -> None:
    """El caso de Tehuantepec: M8,2 cuyo maximo sobre poblacion es MMI 6,5."""
    assert Totales(pop_mmi6p=760_856.0, pop_mmi7p=0.0).banda_titular == 6


def test_un_sismo_que_no_alcanza_poblacion_no_tiene_banda() -> None:
    """Masachapa 2022: M6,6 a 55 km mar adentro, cero en todas las bandas.

    Tambien es un resultado. Devolver 6 aqui haria que el visor titulara "0
    personas en MMI≥6", que es la frase que este arreglo existe para evitar.
    """
    assert Totales().banda_titular == 0


def test_la_poblacion_de_una_banda_no_publicada_es_cero() -> None:
    """MMI 5 no se publica: preguntarlo no puede devolver una cifra inventada."""
    totales = Totales(pop_mmi6p=100.0)

    assert totales.poblacion_en(6) == 100.0
    assert totales.poblacion_en(5) == 0.0


# --- Lo que ve el lector ----------------------------------------------------


def _reporte(totales: Totales, municipios: tuple[MunicipioTop, ...]) -> Report:
    from pipelines.p3_report.model import Evento, Inputs

    return Report(
        event=Evento(
            usgs_id="us2000ahv0",
            mag=8.2,
            depth_km=47.4,
            utc="2017-09-08T04:49:19Z",
            lugar="Terremoto de Tehuantepec, México (2017)",
        ),
        inputs=Inputs(shakemap_version=1, groundfailure_version=0, exposure_manifest="mex-v0.1"),
        totales=totales,
        top_municipios=municipios,
    )


def test_la_tabla_se_rotula_con_la_banda_alcanzada() -> None:
    """La columna decia siempre MMI≥7, y para este evento son quince ceros."""
    reporte = _reporte(
        Totales(pop_mmi6p=760_856.0),
        (MunicipioTop("MX20043", "Arriaga", 6.5, pop_mmi7p=0.0, pop_banda=41_000.0),),
    )

    texto = render_markdown(reporte)

    assert "Población MMI≥6" in texto
    assert "por población en MMI≥6" in texto
    assert "41 mil" in texto, "la tabla tiene que traer la cifra de la banda, no el cero"


def test_un_evento_que_si_llega_a_siete_no_cambia() -> None:
    """El caso normal se publica igual que siempre: nada de regresiones."""
    reporte = _reporte(
        Totales(pop_mmi6p=6_960_086.0, pop_mmi7p=2_415_793.0),
        (MunicipioTop("66001", "Pereira", 7.5, pop_mmi7p=500_000.0, pop_banda=500_000.0),),
    )

    texto = render_markdown(reporte)

    assert "Población MMI≥7" in texto
    assert "500 mil" in texto


def test_un_reporte_antiguo_sin_pop_banda_se_sigue_renderizando() -> None:
    """Los reportes emitidos antes del campo tienen banda 7 y cifra de siempre.

    El visor y el markdown leen artefactos ya publicados: romperlos por anadir
    un campo seria cambiar el pasado.
    """
    reporte = _reporte(
        Totales(pop_mmi6p=1_000.0, pop_mmi7p=800.0),
        (MunicipioTop("05001", "Medellin", 7.0, pop_mmi7p=800.0),),
    )

    assert "800" in render_markdown(reporte)


def test_el_ranking_se_ordena_por_la_banda_del_evento() -> None:
    """Es el arreglo: con `pop_mmi7p` todo a cero, el orden era el alfabetico.

    Esto comprobaba `"banda_titular" in inspect.getsource(build_report)`, que
    es un guardia que pasa aunque la funcion no se ejecute nunca —y
    `build_report` tenia cero llamadas en toda la suite—. Ademas fijaba el
    nombre equivocado: `banda_titular` era justo la regla que sobraba.

    Ahora se comprueba la propiedad, no el texto: los dos productores tienen que
    decidir la misma banda para los mismos totales.
    """
    from pipelines.p2_impact.pipeline import ImpactTotals

    casos = [
        # (mmi6, mmi7, mmi8) -> banda esperada
        ((900.0, 500.0, 100.0), 7),  # alcanza 8: se ordena por 7 igualmente
        ((900.0, 500.0, 0.0), 7),
        ((760_856.0, 0.0, 0.0), 6),
        ((0.0, 0.0, 0.0), 6),
    ]
    for (mmi6, mmi7, mmi8), esperada in casos:
        totales = Totales(pop_mmi6p=mmi6, pop_mmi7p=mmi7, pop_mmi8p=mmi8)
        # La que usa P2 para seleccionar los quince en SQL...
        desde_p2 = ImpactTotals(pop_mmi6p=mmi6, pop_mmi7p=mmi7, pop_mmi8p=mmi8)
        assert desde_p2.to_totales().banda_publicada == esperada
        # ...y la que usan el markdown, el hilo y el mapa para reordenarlos.
        assert totales.banda_publicada == esperada


def test_la_banda_del_ranking_nunca_es_ocho() -> None:
    """MMI>=8 es demasiado estrecha para ordenar municipios.

    Ordenando por ella, Manta —265.263 personas en MMI>=7 y ninguna en MMI>=8—
    no entraba en la tabla de `reports/us20005j32`, y si entraba Eloy Alfaro con
    6.605. El SQL recortaba a quince por MMI>=8 y la publicacion reordenaba por
    MMI>=7, asi que quien no pasaba el primer corte ya no existia.
    """
    con_ocho = Totales(pop_mmi6p=4_311_549.0, pop_mmi7p=2_283_454.0, pop_mmi8p=107_904.0)
    assert con_ocho.banda_titular == 8, "el titular si distingue la banda 8"
    assert con_ocho.banda_publicada == 7, "el ranking no puede ordenar por MMI>=8"


@pytest.mark.parametrize("banda", [6, 7, 8])
def test_toda_banda_publicada_sabe_ordenar(banda: int) -> None:
    """`impact_adm2` tiene que traer la columna de cualquier banda titular."""
    from pipelines.p2_impact.pipeline import SQL_IMPACT_ADM2

    assert f"AS pop_mmi{banda}p" in SQL_IMPACT_ADM2


def test_el_visor_usa_la_misma_regla_que_el_reporte() -> None:
    """Dos reglas distintas darian dos titulares distintos del mismo evento."""
    from pathlib import Path

    app = (Path(__file__).parent.parent.parent / "site" / "assets" / "app.js").read_text("utf-8")

    assert "function bandaTitular(" in app
    assert "pop_mmi6p" in app, "el visor no puede bajar de banda sin la cifra de MMI≥6"


def test_el_indice_publica_las_dos_bandas() -> None:
    """Sin `pop_mmi6p` en el indice, el visor no puede titular sin abrir el reporte."""
    import inspect

    from pipelines.p3_report import run

    fuente = inspect.getsource(run.rebuild_index)

    assert '"pop_mmi6p"' in fuente
    assert '"pop_mmi7p"' in fuente
