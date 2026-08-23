"""``event_state``: la maquina de estados de un evento (§3.3).

Un archivo JSON por evento, versionado en git. Esto da tres cosas que una base
de datos viva no daria gratis: auditoria (``git log`` del evento), costo cero
(RNF-01) e idempotencia trivial ante reinicios del runner (RF-02).

Transiciones validas::

    detectado ──▶ preliminar ──▶ publicado ──▶ publicado (nueva version SM)
        │             │              │
        └─────────────┴──────────────┴──▶ degradado   (contrato USGS roto)
        └─────────────┴──────────────┴──▶ descartado  (fuera de alcance / retirado)
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any, Self

from .paths import event_state_path


class EventStatus(StrEnum):
    """Estado del ciclo de vida de un evento."""

    DETECTADO = "detectado"
    PRELIMINAR = "preliminar"
    PUBLICADO = "publicado"
    DEGRADADO = "degradado"
    DESCARTADO = "descartado"


_ALLOWED_TRANSITIONS: dict[EventStatus, frozenset[EventStatus]] = {
    EventStatus.DETECTADO: frozenset(
        {
            EventStatus.PRELIMINAR,
            EventStatus.PUBLICADO,
            EventStatus.DEGRADADO,
            EventStatus.DESCARTADO,
        }
    ),
    EventStatus.PRELIMINAR: frozenset(
        {
            EventStatus.PRELIMINAR,
            EventStatus.PUBLICADO,
            EventStatus.DEGRADADO,
            EventStatus.DESCARTADO,
        }
    ),
    # Un evento publicado se re-publica al aparecer ShakeMap v(n+1) (RF-04).
    EventStatus.PUBLICADO: frozenset(
        {EventStatus.PUBLICADO, EventStatus.DEGRADADO, EventStatus.DESCARTADO}
    ),
    EventStatus.DEGRADADO: frozenset(
        {EventStatus.PRELIMINAR, EventStatus.PUBLICADO, EventStatus.DESCARTADO}
    ),
    EventStatus.DESCARTADO: frozenset(),
}


class InvalidTransitionError(Exception):
    """Se intento una transicion de estado no permitida."""


def utcnow_iso() -> str:
    """Timestamp UTC ISO-8601 con segundos (§3.1: todo timestamp en UTC)."""
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True, slots=True)
class ProcessedVersions:
    """Ultima version consumida de cada producto USGS versionado (§2.1)."""

    shakemap: int = 0
    groundfailure: int = 0

    def to_dict(self) -> dict[str, int]:
        return {"shakemap": self.shakemap, "groundfailure": self.groundfailure}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            shakemap=int(data.get("shakemap", 0)),
            groundfailure=int(data.get("groundfailure", 0)),
        )


@dataclass(frozen=True, slots=True)
class EventState:
    """Estado persistido de un evento."""

    usgs_id: str
    estado: EventStatus
    mag: float
    lon: float
    lat: float
    depth_km: float
    lugar: str
    origen_utc: str
    versiones_procesadas: ProcessedVersions = field(default_factory=ProcessedVersions)
    timestamps: dict[str, str] = field(default_factory=dict)
    hashes: dict[str, str] = field(default_factory=dict)
    intentos_preliminar: int = 0
    notas: list[str] = field(default_factory=list)

    # -- transiciones -------------------------------------------------------

    def transition(self, nuevo: EventStatus, *, nota: str | None = None) -> EventState:
        """Devuelve un estado nuevo, validando la transicion.

        Raises:
            InvalidTransitionError: si el paso no esta permitido.
        """
        if nuevo not in _ALLOWED_TRANSITIONS[self.estado]:
            raise InvalidTransitionError(f"{self.estado} -> {nuevo} no permitida ({self.usgs_id})")
        stamps = dict(self.timestamps) | {nuevo.value: utcnow_iso()}
        notas = [*self.notas, nota] if nota else list(self.notas)
        return replace(self, estado=nuevo, timestamps=stamps, notas=notas)

    def needs_reprocessing(self, shakemap_version: int, groundfailure_version: int) -> bool:
        """¿Hay una version de producto mas nueva que la ya consumida? (RF-04)"""
        return (
            shakemap_version > self.versiones_procesadas.shakemap
            or groundfailure_version > self.versiones_procesadas.groundfailure
        )

    # -- (de)serializacion --------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        return {
            "usgs_id": self.usgs_id,
            "estado": self.estado.value,
            "mag": self.mag,
            "lon": self.lon,
            "lat": self.lat,
            "depth_km": self.depth_km,
            "lugar": self.lugar,
            "origen_utc": self.origen_utc,
            "versiones_procesadas": self.versiones_procesadas.to_dict(),
            "timestamps": dict(sorted(self.timestamps.items())),
            "hashes": dict(sorted(self.hashes.items())),
            "intentos_preliminar": self.intentos_preliminar,
            "notas": list(self.notas),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            usgs_id=str(data["usgs_id"]),
            estado=EventStatus(data["estado"]),
            mag=float(data["mag"]),
            lon=float(data["lon"]),
            lat=float(data["lat"]),
            depth_km=float(data["depth_km"]),
            lugar=str(data["lugar"]),
            origen_utc=str(data["origen_utc"]),
            versiones_procesadas=ProcessedVersions.from_dict(data.get("versiones_procesadas", {})),
            timestamps=dict(data.get("timestamps", {})),
            hashes=dict(data.get("hashes", {})),
            intentos_preliminar=int(data.get("intentos_preliminar", 0)),
            notas=list(data.get("notas", [])),
        )

    # -- persistencia -------------------------------------------------------

    def save(self, directory: Path | None = None) -> Path:
        """Escribe el estado de forma atomica y determinista.

        Determinista (claves ordenadas, indentacion fija) para que el diff de
        git muestre solo lo que realmente cambio.
        """
        path = (directory / f"{self.usgs_id}.json") if directory else event_state_path(self.usgs_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(
            json.dumps(self.to_dict(), ensure_ascii=False, indent=2, sort_keys=False) + "\n",
            encoding="utf-8",
        )
        tmp.replace(path)
        return path

    @classmethod
    def load(cls, usgs_id: str, directory: Path | None = None) -> Self | None:
        """Carga el estado, o ``None`` si el evento aun no se conoce."""
        path = (directory / f"{usgs_id}.json") if directory else event_state_path(usgs_id)
        if not path.exists():
            return None
        return cls.from_dict(json.loads(path.read_text(encoding="utf-8")))
