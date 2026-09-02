"""Pagina de estado: latencia medida y publicada (RNF-02).

La espec es explicita en que **la transparencia es parte del producto**: no
basta con tener un objetivo de latencia, hay que publicar la distribucion real
y dejar que cualquiera compare. Aqui se calcula esa distribucion a partir de lo
unico que no se puede falsear: los timestamps que el propio sistema fue
escribiendo en cada ``event_state``.

La latencia que importa es la que separa el **origen del sismo** de la
**publicacion del reporte**. Incluye la demora del cron de GitHub Actions, que
no controlamos, asi que se publica tambien desagregada — el SLO se define sobre
lo controlable, pero el lector merece ver el total.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from itertools import pairwise
from pathlib import Path
from typing import Any

from .logging import get_logger
from .paths import EVENTS_DIR, REPORTS_DIR, SITE_DIR
from .state import EventState, EventStatus, utcnow_iso

_log = get_logger(__name__)

#: Cuantos latidos del disparador se conservan. Suficiente para ver un patron
#: sin que el archivo crezca sin limite.
MAX_LATIDOS = 200

STATUS_FILENAME = "status.json"


@dataclass(frozen=True, slots=True)
class EventLatency:
    """Latencia de un evento publicado."""

    usgs_id: str
    origen_utc: str
    publicado_utc: str
    minutos: float
    #: Reconstruccion retrospectiva: se lista, pero no cuenta para el p50/p95.
    backtest: bool = False


def _parse(ts: str) -> datetime | None:
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def event_latencies(
    events_dir: Path | None = None, *, reports_root: Path | None = None
) -> list[EventLatency]:
    """Minutos entre el origen del sismo y la publicacion del reporte.

    **Solo cuentan los eventos cuyo reporte existe de verdad.** Un `event_state`
    en estado PUBLICADO es una afirmacion; el directorio en `reports/` es la
    prueba. Cuando se separan, gana la prueba.

    No es paranoia de esquema: el 26-ago-2026 la pagina publica llego a servir
    un evento `us7000abcd` —inexistente en USGS, HTTP 404— con
    `"backtest": false` y una latencia de 20,0 minutos, contando como el unico
    evento real publicado por el sistema. Salio de un `event_state` de prueba
    que existio un rato y se borro despues; `status.json` ya lo habia
    absorbido.

    Publicar una latencia inventada es el peor fallo posible de esta pagina en
    concreto, porque su unica razon de existir es que la latencia sea
    verificable: si el numero puede salir de la nada, la pagina deja de probar
    nada.
    """
    base = events_dir or EVENTS_DIR
    reportes = reports_root or REPORTS_DIR
    latencias: list[EventLatency] = []
    for path in sorted(base.glob("*.json")):
        try:
            estado = EventState.from_dict(json.loads(path.read_text(encoding="utf-8")))
        except (ValueError, KeyError, OSError) as error:
            # Se salta, pero no en silencio: si `events/` se corrompe hay que
            # enterarse. Es el mismo patron de `repaso.py` y `rezago.py`; aqui
            # era el unico de los tres sin log.
            _log.warning(
                "event_state ilegible al calcular latencias",
                extra={"context": {"ruta": str(path), "error": str(error)}},
            )
            continue
        if estado.estado is not EventStatus.PUBLICADO:
            continue
        publicado = estado.timestamps.get("publicado", "")
        inicio, fin = _parse(estado.origen_utc), _parse(publicado)
        if inicio is None or fin is None:
            continue
        if not (reportes / estado.usgs_id / "report.json").is_file():
            _log.warning(
                "event_state dice PUBLICADO pero no hay reporte; no se publica su latencia",
                extra={"context": {"usgs_id": estado.usgs_id}},
            )
            continue
        latencias.append(
            EventLatency(
                usgs_id=estado.usgs_id,
                origen_utc=estado.origen_utc,
                publicado_utc=publicado,
                minutos=round((fin - inicio).total_seconds() / 60.0, 1),
                backtest=estado.backtest,
            )
        )
    return sorted(latencias, key=lambda e: e.origen_utc, reverse=True)


def percentil(valores: list[float], p: float) -> float | None:
    """Percentil por interpolacion lineal. ``None`` si no hay datos."""
    if not valores:
        return None
    ordenados = sorted(valores)
    if len(ordenados) == 1:
        return round(ordenados[0], 1)
    pos = (len(ordenados) - 1) * p
    bajo = int(pos)
    alto = min(bajo + 1, len(ordenados) - 1)
    valor = ordenados[bajo] + (ordenados[alto] - ordenados[bajo]) * (pos - bajo)
    return round(valor, 1)


def cadencia_del_vigia(latidos: list[dict[str, Any]]) -> dict[str, Any]:
    """Cuanto tarda de verdad el cron entre una revision y la siguiente.

    Es la unica cifra de este sistema que mide **la infraestructura y no el
    sismo**, y hasta el 27-ago-2026 no se publicaba: habia que deducirla a mano
    de `gh run list` cada vez que alguien sospechaba.

    Y hace falta. Ese dia se midio que GitHub no concede un turno por workflow
    sino unos pocos por repositorio: cinco en veinticuatro horas, con cinco
    workflows programados pidiendo. El cron del vigia se bajo de diez a treinta
    minutos para dejar de acaparar una cola que no podia ganar, y la unica forma
    honesta de saber si eso sirvio es tener la serie delante.

    Se salta el hueco cuando pasa de un dia: es una parada, no una cadencia, y
    meterla en la mediana la ahogaria.

    **Un latido no es una revision.** El latido se publica como mucho una vez
    por hora para no llenar el historial de commits, asi que el hueco entre dos
    latidos cubre todas las revisiones que hubo en medio. Mientras el vigia
    corrio cada media hora los dos numeros se parecian bastante y la diferencia
    no se noto; con el cron externo a cinco minutos, el hueco entre latidos
    dejo de medir nada — la pagina publicaba "revisa cada 2,6 h" mientras el
    vigia revisaba cada cinco. Por eso cada latido declara cuantas revisiones
    representa, y el intervalo real es el hueco dividido entre ellas.

    Un latido sin ese campo cuenta como una sola revision, que es exactamente
    lo que era antes: los historicos siguen midiendo lo mismo.
    """
    con_sello = [
        (sello, max(1, int(latido.get("revisiones", 1) or 1)))
        for latido in latidos
        if (sello := _parse(str(latido.get("utc", "")))) is not None
    ]
    con_sello.sort(key=lambda par: par[0])

    intervalos = [
        minutos / cuantas
        for (antes, _), (despues, cuantas) in pairwise(con_sello)
        if 0 < (minutos := (despues - antes).total_seconds() / 60) <= 24 * 60
    ]
    if not intervalos:
        return {}

    return {
        "declarado_min": 30,
        "p50_min": percentil(intervalos, 0.50),
        "p90_min": percentil(intervalos, 0.90),
        "peor_min": round(max(intervalos), 1),
        "revisiones": sum(cuantas for _, cuantas in con_sello[1:]) + 1,
        "latidos": len(con_sello),
    }


def build_status(
    *,
    events_dir: Path | None = None,
    latidos: list[dict[str, Any]] | None = None,
    reports_root: Path | None = None,
) -> dict[str, Any]:
    """Construye el ``status.json`` que consume la pagina."""
    latencias = event_latencies(events_dir, reports_root=reports_root)
    # Los backtests se listan pero no entran en la estadistica: se publican
    # dias despues del sismo y su "latencia" no mide nada del sistema.
    en_vivo = [e for e in latencias if not e.backtest]
    minutos = [e.minutos for e in en_vivo]
    return {
        "generado_utc": utcnow_iso(),
        "objetivo": {"p50_min": 60, "p95_min": 90},
        "medido": {
            "eventos_publicados": len(en_vivo),
            "backtests_excluidos": len(latencias) - len(en_vivo),
            "p50_min": percentil(minutos, 0.50),
            "p95_min": percentil(minutos, 0.95),
            "peor_min": max(minutos) if minutos else None,
        },
        "eventos": [
            {
                "usgs_id": e.usgs_id,
                "origen_utc": e.origen_utc,
                "publicado_utc": e.publicado_utc,
                "minutos": e.minutos,
                "backtest": e.backtest,
            }
            for e in latencias[:50]
        ],
        "cadencia": cadencia_del_vigia(previos_y_nuevo := (latidos or [])),
        "latidos": previos_y_nuevo[-MAX_LATIDOS:],
        "nota": (
            "La latencia incluye la demora del cron de GitHub Actions, que el "
            "proyecto no controla y que su documentacion situa entre 5 y 30 "
            "minutos. El objetivo se define sobre lo controlable; esta cifra es "
            "el total real, sin descontar nada."
        ),
    }


@dataclass(frozen=True)
class HistorialPrevio:
    """Los latidos que habia, y lo que hubo que tirar para llegar a ellos."""

    latidos: list[dict[str, Any]]
    #: Solo cuando `--recuperar` aparto un fichero ilegible. Viaja al JSON.
    perdido_por: str | None = None
    apartado_en: str | None = None


def _latidos_previos(destino: Path, *, recuperar: bool = False) -> HistorialPrevio:
    """El historial que ya hay, o vacio **solo si el fichero no existe**.

    ESTE `except` BORRO EL LATIDO ENTERO DURANTE HORAS.

    Decia `except (ValueError, OSError): previos = []`, y eso convierte «no
    pude leer los latidos» en «no habia latidos». Se disparo de verdad el
    2-sep-2026: dos sismos en vivo corriendo a la vez, cada P2/P3 en su propio
    grupo de concurrencia, y el manejador de rebase de `impact.yml` llamando a
    `centinela status` para regenerar los derivados **con el fichero todavia
    lleno de marcadores de conflicto**. `json.loads` fallaba, el historial se
    reponia vacio, y `cadencia_del_vigia` sobre una lista vacia dejaba tambien
    `cadencia: {}`.

    El resultado fue una pagina publicando `latidos: []` —el sintoma exacto del
    hallazgo A1 de la auditoria, dado por cerrado— mientras tres documentos
    citaban cifras de esos campos. Nadie lo vio porque `frescura` comprueba
    `generado_utc`, que si se actualizaba.

    Ahora se distinguen los dos casos. Que no exista es normal: la primera
    corrida de un repositorio nuevo. Que exista y no se pueda leer **no** es
    normal, y publicar un historial vacio encima seria destruir la unica prueba
    de que el vigia esta vivo.
    """
    if not destino.exists():
        return HistorialPrevio(latidos=[])
    try:
        crudo = json.loads(destino.read_text(encoding="utf-8"))
    except (ValueError, OSError) as error:
        if not recuperar:
            raise ValueError(
                f"{destino} existe y no se puede leer ({error}). No se reescribe: "
                f"hacerlo publicaria un historial de latidos vacio y borraria la "
                f"unica senal de que el vigia sigue vivo. Para salir de aqui: "
                f"`centinela status --recuperar`, que aparta el fichero ilegible "
                f"y arranca historial nuevo dejando constancia de la perdida."
            ) from error
        # LA SALIDA DEL BLOQUEO, Y POR QUE ES EXPLICITA.
        #
        # La negativa de arriba cerro el hallazgo A1 y es correcta. Lo que no
        # tenia era salida: **todo** camino que escribe este fichero pasa por
        # aqui, incluido `centinela status`, asi que el unico comando capaz de
        # repararlo se negaba a correr mientras estuviera roto. El 2-sep-2026
        # un conflicto de dos lineas dejo al vigia dos horas ciego por eso.
        #
        # La salida no se toma sola: la pide una persona con `--recuperar`. Se
        # aparta el original en vez de borrarlo —el historial perdido es
        # evidencia— y la perdida viaja al JSON publicado, que es donde alguien
        # la va a ver.
        apartado = destino.with_suffix(f".ilegible-{utcnow_iso().replace(':', '')}.json")
        destino.rename(apartado)
        _log.error(
            "status.json ilegible: se aparta y se arranca historial nuevo",
            extra={"context": {"apartado": str(apartado), "error": str(error)}},
        )
        return HistorialPrevio(latidos=[], perdido_por=str(error), apartado_en=apartado.name)
    return HistorialPrevio(latidos=list(crudo.get("latidos", [])))


def write_status(
    *,
    events_dir: Path | None = None,
    site_dir: Path | None = None,
    latido: dict[str, Any] | None = None,
    reports_root: Path | None = None,
    recuperar: bool = False,
) -> Path:
    """Escribe ``site/status.json``, conservando el historial de latidos.

    Con ``recuperar`` se sale del bloqueo que deja un fichero ilegible: se
    aparta, se arranca historial nuevo y la perdida se declara en el JSON.
    """
    destino = (site_dir or SITE_DIR) / STATUS_FILENAME
    historial = _latidos_previos(destino, recuperar=recuperar)
    previos = [*historial.latidos, latido] if latido else list(historial.latidos)

    destino.parent.mkdir(parents=True, exist_ok=True)
    datos = build_status(events_dir=events_dir, reports_root=reports_root, latidos=previos)
    if historial.perdido_por:
        # LA PERDIDA SE PUBLICA. Un historial que arranca de cero sin decir por
        # que es indistinguible de un vigia recien estrenado, y esa ambiguedad
        # es justo la que la guarda de `_latidos_previos` existe para evitar.
        datos["historial_reiniciado"] = {
            "utc": datos["generado_utc"],
            "motivo": historial.perdido_por,
            "fichero_apartado": historial.apartado_en,
        }
    destino.write_text(json.dumps(datos, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _log.info(
        "estado publicado",
        extra={
            "context": {
                "eventos": datos["medido"]["eventos_publicados"],
                "p50_min": datos["medido"]["p50_min"],
            }
        },
    )
    return destino
