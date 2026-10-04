"""El release de Overture pasa solo al nuevo, sin abrir la puerta del 27-ago.

Overture publica release mensual y conserva dos, asi que el fijado caduca solo.
Pasarlo al nuevo era editar diecinueve manifests, subir diecinueve versiones y
pegar diecinueve huellas en una prueba: quedo a mano desde el primer dia y el
27-sep-2026 se hizo a mano, a un release de quedarse sin camino de vuelta.

Lo que estas pruebas atan es que automatizarlo no rompa la garantia del cerrojo:
un `manifest_id` sigue identificando una receta y solo una.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from pipelines.common.manifest import Manifest
from pipelines.common.recetas import (
    RecetaReescritaError,
    huella_del_manifest,
    pasar_a_release,
    registrar,
    registro,
    release_fijado,
    siguiente_version,
    ultimo_release_de_overture,
)

VIEJO, NUEVO = "2026-08-19.0", "2026-09-23.1"

MANIFEST = f"""# Panama. Esta prosa tiene que sobrevivir: menciona {VIEJO} a proposito.

manifest_id: pan-v0.3
iso3: PAN
generated_utc: "2026-09-09T00:00:00Z"

sources:
  - id: hotosm_health
    layer: health
    url: https://data.humdata.org/dataset/hotosm_pan_health_facilities
    license: ODbL-1.0
    vintage: "2026-09"
  - id: overture_buildings
    layer: buildings
    url: s3://overturemaps-us-west-2/release/{VIEJO}/theme=buildings/type=building
    license: ODbL-1.0
    vintage: "{VIEJO}"
    notes: >-
      Se paso a {VIEJO} el 9-sep.
  - id: overture_transportation
    layer: roads
    url: s3://overturemaps-us-west-2/release/{VIEJO}/theme=transportation/type=segment
    license: ODbL-1.0
    vintage: "{VIEJO}"
"""


@pytest.fixture
def dirs(tmp_path: Path) -> tuple[Path, Path]:
    manifests, recetas = tmp_path / "manifests", tmp_path / "recetas"
    manifests.mkdir()
    (manifests / "PAN.yaml").write_text(MANIFEST, encoding="utf-8")
    registrar("PAN", manifests_dir=manifests, recetas_dir=recetas)
    return manifests, recetas


def test_pasa_las_fuentes_de_overture_y_sube_la_version(dirs: tuple[Path, Path]) -> None:
    manifests, recetas = dirs
    paso = pasar_a_release("PAN", NUEVO, manifests_dir=manifests, recetas_dir=recetas)

    assert paso is not None and paso.manifest_id == "pan-v0.4"
    m = Manifest.load("PAN", manifests)
    assert m.manifest_id == "pan-v0.4"
    overture = [s for s in m.sources if s.url.startswith("s3://")]
    assert all(f"/release/{NUEVO}/" in s.url and s.vintage == NUEVO for s in overture)


def test_no_toca_lo_que_no_es_overture(dirs: tuple[Path, Path]) -> None:
    """Ni las otras fuentes ni la prosa, aunque la prosa nombre el release viejo."""
    manifests, recetas = dirs
    pasar_a_release("PAN", NUEVO, manifests_dir=manifests, recetas_dir=recetas)
    texto = (manifests / "PAN.yaml").read_text(encoding="utf-8")

    assert f"menciona {VIEJO} a proposito" in texto
    assert f"Se paso a {VIEJO} el 9-sep." in texto
    assert 'vintage: "2026-09"' in texto


def test_registra_la_receta_nueva_y_conserva_la_vieja(dirs: tuple[Path, Path]) -> None:
    manifests, recetas = dirs
    antes = registro("PAN", recetas)
    pasar_a_release("PAN", NUEVO, manifests_dir=manifests, recetas_dir=recetas)
    despues = registro("PAN", recetas)

    assert despues.items() >= antes.items()
    assert despues["pan-v0.4"] == huella_del_manifest("PAN", manifests)[1]


def test_si_ya_esta_al_dia_no_hace_nada(dirs: tuple[Path, Path]) -> None:
    manifests, recetas = dirs
    pasar_a_release("PAN", NUEVO, manifests_dir=manifests, recetas_dir=recetas)
    assert pasar_a_release("PAN", NUEVO, manifests_dir=manifests, recetas_dir=recetas) is None
    assert Manifest.load("PAN", manifests).manifest_id == "pan-v0.4"


def test_cambiar_fuentes_sin_subir_version_no_se_registra(dirs: tuple[Path, Path]) -> None:
    """El fallo del 27-ago, intentado contra el registro: tiene que negarse."""
    manifests, recetas = dirs
    ruta = manifests / "PAN.yaml"
    ruta.write_text(
        ruta.read_text(encoding="utf-8").replace("theme=buildings", "theme=places"),
        encoding="utf-8",
    )
    with pytest.raises(RecetaReescritaError):
        registrar("PAN", manifests_dir=manifests, recetas_dir=recetas)


def test_respeta_el_fin_de_linea(tmp_path: Path) -> None:
    """En Windows git saca los manifests en CRLF; reescribir en LF seria un diff entero."""
    manifests, recetas = tmp_path / "m", tmp_path / "r"
    manifests.mkdir()
    (manifests / "PAN.yaml").write_bytes(MANIFEST.replace("\n", "\r\n").encode("utf-8"))
    registrar("PAN", manifests_dir=manifests, recetas_dir=recetas)
    pasar_a_release("PAN", NUEVO, manifests_dir=manifests, recetas_dir=recetas)

    crudo = (manifests / "PAN.yaml").read_bytes()
    assert b"\r\n" in crudo and b"\n" not in crudo.replace(b"\r\n", b"")
    assert release_fijado("PAN", manifests) == NUEVO


@pytest.mark.parametrize(
    ("antes", "despues"), [("pan-v0.4", "pan-v0.5"), ("col-v0.9", "col-v0.10")]
)
def test_siguiente_version(antes: str, despues: str) -> None:
    assert siguiente_version(antes) == despues


class _Catalogo:
    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload

    def get_json(self, url: str) -> dict[str, Any]:
        return self.payload

    def get_bytes(self, url: str) -> bytes:
        raise AssertionError("el catalogo se lee como JSON")


def _catalogo(latest: str, hijos: list[str]) -> _Catalogo:
    return _Catalogo(
        {
            "latest": latest,
            "links": [
                {"rel": "child", "href": f"https://stac.overturemaps.org/{h}/catalog.json"}
                for h in hijos
            ],
        }
    )


def test_el_ultimo_release_sale_del_catalogo() -> None:
    assert ultimo_release_de_overture(_catalogo(NUEVO, [VIEJO, NUEVO])) == NUEVO


def test_un_latest_que_no_se_sirve_es_un_catalogo_a_medio_publicar() -> None:
    with pytest.raises(ValueError):
        ultimo_release_de_overture(_catalogo("2026-10-21.0", [VIEJO, NUEVO]))


def test_un_latest_con_forma_rara_no_se_fija() -> None:
    with pytest.raises(ValueError):
        ultimo_release_de_overture(_catalogo("latest", [VIEJO]))


def test_los_registros_del_repo_son_json_ordenado() -> None:
    """Un registro escrito a mano con otra forma daria diffs de todo el fichero."""
    for ruta in sorted(
        (Path(__file__).parents[2] / "data" / "manifests" / "recetas").glob("*.json")
    ):
        datos = json.loads(ruta.read_text(encoding="utf-8"))
        assert (
            ruta.read_text(encoding="utf-8") == json.dumps(datos, indent=2, sort_keys=True) + "\n"
        )
