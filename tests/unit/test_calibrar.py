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


#: Un manifest recien escrito: declara referencia y tolerancia provisional, pero
#: todavia no ha medido nada. Es la forma que tiene un pais antes de su primer
#: build — y la que tenia Brasil despues de dos builds correctos.
MANIFEST_SIN_MEDIR = """\
manifest_id: bra-v0.2
iso3: BRA

referencia_oficial:
  poblacion_2025: 212812405
  fuente: "ONU, World Population Prospects"
  tolerancia_pct: 25.0
  nota: >-
    Tolerancia provisional hasta el primer build.
"""


def test_lo_medido_se_anade_cuando_la_clave_no_estaba(tmp_path: Path) -> None:
    """El fallo de Brasil: `aplicar` solo reescribia la clave si ya existia.

    Dos builds correctos —218.881.538 habitantes, desvio real del 2,85 %— y el
    manifest seguia con `tolerancia_pct: 25.0` y sin una cifra detras, mientras
    su propia nota afirmaba que la fija cada build. Con 25 % de tolerancia el
    assert de §6.4 aceptaba a Brasil con 55 millones de habitantes de menos.

    Y no era un caso de Brasil: **ningun manifest recien escrito trae la clave**,
    asi que le habria pasado a cada pais nuevo de Fase 1.
    """
    ruta = tmp_path / "BRA.yaml"
    ruta.write_text(MANIFEST_SIN_MEDIR, encoding="utf-8")
    cal = calibrar(_medicion("BRA", 218_881_538, 212_812_405, 2.8519), {"tolerancia_pct": 25.0})

    assert aplicar(ruta, cal, fecha="2026-08-28")
    texto = ruta.read_text(encoding="utf-8")
    assert "medido_ghs_pop: 218881538" in texto
    assert "tolerancia_pct: 3.35" in texto
    # Va junto a la tolerancia, que es como se leen: el margen y lo medido.
    lineas = texto.splitlines()
    i_tol = next(i for i, x in enumerate(lineas) if "tolerancia_pct:" in x)
    assert "medido_ghs_pop:" in lineas[i_tol + 1]
    # Y la prosa sigue entera.
    assert "Tolerancia provisional hasta el primer build." in texto


def test_sin_tolerancia_declarada_no_se_inventa_donde_ponerlo(tmp_path: Path) -> None:
    """Un manifest sin referencia oficial no tiene con que comparar lo medido.

    Anadir `medido_ghs_pop` suelto ahi seria una cifra sin guardian al lado, que
    es justo la forma en que este repositorio se ha mordido antes.
    """
    ruta = tmp_path / "XXX.yaml"
    ruta.write_text("manifest_id: xxx-v0.1\niso3: XXX\n", encoding="utf-8")
    cal = calibrar(_medicion("XXX", 1_000.0, 900.0, 11.1), {"tolerancia_pct": 2.0})

    aplicar(ruta, cal, fecha="2026-08-28")
    assert "medido_ghs_pop" not in ruta.read_text(encoding="utf-8")


def test_los_manifests_del_repo_declaran_lo_que_midieron() -> None:
    """Los diecinueve, sin excepcion.

    Una tolerancia sin la cifra que la justifica no se puede auditar: no hay
    forma de saber si es estrecha porque se midio o ancha porque nadie volvio.
    """
    import yaml

    from pipelines.common.paths import MANIFESTS_DIR

    for path in sorted(MANIFESTS_DIR.glob("*.yaml")):
        ref = yaml.safe_load(path.read_text(encoding="utf-8")).get("referencia_oficial") or {}
        assert ref.get("tolerancia_pct"), f"{path.name} no declara tolerancia"
        assert ref.get("medido_ghs_pop"), (
            f"{path.name} tiene tolerancia pero no dice que midio para fijarla"
        )
