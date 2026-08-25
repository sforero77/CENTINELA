"""Resolucion de recursos en HDX (Humanitarian Data Exchange).

Existe por un hallazgo concreto de la auditoria de fuentes: **la URL de
descarga de un mismo dataset de HOTOSM cambia de forma segun el pais**. Para la
misma capa logica (`health_facilities`) conviven al menos tres patrones::

    COL -> production-raw-data-api.s3.amazonaws.com/ISO3/COL/health_facilities/…
    MEX -> s3.dualstack.us-east-1.amazonaws.com/production-raw-data-api/ISO3/MEX/
           health_facilities/points/…
    PER -> export.hotosm.org/downloads/<uuid>/…

Adivinar la ruta funciona para unos paises y falla para otros — exactamente el
tipo de fallo que aparecería en Fase 1 al agregar el sexto pais y no antes. El
identificador estable es el **nombre del dataset** (`hotosm_per_health_facilities`),
y la URL se resuelve por la API de CKAN en el momento del build.

El manifest guarda el nombre del dataset y el hash del archivo obtenido; la URL
resuelta se registra en el log del build para que quede en la trazabilidad.
"""

from __future__ import annotations

from .http import Fetcher

HDX_PACKAGE_SHOW = "https://data.humdata.org/api/3/action/package_show?id={dataset}"

#: Formatos preferidos, en orden. GeoPackage primero: un solo archivo, con CRS
#: declarado y sin el limite de 10 caracteres por campo del shapefile.
PREFERRED_FORMATS: tuple[str, ...] = ("Geopackage", "GeoJSON", "SHP")


#: Fragmentos que delatan un recurso **parcial**: la misma capa partida por tipo
#: de geometria. Aparecen en algunos paises y no en otros.
PARTIAL_MARKERS: tuple[str, ...] = ("_points_", "_polygons_", "_lines_")


class HdxResolutionError(Exception):
    """No se pudo resolver el recurso pedido en HDX."""


def _es_parcial(nombre: str) -> bool:
    return any(marca in nombre.lower() for marca in PARTIAL_MARKERS)


def resolve_attempts(
    fetcher: Fetcher,
    dataset: str,
    *,
    formats: tuple[str, ...] = PREFERRED_FORMATS,
    resource: str = "",
) -> list[tuple[str, list[str]]]:
    """Formas de obtener la capa completa, en orden de preferencia.

    Cada intento es ``(formato, urls)`` y **todas sus urls hacen falta**: quien
    descargue prueba el primero y pasa al siguiente si alguna falla.

    Existe porque HOTOSM publica la misma capa de tres maneras segun el pais:

    * Colombia y Ecuador: **un** GeoPackage combinado, en S3.
    * Peru: el combinado apunta a ``export.hotosm.org`` —un export efimero que
      ya devuelve 404— y ademas publica ``_points_`` y ``_polygons_`` por
      separado, esos si vivos en S3.

    Quedarse con los puntos no es opcion: el propio extracto de salud mezcla
    POINT, POLYGON y MULTIPOLYGON porque **un hospital grande esta mapeado como
    edificio y no como nodo**, asi que descartar los poligonos perderia
    justamente los establecimientos mas grandes.

    El combinado va primero y los parciales despues, nunca juntos: si los tres
    estuvieran vivos, bajarlos todos contaria cada sede dos veces.
    """
    payload = fetcher.get_json(HDX_PACKAGE_SHOW.format(dataset=dataset))
    if not payload.get("success"):
        raise HdxResolutionError(f"HDX no reconoce el dataset {dataset!r}")
    recursos = [r for r in (payload["result"].get("resources") or []) if r.get("url")]

    if resource:
        aguja = resource.lower()
        elegidos = [r for r in recursos if aguja in str(r.get("name", "")).lower()]
        if len(elegidos) != 1:
            nombres = [str(r.get("name", "?")) for r in recursos]
            raise HdxResolutionError(
                f"{resource!r} identifica {len(elegidos)} recursos en {dataset!r}, "
                f"y tiene que identificar exactamente uno. Disponibles: {nombres}"
            )
        return [(str(elegidos[0].get("format", "?")), [str(elegidos[0]["url"])])]

    intentos: list[tuple[str, list[str]]] = []
    for formato in formats:
        del_formato = [r for r in recursos if str(r.get("format", "")).lower() == formato.lower()]
        if not del_formato:
            continue
        completos = [r for r in del_formato if not _es_parcial(str(r.get("name", "")))]
        parciales = [r for r in del_formato if _es_parcial(str(r.get("name", "")))]
        if completos:
            intentos.append((formato, [str(completos[0]["url"])]))
        if parciales:
            intentos.append((formato, [str(r["url"]) for r in parciales]))

    if not intentos:
        disponibles = sorted({str(r.get("format", "?")) for r in recursos})
        raise HdxResolutionError(
            f"{dataset!r} no publica ninguno de {list(formats)}; tiene {disponibles}"
        )
    return intentos


def dataset_license(fetcher: Fetcher, dataset: str) -> str:
    """Identificador de licencia que HDX declara para un dataset.

    Se consulta en cada build y se contrasta con lo que dice el manifest: si el
    publicador cambia la licencia, queremos enterarnos por un fallo del lint y
    no por un reclamo.
    """
    payload = fetcher.get_json(HDX_PACKAGE_SHOW.format(dataset=dataset))
    if not payload.get("success"):
        raise HdxResolutionError(f"HDX no reconoce el dataset {dataset!r}")
    return str(payload["result"].get("license_id") or "")


#: Traduccion de los identificadores de licencia de HDX a los del registro
#: interno (:mod:`pipelines.common.licensing`).
HDX_LICENSE_MAP: dict[str, str] = {
    "hdx-odc-odbl": "ODbL-1.0",
    "odbl": "ODbL-1.0",
    "cc-by": "CC-BY-4.0",
    "cc-by-igo": "CC-BY-IGO",
    "cc-by-sa": "CC-BY-SA-4.0",
    "cc-zero": "CC0-1.0",
    "public-domain": "public-domain",
}


def map_license(hdx_license_id: str) -> str:
    """Traduce una licencia de HDX al registro interno.

    Raises:
        HdxResolutionError: ante una licencia que no sabemos clasificar. HDX usa
            ``hdx-other`` como cajon de sastre; darle un default permisivo seria
            justo el error que la regla de los tres cubos existe para evitar.
    """
    try:
        return HDX_LICENSE_MAP[hdx_license_id.lower()]
    except KeyError:
        raise HdxResolutionError(
            f"Licencia de HDX sin traduccion: {hdx_license_id!r}. "
            f"Revisa el dataset a mano antes de incorporarlo."
        ) from None
