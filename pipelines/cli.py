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

from .common.http import HttpFetcher
from .common.logging import get_logger
from .common.manifest import Manifest, lint_manifest_file
from .common.paths import BUILD_DIR, MANIFESTS_DIR
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
