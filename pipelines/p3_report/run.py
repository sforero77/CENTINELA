"""Orquestacion de P3: ``report.json`` -> todos los derivados.

Orden deliberado: primero el JSON (fuente de verdad), luego los derivados. Si
un derivado falla, el JSON ya esta en disco y el reporte puede re-renderizarse
sin recomputar el impacto.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from ..common.logging import get_logger
from ..common.paths import REPORTS_DIR, validate_usgs_id
from .csv_out import write_adm2_csv
from .markdown import render_markdown
from .model import Report
from .social import render_thread_text
from .static_map import MapVariant, render_map

_log = get_logger(__name__)

#: Indice que consume el visor estatico. Sin backend no hay forma de listar un
#: directorio: si este archivo no existe, la lista de eventos del sitio queda
#: vacia para siempre.
INDEX_FILENAME = "index.json"


def write_report_bundle(
    report: Report,
    adm2_rows: Iterable[Mapping[str, Any]],
    *,
    reports_root: Path | None = None,
    con_mapa: bool = True,
) -> dict[str, Path]:
    """Escribe el paquete completo de salidas de un evento y refresca el indice.

    Args:
        report: reporte ya calculado, fuente de verdad de todos los derivados.
        adm2_rows: filas municipales exactas para el CSV. Si traen la columna
            ``centroide`` (WKT ``POINT``) tambien alimentan el mapa.
        reports_root: raiz de ``reports/``. Los tests la redirigen.
        con_mapa: renderiza las dos variantes del PNG. Se puede apagar en
            pruebas para no pagar el arranque de matplotlib.

    Returns:
        Mapa nombre-de-artefacto -> ruta escrita. El mapa PNG se agrega cuando
        T0.8 cierre; su ausencia no bloquea la publicacion del resto.
    """
    root = reports_root or REPORTS_DIR
    directory = root / validate_usgs_id(report.event.usgs_id)
    directory.mkdir(parents=True, exist_ok=True)

    escritos: dict[str, Path] = {}
    escritos["report_json"] = report.save(directory / "report.json")

    md_path = directory / "report.md"
    md_path.write_text(render_markdown(report), encoding="utf-8")
    escritos["report_md"] = md_path

    filas = list(adm2_rows)
    escritos["adm2_csv"] = write_adm2_csv(filas, directory / "adm2.csv")

    if con_mapa:
        for variante in MapVariant:
            try:
                escritos[f"mapa_{variante.value}"] = render_map(
                    report,
                    variante,
                    directory / f"mapa_{variante.value}.png",
                    municipios=filas,
                )
            except Exception as exc:  # el mapa es un derivado, no la verdad
                # Un fallo de render no puede tumbar la publicacion: el JSON y
                # el markdown ya estan en disco y son lo que importa.
                _log.warning(
                    "no se pudo renderizar el mapa",
                    extra={"context": {"variante": variante.value, "error": str(exc)}},
                )

    hilo_path = directory / "hilo.txt"
    hilo_path.write_text(render_thread_text(report), encoding="utf-8")
    escritos["hilo_txt"] = hilo_path

    escritos["index_json"] = rebuild_index(root)

    _log.info(
        "paquete de reporte escrito",
        extra={
            "context": {
                "usgs_id": report.event.usgs_id,
                "shakemap_version": report.inputs.shakemap_version,
                "preliminar": report.preliminar,
                "artefactos": sorted(escritos),
            }
        },
    )
    return escritos


def rebuild_index(reports_root: Path | None = None) -> Path:
    """Reconstruye ``reports/index.json`` a partir de los reportes en disco.

    Se reconstruye entero en vez de anexar: el indice es un derivado, y un
    derivado que se acumula termina divergiendo de lo que hay en el directorio.
    Los eventos van del mas reciente al mas antiguo.
    """
    root = reports_root or REPORTS_DIR
    entradas: list[dict[str, Any]] = []

    for path in sorted(root.glob("*/report.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            entradas.append(
                {
                    "usgs_id": data["event"]["usgs_id"],
                    "mag": data["event"]["mag"],
                    "lugar": data["event"]["lugar"],
                    "utc": data["event"]["utc"],
                    "shakemap_version": data["inputs"]["shakemap_version"],
                    "preliminar": bool(data.get("preliminar", False)),
                    "generado_utc": data.get("generado_utc", ""),
                }
            )
        except (OSError, ValueError, KeyError) as exc:
            # Un reporte corrupto no puede tumbar el indice de todos los demas.
            _log.warning(
                "reporte ilegible, excluido del indice",
                extra={"context": {"path": str(path), "error": str(exc)}},
            )

    entradas.sort(key=lambda e: str(e["utc"]), reverse=True)
    destino = root / INDEX_FILENAME
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(entradas, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return destino
