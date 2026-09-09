"""Eleccion de la geometria administrativa y de sus columnas.

Los dos puntos donde un pais nuevo se rompe de forma silenciosa: tomar el
archivo equivocado dentro de una entrega con varios niveles, y asumir que las
columnas se llaman como en Colombia.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pipelines.p0_exposure.build import ADM2_HINTS, pick_admin_source
from pipelines.p0_exposure.crosswalk import COD_AB_COLUMNS, admin_columns

#: Lo que trae el ZIP del COD-AB de Venezuela, verificado abriendolo.
COD_AB_VEN = [
    Path("ven_admin0.shp"),
    Path("ven_admin1.shp"),
    Path("ven_admin2.shp"),
    Path("ven_admin3.shp"),
    Path("ven_adminlines.shp"),
    Path("ven_adminpoints.shp"),
]


def test_del_cod_ab_se_toma_el_nivel_municipal() -> None:
    """Tomar el primero daria el pais entero como un solo 'municipio'."""
    assert pick_admin_source(COD_AB_VEN).name == "ven_admin2.shp"


def test_el_mgn_del_dane_se_reconoce_por_mpio() -> None:
    """Colombia no usa COD-AB: su archivo se llama por la nomenclatura DIVIPOLA."""
    entrega = [Path("MGN_ADM_MPIO_GRAFICO.shp")]
    assert pick_admin_source(entrega).name == "MGN_ADM_MPIO_GRAFICO.shp"


def test_una_sola_capa_sin_pista_se_acepta() -> None:
    """Si no hay ambiguedad, no hay nada que adivinar."""
    assert pick_admin_source([Path("limites.gpkg")]).name == "limites.gpkg"


def test_varias_capas_sin_pista_es_error() -> None:
    """Adivinar aqui da un crosswalk con el numero de municipios equivocado."""
    with pytest.raises(ValueError, match="No se puede elegir"):
        pick_admin_source([Path("capa_a.shp"), Path("capa_b.shp")])


def test_dos_capas_municipales_es_error() -> None:
    """Dos fuentes de municipios en el mismo build es un manifest mal armado."""
    with pytest.raises(ValueError, match="No se puede elegir"):
        pick_admin_source([Path("ven_admin2.shp"), Path("otro_adm2.geojson")])


def test_sin_geometria_es_error() -> None:
    with pytest.raises(ValueError, match="geometria administrativa"):
        pick_admin_source([Path("tabla.xlsx"), Path("leeme.txt")])


@pytest.mark.parametrize("suffix", [".shp", ".gpkg", ".geojson"])
def test_se_aceptan_los_formatos_que_st_read_abre(suffix: str) -> None:
    """El COD-AB llega en GeoJSON en 14 de los 19 paises y en SHP en cinco."""
    assert pick_admin_source([Path(f"pais_admin2{suffix}")]).suffix == suffix


def test_el_metadata_json_de_hotosm_no_cuenta_como_capa() -> None:
    """Los extractos de HOTOSM traen un metadata.json junto al GeoPackage.

    Tomarlo por una capa hace que ``ST_Read`` falle con "Could not open GDAL
    dataset", que es justo lo que paso al probar la extraccion del ZIP.
    """
    entrega = [Path("health_facilities.gpkg"), Path("metadata.json")]
    assert pick_admin_source(entrega).name == "health_facilities.gpkg"


def test_las_pistas_cubren_las_dos_nomenclaturas() -> None:
    assert "admin2" in ADM2_HINTS and "mpio" in ADM2_HINTS


# --- Mapeo de columnas -----------------------------------------------------


def test_colombia_usa_las_columnas_del_dane() -> None:
    variantes = admin_columns("COL")
    assert len(variantes) == 1
    assert variantes[0].adm2_id == "mpio_cdpmp"


def test_el_resto_cae_en_cod_ab() -> None:
    """Es lo que hace que agregar un pais sea escribir un manifest, no codigo."""
    from pipelines.p0_exposure.crosswalk import COD_AB_VARIANTES

    for iso3 in ("VEN", "MEX", "PER", "ECU", "CHL", "GTM", "BRA"):
        assert admin_columns(iso3) is COD_AB_VARIANTES


def test_el_cod_ab_tiene_dos_nomenclaturas() -> None:
    """Medido: Venezuela usa adm2_name y Ecuador adm2_es.

    Ecuador fallo el primer build con "no trae las columnas ['adm2_name',
    'adm1_name']" y un listado que traia adm0_es, adm1_es y adm2_es. Las dos
    conviven en el COD-AB segun cuando se publico la entrega.
    """
    from pipelines.p0_exposure.crosswalk import COD_AB_VARIANTES, match_columns

    ven = {"adm2_pcode", "adm2_name", "adm1_pcode", "adm1_name", "geom"}
    ecu = {"adm0_es", "adm0_pcode", "adm1_es", "adm1_pcode", "adm2_es", "adm2_pcode", "geom"}

    assert match_columns(COD_AB_VARIANTES, ven) is not None
    assert match_columns(COD_AB_VARIANTES, ecu) is not None
    assert match_columns(COD_AB_VARIANTES, ven) != match_columns(COD_AB_VARIANTES, ecu)


def test_una_nomenclatura_desconocida_no_encaja() -> None:
    """Anadir una variante tiene que ser deliberado, no un acierto por azar."""
    from pipelines.p0_exposure.crosswalk import COD_AB_VARIANTES, match_columns

    assert match_columns(COD_AB_VARIANTES, {"codigo", "nombre", "geom"}) is None


def test_las_columnas_de_cod_ab_son_las_medidas_en_el_archivo() -> None:
    """No son los ADM2_PCODE/ADM2_ES que documenta HDX para entregas viejas."""
    assert COD_AB_COLUMNS.adm2_id == "adm2_pcode"
    assert COD_AB_COLUMNS.nombre == "adm2_name"
    assert COD_AB_COLUMNS.adm1_id == "adm1_pcode"
    assert COD_AB_COLUMNS.departamento == "adm1_name"


def test_el_mapeo_no_distingue_mayusculas_en_el_iso() -> None:
    assert admin_columns("col") is admin_columns("COL")


def test_las_columnas_se_comparan_sin_distinguir_mayusculas() -> None:
    """HDX documenta ADM2_PCODE; el shapefile lo devuelve en minusculas."""
    from pipelines.p0_exposure.crosswalk import COD_AB_VARIANTES, match_columns

    mayusculas = {"ADM2_PCODE", "ADM2_NAME", "ADM1_PCODE", "ADM1_NAME"}
    assert match_columns(COD_AB_VARIANTES, mayusculas) is not None


# --- Escritura atomica de las descargas ------------------------------------


def test_una_descarga_completa_deja_el_archivo(tmp_path: Path) -> None:
    from pipelines.p0_exposure.download import write_atomic

    destino = tmp_path / "raster.tif"
    assert write_atomic(destino, b"contenido") == destino
    assert destino.read_bytes() == b"contenido"


def test_no_queda_rastro_del_parcial(tmp_path: Path) -> None:
    from pipelines.common.http import PARTIAL_SUFFIX
    from pipelines.p0_exposure.download import write_atomic

    destino = tmp_path / "raster.tif"
    write_atomic(destino, b"contenido")
    assert not (tmp_path / f"raster.tif{PARTIAL_SUFFIX}").exists()
    assert [p.name for p in tmp_path.iterdir()] == ["raster.tif"]


def test_una_descarga_cortada_no_ocupa_el_destino(tmp_path: Path) -> None:
    """El motivo de existir de write_atomic.

    Todas las rutas de descarga saltan lo que ya esta en disco. Si un corte de
    red dejara el archivo truncado en su nombre final, la siguiente corrida lo
    daria por bueno: un raster de poblacion a medias se abre sin error, solo le
    faltan filas.
    """
    from pipelines.common.http import PARTIAL_SUFFIX
    from pipelines.p0_exposure.download import write_atomic

    destino = tmp_path / "raster.tif"
    parcial = tmp_path / f"raster.tif{PARTIAL_SUFFIX}"
    parcial.write_bytes(b"a medias")  # simula el corte antes del rename
    assert not destino.exists()

    write_atomic(destino, b"entero")
    assert destino.read_bytes() == b"entero"


def test_sobrescribe_un_destino_previo(tmp_path: Path) -> None:
    """Un vintage nuevo tiene que poder reemplazar al anterior."""
    from pipelines.p0_exposure.download import write_atomic

    destino = tmp_path / "raster.tif"
    destino.write_bytes(b"viejo")
    write_atomic(destino, b"nuevo")
    assert destino.read_bytes() == b"nuevo"


# --- Empate entre dos fuentes municipales ----------------------------------

#: Colombia declara dos: el MGN del DANE y el adm2 del COD-AB reempaquetado.
EMPATE_COL = [Path("MGN_ADM_MPIO_GRAFICO.shp"), Path("col_admbnda_adm2_dane_2024.shp")]


def test_dos_fuentes_municipales_sin_conexion_es_error() -> None:
    """Sin poder mirar columnas, elegir seria adivinar."""
    with pytest.raises(ValueError, match="No se puede elegir"):
        pick_admin_source(EMPATE_COL, iso3="COL")


@pytest.mark.geo
def test_el_empate_se_deshace_por_las_columnas_declaradas(tmp_path: Path) -> None:
    """Colombia declara las columnas del DANE, asi que gana el MGN.

    Es el caso real: al fijar el recurso correcto del COD-AB, Colombia pasa a
    tener dos capas municipales y hay que quedarse con la fuente de verdad del
    codigo DIVIPOLA.
    """
    import json

    from pipelines.p2_impact.exposure_join import connect

    def _capa(nombre: str, propiedades: dict[str, str]) -> Path:
        ruta = tmp_path / nombre
        ruta.write_text(
            json.dumps(
                {
                    "type": "FeatureCollection",
                    "features": [
                        {
                            "type": "Feature",
                            "properties": propiedades,
                            "geometry": {
                                "type": "Polygon",
                                "coordinates": [[[0, 0], [0, 1], [1, 1], [0, 0]]],
                            },
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        return ruta

    mgn = _capa(
        "MGN_ADM_MPIO_GRAFICO.geojson",
        {
            "mpio_cdpmp": "05001",
            "mpio_cnmbr": "Medellín",
            "dpto_ccdgo": "05",
            "dpto_cnmbr": "Antioquia",
        },
    )
    cod_ab = _capa(
        "col_admbnda_adm2_2024.geojson",
        {
            "adm2_pcode": "CO05001",
            "adm2_name": "Medellin",
            "adm1_pcode": "CO05",
            "adm1_name": "Antioquia",
        },
    )

    elegida = pick_admin_source([cod_ab, mgn], iso3="COL", con=connect())
    assert elegida.name == "MGN_ADM_MPIO_GRAFICO.geojson"


# --- Reanudar una descarga de HDX ------------------------------------------


def _source(**extra: str) -> object:
    from pipelines.common.manifest import Source

    datos = {
        "id": "cod_ab_col",
        "layer": "divisions",
        "url": "https://data.humdata.org/dataset/cod-ab-col",
        "license": "CC-BY-IGO",
        "vintage": "COD-AB-2025",
        "hdx_dataset": "cod-ab-col",
        **extra,
    }
    return Source.from_dict(datos)


def test_sin_descarga_previa_no_hay_nada_en_disco(tmp_path: Path) -> None:
    from pipelines.p0_exposure.download import _hdx_en_disco

    assert _hdx_en_disco(_source(), tmp_path) == []  # type: ignore[arg-type]


def test_se_reconoce_un_zip_ya_extraido(tmp_path: Path) -> None:
    """El COD-AB de Colombia son 117 MB: repetirlo en cada reintento duele."""
    from pipelines.p0_exposure.download import _hdx_en_disco

    carpeta = tmp_path / "cod_ab_col"
    carpeta.mkdir()
    (carpeta / "col_admin2.shp").write_bytes(b"x")
    (carpeta / "col_admin1.shp").write_bytes(b"x")
    encontrados = _hdx_en_disco(_source(), tmp_path)  # type: ignore[arg-type]
    assert [p.name for p in encontrados] == ["col_admin1.shp", "col_admin2.shp"]


def test_se_reconoce_un_archivo_suelto(tmp_path: Path) -> None:
    from pipelines.p0_exposure.download import _hdx_en_disco

    (tmp_path / "cod_ab_col.gpkg").write_bytes(b"x")
    assert [p.name for p in _hdx_en_disco(_source(), tmp_path)] == ["cod_ab_col.gpkg"]  # type: ignore[arg-type]


def test_un_parcial_no_cuenta_como_descargado(tmp_path: Path) -> None:
    """Justo lo que write_atomic existe para evitar: dar por bueno lo truncado."""
    from pipelines.common.http import PARTIAL_SUFFIX
    from pipelines.p0_exposure.download import _hdx_en_disco

    (tmp_path / f"cod_ab_col.gpkg{PARTIAL_SUFFIX}").write_bytes(b"a medias")
    assert _hdx_en_disco(_source(), tmp_path) == []  # type: ignore[arg-type]


def test_un_zip_extraido_sin_capas_no_cuenta(tmp_path: Path) -> None:
    """Una carpeta con solo metadata.json es una extraccion fallida."""
    from pipelines.p0_exposure.download import _hdx_en_disco

    carpeta = tmp_path / "cod_ab_col"
    carpeta.mkdir()
    (carpeta / "metadata.json").write_bytes(b"{}")
    assert _hdx_en_disco(_source(), tmp_path) == []  # type: ignore[arg-type]


def test_todas_las_rutas_de_descarga_saltan_lo_que_ya_esta(tmp_path: Path) -> None:
    """Reanudar tiene que ser barato en TODAS las ramas, no en casi todas.

    Un build de un pais son ~1 GB y falla tarde —la lectura remota de Overture
    va al final—, asi que cada reintento repetia lo que ya estaba en disco. Esta
    prueba lee el codigo: es la unica forma de cubrir las seis ramas sin red.
    """
    import inspect

    from pipelines.p0_exposure import download

    # Las ramas viven en `_descargar_fuente`, no en `download_manifest`: salieron
    # aparte para que exista el momento en que los ficheros de UNA fuente estan
    # completos y se puede verificar su digest. Se comprueba tambien que el
    # orquestador siga llamandola — sin eso esta prueba volveria a leer una
    # funcion que ya no esta en el camino, que es el fallo que documenta abajo.
    assert "_descargar_fuente(" in inspect.getsource(download.download_manifest), (
        "download_manifest ya no delega en _descargar_fuente: esta prueba mira al lado equivocado"
    )
    fuente = inspect.getsource(download._descargar_fuente)
    # La rama generica de .tif/.csv era la que faltaba.
    assert "if not path.exists():" in fuente, "la rama generica volvio a descargar siempre"

    for funcion in (
        download.download_ghsl,
        download.download_worldpop_agesex,
        download.download_zip_completo,
        download.download_hdx,
    ):
        cuerpo = inspect.getsource(funcion)
        # Cada ruta comprueba a su manera —un fichero con `exists()`, una
        # carpeta extraida con `is_dir()`, HDX con su propio inventario— asi
        # que se aceptan las tres. Exigir una sola forma haria fallar a codigo
        # correcto, que es como esta prueba acabo apuntando a la funcion
        # muerta: `download_zip_entries` decia `exists()` y la viva no.
        sondas = ("exists()", "is_dir()", "_hdx_en_disco")
        assert any(sonda in cuerpo for sonda in sondas), (
            f"{funcion.__name__} no comprueba si el archivo ya esta en disco"
        )


# --- Copias del mismo nivel -------------------------------------------------

#: Lo que trae el COD-AB de El Salvador: cada nivel por duplicado.
COD_AB_SLV = [
    Path("slv_admin0.geojson"),
    Path("slv_admin0_em.geojson"),
    Path("slv_admin1.geojson"),
    Path("slv_admin1_em.geojson"),
    Path("slv_admin2.geojson"),
    Path("slv_admin2_em.geojson"),
    Path("slv_adminlines.geojson"),
]


def test_una_copia_del_nivel_no_detiene_el_build() -> None:
    """Medido: slv_admin2 y slv_admin2_em traen los mismos 48 registros.

    Detener el build por una copia identica seria pedantico; elegir al azar
    entre dos archivos distintos, peligroso. Se toma el nombre sin decorar.
    """
    assert pick_admin_source(COD_AB_SLV).name == "slv_admin2.geojson"


def test_si_solo_existe_la_variante_se_usa() -> None:
    """Descartar copias no puede convertirse en descartar la unica capa."""
    solo_em = [Path("slv_admin1_em.geojson"), Path("slv_admin2_em.geojson")]
    assert pick_admin_source(solo_em).name == "slv_admin2_em.geojson"


def test_dos_capas_municipales_distintas_siguen_siendo_error() -> None:
    """El descarte de copias no debe tapar un empate de verdad."""
    with pytest.raises(ValueError, match="No se puede elegir"):
        pick_admin_source([Path("pais_admin2.shp"), Path("otro_adm2.geojson")])


def test_el_sufijo_del_nombre_es_el_idioma_de_la_entrega() -> None:
    """Brasil rompio el supuesto: `_es` no era "version antigua" sino espanol.

    Su COD-AB trae adm2_pt, y el archivo mezcla adm0_en con adm0_pt. El sufijo
    es el idioma, no una version del formato — obvio en retrospectiva, y no
    anticipado hasta que Brasil fallo.
    """
    from pipelines.p0_exposure.crosswalk import COD_AB_VARIANTES, match_columns

    brasil = {
        "adm0_en",
        "adm0_pcode",
        "adm0_pt",
        "adm1_pcode",
        "adm1_pt",
        "adm2_pcode",
        "adm2_pt",
        "geom",
    }
    mapeo = match_columns(COD_AB_VARIANTES, brasil)
    assert mapeo is not None
    assert mapeo.nombre == "adm2_pt"


def test_hay_variante_para_las_cuatro_nomenclaturas_vistas() -> None:
    from pipelines.p0_exposure.crosswalk import COD_AB_NAME_SUFFIXES

    assert COD_AB_NAME_SUFFIXES == ("name", "es", "pt", "en")
