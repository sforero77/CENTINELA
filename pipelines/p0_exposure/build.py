"""Construccion del activo ``exposure_h3`` de un pais (O4, RF-08).

Punto de entrada de ``make country ISO=COL``. El pipeline es
descarga -> agregacion por capa -> join -> asserts de calidad -> parquet
particionado, y todo el linaje queda registrado en el manifest.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..common.logging import get_logger
from ..common.manifest import Manifest, lint_manifest
from .layers import LAYERS, LayerSpec, required_layers

_log = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class BuildPlan:
    """Plan de construccion resuelto contra un manifest."""

    iso3: str
    manifest: Manifest
    #: Capas que se van a construir, en orden.
    capas: tuple[LayerSpec, ...]
    salida: Path

    @property
    def capas_faltantes(self) -> tuple[LayerSpec, ...]:
        """Capas requeridas sin fuente declarada en el manifest."""
        declaradas = {source.layer for source in self.manifest.sources}
        return tuple(layer for layer in required_layers() if layer.id not in declaradas)


def plan_build(iso3: str, *, manifests_dir: Path | None = None, out_dir: Path) -> BuildPlan:
    """Resuelve el plan y valida el manifest antes de descargar nada.

    Fallar temprano importa: descargar GHS-POP y un release de Overture cuesta
    minutos y gigas; un manifest con una licencia NC colada o un vintage
    flotante debe detenerse antes de eso.

    Raises:
        ValueError: si el manifest no pasa el lint o faltan capas requeridas.
    """
    manifest = Manifest.load(iso3, manifests_dir)
    problemas = [p for p in lint_manifest(manifest) if "(aviso)" not in p]
    if problemas:
        raise ValueError(f"Manifest {iso3} invalido:\n  - " + "\n  - ".join(problemas))

    plan = BuildPlan(
        iso3=manifest.iso3,
        manifest=manifest,
        capas=LAYERS,
        salida=out_dir / f"iso3={manifest.iso3}" / "layer=exposure",
    )
    if plan.capas_faltantes:
        faltan = ", ".join(layer.id for layer in plan.capas_faltantes)
        raise ValueError(f"Manifest {iso3} no declara capas requeridas: {faltan}")

    _log.info(
        "plan de construccion resuelto",
        extra={
            "context": {
                "iso3": plan.iso3,
                "manifest": manifest.manifest_id,
                "cubo": manifest.bucket.value,
                "capas": len(plan.capas),
            }
        },
    )
    return plan


def build_country(iso3: str, *, manifests_dir: Path | None = None, out_dir: Path) -> Path:
    """Construye el activo completo de un pais.

    Implementacion pendiente (Fase 0, semana 2): descarga por capa segun
    :data:`pipelines.p0_exposure.layers.LAYERS`, agregacion a H3 r8, join,
    asserts de calidad de §6.4 y escritura de GeoParquet particionado Hive.
    """
    plan = plan_build(iso3, manifests_dir=manifests_dir, out_dir=out_dir)
    raise NotImplementedError(
        f"Pendiente: construccion de exposure_h3 para {plan.iso3} (Fase 0 semana 2). "
        f"El plan y la validacion de manifest ya son funcionales."
    )
