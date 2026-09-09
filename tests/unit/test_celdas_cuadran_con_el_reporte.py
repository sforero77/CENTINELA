"""`celdas.json` y `report.json` tienen que hablar del mismo conjunto.

Una celda r7 tiene siete hijas r8. `mmi` era el maximo de las siete y `pop`
sumaba las siete enteras, asi que una celda rotulada «MMI 7,2» traia tambien a
la gente de sus hijas a MMI 6,1. Quien sumara `pop` sobre las celdas con
`mmi >= 7` —que es lo que hace cualquiera que descargue el fichero— contaba
personas que no estan en esa banda.

Medido sobre lo publicado antes del arreglo:

    us6000t7zp   celdas.json 2.596.894   report.json 2.276.854   +320.040 (+14,1 %)
    us2000bmhe   celdas.json      8.983   report.json      7.401   +1.582  (+21,4 %)
    us6000tjl2   celdas.json 2.522.181   report.json 2.424.287   +97.894  (+4,0 %)

Las dos mitades eran correctas por separado. Lo que no cuadraba era el conjunto
sobre el que se calculaba cada una — y eso no se ve leyendo ninguno de los dos
ficheros solo.

ESTA PRUEBA ES UN TRINQUETE. `celdas.json` no se puede regenerar sin volver a
correr el impacto contra el activo del pais, asi que los ficheros ya publicados
conservan la forma vieja hasta que su reporte se re-emita. El guardia exige
igualdad exacta en los que ya llevan las columnas nuevas, y **fija cuantos
quedan por migrar**: ese numero solo puede bajar.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

RAIZ = Path(__file__).parent.parent.parent
REPORTES = sorted(p for p in (RAIZ / "reports").glob("*/report.json"))

#: Ficheros publicados que todavia no traen `pop7`. Se emitieron antes del
#: arreglo y se migran al re-emitir su reporte. **Solo puede bajar.**
#:
#: Llego a cero el 7-sep-2026, cuando se re-emitieron los veintisiete contra los
#: activos reconstruidos. Con el trinquete apretado, publicar una malla de la
#: forma vieja vuelve a poner esto en rojo — que es justo para lo que existia.
SIN_MIGRAR = 0


def _celdas(reporte: Path) -> dict[str, Any] | None:
    ruta = reporte.parent / "celdas.json"
    if not ruta.exists():
        return None
    datos: dict[str, Any] = json.loads(ruta.read_text(encoding="utf-8"))
    return datos


def _suma(datos: dict[str, Any], columna: str) -> float:
    if columna not in datos["columnas"]:
        return float("nan")
    i = datos["columnas"].index(columna)
    return sum(float(c[i] or 0) for c in datos["celdas"])


def _ids(reporte: Path) -> str:
    return reporte.parent.name


def test_el_trinquete_no_puede_subir() -> None:
    """Cuantos `celdas.json` publicados siguen sin la poblacion por banda.

    Si esto falla porque el numero BAJO, actualizar la constante: es la senal
    de que un reporte se re-emitio y su malla ya cuadra. Si falla porque SUBIO,
    alguien publico una malla con la forma vieja.
    """
    viejos = [
        _ids(r)
        for r in REPORTES
        if (datos := _celdas(r)) is not None and "pop7" not in datos["columnas"]
    ]
    assert len(viejos) <= SIN_MIGRAR, (
        f"hay {len(viejos)} mallas sin `pop7` y el trinquete declara {SIN_MIGRAR}: "
        f"se publico una con la forma vieja. {viejos}"
    )
    if len(viejos) < SIN_MIGRAR:
        pytest.fail(
            f"quedan {len(viejos)} mallas sin migrar y la constante dice {SIN_MIGRAR}. "
            f"Bajar SIN_MIGRAR a {len(viejos)}: el trinquete solo sirve si se aprieta."
        )


def _celdas_con(datos: dict[str, Any], columna: str) -> int:
    """Cuantas celdas aportan algo a esa columna. Es la cota del redondeo."""
    if columna not in datos["columnas"]:
        return 0
    i = datos["columnas"].index(columna)
    return sum(1 for c in datos["celdas"] if float(c[i] or 0) != 0)


@pytest.mark.parametrize("reporte", REPORTES, ids=_ids)
def test_la_poblacion_por_banda_cuadra_con_el_reporte(reporte: Path) -> None:
    """Sumar `pop7` sobre el fichero da el `pop_mmi7p` del reporte.

    NO EXACTO, Y NO PUEDE SERLO. `celdas.py` publica `round(sum(pop_total)
    FILTER (WHERE mmi_max >= 7))`: **cada celda va redondeada a la unidad**, asi
    que sumar cinco mil enteros redondeados no da el total exacto ni deberia. La
    prueba exigia `rel=1e-6` y decia «Exacto» en su docstring; paso durante meses
    porque el trinquete se saltaba casi todas las mallas —eran de la forma
    vieja, sin `pop7`— y solo miraba las pocas migradas.

    Al re-emitir los veintisiete reportes el 7-sep-2026 todas migraron, y las
    ocho que quedaron dentro del umbral por suerte dejaron de estarlo: los
    desvios medidos van de 1,4 a 15 personas sobre cientos de miles, hasta el
    0,0029 %, o sea treinta veces la tolerancia que pedia.

    Lo que el mecanismo si garantiza es **media persona por celda**: el error de
    redondear N celdas no puede pasar de N/2. Esa es la cota que se comprueba, y
    sigue cazando lo que esta prueba existe para cazar —una celda que falta o
    que se cuenta dos veces mueve su poblacion entera, que son miles.
    """
    datos = _celdas(reporte)
    if datos is None or "pop7" not in datos["columnas"]:
        pytest.skip("malla anterior a la poblacion por banda; la cuenta el trinquete")

    totales = json.loads(reporte.read_text(encoding="utf-8"))["totales"]
    for columna, campo in (("pop7", "pop_mmi7p"), ("pop8", "pop_mmi8p")):
        suma = _suma(datos, columna)
        esperado = float(totales[campo])
        cota = max(0.5 * _celdas_con(datos, columna), 0.5)
        assert abs(suma - esperado) <= cota, (
            f"{columna}: la malla suma {suma:,.1f} y el reporte publica "
            f"{esperado:,.1f}. La diferencia ({suma - esperado:+,.1f}) pasa de "
            f"media persona por celda ({cota:,.1f} sobre "
            f"{_celdas_con(datos, columna)} celdas), asi que no es el redondeo: "
            f"o falta una celda o se esta contando dos veces"
        )


@pytest.mark.parametrize("reporte", REPORTES, ids=_ids)
def test_la_malla_declara_sobre_que_conjunto_se_calculo_cada_columna(reporte: Path) -> None:
    """Sin la nota, quien descargue el fichero tiene que adivinarlo.

    Y la respuesta no es la misma para todas las columnas: `pop7` es por banda y
    `bld` es el agregado de la celda entera.
    """
    datos = _celdas(reporte)
    if datos is None or "pop7" not in datos["columnas"]:
        pytest.skip("malla anterior a la nota; la cuenta el trinquete")

    assert "no se pueden sumar filtrando por `mmi`" in datos["nota"]


@pytest.mark.geo
def test_una_celda_mixta_no_cuenta_a_sus_hijas_de_otra_banda() -> None:
    """El mecanismo, en una celda construida a mano.

    Dos hijas r8 dentro del mismo padre r7: una a MMI 7,2 con 100 personas y
    otra a MMI 6,1 con 900. La celda se rotula MMI 7,2 y antes traia `pop`=1000,
    asi que sumar por banda daba 1.000 personas en MMI>=7 donde hay 100.
    """
    from pipelines.p2_impact.exposure_join import connect
    from pipelines.p3_report.celdas import SQL_CELDAS

    con = connect()
    # Dos hijas del mismo padre r7: se toman de una celda real y su vecina.
    hijas = con.execute(
        "SELECT h3_cell_to_children(h3_latlng_to_cell(4.0, -75.0, 7), 8) AS h"
    ).fetchone()[0][:2]
    con.execute(
        "CREATE OR REPLACE TABLE impact_h3 AS SELECT * FROM (VALUES "
        f"({hijas[0]}::UBIGINT, 7.2, 100.0), ({hijas[1]}::UBIGINT, 6.1, 900.0)"
        ") AS t(h3_08, mmi_max, pop_total)"
    )
    for columna in ("bld_count", "built_m2", "health_count", "edu_count"):
        con.execute(f"ALTER TABLE impact_h3 ADD COLUMN {columna} DOUBLE DEFAULT 0.0")
    for columna in ("road_km_primary", "road_km_secondary", "road_km_other"):
        con.execute(f"ALTER TABLE impact_h3 ADD COLUMN {columna} DOUBLE DEFAULT 0.0")

    fila = con.execute(SQL_CELDAS.format(resolucion=7, mmi_minimo=6.0)).fetchone()
    columnas = ["h3", "mmi", "pop", "pop7", "pop8", "bld", "built_m2", "vias_km", "salud", "edu"]
    # DuckDB devuelve `round()` como DECIMAL; el fichero lo escribe como numero.
    valores = {
        k: (float(v) if v is not None else 0.0) for k, v in zip(columnas[1:], fila[1:], strict=True)
    }

    assert valores["mmi"] == pytest.approx(7.2), "la celda se rotula con el maximo"
    assert valores["pop"] == pytest.approx(1000), "y `pop` sigue siendo la celda entera"
    assert valores["pop7"] == pytest.approx(100), "pero en MMI>=7 solo hay cien personas"
    assert valores["pop8"] == pytest.approx(0)
