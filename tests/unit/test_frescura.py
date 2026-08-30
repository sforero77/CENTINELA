"""Que la pagina publicada sirva lo que hay en el repositorio.

El 26-ago-2026 el visor llevaba diecisiete horas congelado y **nada estaba en
rojo**. Salio a la luz porque una persona sintio un sismo, fue a mirar y
pregunto. Ese no puede ser el mecanismo de deteccion de un sistema de
vigilancia.

Estas pruebas cubren el vigilante, que es la pieza en la que un fallo silencioso
es peor que no tener nada: un vigilante que no avisa da **mas** confianza que la
ausencia de vigilante.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from pipelines.common.frescura import (
    FICHEROS_CON_FECHA,
    HORAS_DE_GRACIA,
    Desfase,
    PaginaDesactualizadaError,
    comparar,
    raise_if_stale,
    resumen,
    revisar,
)


class _PaginaFalsa:
    """Sirve lo que se le diga, o revienta si se le pide."""

    def __init__(self, por_url: dict[str, Any] | None = None, error: Exception | None = None):
        self.por_url = por_url or {}
        self.error = error
        self.pedidas: list[str] = []

    def get_json(self, url: str) -> Any:
        self.pedidas.append(url)
        if self.error is not None:
            raise self.error
        for sufijo, datos in self.por_url.items():
            if url.endswith(sufijo):
                return datos
        raise FileNotFoundError(url)


def _escribir(raiz: Path, fichero: str, generado: str) -> None:
    raiz.mkdir(parents=True, exist_ok=True)
    (raiz / fichero).write_text(json.dumps({"generado_utc": generado}), encoding="utf-8")


# --- La comparacion ---------------------------------------------------------


def test_al_dia_no_preocupa() -> None:
    d = comparar(
        "status.json",
        {"generado_utc": "2026-08-26T19:46:23Z"},
        {"generado_utc": "2026-08-26T19:46:23Z"},
    )

    assert d is not None
    assert d.horas == 0.0
    assert not d.preocupa


def test_el_caso_real_de_diecisiete_horas() -> None:
    """Los numeros exactos del dia que esto no existia."""
    d = comparar(
        "status.json",
        {"generado_utc": "2026-08-26T19:46:22Z"},
        {"generado_utc": "2026-08-26T02:53:37Z"},
    )

    assert d is not None
    assert 16.8 < d.horas < 17.0
    assert d.preocupa


def test_una_pagina_por_delante_no_es_un_desfase() -> None:
    """Ocurre entre el despliegue y el commit siguiente, y no es un problema.

    Sin el suelo en cero saldria un desfase negativo, que no significa nada y
    ensuciaria el resumen.
    """
    d = comparar(
        "status.json",
        {"generado_utc": "2026-08-26T02:00:00Z"},
        {"generado_utc": "2026-08-26T03:00:00Z"},
    )

    assert d is not None
    assert d.horas == 0.0


def test_una_fecha_ilegible_no_se_inventa_un_veredicto() -> None:
    """Mejor "no se pudo comparar" que un falso ok o un falso rojo."""
    assert comparar("x.json", {"generado_utc": "el martes"}, {"generado_utc": "2026-08-26"}) is None
    assert comparar("x.json", {}, {}) is None


# --- Medir no basta: hay que levantar --------------------------------------


def test_un_desfase_grande_levanta() -> None:
    """Medir y no avisar es el patron que esta auditoria persigue."""
    viejo = Desfase("status.json", "2026-08-26T19:00:00Z", "2026-08-26T02:00:00Z", 17.0)

    with pytest.raises(PaginaDesactualizadaError, match="detras del repositorio"):
        raise_if_stale([viejo])


def test_el_aviso_dice_como_repararlo() -> None:
    """Quien lea la alarma a las tres de la manana no deberia investigar de cero."""
    viejo = Desfase("status.json", "2026-08-26T19:00:00Z", "2026-08-26T02:00:00Z", 17.0)

    with pytest.raises(PaginaDesactualizadaError) as excinfo:
        raise_if_stale([viejo])

    assert "gh workflow run site.yml" in str(excinfo.value)
    assert "GITHUB_TOKEN" in str(excinfo.value)


def test_dentro_de_la_gracia_no_levanta() -> None:
    """El despliegue tarda; una alarma que salta sola se aprende a ignorar."""
    reciente = Desfase("status.json", "", "", HORAS_DE_GRACIA - 0.1)

    raise_if_stale([reciente])


def test_sin_nada_que_comparar_no_levanta() -> None:
    """No poder comprobar no es lo mismo que estar roto.

    Levantar aqui convertiria un fallo de red en una alarma de datos viejos, y
    quien la mire buscara el problema en el sitio equivocado.
    """
    raise_if_stale([])


# --- La revision completa ---------------------------------------------------


def test_revisa_los_ficheros_que_el_visor_lee(tmp_path: Path) -> None:
    for fichero in FICHEROS_CON_FECHA:
        _escribir(tmp_path, fichero, "2026-08-26T20:00:00Z")
    pagina = _PaginaFalsa({f: {"generado_utc": "2026-08-26T20:00:00Z"} for f in FICHEROS_CON_FECHA})

    desfases = revisar(pagina, site_dir=tmp_path, sitio="https://ejemplo/")

    assert {d.fichero for d in desfases} == set(FICHEROS_CON_FECHA)
    assert not any(d.preocupa for d in desfases)


def test_un_fichero_que_aun_no_esta_publicado_no_es_un_desfase(tmp_path: Path) -> None:
    """Acaba de nacer y el primer despliegue no ha corrido. No es un fallo."""
    _escribir(tmp_path, "observados.json", "2026-08-26T20:00:00Z")
    pagina = _PaginaFalsa({})  # 404 para todo

    assert revisar(pagina, site_dir=tmp_path, sitio="https://ejemplo/") == []


def test_una_caida_de_red_no_se_reporta_como_pagina_vieja(tmp_path: Path) -> None:
    """Son dos problemas distintos y confundirlos manda a investigar mal."""
    _escribir(tmp_path, "status.json", "2026-08-26T20:00:00Z")
    pagina = _PaginaFalsa(error=TimeoutError("la red"))

    assert revisar(pagina, site_dir=tmp_path, sitio="https://ejemplo/") == []


def test_no_pide_lo_que_no_existe_en_el_repo(tmp_path: Path) -> None:
    """Un fichero que el repo no tiene no es asunto de esta comprobacion."""
    _escribir(tmp_path, "status.json", "2026-08-26T20:00:00Z")
    pagina = _PaginaFalsa({"status.json": {"generado_utc": "2026-08-26T20:00:00Z"}})

    revisar(pagina, site_dir=tmp_path, sitio="https://ejemplo/")

    assert not any("observados.json" in u for u in pagina.pedidas)


# --- El resumen -------------------------------------------------------------


def test_el_caso_bueno_tambien_se_imprime() -> None:
    """Distingue "esta fresco" de "la comprobacion no llego a correr".

    Un vigilante silencioso cuando todo va bien es indistinguible de uno
    apagado, que es exactamente como estaba el sistema el 26-ago.
    """
    texto = resumen([Desfase("status.json", "a", "a", 0.0)])

    assert "ok" in texto
    assert "status.json" in texto


def test_el_resumen_marca_lo_que_preocupa() -> None:
    texto = resumen([Desfase("status.json", "a", "b", 17.0)])

    assert "ALERTA" in texto


# --- Y que el workflow lo llame de verdad ------------------------------------


def test_hay_un_workflow_que_lo_ejecuta() -> None:
    """Escrito y no conectado seria especialmente ironico en este modulo."""
    raiz = Path(__file__).parent.parent.parent
    workflow = raiz / ".github" / "workflows" / "frescura.yml"

    assert workflow.exists(), "el vigilante no tiene quien lo despierte"
    texto = workflow.read_text(encoding="utf-8")
    assert "centinela frescura" in texto
    assert "schedule" in texto, "sin cron, solo corre cuando alguien se acuerda"
    assert "gh issue create" in texto, "una corrida en rojo que nadie mira no es una alarma"


def test_la_alarma_sabe_apagarse() -> None:
    """Un vigilante que solo sabe encenderse gasta la confianza que necesita.

    La primera version abria una issue en cada corrida en rojo y no cerraba
    ninguna al volver el verde. Medido el 30-ago-2026: dos abiertas —del 27 y del
    29— por condiciones resueltas hacia horas, las dos describiendo un desfase
    que ya no existia. La proxima vez que este workflow tenga razon, nadie iria
    a mirar.
    """
    raiz = Path(__file__).parent.parent.parent
    texto = (raiz / ".github" / "workflows" / "frescura.yml").read_text(encoding="utf-8")

    assert "gh issue close" in texto, "la alarma no sabe decir «ya paso»"
    assert "if: success()" in texto, "el cierre tiene que colgar de la revision en verde"

    # Y no duplicar: buscar una abierta antes de crear otra.
    crear = texto.index("gh issue create")
    assert "gh issue list --state open" in texto[:crear], (
        "se crea la issue sin mirar antes si ya hay una abierta"
    )
    assert "gh issue comment" in texto, (
        "si ya hay una abierta hay que anotar en ella, no callarse ni duplicar"
    )


# --- Lo que no lleva fecha: colecciones --------------------------------------


def _coleccion(raiz: Path, ids: list[str]) -> None:
    destino = raiz / "reports"
    destino.mkdir(parents=True, exist_ok=True)
    (destino / "index.json").write_text(
        json.dumps([{"usgs_id": i, "mag": 6.0} for i in ids]), encoding="utf-8"
    )


def test_un_reporte_publicado_que_la_pagina_no_lista(tmp_path: Path) -> None:
    """El artefacto mas importante del sistema, y hasta hoy nadie lo vigilaba.

    Estaba cubierto de rebote —P2 toca `status.json` en el mismo commit— pero de
    rebote no es de frente: el dia que P2 deje de tocarlo, la cobertura
    desaparece sin que nadie se entere.
    """
    from pipelines.common.frescura import raise_if_stale, revisar_colecciones

    _coleccion(tmp_path, ["us1", "us2", "us3"])
    pagina = _PaginaFalsa({"reports/index.json": [{"usgs_id": "us1"}, {"usgs_id": "us2"}]})

    ausentes = revisar_colecciones(pagina, raiz=tmp_path, sitio="https://ejemplo/")

    assert ausentes[0].faltan == ("us3",)
    assert ausentes[0].preocupa
    with pytest.raises(PaginaDesactualizadaError, match="us3"):
        raise_if_stale(list(ausentes))


def test_para_un_indice_la_pregunta_no_es_cuanto_hace(tmp_path: Path) -> None:
    """Un indice recien generado que no lista un reporte esta fresco y roto.

    Por eso las colecciones se comparan por contenido y no por fecha: la unica
    respuesta util es "¿estan los mismos?".
    """
    from pipelines.common.frescura import revisar_colecciones

    _coleccion(tmp_path, ["us1"])
    pagina = _PaginaFalsa({"reports/index.json": [{"usgs_id": "us1"}]})

    assert not revisar_colecciones(pagina, raiz=tmp_path, sitio="https://ejemplo/")[0].preocupa


def test_un_reporte_retirado_no_es_un_fallo(tmp_path: Path) -> None:
    """Sobra en la pagina y falta en el repo: es el estado normal justo despues
    de retirar un reporte, mientras el despliegue esta en vuelo.

    Tratarlo como fallo daria una alarma cada vez que se corrige algo.
    """
    from pipelines.common.frescura import revisar_colecciones

    _coleccion(tmp_path, ["us1"])
    pagina = _PaginaFalsa({"reports/index.json": [{"usgs_id": "us1"}, {"usgs_id": "viejo"}]})

    assert not revisar_colecciones(pagina, raiz=tmp_path, sitio="https://ejemplo/")[0].preocupa


def test_una_caida_de_red_tampoco_inventa_reportes_ausentes(tmp_path: Path) -> None:
    """Misma regla que con las fechas: no poder comprobar no es estar roto."""
    from pipelines.common.frescura import revisar_colecciones

    _coleccion(tmp_path, ["us1"])
    pagina = _PaginaFalsa(error=TimeoutError("la red"))

    assert revisar_colecciones(pagina, raiz=tmp_path, sitio="https://ejemplo/") == []


def test_el_indice_de_reportes_esta_vigilado() -> None:
    """Escrito y no conectado seria especialmente ironico en este modulo."""
    from pipelines.common.frescura import COLECCIONES

    assert "reports/index.json" in COLECCIONES


def test_el_comando_frescura_pregunta_las_dos_cosas() -> None:
    """Fechas y colecciones son preguntas distintas contra la misma pagina."""
    import inspect

    from pipelines.cli import _cmd_frescura

    fuente = inspect.getsource(_cmd_frescura)

    assert "revisar(" in fuente
    assert "revisar_colecciones(" in fuente


# --- Lo que faltaba: que un fichero se congele ------------------------------


def test_un_fichero_congelado_no_desfasa_y_aun_asi_esta_mal(tmp_path: Path) -> None:
    """El agujero que oculto que `incendios.yml` no se disparara nunca.

    `frescura` comparaba repositorio contra pagina y nada mas. Un fichero de
    hace tres dias pasaba la revision sin protestar: los dos lados igual de
    viejos, cero desfase entre ellos. El workflow figuraba activo, el fichero
    sincronizado, y la capa llevaba horas sin actualizarse.
    """
    from pipelines.common.frescura import comparar, revisar_vejez

    viejo = {"generado_utc": "2026-08-24T00:00:00Z"}
    desfase = comparar("incendios.json", viejo, viejo)

    assert desfase is not None
    assert not desfase.preocupa, "por eso hacia falta otra pregunta"

    _escribir(tmp_path, "incendios.json", "2026-08-24T00:00:00Z")
    congelados = revisar_vejez(site_dir=tmp_path, ahora=datetime(2026, 8, 27, tzinfo=UTC))

    assert congelados[0].preocupa
    assert congelados[0].horas == pytest.approx(72.0)


def test_un_retraso_normal_no_dispara_la_alarma(tmp_path: Path) -> None:
    """GitHub estrangula los crones de este repositorio: siete horas de hueco
    es lo corriente.

    Una alarma que salta por eso se aprende a ignorar, y entonces no avisa del
    dia que de verdad importa. Los limites persiguen el silencio de un dia, no
    el de una hora.
    """
    from pipelines.common.frescura import raise_if_stale, revisar_vejez

    _escribir(tmp_path, "status.json", "2026-08-27T00:00:00Z")
    congelados = revisar_vejez(site_dir=tmp_path, ahora=datetime(2026, 8, 27, 7, tzinfo=UTC))

    assert not congelados[0].preocupa
    raise_if_stale(list(congelados))


def test_cada_fichero_publicado_tiene_su_limite() -> None:
    """Uno sin limite no lo vigila nadie, que es como estabamos."""
    from pipelines.common.frescura import FICHEROS_CON_FECHA, MAX_HORAS_SIN_REGENERAR

    assert set(FICHEROS_CON_FECHA) <= set(MAX_HORAS_SIN_REGENERAR)


def test_el_aviso_dice_que_mirar_si_algo_se_congelo() -> None:
    """Quien lea la alarma no deberia deducir que workflow no se disparo."""
    from pipelines.common.frescura import Congelado, raise_if_stale

    with pytest.raises(PaginaDesactualizadaError) as excinfo:
        raise_if_stale([Congelado("incendios.json", "2026-08-24T00:00:00Z", 72.0, 24.0)])

    assert "gh run list --workflow=" in str(excinfo.value)
