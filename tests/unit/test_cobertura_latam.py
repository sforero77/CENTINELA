"""El sistema es para LATAM: los manifests y las cajas tienen que cuadrar.

Estas pruebas no miran datos, miran coherencia. Un pais con manifest y sin caja
envolvente falla al descargar; una caja mal copiada recorta el pais y el activo
sale con una punta sin poblacion, cuadrando todo.
"""

from __future__ import annotations

from typing import Any

import pytest

from pipelines.common.manifest import Manifest
from pipelines.common.paths import MANIFESTS_DIR
from pipelines.p0_exposure.build import validate_bbox_covers_country
from pipelines.p0_exposure.download import COUNTRY_BBOX
from pipelines.p0_exposure.layers import required_layers

#: Los 19 de LATAM hispanohablante mas Brasil. Fuentes verificadas una por una
#: con peticion real el 23-ago-2026.
LATAM = (
    "ARG",
    "BOL",
    "BRA",
    "CHL",
    "COL",
    "CRI",
    "CUB",
    "DOM",
    "ECU",
    "GTM",
    "HND",
    "MEX",
    "NIC",
    "PAN",
    "PER",
    "PRY",
    "SLV",
    "URY",
    "VEN",
)


def _manifests() -> list[str]:
    return sorted(p.stem for p in MANIFESTS_DIR.glob("*.yaml"))


def test_estan_los_19_paises() -> None:
    assert set(_manifests()) == set(LATAM)


@pytest.mark.parametrize("iso3", LATAM)
def test_cada_manifest_tiene_caja(iso3: str) -> None:
    """Sin caja, `download_manifest` falla antes de bajar nada."""
    assert iso3 in COUNTRY_BBOX


@pytest.mark.parametrize("iso3", LATAM)
def test_cada_manifest_declara_las_capas_requeridas(iso3: str) -> None:
    declaradas = {s.layer for s in Manifest.load(iso3).sources}
    faltan = {c.id for c in required_layers()} - declaradas
    assert not faltan, f"{iso3} no declara: {sorted(faltan)}"


@pytest.mark.parametrize("iso3", LATAM)
def test_cada_manifest_tiene_referencia_de_poblacion(iso3: str) -> None:
    """Sin referencia no hay assert de total nacional, que es la red principal."""
    ref = Manifest.load(iso3).referencia_oficial
    assert ref.get("poblacion_2025", 0) > 0, f"{iso3} sin referencia"
    assert ref.get("fuente")


@pytest.mark.parametrize("iso3", LATAM)
def test_ninguna_caja_esta_invertida(iso3: str) -> None:
    caja = COUNTRY_BBOX[iso3]
    assert caja.lon_min < caja.lon_max
    assert caja.lat_min < caja.lat_max


#: Unico pais cuyo territorio queda parcialmente fuera de la ventana del
#: disparador, y por que. Ver LATAM_BBOX: llegar hasta el archipielago de San
#: Pedro y San Pablo —que se asienta sobre la dorsal mesoatlantica— meteria
#: sismicidad oceanica sin poblacion a cambio de una estacion cientifica.
#: Fernando de Noronha, habitada, si entra.
FUERA_DE_VENTANA = {"BRA"}


@pytest.mark.parametrize("iso3", [p for p in LATAM if p not in FUERA_DE_VENTANA])
def test_el_disparador_vigila_todo_el_territorio_que_el_sistema_cubre(iso3: str) -> None:
    """Si el pais se sale de la ventana, el disparador no ve sus sismos.

    Y no falla al no verlos: el evento simplemente nunca existe para el sistema.
    Esta prueba cazo que Mexico llegaba a 118,65°W y Chile a 56,78°S mientras la
    ventana cortaba en 118,0 y 56,0.
    """
    from pipelines.common.geo import LATAM_BBOX

    caja = COUNTRY_BBOX[iso3]
    assert LATAM_BBOX.contains(caja.lon_min, caja.lat_min), f"{iso3} se sale al suroeste"
    assert LATAM_BBOX.contains(caja.lon_max, caja.lat_max), f"{iso3} se sale al noreste"


def test_la_excepcion_de_la_ventana_esta_acotada_y_es_solo_insular() -> None:
    """Brasil continental tiene que estar dentro; lo que queda fuera es el islote."""
    from pipelines.common.geo import LATAM_BBOX

    caja = COUNTRY_BBOX["BRA"]
    assert LATAM_BBOX.contains(caja.lon_min, caja.lat_min)
    assert not LATAM_BBOX.contains(caja.lon_max, caja.lat_max)
    # Fernando de Noronha (32,42°W, ~3.000 habitantes) tiene que entrar: fue
    # justo lo que obligo a mover el limite de 34°W a 32°W.
    assert LATAM_BBOX.contains(-32.42, -3.85)
    # El islote de San Pedro y San Pablo (29,35°W), sobre la dorsal, no.
    assert not LATAM_BBOX.contains(-29.35, 0.92)


def test_solo_dos_paises_fijan_el_recurso_de_hdx() -> None:
    """Y por razones distintas, las dos documentadas en su manifest.

    Colombia por **necesidad**: su COD-AB publica cuatro recursos SHP y el
    primero son secciones urbanas. Venezuela por **preferencia**: publica SHP y
    GeoJSON, y se fija el SHP porque es el que trae el `.prj` con el CRS y es
    sobre el que se verificaron columnas y caja. Ningun otro pais de LATAM lo
    necesita: los diecisiete restantes publican un solo recurso del formato
    preferido.
    """
    con_pin = {
        iso3
        for iso3 in LATAM
        for s in Manifest.load(iso3).sources
        if s.hdx_resource and s.layer == "divisions"
    }
    assert con_pin == {"COL", "VEN"}


# --- El assert que convierte la caja en invariante -------------------------


@pytest.fixture
def con() -> Any:
    from pipelines.p2_impact.exposure_join import connect

    return connect()


def _admin_geom(con: Any, xmin: float, ymin: float, xmax: float, ymax: float) -> None:
    con.execute(
        f"""
        CREATE OR REPLACE TABLE admin_geom AS
        SELECT ST_GeomFromText(
            'POLYGON(({xmin} {ymin}, {xmax} {ymin}, {xmax} {ymax}, {xmin} {ymax}, {xmin} {ymin}))'
        ) AS geom
        """
    )


@pytest.mark.geo
def test_una_caja_que_cubre_el_pais_pasa(con: Any) -> None:
    _admin_geom(con, -75.0, 1.0, -70.0, 10.0)
    assert validate_bbox_covers_country(con, COUNTRY_BBOX["COL"], iso3="COL") == []


@pytest.mark.geo
@pytest.mark.parametrize(
    ("geom", "lado"),
    [
        ((-90.0, 1.0, -70.0, 10.0), "oeste"),
        ((-75.0, -10.0, -70.0, 10.0), "sur"),
        ((-75.0, 1.0, -60.0, 10.0), "este"),
        ((-75.0, 1.0, -70.0, 20.0), "norte"),
    ],
)
@pytest.mark.filterwarnings("ignore")
def test_una_caja_corta_falla_por_el_lado_correcto(
    con: Any, geom: tuple[float, float, float, float], lado: str
) -> None:
    """Perder territorio no puede ser silencioso: cuadra todo y falta un trozo."""
    _admin_geom(con, *geom)
    fallos = validate_bbox_covers_country(con, COUNTRY_BBOX["COL"], iso3="COL")
    assert fallos and lado in fallos[0]


@pytest.mark.geo
def test_sin_geometria_es_aviso_no_error(con: Any) -> None:
    """Un aviso no debe tumbar el build; el fallo real llega mas adelante."""
    con.execute("CREATE OR REPLACE TABLE admin_geom AS SELECT NULL::GEOMETRY AS geom")
    fallos = validate_bbox_covers_country(con, COUNTRY_BBOX["COL"], iso3="COL")
    assert all("(aviso)" in f for f in fallos)
