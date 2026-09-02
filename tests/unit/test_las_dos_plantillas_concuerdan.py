"""El `report.md` y el `hilo.txt` del mismo evento dicen lo mismo.

EL FALLO QUE CIERRA. Para Muisne, el reporte nombraba Portoviejo / Esmeraldas /
Quinindé y el hilo nombraba Pedernales / Jama / Muisne. Dos respuestas a la misma
pregunta sobre el mismo evento, publicadas a la vez y firmadas por el mismo
sistema.

No fue un descuido de escritura: el ranking se arreglo —ordenar por la banda del
reporte y descartar los ceros— en `markdown.py`, y `social.py` siguio leyendo
`top_municipios` crudo. **Un arreglo que aterriza en una plantilla y no en la
otra.**

La leccion no es "revisar las dos": es que la respuesta pertenece al reporte y no
a como se dibuje. Por eso el ranking vive en `model.py` y estas pruebas comprueban
que las dos plantillas lo usan.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pipelines.p3_report.markdown import render_markdown
from pipelines.p3_report.model import Report, municipios_del_ranking
from pipelines.p3_report.social import render_thread_text

RAIZ = Path(__file__).parent.parent.parent
REPORTES = RAIZ / "reports"


def _eventos() -> list[str]:
    return sorted(p.parent.name for p in REPORTES.glob("*/report.json"))


def _reporte(usgs_id: str) -> Report:
    return Report.from_dict(
        json.loads((REPORTES / usgs_id / "report.json").read_text(encoding="utf-8"))
    )


@pytest.mark.parametrize("usgs_id", _eventos())
def test_el_hilo_nombra_los_mismos_municipios_que_el_reporte(usgs_id: str) -> None:
    """Los tres primeros del hilo son los tres primeros de la tabla."""
    report = _reporte(usgs_id)
    esperados = [m.nombre for m in municipios_del_ranking(report)[:3]]
    if not esperados:
        pytest.skip("evento sin municipios expuestos; lo cubre la prueba de abajo")

    hilo = render_thread_text(report)
    md = render_markdown(report)
    for nombre in esperados:
        assert nombre in hilo, f"{usgs_id}: el hilo no nombra a {nombre}"
        assert nombre in md, f"{usgs_id}: el reporte no nombra a {nombre}"


@pytest.mark.parametrize("usgs_id", _eventos())
def test_sin_expuestos_ninguna_plantilla_nombra_municipios(usgs_id: str) -> None:
    """Nombrar a los tres primeros de una lista de ceros es inventar un ranking.

    `us1000c2zy` —M7,5 mar adentro— publicaba «Municipios más expuestos: Ahuas,
    Puerto Lempira, Brus Laguna» con cero personas expuestas en los tres.
    """
    report = _reporte(usgs_id)
    if municipios_del_ranking(report):
        pytest.skip("este evento sí tiene municipios expuestos")

    hilo = render_thread_text(report)
    assert "Municipios más expuestos" not in hilo, (
        f"{usgs_id}: el hilo promete un ranking que no existe"
    )
    # Y el reporte no publica una cabecera de tabla sin una sola fila debajo.
    md = render_markdown(report)
    assert "| # | Municipio |" not in md, f"{usgs_id}: cabecera de tabla sin filas"


@pytest.mark.parametrize("usgs_id", _eventos())
def test_un_muro_de_ceros_se_explica(usgs_id: str) -> None:
    """Siete filas en cero sin una palabra se leen como «no se pudo calcular»."""
    report = _reporte(usgs_id)
    if report.preliminar or report.totales.banda_titular:
        pytest.skip("este evento sí alcanza alguna banda sobre población")

    md = render_markdown(report)
    assert "es un resultado, no un fallo" in md, (
        f"{usgs_id}: publica ceros en todo sin decir por qué"
    )


@pytest.mark.parametrize("usgs_id", _eventos())
def test_el_hilo_enlaza_el_reporte_que_promete(usgs_id: str) -> None:
    """Decia «ver el reporte completo» y no daba dónde."""
    hilo = render_thread_text(_reporte(usgs_id))
    assert f"/reports/{usgs_id}/" in hilo, f"{usgs_id}: el hilo no enlaza su reporte"


@pytest.mark.parametrize("usgs_id", _eventos())
def test_la_fecha_del_hilo_no_dice_utc_dos_veces(usgs_id: str) -> None:
    """`ev.utc` ya acaba en Z, que **es** la marca de UTC: salia «Z UTC»."""
    hilo = render_thread_text(_reporte(usgs_id))
    assert "Z UTC" not in hilo, f"{usgs_id}: la fecha dice UTC dos veces"


@pytest.mark.parametrize("usgs_id", _eventos())
def test_ningun_hilo_afirma_mar_adentro_de_un_epicentro_en_tierra(usgs_id: str) -> None:
    """AFIRMAR DE MÁS CUESTA LA CREDIBILIDAD DE TODO LO DEMÁS.

    El hilo de `usp000jd2q` decía «la sacudida fue mar adentro» de un sismo con
    el epicentro a 5 km de Baní, tierra adentro en República Dominicana. El
    `.md` del mismo evento ya decía la versión correcta —«mar adentro **o sobre
    zona despoblada**»— y el hilo se había quedado con la mitad falsa.

    No se comprueba dónde cae el epicentro —eso pediría una línea de costa que
    este sistema no consume— sino que el hilo **no afirme categóricamente** algo
    que no puede saber. La redacción con «o» es cierta en los cinco casos.
    """
    hilo = render_thread_text(_reporte(usgs_id))

    assert "fue mar adentro" not in hilo, (
        f"{usgs_id}: el hilo afirma que la sacudida fue mar adentro sin poder saberlo. "
        "El epicentro puede estar en tierra sobre zona despoblada."
    )
