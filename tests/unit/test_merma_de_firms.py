"""Ceguera es "no lei nada util", no "fallo el transporte".

Y la merma tiene que salir del proceso: al JSON publicado, al output del
workflow y al codigo de salida. Se media y se quedaba dentro.

Dos casos que pasaban por corrida sana:

* Seis HTTP 200 con el cuerpo vacio o la cabecera renombrada: `focos=0`,
  `fallidos=0`, `ciego=False`. P5 salia por el retorno temprano, el workflow
  quedaba verde y el visor seguia sirviendo el fuego de la corrida anterior.
* Tres de los seis ficheros caidos —Sudamerica entera, el 11,9 % del dato—:
  exit 0 y la capa publicada con cara de completa.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from pipelines.p5_incendios.firms import Lectura
from pipelines.p5_incendios.run import IncendiosResult

CABECERA = "latitude,longitude,bright_ti4,acq_date,acq_time,satellite,confidence,frp\n"
FILA = "4.5,-75.2,320.1,2026-09-05,1830,N,nominal,12.5\n"


# --- La definicion de ceguera ----------------------------------------------


def test_seis_ficheros_vacios_es_ceguera() -> None:
    """El caso que pasaba: 200 OK, cuerpo sin filas, cero fallidos."""
    lectura = Lectura(focos=[], fallidos=[], pedidos=6, leidos=0)
    assert lectura.ciego, "seis ficheros sin una sola deteccion no es un dia tranquilo"


def test_seis_ficheros_caidos_sigue_siendo_ceguera() -> None:
    """El caso que ya se cubria, y que no puede dejar de cubrirse."""
    lectura = Lectura(focos=[], fallidos=[f"S{i}" for i in range(6)], pedidos=6, leidos=0)
    assert lectura.ciego


def test_un_solo_fichero_con_dato_ya_no_es_ceguera() -> None:
    """Cinco de seis caidos degrada la capa, no la invalida."""
    lectura = Lectura(focos=[], fallidos=[f"S{i}" for i in range(5)], pedidos=6, leidos=1)
    assert not lectura.ciego


def test_sin_peticiones_no_hay_ceguera() -> None:
    """`pedidos=0` es una corrida que no pidio nada, no una ciega."""
    assert not Lectura(focos=[], fallidos=[], pedidos=0, leidos=0).ciego


def test_el_resultado_de_la_corrida_usa_la_misma_regla() -> None:
    """`IncendiosResult.ciego` preguntaba solo por el transporte, igual que Lectura."""
    assert IncendiosResult(pedidos=6, fallidos=[], ficheros_leidos=0).ciego
    assert not IncendiosResult(pedidos=6, fallidos=["a"], ficheros_leidos=5).ciego


# --- Que la lectura de verdad cuente los vacios aparte ----------------------


class _FetcherFalso:
    def __init__(self, cuerpos: list[str]) -> None:
        self.cuerpos = cuerpos
        self.i = 0

    def get_bytes(self, url: str) -> bytes:
        cuerpo = self.cuerpos[self.i % len(self.cuerpos)]
        self.i += 1
        if cuerpo is None:
            raise TimeoutError(url)
        return cuerpo.encode("utf-8")


def test_un_csv_con_solo_cabecera_no_cuenta_como_leido() -> None:
    from pipelines.p5_incendios.firms import fetch_focos

    lectura = fetch_focos(_FetcherFalso([CABECERA]))
    assert lectura.pedidos == 6
    assert lectura.fallidos == []
    assert lectura.leidos == 0
    assert lectura.ciego, "seis cabeceras sin filas se colaban como corrida sana"


def test_un_csv_con_filas_si_cuenta() -> None:
    from pipelines.p5_incendios.firms import fetch_focos

    lectura = fetch_focos(_FetcherFalso([CABECERA + FILA]))
    assert lectura.leidos == 6
    assert not lectura.ciego


# --- Que la merma salga del proceso ----------------------------------------


def test_la_merma_viaja_al_json_publicado(tmp_path: Path) -> None:
    """`fallidos` y `pedidos` se median y se quedaban en el dataclass."""
    from pipelines.p5_incendios.incendios import write_incendios

    destino = write_incendios(
        [],
        site_dir=tmp_path,
        lectura={
            "ficheros_pedidos": 6,
            "ficheros_leidos": 3,
            "ficheros_fallidos": ["N_VIIRS/South_America", "J1_VIIRS/South_America"],
            "paises_cruzados": ["COL", "BRA"],
        },
    )
    datos: dict[str, Any] = json.loads(destino.read_text(encoding="utf-8"))

    assert datos["lectura"]["ficheros_pedidos"] == 6
    assert datos["lectura"]["ficheros_leidos"] == 3
    assert datos["lectura"]["paises_cruzados"] == ["COL", "BRA"]
    # Y un aviso en prosa, porque quien integra lee `avisos` y no cuenta ficheros.
    assert any("no es todo el fuego" in a for a in datos["avisos"])
    assert any("South_America" in a for a in datos["avisos"])


def test_sin_fallos_no_se_inventa_un_aviso(tmp_path: Path) -> None:
    from pipelines.p5_incendios.incendios import write_incendios

    destino = write_incendios(
        [],
        site_dir=tmp_path,
        lectura={
            "ficheros_pedidos": 6,
            "ficheros_leidos": 6,
            "ficheros_fallidos": [],
            "paises_cruzados": [],
        },
    )
    datos = json.loads(destino.read_text(encoding="utf-8"))
    assert "avisos" not in datos or not any("no es todo el fuego" in a for a in datos["avisos"])


def test_el_comando_avisa_de_la_lectura_parcial(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Tres de seis ficheros caidos publicaba la capa como completa y salia 0."""
    import argparse

    from pipelines import cli

    salidas: dict[str, str] = {}
    monkeypatch.setattr(cli, "_emit_github_output", lambda k, v: salidas.__setitem__(k, v))
    monkeypatch.setattr(cli, "HttpFetcher", lambda *a, **k: object())
    monkeypatch.setattr(
        "pipelines.p5_incendios.run.run_incendios",
        lambda *a, **k: IncendiosResult(
            leidos=100,
            en_latam=90,
            celdas=40,
            pedidos=6,
            fallidos=["N/South_America", "J1/South_America", "J2/South_America"],
            ficheros_leidos=3,
            publicado=Path("site/incendios.json"),
        ),
    )

    codigo = cli._cmd_incendios(argparse.Namespace(exposure=""))
    salida = capsys.readouterr()

    assert codigo == 0, "media lectura sigue publicandose: es mejor que nada"
    assert "no es todo el fuego" in salida.err
    assert salidas["ficheros_fallidos"] == "3"
    assert salidas["ficheros_pedidos"] == "6"
    assert json.loads(salida.out)["ficheros_leidos"] == 3


def test_la_corrida_ciega_sigue_saliendo_en_rojo(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    import argparse

    from pipelines import cli

    monkeypatch.setattr(cli, "_emit_github_output", lambda k, v: None)
    monkeypatch.setattr(cli, "HttpFetcher", lambda *a, **k: object())
    monkeypatch.setattr(
        "pipelines.p5_incendios.run.run_incendios",
        lambda *a, **k: IncendiosResult(pedidos=6, fallidos=[], ficheros_leidos=0),
    )

    assert cli._cmd_incendios(argparse.Namespace(exposure="")) == 1
    assert "no devolvio dato util" in capsys.readouterr().err
