#!/usr/bin/env python3
"""Simulacro: un sismo que SI alcanza poblacion, contra el pipeline de verdad.

Uso::

    uv run --extra geo --extra render python scripts/simulacro_sismo.py \\
        --sobre 3.4516,-76.5320 --iso3 COL

Por que existe
--------------

`docs/GARANTIAS.md` dice que lo unico que sigue sin ejercitarse es un evento en
vivo que **alcance poblacion** —los dos del 2-sep se quedaron mar adentro y sus
tablas salieron en ceros— y cierra con "no se puede ensayar".

Si se puede. Lo que hace falta no es un sismo: es un ShakeMap que caiga sobre
gente. Este script coge el ShakeMap **real** de un evento ya congelado y lo
**muda** al punto que se le indique. La geometria de las isolineas es de USGS;
lo unico sintetico es donde cae.

Con eso corre `run_impact` de verdad —descarga HTTP incluida, contra un
servidor local— contra el activo de exposicion real del pais, y escribe el
paquete completo: `report.json`, `adm2.csv`, los dos PNG, el hilo, el markdown
y su indice.

Que NO ensaya
-------------

* **P1.** El vigia no ve este evento: no esta en el feed de USGS. Esa mitad de
  la cadena la cubren el simulacro mensual (`--dry-run` contra el feed vivo) y
  los dos eventos reales del 2-sep, que P1 detecto y despacho solo.
* **La fisica.** Trasladar un ShakeMap no es modelarlo. Las cifras que salgan
  son las de *ese* campo de sacudida puesto en otro sitio; no afirman nada
  sobre lo que pasaria si un sismo asi ocurriera ahi. Para eso hace falta un
  modelo de atenuacion y un mapa de suelos, que es otro proyecto.

Lo que si mide, y es lo que no estaba medido: que el join contra el activo, el
ranking municipal, el CSV con sus etiquetas HXL, los mapas, el changelog y la
validacion contra el esquema aguantan **cifras grandes de verdad**, no ceros.

Donde escribe
-------------

En un directorio aparte, nunca en `events/` ni en `reports/` del repositorio.
El guardarrail es una comprobacion explicita y no una convencion: un reporte de
un terremoto que no ocurrio, dentro de la carpeta que publica el sitio, es el
peor fallo imaginable de este proyecto. Lo respalda
`tests/unit/test_ningun_simulacro_publicado.py`, que revienta si un id de
simulacro aparece en `events/`, en `reports/` o en el indice.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from datetime import UTC, datetime
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from typing import Any

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

# Toribio, Jambalo, Guacheni: los nombres llevan tilde y la consola de Windows
# los sirve en cp1252. Sin esto la tabla del simulacro sale con rombos.
if hasattr(sys.stdout, "reconfigure"):  # pragma: no cover - depende de la consola
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from pipelines.common.http import HttpFetcher  # noqa: E402
from pipelines.common.paths import EVENTS_DIR, REPORTS_DIR  # noqa: E402
from pipelines.p2_impact.run import run_impact  # noqa: E402

#: Prefijo obligatorio del id. Lo comparten el guardarrail de este script y la
#: prueba que vigila el repositorio: si cambia aqui, cambia alli.
PREFIJO_SIMULACRO = "simulacro"

#: Fuente por defecto: el Choco M7,4, la fixture golden que ya vive en el repo.
#: Se elige porque su ShakeMap esta congelado (no hace falta red para el campo
#: de sacudida) y porque alcanza MMI 7 sobre area metropolitana, que es
#: exactamente el caso que nunca se ha ejercitado en vivo.
FUENTE_POR_DEFECTO = RAIZ / "tests" / "fixtures" / "golden" / "choco_2026_08_10"


class _Silencioso(SimpleHTTPRequestHandler):
    """Servidor de archivos sin una linea de log por peticion."""

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        del format, args


def _servir(directorio: Path) -> tuple[ThreadingHTTPServer, str]:
    """Levanta un servidor local sobre `directorio` y devuelve su base URL.

    Se usa un servidor de verdad, y no `FixtureFetcher`, a proposito: la ruta
    con fixtures ya la ejercitan los golden tests. Lo que este simulacro quiere
    medir es la cadena real, y ahi `HttpFetcher` y `download_products` son dos
    eslabones que no conviene saltarse.

    Puerto 0: lo elige el sistema, asi que dos simulacros a la vez no chocan.
    """
    handler = partial(_Silencioso, directory=str(directorio))
    servidor = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    Thread(target=servidor.serve_forever, daemon=True).start()
    return servidor, f"http://127.0.0.1:{servidor.server_address[1]}"


def _factor_longitud(lat_origen: float, lat_destino: float) -> float:
    """Estiramiento de las longitudes que conserva la distancia en el terreno.

    Un grado de longitud mide `cos(lat)` veces lo que uno de latitud. Mudar el
    ShakeMap sumando grados a secas encogeria o estiraria su huella segun la
    latitud de destino. Entre Choco (4,8 N) y Cali (3,4 N) el error es del 0,2 %
    y daria igual; entre el Caribe y Tierra del Fuego, no.
    """
    coseno_destino = math.cos(math.radians(lat_destino))
    if abs(coseno_destino) < 1e-9:  # polo: no aplica a LATAM, pero no se divide por cero
        return 1.0
    return math.cos(math.radians(lat_origen)) / coseno_destino


def _mudar(coords: Any, origen: tuple[float, float], destino: tuple[float, float]) -> Any:
    """Traslada recursivamente cualquier anidamiento de coordenadas GeoJSON.

    `origen` y `destino` son `(lon, lat)`. Las isolineas de `cont_mmi.json`
    llegan como `MultiLineString`, o sea tres niveles de lista, pero la funcion
    no depende de eso.
    """
    if coords and isinstance(coords[0], int | float):
        factor = _factor_longitud(origen[1], destino[1])
        lon, lat = float(coords[0]), float(coords[1])
        return [destino[0] + (lon - origen[0]) * factor, destino[1] + (lat - origen[1])]
    return [_mudar(hijo, origen, destino) for hijo in coords]


def _bbox(payload: dict[str, Any]) -> list[float]:
    """Caja envolvente de todas las coordenadas, para no dejarla obsoleta."""
    lons: list[float] = []
    lats: list[float] = []

    def recorrer(coords: Any) -> None:
        if coords and isinstance(coords[0], int | float):
            lons.append(float(coords[0]))
            lats.append(float(coords[1]))
            return
        for hijo in coords:
            recorrer(hijo)

    for feature in payload.get("features", []):
        recorrer(feature["geometry"]["coordinates"])
    return [min(lons), min(lats), max(lons), max(lats)]


def _cargar_fuente(directorio: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    """Devuelve `(cont_mmi, detail)` de una fixture golden congelada."""
    contornos = sorted(directorio.glob("cont_mmi*.json"))
    if not contornos:
        raise SystemExit(f"No hay cont_mmi*.json en {directorio}")
    detalles = sorted(directorio.glob("detail*.json"))
    if not detalles:
        raise SystemExit(f"No hay detail*.json en {directorio}")
    return (
        json.loads(contornos[-1].read_text(encoding="utf-8")),
        json.loads(detalles[-1].read_text(encoding="utf-8")),
    )


def _detail_simulado(
    *,
    usgs_id: str,
    fuente: dict[str, Any],
    destino: tuple[float, float],
    base_url: str,
    lugar: str,
) -> dict[str, Any]:
    """Arma el `detail` que P2 va a leer, con la forma exacta del de USGS.

    Solo se declara el producto `shakemap`. `ground-failure` y `losspager` son
    opcionales por contrato (`ProductSet` los tiene como `| None`, y el golden
    G3 cubre su ausencia), y fabricarlos exigiria inventar rasters: eso si
    seria simular, no mudar.
    """
    props_fuente: dict[str, Any] = fuente["properties"]
    profundidad = float(fuente["geometry"]["coordinates"][2])
    ahora_ms = int(time.time() * 1000)

    return {
        "type": "Feature",
        "id": usgs_id,
        "geometry": {"type": "Point", "coordinates": [destino[0], destino[1], profundidad]},
        "properties": {
            "mag": props_fuente["mag"],
            "place": lugar,
            "time": ahora_ms,
            "updated": ahora_ms,
            "status": "reviewed",
            "net": "si",
            "code": usgs_id,
            "type": "earthquake",
            "title": f"SIMULACRO M {props_fuente['mag']} - {lugar}",
            "magType": props_fuente.get("magType", "mww"),
            "tsunami": 0,
            "products": {
                "shakemap": [
                    {
                        "type": "shakemap",
                        "code": usgs_id,
                        "source": "si",
                        "status": "UPDATE",
                        "preferredWeight": 231,
                        "updateTime": ahora_ms,
                        "properties": {
                            "version": "1",
                            "event-type": "SIMULACRO",
                            "latitude": str(destino[1]),
                            "longitude": str(destino[0]),
                            "magnitude": str(props_fuente["mag"]),
                            "depth": str(profundidad),
                        },
                        "contents": {
                            "download/cont_mmi.json": {
                                "contentType": "application/json",
                                "url": f"{base_url}/cont_mmi.json",
                            }
                        },
                    }
                ]
            },
        },
    }


def _comprobar_salida(salida: Path) -> None:
    """Se niega a correr si el simulacro pudiera tocar el estado publicado.

    No es paranoia: `run_impact` escribe `event_state`, el paquete del reporte
    **y reconstruye `index.json`**, que es lo que lee el visor. Un descuido en
    el `--salida` no puede terminar con un terremoto inventado en la pagina.
    """
    resuelta = salida.resolve()
    for prohibida in (EVENTS_DIR.resolve(), REPORTS_DIR.resolve()):
        if resuelta == prohibida or prohibida in resuelta.parents or resuelta in prohibida.parents:
            raise SystemExit(
                f"--salida no puede estar dentro ni por encima de {prohibida}: "
                f"un simulacro nunca escribe donde se publica."
            )


def _escribir_marca(salida: Path, *, usgs_id: str, origen: str, sobre: str) -> None:
    """Deja en el directorio un aviso de que nada de esto ocurrio.

    El paquete que sale de aqui es indistinguible de uno real en formato: mismo
    `report.json`, mismo CSV con etiquetas HXL, mismo `hilo.txt` listo para
    pegar en una red social. El id empieza por `simulacro-` y eso viaja dentro
    del markdown, pero un PNG suelto o un CSV reenviado pierden ese contexto.
    Esta nota viaja con la carpeta.
    """
    salida.mkdir(parents=True, exist_ok=True)
    (salida / "LEEME-SIMULACRO.md").write_text(
        f"""# ESTO NO OCURRIO

Paquete de un **simulacro** de CENTINELA, generado por `scripts/simulacro_sismo.py`.

- **Id:** `{usgs_id}`
- **Generado:** {datetime.now(UTC).isoformat(timespec="seconds")}
- **ShakeMap:** el real de `{origen}`, **trasladado** a `{sobre}`.

No hubo ningun sismo en ese punto. Las cifras son el cruce del activo de
exposicion real contra un campo de sacudida mudado de sitio: sirven para
comprobar que el pipeline responde, **no** para informar a nadie de nada.

No publiques estos archivos. No los subas a `reports/`. El `hilo.txt` de esta
carpeta esta escrito para pegarse en una red social y dice "Sismo M7,4": fuera
de esta carpeta, eso es desinformacion sobre una emergencia.
""",
        encoding="utf-8",
    )


def _punto(texto: str) -> tuple[float, float]:
    """Lee `lat,lon` y devuelve `(lon, lat)`, que es el orden de GeoJSON."""
    try:
        lat, lon = (float(p) for p in texto.split(","))
    except ValueError:
        raise SystemExit(f"--sobre espera 'lat,lon'; llego {texto!r}") from None
    if not -90 <= lat <= 90 or not -180 <= lon <= 180:
        raise SystemExit(f"--sobre fuera de rango: {texto!r}")
    return lon, lat


def _miles(valor: float) -> str:
    return f"{valor:,.0f}".replace(",", ".")


def _imprimir_resumen(reporte: Path, segundos: float) -> None:
    datos = json.loads(reporte.read_text(encoding="utf-8"))
    total = datos["totales"]
    evento = datos["event"]

    print()
    print(f"  SIMULACRO  M{evento['mag']}  {evento['lugar']}")
    print(f"  epicentro {evento['lat']:.4f}, {evento['lon']:.4f} · prof. {evento['depth_km']} km")
    print(f"  ShakeMap v{datos['inputs']['shakemap_version']} · {segundos:.1f} s de computo")
    print()
    print(f"  Poblacion en MMI>=6 ....... {_miles(total['pop_mmi6p']):>15}")
    print(f"  Poblacion en MMI>=7 ....... {_miles(total['pop_mmi7p']):>15}")
    print(f"  Mayores de 65 en MMI>=7 ... {_miles(total['pop_65p_mmi7p']):>15}")
    print(f"  Edificaciones en MMI>=6 ... {_miles(total['bld_mmi6p']):>15}")
    print(f"  Salud en MMI>=6 ........... {_miles(total['health_mmi6p']):>15}")
    print(f"  Educacion en MMI>=6 ....... {_miles(total['edu_mmi6p']):>15}")
    print(f"  Vias km en MMI>=6 ......... {_miles(total['road_km_mmi6p']):>15}")
    print()
    print("  Municipios mas expuestos")
    for fila in datos["top_municipios"][:10]:
        print(
            f"    {fila['nombre'][:34]:<34} MMI {fila['mmi_max']:>4} "
            f"{_miles(fila['pop_banda']):>14}"
        )
    print()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Ensaya P2->P3 con un ShakeMap real mudado sobre poblacion.",
    )
    parser.add_argument(
        "--sobre",
        required=True,
        metavar="LAT,LON",
        help="donde cae el epicentro del simulacro, p. ej. 3.4516,-76.5320 (Cali)",
    )
    parser.add_argument("--iso3", default="COL", help="pais del activo de exposicion")
    parser.add_argument(
        "--fuente",
        type=Path,
        default=FUENTE_POR_DEFECTO,
        help="fixture golden de la que se toma el ShakeMap real",
    )
    parser.add_argument("--activo", help="ruta del exposure_h3.parquet; por defecto, el de --iso3")
    parser.add_argument(
        "--admin-lookup", help="diccionario municipal; por defecto, junto al activo"
    )
    parser.add_argument(
        "--salida",
        type=Path,
        help="directorio del simulacro; por defecto work/simulacro/<id>",
    )
    parser.add_argument("--lugar", default="", help="texto del lugar; por defecto, las coordenadas")
    parser.add_argument(
        "--exigir-poblacion",
        type=int,
        default=0,
        metavar="N",
        help=(
            "falla si el simulacro no alcanza N personas en MMI>=6. Es lo que "
            "convierte el ensayo en una comprobacion: un simulacro que sale en "
            "ceros no ensayo nada, y es justo el caso que ya se daba solo"
        ),
    )
    args = parser.parse_args()

    destino = _punto(args.sobre)
    sello = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    usgs_id = f"{PREFIJO_SIMULACRO}-{sello}"
    salida = args.salida or (RAIZ / "work" / "simulacro" / usgs_id)
    _comprobar_salida(salida)

    por_defecto = RAIZ / "data" / "activos" / args.iso3.lower() / "exposure_h3.parquet"
    activo = args.activo or str(por_defecto)
    if not Path(activo).exists():
        raise SystemExit(
            f"No existe el activo {activo}. Construyelo con `make country ISO={args.iso3}` "
            f"o bajalo del Release exposure-{args.iso3.lower()}-<fecha>."
        )

    contornos, detail_fuente = _cargar_fuente(args.fuente)
    origen = (
        float(detail_fuente["geometry"]["coordinates"][0]),
        float(detail_fuente["geometry"]["coordinates"][1]),
    )

    for feature in contornos.get("features", []):
        feature["geometry"]["coordinates"] = _mudar(
            feature["geometry"]["coordinates"], origen, destino
        )
    contornos["bbox"] = _bbox(contornos)
    # El archivo queda marcado por dentro. Si alguien lo encuentra suelto en un
    # disco dentro de seis meses, tiene que poder saber que no es de USGS.
    contornos["metadata"] = {
        "simulacro": True,
        "origen_real": detail_fuente["id"],
        "mudado_a": [destino[1], destino[0]],
        "advertencia": "Geometria real de USGS trasladada. No es un ShakeMap de este lugar.",
    }

    lugar = args.lugar or f"SIMULACRO - {destino[1]:.4f}, {destino[0]:.4f}"
    servidor_dir = salida / "productos"
    servidor_dir.mkdir(parents=True, exist_ok=True)
    (servidor_dir / "cont_mmi.json").write_text(
        json.dumps(contornos, ensure_ascii=False), encoding="utf-8"
    )

    _escribir_marca(salida, usgs_id=usgs_id, origen=detail_fuente["id"], sobre=args.sobre)

    servidor, base_url = _servir(servidor_dir)
    try:
        detail = _detail_simulado(
            usgs_id=usgs_id,
            fuente=detail_fuente,
            destino=destino,
            base_url=base_url,
            lugar=lugar,
        )
        (servidor_dir / "detail.json").write_text(
            json.dumps(detail, ensure_ascii=False), encoding="utf-8"
        )

        print(f"  simulacro {usgs_id}")
        print(f"  ShakeMap real de {detail_fuente['id']} mudado a {args.sobre}")
        print(f"  activo: {activo}")
        print(f"  salida: {salida}")
        print("  calculando...")

        inicio = time.monotonic()
        decision = run_impact(
            usgs_id,
            HttpFetcher(timeout_s=120.0),
            detail_url=f"{base_url}/detail.json",
            exposure_glob=activo,
            events_dir=salida / "events",
            reports_root=salida / "reports",
            workdir=salida / "work",
            admin_lookup_parquet=args.admin_lookup,
            backtest=True,
        )
        segundos = time.monotonic() - inicio
    finally:
        servidor.shutdown()

    reporte = salida / "reports" / usgs_id / "report.json"
    if not reporte.exists():
        print(f"  decision: {decision.action.value} — {decision.razon}")
        print("  no se escribio reporte: el simulacro NO paso.")
        return 1

    _imprimir_resumen(reporte, segundos)
    artefactos = sorted(p.name for p in (salida / "reports" / usgs_id).iterdir())
    print(f"  artefactos: {', '.join(artefactos)}")
    print(f"  todo en {salida}. Borralo cuando termines: no va a ninguna parte.")

    alcanzada = json.loads(reporte.read_text(encoding="utf-8"))["totales"]["pop_mmi6p"]
    if args.exigir_poblacion and alcanzada < args.exigir_poblacion:
        print()
        print(
            f"  FALLA: se exigian {_miles(args.exigir_poblacion)} personas "
            f"en MMI>=6 y el simulacro alcanzo {_miles(alcanzada)}."
        )
        return 1
    if args.exigir_poblacion:
        print()
        print(f"  PASA: {_miles(alcanzada)} personas en MMI>=6, sobre el minimo.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
