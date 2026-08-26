"""Sismos vistos y deliberadamente no despachados (ventana movil de 5 dias).

El 26-ago-2026 un M4,9 a 160 km bajo Jordan, Santander, se sintio en media
Colombia. El sistema lo vio doce minutos despues, lo evaluo, y decidio bien:
`M4.9 < umbral M5.5`. Pero esa decision solo existia en un log de CI, asi que
desde fuera **«lo vi y es inofensivo» y «estoy roto» se veian igual**.

Eso es lo que arregla este modulo. No baja el umbral —M5.5 sigue siendo el que
dispara un reporte— sino que hace visible lo que hay por debajo: el sistema
publica que estuvo mirando.

**Estos eventos no son reportes degradados.** Es una coleccion distinta con un
esquema que no tiene un solo campo de impacto, y es a proposito: si publicaramos
un `pop_mmi7p: 0`, quien lo leyera lo tomaria por una medicion. Ausencia de
medicion no es medicion de cero, y esa confusion es el modo de fallo caro de
todo este sistema.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Final

from ..common.logging import get_logger
from ..common.paths import SITE_DIR
from ..common.state import utcnow_iso

_log = get_logger(__name__)

#: Cuantos dias se conservan. Con ~3,1 sismos M4,5-5,5 al dia en LATAM son unos
#: quince puntos a la vez: una capa legible. La ventana corta tambien dice que
#: es la coleccion, «que esta pasando ahora» y no un archivo historico — para
#: eso esta el catalogo del USGS, que es la fuente de registro de estos sismos y
#: no nosotros.
DIAS_OBSERVADOS: Final[int] = 5

OBSERVADOS_FILENAME: Final[str] = "observados.json"

OBSERVADOS_SCHEMA_ID: Final[str] = "centinela/observados/1.0"


@dataclass(frozen=True, slots=True)
class EventoObservado:
    """Un sismo que el vigia vio y no despacho, con la razon.

    Los campos son los del catalogo de origen y nada mas. Que aqui no quepa una
    cifra de poblacion no es una omision: es el contrato.
    """

    usgs_id: str
    mag: float
    lon: float
    lat: float
    depth_km: float
    lugar: str
    origen_utc: str
    #: Por que no se despacho, en las palabras del filtro.
    razon: str

    @classmethod
    def desde_candidato(cls, candidate: Any, razon: str) -> EventoObservado:
        return cls(
            usgs_id=candidate.usgs_id,
            mag=round(float(candidate.mag), 1),
            lon=round(float(candidate.lon), 4),
            lat=round(float(candidate.lat), 4),
            depth_km=round(float(candidate.depth_km), 1),
            lugar=candidate.lugar,
            origen_utc=candidate.origen_utc,
            razon=razon,
        )


def _parse(ts: str) -> datetime | None:
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None


def podar(
    eventos: list[EventoObservado],
    *,
    ahora: datetime | None = None,
    dias: int = DIAS_OBSERVADOS,
) -> list[EventoObservado]:
    """Deja solo los de los ultimos ``dias``, del mas reciente al mas viejo.

    Un evento sin fecha legible se descarta: no se puede saber si caduco, y
    conservarlo indefinidamente es justo lo que la ventana existe para evitar.
    """
    limite = (ahora or datetime.now(UTC)) - timedelta(days=dias)
    vigentes = [
        (fecha, e)
        for e in eventos
        if (fecha := _parse(e.origen_utc)) is not None
        if fecha >= limite
    ]
    return [e for _, e in sorted(vigentes, key=lambda par: par[0], reverse=True)]


def fusionar(
    previos: list[EventoObservado],
    nuevos: list[EventoObservado],
) -> list[EventoObservado]:
    """Une lo ya publicado con lo de esta corrida, sin duplicar.

    Los feeds se solapan y el vigia corre cada hora: el mismo sismo se vuelve a
    ver muchas veces. Gana la version nueva, que puede traer la magnitud ya
    revisada por un humano.
    """
    por_id = {e.usgs_id: e for e in previos}
    por_id.update({e.usgs_id: e for e in nuevos})
    return list(por_id.values())


def leer(site_dir: Path | None = None) -> list[EventoObservado]:
    """Lo publicado hasta ahora. Un archivo ausente o corrupto no es un fallo."""
    destino = (site_dir or SITE_DIR) / OBSERVADOS_FILENAME
    if not destino.exists():
        return []
    try:
        datos = json.loads(destino.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        _log.warning("observados.json ilegible; se reconstruye", extra={"context": {}})
        return []
    return [EventoObservado(**e) for e in datos.get("eventos", []) if isinstance(e, dict)]


def write_observados(
    eventos: list[EventoObservado],
    *,
    site_dir: Path | None = None,
    ahora: datetime | None = None,
) -> Path:
    """Publica la ventana movil ya podada y ordenada."""
    destino = (site_dir or SITE_DIR) / OBSERVADOS_FILENAME
    destino.parent.mkdir(parents=True, exist_ok=True)
    vigentes = podar(eventos, ahora=ahora)
    datos = {
        "schema": OBSERVADOS_SCHEMA_ID,
        "generado_utc": utcnow_iso(),
        "ventana_dias": DIAS_OBSERVADOS,
        "nota": (
            "Sismos vistos por el vigia y no despachados: por debajo del umbral "
            "de reporte. No se midio su impacto — esto no es una estimacion de "
            "cero, es la ausencia de una medicion."
        ),
        "eventos": [asdict(e) for e in vigentes],
    }
    destino.write_text(json.dumps(datos, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _log.info("observados publicados", extra={"context": {"eventos": len(vigentes)}})
    return destino
