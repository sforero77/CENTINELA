"""El reporte declara el manifiesto que **consumio**, no el que le pasaron.

EL REPORTE PODIA MENTIR SOBRE SU PROPIO INSUMO. `impact.yml` lee
`data/manifests/<ISO3>.yaml` del repositorio y se lo pasa a P2 por `--manifest`;
P2 lo escribia tal cual. El activo, en cambio, es un Release, y puede ser mas
viejo que el YAML: el reporte declaraba `col-v0.6` habiendose calculado contra un
activo `col-v0.5`.

Rompe RNF-04 por donde mas duele —la trazabilidad de un reporte a sus insumos— y
dejaba ciego a `rezago.py`, que comparaba el manifiesto del reporte contra
`data/manifests/`: el repositorio contra si mismo.
"""

from __future__ import annotations

from typing import Any

import duckdb
import pytest

from pipelines.p2_impact.pipeline import manifiesto_del_activo


def _con(valores: list[str] | None) -> Any:
    """Una conexion con una vista `exposure` como la que deja P2."""
    con = duckdb.connect()
    if valores is None:
        con.execute("CREATE VIEW exposure AS SELECT 1 AS h3_08")
        return con
    filas = ", ".join(f"('{v}')" for v in valores)
    con.execute(f"CREATE VIEW exposure AS SELECT * FROM (VALUES {filas}) t(src_manifest)")
    return con


def test_manda_el_del_activo_y_no_el_declarado() -> None:
    """El caso real: el YAML del repositorio va por delante del Release."""
    assert manifiesto_del_activo(_con(["col-v0.5"]), "col-v0.6") == "col-v0.5"


def test_si_coinciden_no_pasa_nada() -> None:
    assert manifiesto_del_activo(_con(["col-v0.6"]), "col-v0.6") == "col-v0.6"


def test_un_activo_sin_la_columna_cae_al_declarado() -> None:
    """Los activos anteriores a Fase 1 no traen `src_manifest`.

    Fallar ahi seria romper el calculo por un campo de trazabilidad. Se avisa y
    se sigue, que es lo mismo que hace `COLUMNAS_OPCIONALES` con `built_m2`.
    """
    assert manifiesto_del_activo(_con(None), "col-v0.6") == "col-v0.6"


def test_dos_manifiestos_en_el_mismo_activo_no_se_eligen_a_dedo() -> None:
    """Un join contra dos recetas no es un reporte: son dos sumados.

    Elegir uno publicaria una trazabilidad falsa para la mitad de las celdas.
    """
    with pytest.raises(ValueError, match="dos recetas"):
        manifiesto_del_activo(_con(["col-v0.5", "col-v0.6"]), "col-v0.6")


def test_sin_declarado_tambien_sale_el_del_activo() -> None:
    """`--manifest` tiene default vacio: correr P2 a mano no deja el campo vacio."""
    assert manifiesto_del_activo(_con(["per-v0.2"]), "") == "per-v0.2"
