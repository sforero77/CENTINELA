"""`ground_failure_usgs`: la alerta que publica USGS, al lado de la nuestra.

POR QUE HACE FALTA UN RELLENO. Los veintiun reportes del catalogo se emitieron
antes de que el reporte supiera citar esta alerta, y sus `report.json` no la
traen. Recomputar su impacto entero para obtenerla costaria bajar el activo de
cada pais y rehacer el join, cuando lo unico que falta son cuatro cadenas que
USGS sigue sirviendo en el detalle del evento.

Existe por la misma razon que `regenerar-mapas` y `contornos`: la vez anterior
que hubo que rehacer un derivado de todos los reportes publicados se hizo con un
script de usar y tirar, y la siguiente correccion dependia de que alguien
recordara como se hacia.

QUE ARREGLA EN LO PUBLICADO. El reporte del Choco decia «Deslizamiento: 0» junto
a la palabra «alta», en un M7,4 sobre la cordillera Occidental. El mismo
producto Ground Failure v7 de ese evento trae alerta **naranja** con ~1.400
personas expuestas. El cero es cierto —ninguna celda llega al umbral— y se lee
como "no hay exposicion a deslizamiento". Con la alerta de USGS al lado, no.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..common.logging import get_logger

_log = get_logger(__name__)

#: Detalle del evento en USGS. Es la misma URL que usa `backfill_contours`.
DETALLE_USGS = "https://earthquake.usgs.gov/fdsnws/event/1/query?eventid={evento}&format=geojson"


def backfill_ground_failure_alerts(
    usgs_id: str = "", *, fetcher: Any = None, reports_root: Path | None = None
) -> dict[str, Path]:
    """Escribe `ground_failure_usgs` en un `report.json` publicado, o en todos.

    Solo toca ese bloque: ninguna cifra propia del reporte se recalcula aqui, y
    un evento sin producto Ground Failure se salta sin escribir nada. El
    markdown se rehace despues con `centinela regenerar-textos`.

    Returns:
        ``usgs_id -> ruta`` de lo escrito.
    """
    from ..common.http import HttpFetcher
    from ..common.paths import REPORTS_DIR, validate_usgs_id
    from ..p2_impact.products import parse_products

    cliente = fetcher or HttpFetcher(timeout_s=120.0)
    raiz = reports_root or REPORTS_DIR
    directorios = (
        [raiz / validate_usgs_id(usgs_id)]
        if usgs_id
        else sorted(p.parent for p in raiz.glob("*/report.json"))
    )

    escritos: dict[str, Path] = {}
    for directorio in directorios:
        evento = directorio.name
        destino = directorio / "report.json"
        try:
            detalle = cliente.get_json(DETALLE_USGS.format(evento=evento))
            alertas = parse_products(detalle).ground_failure_alerts()
            if not alertas:
                _log.info(
                    "este evento no trae alertas de falla de terreno",
                    extra={"context": {"usgs_id": evento}},
                )
                continue
            datos = json.loads(destino.read_text(encoding="utf-8"))
            if datos.get("ground_failure_usgs") == alertas:
                continue
            # El bloque va donde lo pone el modelo, para que un `git diff` del
            # reporte no dependa del orden de escritura de este relleno.
            datos["ground_failure_usgs"] = alertas
            ordenado = {k: datos[k] for k in _orden(datos)}
            destino.write_text(
                json.dumps(ordenado, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
            escritos[evento] = destino
        except Exception as exc:  # una fuente caida no puede tumbar los demas
            _log.warning(
                "no se pudieron traer las alertas de falla de terreno",
                extra={"context": {"usgs_id": evento, "error": str(exc)}},
            )

    _log.info(
        "alertas de falla de terreno actualizadas",
        extra={"context": {"eventos": len(escritos), "de": len(directorios)}},
    )
    return escritos


def _orden(datos: dict[str, Any]) -> list[str]:
    """Las claves del reporte en el orden que emite el modelo.

    Las que el modelo no conoce se conservan al final: este relleno no es el
    sitio donde se decide que campos tiene un reporte publicado.
    """
    from .model import Report

    canonico = list(Report(**_minimo()).to_dict())
    conocidas = [k for k in canonico if k in datos]
    return conocidas + [k for k in datos if k not in canonico]


def _minimo() -> dict[str, Any]:
    from .model import Evento, Inputs, Totales

    return {
        "event": Evento(usgs_id="us0", mag=0.0, depth_km=0.0, utc="", lugar=""),
        "inputs": Inputs(shakemap_version=0, groundfailure_version=0, exposure_manifest=""),
        "totales": Totales(),
    }
