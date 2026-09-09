"""La tabla de cifras del README, generada desde el reporte publicado.

LA PORTADA SE DESINCRONIZO TRES VECES, Y LA TERCERA TUMBO `main`.

El README publica la tabla del backtest del Choco. Tres veces se quedo atras
del artefacto que dice reproducir:

* **25-ago-2026**: se reconstruyo el activo y cinco filas quedaron viejas — los
  kilometros de via, por un factor de seis. De ahi salio
  `tests/unit/test_cifras_del_readme.py`, que falla si la tabla se separa del
  `report.json`.
* **7-sep-2026**: la reconstruccion volvio a mover cifras escritas a mano.
* **8-sep-2026**: el repaso dejo de excluir los backtests, re-emitio el reporte
  de ShakeMap v8 a v9 —`pop_mmi7p` subio un 26,6 %— y **`main` se quedo en
  rojo**, porque el bot publica el reporte y nadie actualiza la portada.

La prueba cumplio su trabajo las tres veces: aviso. Pero avisar no es
suficiente cuando quien re-emite es un workflow a las tres de la manana. Una
tabla escrita a mano no se arregla con disciplina ni con una prueba; se arregla
dejando de escribirla a mano.

Este modulo es el generador, y `test_cifras_del_readme.py` importa de aqui su
mapeo para que la prueba y el generador no puedan discrepar. `impact.yml` lo
corre antes de commitear, asi que la tabla viaja en el **mismo commit** que
re-emite el reporte.

**Lo que este modulo NO puede arreglar** es la prosa: que Cali entrara primera
al top de municipios con el v9, o que el acotamiento con PAGER dejara de
cumplirse en MMI≥6, son cambios de argumento y los escribe una persona. Para
eso siguen las pruebas, que ahora fallan solas y con el motivo escrito.
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path

from ..common.formatting import format_number_es
from ..common.paths import REPORTS_DIR

#: El reporte que la portada reproduce. Es el backtest que motiva el proyecto,
#: y el unico cuyas cifras estan escritas en el README.
EVENTO_DE_PORTADA = "us6000tjl2"

#: Fila del README -> campo de `totales`. **Fuente unica**: la prueba importa
#: esta misma tupla, asi que no puede quedarse describiendo otra tabla.
#: Las etiquetas van con tildes: hay una prueba que lo exige en todo lo
#: publicado.
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

#: Las dos filas que no salen de `totales` sino de contar municipios con
#: poblacion en el `adm2.csv`. El CSV trae una fila por municipio que el
#: ShakeMap **toca** desde MMI 5,0, asi que contar filas daria otro universo:
#: de las 299 de `us6000tjl2`, 188 estan enteras en cero.
FILAS_MUNICIPIOS: tuple[tuple[str, str], ...] = (
    ("Municipios con población en MMI≥6", "pop_mmi6p"),
    ("De ellos, con población en MMI≥7", "pop_mmi7p"),
)


@dataclass(frozen=True, slots=True)
class CambioDePortada:
    """Una fila que la portada publicaba distinto del artefacto."""

    etiqueta: str
    antes: str
    ahora: str

    def __str__(self) -> str:
        return f"{self.etiqueta}: {self.antes} -> {self.ahora}"


def _fila(etiqueta: str, valor: str) -> str:
    return f"| {etiqueta} | **{valor}** |"


def cifras_publicadas(reports_root: Path | None = None) -> dict[str, str]:
    """Lo que el reporte publicado dice hoy, ya formateado como va en la tabla."""
    raiz = reports_root or REPORTS_DIR
    directorio = raiz / EVENTO_DE_PORTADA
    totales = json.loads((directorio / "report.json").read_text(encoding="utf-8"))["totales"]

    valores = {
        etiqueta: format_number_es(round(float(totales[campo]))) for etiqueta, campo in FILAS
    }

    with (directorio / "adm2.csv").open(encoding="utf-8") as fh:
        # La segunda linea del CSV son las etiquetas HXL, no un municipio.
        filas = [f for f in csv.DictReader(fh) if not str(f["usgs_id"]).startswith("#")]
    for etiqueta, columna in FILAS_MUNICIPIOS:
        valores[etiqueta] = format_number_es(sum(1 for f in filas if float(f[columna] or 0) > 0))

    return valores


def sincronizar_portada(
    readme: Path,
    *,
    reports_root: Path | None = None,
    escribir: bool = True,
) -> list[CambioDePortada]:
    """Reescribe la tabla del README con las cifras del reporte publicado.

    Devuelve lo que cambio. Con ``escribir=False`` solo informa, que es como lo
    usa la comprobacion: sirve igual para arreglar y para preguntar.

    **Solo toca filas que ya existen.** Si una etiqueta no esta en el README no
    la inventa: eso seria reescribir la portada por su cuenta, y lo que aqui se
    automatiza es mantener al dia una tabla que alguien decidio publicar, no
    decidir que se publica.
    """
    texto = readme.read_text(encoding="utf-8")
    cambios: list[CambioDePortada] = []

    for etiqueta, valor in cifras_publicadas(reports_root).items():
        nueva = _fila(etiqueta, valor)
        if nueva in texto:
            continue
        # `| <etiqueta> | **<lo que sea>** |`, una sola vez.
        marca = f"| {etiqueta} | **"
        i = texto.find(marca)
        if i == -1:
            continue
        fin = texto.index("\n", i)
        antigua = texto[i:fin]
        anterior = antigua.split("**")[1] if "**" in antigua else antigua
        cambios.append(CambioDePortada(etiqueta=etiqueta, antes=anterior, ahora=valor))
        texto = texto[:i] + nueva + texto[fin:]

    if cambios and escribir:
        readme.write_text(texto, encoding="utf-8")
    return cambios
