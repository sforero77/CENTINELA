"""Las cifras escritas en prosa, atadas a los artefactos de los que salen.

Nacio para la portada. El README publicaba nueve cifras del backtest del Choco y
**cinco estaban desactualizadas**: el activo se reconstruyo (col-v0.4 → col-v0.5),
los reportes se regeneraron y la tabla se quedo con los numeros anteriores. Los
kilometros de via estaban errados por un factor de seis.

No fue descuido de nadie en particular: es lo que le pasa a toda cifra copiada a
mano. Para sostener las de la portada hicieron falta un generador que reescribia
el README desde `impact.yml` y media docena de guardias.

DESDE EL 13-SEP-2026 EL README NO PUBLICA CIFRAS. Dice que es CENTINELA y que
hace; las cifras viven donde tienen su procedencia —cada `report.json`,
`/status` y `docs/PARA_INSTITUCIONES.md`—. Este fichero sigue atando las que
quedan escritas a mano en esos documentos, y del README vigila lo contrario: que
ninguna vuelva a entrar.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
import yaml

from pipelines.common.formatting import format_number_es

RAIZ = Path(__file__).parent.parent.parent
README = RAIZ / "README.md"


@pytest.fixture(scope="module")
def readme() -> str:
    return README.read_text(encoding="utf-8")


# --- El README describe; no publica cifras ------------------------------------

#: Las formas en que una cifra se cuela en prosa. Pensadas para no confundir un
#: resultado con una regla o un nombre: «magnitud 5,5 o más», «MMI≥7»,
#: «Python 3.12» o «CC BY 4.0» no son cifras del sistema.
_CIFRAS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\b\d{1,3}(?:\.\d{3})+\b"), "un número con separador de miles"),
    (re.compile(r"\d(?:,\d+)?\s?%"), "un porcentaje"),
    (
        re.compile(
            r"\b\d[\d.,]*\s+(?:millones|personas|habitantes|pruebas|reportes|países|"
            r"sismos|eventos|celdas|municipios|edificaciones|sedes|km|kilómetros|"
            r"minutos|min|horas|días)\b",
            flags=re.IGNORECASE,
        ),
        "un recuento",
    ),
)


def test_el_readme_no_publica_cifras(readme: str) -> None:
    """Decision del 13-sep-2026: la portada explica, no publica resultados.

    Cada cifra que la portada llego a publicar —la tabla del backtest del Choco,
    el contraste con PAGER, el recuento de reportes, el de pruebas, la latencia—
    se quedo atras al menos una vez, y el recuento de pruebas en cada PR. Una
    cifra que vuelva a entrar aqui vuelve a necesitar quien la mantenga.
    """
    # Los enlaces no son prosa: `?evento=us6000tjl2` no es un recuento.
    prosa = re.sub(r"\]\([^)]*\)|https?://\S+", " ", readme)
    halladas = [f"{que}: «{m.group(0)}»" for patron, que in _CIFRAS for m in patron.finditer(prosa)]
    assert not halladas, (
        f"el README vuelve a publicar cifras: {halladas}. Van en el reporte, en "
        f"/status o en docs/PARA_INSTITUCIONES.md, con su procedencia."
    )


def test_las_garantias_siguen_enlazadas() -> None:
    """El documento que dice que esta probado y que no.

    Si no se llega a el desde ninguna parte, alguien dara por buena una garantia
    que este fichero marca como sin demostrar.
    """
    garantias = RAIZ / "docs" / "GARANTIAS.md"

    assert garantias.exists()
    assert "GARANTIAS" in README.read_text(encoding="utf-8")

    texto = garantias.read_text(encoding="utf-8")
    assert "Lo que NO está garantizado" in texto, "un documento de garantias sin la mitad incomoda"


def test_la_portada_define_mmi_antes_de_usarlo(readme: str) -> None:
    """MMI aparecia veinte veces y no se definia nunca.

    LA CONFUSION MAGNITUD-INTENSIDAD ES EL ERROR DE LECTURA MAS CARO QUE ESTE
    SISTEMA PUEDE PROVOCAR. La magnitud es una cifra para el sismo entero; la
    intensidad es un mapa. Quien las confunda reparte ayuda por la cifra
    equivocada, y el documento que mas gente lee daba por sabida la diferencia.

    Se comprueba que la definicion existe **y que llega antes** del primer uso
    en una banda: una glosa al final no evita la mala lectura de arriba.
    """
    assert "Mercalli" in readme, "el README usa MMI sin decir nunca qué es"

    definicion = readme.index("Mercalli")
    primer_uso = readme.find("MMI≥")
    assert primer_uso == -1 or definicion < primer_uso, (
        "el README define MMI después de usarlo en una banda; quien lea de "
        "arriba abajo se encuentra la banda antes que la explicación"
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
    que este fichero vigilaba para el README: una tabla copiada a mano se
    desincroniza, y esta va a instituciones.
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
    signo = "+" if desvio >= 0 else "−"
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
    # Ahora comprueba lo que de verdad importa: que el documento hable del
    # reporte en vivo en vez de seguir diciendo que no lo hay.
    assert "los 21 son reconstrucciones" not in instituciones.lower(), (
        "§3 de PARA_INSTITUCIONES sigue diciendo que ninguno se disparo en vivo, "
        "y `status.json` publica que si."
    )
    assert "en vivo" in instituciones.lower(), (
        "§3 no menciona el reporte en vivo, que es lo mejor que este documento tiene que contar"
    )


# --- La cuenta de eventos por banda, que ya se quedo vieja dos veces --------
#
# "Ocho de diecinueve" -> "once de veintiuno" -> "trece de veintitres". La cifra
# se copiaba a mano en dos documentos y envejecia cada vez que entraba un
# reporte, que es justo lo que este fichero existe para impedir.

BANDAS_EN_PROSA = (("docs/datos/agregaciones.md", "diecisiete de los veintisiete"),)


def _sin_banda(banda: str) -> int:
    """Cuantos reportes publicados no tienen poblacion en esa banda."""
    return sum(
        1
        for p in sorted((RAIZ / "reports").glob("*/report.json"))
        if json.loads(p.read_text(encoding="utf-8"))["totales"][banda] == 0
    )


def test_la_cuenta_de_eventos_sin_mmi7_es_la_que_dicen_los_documentos() -> None:
    """Diecisiete de veintisiete, y que lo siga diciendo el disco y no la memoria."""
    total = len(list((RAIZ / "reports").glob("*/report.json")))
    sin7 = _sin_banda("pop_mmi7p")

    assert (sin7, total) == (17, 27), (
        f"la cuenta cambio: hoy son {sin7} de {total} sin población en MMI≥7. "
        f"Actualiza docs/datos/agregaciones.md y esta prueba."
    )


def test_la_cuenta_de_eventos_sin_mmi6_tambien() -> None:
    """Los que ni siquiera llegan a 6: solo el corte por radios los dimensiona."""
    assert _sin_banda("pop_mmi6p") == 9


@pytest.mark.parametrize(("documento", "frase"), BANDAS_EN_PROSA)
def test_los_documentos_dicen_esa_cuenta(documento: str, frase: str) -> None:
    """La prosa y el disco, atados."""
    texto = (RAIZ / documento).read_text(encoding="utf-8")
    assert frase in texto, f"{documento} ya no dice «{frase}»"


# --- La misma familia, en los otros documentos que copian cifras ------------


#: Documentos que publican el recuento de reportes, y como lo escriben.
#:
#: Un documento de estado llego a llevar cinco cifras desfasadas a la vez, sin
#: cambiar ninguna en seis ediciones posteriores. Otro citaba 601 pruebas. El
#: README decia 23 reportes en 15 paises treinta lineas por encima de donde ya
#: decia «veintisiete»; hoy ya no publica ninguno.
DOCUMENTOS_CON_RECUENTO: tuple[str, ...] = ("docs/PARA_INSTITUCIONES.md",)


def _indice_publicado() -> list[dict[str, object]]:
    entradas: list[dict[str, object]] = json.loads(
        (RAIZ / "reports" / "index.json").read_text(encoding="utf-8")
    )
    return entradas


@pytest.mark.parametrize("nombre", DOCUMENTOS_CON_RECUENTO)
def test_ningun_documento_publica_un_recuento_de_reportes_desfasado(nombre: str) -> None:
    """El numero sale de `reports/index.json`, que es lo que el visor lee.

    No se exige una frase concreta —cada documento la escribe a su manera— sino
    que **ninguna** cifra de reportes que aparezca sea una de las viejas. Pedir
    la cadena exacta convertiria esto en un cerrojo tipografico; pedir que no
    mienta es lo que hace falta.
    """
    entradas = _indice_publicado()
    total = len(entradas)
    paises = len({e.get("iso3") for e in entradas if e.get("iso3")})
    backtests = sum(1 for e in entradas if e.get("backtest"))

    texto = (RAIZ / nombre).read_text(encoding="utf-8")

    # Las formas en que estos documentos escriben el recuento, con el numero
    # dentro. Si el documento las usa, el numero tiene que ser el de hoy.
    for patron, esperado, que in (
        (r"Reportes (?:publicados|emitidos de punta a punta) \| \*\*(\d+)\*\*", total, "reportes"),
        (r"\*\*(\d+) sismos de \d+ países\*\*", backtests, "backtests"),
        (r"\*\*\d+ reportes en (\d+) países\*\*", paises, "países"),
    ):
        for hallado in re.finditer(patron, texto):
            assert int(hallado.group(1)) == esperado, (
                f"{nombre} dice {hallado.group(1)} {que} y en reports/index.json hay "
                f"{esperado}. La cifra se copia a mano y se desfasa sola; es la "
                f"tercera vez que pasa en este repositorio."
            )

    # Y los paises: se cuentan igual que en la tabla, con el numero al lado.
    for hallado in re.finditer(r"en (?:\*\*)?(\d+)(?:\*\*)? países", texto):
        assert int(hallado.group(1)) == paises, (
            f"{nombre} dice {hallado.group(1)} países con reporte y hay {paises}"
        )
