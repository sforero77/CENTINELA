"""Contorno de LATAM para la vista regional del visor.

**Las teselas de Overture son para el detalle, no para el conjunto.** Medido
sobre el release 2026-08-19.0: una sola tesela de `base` a zoom 4 pesa 4,3 MB y
una de `divisions` a zoom 3 pesa 1,7 MB. La vista inicial del visor —toda
America Latina— pide unos 6 MB para dibujar cuatro rayas.

Asi que para esa vista se usa un contorno propio: los mismos poligonos de pais
de Overture, recortados a la ventana LATAM y simplificados a 0,02 grados
(~2,2 km). A la escala en la que se ven —un continente en 1.100 pixeles— dos
kilometros son menos de un pixel.

Las teselas siguen entrando al acercarse, que es donde su detalle vale lo que
pesa.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..common.geo import LATAM_BBOX
from ..common.logging import get_logger

_log = get_logger(__name__)

#: Tolerancia de simplificacion, en grados. ~2,2 km: menos de un pixel a la
#: escala en la que se dibuja este contorno.
SIMPLIFICACION_GRADOS = 0.02

#: Superficie minima de un poligono para entrar al contorno, en km2.
#:
#: **Es una decision de dibujo, no de datos.** El activo de exposicion cuenta
#: hasta la ultima isla habitada y eso no se toca; esto solo decide que se pinta
#: en el fondo gris de detras. Medido: de los 10.536 poligonos de la ventana
#: LATAM, **8.361 miden menos de 1 km2**, sobre todo islotes del Caribe. A la
#: escala en que se dibuja este contorno un pixel son unos 80 km2, asi que cada
#: uno ocupa menos de una centesima de pixel y pesa lo mismo que uno visible.
AREA_MINIMA_KM2 = 1.0

#: Decimales de las coordenadas. Cuatro son ~11 m, muy por debajo del pixel.
#: `ST_AsGeoJSON` emite quince, que pesan y no dibujan nada.
DECIMALES = 4

#: Solo tierra. El poligono de aguas territoriales de cada pais duplicaria el
#: peso y no dibuja nada que se vea.
#:
#: Se descompone con `ST_Dump` para poder descartar por superficie: un pais es
#: un MULTIPOLYGON y su area total no dice nada de sus partes.
SQL_CONTORNO = """
WITH recorte AS (
    SELECT country,
           ST_SimplifyPreserveTopology(
               ST_Intersection(
                   geometry,
                   ST_MakeEnvelope({lon_min}, {lat_min}, {lon_max}, {lat_max})
               ),
               {tolerancia}
           ) AS geom
    FROM read_parquet('{url}')
    WHERE subtype = 'country'
      AND country IS NOT NULL
      AND is_land
      AND bbox.xmin <= {lon_max} AND bbox.xmax >= {lon_min}
      AND bbox.ymin <= {lat_max} AND bbox.ymax >= {lat_min}
)
SELECT country, ST_AsGeoJSON(ST_Collect(list(g))) AS geojson
FROM (
    SELECT country, t.p.geom AS g
    FROM recorte, unnest(ST_Dump(geom)) AS t(p)
    WHERE ST_Area_Spheroid(t.p.geom) / 1e6 >= {area_minima}
)
GROUP BY country
"""


def _recortar(obj: Any, decimales: int) -> Any:
    """Redondea las coordenadas. Quince decimales pesan y no dibujan nada."""
    if isinstance(obj, float):
        return round(obj, decimales)
    if isinstance(obj, list):
        return [_recortar(x, decimales) for x in obj]
    if isinstance(obj, dict):
        return {k: _recortar(v, decimales) for k, v in obj.items()}
    return obj


def build_contorno(destino: Path, *, release: str, fetcher: Any = None) -> Path:
    """Escribe el GeoJSON del contorno de LATAM desde Overture."""
    from ..common.http import HttpFetcher
    from ..p2_impact.exposure_join import connect
    from .overture_h3 import ensure_httpfs
    from .sources.overture import THEME_DIVISIONS, resolve_data_urls, select_files

    f = fetcher or HttpFetcher()
    urls = resolve_data_urls(
        f,
        select_files(
            f, LATAM_BBOX, release=release, theme=THEME_DIVISIONS[0], type_=THEME_DIVISIONS[1]
        ),
    )
    con = connect()
    ensure_httpfs(con)

    rasgos: list[dict[str, Any]] = []
    for url in urls:
        filas = con.execute(
            SQL_CONTORNO.format(
                url=url,
                lon_min=LATAM_BBOX.lon_min,
                lat_min=LATAM_BBOX.lat_min,
                lon_max=LATAM_BBOX.lon_max,
                lat_max=LATAM_BBOX.lat_max,
                tolerancia=SIMPLIFICACION_GRADOS,
                area_minima=AREA_MINIMA_KM2,
            )
        ).fetchall()
        for pais, geojson in filas:
            geom = json.loads(geojson)
            # Un pais cuya interseccion con la ventana es vacia sale con una
            # geometria sin coordenadas: no aporta y solo pesa.
            if not geom.get("coordinates"):
                continue
            rasgos.append(
                {
                    "type": "Feature",
                    "geometry": _recortar(geom, DECIMALES),
                    "properties": {"country": pais},
                }
            )

    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(
        json.dumps({"type": "FeatureCollection", "features": rasgos}, separators=(",", ":")),
        encoding="utf-8",
    )
    _log.info(
        "contorno de LATAM escrito",
        extra={
            "context": {
                "destino": str(destino),
                "paises": len(rasgos),
                "kb": round(destino.stat().st_size / 1024),
                "tolerancia_grados": SIMPLIFICACION_GRADOS,
            }
        },
    )
    return destino
