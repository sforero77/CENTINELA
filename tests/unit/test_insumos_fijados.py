"""El digest de insumos: la puerta que detiene un insumo republicado.

El caso real que la motiva: un dataset de HDX republicado —misma URL estable,
mismo nombre de recurso, geometria distinta— dejo a un pais entero fuera del
sistema durante horas, y el fallo aparecio al final de la cadena disfrazado de
error de geometria.

Lo que impedia cerrarlo no era falta de disciplina: era que el campo tenia la
forma equivocada. `sha256` es escalar y una fuente del manifest no es un
fichero —GHS-POP son nueve u once teselas, el desglose etario veinte rasters, un
COD-AB el shapefile con su .dbf y su .prj, y Overture no baja ninguno—, asi que
las 194 fuentes de los diecinueve manifests llevaban el campo vacio desde el
primer dia porque no habia un fichero al que pertenecer.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
import yaml

from pipelines.common.manifest import Manifest, Source, fijar_insumos_en_manifest
from pipelines.p0_exposure.build import write_measurement
from pipelines.p0_exposure.download import (
    Descargado,
    InsumoAusenteError,
    InsumoCambiadoError,
    _verificar_insumos,
    digest_de_insumos,
    resumen_de_insumos,
)


def _bajado(nombre: str, sha: str, *, source_id: str = "cod_ab_arg") -> Descargado:
    return Descargado(
        source_id=source_id,
        layer="divisions",
        path=Path("descargas") / "divisions" / nombre,
        sha256=sha,
        bytes=1024,
    )


# --- El digest -------------------------------------------------------------


def test_el_orden_de_descarga_no_cambia_el_digest() -> None:
    """Las teselas GHSL no llegan en un orden garantizado.

    Si el digest dependiera del orden, el mismo insumo daria valores distintos
    entre corridas y la puerta se volveria un generador de falsos positivos —que
    es la forma mas rapida de que alguien la desactive.
    """
    uno = [_bajado("a.shp", "a" * 64), _bajado("b.dbf", "b" * 64)]
    otro = [_bajado("b.dbf", "b" * 64), _bajado("a.shp", "a" * 64)]
    assert digest_de_insumos(uno) == digest_de_insumos(otro)


def test_un_byte_distinto_da_otro_digest() -> None:
    original = [_bajado("adm2.shp", "a" * 64), _bajado("adm2.dbf", "b" * 64)]
    republicado = [_bajado("adm2.shp", "a" * 64), _bajado("adm2.dbf", "c" * 64)]
    assert digest_de_insumos(original) != digest_de_insumos(republicado)


def test_un_fichero_que_falta_da_otro_digest() -> None:
    """Perder el .prj de un shapefile no falla al abrirlo: reproyecta mal.

    Es justo la clase de cambio que no levanta ninguna excepcion y sale como una
    cifra plausible al otro extremo del pipeline.
    """
    completo = [
        _bajado("adm2.shp", "a" * 64),
        _bajado("adm2.dbf", "b" * 64),
        _bajado("adm2.prj", "c" * 64),
    ]
    assert digest_de_insumos(completo) != digest_de_insumos(completo[:2])


def test_el_nombre_entra_en_el_digest() -> None:
    """Dos teselas que intercambian contenido son un fallo del selector.

    Sin el nombre en la linea, el conjunto de hashes seria identico y el digest
    no veria nada.
    """
    bien = [_bajado("R9_C11.tif", "a" * 64), _bajado("R9_C12.tif", "b" * 64)]
    cruzado = [_bajado("R9_C11.tif", "b" * 64), _bajado("R9_C12.tif", "a" * 64)]
    assert digest_de_insumos(bien) != digest_de_insumos(cruzado)


# --- La puerta -------------------------------------------------------------


def _fuente(**kw: Any) -> Source:
    base: dict[str, Any] = {
        "id": "cod_ab_arg",
        "layer": "divisions",
        "url": "https://data.humdata.org/dataset/cod-ab-arg",
        "license": "CC-BY-IGO",
        "vintage": "COD-AB-2025-05-27",
    }
    return Source.from_dict(base | kw)


def test_un_insumo_republicado_detiene_el_build() -> None:
    """El fallo que costo horas: mismo dataset, geometria distinta."""
    llegado = [_bajado("arg_adm2.shp", "9" * 64)]
    fuente = _fuente(insumos_sha256="f" * 64)
    with pytest.raises(InsumoCambiadoError) as exc:
        _verificar_insumos(fuente, llegado)

    mensaje = str(exc.value)
    # El mensaje tiene que bastar para decidir sin abrir el codigo: que fuente,
    # que se esperaba, que llego, y que hacer con ello.
    assert "cod_ab_arg" in mensaje
    assert "f" * 64 in mensaje
    assert "arg_adm2.shp" in mensaje
    assert "9" * 64 in mensaje


def test_el_insumo_intacto_no_molesta() -> None:
    llegado = [_bajado("arg_adm2.shp", "9" * 64)]
    fuente = _fuente(insumos_sha256=digest_de_insumos(llegado))
    _verificar_insumos(fuente, llegado)  # no levanta


def test_sin_digest_fijado_el_build_sigue() -> None:
    """Los diecinueve manifests arrancan sin digest y tienen que poder construir.

    Una puerta que rompe el sistema el dia que se instala no se instala: se
    revierte. El digest se mide primero y se exige despues.
    """
    _verificar_insumos(_fuente(insumos_sha256=""), [_bajado("arg_adm2.shp", "9" * 64)])


def test_una_fuente_remota_no_se_verifica() -> None:
    """Overture no baja un byte: no hay nada que comparar, y fingirlo seria peor."""
    remota = _fuente(
        id="overture_buildings",
        layer="buildings",
        url="s3://overturemaps-us-west-2/release/2026-08-19.0/theme=buildings/type=building",
        license="ODbL-1.0",
        vintage="2026-08-19.0",
        insumos_sha256="f" * 64,
    )
    _verificar_insumos(remota, [])


def test_una_fuente_que_descarga_y_vuelve_vacia_detiene_el_build() -> None:
    """Vacio no es lo mismo que remoto, y suponerlo era el agujero.

    Medido con Peru el 27-ago-2026: el JRC estuvo caido tres horas, cada tesela
    GHSL agoto sus reintentos, `download_ghsl` las conto como "probablemente
    solo oceano" y el pais se ensamblo con poblacion 0. Lo detuvo el assert de
    §6.4 pero al final de la cadena, tras agregar 24 millones de edificaciones.
    """
    with pytest.raises(InsumoAusenteError) as exc:
        _verificar_insumos(_fuente(id="ghs_pop_2025", layer="pop_ghs"), [])

    mensaje = str(exc.value)
    assert "ghs_pop_2025" in mensaje
    assert "pop_ghs" in mensaje


def test_vuelve_vacia_tambien_falla_sin_digest_fijado() -> None:
    """No depende de haber fijado el digest: hoy los 194 estan vacios.

    Si esta puerta solo actuara sobre fuentes ya fijadas, no serviria para nada
    hasta la proxima reconstruccion — que es justo cuando hace falta.
    """
    with pytest.raises(InsumoAusenteError):
        _verificar_insumos(_fuente(id="ghs_pop_2025", layer="pop_ghs", insumos_sha256=""), [])


# --- Lo que se publica junto al activo --------------------------------------


def _manifest_min() -> Manifest:
    return Manifest.from_dict(
        {
            "manifest_id": "arg-v0.6",
            "iso3": "ARG",
            "generated_utc": "2026-08-23T00:00:00Z",
            "sources": [
                {
                    "id": "cod_ab_arg",
                    "layer": "divisions",
                    "url": "https://data.humdata.org/dataset/cod-ab-arg",
                    "hdx_dataset": "cod-ab-arg",
                    "license": "CC-BY-IGO",
                    "vintage": "COD-AB-2025-05-27",
                },
                {
                    "id": "overture_buildings",
                    "layer": "buildings",
                    "url": "s3://overturemaps-us-west-2/release/2026-08-19.0/theme=buildings/type=building",
                    "license": "ODbL-1.0",
                    "vintage": "2026-08-19.0",
                },
            ],
        }
    )


def test_el_resumen_conserva_el_hash_de_cada_fichero() -> None:
    """Un digest que no cuadra solo dice *que* la fuente cambio.

    El detalle por fichero es lo que permite decir *que fichero*, y por eso se
    publica: sin el, diagnosticar exige reconstruir el pais.
    """
    inventario = [_bajado("arg_adm2.shp", "a" * 64), _bajado("arg_adm2.dbf", "b" * 64)]
    resumen = resumen_de_insumos(_manifest_min(), inventario)

    assert resumen["cod_ab_arg"]["ficheros"] == {
        "arg_adm2.dbf": "b" * 64,
        "arg_adm2.shp": "a" * 64,
    }
    assert resumen["cod_ab_arg"]["insumos_sha256"] == digest_de_insumos(inventario)


def test_la_fuente_remota_se_declara_igual() -> None:
    """Que no toque el disco no la saca del activo: sigue siendo su procedencia."""
    resumen = resumen_de_insumos(_manifest_min(), [])
    assert resumen["overture_buildings"] == {"remoto": True, "vintage": "2026-08-19.0"}
    assert "insumos_sha256" not in resumen["overture_buildings"]


def test_la_medicion_publica_los_insumos(tmp_path: Path) -> None:
    """Los hashes se calculaban en cada corrida y se tiraban.

    `_registrar` los computa desde siempre; del inventario solo llegaba al log
    un conteo de ficheros y un total de bytes. Este es el punto donde dejan de
    perderse, y viaja en el fichero que ya se publica en el Release.
    """
    salida = tmp_path / "iso3=ARG" / "layer=exposure"
    salida.mkdir(parents=True)
    plan = SimpleNamespace(
        iso3="ARG", salida=salida, manifest=SimpleNamespace(manifest_id="arg-v0.6")
    )
    insumos = resumen_de_insumos(_manifest_min(), [_bajado("arg_adm2.shp", "a" * 64)])

    ruta = write_measurement(plan, {"pop_total": 1.0}, rescate={}, insumos=insumos)
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    assert datos["insumos"]["cod_ab_arg"]["ficheros"]["arg_adm2.shp"] == "a" * 64


# --- El volcado al manifest -------------------------------------------------

MANIFEST_CON_PROSA = """# Manifest de vintages — Argentina (Fase 0).
#
# REGLA DURA: nunca "latest".

manifest_id: arg-v0.6
iso3: ARG
generated_utc: "2026-08-23T00:00:00Z"

sources:
  - id: cod_ab_arg
    layer: divisions
    url: https://data.humdata.org/dataset/cod-ab-arg
    hdx_dataset: cod-ab-arg
    license: CC-BY-IGO
    vintage: COD-AB-2025-05-27
    insumos_sha256: ""
    notes: >-
      Common Operational Dataset de OCHA. Esta nota existe para comprobar que
      el volcado no se la lleva por delante.

  - id: overture_buildings
    layer: buildings
    url: s3://overturemaps-us-west-2/release/2026-08-19.0/theme=buildings/type=building
    license: ODbL-1.0
    vintage: "2026-08-19.0"
    insumos_sha256: ""
"""


def test_fijar_no_destruye_los_comentarios(tmp_path: Path) -> None:
    """Los manifests llevan mas prosa que datos, y esa prosa es el trabajo.

    `yaml.safe_dump` reescribiria el fichero y se llevaria por delante todos los
    comentarios y el plegado de las notas. Por eso el volcado edita por lineas.
    """
    path = tmp_path / "ARG.yaml"
    path.write_text(MANIFEST_CON_PROSA, encoding="utf-8")

    parte = fijar_insumos_en_manifest(path, {"cod_ab_arg": "a" * 64})
    texto = path.read_text(encoding="utf-8")

    assert 'REGLA DURA: nunca "latest".' in texto
    assert "el volcado no se la lleva por delante" in texto
    assert f'insumos_sha256: "{"a" * 64}"' in texto
    assert parte == [f"[cod_ab_arg] fijado {'a' * 64}"]
    # Y sigue siendo YAML valido y cargable como manifest.
    assert Manifest.load("ARG", tmp_path).sources[0].insumos_sha256 == "a" * 64


def test_fijar_no_pisa_un_digest_que_no_coincide(tmp_path: Path) -> None:
    """Sobrescribir en silencio convertiria la puerta en un sello de goma.

    Un digest fijado que no coincide con lo medido ES el caso que
    `_verificar_insumos` esta para detener. Aceptarlo sin preguntar seria
    reintroducir el fallo por la puerta de atras.
    """
    path = tmp_path / "ARG.yaml"
    ya_fijado = MANIFEST_CON_PROSA.replace(
        '    insumos_sha256: ""\n    notes: >-',
        f'    insumos_sha256: "{"f" * 64}"\n    notes: >-',
    )
    path.write_text(ya_fijado, encoding="utf-8")

    parte = fijar_insumos_en_manifest(path, {"cod_ab_arg": "a" * 64})
    assert Manifest.load("ARG", tmp_path).sources[0].insumos_sha256 == "f" * 64
    assert parte and "SIN TOCAR" in parte[0]


def test_fijar_anade_la_clave_si_no_estaba(tmp_path: Path) -> None:
    """El schema no la exige, asi que una fuente puede no declararla."""
    path = tmp_path / "ARG.yaml"
    path.write_text(
        MANIFEST_CON_PROSA.replace('    insumos_sha256: ""\n    notes: >-', "    notes: >-"),
        encoding="utf-8",
    )

    parte = fijar_insumos_en_manifest(path, {"cod_ab_arg": "a" * 64})
    assert Manifest.load("ARG", tmp_path).sources[0].insumos_sha256 == "a" * 64
    assert parte and "clave anadida" in parte[0]
    assert "el volcado no se la lleva por delante" in path.read_text(encoding="utf-8")


def test_el_volcado_cierra_el_circuito(tmp_path: Path) -> None:
    """Build mide -> medicion.json publica -> fijar-insumos vuelca.

    Es el circuito completo, y existe porque copiar a mano 194 hashes en
    diecinueve paises no es tedioso: es que no ocurre. Que es exactamente por
    que llevaban vacios desde el primer dia.
    """
    path = tmp_path / "ARG.yaml"
    path.write_text(MANIFEST_CON_PROSA, encoding="utf-8")
    inventario = [_bajado("arg_adm2.shp", "a" * 64), _bajado("arg_adm2.dbf", "b" * 64)]

    medido = resumen_de_insumos(_manifest_min(), inventario)
    digests = {
        sid: datos["insumos_sha256"] for sid, datos in medido.items() if "insumos_sha256" in datos
    }
    fijar_insumos_en_manifest(path, digests)

    fijado = Manifest.load("ARG", tmp_path).sources[0]
    # Y ahora la puerta reconoce el mismo insumo y deja pasar el build.
    _verificar_insumos(fijado, inventario)
    # Pero no el republicado.
    republicado = [_bajado("arg_adm2.shp", "a" * 64), _bajado("arg_adm2.dbf", "9" * 64)]
    with pytest.raises(InsumoCambiadoError):
        _verificar_insumos(fijado, republicado)


def test_los_manifests_del_repo_declaran_la_clave_nueva() -> None:
    """El rename toco 194 lineas en diecinueve ficheros; ninguna se queda atras.

    El schema tiene `additionalProperties: false`, asi que un `sha256:` olvidado
    seria un error de forma. Esta prueba lo dice sin depender de eso.
    """
    from pipelines.common.paths import MANIFESTS_DIR

    for path in sorted(MANIFESTS_DIR.glob("*.yaml")):
        crudo = yaml.safe_load(path.read_text(encoding="utf-8"))
        for fuente in crudo["sources"]:
            assert "sha256" not in fuente, f"{path.name}/{fuente['id']} conserva la clave vieja"
            assert "insumos_sha256" in fuente, f"{path.name}/{fuente['id']} no declara el digest"
