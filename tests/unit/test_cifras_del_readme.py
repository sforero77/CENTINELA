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
