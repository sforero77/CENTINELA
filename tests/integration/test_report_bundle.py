"""P3 completo: report.json -> md + csv + hilo + indice del visor."""

from __future__ import annotations

import json
from pathlib import Path

from pipelines.p3_report.model import Evento, Inputs, MunicipioTop, Report, Totales
from pipelines.p3_report.run import rebuild_index, write_report_bundle


def _reporte() -> Report:
    return Report(
        event=Evento("us7000sint", 6.9, 24.7, "2026-08-19T05:00:00Z", "Choco, Colombia"),
        inputs=Inputs(3, 2, "col-v0.1-draft"),
        totales=Totales(pop_mmi6p=1_240_000, pop_mmi7p=347_129, bld_mmi7p=96_500),
        top_municipios=(MunicipioTop("27001", "Quibdo", 7.4, 118_000),),
    )


def _otro_reporte() -> Report:
    return Report.from_dict(
        {
            **_reporte().to_dict(),
            "event": {
                "usgs_id": "us7000otro",
                "mag": 5.8,
                "depth_km": 40.0,
                "utc": "2026-09-01T12:00:00Z",
                "lugar": "Costa de Peru",
                "pager_alert": "",
            },
        }
    )


def test_escribe_el_paquete_completo(tmp_path: Path) -> None:
    filas = [
        {"usgs_id": "us7000sint", "adm2_id": "27001", "nombre": "Quibdo", "pop_mmi7p": 118_000}
    ]
    escritos = write_report_bundle(_reporte(), filas, reports_root=tmp_path)
    assert set(escritos) == {"report_json", "report_md", "adm2_csv", "hilo_txt", "index_json"}
    for path in escritos.values():
        assert path.exists() and path.stat().st_size > 0


def test_el_reporte_cabe_en_un_movil_3g(tmp_path: Path) -> None:
    """RNF-05: md + png < 500 KB. Aqui verificamos la parte de texto."""
    escritos = write_report_bundle(_reporte(), [], reports_root=tmp_path)
    assert escritos["report_md"].stat().st_size < 100_000


def test_el_indice_lista_el_evento(tmp_path: Path) -> None:
    """Sin backend, el visor no puede listar un directorio: vive del indice."""
    write_report_bundle(_reporte(), [], reports_root=tmp_path)
    indice = json.loads((tmp_path / "index.json").read_text(encoding="utf-8"))
    assert [e["usgs_id"] for e in indice] == ["us7000sint"]
    assert indice[0]["shakemap_version"] == 3


def test_el_indice_se_reconstruye_entero(tmp_path: Path) -> None:
    """Reconstruir, no anexar: un indice acumulado diverge del directorio."""
    write_report_bundle(_reporte(), [], reports_root=tmp_path)
    write_report_bundle(_otro_reporte(), [], reports_root=tmp_path)
    indice = json.loads((tmp_path / "index.json").read_text(encoding="utf-8"))
    assert [e["usgs_id"] for e in indice] == ["us7000otro", "us7000sint"]  # reciente primero


def test_un_reporte_corrupto_no_tumba_el_indice(tmp_path: Path) -> None:
    write_report_bundle(_reporte(), [], reports_root=tmp_path)
    roto = tmp_path / "us7000roto"
    roto.mkdir()
    (roto / "report.json").write_text("{ esto no es json", encoding="utf-8")

    indice = json.loads(rebuild_index(tmp_path).read_text(encoding="utf-8"))
    assert [e["usgs_id"] for e in indice] == ["us7000sint"]
