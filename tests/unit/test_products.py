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
