"""`site/sin_alcance.json`: los sismos medidos que no alcanzaron a nadie en la clase VI.

POR QUE EXISTE (21-nov-2026, `report/2.0`). Todo sismo con ShakeMap publicaba un
reporte completo aunque sus cifras fueran todas cero: quince de treinta y nueve.
En el visor se leian como reportes rotos —ficha, isolineas, ni un hexagono—, y
el M6,7 de Carhuamayo (`pt26325050`) lo hizo evidente. Desde la 2.0, si ninguna
celda poblada llega a la clase VI (MMI 5,5) el evento pasa a `sin_alcance`, no
tiene reporte, y se enseña en el mapa como "visto, sin reporte" con la
intensidad que si alcanzo.

POR QUE NO VA EN `observados.json`. Ese fichero es una ventana movil de cinco
dias que P1 poda en cada corrida, y sus eventos son los que **no se midieron**.
Estos si se midieron, y un sismo de hace tres meses sin alcance sigue siendo un
resultado que el catalogo tiene que poder enseñar. Este fichero se reconstruye
entero desde `events/*.json`, sin fecha de generacion: es determinista, asi que
dos workflows que lo regeneran a la vez escriben lo mismo.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Final

from .constants import UMBRAL_CLASE
from .formatting import format_number_es
from .logging import get_logger
from .paths import EVENTS_DIR, SITE_DIR
from .state import EventState, EventStatus

_log = get_logger(__name__)

SIN_ALCANCE_FILENAME: Final[str] = "sin_alcance.json"
SIN_ALCANCE_SCHEMA_ID: Final[str] = "centinela/sin_alcance/1.0"


def razon_sin_alcance(estado: EventState) -> str:
    """La frase que el visor enseña junto a la estrella gris."""
    umbral = format_number_es(UMBRAL_CLASE[6], 1)
    version = estado.versiones_procesadas.shakemap
    con = f"con el ShakeMap v{version}" if version else "con el ShakeMap"
    if estado.mmi_max_poblado is not None:
        alcanzada = format_number_es(estado.mmi_max_poblado, 1)
        return (
            f"Se midió {con}: la población llegó a MMI {alcanzada}, por debajo de "
            f"la intensidad VI (MMI {umbral})"
        )
    return (
        f"Se midió {con}: la sacudida no llegó a zonas habitadas con intensidad VI (MMI {umbral})"
    )


def entrada(estado: EventState) -> dict[str, Any]:
    """Un evento `sin_alcance`, con los campos de `observados.json` y algo mas.

    Comparte forma con `EventoObservado` —el visor pinta las dos listas con la
    misma estrella gris y el mismo filtro de pais y de fecha— y añade
    `mmi_max_poblado` y `shakemap_version`, que son lo que distingue un sismo
    medido de uno que no se midio.
    """
    from ..p1_trigger.observados import pais_del_toponimo

    return {
        "usgs_id": estado.usgs_id,
        "mag": estado.mag,
        "lon": round(estado.lon, 4),
        "lat": round(estado.lat, 4),
        "depth_km": round(estado.depth_km, 1),
        "lugar": estado.lugar,
        "origen_utc": estado.origen_utc,
        "razon": razon_sin_alcance(estado),
        "iso3": pais_del_toponimo(estado.lugar),
        "mmi_max_poblado": estado.mmi_max_poblado,
        "shakemap_version": estado.versiones_procesadas.shakemap,
        "backtest": estado.backtest,
    }


def build_sin_alcance(events_dir: Path | None = None) -> dict[str, Any]:
    """El fichero entero, a partir de los estados en disco."""
    eventos = []
    for ruta in sorted((events_dir or EVENTS_DIR).glob("*.json")):
        try:
            estado = EventState.from_dict(json.loads(ruta.read_text(encoding="utf-8")))
        except (ValueError, KeyError, TypeError):
            continue
        if estado.estado is EventStatus.SIN_ALCANCE:
            eventos.append(entrada(estado))
    eventos.sort(key=lambda e: e["origen_utc"], reverse=True)
    return {
        "schema": SIN_ALCANCE_SCHEMA_ID,
        "nota": (
            "Sismos medidos con su ShakeMap en los que ninguna zona habitada llegó a "
            f"la intensidad VI (MMI {format_number_es(UMBRAL_CLASE[6], 1)}), la clase "
            "desde la que este sistema publica cifras. No tienen reporte: el cálculo "
            "corrió entero y no hay nadie que contar. Se vuelven a medir si USGS "
            "publica un ShakeMap nuevo."
        ),
        "eventos": eventos,
    }


def write_sin_alcance(events_dir: Path | None = None, site_dir: Path | None = None) -> Path:
    """Escribe `site/sin_alcance.json` desde los estados. Determinista."""
    destino = (site_dir or SITE_DIR) / SIN_ALCANCE_FILENAME
    destino.parent.mkdir(parents=True, exist_ok=True)
    datos = build_sin_alcance(events_dir)
    destino.write_text(json.dumps(datos, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _log.info("sin alcance publicados", extra={"context": {"eventos": len(datos["eventos"])}})
    return destino
