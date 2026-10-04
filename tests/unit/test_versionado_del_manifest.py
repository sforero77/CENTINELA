"""Cambiar lo que un manifest declara obliga a cambiar su version.

El 27-ago-2026 anadi ESA WorldCover como fuente a los diecinueve manifiestos y
**no subi ningun `manifest_id`**. El resultado:

    exposure-col-20260824  ->  18 columnas  ->  src_manifest: col-v0.5
    exposure-col-20260827  ->  25 columnas  ->  src_manifest: col-v0.5

Dos activos con contenido distinto y el mismo identificador. Un identificador
que no identifica es lo peor que le puede pasar a la trazabilidad de este
proyecto: cada reporte publicado guarda de que receta salio, y la receta cambio
sin cambiar de nombre. Quien audite un reporte de agosto no puede saber si el
activo que uso tenia cobertura del suelo o no.

Este fichero es un cerrojo, no una prueba de comportamiento. Guarda la huella de
lo que cada manifest declara; si alguien anade, quita o renombra una fuente sin
subir la version, falla y dice exactamente que hacer.

DESDE EL 3-OCT-2026 LAS HUELLAS VIVEN EN `data/manifests/recetas/<ISO3>.json`.
Estaban en una tabla de este fichero, y eso impedia que ningun proceso subiera
una version solo: el release de Overture caduca cada dos meses y pasarlo al
nuevo quedo a mano desde el primer dia. El registro solo crece —
`pipelines.common.recetas.registrar` se niega a dar otra huella a un id ya
anotado—, asi que la garantia es la misma y ahora la cumple tambien un workflow.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from pipelines.common.recetas import RECETAS_DIR, huella, registro

MANIFIESTOS = Path(__file__).parent.parent.parent / "data" / "manifests"
ISO3 = sorted(p.stem for p in MANIFIESTOS.glob("*.yaml"))


def _leer(iso3: str) -> tuple[str, str, int]:
    datos = yaml.safe_load((MANIFIESTOS / f"{iso3}.yaml").read_text(encoding="utf-8"))
    fuentes = datos.get("sources") or []
    return str(datos["manifest_id"]), huella(fuentes), len(fuentes)


@pytest.mark.parametrize("iso3", ISO3)
def test_la_version_del_manifest_es_la_registrada(iso3: str) -> None:
    """Si cambian las fuentes, tiene que cambiar la version. Y al reves."""
    version, actual, cuantas = _leer(iso3)
    anotadas = registro(iso3)

    assert version in anotadas, (
        f"{iso3} declara {version} y esa version no esta registrada "
        f"(huella {actual}, {cuantas} fuentes). Registrala con "
        f"`uv run centinela registrar-receta {iso3}`."
    )
    assert anotadas[version] == actual, (
        f"{iso3} declara fuentes distintas a las registradas para {version}.\n"
        f"  registrado: huella {anotadas[version]}\n"
        f"  ahora:      huella {actual}  ({cuantas} fuentes)\n"
        "Si el cambio es intencionado: sube el `manifest_id` y registra la receta "
        f"nueva con `uv run centinela registrar-receta {iso3}`. Los dos pasos, no uno."
    )


def test_ningun_pais_se_queda_fuera_del_cerrojo() -> None:
    """Un manifest nuevo sin registro no estaria vigilado por nadie.

    Es la forma silenciosa de saltarse este fichero: anadir Haiti y no
    registrarlo.
    """
    registrados = {p.stem for p in RECETAS_DIR.glob("*.json")}
    assert set(ISO3) <= registrados, f"sin registrar: {sorted(set(ISO3) - registrados)}"


def test_dos_paises_no_comparten_version() -> None:
    """Cada pais lleva su propio contador; un id repetido seria un copiar y pegar."""
    versiones = [_leer(i)[0] for i in ISO3]
    assert len(versiones) == len(set(versiones))


def test_cada_version_registrada_es_de_su_pais() -> None:
    for iso3 in ISO3:
        ajenas = [v for v in registro(iso3) if not v.startswith(f"{iso3.lower()}-v")]
        assert not ajenas, f"el registro de {iso3} trae versiones de otro pais: {ajenas}"
