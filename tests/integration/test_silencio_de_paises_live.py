"""Los cuatro paises sin reporte: por que estan en silencio, comprobado.

EL PARRAFO QUE ESTA PRUEBA VIGILA. El README explica que Paraguay y Uruguay no
registran un solo sismo M≥5,5 desde 2000, y que los de Bolivia y Brasil son
todos tan profundos que no producen intensidad de superficie que medir. Es un
buen argumento —convierte cuatro casillas vacias en cuatro respuestas— y estaba
mal en los dos numeros que cita.

DE DONDE SALIO EL ERROR. La busqueda original se hizo ordenando por relevancia
sobre cajas envolventes que se llenan de sismos chilenos, y la lista se leyo
truncada; la propia auditoria del 25-ago-2026 lo dice de Argentina y Republica
Dominicana. Bolivia arrastro el mismo sesgo sin que nadie lo notara: su rango
publicado empezaba en 359 km cuando su sismo mas somero desde 2000 esta a 33.

Marcado ``network``: lo corre el workflow nocturno, como el resto de la deriva
de contrato. Su trabajo es **alertar**, no bloquear un reporte.
"""

from __future__ import annotations

from typing import Any

import pytest

from pipelines.common.http import HttpFetcher

pytestmark = pytest.mark.network

CONSULTA = (
    "https://earthquake.usgs.gov/fdsnws/event/1/query?format=geojson"
    "&starttime=2000-01-01&minmagnitude=5.5"
    "&minlatitude={lat_min}&maxlatitude={lat_max}"
    "&minlongitude={lon_min}&maxlongitude={lon_max}&limit=2000"
)

#: Caja envolvente y el nombre con que USGS escribe el pais en `place`. El
#: filtro por nombre es lo que evita el sesgo que tumbo la cifra anterior: la
#: caja de Bolivia se llena de sismos chilenos, y ordenar por relevancia sobre
#: ella deja fuera justo los someros.
PAISES: dict[str, tuple[dict[str, float], str]] = {
    "BOL": ({"lat_min": -23.0, "lat_max": -9.6, "lon_min": -69.7, "lon_max": -57.4}, "Bolivia"),
    "BRA": ({"lat_min": -33.8, "lat_max": 5.3, "lon_min": -74.1, "lon_max": -32.4}, "Brazil"),
    "PRY": ({"lat_min": -27.6, "lat_max": -19.3, "lon_min": -62.7, "lon_max": -54.2}, "Paraguay"),
    "URY": ({"lat_min": -35.0, "lat_max": -30.0, "lon_min": -58.5, "lon_max": -53.1}, "Uruguay"),
}


def _eventos(iso3: str) -> list[dict[str, Any]]:
    caja, nombre = PAISES[iso3]
    payload = HttpFetcher().get_json(CONSULTA.format(**caja))
    return [
        f for f in payload.get("features", []) if nombre in (f["properties"].get("place") or "")
    ]


def _profundidades(eventos: list[dict[str, Any]]) -> list[float]:
    return sorted(float(f["geometry"]["coordinates"][2]) for f in eventos)


@pytest.mark.parametrize("iso3", ["PRY", "URY"])
def test_paraguay_y_uruguay_siguen_sin_un_solo_sismo(iso3: str) -> None:
    """El caso que el README presenta como el estado que se persigue.

    Si algun dia deja de ser cierto, el parrafo del README deja de serlo con el
    — y ese pais pasa a tener reporte pendiente, no silencio explicado.
    """
    assert _eventos(iso3) == [], f"{iso3} ya registra un sismo M≥5,5: el README esta desfasado"


def test_los_sismos_de_brasil_siguen_siendo_todos_profundos() -> None:
    """Doce, todos en Acre, ninguno somero. Esta parte del parrafo si aguanta."""
    profundidades = _profundidades(_eventos("BRA"))

    assert profundidades, "sin eventos no hay nada que comprobar: la consulta cambio"
    assert min(profundidades) > 500.0, (
        f"Brasil ya tiene un sismo M≥5,5 a {min(profundidades):.1f} km: "
        "deja de ser un pais en silencio por profundidad"
    )


def test_bolivia_no_es_el_caso_de_brasil() -> None:
    """La correccion. El README decia que los bolivianos estaban «todos» entre
    359 y 596 km; el mas somero desde 2000 esta a 33, es un M6,2 y su ShakeMap
    modela MMI 6,4. Bolivia no esta en silencio por profundidad: tiene un
    reporte pendiente de construir."""
    profundidades = _profundidades(_eventos("BOL"))

    assert profundidades, "sin eventos no hay nada que comprobar: la consulta cambio"
    assert min(profundidades) < 100.0, (
        "Bolivia ya no registra un sismo somero M≥5,5 desde 2000. Si es cierto, el "
        "parrafo del README vuelve a ser el de Brasil y hay que reescribirlo."
    )


def test_el_sismo_somero_de_bolivia_tiene_contornos_que_calcular() -> None:
    """Lo que convierte «no hay nada que calcular» en «falta calcularlo»."""
    detalle = HttpFetcher().get_json(
        "https://earthquake.usgs.gov/fdsnws/event/1/query?eventid=usp000ahzc&format=geojson"
    )
    productos = detalle["properties"].get("products") or {}
    contenidos = productos["shakemap"][0]["contents"]

    assert float(detalle["properties"]["mmi"]) >= 5.0
    assert "download/cont_mmi.json" in contenidos
