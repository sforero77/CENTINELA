"""P3 completo: report.json -> md + csv + hilo."""

from __future__ import annotations

from pathlib import Path

from pipelines.p3_report.model import Evento, Inputs, MunicipioTop, Report, Totales
from pipelines.p3_report.run import write_report_bundle


def _reporte() -> Report:
    return Report(
        event=Evento("us7000sint", 6.9, 24.7, "2026-08-19T05:00:00Z", "Choco, Colombia"),
        inputs=Inputs(3, 2, "col-v0.1-draft"),
        totales=Totales(pop_mmi6p=1_240_000, pop_mmi7p=347_129, bld_mmi7p=96_500),
        top_municipios=(MunicipioTop("27001", "Quibdo", 7.4, 118_000),),
    )


def test_escribe_el_paquete_completo(tmp_path: Path) -> None:
    filas = [
        {"usgs_id": "us7000sint", "adm2_id": "27001", "nombre": "Quibdo", "pop_mmi7p": 118_000}
    ]
    escritos = write_report_bundle(_reporte(), filas, out_dir=tmp_path)
    assert set(escritos) == {"report_json", "report_md", "adm2_csv", "hilo_txt"}
    for path in escritos.values():
        assert path.exists() and path.stat().st_size > 0


def test_el_reporte_cabe_en_un_movil_3g(tmp_path: Path) -> None:
    """RNF-05: md + png < 500 KB. Aqui verificamos la parte de texto."""
    escritos = write_report_bundle(_reporte(), [], out_dir=tmp_path)
    assert escritos["report_md"].stat().st_size < 100_000
