"""Ejecucion del computo de impacto: de los productos USGS al reporte.

Este modulo es el que encadena. Todas las piezas —polyfill de contornos,
muestreo de Ground Failure, join contra el activo, emision del reporte— viven
en sus propios modulos y estan probadas por separado; aqui se llaman en orden y
se persiste el resultado.

Es la diferencia entre "las piezas funcionan" y "el sistema funciona", que es
literalmente la puerta de salida de Fase 0: *un reporte real publicado
end-to-end sin intervencion*.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

from ..common.constants import (
    GROUND_FAILURE_HIGH_PROB,
    MMI_BAND_AGE_BREAKDOWN,
    PRELIMINARY_RADII_KM,
    TOP_ADM2_COUNT,
)
from ..common.formatting import titulo_es
from ..common.geo import haversine_km
from ..common.http import Fetcher
from ..common.logging import get_logger
from ..common.state import EventState
from ..p3_report.model import (
    Descargas,
    Evento,
    GroundFailureUSGS,
    Incertidumbre,
    Inputs,
    MunicipioTop,
    PoblacionEnRadio,
    Report,
    Totales,
)
from .exposure_join import register_cells
from .ground_failure import (
    LANDSLIDE_FALLBACKS,
    LANDSLIDE_MODEL,
    LIQUEFACTION_FALLBACKS,
    LIQUEFACTION_MODEL,
    sample_rasters,
)
from .products import ProductSet
from .shakemap import contours_to_h3, parse_contours

_log = get_logger(__name__)

#: Banda MMI minima que se rellena. El reporte publica desde MMI 6; rellenar
#: los niveles bajos multiplica las celdas sin cambiar una sola cifra.
MMI_MIN_POLYFILL = 5.0


class ExposureCountryMismatchError(ValueError):
    """El activo descargado no es del pais donde ocurrio el sismo.

    Se distingue del resto de errores porque **no es un fallo: es un descarte**.
    P1 vigila toda la ventana LATAM y las cajas de los paises se solapan, asi
    que `countries_for_point` devuelve varios candidatos y el llamador tiene que
    probarlos en orden hasta que uno alcance celdas.

    Que haga falta reintentar no es hipotetico. La caja de Chile mide 1.719
    grados cuadrados por Rapa Nui y la de Argentina 671, asi que **un sismo en
    Coquimbo se ordena como argentino antes que como chileno**. Sin reintento,
    el evento se calcularia contra el activo de Argentina, el join quedaria
    vacio y Chile —de los paises mas sismicos de la region— se quedaria sin
    reporte cada vez.

    Hereda de `ValueError` para no cambiar el comportamiento de quien ya
    capturaba el error anterior.
    """


@dataclass(frozen=True, slots=True)
class ImpactTotals:
    """Cifras nacionales del evento, tal como salen del join."""

    pop_mmi6p: float = 0.0
    pop_mmi7p: float = 0.0
    pop_mmi8p: float = 0.0
    pop_65p_mmi7p: float = 0.0
    bld_mmi7p: float = 0.0
    built_m2_mmi7p: float = 0.0
    health_mmi7p: float = 0.0
    edu_mmi7p: float = 0.0
    road_km_mmi7p: float = 0.0
    #: Solo troncal, autopista, primaria y secundaria. Se publica aparte
    #: porque no es lo mismo que quede cortada una troncal que una calle de
    #: barrio, y porque es la cifra comparable con las estadisticas viales
    #: oficiales. `road_km_mmi7p` sigue siendo el total de red rodada.
    road_km_principal_mmi7p: float = 0.0
    pop_ls_alta: float = 0.0
    pop_lq_alta: float = 0.0
    #: `None` cuando **no se pudo medir**, que no es lo mismo que cero.
    #:
    #: El SQL divide por `SUM(pop_alt_worldpop)` con `NULLIF(...,0)`: si ninguna
    #: celda alcanzada tiene poblacion de WorldPop, el resultado es NULL. Con
    #: `float(v or 0.0)` salia **0,0 %**, y "los dos productos coinciden
    #: perfectamente" es lo contrario de "no habia con que compararlos". Tres
    #: reportes publicados lo decian: us1000c2zy, us6000hf75 y usp000jd2q.
    discrepancia_pct: float | None = None
    #: Columnas que el activo no traia y `register_exposure_view` sustituyo por
    #: cero. Va **al final** y con valor por defecto a proposito: las de arriba
    #: se rellenan por posicion desde la fila de `SQL_TOTALES`, y esta no.
    #:
    #: Existe porque el aviso se perdia. `register_exposure_view` devolvia la
    #: lista y los tres llamadores de produccion descartaban el retorno; solo
    #: una prueba lo miraba. El `report.json` publicaba `built_m2_mmi7p: 0.0`
    #: sin distinguir "no medido" de "medido y da cero", y el CSV igual. El
    #: markdown escondia la fila, que tapa el problema para quien lee y lo deja
    #: intacto para quien integra — que es el consumidor al que mas dano hace.
    #:
    #: `kw_only` para que `*fila` no pueda desbordar hasta aqui: las de arriba se
    #: rellenan por posicion desde el SQL, y esta no sale del SQL.
    columnas_ausentes: tuple[str, ...] = field(default=(), kw_only=True)

    def to_totales(self) -> Totales:
        return Totales(
            pop_mmi6p=self.pop_mmi6p,
            pop_mmi7p=self.pop_mmi7p,
            pop_mmi8p=self.pop_mmi8p,
            pop_65p_mmi7p=self.pop_65p_mmi7p,
            bld_mmi7p=self.bld_mmi7p,
            built_m2_mmi7p=self.built_m2_mmi7p,
            health_mmi7p=self.health_mmi7p,
            edu_mmi7p=self.edu_mmi7p,
            road_km_mmi7p=self.road_km_mmi7p,
            road_km_principal_mmi7p=self.road_km_principal_mmi7p,
            pop_ls_alta=self.pop_ls_alta,
            pop_lq_alta=self.pop_lq_alta,
        )


# --- Descarga de los contenidos del producto -------------------------------


def download_products(
    products: ProductSet, workdir: Path, *, fetcher: Fetcher
) -> tuple[Path | None, Path | None, Path | None]:
    """Baja lo que el computo necesita: contornos y los dos rasters vigentes.

    Returns:
        ``(cont_mmi, deslizamiento, licuefaccion)``. Cualquiera puede ser
        ``None``: un evento sin Ground Failure publicado es normal y el reporte
        lo declara en vez de fallar (golden G3).
    """
    workdir.mkdir(parents=True, exist_ok=True)

    contornos = None
    url = products.cont_mmi_url()
    if url:
        contornos = workdir / "cont_mmi.json"
        contornos.write_bytes(fetcher.get_bytes(url))

    def bajar(nombre: str, alternativas: tuple[str, ...]) -> Path | None:
        if products.ground_failure is None:
            return None
        url = products.ground_failure.content_url(nombre, *alternativas)
        if not url:
            return None
        destino = workdir / nombre
        destino.write_bytes(fetcher.get_bytes(url))
        return destino

    deslizamiento = bajar(LANDSLIDE_MODEL, LANDSLIDE_FALLBACKS)
    licuefaccion = bajar(LIQUEFACTION_MODEL, LIQUEFACTION_FALLBACKS)

    _log.info(
        "productos descargados",
        extra={
            "context": {
                "usgs_id": products.usgs_id,
                "contornos": contornos is not None,
                "deslizamiento": deslizamiento is not None,
                "licuefaccion": licuefaccion is not None,
            }
        },
    )
    return contornos, deslizamiento, licuefaccion


# --- Compatibilidad con activos anteriores ---------------------------------

#: Columnas que el activo gano despues de haberse publicado, con el valor que
#: las sustituye si faltan. La clave del contrato: **un activo viejo tiene que
#: seguir produciendo un reporte**.
#:
#: El caso real es `built_m2`, que llega en col-v0.5. El Release publicado en
#: ese momento era col-v0.4 y no la tiene. Si P2 exigiera la columna, el primer
#: sismo despues de actualizar el codigo y antes de republicar el activo se
#: quedaria **sin reporte** — y no hay peor momento para eso. Con el sustituto,
#: el reporte sale sin la fila de superficie construida, que es una ausencia
#: honesta y no un cero: `_nota_superficie` y la tabla de totales omiten la
#: cifra cuando vale 0 en vez de publicar "0 km² construidos".
#: Columnas que un activo viejo puede no traer, con el valor que las sustituye.
#:
#: Los diecinueve activos publicados se construyeron antes de que existiera la
#: capa de cobertura del suelo, y reconstruirlos cuesta horas de CI. Sin esto,
#: P2 y P5 reventarian con "column not found" contra cualquier activo anterior
#: a la Fase 1 — un fallo total por una columna que solo describe el terreno.
#:
#: El cero no miente aqui porque `register_exposure_view` devuelve la lista de
#: sustituidas y deja aviso: quien lo lea sabe que es "no medido", no "medido y
#: da cero". Es la misma distincion que sostiene toda la capa de observados.
COLUMNAS_OPCIONALES: dict[str, str] = {
    "built_m2": "0.0",
    "lulc_arbolado_pct": "0.0",
    "lulc_arbustos_pct": "0.0",
    "lulc_pastizal_pct": "0.0",
    "lulc_cultivo_pct": "0.0",
    "lulc_construido_pct": "0.0",
    "lulc_humedal_pct": "0.0",
    "lulc_px": "0",
}


def manifiesto_del_activo(con: Any, declarado: str) -> str:
    """El manifiesto que el activo **dice traer**, no el que le pasaron al CLI.

    EL REPORTE DECLARABA UNA RECETA QUE PODIA NO HABER CONSUMIDO.

    `impact.yml` lee `data/manifests/<ISO3>.yaml` del repositorio y se lo pasa a
    P2 por `--manifest`; P2 lo escribia tal cual en `inputs.exposure_manifest`.
    Pero el activo que se descarga es un Release, y el Release puede ser mas
    viejo que el YAML: el reporte declaraba `col-v0.6` habiendose calculado
    contra un activo `col-v0.5`, y nadie podia saberlo.

    Eso rompe RNF-04 por donde mas duele —la trazabilidad de un reporte a sus
    insumos— y ademas dejaba ciego a `rezago.py`: comparaba el manifiesto del
    reporte contra `data/manifests/`, que es de donde habia salido, asi que
    comparaba el repositorio consigo mismo.

    El parquet trae `src_manifest`, escrito por P0 al construirlo. Esa es la
    fuente. El declarado solo se usa si el activo no lo trae —los anteriores a
    Fase 1— y entonces se avisa.
    """
    try:
        filas = con.execute("SELECT DISTINCT src_manifest FROM exposure").fetchall()
    except Exception:  # activo sin la columna
        _log.warning(
            "el activo no declara src_manifest; se usa el manifiesto del CLI",
            extra={"context": {"declarado": declarado}},
        )
        return declarado

    valores = sorted({str(f[0]) for f in filas if f[0]})
    if not valores:
        return declarado
    if len(valores) > 1:
        # Un join contra dos activos de recetas distintas no es un reporte: es
        # dos reportes sumados. Se nombra en vez de elegir uno.
        raise ValueError(
            f"El activo mezcla manifiestos distintos: {valores}. "
            "Un reporte no puede declarar dos recetas."
        )
    if declarado and declarado != valores[0]:
        _log.warning(
            "el manifiesto declarado no es el del activo; manda el del activo",
            extra={"context": {"declarado": declarado, "activo": valores[0]}},
        )
    return valores[0]


def register_exposure_view(con: Any, exposure_glob: str) -> list[str]:
    """Publica la vista ``exposure``, rellenando las columnas que falten.

    Returns:
        Las columnas que hubo que sustituir. Vacio con un activo al dia.
    """
    con.execute(
        f"CREATE OR REPLACE VIEW _exposure_cruda AS SELECT * FROM read_parquet('{exposure_glob}')"
    )
    presentes = {
        str(f[0]).lower() for f in con.execute("DESCRIBE SELECT * FROM _exposure_cruda").fetchall()
    }
    faltan = {c: v for c, v in COLUMNAS_OPCIONALES.items() if c.lower() not in presentes}
    extra = "".join(f", {valor} AS {col}" for col, valor in faltan.items())
    con.execute(f"CREATE OR REPLACE VIEW exposure AS SELECT *{extra} FROM _exposure_cruda")

    if faltan:
        _log.warning(
            "el activo no trae columnas que el reporte sabe publicar; se omitiran",
            extra={
                "context": {
                    "columnas_ausentes": sorted(faltan),
                    "activo": exposure_glob,
                    "accion": "reconstruir y republicar el activo para incluirlas",
                }
            },
        )
    return sorted(faltan)


# --- SQL del computo -------------------------------------------------------

SQL_IMPACT_H3 = """
CREATE OR REPLACE TABLE impact_h3 AS
SELECT
    ? AS usgs_id, ? AS shakemap_version,
    e.*, m.mmi_mean, m.mmi_max,
    COALESCE(g.ls_prob, 0.0) AS ls_prob,
    COALESCE(g.lq_prob, 0.0) AS lq_prob
FROM exposure AS e
JOIN mmi_cells AS m USING (h3_08)
LEFT JOIN gf_cells AS g USING (h3_08)
"""

#: Agregado municipal. **Toda** columna lleva su propio corte de MMI, incluidas
#: las dos de Ground Failure: `impact_h3` arranca en MMI 5,0 y sin ese corte las
#: celdas de 5-5,5 entraban solo en la exposicion a deslizamiento y licuefaccion,
#: que es exactamente el conjunto que `SQL_TOTALES` no cuenta. La suma del CSV
#: daba mas que la cifra nacional del mismo evento, las dos positivas y del orden
#: correcto, asi que ninguna prueba lo veia. El corte va en los dos sitios y en
#: el nombre de la columna.
SQL_IMPACT_ADM2 = """
CREATE OR REPLACE TABLE impact_adm2 AS
SELECT
    usgs_id, shakemap_version, adm2_id,
    MAX(mmi_max) AS mmi_max,
    SUM(CASE WHEN mmi_max >= 6 THEN pop_total ELSE 0 END) AS pop_mmi6p,
    SUM(CASE WHEN mmi_max >= 7 THEN pop_total ELSE 0 END) AS pop_mmi7p,
    SUM(CASE WHEN mmi_max >= 8 THEN pop_total ELSE 0 END) AS pop_mmi8p,
    SUM(CASE WHEN mmi_max >= {edad} THEN pop_65p ELSE 0 END) AS pop_65p_mmi7p,
    SUM(CASE WHEN mmi_max >= 7 THEN bld_count ELSE 0 END) AS bld_mmi7p,
    SUM(CASE WHEN mmi_max >= 7 THEN built_m2 ELSE 0 END) AS built_m2_mmi7p,
    SUM(CASE WHEN mmi_max >= 7 THEN health_count ELSE 0 END) AS health_mmi7p,
    SUM(CASE WHEN mmi_max >= 7 THEN edu_count ELSE 0 END) AS edu_mmi7p,
    SUM(CASE WHEN mmi_max >= 7
             THEN road_km_primary + road_km_secondary + road_km_other
             ELSE 0 END) AS road_km_mmi7p,
    SUM(CASE WHEN mmi_max >= 7
             THEN road_km_primary + road_km_secondary
             ELSE 0 END) AS road_km_principal_mmi7p,
    SUM(CASE WHEN mmi_max >= 6 AND ls_prob >= {gf}
             THEN pop_total ELSE 0 END) AS ls_pop_expuesta_mmi6p,
    SUM(CASE WHEN mmi_max >= 6 AND lq_prob >= {gf}
             THEN pop_total ELSE 0 END) AS lq_pop_expuesta_mmi6p,
    NULLIF(STRING_AGG(DISTINCT flags_calidad, ','), '') AS flags_calidad
FROM impact_h3
GROUP BY ALL
ORDER BY pop_mmi7p DESC
"""

SQL_TOTALES = """
SELECT
    SUM(CASE WHEN mmi_max >= 6 THEN pop_total ELSE 0 END),
    SUM(CASE WHEN mmi_max >= 7 THEN pop_total ELSE 0 END),
    SUM(CASE WHEN mmi_max >= 8 THEN pop_total ELSE 0 END),
    SUM(CASE WHEN mmi_max >= {edad} THEN pop_65p ELSE 0 END),
    SUM(CASE WHEN mmi_max >= 7 THEN bld_count ELSE 0 END),
    SUM(CASE WHEN mmi_max >= 7 THEN built_m2 ELSE 0 END),
    SUM(CASE WHEN mmi_max >= 7 THEN health_count ELSE 0 END),
    SUM(CASE WHEN mmi_max >= 7 THEN edu_count ELSE 0 END),
    SUM(CASE WHEN mmi_max >= 7
             THEN road_km_primary + road_km_secondary + road_km_other
             ELSE 0 END),
    SUM(CASE WHEN mmi_max >= 7
             THEN road_km_primary + road_km_secondary
             ELSE 0 END),
    SUM(CASE WHEN mmi_max >= 6 AND ls_prob >= {gf} THEN pop_total ELSE 0 END),
    SUM(CASE WHEN mmi_max >= 6 AND lq_prob >= {gf} THEN pop_total ELSE 0 END),
    100 * abs(SUM(pop_total) - SUM(pop_alt_worldpop))
        / NULLIF(SUM(pop_alt_worldpop), 0)
FROM impact_h3
WHERE mmi_max >= 6
"""


def compute_impact(
    con: Any,
    products: ProductSet,
    *,
    exposure_glob: str,
    contornos: Path,
    deslizamiento: Path | None,
    licuefaccion: Path | None,
) -> ImpactTotals:
    """Corre el computo completo y deja ``impact_h3`` e ``impact_adm2``."""
    import json

    celdas_mmi = contours_to_h3(
        parse_contours(json.loads(contornos.read_text(encoding="utf-8"))),
        min_value=MMI_MIN_POLYFILL,
    )
    if not celdas_mmi:
        raise ValueError(
            f"El ShakeMap de {products.usgs_id} no produjo ninguna celda: "
            f"contornos vacios o degenerados."
        )
    celdas_gf = sample_rasters(deslizamiento, licuefaccion, list(celdas_mmi))

    from .exposure_join import JoinInputs

    register_cells(
        con,
        JoinInputs(
            usgs_id=products.usgs_id,
            shakemap_version=products.shakemap_version,
            exposure_glob=exposure_glob,
            mmi_cells=celdas_mmi,
            gf_cells=celdas_gf,
        ),
    )
    ausentes = register_exposure_view(con, exposure_glob)
    con.execute(SQL_IMPACT_H3, [products.usgs_id, products.shakemap_version])

    # El activo y el sismo tienen que ser del mismo pais. Si no lo son, el join
    # no encuentra una sola celda, `SQL_TOTALES` devuelve NULL en cada columna,
    # `float(v or 0.0)` los convierte en ceros y **se publica un reporte
    # diciendo que no hay nadie expuesto**. Durante un terremoto real, en el
    # visor publico. Es preferible no publicar nada.
    alcanzadas: int = con.execute("SELECT count(*) FROM impact_h3").fetchone()[0]
    if alcanzadas == 0:
        raise ExposureCountryMismatchError(
            f"El ShakeMap de {products.usgs_id} no toca ninguna celda del activo "
            f"({exposure_glob}). Significa que el sismo cayo en un pais distinto al "
            f"del activo descargado. Un reporte calculado asi saldria con ceros en "
            f"todas las cifras, que es peor que no publicarlo: hay que reintentar "
            f"con el activo del siguiente pais candidato."
        )
    _log.info(
        "celdas alcanzadas por el ShakeMap",
        extra={"context": {"usgs_id": products.usgs_id, "celdas": alcanzadas}},
    )

    con.execute(SQL_IMPACT_ADM2.format(edad=MMI_BAND_AGE_BREAKDOWN, gf=GROUND_FAILURE_HIGH_PROB))

    fila = con.execute(
        SQL_TOTALES.format(edad=MMI_BAND_AGE_BREAKDOWN, gf=GROUND_FAILURE_HIGH_PROB)
    ).fetchone()
    # `replace` y no un positional mas: las cifras se rellenan por posicion desde
    # la fila del SQL, y mezclar las dos formas en la misma llamada deja a mypy
    # sin poder contar los argumentos.
    # La discrepancia se saca aparte: es la unica columna donde NULL significa
    # "no se pudo medir" y no "cero". Ver `ImpactTotals.discrepancia_pct`.
    crudos = list(fila)
    discrepancia = crudos[-1]
    totales = replace(
        ImpactTotals(*(float(v or 0.0) for v in crudos)),
        columnas_ausentes=tuple(ausentes),
        discrepancia_pct=None if discrepancia is None else float(discrepancia),
    )
    _log.info(
        "impacto calculado",
        extra={
            "context": {
                "usgs_id": products.usgs_id,
                "celdas_mmi": len(celdas_mmi),
                "pop_mmi7p": totales.pop_mmi7p,
            }
        },
    )
    return totales


# --- Reporte preliminar sin ShakeMap (RF-03) -------------------------------


def compute_preliminary(con: Any, state: EventState, *, exposure_glob: str) -> dict[int, float]:
    """Poblacion dentro de radios alrededor del epicentro.

    Cuando USGS aun no ha publicado ShakeMap, el corte por radios es lo unico
    honesto que se puede decir: no hay modelo de intensidad, solo distancia. El
    reporte lo declara asi y se re-emite solo en cuanto aparezca el ShakeMap.
    """
    register_exposure_view(con, exposure_glob)
    filas = con.execute(
        "SELECT h3_cell_to_lat(h3_08), h3_cell_to_lng(h3_08), pop_total FROM exposure"
    ).fetchall()

    por_radio = dict.fromkeys(PRELIMINARY_RADII_KM, 0.0)
    for lat, lon, pop in filas:
        d = haversine_km(state.lon, state.lat, float(lon), float(lat))
        for radio in PRELIMINARY_RADII_KM:
            if d <= radio:
                por_radio[radio] += float(pop or 0.0)
    _log.info(
        "corte preliminar por radios",
        extra={
            "context": {"usgs_id": state.usgs_id, **{f"r{k}km": v for k, v in por_radio.items()}}
        },
    )
    return por_radio


def build_preliminary_report(
    state: EventState,
    products: ProductSet,
    por_radio: dict[int, float],
    *,
    manifest_id: str,
) -> Report:
    """Arma el reporte preliminar de RF-03, el que sale sin ShakeMap.

    Deliberadamente **no** lleva `Totales`: sin ShakeMap todas las cifras por
    intensidad valen cero, y publicar "poblacion en MMI>=7: 0" seria una
    respuesta falsa y creible. El markdown publica la tabla por radios en su
    lugar, no ademas.
    """
    return Report(
        event=Evento(
            usgs_id=state.usgs_id,
            mag=state.mag,
            depth_km=state.depth_km,
            utc=state.origen_utc,
            lugar=state.lugar,
            pager_alert=products.pager_alert(),
            lon=state.lon,
            lat=state.lat,
        ),
        inputs=Inputs(
            shakemap_version=0,
            groundfailure_version=products.groundfailure_version,
            exposure_manifest=manifest_id,
        ),
        totales=Totales(),
        radios=tuple(
            PoblacionEnRadio(radio_km=int(km), pop=float(pop))
            for km, pop in sorted(por_radio.items())
        ),
        preliminar=True,
        backtest=state.backtest,
    )


# --- Construccion del reporte ----------------------------------------------


def nota_de_columnas_ausentes(columnas: tuple[str, ...]) -> tuple[str, ...]:
    """Convierte el aviso de `register_exposure_view` en una nota publicada.

    Sin esto, una columna que el activo no trae sale como `0.0` en el JSON y en
    el CSV, indistinguible de una medida que da cero. El markdown esconde la
    fila —que es lo correcto para quien lee— y por eso el problema solo lo
    sufria quien integra, que es a quien mas le cuesta.
    """
    if not columnas:
        return ()
    return (
        f"El activo consumido no trae {len(columnas)} columna(s) que este reporte sabe "
        f"publicar ({', '.join(columnas)}); salen como cero y **no estan medidas**. "
        "Se corrige reconstruyendo y republicando el activo del pais.",
    )


def build_report(
    con: Any,
    state: EventState,
    products: ProductSet,
    totales: ImpactTotals,
    *,
    manifest_id: str,
    notas: tuple[str, ...] = (),
) -> Report:
    """Arma el ``Report`` a partir de lo ya calculado en la conexion."""
    # SE ORDENA POR LA BANDA QUE ESTE EVENTO ALCANZO, NO SIEMPRE POR MMI≥7.
    #
    # Casi la mitad de los sismos reales de LATAM no llegan a MMI≥7 sobre
    # poblacion —ocho de los primeros dieciocho reportes— porque son profundos
    # o mar adentro. Para esos, `ORDER BY pop_mmi7p` ordenaba por una columna
    # de ceros, o sea que la tabla "municipios mas expuestos" salia en orden
    # alfabetico con quince ceros al lado. Tehuantepec 2017, un M8,2 con 98
    # muertos, se publicaba asi.
    banda = totales.to_totales().banda_titular
    columna = f"pop_mmi{banda}p" if banda else "pop_mmi6p"
    top = [
        MunicipioTop(
            adm2_id=str(r[0]),
            nombre=titulo_es(str(r[1])),
            mmi_max=float(r[2]),
            pop_mmi7p=float(r[3]),
            pop_banda=float(r[4]),
        )
        for r in con.execute(
            f"""
            SELECT i.adm2_id, a.nombre, i.mmi_max, i.pop_mmi7p, i.{columna}
            FROM impact_adm2 i JOIN admin_lookup a USING (adm2_id)
            ORDER BY i.{columna} DESC, i.mmi_max DESC LIMIT {TOP_ADM2_COUNT}
            """
        ).fetchall()
    ]
    return Report(
        event=Evento(
            usgs_id=state.usgs_id,
            mag=state.mag,
            depth_km=state.depth_km,
            utc=state.origen_utc,
            lugar=state.lugar,
            pager_alert=products.pager_alert(),
            lon=state.lon,
            lat=state.lat,
        ),
        inputs=Inputs(
            shakemap_version=products.shakemap_version,
            groundfailure_version=products.groundfailure_version,
            exposure_manifest=manifest_id,
        ),
        totales=totales.to_totales(),
        ground_failure_usgs=GroundFailureUSGS(**products.ground_failure_alerts()),
        # El estado del evento sabe si es una reconstruccion; el reporte tiene
        # que decirlo, porque cambia lo que sus cifras afirman.
        backtest=state.backtest,
        top_municipios=tuple(top),
        incertidumbre=Incertidumbre(
            pop_discrepancia_pct=(
                None if totales.discrepancia_pct is None else round(totales.discrepancia_pct, 1)
            ),
            notas=notas + nota_de_columnas_ausentes(totales.columnas_ausentes),
        ),
        descargas=Descargas(csv_adm2="adm2.csv", mapa_png="mapa_general.png"),
    )
