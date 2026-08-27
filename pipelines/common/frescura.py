"""¿Lo que sirve la pagina publicada es lo que hay en el repositorio?

El 26-ago-2026 el visor llevaba **diecisiete horas** sirviendo datos viejos y
nada estaba en rojo. Un push hecho con `GITHUB_TOKEN` no dispara otros
workflows, asi que `site.yml` no corria: los dos workflows en verde, el
artefacto correcto commiteado, y la pagina congelada en el latido de las 02:53.

Salio a la luz porque una persona sintio un sismo, fue a mirar y pregunto. Esa
es exactamente la forma de fallo que este modulo existe para eliminar.

**Que vigila y que no.** Compara la pagina *publicada* con el repositorio, y
solo eso: detecta que el repositorio avanza y la pagina no. Si el vigia se
muriera, los dos se quedarian quietos a la vez y esto pasaria — de eso se ocupa
el latido al monitor externo (§6.5), que es un vigilante distinto para un fallo
distinto. Mezclarlos daria una alarma que no sabe decir cual de las dos cosas se
rompio.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final

from .logging import get_logger
from .paths import SITE_DIR

_log = get_logger(__name__)

#: Donde vive la pagina publicada.
SITIO_PUBLICADO: Final[str] = "https://sforero77.github.io/CENTINELA"

#: Cuanto puede ir la pagina por detras del repositorio antes de que sea un
#: fallo. El latido se commitea como mucho una vez por hora y el despliegue
#: tarda un par de minutos, asi que el retraso normal no llega a una hora. Tres
#: da margen para una demora del cron sin tolerar un dia congelado.
HORAS_DE_GRACIA: Final[float] = 3.0

#: Los ficheros que el visor lee y que tienen fecha propia dentro.
FICHEROS_CON_FECHA: Final[tuple[str, ...]] = (
    "status.json",
    "observados.json",
    "incendios.json",
)


class PaginaDesactualizadaError(Exception):
    """La pagina publicada quedo detras del repositorio."""


@dataclass(frozen=True, slots=True)
class Desfase:
    """Cuanto va la pagina por detras, para un fichero."""

    fichero: str
    en_el_repo: str
    en_la_pagina: str
    horas: float

    @property
    def preocupa(self) -> bool:
        return self.horas > HORAS_DE_GRACIA

    def __str__(self) -> str:
        return (
            f"{self.fichero}: repo {self.en_el_repo} · pagina {self.en_la_pagina} "
            f"({self.horas:.1f} h de desfase)"
        )


def _fecha(datos: dict[str, Any]) -> str:
    """La marca de tiempo que el fichero declara.

    Se lee `generado_utc` y no el mtime: el fichero se regenera en cada corrida
    aunque su contenido no cambie, asi que el mtime diria que todo esta fresco
    justo cuando no lo esta.
    """
    return str(datos.get("generado_utc", ""))


def _parse(ts: str) -> datetime | None:
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None


def comparar(
    fichero: str,
    en_el_repo: dict[str, Any],
    en_la_pagina: dict[str, Any],
) -> Desfase | None:
    """Desfase entre las dos copias de un fichero, o ``None`` si no se puede saber."""
    repo, pagina = _fecha(en_el_repo), _fecha(en_la_pagina)
    t_repo, t_pagina = _parse(repo), _parse(pagina)
    if t_repo is None or t_pagina is None:
        return None
    horas = max(0.0, (t_repo - t_pagina).total_seconds() / 3600)
    return Desfase(fichero=fichero, en_el_repo=repo, en_la_pagina=pagina, horas=horas)


def revisar(
    fetcher: Any,
    *,
    site_dir: Path | None = None,
    sitio: str = SITIO_PUBLICADO,
) -> list[Desfase]:
    """Compara cada fichero con fecha entre el repositorio y la pagina.

    Un fichero que no esta en la pagina todavia no es un desfase: acaba de
    nacer y el primer despliegue aun no ha corrido. Un fichero que no esta en el
    repositorio no es asunto de esta comprobacion.
    """
    raiz = site_dir or SITE_DIR
    desfases = []

    for fichero in FICHEROS_CON_FECHA:
        local = raiz / fichero
        if not local.exists():
            continue
        try:
            publicado = fetcher.get_json(f"{sitio.rstrip('/')}/{fichero}")
        except Exception as error:
            _log.warning(
                "no se pudo leer la pagina publicada",
                extra={"context": {"fichero": fichero, "error": str(error)}},
            )
            continue

        desfase = comparar(
            fichero,
            json.loads(local.read_text(encoding="utf-8")),
            publicado,
        )
        if desfase is not None:
            desfases.append(desfase)

    return desfases


def raise_if_stale(desfases: list[Desfase]) -> None:
    """Levanta si alguna copia publicada quedo demasiado atras.

    Es lo que convierte la medicion en una alarma. Medir y no levantar seria el
    patron que esta auditoria persigue desde el primer dia — y aqui con un giro
    especialmente feo, porque el vigilante que no avisa da **mas** confianza que
    no tener vigilante.
    """
    viejos = [d for d in desfases if d.preocupa]
    if not viejos:
        return
    detalle = "\n".join(f"  - {d}" for d in viejos)
    raise PaginaDesactualizadaError(
        "La pagina publicada quedo detras del repositorio:\n"
        f"{detalle}\n\n"
        "Causa mas probable: algo commiteo en site/ o reports/ y no republico "
        "el visor. Un push con GITHUB_TOKEN no dispara site.yml; hace falta "
        "`gh workflow run site.yml` tras el push."
    )


def resumen(desfases: list[Desfase]) -> str:
    """Linea por fichero, tambien cuando todo esta bien.

    Publicar el resultado del caso bueno es lo que permite distinguir "esta
    fresco" de "la comprobacion no llego a correr".
    """
    if not desfases:
        return "No se pudo comparar ningun fichero con la pagina publicada."
    ahora = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    lineas = [f"Frescura del visor · {ahora}"]
    lineas += [f"  {'ALERTA' if d.preocupa else 'ok'}  {d}" for d in desfases]
    return "\n".join(lineas)
