"""Un sismo detectado no puede quedarse sin reporte y sin que nadie lo diga.

LA FORMA EXACTA DEL FALLO DEL 2-SEP-2026. Un M5,6 a 71 km al OSO de Puerto
Madero, Mexico. El vigia lo detecto y despacho en minutos; P2 lo rechazo veinte
veces seguidas porque trataba «el ShakeMap no alcanza ninguna celda» como error
incluso con el pais bien enrutado. Durante ochenta y nueve minutos hubo un sismo
real, detectado, dentro de alcance, **sin reporte publicado** — y lo unico que lo
decia era una incidencia repetida que se leia como ruido.

Nada comprobaba esa forma: ni que el evento existiera, ni que le faltara el
reporte. El catalogo se vigilaba por dentro —que las cifras cuadren, que los
CSV sumen— y no por el hueco entre lo detectado y lo publicado.

DOS PREGUNTAS DISTINTAS, Y LAS DOS IMPORTAN:

- **¿Hay algun evento en vuelo atascado?** Uno reciente sin reporte es el fallo
  de hoy repitiendose, y hay que verlo el mismo dia.
- **¿Cuantos huecos historicos quedan?** Los que ya estaban, enumerados con
  nombre para que la lista solo pueda encoger.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

RAIZ = Path(__file__).parent.parent.parent
EVENTOS = RAIZ / "events"
REPORTES = RAIZ / "reports"

#: Cuantas horas puede llevar un evento detectado sin reporte antes de que sea
#: un atasco. El del 2-sep tardo 89 minutos **con el fallo de por medio**; en
#: regimen son minutos. Seis horas es holgado a proposito: lo que se persigue
#: aqui es el silencio de medio dia, no un despacho que va tarde.
MAX_HORAS_SIN_REPORTE = 6.0

#: Detectados hace anos y nunca despachados, de la barrida historica que la
#: auditoria ya documenta: la busqueda se hizo sobre cajas envolventes que se
#: llenan de sismos chilenos y la lista se leyo truncada. Ver PENDIENTES
#: 2.1.bis. **Solo puede encoger.**
HUECOS_HISTORICOS: frozenset[str] = frozenset(
    {
        "pr2025056002",
        "pr2025175000",
        "us1000jg5z",
        "us7000kg9g",
    }
)


def _estados() -> list[tuple[str, dict[str, Any]]]:
    return [
        (p.stem, json.loads(p.read_text(encoding="utf-8"))) for p in sorted(EVENTOS.glob("*.json"))
    ]


def _tiene_reporte(usgs_id: str) -> bool:
    return (REPORTES / usgs_id / "report.json").is_file()


def _horas(origen_utc: str) -> float:
    t = datetime.strptime(origen_utc, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    return (datetime.now(UTC) - t).total_seconds() / 3600


def test_ningun_evento_en_vuelo_lleva_horas_sin_reporte() -> None:
    """El fallo de hoy, si volviera a pasar, se ve el mismo dia.

    No mira la causa —puede ser P2, el activo, la red— sino el hueco: hay un
    sismo detectado, dentro de alcance, y la pagina no publica nada de el.
    """
    atascados = [
        f"{eid} (M{d['mag']}, {_horas(d['origen_utc']):.0f} h, estado {d['estado']}): {d['lugar']}"
        for eid, d in _estados()
        if eid not in HUECOS_HISTORICOS
        and not _tiene_reporte(eid)
        and _horas(d["origen_utc"]) > MAX_HORAS_SIN_REPORTE
    ]

    assert not atascados, "hay sismos detectados y sin reporte publicado:\n  " + "\n  ".join(
        atascados
    )


def test_todo_lo_publicado_tiene_su_reporte() -> None:
    """Un estado que dice `publicado` sin reporte al lado miente sobre si mismo."""
    mienten = [
        eid for eid, d in _estados() if d["estado"] == "publicado" and not _tiene_reporte(eid)
    ]

    assert not mienten, f"su event_state dice publicado y no hay report.json: {mienten}"


def test_la_lista_de_huecos_historicos_no_se_pudre() -> None:
    """Si uno se despacha, sale de la lista. Solo puede encoger.

    Sin esto, un hueco resuelto se quedaria excluido para siempre y su guardia
    no volveria a correr — que es como una excepcion temporal se vuelve
    permanente sin que nadie lo decida.
    """
    ya_resueltos = sorted(e for e in HUECOS_HISTORICOS if _tiene_reporte(e))

    assert not ya_resueltos, (
        f"estos ya tienen reporte y siguen en HUECOS_HISTORICOS: {ya_resueltos}. "
        "Quitalos de la lista."
    )


def test_la_lista_no_nombra_eventos_que_no_existen() -> None:
    """Un id mal copiado dejaria un evento sin vigilar sin que nada lo diga."""
    conocidos = {eid for eid, _ in _estados()}
    fantasmas = sorted(HUECOS_HISTORICOS - conocidos)

    assert not fantasmas, f"la lista nombra eventos que no estan en events/: {fantasmas}"


@pytest.mark.parametrize("campo", ["mag", "lon", "lat", "origen_utc", "estado"])
def test_todo_event_state_trae_lo_que_esta_guardia_necesita(campo: str) -> None:
    """La guardia se cae en silencio si un estado no trae lo que lee.

    Un `KeyError` dentro de una comprension no falla la prueba: la hace
    reventar, que en una suite grande se lee igual que un fallo cualquiera y no
    dice que la vigilancia se quedo ciega.
    """
    sin_campo = [eid for eid, d in _estados() if campo not in d]

    assert not sin_campo, f"event_state sin `{campo}`: {sin_campo}"
