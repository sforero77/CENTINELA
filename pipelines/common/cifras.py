"""Las cifras de los documentos salen de los datos, no de la memoria.

LOS DATOS CAMBIAN SOLOS Y LOS DOCUMENTOS NO.

`docs/PARA_INSTITUCIONES.md` decia «27 reportes, 2 en vivo» con 28 y 3 en el
catalogo, y su tabla de poblacion citaba cifras que la reconstruccion del
1-oct-2026 ya habia movido. Las pruebas lo vieron —siete en rojo— pero los
commits del bot no corren CI, asi que estuvieron rojas seis dias sin que nadie
se enterara. Copiar a mano y vigilar despues es perseguir el dato: cada reporte
nuevo vuelve a romper el documento.

Aqui se invierte. Cada cifra derivada vive entre dos marcas invisibles en el
Markdown renderizado::

    <!-- cifra:reportes_total -->28<!-- /cifra -->

y `centinela cifras` reescribe lo de dentro desde los manifests y
`reports/index.json`. `centinela cifras --comprobar` no escribe: sale con 1 si
algun documento quedo atras, que es lo que mira la suite.

Lo de fuera de las marcas es prosa y no se toca. Una cifra historica —«el
primero en vivo llego el 2-sep»— no lleva marca a proposito: no envejece.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .cobertura import NOMBRE_PAIS
from .formatting import format_number_es
from .paths import MANIFESTS_DIR, REPO_ROOT, REPORTS_DIR

#: Los documentos que llevan cifras marcadas. Un documento nuevo con marcas que
#: no este aqui no se regeneraria: `test_cifras_del_readme.py` lo vigila.
DOCUMENTOS: tuple[str, ...] = (
    "docs/PARA_INSTITUCIONES.md",
    "docs/datos/agregaciones.md",
)

MARCA = re.compile(r"<!-- cifra:(?P<nombre>[a-z0-9_]+) -->(?P<cuerpo>.*?)<!-- /cifra -->", re.S)


# --- Numeros en letras -------------------------------------------------------

# fmt: off
_UNIDADES = (
    "cero", "uno", "dos", "tres", "cuatro", "cinco", "seis", "siete", "ocho", "nueve",
    "diez", "once", "doce", "trece", "catorce", "quince", "dieciséis", "diecisiete",
    "dieciocho", "diecinueve", "veinte", "veintiuno", "veintidós", "veintitrés",
    "veinticuatro", "veinticinco", "veintiséis", "veintisiete", "veintiocho", "veintinueve",
)
# fmt: on
_DECENAS = {
    3: "treinta",
    4: "cuarenta",
    5: "cincuenta",
    6: "sesenta",
    7: "setenta",
    8: "ochenta",
    9: "noventa",
}


def en_letras(n: int, *, femenino: bool = False, apocope: bool = True) -> str:
    """El numero en letras, por defecto tal como va delante de un sustantivo.

    Delante de sustantivo el "uno" se apocopa —«veintiún reportes», «un
    país»— y en femenino es «una», «veintiuna»: «veintiuna veces». Como
    pronombre no: «veintiuno de los veintiocho reportes» (``apocope=False``).

    >>> en_letras(27)
    'veintisiete'
    >>> en_letras(21)
    'veintiún'
    >>> en_letras(21, apocope=False)
    'veintiuno'
    >>> en_letras(31, femenino=True)
    'treinta y una'
    >>> en_letras(100)
    'cien'
    """
    if not 0 <= n <= 199:
        raise ValueError(f"fuera del rango que estos documentos necesitan: {n}")
    if n == 100:
        return "cien"
    if n > 100:
        return f"ciento {en_letras(n - 100, femenino=femenino, apocope=apocope)}"
    if n < 30:
        palabra = _UNIDADES[n]
    else:
        decena, unidad = divmod(n, 10)
        palabra = _DECENAS[decena] + (f" y {_UNIDADES[unidad]}" if unidad else "")
    if palabra.endswith("uno"):
        if femenino:
            palabra = palabra[:-3] + "una"
        elif apocope:
            palabra = palabra[:-3] + ("ún" if n % 100 == 21 else "un")
    return palabra


# --- Los datos de los que salen ----------------------------------------------


@dataclass(frozen=True, slots=True)
class Datos:
    """Lo que los documentos citan, leido una vez."""

    manifests: dict[str, dict[str, Any]]
    indice: list[dict[str, Any]]
    totales_por_reporte: list[dict[str, float]]

    @classmethod
    def leer(cls, manifests_dir: Path = MANIFESTS_DIR, reports_dir: Path = REPORTS_DIR) -> Datos:
        manifests = {
            p.stem: yaml.safe_load(p.read_text(encoding="utf-8"))
            for p in sorted(manifests_dir.glob("*.yaml"))
        }
        indice = json.loads((reports_dir / "index.json").read_text(encoding="utf-8"))
        totales = [
            json.loads(p.read_text(encoding="utf-8"))["totales"]
            for p in sorted(reports_dir.glob("*/report.json"))
        ]
        return cls(manifests=manifests, indice=indice, totales_por_reporte=totales)

    def referencia(self, iso3: str) -> dict[str, Any]:
        ref: dict[str, Any] = self.manifests[iso3]["referencia_oficial"]
        return ref

    @property
    def construidos(self) -> list[str]:
        return [i for i in self.manifests if int(self.referencia(i).get("medido_ghs_pop") or 0) > 0]

    @property
    def en_vivo(self) -> int:
        return sum(1 for e in self.indice if not e.get("backtest"))

    @property
    def reconstrucciones(self) -> int:
        return sum(1 for e in self.indice if e.get("backtest"))

    @property
    def paises_con_reporte(self) -> int:
        return len({e["iso3"] for e in self.indice if e.get("iso3")})

    def sin_banda(self, banda: str) -> int:
        return sum(1 for t in self.totales_por_reporte if t[banda] == 0)


# --- Cada cifra, por nombre ----------------------------------------------------


def _desvio(medido: int, oficial: int) -> str:
    desvio = 100.0 * (medido - oficial) / oficial
    # El menos es U+2212: es prosa, no codigo.
    signo = "+" if desvio >= 0 else "−"
    return f"{signo}{abs(desvio):.2f} %".replace(".", ",")


def _tabla_poblacion(d: Datos) -> str:
    filas = []
    for iso3 in d.construidos:
        ref = d.referencia(iso3)
        medido, oficial = int(ref["medido_ghs_pop"]), int(ref["poblacion_2025"])
        fuente = str(ref.get("fuente", ""))
        # La ONU es la referencia por defecto; un instituto nacional se nombra.
        quien = "" if fuente.startswith("ONU") else f" ({fuente.split(',')[0].strip()})"
        filas.append(
            (
                100.0 * (medido - oficial) / oficial,
                f"| {NOMBRE_PAIS.get(iso3, iso3)} | {format_number_es(medido)} | "
                f"{format_number_es(oficial)}{quien} | {_desvio(medido, oficial)} |",
            )
        )
    cuerpo = "\n".join(fila for _, fila in sorted(filas))
    return f"\n\n| País | Medido | Referencia | Desvío |\n|---|---:|---:|---:|\n{cuerpo}\n\n"


def _tabla_estado(d: Datos) -> str:
    malla = sum(int(d.referencia(i)["medido_ghs_pop"]) for i in d.construidos)
    return (
        "\n\n| | |\n|---|---|\n"
        f"| Activos de exposición publicados | **{len(d.construidos)} de {len(d.manifests)}** |\n"
        f"| Reportes emitidos de punta a punta | **{len(d.indice)}**, en "
        f"{d.paises_con_reporte} países |\n"
        f"| De ellos, disparados en vivo | **{d.en_vivo}**; los otros {d.reconstrucciones} "
        "son reconstrucciones |\n"
        f"| Personas ya en la malla hexagonal | **{format_number_es(malla / 1e6, 1)} millones** |\n"
        "| Latencia objetivo, sismo → reporte | p50 ≤ 60 min · lo medido, en `/status` |\n\n"
    )


def _veces(n: int) -> str:
    return "una vez" if n == 1 else f"{en_letras(n, femenino=True)} veces"


CIFRAS: dict[str, Callable[[Datos], str]] = {
    "tabla_estado": _tabla_estado,
    "tabla_poblacion": _tabla_poblacion,
    "reconstrucciones_en_letras": lambda d: en_letras(d.reconstrucciones),
    "en_vivo_veces": lambda d: _veces(d.en_vivo),
    # El primero es pronombre («dieciocho de los...») y no se apocopa; el
    # segundo va delante de «reportes»/«eventos» y si.
    "sin_mmi7_de_total": lambda d: (
        f"{en_letras(d.sin_banda('pop_mmi7p'), apocope=False)} de los "
        f"{en_letras(len(d.totales_por_reporte))}"
    ),
    "sin_mmi7_de_total_titulo": lambda d: (
        f"{en_letras(d.sin_banda('pop_mmi7p'), apocope=False).capitalize()} de "
        f"{en_letras(len(d.totales_por_reporte))}"
    ),
    # «De ellos, nueve tampoco»: pronombre.
    "sin_mmi6": lambda d: en_letras(d.sin_banda("pop_mmi6p"), apocope=False),
}


# --- Reescribir y comprobar ----------------------------------------------------


class CifraDesconocidaError(KeyError):
    """Un documento marca una cifra que este modulo no sabe calcular."""


def regenerar(texto: str, datos: Datos) -> str:
    """Devuelve el texto con cada cifra marcada recalculada."""

    def sustituir(m: re.Match[str]) -> str:
        nombre = m["nombre"]
        if nombre not in CIFRAS:
            raise CifraDesconocidaError(nombre)
        return f"<!-- cifra:{nombre} -->{CIFRAS[nombre](datos)}<!-- /cifra -->"

    return MARCA.sub(sustituir, texto)


def actualizar(*, escribir: bool, raiz: Path = REPO_ROOT, datos: Datos | None = None) -> list[str]:
    """Regenera los documentos y devuelve los que cambiaron (o cambiarian)."""
    datos = datos or Datos.leer()
    cambiados = []
    for nombre in DOCUMENTOS:
        ruta = raiz / nombre
        crudo = ruta.read_bytes().decode("utf-8")
        # El fin de linea del fichero manda: en Windows git los saca en CRLF y
        # en CI en LF. Reescribir en el otro convertiria el documento entero en
        # un diff de todas sus lineas.
        fin = "\r\n" if "\r\n" in crudo else "\n"
        antes = crudo.replace("\r\n", "\n")
        despues = regenerar(antes, datos)
        if despues != antes:
            cambiados.append(nombre)
            if escribir:
                ruta.write_bytes(despues.replace("\n", fin).encode("utf-8"))
    return cambiados
