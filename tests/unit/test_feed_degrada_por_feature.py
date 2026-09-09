"""Una feature rota no puede tumbar la vigilancia de una región entera.

EL RADIO ERA EL EQUIVOCADO. El principio —antes fallar que publicar un evento
mal leido— es correcto y no se toca. Pero `parse_feed` lo aplicaba a un feed
**mundial**: un `mag: null` en un sismo de Indonesia dejaba a LATAM sin vigilar
hasta que alguien mirara, y la excepcion subia hasta `cli.main`, que solo atrapa
`NotImplementedError`, asi que salia como caida sin diagnostico.

Se aplica la distincion que el proyecto ya usa en el repaso, en FIRMS, en la
frescura y en el rezago: que falle **alguna** es tolerable; que fallen **todas**
es no haber leido el feed.
"""

from __future__ import annotations

from typing import Any

import pytest

from pipelines.p1_trigger.feed import FeedContractError, parse_feed


def _feature(usgs_id: str, *, mag: float | None = 6.0) -> dict[str, Any]:
    return {
        "type": "Feature",
        "id": usgs_id,
        "properties": {
            "mag": mag,
            "place": "en algun sitio",
            "time": 1,
            "updated": 1,
            "url": "u",
            "detail": "d",
        },
        "geometry": {"type": "Point", "coordinates": [-75.0, 5.0, 30.0]},
    }


def _feed(*features: dict[str, Any]) -> dict[str, Any]:
    return {"type": "FeatureCollection", "features": list(features)}


def test_una_feature_rota_no_se_lleva_a_las_demas() -> None:
    """El caso real: un sismo sin magnitud en la otra punta del mundo."""
    leidos = parse_feed(_feed(_feature("us1"), _feature("us2", mag=None), _feature("us3")))

    assert [c.usgs_id for c in leidos] == ["us1", "us3"]


def test_si_no_se_puede_leer_ninguna_eso_si_sube() -> None:
    """Un feed que llega entero y no da un solo candidato legible **cambio de forma**.

    Tragarselo seria el cero silencioso: "cero eventos relevantes" es una noche
    tranquila perfectamente normal, y confundirla con "el contrato se rompio"
    dejaria la vigilancia caida sin que nada se pusiera rojo.
    """
    with pytest.raises(FeedContractError, match="cambio de forma"):
        parse_feed(_feed(_feature("us1", mag=None), _feature("us2", mag=None)))


def test_un_feed_sin_eventos_no_es_un_fallo() -> None:
    """Cero features es una noche tranquila, no una ruptura de contrato."""
    assert parse_feed(_feed()) == []


def test_el_feed_que_no_es_una_coleccion_sigue_subiendo() -> None:
    """Lo que ya fallaba ruidosamente tiene que seguir fallando igual."""
    with pytest.raises(FeedContractError, match="FeatureCollection"):
        parse_feed({"type": "Feature", "features": []})
