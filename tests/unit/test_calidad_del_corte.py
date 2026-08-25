"""Los asserts de §6.4 sobre el corte de un evento, que en P2 no corrian.

Vivian en `check_quality`, una funcion sin llamador, invocada desde `run_join`
—otra funcion sin llamador— cuya docstring afirmaba que si los corria. La espec
pide explicitamente que corran «en P0 y P2».

Un assert que no se ejecuta es peor que no tenerlo: ocupa el sitio de la
vigilancia que no existe, y quien lee el codigo cree que esta cubierto.
"""

from __future__ import annotations

from typing import Any

import pytest

from pipelines.p2_impact.exposure_join import (
    QUALITY_ASSERTIONS,
    QualityAssertionError,
    QualityReport,
    check_quality,
)

pytestmark = pytest.mark.geo


@pytest.fixture
def con() -> Any:
    """Un corte limpio: dos celdas, un municipio, todo cuadrado."""
    from pipelines.p2_impact.exposure_join import connect

    con = connect()
    con.execute(
        """
        CREATE OR REPLACE TABLE impact_h3 AS
        SELECT * FROM (VALUES
            (1::UBIGINT, '05001', 120.0, 7.5),
            (2::UBIGINT, '05001',  80.0, 6.5)
        ) AS t(h3_08, adm2_id, pop_total, mmi_max)
        """
    )
    con.execute(
        "CREATE OR REPLACE TABLE impact_adm2 AS "
        "SELECT '05001' AS adm2_id, 7.5 AS mmi_max, 200.0 AS pop_mmi7p"
    )
    con.execute("CREATE OR REPLACE TABLE admin_lookup AS SELECT '05001' AS adm2_id")
    return con


def test_un_corte_sano_pasa_limpio(con: Any) -> None:
    parte = check_quality(con)

    assert parte.limpio
    assert parte.bloqueantes == ()
    assert parte.avisos == ()


def test_la_poblacion_negativa_detiene_la_publicacion(con: Any) -> None:
    """Es el sintoma del nodata sin enmascarar: -200 por pixel de oceano.

    Publicar poblacion negativa no es un detalle estetico: es una cifra falsa
    y creible, en el artefacto que alguien va a citar durante una emergencia.
    """
    con.execute("INSERT INTO impact_h3 VALUES (3::UBIGINT, '05001', -50.0, 7.0)")

    parte = check_quality(con)

    assert any("pop_negativa" in fallo for fallo in parte.bloqueantes)
    with pytest.raises(QualityAssertionError, match="pop_negativa"):
        parte.raise_if_blocking()


def test_una_celda_sin_municipio_detiene_la_publicacion(con: Any) -> None:
    """Una celda sin `adm2_id` no aparece en ninguna fila municipal.

    Su poblacion cuenta en el total nacional y no en ningun municipio: las dos
    cifras publicadas dejan de sumar entre si.
    """
    con.execute("INSERT INTO impact_h3 VALUES (4::UBIGINT, NULL, 10.0, 7.0)")

    assert any("pop_nula" in fallo for fallo in check_quality(con).bloqueantes)


def test_un_municipio_sin_nombre_avisa_pero_no_detiene(con: Any) -> None:
    """Se cae de la tabla del reporte, sin una palabra, por un JOIN interno.

    Puede ser el mas expuesto del evento. Pero los totales nacionales salen de
    `impact_h3` y siguen siendo correctos, asi que tumbar el reporte entero
    durante un terremoto por un municipio sin nombre seria peor que decirlo.
    """
    con.execute("INSERT INTO impact_adm2 VALUES ('99999', 7.0, 500.0)")

    parte = check_quality(con)

    assert parte.bloqueantes == ()
    assert any("crosswalk_incompleto" in aviso for aviso in parte.avisos)
    parte.raise_if_blocking()  # no lanza


def test_una_tabla_ausente_no_se_confunde_con_un_assert_aprobado(con: Any) -> None:
    """No poder evaluar un assert no es lo mismo que aprobarlo.

    Es la diferencia entre "lo comprobe y esta bien" y "no lo comprobe", y
    tratarlas igual es como se publica un fallo en silencio.
    """
    con.execute("DROP TABLE impact_h3")

    parte = check_quality(con)

    assert any("no se pudo evaluar" in fallo for fallo in parte.bloqueantes)


def test_cada_assert_declara_su_severidad() -> None:
    """El tercer campo decide si el reporte sale o no: no puede quedar implicito."""
    for nombre, consulta, bloquea in QUALITY_ASSERTIONS:
        assert isinstance(bloquea, bool), f"{nombre} sin severidad declarada"
        assert consulta.strip().upper().startswith("SELECT"), nombre


def test_los_asserts_van_contra_las_tablas_del_corte() -> None:
    """Preguntan por lo que se va a publicar, no por el activo entero.

    El activo lo vigila `validate_layer_coverage` en P0, en su momento y con
    sus reglas. Estos miran las cifras de **este** evento.
    """
    for nombre, consulta, _ in QUALITY_ASSERTIONS:
        assert "impact_h3" in consulta or "impact_adm2" in consulta, nombre
        assert "exposure_h3" not in consulta, f"{nombre} mira el activo, no el corte"


def test_el_parte_vacio_es_limpio() -> None:
    assert QualityReport().limpio
    QualityReport().raise_if_blocking()  # no lanza
