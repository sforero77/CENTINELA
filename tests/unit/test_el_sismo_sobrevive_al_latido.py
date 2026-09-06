"""El sismo ya detectado no se puede perder por la contabilidad de despues.

`run_trigger` hace el trabajo que importa al principio: lee el feed, decide que
eventos son relevantes y **escribe su estado en disco**. Todo lo que viene
detras —el latido de `/status`, el commit, la republicacion del visor— es
contabilidad sobre un hecho que ya ocurrio.

El 2-sep-2026 esa contabilidad se llevo por delante el hecho. `write_status` se
niega, con razon, a reescribir un `site/status.json` ilegible: publicar encima
borraria el historial de latidos, que es la unica prueba de que el vigia esta
vivo. Pero la excepcion no la paraba nadie:

    centinela trigger
      -> run_trigger  ........ el sismo queda escrito en events/
      -> write_status ........ ValueError: status.json existe y no se puede leer
      -> [muere]

y a partir de ahi, en cascada:

  * `observados.json` no se reescribe
  * el paso del workflow queda en rojo
  * `Publicar estado y latido` lleva `success()` implicito -> se salta
  * `despachar` depende de `needs: vigilar` -> se salta

O sea: un fichero derivado con dos lineas de marcadores de conflicto bastaba
para que un terremoto detectado no se reportara **nunca**. Ni el latido que
delata el problema, porque el latido tampoco llegaba a commitearse.

Aqui se prueban las dos mitades de la reparacion: que el comando termina su
trabajo y sale en rojo en vez de morir a medias, y que el workflow ya no
confunde "la corrida termino mal" con "no hay nada que despachar".
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import yaml

from pipelines import cli
from pipelines.p1_trigger.run import TriggerResult

WORKFLOWS = Path(__file__).parent.parent.parent / ".github" / "workflows"


def _que_revienta(**_kwargs: Any) -> Path:
    raise ValueError("site/status.json existe y no se puede leer (marcadores de conflicto)")


def test_un_status_ilegible_no_se_traga_el_sismo(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    """El latido cae, y aun asi salen los eventos, la ventana y el codigo 1."""
    salidas = tmp_path / "outputs"
    salidas.write_text("", encoding="utf-8")
    monkeypatch.setenv("GITHUB_OUTPUT", str(salidas))

    observados_escritos: list[Any] = []
    resultado = TriggerResult(
        nuevos=["us7000abcd"], revisados=12, relevantes=1, latido_utc="2026-09-02T20:01:00Z"
    )

    monkeypatch.setattr(cli, "run_trigger", lambda *_a, **_k: resultado)
    monkeypatch.setattr(cli, "HttpFetcher", lambda *_a, **_k: object())
    monkeypatch.setattr(cli, "write_status", _que_revienta)
    monkeypatch.setattr(cli, "leer", lambda *_a, **_k: [])
    monkeypatch.setattr(
        cli, "write_observados", lambda evs, *_a, **_k: observados_escritos.append(evs) or Path("x")
    )

    codigo = cli.main(["trigger"])

    # 1. LA CORRIDA SE VE ROJA. Un latido que no se publica es un fallo real y
    #    no se disimula: lo que no puede es ser un fallo *mudo*.
    assert codigo == 1

    # 2. PERO EL SISMO SALE. Es lo unico que no se puede perder.
    salida = salidas.read_text(encoding="utf-8")
    assert "eventos<<" in salida or "eventos=" in salida
    assert "us7000abcd" in salida
    assert "hay_trabajo=true" in salida

    # 3. Y EL RESTO DEL TRABAJO SE TERMINA. Antes el comando moria en el latido
    #    y la ventana de observados se quedaba con la poda del dia anterior.
    assert observados_escritos == [[]]

    # 4. LA CAUSA ES LEGIBLE, en stdout para quien parsea y en stderr para quien
    #    lee. "Fallo el latido" y "no habia sismos" no se pueden confundir.
    capturado = capsys.readouterr()
    assert "no se puede leer" in capturado.err
    assert json.loads(capturado.out)["latido_fallido"]


def test_el_latido_sano_no_declara_fallo(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """La otra mitad: sin `try/except` que se trague un error de verdad.

    Un `except` demasiado ancho convierte cualquier fallo en un aviso, y esa es
    la forma exacta que esta auditoria lleva persiguiendo. Se comprueba que el
    camino sano sigue saliendo en verde y sin declarar perdida.
    """
    resultado = TriggerResult(revisados=4, relevantes=0, latido_utc="2026-09-02T21:00:00Z")
    monkeypatch.setattr(cli, "run_trigger", lambda *_a, **_k: resultado)
    monkeypatch.setattr(cli, "HttpFetcher", lambda *_a, **_k: object())
    monkeypatch.setattr(cli, "write_status", lambda **_k: Path("x"))

    assert cli.main(["trigger", "--dry-run"]) == 0
    assert json.loads(capsys.readouterr().out)["latido_fallido"] is None


# --------------------------------------------------------------------------
# La otra mitad de la reparacion vive en el YAML.
# --------------------------------------------------------------------------


def _trigger() -> dict[str, Any]:
    datos = yaml.safe_load((WORKFLOWS / "trigger.yml").read_text(encoding="utf-8"))
    assert isinstance(datos, dict)
    return datos


def test_el_despacho_no_depende_de_que_todo_lo_demas_salga_bien() -> None:
    """`needs:` trae un `success()` de regalo que nadie pidio.

    Con `if: needs.vigilar.outputs.hay_trabajo == 'true'` a secas, GitHub salta
    el job en cuanto el anterior termina en rojo — por el motivo que sea, aunque
    el sismo este identificado y `hay_trabajo` diga `true`.
    """
    condicion = _trigger()["jobs"]["despachar"]["if"]
    assert "!cancelled()" in condicion, (
        "sin `!cancelled()`, un vigia rojo se salta el despacho de P2 aunque ya "
        "tenga el evento detectado y escrito en disco"
    )
    # Y sigue sin disparar a ciegas: hace falta que el paso del feed haya
    # llegado a declarar trabajo.
    assert "hay_trabajo == 'true'" in condicion
    # Ni en simulacro. Un ensayo que produce el efecto que ensaya no es ensayo.
    assert "!inputs.dry_run" in condicion


def test_el_latido_de_la_pasada_ciega_llega_a_commitearse() -> None:
    """El caso que el latido existe para cubrir era el unico que no se publicaba.

    `centinela trigger` sale con 1 **a proposito** cuando los dos feeds de USGS
    estan caidos: la corrida tiene que verse roja porque "cero eventos" ahi
    significa "no mire". Con el `success()` implicito del paso, ese mismo codigo
    de salida saltaba la publicacion — asi que la senal se generaba y se tiraba.
    """
    pasos = {p.get("name"): p for p in _trigger()["jobs"]["vigilar"]["steps"]}

    publicar = pasos["Publicar estado y latido"]
    assert "!cancelled()" in publicar["if"], (
        "un paso sin `if` explicito lleva `success()`: el latido de la pasada "
        "ciega, que es el que hace falta, nunca se commiteaba"
    )

    republicar = pasos["Republicar el visor"]
    assert "!cancelled()" in republicar["if"], (
        "si se llego a commitear, la pagina tiene que enterarse aunque la "
        "corrida vaya a terminar en rojo"
    )


def test_el_latido_al_monitor_externo_sigue_exigiendo_verde() -> None:
    """Y el que **no** debe llevar `!cancelled()`, para que nadie lo iguale.

    El monitor de healthchecks.io interpreta el silencio como alarma. Un latido
    enviado desde una corrida que fallo le dice "estoy vivo" cuando no lo esta,
    y lo convierte en un detector de "no corrio" que nunca ve "corrio y se
    rompio" — justo el caso que los pasos de arriba acaban de habilitar.
    """
    pasos = {p.get("name"): p for p in _trigger()["jobs"]["vigilar"]["steps"]}
    monitor = pasos["Latido al monitor externo"]
    assert monitor["if"].startswith("success()")
    assert "cancelled" not in monitor["if"]
