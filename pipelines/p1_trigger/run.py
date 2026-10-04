"""Orquestacion de P1: feed -> filtro -> dedupe -> ``event_state`` -> dispatch.

Contrato de salida: una lista de ``usgs_id`` a despachar hacia P2 por
``repository_dispatch``. El pipeline es idempotente (RF-02): correrlo dos veces
sobre el mismo feed no crea trabajo duplicado.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path

from ..common.constants import (
    MINUTOS_ENTRE_REDESPACHOS,
    USGS_FEED_BACKFILL,
    USGS_FEED_PRIMARY,
)
from ..common.geo import LATAM_BBOX, BBox
from ..common.http import Fetcher
from ..common.logging import get_logger
from ..common.paths import USGS_ID_RE
from ..common.state import EventState, EventStatus, leer_sello_utc, utcnow_iso
from .feed import EventCandidate, fetch_feed
from .filters import evaluate
from .observados import EventoObservado

_log = get_logger(__name__)


@dataclass(slots=True)
class TriggerResult:
    """Resumen de una corrida del disparador."""

    revisados: int = 0
    relevantes: int = 0
    #: Eventos nuevos, que P2 debe procesar por primera vez.
    nuevos: list[str] = field(default_factory=list)
    #: Eventos ya conocidos, re-verificados por si hay nueva version de
    #: producto. P2 decide si hay trabajo real (RF-04).
    revisitados: list[str] = field(default_factory=list)
    #: Sismos de LATAM vistos y no despachados por quedar bajo el umbral. No se
    #: despachan, pero se publican: el vigia tiene que poder demostrar que
    #: estuvo mirando.
    observados: list[EventoObservado] = field(default_factory=list)
    #: Eventos cuyo `event_state` no se pudo leer. Se cuentan **aparte** de los
    #: relevantes: descartarlos en silencio haria que "cero eventos" no
    #: distinguiera "ninguno interesante" de "no pude leer ninguno".
    estados_ilegibles: list[str] = field(default_factory=list)
    #: Feeds que no se pudieron leer. Con los dos caidos la corrida es ciega y
    #: "cero eventos" significa "no mire", no "no habia".
    feeds_fallidos: list[str] = field(default_factory=list)
    #: Eventos conocidos que USGS marco `deleted` en esta pasada y que se
    #: cerraron. No se despachan ni se publican como observados.
    retirados: list[str] = field(default_factory=list)
    latido_utc: str = field(default_factory=utcnow_iso)

    @property
    def ciego(self) -> bool:
        """No se pudo leer NINGUN feed. Misma regla que FIRMS y que frescura."""
        return len(self.feeds_fallidos) >= self._feeds_pedidos > 0

    #: Cuantos feeds se pidieron en esta pasada. Lo fija `run_trigger`.
    _feeds_pedidos: int = 0

    @property
    def a_despachar(self) -> list[str]:
        """Eventos que se envian a P2 en esta corrida."""
        return [*self.nuevos, *self.revisitados]


#: Estados terminales: no se re-despachan.
_TERMINAL = frozenset({EventStatus.DESCARTADO})


def run_trigger(
    fetcher: Fetcher,
    *,
    feeds: tuple[str, ...] = (USGS_FEED_PRIMARY, USGS_FEED_BACKFILL),
    bbox: BBox = LATAM_BBOX,
    events_dir: Path | None = None,
    dry_run: bool = False,
) -> TriggerResult:
    """Ejecuta una pasada del disparador.

    Args:
        fetcher: cliente HTTP (real o de fixtures).
        feeds: feeds a consultar. El segundo cubre la demora del cron: si el
            runner desperto 25 min tarde, ``4.5_hour`` sigue alcanzando, pero
            ``4.5_day`` garantiza que no se pierda nada.
        bbox: ventana geografica de interes.
        events_dir: directorio de ``event_state`` (tests lo redirigen).
        dry_run: no escribe estado; util para el simulacro mensual.
    """
    result = TriggerResult()
    result._feeds_pedidos = len(feeds)
    vistos: set[str] = set()

    for feed in feeds:
        # UN FEED CAIDO NO PUEDE LLEVARSE AL OTRO.
        #
        # `fetch_feed` iba sin proteccion, asi que un 503 en `4.5_hour` abortaba
        # el bucle entero y **el feed de respaldo no se llegaba a leer** — el que
        # existe precisamente para que no se pierda un sismo cuando algo falla.
        # La excepcion subia hasta `cli.main`, que solo atrapa
        # `NotImplementedError`, y mataba la pasada.
        #
        # Es el mismo patron que ya aplican `_classify`, `repaso` y `rezago`: se
        # cuenta el fallo, se sigue con lo demas, y la merma sale del proceso.
        try:
            candidatos = fetch_feed(fetcher, feed)
        except Exception as error:
            result.feeds_fallidos.append(feed)
            _log.warning(
                "no se pudo leer un feed; se sigue con los demas",
                extra={"context": {"feed": feed, "error": str(error)}},
            )
            continue

        for candidate in candidatos:
            # Por todos sus ids y no solo por el preferido: entre la lectura de
            # un feed y la del otro USGS puede haber renumerado el evento.
            if vistos.intersection(candidate.identificadores):
                continue  # el mismo evento aparece en ambos feeds
            vistos.update(candidate.identificadores)
            result.revisados += 1

            if candidate.retirado:
                _retirar(candidate, result, events_dir=events_dir, dry_run=dry_run)
                continue

            decision = evaluate(candidate, bbox=bbox)
            if not decision:
                _log.debug(
                    "evento descartado",
                    extra={"context": {"usgs_id": candidate.usgs_id, "razon": decision.razon}},
                )
                if _solo_le_falto_magnitud(candidate, bbox):
                    result.observados.append(
                        EventoObservado.desde_candidato(candidate, decision.razon)
                    )
                continue
            result.relevantes += 1
            _classify(candidate, result, events_dir=events_dir, dry_run=dry_run)

    _log.info(
        "latido del trigger",
        extra={
            "context": {
                "revisados": result.revisados,
                "relevantes": result.relevantes,
                "estados_ilegibles": len(result.estados_ilegibles),
                "feeds_fallidos": result.feeds_fallidos,
                "observados": len(result.observados),
                "nuevos": result.nuevos,
                "revisitados": result.revisitados,
                "retirados": result.retirados,
            }
        },
    )
    return result


def _despachado_hace_poco(estado: EventState) -> bool:
    """¿Se despacho este evento hace menos de `MINUTOS_ENTRE_REDESPACHOS`?

    Sin sello previo devuelve `False`: los eventos que ya estaban vivos cuando
    esto se anadio se despachan una vez mas y a partir de ahi cuentan.
    """
    desde = leer_sello_utc(estado.timestamps.get("despachado"))
    if desde is None:
        # Sin sello, o ilegible: no puede frenar el despacho. Ante la duda, se
        # despacha. Perder una revision es peor que gastar una corrida.
        return False
    return datetime.now(UTC) - desde < timedelta(minutes=MINUTOS_ENTRE_REDESPACHOS)


def _solo_le_falto_magnitud(candidate: EventCandidate, bbox: BBox) -> bool:
    """¿Es un sismo de LATAM que solo se descarto por ser pequeno?

    Los feeds del USGS son **mundiales**: de los catorce candidatos de una
    corrida tipica, la mayoria se descartan por caer fuera del bbox. Publicar
    esos convertiria la capa en un sismografo global y taparia lo unico que le
    importa a este sistema.

    Se resuelve volviendo a preguntarle al filtro con el umbral en cero. Si asi
    pasa, lo unico que le sobraba era el tamano. Preferible a inspeccionar el
    texto de la razon, que es prosa para un log y puede cambiar.
    """
    return bool(evaluate(candidate, bbox=bbox, min_magnitude=0.0))


def _classify(
    candidate: EventCandidate,
    result: TriggerResult,
    *,
    events_dir: Path | None,
    dry_run: bool,
) -> None:
    """Decide si el evento es nuevo, revisita o terminal, y persiste el estado.

    UN `event_state` CORRUPTO CEGABA A P1 ENTERO, Y PARA SIEMPRE.

    `EventState.load` se llamaba aqui sin proteccion. Un solo fichero ilegible
    en `events/` propagaba hasta `cli.main` —que solo atrapa
    `NotImplementedError`— y mataba la pasada entera; y la mataria igual en cada
    corrida siguiente hasta que alguien lo tocara a mano. Con el cron a cinco
    minutos, eso es la vigilancia caida indefinidamente.

    Lo llamativo es que los consumidores secundarios si se protegian —
    `repaso.py`, `rezago.py`, `status.py`— y el critico no. Aqui se aplica el
    mismo patron, y ademas se **cuenta** el ilegible: si se descartara en
    silencio, "cero eventos relevantes" seria indistinguible de "no pude leer
    ninguno", que es la confusion que este proyecto persigue en todas partes.
    """
    try:
        existing = _estado_conocido(candidate, events_dir)
    except (ValueError, KeyError, OSError) as error:
        result.estados_ilegibles.append(candidate.usgs_id)
        _log.warning(
            "event_state ilegible; el evento se salta y los demas siguen",
            extra={"context": {"usgs_id": candidate.usgs_id, "error": str(error)}},
        )
        return

    if existing is None:
        state = EventState(
            usgs_id=candidate.usgs_id,
            estado=EventStatus.DETECTADO,
            mag=candidate.mag,
            lon=candidate.lon,
            lat=candidate.lat,
            depth_km=candidate.depth_km,
            lugar=candidate.lugar,
            origen_utc=candidate.origen_utc,
            timestamps={"detectado": utcnow_iso(), "usgs_origen": candidate.origen_utc},
        )
        if not dry_run:
            state.save(events_dir)
        result.nuevos.append(candidate.usgs_id)
        _log.info(
            "evento nuevo detectado",
            extra={
                "context": {
                    "usgs_id": candidate.usgs_id,
                    "mag": candidate.mag,
                    "lugar": candidate.lugar,
                }
            },
        )
        return

    if existing.estado in _TERMINAL:
        return

    # SUELO ENTRE DOS DESPACHOS DEL MISMO EVENTO.
    #
    # Esto re-despachaba todo evento vivo en **cada** pasada. Con el vigia a
    # cinco minutos son 288 despachos al dia por evento: medido, 257 despachos
    # y 262 commits por dos sismos en 24 h. P2 hace lo correcto —devuelve
    # OMITIR si la version no avanzo— pero cada despacho cuesta una corrida de
    # la cola de Actions, que este proyecto documenta como su cuello de botella.
    #
    # El trigger no puede saber si la version avanzo sin descargar el detail, y
    # descargarlo aqui seria pagar el coste de P2 para averiguar si hace falta
    # P2. Asi que el freno es de reloj, y solo para re-despachos: un evento
    # nuevo sale en el acto.
    if _despachado_hace_poco(existing):
        _log.debug(
            "re-despacho frenado: el anterior es demasiado reciente",
            extra={"context": {"usgs_id": candidate.usgs_id}},
        )
        return

    # Ya conocido: P2 decide si la version de ShakeMap avanzo (RF-04). El
    # trigger no descarga productos — eso lo hace P2 con el feed detail.
    #
    # Se despacha con el id **del estado**, no con el preferido de hoy: el
    # reporte vive en `reports/<id del estado>/`, y el detail de USGS responde
    # igual por cualquiera de los ids del evento.
    result.revisitados.append(existing.usgs_id)
    if not dry_run:
        existing.timestamps["despachado"] = utcnow_iso()
        existing.save(events_dir)


def _estado_conocido(candidate: EventCandidate, events_dir: Path | None) -> EventState | None:
    """El `event_state` del evento, buscado por **todos** sus identificadores.

    EL MISMO SISMO PODIA PUBLICARSE DOS VECES.

    El dedupe era `EventState.load(candidate.usgs_id)`: una comparacion de
    cadenas contra el id preferido de hoy. USGS cambia el preferido cuando otra
    red asume el evento y deja el viejo en `ids`. No es hipotetico: el 3-oct-2026
    el detail de `pr2025056002` declaraba
    `,pt25056000,us6000pvad,pr2025056002,usauto6000pvad,`. Si el feed pasara a
    servirlo como `us6000pvad`, el vigia no encontraba `events/us6000pvad.json`,
    lo daba por nuevo y P2 publicaba un segundo reporte del mismo sismo
    (auditoria del 5-sep-2026, #87).

    El preferido va primero: si existe, es el. Los demas se prueban despues, y
    uno con forma de id invalida se salta en vez de contarse como estado
    ilegible: es un alias de otra red, no un fichero roto nuestro.

    Raises:
        ValueError, KeyError, OSError: si el fichero que existe no se puede leer.
    """
    for usgs_id in candidate.identificadores:
        if usgs_id != candidate.usgs_id and not USGS_ID_RE.match(usgs_id):
            continue
        estado = EventState.load(usgs_id, events_dir)
        if estado is not None:
            if usgs_id != candidate.usgs_id:
                _log.info(
                    "evento conocido con otro id: USGS cambio el preferido",
                    extra={"context": {"preferido": candidate.usgs_id, "conocido_como": usgs_id}},
                )
            return estado
    return None


def _retirar(
    candidate: EventCandidate,
    result: TriggerResult,
    *,
    events_dir: Path | None,
    dry_run: bool,
) -> None:
    """Un evento que USGS marco `deleted` no se despacha, y si se conocia, se cierra.

    `status: deleted` NO SE MIRABA.

    El feed lo trae en `status` y aqui solo se leia el tipo, la magnitud y la
    caja, asi que un evento retirado —un fantasma del procesado automatico, o el
    duplicado de otro— que pasara el filtro se despachaba como nuevo y se
    seguia re-despachando como vivo. Un sismo que no ocurrio con un reporte de
    exposicion es la cifra alarmista del registro de riesgos (#87).

    Se cierra con `DESCARTADO`, que es el estado que `state.py` reserva para lo
    retirado. Es terminal pero no irreversible: `impact --reprocesar` lo revive
    si USGS lo restituye. El reporte que ya estuviera publicado **no se borra
    desde aqui**: retirarlo de la pagina es una decision sobre un artefacto
    publico, y queda la nota en el estado para quien la tome.
    """
    try:
        existente = _estado_conocido(candidate, events_dir)
    except (ValueError, KeyError, OSError) as error:
        result.estados_ilegibles.append(candidate.usgs_id)
        _log.warning(
            "event_state ilegible al retirar un evento borrado por USGS",
            extra={"context": {"usgs_id": candidate.usgs_id, "error": str(error)}},
        )
        return
    if existente is None or existente.estado in _TERMINAL:
        return
    result.retirados.append(existente.usgs_id)
    _log.warning(
        "USGS retiro un evento conocido; se cierra",
        extra={"context": {"usgs_id": existente.usgs_id, "estado": existente.estado.value}},
    )
    if not dry_run:
        existente.transition(
            EventStatus.DESCARTADO,
            nota=f"USGS lo marco deleted ({candidate.usgs_id}); no se vuelve a despachar.",
        ).save(events_dir)
