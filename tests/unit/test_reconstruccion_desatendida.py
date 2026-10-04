"""Un insumo republicado ya no para la reconstruccion: la decide la comparacion.

El 1-oct-2026 HOT y HDX republicaron las sedes de salud de cinco paises y los
limites de Paraguay. `_verificar_insumos` paro los seis builds —bien: el insumo
no era el fijado— y la incidencia pedia a una persona comparar y decidir. Nadie
lo hizo, y el activo de esos seis paises dejo de poder reconstruirse.

La pregunta que esa persona se haria es medible, y estas pruebas atan las tres
piezas que la contestan solas: el build sigue y anota el cambio, el activo nuevo
se compara con el publicado, y solo si se parece se fija el digest nuevo. Lo que
no puede pasar es que la bandera convierta la puerta en un sello de goma.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from pipelines.common.manifest import Manifest, Source, fijar_insumos_en_manifest
from pipelines.p0_exposure.comparar import MARGENES, comparar_mediciones, insumos_cambiados
from pipelines.p0_exposure.download import (
    Descargado,
    InsumoAusenteError,
    InsumoCambiadoError,
    _verificar_insumos,
    digest_de_insumos,
    resumen_de_insumos,
)

FIJADO = "f" * 64


def _bajado(nombre: str, sha: str) -> Descargado:
    return Descargado(
        source_id="hotosm_health",
        layer="health",
        path=Path("descargas") / "health" / nombre,
        sha256=sha,
        bytes=1024,
    )


def _fuente(**kw: Any) -> Source:
    base: dict[str, Any] = {
        "id": "hotosm_health",
        "layer": "health",
        "url": "https://data.humdata.org/dataset/hotosm_pan_health_facilities",
        "license": "ODbL-1.0",
        "vintage": "2026-09",
        "insumos_sha256": FIJADO,
    }
    return Source.from_dict(base | kw)


# --- La puerta, con y sin bandera --------------------------------------------


def test_sin_bandera_la_puerta_sigue_parando() -> None:
    """Lo de siempre: construir a mano no cambia de comportamiento."""
    with pytest.raises(InsumoCambiadoError):
        _verificar_insumos(_fuente(), [_bajado("pan_health.geojson", "9" * 64)])


def test_con_bandera_el_build_sigue() -> None:
    _verificar_insumos(_fuente(), [_bajado("pan_health.geojson", "9" * 64)], aceptar_cambio=True)


def test_la_bandera_no_tapa_una_fuente_vacia() -> None:
    """Republicado no es lo mismo que ausente: el cero silencioso sigue parando."""
    with pytest.raises(InsumoAusenteError):
        _verificar_insumos(_fuente(), [], aceptar_cambio=True)


def _manifest(digest: str) -> Manifest:
    return Manifest.from_dict(
        {
            "manifest_id": "pan-v0.4",
            "iso3": "PAN",
            "generated_utc": "2026-09-27T00:00:00Z",
            "sources": [
                {
                    "id": "hotosm_health",
                    "layer": "health",
                    "url": "https://data.humdata.org/dataset/hotosm_pan_health_facilities",
                    "license": "ODbL-1.0",
                    "vintage": "2026-09",
                    "insumos_sha256": digest,
                }
            ],
        }
    )


def test_el_cambio_aceptado_queda_anotado() -> None:
    """Sin el rastro, la medicion publicada no diria que el insumo cambio."""
    llegado = [_bajado("pan_health.geojson", "9" * 64)]
    resumen = resumen_de_insumos(_manifest(FIJADO), llegado)

    assert resumen["hotosm_health"]["fijado_antes"] == FIJADO
    assert insumos_cambiados({"insumos": resumen}) == {"hotosm_health": digest_de_insumos(llegado)}


def test_un_insumo_intacto_no_se_anota_como_cambiado() -> None:
    llegado = [_bajado("pan_health.geojson", "9" * 64)]
    resumen = resumen_de_insumos(_manifest(digest_de_insumos(llegado)), llegado)
    assert "fijado_antes" not in resumen["hotosm_health"]
    assert insumos_cambiados({"insumos": resumen}) == {}


# --- La comparacion con el publicado ------------------------------------------

PUBLICADO: dict[str, Any] = {
    "iso3": "PAN",
    "resumen": {
        "celdas": 52135,
        "pop_total": 4590423.0,
        "bld_count": 1800184,
        "health_count": 1096,
        "built_m2": 312943966.0,
        "edu_count": 2720,
        "road_km": 42478.9,
        "municipios": 76,
    },
}


def _con(**cambios: float) -> dict[str, Any]:
    return {"iso3": "PAN", "resumen": PUBLICADO["resumen"] | cambios}


def test_una_actualizacion_normal_pasa() -> None:
    """Unas sedes mas y un release de Overture con algo mas de edificios."""
    assert comparar_mediciones(PUBLICADO, _con(health_count=1180, bld_count=1850000)) == []


def test_perder_un_tercio_de_las_sedes_no_pasa() -> None:
    problemas = comparar_mediciones(PUBLICADO, _con(health_count=600))
    assert len(problemas) == 1 and problemas[0].startswith("health_count")


def test_una_capa_vacia_no_pasa_nunca() -> None:
    problemas = comparar_mediciones(PUBLICADO, _con(edu_count=0))
    assert problemas and "vacia" in problemas[0]


def test_la_poblacion_apenas_puede_moverse() -> None:
    """GHS-POP no cambia por un listado de sedes: si se mueve, algo se rompio."""
    assert comparar_mediciones(PUBLICADO, _con(pop_total=4590423.0 * 1.06))


def test_comparar_paises_distintos_es_un_error() -> None:
    assert comparar_mediciones(PUBLICADO, {"iso3": "PRY", "resumen": PUBLICADO["resumen"]})


def test_una_capa_nueva_sin_historial_no_bloquea() -> None:
    """Un activo publicado por una version anterior puede no tener la capa."""
    anterior = {"iso3": "PAN", "resumen": {"pop_total": 4590423.0}}
    assert comparar_mediciones(anterior, _con()) == []


def test_cada_margen_tiene_sentido() -> None:
    """Un margen negativo o una caida del 100 % desactivarian la capa en silencio."""
    for capa, margen in MARGENES.items():
        assert 0 < margen.caida < 1, capa
        assert margen.crecida > 0, capa


# --- El fijado: solo lo que el build anoto ------------------------------------

MANIFEST = f"""manifest_id: pan-v0.4
iso3: PAN
generated_utc: "2026-09-27T00:00:00Z"

sources:
  - id: hotosm_health
    layer: health
    url: https://data.humdata.org/dataset/hotosm_pan_health_facilities
    license: ODbL-1.0
    vintage: "2026-09"
    insumos_sha256: "{FIJADO}"
"""


def test_reemplaza_el_republicado_que_el_build_anoto(tmp_path: Path) -> None:
    path = tmp_path / "PAN.yaml"
    path.write_text(MANIFEST, encoding="utf-8")

    parte = fijar_insumos_en_manifest(
        path, {"hotosm_health": "a" * 64}, reemplazar={"hotosm_health": FIJADO}
    )

    assert Manifest.load("PAN", tmp_path).sources[0].insumos_sha256 == "a" * 64
    assert parte and "reemplazado" in parte[0]


def test_no_reemplaza_si_el_manifest_ya_fijaba_otra_cosa(tmp_path: Path) -> None:
    """Si alguien cambio el manifest entre el build y el fijado, no se adivina."""
    path = tmp_path / "PAN.yaml"
    path.write_text(MANIFEST, encoding="utf-8")

    parte = fijar_insumos_en_manifest(
        path, {"hotosm_health": "a" * 64}, reemplazar={"hotosm_health": "e" * 64}
    )

    assert Manifest.load("PAN", tmp_path).sources[0].insumos_sha256 == FIJADO
    assert parte and "SIN TOCAR" in parte[0]


def test_el_workflow_compara_antes_de_publicar() -> None:
    """El orden es el guardia: comparar, luego publicar, luego fijar."""
    texto = (
        Path(__file__).parents[2] / ".github" / "workflows" / "exposure_quarterly.yml"
    ).read_text(encoding="utf-8")

    comparar = texto.index("centinela comparar-medicion")
    publicar = texto.index("- name: Publicar Release versionado")
    fijar = texto.index("centinela fijar-insumos")
    assert comparar < publicar < fijar
    assert "--aceptar-insumos-nuevos" in texto
    assert "--aceptar-cambiados" in texto


def test_la_cli_compara_dos_mediciones(tmp_path: Path) -> None:
    from pipelines.cli import main

    anterior, nueva = tmp_path / "a.json", tmp_path / "n.json"
    anterior.write_text(json.dumps(PUBLICADO), encoding="utf-8")
    nueva.write_text(json.dumps(_con(health_count=1150)), encoding="utf-8")
    assert main(["comparar-medicion", str(anterior), str(nueva)]) == 0

    nueva.write_text(json.dumps(_con(health_count=200)), encoding="utf-8")
    assert main(["comparar-medicion", str(anterior), str(nueva)]) == 1


def test_el_2_de_calibrar_no_aborta_el_paso_que_anota() -> None:
    """Con el activo ya publicado, «hay que decidir la tolerancia» no puede tumbar el commit."""
    texto = (
        Path(__file__).parents[2] / ".github" / "workflows" / "exposure_quarterly.yml"
    ).read_text(encoding="utf-8")
    bloque = texto[texto.index("Anotar la medicion en el manifest") :]
    bloque = bloque[: bloque.index("centinela fijar-insumos")]

    assert 'uv run centinela calibrar --escribir "$MEDICION"' in bloque
    assert "set +e" in bloque and '"$CALIBRAR" -eq 2' in bloque
