"""`falla_de_terreno.py`: el relleno de la alerta de USGS en reportes publicados.

El modulo tenia **0 % de cobertura**. Nada lo ejercitaba: la prueba que lleva su
nombre —`test_falla_de_terreno_publicada.py`— comprueba como se RENDERIZA la
alerta en el markdown, que es otra cosa, y no importa este modulo ni una vez.

Un modulo cableado a un subcomando y sin una sola prueba es el punto ciego que
esta auditoria persigue: `centinela alertas-terreno` reescribe `report.json` de
los veintisiete reportes publicados, y nadie habia comprobado que escriba lo que
dice ni que se detenga cuando no puede.

Y al ejercitarlo aparecieron dos fallos que solo se ven corriendo:

* Una corrida **idempotente sana** —todos los reportes ya con su alerta, que es
  el caso normal de la segunda vez— salia con **exit 1**. Un comando que sale en
  rojo cuando no hay trabajo ensena a ignorar su codigo de salida.
* Los fallos de origen se quedaban en el log: el retorno solo decia que se
  escribio, asi que "no habia nada que hacer" y "USGS no contesto" llegaban
  iguales al llamador.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from pipelines.p3_report.falla_de_terreno import backfill_ground_failure_alerts

#: Los nombres son los de USGS, con guion: `parse_products` los lee tal cual.
ALERTAS = {
    "landslide-alert": "orange",
    "landslide-population-alert-value": "1400",
    "liquefaction-alert": "yellow",
    "liquefaction-population-alert-value": "460000",
}


def _detalle(con_alertas: bool = True) -> dict[str, Any]:
    """Un `detail` de USGS con —o sin— producto Ground Failure."""
    productos: dict[str, Any] = {}
    if con_alertas:
        productos["ground-failure"] = [
            {
                "preferredWeight": 1,
                "properties": {**ALERTAS, "version": "1"},
                "contents": {},
            }
        ]
    return {"id": "us0000test", "properties": {"products": productos}}


class _Usgs:
    """Sirve el mismo detalle, o revienta si se le pide."""

    def __init__(self, detalle: dict[str, Any] | None = None, error: Exception | None = None):
        self.detalle = detalle
        self.error = error
        self.pedidas: list[str] = []

    def get_json(self, url: str) -> dict[str, Any]:
        self.pedidas.append(url)
        if self.error is not None:
            raise self.error
        assert self.detalle is not None
        return self.detalle

    def get_bytes(self, url: str) -> bytes:  # pragma: no cover - no se usa
        raise NotImplementedError


def _reporte(raiz: Path, evento: str, **extra: Any) -> Path:
    directorio = raiz / evento
    directorio.mkdir(parents=True)
    destino = directorio / "report.json"
    destino.write_text(
        json.dumps(
            {
                "schema": "centinela/report/1.0",
                "event": {"usgs_id": evento},
                "totales": {"pop_mmi7p": 1.0},
                **extra,
            }
        ),
        encoding="utf-8",
    )
    return destino


def test_escribe_la_alerta_en_un_reporte_que_no_la_tiene(tmp_path: Path) -> None:
    destino = _reporte(tmp_path, "us0000test")

    relleno = backfill_ground_failure_alerts(fetcher=_Usgs(_detalle()), reports_root=tmp_path)

    assert list(relleno.escritos) == ["us0000test"]
    datos = json.loads(destino.read_text(encoding="utf-8"))
    assert datos["ground_failure_usgs"]["ls_alerta_usgs"] == "orange"


def test_una_segunda_corrida_no_reescribe_nada_y_no_es_un_fallo(tmp_path: Path) -> None:
    """EL CASO NORMAL, QUE SALIA EN ROJO."""
    _reporte(tmp_path, "us0000test")
    usgs = _Usgs(_detalle())

    backfill_ground_failure_alerts(fetcher=usgs, reports_root=tmp_path)
    segunda = backfill_ground_failure_alerts(fetcher=usgs, reports_root=tmp_path)

    assert segunda.escritos == {}
    assert segunda.ya_al_dia == ["us0000test"]
    assert not segunda.fallidos
    assert not segunda.ciego, "una corrida con todo al dia no es una corrida ciega"


def test_un_evento_sin_producto_no_cuenta_como_fallo(tmp_path: Path) -> None:
    _reporte(tmp_path, "us0000test")

    relleno = backfill_ground_failure_alerts(
        fetcher=_Usgs(_detalle(con_alertas=False)), reports_root=tmp_path
    )

    assert relleno.sin_alertas == ["us0000test"]
    assert not relleno.fallidos


def test_una_fuente_caida_no_tumba_los_demas_pero_se_declara(tmp_path: Path) -> None:
    """`except Exception` dejaba el fallo solo en el log."""
    for evento in ("us0000aaa", "us0000bbb"):
        _reporte(tmp_path, evento)

    class _UnoFalla(_Usgs):
        def get_json(self, url: str) -> dict[str, Any]:
            if "us0000aaa" in url:
                raise TimeoutError("USGS no contesta")
            return _detalle()

    relleno = backfill_ground_failure_alerts(fetcher=_UnoFalla(), reports_root=tmp_path)

    assert list(relleno.escritos) == ["us0000bbb"], "el evento sano tiene que escribirse"
    assert "us0000aaa" in relleno.fallidos
    assert "no contesta" in relleno.fallidos["us0000aaa"]
    assert not relleno.ciego, "uno de dos caido no es quedarse a ciegas"


def test_si_fallan_todos_la_corrida_es_ciega(tmp_path: Path) -> None:
    for evento in ("us0000aaa", "us0000bbb"):
        _reporte(tmp_path, evento)

    relleno = backfill_ground_failure_alerts(
        fetcher=_Usgs(error=TimeoutError("la red")), reports_root=tmp_path
    )

    assert relleno.ciego
    assert len(relleno.fallidos) == 2


def test_el_bloque_va_donde_lo_pone_el_modelo(tmp_path: Path) -> None:
    """Para que un `git diff` del reporte no dependa del orden de escritura."""
    destino = _reporte(tmp_path, "us0000test", clave_ajena={"x": 1})

    backfill_ground_failure_alerts(fetcher=_Usgs(_detalle()), reports_root=tmp_path)

    claves = list(json.loads(destino.read_text(encoding="utf-8")))
    assert "ground_failure_usgs" in claves
    assert claves[-1] == "clave_ajena", "lo que el modelo no conoce se conserva al final"


def test_un_reporte_corrupto_se_declara_y_no_revienta(tmp_path: Path) -> None:
    """Un `report.json` ilegible es un fallo de ese evento, no de la corrida."""
    directorio = tmp_path / "us0000test"
    directorio.mkdir()
    (directorio / "report.json").write_text("{roto", encoding="utf-8")

    relleno = backfill_ground_failure_alerts(fetcher=_Usgs(_detalle()), reports_root=tmp_path)

    assert "us0000test" in relleno.fallidos


# --- El comando ------------------------------------------------------------


def test_el_comando_sale_en_verde_cuando_no_hay_nada_que_hacer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Salia 1. Un comando idempotente en rojo ensena a ignorar su exit code."""
    import argparse

    from pipelines import cli
    from pipelines.p3_report.falla_de_terreno import Relleno

    monkeypatch.setattr(cli, "_emit_github_output", lambda k, v: None)
    monkeypatch.setattr(
        "pipelines.p3_report.falla_de_terreno.backfill_ground_failure_alerts",
        lambda *a, **k: Relleno(ya_al_dia=["us0000test"]),
    )

    codigo = cli._cmd_alertas_terreno(argparse.Namespace(usgs_id="", reports=str(tmp_path)))

    assert codigo == 0
    assert "ya al dia: 1" in capsys.readouterr().err


def test_el_comando_sale_en_rojo_solo_si_no_pudo_leer_ninguno(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import argparse

    from pipelines import cli
    from pipelines.p3_report.falla_de_terreno import Relleno

    monkeypatch.setattr(cli, "_emit_github_output", lambda k, v: None)
    monkeypatch.setattr(
        "pipelines.p3_report.falla_de_terreno.backfill_ground_failure_alerts",
        lambda *a, **k: Relleno(fallidos={"us0000test": "la red"}),
    )

    assert cli._cmd_alertas_terreno(argparse.Namespace(usgs_id="", reports=str(tmp_path))) == 1
