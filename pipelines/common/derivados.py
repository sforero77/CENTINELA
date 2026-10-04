"""Resolver un rebase que choca en los ficheros derivados, en un solo sitio.

UN DERIVADO NO SE FUSIONA: SE REGENERA.

`impact.yml` y `trigger.yml` empujan a la misma rama y reescriben enteros los
mismos ficheros —el indice de reportes, la pagina de estado, la ventana de
observados—, asi que cuando coinciden el `git pull --rebase` conflicta siempre.
Paso de verdad al reemitir los dos mainshocks de Venezuela: el segundo murio con
«CONFLICT (content): Merge conflict in reports/index.json» y su reporte, ya
calculado, no llego a publicarse.

HASTA EL 3-OCT-2026 EL MANEJADOR ESTABA ESCRITO DOS VECES, EN BASH, Y YA HABIA
DIVERGIDO. Cada workflow tenia su copia de `regenerar_derivados()` con su propia
lista de derivados. `trigger.yml` no sabia del indice de reportes e
`impact.yml` no sabia de `observados.json`; el `checkout --theirs` que salva el
historial de latidos llego a una copia semanas despues que a la otra, y el
2-sep-2026 la copia atrasada dejo los dos derivados con marcadores de conflicto
en `main`: `/status` sirvio JSON invalido y el vigia se cayo detras. Hallazgo
#68 de la auditoria de septiembre de 2026.

Ahora la lista y las reglas viven aqui, y los dos workflows llaman a
`centinela resolver-derivados`. Lo vigila
`tests/unit/test_derivados_se_resuelven_en_un_sitio.py`.

Las reglas, una por fichero:

- `reports/index.json` se rehace de los `report.json` en disco.
- `site/status.json` se rehace de los `event_state`, con la **union** de los
  latidos de las dos versiones. Antes se tomaba una sola y se perdia un latido.
- `site/observados.json` es la **union** de las dos ventanas, podada. Antes
  `trigger.yml` la rellenaba desde FDSN —una llamada de red dentro del manejador
  de conflictos— y se perdia lo que el otro lado hubiera anadido: el evento en
  mar abierto que cierra `centinela sin-pais` no esta en ningun catalogo de
  sismos menores, y desaparecia.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any, Final

from .logging import get_logger
from .paths import REPO_ROOT

_log = get_logger(__name__)

INDICE: Final[str] = "reports/index.json"
ESTADO: Final[str] = "site/status.json"
OBSERVADOS: Final[str] = "site/observados.json"

#: Los ficheros que dos workflows reescriben enteros y que, por tanto, chocan.
DERIVADOS: Final[tuple[str, ...]] = (INDICE, ESTADO, OBSERVADOS)

#: Lo que deja git en un fichero con conflicto. Un derivado que lo conserve no
#: se publica, sea cual sea el motivo.
_MARCADORES: Final[tuple[str, ...]] = ("<<<<<<< ", ">>>>>>> ")


class ConflictoNoResolubleError(Exception):
    """Hay un conflicto que no es de derivados, o no lo hay, o no se pudo regenerar."""


def _git(raiz: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=raiz, capture_output=True, text=True, check=True, encoding="utf-8"
    ).stdout


def _version(raiz: Path, etapa: int, fichero: str) -> Any:
    """Una de las dos versiones en conflicto, parseada; ``None`` si no existe o no es JSON.

    En un rebase la etapa 2 es la rama sobre la que se reaplica (lo que ya esta
    en el remoto) y la 3 el commit propio que se reaplica.
    """
    try:
        return json.loads(_git(raiz, "show", f":{etapa}:{fichero}"))
    except (subprocess.CalledProcessError, ValueError):
        return None


def en_conflicto(raiz: Path = REPO_ROOT) -> list[str]:
    """Los ficheros con conflicto sin resolver en el arbol de trabajo."""
    return [x for x in _git(raiz, "diff", "--name-only", "--diff-filter=U").splitlines() if x]


def _latidos(datos: Any) -> list[dict[str, Any]]:
    filas = datos.get("latidos", []) if isinstance(datos, dict) else []
    return [f for f in filas if isinstance(f, dict)]


def _resolver_estado(raiz: Path) -> None:
    """Union de los latidos de los dos lados, y despues se regenera el resto."""
    from .status import write_status

    vistos: dict[str, dict[str, Any]] = {}
    for etapa in (2, 3):
        for latido in _latidos(_version(raiz, etapa, ESTADO)):
            vistos[str(latido.get("utc", ""))] = latido
    latidos = [vistos[k] for k in sorted(vistos)]
    # `write_status` lee el historial del propio fichero y se niega —con razon—
    # a reescribir uno con marcadores. Se le deja delante uno legible con los
    # latidos ya unidos, y el resto lo recalcula de los `event_state`.
    destino = raiz / ESTADO
    destino.write_text(json.dumps({"latidos": latidos}, ensure_ascii=False), encoding="utf-8")
    write_status(
        site_dir=raiz / "site",
        events_dir=raiz / "events",
        reports_root=raiz / "reports",
    )


def _resolver_observados(raiz: Path) -> None:
    """Union de las dos ventanas, podada: lo que cualquiera de los dos vio."""
    from ..p1_trigger.observados import eventos_de, fusionar, podar, write_observados

    remoto = eventos_de(_version(raiz, 2, OBSERVADOS))
    propio = eventos_de(_version(raiz, 3, OBSERVADOS))
    write_observados(podar(fusionar(remoto, propio)), site_dir=raiz / "site")


def _resolver_indice(raiz: Path) -> None:
    from ..p3_report.run import rebuild_index

    indice = rebuild_index(raiz / "reports")
    if indice.excluidos:
        raise ConflictoNoResolubleError(
            f"{len(indice.excluidos)} reporte(s) no se pudieron leer al rehacer el indice "
            f"({', '.join(indice.excluidos)}): publicarlo los quitaria del visor"
        )


def resolver(raiz: Path = REPO_ROOT) -> list[str]:
    """Regenera los derivados en conflicto y los deja anadidos al indice de git.

    Quien llama sigue con `git rebase --continue`. Levanta
    `ConflictoNoResolubleError` si no hay conflicto, si alguno no es de un
    derivado —regenerar a ciegas descartaria el trabajo del otro job— o si un
    derivado sigue con marcadores al terminar.
    """
    conflictos = en_conflicto(raiz)
    if not conflictos:
        raise ConflictoNoResolubleError("no hay ningun conflicto que resolver")
    ajenos = sorted(set(conflictos) - set(DERIVADOS))
    if ajenos:
        raise ConflictoNoResolubleError(
            f"conflicto en ficheros que no son derivados: {', '.join(ajenos)}. "
            "No se tocan: es trabajo de otro job."
        )

    # El indice va antes que el estado: la pagina de estado cuenta los reportes.
    reglas = {INDICE: _resolver_indice, OBSERVADOS: _resolver_observados, ESTADO: _resolver_estado}
    for fichero, regla in reglas.items():
        if fichero in conflictos:
            _log.info("derivado en conflicto: se regenera", extra={"context": {"fichero": fichero}})
            regla(raiz)

    # LA RED DE SEGURIDAD. Un fichero con marcadores no se publica, sea cual sea
    # el motivo: es preferible reintentar y quedarse en rojo —que se ve— a
    # servir un JSON que el visor no puede leer.
    for fichero in conflictos:
        texto = (raiz / fichero).read_text(encoding="utf-8")
        if any(linea.startswith(_MARCADORES) for linea in texto.splitlines()):
            raise ConflictoNoResolubleError(f"{fichero} conserva marcadores de conflicto")

    _git(raiz, "add", *conflictos)
    return conflictos
