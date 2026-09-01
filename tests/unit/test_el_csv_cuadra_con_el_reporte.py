"""El `adm2.csv` publicado suma lo que dice el `report.json` de al lado.

EL HUECO QUE CIERRA. `test_ground_failure_cuadra.py` vigila el **SQL**: que las
dos consultas cuenten sobre las mismas celdas. Nadie vigilaba el **artefacto**.

Y esa distinción no es teórica: el SQL se arregló y los veintiún `adm2.csv`
publicados se quedaron con la columna vieja, calculada desde MMI 5,0. Medido
sobre la página publicada el 1-sep-2026, quince de los veintiuno no cuadran, y
Tehuantepec se pasa en 229.663 personas. Quien baje el CSV para repartir ayuda y
lo contraste contra la cifra nacional del reporte encuentra hoy una diferencia
que nadie sabe explicar.

Es la misma familia que este proyecto ya tiene nombrada —la defensa escrita y el
artefacto sin tocar— y la única forma de que no se repita es comprobar el
fichero, no el código que lo escribe.

POR QUE HAY UNA LISTA DE PENDIENTES Y NO UNA TOLERANCIA. Rehacer un `adm2.csv`
exige correr P2 entero por evento contra el activo de exposición de su país, que
no vive en el repositorio: `regenerar-textos` y `regenerar-mapas` no llegan,
porque los dos son derivados del `report.json` y esta columna no. Hasta que se
re-emitan hay quince ficheros que fallan, y esconderlos tras un margen sería
exactamente lo que este proyecto le reprocha a las tolerancias que nadie ve.

Así que están **enumerados**, con nombre y apellido, y la lista sólo puede
encoger: `test_la_lista_de_pendientes_no_se_pudre` falla si alguno ya cuadra y
sigue en la lista. Cuando quede vacía, la guardia es total.

Cómo se vacía, en `docs/OPERACION.md`: un despacho de `impact.yml` por evento
con `backtest` y `reprocesar`.
"""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path

import pytest

RAIZ = Path(__file__).parent.parent.parent
REPORTES = RAIZ / "reports"

#: Columna del CSV -> campo de `totales`. Las dos que arrastran el corte viejo.
COLUMNAS: tuple[tuple[str, str], ...] = (
    ("lq_pop", "pop_lq_alta"),
    ("ls_pop", "pop_ls_alta"),
)

#: Los que todavía llevan la columna calculada desde MMI 5,0. **Sólo puede
#: encoger.** Se vacía re-emitiendo cada evento; ver el módulo.
PENDIENTES_DE_REEMITIR: frozenset[str] = frozenset(
    {
        "us1000gez7",
        "us20005j32",
        "us2000ahv0",
        "us2000bmhe",
        "us2000j6hy",
        "us60003sc0",
        "us6000hf75",
        "us6000t7zc",
        "us6000t7zp",
        "us6000tjl2",
        "us70003t2n",
        "us7000455l",
        "us7000f93v",
        "us7000jl3s",
        "us7000nr0v",
    }
)


def _eventos() -> list[str]:
    return sorted(p.parent.name for p in REPORTES.glob("*/report.json"))


def _descuadres(usgs_id: str) -> list[str]:
    """Las columnas de este evento cuya suma municipal no da la cifra nacional."""
    directorio = REPORTES / usgs_id
    reporte = json.loads((directorio / "report.json").read_text(encoding="utf-8"))
    csv_path = directorio / "adm2.csv"
    if not csv_path.is_file():
        return []

    # La segunda fila del CSV son las etiquetas HXL, no un municipio.
    filas = [
        f
        for f in csv.DictReader(io.StringIO(csv_path.read_text(encoding="utf-8")))
        if f.get("adm2_id", "").strip() and not f["adm2_id"].startswith("#")
    ]
    if not filas:
        return []

    fallos = []
    for prefijo, campo in COLUMNAS:
        columna = next((c for c in filas[0] if c.startswith(prefijo)), None)
        if columna is None:
            continue
        suma = sum(float(f[columna] or 0) for f in filas)
        nacional = float(reporte["totales"].get(campo, 0.0))
        # Una persona de margen por el redondeo del CSV, no por tolerancia: la
        # columna se escribe con decimales y la suma acumula error de coma
        # flotante sobre cientos de municipios.
        if abs(suma - nacional) > 1.0:
            fallos.append(
                f"{columna}: el CSV suma {suma:,.0f} y el reporte publica "
                f"{nacional:,.0f} en {campo} (diferencia {suma - nacional:+,.0f})"
            )
    return fallos


@pytest.mark.parametrize("usgs_id", _eventos())
def test_el_csv_municipal_suma_la_cifra_nacional(usgs_id: str) -> None:
    """Quien baje el CSV y lo sume tiene que llegar a la cifra del reporte."""
    if usgs_id in PENDIENTES_DE_REEMITIR:
        pytest.skip("pendiente de re-emitir; ver PENDIENTES.md 2.1.septies")
    fallos = _descuadres(usgs_id)
    assert not fallos, f"{usgs_id}: " + " · ".join(fallos)


def test_la_lista_de_pendientes_no_se_pudre() -> None:
    """La lista sólo puede encoger.

    Sin esto, un evento re-emitido se quedaría en la lista para siempre y su
    guardia no volvería a correr — que es como una excepción temporal se vuelve
    permanente sin que nadie lo decida.
    """
    ya_cuadran = sorted(e for e in PENDIENTES_DE_REEMITIR if not _descuadres(e))
    assert not ya_cuadran, (
        "estos ya cuadran y siguen en PENDIENTES_DE_REEMITIR, así que su guardia "
        f"no corre: {ya_cuadran}. Quítalos de la lista."
    )


def test_la_lista_no_nombra_eventos_que_no_existen() -> None:
    """Un id mal copiado dejaría un evento sin vigilar sin que nada lo diga."""
    fantasmas = sorted(PENDIENTES_DE_REEMITIR - set(_eventos()))
    assert not fantasmas, f"la lista nombra eventos que no están publicados: {fantasmas}"
