"""Lo que se publica en espanol se publica **con** tildes y con enes.

EL HUECO QUE CIERRA. `markdown.py`, `social.py` y `DISCLAIMERS` llevaban las
tildes puestas en el repositorio y los ficheros servidos seguian diciendo
"Exposicion no es dano": se emitieron el 25-ago-2026, antes de esa correccion, y
nada volvia a tocarlos. El hilo para redes —el unico artefacto de todo el
sistema que un humano publica a mano— abria con "Reporte automatico de
EXPOSICION estimada" y cerraba con "Exposicion no es dano", que en espanol no es
una frase: "dano" no es una palabra.

Esta prueba no comprueba el fichero publicado, que puede estar rancio: comprueba
el generador. Que lo publicado se ponga al dia es trabajo de
`centinela regenerar-textos`, y `test_frescura` es quien vigila que se haya
corrido.

POR QUE UNA LISTA NEGRA Y NO UN DETECTOR GENERICO. "Se publica" y "se publico"
son las dos correctas y solo se distinguen por el sentido; un detector de
"palabras que deberian llevar tilde" daria falsos positivos en cada linea. La
lista son las formas que de verdad se colaron, que es contra lo que hay que
defenderse.
"""

from __future__ import annotations

import re

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
