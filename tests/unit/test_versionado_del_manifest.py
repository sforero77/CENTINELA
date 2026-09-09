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
    corregir una nota o rellenar un `insumos_sha256` no cambia el resultado y no deberia
    obligar a una version nueva.
    """
    partes = sorted(
        f"{f.get('id')}|{f.get('layer')}|{f.get('url')}|{f.get('license')}" for f in fuentes
    )
    return hashlib.sha256("\n".join(partes).encode("utf-8")).hexdigest()[:16]


#: `iso3 -> (manifest_id, huella de sus fuentes)`, al 6-sep-2026.
#:
#: La subida a `v0.3` de los dieciocho paises es la declaracion de
#: `overture_divisions`: el build ya bajaba ese tema en todos ellos —de ahi
#: salen los poligonos de los vecinos que acotan el reparto— y ninguno lo
#: decia. Colombia se queda en `col-v0.6` porque era el unico que ya lo
#: declaraba, asi que su conjunto de fuentes no ha cambiado.
#:
#: Para actualizarlo: sube el `manifest_id` del pais que cambio y pega aqui la
#: huella nueva que la prueba te imprime. Los dos pasos son el punto — si
#: bastara con uno, el cerrojo no cerraria nada.
ESPERADO: dict[str, tuple[str, str]] = {
    "ARG": ("arg-v0.3", "70d3c95cfa496b03"),
    "BOL": ("bol-v0.3", "c3a86f50fa8c5541"),
    "BRA": ("bra-v0.3", "3168d7324958f004"),
    "CHL": ("chl-v0.3", "b1bd667980fa40c8"),
    "COL": ("col-v0.6", "e5985587c95049c9"),
    "CRI": ("cri-v0.3", "6965170670117816"),
    "CUB": ("cub-v0.3", "f62d7b7626cfa180"),
    "DOM": ("dom-v0.3", "5ffca9e588d6f446"),
    "ECU": ("ecu-v0.3", "38b7eeb8921d2e88"),
    "GTM": ("gtm-v0.3", "1880d72b5163f4f8"),
    "HND": ("hnd-v0.3", "dec27c59c77a2fca"),
    "MEX": ("mex-v0.3", "6d8f39e811591002"),
    "NIC": ("nic-v0.3", "dd9484042979329e"),
    "PAN": ("pan-v0.3", "a28d6765b9b0a859"),
    "PER": ("per-v0.3", "2994b46bc6915b70"),
    "PRY": ("pry-v0.3", "1de4f1ed9b66417a"),
    "SLV": ("slv-v0.3", "e000802279905565"),
    "URY": ("ury-v0.3", "ee01282f94534849"),
    "VEN": ("ven-v0.3", "69ea7f8df4e40b02"),
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
