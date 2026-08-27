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
lo que cada manifest declara hoy; si alguien anade, quita o renombra una fuente
sin subir la version, falla y dice exactamente que hacer.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
import yaml

MANIFIESTOS = Path(__file__).parent.parent.parent / "data" / "manifests"


def huella(fuentes: list[dict[str, object]]) -> str:
    """Resumen de **lo que se declara**, no de como esta escrito el fichero.

    Solo entran el id, la capa, la url y la licencia de cada fuente: es lo que
    determina que datos entran en el activo. Reordenar las claves de un YAML,
    corregir una nota o rellenar un `sha256` no cambia el resultado y no deberia
    obligar a una version nueva.
    """
    partes = sorted(
        f"{f.get('id')}|{f.get('layer')}|{f.get('url')}|{f.get('license')}" for f in fuentes
    )
    return hashlib.sha256("\n".join(partes).encode("utf-8")).hexdigest()[:16]


#: `iso3 -> (manifest_id, huella de sus fuentes)`, al 27-ago-2026.
#:
#: Para actualizarlo: sube el `manifest_id` del pais que cambio y pega aqui la
#: huella nueva que la prueba te imprime. Los dos pasos son el punto — si
#: bastara con uno, el cerrojo no cerraria nada.
ESPERADO: dict[str, tuple[str, str]] = {
    "ARG": ("arg-v0.2", "a043b452f81a054f"),
    "BOL": ("bol-v0.2", "e2da138cc7609a4b"),
    "BRA": ("bra-v0.2", "02eb073b9b4ef779"),
    "CHL": ("chl-v0.2", "a216e3205f769214"),
    "COL": ("col-v0.6", "e5985587c95049c9"),
    "CRI": ("cri-v0.2", "69746622b91d5a69"),
    "CUB": ("cub-v0.2", "4936b676690cd28c"),
    "DOM": ("dom-v0.2", "270a133236c7a961"),
    "ECU": ("ecu-v0.2", "bcc77c931d02bf52"),
    "GTM": ("gtm-v0.2", "b914b1df4681dfb6"),
    "HND": ("hnd-v0.2", "c56ff4198fac4e2a"),
    "MEX": ("mex-v0.2", "7631386829fc553e"),
    "NIC": ("nic-v0.2", "736f25e58ebddf04"),
    "PAN": ("pan-v0.2", "b4fbfe5a4d04f10a"),
    "PER": ("per-v0.2", "cd4004c973217402"),
    "PRY": ("pry-v0.2", "2ad5a8f1764f3cea"),
    "SLV": ("slv-v0.2", "8cb2482a0c0f8cfb"),
    "URY": ("ury-v0.2", "524127ccf993c526"),
    "VEN": ("ven-v0.2", "f4ae67113d00707b"),
}


def _leer(iso3: str) -> tuple[str, str, int]:
    datos = yaml.safe_load((MANIFIESTOS / f"{iso3}.yaml").read_text(encoding="utf-8"))
    fuentes = datos.get("sources") or []
    return str(datos["manifest_id"]), huella(fuentes), len(fuentes)


@pytest.mark.parametrize("iso3", sorted(ESPERADO))
def test_la_version_del_manifest_es_la_registrada(iso3: str) -> None:
    """Si cambian las fuentes, tiene que cambiar la version. Y al reves."""
    version, actual, cuantas = _leer(iso3)
    version_esperada, huella_esperada = ESPERADO[iso3]

    if not huella_esperada:
        pytest.skip(f"huella sin registrar; la de {iso3} es {actual} ({cuantas} fuentes)")

    assert (version, actual) == (version_esperada, huella_esperada), (
        f"{iso3} declara fuentes distintas a las registradas.\n"
        f"  registrado: {version_esperada}  huella {huella_esperada}\n"
        f"  ahora:      {version}  huella {actual}  ({cuantas} fuentes)\n"
        "Si el cambio es intencionado: sube el `manifest_id` y pega la huella "
        "nueva en ESPERADO. Los dos pasos, no uno."
    )


def test_ningun_pais_se_queda_fuera_del_cerrojo() -> None:
    """Un manifest nuevo sin entrada aqui no estaria vigilado por nadie.

    Es la forma silenciosa de saltarse este fichero: anadir Haiti y no
    registrarlo. La prueba pasaria y el cerrojo no cubriria el pais nuevo.
    """
    en_disco = {p.stem for p in MANIFIESTOS.glob("*.yaml")}

    assert en_disco == set(ESPERADO), f"sin registrar: {sorted(en_disco - set(ESPERADO))}"


def test_dos_paises_no_comparten_version() -> None:
    """Cada pais lleva su propio contador; un id repetido seria un copiar y pegar."""
    versiones = [v for v, _ in ESPERADO.values()]

    assert len(versiones) == len(set(versiones))
