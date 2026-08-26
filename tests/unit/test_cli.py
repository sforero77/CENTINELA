"""La capa que conecta todo, que era la unica sin una sola prueba.

`cli.py` no calcula nada: despacha. Y **todos los fallos que este proyecto ha
tenido que cazar fueron fallos de despacho**, no de calculo — el reporte
preliminar escrito y sin llamador, las tres capas del activo agregadas a tablas
que nadie leia, los seis PNG vacios de `static_map.py`. La cobertura de este
modulo era 0 %, que es exactamente donde vivian.

Las pruebas de aqui no verifican cifras: verifican que **el comando llega a la
funcion**, que su codigo de salida significa lo que los workflows creen que
significa, y que un fallo se ve.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from pipelines import cli

# --- El contrato del parser -------------------------------------------------


def _subparsers(parser: argparse.ArgumentParser) -> dict[str, argparse.ArgumentParser]:
    """Los subcomandos registrados, por nombre."""
    for accion in parser._subparsers._group_actions:  # type: ignore[union-attr]
        if isinstance(accion, argparse._SubParsersAction):
            return dict(accion.choices)
    raise AssertionError("el parser no declara subcomandos")


def test_todos_los_subcomandos_tienen_manejador() -> None:
    """Un subcomando sin `func` revienta con AttributeError al invocarse.

    Y revienta en el runner, durante el evento, no en CI.
    """
    for nombre, sub in _subparsers(cli.build_parser()).items():
        assert callable(sub.get_default("func")), f"{nombre} no tiene manejador"


def test_los_workflows_solo_llaman_a_subcomandos_que_existen() -> None:
    """Renombrar un subcomando sin tocar los workflows los rompe en silencio.

    El fallo no aparece hasta que el workflow corre — y `impact.yml` corre
    durante un terremoto.
    """
    registrados = set(_subparsers(cli.build_parser()))
    raiz = Path(__file__).parent.parent.parent

    invocados: set[str] = set()
    for workflow in sorted((raiz / ".github" / "workflows").glob("*.yml")):
        for linea in workflow.read_text(encoding="utf-8").splitlines():
            _, _, resto = linea.partition("centinela ")
            if not resto:
                continue
            palabra = resto.split()[0] if resto.split() else ""
            if palabra and not palabra.startswith("-") and not palabra.startswith("$"):
                invocados.add(palabra)

    assert invocados, "ningun workflow invoca al CLI: la extraccion esta rota"
    assert invocados <= registrados, (
        f"Workflows que llaman a subcomandos inexistentes: {sorted(invocados - registrados)}"
    )


def test_cada_subcomando_acepta_su_ayuda() -> None:
    """`--help` recorre la configuracion entera de argparse.

    Un `default` incoherente o un `type` mal puesto salen aqui y no en la
    primera invocacion real.
    """
    parser = cli.build_parser()
    for nombre in _subparsers(parser):
        with pytest.raises(SystemExit) as salida:
            parser.parse_args([nombre, "--help"])
        assert salida.value.code == 0


def test_sin_subcomando_no_hace_nada_en_silencio() -> None:
    with pytest.raises(SystemExit):
        cli.main([])


# --- Despacho ---------------------------------------------------------------


def test_main_devuelve_el_codigo_del_manejador(monkeypatch: pytest.MonkeyPatch) -> None:
    """Los workflows se ramifican con el codigo de salida: tiene que propagarse."""
    monkeypatch.setattr(cli, "write_status", lambda **_: Path("x"))
    monkeypatch.setattr(cli, "_cmd_status", lambda _args: 7)
    assert cli.main(["status"]) == 7


def test_una_etapa_pendiente_sale_con_codigo_2(monkeypatch: pytest.MonkeyPatch) -> None:
    """`NotImplementedError` no puede confundirse con un fallo de calculo.

    Es la guardia que acompana a `test_pendientes.py`: si alguien deja una
    etapa a medias, el sistema lo dice con un codigo propio.
    """

    def pendiente(_args: argparse.Namespace) -> int:
        raise NotImplementedError("la brigada es Fase 2")

    monkeypatch.setattr(cli, "_cmd_status", pendiente)
    assert cli.main(["status"]) == 2


def test_status_escribe_la_pagina(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    destino = tmp_path / "status.json"
    monkeypatch.setattr(cli, "write_status", lambda: destino)
    assert cli.main(["status"]) == 0


def test_trigger_publica_el_latido_aunque_no_haya_eventos(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """El latido es la senal de que el cron sigue vivo.

    Se escribe **siempre**, y sobre todo cuando no hay eventos: su ausencia es
    lo que delata que GitHub desactivo los schedules a los 60 dias, que es el
    modo de falla mas probable del proyecto. `trigger.yml` llego a condicionar
    el commit de `status.json` a que hubiera trabajo, con lo que el unico caso
    que el latido vigila era justo el que no se publicaba.
    """
    escrito: dict[str, Any] = {}
    resultado = SimpleNamespace(
        nuevos=[],
        revisitados=[],
        a_despachar=[],
        revisados=18,
        relevantes=0,
        observados=[],
        latido_utc="2026-08-25T15:00:00Z",
    )

    monkeypatch.setattr(cli, "run_trigger", lambda *_a, **_k: resultado)
    monkeypatch.setattr(cli, "HttpFetcher", lambda *_a, **_k: object())
    monkeypatch.setattr(cli, "write_status", lambda **kw: escrito.update(kw) or Path("x"))

    assert cli.main(["trigger", "--dry-run"]) == 0
    assert escrito["latido"]["revisados"] == 18
    assert json.loads(capsys.readouterr().out)["a_despachar"] == []


def test_el_json_del_trigger_sale_limpio_por_stdout(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """El workflow canaliza stdout a `python -c json.load`.

    Una linea de log en medio lo vuelve imparseable — paso de verdad al
    recalibrar los diecinueve manifests, con "Extra data: line 2 column 1".
    Por eso el log va a stderr.
    """

    resultado = SimpleNamespace(
        nuevos=["us1"],
        revisitados=[],
        a_despachar=["us1"],
        revisados=3,
        relevantes=1,
        observados=[],
        latido_utc="2026-08-25T15:00:00Z",
    )

    monkeypatch.setattr(cli, "run_trigger", lambda *_a, **_k: resultado)
    monkeypatch.setattr(cli, "HttpFetcher", lambda *_a, **_k: object())
    monkeypatch.setattr(cli, "write_status", lambda **_k: Path("x"))
    # Sin `--dry-run` esto publica de verdad, y una prueba no puede reescribir
    # el `site/` del repo.
    monkeypatch.setattr(cli, "leer", lambda *_a, **_k: [])
    monkeypatch.setattr(cli, "write_observados", lambda *_a, **_k: Path("x"))

    cli.main(["trigger"])
    assert json.loads(capsys.readouterr().out) == {
        "nuevos": ["us1"],
        "revisitados": [],
        "a_despachar": ["us1"],
        "revisados": 3,
        "observados": 0,
        "latido_utc": "2026-08-25T15:00:00Z",
    }


# --- Salida para GitHub Actions ---------------------------------------------


def test_el_output_se_anexa_y_no_se_pisa(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """`$GITHUB_OUTPUT` es acumulativo: abrirlo en modo `w` borraria lo previo."""
    destino = tmp_path / "salida.txt"
    monkeypatch.setenv("GITHUB_OUTPUT", str(destino))

    cli._emit_github_output("eventos", '["us1"]')
    cli._emit_github_output("hay_trabajo", "true")

    assert destino.read_text(encoding="utf-8") == 'eventos=["us1"]\nhay_trabajo=true\n'


def test_fuera_de_actions_no_escribe_nada(monkeypatch: pytest.MonkeyPatch) -> None:
    """En local no hay `$GITHUB_OUTPUT` y el comando no puede fallar por eso."""
    monkeypatch.delenv("GITHUB_OUTPUT", raising=False)
    cli._emit_github_output("eventos", "[]")  # no revienta


# --- lint-manifests ---------------------------------------------------------


def test_lint_manifests_falla_con_un_manifest_roto(tmp_path: Path) -> None:
    """CI se apoya en este codigo de salida para bloquear el merge."""
    (tmp_path / "COL.yaml").write_text("no soy un manifest", encoding="utf-8")
    assert cli.main(["lint-manifests", "--dir", str(tmp_path)]) == 1


def test_lint_manifests_sin_manifests_es_error(tmp_path: Path) -> None:
    """Un directorio vacio devolviendo 0 seria un lint que aprueba la nada."""
    assert cli.main(["lint-manifests", "--dir", str(tmp_path)]) == 1


def test_lint_manifests_aprueba_los_del_repositorio() -> None:
    """Los diecinueve manifests reales pasan su propio lint."""
    assert cli.main(["lint-manifests"]) == 0


# --- paises-candidatos ------------------------------------------------------


def test_paises_candidatos_sin_estado_ni_detail_falla(tmp_path: Path) -> None:
    """Devolver la lista vacia dejaria a `impact.yml` sin activo y sin motivo."""
    assert cli.main(["paises-candidatos", "us6000xxxx", "--events-dir", str(tmp_path)]) == 1


def test_paises_candidatos_resuelve_desde_el_estado(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """El epicentro del Choco tiene que resolver a Colombia."""
    from pipelines.common.state import EventState, EventStatus

    EventState(
        usgs_id="us6000tjl2",
        estado=EventStatus.DETECTADO,
        mag=7.4,
        lon=-76.2422,
        lat=4.8436,
        depth_km=110.3,
        lugar="Choco",
        origen_utc="2026-08-10T12:34:28Z",
    ).save(tmp_path)

    assert cli.main(["paises-candidatos", "us6000tjl2", "--events-dir", str(tmp_path)]) == 0
    assert "COL" in capsys.readouterr().out.split()


# --- regenerar-mapas --------------------------------------------------------


def test_regenerar_mapas_sin_reportes_avisa(tmp_path: Path) -> None:
    """Salir con 0 sin haber dibujado nada es el silencio que hay que evitar."""
    assert cli.main(["regenerar-mapas", "--reports", str(tmp_path)]) == 1


def test_regenerar_mapas_de_un_evento_inexistente_falla(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        cli.main(["regenerar-mapas", "us6000tjl2", "--reports", str(tmp_path)])
