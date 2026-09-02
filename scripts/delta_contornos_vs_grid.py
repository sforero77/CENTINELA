#!/usr/bin/env python3
"""Cuanto se separa el metodo de contornos del campo continuo de `grid.xml`.

Uso::

    uv run --extra dev python scripts/delta_contornos_vs_grid.py us6000tjl2 COL

LA PREGUNTA. CENTINELA calcula la intensidad por celda rellenando entre las
isolineas de `cont_mmi.json`: cada celda toma el valor del contorno que la
contiene, o sea el **suelo** de su banda. `grid.xml` trae el campo muestreado en
una rejilla regular de ~1 km. La justificacion escrita para elegir contornos es
de rendimiento —son ordenes de magnitud menos geometria— y esa es una razon de
ingenieria, no de metodo.

PENDIENTES 2.1.sexies fijo el criterio **antes** de medir: por debajo del 3 % la
decision queda defendida con un numero; por encima es un hallazgo. Este script
es lo que produce ese numero.

QUE HACE. Replica el computo real —r8, `MMI_MIN_POLYFILL`, y el mismo umbral
`mmi_max >= X` que usa `SQL_TOTALES`— por los dos caminos, sobre el mismo activo
de exposicion, y compara los totales que el reporte publica.

Descarga ~50 MB por evento (el `grid.xml` y el activo del pais). Por eso vive
aqui y no en la suite: es una medicion que se corre cuando se cuestiona el
metodo, no en cada commit.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
import tempfile
import urllib.request

import numpy as np

RAIZ = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(RAIZ))

from pipelines.common.constants import USGS_FDSN_EVENT  # noqa: E402
from pipelines.p2_impact.pipeline import MMI_MIN_POLYFILL  # noqa: E402
from pipelines.p2_impact.shakemap import contours_to_h3, parse_contours  # noqa: E402

R8 = 8


def _urls(usgs_id: str) -> tuple[str, str, int]:
    """`(grid.xml, cont_mmi.json, version)` del ShakeMap preferido del evento."""
    detalle = json.load(
        urllib.request.urlopen(f"{USGS_FDSN_EVENT}?eventid={usgs_id}&format=geojson", timeout=60)
    )
    sm = detalle["properties"]["products"]["shakemap"][0]
    contenidos = sm["contents"]
    return (
        contenidos["download/grid.xml"]["url"],
        contenidos["download/cont_mmi.json"]["url"],
        int(sm["properties"]["version"]),
    )


def leer_grid(ruta: pathlib.Path) -> tuple[np.ndarray, float, float, float, float, int, int]:
    """`grid.xml` -> matriz MMI[ilat, ilon] y los limites de la rejilla.

    Las filas van de `lat_max` hacia abajo y de `lon_min` a la derecha. Es lo
    que declara `grid_specification`, y se comprueba contra la primera y la
    ultima fila en vez de darlo por supuesto: un reshape con el eje al reves
    daria un resultado plausible y equivocado, que es justo lo que este
    proyecto persigue.
    """
    texto = ruta.read_text(encoding="utf-8")
    spec = re.search(r"<grid_specification([^>]*)>", texto)
    if spec is None:
        raise ValueError("grid.xml sin <grid_specification>")
    attrs = dict(re.findall(r'(\w+)="([^"]+)"', spec.group(1)))
    lon_min, lon_max = float(attrs["lon_min"]), float(attrs["lon_max"])
    lat_min, lat_max = float(attrs["lat_min"]), float(attrs["lat_max"])
    nlon, nlat = int(attrs["nlon"]), int(attrs["nlat"])

    # CUANTAS COLUMNAS TRAE LA REJILLA SE PREGUNTA, NO SE SUPONE.
    #
    # Asumir diez —las que trae un ShakeMap moderno— revienta contra los
    # historicos: el de Muisne (2016, v1) trae otras, y el reshape falla con un
    # "cannot reshape array of size N". El propio fichero declara sus campos.
    campos = texto.count("<grid_field")
    columna_mmi = next(
        int(i) - 1
        for i, nombre in re.findall(r'<grid_field index="(\d+)" name="(\w+)"', texto)
        if nombre.upper() == "MMI"
    )

    inicio = texto.index("<grid_data>") + len("<grid_data>")
    datos = np.fromstring(texto[inicio : texto.index("</grid_data>")], sep=" ").reshape(-1, campos)
    if datos.shape[0] != nlon * nlat:
        raise ValueError(f"{datos.shape[0]} filas, la especificacion dice {nlon * nlat}")
    if not (
        abs(datos[0, 0] - lon_min) < 1e-6
        and abs(datos[0, 1] - lat_max) < 1e-6
        and abs(datos[-1, 0] - lon_max) < 1e-6
        and abs(datos[-1, 1] - lat_min) < 1e-6
    ):
        raise ValueError("el orden de las filas no es el que declara grid_specification")

    return datos[:, columna_mmi].reshape(nlat, nlon), lon_min, lon_max, lat_min, lat_max, nlon, nlat


def muestrear(
    mmi: np.ndarray,
    lons: np.ndarray,
    lats: np.ndarray,
    limites: tuple[float, float, float, float],
    nlon: int,
    nlat: int,
) -> np.ndarray:
    """MMI en cada `(lon, lat)` por interpolacion bilineal. NaN fuera de la rejilla."""
    lon_min, lon_max, lat_min, lat_max = limites
    fx = (lons - lon_min) / (lon_max - lon_min) * (nlon - 1)
    fy = (lat_max - lats) / (lat_max - lat_min) * (nlat - 1)  # la fila 0 es lat_max

    dentro = (fx >= 0) & (fx <= nlon - 1) & (fy >= 0) & (fy <= nlat - 1)
    salida = np.full(lons.shape, np.nan)
    x0 = np.clip(np.floor(fx[dentro]).astype(int), 0, nlon - 2)
    y0 = np.clip(np.floor(fy[dentro]).astype(int), 0, nlat - 2)
    tx, ty = fx[dentro] - x0, fy[dentro] - y0
    salida[dentro] = (
        mmi[y0, x0] * (1 - tx) * (1 - ty)
        + mmi[y0, x0 + 1] * tx * (1 - ty)
        + mmi[y0 + 1, x0] * (1 - tx) * ty
        + mmi[y0 + 1, x0 + 1] * tx * ty
    )
    return salida


def finura_del_contorno(payload: dict, valor: float) -> tuple[int, float]:
    """`(vertices, paso mediano en km)` de un nivel. El mecanismo esta aqui.

    Un contorno con paso de 4 km no puede describir estructura de 1 km, que es
    la que tiene la rejilla. `cont_mmi.json` es un producto de dibujo.
    """
    pasos, vertices = [], 0
    for f in payload["features"]:
        if f["properties"].get("value") != valor:
            continue
        geo = f["geometry"]
        lineas = geo["coordinates"] if geo["type"] == "MultiLineString" else [geo["coordinates"]]
        for linea in lineas:
            a = np.array(linea)
            vertices += len(a)
            if len(a) > 1:
                pasos.append(
                    np.hypot(
                        np.diff(a[:, 0]) * 111 * np.cos(np.radians(a[:-1, 1])),
                        np.diff(a[:, 1]) * 111,
                    )
                )
    return vertices, float(np.median(np.concatenate(pasos))) if pasos else float("nan")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("usgs_id")
    ap.add_argument("iso3", help="pais cuyo activo de exposicion se usa para el join")
    ap.add_argument("--release", default="", help="tag del Release; vacio = el mas reciente")
    args = ap.parse_args()

    import duckdb
    import h3

    with tempfile.TemporaryDirectory() as tmp:
        trabajo = pathlib.Path(tmp)
        url_grid, url_cont, version = _urls(args.usgs_id)
        print(f"{args.usgs_id} · ShakeMap v{version}")

        grid = trabajo / "grid.xml"
        cont = trabajo / "cont_mmi.json"
        urllib.request.urlretrieve(url_grid, grid)
        urllib.request.urlretrieve(url_cont, cont)

        tag = args.release or _ultimo_release(args.iso3)
        expo = trabajo / "exposure_h3.parquet"
        _descargar_activo(tag, expo)
        print(f"activo: {tag}")

        mmi, lon_min, lon_max, lat_min, lat_max, nlon, nlat = leer_grid(grid)
        paso_km = (lon_max - lon_min) / (nlon - 1) * 111
        print(f"rejilla: {nlat}x{nlon} = {mmi.size:,} puntos · {paso_km:.2f} km")

        payload = json.loads(cont.read_text(encoding="utf-8"))
        celdas_cont = contours_to_h3(
            parse_contours(payload), resolution=R8, min_value=MMI_MIN_POLYFILL
        )
        for nivel in (6.0, 7.0):
            v, paso = finura_del_contorno(payload, nivel)
            print(f"contorno MMI {nivel:.0f}: {v} vertices · paso mediano {paso:.2f} km")

        con = duckdb.connect()
        filas = con.execute(
            f"SELECT h3_08, pop_total, bld_count FROM '{expo.as_posix()}'"
        ).fetchall()
        h3s = np.fromiter((f[0] for f in filas), dtype=np.int64, count=len(filas))
        pop = np.fromiter((f[1] or 0.0 for f in filas), dtype=float, count=len(filas))
        bld = np.fromiter((f[2] or 0.0 for f in filas), dtype=float, count=len(filas))

        centros = np.array([h3.cell_to_latlng(h3.int_to_str(int(x))) for x in h3s])
        g = muestrear(
            mmi, centros[:, 1], centros[:, 0], (lon_min, lon_max, lat_min, lat_max), nlon, nlat
        )
        v = np.array(
            [celdas_cont[int(x)].mmi_max if int(x) in celdas_cont else np.nan for x in h3s]
        )
        a = np.where(np.isnan(v), 0.0, v)
        b = np.where(np.isnan(g), 0.0, g)

        print(f"\n{'umbral':>8} {'contornos (hoy)':>18} {'grid.xml':>16} {'delta':>14} {'%':>9}")
        for umbral in (6.0, 7.0):
            pa, pb = pop[a >= umbral].sum(), pop[b >= umbral].sum()
            pct = (pb - pa) / pa * 100 if pa else float("nan")
            print(f"{umbral:>8.0f} {pa:>18,.0f} {pb:>16,.0f} {pb - pa:>+14,.0f} {pct:>+8.1f}%")
        ba, bb = bld[a >= 7].sum(), bld[b >= 7].sum()
        print(
            f"{'bld>=7':>8} {ba:>18,.0f} {bb:>16,.0f} {bb - ba:>+14,.0f} "
            f"{(bb - ba) / ba * 100:>+8.1f}%"
        )

        # SIN COBERTURA vs VALOR DISTINTO. Son dos fallos muy distintos y hay que
        # poder separarlos: que el relleno pierda area seria peor que que el valor
        # difiera, y a ojo se ven igual.
        for umbral in (6.0, 7.0):
            sel = ~np.isnan(g) & (g >= umbral)
            sin = sel & np.isnan(v)
            print(f"\nceldas que la rejilla pone en MMI>={umbral:.0f}: {sel.sum():,}")
            print(
                f"  sin contorno alguno (perdida de area): {sin.sum():,} "
                f"({pop[sin].sum():,.0f} hab)"
            )
            entran = (a < umbral) & (b >= umbral)
            salen = (a >= umbral) & (b < umbral)
            print(
                f"  entran {entran.sum():,} ({pop[entran].sum():,.0f} hab) · "
                f"salen {salen.sum():,} ({pop[salen].sum():,.0f} hab)"
            )
    return 0


def _ultimo_release(iso3: str) -> str:
    import subprocess

    salida = subprocess.run(
        ["gh", "release", "list", "--limit", "200", "--json", "tagName", "-q", ".[].tagName"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    tags = [t for t in salida.split() if t.startswith(f"exposure-{iso3.lower()}-")]
    if not tags:
        raise SystemExit(f"no hay Release de exposicion para {iso3}")
    return sorted(tags)[-1]


def _descargar_activo(tag: str, destino: pathlib.Path) -> None:
    import subprocess

    subprocess.run(
        [
            "gh",
            "release",
            "download",
            tag,
            "-p",
            "exposure_h3.parquet",
            "-D",
            str(destino.parent),
            "--clobber",
        ],
        check=True,
        capture_output=True,
    )


if __name__ == "__main__":
    raise SystemExit(main())
