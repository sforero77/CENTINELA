"""«Se verifica en CI» era falso, y este fichero es el que lo vuelve verdad.

La tercera linea de `ATTRIBUTION.md` afirmaba que toda salida de CENTINELA lleva
sus atribuciones y que se verifica en CI. Medido punto por punto:

* `grep -rn ATTRIBUTION_LINE tests/` no devolvia **nada**.
* Ningun test comparaba `ATTRIBUTION.md` con las licencias de los manifiestos.
* ESA WorldCover no aparecia en `ATTRIBUTION.md` (`grep -c -i worldcover` -> 0)
  pese a estar declarada en los diecinueve manifiestos bajo CC BY 4.0 y a
  publicarse su dato en `site/incendios.json` y en las columnas `lulc_*_pct`.
* El pie de todo mapa no citaba WorldPop, de donde sale `pop_65p`, que el
  reporte publica en portada como «De ellas, 65 años o más».
* El pie del visor citaba cuatro fuentes y cerraba con «Datos del núcleo bajo
  CC BY 4.0» sobre datos que `resolve_bucket` resuelve a **ODbL en los
  diecinueve paises**.
* NASA FIRMS no estaba en ningun manifiesto, en ningun `LICENSE_BUCKET` y en
  ningun credito: la regla de los tres cubos no la habia visto jamas.
* Y la carpeta de un reporte no llevaba ni un LICENSE ni un NOTICE, con la ODbL
  §4.3 exigiendo que el aviso viaje con la obra producida.

El guardia va contra **todo el catalogo**, no contra las fuentes de hoy: la
forma de este fallo es que entre una fuente nueva y nadie se acuerde de citarla,
que es exactamente como entro WorldCover.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from pipelines.common.atribucion import (
    CATALOGO,
    INCENDIOS,
    MAPA,
    REPORTE,
    VISOR,
    FuenteSinCreditoError,
    atribuciones_de,
    claves_de_fuente,
    para_superficie,
)
from pipelines.p2_impact.pipeline import licencia_del_reporte
from pipelines.p3_report.static_map import ATTRIBUTION_LINE

RAIZ = Path(__file__).parent.parent.parent
MANIFESTS = RAIZ / "data" / "manifests"
ATRIBUCION_MD = RAIZ / "ATTRIBUTION.md"
INDEX_HTML = RAIZ / "site" / "index.html"


def _ids_del_catalogo() -> list[str]:
    """Todos los `id` de fuente declarados en los diecinueve manifiestos."""
    ids: set[str] = set()
    for ruta in sorted(MANIFESTS.glob("*.yaml")):
        datos = yaml.safe_load(ruta.read_text(encoding="utf-8"))
        ids.update(str(s["id"]) for s in datos["sources"])
    return sorted(ids)


IDS = _ids_del_catalogo()


@pytest.mark.parametrize("source_id", IDS)
def test_toda_fuente_declarada_tiene_a_quien_atribuir(source_id: str) -> None:
    """Publicar el dato de alguien sin citarlo incumple su licencia.

    Es un error y no una lista vacia a proposito: un credito ausente que degrada
    en silencio es indistinguible de una fuente que no exige atribucion.
    """
    claves = claves_de_fuente(source_id)
    assert claves, source_id
    for clave in claves:
        assert clave in CATALOGO, f"{source_id} apunta a {clave!r}, que no esta en el catalogo"


def test_una_fuente_desconocida_es_un_error_y_no_un_silencio() -> None:
    with pytest.raises(FuenteSinCreditoError, match="no tiene credito declarado"):
        claves_de_fuente("una_fuente_que_nadie_declaro_2027")


#: Se busca `Atribucion.aguja`, que cada entrada declara.
#:
#: La primera version recortaba el titulo a ojo —hasta la raya, hasta el
#: parentesis, hasta la coma— y fallaba en dos de doce: `ATTRIBUTION.md` cita
#: «USGS Earthquake Hazards Program» mientras el pie del mapa dice «USGS
#: ShakeMap», y el titulo que el DANE pide lleva su propia URL dentro. Un guardia
#: que aprueba o rechaza segun como este puntuada una frase es un cerrojo
#: tipografico, no una comprobacion.


@pytest.mark.parametrize("clave", sorted(CATALOGO))
def test_cada_credito_del_catalogo_esta_en_attribution_md(clave: str) -> None:
    """El fichero que dice llevarlas todas tiene que llevarlas todas."""
    texto = ATRIBUCION_MD.read_text(encoding="utf-8")
    assert CATALOGO[clave].aparece_en(texto), (
        f"{CATALOGO[clave].titulo} no aparece en ATTRIBUTION.md, que afirma en su "
        f"tercera linea que toda salida lleva estas atribuciones"
    )


def test_el_pie_de_los_mapas_cita_lo_que_el_mapa_publica() -> None:
    """WorldPop faltaba, y de ahi sale «De ellas, 65 años o más»."""
    for atribucion in para_superficie(CATALOGO.values(), MAPA):
        assert atribucion.aparece_en(ATTRIBUTION_LINE), (
            f"{atribucion.titulo} no sale en el pie de los mapas y su dato si"
        )


def test_el_pie_del_visor_cita_lo_que_el_visor_publica() -> None:
    """Cuatro fuentes de las diez, y la cobertura del suelo pintada en pantalla."""
    html = INDEX_HTML.read_text(encoding="utf-8")
    # Solo el pie: el resto de la pagina menciona fuentes en prosa explicativa,
    # y un guardia que confunde la prosa con el credito aprueba cualquier cosa.
    pie = html.split("<footer>", 1)[1].split("</footer>", 1)[0]
    for atribucion in para_superficie(CATALOGO.values(), VISOR):
        assert atribucion.aparece_en(pie), (
            f"{atribucion.titulo} no sale en el pie del visor y su dato si"
        )


def test_el_visor_no_dice_cc_by_sobre_datos_odbl() -> None:
    """Decia «Datos del núcleo bajo CC BY 4.0» y los diecinueve dan `odbl`.

    No era una imprecision: la ODbL §4.4 exige que el derivado se publique bajo
    ODbL, asi que la linea anterior declaraba la licencia equivocada.
    """
    pie = INDEX_HTML.read_text(encoding="utf-8").split("<footer>", 1)[1].split("</footer>", 1)[0]
    assert "Datos del núcleo bajo CC BY 4.0" not in pie
    assert "ODbL" in pie


# --------------------------------------------------------------------------
# Y que viaje **dentro** del artefacto, no solo en una pagina del repositorio.
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "ruta", sorted((RAIZ / "reports").glob("*/report.json")), ids=lambda p: p.parent.name
)
def test_cada_reporte_publicado_lleva_su_licencia(ruta: Path) -> None:
    """La carpeta de un reporte no llevaba ni un LICENSE ni un NOTICE."""
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    licencia = datos.get("licencia") or {}
    assert licencia.get("spdx") == "ODbL-1.0", (
        f"{ruta.parent.name} no declara licencia; los diecinueve activos resuelven "
        f"a ODbL y la ODbL §4.3 exige que el aviso viaje con la obra producida"
    )
    assert licencia.get("cubo") == "odbl"
    assert licencia.get("atribuciones"), "una licencia sin a quien citar no es una licencia"
    assert licencia.get("manifiesto_url", "").endswith(".yaml"), (
        "el cuarto disclaimer remite a «el manifiesto enlazado» y no habia enlace"
    )

    aviso = ruta.parent / "LICENSE.txt"
    assert aviso.is_file(), f"{ruta.parent.name} no tiene LICENSE.txt al lado del dato"
    texto = aviso.read_text(encoding="utf-8")
    assert "ODbL" in texto
    for atribuido in licencia["atribuciones"]:
        assert atribuido["titulo"] in texto


def test_el_bloque_se_calcula_y_no_se_escribe_a_mano() -> None:
    """La regla vive en `resolve_bucket`; una segunda copia en prosa diverge.

    Es literalmente como el pie del visor acabo diciendo CC BY 4.0 sobre datos
    ODbL: alguien escribio la licencia a mano una vez y el dato cambio debajo.
    """
    licencia = licencia_del_reporte("col-v0.6")
    assert licencia.spdx == "ODbL-1.0"
    assert licencia.cubo == "odbl"
    assert any("WorldPop" in a.titulo for a in licencia.atribuciones)
    assert any("WorldCover" in a.titulo for a in licencia.atribuciones)


def test_un_manifest_irreconocible_no_tumba_el_reporte() -> None:
    """Un reporte tiene que poder publicarse aunque su manifest este mal escrito.

    Quien lo tiene que cazar es el guardia de esquema, no una excepcion en medio
    de la publicacion de un sismo en vivo.
    """
    assert licencia_del_reporte("").spdx == ""
    assert licencia_del_reporte("no-es-un-pais").spdx == ""


def test_incendios_declara_firms_que_no_estaba_en_ningun_manifest() -> None:
    """Su fuente primaria no la habia evaluado nunca la regla de los tres cubos."""
    from pipelines.p5_incendios.incendios import FUENTES_DE_INCENDIOS

    atribuciones = para_superficie(atribuciones_de(FUENTES_DE_INCENDIOS, evento=False), INCENDIOS)
    titulos = [a.titulo for a in atribuciones]
    assert any("FIRMS" in t for t in titulos), titulos
    assert any("WorldCover" in t for t in titulos), titulos
    assert any("OpenStreetMap" in t for t in titulos), titulos


def test_el_reporte_cita_mas_que_el_mapa() -> None:
    """Cada superficie declara lo suyo, y no todas publican lo mismo.

    El PNG no dibuja cobertura del suelo ni aeropuertos; el `report.json` si los
    trae detras. Si las dos listas fueran iguales, la distincion por superficie
    seria decorativa y el guardia no estaria comprobando nada.
    """
    todas = atribuciones_de([s for s in IDS if s.startswith(("ghs", "overture", "worldcover"))])
    del_mapa = para_superficie(todas, MAPA)
    del_reporte = para_superficie(todas, REPORTE)
    assert set(del_mapa) < set(del_reporte)
