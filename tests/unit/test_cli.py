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
from typing import Any

import pytest

from pipelines import cli
from pipelines.p1_trigger.run import TriggerResult

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
            # Los comentarios citan los subcomandos entre acentos graves —«y
            # `centinela status` regenera el resto»— y sin limpiarlos la guardia
            # reclamaba un subcomando llamado "status`". Fallaba por como esta
            # escrito el comentario, no por lo que hace el workflow, que es la
            # peor clase de falso positivo: enseña a editar el comentario para
            # callarla.
            palabra = palabra.strip("`\"'.,;:)")
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
    monkeypatch.setattr(cli, "write_status", lambda **_: destino)
    assert cli.main(["status"]) == 0


def test_status_recuperar_llega_hasta_write_status(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """El flag no sirve de nada si se queda en el parser.

    Es la salida del bloqueo que dejo al vigia dos horas ciego el 2-sep-2026:
    si no viaja hasta `write_status`, el operador cree que la tiene y no.
    """
    visto: dict[str, bool] = {}

    def falso(**kwargs: object) -> Path:
        visto["recuperar"] = bool(kwargs.get("recuperar"))
        return tmp_path / "status.json"

    monkeypatch.setattr(cli, "write_status", falso)

    assert cli.main(["status"]) == 0
    assert visto["recuperar"] is False

    assert cli.main(["status", "--recuperar"]) == 0
    assert visto["recuperar"] is True


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
    # EL TIPO DE VERDAD, NO UN NAMESPACE A MANO.
    #
    # Era un `SimpleNamespace` con los campos que hacian falta ese dia, asi que
    # cada campo nuevo de `TriggerResult` —`estados_ilegibles`, `feeds_fallidos`—
    # rompia estas pruebas con un `AttributeError` en vez de ejercitarlo. Un
    # doble escrito a mano se separa del original en cuanto el original crece.
    resultado = TriggerResult(revisados=18, relevantes=0, latido_utc="2026-08-25T15:00:00Z")

    monkeypatch.setattr(cli, "run_trigger", lambda *_a, **_k: resultado)
    monkeypatch.setattr(cli, "HttpFetcher", lambda *_a, **_k: object())
    monkeypatch.setattr(cli, "write_status", lambda **kw: escrito.update(kw) or Path("x"))
    # Sin `--dry-run`: un simulacro ya no late (ver la prueba de abajo), asi que
    # se corre de verdad con la ventana de observados desviada.
    monkeypatch.setattr(cli, "leer", lambda *_a, **_k: [])
    monkeypatch.setattr(cli, "write_observados", lambda *_a, **_k: Path("x"))

    assert cli.main(["trigger"]) == 0
    assert escrito["latido"]["revisados"] == 18
    assert json.loads(capsys.readouterr().out)["a_despachar"] == []


def test_un_simulacro_no_escribe_el_latido(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Hallazgo #155 de la auditoria de septiembre de 2026.

    `--dry-run` se saltaba `observados.json` y el estado del evento, pero no
    `write_status`: `make trigger` y el simulacro mensual reescribian el
    `site/status.json` que publica /status y le anadian un latido falso. Un
    latido es la prueba de que el vigia de verdad sigue vivo.
    """
    escrito: list[str] = []
    resultado = TriggerResult(revisados=18, relevantes=0, latido_utc="2026-08-25T15:00:00Z")

    def _anotar(que: str) -> Any:
        def _escribe(*_a: object, **_k: object) -> Path:
            escrito.append(que)
            return Path("x")

        return _escribe

    monkeypatch.setattr(cli, "run_trigger", lambda *_a, **_k: resultado)
    monkeypatch.setattr(cli, "HttpFetcher", lambda *_a, **_k: object())
    monkeypatch.setattr(cli, "write_status", _anotar("status.json"))
    monkeypatch.setattr(cli, "write_observados", _anotar("observados.json"))

    assert cli.main(["trigger", "--dry-run"]) == 0
    assert escrito == [], "el simulacro escribio en site/"
    salida = capsys.readouterr()
    assert json.loads(salida.out)["latido_fallido"] is None
    assert "el latido no se escribe" in salida.err


def test_el_json_del_trigger_sale_limpio_por_stdout(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """El workflow canaliza stdout a `python -c json.load`.

    Una linea de log en medio lo vuelve imparseable — paso de verdad al
    recalibrar los diecinueve manifests, con "Extra data: line 2 column 1".
    Por eso el log va a stderr.
    """

    resultado = TriggerResult(
        nuevos=["us1"], revisados=3, relevantes=1, latido_utc="2026-08-25T15:00:00Z"
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
        # La merma viaja por stdout, no solo al log: un estado ilegible saca al
        # sismo del despacho para siempre y un feed caido puede dejar la pasada
        # ciega. Las dos salian solo en un `_log.warning`.
        "estados_ilegibles": [],
        "feeds_fallidos": [],
        "latido_utc": "2026-08-25T15:00:00Z",
        # Y el veredicto del latido, que ya no puede matar al comando: `None`
        # cuando se publico. Ver `test_el_sismo_sobrevive_al_latido`.
        "latido_fallido": None,
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


# --- sin-pais -----------------------------------------------------------------


def _mar_abierto(tmp_path: Path, origen_utc: str) -> Path:
    from pipelines.common.state import EventState, EventStatus

    eventos = tmp_path / "events"
    EventState(
        usgs_id="us7000mar0",
        estado=EventStatus.DETECTADO,
        mag=5.8,
        lon=-100.0,
        lat=-20.0,
        depth_km=10.0,
        lugar="southern East Pacific Rise",
        origen_utc=origen_utc,
    ).save(eventos)
    return eventos


@pytest.mark.parametrize(("dias", "visible"), [(1, True), (30, False)], ids=["reciente", "viejo"])
def test_sin_pais_dice_si_el_evento_cabe_en_la_ventana(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    dias: int,
    visible: bool,
) -> None:
    """Hallazgo #154 de la auditoria de septiembre de 2026.

    El comando prometia «terminal y visible en observados», y `write_observados`
    poda por fecha de origen a cinco dias: un historico despachado a mano
    entraba y salia en la misma escritura. Ahora lo que se publica es lo que
    hay, y la salida lo declara.
    """
    from datetime import UTC, datetime, timedelta

    from pipelines.common.state import EventState, EventStatus
    from pipelines.p1_trigger import observados

    origen = (datetime.now(UTC) - timedelta(days=dias)).strftime("%Y-%m-%dT%H:%M:%SZ")
    eventos = _mar_abierto(tmp_path, origen)
    sitio = tmp_path / "site"
    monkeypatch.setattr(observados, "SITE_DIR", sitio)

    assert cli.main(["sin-pais", "us7000mar0", "--events-dir", str(eventos)]) == 0

    salida = capsys.readouterr()
    assert json.loads(salida.out)["en_observados"] is visible
    publicados = {e.usgs_id for e in observados.leer(sitio)}
    assert ("us7000mar0" in publicados) is visible
    if not visible:
        assert "fuera de la ventana" in salida.err
    estado = EventState.load("us7000mar0", eventos)
    assert estado is not None
    assert estado.estado is EventStatus.DESCARTADO


def test_impact_commitea_la_capa_donde_sin_pais_deja_el_evento() -> None:
    """La otra mitad de #154: escrito en el runner no es publicado.

    `impact.yml` hacia `git add site/status.json` y nada mas, asi que el evento
    en mar abierto se cerraba como descartado y la capa que lo pintaba se
    quedaba en el disco del runner.
    """
    raiz = Path(__file__).resolve().parents[2]
    texto = (raiz / ".github" / "workflows" / "impact.yml").read_text(encoding="utf-8")
    anadidos = {
        argumento
        for linea in texto.splitlines()
        if (comando := linea.strip()).startswith("git add ")
        for argumento in comando.removeprefix("git add ").split()
    }

    assert "site/observados.json" in anadidos
