"""Muestreo de Ground Failure (§2.1, golden G3)."""

from __future__ import annotations

from pipelines.common.constants import GROUND_FAILURE_HIGH_PROB
from pipelines.p2_impact.ground_failure import (
    LANDSLIDE_MODEL,
    LIQUEFACTION_MODEL,
    GroundFailureCell,
    sample_rasters,
)

#: Celdas H3 r8 reales (Bogota y dos vecinas). Ids inventados no son validos y
#: `h3.int_to_str` los rechaza.
BOGOTA_R8 = 614299631221735423


def test_sin_celdas_no_hay_trabajo() -> None:
    assert sample_rasters(None, None, []) == {}


def test_sin_rasters_las_probabilidades_son_cero() -> None:
    """G3: la ausencia del producto no puede propagarse como NaN ni fallar."""
    celdas = sample_rasters(None, None, [BOGOTA_R8])
    assert celdas[BOGOTA_R8] == GroundFailureCell(BOGOTA_R8, 0.0, 0.0)


def test_umbral_de_probabilidad_alta() -> None:
    baja = GroundFailureCell(1, ls_prob=0.05, lq_prob=0.05)
    alta = GroundFailureCell(2, ls_prob=0.20, lq_prob=0.20)
    assert not baja.ls_alta and not baja.lq_alta
    assert alta.ls_alta and alta.lq_alta
    assert GroundFailureCell(3, GROUND_FAILURE_HIGH_PROB, 0.0).ls_alta


def test_los_modelos_vigentes_son_los_que_usgs_prefiere() -> None:
    """Verificado contra el producto real de Chocó (Ground Failure v7)."""
    assert LANDSLIDE_MODEL == "jessee_2018_model.tif"
    assert LIQUEFACTION_MODEL == "zhu_2017_general_model.tif"


def test_todas_las_celdas_reciben_respuesta() -> None:
    """El join posterior es LEFT, pero una celda perdida aqui seria un hueco."""
    import h3

    vecinas = [h3.str_to_int(c) for c in h3.grid_disk(h3.int_to_str(BOGOTA_R8), 1)]
    celdas = sample_rasters(None, None, vecinas)
    assert set(celdas) == set(vecinas)
