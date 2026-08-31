"""Repaso de versiones: los eventos que ya se cayeron del feed (RF-04).

RF-04 promete que al aparecer una version nueva de ShakeMap o Ground Failure el
reporte se re-emite con changelog de deltas. El vigia lo cumple mirando el feed
cada cinco minutos... y el feed es `4.5_day`: **veinticuatro horas**. Pasado un
dia el evento desaparece de ahi, el vigia deja de nombrarlo y nadie vuelve a
preguntar por el. La promesa se cumplia el primer dia y caducaba en silencio.

Que no es una hipotesis. Medido el 30-ago-2026 contra USGS, sobre los veinte
eventos publicados del catalogo, dias desde el sismo hasta la ULTIMA revision
de ShakeMap del contribuidor `us`:

    mediana 63 dias · Chocó 11,5 · Venezuela 61,2 (v15) · 2024-11 75,1 (v9)

Ni uno solo termino de revisarse dentro de las 24 h que cubre el feed. El de
Venezuela llego a la version quince **dos meses despues** del sismo.

**La ventana es de 90 dias** porque cubre 17 de los 20 medidos. Los tres que se
salen —185, 571 y 2.024 dias— no son revisiones del evento: son reprocesos del
catalogo entero que USGS hace cada varios anos, y perseguirlos a diario seria
gastar peticiones en algo que no va a pasar hoy.

Este modulo NO descarga productos ni recalcula nada: pregunta por el detail de
cada evento, compara versiones contra `versiones_procesadas` y devuelve la
lista de los que avanzaron. Quien recalcula es P2, por el camino de siempre.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path

from ..common.constants import USGS_FDSN_EVENT
from ..common.http import Fetcher
from ..common.logging import get_logger
from ..common.paths import EVENTS_DIR
from ..common.state import EventState, EventStatus
from ..p2_impact.products import ProductContractError, parse_products

_log = get_logger(__name__)

#: Cuantos dias atras se repasa. Ver el docstring del modulo: 90 cubre 17 de
#: los 20 eventos medidos, y los que se salen son reprocesos de catalogo.
DIAS_DE_REPASO = 90

#: Estados que no se repasan. `descartado` es terminal; un `backtest` es una
#: reconstruccion congelada de un historico y re-emitirlo cada vez que USGS
#: retoca su Atlas convertiria el catalogo en ruido.
_SIN_REPASO = frozenset({EventStatus.DESCARTADO})


@dataclass(slots=True)
class ResultadoRepaso:
    """Que encontro una pasada del repaso."""

    #: Eventos dentro de la ventana que se llegaron a consultar.
    revisados: int = 0
    #: Los que traen version nueva y hay que re-despachar a P2.
    a_despachar: list[str] = field(default_factory=list)
    #: Eventos que no se pudieron consultar. Se cuentan aparte y NO se
    #: confunden con "sin cambios": un fallo de red no es una respuesta.
    fallidos: list[str] = field(default_factory=list)


def detail_url(usgs_id: str) -> str:
    """El detail de un evento, por identificador.

    Es la misma llamada que P2 ya hace por evento, contra el mismo endpoint. No
    entra una fuente nueva al sistema por esto.
    """
    return f"{USGS_FDSN_EVENT}?eventid={usgs_id}&format=geojson"


def eventos_a_repasar(
    events_dir: Path | None = None,
    *,
    dias: int = DIAS_DE_REPASO,
    ahora: datetime | None = None,
) -> list[EventState]:
    """Los eventos vivos dentro de la ventana, del mas reciente al mas viejo.

    Del mas reciente primero porque es donde se concentran las revisiones: si
    algun dia hay que recortar la lista, que lo que se caiga sea la cola.
    """
    raiz = events_dir or EVENTS_DIR
    if not raiz.exists():
        return []
    corte = (ahora or datetime.now(UTC)) - timedelta(days=dias)

    vivos: list[tuple[datetime, EventState]] = []
    for ruta in sorted(raiz.glob("*.json")):
        try:
            estado = EventState.from_dict(_leer(ruta))
        except (ValueError, KeyError, OSError) as error:
            # Un estado ilegible no puede parar el repaso de los demas, pero
            # tampoco se calla: si `events/` se corrompe hay que enterarse.
            _log.warning(
                "event_state ilegible en el repaso",
                extra={"context": {"ruta": str(ruta), "error": str(error)}},
            )
            continue
        if estado.estado in _SIN_REPASO or estado.backtest:
            continue
        origen = _parse(estado.origen_utc)
        if origen is None or origen < corte:
            continue
        vivos.append((origen, estado))

    vivos.sort(key=lambda par: par[0], reverse=True)
    return [estado for _, estado in vivos]


def repasar(
    fetcher: Fetcher,
    *,
    events_dir: Path | None = None,
    dias: int = DIAS_DE_REPASO,
) -> ResultadoRepaso:
    """Pregunta por cada evento de la ventana y ve si su version avanzo."""
    resultado = ResultadoRepaso()

    for estado in eventos_a_repasar(events_dir, dias=dias):
        try:
            detalle = fetcher.get_json(detail_url(estado.usgs_id))
            productos = parse_products(detalle)
        except (ProductContractError, OSError, ValueError) as error:
            # UN FALLO NO ES UN "SIN CAMBIOS".
            #
            # Tragarselo dejaria un evento sin repasar y el contador diciendo
            # que se repaso: exactamente el cero silencioso que este proyecto
            # persigue, en version "todo al dia".
            resultado.fallidos.append(estado.usgs_id)
            _log.warning(
                "no se pudo repasar el evento",
                extra={"context": {"usgs_id": estado.usgs_id, "error": str(error)}},
            )
            continue

        resultado.revisados += 1
        if estado.needs_reprocessing(productos.shakemap_version, productos.groundfailure_version):
            resultado.a_despachar.append(estado.usgs_id)
            _log.info(
                "version nueva fuera de la ventana del feed",
                extra={
                    "context": {
                        "usgs_id": estado.usgs_id,
                        "shakemap": f"{estado.versiones_procesadas.shakemap} -> "
                        f"{productos.shakemap_version}",
                        "ground_failure": f"{estado.versiones_procesadas.groundfailure} -> "
                        f"{productos.groundfailure_version}",
                    }
                },
            )

    _log.info(
        "repaso terminado",
        extra={
            "context": {
                "revisados": resultado.revisados,
                "a_despachar": resultado.a_despachar,
                "fallidos": resultado.fallidos,
                "ventana_dias": dias,
            }
        },
    )
    return resultado


def _leer(ruta: Path) -> dict[str, object]:
    import json

    return dict(json.loads(ruta.read_text(encoding="utf-8")))


def _parse(sello: str) -> datetime | None:
    try:
        momento = datetime.fromisoformat(sello.replace("Z", "+00:00"))
    except ValueError:
        return None
    return momento if momento.tzinfo else momento.replace(tzinfo=UTC)
