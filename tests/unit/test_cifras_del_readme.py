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
        return

    # YA LLEGO EL DIA, Y LA GUARDIA TIENE QUE PODER PASAR.
    #
    # Escrita como estaba, elevaba siempre que hubiera un reporte en vivo: era
    # un aviso de un solo sentido, sin estado de "ya esta reescrito". Cumplio su
    # trabajo el 2-sep-2026 —hizo saltar los dos parrafos rancios en cuanto
    # `eventos_publicados` paso a 1— y despues no podia volver a verde nunca.
    #
    # Ahora comprueba lo que de verdad importa: que los dos documentos hablen
    # del reporte en vivo en vez de seguir diciendo que no lo hay.
    assert "los 21 son reconstrucciones" not in instituciones.lower(), (
        "§3 de PARA_INSTITUCIONES sigue diciendo que ninguno se disparo en vivo, "
        "y `status.json` publica que si."
    )
    assert "en vivo" in instituciones.lower(), (
        "§3 no menciona el reporte en vivo, que es lo mejor que este documento tiene que contar"
    )


# --- El recuento de pruebas también es una cifra de la portada ---------------

#: Marca que ya estamos dentro del subproceso que cuenta. Sin ella, la prueba se
#: llamaría a sí misma sin fin.
_CONTANDO = "CENTINELA_CONTANDO_PRUEBAS"


def _pasadas(*argumentos: str) -> int:
    """Cuántas pruebas **pasan** con esos argumentos.

    Pasadas y no recolectadas: la portada dice «1.152 pruebas» y eso tiene que
    significar las que verifican algo, no las que se recolectan incluyendo 27 que
    se saltan por falta de datos locales. Contar recolectadas inflaría la cifra
    en justo esas 27.
    """
    import os
    import re
    import subprocess
    import sys

    entorno = {**os.environ, _CONTANDO: "1"}
    salida = subprocess.run(
        [sys.executable, "-m", "pytest", "--tb=no", "-p", "no:cacheprovider", *argumentos],
        cwd=RAIZ,
        capture_output=True,
        text=True,
        check=False,
        env=entorno,
    ).stdout
    hallado = re.search(r"(\d+) passed", salida)
    assert hallado, f"pytest no dijo cuántas pasaron:\n{salida[-800:]}"
    return int(hallado.group(1))


def _recolectadas(*argumentos: str) -> int:
    """Cuántas recolecta, para las suites que no se pueden correr aquí.

    La de navegador arranca un Chromium y tarda ocho minutos: no cabe dentro de
    otra prueba. Se recolecta, que es exacto mientras ninguna se salte — y si
    alguna empezara a saltarse, esta misma cifra dejaría de cuadrar con la
    portada y habría que mirarlo.
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
    hallado = re.search(r"(\d+)(?:/\d+)? tests collected", salida)
    assert hallado, f"pytest no dijo cuántas recolectó:\n{salida[-800:]}"
    return int(hallado.group(1))


def test_el_readme_no_miente_sobre_cuantas_pruebas_hay(readme: str) -> None:
    """La portada decía «953 pruebas … 43 de navegador». Eran 1.152 y 101.

    Nadie lo notó porque **nadie lo vigilaba**: las nueve cifras del backtest del
    Chocó tienen guardia desde que se descubrió que cinco estaban desfasadas, y
    estas dos se quedaron fuera. Se separaron en cuanto la suite creció, que es
    lo que le pasa a toda cifra copiada a mano — la misma lección que enuncia la
    cabecera de este fichero, aplicada a la única cifra del README que habla del
    propio repositorio.
    """
    import os
    import re

    if os.environ.get(_CONTANDO):
        pytest.skip("ya estamos dentro del subproceso que cuenta")

    hallado = re.search(
        r"\*\*([\d.]+) pruebas\*\* sin red, más \*\*([\d.]+) de navegador\*\*", readme
    )
    assert hallado, "el README ya no dice cuántas pruebas hay en la forma esperada"

    dice_pipeline = int(hallado.group(1).replace(".", ""))
    dice_visor = int(hallado.group(2).replace(".", ""))

    # `+ 1` por esta misma prueba: dentro del subproceso se salta —si no, se
    # llamaria a si misma sin fin— asi que el recuento que devuelve le falta una.
    # La portada dice lo que ve quien corre `make check`, que si la incluye.
    pipeline = _pasadas() + 1
    visor = _recolectadas("tests/visor", "-m", "visor")

    assert dice_pipeline == pipeline, (
        f"el README dice {dice_pipeline} pruebas sin red y pasan {pipeline}"
    )
    assert dice_visor == visor, f"el README dice {dice_visor} de navegador y hay {visor}"


# --- La portada tiene que explicarse antes de usarse -------------------------


def test_la_portada_define_mmi_antes_de_usarlo(readme: str) -> None:
    """MMI aparecia veinte veces y no se definia nunca.

    LA CONFUSION MAGNITUD-INTENSIDAD ES EL ERROR DE LECTURA MAS CARO QUE ESTE
    SISTEMA PUEDE PROVOCAR. La magnitud es una cifra para el sismo entero; la
    intensidad es un mapa. Quien las confunda reparte ayuda por la cifra
    equivocada, y el documento que mas gente lee daba por sabida la diferencia.

    Se comprueba que la definicion existe **y que llega antes** del primer uso
    en una cifra: una glosa al final no evita la mala lectura de arriba.
    """
    assert "Mercalli" in readme, "el README usa MMI sin decir nunca qué es"

    definicion = readme.index("Mercalli")
    primer_uso = readme.index("MMI≥")
    assert definicion < primer_uso, (
        "el README define MMI después de usarlo en una banda; quien lea de "
        "arriba abajo se encuentra la cifra antes que la explicación"
    )


def test_la_portada_enlaza_el_visor_antes_de_la_mitad(readme: str) -> None:
    """El enlace vivia en la linea 255 de un documento de 3.150 palabras.

    Un sistema que publica una pagina y no la enlaza hasta el ultimo tercio
    obliga a leerse el argumento entero para llegar al producto.
    """
    enlace = readme.find("https://sforero77.github.io/CENTINELA/")
    assert enlace > 0, "el README no enlaza el visor"
    assert enlace < len(readme) // 3, (
        "el enlace al visor queda pasado el primer tercio del documento"
    )


# --- La cuenta de eventos por banda, que ya se quedo vieja dos veces --------
#
# "Ocho de diecinueve" -> "once de veintiuno" -> "trece de veintitres". La cifra
# se copiaba a mano en dos documentos y envejecia cada vez que entraba un
# reporte, que es justo lo que este fichero existe para impedir.

BANDAS_EN_PROSA = (
    ("README.md", "trece de los veintitrés"),
    ("docs/datos/agregaciones.md", "trece de los veintitrés"),
)


def _sin_banda(banda: str) -> int:
    """Cuantos reportes publicados no tienen poblacion en esa banda."""
    return sum(
        1
        for p in sorted((RAIZ / "reports").glob("*/report.json"))
        if json.loads(p.read_text(encoding="utf-8"))["totales"][banda] == 0
    )


def test_la_cuenta_de_eventos_sin_mmi7_es_la_que_dicen_los_documentos() -> None:
    """Trece de veintitrés, y que lo siga diciendo el disco y no la memoria."""
    total = len(list((RAIZ / "reports").glob("*/report.json")))
    sin7 = _sin_banda("pop_mmi7p")

    assert (sin7, total) == (13, 23), (
        f"la cuenta cambio: hoy son {sin7} de {total} sin población en MMI≥7. "
        f"Actualiza README.md y docs/datos/agregaciones.md, y esta prueba."
    )


def test_la_cuenta_de_eventos_sin_mmi6_tambien() -> None:
    """Los que ni siquiera llegan a 6: solo el corte por radios los dimensiona."""
    assert _sin_banda("pop_mmi6p") == 5


@pytest.mark.parametrize(("documento", "frase"), BANDAS_EN_PROSA)
def test_los_documentos_dicen_esa_cuenta(documento: str, frase: str) -> None:
    """La prosa y el disco, atados."""
    texto = (RAIZ / documento).read_text(encoding="utf-8")
    assert frase in texto, f"{documento} ya no dice «{frase}»"
