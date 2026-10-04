#!/usr/bin/env python3
"""Congela un evento real como fixture golden (T0.2).

Uso::

    uv run --extra dev python scripts/freeze_event.py us6000tjl2 \\
        --out tests/fixtures/golden/choco_2026_08_10

    # Evento doble: los dos ids van a la misma carpeta y comparten feed
    uv run --extra dev python scripts/freeze_event.py us6000t7zp us6000t7zc \\
        --out tests/fixtures/golden/venezuela_2026_06_24

Escribe **los ficheros que `tests/golden/` lee, con los nombres con que los lee**:

- ``detail_superseded.json`` —``detail_<id>_superseded.json`` si son varios
  ids—: el detail con ``includesuperseded``, recortado a los tres productos que
  consume el pipeline y, dentro de cada version, a los contenidos que pide por
  nombre. Es la **secuencia de versiones** que G1 y G2 recorren para el
  changelog de RF-04: metadatos, no contenidos.
- ``cont_mmi_v<N>.json``: los contornos del ShakeMap **vigente**, byte a byte
  como los sirve USGS. Es el insumo de G4 y de ``scripts/fixture_golden.py``.
- ``feed_reconstruido.json``: la consulta FDSN que reconstruye lo que P1 habria
  visto en la ventana del evento.
- ``congelado.json``: que version era la preferida al congelar, y de donde salio.
- ``hashes.json``: el sha256 de cada fichero anterior. Solo de esos.

``exposure_recortado.parquet`` no sale de USGS sino del activo del pais: lo
escribe ``scripts/fixture_golden.py`` a partir del ``cont_mmi_v<N>.json`` de
aqui. ``pager_exposures.json`` tampoco: su emparejamiento con un ShakeMap se
comprueba a mano y lo cuenta su ``.origen.json``.

ESCRIBIA UN ``detail.json`` QUE NO LEIA NADIE, Y BAJABA 241 MB PARA NADA.

Hasta el 3-oct-2026 el script guardaba el detail como ``detail.json`` —ninguna
prueba abre ese nombre— y, en una carpeta por version, **todos** los contenidos
de **todas** las versiones: la auditoria del 5-sep conto unos 116 contenidos,
241 MB solo del ShakeMap con un ``.hdf`` de 62 MB, escritos dentro del
repositorio con ``get_bytes``. A la vez, ninguno de los ficheros que las
fixtures golden si leen lo producia el script: se habian sacado con ``curl`` a mano, como cuenta
``tests/fixtures/golden/README.md``. La herramienta de T0.2 no servia para
regenerar la fixture de T0.2.

Y los rasteres ``.tif`` de Ground Failure que bajaba los descarta
``.gitignore`` (``*.tif``, sin excepcion para ``tests/fixtures``) sin decir
nada, mientras ``hashes.json`` los declaraba como parte de la fixture: el
manifiesto prometia ficheros que ningun clon iba a tener.

La secuencia v1 -> v2 -> v3 que motivo el «todas las versiones» sigue entera:
vive en el detail con ``includesuperseded``, que es justo lo que las pruebas
recorren. Lo que no hacia falta eran los contenidos de cada version.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from pipelines.common.constants import MIN_MAGNITUDE, USGS_FDSN_EVENT
from pipelines.common.geo import LATAM_BBOX
from pipelines.common.http import Fetcher, HttpFetcher
from pipelines.p2_impact.products import (
    GROUND_FAILURE,
    LOSSPAGER,
    SHAKEMAP,
    ProductRef,
    parse_products,
)

#: `includesuperseded` es lo que convierte «la vigente» en «la secuencia».
DETAIL_URL = f"{USGS_FDSN_EVENT}?eventid={{usgs_id}}&format=geojson&includesuperseded=true"

#: Productos que se conservan en el detail recortado.
TIPOS: tuple[str, ...] = (SHAKEMAP, GROUND_FAILURE, LOSSPAGER)

#: Contenidos que el pipeline pide por nombre; el resto —``phase-data``,
#: ``.hdf``, cientos de auxiliares por version— es peso que pagaria cada clon
#: sin que nada lo lea. Es la regla con que se recortaron a mano las fixtures
#: de Choco y Venezuela: aplicada a su detail lo deja igual byte a byte.
CONTENIDOS_QUE_SE_CONSERVAN: frozenset[str] = frozenset({"cont_mmi.json", "grid.xml"})
SUFIJOS_QUE_SE_CONSERVAN: tuple[str, ...] = (".tif",)

#: La unica clave de contornos que se congela: G4 y `fixture_golden.py` leen
#: JSON. Las alternativas de `cont_mmi_url` (``.zip``, ``contours.json``) no se
#: escriben con nombre ``.json`` porque no lo son.
CLAVE_CONTORNOS = "download/cont_mmi.json"


def _se_conserva(clave: str) -> bool:
    return Path(clave).name in CONTENIDOS_QUE_SE_CONSERVAN or clave.endswith(
        SUFIJOS_QUE_SE_CONSERVAN
    )


def recortar_detail(detail: dict[str, Any]) -> dict[str, Any]:
    """El detail con solo los productos y contenidos que consume el pipeline.

    Conserva el historial de versiones entero: el recorte es por contenido,
    nunca por entrada.
    """
    propiedades = dict(detail.get("properties") or {})
    productos = propiedades.get("products") or {}
    recortados: dict[str, list[dict[str, Any]]] = {}
    for tipo in sorted(productos):
        if tipo not in TIPOS or not isinstance(productos[tipo], list):
            continue
        entradas = []
        for entrada in productos[tipo]:
            if not isinstance(entrada, dict):
                continue
            contenidos = entrada.get("contents") or {}
            entradas.append(
                {**entrada, "contents": {k: v for k, v in contenidos.items() if _se_conserva(k)}}
            )
        recortados[tipo] = entradas
    propiedades["products"] = recortados
    return {**detail, "properties": propiedades}


def ventana_del_feed(origenes_ms: Sequence[int]) -> tuple[datetime, datetime]:
    """Ventana de la consulta FDSN: de media hora antes a una hora despues.

    Redondeada a la media hora, que es como se reconstruyeron a mano los dos
    feeds congelados (Choco 12:34 -> 12:00-13:30; Venezuela 22:04 y 22:05 ->
    21:30-23:00). Con varios ids abarca del primero al ultimo.
    """

    def _a_media_hora(t: datetime) -> datetime:
        return t.replace(minute=30 if t.minute >= 30 else 0, second=0, microsecond=0)

    origenes = [datetime.fromtimestamp(ms / 1000, tz=UTC) for ms in origenes_ms]
    desde = _a_media_hora(min(origenes) - timedelta(minutes=30))
    hasta = _a_media_hora(max(origenes) + timedelta(hours=1))
    return desde, hasta


def url_del_feed(origenes_ms: Sequence[int]) -> str:
    """Consulta FDSN con la caja y el umbral de P1, no con otros a mano."""
    desde, hasta = ventana_del_feed(origenes_ms)
    caja = LATAM_BBOX
    return (
        f"{USGS_FDSN_EVENT}?format=geojson"
        f"&starttime={desde.strftime('%Y-%m-%dT%H:%M:%S')}"
        f"&endtime={hasta.strftime('%Y-%m-%dT%H:%M:%S')}"
        f"&minlatitude={caja.lat_min}&maxlatitude={caja.lat_max}"
        f"&minlongitude={caja.lon_min}&maxlongitude={caja.lon_max}"
        f"&minmagnitude={MIN_MAGNITUDE}"
    )


def congelar(
    usgs_ids: Sequence[str], destino: Path, fetcher: Fetcher | None = None
) -> dict[str, str]:
    """Escribe la fixture y devuelve lo que declara `hashes.json`."""
    if not usgs_ids:
        raise ValueError("hace falta al menos un usgs_id")
    destino.mkdir(parents=True, exist_ok=True)
    fetcher = fetcher or HttpFetcher()
    varios = len(usgs_ids) > 1
    escritos: dict[str, bytes] = {}
    origenes_ms: list[int] = []
    preferidas: dict[str, dict[str, Any]] = {}

    for usgs_id in usgs_ids:
        detail = recortar_detail(fetcher.get_json(DETAIL_URL.format(usgs_id=usgs_id)))
        nombre = f"detail_{usgs_id}_superseded.json" if varios else "detail_superseded.json"
        escritos[nombre] = _json_bytes(detail)
        origenes_ms.append(int((detail.get("properties") or {})["time"]))

        # QUE ERA LA PREFERIDA AL CONGELAR, Y NO CUAL HAY QUE USAR.
        #
        # El criterio de `_preferred` ya cambio una vez —ordenar por
        # `preferredWeight` elegia un ShakeMap de hace mes y medio en
        # Venezuela— y puede volver a cambiar. Sin esta anotacion, una fixture
        # que empieza a dar otro resultado no distingue «el codigo elige otra»
        # de «USGS publico otra».
        productos = parse_products(detail)
        preferidas[usgs_id] = {
            tipo: None if ref is None else {"version": ref.version, "utc_ms": ref.actualizado_ms}
            for tipo, ref in (
                (SHAKEMAP, productos.shakemap),
                (GROUND_FAILURE, productos.ground_failure),
                (LOSSPAGER, productos.losspager),
            )
        }

        contornos = _contornos(productos.shakemap)
        if contornos is None:
            print(f"  {usgs_id}: sin {CLAVE_CONTORNOS} en el ShakeMap vigente; no se congela")
        else:
            version, url = contornos
            sufijo = f"{usgs_id}_v{version}" if varios else f"v{version}"
            escritos[f"cont_mmi_{sufijo}.json"] = fetcher.get_bytes(url)

    url_feed = url_del_feed(origenes_ms)
    escritos["feed_reconstruido.json"] = fetcher.get_bytes(url_feed)
    escritos["congelado.json"] = _json_bytes(
        {
            "usgs_ids": list(usgs_ids),
            "detail_url": DETAIL_URL,
            "feed_url": url_feed,
            "preferidas_al_congelar": preferidas,
        }
    )

    hashes = {nombre: hashlib.sha256(datos).hexdigest() for nombre, datos in escritos.items()}
    escritos["hashes.json"] = _json_bytes(hashes)
    for nombre, datos in escritos.items():
        (destino / nombre).write_bytes(datos)
        print(f"  {nombre} ({len(datos)} bytes)")
    print(f"Fixture congelada en {destino} ({len(escritos)} ficheros)")
    return hashes


def _contornos(shakemap: ProductRef | None) -> tuple[int, str] | None:
    if shakemap is None:
        return None
    url = shakemap.content_url(CLAVE_CONTORNOS)
    return None if url is None else (shakemap.version, url)


def _json_bytes(data: object) -> bytes:
    """Mismo formato que las fixtures versionadas: sangria 1, sin escapar tildes."""
    return (json.dumps(data, ensure_ascii=False, indent=1) + "\n").encode("utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("usgs_ids", nargs="+", help="identificador(es) USGS del evento")
    parser.add_argument("--out", required=True, type=Path, help="directorio destino")
    args = parser.parse_args(argv)

    congelar(args.usgs_ids, args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
