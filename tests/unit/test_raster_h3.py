"""Agregacion raster -> H3: de aqui sale **cada cifra de poblacion** publicada.

Era el modulo de mayor consecuencia sin una sola prueba. Lo que se afirma en un
reporte —"2.415.793 personas en MMI≥7"— pasa entero por estas dos funciones, y
todos sus modos de fallo producen numeros plausibles: un nodata sin enmascarar
da poblacion negativa, una reproyeccion omitida coloca a un pais entero en el
Golfo de Guinea, y una celda contada dos veces infla el total sin que nada
proteste.

Los rasters se fabrican aqui mismo con `rasterio`, en memoria de disco
temporal: pequenos, deliberados, y cada uno con un solo modo de fallo dentro.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pytest

from pipelines.p0_exposure.raster_h3 import aggregate_rasters_to_h3, raster_to_arrow

pytestmark = pytest.mark.geo

#: Un rincon del Choco. Cualquier sitio sirve; importa que sea el mismo siempre.
LON_ORIGEN, LAT_ORIGEN = -76.70, 5.72

#: Lado del pixel en grados. 0,001° son unos 111 m, del orden de GHS-POP.
PASO = 0.001


def _escribir_raster(
    destino: Path,
    banda: np.ndarray,
    *,
    nodata: float | None = None,
    crs: str = "EPSG:4326",
    origen: tuple[float, float] = (LON_ORIGEN, LAT_ORIGEN),
    paso: float = PASO,
) -> Path:
    """GeoTIFF de una banda, del tamano que le pasen."""
    import rasterio
    from rasterio.transform import from_origin

    alto, ancho = banda.shape
    perfil: dict[str, Any] = {
        "driver": "GTiff",
        "height": alto,
        "width": ancho,
        "count": 1,
        "dtype": "float32",
        "crs": crs,
        "transform": from_origin(origen[0], origen[1], paso, paso),
    }
    if nodata is not None:
        perfil["nodata"] = nodata
    with rasterio.open(destino, "w", **perfil) as dst:
        dst.write(banda.astype("float32"), 1)
    return destino


@pytest.fixture
def con() -> Any:
    from pipelines.p2_impact.exposure_join import connect

    return connect()


# --- Lectura del raster -----------------------------------------------------


def test_el_nodata_del_oceano_no_entra_como_poblacion(tmp_path: Path) -> None:
    """GHS-POP marca el mar con -200, y son ~22 millones de pixeles por tesela.

    Sumarlos da poblacion negativa y el assert de §6.4 marcaria como corruptos
    unos datos que estan perfectos. Es el fallo que hace fallar la vigilancia,
    no solo la cifra.
    """
    banda = np.array([[10.0, -200.0], [-200.0, 30.0]])
    tabla = raster_to_arrow(_escribir_raster(tmp_path / "pop.tif", banda, nodata=-200.0))

    assert tabla.num_rows == 2
    assert sum(tabla.column("valor").to_pylist()) == pytest.approx(40.0)


def test_el_nodata_explicito_manda_sobre_el_declarado(tmp_path: Path) -> None:
    """Hay rasters que declaran mal su nodata, y el manifest tiene que poder corregirlo."""
    banda = np.array([[10.0, -99.0]])
    ruta = _escribir_raster(tmp_path / "pop.tif", banda, nodata=-200.0)

    assert raster_to_arrow(ruta, nodata=-99.0).num_rows == 1


def test_un_raster_sin_nodata_declarado_no_revienta(tmp_path: Path) -> None:
    """Sin nodata en el archivo ni en la llamada, no se enmascara nada."""
    banda = np.array([[5.0, 7.0]])

    assert raster_to_arrow(_escribir_raster(tmp_path / "pop.tif", banda)).num_rows == 2


def test_los_pixeles_vacios_se_descartan_antes_de_indexar(tmp_path: Path) -> None:
    """La poblacion es dispersa: 2,2 millones de pixeles con dato de cada 100.

    Indexar los ceros multiplicaria por veinte el volumen sin cambiar una sola
    cifra. No es una optimizacion opcional: es lo que hace el build viable.
    """
    banda = np.array([[0.0, 0.0, 12.0], [0.0, 0.0, 0.0]])

    assert raster_to_arrow(_escribir_raster(tmp_path / "pop.tif", banda)).num_rows == 1


def test_las_coordenadas_son_del_centro_del_pixel(tmp_path: Path) -> None:
    """Media celda de desfase son 50 m, y a r8 eso puede cambiar de hexagono.

    Un sesgo sistematico en una direccion no se nota en el total nacional y si
    en el reparto por municipio, que es la cifra que mira un alcalde.
    """
    tabla = raster_to_arrow(_escribir_raster(tmp_path / "pop.tif", np.array([[42.0]])))

    assert tabla.column("lon")[0].as_py() == pytest.approx(LON_ORIGEN + PASO / 2)
    assert tabla.column("lat")[0].as_py() == pytest.approx(LAT_ORIGEN - PASO / 2)


def test_un_raster_proyectado_se_reproyecta_a_wgs84(tmp_path: Path) -> None:
    """GHS-POP viene en Mollweide (ESRI:54009), no en grados.

    Sin reproyectar, sus coordenadas en metros se leerian como grados y el pais
    entero acabaria a unos pocos grados del punto (0, 0), en el Golfo de
    Guinea. El polyfill no encontraria nada y el activo saldria vacio.
    """
    ruta = _escribir_raster(
        tmp_path / "pop.tif",
        np.array([[100.0]]),
        crs="ESRI:54009",
        origen=(-7_600_000.0, 640_000.0),
        paso=100.0,
    )
    tabla = raster_to_arrow(ruta)

    assert -180.0 <= tabla.column("lon")[0].as_py() <= 180.0
    assert -90.0 <= tabla.column("lat")[0].as_py() <= 90.0


def test_un_raster_entero_de_nodata_devuelve_una_tabla_vacia_tipada(tmp_path: Path) -> None:
    """Una tesela puede ser todo oceano, y el build tiene que seguir.

    La tabla vacia va tipada a proposito: sin tipos, DuckDB no puede unirla con
    las demas y el fallo aparece varias teselas despues.
    """
    banda = np.full((3, 3), -200.0)
    tabla = raster_to_arrow(_escribir_raster(tmp_path / "mar.tif", banda, nodata=-200.0))

    assert tabla.num_rows == 0
    assert tabla.schema.names == ["lon", "lat", "valor"]


# --- Agregacion a celdas ----------------------------------------------------


def test_la_suma_nacional_se_conserva(con: Any, tmp_path: Path) -> None:
    """El invariante de §6.1: agregar no puede crear ni perder poblacion."""
    banda = np.array([[10.0, 20.0, 30.0], [40.0, 50.0, 60.0]])
    ruta = _escribir_raster(tmp_path / "pop.tif", banda)

    resumen = aggregate_rasters_to_h3(con, [ruta], tabla="pop_h3", columna="pop_total")

    assert resumen.total == pytest.approx(210.0)
    assert resumen.celdas > 0


def test_dos_teselas_vecinas_no_duplican_su_celda_compartida(con: Any, tmp_path: Path) -> None:
    """Una celda H3 puede recibir pixeles de dos teselas, y GHS-POP viene en nueve.

    Sin la consolidacion final, esa celda aparece dos veces: el total nacional
    sale inflado y el `LEFT JOIN` del ensamblaje elige una de las dos filas.
    Colombia necesita nueve teselas, asi que no es un caso raro.
    """
    ruta_a = _escribir_raster(tmp_path / "a.tif", np.array([[100.0]]))
    ruta_b = _escribir_raster(tmp_path / "b.tif", np.array([[50.0]]))

    resumen = aggregate_rasters_to_h3(con, [ruta_a, ruta_b], tabla="pop_h3", columna="pop_total")

    repetidas = con.execute(
        "SELECT count(*) FROM (SELECT h3_08 FROM pop_h3 GROUP BY 1 HAVING count(*) > 1)"
    ).fetchone()[0]
    assert repetidas == 0
    assert resumen.total == pytest.approx(150.0)


def test_una_tesela_vacia_no_tumba_la_corrida(con: Any, tmp_path: Path) -> None:
    """De nueve teselas, varias pueden ser todo mar. El build tiene que llegar al final."""
    con_dato = _escribir_raster(tmp_path / "tierra.tif", np.array([[80.0]]))
    vacia = _escribir_raster(tmp_path / "mar.tif", np.full((2, 2), -200.0), nodata=-200.0)

    resumen = aggregate_rasters_to_h3(con, [vacia, con_dato], tabla="pop_h3", columna="pop_total")

    assert resumen.total == pytest.approx(80.0)


def test_sin_ningun_raster_el_total_es_cero_y_no_nulo(con: Any) -> None:
    """`sum()` sobre cero filas devuelve NULL en SQL, y NULL rompe el ensamblaje.

    Cero es ademas la respuesta honesta: `validate_layer_coverage` es quien
    decide si un cero nacional es motivo para detener el build.
    """
    resumen = aggregate_rasters_to_h3(con, [], tabla="pop_h3", columna="pop_total")

    assert resumen.total == 0.0
    assert resumen.celdas == 0


def test_la_tabla_se_reemplaza_y_no_se_acumula(con: Any, tmp_path: Path) -> None:
    """Reanudar un build es normal: son ~1 GB y el paso que mas falla es el ultimo.

    Si la tabla se acumulara, la segunda corrida duplicaria la poblacion del
    pais — y saldria un numero perfectamente plausible.
    """
    ruta = _escribir_raster(tmp_path / "pop.tif", np.array([[100.0]]))

    aggregate_rasters_to_h3(con, [ruta], tabla="pop_h3", columna="pop_total")
    segunda = aggregate_rasters_to_h3(con, [ruta], tabla="pop_h3", columna="pop_total")

    assert segunda.total == pytest.approx(100.0)


def test_los_pixeles_lejanos_caen_en_celdas_distintas(con: Any, tmp_path: Path) -> None:
    """Si todo cayera en una celda, el reparto por municipio no significaria nada."""
    banda = np.arange(1.0, 101.0).reshape(10, 10)
    ruta = _escribir_raster(tmp_path / "pop.tif", banda, paso=0.01)

    resumen = aggregate_rasters_to_h3(con, [ruta], tabla="pop_h3", columna="pop_total")

    assert resumen.celdas > 1
