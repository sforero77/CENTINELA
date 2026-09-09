"""El contrato de USGS tiene que sonar por lo que se usa y callar por lo demas.

EL 7-SEP-2026 USGS CAMBIO SU FEED Y EL NOCTURNO EMPEZO A FALLAR POR UN PRODUCTO
QUE NADIE ABRE. Quito `url` y `version` del nivel superior de cada producto, y
`schemas/usgs/detail-products.schema.json` los exigia via `additionalProperties`
a los doce que USGS publica. Reventaba por `impact-text` y `general-text`.

La tuberia no se entero en ningun momento: `ProductRef.from_dict` lee
`properties.version` primero, y ahi sigue estando. O sea que la alarma sono dos
noches por algo que no afectaba a nada, que es la peor cosa que puede hacer una
alarma — la siguiente ya no se mira.

El arreglo fue acotar el rigor a los tres productos que se consumen. Aflojar un
contrato es facil de hacer de mas, asi que estas pruebas fijan las dos mitades:
lo que **tiene** que seguir cazando y lo que **tiene** que dejar pasar. Corren
sin red, sobre un payload minimo construido aqui.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator

ESQUEMA = Path(__file__).resolve().parents[2] / "schemas" / "usgs" / "detail-products.schema.json"


@pytest.fixture(scope="module")
def validador() -> Draft202012Validator:
    esquema = json.loads(ESQUEMA.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(esquema)
    return Draft202012Validator(esquema)


def _detalle() -> dict[str, Any]:
    """Un detail con la forma que USGS publica **hoy**, reducido a lo esencial."""

    def producto(props: dict[str, Any]) -> list[dict[str, Any]]:
        return [
            {
                "status": "UPDATE",
                "preferredWeight": 233,
                "updateTime": 1788821766631,
                "contents": {"download/cont_mmi.json": {"url": "https://example.org/c.json"}},
                "properties": props,
            }
        ]

    return {
        "id": "us6000tjl2",
        "properties": {
            "products": {
                "shakemap": producto({"version": "9"}),
                "ground-failure": producto({"version": "9"}),
                # Sin `version`: USGS nunca se la puso, y no hace falta.
                "losspager": producto({"alertlevel": "red"}),
                # Los que rompieron el nocturno. Su forma no es asunto nuestro.
                "impact-text": [
                    {
                        "status": "UPDATE",
                        "preferredWeight": 6,
                        "updateTime": 1788821766631,
                        "contents": {},
                        "properties": {},
                    }
                ],
                "event-sequence": [{"contents": []}],
            }
        },
    }


def test_el_detalle_de_hoy_pasa(validador: Draft202012Validator) -> None:
    """Sin esto, las de abajo podrian estar pasando por el motivo equivocado."""
    assert list(validador.iter_errors(_detalle())) == []


#: Deriva que **tiene** que sonar: cada una rompe algo que la tuberia lee.
ROMPE: dict[str, Callable[[dict[str, Any]], None]] = {
    "shakemap sin version": lambda p: p["shakemap"][0]["properties"].pop("version"),
    "ground-failure sin version": lambda p: p["ground-failure"][0]["properties"].pop("version"),
    "un contents sin url": lambda p: p["shakemap"][0]["contents"]["download/cont_mmi.json"].clear(),
    "shakemap sin contents": lambda p: p["shakemap"][0].pop("contents"),
    "shakemap sin updateTime": lambda p: p["shakemap"][0].pop("updateTime"),
    "losspager sin alertlevel": lambda p: p["losspager"][0]["properties"].pop("alertlevel"),
    # Los dos que el esquema anterior dejaba escapar pese a que su propia
    # descripcion presumia de cazarlos: el `required` vivia dentro de `items`,
    # que no corre sobre una lista vacia.
    "shakemap con lista vacia": lambda p: p.__setitem__("shakemap", []),
    "shakemap ausente": lambda p: p.pop("shakemap"),
    "products vacio": lambda p: p.clear(),
}


@pytest.mark.parametrize("caso", sorted(ROMPE))
def test_la_deriva_que_importa_sigue_sonando(caso: str, validador: Draft202012Validator) -> None:
    detalle = _detalle()
    ROMPE[caso](detalle["properties"]["products"])
    assert list(validador.iter_errors(detalle)), (
        f"«{caso}» rompe algo que la tuberia lee y el contrato lo deja pasar"
    )


#: Ruido que **no** debe sonar: productos que CENTINELA no abre nunca.
CALLA: dict[str, Callable[[dict[str, Any]], None]] = {
    "impact-text sin version": lambda p: p["impact-text"][0]["properties"].clear(),
    "general-text nuevo y raro": lambda p: p.__setitem__("general-text", [{"contents": []}]),
    "event-sequence con contents lista": lambda p: p["event-sequence"][0].__setitem__(
        "contents", []
    ),
    "un producto que USGS invente mañana": lambda p: p.__setitem__("lo-que-sea", [{"a": 1}]),
}


@pytest.mark.parametrize("caso", sorted(CALLA))
def test_lo_que_no_se_consume_no_dispara_la_alarma(
    caso: str, validador: Draft202012Validator
) -> None:
    detalle = _detalle()
    CALLA[caso](detalle["properties"]["products"])
    assert list(validador.iter_errors(detalle)) == [], (
        f"«{caso}» no toca nada que la tuberia lea y aun asi rompe el contrato"
    )


def test_el_esquema_solo_exige_de_cada_producto_lo_que_su_lector_usa() -> None:
    """La regla que hace falta recordar al editar el esquema.

    `losspager` no trae `version` y `shakemap` si: pedirles lo mismo fue el
    error original, en la direccion contraria.
    """
    esquema = json.loads(ESQUEMA.read_text(encoding="utf-8"))
    productos = esquema["properties"]["properties"]["properties"]["products"]
    versionado = esquema["$defs"]["productoVersionado"]["items"]["properties"]["properties"]
    pager = esquema["$defs"]["productoPager"]["items"]["properties"]["properties"]

    assert versionado["required"] == ["version"]
    assert pager["required"] == ["alertlevel"]
    assert "version" not in pager.get("required", [])
    assert productos["additionalProperties"] == {"type": "array"}
