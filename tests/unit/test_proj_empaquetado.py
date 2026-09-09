"""Que un PROJ del sistema no deje inservible el pipeline geo.

Hallazgo de la auditoria del 25-ago-2026, encontrado al escribir las primeras
pruebas de `raster_h3`: en una maquina con PostgreSQL/PostGIS instalado,
`PROJ_LIB` queda apuntando al PROJ de PostGIS y tapa la base de datos que traen
las ruedas de `rasterio` y `pyproj`. A partir de ahi **ningun CRS se resuelve**:

    proj.db contains DATABASE.LAYOUT.VERSION.MINOR = 2 whereas a number >= 6
    is expected. It comes from another PROJ installation.

Y con el CRS se cae la reproyeccion de GHS-POP desde Mollweide, que es el primer
paso de cada cifra de poblacion. `centinela country` inservible en un equipo que
por lo demas cumple todos los requisitos, y con un mensaje que no apunta a la
causa.

O4 dice que el sistema construye un pais desde un clon limpio sin dependencias
del sistema. Un PROJ del sistema **es** una dependencia del sistema, y ademas
una que nadie eligio instalar.
"""

from __future__ import annotations

import pytest

from pipelines.common.geo import RESPETAR_PROJ_DEL_SISTEMA, ensure_bundled_proj


def test_aparta_el_proj_del_sistema(monkeypatch: pytest.MonkeyPatch) -> None:
    import os

    monkeypatch.delenv(RESPETAR_PROJ_DEL_SISTEMA, raising=False)
    monkeypatch.setenv("PROJ_LIB", r"C:\Program Files\PostgreSQL\18\share\contrib\postgis-3.6\proj")

    apartadas = ensure_bundled_proj()

    assert apartadas == ("PROJ_LIB",)
    assert "PROJ_LIB" not in os.environ


def test_aparta_las_dos_variables(monkeypatch: pytest.MonkeyPatch) -> None:
    """PROJ 9 lee `PROJ_DATA`; las versiones anteriores, `PROJ_LIB`.

    Quitar solo una deja a la otra tapando la base empaquetada.
    """
    monkeypatch.delenv(RESPETAR_PROJ_DEL_SISTEMA, raising=False)
    monkeypatch.setenv("PROJ_LIB", "/opt/proj")
    monkeypatch.setenv("PROJ_DATA", "/opt/proj")

    assert set(ensure_bundled_proj()) == {"PROJ_LIB", "PROJ_DATA"}


def test_en_un_entorno_limpio_no_toca_nada(monkeypatch: pytest.MonkeyPatch) -> None:
    """El caso normal: las ruedas encuentran su base solas."""
    monkeypatch.delenv(RESPETAR_PROJ_DEL_SISTEMA, raising=False)
    monkeypatch.delenv("PROJ_LIB", raising=False)
    monkeypatch.delenv("PROJ_DATA", raising=False)

    assert ensure_bundled_proj() == ()


def test_se_puede_exigir_el_proj_del_sistema(monkeypatch: pytest.MonkeyPatch) -> None:
    """Quien de verdad necesite rejillas geoidales nacionales lo declara.

    Sin esta salida, la correccion pasaria de arreglar un accidente a imponer
    una politica, y no hay forma de que el codigo distinga las dos desde fuera.
    """
    import os

    monkeypatch.setenv(RESPETAR_PROJ_DEL_SISTEMA, "1")
    monkeypatch.setenv("PROJ_LIB", "/opt/proj-con-rejillas")

    assert ensure_bundled_proj() == ()
    assert os.environ["PROJ_LIB"] == "/opt/proj-con-rejillas"


@pytest.mark.geo
def test_un_crs_proyectado_se_resuelve_de_verdad() -> None:
    """La prueba que importa: que Mollweide se pueda usar.

    Las anteriores comprueban el manejo del entorno; esta comprueba el efecto,
    que es lo unico que le sirve al build.
    """
    ensure_bundled_proj()
    from pyproj import Transformer

    lon, lat = Transformer.from_crs("ESRI:54009", "EPSG:4326", always_xy=True).transform(
        -7_600_000.0, 640_000.0
    )

    assert -180.0 <= lon <= 180.0
    assert -90.0 <= lat <= 90.0


@pytest.mark.geo
def test_toda_ruta_que_importa_gdal_aparta_el_proj_antes() -> None:
    """Hay que llamarla **antes** del import: GDAL fija su ruta al arrancar.

    Medido: ponerla despues de `import rasterio` no sirve de nada. Por eso la
    llamada va pegada al import diferido en cada funcion, y esta prueba lo fija
    para que nadie la suba al principio del modulo creyendo que da igual.
    """
    import inspect

    from pipelines.p0_exposure.raster_h3 import raster_blocks_to_arrow
    from pipelines.p0_exposure.sources.ghsl import tiles_for_bbox
    from pipelines.p2_impact.ground_failure import sample_rasters

    for funcion in (raster_blocks_to_arrow, sample_rasters, tiles_for_bbox):
        lineas = [
            linea.strip()
            for linea in inspect.getsource(funcion).splitlines()
            if linea.strip().startswith(("import ", "from ")) or "ensure_bundled_proj()" in linea
        ]
        assert lineas, f"{funcion.__name__} no importa nada geo"
        assert lineas[0] == "ensure_bundled_proj()", (
            f"{funcion.__name__} importa GDAL/PROJ antes de apartar el PROJ del sistema"
        )
