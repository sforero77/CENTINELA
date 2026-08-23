"""Pagina de estado y calculo de latencia (RNF-02)."""

from __future__ import annotations

import json
from pathlib import Path

from pipelines.common.state import EventState, EventStatus
from pipelines.common.status import build_status, event_latencies, percentil, write_status


def _publicado(usgs_id: str, origen: str, publicado: str, *, backtest: bool = False) -> EventState:
    return EventState(
        usgs_id=usgs_id,
        estado=EventStatus.PUBLICADO,
        mag=6.0,
        lon=-75.0,
        lat=5.0,
        depth_km=30.0,
        lugar="x",
        origen_utc=origen,
        timestamps={"publicado": publicado},
        backtest=backtest,
    )


def test_percentil_con_un_solo_valor() -> None:
    assert percentil([42.0], 0.5) == 42.0


def test_percentil_interpola() -> None:
    assert percentil([10.0, 20.0, 30.0], 0.5) == 20.0


def test_percentil_sin_datos_no_inventa_un_cero() -> None:
    """Un cero parece un logro; None dice la verdad."""
    assert percentil([], 0.5) is None


def test_latencia_de_un_evento(tmp_path: Path) -> None:
    _publicado("us1", "2026-08-10T12:00:00Z", "2026-08-10T12:45:00Z").save(tmp_path)
    latencias = event_latencies(tmp_path)
    assert len(latencias) == 1
    assert latencias[0].minutos == 45.0


def test_los_backtests_no_entran_en_la_estadistica(tmp_path: Path) -> None:
    """Se publican dias despues del sismo: su latencia daria un p50 absurdo."""
    _publicado("us1", "2026-08-10T12:00:00Z", "2026-08-10T12:45:00Z").save(tmp_path)
    _publicado("us2", "2026-08-10T12:00:00Z", "2026-08-23T12:00:00Z", backtest=True).save(tmp_path)

    datos = build_status(events_dir=tmp_path)
    assert datos["medido"]["eventos_publicados"] == 1
    assert datos["medido"]["backtests_excluidos"] == 1
    assert datos["medido"]["p50_min"] == 45.0
    # Pero si se listan: ocultarlos seria peor que excluirlos del calculo.
    assert {e["usgs_id"] for e in datos["eventos"]} == {"us1", "us2"}


def test_un_evento_no_publicado_no_cuenta(tmp_path: Path) -> None:
    estado = _publicado("us1", "2026-08-10T12:00:00Z", "2026-08-10T12:45:00Z")
    EventState.from_dict({**estado.to_dict(), "estado": "preliminar"}).save(tmp_path)
    assert event_latencies(tmp_path) == []


def test_el_status_conserva_los_latidos(tmp_path: Path) -> None:
    """Sin historial no se puede ver que el cron dejo de latir."""
    site = tmp_path / "site"
    write_status(events_dir=tmp_path, site_dir=site, latido={"utc": "a", "revisados": 1})
    write_status(events_dir=tmp_path, site_dir=site, latido={"utc": "b", "revisados": 2})
    datos = json.loads((site / "status.json").read_text(encoding="utf-8"))
    assert [x["utc"] for x in datos["latidos"]] == ["a", "b"]


def test_el_objetivo_publicado_es_el_de_la_espec(tmp_path: Path) -> None:
    datos = build_status(events_dir=tmp_path)
    assert datos["objetivo"] == {"p50_min": 60, "p95_min": 90}
