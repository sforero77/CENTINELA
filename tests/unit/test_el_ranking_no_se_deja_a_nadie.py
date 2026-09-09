"""La tabla «municipios más expuestos» tiene que ser la de los más expuestos.

Guardia de catalogo: corre contra los reportes ya publicados, no contra una
fixture. La razon es que el fallo que cierra no se veia en ninguna prueba
unitaria — las dos mitades eran correctas y lo que estaba mal era la costura
entre el SQL que seleccionaba quince municipios y la plantilla que los
reordenaba por otra columna.

En `reports/us20005j32` (Muisne, M7,8) faltaba **Manta, con 265.263 personas en
MMI>=7**, que seria el tercero de la tabla, y en su lugar figuraba Eloy Alfaro
con 6.605. Faltaban tambien El Carmen (131.651), El Empalme (87.249) y
Montecristi (77.993). En `reports/us6000t7zp` faltaban Sucre (352.686) y Plaza
(172.919).

Quien reparte ayuda leyendo esa tabla despacha al municipio equivocado, y la
cifra que le hizo equivocarse estaba publicada correctamente dos ficheros mas
alla, en el `adm2.csv` del mismo directorio.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from pipelines.common.constants import TOP_ADM2_COUNT
from pipelines.p3_report.model import Report

RAIZ = Path(__file__).parent.parent.parent
REPORTES = sorted(p for p in (RAIZ / "reports").glob("*/report.json"))


def _ids(reporte: Path) -> str:
    return reporte.parent.name


def _filas(reporte: Path) -> list[dict[str, str]]:
    csv_path = reporte.parent / "adm2.csv"
    with csv_path.open(encoding="utf-8") as fh:
        return [r for r in csv.DictReader(fh) if not r["usgs_id"].startswith("#")]


def _cifra(fila: dict[str, str], banda: int) -> float:
    return float(fila[f"pop_mmi{banda}p"] or 0.0)


def test_hay_reportes_que_comprobar() -> None:
    """Si el glob se queda vacio, todo lo de abajo pasa sin mirar nada."""
    assert len(REPORTES) >= 27


@pytest.mark.parametrize("reporte", REPORTES, ids=_ids)
def test_nadie_fuera_de_la_tabla_supera_al_ultimo_de_la_tabla(reporte: Path) -> None:
    """La propiedad que define un top-N: no puede haber un N+1 mayor fuera."""
    report = Report.from_dict(json.loads(reporte.read_text(encoding="utf-8")))
    banda = report.totales.banda_publicada
    en_tabla = {m.adm2_id for m in report.top_municipios}

    dentro = report.top_municipios
    if not dentro:
        return  # un evento que no alcanza poblacion no publica tabla

    corte = min((m.pop_banda or m.pop_mmi7p) if banda == 6 else m.pop_mmi7p for m in dentro)
    intrusos = [
        (f["nombre"], _cifra(f, banda))
        for f in _filas(reporte)
        if f["adm2_id"] not in en_tabla and _cifra(f, banda) > corte
    ]
    assert not intrusos, (
        f"quedan fuera de la tabla municipios con mas poblacion en MMI>={banda} que el "
        f"ultimo que si esta ({corte:,.0f}): {sorted(intrusos, key=lambda x: -x[1])[:5]}"
    )


@pytest.mark.parametrize("reporte", REPORTES, ids=_ids)
def test_la_tabla_trae_los_quince_primeros_si_los_hay(reporte: Path) -> None:
    """Un top-15 con menos de quince filas solo vale si no hay quince candidatos."""
    report = Report.from_dict(json.loads(reporte.read_text(encoding="utf-8")))
    banda = report.totales.banda_publicada
    con_poblacion = [f for f in _filas(reporte) if _cifra(f, banda) > 0]
    esperadas = min(len(con_poblacion), TOP_ADM2_COUNT)
    publicadas = len([m for m in report.top_municipios if (m.pop_banda or m.pop_mmi7p) > 0])
    assert publicadas >= esperadas, (
        f"hay {len(con_poblacion)} municipios con poblacion en MMI>={banda} y la tabla "
        f"publica {publicadas}"
    )


@pytest.mark.parametrize("reporte", REPORTES, ids=_ids)
def test_el_csv_empieza_por_el_municipio_mas_expuesto(reporte: Path) -> None:
    """El CSV es "la tabla que consume el mundo" y se abre por arriba.

    Se volcaba con `ORDER BY pop_mmi7p DESC` fijo, que en los reportes que no
    alcanzan esa banda es una columna de ceros: en dieciseis de los veintisiete
    la primera fila no era el municipio mas expuesto. En `us2000ahv0`, Juchitan
    —109.670 personas en MMI>=6— salia en la fila 43 de 92, y la primera fila
    era un municipio con 9.617.
    """
    report = Report.from_dict(json.loads(reporte.read_text(encoding="utf-8")))
    banda = report.totales.banda_publicada
    filas = _filas(reporte)
    if not filas or _cifra(filas[0], banda) <= 0:
        return  # ningun municipio con poblacion en la banda: el orden da igual

    mayor = max(_cifra(f, banda) for f in filas)
    assert _cifra(filas[0], banda) == pytest.approx(mayor), (
        f"la primera fila del adm2.csv tiene {_cifra(filas[0], banda):,.0f} personas en "
        f"MMI>={banda} y el maximo del fichero es {mayor:,.0f}"
    )
    if report.top_municipios:
        assert filas[0]["adm2_id"] == report.top_municipios[0].adm2_id, (
            "el CSV y la tabla del reporte no empiezan por el mismo municipio"
        )
