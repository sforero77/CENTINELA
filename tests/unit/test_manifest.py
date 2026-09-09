"""Manifests de vintages y su lint (§2.4, RNF-04)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

from pipelines.common.licensing import Bucket
from pipelines.common.manifest import Manifest, lint_manifest, lint_manifest_file


def _fuente(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "id": "ghs",
        "layer": "pop_ghs",
        "url": "https://example.org/ghs.zip",
        "license": "EC-reuse-attribution",
        "vintage": "R2023A-E2025",
        "insumos_sha256": "a" * 64,
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


def test_digest_faltante_es_solo_aviso(tmp_path: Path) -> None:
    problemas = lint_manifest(_cargar(tmp_path, _manifest(_fuente(insumos_sha256=""))))
    assert problemas and all("(aviso)" in p for p in problemas)


def test_una_fuente_remota_no_reclama_digest(tmp_path: Path) -> None:
    """Overture y la cobertura del suelo nunca tocan el disco.

    No hay bytes que hashear, asi que pedirles un digest es pedir algo que no
    puede existir. Un aviso irresoluble por fuente son cuatro por pais y 76 en
    el repositorio: con ese ruido los que si son accionables dejan de leerse.
    """
    overture = _fuente(
        id="overture_buildings",
        layer="buildings",
        url="s3://overturemaps-us-west-2/release/2026-08-19.0/theme=buildings/type=building",
        license="ODbL-1.0",
        vintage="2026-08-19.0",
        insumos_sha256="",
    )
    landcover = _fuente(
        id="worldcover",
        layer="landcover",
        url="https://esa-worldcover.s3.eu-central-1.amazonaws.com/v200/2021/map/",
        license="CC-BY-4.0",
        vintage="2021",
        insumos_sha256="",
    )
    manifest = _cargar(tmp_path, _manifest(overture, landcover))
    assert all(s.se_lee_en_remoto for s in manifest.sources)
    assert not [p for p in lint_manifest(manifest) if "insumos_sha256" in p]


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


def test_el_lint_de_archivo_atrapa_una_clave_mal_escrita(tmp_path: Path) -> None:
    """Sin validacion de forma, `licence` se volveria invisible en vez de fallar."""
    fuente = _fuente()
    fuente["licence"] = fuente.pop("license")
    path = tmp_path / "COL.yaml"
    path.write_text(yaml.safe_dump(_manifest(fuente)), encoding="utf-8")

    problemas = lint_manifest_file(path)
    assert any("licence" in p for p in problemas)
    assert all(p.startswith("schema:") for p in problemas)


def test_el_lint_de_archivo_reporta_yaml_roto(tmp_path: Path) -> None:
    path = tmp_path / "COL.yaml"
    path.write_text("manifest_id: [sin cerrar\n", encoding="utf-8")
    assert any("YAML invalido" in p for p in lint_manifest_file(path))


def test_el_lint_de_archivo_llega_al_contenido(tmp_path: Path) -> None:
    """Con la forma correcta, el lint sigue hasta las reglas de licencia."""
    path = tmp_path / "COL.yaml"
    path.write_text(yaml.safe_dump(_manifest(_fuente(license="CC-BY-NC-SA-4.0"))), encoding="utf-8")
    assert any("fuente NC" in p for p in lint_manifest_file(path))


def test_el_manifest_real_pasa_el_lint_de_archivo() -> None:
    from pipelines.common.paths import MANIFESTS_DIR

    errores = [p for p in lint_manifest_file(MANIFESTS_DIR / "COL.yaml") if "(aviso)" not in p]
    assert errores == []
