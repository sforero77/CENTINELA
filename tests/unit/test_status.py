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


def _con_reporte(raiz: Path, *usgs_ids: str) -> Path:
    """Crea el `reports/<id>/report.json` que respalda cada `event_state`.

    Antes estas pruebas afirmaban una latencia para eventos sin reporte, que es
    exactamente el bug que se colo en produccion el 26-ago-2026. Ahora hay que
    poner la prueba, no solo la afirmacion.
    """
    reportes = raiz / "reports"
    for usgs_id in usgs_ids:
        (reportes / usgs_id).mkdir(parents=True, exist_ok=True)
        (reportes / usgs_id / "report.json").write_text("{}", encoding="utf-8")
    return reportes


def test_percentil_con_un_solo_valor() -> None:
    assert percentil([42.0], 0.5) == 42.0


def test_percentil_interpola() -> None:
    assert percentil([10.0, 20.0, 30.0], 0.5) == 20.0


def test_percentil_sin_datos_no_inventa_un_cero() -> None:
    """Un cero parece un logro; None dice la verdad."""
    assert percentil([], 0.5) is None


def test_latencia_de_un_evento(tmp_path: Path) -> None:
    _publicado("us1", "2026-08-10T12:00:00Z", "2026-08-10T12:45:00Z").save(tmp_path)
    latencias = event_latencies(tmp_path, reports_root=_con_reporte(tmp_path, "us1"))
    assert len(latencias) == 1
    assert latencias[0].minutos == 45.0


def test_los_backtests_no_entran_en_la_estadistica(tmp_path: Path) -> None:
    """Se publican dias despues del sismo: su latencia daria un p50 absurdo."""
    _publicado("us1", "2026-08-10T12:00:00Z", "2026-08-10T12:45:00Z").save(tmp_path)
    _publicado("us2", "2026-08-10T12:00:00Z", "2026-08-23T12:00:00Z", backtest=True).save(tmp_path)

    datos = build_status(events_dir=tmp_path, reports_root=_con_reporte(tmp_path, "us1", "us2"))
    assert datos["medido"]["eventos_publicados"] == 1
    assert datos["medido"]["backtests_excluidos"] == 1
    assert datos["medido"]["p50_min"] == 45.0
    # Pero si se listan: ocultarlos seria peor que excluirlos del calculo.
    assert {e["usgs_id"] for e in datos["eventos"]} == {"us1", "us2"}


def test_un_evento_no_publicado_no_cuenta(tmp_path: Path) -> None:
    estado = _publicado("us1", "2026-08-10T12:00:00Z", "2026-08-10T12:45:00Z")
    EventState.from_dict({**estado.to_dict(), "estado": "preliminar"}).save(tmp_path)
    assert event_latencies(tmp_path, reports_root=_con_reporte(tmp_path, "us1")) == []


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


# --- Una latencia publicada tiene que tener un reporte detras ---------------


def test_un_estado_publicado_sin_reporte_no_produce_latencia(tmp_path: Path) -> None:
    """El caso real del 26-ago-2026, y el peor fallo posible de esta pagina.

    La pagina publica llego a servir un evento `us7000abcd` —inexistente en
    USGS, HTTP 404— con `"backtest": false` y 20,0 minutos de latencia,
    contando como el unico evento real que el sistema habia publicado. Salio de
    un `event_state` que existio un rato y se borro despues; `status.json` ya lo
    habia absorbido y nada lo revisaba.

    El `event_state` es una **afirmacion**; el directorio en `reports/` es la
    **prueba**. Cuando se separan, gana la prueba.

    Es el peor fallo posible de esta pagina en concreto: su unica razon de
    existir es que la latencia sea verificable, y si el numero puede salir de la
    nada, la pagina deja de probar nada.
    """
    _publicado("us7000abcd", "2026-08-26T19:50:00Z", "2026-08-26T20:10:00Z").save(tmp_path)

    assert event_latencies(tmp_path, reports_root=tmp_path / "reports") == []


def test_con_su_reporte_la_latencia_si_cuenta(tmp_path: Path) -> None:
    """El guardia no puede tragarse los eventos legitimos."""
    _publicado("us7000real", "2026-08-26T19:50:00Z", "2026-08-26T20:10:00Z").save(tmp_path)

    latencias = event_latencies(tmp_path, reports_root=_con_reporte(tmp_path, "us7000real"))

    assert [e.usgs_id for e in latencias] == ["us7000real"]
    assert latencias[0].minutos == 20.0


def test_un_evento_fantasma_no_infla_la_cuenta_publicada(tmp_path: Path) -> None:
    """La cifra de portada de /status es "cuantos eventos hemos publicado".

    Con el fantasma dentro decia 1 cuando la respuesta honesta era 0.
    """
    _publicado("us7000abcd", "2026-08-26T19:50:00Z", "2026-08-26T20:10:00Z").save(tmp_path)

    datos = build_status(events_dir=tmp_path, reports_root=tmp_path / "reports")

    assert datos["medido"]["eventos_publicados"] == 0
    assert datos["eventos"] == []
