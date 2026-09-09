"""Lo que el vigía no pudo leer tiene que salir del proceso.

Cuatro señales que se medían, se registraban en un `_log.warning` y ahí morían:
no llegaban al stdout, ni al output del workflow, ni al latido, ni a `/status`,
ni al código de salida. Y las cuatro dejan «cero eventos» indistinguible de «no
pude mirar», que es la confusión que este proyecto persigue en todas partes.

* **Un `event_state` ilegible** saca al sismo del despacho **para siempre**: el
  fichero sigue ilegible en la corrida siguiente. El latido publicaba
  «revisados: 18, relevantes: 0», idéntico a una noche tranquila.
* **Un feed caído** abortaba el bucle entero, así que el feed de respaldo —el
  que existe para que no se pierda un sismo cuando algo falla— no se llegaba a
  leer. La excepción subía hasta `cli.main`, que solo atrapa
  `NotImplementedError`, y mataba la pasada.
* **Un manifiesto ilegible** se convertía en «el mismo que se publicó» por un
  `or`, y el reporte salía **al día**.
* **Un producto que desaparece del detail** —`vigente=0` frente a
  `publicado=11`— no disparaba nada, porque la comparación era `vigente >
  publicado`, y el evento contaba como revisado.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from pipelines.common.constants import USGS_FEED_BACKFILL, USGS_FEED_PRIMARY
from pipelines.common.http import FixtureFetcher
from pipelines.p1_trigger.feed import feed_url
from pipelines.p1_trigger.run import TriggerResult, run_trigger

VACIO: dict[str, Any] = {"type": "FeatureCollection", "features": []}


# --- Un estado ilegible -----------------------------------------------------


def test_un_estado_ilegible_se_cuenta_y_no_tumba_la_pasada(
    feed_payload: dict[str, Any], events_dir: Path
) -> None:
    """El evento se salta, los demás siguen, y queda constancia."""
    usgs_id = str(feed_payload["features"][0]["id"])
    (events_dir / f"{usgs_id}.json").write_text("{roto", encoding="utf-8")

    resultado = run_trigger(
        FixtureFetcher(
            {feed_url(USGS_FEED_PRIMARY): feed_payload, feed_url(USGS_FEED_BACKFILL): VACIO}
        ),
        events_dir=events_dir,
    )

    assert resultado.estados_ilegibles == [usgs_id]
    assert usgs_id not in resultado.a_despachar, "un estado ilegible no se puede despachar"


def test_el_estado_ilegible_viaja_al_stdout_y_al_latido(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Se contaba en un log y no llegaba a ninguna superficie publica."""
    from pipelines import cli

    escrito: dict[str, Any] = {}
    salidas: dict[str, str] = {}
    resultado = TriggerResult(revisados=18, relevantes=0, estados_ilegibles=["us0000roto"])

    monkeypatch.setattr(cli, "run_trigger", lambda *_a, **_k: resultado)
    monkeypatch.setattr(cli, "HttpFetcher", lambda *_a, **_k: object())
    monkeypatch.setattr(cli, "write_status", lambda **kw: escrito.update(kw) or Path("x"))
    monkeypatch.setattr(cli, "_emit_github_output", lambda k, v: salidas.__setitem__(k, v))

    assert cli.main(["trigger", "--dry-run"]) == 0
    salida = capsys.readouterr()

    assert json.loads(salida.out)["estados_ilegibles"] == ["us0000roto"]
    assert escrito["latido"]["estados_ilegibles"] == 1
    assert salidas["estados_ilegibles"] == "1"
    assert "us0000roto" in salida.err


def test_un_latido_sano_no_lleva_el_campo(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Para que su presencia signifique algo cuando aparezca."""
    from pipelines import cli

    escrito: dict[str, Any] = {}
    monkeypatch.setattr(cli, "run_trigger", lambda *_a, **_k: TriggerResult(revisados=18))
    monkeypatch.setattr(cli, "HttpFetcher", lambda *_a, **_k: object())
    monkeypatch.setattr(cli, "write_status", lambda **kw: escrito.update(kw) or Path("x"))
    monkeypatch.setattr(cli, "_emit_github_output", lambda k, v: None)

    cli.main(["trigger", "--dry-run"])
    capsys.readouterr()

    assert "estados_ilegibles" not in escrito["latido"]
    assert "feeds_fallidos" not in escrito["latido"]


# --- Un feed caído ----------------------------------------------------------


class _FeedRoto(FixtureFetcher):
    """Revienta para las URL que se le marquen."""

    def __init__(self, por_url: dict[str, Any], revienta: str) -> None:
        super().__init__(por_url)
        self.revienta = revienta

    def get_json(self, url: str) -> Any:
        if self.revienta in url:
            raise OSError("503 del feed")
        return super().get_json(url)


def test_un_feed_caido_no_impide_leer_el_otro(
    feed_payload: dict[str, Any], events_dir: Path
) -> None:
    """EL CASO QUE DEJABA SIN LEER EL FEED DE RESPALDO.

    El de una hora devuelve 503 y el sismo solo está en el de 24 h. Antes, la
    excepción abortaba el bucle antes de llegar al segundo.
    """
    fetcher = _FeedRoto(
        {feed_url(USGS_FEED_PRIMARY): VACIO, feed_url(USGS_FEED_BACKFILL): feed_payload},
        revienta=USGS_FEED_PRIMARY,
    )

    resultado = run_trigger(fetcher, events_dir=events_dir)

    assert resultado.feeds_fallidos == [USGS_FEED_PRIMARY]
    assert resultado.a_despachar, "el sismo del feed de respaldo no se despachó"
    assert not resultado.ciego, "uno de dos caído no es quedarse a ciegas"


def test_con_los_dos_feeds_caidos_la_pasada_es_ciega(events_dir: Path) -> None:
    """«Cero eventos» significa «no miré», no «no había»."""

    class _TodoRoto(FixtureFetcher):
        def get_json(self, url: str) -> Any:
            raise OSError("la red")

    resultado = run_trigger(_TodoRoto({}), events_dir=events_dir)

    assert resultado.ciego
    assert len(resultado.feeds_fallidos) == 2


def test_la_pasada_ciega_sale_en_rojo(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from pipelines import cli

    ciego = TriggerResult(feeds_fallidos=[USGS_FEED_PRIMARY, USGS_FEED_BACKFILL])
    ciego._feeds_pedidos = 2

    monkeypatch.setattr(cli, "run_trigger", lambda *_a, **_k: ciego)
    monkeypatch.setattr(cli, "HttpFetcher", lambda *_a, **_k: object())
    monkeypatch.setattr(cli, "write_status", lambda **_k: Path("x"))
    monkeypatch.setattr(cli, "_emit_github_output", lambda k, v: None)

    assert cli.main(["trigger", "--dry-run"]) == 1
    assert "no es que no hubiera sismos" in capsys.readouterr().err


def test_el_latido_se_escribe_aunque_la_pasada_sea_ciega(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """La ausencia de latidos es la señal de que el cron murió, y son cosas distintas."""
    from pipelines import cli

    escrito: dict[str, Any] = {}
    ciego = TriggerResult(feeds_fallidos=[USGS_FEED_PRIMARY, USGS_FEED_BACKFILL])
    ciego._feeds_pedidos = 2

    monkeypatch.setattr(cli, "run_trigger", lambda *_a, **_k: ciego)
    monkeypatch.setattr(cli, "HttpFetcher", lambda *_a, **_k: object())
    monkeypatch.setattr(cli, "write_status", lambda **kw: escrito.update(kw) or Path("x"))
    monkeypatch.setattr(cli, "_emit_github_output", lambda k, v: None)

    cli.main(["trigger", "--dry-run"])
    capsys.readouterr()

    assert escrito["latido"]["feeds_fallidos"] == [USGS_FEED_PRIMARY, USGS_FEED_BACKFILL]


# --- Un manifiesto ilegible, y un producto que desaparece -------------------


def test_un_manifiesto_ilegible_no_es_un_reporte_al_dia(tmp_path: Path) -> None:
    """EL `or` QUE CONVERTIA «NO PUDE LEER» EN «AL DIA».

    `_manifiesto_vigente` devolvia cadena vacia al fallar y el llamador hacia
    `manifiesto_vigente or manifiesto_publicado`: el reporte salia con los dos
    manifiestos iguales, o sea al dia. El propio modulo evita esa confusion tres
    lineas mas abajo para los productos —«UN FALLO NO ES UN "AL DIA"»—.
    """
    from tests.unit.test_rezago import _FetcherFalso, _reporte

    reports = tmp_path / "reports"
    _reporte(reports, "us1", shakemap=8, groundfailure=8)
    # Directorio de manifiestos vacio: el de COL no existe.
    vacio = tmp_path / "manifests"
    vacio.mkdir()

    from pipelines.p1_trigger.rezago import comprobar

    resultado = comprobar(_FetcherFalso({"us1": (8, 8)}), reports_dir=reports, manifests_dir=vacio)

    assert resultado.fallidos == ["us1"], "el reporte tiene que contarse como no comprobado"
    assert resultado.revisados == 0, "no se sabe nada de el: no cuenta como revisado"
    assert resultado.rezagados == [], "y tampoco se afirma que este rezagado"


def test_un_producto_que_desaparece_del_detail_se_declara() -> None:
    """`vigente=0` frente a `publicado=11` no es «todo al dia».

    La comparacion era `vigente > publicado`, que con un cero no dispara nada, y
    el evento contaba como revisado. El reporte publicado cita una version que
    su propia fuente ya no reconoce.
    """
    from pipelines.p1_trigger.rezago import Rezago

    perdido = Rezago(
        usgs_id="us1",
        shakemap_publicado=11,
        shakemap_vigente=0,
        groundfailure_publicado=3,
        groundfailure_vigente=3,
        manifiesto_publicado="col-v0.6",
        manifiesto_vigente="col-v0.6",
    )
    assert perdido.desaparecido
    assert perdido.hay, "un producto que se esfuma tiene que aparecer en la lista"
    assert "DESAPARECIO" in perdido.describir()


def test_una_version_que_sube_no_es_una_desaparicion() -> None:
    from pipelines.p1_trigger.rezago import Rezago

    normal = Rezago(
        usgs_id="us1",
        shakemap_publicado=8,
        shakemap_vigente=11,
        groundfailure_publicado=3,
        groundfailure_vigente=3,
        manifiesto_publicado="col-v0.6",
        manifiesto_vigente="col-v0.6",
    )
    assert not normal.desaparecido
    assert normal.productos


def test_un_reporte_sin_producto_publicado_no_cuenta_como_desaparicion() -> None:
    """`publicado=0` es un reporte que nunca consumio ese producto."""
    from pipelines.p1_trigger.rezago import Rezago

    sin_gf = Rezago(
        usgs_id="us1",
        shakemap_publicado=8,
        shakemap_vigente=8,
        groundfailure_publicado=0,
        groundfailure_vigente=0,
        manifiesto_publicado="col-v0.6",
        manifiesto_vigente="col-v0.6",
    )
    assert not sin_gf.desaparecido
    assert not sin_gf.hay


# --- Un reporte que se cae del indice ---------------------------------------


def test_un_reporte_ilegible_se_declara_al_caerse_del_indice(tmp_path: Path) -> None:
    """Desaparecia del visor con un `_log.warning` y exit 0."""
    from pipelines.p3_report.run import rebuild_index

    bueno = tmp_path / "us0000bien"
    bueno.mkdir()
    (bueno / "report.json").write_text(
        json.dumps(
            {
                "event": {"usgs_id": "us0000bien", "mag": 6.0, "lugar": "x", "utc": "2026-01-01Z"},
                "inputs": {"exposure_manifest": "col-v0.6", "shakemap_version": 1},
                "totales": {"pop_mmi7p": 1.0, "pop_mmi6p": 2.0},
            }
        ),
        encoding="utf-8",
    )
    roto = tmp_path / "us0000roto"
    roto.mkdir()
    (roto / "report.json").write_text("{roto", encoding="utf-8")

    indice = rebuild_index(tmp_path)

    assert indice.entradas == 1, "el reporte sano sigue listado"
    assert indice.excluidos == ["us0000roto"]


def test_el_comando_de_reindexar_sale_en_rojo_si_perdio_alguno(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    import argparse

    from pipelines import cli
    from pipelines.p3_report.run import Indice

    monkeypatch.setattr(
        "pipelines.p3_report.run.rebuild_index",
        lambda *_a, **_k: Indice(
            ruta=tmp_path / "index.json", entradas=26, excluidos=["us0000roto"]
        ),
    )

    assert cli._cmd_reindexar(argparse.Namespace(reports=str(tmp_path))) == 1
    assert "dejara de listarlos" in capsys.readouterr().err
