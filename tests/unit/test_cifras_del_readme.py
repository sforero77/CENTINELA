"""Que la portada diga lo que dicen los artefactos publicados.

El README publicaba nueve cifras del backtest del Choco y **cinco estaban
desactualizadas**: el activo se reconstruyo (col-v0.4 → col-v0.5), los reportes
se regeneraron, y la tabla se quedo con los numeros anteriores. Los kilometros
de via estaban errados por un factor de seis — 1.400 donde el reporte publica
8.503.

No fue descuido de nadie en particular: es lo que le pasa a toda cifra copiada
a mano. Y en un repositorio publico cuyo argumento entero es que sus numeros
son de fiar, la portada es justo donde menos puede pasar.

Asi que la tabla deja de sostenerse en disciplina. Estas pruebas leen el
`report.json` publicado y fallan si la portada se separa de el.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from pipelines.common.formatting import format_number_es

RAIZ = Path(__file__).parent.parent.parent
README = RAIZ / "README.md"
REPORTE_GOLDEN = RAIZ / "reports" / "us6000tjl2" / "report.json"

#: Fila del README -> campo de `totales` en el reporte. El README redondea al
#: entero, que es como se lee una cifra de exposicion: nadie publica "2.415.793,46
#: personas".
FILAS: tuple[tuple[str, str], ...] = (
    ("Personas en MMI≥6", "pop_mmi6p"),
    ("Personas en MMI≥7", "pop_mmi7p"),
    ("De ellas, 65 anos o mas", "pop_65p_mmi7p"),
    ("Edificaciones en MMI≥7", "bld_mmi7p"),
    ("Sedes de salud en MMI≥7", "health_mmi7p"),
    ("Sedes educativas en MMI≥7", "edu_mmi7p"),
    ("Kilometros de via en MMI≥7", "road_km_mmi7p"),
    ("De ellos, primarias y secundarias", "road_km_principal_mmi7p"),
    ("Personas en zona de licuefaccion alta", "pop_lq_alta"),
)


@pytest.fixture(scope="module")
def readme() -> str:
    return README.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def totales() -> dict[str, float]:
    datos: dict[str, float] = json.loads(REPORTE_GOLDEN.read_text(encoding="utf-8"))["totales"]
    return datos


@pytest.mark.parametrize(("etiqueta", "campo"), FILAS, ids=[c for _, c in FILAS])
def test_la_cifra_del_readme_es_la_publicada(
    etiqueta: str, campo: str, readme: str, totales: dict[str, float]
) -> None:
    esperada = format_number_es(round(float(totales[campo])))
    fila = f"| {etiqueta} | **{esperada}** |"

    assert fila in readme, (
        f"El README no trae {esperada!r} para {etiqueta!r}. "
        f"El reporte publicado dice {totales[campo]}. Actualiza la tabla."
    )


def test_los_municipios_alcanzados_son_los_del_csv() -> None:
    """La fila que no sale de `totales` sino de contar filas del CSV."""
    import csv

    with (RAIZ / "reports" / "us6000tjl2" / "adm2.csv").open(encoding="utf-8") as fh:
        filas = [f for f in csv.DictReader(fh) if not str(f["usgs_id"]).startswith("#")]

    assert f"| Municipios alcanzados | **{format_number_es(len(filas))}** |" in README.read_text(
        encoding="utf-8"
    )


def test_la_poblacion_del_activo_es_la_medida_en_el_manifest(readme: str) -> None:
    """El README decia "52,9 millones" y el manifest mide 52.620.466.

    Es la unica cifra del activo que vive en git —el resto viaja en el
    `medicion.json` del Release— asi que es la unica que se puede vigilar aqui.
    """
    manifest = yaml.safe_load((RAIZ / "data" / "manifests" / "COL.yaml").read_text("utf-8"))
    medido = int(manifest["referencia_oficial"]["medido_ghs_pop"])

    assert format_number_es(medido) in readme, (
        f"El README no cita la poblacion medida del activo ({format_number_es(medido)})."
    )


def test_el_readme_nombra_el_release_del_que_salen_las_cifras(readme: str) -> None:
    """Sin el tag, las cifras del activo no son verificables por nadie.

    El activo no esta en git —pesa 17 MB por pais— asi que la unica forma de
    que un lector compruebe estas cifras es sabiendo **que** Release describen.
    """
    assert "exposure-col-2" in readme, "el README no dice de que Release salen las cifras"


def test_las_familias_de_fallo_siguen_enlazadas() -> None:
    """Un documento al que no se llega desde ninguna parte no lo lee nadie.

    Es la version documental de "escrito no es conectado", que es justo la
    primera de las siete familias que ese fichero describe.
    """
    raiz = Path(__file__).parent.parent.parent
    familias = raiz / "docs" / "FAMILIAS_DE_FALLO.md"

    assert familias.exists()
    for puerta in (raiz / "docs" / "AUDITORIA.md", raiz / "PENDIENTES.md"):
        assert "FAMILIAS_DE_FALLO" in puerta.read_text(encoding="utf-8"), (
            f"{puerta.name} no lleva a las familias de fallo"
        )


def test_las_garantias_siguen_enlazadas() -> None:
    """El documento que dice que esta probado y que no.

    Si no se llega a el desde ninguna parte, alguien dara por buena una garantia
    que este fichero marca como sin demostrar.
    """
    raiz = Path(__file__).parent.parent.parent
    garantias = raiz / "docs" / "GARANTIAS.md"

    assert garantias.exists()
    assert "GARANTIAS" in (raiz / "PENDIENTES.md").read_text(encoding="utf-8")

    texto = garantias.read_text(encoding="utf-8")
    assert "Lo que NO está garantizado" in texto, "un documento de garantias sin la mitad incomoda"


# --- El conteo de pruebas tambien es una cifra de la portada -----------------


def _recolectadas(*argumentos: str) -> int:
    """Cuantas pruebas recolecta pytest con esos argumentos.

    Se lanza en un subproceso con `--collect-only`, que no ejecuta nada: la
    recoleccion entera tarda decimas de segundo y no toca red ni navegador.
    """
    import re
    import subprocess
    import sys

    salida = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", *argumentos],
        cwd=RAIZ,
        capture_output=True,
        text=True,
        check=False,
    ).stdout
    # "1064/1173 tests collected (109 deselected)" o "101 tests collected"
    hallado = re.search(r"(\d+)(?:/\d+)? tests collected", salida)
    assert hallado, f"pytest no dijo cuantas recolecto:\n{salida[-800:]}"
    return int(hallado.group(1))


def test_el_readme_no_miente_sobre_cuantas_pruebas_hay(readme: str) -> None:
    """La portada decia «953 pruebas … 43 de navegador». Eran 1.064 y 101.

    Nadie lo noto porque **nadie lo vigilaba**: las nueve cifras del backtest
    tienen guardia desde que se descubrio que cinco estaban desfasadas, y estas
    dos se quedaron fuera. Se separaron en cuanto la suite crecio, que es lo que
    le pasa a toda cifra copiada a mano.

    Es la misma leccion del resto del fichero, aplicada a la unica cifra del
    README que habla del propio repositorio.
    """
    import re

    pipeline = _recolectadas()
    visor = _recolectadas("tests/visor", "-m", "visor")

    hallado = re.search(
        r"\*\*([\d.]+) pruebas\*\* sin red, mas \*\*([\d.]+) de navegador\*\*", readme
    )
    assert hallado, "el README ya no dice cuantas pruebas hay en la forma esperada"

    dice_pipeline = int(hallado.group(1).replace(".", ""))
    dice_visor = int(hallado.group(2).replace(".", ""))

    assert dice_pipeline == pipeline, (
        f"el README dice {dice_pipeline} pruebas sin red y hay {pipeline}"
    )
    assert dice_visor == visor, f"el README dice {dice_visor} de navegador y hay {visor}"
