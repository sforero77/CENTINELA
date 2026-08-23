"""CSV municipal con cabecera HXL (T1.3)."""

from __future__ import annotations

import csv
from pathlib import Path

from pipelines.p3_report.csv_out import HXL_HEADERS, write_adm2_csv


def test_cabecera_hxl_en_la_segunda_fila(tmp_path: Path) -> None:
    filas = [
        {"usgs_id": "us7000sint", "adm2_id": "27001", "nombre": "Quibdo", "pop_mmi7p": 118000.5}
    ]
    path = write_adm2_csv(filas, tmp_path / "adm2.csv")
    with path.open(encoding="utf-8") as fh:
        leidas = list(csv.reader(fh))
    assert leidas[0] == list(HXL_HEADERS)
    assert leidas[1] == list(HXL_HEADERS.values())
    assert leidas[2][leidas[0].index("nombre")] == "Quibdo"


def test_cifras_exactas_no_redondeadas(tmp_path: Path) -> None:
    """RF-06: la prosa redondea, el CSV nunca."""
    path = write_adm2_csv([{"adm2_id": "27001", "pop_mmi7p": 118000.5}], tmp_path / "a.csv")
    assert "118000.5" in path.read_text(encoding="utf-8")


def test_columnas_desconocidas_se_ignoran(tmp_path: Path) -> None:
    path = write_adm2_csv([{"adm2_id": "27001", "columna_rara": 1}], tmp_path / "a.csv")
    assert "columna_rara" not in path.read_text(encoding="utf-8")
