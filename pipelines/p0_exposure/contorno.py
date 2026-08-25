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

#: Solo tierra. El poligono de aguas territoriales de cada pais duplicaria el
#: peso y no dibuja nada que se vea.
SQL_CONTORNO = """
SELECT country,
       ST_AsGeoJSON(
           ST_SimplifyPreserveTopology(
               ST_Intersection(
                   geometry,
                   ST_MakeEnvelope({lon_min}, {lat_min}, {lon_max}, {lat_max})
               ),
               {tolerancia}
           )
       ) AS geojson
FROM read_parquet('{url}')
WHERE subtype = 'country'
  AND country IS NOT NULL
  AND is_land
  AND bbox.xmin <= {lon_max} AND bbox.xmax >= {lon_min}
  AND bbox.ymin <= {lat_max} AND bbox.ymax >= {lat_min}
"""


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
            )
        ).fetchall()
        for pais, geojson in filas:
            geom = json.loads(geojson)
            # Un pais cuya interseccion con la ventana es vacia sale con una
            # geometria sin coordenadas: no aporta y solo pesa.
            if not geom.get("coordinates"):
                continue
            rasgos.append({"type": "Feature", "geometry": geom, "properties": {"country": pais}})

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
