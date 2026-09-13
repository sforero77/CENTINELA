"""Los diagramas de la documentacion se compilan en CI, y ninguno se queda fuera.

`scripts/validar_diagramas.py` compila cada bloque Mermaid con mermaid-cli, y el
job `diagramas` de `ci.yml` lo corre en cada push y en cada PR. Aqui no se
compila nada —eso pide Chromium y red, y esta suite corre sin los dos—: se
vigila que el guardia siga existiendo y que mire todo lo que tiene que mirar.

Un guardia asi desaparece sin ponerse rojo de dos maneras:

1. **Deja de correr.** Un filtro de rutas en `ci.yml`, o mudar el job a
   `visor.yml` porque ya instala Chromium: aquel solo se dispara con `site/`,
   `reports/` y `tests/visor/`, asi que no abriria nunca un diagrama de `docs/`.
2. **Deja de encontrar.** Un extractor que se salta los bloques con sangria, o
   los de virgulillas, compila todos los que ve y sale en verde. Por eso lo que
   encuentra se contrasta con una busqueda aparte, mas tonta y mas amplia.

No se importa el script: `scripts/` no es un paquete y la suite no lo cubre. Se
ejecuta, que ademas es como lo usa CI.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

RAIZ = Path(__file__).resolve().parents[2]
SCRIPT = RAIZ / "scripts" / "validar_diagramas.py"
CI = RAIZ / ".github" / "workflows" / "ci.yml"


def _ci() -> dict[Any, Any]:
    datos = yaml.safe_load(CI.read_text(encoding="utf-8"))
    assert isinstance(datos, dict)
    return datos


def _comandos(job: dict[str, Any]) -> list[str]:
    """Las lineas de `run:` que ejecutan algo: un comentario que cite el script no."""
    lineas: list[str] = []
    for paso in job.get("steps") or []:
        cuerpo = paso.get("run") if isinstance(paso, dict) else None
        if isinstance(cuerpo, str):
            lineas += [
                x for x in cuerpo.splitlines() if x.strip() and not x.lstrip().startswith("#")
            ]
    return lineas


def test_ci_compila_los_diagramas() -> None:
    jobs = _ci()["jobs"]
    quien = [
        nombre
        for nombre, job in jobs.items()
        if any("scripts/validar_diagramas.py" in x for x in _comandos(job))
    ]
    assert quien, "ningún job de ci.yml corre scripts/validar_diagramas.py"
    for nombre in quien:
        assert not any("--listar" in x for x in _comandos(jobs[nombre])), (
            f"el job {nombre} corre el script con --listar, que no compila nada"
        )


def test_ci_no_filtra_por_rutas() -> None:
    """Los diagramas viven en `docs/`, en el README y en `scripts/README.md`.

    Un `paths:` que no los incluya a todos deja el job en verde sin correr sobre
    el cambio que lo necesitaba.
    """
    datos = _ci()
    # `on` es la palabra reservada `True` para el cargador de YAML.
    disparo = datos.get(True) or datos.get("on") or {}
    for evento in ("push", "pull_request"):
        assert evento in disparo, f"ci.yml ya no se dispara con {evento}"
        conf = disparo[evento] or {}
        filtros = sorted({"paths", "paths-ignore"} & set(conf))
        assert not filtros, f"ci.yml filtra {evento} con {filtros}: los diagramas no se compilarían"


def test_mermaid_cli_va_por_version_exacta() -> None:
    """Con `@11` a secas, `npx` compila con lo que tenga en caché ese día."""
    texto = SCRIPT.read_text(encoding="utf-8")
    hallado = re.search(r'^MERMAID_CLI = "([^"]+)"$', texto, flags=re.M)
    assert hallado, "scripts/validar_diagramas.py ya no declara MERMAID_CLI"
    assert re.fullmatch(r"@mermaid-js/mermaid-cli@\d+\.\d+\.\d+", hallado.group(1)), (
        f"{hallado.group(1)} no es una versión exacta"
    )


def _a_mano() -> set[str]:
    """Cualquier linea que, quitada la sangria, abra un bloque mermaid.

    A proposito mas tonta que el extractor: no sabe de bloques anidados ni de
    vallas de cuatro acentos. Si un dia las dos cuentas difieren por eso, el
    fallo pide mirarlo, que es lo que tiene que pasar.
    """
    salida = subprocess.run(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard", "--", "*.md"],
        cwd=RAIZ,
        capture_output=True,
        check=True,
    ).stdout.decode("utf-8")
    encontrados: set[str] = set()
    for relativa in filter(None, salida.split("\0")):
        ruta = RAIZ / relativa
        if not ruta.is_file():
            continue
        for numero, linea in enumerate(ruta.read_text(encoding="utf-8").splitlines(), 1):
            if linea.lstrip().startswith(("```mermaid", "~~~mermaid")):
                encontrados.add(f"{relativa}:{numero}")
    return encontrados


def test_el_extractor_no_se_salta_ningun_diagrama() -> None:
    salida = subprocess.run(
        [sys.executable, str(SCRIPT), "--listar"],
        cwd=RAIZ,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    ).stdout
    extraidos = set(salida.splitlines())
    a_mano = _a_mano()
    assert extraidos == a_mano, (
        f"el extractor se salta {sorted(a_mano - extraidos)} "
        f"y encuentra de más {sorted(extraidos - a_mano)}"
    )


def test_hay_diagramas_que_compilar() -> None:
    """Si las dos busquedas salen vacias, la de arriba pasa en vacio.

    `docs/acciones/por-reloj.md` lleva uno por workflow, asi que por debajo de
    esa cifra algo dejo de mirar.
    """
    workflows = len(list((RAIZ / ".github" / "workflows").glob("*.yml")))
    assert len(_a_mano()) >= workflows
