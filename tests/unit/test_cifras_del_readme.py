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
#: Las etiquetas van **con tildes**: el README las llevaba sin ellas y el
#: proyecto tiene una prueba que exige lo contrario en todo lo publicado. La
#: fila de licuefaccion ademas cambio de nombre: decia "zona de licuefaccion
#: alta", y "alta" afirmaba una categoria que USGS no publica a ese umbral
#: sobre una magnitud —cobertura areal— que no es una probabilidad.
FILAS: tuple[tuple[str, str], ...] = (
    ("Personas en MMI≥6", "pop_mmi6p"),
    ("Personas en MMI≥7", "pop_mmi7p"),
    ("De ellas, 65 años o más", "pop_65p_mmi7p"),
    ("Edificaciones en MMI≥7", "bld_mmi7p"),
    ("Sedes de salud en MMI≥7", "health_mmi7p"),
    ("Sedes educativas en MMI≥7", "edu_mmi7p"),
    ("Kilómetros de vía en MMI≥7", "road_km_mmi7p"),
    ("De ellos, primarias y secundarias", "road_km_principal_mmi7p"),
    ("Personas en celdas con cobertura areal por licuefacción ≥ 0,10", "pop_lq_alta"),
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


# --- La tabla de poblacion que va a instituciones --------------------------

INSTITUCIONES = RAIZ / "docs" / "PARA_INSTITUCIONES.md"
MANIFESTS = RAIZ / "data" / "manifests"

#: Los diecinueve, por ISO3. El fichero es la fuente; la tabla, el derivado.
ISO3 = sorted(p.stem for p in MANIFESTS.glob("*.yaml"))


@pytest.fixture(scope="module")
def instituciones() -> str:
    return INSTITUCIONES.read_text(encoding="utf-8")


@pytest.mark.parametrize("iso3", ISO3)
def test_la_tabla_de_instituciones_no_se_despega_de_los_manifests(
    iso3: str, instituciones: str
) -> None:
    """El documento decia 18 de 19 paises, 3 reportes y Brasil pendiente.

    Eran 19, 21 y construido. Y una cifra de poblacion —la de Argentina— se
    habia movido en el manifest sin que la tabla se enterara. Es el mismo fallo
    que el resto de este fichero vigila para el README: una tabla copiada a mano
    se desincroniza, y esta va a instituciones.
    """
    referencia = yaml.safe_load((MANIFESTS / f"{iso3}.yaml").read_text("utf-8"))[
        "referencia_oficial"
    ]
    medido = format_number_es(int(referencia["medido_ghs_pop"]))

    assert medido in instituciones, (
        f"§4 no cita la poblacion medida de {iso3} ({medido}). El manifest la movio."
    )


@pytest.mark.parametrize("iso3", ISO3)
def test_el_desvio_publicado_es_el_que_sale_de_las_dos_cifras(
    iso3: str, instituciones: str
) -> None:
    """El desvio no es un dato del manifest: es la resta. Publicado a mano, se
    queda contradiciendo a las dos cifras de su propia fila."""
    referencia = yaml.safe_load((MANIFESTS / f"{iso3}.yaml").read_text("utf-8"))[
        "referencia_oficial"
    ]
    medido, oficial = int(referencia["medido_ghs_pop"]), int(referencia["poblacion_2025"])
    desvio = 100.0 * (medido - oficial) / oficial
    # El menos del documento es U+2212, no un guion: es prosa, no codigo.
    signo = "+" if desvio >= 0 else "\u2212"
    esperado = f"| {signo}{abs(desvio):.2f} %".replace(".", ",")

    assert esperado in instituciones, f"§4 no publica {esperado.strip()} para {iso3}"


def test_el_documento_dice_que_ningun_reporte_se_disparo_en_vivo(instituciones: str) -> None:
    """El silencio sobre esto se lee como ambiguedad deliberada.

    `site/status.json` publica `eventos_publicados: 0`. Si algun dia deja de ser
    cero, esta prueba falla y toca reescribir el parrafo — que es exactamente el
    dia en que hay algo mejor que contar.
    """
    estado = json.loads((RAIZ / "site" / "status.json").read_text(encoding="utf-8"))

    if int(estado["medido"]["eventos_publicados"]) == 0:
        assert "los 21 son reconstrucciones" in instituciones.lower()
    else:
        raise AssertionError(
            "Ya hay reportes disparados en vivo: §3 de PARA_INSTITUCIONES y el "
            "README siguen diciendo que no, y ahora hay algo mejor que contar."
        )
