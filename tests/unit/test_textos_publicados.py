"""Lo que se publica en español se publica **con** tildes y con eñes.

EL HUECO QUE CIERRA. `markdown.py`, `social.py` y `DISCLAIMERS` llevaban las
tildes puestas en el repositorio y los ficheros servidos seguían diciendo
"Exposicion no es dano": se emitieron el 25-ago-2026, antes de esa corrección, y
nada volvía a tocarlos. El hilo para redes —el único artefacto de todo el
sistema que un humano publica a mano— abría con "Reporte automatico de
EXPOSICION estimada" y cerraba con "Exposicion no es dano", que en español no es
una frase: "dano" no es una palabra.

Esta prueba no comprueba el fichero publicado, que puede estar rancio: comprueba
el generador. Que lo publicado se ponga al día es trabajo de
`centinela regenerar-textos`, y `test_frescura` es quien vigila que se haya
corrido.

Y EL SEGUNDO HUECO, CERRADO EL 1-SEP-2026. El guardia solo miraba a los
generadores. Los veintiún `report.md` salían perfectamente acentuados —de 17 a
26 acentos por cada 100 palabras— mientras el README, que es la vitrina,
violaba **veinte de las veintidós formas** de la lista negra, y la frase que
enuncia la misión escribía mal la palabra de la misión: «con datos descargables
y en espanol», dos veces. El producto público estaba bien escrito; la
documentación a mano, no. `DOCUMENTOS` es lo que faltaba vigilar.

POR QUÉ UNA LISTA NEGRA Y NO UN DETECTOR GENÉRICO. "Se publica" y "se publico"
son las dos correctas y solo se distinguen por el sentido; un detector de
"palabras que deberían llevar tilde" daría falsos positivos en cada línea. La
lista son las formas que de verdad se colaron, que es contra lo que hay que
defenderse. Para las dos que dependen del contexto —`publica` y `publico`, que
también son el verbo— la lista es de **colocaciones**, no de palabras.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from pipelines.common.constants import DISCLAIMERS
from pipelines.p3_report.markdown import render_markdown
from pipelines.p3_report.social import render_thread_text

#: Formas sin tilde —o sin ene— que estuvieron publicadas. La clave es la forma
#: mala; el valor, la buena, para que el mensaje del fallo diga que hacer.
SIN_TILDE: dict[str, str] = {
    "exposicion": "exposición",
    "poblacion": "población",
    "sismica": "sísmica",
    "sismico": "sísmico",
    "dano": "daño",
    "danos": "daños",
    "publico": "público",
    "publica": "publicada/pública",
    "codigo": "código",
    "victimas": "víctimas",
    "reconstruccion": "reconstrucción",
    "licuefaccion": "licuefacción",
    "automatico": "automático",
    "geologicos": "geológicos",
    "gestion": "gestión",
    "metodologia": "metodología",
    "estadistica": "estadística",
    "maxima": "máxima",
    "vias": "vías",
    "mas": "más",
    "millon": "millón",
}

#: Formas adicionales que solo se vigilan en la documentacion escrita a mano.
#:
#: **`publica` y `publico` no estan en la lista de arriba por una razon**: son
#: tambien el verbo, que es correcto sin tilde («USGS publica el ShakeMap»). En
#: prosa la forma que se colaba era la adjetiva, y se distingue por lo que lleva
#: delante — no por la palabra suelta. Un detector generico daria un falso
#: positivo en cada linea.
COLOCACIONES_MALAS: dict[str, str] = {
    "dominio publico": "dominio público",
    "repositorio publico": "repositorio público",
    "discusion publica": "discusión pública",
    "funcion publica": "función pública",
    "pagina publica": "página pública",
    "cifra publica": "cifra pública",
    "api publica": "API pública",
    "camino critico": "camino crítico",
}


def _palabras_malas(texto: str) -> list[str]:
    """Las formas de la lista negra que aparecen como palabra suelta.

    Como palabra y no como subcadena: "publicas" contiene "publica" y es
    correcta, y `report.json` contiene "poblacion" en sus **claves**, que son
    identificadores y no prosa.
    """
    # Los identificadores no son prosa: `pop_mmi7p`, `adm2_id`, rutas y claves
    # entre acentos graves se quedan fuera.
    limpio = re.sub(r"`[^`]*`", " ", texto)
    encontradas = set()
    for mala in SIN_TILDE:
        if re.search(rf"(?<![\w-]){re.escape(mala)}(?![\w-])", limpio, flags=re.IGNORECASE):
            encontradas.add(mala)
    return sorted(encontradas)


#: Los documentos escritos a mano. **Esta prueba existe porque el guardia solo
#: miraba a los generadores**, y el README —la vitrina— violaba veinte de las
#: veintidos formas de la lista negra mientras los veintiun `report.md`
#: generados salian perfectamente acentuados. El producto publico estaba bien
#: escrito; la documentacion, no.
#:
#: La defensa de "ASCII por compatibilidad" no estaba disponible: el mismo
#: README usa ──▶, ⋈, ✅ y ≥. No era una politica, era un teclado.
RAIZ = Path(__file__).parent.parent.parent
DOCUMENTOS: tuple[str, ...] = (
    "README.md",
    "DISCLAIMER.md",
    "CONTRIBUTING.md",
    "GOVERNANCE.md",
    "ATTRIBUTION.md",
    "PENDIENTES.md",
    "VERIFICACIONES.md",
    "ESPECIFICACION.md",
    "LICENSES/README.md",
    "docs/AUDITORIA.md",
    "docs/CLEAN_CODE.md",
    "docs/FAMILIAS_DE_FALLO.md",
    "docs/GARANTIAS.md",
    "docs/OPERACION.md",
    "docs/PARA_INSTITUCIONES.md",
    "docs/PUBLICAR_ACTIVO.md",
    "docs/PUESTA_EN_MARCHA.md",
    "docs/README.md",
    "events/README.md",
    "reports/README.md",
    "scripts/README.md",
    "tests/fixtures/golden/README.md",
    "tests/golden/README.md",
    # Y los de subcarpeta, que quedaron fuera del primer pase: son veinticinco
    # ficheros mas —toda la documentacion de arquitectura, datos, pipelines,
    # acciones y visor— y ahi es donde vive lo que lee quien va a tocar el
    # codigo. Una guardia que solo mira la raiz deja sin vigilar el doble de
    # prosa de la que vigila.
    "docs/acciones/README.md",
    "docs/acciones/cadena-de-evento.md",
    "docs/acciones/el-vigia.md",
    "docs/acciones/mantenimiento.md",
    "docs/acciones/orquestacion.md",
    "docs/arquitectura/README.md",
    "docs/arquitectura/contratos-de-datos.md",
    "docs/arquitectura/decisiones.md",
    "docs/arquitectura/flujo-de-datos.md",
    "docs/datos/README.md",
    "docs/datos/activo-h3.md",
    "docs/datos/agregaciones.md",
    "docs/datos/fuentes.md",
    "docs/pipelines/README.md",
    "docs/pipelines/common.md",
    "docs/pipelines/p0-exposicion.md",
    "docs/pipelines/p1-trigger.md",
    "docs/pipelines/p2-impacto.md",
    "docs/pipelines/p3-reporte.md",
    "docs/pipelines/p4-brigada.md",
    "docs/pipelines/p5-incendios.md",
    "docs/visor/README.md",
    "docs/visor/capas-y-modos.md",
    "docs/visor/consumo-de-datos.md",
    "docs/visor/validacion.md",
)

#: Formas que en estos documentos son siempre el verbo, nunca el adjetivo, y que
#: por eso se sacan de la lista negra al mirar prosa a mano.
SOLO_EN_GENERADORES: frozenset[str] = frozenset({"publica", "publico"})


def _prosa(texto: str) -> str:
    """El documento sin lo que no es prosa.

    Los bloques de tres backticks hay que quitarlos **antes** que los
    identificadores entre acentos graves: sin eso, el `re.sub` de una sola
    comilla los parte por la mitad y deja dentro trozos de codigo que disparan
    falsos positivos con `mas`, `dano` y compania.
    """
    texto = re.sub(r"```.*?```", " ", texto, flags=re.S)
    texto = re.sub(r"`[^`]*`", " ", texto)
    texto = re.sub(r"\]\([^)]*\)", "] ", texto)  # destinos de enlace
    texto = re.sub(r"https?://\S+", " ", texto)
    return re.sub(r"<[^>\n]+>", " ", texto)


@pytest.mark.parametrize("documento", DOCUMENTOS)
def test_la_documentacion_escrita_a_mano_va_con_tildes(documento: str) -> None:
    """El README violaba veinte de las veintidos formas de la lista negra.

    Y la frase que enuncia la mision escribia mal la palabra de la mision:
    «con datos descargables y en espanol». Dos veces.
    """
    ruta = RAIZ / documento
    assert ruta.exists(), f"{documento} ya no existe: actualiza DOCUMENTOS"

    malas = [
        m
        for m in _palabras_malas(_prosa(ruta.read_text(encoding="utf-8")))
        if m not in SOLO_EN_GENERADORES
    ]

    assert not malas, f"{documento} sin tildes: {[(m, SIN_TILDE[m]) for m in malas]}"


@pytest.mark.parametrize("documento", DOCUMENTOS)
def test_la_documentacion_no_usa_publico_ni_publica_como_adjetivo(documento: str) -> None:
    """La mitad que la lista negra no puede ver sin contexto.

    Con frontera de palabra, no como subcadena: «cifra publicada» contiene
    «cifra publica» y es correcta. Es la misma trampa que `_palabras_malas`
    documenta para "publicas", y buscar la colocacion a pelo la reintroducia.
    """
    prosa = _prosa((RAIZ / documento).read_text(encoding="utf-8"))

    malas = [
        mala
        for mala in COLOCACIONES_MALAS
        if re.search(rf"(?<![\w-]){re.escape(mala)}(?![\w-])", prosa, flags=re.IGNORECASE)
    ]

    assert not malas, f"{documento}: {[(m, COLOCACIONES_MALAS[m]) for m in malas]}"


def test_los_disclaimers_van_en_espanol_completo() -> None:
    """Van en TODO artefacto (§1.2): si se rompen aqui, se rompen en todas partes."""
    malas = _palabras_malas("\n".join(DISCLAIMERS))
    assert not malas, f"disclaimers sin tildes: {[(m, SIN_TILDE[m]) for m in malas]}"


def test_el_reporte_markdown_va_en_espanol_completo(reporte_completo) -> None:  # type: ignore[no-untyped-def]
    """El `.md` es el artefacto mas citable del sistema."""
    malas = _palabras_malas(render_markdown(reporte_completo))
    assert not malas, f"report.md sin tildes: {[(m, SIN_TILDE[m]) for m in malas]}"


def test_el_hilo_para_redes_va_en_espanol_completo(reporte_completo) -> None:  # type: ignore[no-untyped-def]
    """Y este ademas se publica a mano, con el nombre del proyecto encima."""
    malas = _palabras_malas(render_thread_text(reporte_completo))
    assert not malas, f"hilo.txt sin tildes: {[(m, SIN_TILDE[m]) for m in malas]}"


def test_el_hilo_no_mete_una_preposicion_donde_no_cabe(reporte_completo) -> None:  # type: ignore[no-untyped-def]
    """«Sismo M7.8 **en** 27 km al SSE de Muisne».

    Los toponimos de USGS son casi siempre una distancia, y con "en" delante no
    se pueden leer. Con "Acapulco, México" si funcionaba, y de ahi que
    sobreviviera.
    """
    hilo = render_thread_text(reporte_completo)
    assert " en 27 km" not in hilo, f"la preposicion sigue ahi: {hilo[:120]!r}"
    assert "·" in hilo.splitlines()[0]


def test_el_hilo_escribe_la_magnitud_en_espanol(reporte_completo) -> None:  # type: ignore[no-untyped-def]
    """ "M7.8" en redes y "M7,8" en la pagina, del mismo evento."""
    assert "M7,8" in render_thread_text(reporte_completo)


def test_la_alerta_de_pager_se_traduce(reporte_completo) -> None:  # type: ignore[no-untyped-def]
    """USGS la publica en ingles y este documento se lee en espanol.

    El visor ya decia "naranja" mientras el `.md` decia "orange": la unica cifra
    ajena que el reporte cita salia de dos maneras segun donde se mirara.
    """
    md = render_markdown(reporte_completo)
    assert "naranja" in md, "la alerta de PAGER sigue sin traducirse"
    assert "**orange**" not in md
