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

    Se comprueba sobre el SQL porque es donde vive el `ORDER BY`, y porque el
    fallo era justo que el `ORDER BY` miraba una columna constante.
    """
    import inspect

    from pipelines.p2_impact import pipeline

    fuente = inspect.getsource(pipeline.build_report)

    assert "banda_titular" in fuente, "el ranking no consulta la banda del evento"
    assert "ORDER BY i.{columna}" in fuente, "el ORDER BY sigue fijado a una columna"


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
