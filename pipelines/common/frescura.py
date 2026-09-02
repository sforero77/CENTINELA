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

from .constants import SITIO_PUBLICADO
from .logging import get_logger
from .paths import SITE_DIR

_log = get_logger(__name__)

#: Donde vive la pagina publicada.


#: Cuanto puede ir la pagina por detras del repositorio antes de que sea un
#: fallo. El latido se commitea como mucho una vez por hora y el despliegue
#: tarda un par de minutos, asi que el retraso normal no llega a una hora. Tres
#: da margen para una demora del cron sin tolerar un dia congelado.
HORAS_DE_GRACIA: Final[float] = 3.0

#: Colecciones que el visor lee y que **no llevan fecha**: se comparan por su
#: contenido. `fichero -> clave que identifica cada elemento`.
#:
#: `reports/index.json` es lo mas importante que publica este sistema y hasta el
#: 27-ago-2026 nadie lo vigilaba. Estaba cubierto de rebote —P2 toca
#: `status.json` en el mismo commit, asi que un desfase de reportes desfasaba
#: tambien el latido— pero de rebote no es lo mismo que de frente: el dia que P2
#: deje de tocar `status.json`, la cobertura desaparece sin que nadie se entere.
#:
#: Y para un indice la pregunta correcta no es "cuanto hace" sino "¿estan los
#: mismos eventos?". Un reporte publicado que la pagina no lista es el fallo,
#: aunque el fichero se haya generado hace un minuto.
COLECCIONES: Final[dict[str, str]] = {"reports/index.json": "usgs_id"}

#: Cuantas horas puede llevar un fichero sin regenerarse antes de que sea un
#: problema. `fichero -> horas`.
#:
#: Esto detecta que algo se **congelo**, no que llegue tarde. Es una distincion
#: cara: `frescura` comparaba repositorio contra pagina y nada mas, asi que un
#: fichero de hace tres dias pasaba la revision sin protestar — los dos lados
#: viejos, cero desfase entre ellos.
#:
#: Fue exactamente lo que oculto que `incendios.yml` no se disparara nunca. El
#: workflow figuraba activo, el fichero estaba sincronizado, y la capa llevaba
#: horas sin actualizarse sin que nada lo dijera.
#:
#: Los umbrales son deliberadamente holgados —del orden de tres o cuatro veces
#: la cadencia buscada— porque GitHub estrangula los crones de este repositorio
#: y una alarma que salta por un retraso normal se aprende a ignorar. Lo que se
#: persigue aqui es el silencio de un dia, no el de una hora.
MAX_HORAS_SIN_REGENERAR: Final[dict[str, float]] = {
    "status.json": 12.0,
    "observados.json": 12.0,
    "incendios.json": 24.0,
}

#: Los ficheros que el visor lee y que tienen fecha propia dentro.
FICHEROS_CON_FECHA: Final[tuple[str, ...]] = (
    "status.json",
    "observados.json",
    "incendios.json",
)


@dataclass(frozen=True, slots=True)
class Ausentes:
    """Elementos que estan en el repositorio y no en la pagina."""

    fichero: str
    faltan: tuple[str, ...]
    en_el_repo: int
    en_la_pagina: int

    @property
    def preocupa(self) -> bool:
        return bool(self.faltan)

    def __str__(self) -> str:
        muestra = ", ".join(self.faltan[:4]) + ("…" if len(self.faltan) > 4 else "")
        return f"{self.fichero}: repo {self.en_el_repo} · pagina {self.en_la_pagina}" + (
            f" · no publicados: {muestra}" if self.faltan else ""
        )


@dataclass(frozen=True, slots=True)
class Congelado:
    """Un fichero que lleva demasiado tiempo sin regenerarse."""

    fichero: str
    generado_utc: str
    horas: float
    limite: float

    @property
    def preocupa(self) -> bool:
        return self.horas > self.limite

    def __str__(self) -> str:
        return (
            f"{self.fichero}: generado hace {self.horas:.1f} h "
            f"(limite {self.limite:.0f} h) · {self.generado_utc}"
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


def _elementos(datos: Any, clave: str) -> set[str]:
    """Ids de una coleccion, venga como lista o envuelta en un objeto."""
    filas = datos if isinstance(datos, list) else (datos or {}).get("eventos", [])
    return {str(f[clave]) for f in filas if isinstance(f, dict) and clave in f}


def revisar_colecciones(
    fetcher: Any,
    *,
    raiz: Path | None = None,
    sitio: str = SITIO_PUBLICADO,
) -> list[Ausentes]:
    """Compara, elemento a elemento, lo que el repositorio tiene y la pagina sirve.

    Solo mira en una direccion: lo que esta en el repositorio y **no** en la
    pagina. Al reves no es un fallo sino el estado normal justo despues de
    retirar un reporte, mientras el despliegue esta en vuelo.
    """
    base = raiz or SITE_DIR.parent
    ausentes = []

    for fichero, clave in COLECCIONES.items():
        local = base / fichero
        if not local.exists():
            continue
        try:
            publicado = fetcher.get_json(f"{sitio.rstrip('/')}/{fichero}")
        except Exception as error:
            _log.warning(
                "no se pudo leer la coleccion publicada",
                extra={"context": {"fichero": fichero, "error": str(error)}},
            )
            continue

        aqui = _elementos(json.loads(local.read_text(encoding="utf-8")), clave)
        alla = _elementos(publicado, clave)
        ausentes.append(
            Ausentes(
                fichero=fichero,
                faltan=tuple(sorted(aqui - alla)),
                en_el_repo=len(aqui),
                en_la_pagina=len(alla),
            )
        )

    return ausentes


def revisar_vejez(
    *,
    site_dir: Path | None = None,
    ahora: datetime | None = None,
) -> list[Congelado]:
    """Cuanto lleva cada fichero sin regenerarse, contra su propio limite.

    Mira **solo el repositorio**: si un fichero esta congelado ahi, la pagina
    tampoco tiene nada mejor que servir. Y no necesita red, asi que responde
    aunque el sitio publicado no conteste.
    """
    raiz = site_dir or SITE_DIR
    referencia = ahora or datetime.now(UTC)
    congelados = []

    for fichero, limite in MAX_HORAS_SIN_REGENERAR.items():
        local = raiz / fichero
        if not local.exists():
            continue
        try:
            datos = json.loads(local.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue

        generado = _fecha(datos)
        cuando = _parse(generado)
        if cuando is None:
            continue
        congelados.append(
            Congelado(
                fichero=fichero,
                generado_utc=generado,
                horas=max(0.0, (referencia - cuando).total_seconds() / 3600),
                limite=limite,
            )
        )

    return congelados


def raise_if_stale(desfases: list[Desfase | Ausentes | Congelado]) -> None:
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
        "Si el desfase es entre repositorio y pagina: algo commiteo en site/ o "
        "reports/ y no republico el visor — un push con GITHUB_TOKEN no dispara "
        "site.yml, hace falta `gh workflow run site.yml` tras el push. "
        "Si un fichero lleva horas sin regenerarse: su workflow no se esta "
        "disparando. Comprueba `gh run list --workflow=<el suyo>` y lanzalo a "
        "mano con `gh workflow run` mientras se investiga."
    )


def resumen(desfases: list[Desfase | Ausentes | Congelado]) -> str:
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
