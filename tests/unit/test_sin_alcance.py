"""Un sismo medido sin nadie en la clase VI no tiene reporte (`report/2.0`).

EL CASO QUE LO MOTIVO. El M6,7 de Carhuamayo (`pt26325050`, 108 km de
profundidad) salia como reporte completo con todas sus cifras en cero: ficha,
isolineas y ni un hexagono. En el visor se leia como un reporte roto. Quince de
treinta y nueve reportes eran asi. La regla nueva: si ninguna celda poblada
llega a la clase VI (MMI 5,5), el evento pasa a `sin_alcance`, se retira lo que
tuviera publicado y se enseña como "visto, sin reporte" con su razon. Un
ShakeMap nuevo que si alcance a alguien lo devuelve a `publicado`.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from pipelines.common.sin_alcance import build_sin_alcance, razon_sin_alcance, write_sin_alcance
from pipelines.common.state import EventState, EventStatus, ProcessedVersions


def _estado(**kwargs: object) -> EventState:
    base: dict[str, object] = {
        "usgs_id": "pt26325050",
        "estado": EventStatus.PUBLICADO,
        "mag": 6.7,
        "lon": -75.9779,
        "lat": -10.8548,
        "depth_km": 107.991,
        "lugar": "9 km al NE de Carhuamayo, Perú",
        "origen_utc": "2026-11-21T00:09:17Z",
        "versiones_procesadas": ProcessedVersions(shakemap=2, groundfailure=2),
    }
    base.update(kwargs)
    return EventState(**base)  # type: ignore[arg-type]


# --- la maquina de estados ---------------------------------------------------


@pytest.mark.parametrize(
    "desde",
    [EventStatus.DETECTADO, EventStatus.PRELIMINAR, EventStatus.PUBLICADO, EventStatus.DEGRADADO],
)
def test_todo_estado_en_vuelo_puede_quedarse_sin_alcance(desde: EventStatus) -> None:
    nuevo = _estado(estado=desde).transition(EventStatus.SIN_ALCANCE, nota="x")
    assert nuevo.estado is EventStatus.SIN_ALCANCE


def test_sin_alcance_no_es_terminal() -> None:
    """Un ShakeMap nuevo que alcance a alguien tiene que poder publicarlo."""
    sin = _estado(estado=EventStatus.SIN_ALCANCE)
    assert sin.transition(EventStatus.PUBLICADO).estado is EventStatus.PUBLICADO
    assert sin.transition(EventStatus.SIN_ALCANCE).estado is EventStatus.SIN_ALCANCE


def test_p1_y_el_repaso_lo_siguen_vigilando() -> None:
    """Si fuera terminal, la revision del ShakeMap que alcanza tierra no llegaria."""
    from pipelines.p1_trigger.repaso import _SIN_REPASO
    from pipelines.p1_trigger.run import _TERMINAL

    assert EventStatus.SIN_ALCANCE not in _TERMINAL
    assert EventStatus.SIN_ALCANCE not in _SIN_REPASO


def test_la_intensidad_alcanzada_viaja_en_el_estado(tmp_path: Path) -> None:
    _estado(estado=EventStatus.SIN_ALCANCE, mmi_max_poblado=5.0).save(tmp_path)
    leido = EventState.load("pt26325050", tmp_path)
    assert leido is not None and leido.mmi_max_poblado == 5.0


def test_un_estado_de_siempre_no_cambia_de_forma() -> None:
    """Sin `mmi_max_poblado` no se escribe la clave: los 42 estados no se tocan."""
    assert "mmi_max_poblado" not in _estado().to_dict()


def test_el_esquema_del_estado_admite_el_nuevo() -> None:
    raiz = Path(__file__).parent.parent.parent
    esquema = json.loads((raiz / "schemas" / "event-state.schema.json").read_text("utf-8"))
    assert "sin_alcance" in esquema["properties"]["estado"]["enum"]
    assert "mmi_max_poblado" in esquema["properties"]


# --- la rama de P2 -----------------------------------------------------------


def _impacto(con: object, celdas: list[tuple[float, float]]) -> None:
    filas = ", ".join(f"({i}::UBIGINT, {m}, {p})" for i, (m, p) in enumerate(celdas, start=1))
    con.execute(  # type: ignore[attr-defined]
        f"CREATE OR REPLACE TABLE impact_h3 AS SELECT * FROM (VALUES {filas}) "
        "AS t(h3_08, mmi_max, pop_total)"
    )


def test_la_intensidad_maxima_cuenta_solo_celdas_con_gente() -> None:
    from pipelines.p2_impact.exposure_join import connect
    from pipelines.p2_impact.run import mmi_max_poblado

    con = connect()
    _impacto(con, [(5.0, 1200.0), (5.5, 0.0)])
    assert mmi_max_poblado(con) == 5.0


def test_el_reporte_de_ceros_se_retira_y_el_estado_lo_dice(tmp_path: Path) -> None:
    from pipelines.p2_impact.exposure_join import connect
    from pipelines.p2_impact.run import Action, Decision, _pasar_a_sin_alcance

    eventos = tmp_path / "events"
    reportes = tmp_path / "reports"
    publicado = reportes / "pt26325050"
    publicado.mkdir(parents=True)
    (publicado / "report.json").write_text("{}", encoding="utf-8")
    _estado().save(eventos)

    con = connect()
    _impacto(con, [(5.0, 36000.0), (4.5, 90000.0)])
    # Solo se leen las versiones y sus contribuidores.
    productos = SimpleNamespace(
        shakemap_version=2, groundfailure_version=2, shakemap_fuente="us", groundfailure_fuente="us"
    )

    decision = _pasar_a_sin_alcance(
        con,
        _estado(),
        productos,  # type: ignore[arg-type]
        Decision(Action.COMPLETO, "reproceso forzado", 2, 2),
        "pt26325050",
        eventos,
        reportes,
    )

    assert decision.action is Action.SIN_ALCANCE
    assert not publicado.exists(), "el reporte de ceros sigue publicado"
    assert json.loads((reportes / "index.json").read_text("utf-8")) == []
    estado = EventState.load("pt26325050", eventos)
    assert estado is not None
    assert estado.estado is EventStatus.SIN_ALCANCE
    assert estado.mmi_max_poblado == 5.0
    assert "MMI 5.0" in estado.notas[-1]


# --- la lista que pinta el visor -----------------------------------------------


def test_la_razon_dice_que_si_se_midio_y_hasta_donde_llego() -> None:
    razon = razon_sin_alcance(_estado(estado=EventStatus.SIN_ALCANCE, mmi_max_poblado=5.0))
    assert "ShakeMap v2" in razon
    assert "MMI 5,0" in razon
    assert "intensidad VI (MMI 5,5)" in razon


def test_la_lista_sale_de_los_estados_y_solo_de_los_sin_alcance(tmp_path: Path) -> None:
    _estado(estado=EventStatus.SIN_ALCANCE, mmi_max_poblado=5.0).save(tmp_path)
    _estado(usgs_id="us7000aaaa").save(tmp_path)

    datos = build_sin_alcance(tmp_path)

    assert [e["usgs_id"] for e in datos["eventos"]] == ["pt26325050"]
    entrada = datos["eventos"][0]
    assert entrada["iso3"] == "PER"
    assert entrada["mmi_max_poblado"] == 5.0


def test_la_lista_es_determinista(tmp_path: Path) -> None:
    """Dos workflows que la regeneran a la vez tienen que escribir lo mismo."""
    eventos = tmp_path / "events"
    _estado(estado=EventStatus.SIN_ALCANCE, mmi_max_poblado=5.0).save(eventos)
    ruta = write_sin_alcance(events_dir=eventos, site_dir=tmp_path / "site")
    primero = ruta.read_text("utf-8")
    write_sin_alcance(events_dir=eventos, site_dir=tmp_path / "site")
    assert ruta.read_text("utf-8") == primero
    assert "generado_utc" not in json.loads(primero)
