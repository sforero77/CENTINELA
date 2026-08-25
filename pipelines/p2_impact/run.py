"""Orquestacion de P2.

La parte decisoria — ¿hay trabajo? ¿preliminar o completo? ¿que version? — es
codigo puro y testeable sin red ni geo. El computo pesado se delega a
:mod:`shakemap`, :mod:`ground_failure` y :mod:`exposure_join`.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum
from pathlib import Path
from typing import Any

from ..common.constants import PRELIMINARY_MAX_HOURS, PRELIMINARY_RETRY_MINUTES
from ..common.http import Fetcher
from ..common.logging import get_logger
from ..common.state import EventState, EventStatus, ProcessedVersions, utcnow_iso
from ..p1_trigger.feed import FeedContractError, epoch_ms_to_iso
from ..p3_report.run import write_report_bundle
from .exposure_join import connect
from .products import ProductSet, parse_products

_log = get_logger(__name__)

#: Cuantos reintentos preliminares caben en la ventana de RF-03.
MAX_PRELIMINARY_ATTEMPTS = PRELIMINARY_MAX_HOURS * 60 // PRELIMINARY_RETRY_MINUTES


class Action(StrEnum):
    """Que debe hacer P2 con un evento en esta corrida."""

    #: Nada cambio desde la ultima corrida: misma version de todos los productos.
    OMITIR = "omitir"
    #: Aun no hay ShakeMap: reporte por radios (RF-03).
    PRELIMINAR = "preliminar"
    #: Hay ShakeMap nuevo (o el primero): reporte completo.
    COMPLETO = "completo"
    #: Se agoto la ventana de 6 h sin ShakeMap; se deja de reintentar.
    AGOTADO = "agotado"


@dataclass(frozen=True, slots=True)
class Decision:
    """Accion elegida y su justificacion, para el log y el changelog."""

    action: Action
    razon: str
    shakemap_version: int = 0
    groundfailure_version: int = 0


def decide(state: EventState, products: ProductSet, *, forzar: bool = False) -> Decision:
    """Decide la accion a partir del estado persistido y los productos vivos.

    Esta funcion es el corazon de la idempotencia (RF-02): dos corridas sobre
    el mismo par ``(estado, productos)`` devuelven la misma decision.

    Args:
        forzar: reemite aunque no haya version nueva de ningun producto. El
            estado solo sigue las versiones de USGS, asi que un reporte no se
            entera de que **el pipeline** cambio: el del Choco quedo sin las
            coordenadas del epicentro y sin la marca de backtest, ambas
            anadidas despues. Es una decision de quien opera, no automatica,
            porque reemitir cuesta y cambia un artefacto ya publicado.
    """
    if state.estado is EventStatus.DESCARTADO:
        return Decision(Action.OMITIR, "evento descartado")

    if forzar and products.has_shakemap:
        return Decision(
            Action.COMPLETO,
            "reproceso forzado: el pipeline cambio, no los productos",
            products.shakemap_version,
            products.groundfailure_version,
        )

    if not products.has_shakemap:
        if state.intentos_preliminar >= MAX_PRELIMINARY_ATTEMPTS:
            return Decision(
                Action.AGOTADO,
                f"sin ShakeMap tras {PRELIMINARY_MAX_HOURS} h de reintentos",
            )
        return Decision(Action.PRELIMINAR, "sin ShakeMap disponible aun")

    sm_version = products.shakemap_version
    gf_version = products.groundfailure_version

    if state.needs_reprocessing(sm_version, gf_version):
        previa = state.versiones_procesadas
        razon = (
            f"ShakeMap v{previa.shakemap} -> v{sm_version}"
            if sm_version > previa.shakemap
            else f"Ground Failure v{previa.groundfailure} -> v{gf_version}"
        )
        return Decision(Action.COMPLETO, razon, sm_version, gf_version)

    return Decision(
        Action.OMITIR,
        f"ya procesado en ShakeMap v{sm_version}",
        sm_version,
        gf_version,
    )


#: Nota que queda en el `event_state` de un historico. Se escribe una sola vez,
#: al reconstruirlo, y viaja al reporte por el campo `backtest`.
NOTA_BACKTEST = "Backtest: reconstruccion retrospectiva de {fecha}, no una respuesta en vivo."


def reconstruct_backtest_state(detail: dict[str, Any]) -> EventState:
    """Arma el `event_state` de un evento que P1 nunca vio.

    P1 vigila el feed de la ultima hora, asi que un sismo de hace dos meses no
    tiene estado y P2 se niega a procesarlo. Para los casos golden —el Choco,
    el doble evento de Venezuela— eso obliga a escribir el JSON a mano y
    commitearlo. Se hizo una vez y no se debe hacer dos: un estado escrito a
    mano no se puede volver a generar, y cuando el esquema cambie nadie sabra
    que campos le faltan.

    Queda marcado `backtest=True` desde el primer momento. No es una etiqueta
    cosmetica: excluye el evento del p50/p95 de latencia —publicarlo dos meses
    tarde daria una latencia de dos meses— y pone en el reporte el aviso de que
    las edificaciones y las vias son las de hoy, no las del dia del sismo.
    """
    # No se reusa `EventCandidate.from_feature`: el feed de resumen y la
    # respuesta detail son dos contratos distintos, y el detail no trae
    # `properties.detail` —la URL a si mismo— que aquel exige. Compartir el
    # lector obligaria a aflojar el contrato del camino en vivo, que es el que
    # mas conviene que sea estricto.
    try:
        props: dict[str, Any] = detail["properties"]
        coords = detail["geometry"]["coordinates"]
        lon, lat, depth = float(coords[0]), float(coords[1]), float(coords[2])
        mag = props["mag"]
        if mag is None:
            raise FeedContractError(f"Evento sin magnitud: {detail.get('id')}")
        usgs_id = str(detail["id"])
        origen_utc = epoch_ms_to_iso(props["time"])
        lugar = str(props.get("place") or "ubicacion no reportada")
    except FeedContractError:
        raise
    except (KeyError, TypeError, ValueError, IndexError) as exc:
        raise FeedContractError(
            f"El detail de {detail.get('id')} no cumple el contrato USGS: {exc}"
        ) from exc

    return EventState(
        usgs_id=usgs_id,
        estado=EventStatus.DETECTADO,
        mag=float(mag),
        lon=lon,
        lat=lat,
        depth_km=depth,
        lugar=lugar,
        origen_utc=origen_utc,
        timestamps={"detectado": utcnow_iso(), "usgs_origen": origen_utc},
        backtest=True,
        notas=[NOTA_BACKTEST.format(fecha=origen_utc[:10])],
    )


def run_impact(
    usgs_id: str,
    fetcher: Fetcher,
    *,
    detail_url: str,
    exposure_glob: str,
    manifest_id: str = "",
    events_dir: Path | None = None,
    reports_root: Path | None = None,
    workdir: Path | None = None,
    admin_lookup_parquet: str | None = None,
    backtest: bool = False,
    forzar: bool = False,
) -> Decision:
    """Procesa un evento de punta a punta: productos -> impacto -> reporte.

    Es el punto de entrada que corre el workflow. Cuando termina sin excepcion,
    hay un reporte en disco y el ``event_state`` refleja la version consumida.

    Args:
        usgs_id: evento, ya detectado por P1.
        fetcher: cliente HTTP.
        detail_url: feed detail del evento.
        exposure_glob: ruta o glob del activo de exposicion (GeoParquet).
        manifest_id: identificador del manifest con el que se construyo el
            activo; viaja al reporte para cerrar la trazabilidad de RNF-04.
        admin_lookup_parquet: diccionario administrativo. Si es ``None`` se
            busca junto al activo.
        backtest: reconstruye el estado si P1 nunca vio el evento, y lo marca
            como retrospectivo. Sin esto un evento sin estado es un error, que
            es lo correcto en el camino en vivo: significa que P1 fallo.
        forzar: reemite el reporte aunque no haya version nueva de productos.

    Returns:
        La decision tomada, ya ejecutada.
    """
    from .pipeline import build_report, compute_impact, download_products

    detail = fetcher.get_json(detail_url)
    state = EventState.load(usgs_id, events_dir)
    if state is None:
        if not backtest:
            raise FileNotFoundError(
                f"No existe event_state para {usgs_id}; P1 debe crearlo primero. "
                f"Si es un evento historico que P1 nunca vio, corre con --backtest."
            )
        state = reconstruct_backtest_state(detail)
        state.save(events_dir)
        _log.info(
            "estado reconstruido para un historico",
            extra={
                "context": {
                    "usgs_id": usgs_id,
                    "origen_utc": state.origen_utc,
                    "lugar": state.lugar,
                }
            },
        )

    products = parse_products(detail)
    decision = decide(state, products, forzar=forzar)
    _log.info(
        "decision de impacto",
        extra={
            "context": {
                "usgs_id": usgs_id,
                "accion": decision.action.value,
                "razon": decision.razon,
                "shakemap_version": decision.shakemap_version,
            }
        },
    )

    if decision.action is Action.OMITIR:
        return decision

    if decision.action is Action.AGOTADO:
        state.transition(EventStatus.DESCARTADO, nota=decision.razon).save(events_dir)
        return decision

    if decision.action is Action.PRELIMINAR:
        # RF-03: sin ShakeMap no hay reporte completo, pero si un corte por
        # radios. Se cuenta el intento para que la ventana de 6 h se agote.
        #
        # El calculo existia desde el principio y **no lo llamaba nadie**: el
        # evento pasaba a estado `preliminar` y no se publicaba nada, asi que
        # durante las primeras horas —las unicas en que un preliminar sirve—
        # el sistema no decia una palabra. Mismo patron que las tres capas del
        # activo que se agregaban a una tabla que nadie leia.
        siguiente = replace(state, intentos_preliminar=state.intentos_preliminar + 1)
        siguiente = siguiente.transition(EventStatus.PRELIMINAR, nota=decision.razon)
        siguiente.save(events_dir)
        _publicar_preliminar(
            siguiente,
            products,
            exposure_glob=exposure_glob,
            manifest_id=manifest_id,
            reports_root=reports_root,
            admin_lookup_parquet=admin_lookup_parquet,
        )
        return decision

    trabajo = workdir or (Path(exposure_glob).parent / "work" / usgs_id)
    contornos, deslizamiento, licuefaccion = download_products(products, trabajo, fetcher=fetcher)
    if contornos is None:
        raise ValueError(
            f"El ShakeMap v{products.shakemap_version} de {usgs_id} no publica cont_mmi: "
            f"no se puede calcular el impacto sin contornos de intensidad."
        )

    con = connect()
    _cargar_admin_lookup(con, exposure_glob, admin_lookup_parquet)
    totales = compute_impact(
        con,
        products,
        exposure_glob=exposure_glob,
        contornos=contornos,
        deslizamiento=deslizamiento,
        licuefaccion=licuefaccion,
    )
    reporte = build_report(con, state, products, totales, manifest_id=manifest_id)

    columnas = [c[0] for c in con.execute("SELECT * FROM impact_adm2 LIMIT 0").description]
    filas = [
        dict(zip(columnas, fila, strict=True))
        for fila in con.execute("SELECT * FROM impact_adm2 ORDER BY pop_mmi7p DESC").fetchall()
    ]
    filas = _enriquecer_con_admin(con, filas)
    escritos = write_report_bundle(reporte, filas, reports_root=reports_root)

    # La malla del evento, para que el visor dibuje el dato donde esta y no un
    # circulo en el centroide del municipio. Se escribe junto al resto del
    # paquete; si falla, el reporte ya esta publicado y eso es lo que importa.
    try:
        from ..p3_report.celdas import write_cells_json

        escritos["celdas_json"] = write_cells_json(
            con, escritos["report_json"].parent / "celdas.json"
        )
    except Exception as exc:
        _log.warning(
            "no se pudo escribir la malla del evento",
            extra={"context": {"usgs_id": usgs_id, "error": str(exc)}},
        )

    versiones = ProcessedVersions(
        shakemap=products.shakemap_version, groundfailure=products.groundfailure_version
    )
    replace(state, versiones_procesadas=versiones).transition(
        EventStatus.PUBLICADO, nota=decision.razon
    ).save(events_dir)

    _log.info(
        "reporte publicado",
        extra={
            "context": {
                "usgs_id": usgs_id,
                "shakemap_version": products.shakemap_version,
                "artefactos": sorted(escritos),
                "pop_mmi7p": totales.pop_mmi7p,
            }
        },
    )
    return decision


def _publicar_preliminar(
    state: EventState,
    products: ProductSet,
    *,
    exposure_glob: str,
    manifest_id: str,
    reports_root: Path | None,
    admin_lookup_parquet: str | None,
) -> None:
    """Calcula el corte por radios y publica el reporte preliminar.

    Un fallo aqui no puede tumbar el evento: el preliminar es lo mejor que hay
    mientras no llega el ShakeMap, no es el reporte definitivo, y el reintento
    vuelve a pasar por aqui en quince minutos. Se registra y se sigue.
    """
    from .pipeline import build_preliminary_report, compute_preliminary

    try:
        con = connect()
        _cargar_admin_lookup(con, exposure_glob, admin_lookup_parquet)
        por_radio = compute_preliminary(con, state, exposure_glob=exposure_glob)
        reporte = build_preliminary_report(state, products, por_radio, manifest_id=manifest_id)
        escritos = write_report_bundle(reporte, [], reports_root=reports_root)
    except Exception as exc:
        _log.warning(
            "no se pudo publicar el preliminar; se reintenta en la proxima corrida",
            extra={"context": {"usgs_id": state.usgs_id, "error": str(exc)}},
        )
        return
    _log.info(
        "reporte preliminar publicado",
        extra={
            "context": {
                "usgs_id": state.usgs_id,
                "intento": state.intentos_preliminar,
                "artefactos": sorted(escritos),
                **{f"r{km}km": pop for km, pop in sorted(por_radio.items())},
            }
        },
    )


def _cargar_admin_lookup(con: Any, exposure_glob: str, ruta: str | None) -> None:
    """Materializa ``admin_lookup``, que aporta nombre y centroide municipal."""
    candidata = ruta or str(Path(exposure_glob).parent / "admin_lookup.parquet")
    if Path(candidata).exists():
        con.execute(
            f"CREATE OR REPLACE TABLE admin_lookup AS SELECT * FROM read_parquet('{candidata}')"
        )
        return
    # Sin diccionario el reporte sigue saliendo, con el codigo DIVIPOLA como
    # nombre. Es peor de leer, pero mejor que no publicar.
    _log.warning(
        "sin admin_lookup: el reporte usara el codigo DIVIPOLA como nombre",
        extra={"context": {"buscado": candidata}},
    )
    con.execute(
        "CREATE OR REPLACE TABLE admin_lookup AS "
        "SELECT DISTINCT adm2_id, adm2_id AS nombre, adm1_id, "
        "'' AS departamento, iso3, '' AS centroide FROM exposure"
    )


def _enriquecer_con_admin(con: Any, filas: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Anade nombre y centroide a las filas municipales, para CSV y mapa."""
    extra = {
        str(r[0]): (str(r[1]), float(r[2]), float(r[3]))
        for r in con.execute(
            """
            SELECT adm2_id, nombre,
                   ST_X(ST_GeomFromText(centroide)) AS lon,
                   ST_Y(ST_GeomFromText(centroide)) AS lat
            FROM admin_lookup
            """
        ).fetchall()
    }
    for fila in filas:
        nombre, lon, lat = extra.get(str(fila.get("adm2_id")), ("", 0.0, 0.0))
        fila.setdefault("nombre", nombre)
        # El centroide se descompone en dos columnas numericas y no viaja como
        # WKT: asi el CSV se puede pintar en un mapa sin parsear geometria, que
        # es la diferencia entre una tabla que alguien usa y una que alguien
        # tiene que preparar antes de usar.
        fila["lon"] = round(lon, 6)
        fila["lat"] = round(lat, 6)
    return filas
