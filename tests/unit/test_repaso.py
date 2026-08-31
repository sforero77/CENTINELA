"""El repaso de versiones: RF-04 mas alla de las 24 h que cubre el feed."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from pipelines.common.state import EventState, EventStatus, ProcessedVersions
from pipelines.p1_trigger.repaso import (
    DIAS_DE_REPASO,
    detail_url,
    eventos_a_repasar,
    repasar,
)


def _hace(dias: float) -> str:
    return (datetime.now(UTC) - timedelta(days=dias)).strftime("%Y-%m-%dT%H:%M:%SZ")


def _evento(
    tmp_path: Path,
    usgs_id: str,
    *,
    dias: float = 1.0,
    estado: EventStatus = EventStatus.PUBLICADO,
    shakemap: int = 1,
    backtest: bool = False,
) -> EventState:
    ev = EventState(
        usgs_id=usgs_id,
        estado=estado,
        mag=6.0,
        lon=-75.0,
        lat=5.0,
        depth_km=30.0,
        lugar="en algun sitio",
        origen_utc=_hace(dias),
        versiones_procesadas=ProcessedVersions(shakemap=shakemap, groundfailure=1),
        backtest=backtest,
    )
    ev.save(tmp_path)
    return ev


class _FetcherFalso:
    """Devuelve el detail que se le diga, por identificador."""

    def __init__(self, versiones: dict[str, int], revientan: set[str] | None = None) -> None:
        self.versiones = versiones
        self.revientan = revientan or set()
        self.pedidos: list[str] = []

    def get_bytes(self, url: str) -> bytes:
        # El protocolo `Fetcher` lo exige y el repaso no debe usarlo: pregunta
        # versiones, no descarga productos. Si algun dia lo llamara, esto lo
        # dice en vez de devolver un vacio plausible.
        raise AssertionError("el repaso no descarga bytes, solo compara versiones")

    def get_json(self, url: str) -> dict[str, Any]:
        uid = url.split("eventid=")[1].split("&")[0]
        self.pedidos.append(uid)
        if uid in self.revientan:
            raise OSError("la red se cayo")
        v = self.versiones[uid]
        return {
            "id": uid,
            "properties": {
                "products": {
                    "shakemap": [
                        {
                            "source": "us",
                            "status": "UPDATE",
                            "preferredWeight": 233,
                            "updateTime": 1,
                            "code": uid,
                            "properties": {"version": str(v)},
                            "contents": {},
                        }
                    ]
                }
            },
        }


# --- La ventana --------------------------------------------------------------


def test_la_ventana_cubre_donde_de_verdad_se_revisan_los_shakemap() -> None:
    """90 dias, y el numero esta medido, no elegido a ojo.

    Contra USGS, sobre los veinte eventos publicados del catalogo, la mediana
    desde el sismo hasta la ultima revision de ShakeMap son **63 dias**: Chocó
    11,5, Venezuela 61,2 (v15), el de noviembre de 2024 75,1 (v9). Ni uno
    termino de revisarse dentro de las 24 h que cubre el feed, que es
    justamente el agujero que este modulo tapa.

    Una ventana de 30 dias habria cubierto 2 de 20.
    """
    assert DIAS_DE_REPASO == 90


def test_lo_viejo_se_queda_fuera(tmp_path: Path) -> None:
    _evento(tmp_path, "us1", dias=10)
    _evento(tmp_path, "us2", dias=200)

    ids = [e.usgs_id for e in eventos_a_repasar(tmp_path)]

    assert ids == ["us1"], "un evento de hace 200 dias no se repasa a diario"


def test_lo_descartado_y_los_backtest_no_se_repasan(tmp_path: Path) -> None:
    """`descartado` es terminal. Un backtest es una reconstruccion congelada:
    re-emitirlo cada vez que USGS retoca su Atlas convertiria el catalogo
    historico en ruido."""
    _evento(tmp_path, "us1", dias=1)
    _evento(tmp_path, "us2", dias=1, estado=EventStatus.DESCARTADO)
    _evento(tmp_path, "us3", dias=1, backtest=True)

    assert [e.usgs_id for e in eventos_a_repasar(tmp_path)] == ["us1"]


def test_el_degradado_si_se_repasa(tmp_path: Path) -> None:
    """Es el que mas lo necesita: se le acabo la ventana de RF-03 sin ShakeMap,
    y `degradado -> publicado` es una transicion permitida justo para cuando
    ese ShakeMap acaba llegando."""
    _evento(tmp_path, "us1", dias=2, estado=EventStatus.DEGRADADO, shakemap=0)

    assert [e.usgs_id for e in eventos_a_repasar(tmp_path)] == ["us1"]


def test_primero_los_mas_recientes(tmp_path: Path) -> None:
    """Ahi se concentran las revisiones: si algun dia hay que recortar la
    lista, que se caiga la cola y no la cabeza."""
    _evento(tmp_path, "viejo", dias=80)
    _evento(tmp_path, "nuevo", dias=2)
    _evento(tmp_path, "medio", dias=40)

    assert [e.usgs_id for e in eventos_a_repasar(tmp_path)] == ["nuevo", "medio", "viejo"]


def test_un_event_state_ilegible_no_para_el_repaso(tmp_path: Path) -> None:
    _evento(tmp_path, "us1", dias=1)
    (tmp_path / "roto.json").write_text("{esto no es json", encoding="utf-8")

    assert [e.usgs_id for e in eventos_a_repasar(tmp_path)] == ["us1"]


# --- La comparacion ----------------------------------------------------------


def test_solo_se_despacha_lo_que_avanzo(tmp_path: Path) -> None:
    _evento(tmp_path, "quieto", dias=5, shakemap=7)
    _evento(tmp_path, "avanzo", dias=5, shakemap=7)
    fetcher = _FetcherFalso({"quieto": 7, "avanzo": 9})

    r = repasar(fetcher, events_dir=tmp_path)

    assert r.a_despachar == ["avanzo"]
    assert r.revisados == 2
    assert not r.fallidos


def test_una_version_mas_baja_no_dispara_nada(tmp_path: Path) -> None:
    """USGS puede retirar un producto y dejar a la vista uno anterior.
    Reprocesar hacia atras publicaria cifras mas viejas como si fueran nuevas.
    """
    _evento(tmp_path, "us1", dias=5, shakemap=9)
    fetcher = _FetcherFalso({"us1": 7})

    assert repasar(fetcher, events_dir=tmp_path).a_despachar == []


def test_un_fallo_de_red_no_se_cuenta_como_sin_cambios(tmp_path: Path) -> None:
    """El cero silencioso, en su version "todo al dia".

    Tragarse el error dejaria el evento sin repasar y el contador diciendo que
    se repaso. Se cuenta aparte, y el comando sale con codigo 1 para que la
    corrida no aparezca en verde.
    """
    _evento(tmp_path, "bien", dias=5, shakemap=1)
    _evento(tmp_path, "mal", dias=5, shakemap=1)
    fetcher = _FetcherFalso({"bien": 3, "mal": 3}, revientan={"mal"})

    r = repasar(fetcher, events_dir=tmp_path)

    assert r.a_despachar == ["bien"]
    assert r.fallidos == ["mal"]
    assert r.revisados == 1, "el que fallo no cuenta como revisado"


def test_se_pregunta_por_el_mismo_endpoint_que_ya_usa_p2() -> None:
    """No entra una fuente nueva al sistema por esto: es la misma llamada que
    P2 hace por evento, contra el mismo endpoint."""
    url = detail_url("us6000tjl2")

    assert url.startswith("https://earthquake.usgs.gov/fdsnws/event/1/query")
    assert "eventid=us6000tjl2" in url
    assert "format=geojson" in url


def test_sin_directorio_de_eventos_no_revienta(tmp_path: Path) -> None:
    assert eventos_a_repasar(tmp_path / "no-existe") == []


@pytest.mark.parametrize("dias", [1, 30, 365])
def test_la_ventana_es_configurable(tmp_path: Path, dias: int) -> None:
    _evento(tmp_path, "us1", dias=15)

    esperado = ["us1"] if dias > 15 else []
    assert [e.usgs_id for e in eventos_a_repasar(tmp_path, dias=dias)] == esperado


def test_si_no_se_pudo_consultar_ninguno_la_corrida_no_sale_en_verde(tmp_path: Path) -> None:
    """La misma distinción que en FIRMS y en frescura, y por el mismo motivo.

    El repaso salía con código 1 en cuanto fallaba **un** evento, y el workflow
    lo tapaba con `continue-on-error` para que los demás despachos salieran.
    Efecto: una corrida que no pudo consultar nada quedaba en verde con un
    aviso amarillo. Es el fallo que este mismo día se encontró en la lectura de
    FIRMS, repetido dentro del código escrito para arreglarlo.
    """
    _evento(tmp_path, "us1", dias=5)
    _evento(tmp_path, "us2", dias=5)
    fetcher = _FetcherFalso({"us1": 3, "us2": 3}, revientan={"us1", "us2"})

    r = repasar(fetcher, events_dir=tmp_path)

    assert r.revisados == 0
    assert len(r.fallidos) == 2
    assert r.ciego, "cero consultados de dos es no haber repasado"


def test_si_falla_alguno_pero_no_todos_la_corrida_sigue_valiendo(tmp_path: Path) -> None:
    """Los que sí se miraron valen, y sus despachos tienen que salir."""
    _evento(tmp_path, "bien", dias=5, shakemap=1)
    _evento(tmp_path, "mal", dias=5, shakemap=1)
    fetcher = _FetcherFalso({"bien": 9, "mal": 9}, revientan={"mal"})

    r = repasar(fetcher, events_dir=tmp_path)

    assert r.a_despachar == ["bien"]
    assert r.fallidos == ["mal"]
    assert not r.ciego, "uno de dos no es quedarse a ciegas"


def test_sin_eventos_que_repasar_no_es_estar_ciego(tmp_path: Path) -> None:
    """Hoy es el caso real: los 25 eventos son backtests y quedan fuera.

    Cero revisados y cero fallidos es "no había nada que mirar", no "no se pudo
    mirar". Confundirlos pondría el workflow en rojo todos los días.
    """
    r = repasar(_FetcherFalso({}), events_dir=tmp_path)

    assert r.revisados == 0
    assert not r.fallidos
    assert not r.ciego
