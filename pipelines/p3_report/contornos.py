"""`contornos.json`: el area de afectacion del sismo, no la de la exposicion.

El visor dibujaba la malla H3, que llega **hasta donde hay algo expuesto**. Su
propia nota lo admitia: «el hueco no es ausencia de sacudida, es ausencia de
gente y de infraestructura». O sea que el tablero ensenaba la forma de la
poblacion recortada por la sacudida, y quien preguntaba «¿hasta donde llego el
terremoto?» no tenia donde mirarlo.

Los contornos del ShakeMap si son eso: la isolinea de cada nivel de intensidad,
sobre tierra y sobre mar, con gente o sin ella. El pipeline los descarga en cada
evento —son la entrada del polyfill— y los tiraba al terminar.

**Se publican desde MMI 4.** Por debajo, USGS dibuja niveles que casi nadie
percibe y que multiplican el peso del fichero con lineas que no significan nada
para quien responde. Desde 4 se cubre lo sentido; desde 6, lo que este sistema
se atreve a cuantificar.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..common.logging import get_logger

_log = get_logger(__name__)

#: Nivel MMI mas bajo que se publica. Ver el modulo.
MMI_MINIMO_CONTORNO = 4.0

#: Lo unico que el visor necesita de cada isolinea. `color` y `weight` vienen
#: del estilo de ShakeMap y **no se copian**: el visor tiene su propia rampa,
#: decidida y argumentada, y arrastrar la de la fuente seria pintar el mismo
#: evento de dos colores segun donde se mire — el error que ya se corrigio una
#: vez entre el visor y el mapa estatico.
PROPIEDAD_VALOR = "value"


def build_contours(
    payload: dict[str, Any], *, mmi_minimo: float = MMI_MINIMO_CONTORNO
) -> dict[str, Any]:
    """GeoJSON minimo con las isolineas de intensidad, de mayor a menor.

    Se ordena descendente para que las lineas de intensidad alta queden encima
    al dibujarse: son las que importan y las que menos espacio ocupan.
    """
    features: list[dict[str, Any]] = []
    for feature in payload.get("features", []):
        try:
            valor = float(feature["properties"][PROPIEDAD_VALOR])
        except (KeyError, TypeError, ValueError):
            continue
        if valor < mmi_minimo:
            continue
        features.append(
            {
                "type": "Feature",
                "geometry": feature["geometry"],
                "properties": {"mmi": valor},
            }
        )

    features.sort(key=lambda f: float(f["properties"]["mmi"]), reverse=True)
    return {"type": "FeatureCollection", "mmi_minimo": mmi_minimo, "features": features}


def write_contours_json(
    origen: Path, destino: Path, *, mmi_minimo: float = MMI_MINIMO_CONTORNO
) -> Path:
    """Escribe los contornos del evento junto al resto del paquete.

    Args:
        origen: el `cont_mmi.json` que P2 ya descargo para el polyfill.
        destino: donde dejarlo, normalmente `reports/<id>/contornos.json`.

    Raises:
        FileNotFoundError: si el `cont_mmi.json` no esta. Sin el no hay area que
            dibujar, y fingir una a partir de la malla seria dibujar la forma de
            la poblacion y llamarla sacudida.
    """
    datos = build_contours(json.loads(origen.read_text(encoding="utf-8")), mmi_minimo=mmi_minimo)
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(datos, separators=(",", ":")), encoding="utf-8")

    niveles = sorted({f["properties"]["mmi"] for f in datos["features"]})
    _log.info(
        "contornos del evento escritos",
        extra={
            "context": {
                "destino": str(destino),
                "niveles": niveles,
                "kb": round(destino.stat().st_size / 1024),
            }
        },
    )
    return destino


def backfill_contours(
    usgs_id: str = "", *, fetcher: Any = None, reports_root: Path | None = None
) -> dict[str, Path]:
    """Baja de USGS el area de afectacion de un reporte ya publicado, o de todos.

    Los reportes emitidos antes de que este fichero existiera no lo traen, y
    recomputar su impacto entero para obtenerlo costaria bajar el activo de su
    pais y rehacer el join — cuando lo unico que falta es un GeoJSON de 100 kB
    que USGS sigue sirviendo.

    Existe por la misma razon que `regenerar-mapas`: la vez anterior que hubo
    que rehacer un derivado de todos los reportes publicados se hizo con un
    script de usar y tirar, y la siguiente correccion dependia de que alguien
    recordara como se hacia.

    Returns:
        ``usgs_id -> ruta`` de lo escrito. Un evento cuyo ShakeMap no publique
        contornos se registra y se salta: no todos los tienen, y para los
        profundos es lo normal.
    """
    from ..common.http import HttpFetcher
    from ..common.paths import REPORTS_DIR, validate_usgs_id
    from ..p2_impact.products import parse_products

    cliente = fetcher or HttpFetcher(timeout_s=120.0)
    raiz = reports_root or REPORTS_DIR
    directorios = (
        [raiz / validate_usgs_id(usgs_id)]
        if usgs_id
        else sorted(p.parent for p in raiz.glob("*/report.json"))
    )

    escritos: dict[str, Path] = {}
    for directorio in directorios:
        evento = directorio.name
        try:
            detalle = cliente.get_json(
                f"https://earthquake.usgs.gov/fdsnws/event/1/query?eventid={evento}&format=geojson"
            )
            url = parse_products(detalle).cont_mmi_url()
            if not url:
                _log.info(
                    "el ShakeMap de este evento no publica contornos",
                    extra={"context": {"usgs_id": evento}},
                )
                continue
            datos = build_contours(json.loads(cliente.get_bytes(url).decode("utf-8")))
            destino = directorio / "contornos.json"
            destino.parent.mkdir(parents=True, exist_ok=True)
            destino.write_text(json.dumps(datos, separators=(",", ":")), encoding="utf-8")
            escritos[evento] = destino
        except Exception as exc:  # una fuente caida no puede tumbar los demas
            _log.warning(
                "no se pudo traer el area de afectacion",
                extra={"context": {"usgs_id": evento, "error": str(exc)}},
            )

    _log.info(
        "areas de afectacion actualizadas",
        extra={"context": {"eventos": len(escritos), "de": len(directorios)}},
    )
    return escritos
