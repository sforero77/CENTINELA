"""Rutas canonicas del repositorio.

El estado del sistema vive en archivos versionados por git (D: "Estado" en
§4.2), no en una base de datos viva. Estas rutas son el contrato de esa
decision.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Final

REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[2]

SCHEMAS_DIR: Final[Path] = REPO_ROOT / "schemas"
MANIFESTS_DIR: Final[Path] = REPO_ROOT / "data" / "manifests"
EVENTS_DIR: Final[Path] = REPO_ROOT / "events"
REPORTS_DIR: Final[Path] = REPO_ROOT / "reports"
SITE_DIR: Final[Path] = REPO_ROOT / "site"
FIXTURES_DIR: Final[Path] = REPO_ROOT / "tests" / "fixtures"

#: Directorio de trabajo efimero (descargas, intermedios). Nunca versionado.
WORK_DIR: Final[Path] = REPO_ROOT / "work"
CACHE_DIR: Final[Path] = REPO_ROOT / "data" / "cache"
BUILD_DIR: Final[Path] = REPO_ROOT / "data" / "build"


#: Forma de un identificador de evento de USGS (``us7000sint``, ``ci40000000``).
#: El id llega de un tercero y aqui se convierte en nombre de archivo: se valida
#: en el unico punto donde eso ocurre, no en cada llamador.
USGS_ID_RE: Final[re.Pattern[str]] = re.compile(r"^[A-Za-z0-9_-]{3,64}$")


def validate_usgs_id(usgs_id: str) -> str:
    """Devuelve el id si tiene forma valida.

    Raises:
        ValueError: si el id no podria ser un identificador de USGS. Un id con
            separadores de ruta escribiria fuera de ``events/``.
    """
    if not USGS_ID_RE.match(usgs_id):
        raise ValueError(f"usgs_id con forma invalida: {usgs_id!r}")
    return usgs_id


def event_state_path(usgs_id: str) -> Path:
    """Ruta del ``event_state`` de un evento (§3.3)."""
    return EVENTS_DIR / f"{validate_usgs_id(usgs_id)}.json"
