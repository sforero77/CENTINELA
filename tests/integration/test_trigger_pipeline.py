"""P1 completo contra fixtures: feed -> filtro -> dedupe -> event_state (§6.2)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pipelines.common.http import FixtureFetcher
from pipelines.common.state import EventState, EventStatus
from pipelines.p1_trigger.feed import feed_url
from pipelines.p1_trigger.run import run_trigger


def test_primera_corrida_detecta_los_eventos_en_alcance(
    fetcher: FixtureFetcher, events_dir: Path
) -> None:
    resultado = run_trigger(fetcher, events_dir=events_dir)
    assert resultado.revisados == 5
    assert resultado.relevantes == 2
    assert resultado.nuevos == ["us7000sint", "us7000mxmid"]
    assert resultado.revisitados == []


def test_el_estado_queda_persistido(fetcher: FixtureFetcher, events_dir: Path) -> None:
    run_trigger(fetcher, events_dir=events_dir)
    estado = EventState.load("us7000sint", events_dir)
    assert estado is not None
    assert estado.estado is EventStatus.DETECTADO
    assert estado.mag == 6.9
    assert estado.timestamps["usgs_origen"] == "2026-08-19T05:00:00Z"


def test_segunda_corrida_no_duplica(fetcher: FixtureFetcher, events_dir: Path) -> None:
    """RF-02: correr dos veces sobre el mismo feed no crea trabajo nuevo."""
    run_trigger(fetcher, events_dir=events_dir)
    segunda = run_trigger(fetcher, events_dir=events_dir)
    assert segunda.nuevos == []
    assert segunda.revisitados == ["us7000sint", "us7000mxmid"]
    assert len(list(events_dir.glob("*.json"))) == 2


def test_evento_descartado_no_se_redespacha(fetcher: FixtureFetcher, events_dir: Path) -> None:
    run_trigger(fetcher, events_dir=events_dir)
    estado = EventState.load("us7000sint", events_dir)
    assert estado is not None
    estado.transition(EventStatus.DESCARTADO, nota="retirado por USGS").save(events_dir)

    resultado = run_trigger(fetcher, events_dir=events_dir)
    assert "us7000sint" not in resultado.a_despachar


def test_el_mismo_evento_en_ambos_feeds_se_cuenta_una_vez(
    feed_payload: dict[str, Any], events_dir: Path
) -> None:
    """El feed de respaldo cubre la demora del cron sin duplicar eventos."""
    doble = FixtureFetcher({feed_url("4.5_hour"): feed_payload, feed_url("4.5_day"): feed_payload})
    resultado = run_trigger(doble, events_dir=events_dir)
    assert resultado.revisados == 5
    assert resultado.nuevos == ["us7000sint", "us7000mxmid"]


def test_dry_run_no_escribe_nada(fetcher: FixtureFetcher, events_dir: Path) -> None:
    """El simulacro mensual no debe ensuciar el historial de eventos."""
    resultado = run_trigger(fetcher, events_dir=events_dir, dry_run=True)
    assert resultado.nuevos
    assert list(events_dir.glob("*.json")) == []


def test_el_estado_valida_contra_su_schema(fetcher: FixtureFetcher, events_dir: Path) -> None:
    from jsonschema import Draft202012Validator

    from pipelines.common.paths import SCHEMAS_DIR

    run_trigger(fetcher, events_dir=events_dir)
    schema = json.loads((SCHEMAS_DIR / "event-state.schema.json").read_text(encoding="utf-8"))
    validador = Draft202012Validator(schema)
    for path in events_dir.glob("*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        errores = [e.message for e in validador.iter_errors(data)]
        assert errores == [], f"{path.name}: {errores}"


# --- La capa de lo visto y no despachado ------------------------------------


def test_lo_pequeno_de_latam_se_registra_sin_despacharse(
    fetcher: FixtureFetcher, events_dir: Path
) -> None:
    """El caso de Jordan, en fixture: M4,8 en Popayan.

    Ni se despacha ni se olvida. Es la tercera opcion que hasta ahora no
    existia, y la que hace que el vigia pueda demostrar que estuvo mirando.
    """
    resultado = run_trigger(fetcher, events_dir=events_dir)

    observados = [e.usgs_id for e in resultado.observados]
    assert observados == ["us7000small"]
    assert "us7000small" not in resultado.a_despachar


def test_lo_que_se_despacha_no_aparece_ademas_como_visto(
    fetcher: FixtureFetcher, events_dir: Path
) -> None:
    """Contarlo dos veces seria inflar la actividad sismica de la region."""
    resultado = run_trigger(fetcher, events_dir=events_dir)

    assert not set(resultado.a_despachar) & {e.usgs_id for e in resultado.observados}


def test_la_capa_no_es_un_sismografo_mundial(fetcher: FixtureFetcher, events_dir: Path) -> None:
    """Los feeds del USGS son globales, y esto es un sistema para LATAM.

    Kermadec es un M6,1 legitimo y ajeno; la voladura de Nevada no es ni un
    sismo. Ninguno de los dos tiene sitio en un mapa de exposicion de LATAM.
    """
    resultado = run_trigger(fetcher, events_dir=events_dir)

    vistos = {e.usgs_id for e in resultado.observados}
    assert "us7000faraway" not in vistos, "un sismo de Kermadec no es de LATAM"
    assert "us7000quarry" not in vistos, "una voladura de cantera no es un sismo"


def test_un_evento_registrado_no_crea_event_state(
    fetcher: FixtureFetcher, events_dir: Path
) -> None:
    """`events/` es la cola de trabajo de P2; esto no es trabajo.

    Escribir ahi un evento que nadie va a procesar ensuciaria la cola y le daria
    entrada al pipeline de impacto por la puerta de atras.
    """
    run_trigger(fetcher, events_dir=events_dir)

    assert not (events_dir / "us7000small.json").exists()
