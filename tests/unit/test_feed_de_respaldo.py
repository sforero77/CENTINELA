"""El feed de respaldo de 24 h: la garantía «no se pierde un sismo».

`docs/GARANTIAS.md` la declara y dice «`test_enrutado_latam` cubre el caso».
No lo cubre: ese fichero no toca el feed. Y la fixture `fetcher` que usa media
suite sirve el feed de respaldo **vacío**, así que en toda la suite no había una
sola prueba donde `4.5_day` aportara un evento que `4.5_hour` no tuviera — que
es exactamente el único caso para el que existe.

Un mecanismo de rescate que nunca se ejercita es un mecanismo del que no se sabe
nada. El escenario real: GitHub Actions documenta demoras del cron de 5 a 30
minutos, y una parada más larga —el healthcheck detectó una el 27-ago— deja
fuera de `4.5_hour` cualquier sismo ocurrido durante la parada.
"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import pytest

from pipelines.common.constants import USGS_FEED_BACKFILL, USGS_FEED_PRIMARY
from pipelines.common.http import FixtureFetcher
from pipelines.p1_trigger.feed import feed_url
from pipelines.p1_trigger.run import run_trigger

VACIO: dict[str, Any] = {"type": "FeatureCollection", "features": []}


def _con_id(feature: dict[str, Any], usgs_id: str) -> dict[str, Any]:
    """Copia el rasgo con otro identificador, para simular un evento distinto."""
    otro = copy.deepcopy(feature)
    otro["id"] = usgs_id
    otro["properties"] = dict(otro["properties"])
    otro["properties"]["detail"] = otro["properties"]["detail"].replace(str(feature["id"]), usgs_id)
    return otro


@pytest.fixture
def feed(feed_payload: dict[str, Any]) -> dict[str, Any]:
    return feed_payload


def test_un_sismo_que_solo_esta_en_el_respaldo_se_despacha(
    feed: dict[str, Any], events_dir: Path
) -> None:
    """EL CASO QUE LA GARANTÍA PROMETE Y NADIE PROBABA.

    El cron se retrasó, el sismo cayó fuera de la ventana de una hora y solo
    aparece en el feed de 24 h.
    """
    fetcher = FixtureFetcher(
        {
            feed_url(USGS_FEED_PRIMARY): VACIO,
            feed_url(USGS_FEED_BACKFILL): feed,
        }
    )

    resultado = run_trigger(fetcher, events_dir=events_dir)

    assert resultado.revisados > 0, "el feed de respaldo no se llegó a leer"
    assert resultado.a_despachar, "un sismo solo presente en el respaldo no se despachó"


def test_el_mismo_sismo_en_los_dos_feeds_se_despacha_una_vez(
    feed: dict[str, Any], events_dir: Path
) -> None:
    """El caso normal: los dos feeds se solapan y no puede contarse dos veces."""
    fetcher = FixtureFetcher(
        {
            feed_url(USGS_FEED_PRIMARY): feed,
            feed_url(USGS_FEED_BACKFILL): feed,
        }
    )

    resultado = run_trigger(fetcher, events_dir=events_dir)

    assert len(resultado.a_despachar) == len(set(resultado.a_despachar))

    otro = events_dir.parent / "solo_primario"
    otro.mkdir()
    solo_primario = run_trigger(
        FixtureFetcher({feed_url(USGS_FEED_PRIMARY): feed, feed_url(USGS_FEED_BACKFILL): VACIO}),
        events_dir=otro,
    )
    assert resultado.revisados == solo_primario.revisados, (
        "el solape entre feeds infla el recuento de revisados"
    )


def test_un_sismo_distinto_en_cada_feed_se_despachan_los_dos(
    feed: dict[str, Any], events_dir: Path
) -> None:
    """El rescate no puede costar el evento que sí llegó por el feed rápido."""
    original = feed["features"][0]
    otro_feed = {**feed, "features": [_con_id(original, "us9999rescate")]}

    fetcher = FixtureFetcher(
        {
            feed_url(USGS_FEED_PRIMARY): feed,
            feed_url(USGS_FEED_BACKFILL): otro_feed,
        }
    )

    resultado = run_trigger(fetcher, events_dir=events_dir)

    assert set(resultado.a_despachar) >= {str(original["id"]), "us9999rescate"}


def test_el_respaldo_se_lee_aunque_el_primario_venga_lleno(
    feed: dict[str, Any], events_dir: Path
) -> None:
    """Leer solo el segundo feed cuando el primero viene vacío sería un atajo.

    Un sismo puede caer entre la ventana de una hora y la de un día sin que la
    de una hora esté vacía: pasa cada vez que el cron se salta una corrida.
    """
    pedidas: list[str] = []

    class _Espia(FixtureFetcher):
        def get_json(self, url: str) -> Any:
            pedidas.append(url)
            return super().get_json(url)

    fetcher = _Espia(
        {
            feed_url(USGS_FEED_PRIMARY): feed,
            feed_url(USGS_FEED_BACKFILL): VACIO,
        }
    )
    run_trigger(fetcher, events_dir=events_dir)

    assert any(USGS_FEED_BACKFILL in u for u in pedidas), (
        "con el feed rápido lleno ya no se consulta el de respaldo"
    )


def test_la_garantia_cita_una_prueba_que_de_verdad_toca_el_feed() -> None:
    """`GARANTIAS.md` citaba `test_enrutado_latam`, que no toca el feed.

    Una garantía que cita la prueba equivocada es peor que una sin cita: manda
    a quien la audite a leer un fichero que no dice nada del asunto.
    """
    raiz = Path(__file__).parent.parent.parent
    garantias = (raiz / "docs" / "GARANTIAS.md").read_text(encoding="utf-8")
    bloque = garantias[garantias.index("no se pierde") : garantias.index("no se pierde") + 2000]
    citada = "test_feed_de_respaldo"
    assert citada in bloque, (
        f"la garantía del feed de respaldo no cita {citada}, que es la que la ejercita"
    )

    fuente = Path(__file__).read_text(encoding="utf-8")
    assert "USGS_FEED_BACKFILL" in fuente and "run_trigger" in fuente
