"""Un rebase que choca en los derivados se resuelve en un solo sitio, y bien.

Hallazgo #68 de la auditoria de septiembre de 2026: el manejador de conflictos
estaba escrito dos veces en bash —`impact.yml` y `trigger.yml`—, cada copia con
su lista de derivados, y ya habian divergido. Ahora vive en
`pipelines/common/derivados.py`. Estas pruebas lo ejecutan contra un rebase de
verdad en un repositorio temporal: lo que se comprueba es lo que queda en disco,
no lo que dice el codigo.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from pipelines.common.derivados import (
    DERIVADOS,
    OBSERVADOS,
    ConflictoNoResolubleError,
    en_conflicto,
    resolver,
)

pytestmark = pytest.mark.skipif(shutil.which("git") is None, reason="hace falta git")


def _git(raiz: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=raiz, capture_output=True, text=True, check=check)


def _escribir(raiz: Path, ruta: str, datos: Any) -> None:
    destino = raiz / ruta
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(datos, indent=2) + "\n", encoding="utf-8")


def _observado(usgs_id: str, horas: float = 1.0) -> dict[str, Any]:
    origen = (datetime.now(UTC) - timedelta(hours=horas)).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {
        "usgs_id": usgs_id,
        "mag": 4.8,
        "lon": -80.0,
        "lat": -5.0,
        "depth_km": 10.0,
        "lugar": "en el mar",
        "origen_utc": origen,
        "razon": "prueba",
        "iso3": "",
    }


def _status(*utcs: str) -> dict[str, Any]:
    return {"latidos": [{"utc": u, "revisados": 1, "relevantes": 0} for u in utcs]}


def _observados(*ids: str) -> dict[str, Any]:
    return {"generado_utc": "x", "eventos": [_observado(i) for i in ids]}


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """Un repositorio con los derivados comprometidos en una base comun."""
    raiz = tmp_path / "repo"
    raiz.mkdir()
    _git(raiz, "init", "-q", "-b", "main")
    _git(raiz, "config", "user.email", "prueba@example.org")
    _git(raiz, "config", "user.name", "prueba")
    _git(raiz, "config", "core.autocrlf", "false")
    (raiz / "events").mkdir()
    (raiz / "reports").mkdir()
    (raiz / "events" / ".keep").write_text("", encoding="utf-8")
    _escribir(raiz, "site/status.json", _status("2026-10-03T00:00:00Z"))
    _escribir(raiz, OBSERVADOS, _observados("us0base"))
    (raiz / "notas.txt").write_text("base\n", encoding="utf-8")
    _git(raiz, "add", "-A")
    _git(raiz, "commit", "-q", "-m", "base")
    return raiz


def _chocar(raiz: Path, remoto: dict[str, Any], propio: dict[str, Any]) -> None:
    """El remoto avanza en `main`; el commit propio se rebasa encima y choca."""
    _git(raiz, "checkout", "-q", "-b", "propio")
    for ruta, datos in propio.items():
        _escribir(raiz, ruta, datos) if ruta.endswith(".json") else (raiz / ruta).write_text(
            datos, encoding="utf-8"
        )
    _git(raiz, "commit", "-q", "-am", "propio")
    _git(raiz, "checkout", "-q", "main")
    for ruta, datos in remoto.items():
        _escribir(raiz, ruta, datos) if ruta.endswith(".json") else (raiz / ruta).write_text(
            datos, encoding="utf-8"
        )
    _git(raiz, "commit", "-q", "-am", "remoto")
    _git(raiz, "checkout", "-q", "propio")
    assert _git(raiz, "rebase", "main", check=False).returncode != 0, "el rebase no choco"


def test_el_estado_y_la_ventana_se_unen_en_vez_de_perder_un_lado(repo: Path) -> None:
    """El caso del vigia y P2 empujando a la vez.

    Antes se tomaba una sola version de `status.json` —se perdia un latido— y
    `observados.json` se rellenaba desde FDSN, que no sabe nada de lo que el
    otro lado hubiera anadido a mano: un cierre de `sin-pais`, por ejemplo.
    """
    _chocar(
        repo,
        remoto={
            "site/status.json": _status("2026-10-03T00:00:00Z", "2026-10-03T01:00:00Z"),
            OBSERVADOS: _observados("us0base", "us0remoto"),
        },
        propio={
            "site/status.json": _status("2026-10-03T00:00:00Z", "2026-10-03T02:00:00Z"),
            OBSERVADOS: _observados("us0base", "us0propio"),
        },
    )
    assert sorted(en_conflicto(repo)) == sorted(["site/status.json", OBSERVADOS])

    resueltos = resolver(repo)

    assert sorted(resueltos) == sorted(["site/status.json", OBSERVADOS])
    estado = json.loads((repo / "site/status.json").read_text(encoding="utf-8"))
    assert [x["utc"] for x in estado["latidos"]] == [
        "2026-10-03T00:00:00Z",
        "2026-10-03T01:00:00Z",
        "2026-10-03T02:00:00Z",
    ]
    ventana = json.loads((repo / OBSERVADOS).read_text(encoding="utf-8"))
    assert {e["usgs_id"] for e in ventana["eventos"]} == {"us0base", "us0remoto", "us0propio"}
    assert en_conflicto(repo) == []
    assert _git(repo, "-c", "core.editor=true", "rebase", "--continue").returncode == 0


def test_un_conflicto_que_no_es_de_un_derivado_no_se_toca(repo: Path) -> None:
    """Regenerar a ciegas descartaria el trabajo del otro job."""
    _chocar(repo, remoto={"notas.txt": "remoto\n"}, propio={"notas.txt": "propio\n"})

    with pytest.raises(ConflictoNoResolubleError, match=r"notas\.txt"):
        resolver(repo)
    assert "<<<<<<<" in (repo / "notas.txt").read_text(encoding="utf-8")


def test_sin_conflicto_no_hay_nada_que_resolver(repo: Path) -> None:
    """Llamarlo sin conflicto es un error del llamador, no un exito."""
    with pytest.raises(ConflictoNoResolubleError, match="ningun conflicto"):
        resolver(repo)


def test_la_lista_cubre_lo_que_los_dos_workflows_reescriben() -> None:
    assert set(DERIVADOS) == {"reports/index.json", "site/status.json", OBSERVADOS}
