"""La cobertura regional que el visor publica.

El tablero listaba eventos y nada mas, y con pocos reportes eso se lee como una
demo. Detras hay dieciocho paises con activo construido y medido — el hecho que
responde la pregunta de quien llega, *¿esto sirve para mi pais?*, y que no
aparecia en ninguna pantalla.

Lo que estas pruebas vigilan no es el formato: es que **la cobertura no pueda
prometer mas de lo que el sistema hizo**. Un tablero que dice "19 paises" cuando
hay 18 construidos deja de ser un tablero y pasa a ser un folleto.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from pipelines.common.cobertura import (
    NOMBRE_PAIS,
    build_cobertura,
    leer_cobertura,
    write_cobertura,
)

RAIZ = Path(__file__).parent.parent.parent
MANIFESTS = RAIZ / "data" / "manifests"


def _manifest(tmp_path: Path, iso3: str, **referencia: object) -> Path:
    datos: dict[str, object] = {
        "manifest_id": f"{iso3.lower()}-v0.1",
        "iso3": iso3,
        "generated_utc": "2026-08-25T00:00:00Z",
        "sources": [
            {
                "id": "pop",
                "layer": "population",
                "url": "https://ejemplo.org/pop.zip",
                "license": "CC-BY-4.0",
                "vintage": "R2023A",
                "sha256": "",
            }
        ],
    }
    if referencia:
        datos["referencia_oficial"] = referencia
    destino = tmp_path / f"{iso3}.yaml"
    destino.write_text(yaml.safe_dump(datos), encoding="utf-8")
    return destino


def test_un_pais_sin_medicion_no_cuenta_como_construido(tmp_path: Path) -> None:
    """`medido_ghs_pop` solo lo escribe un build de verdad.

    Es la unica senal en git de que un pais se construyo. Sin ella, la
    cobertura estaria afirmando un activo que nadie ha visto.
    """
    _manifest(tmp_path, "BRA", poblacion_2025=212_000_000, tolerancia_pct=25.0)

    paises = leer_cobertura(tmp_path)

    assert [p.construido for p in paises] == [False]
    assert paises[0].poblacion_medida == 0


def test_un_pais_medido_cuenta_y_calcula_su_desvio(tmp_path: Path) -> None:
    _manifest(
        tmp_path, "COL", poblacion_2025=53_000_000, medido_ghs_pop=52_620_466, tolerancia_pct=1.0
    )

    pais = leer_cobertura(tmp_path)[0]

    assert pais.construido
    assert pais.desvio_pct == pytest.approx(-0.72, abs=0.01)


def test_la_poblacion_de_la_malla_solo_suma_lo_construido(tmp_path: Path) -> None:
    """Sumar un pais sin activo inflaria la cifra con poblacion que no existe.

    Es el mismo error que el sistema persigue en todas partes: una cifra
    plausible que nadie midio.
    """
    _manifest(tmp_path, "COL", poblacion_2025=53_000_000, medido_ghs_pop=52_620_466)
    _manifest(tmp_path, "BRA", poblacion_2025=212_000_000)

    resumen = build_cobertura(tmp_path)["resumen"]

    assert resumen["poblacion_en_la_malla"] == 52_620_466
    assert resumen["paises_construidos"] == 1
    assert resumen["paises_con_manifest"] == 2


def test_el_peor_desvio_se_publica_aunque_incomode(tmp_path: Path) -> None:
    """Decir "todos dentro de tolerancia" sin decir cuanto no informa nada."""
    _manifest(tmp_path, "COL", poblacion_2025=53_000_000, medido_ghs_pop=52_620_466)
    _manifest(tmp_path, "VEN", poblacion_2025=28_516_896, medido_ghs_pop=29_924_657)

    assert build_cobertura(tmp_path)["resumen"]["peor_desvio_pct"] == pytest.approx(4.94, abs=0.01)


def test_sin_ningun_pais_construido_el_peor_desvio_es_nulo(tmp_path: Path) -> None:
    """Cero seria una mentira: no es que no haya desvio, es que no hay medicion."""
    _manifest(tmp_path, "BRA", poblacion_2025=212_000_000)

    assert build_cobertura(tmp_path)["resumen"]["peor_desvio_pct"] is None


def test_un_manifest_ilegible_no_oculta_a_los_demas(tmp_path: Path) -> None:
    _manifest(tmp_path, "COL", poblacion_2025=53_000_000, medido_ghs_pop=52_620_466)
    (tmp_path / "ZZZ.yaml").write_text("{ esto no es: un manifest }", encoding="utf-8")

    assert [p.iso3 for p in leer_cobertura(tmp_path)] == ["COL"]


def test_se_escribe_donde_el_visor_lo_busca(tmp_path: Path) -> None:
    _manifest(tmp_path, "COL", poblacion_2025=53_000_000, medido_ghs_pop=52_620_466)
    sitio = tmp_path / "site"

    destino = write_cobertura(manifests_dir=tmp_path, site_dir=sitio)

    assert destino == sitio / "cobertura.json"
    assert destino.is_file()


# --- Contra los manifests reales -------------------------------------------


def test_todo_manifest_del_repositorio_tiene_nombre_en_espanol() -> None:
    """Un codigo ISO3 no es un nombre. El visor esta en espanol."""
    sin_nombre = sorted({p.stem.upper() for p in MANIFESTS.glob("*.yaml")} - set(NOMBRE_PAIS))

    assert sin_nombre == [], f"Paises sin nombre en NOMBRE_PAIS: {sin_nombre}"


def test_la_cobertura_publicada_coincide_con_los_manifests() -> None:
    """`site/cobertura.json` es un derivado: no puede haber divergido.

    Si esta prueba falla, alguien construyo un pais y no regenero el fichero —
    y el visor esta publicando una cobertura vieja.
    """
    import json

    publicado = json.loads((RAIZ / "site" / "cobertura.json").read_text(encoding="utf-8"))
    recalculado = build_cobertura()

    assert publicado["resumen"] == recalculado["resumen"], (
        "site/cobertura.json esta desactualizado: corre `centinela cobertura`"
    )
    assert publicado["paises"] == recalculado["paises"]


def test_la_cifra_que_el_visor_presume_es_la_medida() -> None:
    """El titular de la seccion sale de sumar mediciones, no de una estimacion."""
    resumen = build_cobertura()["resumen"]

    medidos = sum(
        int(
            yaml.safe_load(p.read_text(encoding="utf-8"))
            .get("referencia_oficial", {})
            .get("medido_ghs_pop")
            or 0
        )
        for p in MANIFESTS.glob("*.yaml")
    )

    assert resumen["poblacion_en_la_malla"] == medidos
    assert resumen["poblacion_en_la_malla"] > 400_000_000, "LATAM no cabe en menos"
