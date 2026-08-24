"""Ventana geografica del sistema (RF-01)."""

from __future__ import annotations

import pytest

from pipelines.common.geo import LATAM_BBOX, BBox, haversine_km


@pytest.mark.parametrize(
    ("lon", "lat", "dentro"),
    [
        (-77.85, 6.42, True),  # Choco, Colombia
        (-96.5, 16.9, True),  # Oaxaca, Mexico
        (-103.0, 32.5, True),  # norte de Mexico, dentro del limite ampliado a 33N
        (-70.6, -33.4, True),  # Santiago de Chile
        (-68.3, -54.8, True),  # Ushuaia, cerca del limite sur
        (-177.2, -30.1, False),  # Kermadec: fuera por longitud
        (-116.0, 38.0, False),  # Nevada: fuera por latitud norte
        (-20.0, 10.0, False),  # Atlantico oriental: fuera por longitud este
    ],
)
def test_bbox_latam(lon: float, lat: float, dentro: bool) -> None:
    assert LATAM_BBOX.contains(lon, lat) is dentro


def test_bbox_incluye_bordes() -> None:
    b = LATAM_BBOX
    assert b.contains(b.lon_min, b.lat_min)
    assert b.contains(b.lon_max, b.lat_max)


def test_bbox_rechaza_limites_invertidos() -> None:
    with pytest.raises(ValueError, match="lon_min debe ser"):
        BBox(lon_min=10.0, lat_min=0.0, lon_max=-10.0, lat_max=1.0)


def test_haversine_conocida() -> None:
    # Bogota -> Medellin, ~ 240 km en linea recta.
    d = haversine_km(-74.07, 4.71, -75.56, 6.24)
    assert 235 < d < 250


def test_haversine_es_cero_en_el_mismo_punto() -> None:
    assert haversine_km(-74.07, 4.71, -74.07, 4.71) == pytest.approx(0.0)
