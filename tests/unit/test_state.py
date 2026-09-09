"""Maquina de estados del evento (§3.3, RF-02)."""

from __future__ import annotations

from pathlib import Path

import pytest

from pipelines.common.state import (
    EventState,
    EventStatus,
    InvalidTransitionError,
    ProcessedVersions,
)


def _estado(**kwargs: object) -> EventState:
    base: dict[str, object] = {
        "usgs_id": "us7000sint",
        "estado": EventStatus.DETECTADO,
        "mag": 6.9,
        "lon": -77.85,
        "lat": 6.42,
        "depth_km": 24.7,
        "lugar": "Choco, Colombia",
        "origen_utc": "2026-08-19T05:00:00Z",
    }
    base.update(kwargs)
    return EventState(**base)  # type: ignore[arg-type]


def test_roundtrip_json(events_dir: Path) -> None:
    original = _estado(versiones_procesadas=ProcessedVersions(shakemap=3, groundfailure=2))
    original.save(events_dir)
    recuperado = EventState.load("us7000sint", events_dir)
    assert recuperado is not None
    assert recuperado.to_dict() == original.to_dict()


def test_evento_desconocido_devuelve_none(events_dir: Path) -> None:
    assert EventState.load("us0000nope", events_dir) is None


def test_escritura_determinista(events_dir: Path) -> None:
    """El diff de git debe mostrar solo lo que cambio, no reordenamientos."""
    estado = _estado()
    path = estado.save(events_dir)
    primero = path.read_text(encoding="utf-8")
    estado.save(events_dir)
    assert path.read_text(encoding="utf-8") == primero


def test_transicion_valida() -> None:
    nuevo = _estado().transition(EventStatus.PRELIMINAR, nota="sin ShakeMap aun")
    assert nuevo.estado is EventStatus.PRELIMINAR
    assert "preliminar" in nuevo.timestamps
    assert nuevo.notas == ["sin ShakeMap aun"]


def test_publicado_puede_republicarse() -> None:
    """RF-04: al aparecer ShakeMap v(n+1) el evento se re-publica."""
    publicado = _estado(estado=EventStatus.PUBLICADO)
    assert publicado.transition(EventStatus.PUBLICADO).estado is EventStatus.PUBLICADO


def test_descartado_es_terminal() -> None:
    descartado = _estado(estado=EventStatus.DESCARTADO)
    with pytest.raises(InvalidTransitionError):
        descartado.transition(EventStatus.PUBLICADO)


def test_needs_reprocessing_detecta_version_nueva() -> None:
    estado = _estado(versiones_procesadas=ProcessedVersions(shakemap=2, groundfailure=1))
    assert estado.needs_reprocessing(3, 1)
    assert estado.needs_reprocessing(2, 2)
    assert not estado.needs_reprocessing(2, 1)


def test_no_reprocesa_version_anterior() -> None:
    """Un producto que llega retrasado no debe hacer retroceder el reporte."""
    estado = _estado(versiones_procesadas=ProcessedVersions(shakemap=3, groundfailure=2))
    assert not estado.needs_reprocessing(1, 1)


@pytest.mark.parametrize("malo", ["../../etc/passwd", "us/7000", "", "a", "us 7000"])
def test_un_usgs_id_con_forma_invalida_no_escribe_ruta(malo: str, events_dir: Path) -> None:
    """El id viene de un tercero y se convierte en nombre de archivo."""
    with pytest.raises(ValueError, match="forma invalida"):
        _estado(usgs_id=malo).save(events_dir)


def test_usgs_ids_reales_son_validos(events_dir: Path) -> None:
    for bueno in ("us7000sint", "ci40000000", "nc73872510", "official2026-08-10"):
        assert _estado(usgs_id=bueno).save(events_dir).name == f"{bueno}.json"


def test_un_backtest_se_marca_como_tal(events_dir: Path) -> None:
    """Su latencia no mide nada del sistema y no puede contaminar el p50."""
    estado = _estado(backtest=True)
    estado.save(events_dir)
    recuperado = EventState.load("us7000sint", events_dir)
    assert recuperado is not None and recuperado.backtest


def test_por_defecto_un_evento_no_es_backtest() -> None:
    assert _estado().backtest is False


def test_el_primer_sello_de_un_estado_no_se_pisa() -> None:
    """La latencia medía «cuánto hace que lo relanzamos», no cuánto tardó.

    `transition` hacía `timestamps | {estado: ahora}`, así que cada re-emisión
    —rutina cada vez que USGS publica un ShakeMap nuevo— reescribía `publicado`
    y la latencia del evento crecía sola. Medido el 3-sep-2026: los dos sismos
    en vivo daban p50 893,9 min cuando lo real es 92,1.

    Lo mismo rompía la ventana de 6 h del preliminar, que cuenta desde
    `detectado` o `preliminar` y se reiniciaba en cada reintento.
    """
    from pipelines.common.state import EventState, EventStatus

    inicial = EventState(
        usgs_id="us7000test",
        estado=EventStatus.DETECTADO,
        mag=6.0,
        lon=-75.0,
        lat=4.0,
        depth_km=10.0,
        lugar="X",
        origen_utc="2026-09-02T12:00:00Z",
    )
    publicado = inicial.transition(EventStatus.PUBLICADO)
    primero = publicado.timestamps["publicado"]

    reemitido = publicado.transition(EventStatus.PUBLICADO)

    assert reemitido.timestamps["publicado"] == primero, "la latencia se mide al primero"
    assert "publicado_ultimo" in reemitido.timestamps, "y la re-emisión no se pierde"
