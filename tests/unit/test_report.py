"""Modelo y render del reporte (§3.4, RF-05, RF-06)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from pipelines.common.constants import DISCLAIMERS
from pipelines.common.paths import SCHEMAS_DIR
from pipelines.p3_report.markdown import render_markdown
from pipelines.p3_report.model import (
    Descargas,
    Evento,
    Incertidumbre,
    Inputs,
    MunicipioTop,
    Report,
    Totales,
)
from pipelines.p3_report.social import MAX_CHARS, render_thread, render_thread_text


@pytest.fixture
def reporte() -> Report:
    return Report(
        event=Evento(
            usgs_id="us7000sint",
            mag=6.9,
            depth_km=24.7,
            utc="2026-08-19T05:00:00Z",
            lugar="38 km al W de Bahia Solano, Choco, Colombia",
            pager_alert="orange",
        ),
        inputs=Inputs(
            shakemap_version=3, groundfailure_version=2, exposure_manifest="col-v0.1-draft"
        ),
        totales=Totales(
            pop_mmi6p=1_240_000,
            pop_mmi7p=347_129,
            pop_mmi8p=41_200,
            pop_65p_mmi7p=28_400,
            bld_mmi7p=96_500,
            health_mmi7p=42,
            edu_mmi7p=310,
            road_km_mmi7p=1_820,
            pop_ls_alta=88_000,
            pop_lq_alta=12_500,
        ),
        top_municipios=(
            MunicipioTop("27075", "Bahia Solano", 8.1, 9_400),
            MunicipioTop("27001", "Quibdo", 7.4, 118_000),
        ),
        incertidumbre=Incertidumbre(
            pop_discrepancia_pct=14.2,
            notas=("Cobertura de edificaciones incompleta en zona rural dispersa.",),
        ),
        descargas=Descargas(geoparquet="https://example.org/e.parquet", csv_adm2="adm2.csv"),
    )


@pytest.fixture
def validator() -> Draft202012Validator:
    schema = json.loads((SCHEMAS_DIR / "report-1.0.schema.json").read_text(encoding="utf-8"))
    return Draft202012Validator(schema)


def test_el_json_cumple_su_propio_schema(reporte: Report, validator: Draft202012Validator) -> None:
    errores = sorted(validator.iter_errors(reporte.to_dict()), key=str)
    assert errores == [], [e.message for e in errores]


def test_roundtrip_del_modelo(reporte: Report) -> None:
    assert Report.from_dict(reporte.to_dict()).to_dict() == reporte.to_dict()


def test_guardar_escribe_json_valido(reporte: Report, tmp_path: Path) -> None:
    path = reporte.save(tmp_path / "report.json")
    assert json.loads(path.read_text(encoding="utf-8"))["event"]["usgs_id"] == "us7000sint"


def test_los_disclaimers_siempre_estan(reporte: Report) -> None:
    """Linea roja del proyecto: ningun artefacto sale sin sus advertencias."""
    assert reporte.to_dict()["disclaimers"] == list(DISCLAIMERS)


def test_markdown_con_cifras_en_prosa(reporte: Report) -> None:
    md = render_markdown(reporte)
    assert "350 mil" in md  # 347.129 redondeado a 2 significativas
    assert "1,2 millones" in md
    assert "Bahia Solano" in md
    assert "PAGER" in md
    assert "exposicion estimada" in md.lower()


def test_markdown_omite_ground_failure_si_no_hay_producto(reporte: Report) -> None:
    """Golden test G3: el reporte omite la seccion con nota, no falla."""
    sin_gf = Report.from_dict(
        {
            **reporte.to_dict(),
            "inputs": {
                "shakemap_version": 3,
                "groundfailure_version": 0,
                "exposure_manifest": "col-v0.1-draft",
            },
        }
    )
    md = render_markdown(sin_gf)
    assert "no ha publicado el producto" in md
    assert "88 mil" not in md


def test_markdown_preliminar_lleva_encabezado(reporte: Report) -> None:
    preliminar = Report.from_dict({**reporte.to_dict(), "preliminar": True})
    assert "Reporte preliminar sin ShakeMap" in render_markdown(preliminar)


def test_markdown_incluye_changelog(reporte: Report) -> None:
    con_cambios = Report.from_dict(
        {**reporte.to_dict(), "changelog": ["pop MMI≥7: 340 mil → 350 mil"]}
    )
    assert "Cambios frente a la version anterior" in render_markdown(con_cambios)


def test_hilo_respeta_el_limite_de_caracteres(reporte: Report) -> None:
    assert all(len(post) <= MAX_CHARS for post in render_thread(reporte))


def test_hilo_aclara_que_no_es_dano(reporte: Report) -> None:
    texto = render_thread_text(reporte)
    assert "No es un reporte de danos" in texto
    assert "no es alerta temprana" in texto.lower()


def test_hilo_va_numerado(reporte: Report) -> None:
    assert render_thread_text(reporte).startswith("1/")
