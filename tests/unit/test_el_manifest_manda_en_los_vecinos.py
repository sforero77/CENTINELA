"""El release que se descarga tiene que ser el que el manifest declara.

`data/manifests/` promete, en su propio docstring, «declarar por pais
exactamente que version de que fuente entro al activo». Para los poligonos de
los paises vecinos eso no era cierto por partida doble:

* el release salia de una constante escrita a mano en `build.py`
  (`OVERTURE_RELEASE_POR_DEFECTO = "2026-08-19.0"`), no del manifest;
* dieciocho de los diecinueve manifests **no declaraban** la fuente
  `overture_divisions` que el build si consumia, asi que `resolve_bucket`
  evaluaba la regla de los tres cubos sobre un conjunto de licencias que no era
  el conjunto de fuentes consumidas.

Y no es un detalle de contabilidad: esos poligonos deciden de donde puede
rescatar celdas el reparto. Sin ellos, «fuera del pais y cerca» incluye el otro
lado de la frontera — medido, Paraguay se llevaba 459.518 personas de Brasil,
Argentina y Bolivia, el 93 % de su desvio frente a la ONU.

El fallo tenia fecha de caducidad puesta: Overture publica release mensual y
conserva **dos**, el cron del trimestral corre cada tres meses, asi que los
manifests renuevan su release por obligacion y nada renovaba la constante. El
dia que caducara, `select_files` reventaria, el `except Exception` lo convertiria
en un `_log.warning`, el valor de retorno se descartaba en el llamador, y el
activo saldria robandole poblacion al vecino con todos los asserts en verde.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest
import yaml

from pipelines.p0_exposure import build

RAIZ = Path(__file__).parent.parent.parent
MANIFESTS = RAIZ / "data" / "manifests"

#: Los temas de Overture que el build consume, y la capa del manifest que los
#: tiene que declarar. `divisions` es el que faltaba.
TEMAS_CONSUMIDOS = {
    "buildings": "buildings",
    "transportation": "roads",
    "divisions": "divisions",
}


def _manifests() -> list[Path]:
    return sorted(MANIFESTS.glob("*.yaml"))


def _fuentes(ruta: Path) -> list[dict[str, Any]]:
    datos = yaml.safe_load(ruta.read_text(encoding="utf-8"))
    fuentes: list[dict[str, Any]] = datos["sources"]
    return fuentes


@pytest.mark.parametrize("ruta", _manifests(), ids=lambda p: p.stem)
@pytest.mark.parametrize("tema,capa", sorted(TEMAS_CONSUMIDOS.items()))
def test_cada_tema_de_overture_que_se_consume_esta_declarado(
    ruta: Path, tema: str, capa: str
) -> None:
    """Consumir una fuente sin declararla rompe la relacion causal del manifest."""
    de_overture = [
        f for f in _fuentes(ruta) if f["url"].startswith("s3://") and f"theme={tema}" in f["url"]
    ]
    assert de_overture, (
        f"{ruta.stem} no declara el tema {tema!r} de Overture y el build lo consume. "
        f"El conjunto de licencias que evalua `resolve_bucket` no seria el conjunto "
        f"de fuentes que entro al activo."
    )
    fuente = de_overture[0]
    assert fuente["layer"] == capa, f"{ruta.stem}: {fuente['id']} deberia ir en la capa {capa!r}"
    assert fuente["license"] == "ODbL-1.0", (
        f"{ruta.stem}: {fuente['id']} no declara ODbL-1.0, que es la licencia de Overture"
    )


@pytest.mark.parametrize("ruta", _manifests(), ids=lambda p: p.stem)
def test_los_tres_temas_van_al_mismo_release(ruta: Path) -> None:
    """Mezclar releases no reventaria: daria un activo silenciosamente mestizo.

    Los ficheros de cada tema se resuelven contra su propio catalogo, asi que
    dos releases distintos descargan sin error. Lo que sale es un activo cuyas
    edificaciones y cuyas fronteras no son del mismo dia, y eso no se ve en
    ninguna cifra publicada.
    """
    releases = {f["vintage"] for f in _fuentes(ruta) if f["url"].startswith("s3://")}
    assert len(releases) == 1, f"{ruta.stem} mezcla releases de Overture: {sorted(releases)}"


def test_el_release_no_esta_escrito_a_mano_en_el_codigo() -> None:
    """La constante cubria «la llamada suelta» y en realidad cubria todo.

    `build_country` era el unico llamador en produccion y no pasaba release.
    Este guardia es contra la tentacion de reponerla: un valor por defecto aqui
    vuelve a desconectar el manifest de los bytes sin que nada falle.
    """
    fuente = (RAIZ / "pipelines" / "p0_exposure" / "build.py").read_text(encoding="utf-8")
    codigo = "\n".join(x for x in fuente.splitlines() if not x.lstrip().startswith("#"))
    fechas = re.findall(r"\"20\d\d-\d\d-\d\d\.\d\"", codigo)
    assert not fechas, (
        f"hay un release de Overture escrito a mano en build.py: {fechas}. "
        f"Tiene que salir del manifest, que es lo unico que se renueva cuando "
        f"Overture retira el release viejo."
    )
    assert not hasattr(build, "OVERTURE_RELEASE_POR_DEFECTO")


# --------------------------------------------------------------------------
# Y que el fallo no vuelva a ser mudo.
# --------------------------------------------------------------------------


class _FetcherFalso:
    """No se llega a usar: los dos caminos se cortan antes o se monkeypatchean."""


def test_sin_release_no_se_construye(monkeypatch: pytest.MonkeyPatch) -> None:
    """Un manifest que no fija el release no puede caer a `latest` en silencio."""
    with pytest.raises(ValueError, match="no fija el release"):
        build.load_country_neighbours(
            None, "COL", bbox=build.BBox(-80, -5, -66, 13), fetcher=_FetcherFalso(), release=""
        )


def test_overture_caido_detiene_el_build(monkeypatch: pytest.MonkeyPatch) -> None:
    """El release caducado es el modo de falla previsto, y ya no es un warning.

    Antes esto devolvia 0 y seguia. El activo se terminaba de construir, pasaba
    los asserts de calidad y se publicaba como Release — con el reparto sin
    acotar dentro.
    """
    from pipelines.p0_exposure.sources import overture

    def revienta(*_a: object, **_k: object) -> list[str]:
        raise RuntimeError("404 sobre collection.json: el release ya no existe")

    monkeypatch.setattr(overture, "select_files", revienta)

    with pytest.raises(ValueError, match="El build se detiene a proposito"):
        build.load_country_neighbours(
            None,
            "PRY",
            bbox=build.BBox(-63, -28, -54, -19),
            fetcher=_FetcherFalso(),
            release="2026-08-19.0",
        )


def test_cero_vecinos_detiene_el_build(monkeypatch: pytest.MonkeyPatch) -> None:
    """Overture contesta y no deja ni un poligono: el filtro esta mal, no el mapa.

    En los diecinueve paises del catalogo cero vecinos nunca es la verdad — solo
    Cuba no toca a nadie por tierra, y hasta su caja alcanza a Haiti y Jamaica.
    Asi se descubrio que la poda por contencion descartaba a Brasil entero.
    """
    from pipelines.p0_exposure import overture_h3
    from pipelines.p0_exposure.sources import overture

    monkeypatch.setattr(overture, "select_files", lambda *_a, **_k: ["f1"])
    monkeypatch.setattr(overture, "resolve_data_urls", lambda *_a, **_k: ["https://x/f1"])
    monkeypatch.setattr(overture_h3, "load_neighbours", lambda *_a, **_k: 0)

    with pytest.raises(ValueError, match="ni un poligono de vecino"):
        build.load_country_neighbours(
            None,
            "CUB",
            bbox=build.BBox(-85, 19, -74, 24),
            fetcher=_FetcherFalso(),
            release="2026-08-19.0",
        )


def test_los_vecinos_cargados_quedan_en_la_medicion(tmp_path: Path) -> None:
    """El numero de vecinos se descartaba en el llamador y no llegaba a ningun sitio.

    Sin el, un activo construido sin acotar el reparto es indistinguible de uno
    acotado: las dos cosas publican `rescate` y las dos cuadran.
    """
    import json
    from types import SimpleNamespace

    from pipelines.common.manifest import Manifest

    plan = SimpleNamespace(
        iso3="PRY",
        # El manifest de verdad: `write_measurement` publica tambien el cubo,
        # que es una propiedad calculada sobre las licencias de las fuentes.
        manifest=Manifest.load("PRY"),
        salida=tmp_path,
    )
    ruta = build.write_measurement(plan, {"pop_total": 1.0}, rescate={}, vecinos=7)
    assert json.loads(ruta.read_text(encoding="utf-8"))["vecinos"] == 7
