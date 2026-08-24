"""Manifests de vintages (§2.2, RNF-04).

Un manifest declara, por pais, exactamente que version de que fuente entro al
activo de exposicion: URL, licencia, fecha y hash. Es el eslabon que hace
re-derivable todo numero publicado: ``reporte -> manifest -> hashes de insumos``.

La regla dura: **nunca "latest"**. Overture publica release mensual y su STAC
apunta siempre al ultimo; fijar el release explicito es lo que hace que un
reporte de hace seis meses siga siendo reproducible.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, Self

import yaml
from jsonschema import Draft202012Validator

from .licensing import Bucket, LicenseViolationError, bucket_for, resolve_bucket
from .paths import MANIFESTS_DIR, SCHEMAS_DIR

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
    #: Nombre del dataset en HDX cuando la descarga se resuelve por su API en
    #: vez de por URL fija. Ver :mod:`pipelines.common.hdx`: la ruta real de un
    #: mismo dataset de HOTOSM cambia de forma segun el pais, asi que el
    #: identificador estable es el nombre, no la URL.
    hdx_dataset: str = ""
    #: Fragmento del nombre del recurso dentro del dataset. Hace falta cuando el
    #: dataset publica varios recursos del mismo formato: sin el se toma el
    #: primero, y en el COD-AB de Colombia el primer SHP son secciones urbanas.
    hdx_resource: str = ""
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
            hdx_dataset=str(data.get("hdx_dataset", "")),
            hdx_resource=str(data.get("hdx_resource", "")),
            notes=str(data.get("notes", "")),
        )


@dataclass(frozen=True, slots=True)
class Manifest:
    """Conjunto de fuentes fijadas para un pais y una version del activo."""

    manifest_id: str
    iso3: str
    generated_utc: str
    sources: tuple[Source, ...]
    #: Cifra oficial contra la que se valida el total nacional (assert §6.4).
    #: Vacio significa que el activo se construye sin esa red de seguridad, y
    #: el lint lo reporta como aviso.
    referencia_oficial: dict[str, Any] = field(default_factory=dict)

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
            referencia_oficial=dict(data.get("referencia_oficial") or {}),
        )

    @classmethod
    def load(cls, iso3: str, directory: Path | None = None) -> Self:
        """Carga ``data/manifests/<iso3>.yaml``."""
        base = directory or MANIFESTS_DIR
        path = base / f"{iso3.upper()}.yaml"
        if not path.exists():
            raise FileNotFoundError(f"No hay manifest para {iso3.upper()}: {path}")
        return cls.from_dict(yaml.safe_load(path.read_text(encoding="utf-8")))


@lru_cache(maxsize=1)
def _schema_validator() -> Draft202012Validator:
    """Validador del schema del manifest, cargado una sola vez."""
    schema = json.loads((SCHEMAS_DIR / "manifest.schema.json").read_text(encoding="utf-8"))
    return Draft202012Validator(schema)


def lint_manifest_file(path: Path) -> list[str]:
    """Valida un manifest en disco: primero su forma, luego su contenido.

    El orden importa. ``Manifest.from_dict`` colapsa el YAML a dataclasses y en
    el camino descarta lo que no reconoce; si el schema no se aplica antes, una
    clave mal escrita se volveria invisible en vez de ser un error.
    """
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        return [f"YAML invalido: {exc}"]
    if not isinstance(raw, dict):
        return ["El manifest no es un objeto YAML"]

    forma = [
        f"schema: {'.'.join(str(x) for x in error.path) or '(raiz)'}: {error.message}"
        for error in sorted(_schema_validator().iter_errors(raw), key=str)
    ]
    if forma:
        # Sin forma valida, el lint de contenido solo produciria ruido derivado.
        return forma
    return lint_manifest(Manifest.from_dict(raw))


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
        if source.hdx_dataset and "data.humdata.org" not in source.url:
            problems.append(
                f"[{source.id}] declara hdx_dataset pero su url no apunta a HDX: "
                f"la url debe ser la pagina estable del dataset, y la de descarga "
                f"se resuelve por la API en cada build"
            )
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
