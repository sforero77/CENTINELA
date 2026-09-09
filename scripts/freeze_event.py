#!/usr/bin/env python3
"""Congela los productos de un evento como fixture golden (T0.2).

Uso::

    uv run --extra dev python scripts/freeze_event.py us7000sint \\
        --out tests/fixtures/golden/choco_2026_08_10

Descarga el feed detail y **todas** las versiones de ShakeMap, Ground Failure y
PAGER del evento, y las guarda con su hash. Las fixtures congeladas se
versionan: son la unica forma de que el sistema pueda decir "esto habria salido
a las 08:3X" del 10 de agosto.

DECIA «TODAS» Y BAJABA UNA POR TIPO.

`parse_products` devuelve un `ProductSet` con tres `ProductRef | None`, uno por
tipo, **ya reducidos por `_preferred` a la version vigente de un solo
contribuidor**. `productos.shakemap` es un objeto, no una lista: el bucle daba
como mucho tres vueltas y creaba como mucho tres carpetas. Ningun camino del
script llegaba a la entrada `i > 0` de un tipo.

Y la secuencia es justo lo que hace falta. La nota de abajo lo dice desde el
principio —«sin ellas no se puede reconstruir la secuencia v1 -> v2 -> v3 que los
golden tests necesitan para verificar el changelog de RF-04»— y el script que la
lleva escrita era el que se quedaba con la ultima.

Ahora se recorre la lista entera de cada tipo y cada entrada va a su carpeta.
`parse_products` sigue usandose, pero solo para **anotar** cual era la preferida
en el momento de congelar: esa anotacion es parte de la fixture, porque el
criterio de preferencia puede cambiar y entonces hay que poder distinguir «el
codigo elige otra» de «USGS publico otra».

Nota sobre versiones superadas: ComCat expone las versiones anteriores de un
producto solo si se piden explicitamente (``includesuperseded``, disponible via
``libcomcat``). Este script pide el detail con ese parametro; sin el, USGS
devuelve una sola entrada por contribuidor y la secuencia no existe ni aunque se
recorra entera.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from pipelines.common.http import HttpFetcher
from pipelines.p2_impact.products import (
    GROUND_FAILURE,
    LOSSPAGER,
    SHAKEMAP,
    ProductRef,
    parse_products,
)

#: `includesuperseded` es lo que convierte «la vigente» en «la secuencia».
DETAIL_URL = (
    "https://earthquake.usgs.gov/fdsnws/event/1/query"
    "?eventid={usgs_id}&format=geojson&includesuperseded=true"
)

#: Tipos que se congelan, en el orden en que se escriben.
TIPOS: tuple[str, ...] = (SHAKEMAP, GROUND_FAILURE, LOSSPAGER)


def nombre_de_carpeta(tipo: str, entrada: dict[str, Any]) -> str:
    """Carpeta de una entrada concreta, no de un tipo.

    Lleva contribuidor, version y ``updateTime`` porque ninguno de los tres
    basta solo: en ``us20005j32`` hay dos entradas **ambas rotuladas v1** de
    contribuidores distintos, y un mismo contribuidor puede republicar la misma
    version. Con los tres, dos entradas distintas no pueden pisarse.
    """
    ref = ProductRef.from_dict(tipo, entrada)
    fuente = str(entrada.get("source", "us"))
    return f"{tipo}_{fuente}_v{ref.version}_{ref.actualizado_ms}"


def congelar(usgs_id: str, destino: Path) -> None:
    """Descarga y guarda el detail y los contenidos de **todas** sus versiones."""
    destino.mkdir(parents=True, exist_ok=True)
    fetcher = HttpFetcher()

    detail = fetcher.get_json(DETAIL_URL.format(usgs_id=usgs_id))
    _guardar_json(destino / "detail.json", detail)

    products: dict[str, Any] = (detail.get("properties") or {}).get("products") or {}
    hashes: dict[str, str] = {}
    congeladas: dict[str, list[str]] = {}

    for tipo in TIPOS:
        entradas = products.get(tipo)
        if not isinstance(entradas, list):
            continue
        congeladas[tipo] = []
        for entrada in entradas:
            if not isinstance(entrada, dict):
                continue
            carpeta = destino / nombre_de_carpeta(tipo, entrada)
            carpeta.mkdir(exist_ok=True)
            congeladas[tipo].append(carpeta.name)
            ref = ProductRef.from_dict(tipo, entrada)
            for nombre, url in ref.contents.items():
                archivo = carpeta / Path(nombre).name
                datos = fetcher.get_bytes(url)
                archivo.write_bytes(datos)
                hashes[str(archivo.relative_to(destino))] = hashlib.sha256(datos).hexdigest()
                print(f"  {archivo.relative_to(destino)} ({len(datos)} bytes)")

    # QUE ERA LA PREFERIDA AL CONGELAR, Y NO CUAL HAY QUE USAR.
    #
    # El criterio de `_preferred` ya cambio una vez —ordenar por
    # `preferredWeight` elegia un ShakeMap de hace mes y medio en Venezuela— y
    # puede volver a cambiar. Sin esta anotacion, una fixture que empieza a dar
    # otro resultado no distingue «el codigo elige otra» de «USGS publico otra».
    preferidas = parse_products(detail)
    _guardar_json(
        destino / "congelado.json",
        {
            "usgs_id": usgs_id,
            "detail_url": DETAIL_URL.format(usgs_id=usgs_id),
            "versiones": congeladas,
            "preferidas_al_congelar": {
                tipo: None
                if ref is None
                else {"version": ref.version, "utc_ms": ref.actualizado_ms}
                for tipo, ref in (
                    (SHAKEMAP, preferidas.shakemap),
                    (GROUND_FAILURE, preferidas.ground_failure),
                    (LOSSPAGER, preferidas.losspager),
                )
            },
        },
    )

    _guardar_json(destino / "hashes.json", hashes)
    cuantas = sum(len(v) for v in congeladas.values())
    print(f"Fixture congelada en {destino} ({cuantas} versiones, {len(hashes)} archivos)")


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
