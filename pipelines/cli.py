"""Interfaz de linea de comandos de CENTINELA.

Los workflows de GitHub Actions no contienen logica: llaman a estos
subcomandos. Asi el sistema se puede correr y depurar completo en local, que es
lo que hace `make country` posible (O4).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .common.http import HttpFetcher
from .common.logging import get_logger
from .common.manifest import Manifest, lint_manifest_file
from .common.paths import BUILD_DIR, MANIFESTS_DIR
from .common.state import EventState
from .common.status import write_status
from .p0_exposure.build import build_country
from .p1_trigger.run import run_trigger
from .p2_impact.run import run_impact

_log = get_logger("centinela.cli")


def _cmd_trigger(args: argparse.Namespace) -> int:
    """P1: revisa el feed y reporta que eventos despachar."""
    result = run_trigger(HttpFetcher(), dry_run=args.dry_run)
    payload = {
        "nuevos": result.nuevos,
        "revisitados": result.revisitados,
        "a_despachar": result.a_despachar,
        "revisados": result.revisados,
        "latido_utc": result.latido_utc,
    }
    print(json.dumps(payload, ensure_ascii=False))
    _emit_github_output("eventos", json.dumps(result.a_despachar))
    _emit_github_output("hay_trabajo", "true" if result.a_despachar else "false")

    # El latido alimenta /status. Se escribe siempre, tambien cuando no hay
    # eventos: la ausencia de latidos es la senal de que el cron se desactivo,
    # que es el modo de falla mas probable de todo el sistema.
    write_status(
        latido={
            "utc": result.latido_utc,
            "revisados": result.revisados,
            "relevantes": result.relevantes,
        }
    )
    return 0


def _cmd_impact(args: argparse.Namespace) -> int:
    """P2/P3: procesa un evento ya detectado y publica su reporte."""
    decision = run_impact(
        args.usgs_id,
        HttpFetcher(timeout_s=300.0),
        detail_url=args.detail_url,
        exposure_glob=args.exposure,
        manifest_id=args.manifest,
        backtest=args.backtest,
        forzar=args.reprocesar,
    )
    print(json.dumps({"accion": decision.action.value, "razon": decision.razon}))
    _emit_github_output("accion", decision.action.value)
    return 0


def _cmd_country(args: argparse.Namespace) -> int:
    """P0: reconstruye el activo de exposicion de un pais."""
    out = build_country(args.iso3, out_dir=Path(args.out or BUILD_DIR))
    print(out)
    return 0


def _cmd_lint_manifests(args: argparse.Namespace) -> int:
    """Lint de licencias y vintages sobre todos los manifests (§2.4, CI)."""
    directory = Path(args.dir or MANIFESTS_DIR)
    archivos = sorted(directory.glob("*.yaml"))
    if not archivos:
        print(f"No hay manifests en {directory}", file=sys.stderr)
        return 1

    fallo = False
    for path in archivos:
        problemas = lint_manifest_file(path)
        errores = [p for p in problemas if "(aviso)" not in p]
        avisos = [p for p in problemas if "(aviso)" in p]
        estado = "FALLA" if errores else "ok"
        cubo = Manifest.load(path.stem, directory).bucket.value if not errores else "?"
        print(f"{path.name}: {estado} (cubo {cubo})")
        for problema in errores:
            print(f"  ERROR {problema}")
        for aviso in avisos:
            print(f"  aviso {aviso}")
        fallo = fallo or bool(errores)
    return 1 if fallo else 0


def _cmd_status(args: argparse.Namespace) -> int:
    """Recalcula la pagina de estado a partir de los event_state en disco."""
    path = write_status()
    print(path)
    return 0


def _cmd_reindexar(args: argparse.Namespace) -> int:
    """Rehace `reports/index.json` desde los reportes en disco.

    Existe por un conflicto real: dos eventos publicados a la vez —el caso de
    G2, dos mainshocks separados por 33 segundos— chocan en este fichero al
    empujar a la misma rama. Fusionarlo linea a linea no tiene sentido porque es
    un **derivado**: la verdad son los `report.json` del directorio. Se
    regenera y se sigue.
    """
    from .p3_report.run import rebuild_index

    print(rebuild_index(Path(args.reports) if args.reports else None))
    return 0


def _cmd_calibrar(args: argparse.Namespace) -> int:
    """Reajusta la tolerancia de los manifests con lo que midio el ultimo build.

    Estrechar es automatico; ensanchar no. Una tolerancia que se ensancha sola
    para acomodar lo que salio deja de ser un guardian y pasa a ser un sello.
    """
    from datetime import UTC, datetime

    from .common.manifest import Manifest
    from .common.paths import MANIFESTS_DIR
    from .p0_exposure.calibrar import aplicar, calibrar, leer_medicion

    fecha = datetime.now(UTC).date().isoformat()
    salida: list[dict[str, Any]] = []
    bloqueadas = 0

    for ruta in (Path(p) for p in args.medicion):
        medicion = leer_medicion(ruta)
        iso3 = str(medicion.get("iso3", ""))
        manifest = Manifest.load(iso3, Path(args.manifests) if args.manifests else None)
        cal = calibrar(medicion, manifest.referencia_oficial)
        escrito = False
        if args.escribir:
            destino = (Path(args.manifests) if args.manifests else MANIFESTS_DIR) / f"{iso3}.yaml"
            escrito = aplicar(destino, cal, fecha=fecha)
        if cal.motivo_bloqueo:
            bloqueadas += 1
        salida.append(
            {
                "iso3": cal.iso3,
                "medido": round(cal.medido),
                "referencia": round(cal.referencia),
                "desvio_pct": cal.desvio_pct,
                "tolerancia_vigente": cal.tolerancia_vigente,
                "tolerancia_propuesta": cal.tolerancia_propuesta,
                "aplicable": cal.aplicable,
                "motivo_bloqueo": cal.motivo_bloqueo,
                "escrito": escrito,
            }
        )

    print(json.dumps(salida, ensure_ascii=False, indent=2))
    if not args.escribir:
        print("(simulacion: nada escrito. Anade --escribir)", file=sys.stderr)
    # Una calibracion bloqueada no es un fallo del comando: es informacion que
    # alguien tiene que mirar. Se distingue con codigo 2 para que un workflow
    # pueda pararse sin confundirlo con un error.
    return 2 if bloqueadas else 0


def _cmd_paises(args: argparse.Namespace) -> int:
    """Paises cuyo activo podria servir para un evento ya detectado.

    Existe porque P1 vigila **toda** la ventana LATAM y el activo es por pais:
    sin esto, el workflow de impacto bajaba siempre el de Colombia y un sismo en
    Peru se calculaba contra celdas colombianas, publicando ceros.

    Imprime los ISO3 candidatos separados por espacio, del pais mas ajustado al
    mas amplio. Varias cajas se solapan, asi que puede devolver mas de uno: el
    llamador prueba en ese orden y el join contra las celdas H3 desempata.
    """
    from .p0_exposure.download import countries_for_point

    state = EventState.load(args.usgs_id, Path(args.events_dir) if args.events_dir else None)
    if state is not None:
        lon, lat = state.lon, state.lat
    elif args.detail_url:
        # Un historico no tiene estado hasta que P2 lo reconstruye, y en el
        # workflow esta pregunta va **antes** de P2: hay que saber que activo
        # bajar para poder correrlo. La respuesta es geografica, asi que el
        # epicentro del detail sirve igual de bien que el estado.
        detalle = HttpFetcher(timeout_s=60.0).get_json(args.detail_url)
        lon, lat = (float(c) for c in detalle["geometry"]["coordinates"][:2])
    else:
        print(
            f"No existe event_state para {args.usgs_id}. Si es un historico que P1 "
            f"nunca vio, pasa --detail-url para sacar el epicentro del feed.",
            file=sys.stderr,
        )
        return 1

    candidatos = countries_for_point(lon, lat)
    if not candidatos:
        print(
            f"El epicentro de {args.usgs_id} ({lon}, {lat}) no cae en "
            f"ningun pais con caja declarada. Puede ser mar abierto o un pais que "
            f"el sistema todavia no cubre; anadelo a COUNTRY_BBOX.",
            file=sys.stderr,
        )
        return 1

    print(" ".join(candidatos))
    _emit_github_output("paises", " ".join(candidatos))
    _emit_github_output("pais", candidatos[0])
    return 0


def _emit_github_output(key: str, value: str) -> None:
    """Escribe en ``$GITHUB_OUTPUT`` si el runner lo expone."""
    import os

    path = os.environ.get("GITHUB_OUTPUT")
    if not path:
        return
    with Path(path).open("a", encoding="utf-8") as fh:
        fh.write(f"{key}={value}\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="centinela", description=__doc__)
    sub = parser.add_subparsers(dest="comando", required=True)

    p_trigger = sub.add_parser("trigger", help="P1: vigila el feed USGS")
    p_trigger.add_argument("--dry-run", action="store_true", help="no escribe event_state")
    p_trigger.set_defaults(func=_cmd_trigger)

    p_impact = sub.add_parser("impact", help="P2: procesa un evento")
    p_impact.add_argument("usgs_id")
    p_impact.add_argument("--detail-url", required=True, help="URL del feed detail del evento")
    p_impact.add_argument(
        "--exposure",
        required=True,
        help="ruta o glob del activo de exposicion (GeoParquet)",
    )
    p_impact.add_argument(
        "--manifest",
        default="",
        help="id del manifest con el que se construyo el activo",
    )
    p_impact.add_argument(
        "--backtest",
        action="store_true",
        help=(
            "evento historico que P1 nunca vio: reconstruye su estado desde el "
            "detail y lo marca como retrospectivo (queda fuera de la latencia)"
        ),
    )
    p_impact.add_argument(
        "--reprocesar",
        action="store_true",
        help=(
            "reemite el reporte aunque USGS no haya publicado nada nuevo; para "
            "cuando lo que cambio es el pipeline y no los productos"
        ),
    )
    p_impact.set_defaults(func=_cmd_impact)

    p_country = sub.add_parser("country", help="P0: construye exposure_h3 de un pais")
    p_country.add_argument("iso3")
    p_country.add_argument("--out", help="directorio de salida")
    p_country.set_defaults(func=_cmd_country)

    p_lint = sub.add_parser("lint-manifests", help="valida licencias y vintages")
    p_lint.add_argument("--dir", help="directorio de manifests")
    p_lint.set_defaults(func=_cmd_lint_manifests)

    p_status = sub.add_parser("status", help="recalcula site/status.json")
    p_status.set_defaults(func=_cmd_status)

    p_reindexar = sub.add_parser(
        "reindexar", help="rehace reports/index.json desde los reportes en disco"
    )
    p_reindexar.add_argument("--reports", help="raiz de reports/")
    p_reindexar.set_defaults(func=_cmd_reindexar)

    p_calibrar = sub.add_parser(
        "calibrar", help="reajusta la tolerancia de los manifests con lo medido"
    )
    p_calibrar.add_argument("medicion", nargs="+", help="ficheros medicion.json de los Releases")
    p_calibrar.add_argument(
        "--escribir", action="store_true", help="escribe los manifests (por defecto simula)"
    )
    p_calibrar.add_argument("--manifests", help="directorio de manifests")
    p_calibrar.set_defaults(func=_cmd_calibrar)

    p_paises = sub.add_parser(
        "paises-candidatos", help="ISO3 cuyo activo podria servir para un evento"
    )
    p_paises.add_argument(
        "--detail-url",
        default="",
        help="feed detail del evento; se usa si aun no existe su event_state",
    )
    p_paises.add_argument("usgs_id")
    p_paises.add_argument("--events-dir", help="directorio de event_state")
    p_paises.set_defaults(func=_cmd_paises)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        exit_code: int = args.func(args)
        return exit_code
    except NotImplementedError as exc:
        _log.error("etapa pendiente", extra={"context": {"detalle": str(exc)}})
        print(f"PENDIENTE: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
