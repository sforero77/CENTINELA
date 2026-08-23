"""Rutas canonicas del repositorio.

El estado del sistema vive en archivos versionados por git (D: "Estado" en
§4.2), no en una base de datos viva. Estas rutas son el contrato de esa
decision.
"""

from __future__ import annotations

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


def event_state_path(usgs_id: str) -> Path:
    """Ruta del ``event_state`` de un evento (§3.3)."""
    return EVENTS_DIR / f"{usgs_id}.json"


def report_dir(usgs_id: str) -> Path:
    """Directorio de salidas publicadas de un evento (§4.3)."""
    return REPORTS_DIR / usgs_id


def ensure_workspace() -> None:
    """Crea los directorios efimeros si no existen."""
    for path in (WORK_DIR, CACHE_DIR, BUILD_DIR):
        path.mkdir(parents=True, exist_ok=True)
