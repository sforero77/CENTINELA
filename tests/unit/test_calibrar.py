"""Reajuste de la tolerancia del manifest con lo que midio el build.

La tolerancia del assert de §6.4 es el unico guardian contra que la poblacion
de un pais se mueva sin que nadie lo note, y solo vale lo estrecha que sea:
Paraguay la tenia en 7,5 % para acomodar un desvio de +6,59 % que resulto ser
un fallo del rescate de frontera. Corregido el rescate el desvio es +0,035 %, y
una tolerancia de 7,5 % ya no vigila nada.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from pipelines.p0_exposure.calibrar import (
    MARGEN_PUNTOS,
    TOLERANCIA_MINIMA,
    aplicar,
    calibrar,
    tolerancia_propuesta,
)


def _medicion(iso3: str, pop: float, referencia: float, desvio: float) -> dict[str, Any]:
    return {
        "iso3": iso3,
        "manifest_id": f"{iso3.lower()}-v0.1",
        "resumen": {"pop_total": pop},
        "referencia": {"poblacion": referencia, "fuente": "ONU", "desvio_pct": desvio},
    }


def test_estrechar_es_automatico() -> None:
    """El caso de Paraguay: de 7,5 % a algo que de verdad vigile."""
    cal = calibrar(_medicion("PRY", 7_015_517, 7_013_078, 0.035), {"tolerancia_pct": 7.5})
    assert cal.aplicable
    assert cal.tolerancia_propuesta == pytest.approx(0.54, abs=0.01)
    assert cal.tolerancia_propuesta < cal.tolerancia_vigente


def test_ensanchar_no_es_automatico() -> None:
    """Aflojar la alarma para que deje de sonar no se automatiza."""
    cal = calibrar(_medicion("XXX", 100.0, 90.0, 11.1), {"tolerancia_pct": 2.0})
    assert not cal.aplicable
    assert "aflojar la alarma" in cal.motivo_bloqueo


def test_un_desvio_que_cabe_no_es_una_alarma() -> None:
    """Caso real de Colombia y Mexico: la vigente ya es mas estrecha que la politica.

    3,0 % medido con 3,2 % vigente: el assert pasa. La politica de margen
    propondria 3,5 %, que ensancha, asi que no se toca — pero eso no es un
    problema que alguien deba mirar. Confundirlo con uno haria sonar la alarma
    cada trimestre sin motivo, y una alarma que suena sin motivo se ignora.
    """
    cal = calibrar(_medicion("XXX", 103.0, 100.0, 3.0), {"tolerancia_pct": 3.2})
    assert cal.tolerancia_propuesta == pytest.approx(3.5)
    assert not cal.aplicable
    assert not cal.necesita_decision
    assert "nada que hacer" in cal.motivo_bloqueo


def test_un_desvio_fuera_de_tolerancia_si_es_una_alarma() -> None:
    """La otra mitad: aqui el assert del build ya estaria fallando."""
    cal = calibrar(_medicion("XXX", 111.0, 100.0, 11.1), {"tolerancia_pct": 2.0})
    assert cal.necesita_decision
    assert "aflojar la alarma" in cal.motivo_bloqueo


def test_hay_un_suelo() -> None:
    """Una tolerancia de 0,05 % convertiria el assert en un generador de ruido."""
    assert tolerancia_propuesta(0.001) == TOLERANCIA_MINIMA


def test_el_margen_va_sobre_el_valor_absoluto() -> None:
    """Chile se desvia -0,80 %: el signo no cambia cuanta holgura hace falta."""
    assert tolerancia_propuesta(-0.80) == pytest.approx(0.80 + MARGEN_PUNTOS)
    assert tolerancia_propuesta(0.80) == tolerancia_propuesta(-0.80)


def test_sin_referencia_no_inventa_nada() -> None:
    cal = calibrar({"iso3": "XXX", "resumen": {"pop_total": 1.0}}, {"tolerancia_pct": 5.0})
    assert not cal.aplicable
    assert "no trae referencia" in cal.motivo_bloqueo


MANIFEST = """\
manifest_id: pry-v0.1
iso3: PRY

# Un comentario que explica de donde sale la referencia y que no se puede
# perder: es la mitad del valor de este fichero.
referencia_oficial:
  poblacion_2025: 7013078
  fuente: "ONU, World Population Prospects"
  tolerancia_pct: 7.5
  medido_ghs_pop: 7474922
  nota: >-
    MEDIDO EL 24-AGO-2026.
"""


def test_conserva_los_comentarios(tmp_path: Path) -> None:
    """Se edita linea a linea, no se re-serializa: un yaml.dump borra el porque.

    Los manifests llevan mas comentario que dato —de donde sale cada fuente,
    por que ese vintage, que se midio y cuando— y eso es la mitad de su valor.
    """
    ruta = tmp_path / "PRY.yaml"
    ruta.write_text(MANIFEST, encoding="utf-8")
    cal = calibrar(_medicion("PRY", 7_015_517, 7_013_078, 0.035), {"tolerancia_pct": 7.5})
    assert aplicar(ruta, cal, fecha="2026-08-24")
    texto = ruta.read_text(encoding="utf-8")
    assert "es la mitad del valor de este fichero" in texto
    assert "medido_ghs_pop: 7015517" in texto
    assert "tolerancia_pct: 0.54" in texto
    assert 'fuente: "ONU, World Population Prospects"' in texto


def test_una_calibracion_bloqueada_actualiza_lo_medido_pero_no_la_tolerancia(
    tmp_path: Path,
) -> None:
    """Registrar lo que se midio siempre; cambiar el guardian, no."""
    ruta = tmp_path / "XXX.yaml"
    ruta.write_text(
        MANIFEST.replace("tolerancia_pct: 7.5", "tolerancia_pct: 2.0"), encoding="utf-8"
    )
    cal = calibrar(_medicion("PRY", 9_000_000, 7_013_078, 28.3), {"tolerancia_pct": 2.0})
    assert not cal.aplicable
    aplicar(ruta, cal, fecha="2026-08-24")
    texto = ruta.read_text(encoding="utf-8")
    assert "medido_ghs_pop: 9000000" in texto
    assert "tolerancia_pct: 2.0" in texto
