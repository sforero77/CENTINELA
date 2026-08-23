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

from typing import Any

from .http import Fetcher

HDX_PACKAGE_SHOW = "https://data.humdata.org/api/3/action/package_show?id={dataset}"

#: Formatos preferidos, en orden. GeoPackage primero: un solo archivo, con CRS
#: declarado y sin el limite de 10 caracteres por campo del shapefile.
PREFERRED_FORMATS: tuple[str, ...] = ("Geopackage", "GeoJSON", "SHP")


class HdxResolutionError(Exception):
    """No se pudo resolver el recurso pedido en HDX."""


def resolve_resource(
    fetcher: Fetcher,
    dataset: str,
    *,
    formats: tuple[str, ...] = PREFERRED_FORMATS,
) -> tuple[str, str]:
    """Devuelve ``(formato, url)`` del mejor recurso disponible de un dataset.

    Args:
        fetcher: cliente HTTP.
        dataset: nombre estable del dataset en HDX, p. ej.
            ``hotosm_col_health_facilities``.
        formats: formatos aceptados, en orden de preferencia.

    Raises:
        HdxResolutionError: si el dataset no existe o no publica ninguno de los
            formatos pedidos.
    """
    payload = fetcher.get_json(HDX_PACKAGE_SHOW.format(dataset=dataset))
    if not payload.get("success"):
        raise HdxResolutionError(f"HDX no reconoce el dataset {dataset!r}")

    resultado: dict[str, Any] = payload["result"]
    recursos = resultado.get("resources") or []
    por_formato = {
        str(r.get("format", "")).lower(): str(r["url"])
        for r in reversed(recursos)  # el primero de cada formato gana
        if r.get("url")
    }
    for formato in formats:
        url = por_formato.get(formato.lower())
        if url:
            return formato, url

    disponibles = sorted({str(r.get("format", "?")) for r in recursos})
    raise HdxResolutionError(
        f"{dataset!r} no publica ninguno de {list(formats)}; tiene {disponibles}"
    )


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
