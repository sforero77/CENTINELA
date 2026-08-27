"""Publicacion de la capa de incendios a `site/incendios.json`.

Mismo contrato que `observados.json` y `status.json`: id de esquema,
`generado_utc` en la raiz —que es lo que lee `frescura.py` para saber si la
pagina publicada se quedo atras— y una `nota` que dice en prosa **que no afirma
el dato**.

Esa nota no es decorativa. Es la unica linea que impide leer "detecciones" como
"incendios" y "celda con fuego" como "hectareas quemadas".
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any, Final

from ..common.logging import get_logger
from ..common.paths import SITE_DIR
from ..common.state import utcnow_iso
from .focos_h3 import CeldaConFuego

_log = get_logger(__name__)

INCENDIOS_FILENAME: Final[str] = "incendios.json"

INCENDIOS_SCHEMA_ID: Final[str] = "centinela/incendios/1.0"

#: Cuantas celdas se publican. Ordenadas por potencia radiativa acumulada, asi
#: que el corte se lleva la cola larga de detecciones debiles y aisladas, no lo
#: que importa. Con 22.701 celdas en un dia normal, publicarlas todas serian
#: varios megabytes que el visor tiene que descargar en cada carga.
MAX_CELDAS: Final[int] = 4000

NOTA: Final[str] = (
    "Detecciones de satelite (VIIRS, 375 m) en las ultimas 24 horas, agregadas a "
    "celdas H3. Una deteccion no es un incendio: tres satelites sobre el mismo "
    "fuego producen tres detecciones. NO se estima area quemada — el propio "
    "FIRMS lo desaconseja, porque el muestreo espacial y temporal es irregular. "
    "La exposicion es la del activo de cada pais; una celda sin poblacion puede "
    "estar fuera de los paises cubiertos, no vacia."
)


def build_incendios(
    celdas: list[CeldaConFuego],
    *,
    ventana_horas: int = 24,
    max_celdas: int = MAX_CELDAS,
) -> dict[str, Any]:
    """Arma el JSON que consume el visor.

    Los totales se calculan sobre **todas** las celdas, no sobre las publicadas.
    Recortar la lista para que quepa es razonable; recortar la suma nacional
    para que cuadre con la lista seria publicar una cifra falsa por comodidad.
    """
    publicadas = celdas[:max_celdas]
    return {
        "schema": INCENDIOS_SCHEMA_ID,
        "generado_utc": utcnow_iso(),
        "ventana_horas": ventana_horas,
        "nota": NOTA,
        "totales": {
            "celdas": len(celdas),
            "celdas_publicadas": len(publicadas),
            "detecciones": sum(c.detecciones for c in celdas),
            "detecciones_baja": sum(c.detecciones_baja for c in celdas),
            "celdas_con_poblacion": sum(1 for c in celdas if c.pop > 0),
            "pop_en_celdas_con_fuego": round(sum(c.pop for c in celdas)),
            "frp_total_mw": round(sum(c.frp_suma for c in celdas), 1),
        },
        "celdas": [asdict(c) for c in publicadas],
    }


def write_incendios(
    celdas: list[CeldaConFuego],
    *,
    site_dir: Path | None = None,
    ventana_horas: int = 24,
) -> Path:
    """Publica `site/incendios.json`."""
    destino = (site_dir or SITE_DIR) / INCENDIOS_FILENAME
    destino.parent.mkdir(parents=True, exist_ok=True)
    datos = build_incendios(celdas, ventana_horas=ventana_horas)
    destino.write_text(json.dumps(datos, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    _log.info("incendios publicados", extra={"context": datos["totales"]})
    return destino


def leer(site_dir: Path | None = None) -> dict[str, Any]:
    """Lo publicado hasta ahora. Un fichero ausente o corrupto no es un fallo."""
    destino = (site_dir or SITE_DIR) / INCENDIOS_FILENAME
    if not destino.exists():
        return {}
    try:
        datos: dict[str, Any] = json.loads(destino.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        _log.warning("incendios.json ilegible; se reconstruye", extra={"context": {}})
        return {}
    return datos
