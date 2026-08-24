#!/usr/bin/env python3
"""Congela los productos de un evento como fixture golden (T0.2).

Uso::

    uv run --extra dev python scripts/freeze_event.py us7000sint \\
        --out tests/fixtures/golden/choco_2026_08_10

Descarga el feed detail y **todas** las versiones de ShakeMap y Ground Failure
del evento, y las guarda con su hash. Las fixtures congeladas se versionan: son
la unica forma de que el sistema pueda decir "esto habria salido a las 08:3X"
del 10 de agosto.

Nota sobre versiones superadas: ComCat expone las versiones anteriores de un
producto solo si se piden explicitamente (``includesuperseded``, disponible via
``libcomcat``). Sin ellas no se puede reconstruir la secuencia v1 → v2 → v3 que
los golden tests necesitan para verificar el changelog de RF-04.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from pipelines.common.http import HttpFetcher
from pipelines.p2_impact.products import parse_products

DETAIL_URL = "https://earthquake.usgs.gov/fdsnws/event/1/query?eventid={usgs_id}&format=geojson"


def congelar(usgs_id: str, destino: Path) -> None:
    """Descarga y guarda el detail y los contenidos de sus productos."""
    destino.mkdir(parents=True, exist_ok=True)
    fetcher = HttpFetcher()

    detail = fetcher.get_json(DETAIL_URL.format(usgs_id=usgs_id))
    _guardar_json(destino / "detail.json", detail)

    productos = parse_products(detail)
    hashes: dict[str, str] = {}

    for producto in (productos.shakemap, productos.ground_failure, productos.losspager):
        if producto is None:
            continue
        carpeta = destino / f"{producto.tipo}_v{producto.version}"
        carpeta.mkdir(exist_ok=True)
        for nombre, url in producto.contents.items():
            archivo = carpeta / Path(nombre).name
            datos = fetcher.get_bytes(url)
            archivo.write_bytes(datos)
            hashes[str(archivo.relative_to(destino))] = hashlib.sha256(datos).hexdigest()
            print(f"  {archivo.relative_to(destino)} ({len(datos)} bytes)")

    _guardar_json(destino / "hashes.json", hashes)
    print(f"Fixture congelada en {destino} ({len(hashes)} archivos)")


def _guardar_json(path: Path, data: object) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("usgs_id", help="identificador USGS del evento")
    parser.add_argument("--out", required=True, type=Path, help="directorio destino")
    args = parser.parse_args()

    congelar(args.usgs_id, args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
