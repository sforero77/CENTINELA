"""Manifests de vintages y su lint (§2.4, RNF-04)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

from pipelines.common.licensing import Bucket
from pipelines.common.manifest import Manifest, lint_manifest


def _fuente(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "id": "ghs",
        "layer": "pop_ghs",
        "url": "https://example.org/ghs.zip",
        "license": "EC-reuse-attribution",
        "vintage": "R2023A-E2025",
        "sha256": "a" * 64,
    }
    return base | overrides


def _manifest(*fuentes: dict[str, Any]) -> dict[str, Any]:
    return {
        "manifest_id": "test-v1",
        "iso3": "COL",
        "generated_utc": "2026-08-23T00:00:00Z",
        "sources": list(fuentes) or [_fuente()],
    }


def _cargar(tmp_path: Path, data: dict[str, Any]) -> Manifest:
    (tmp_path / "COL.yaml").write_text(yaml.safe_dump(data), encoding="utf-8")
    return Manifest.load("COL", tmp_path)


def test_manifest_limpio(tmp_path: Path) -> None:
    manifest = _cargar(tmp_path, _manifest())
    assert lint_manifest(manifest) == []
    assert manifest.bucket is Bucket.CORE


def test_vintage_flotante_es_error(tmp_path: Path) -> None:
    problemas = lint_manifest(_cargar(tmp_path, _manifest(_fuente(vintage="latest"))))
    assert any("vintage flotante" in p for p in problemas)


def test_fuente_nc_es_error(tmp_path: Path) -> None:
    """GEM es CC BY-NC-SA: no puede entrar al activo que consume el reporte."""
    nc = _fuente(id="gem", license="CC-BY-NC-SA-4.0")
    problemas = lint_manifest(_cargar(tmp_path, _manifest(nc)))
    assert any("fuente NC" in p for p in problemas)


def test_url_no_reconocida_es_error(tmp_path: Path) -> None:
    problemas = lint_manifest(_cargar(tmp_path, _manifest(_fuente(url="/local/ruta"))))
    assert any("url no reconocida" in p for p in problemas)


def test_sha256_faltante_es_solo_aviso(tmp_path: Path) -> None:
    problemas = lint_manifest(_cargar(tmp_path, _manifest(_fuente(sha256=""))))
    assert problemas and all("(aviso)" in p for p in problemas)


def test_ids_duplicados(tmp_path: Path) -> None:
    problemas = lint_manifest(_cargar(tmp_path, _manifest(_fuente(), _fuente())))
    assert any("duplicado" in p for p in problemas)


def test_manifest_inexistente(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        Manifest.load("XXX", tmp_path)


def test_manifest_de_colombia_pasa_el_lint() -> None:
    """El manifest real del repo no puede tener errores, solo avisos."""
    manifest = Manifest.load("COL")
    errores = [p for p in lint_manifest(manifest) if "(aviso)" not in p]
    assert errores == []
    # Overture buildings es ODbL y contagia share-alike al activo completo.
    assert manifest.bucket is Bucket.ODBL
