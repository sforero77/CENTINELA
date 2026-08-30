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


# --- La cadencia del vigia: medir la infraestructura, no el sismo -----------


def _latidos(*horas: str) -> list[dict[str, object]]:
    return [{"utc": h, "revisados": 10, "relevantes": 0} for h in horas]


def test_se_mide_el_hueco_real_entre_revisiones() -> None:
    """Hasta el 27-ago habia que deducirlo a mano de `gh run list`.

    Es la unica cifra del sistema que mide la infraestructura y no el sismo, y
    es la que decide si bajar el cron de diez a treinta minutos sirvio de algo.
    """
    from pipelines.common.status import cadencia_del_vigia

    c = cadencia_del_vigia(
        _latidos(
            "2026-08-27T00:00:00Z",
            "2026-08-27T01:00:00Z",
            "2026-08-27T03:00:00Z",
        )
    )

    assert c["p50_min"] == 90.0
    assert c["peor_min"] == 120.0
    assert c["revisiones"] == 3


def test_un_latido_no_es_una_revision() -> None:
    """El fallo que este campo existe para impedir.

    El latido se commitea como mucho una vez por hora. Mientras el vigia corrio
    cada media hora, el hueco entre latidos y el ritmo real se parecian lo
    bastante como para que nadie mirara; con el cron externo a cinco minutos,
    `/status` publicaba "el vigia tarda 2,6 h en revisar el feed" mientras
    revisaba cada cinco, y encima culpaba de ello a la cola de GitHub.
    """
    from pipelines.common.status import cadencia_del_vigia

    c = cadencia_del_vigia(
        [
            {"utc": "2026-08-30T00:00:00Z", "revisiones": 1},
            {"utc": "2026-08-30T01:00:00Z", "revisiones": 12},
            {"utc": "2026-08-30T02:00:00Z", "revisiones": 12},
        ]
    )

    assert c["p50_min"] == 5.0, "una hora con doce revisiones son cinco minutos"
    assert c["revisiones"] == 25, "se cuentan las corridas, no los commits"
    assert c["latidos"] == 3


def test_un_latido_sin_el_campo_se_sigue_midiendo_como_antes() -> None:
    """Los latidos publicados antes del 30-ago no traen `revisiones`.

    Contarlos como una revision es exactamente lo que valian: la serie
    historica no cambia de significado por añadir el campo.
    """
    from pipelines.common.status import cadencia_del_vigia

    c = cadencia_del_vigia([{"utc": "2026-08-27T00:00:00Z"}, {"utc": "2026-08-27T00:30:00Z"}])

    assert c["p50_min"] == 30.0


def test_el_conteo_de_revisiones_nunca_mejora_la_cifra_por_error() -> None:
    """Un cero o un negativo colados dividirian por cero o inflarian el ritmo.

    El conteo viene de una llamada a la API dentro del workflow; si falla,
    tiene que degradar hacia "no se midio mejor", nunca hacia un numero
    optimista que nadie puede respaldar.
    """
    from pipelines.common.status import cadencia_del_vigia

    for malo in (0, -3, None):
        c = cadencia_del_vigia(
            [
                {"utc": "2026-08-30T00:00:00Z"},
                {"utc": "2026-08-30T01:00:00Z", "revisiones": malo},
            ]
        )
        assert c["p50_min"] == 60.0, f"con revisiones={malo!r} debe caer a 1"


def test_una_parada_larga_no_se_cuenta_como_cadencia() -> None:
    """Un hueco de dias es una parada, no un ritmo.

    Meterlo en la mediana la ahogaria y el numero dejaria de decir como se
    comporta el cron cuando funciona.
    """
    from pipelines.common.status import cadencia_del_vigia

    c = cadencia_del_vigia(
        _latidos(
            "2026-08-20T00:00:00Z",
            "2026-08-27T00:00:00Z",  # siete dias parado
            "2026-08-27T01:00:00Z",
        )
    )

    assert c["peor_min"] == 60.0, "la parada de siete dias no puede ser el peor caso"


def test_sin_suficientes_latidos_no_se_inventa_una_cadencia() -> None:
    """Con un solo latido no hay hueco que medir.

    Publicar un cero seria decir "corre instantaneamente", que es lo contrario
    de lo que pasa.
    """
    from pipelines.common.status import cadencia_del_vigia

    assert cadencia_del_vigia(_latidos("2026-08-27T00:00:00Z")) == {}
    assert cadencia_del_vigia([]) == {}


def test_la_cadencia_se_publica_en_status() -> None:
    """Medida y no publicada seria el patron que esta auditoria persigue."""
    from pipelines.common.status import build_status

    datos = build_status(
        events_dir=None,
        latidos=_latidos("2026-08-27T00:00:00Z", "2026-08-27T00:45:00Z"),
    )

    assert datos["cadencia"]["p50_min"] == 45.0
    assert datos["cadencia"]["declarado_min"] == 30


def test_lo_declarado_coincide_con_el_cron_del_workflow() -> None:
    """Publicar "declarado: 10 min" con un cron de 30 seria mentir con precision."""
    from pathlib import Path

    from pipelines.common.status import cadencia_del_vigia

    workflow = (
        Path(__file__).parent.parent.parent / ".github" / "workflows" / "trigger.yml"
    ).read_text(encoding="utf-8")
    c = cadencia_del_vigia(_latidos("2026-08-27T00:00:00Z", "2026-08-27T00:30:00Z"))

    assert f'cron: "*/{c["declarado_min"]} * * * *"' in workflow
