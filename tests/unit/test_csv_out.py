"""CSV municipal con cabecera HXL (T1.3)."""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from pipelines.p3_report.csv_out import HXL_HEADERS, write_adm2_csv


def test_cabecera_hxl_en_la_segunda_fila(tmp_path: Path) -> None:
    filas = [
        {"usgs_id": "us7000sint", "adm2_id": "27001", "nombre": "Quibdo", "pop_mmi7p": 118000.5}
    ]
    path = write_adm2_csv(filas, tmp_path / "adm2.csv")
    with path.open(encoding="utf-8") as fh:
        leidas = list(csv.reader(fh))
    assert leidas[0] == list(HXL_HEADERS)
    assert leidas[1] == list(HXL_HEADERS.values())
    assert leidas[2][leidas[0].index("nombre")] == "Quibdo"


#: Las etiquetas HXL que un integrador cruza de verdad, **escritas a mano**.
#:
#: La prueba de arriba compara el fichero contra la misma constante con la que
#: se escribio: no puede fallar por una etiqueta mal puesta, porque los dos
#: lados cambian juntos. Renombrar `#population+mmi7` a cualquier cosa la dejaba
#: en verde, y HXL existe precisamente para que un tercero mapee columnas sin
#: leer nuestro codigo.
#:
#: No se fijan las veinticinco: se fijan las que rompen a alguien si cambian.
HXL_FIJADAS: dict[str, str] = {
    "adm2_id": "#adm2+code",
    "nombre": "#adm2+name",
    "lon": "#geo+lon",
    "lat": "#geo+lat",
    "pop_mmi6p": "#population+mmi6",
    "pop_mmi7p": "#population+mmi7",
    "pop_65p_mmi7p": "#population+age65+mmi7",
    "bld_mmi7p": "#infra+buildings+mmi7",
    "health_mmi7p": "#infra+health+mmi7",
    "edu_mmi7p": "#infra+education+mmi7",
    "road_km_mmi7p": "#infra+roads+km+mmi7",
}


@pytest.mark.parametrize(("columna", "etiqueta"), sorted(HXL_FIJADAS.items()))
def test_la_etiqueta_hxl_es_la_que_un_tercero_espera(columna: str, etiqueta: str) -> None:
    """Contra un valor escrito aqui, no contra el que produce el codigo."""
    assert HXL_HEADERS[columna] == etiqueta, (
        f"la etiqueta HXL de {columna} cambio: quien mapee columnas por ella dejara de encontrarla"
    )


def test_toda_columna_publicada_lleva_etiqueta_hxl() -> None:
    """Una columna sin etiqueta no la ve un lector de HXL."""
    sin_etiqueta = [c for c, e in HXL_HEADERS.items() if not e.startswith("#")]
    assert sin_etiqueta == []


def test_cifras_exactas_no_redondeadas(tmp_path: Path) -> None:
    """RF-06: la prosa redondea, el CSV nunca."""
    path = write_adm2_csv([{"adm2_id": "27001", "pop_mmi7p": 118000.5}], tmp_path / "a.csv")
    assert "118000.5" in path.read_text(encoding="utf-8")


def test_columnas_desconocidas_no_se_pierden_en_silencio(tmp_path: Path) -> None:
    """Esta prueba fijaba lo contrario: que una columna desconocida se ignorase.

    Era justo el fallo. Una agregacion nueva del SQL desaparecia del CSV sin
    aviso, y la prueba lo celebraba.
    """
    with pytest.raises(ValueError, match="columna_rara"):
        write_adm2_csv([{"adm2_id": "27001", "columna_rara": 1}], tmp_path / "a.csv")
    assert not (tmp_path / "a.csv").exists(), "no puede quedar un fichero a medias"
