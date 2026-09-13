#!/usr/bin/env python3
"""Compila cada diagrama Mermaid de la documentacion con mermaid-cli.

Uso::

    python3 scripts/validar_diagramas.py            # compila todos: red y Chromium
    python3 scripts/validar_diagramas.py --listar   # dice donde esta cada uno, sin red

Por que existe
--------------

La documentacion explica el sistema con diagramas Mermaid y GitHub los dibuja al
abrir el fichero. Uno con la sintaxis rota no rompe nada que la suite vea: se
publica como un recuadro de error justo donde tenia que estar la explicacion, y
solo se descubre abriendo esa pagina.

Leerlo no basta. El 12-sep-2026 el `timeline` nuevo de
`docs/acciones/por-reloj.md` se leia perfectamente y no compilaba: las horas
`05:37` chocaban con los dos puntos que Mermaid usa como separador. Se vio
porque se compilo a mano, y lo que depende de hacerlo a mano no se vuelve a
hacer.

La sintaxis la decide el parser de Mermaid, que corre en un navegador, asi que
esto no cabe en la suite —corre sin red y sin Chromium—. Lo corre el job
`diagramas` de `ci.yml`, en cada push y en cada PR.

Como
----

Primero todos juntos en un unico Markdown: una sola apertura de Chromium. `mmdc`
se detiene en el primer error y no dice de que bloque era, asi que si algo falla
se recompila cada diagrama por separado y se da `fichero:linea` de **todos** los
rotos, no solo del primero.

Codigos de salida
-----------------

* 0: todos compilan.
* 1: alguno no compila.
* 2: no se pudo mirar. Cero diagramas encontrados, no hay `npx`, o no compilo
  ninguno, que es el entorno y no la documentacion. No poder mirar no es estar
  en verde.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]

# Las etiquetas de los diagramas llevan tildes y la consola de Windows escribe
# en cp1252: sin esto, el mensaje de error de un diagrama roto sale con rombos.
if hasattr(sys.stdout, "reconfigure"):  # pragma: no cover - depende de la consola
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

#: Version exacta y no `@11`: con el mayor a secas `npx` resuelve lo que tenga en
#: cache o lo ultimo publicado, y el mismo commit podria compilar distinto de un
#: dia para otro. Dependabot no lee esta linea; se sube a mano.
MERMAID_CLI = "@mermaid-js/mermaid-cli@11.17.0"

#: Desde Ubuntu 23.10, AppArmor restringe los user namespaces sin privilegios, que
#: es con lo que Chromium monta su sandbox, y `ubuntu-latest` es 24.04: sin esto
#: `mmdc` puede no arrancar en el runner. Lo que se abre es Markdown de este
#: repositorio, en una maquina que se tira al terminar.
CONFIG_PUPPETEER = {"args": ["--no-sandbox"]}

#: Recompilar uno por uno solo pasa cuando algo ya fallo, pero con sesenta
#: diagramas en serie son varios minutos de Chromium abriendo y cerrando.
EN_PARALELO = 4

#: Una valla de codigo de CommonMark: tres o mas acentos graves o virgulillas,
#: con la sangria que tenga, y detras la etiqueta del lenguaje.
VALLA = re.compile(r"^[ \t]*(?P<marca>`{3,}|~{3,})[ \t]*(?P<info>[^`]*?)[ \t]*$")


@dataclass(frozen=True)
class Diagrama:
    ruta: str  # relativa a la raiz, con barras normales
    linea: int  # la de la valla que lo abre, contando desde 1
    codigo: str


def documentos() -> list[Path]:
    """Los `.md` versionados, y los nuevos que todavia no tienen commit.

    `git ls-files` y no `rglob`: el arbol de trabajo tiene `.venv/`, `work/` y
    `node_modules/`, con Markdown de terceros que no es de este repositorio.
    """
    salida = subprocess.run(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard", "--", "*.md"],
        cwd=RAIZ,
        capture_output=True,
        check=True,
    ).stdout.decode("utf-8")
    return sorted({RAIZ / p for p in salida.split("\0") if p and (RAIZ / p).is_file()})


def extraer(ruta: Path) -> list[Diagrama]:
    """Los bloques `mermaid` de un documento, leidos como los lee GitHub.

    Los demas bloques de codigo se saltan enteros: un ejemplo de Mermaid dentro
    de un bloque `markdown` es texto, no un diagrama, y GitHub no lo dibuja.
    """
    relativa = ruta.relative_to(RAIZ).as_posix()
    lineas = ruta.read_text(encoding="utf-8").splitlines()
    diagramas: list[Diagrama] = []
    i = 0
    while i < len(lineas):
        apertura = VALLA.match(lineas[i])
        if apertura is None:
            i += 1
            continue
        marca = apertura["marca"]
        cierre = next(
            (
                j
                for j in range(i + 1, len(lineas))
                if (m := VALLA.match(lineas[j]))
                and m["marca"][0] == marca[0]
                and len(m["marca"]) >= len(marca)
                and not m["info"]
            ),
            None,
        )
        if cierre is None:
            raise SystemExit(f"{relativa}:{i + 1}: bloque de codigo sin cerrar")
        if apertura["info"].split()[:1] == ["mermaid"]:
            codigo = textwrap.dedent("\n".join(lineas[i + 1 : cierre]))
            diagramas.append(Diagrama(relativa, i + 1, codigo))
        i = cierre + 1
    return diagramas


def _mmdc(npx: str, entrada: Path, salida: Path, config: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            npx,
            "--yes",
            MERMAID_CLI,
            "--quiet",
            "--puppeteerConfigFile",
            str(config),
            "--input",
            str(entrada),
            "--output",
            str(salida),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


def _error(resultado: subprocess.CompletedProcess[str]) -> str:
    """El mensaje del parser, sin la pila de puppeteer que viene detras."""
    lineas = (resultado.stderr or resultado.stdout).strip().splitlines()
    inicio = next((n for n, x in enumerate(lineas) if "Error" in x), max(len(lineas) - 5, 0))
    util: list[str] = []
    for linea in lineas[inicio:]:
        if linea.lstrip().startswith("at ") or "://" in linea:
            break
        util.append(linea)
    return "\n".join(util[:6]) or f"mmdc salio con {resultado.returncode} sin decir por que"


def compilar(diagramas: list[Diagrama], npx: str) -> list[tuple[Diagrama, str]]:
    """Los que no compilan, cada uno con su error. Vacia si compilan todos."""
    with tempfile.TemporaryDirectory(prefix="diagramas-") as tmp:
        carpeta = Path(tmp)
        config = carpeta / "puppeteer.json"
        config.write_text(json.dumps(CONFIG_PUPPETEER), encoding="utf-8")

        juntos = carpeta / "juntos.md"
        juntos.write_text(
            "".join(f"```mermaid\n{d.codigo}\n```\n\n" for d in diagramas), encoding="utf-8"
        )
        dibujos = carpeta / "juntos"
        dibujos.mkdir()
        resultado = _mmdc(npx, juntos, dibujos / "juntos.md", config)
        # Y que haya dibujado uno por diagrama: salir con 0 sin haber escrito
        # los SVG no es haber compilado.
        if resultado.returncode == 0 and len(list(dibujos.glob("*.svg"))) == len(diagramas):
            return []

        def uno(indice: int) -> tuple[Diagrama, str] | None:
            diagrama = diagramas[indice]
            entrada = carpeta / f"{indice}.mmd"
            entrada.write_text(diagrama.codigo, encoding="utf-8")
            svg = carpeta / f"{indice}.svg"
            resultado = _mmdc(npx, entrada, svg, config)
            if resultado.returncode == 0 and svg.is_file():
                return None
            return diagrama, _error(resultado)

        with ThreadPoolExecutor(max_workers=EN_PARALELO) as grupo:
            return [r for r in grupo.map(uno, range(len(diagramas))) if r is not None]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compila cada diagrama Mermaid de los .md.")
    parser.add_argument(
        "--listar",
        action="store_true",
        help="solo escribe fichero:linea de cada diagrama, sin red ni navegador",
    )
    args = parser.parse_args(argv)

    diagramas = [d for doc in documentos() for d in extraer(doc)]
    if args.listar:
        for diagrama in diagramas:
            print(f"{diagrama.ruta}:{diagrama.linea}")
        return 0

    if not diagramas:
        print("no se encontro ningun diagrama: eso no es que compilen, es no haber mirado")
        return 2
    npx = shutil.which("npx")
    if npx is None:
        print("no hay npx en el PATH: sin Node no se puede compilar ninguno")
        return 2

    en = len({d.ruta for d in diagramas})
    print(f"{len(diagramas)} diagramas en {en} documentos, con {MERMAID_CLI}", flush=True)
    rotos = compilar(diagramas, npx)

    if len(diagramas) > 1 and len(rotos) == len(diagramas):
        print(f"no compilo ninguno de los {len(diagramas)}: es el entorno, no la documentacion")
        print(rotos[0][1])
        return 2

    en_actions = os.environ.get("GITHUB_ACTIONS") == "true"
    for diagrama, error in rotos:
        print(f"\n--- {diagrama.ruta}:{diagrama.linea}\n{error}")
        if en_actions:
            titular = error.splitlines()[0] if error else "no compila"
            print(f"::error file={diagrama.ruta},line={diagrama.linea}::{titular}")
    if rotos:
        print(f"\n{len(rotos)} de {len(diagramas)} no compilan")
        return 1
    print(f"los {len(diagramas)} compilan")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
