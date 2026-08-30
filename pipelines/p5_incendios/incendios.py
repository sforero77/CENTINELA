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

#: Cuantas celdas se publican. El criterio del recorte vive en `_prioridad`:
#: primero todas las que tienen gente (por poblacion), y el resto por potencia
#: radiativa. Esta nota decia "ordenadas por potencia radiativa" mucho despues
#: de que ese dejara de ser el criterio — y de una nota desactualizada salio un
#: rotulo falso en el visor. Con 22.701 celdas en un dia normal, publicarlas
#: todas serian varios megabytes que el visor descarga en cada carga.
MAX_CELDAS: Final[int] = 4000

NOTA: Final[str] = (
    "Detecciones de satelite (VIIRS, 375 m) en las ultimas 24 horas, agregadas a "
    "celdas H3. Una deteccion no es un incendio: tres satelites sobre el mismo "
    "fuego producen tres detecciones. NO se estima area quemada — el propio "
    "FIRMS lo desaconseja, porque el muestreo espacial y temporal es irregular. "
    "La exposicion es la del activo de cada pais; una celda sin poblacion puede "
    "estar fuera de los paises cubiertos, no vacia."
)


#: Sobre que arde. Es la pregunta que convierte "hay fuego" en informacion.
#:
#: Un foco sobre pastizal en agosto es rutina agricola; el mismo foco sobre
#: bosque no lo es. Sin este reparto el visor decia cuantas celdas arden y
#: cuanta gente hay debajo, y no decia **que** esta ardiendo — que es lo que
#: separa un contador de un dato.
#:
#: Se pondera por potencia radiativa y no por numero de celdas: mil detecciones
#: debiles sobre cultivo no son lo mismo que cincuenta intensas sobre bosque
#: primario, y contar celdas las igualaria.
SUELOS: Final[tuple[tuple[str, str], ...]] = (
    ("arbolado_pct", "arbolado"),
    ("pastizal_pct", "pastizal"),
    ("cultivo_pct", "cultivo"),
    ("humedal_pct", "humedal"),
)


def _reparto_del_suelo(celdas: list[CeldaConFuego]) -> dict[str, Any]:
    """Que porcentaje de la energia del fuego cayo sobre cada tipo de suelo.

    Devuelve `{}` si ninguna celda trae cobertura del suelo: los activos
    anteriores a la Fase 1 no la tienen, y publicar ceros diria "no hay bosque"
    donde lo correcto es "no se midio". Es la misma regla que sostiene el resto
    del sistema.
    """
    con_suelo = [c for c in celdas if any(getattr(c, campo) > 0 for campo, _ in SUELOS)]
    if not con_suelo:
        return {}

    energia = sum(c.frp_suma for c in con_suelo) or 1.0

    def cuota(campo: str) -> float:
        propia = sum(c.frp_suma * getattr(c, campo) / 100.0 for c in con_suelo)
        return float(round(propia / energia * 100, 1))

    reparto: dict[str, Any] = {nombre: cuota(campo) for campo, nombre in SUELOS}
    reparto["celdas_medidas"] = len(con_suelo)
    reparto["celdas_sin_medir"] = len(celdas) - len(con_suelo)
    return reparto


def _prioridad(celdas: list[CeldaConFuego], max_celdas: int) -> list[CeldaConFuego]:
    """Las que se publican: **primero todas las que tienen gente**.

    Ordenar solo por potencia radiativa parecia lo natural y estaba al reves.
    Medido el 27-ago-2026 sobre los diecinueve activos: de 14.984 celdas con
    fuego, 3.760 tenian poblacion, y con el corte por FRP solo **636**
    sobrevivian. Los 3.124 restantes eran celdas con gente y fuego moderado,
    desplazadas por incendios enormes en Amazonia deshabitada.

    Este es un sistema de exposicion. Un fuego sin nadie cerca es informacion;
    un fuego con tres mil personas debajo es la razon de que el sistema exista,
    y no puede caerse de la lista porque arda menos.
    """
    con_gente = [c for c in celdas if c.pop > 0]
    sin_gente = [c for c in celdas if c.pop <= 0]
    con_gente.sort(key=lambda c: (-c.pop, -c.frp_suma))
    # El relleno despoblado tambien se ordena. Sin esto, el dia que las celdas
    # con gente no llenen el cupo, el resto entraba **en el orden en que DuckDB
    # las escupiera**: arbitrario. Encontrado el 30-ago-2026 auditando el
    # artefacto E2E — ese dia habia 5.244 celdas pobladas para 4.000 puestos y
    # el fallo no se manifestaba, que es exactamente cuando conviene arreglarlo.
    sin_gente.sort(key=lambda c: -c.frp_suma)
    return [*con_gente, *sin_gente][:max_celdas]


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
    publicadas = _prioridad(celdas, max_celdas)
    return {
        "schema": INCENDIOS_SCHEMA_ID,
        "generado_utc": utcnow_iso(),
        "ventana_horas": ventana_horas,
        "nota": NOTA,
        "suelo": _reparto_del_suelo(celdas),
        "totales": {
            "celdas": len(celdas),
            "celdas_publicadas": len(publicadas),
            "detecciones": sum(c.detecciones for c in celdas),
            "detecciones_baja": sum(c.detecciones_baja for c in celdas),
            "celdas_con_poblacion": sum(1 for c in celdas if c.pop > 0),
            "pop_en_celdas_con_fuego": round(sum(c.pop for c in celdas)),
            # Lo que el popup de una celda ya decia y el indicador no.
            #
            # Un hospital dentro de una celda con fuego activo es la cifra que
            # decide un traslado, y estaba solo para quien pulsara esa celda
            # concreta entre catorce mil. Mismo criterio que en el lado sismico:
            # el orden de un tablero lo fija para que sirve.
            "salud_en_celdas_con_fuego": sum(c.salud for c in celdas),
            "edu_en_celdas_con_fuego": sum(c.edu for c in celdas),
            "bld_en_celdas_con_fuego": sum(c.bld for c in celdas),
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
