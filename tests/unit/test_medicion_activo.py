"""La medicion que acompana al activo en el Release.

Las cifras que fijan la tolerancia de cada manifest —`medido_ghs_pop`, el
desvio frente a la referencia oficial— se copiaban del log a mano. Copiar a
mano es como se desincronizan las cosas, y ademas obliga a bajar varios MB de
log por pais para leer tres numeros.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from pipelines.p0_exposure.build import MEDICION_FICHERO, write_measurement

RESUMEN: dict[str, Any] = {
    "celdas": 23_711,
    "pop_total": 7_015_516.586595267,
    "bld_count": 1_204_331,
    "health_count": 812,
    "built_m2": 401_233_100.0,
    "edu_count": 3_044,
    "road_km": 92_144.2,
    "municipios": 262,
    "celdas_marcadas": 1_988,
}
RESCATE = {"pop_rescatada": 112, "pop_total": 7_015_517, "pop_rescatada_pct": 0.002}


def _plan(tmp_path: Path) -> Any:
    salida = tmp_path / "iso3=PRY" / "layer=exposure"
    salida.mkdir(parents=True)
    return SimpleNamespace(
        iso3="PRY",
        salida=salida,
        manifest=SimpleNamespace(manifest_id="pry-v0.1"),
    )


def _referencia() -> Any:
    return SimpleNamespace(poblacion_2025=7_013_078, fuente="ONU, World Population Prospects")


def test_calcula_el_desvio_frente_a_la_referencia(tmp_path: Path) -> None:
    """Es el numero que decide la tolerancia del manifest; no se estima a ojo."""
    ruta = write_measurement(_plan(tmp_path), RESUMEN, rescate=RESCATE, referencia=_referencia())
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    assert ruta.name == MEDICION_FICHERO
    assert datos["referencia"]["desvio_pct"] == 0.0348
    assert datos["referencia"]["poblacion"] == 7_013_078


def test_lleva_la_fraccion_rescatada(tmp_path: Path) -> None:
    """Sin ella no se puede distinguir un rescate costero de una invasion.

    Chile rescata el 31 % de su poblacion y su cifra es correcta; Paraguay
    rescataba el 6,1 % y esa era toda su desviacion. El numero solo sirve si
    viaja junto al total.
    """
    ruta = write_measurement(_plan(tmp_path), RESUMEN, rescate=RESCATE, referencia=_referencia())
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    assert datos["rescate"]["pop_rescatada_pct"] == 0.002
    assert datos["resumen"]["pop_total"] == RESUMEN["pop_total"]


def test_sin_referencia_oficial_no_inventa_un_desvio(tmp_path: Path) -> None:
    """Un pais sin referencia declarada se mide igual, pero sin compararse."""
    ruta = write_measurement(_plan(tmp_path), RESUMEN, rescate=RESCATE, referencia=None)
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    assert "referencia" not in datos
    assert datos["iso3"] == "PRY"
    assert datos["manifest_id"] == "pry-v0.1"


def test_es_json_valido_y_legible(tmp_path: Path) -> None:
    """Se publica en el Release: tiene que poder leerlo una persona y un script."""
    ruta = write_measurement(_plan(tmp_path), RESUMEN, rescate=RESCATE, referencia=_referencia())
    texto = ruta.read_text(encoding="utf-8")
    assert texto.endswith("\n")
    assert "\n  " in texto  # indentado, no una sola linea
    assert json.loads(texto)["medido_utc"].endswith("Z")
