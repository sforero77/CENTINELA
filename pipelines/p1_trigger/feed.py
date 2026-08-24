"""Lectura y parseo del feed GeoJSON de USGS (D7, §2.1)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Self

from ..common.constants import USGS_FEED_BASE
from ..common.http import Fetcher


class FeedContractError(Exception):
    """El feed no cumple el contrato esperado (RNF-03).

    Cuando esto ocurre el pipeline degrada a reporte preliminar y abre issue
    automatico; jamas publica datos corruptos.
    """


def feed_url(feed: str) -> str:
    """URL de un feed de resumen, p. ej. ``4.5_hour``."""
    return f"{USGS_FEED_BASE}/{feed}.geojson"


@dataclass(frozen=True, slots=True)
class EventCandidate:
    """Un evento tal como lo reporta el feed, antes de filtrar."""

    usgs_id: str
    mag: float
    lon: float
    lat: float
    depth_km: float
    lugar: str
    origen_utc: str
    detail_url: str
    tipo: str
    estado_revision: str
    #: Instante en que USGS actualizo el evento por ultima vez.
    actualizado_utc: str

    @classmethod
    def from_feature(cls, feature: dict[str, Any]) -> Self:
        """Construye el candidato desde una feature GeoJSON del feed.

        Raises:
            FeedContractError: si falta cualquier campo del contrato.
        """
        try:
            props: dict[str, Any] = feature["properties"]
            coords = feature["geometry"]["coordinates"]
            lon, lat, depth = float(coords[0]), float(coords[1]), float(coords[2])
            mag = props["mag"]
            if mag is None:
                raise FeedContractError(f"Evento sin magnitud: {feature.get('id')}")
            return cls(
                usgs_id=str(feature["id"]),
                mag=float(mag),
                lon=lon,
                lat=lat,
                depth_km=depth,
                lugar=str(props.get("place") or "ubicacion no reportada"),
                origen_utc=epoch_ms_to_iso(props["time"]),
                detail_url=str(props["detail"]),
                tipo=str(props.get("type", "earthquake")),
                estado_revision=str(props.get("status", "automatic")),
                actualizado_utc=epoch_ms_to_iso(props.get("updated", props["time"])),
            )
        except FeedContractError:
            raise
        except (KeyError, TypeError, ValueError, IndexError) as exc:
            raise FeedContractError(f"Feature del feed no cumple el contrato USGS: {exc}") from exc


def epoch_ms_to_iso(value: Any) -> str:
    """Epoch en milisegundos -> ISO-8601 UTC (§3.1)."""
    ms = int(value)
    return (
        datetime.fromtimestamp(ms / 1000, tz=UTC)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def parse_feed(payload: dict[str, Any]) -> list[EventCandidate]:
    """Parsea un feed completo.

    Las features individuales que rompen el contrato se descartan con
    excepcion propagada: preferimos fallar ruidosamente y degradar, antes que
    publicar un reporte con un evento mal leido.
    """
    if payload.get("type") != "FeatureCollection":
        raise FeedContractError(f"El feed no es una FeatureCollection: {payload.get('type')!r}")
    features = payload.get("features")
    if not isinstance(features, list):
        raise FeedContractError("El feed no trae lista 'features'")
    return [EventCandidate.from_feature(f) for f in features]


def fetch_feed(fetcher: Fetcher, feed: str) -> list[EventCandidate]:
    """Descarga y parsea un feed de resumen."""
    return parse_feed(fetcher.get_json(feed_url(feed)))
