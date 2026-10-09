"""Mapa estatico del reporte (T0.8).

Este modulo no tenia ni una prueba, y por eso los tres reportes publicados
salieron durante meses con el mismo PNG vacio: la estrella del epicentro clavada
en (0, 0) y ni un municipio dibujado. Las dos causas eran desconexiones, no
errores de calculo — el renderizador leia campos que nadie le pasaba — asi que
lo que se prueba aqui es justamente el cableado.
"""

from __future__ import annotations

import math
import re
import struct
from itertools import pairwise
from pathlib import Path

import pytest

from pipelines.common.paths import SITE_DIR
from pipelines.p3_report.model import Evento, Inputs, PoblacionEnRadio, Report, Totales
from pipelines.p3_report.static_map import (
    COLOR_CONTORNO_BAJO,
    MMI_COLORS,
    SPECS,
    MapVariant,
    _a_proporcion,
    _anillos_de_radio,
    _coordenada,
    _epicentro,
    _puntos_municipales,
    _rotular_municipios,
    banda_de_mmi,
    color_for_mmi,
    render_map,
)


@pytest.fixture
def reporte() -> Report:
    return Report(
        event=Evento(
            usgs_id="us7000sint",
            mag=7.1,
            depth_km=30.0,
            utc="2026-08-19T05:00:00Z",
            lugar="38 km al W de Bahia Solano, Choco, Colombia",
            lon=-77.6,
            lat=6.2,
        ),
        inputs=Inputs(
            shakemap_version=3, groundfailure_version=2, exposure_manifest="col-v0.1-draft"
        ),
        totales=Totales(),
    )


def test_epicentro_sale_del_reporte(reporte: Report) -> None:
    """Antes venia de un registro de modulo que no rellenaba nadie."""
    assert _epicentro(reporte) == (-77.6, 6.2)


def test_epicentro_ausente_no_se_inventa() -> None:
    """Sin coordenadas se devuelve ``None``, no ``(0, 0)``.

    El valor por defecto anterior dibujaba la estrella en el golfo de Guinea,
    que es un sitio perfectamente valido para un punto y ninguno para el
    epicentro de un sismo en Colombia.
    """
    sin_coords = Report(
        event=Evento(usgs_id="us7000sint", mag=7.1, depth_km=30.0, utc="", lugar=""),
        inputs=Inputs(shakemap_version=1, groundfailure_version=1, exposure_manifest="x"),
        totales=Totales(),
    )
    assert _epicentro(sin_coords) is None


def test_municipios_desde_columnas_lon_lat() -> None:
    """Las filas del CSV traen ``lon``/``lat``; el render solo leia WKT."""
    filas = [
        {"lon": -75.7, "lat": 4.8, "mmi_max": 7.5, "pop_mmi7p": 498099.0, "nombre": "PEREIRA"},
        {"lon": -77.1, "lat": 3.6, "mmi_max": 7.0, "pop_mmi7p": 401081.0, "nombre": "BUENAVENTURA"},
    ]
    puntos = _puntos_municipales(filas, 7)
    assert len(puntos) == 2
    assert puntos[0][:3] == (-75.7, 4.8, 7.5)


def test_municipios_acepta_wkt_como_respaldo() -> None:
    filas = [{"centroide": "POINT (-74.1 4.6)", "mmi_max": 6.5, "pop_mmi7p": 10.0, "nombre": "X"}]
    assert _puntos_municipales(filas, 7)[0][:2] == (-74.1, 4.6)


def test_municipio_sin_coordenadas_se_descarta() -> None:
    assert _puntos_municipales([{"mmi_max": 7.0, "nombre": "X"}], 7) == []
    assert _coordenada({"lon": "", "lat": ""}) is None


def test_la_rampa_cubre_la_intensidad_maxima_publicada() -> None:
    """El evento de Catia La Mar llega a 8,5 y la rampa se quedaba en 8,0."""
    assert 8.5 in MMI_COLORS
    assert color_for_mmi(8.5) != color_for_mmi(8.0)


def test_la_rampa_es_monotona_en_luminosidad() -> None:
    """Requisito del modulo: legible impresa en blanco y negro."""

    def luminancia(hexa: str) -> float:
        canales = [int(hexa[i : i + 2], 16) / 255 for i in (1, 3, 5)]
        lineal = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in canales]
        return 0.2126 * lineal[0] + 0.7152 * lineal[1] + 0.0722 * lineal[2]

    valores = [luminancia(MMI_COLORS[v]) for v in sorted(MMI_COLORS)]
    assert valores == sorted(valores, reverse=True)
    assert all(a - b > 0.02 for a, b in pairwise(valores))


def test_banda_por_debajo_del_minimo_cae_en_la_primera() -> None:
    assert banda_de_mmi(5.0) == 6.0
    assert banda_de_mmi(7.4) == 7.0


@pytest.mark.render
def test_render_dibuja_los_municipios(reporte: Report, tmp_path: Path) -> None:
    """Un PNG con municipios pesa mas que uno vacio.

    No se compara pixel a pixel —seria fragil frente a cualquier version de
    matplotlib— pero un mapa que dibuja 60 puntos y sus etiquetas no puede pesar
    lo mismo que uno que no dibuja ninguno, y ese era exactamente el sintoma.
    """
    pytest.importorskip("matplotlib")
    filas = [
        {
            "lon": -77.0 + i * 0.05,
            "lat": 6.0 + i * 0.04,
            "mmi_max": 6.0 + (i % 6) * 0.5,
            "pop_mmi7p": 1000.0 * (i + 1),
            "nombre": f"MUNICIPIO {i}",
        }
        for i in range(60)
    ]
    con = tmp_path / "con.png"
    sin = tmp_path / "sin.png"
    render_map(reporte, MapVariant.GENERAL, con, municipios=filas)
    render_map(reporte, MapVariant.GENERAL, sin, municipios=[])
    assert con.stat().st_size > sin.stat().st_size


def _preliminar(reporte: Report) -> Report:
    from dataclasses import replace

    return replace(
        reporte,
        inputs=Inputs(shakemap_version=0, groundfailure_version=0, exposure_manifest="x"),
        preliminar=True,
        radios=(
            PoblacionEnRadio(radio_km=25, pop=16_000.0),
            PoblacionEnRadio(radio_km=50, pop=83_000.0),
            PoblacionEnRadio(radio_km=100, pop=476_000.0),
        ),
    )


def test_el_preliminar_dibuja_sus_radios(reporte: Report, tmp_path: Path) -> None:
    """El preliminar del M7,7 de Azuero (9-oct-2026) salio en blanco.

    Una estrella sobre un lienzo vacio, con los radios calculados en el mismo
    reporte. Sin contornos, los anillos son el mapa.
    """
    pytest.importorskip("matplotlib")
    pre = _preliminar(reporte)
    anillos = _anillos_de_radio(pre, _epicentro(pre))
    assert [a[0].radio_km for a in anillos] == [100, 50, 25]
    # El de 100 km mide 100 km hacia el norte, no una caja de 44 km.
    norte = max(y for _, y in anillos[0][1])
    assert norte - 6.2 == pytest.approx(100 / 111.32, rel=1e-3)

    con = tmp_path / "con.png"
    sin = tmp_path / "sin.png"
    render_map(pre, MapVariant.GENERAL, con, municipios=[])
    render_map(reporte, MapVariant.GENERAL, sin, municipios=[])
    assert con.stat().st_size > 2 * sin.stat().st_size


def test_el_mapa_dimensiona_por_la_banda_del_reporte_no_siempre_por_siete() -> None:
    """El PNG rotulaba MMI≥7 aunque el `report.md` del mismo evento dijera 6.

    Once de los veintiun eventos del catalogo no alcanzan MMI≥7 sobre poblacion.
    Para ellos `pop_mmi7p` es cero en cada fila, asi que todos los circulos
    salian al tamano minimo y la leyenda rotulaba "Personas expuestas: 0"
    mientras la tabla del reporte hablaba de MMI≥6. Dos artefactos del mismo
    evento contando cosas distintas.
    """
    filas = [
        {
            "lon": -95.1,
            "lat": 16.2,
            "mmi_max": 6.5,
            "pop_mmi6p": 74000.0,
            "pop_mmi7p": 0.0,
            "nombre": "X",
        },
    ]
    assert _puntos_municipales(filas, 6)[0][3] == 74000.0
    assert _puntos_municipales(filas, 7)[0][3] == 0.0


# --- La rampa del PNG y la del visor (auditoria del 5-sep-2026, #175) --------


def _sin_comentarios_js(js: str) -> str:
    """El JS sin comentarios: un guardia de texto no puede aprobar por la prosa."""
    limpio = re.sub(r"/\*.*?\*/", "", js, flags=re.S)
    return "\n".join(ln for ln in limpio.splitlines() if not ln.lstrip().startswith("//"))


def test_la_rampa_del_png_es_la_del_visor() -> None:
    """`MMI_COLORS` dice ser «la misma rampa que usa el visor», y nada lo probaba.

    Estan escritas dos veces, una en Python y otra en `CAPAS.mmi` de
    `site/assets/app.js`. Si una cambia sola, el mismo evento sale de dos
    colores segun se mire el PNG o la pagina, y ninguna otra prueba lo nota.
    Se comparan cortes, colores y el gris de las isolineas bajas.
    """
    app = _sin_comentarios_js((SITE_DIR / "assets" / "app.js").read_text(encoding="utf-8"))
    bloque = app[app.index("  mmi: {") :]
    bloque = bloque[: bloque.index("\n  },")]
    cortes = [float(v) for v in re.search(r"cortes:\s*\[([^\]]*)\]", bloque)[1].split(",")]  # type: ignore[index]
    colores = re.findall(r"#[0-9a-fA-F]{6}", re.search(r"colores:\s*\[([^\]]*)\]", bloque)[1])  # type: ignore[index]
    gris = re.search(r'const COLOR_CONTORNO_BAJO = "(#[0-9a-fA-F]{6})"', app)

    # Sin esto, un cambio de formato dejaria dos listas vacias iguales, en verde.
    assert len(cortes) == len(MMI_COLORS) >= 6, f"no se leyo la rampa del visor: {cortes}"
    assert dict(zip(cortes, (c.lower() for c in colores), strict=True)) == {
        k: v.lower() for k, v in MMI_COLORS.items()
    }
    assert gris is not None, "el visor ya no declara COLOR_CONTORNO_BAJO"
    assert gris[1].lower() == COLOR_CONTORNO_BAJO.lower()


# --- `prensa` es 16:9 (auditoria del 5-sep-2026, #174) ---------------------


def _medidas_png(ruta: Path) -> tuple[int, int]:
    ancho, alto = struct.unpack(">II", ruta.read_bytes()[16:24])
    return ancho, alto


@pytest.mark.render
def test_prensa_mide_1920x1080_aunque_el_evento_sea_alto(reporte: Report, tmp_path: Path) -> None:
    """El ancho salia de la forma del evento y 1920 era solo un tope.

    De los 28 `mapa_prensa.png` publicados al 3-oct-2026, uno era 16:9; los
    alargados en latitud —Chile— salian mas altos que anchos (0,80). Aqui un
    evento de 3° de alto por 0,4° de ancho, el peor caso.
    """
    pytest.importorskip("matplotlib")
    filas = [
        {
            "lon": -77.5 + (i % 2) * 0.4,
            "lat": 4.5 + i * 0.1,
            "mmi_max": 7.0,
            "pop_mmi7p": 5000.0,
            "nombre": f"M{i}",
        }
        for i in range(30)
    ]
    prensa = render_map(reporte, MapVariant.PRENSA, tmp_path / "p.png", municipios=filas)
    general = render_map(reporte, MapVariant.GENERAL, tmp_path / "g.png", municipios=filas)

    spec = SPECS[MapVariant.PRENSA]
    assert _medidas_png(prensa) == (spec.width_px, spec.height_px) == (1920, 1080)
    ancho_g, alto_g = _medidas_png(general)
    assert ancho_g < alto_g, "general sigue la forma del evento; no es la misma imagen escalada"


def test_ensanchar_a_la_proporcion_nunca_recorta() -> None:
    """El encuadre crece en la dimension que falta, alrededor del mismo centro."""
    alto = (-78.0, 0.0, -77.0, 4.0)  # mas alto que ancho
    lon0, lat0, lon1, lat1 = _a_proporcion(alto, 16 / 9)
    assert (lat0, lat1) == (0.0, 4.0)
    assert lon0 < -78.0 and lon1 > -77.0
    assert math.isclose((lon0 + lon1) / 2, -77.5)
    coseno = math.cos(math.radians(2.0))
    assert math.isclose((lon1 - lon0) * coseno / (lat1 - lat0), 16 / 9)

    ancho = (-90.0, 10.0, -70.0, 11.0)  # mas ancho que 16:9
    lon0, lat0, lon1, lat1 = _a_proporcion(ancho, 16 / 9)
    assert (lon0, lon1) == (-90.0, -70.0)
    assert lat0 < 10.0 and lat1 > 11.0


# --- Rotulos que se pisan (auditoria del 5-sep-2026, #109) ------------------


@pytest.mark.render
def test_dos_nombres_largos_no_se_escriben_uno_encima_del_otro() -> None:
    """La separacion se media en 0,25° fijos, sin mirar el ancho del texto.

    En `us6000t7zp` «Ocumare de la Costa de Oro» salia sobre «Puerto Cabello»:
    estaban a mas de 0,25° en longitud y el nombre, largo, cruzaba el hueco.
    Aqui dos municipios a 0,3° en un mapa de 3° de ancho, con nombres largos:
    la regla vieja los rotulaba a los dos.
    """
    pytest.importorskip("matplotlib")
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(8, 6), dpi=110)
    try:
        ax.set_xlim(-69.0, -66.0)
        ax.set_ylim(9.5, 11.5)
        puntos = [
            (-68.0, 10.47, 7.5, 200_000.0, "OCUMARE DE LA COSTA DE ORO"),
            (-67.7, 10.47, 7.5, 150_000.0, "PUERTO CABELLO DEL NORTE"),
            # Lejos de los dos: tiene que salir.
            (-66.5, 9.8, 7.0, 50_000.0, "SAN FELIPE"),
        ]
        puestos = _rotular_municipios(fig, ax, puntos, n_max=6, fontsize=8)

        assert puestos == ["Ocumare de la Costa de Oro", "San Felipe"]
        cajas = [t.get_window_extent() for t in ax.texts]
        assert len(cajas) == 2, "el rotulo descartado se quedo dibujado"
        assert not cajas[0].overlaps(cajas[1])
    finally:
        plt.close(fig)
