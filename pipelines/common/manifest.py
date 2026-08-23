"""Manifests de vintages (§2.2, RNF-04).

Un manifest declara, por pais, exactamente que version de que fuente entro al
activo de exposicion: URL, licencia, fecha y hash. Es el eslabon que hace
re-derivable todo numero publicado: ``reporte -> manifest -> hashes de insumos``.

La regla dura: **nunca "latest"**. Overture publica release mensual y su STAC
apunta siempre al ultimo; fijar el release explicito es lo que hace que un
reporte de hace seis meses siga siendo reproducible.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Self

import yaml

from .licensing import Bucket, LicenseViolationError, bucket_for, resolve_bucket
from .paths import MANIFESTS_DIR

#: Valores prohibidos como "vintage": no fijan nada.
_FLOATING_VINTAGES = frozenset({"latest", "current", "rolling", ""})


@dataclass(frozen=True, slots=True)
class Source:
    """Una fuente fijada dentro de un manifest."""

    id: str
    layer: str
    url: str
    license: str
    vintage: str
    #: sha256 del insumo descargado. Vacio mientras la tarea de verificacion
    #: correspondiente siga pendiente (§8); el lint lo reporta como aviso.
    sha256: str = ""
    notes: str = ""

    @property
    def bucket(self) -> Bucket:
        return bucket_for(self.license)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        missing = {"id", "layer", "url", "license", "vintage"} - data.keys()
        if missing:
            raise ValueError(f"Fuente incompleta, faltan campos: {sorted(missing)}")
        return cls(
            id=str(data["id"]),
            layer=str(data["layer"]),
            url=str(data["url"]),
            license=str(data["license"]),
            vintage=str(data["vintage"]),
            sha256=str(data.get("sha256", "")),
            notes=str(data.get("notes", "")),
        )


@dataclass(frozen=True, slots=True)
class Manifest:
    """Conjunto de fuentes fijadas para un pais y una version del activo."""

    manifest_id: str
    iso3: str
    generated_utc: str
    sources: tuple[Source, ...]

    @property
    def bucket(self) -> Bucket:
        """Cubo resultante del activo construido con estas fuentes."""
        return resolve_bucket(s.license for s in self.sources)

    def by_layer(self, layer: str) -> tuple[Source, ...]:
        return tuple(s for s in self.sources if s.layer == layer)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            manifest_id=str(data["manifest_id"]),
            iso3=str(data["iso3"]).upper(),
            generated_utc=str(data["generated_utc"]),
            sources=tuple(Source.from_dict(s) for s in data.get("sources", [])),
        )

    @classmethod
    def load(cls, iso3: str, directory: Path | None = None) -> Self:
        """Carga ``data/manifests/<iso3>.yaml``."""
        base = directory or MANIFESTS_DIR
        path = base / f"{iso3.upper()}.yaml"
        if not path.exists():
            raise FileNotFoundError(f"No hay manifest para {iso3.upper()}: {path}")
        return cls.from_dict(yaml.safe_load(path.read_text(encoding="utf-8")))


def lint_manifest(manifest: Manifest) -> list[str]:
    """Valida un manifest. Devuelve la lista de problemas (vacia = limpio).

    Se ejecuta en CI (§7, mitigacion de "contaminacion de licencias") y como
    guardia previa a cada build de P0.
    """
    problems: list[str] = []
    seen: set[str] = set()

    for source in manifest.sources:
        if source.id in seen:
            problems.append(f"[{source.id}] id duplicado en el manifest")
        seen.add(source.id)

        try:
            bucket = source.bucket
        except LicenseViolationError as exc:
            problems.append(f"[{source.id}] {exc}")
            continue

        if source.vintage.strip().lower() in _FLOATING_VINTAGES:
            problems.append(
                f"[{source.id}] vintage flotante {source.vintage!r}: "
                f"fija el release explicito (RNF-04)"
            )
        if not source.url.startswith(("http://", "https://", "s3://", "az://")):
            problems.append(f"[{source.id}] url no reconocida: {source.url!r}")
        if bucket is Bucket.NC:
            problems.append(
                f"[{source.id}] fuente NC ({source.license}) en el manifest de exposicion: "
                f"pertenece al cubo 'nc/', no al activo que consume el reporte (§2.4)"
            )
        if not source.sha256:
            problems.append(f"[{source.id}] sin sha256: la trazabilidad queda incompleta (aviso)")

    if not manifest.sources:
        problems.append("El manifest no declara ninguna fuente")
    return problems
