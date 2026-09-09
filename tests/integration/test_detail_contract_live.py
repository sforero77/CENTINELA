"""Contrato vivo del feed *detail* de USGS (§6.2, nocturno).

`schemas/usgs/detail-products.schema.json` existía desde el principio y **no lo
cargaba nadie**: `grep -rn "detail-products"` sobre todo el repositorio devolvía
una sola coincidencia, su propio `$id`. Ni un test, ni un módulo, ni un workflow.
No es que se validara contra fixtures congeladas: no se validaba contra nada.

Y `docs/acciones/mantenimiento.md` afirmaba que el vigía nocturno «valida los
contratos de USGS (feed y productos de detalle) contra `schemas/usgs/` y falla si
el esquema derivó», mientras `contract_drift.yml` corría `pytest -m network`, que
solo tocaba el feed resumen, Overture y las cajas de cuatro países.

Este fichero es la mitad que faltaba. Corre igual que su hermano del feed: va
marcado `network` y lo ejecuta el workflow nocturno, que solo alerta.
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from jsonschema import Draft202012Validator

from pipelines.common.http import HttpFetcher
from pipelines.common.paths import SCHEMAS_DIR
from pipelines.p2_impact.products import NIVELES_PAGER, parse_products

pytestmark = pytest.mark.network

#: Dos eventos estables y publicados hace años: su detail ya no se mueve, así
#: que un fallo aquí es una deriva del contrato y no una revisión en curso.
EVENTOS = ("us6000tjl2", "us2000ahv0")

DETAIL_URL = "https://earthquake.usgs.gov/fdsnws/event/1/query?eventid={usgs_id}&format=geojson"


@pytest.fixture(scope="module")
def validador() -> Draft202012Validator:
    esquema = json.loads(
        (SCHEMAS_DIR / "usgs" / "detail-products.schema.json").read_text(encoding="utf-8")
    )
    return Draft202012Validator(esquema)


@pytest.fixture(scope="module")
def fetcher() -> HttpFetcher:
    return HttpFetcher(timeout_s=120.0)


@pytest.mark.parametrize("usgs_id", EVENTOS)
def test_el_detail_cumple_su_contrato(
    usgs_id: str, validador: Draft202012Validator, fetcher: HttpFetcher
) -> None:
    """Lo que P2 lee de cada producto tiene que seguir estando."""
    detail: dict[str, Any] = fetcher.get_json(DETAIL_URL.format(usgs_id=usgs_id))
    errores = sorted(validador.iter_errors(detail), key=str)
    assert errores == [], [f"{'.'.join(str(x) for x in e.path)}: {e.message}" for e in errores]


def test_el_esquema_no_acepta_un_products_vacio(validador: Draft202012Validator) -> None:
    """Si lo aceptara, el guardia de arriba no estaría comprobando nada.

    Y lo aceptaba: el esquema no tenía un solo `required` dentro de `products`,
    así que `{"products": {}}` y `{"products": {"shakemap": [{}]}}` pasaban.
    Sin esta prueba, endurecerlo y no endurecerlo se ven igual desde fuera.
    """
    for payload in (
        {"id": "us1", "properties": {"products": {"shakemap": [{}]}}},
        {
            "id": "us1",
            "properties": {"products": {"shakemap": [{"status": "UPDATE", "contents": {}}]}},
        },
    ):
        assert list(validador.iter_errors(payload)), f"el esquema todavía acepta {payload}"


@pytest.mark.parametrize("usgs_id", EVENTOS)
def test_el_nivel_de_pager_vivo_cabe_en_el_esquema_del_reporte(
    usgs_id: str, fetcher: HttpFetcher
) -> None:
    """USGS emite `pending` mientras el modelo corre, y el reporte lo prohíbe.

    Este es el otro lado del filtro: aquí se comprueba contra el feed vivo que
    lo que sale de `pager_alert()` sigue cabiendo en el enum de
    `report-1.0.schema.json`, sea cual sea lo que USGS esté publicando hoy.
    """
    detail: dict[str, Any] = fetcher.get_json(DETAIL_URL.format(usgs_id=usgs_id))
    assert parse_products(detail).pager_alert() in NIVELES_PAGER | {""}
