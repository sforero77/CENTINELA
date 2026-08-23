"""Orquestacion de P3: ``report.json`` -> todos los derivados.

Orden deliberado: primero el JSON (fuente de verdad), luego los derivados. Si
un derivado falla, el JSON ya esta en disco y el reporte puede re-renderizarse
sin recomputar el impacto.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from ..common.logging import get_logger
from ..common.paths import report_dir
from .csv_out import write_adm2_csv
from .markdown import render_markdown
from .model import Report
from .social import render_thread_text

_log = get_logger(__name__)


def write_report_bundle(
    report: Report,
    adm2_rows: Iterable[Mapping[str, Any]],
    *,
    out_dir: Path | None = None,
) -> dict[str, Path]:
    """Escribe el paquete completo de salidas de un evento.

    Returns:
        Mapa nombre-de-artefacto -> ruta escrita. El mapa PNG se agrega cuando
        T0.8 cierre; su ausencia no bloquea la publicacion del resto.
    """
    directory = out_dir or report_dir(report.event.usgs_id)
    directory.mkdir(parents=True, exist_ok=True)

    escritos: dict[str, Path] = {}
    escritos["report_json"] = report.save(directory / "report.json")

    md_path = directory / "report.md"
    md_path.write_text(render_markdown(report), encoding="utf-8")
    escritos["report_md"] = md_path

    escritos["adm2_csv"] = write_adm2_csv(adm2_rows, directory / "adm2.csv")

    hilo_path = directory / "hilo.txt"
    hilo_path.write_text(render_thread_text(report), encoding="utf-8")
    escritos["hilo_txt"] = hilo_path

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
