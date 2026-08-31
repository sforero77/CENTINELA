"""Orquestacion de P5: FIRMS -> celdas H3 -> cruce con exposicion -> site/."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..common.geo import LATAM_BBOX, BBox
from ..common.logging import get_logger
from .firms import Foco, fetch_focos

_log = get_logger(__name__)


def focos_en(bbox: BBox, focos: list[Foco]) -> list[Foco]:
    """Detecciones dentro de una caja. Aparte para poder probarla sin red."""
    return [f for f in focos if bbox.contains(f.lon, f.lat)]


@dataclass(slots=True)
class IncendiosResult:
    """Resumen de una corrida."""

    leidos: int = 0
    en_latam: int = 0
    celdas: int = 0
    publicado: Path | None = None
    #: Paises cuyo activo se cargo para el cruce.
    paises: list[str] = field(default_factory=list)
    #: Ficheros de FIRMS que no se pudieron leer, y cuantos se pidieron.
    fallidos: list[str] = field(default_factory=list)
    pedidos: int = 0

    @property
    def ciego(self) -> bool:
        """No se pudo leer NADA de FIRMS. La corrida no puede salir en verde."""
        return self.pedidos > 0 and len(self.fallidos) >= self.pedidos


def run_incendios(
    fetcher: Any,
    *,
    bbox: BBox = LATAM_BBOX,
    exposure_glob: str = "",
    site_dir: Path | None = None,
    con: Any = None,
) -> IncendiosResult:
    """Una pasada completa de la capa de incendios.

    Args:
        fetcher: cliente HTTP (real o de fixtures).
        bbox: ventana geografica. Los CSV de FIRMS son regionales y traen de
            mas: Estados Unidos aparece en "Central_America".
        exposure_glob: patron de los parquet de exposicion. Vacio publica el
            fuego sin cruzar, que sigue siendo util y es honesto al decirlo.
        site_dir: destino (los tests lo redirigen).
        con: conexion DuckDB ya abierta.
    """
    from ..p2_impact.exposure_join import connect
    from ..p2_impact.pipeline import register_exposure_view
    from .focos_h3 import cruzar_con_exposicion, registrar_focos
    from .incendios import write_incendios

    result = IncendiosResult()
    lectura = fetch_focos(fetcher)
    focos = lectura.focos
    result.leidos = len(focos)
    # La merma viaja con el resultado. Que FIRMS no responda es normal y
    # tolerable —por eso un fichero caido no tumba los otros cinco—, pero que
    # fallen los seis y la corrida salga verde no lo es.
    result.fallidos = list(lectura.fallidos)
    result.pedidos = lectura.pedidos
    if lectura.ciego:
        _log.error(
            "FIRMS no devolvio ni un fichero",
            extra={"context": {"pedidos": lectura.pedidos, "fallidos": lectura.fallidos}},
        )

    en_latam = focos_en(bbox, focos)
    result.en_latam = len(en_latam)
    if not en_latam:
        _log.warning("ninguna deteccion dentro de LATAM", extra={"context": {}})
        return result

    conexion = con if con is not None else connect()
    result.celdas = registrar_focos(conexion, en_latam)

    if exposure_glob:
        register_exposure_view(conexion, exposure_glob)

    celdas = cruzar_con_exposicion(conexion)
    result.publicado = write_incendios(celdas, site_dir=site_dir)
    return result
