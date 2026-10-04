"""``event_state``: la maquina de estados de un evento (§3.3).

Un archivo JSON por evento, versionado en git. Esto da tres cosas que una base
de datos viva no daria gratis: auditoria (``git log`` del evento), costo cero
(RNF-01) e idempotencia trivial ante reinicios del runner (RF-02).

Transiciones validas::

    detectado ──▶ preliminar ──▶ publicado ──▶ publicado (nueva version SM)
        │             │              │
        └─────────────┴──────────────┴──▶ degradado   (contrato USGS roto)
        └─────────────┴──────────────┴──▶ descartado  (fuera de alcance / retirado)
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any, Self

from .paths import event_state_path, validate_usgs_id


class EventStatus(StrEnum):
    """Estado del ciclo de vida de un evento."""

    DETECTADO = "detectado"
    PRELIMINAR = "preliminar"
    PUBLICADO = "publicado"
    #: DECLARADO Y NUNCA ASIGNADO. Ninguna transicion lo produce: aparece en
    #: los conjuntos de estados validos y en ningun `save`. No se borra porque
    #: es un valor de un fichero versionado y quitarlo romperia la lectura de
    #: cualquier estado antiguo que lo llevara — pero mientras nadie lo escriba,
    #: leer "no hay eventos degradados" no significa nada.
    DEGRADADO = "degradado"
    DESCARTADO = "descartado"


_ALLOWED_TRANSITIONS: dict[EventStatus, frozenset[EventStatus]] = {
    EventStatus.DETECTADO: frozenset(
        {
            EventStatus.PRELIMINAR,
            EventStatus.PUBLICADO,
            EventStatus.DEGRADADO,
            EventStatus.DESCARTADO,
        }
    ),
    EventStatus.PRELIMINAR: frozenset(
        {
            EventStatus.PRELIMINAR,
            EventStatus.PUBLICADO,
            EventStatus.DEGRADADO,
            EventStatus.DESCARTADO,
        }
    ),
    # Un evento publicado se re-publica al aparecer ShakeMap v(n+1) (RF-04).
    EventStatus.PUBLICADO: frozenset(
        {EventStatus.PUBLICADO, EventStatus.DEGRADADO, EventStatus.DESCARTADO}
    ),
    EventStatus.DEGRADADO: frozenset(
        {EventStatus.PRELIMINAR, EventStatus.PUBLICADO, EventStatus.DESCARTADO}
    ),
    EventStatus.DESCARTADO: frozenset(),
}


class InvalidTransitionError(Exception):
    """Se intento una transicion de estado no permitida."""


def utcnow_iso() -> str:
    """Timestamp UTC ISO-8601 con segundos (§3.1: todo timestamp en UTC)."""
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def leer_sello_utc(sello: object) -> datetime | None:
    """Un sello ISO-8601 como instante UTC con zona, o ``None`` si no se lee.

    HABIA SEIS COPIAS DE ESTO Y SOLO ALGUNAS NORMALIZABAN LA ZONA.

    `observados`, `status` y `frescura` hacian `fromisoformat(ts.replace("Z",
    "+00:00"))` y devolvian lo que saliera; `repaso`, el vigia y P2 ademas le
    ponian UTC a un sello sin zona. Un `origen_utc` sin `Z` —un
    `observados.json` editado a mano, un estado escrito por una version vieja—
    salia *naive*, y compararlo con `datetime.now(UTC)` no da falso: lanza
    `TypeError`. En `podar` eso mataba el comando del vigia despues del latido
    y antes de escribir los observados (auditoria del 5-sep-2026, #168).

    Todos los sellos de este sistema son UTC (§3.1), asi que uno sin zona se lee
    como UTC: es lo que quien lo escribio quiso decir.
    """
    if not isinstance(sello, str) or not sello:
        return None
    try:
        momento = datetime.fromisoformat(sello.replace("Z", "+00:00"))
    except ValueError:
        return None
    return momento if momento.tzinfo else momento.replace(tzinfo=UTC)


def version_cambio(
    vigente: int,
    fuente_vigente: str,
    consumida: int,
    fuente_consumida: str,
) -> bool:
    """¿La version preferida de un producto ya no es la que se consumio? (RF-04)

    LA IDENTIDAD DE UNA VERSION ES (CONTRIBUIDOR, NUMERO), NO EL NUMERO.

    Se comparaba `vigente > consumida`, y los numeros de version de USGS son
    **por contribuidor**: `us` lleva su cuenta y `atlas` la suya. Medido el
    3-oct-2026 contra el detail de los veintiocho eventos publicados: en trece
    backtest el ShakeMap preferido es el de `atlas` (peso ~325) mientras `us`
    va por su v6 a v14 (peso 233). Si el preferido pasa de `us` v6 a `atlas` v1,
    `1 > 6` es falso y el reporte se queda para siempre en un grid que USGS ya no
    recomienda, sin que nada falle (auditoria del 5-sep-2026, #81).

    Reglas:

    * Sin producto vigente (0) no hay nada que consumir: eso es un producto
      desaparecido, y lo trata quien llama (`rezago.desaparecido`).
    * Contribuidor conocido a los dos lados y distinto: cambio, sea cual sea el
      numero.
    * Mismo contribuidor: solo cuenta avanzar. Una version menor del mismo
      contribuidor es una revision que USGS retiro, y re-emitir hacia atras es
      lo que `test_un_reporte_por_delante_no_es_rezago` prohibe.
    * Contribuidor consumido desconocido —todo estado y reporte emitido antes
      de que se registrara—: se compara el numero, como antes. No se le supone
      `us`: trece de los veintiocho son `atlas`, y suponerlo los re-emitiria a
      todos de golpe. Tampoco se lee un retroceso como cambio de contribuidor,
      porque sin el dato es indistinguible de una revision retirada. El hueco
      se cierra solo: el siguiente reproceso de ese evento, por el motivo que
      sea, deja el contribuidor registrado.
    """
    if vigente <= 0:
        return False
    if fuente_vigente and fuente_consumida and fuente_vigente != fuente_consumida:
        return True
    return vigente > consumida


def identidad_de_version(fuente: str, version: int) -> str:
    """`v6 (us)`: el numero solo no dice de que contribuidor es (#95)."""
    return f"v{version} ({fuente})" if fuente else f"v{version}"


@dataclass(frozen=True, slots=True)
class ProcessedVersions:
    """Ultima version consumida de cada producto USGS versionado (§2.1)."""

    shakemap: int = 0
    groundfailure: int = 0
    #: Contribuidor (`source` en USGS) de cada version consumida. Vacio en los
    #: estados escritos antes de que se registrara: ver `version_cambio`.
    shakemap_fuente: str = ""
    groundfailure_fuente: str = ""

    def to_dict(self) -> dict[str, Any]:
        datos: dict[str, Any] = {"shakemap": self.shakemap, "groundfailure": self.groundfailure}
        # Solo cuando se conocen: los veintiocho estados publicados no cambian
        # de forma hasta que un reproceso de verdad sepa que contribuidor uso.
        if self.shakemap_fuente:
            datos["shakemap_fuente"] = self.shakemap_fuente
        if self.groundfailure_fuente:
            datos["groundfailure_fuente"] = self.groundfailure_fuente
        return datos

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            shakemap=int(data.get("shakemap", 0)),
            groundfailure=int(data.get("groundfailure", 0)),
            shakemap_fuente=str(data.get("shakemap_fuente") or ""),
            groundfailure_fuente=str(data.get("groundfailure_fuente") or ""),
        )


@dataclass(frozen=True, slots=True)
class EventState:
    """Estado persistido de un evento."""

    usgs_id: str
    estado: EventStatus
    mag: float
    lon: float
    lat: float
    depth_km: float
    lugar: str
    origen_utc: str
    versiones_procesadas: ProcessedVersions = field(default_factory=ProcessedVersions)
    timestamps: dict[str, str] = field(default_factory=dict)
    #: DECLARADO Y SIEMPRE VACIO. Nada lo escribe: se serializa y se lee, pero
    #: ningun paso del pipeline le mete un digest. Se conserva porque el
    #: `event_state` es un fichero versionado y quitarlo cambiaria la forma de
    #: los veintiun estados publicados; lo que no se puede es leerlo como si
    #: dijera algo. Llenarlo sigue pendiente.
    hashes: dict[str, str] = field(default_factory=dict)
    intentos_preliminar: int = 0
    #: Reconstruccion retrospectiva, no una respuesta en vivo. Un backtest se
    #: publica dias o meses despues del sismo, asi que su "latencia" no mide
    #: nada del sistema: mezclarla con las reales daria un p50 sin sentido.
    backtest: bool = False
    notas: list[str] = field(default_factory=list)

    # -- transiciones -------------------------------------------------------

    def transition(self, nuevo: EventStatus, *, nota: str | None = None) -> EventState:
        """Devuelve un estado nuevo, validando la transicion.

        Raises:
            InvalidTransitionError: si el paso no esta permitido.
        """
        if nuevo not in _ALLOWED_TRANSITIONS[self.estado]:
            raise InvalidTransitionError(f"{self.estado} -> {nuevo} no permitida ({self.usgs_id})")
        # EL PRIMER SELLO NO SE PISA, Y ESTO ERA UN CERO SILENCIOSO.
        #
        # Era `dict(self.timestamps) | {nuevo.value: utcnow_iso()}`: cada
        # transicion **sobrescribia** el sello de ese estado. Los dos unicos
        # consumidores quieren el primero, y los dos estaban mal:
        #
        # * `status.event_latencies` mide `origen -> publicado`. Cada
        #   re-emision de RF-04 —rutina cada vez que USGS publica un ShakeMap
        #   nuevo— reescribia `publicado` y la latencia del evento crecia sola.
        #   Medido el 3-sep-2026: los dos sismos en vivo daban p50 893,9 min
        #   cuando lo real es **92,1**. `/status` llevaba publicando una
        #   latencia que no era la del sistema sino la de la ultima vez que
        #   alguien lo relanzo.
        # * `_ventana_agotada` cuenta 6 h desde `detectado` o `preliminar` para
        #   rendirse. Al re-sellar `preliminar` en cada reintento, la ventana se
        #   reiniciaba sola y nunca vencia por tiempo.
        #
        # Se conserva el primero y se guarda aparte el ultimo: la re-emision es
        # informacion, solo que no es la que mide la latencia.
        ahora = utcnow_iso()
        stamps = dict(self.timestamps)
        if nuevo.value in stamps:
            stamps[f"{nuevo.value}_ultimo"] = ahora
        else:
            stamps[nuevo.value] = ahora
        notas = [*self.notas, nota] if nota else list(self.notas)
        return replace(self, estado=nuevo, timestamps=stamps, notas=notas)

    def needs_reprocessing(
        self,
        shakemap_version: int,
        groundfailure_version: int,
        *,
        shakemap_fuente: str,
        groundfailure_fuente: str,
    ) -> bool:
        """¿La version preferida de algun producto no es la ya consumida? (RF-04)

        Los contribuidores son obligatorios a proposito: con un valor por
        defecto, un llamador que se olvidara de pasarlos volveria a comparar
        solo numeros sin que nada lo delatara.
        """
        ya = self.versiones_procesadas
        return version_cambio(
            shakemap_version, shakemap_fuente, ya.shakemap, ya.shakemap_fuente
        ) or version_cambio(
            groundfailure_version, groundfailure_fuente, ya.groundfailure, ya.groundfailure_fuente
        )

    # -- (de)serializacion --------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        return {
            "usgs_id": self.usgs_id,
            "estado": self.estado.value,
            "mag": self.mag,
            "lon": self.lon,
            "lat": self.lat,
            "depth_km": self.depth_km,
            "lugar": self.lugar,
            "origen_utc": self.origen_utc,
            "versiones_procesadas": self.versiones_procesadas.to_dict(),
            "timestamps": dict(sorted(self.timestamps.items())),
            "hashes": dict(sorted(self.hashes.items())),
            "intentos_preliminar": self.intentos_preliminar,
            "backtest": self.backtest,
            "notas": list(self.notas),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            usgs_id=str(data["usgs_id"]),
            estado=EventStatus(data["estado"]),
            mag=float(data["mag"]),
            lon=float(data["lon"]),
            lat=float(data["lat"]),
            depth_km=float(data["depth_km"]),
            lugar=str(data["lugar"]),
            origen_utc=str(data["origen_utc"]),
            versiones_procesadas=ProcessedVersions.from_dict(data.get("versiones_procesadas", {})),
            timestamps=dict(data.get("timestamps", {})),
            hashes=dict(data.get("hashes", {})),
            intentos_preliminar=int(data.get("intentos_preliminar", 0)),
            backtest=bool(data.get("backtest", False)),
            notas=list(data.get("notas", [])),
        )

    # -- persistencia -------------------------------------------------------

    def save(self, directory: Path | None = None) -> Path:
        """Escribe el estado de forma atomica y determinista.

        Determinista (claves ordenadas, indentacion fija) para que el diff de
        git muestre solo lo que realmente cambio.
        """
        path = (
            directory / f"{validate_usgs_id(self.usgs_id)}.json"
            if directory
            else event_state_path(self.usgs_id)
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(
            json.dumps(self.to_dict(), ensure_ascii=False, indent=2, sort_keys=False) + "\n",
            encoding="utf-8",
        )
        tmp.replace(path)
        return path

    @classmethod
    def load(cls, usgs_id: str, directory: Path | None = None) -> Self | None:
        """Carga el estado, o ``None`` si el evento aun no se conoce."""
        path = (
            directory / f"{validate_usgs_id(usgs_id)}.json"
            if directory
            else event_state_path(usgs_id)
        )
        if not path.exists():
            return None
        return cls.from_dict(json.loads(path.read_text(encoding="utf-8")))
