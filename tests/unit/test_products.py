"""Resolucion de productos del feed detail (§2.1)."""

from __future__ import annotations

from typing import Any

import pytest

from pipelines.p2_impact.products import ProductContractError, parse_products


def test_elige_la_version_preferida(detail_con_productos: dict[str, Any]) -> None:
    productos = parse_products(detail_con_productos)
    assert productos.shakemap_version == 3
    assert productos.groundfailure_version == 2


def test_ignora_productos_borrados(detail_con_productos: dict[str, Any]) -> None:
    """El producto v9 tiene mayor peso pero status=DELETE: no debe ganar."""
    assert parse_products(detail_con_productos).shakemap_version != 9


def test_url_de_contornos(detail_con_productos: dict[str, Any]) -> None:
    url = parse_products(detail_con_productos).cont_mmi_url()
    assert url is not None
    assert url.endswith("cont_mmi.json")


def test_pager_solo_como_referencia(detail_con_productos: dict[str, Any]) -> None:
    assert parse_products(detail_con_productos).pager_alert() == "orange"


def test_evento_sin_shakemap(detail_sin_shakemap: dict[str, Any]) -> None:
    productos = parse_products(detail_sin_shakemap)
    assert not productos.has_shakemap
    assert productos.shakemap_version == 0
    assert productos.cont_mmi_url() is None
    assert productos.pager_alert() == ""


def test_detail_sin_products_rompe_el_contrato() -> None:
    with pytest.raises(ProductContractError):
        parse_products({"id": "us1", "properties": {}})


def test_preferred_weight_elige_contribuidor_no_version() -> None:
    """El eje que desempata `preferredWeight` es quien aporta, no cual version.

    Dos contribuidores publican ShakeMap del mismo evento. Gana el de mayor
    peso; dentro de el, la version mas reciente — aunque el otro contribuidor
    tenga un numero de version mas alto.
    """
    detail = {
        "id": "us0000dual",
        "properties": {
            "products": {
                "shakemap": [
                    {
                        "source": "atlas",
                        "status": "UPDATE",
                        "preferredWeight": 10,
                        "updateTime": 9_000,
                        "properties": {"version": "99"},
                        "contents": {},
                    },
                    {
                        "source": "us",
                        "status": "UPDATE",
                        "preferredWeight": 231,
                        "updateTime": 5_000,
                        "properties": {"version": "2"},
                        "contents": {},
                    },
                    {
                        "source": "us",
                        "status": "UPDATE",
                        "preferredWeight": 228,
                        "updateTime": 8_000,
                        "properties": {"version": "3"},
                        "contents": {},
                    },
                ]
            }
        },
    }
    # Gana 'us' por peso; dentro de 'us', v3 por ser mas reciente pese a pesar
    # menos que v2. Ese es exactamente el caso real de us6000t7zp.
    assert parse_products(detail).shakemap_version == 3
