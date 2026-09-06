"""Recorta el activo de un pais a las celdas que toca un ShakeMap congelado.

EXISTE PARA QUE EL GOLDEN PUEDA RECALCULAR.

`tests/golden/` no recalculaba nada: `_reporte_publicado()` abre un JSON
versionado y comprueba que sigue diciendo lo que decia. Contando llamadas
durante la suite completa, `build_report` y `run_impact` tenian **cero**. La
costura `compute_impact -> ImpactTotals -> Report -> to_dict -> report.json` no
la atravesaba ninguna prueba, y por ahi se colaron las siete columnas de la
banda MMI>=6 que nunca llegaban al JSON.

Lo que faltaba era el insumo: el activo de Colombia son 559.103 celdas y 31 MB,
demasiado para versionar. Pero el ShakeMap del Choco solo toca una fraccion, y
esa fraccion cabe. El `.gitignore` ya tenia reservada la excepcion
`!tests/fixtures/**/*.parquet` y no se habia usado nunca.

    uv run --extra geo python scripts/fixture_golden.py \\
        --contornos tests/fixtures/golden/choco_2026_08_10/cont_mmi_v7.json \\
        --activo data/activos/col/exposure_h3.parquet \\
        --salida tests/fixtures/golden/choco_2026_08_10/exposure_recortado.parquet

**Hay que volver a correrlo cuando se reconstruya el activo del pais.** El
golden fija las cifras que salen de ESTE recorte; si el activo cambia —y va a
cambiar, porque los diecinueve publicados se construyeron con el orden de
coordenadas invertido— las cifras se mueven y la prueba lo dira. Regenerar la
fixture es entonces la respuesta correcta, y tiene que costar un comando.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

RAIZ = Path(__file__).resolve().parent.parent


def celdas_del_shakemap(contornos: Path) -> list[int]:
    """Los indices H3 r8 que el ShakeMap rellena, con el mismo corte que P2."""
    from pipelines.p2_impact.pipeline import MMI_MIN_POLYFILL
    from pipelines.p2_impact.shakemap import contours_to_h3, parse_contours

    leidos = parse_contours(json.loads(contornos.read_text(encoding="utf-8")))
    return [int(h) for h in contours_to_h3(leidos, min_value=MMI_MIN_POLYFILL)]


def recortar(con: Any, activo: Path, celdas: list[int], salida: Path) -> int:
    """Escribe las filas del activo cuya celda toca el ShakeMap."""
    con.execute("CREATE OR REPLACE TABLE _tocadas (h3_08 UBIGINT)")
    con.executemany("INSERT INTO _tocadas VALUES (?)", [(c,) for c in celdas])
    salida.parent.mkdir(parents=True, exist_ok=True)
    con.execute(
        f"""
        COPY (
            SELECT e.* FROM read_parquet('{activo.as_posix()}') e
            SEMI JOIN _tocadas USING (h3_08)
        ) TO '{salida.as_posix()}' (FORMAT PARQUET, COMPRESSION ZSTD)
        """
    )
    filas: int = con.execute(
        f"SELECT count(*) FROM read_parquet('{salida.as_posix()}')"
    ).fetchone()[0]
    return filas


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contornos", type=Path, required=True)
    parser.add_argument("--activo", type=Path, required=True)
    parser.add_argument("--salida", type=Path, required=True)
    args = parser.parse_args(argv)

    from pipelines.p2_impact.exposure_join import connect

    celdas = celdas_del_shakemap(args.contornos)
    con = connect()
    filas = recortar(con, args.activo, celdas, args.salida)
    tamano = args.salida.stat().st_size

    print(
        json.dumps(
            {
                "celdas_del_shakemap": len(celdas),
                "filas_del_recorte": filas,
                "bytes": tamano,
                "salida": str(args.salida),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
