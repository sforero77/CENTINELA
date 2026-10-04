"""`docs/arquitectura/contratos-de-datos.md` dice las claves que se publican de verdad.

El documento se declara "el contrato" y se habia quedado atras: describia un
`index.json` de 21 entradas cuando habia 27, y en las claves raiz de
`report.json` faltaban `ground_failure_usgs` —publicado desde el 1-sep-2026— y
`licencia`. Quien integrase leyendo el contrato no sabia que esas dos existian.

Se comparan las listas del documento con lo que el codigo emite, no con otra
lista escrita a mano: el esquema para el reporte, `rebuild_index` corrido de
verdad para el indice. Y el numero de entradas no se escribe: es una cifra que
caduca con cada sismo.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from pipelines.p3_report.model import Report

RAIZ = Path(__file__).parent.parent.parent
CONTRATO = RAIZ / "docs" / "arquitectura" / "contratos-de-datos.md"
ESQUEMA = RAIZ / "schemas" / "report-1.0.schema.json"


def _claves_del_parrafo(despues_de: str) -> set[str]:
    """Los identificadores entre acentos graves del parrafo que sigue a una frase.

    Revienta si la frase no esta: un parrafo no encontrado no puede pasar por
    una lista vacia que coincide con nada.
    """
    texto = CONTRATO.read_text(encoding="utf-8").replace("\r\n", "\n")
    encontrada = texto.find(despues_de)
    assert encontrada >= 0, f"el contrato ya no dice {despues_de!r}: actualizar esta prueba"
    # Tras un encabezado el parrafo empieza despues de la linea en blanco.
    inicio = encontrada + len(despues_de)
    while texto[inicio] in " \n":
        inicio += 1
    fin = texto.find("\n\n", inicio)
    claves = set(re.findall(r"`([a-z0-9_]+)`", texto[inicio:fin]))
    assert claves, f"el parrafo de {despues_de!r} no nombra ninguna clave"
    return claves


def test_las_claves_raiz_del_reporte_son_las_del_esquema() -> None:
    documentadas = _claves_del_parrafo("y sus claves raíz son:")
    esquema = set(json.loads(ESQUEMA.read_text(encoding="utf-8"))["properties"])

    assert documentadas == esquema, (
        f"el contrato omite {sorted(esquema - documentadas)} y nombra de mas "
        f"{sorted(documentadas - esquema)}"
    )


def test_las_claves_del_indice_son_las_que_emite_rebuild_index(
    reporte: Report, tmp_path: Path
) -> None:
    from pipelines.p3_report.run import rebuild_index

    reporte.save(tmp_path / reporte.event.usgs_id / "report.json")
    indice = rebuild_index(tmp_path)
    entradas = json.loads(indice.ruta.read_text(encoding="utf-8"))
    assert len(entradas) == 1
    emitidas = set(entradas[0])

    documentadas = _claves_del_parrafo("### `reports/index.json`: el catálogo")

    assert documentadas == emitidas, (
        f"el contrato omite {sorted(emitidas - documentadas)} y nombra de mas "
        f"{sorted(documentadas - emitidas)}"
    )


def test_el_contrato_no_cuenta_entradas() -> None:
    """«Una lista de 21 entradas» era cierto el dia que se escribio."""
    texto = CONTRATO.read_text(encoding="utf-8")

    assert not re.search(r"\b\d+ entradas\b", texto)
    assert not re.search(r"\blos \d+ backtests\b", texto)
