"""Tres promesas que se anulaban entre ellas, y el contrato que nadie miraba.

1. **RF-03 anulaba RF-04.** Agotada la ventana de seis horas sin ShakeMap, el
   evento pasaba a `DESCARTADO`, que es terminal por tres vías independientes:
   `state.py` no le declara ninguna transición de salida, `repaso.py` lo excluye
   del repaso de RF-04, y `decide` lo omitía **antes** de mirar `forzar`, así que
   ni `centinela impact --reprocesar` podía rescatarlo. Un ShakeMap tardío no se
   procesaba nunca — con una mediana de 63 días hasta la última revisión.

2. **`pending` no es un nivel de alerta.** USGS lo emite mientras el modelo PAGER
   corre y viajaba crudo a `report.json`, cuyo esquema cierra ese campo a
   `["", "green", "yellow", "orange", "red"]`. A los +27,5 min del Chocó ya había
   ShakeMap v2, o sea que el reporte era completo y se publicaba fuera de su
   propio contrato: en inglés en el `.md` y desaparecido del visor.

3. **Y nadie validaba el `report.json` publicado.** Las dos pruebas que lo hacen
   construyen el objeto a mano con `pager_alert="orange"` escrito en la fixture:
   comparan la cadena escrita contra la constante con la que se escribió.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from pipelines.common.state import EventState, EventStatus
from pipelines.p2_impact.pipeline import licencia_del_reporte
from pipelines.p2_impact.products import NIVELES_PAGER, ProductRef, ProductSet, parse_products
from pipelines.p2_impact.run import Action, decide
from pipelines.p3_report.model import Evento, Inputs, Report, Totales
from pipelines.p3_report.run import ReporteFueraDeContratoError, validar_contra_esquema

CHOCO = Path(__file__).parent.parent / "fixtures" / "golden" / "choco_2026_08_10"


# --------------------------------------------------------------------------
# `pending` no llega al artefacto publicado.
# --------------------------------------------------------------------------


def _con_alerta(nivel: str) -> ProductSet:
    return ProductSet(
        usgs_id="us6000tjl2",
        shakemap=None,
        ground_failure=None,
        losspager=ProductRef(
            tipo="losspager",
            version=1,
            actualizado_ms=0,
            contents={},
            props={"alertlevel": nivel},
        ),
    )


@pytest.mark.parametrize("nivel", sorted(NIVELES_PAGER))
def test_los_niveles_reales_pasan(nivel: str) -> None:
    assert _con_alerta(nivel).pager_alert() == nivel


@pytest.mark.parametrize("crudo", ["pending", "PENDING", "unknown", "verde"])
def test_lo_que_no_es_un_nivel_se_publica_como_ausencia(crudo: str) -> None:
    """No es una alerta desconocida: es que PAGER todavía no ha dicho nada."""
    assert _con_alerta(crudo).pager_alert() == ""


def test_pending_esta_en_el_detail_real_del_choco() -> None:
    """Que el caso no es teórico lo dice la fixture congelada.

    Si algún día USGS deja de emitirlo, esta prueba avisa de que el filtro ya no
    cubre nada real — y un guardia que no cubre nada es peor que ninguno.
    """
    detail: dict[str, Any] = json.loads(
        (CHOCO / "detail_superseded.json").read_text(encoding="utf-8")
    )
    niveles = {
        str((e.get("properties") or {}).get("alertlevel", ""))
        for e in detail["properties"]["products"].get("losspager", [])
    }
    assert "pending" in niveles, f"la fixture ya no trae `pending`: {sorted(niveles)}"

    # Y el filtro lo atrapa sobre el objeto real, no sobre uno de laboratorio.
    productos = parse_products(detail)
    assert productos.pager_alert() in NIVELES_PAGER | {""}


# --------------------------------------------------------------------------
# El contrato se comprueba antes de escribir.
# --------------------------------------------------------------------------


def _reporte(pager: str = "orange") -> Report:
    return Report(
        event=Evento(
            usgs_id="us6000tjl2",
            mag=7.4,
            depth_km=110.3,
            utc="2026-08-10T12:34:28Z",
            lugar="Chocó, Colombia",
            pager_alert=pager,
        ),
        inputs=Inputs(shakemap_version=8, groundfailure_version=8, exposure_manifest="col-v0.6"),
        totales=Totales(pop_mmi6p=6_960_086, pop_mmi7p=2_415_793),
        licencia=licencia_del_reporte("col-v0.6"),
    )


def test_un_reporte_en_contrato_pasa() -> None:
    validar_contra_esquema(_reporte())


def test_un_pager_fuera_del_enum_no_se_publica() -> None:
    """Es el unico artefacto publico con esquema cerrado y no tenia guardia."""
    with pytest.raises(ReporteFueraDeContratoError, match="pager_alert"):
        validar_contra_esquema(_reporte("pending"))


def test_el_error_los_lista_todos_y_no_solo_el_primero() -> None:
    """Quien lo lea tiene que poder arreglarlos de una pasada."""
    roto = _reporte("pending")
    object.__setattr__(roto, "licencia", type(roto.licencia)())
    with pytest.raises(ReporteFueraDeContratoError) as exc:
        validar_contra_esquema(roto)
    assert str(exc.value).count("\n  - ") >= 2


# --------------------------------------------------------------------------
# Agotar la ventana de RF-03 no puede anular RF-04.
# --------------------------------------------------------------------------


def _estado(estado: EventStatus, intentos: int = 0) -> EventState:
    return EventState(
        usgs_id="us7000agot",
        estado=estado,
        mag=6.1,
        lon=-76.0,
        lat=4.8,
        depth_km=30.0,
        origen_utc="2026-09-01T00:00:00Z",
        lugar="Costa del Pacífico",
        intentos_preliminar=intentos,
    )


def _con_shakemap() -> ProductSet:
    return ProductSet(
        usgs_id="us7000agot",
        shakemap=ProductRef(tipo="shakemap", version=3, actualizado_ms=0, contents={}),
        ground_failure=None,
        losspager=None,
    )


def test_un_evento_descartado_se_puede_rescatar_a_mano() -> None:
    """El corte por estado iba **antes** de mirar `forzar`.

    La única salida era editar el JSON del evento a mano, o sea la base de datos
    del sistema. Quien opera tiene que poder revivirlo con el comando que existe
    para eso.
    """
    decision = decide(_estado(EventStatus.DESCARTADO), _con_shakemap(), forzar=True)
    assert decision.action is Action.COMPLETO


def test_sin_forzar_un_descartado_sigue_omitiendose() -> None:
    """Y el corte sigue ahí: rescatar es una decisión, no el comportamiento."""
    decision = decide(_estado(EventStatus.DESCARTADO), _con_shakemap(), forzar=False)
    assert decision.action is Action.OMITIR


def test_agotar_la_ventana_deja_el_evento_en_un_estado_que_se_repasa() -> None:
    """`DEGRADADO`, no `DESCARTADO`.

    «USGS no publicó ShakeMap en seis horas» no es «este evento está fuera de
    alcance», y la diferencia decide si RF-04 puede volver a mirarlo. El estado
    al que se va tiene que tener transiciones de salida y no puede estar en la
    lista de exclusión del repaso.
    """
    from pipelines.common.state import _ALLOWED_TRANSITIONS
    from pipelines.p1_trigger.repaso import _SIN_REPASO

    assert _ALLOWED_TRANSITIONS[EventStatus.DEGRADADO], "el estado de destino sería terminal"
    assert EventStatus.DEGRADADO not in _SIN_REPASO, (
        "el estado de destino queda fuera del repaso de RF-04, que es el fallo "
        "que este cambio arregla"
    )
    # Y el destino que el codigo elige, leido del propio manejador.
    fuente = (Path(__file__).parent.parent.parent / "pipelines" / "p2_impact" / "run.py").read_text(
        encoding="utf-8"
    )
    bloque = fuente.split("if decision.action is Action.AGOTADO:", 1)[1][:900]
    codigo = "\n".join(x for x in bloque.splitlines() if not x.lstrip().startswith("#"))
    assert "EventStatus.DEGRADADO" in codigo
    assert "EventStatus.DESCARTADO" not in codigo


# --------------------------------------------------------------------------
# Los dos comandos que reescriben todo lo publicado, y que no ejecutaba nadie.
# --------------------------------------------------------------------------


def _publicar(raiz: Path, usgs_id: str) -> Path:
    """Deja en disco un reporte publicado, con su CSV, sin pasar por P2."""
    from pipelines.p3_report.csv_out import write_adm2_csv

    directorio = raiz / usgs_id
    directorio.mkdir(parents=True)
    reporte = _reporte()
    object.__setattr__(reporte.event, "usgs_id", usgs_id)
    reporte.save(directorio / "report.json")
    write_adm2_csv(
        [
            {
                "usgs_id": usgs_id,
                "adm2_id": "27001",
                "nombre": "Quibdó",
                "mmi_max": 7.4,
                "pop_mmi7p": 118_000,
                "pop_mmi6p": 340_000,
            }
        ],
        directorio / "adm2.csv",
    )
    return directorio


def test_regenerar_textos_reescribe_todos_los_reportes(tmp_path: Path) -> None:
    """Los dos comandos de regeneración no ejecutaban ni una línea en la suite.

    Con `usgs_id` vacío reescriben `report.md` y `hilo.txt` de **todos** los
    reportes publicados de una pasada, `docs/OPERACION.md` los presenta como la
    reparación de rutina, y una mutación que los dejara sin escribir nada pasaba
    la suite entera en verde. El fichero de prueba más cercano declara por
    escrito que quedan fuera de su alcance.
    """
    from pipelines.p3_report.run import regenerate_texts

    _publicar(tmp_path, "us7000aaa1")
    _publicar(tmp_path, "us7000aaa2")

    escritos = regenerate_texts(reports_root=tmp_path)

    for usgs_id in ("us7000aaa1", "us7000aaa2"):
        for artefacto in ("report_md", "hilo_txt", "licencia_txt"):
            clave = f"{usgs_id}/{artefacto}"
            assert clave in escritos, f"{clave} no se regeneró: {sorted(escritos)}"
            assert escritos[clave].stat().st_size > 0


def test_el_texto_regenerado_conserva_las_cifras_del_json(tmp_path: Path) -> None:
    """Es la aserción que ata este comando al fallo de las siete columnas.

    `Totales.to_dict` publicaba doce de diecinueve campos, así que regenerar los
    textos convertía 1.698 hospitales en 0 sobre un reporte que ya los tenía. Un
    comando que reescribe lo publicado tiene que conservar lo publicado.
    """
    from pipelines.p3_report.run import regenerate_texts

    directorio = _publicar(tmp_path, "us7000aaa3")
    antes = json.loads((directorio / "report.json").read_text(encoding="utf-8"))

    regenerate_texts(reports_root=tmp_path)

    despues = json.loads((directorio / "report.json").read_text(encoding="utf-8"))
    assert despues["totales"] == antes["totales"], (
        "regenerar los textos movió las cifras del reporte"
    )
    # La tabla publica la cifra redondeada a dos significativas, que es el
    # contrato del reporte; aquí se comprueba que **llegue**, no su forma.
    md = (directorio / "report.md").read_text(encoding="utf-8")
    fila = next((x for x in md.splitlines() if "Población en MMI≥6" in x), "")
    assert "millones" in fila, f"la población de MMI≥6 no llegó al texto: {fila!r}"


def test_un_reporte_que_no_existe_no_deja_el_lote_a_medias(tmp_path: Path) -> None:
    """Falla antes de tocar nada, en vez de escribir la mitad."""
    from pipelines.p3_report.run import regenerate_texts

    _publicar(tmp_path, "us7000aaa4")
    with pytest.raises((FileNotFoundError, ValueError)):
        regenerate_texts("us7000nada", reports_root=tmp_path)


# --------------------------------------------------------------------------
# Qué modelo de terreno produjo cada cifra.
# --------------------------------------------------------------------------


def _gf(*claves: str) -> ProductSet:
    return ProductSet(
        usgs_id="us6000tjl2",
        shakemap=None,
        ground_failure=ProductRef(
            tipo="ground-failure",
            version=8,
            actualizado_ms=0,
            contents={k: f"https://example.org/{k}" for k in claves},
        ),
        losspager=None,
    )


def test_se_registra_el_modelo_vigente() -> None:
    from pipelines.p2_impact.pipeline import modelos_de_terreno

    modelos = modelos_de_terreno(_gf("jessee_2018_model.tif", "zhu_2017_general_model.tif"))
    assert modelos["modelo_deslizamiento"] == "jessee_2018_model.tif"
    assert modelos["modelo_licuefaccion"] == "zhu_2017_general_model.tif"


def test_se_registra_la_alternativa_historica_y_no_el_preferido() -> None:
    """Este es el caso: el fichero se guardaba con el nombre del preferido.

    Un `jessee_2018_model.tif` en el directorio de trabajo podía ser en realidad
    un `nowicki_2014` o un `godt_2008`, y a partir de ahí nada los distinguía —
    el mismo umbral, la misma etiqueta de unidad y solo el número de versión en
    `report.json`. La docstring de `GROUND_FAILURE_HIGH_PROB` argumenta justo lo
    contrario de que eso sea inocuo.
    """
    from pipelines.p2_impact.pipeline import modelos_de_terreno

    modelos = modelos_de_terreno(_gf("nowicki_2014_global_model.tif", "zhu_2015_model.tif"))
    assert modelos["modelo_deslizamiento"] == "nowicki_2014_global_model.tif"
    assert modelos["modelo_licuefaccion"] == "zhu_2015_model.tif"


def test_sin_ground_failure_no_se_inventa_un_modelo() -> None:
    from pipelines.p2_impact.pipeline import modelos_de_terreno

    assert modelos_de_terreno(_reporte_sin_gf()) == {}


def _reporte_sin_gf() -> ProductSet:
    return ProductSet(usgs_id="us1", shakemap=None, ground_failure=None, losspager=None)


def test_el_reporte_nombra_el_modelo_que_produjo_la_cifra() -> None:
    """«El modelo» sin nombre no dice de qué distribución sale el 0,10."""
    from pipelines.p3_report.markdown import render_markdown
    from pipelines.p3_report.model import GroundFailureUSGS, Inputs

    reporte = _reporte()
    object.__setattr__(
        reporte,
        "inputs",
        Inputs(
            shakemap_version=8,
            groundfailure_version=8,
            exposure_manifest="col-v0.6",
            modelo_deslizamiento="nowicki_2014_global_model.tif",
            modelo_licuefaccion="zhu_2015_model.tif",
        ),
    )
    object.__setattr__(reporte, "totales", Totales(pop_mmi6p=6_960_086, pop_ls_alta=88_000))
    object.__setattr__(reporte, "ground_failure_usgs", GroundFailureUSGS())

    md = render_markdown(reporte)
    assert "nowicki_2014_global_model.tif" in md, (
        "el reporte sigue diciendo «el modelo» sin decir cuál"
    )
