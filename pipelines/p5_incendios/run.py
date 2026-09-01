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
    #: Corrida de GFS que se uso para el viento. Vacia si no se consiguio
    #: ninguna, que **no** tumba la corrida: el fuego se publica igual. El
    #: viento es contexto util, no el dato; perderlo degrada, no invalida.
    ciclo_viento: str = ""
    #: Lo que el activo consumido no traia y salio como cero. No tumba la
    #: corrida —un cero declarado sigue siendo publicable— pero tiene que
    #: llegar a quien la lea, que es lo que no pasaba: `register_exposure_view`
    #: devolvia la lista y este llamador la tiraba.
    avisos: tuple[str, ...] = ()

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
    from .viento import descargar as descargar_viento

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
        # El retorno se descartaba, y aqui duele mas que en el sismo: las siete
        # columnas de cobertura del suelo son justo las que un activo anterior a
        # `col-v0.5` no trae, y sin este aviso un incendio en la Amazonia se
        # publica con "0 % arbolado" sin que nada lo distinga de una medida.
        ausentes = register_exposure_view(conexion, exposure_glob)
        if ausentes:
            result.avisos = (
                *result.avisos,
                f"El activo consumido no trae {len(ausentes)} columna(s) que esta capa sabe "
                f"publicar ({', '.join(ausentes)}); salen como cero y no estan medidas.",
            )

    celdas = cruzar_con_exposicion(conexion)

    # El viento va despues del cruce y no antes a proposito: si no hay celdas
    # no hay a que aplicarselo, y pedir GFS igualmente seria gastar una descarga
    # de 600 KB para tirarla.
    viento = descargar_viento(fetcher)
    if viento.ciego:
        # Aviso, no error. Que GFS no conteste deja el fuego sin contexto de
        # viento; que FIRMS no conteste deja el fuego sin fuego. No son lo
        # mismo y no pueden pintar igual en un log.
        _log.warning(
            "sin viento para esta corrida",
            extra={"context": {"ciclos_probados": viento.fallidos}},
        )
    result.ciclo_viento = viento.ciclo

    result.publicado = write_incendios(
        celdas, site_dir=site_dir, viento=viento, avisos=result.avisos
    )
    return result
