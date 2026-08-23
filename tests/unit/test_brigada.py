"""Brigada de imagen: esquema y guardias de publicacion (RF-10, §6.6)."""

from __future__ import annotations

import pytest

from pipelines.p4_brigada.protocol import (
    ValidationMetrics,
    WeightsLineage,
    gate_publication,
)
from pipelines.p4_brigada.schema import GEOPACKAGE_FIELDS, DamageClass, DamageFeature


def test_el_esquema_es_interoperable() -> None:
    """T2.3: las columnas deben coincidir con el GeoPackage de Microsoft."""
    columnas = [nombre for nombre, _ in GEOPACKAGE_FIELDS]
    assert columnas == [
        "gers_id",
        "geom",
        "damage_class",
        "confidence",
        "scene_id",
        "model_version",
    ]


def test_nube_y_desconocido_son_clases_de_primera() -> None:
    """Decir 'no se pudo ver' es informacion, no un hueco."""
    assert DamageClass.CLOUD in set(DamageClass)
    assert DamageClass.UNKNOWN in set(DamageClass)


def test_confianza_fuera_de_rango() -> None:
    with pytest.raises(ValueError, match="confidence"):
        DamageFeature("g1", DamageClass.DAMAGED, 1.4, "s1", "m1")


def test_metricas_bajo_umbral_bloquean_publicacion() -> None:
    metricas = ValidationMetrics(precision=0.70, recall=0.80, tp=70, fp=30, fn=18, tn=200)
    publicable, razon = gate_publication(metricas, WeightsLineage.LIMPIA)
    assert not publicable
    assert "Bloqueado" in razon


def test_pesos_contaminados_van_al_cubo_nc() -> None:
    """Un modelo afinado desde xBD hereda CC BY-NC-SA (T2.4)."""
    metricas = ValidationMetrics(precision=0.86, recall=0.80, tp=86, fp=14, fn=20, tn=200)
    publicable, destino = gate_publication(metricas, WeightsLineage.NC)
    assert publicable
    assert destino == "nc/"


def test_pesos_limpios_van_al_nucleo() -> None:
    metricas = ValidationMetrics(precision=0.86, recall=0.80, tp=86, fp=14, fn=20, tn=200)
    assert gate_publication(metricas, WeightsLineage.LIMPIA) == (True, "core/")
