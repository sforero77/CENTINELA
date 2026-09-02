"""Orquestacion de P2.

La parte decisoria — ¿hay trabajo? ¿preliminar o completo? ¿que version? — es
codigo puro y testeable sin red ni geo. El computo pesado se delega a
:mod:`shakemap`, :mod:`ground_failure` y :mod:`exposure_join`.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from pathlib import Path
from typing import Any

from ..common.constants import CADENCIA_MINIMA_MIN, PRELIMINARY_MAX_HOURS
from ..common.http import Fetcher
from ..common.logging import get_logger
from ..common.paths import REPORTS_DIR, validate_usgs_id
from ..common.state import EventState, EventStatus, ProcessedVersions, utcnow_iso
from ..common.toponimos import traducir_lugar
from ..p1_trigger.feed import FeedContractError, epoch_ms_to_iso
from ..p3_report.changelog import build_changelog
from ..p3_report.model import Report
from ..p3_report.run import write_report_bundle
from .exposure_join import check_quality, connect
from .products import ProductSet, parse_products

_log = get_logger(__name__)

#: Tope absoluto de intentos preliminares. NO es lo que cierra la ventana.
#:
#: Lo era, y estaba mal. `6 h / 30 min = 12` daba por supuesto que el vigia
#: pasaba cada media hora; el 30-ago-2026 un cron externo lo puso a **cinco
#: minutos** y esos doce intentos se consumieron en una hora. La ventana de
#: RF-03 se encogio de seis horas a una sin que nada fallara, y el evento se
#: marcaba `degradado` con la nota "sin ShakeMap tras 6 h de reintentos" —
#: falsa por un factor de seis, y publicada.
#:
#: Lo peor: `test_ventana_de_reintentos_es_de_seis_horas` seguia en verde. La
#: asercion (`== 12`) era cierta; el nombre era lo que mentia.
#:
#: Ahora la ventana la cierra el reloj y esto es solo una red por si el sello
#: de deteccion falta. Se calcula con la cadencia mas rapida posible para que
#: el conteo no pueda volver a ser lo que cierra antes de tiempo.
MAX_PRELIMINARY_ATTEMPTS = PRELIMINARY_MAX_HOURS * 60 // CADENCIA_MINIMA_MIN


def _ventana_preliminar_agotada(state: EventState) -> bool:
    """¿Se agotaron las seis horas de RF-03? Medidas en reloj, no en intentos.

    El ancla es cuando el vigia vio el evento por primera vez, que es cuando
    empieza a contar la promesa. Si ese sello falta o no se puede leer —un
    estado malformado—, se cae al tope de intentos, que es generoso a
    proposito: rendirse antes de tiempo es el fallo que esto arregla.
    """
    desde = state.timestamps.get("detectado") or state.timestamps.get("preliminar")
    if desde:
        try:
            inicio = datetime.fromisoformat(desde.replace("Z", "+00:00"))
        except ValueError:
            inicio = None
        if inicio is not None:
            if inicio.tzinfo is None:
                inicio = inicio.replace(tzinfo=UTC)
            return datetime.now(UTC) - inicio >= timedelta(hours=PRELIMINARY_MAX_HOURS)
    return state.intentos_preliminar >= MAX_PRELIMINARY_ATTEMPTS


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
        if _ventana_preliminar_agotada(state):
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
        lugar = traducir_lugar(str(props.get("place") or "")) or "ubicacion no reportada"
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
    aunque_no_alcance: bool = False,
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
    from .pipeline import (
        build_report,
        compute_impact,
        download_products,
        manifiesto_del_activo,
    )

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

    else:
        state = _refrescar_lugar(state, detail, events_dir)

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
        aunque_no_alcance=aunque_no_alcance,
    )
    # §6.4 pide estos asserts "en P0 y P2". En P2 no corrian: vivian en una
    # funcion sin llamador, llamada desde otra funcion sin llamador cuya
    # docstring afirmaba que si. Van aqui, en la orquestacion, porque no
    # preguntan si el calculo salio bien —de eso se ocupa `compute_impact`—
    # sino si lo calculado se puede publicar.
    # CUANDO NO ALCANZA, SE PUBLICA **CUANTO** NO ALCANZA.
    #
    # Un M5,6 a 85 km de la costa de Chiapas y un M5,9 a 876 km de Rapa Nui
    # producen el mismo reporte de ceros, y no son lo mismo: el primero puede
    # alcanzar tierra en la revision siguiente del ShakeMap y el segundo no lo
    # hara nunca. En vez de inventar un umbral que decida por el lector, se
    # mide la distancia a la poblacion mas cercana del pais y se publica.
    #
    # Se usa el propio activo, que ya esta cargado: no hace falta una linea de
    # costa ni una fuente nueva.
    avisos_extra: list[str] = []
    if aunque_no_alcance and not totales.pop_mmi6p:
        lejania = _km_a_la_poblacion_mas_cercana(con, state.lon, state.lat)
        if lejania is not None:
            avisos_extra.append(
                f"El epicentro está a {lejania:,.0f} km de la población más cercana "
                f"del país con la que se comparó. La sacudida no alcanzó territorio "
                f"habitado.".replace(",", ".")
            )

    calidad = check_quality(con)
    calidad.raise_if_blocking()
    if calidad.avisos:
        _log.warning(
            "el corte pasa los asserts bloqueantes pero no esta limpio",
            extra={"context": {"usgs_id": usgs_id, "avisos": list(calidad.avisos)}},
        )

    # EL MANIFIESTO LO DICE EL ACTIVO, NO QUIEN LLAMO AL CLI.
    #
    # `--manifest` viene de `data/manifests/` y el activo es un Release que
    # puede ser mas viejo. Ver `manifiesto_del_activo`.
    del_activo = manifiesto_del_activo(con, manifest_id)

    reporte = build_report(
        con,
        state,
        products,
        totales,
        manifest_id=del_activo,
        notas=(*calidad.avisos, *avisos_extra),
    )

    # RF-04: al re-emitir por un ShakeMap nuevo hay que decir **que cambio**.
    # Un ShakeMap se revisa muchas veces —el de Venezuela llego a v14— y quien
    # ya leyo la version anterior no puede tener que releerla entera durante una
    # emergencia para encontrar la diferencia.
    #
    # La seccion se renderizaba desde el principio y no aparecio nunca en un
    # reporte, porque nadie llenaba `Report.changelog`.
    reporte = replace(
        reporte,
        changelog=build_changelog(_reporte_publicado(usgs_id, reports_root), reporte),
    )

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

    # El area de afectacion, que no es la de la exposicion. La malla llega hasta
    # donde hay gente; los contornos del ShakeMap llegan hasta donde llego el
    # sismo, sobre tierra y sobre mar. Se descargan en cada evento para el
    # polyfill y se tiraban al terminar.
    try:
        from ..p3_report.contornos import write_contours_json

        escritos["contornos_json"] = write_contours_json(
            contornos, escritos["report_json"].parent / "contornos.json"
        )
    except Exception as exc:
        _log.warning(
            "no se pudieron escribir los contornos del evento",
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
    from .pipeline import (
        ExposureCountryMismatchError,
        build_preliminary_report,
        compute_preliminary,
        manifiesto_del_activo,
    )

    try:
        con = connect()
        _cargar_admin_lookup(con, exposure_glob, admin_lookup_parquet)
        por_radio = compute_preliminary(con, state, exposure_glob=exposure_glob)
        reporte = build_preliminary_report(
            state, products, por_radio, manifest_id=manifiesto_del_activo(con, manifest_id)
        )
        escritos = write_report_bundle(reporte, [], reports_root=reports_root)
    except ExposureCountryMismatchError:
        # LA UNICA QUE NO SE TRAGA. No es un fallo del preliminar: es la senal
        # de que el activo es de otro pais, y quien tiene que actuar es el
        # orquestador probando el siguiente candidato. Tragarsela aqui deja
        # `run_impact` saliendo con exito y el bucle de `impact.yml` cerrado en
        # el primer candidato, que es como se publica un cero de otro pais.
        raise
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


def _refrescar_lugar(
    state: EventState, detail: dict[str, Any], events_dir: Path | None
) -> EventState:
    """Vuelve a leer del detail lo que USGS puede revisar, y lo guarda si cambio.

    `lugar` es lo unico del `event_state` que es **descripcion y no medida**: no
    identifica el evento ni entra en ningun calculo, solo se lee. Y depende del
    pipeline, no solo de la fuente — desde RF-06 se traduce al espanol al
    entrar.

    Sin esto, los diecinueve eventos ya detectados conservaban para siempre el
    lugar en ingles con que se guardaron, porque `reconstruct_backtest_state`
    —el unico sitio que lo traducia— solo corre cuando el estado **no** existe.
    Reemitir arreglaba las cifras y dejaba el titulo como estaba.

    Y DESDE HOY TAMBIEN LA SOLUCION. `mag`, `depth_km`, `lon` y `lat` no se
    refrescaban por una razon buena —reescribirlos en silencio borraria el
    registro de que el sistema alguna vez dijo otra cosa— pero el precio era
    peor: un M6,6 revisado a M7,2 seguia titulandose M6,6 en el markdown, en el
    PNG y en el indice, **con las intensidades de la solucion revisada**. El
    artefacto quedaba internamente incoherente, y eso nadie puede verlo.

    No hay que elegir entre las dos cosas: se refresca **y** se registra.
    `changelog._cambios_de_solucion` publica "Magnitud: M6,6 → M7,2" en el
    propio reporte, asi que el titular es el vigente y el registro de que
    cambio sigue a la vista.

    `origen_utc` sigue sin tocarse: identifica el evento y es la referencia de
    la latencia.
    """
    try:
        nuevo = traducir_lugar(str(detail["properties"].get("place") or ""))
    except (KeyError, TypeError):
        return state
    solucion: dict[str, float] = {}
    props = detail.get("properties") or {}
    geo = (detail.get("geometry") or {}).get("coordinates") or []
    for campo, valor in (
        ("mag", props.get("mag")),
        ("lon", geo[0] if len(geo) > 0 else None),
        ("lat", geo[1] if len(geo) > 1 else None),
        ("depth_km", geo[2] if len(geo) > 2 else None),
    ):
        if isinstance(valor, int | float) and abs(float(valor) - getattr(state, campo)) > 1e-9:
            solucion[campo] = float(valor)

    if (not nuevo or nuevo == state.lugar) and not solucion:
        return state
    if nuevo and nuevo != state.lugar:
        solucion["lugar"] = nuevo  # type: ignore[assignment]

    _log.info(
        "el detail trae una solución revisada",
        extra={"context": {"usgs_id": state.usgs_id, "campos": sorted(solucion)}},
    )
    refrescado = replace(state, **solucion)  # type: ignore[arg-type]
    refrescado.save(events_dir)
    return refrescado


def _reporte_publicado(usgs_id: str, reports_root: Path | None) -> Report | None:
    """El reporte que ya esta en disco para este evento, si lo hay.

    Es el punto de comparacion del changelog de RF-04. Devuelve ``None`` en la
    primera emision y tambien si el fichero esta ilegible: un changelog que no
    se puede calcular no puede impedir que salga el reporte nuevo, que es lo
    que de verdad hace falta durante el evento.
    """
    raiz = reports_root or REPORTS_DIR
    origen = raiz / validate_usgs_id(usgs_id) / "report.json"
    try:
        return Report.from_dict(json.loads(origen.read_text(encoding="utf-8")))
    except (OSError, ValueError, KeyError) as exc:
        _log.info(
            "sin reporte previo con el que comparar",
            extra={"context": {"usgs_id": usgs_id, "motivo": str(exc)}},
        )
        return None


def _cargar_admin_lookup(con: Any, exposure_glob: str, ruta: str | None) -> None:
    """Materializa ``admin_lookup``, que aporta nombre y centroide municipal."""
    candidata = ruta or str(Path(exposure_glob).parent / "admin_lookup.parquet")
    if Path(candidata).exists():
        con.execute(
            f"CREATE OR REPLACE TABLE admin_lookup AS SELECT * FROM read_parquet('{candidata}')"
        )
        return
    # Sin diccionario el reporte sigue saliendo, con el codigo del municipio como
    # nombre. Es peor de leer, pero mejor que no publicar.
    _log.warning(
        "sin admin_lookup: el reporte usara el codigo del municipio como nombre",
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


def _km_a_la_poblacion_mas_cercana(con: Any, lon: float, lat: float) -> float | None:
    """Del epicentro a la celda poblada mas cercana del activo, en km.

    Haversine en SQL sobre los centroides que DuckDB puede derivar del indice
    H3. Solo se llama cuando el reporte sale con ceros, asi que recorrer el
    activo entero una vez es asumible — y evita depender de una linea de costa
    que este proyecto no consume.
    """
    try:
        fila = con.execute(
            """
            SELECT MIN(
                6371.0 * 2 * asin(sqrt(
                    pow(sin(radians(lat - ?) / 2), 2)
                    + cos(radians(?)) * cos(radians(lat))
                      * pow(sin(radians(lon - ?) / 2), 2)
                ))
            )
            FROM (
                SELECT h3_cell_to_lat(h3_08) AS lat, h3_cell_to_lng(h3_08) AS lon
                FROM exposure WHERE pop_total > 0
            )
            """,
            [lat, lat, lon],
        ).fetchone()
    except Exception as error:  # la extension H3 puede no estar cargada
        _log.warning(
            "no se pudo medir la distancia a la poblacion mas cercana",
            extra={"context": {"error": str(error)}},
        )
        return None
    return None if not fila or fila[0] is None else float(fila[0])
