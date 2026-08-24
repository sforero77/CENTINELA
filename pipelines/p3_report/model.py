"""Modelo de ``report.json`` v1 (§3.4).

Esta estructura es un contrato publico: la consumen el visor, el paquete HDX y
cualquiera que descargue el JSON. Cambiarla incompatiblemente exige subir la
version del schema (``centinela/report/2.0``), no editar en sitio.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Self

from .. import PIPELINE_VERSION
from ..common.constants import DISCLAIMERS, REPORT_SCHEMA_ID
from ..common.state import utcnow_iso


@dataclass(frozen=True, slots=True)
class Evento:
    """Identificacion del sismo."""

    usgs_id: str
    mag: float
    depth_km: float
    utc: str
    lugar: str
    #: Nivel PAGER, referencia cruzada. Vacio si el producto no existe.
    pager_alert: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "usgs_id": self.usgs_id,
            "mag": self.mag,
            "depth_km": self.depth_km,
            "utc": self.utc,
            "lugar": self.lugar,
            "pager_alert": self.pager_alert,
        }


@dataclass(frozen=True, slots=True)
class Inputs:
    """Versiones exactas de los insumos consumidos (RNF-04)."""

    shakemap_version: int
    groundfailure_version: int
    exposure_manifest: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "shakemap_version": self.shakemap_version,
            "groundfailure_version": self.groundfailure_version,
            "exposure_manifest": self.exposure_manifest,
        }


@dataclass(frozen=True, slots=True)
class Totales:
    """Cifras nacionales por banda de intensidad (RF-05)."""

    pop_mmi6p: float = 0.0
    pop_mmi7p: float = 0.0
    pop_mmi8p: float = 0.0
    pop_65p_mmi7p: float = 0.0
    bld_mmi7p: float = 0.0
    #: Superficie construida detectada por satelite. Contrasta a bld_mmi7p:
    #: donde OSM no mapeo el barrio, esta cifra si lo ve.
    built_m2_mmi7p: float = 0.0
    health_mmi7p: float = 0.0
    edu_mmi7p: float = 0.0
    road_km_mmi7p: float = 0.0
    #: Troncal, autopista, primaria y secundaria. El resto —residencial,
    #: service, track— es la diferencia con road_km_mmi7p.
    road_km_principal_mmi7p: float = 0.0
    pop_ls_alta: float = 0.0
    pop_lq_alta: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "pop_mmi6p": self.pop_mmi6p,
            "pop_mmi7p": self.pop_mmi7p,
            "pop_mmi8p": self.pop_mmi8p,
            "pop_65p_mmi7p": self.pop_65p_mmi7p,
            "bld_mmi7p": self.bld_mmi7p,
            "built_m2_mmi7p": self.built_m2_mmi7p,
            "health_mmi7p": self.health_mmi7p,
            "edu_mmi7p": self.edu_mmi7p,
            "road_km_mmi7p": self.road_km_mmi7p,
            "road_km_principal_mmi7p": self.road_km_principal_mmi7p,
            "pop_ls_alta": self.pop_ls_alta,
            "pop_lq_alta": self.pop_lq_alta,
        }


@dataclass(frozen=True, slots=True)
class MunicipioTop:
    """Fila del ranking municipal."""

    adm2_id: str
    nombre: str
    mmi_max: float
    pop_mmi7p: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "adm2_id": self.adm2_id,
            "nombre": self.nombre,
            "mmi_max": self.mmi_max,
            "pop_mmi7p": self.pop_mmi7p,
        }


@dataclass(frozen=True, slots=True)
class Incertidumbre:
    """Banda de discrepancia y notas de calidad.

    "Nunca ocultar el vacio" es una regla del registro de riesgos: los huecos
    de exposicion se publican como notas, no se maquillan.
    """

    pop_discrepancia_pct: float = 0.0
    notas: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "pop_discrepancia_pct": self.pop_discrepancia_pct,
            "notas": list(self.notas),
        }


@dataclass(frozen=True, slots=True)
class Descargas:
    """Enlaces a los artefactos publicados."""

    geoparquet: str = ""
    pmtiles: str = ""
    csv_adm2: str = ""
    mapa_png: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "geoparquet": self.geoparquet,
            "pmtiles": self.pmtiles,
            "csv_adm2": self.csv_adm2,
            "mapa_png": self.mapa_png,
        }


@dataclass(frozen=True, slots=True)
class Report:
    """Reporte completo, serializable a ``report.json``."""

    event: Evento
    inputs: Inputs
    totales: Totales
    top_municipios: tuple[MunicipioTop, ...] = ()
    incertidumbre: Incertidumbre = field(default_factory=Incertidumbre)
    descargas: Descargas = field(default_factory=Descargas)
    #: True cuando aun no hay ShakeMap y el corte es por radios (RF-03).
    preliminar: bool = False
    #: Deltas frente a la version anterior del reporte (RF-04).
    changelog: tuple[str, ...] = ()
    schema: str = REPORT_SCHEMA_ID
    generado_utc: str = field(default_factory=utcnow_iso)
    pipeline_version: str = PIPELINE_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "event": self.event.to_dict(),
            "inputs": self.inputs.to_dict(),
            "preliminar": self.preliminar,
            "totales": self.totales.to_dict(),
            "top_municipios": [m.to_dict() for m in self.top_municipios],
            "incertidumbre": self.incertidumbre.to_dict(),
            "descargas": self.descargas.to_dict(),
            "changelog": list(self.changelog),
            "disclaimers": list(DISCLAIMERS),
            "generado_utc": self.generado_utc,
            "pipeline_version": self.pipeline_version,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2) + "\n"

    def save(self, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_json(), encoding="utf-8")
        return path

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            event=Evento(**data["event"]),
            inputs=Inputs(**data["inputs"]),
            totales=Totales(**data["totales"]),
            top_municipios=tuple(MunicipioTop(**m) for m in data.get("top_municipios", [])),
            incertidumbre=Incertidumbre(
                pop_discrepancia_pct=data["incertidumbre"]["pop_discrepancia_pct"],
                notas=tuple(data["incertidumbre"].get("notas", [])),
            ),
            descargas=Descargas(**data.get("descargas", {})),
            preliminar=bool(data.get("preliminar", False)),
            changelog=tuple(data.get("changelog", [])),
            schema=str(data.get("schema", REPORT_SCHEMA_ID)),
            generado_utc=str(data.get("generado_utc", "")),
            pipeline_version=str(data.get("pipeline_version", "")),
        )
