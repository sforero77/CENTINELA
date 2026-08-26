"""Liberar cada raster en cuanto esta agregado, y medir el disco.

**El disco es el limite del build de un pais grande, no el tiempo.** Brasil
murio dos veces en el mismo punto —a 1 h 43 m con un timeout de 120 min, y a
1 h 46 m con uno de 300— treinta y ocho segundos despues de materializar
`pop_h3` con 4.293.218 celdas. A esa altura el runner tenia 9,1 GB de WorldPop y
437 MB de GHSL en disco, que nadie libera, y DuckDB necesitaba derramar encima.
Un runner de GitHub trae ~14 GB libres.

Costo dos corridas deducirlo porque el mensaje con que GitHub mata un runner sin
recursos —«The runner has received a shutdown signal»— **no distingue disco de
memoria**. Por eso aqui hay dos cosas y no una: liberar, y dejar medido cuanto
disco quedaba en cada paso para que la proxima vez sea un dato y no una
conjetura.
"""

from __future__ import annotations

import inspect
from pathlib import Path

import numpy as np
import pytest

from pipelines.p0_exposure.raster_h3 import aggregate_rasters_to_h3, espacio_libre_mb

pytestmark = pytest.mark.geo


def _raster(destino: Path) -> Path:
    """Un GeoTIFF minimo con algo de poblacion."""
    import rasterio
    from rasterio.transform import from_origin

    from pipelines.common.geo import ensure_bundled_proj

    ensure_bundled_proj()
    banda = np.array([[10.0, 20.0], [30.0, 40.0]], dtype="float32")
    with rasterio.open(
        destino,
        "w",
        driver="GTiff",
        height=2,
        width=2,
        count=1,
        dtype="float32",
        crs="EPSG:4326",
        transform=from_origin(-76.7, 5.72, 0.001, 0.001),
    ) as dst:
        dst.write(banda, 1)
    return destino


@pytest.fixture
def con() -> object:
    from pipelines.p2_impact.exposure_join import connect

    return connect()


def test_por_defecto_no_borra_nada(con: object, tmp_path: Path) -> None:
    """En local, conservarlos es lo que hace barato reanudar un build de una hora.

    Es una regla dura del proyecto —«un build de un pais falla tarde, asi que
    reanudar tiene que ser barato»— y no se rompe por un problema que solo
    tiene CI.
    """
    raster = _raster(tmp_path / "pop.tif")

    aggregate_rasters_to_h3(con, [raster], tabla="pop_h3", columna="pop_total")

    assert raster.exists()


def test_con_liberar_el_raster_desaparece(con: object, tmp_path: Path) -> None:
    """Un raster ya sumado a la tabla H3 no se vuelve a leer: solo ocupa disco."""
    raster = _raster(tmp_path / "pop.tif")

    aggregate_rasters_to_h3(con, [raster], tabla="pop_h3", columna="pop_total", liberar=True)

    assert not raster.exists()


def test_liberar_no_cambia_ni_una_cifra(con: object, tmp_path: Path) -> None:
    """La garantia que hace segura la opcion.

    Si borrar cambiara el resultado, seria una optimizacion que altera lo que se
    publica — justo lo que este sistema no puede permitirse.
    """
    from pipelines.p2_impact.exposure_join import connect

    a = aggregate_rasters_to_h3(
        con, [_raster(tmp_path / "a.tif")], tabla="pop_h3", columna="pop_total"
    )
    b = aggregate_rasters_to_h3(
        connect(),
        [_raster(tmp_path / "b.tif")],
        tabla="pop_h3",
        columna="pop_total",
        liberar=True,
    )

    assert (a.celdas, a.total) == (b.celdas, b.total)


def test_libera_segun_agrega_y_no_al_final(con: object, tmp_path: Path) -> None:
    """Borrar al terminar no serviria: el pico de disco es durante el bucle.

    Con veinte rasters de 453 MB, esperar al final deja los 9,1 GB puestos
    exactamente cuando DuckDB necesita el hueco.
    """
    fuente = inspect.getsource(aggregate_rasters_to_h3)
    cuerpo_del_bucle = fuente[fuente.index("for raster in rasters:") :]
    tras_el_bucle = fuente[fuente.index("# Una celda puede recibir pixeles") :]

    assert "raster.unlink" in cuerpo_del_bucle
    assert "unlink" not in tras_el_bucle


# --- La medicion que faltaba ------------------------------------------------


def test_se_mide_el_disco_libre(tmp_path: Path) -> None:
    """Sin esto, un runner muerto es una conjetura. Costo dos corridas."""
    libres = espacio_libre_mb(tmp_path)

    assert libres > 0


def test_una_ruta_imposible_no_tumba_el_build(tmp_path: Path) -> None:
    """Medir el disco es diagnostico, no funcion: no puede ser un modo de fallo.

    Un build de una hora no se puede caer por la linea que sirve para saber por
    que se cayo. Segun el sistema de archivos, una ruta inexistente devuelve el
    espacio de su volumen o levanta `OSError`; las dos respuestas valen, lo que
    no vale es que se propague.
    """
    valor = espacio_libre_mb(tmp_path / "no" / "existe" / "esto")

    assert isinstance(valor, int)
    assert valor == -1 or valor > 0


def test_el_disco_libre_viaja_en_el_log(con: object, tmp_path: Path) -> None:
    """Que se mida y no se registre no serviria de nada."""
    fuente = inspect.getsource(aggregate_rasters_to_h3)

    assert fuente.count("disco_libre_mb") >= 2, "solo se registra en un sitio"


def test_ci_libera_y_el_uso_local_no() -> None:
    """La opcion existe para CI, y ahi tiene que estar puesta.

    Escribir la opcion y no activarla donde esta el problema seria el patron que
    esta auditoria persigue.
    """
    raiz = Path(__file__).parent.parent.parent
    workflow = (raiz / ".github" / "workflows" / "exposure_quarterly.yml").read_text("utf-8")
    makefile = (raiz / "Makefile").read_text("utf-8")

    assert "--liberar-rasters" in workflow, "CI no libera y el disco es su limite"
    assert "--liberar-rasters" not in makefile, "el build local no debe perder el reanudado"


# --- El pico de memoria no puede depender del tamano del pais ---------------


def test_la_banda_no_se_lee_entera(tmp_path: Path) -> None:
    """La linea que mato el build de Brasil dos veces.

    `src.read(1)` trae toda la banda a memoria, y eso es lineal en el area del
    pais: 1,9 GB para Colombia, 4,3 para Mexico y **12,8 para Brasil**, sobre un
    runner de 16 GB. Se lee por ventanas de filas, asi que el pico es el mismo
    para los diecinueve.
    """
    import ast

    from pipelines.p0_exposure import raster_h3

    # Sobre el AST y no sobre el texto: el docstring cita `src.read(1)` como el
    # error que se corrigio, y buscarlo como subcadena encuentra la explicacion
    # en vez del codigo.
    arbol = ast.parse(inspect.getsource(raster_h3.raster_blocks_to_arrow).lstrip())
    lecturas = [
        nodo
        for nodo in ast.walk(arbol)
        if isinstance(nodo, ast.Call)
        and isinstance(nodo.func, ast.Attribute)
        and nodo.func.attr == "read"
    ]

    assert lecturas, "no lee el raster en ninguna parte"
    for lectura in lecturas:
        assert any(k.arg == "window" for k in lectura.keywords), (
            "se volvio a leer la banda entera: es lo que mato el build de Brasil"
        )


def test_un_raster_alto_se_parte_en_varios_bloques(tmp_path: Path) -> None:
    """Y de verdad se parte: no basta con que la firma lo permita."""
    from pipelines.p0_exposure.raster_h3 import raster_blocks_to_arrow

    ancho, alto = 4, 40
    raster = _raster_de(tmp_path / "alto.tif", np.full((alto, ancho), 5.0, dtype="float32"))

    # Ocho pixeles por bloque sobre un raster de cuatro de ancho: dos filas cada
    # vez, veinte bloques.
    bloques = list(raster_blocks_to_arrow(raster, pixeles_por_bloque=8))

    assert len(bloques) > 1
    assert sum(b.num_rows for b in bloques) == ancho * alto


def test_partir_en_bloques_no_cambia_ni_un_pixel(tmp_path: Path) -> None:
    """Un bloque mal cortado desplazaria filas: el sesgo mas caro posible.

    `filas` es relativa a la ventana y hay que sumarle el origen antes de pedir
    la coordenada. Sin eso, cada bloque menos el primero cae sobre el anterior.
    """
    from pipelines.p0_exposure.raster_h3 import raster_blocks_to_arrow

    banda = np.arange(1, 41, dtype="float32").reshape(10, 4)
    raster = _raster_de(tmp_path / "escalera.tif", banda)

    de_una = list(raster_blocks_to_arrow(raster, pixeles_por_bloque=1 << 20))
    por_bloques = list(raster_blocks_to_arrow(raster, pixeles_por_bloque=4))

    def puntos(bloques: list[object]) -> set[tuple[float, float, float]]:
        return {
            (round(lon, 9), round(lat, 9), val)
            for b in bloques
            for lon, lat, val in zip(
                b.column("lon").to_pylist(),  # type: ignore[attr-defined]
                b.column("lat").to_pylist(),  # type: ignore[attr-defined]
                b.column("valor").to_pylist(),  # type: ignore[attr-defined]
                strict=True,
            )
        }

    assert len(por_bloques) > 1
    assert puntos(de_una) == puntos(por_bloques)


def _raster_de(destino: Path, banda: np.ndarray) -> Path:
    import rasterio
    from rasterio.transform import from_origin

    from pipelines.common.geo import ensure_bundled_proj

    ensure_bundled_proj()
    alto, ancho = banda.shape
    with rasterio.open(
        destino,
        "w",
        driver="GTiff",
        height=alto,
        width=ancho,
        count=1,
        dtype="float32",
        crs="EPSG:4326",
        transform=from_origin(-76.7, 5.72, 0.001, 0.001),
    ) as dst:
        dst.write(banda, 1)
    return destino
