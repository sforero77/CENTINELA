"""Saber si un reporte publicado se quedo atras de sus propias fuentes.

EL AGUJERO QUE CIERRA. `repaso.py` re-emite cuando USGS publica una version
nueva, pero salta los backtest a proposito, y los veintiun reportes publicados
son todos backtest: el repaso lleva dias saliendo en verde con
`"revisados": 0`. Asi es como el Choco llego a publicar el ShakeMap v7 con el
v8 ya servido, y a nadie le constaba.

La decision de no re-emitir historicos automaticamente no se toca —esta
razonada y sigue siendo buena—. Lo que se cierra es la ceguera: esto **informa**
y una persona decide.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from pipelines.p1_trigger.rezago import (
    Rezago,
    comprobar,
    iso3_del_manifiesto,
)

MANIFIESTO = """manifest_id: {mid}
iso3: {iso3}
generated_utc: "2026-08-23T00:00:00Z"
sources: []
"""


def _reporte(
    raiz: Path,
    usgs_id: str,
    *,
    shakemap: int = 1,
    groundfailure: int = 1,
    manifiesto: str = "col-v0.6",
) -> None:
    """Un `report.json` con lo unico que esta comprobacion mira: `inputs`."""
    directorio = raiz / usgs_id
    directorio.mkdir(parents=True, exist_ok=True)
    (directorio / "report.json").write_text(
        json.dumps(
            {
                "event": {"usgs_id": usgs_id},
                "inputs": {
                    "shakemap_version": shakemap,
                    "groundfailure_version": groundfailure,
                    "exposure_manifest": manifiesto,
                },
            }
        ),
        encoding="utf-8",
    )


def _manifiestos(raiz: Path, **por_pais: str) -> Path:
    """`_manifiestos(tmp, COL="col-v0.6")` deja `COL.yaml` con ese id."""
    raiz.mkdir(parents=True, exist_ok=True)
    for iso3, mid in por_pais.items():
        (raiz / f"{iso3}.yaml").write_text(MANIFIESTO.format(mid=mid, iso3=iso3), encoding="utf-8")
    return raiz


class _FetcherFalso:
    """Devuelve las versiones que USGS 'sirve hoy', por identificador."""

    def __init__(
        self,
        versiones: dict[str, tuple[int, int]],
        revientan: set[str] | None = None,
    ) -> None:
        self.versiones = versiones
        self.revientan = revientan or set()
        self.pedidos: list[str] = []

    def get_bytes(self, url: str) -> bytes:
        # El protocolo lo exige y esta comprobacion no debe usarlo: compara
        # versiones, no descarga productos. Descargarlos aqui seria pagar el
        # coste de re-emitir para averiguar si hace falta re-emitir.
        raise AssertionError("la comprobacion de rezago no descarga productos")

    def get_json(self, url: str) -> dict[str, Any]:
        uid = url.split("eventid=")[1].split("&")[0]
        self.pedidos.append(uid)
        if uid in self.revientan:
            raise OSError("la red se cayo")
        sm, gf = self.versiones[uid]

        def producto(version: int) -> list[dict[str, Any]]:
            return [
                {
                    "source": "us",
                    "status": "UPDATE",
                    "preferredWeight": 233,
                    "updateTime": 1,
                    "code": uid,
                    "properties": {"version": str(version)},
                    "contents": {},
                }
            ]

        return {
            "id": uid,
            "properties": {"products": {"shakemap": producto(sm), "groundfailure": producto(gf)}},
        }


# --- De donde sale el pais ---------------------------------------------------


@pytest.mark.parametrize(
    ("manifest_id", "esperado"),
    [("col-v0.6", "COL"), ("ven-v0.1", "VEN"), ("arg-v0.12", "ARG")],
)
def test_el_pais_sale_del_manifiesto_que_uso_el_reporte(manifest_id: str, esperado: str) -> None:
    """El `report.json` no guarda el pais, guarda el manifiesto — y ahi esta.

    Derivarlo de ahi ata la comparacion al mismo dato que se va a comparar: si
    el reporte dice `col`, el vigente que toca mirar es el de COL y no el que
    diga cualquier otro campo.
    """
    assert iso3_del_manifiesto(manifest_id) == esperado


# --- Que cuenta como rezago --------------------------------------------------


def test_un_reporte_al_dia_no_es_rezago(tmp_path: Path) -> None:
    _reporte(tmp_path / "reports", "us1", shakemap=8, groundfailure=8)
    manifiestos = _manifiestos(tmp_path / "manifests", COL="col-v0.6")

    resultado = comprobar(
        _FetcherFalso({"us1": (8, 8)}),
        reports_dir=tmp_path / "reports",
        manifests_dir=manifiestos,
    )

    assert resultado.revisados == 1
    assert resultado.rezagados == []


def test_un_shakemap_mas_nuevo_es_rezago(tmp_path: Path) -> None:
    """El caso del Choco, que es por lo que existe esto: v7 publicado, v8 servido."""
    _reporte(tmp_path / "reports", "us6000tjl2", shakemap=7, groundfailure=7)
    manifiestos = _manifiestos(tmp_path / "manifests", COL="col-v0.6")

    resultado = comprobar(
        _FetcherFalso({"us6000tjl2": (8, 8)}),
        reports_dir=tmp_path / "reports",
        manifests_dir=manifiestos,
    )

    assert [r.usgs_id for r in resultado.rezagados] == ["us6000tjl2"]
    assert resultado.rezagados[0].productos
    assert "ShakeMap v7 -> v8" in resultado.rezagados[0].describir()


def test_un_activo_reconstruido_es_rezago_sin_preguntar_a_usgs(tmp_path: Path) -> None:
    """El trimestral reconstruye el activo y los reportes ya publicados no se enteran.

    Es el caso de los seis eventos que el 1-sep-2026 no se re-emitieron: sus
    cifras siguen calculadas contra `v0.1` mientras el repositorio ya lleva
    `v0.2`. No hace falta red para verlo, y por eso se comprueba aparte.
    """
    _reporte(tmp_path / "reports", "us1", manifiesto="chl-v0.1")
    manifiestos = _manifiestos(tmp_path / "manifests", CHL="chl-v0.2")

    resultado = comprobar(
        _FetcherFalso({"us1": (1, 1)}),
        reports_dir=tmp_path / "reports",
        manifests_dir=manifiestos,
    )

    assert [r.usgs_id for r in resultado.rezagados] == ["us1"]
    assert resultado.rezagados[0].exposicion
    assert not resultado.rezagados[0].productos
    assert "chl-v0.1 -> chl-v0.2" in resultado.rezagados[0].describir()


def test_un_reporte_por_delante_no_es_rezago(tmp_path: Path) -> None:
    """Publicar una version mas alta que la servida no es ir atrasado.

    Pasa de verdad: USGS retira una revision y su detail vuelve a la anterior.
    Contar eso como rezago mandaria a re-emitir hacia atras.
    """
    _reporte(tmp_path / "reports", "us1", shakemap=9, groundfailure=9)
    manifiestos = _manifiestos(tmp_path / "manifests", COL="col-v0.6")

    resultado = comprobar(
        _FetcherFalso({"us1": (8, 8)}),
        reports_dir=tmp_path / "reports",
        manifests_dir=manifiestos,
    )

    assert resultado.rezagados == []


# --- Un fallo no es un "al dia" ----------------------------------------------


def test_un_evento_que_falla_no_pasa_por_estar_al_dia(tmp_path: Path) -> None:
    """La distincion de siempre: no saber no es saber que esta bien.

    Si el que falla se contara como revisado, el resumen diria "21 revisados, 0
    rezagados" habiendo mirado veinte. Es el cero silencioso que este proyecto
    persigue, en version "todo al dia".
    """
    _reporte(tmp_path / "reports", "us1")
    _reporte(tmp_path / "reports", "us2")
    manifiestos = _manifiestos(tmp_path / "manifests", COL="col-v0.6")

    resultado = comprobar(
        _FetcherFalso({"us1": (1, 1), "us2": (1, 1)}, revientan={"us2"}),
        reports_dir=tmp_path / "reports",
        manifests_dir=manifiestos,
    )

    assert resultado.revisados == 1
    assert resultado.fallidos == ["us2"]
    assert not resultado.ciego


def test_que_fallen_todos_es_no_haber_comprobado(tmp_path: Path) -> None:
    """`ciego` es lo que separa "no hay rezago" de "no llegue a mirar"."""
    _reporte(tmp_path / "reports", "us1")
    manifiestos = _manifiestos(tmp_path / "manifests", COL="col-v0.6")

    resultado = comprobar(
        _FetcherFalso({"us1": (1, 1)}, revientan={"us1"}),
        reports_dir=tmp_path / "reports",
        manifests_dir=manifiestos,
    )

    assert resultado.revisados == 0
    assert resultado.ciego


def test_un_reporte_ilegible_no_para_la_comprobacion_de_los_demas(tmp_path: Path) -> None:
    _reporte(tmp_path / "reports", "us1", shakemap=7)
    roto = tmp_path / "reports" / "us2"
    roto.mkdir(parents=True)
    (roto / "report.json").write_text("{ esto no es json", encoding="utf-8")
    manifiestos = _manifiestos(tmp_path / "manifests", COL="col-v0.6")

    resultado = comprobar(
        _FetcherFalso({"us1": (8, 1)}),
        reports_dir=tmp_path / "reports",
        manifests_dir=manifiestos,
    )

    assert [r.usgs_id for r in resultado.rezagados] == ["us1"]


def test_un_pais_sin_manifiesto_no_inventa_un_rezago(tmp_path: Path) -> None:
    """Sin manifiesto vigente no se puede comparar, y no compararlo es lo correcto.

    Dar por rezagado lo que no se pudo leer mandaria a re-emitir por un fichero
    que falta, que es un problema distinto y en otro sitio.
    """
    _reporte(tmp_path / "reports", "us1", manifiesto="xxx-v0.1")
    manifiestos = _manifiestos(tmp_path / "manifests", COL="col-v0.6")

    resultado = comprobar(
        _FetcherFalso({"us1": (1, 1)}),
        reports_dir=tmp_path / "reports",
        manifests_dir=manifiestos,
    )

    assert resultado.rezagados == []


# --- El orden y el resumen ---------------------------------------------------


def test_el_mas_atrasado_se_lee_primero(tmp_path: Path) -> None:
    """Si algun dia la lista es larga, lo primero tiene que ser lo que mas se movio."""
    _reporte(tmp_path / "reports", "us1", shakemap=7)
    _reporte(tmp_path / "reports", "us2", shakemap=1)
    manifiestos = _manifiestos(tmp_path / "manifests", COL="col-v0.6")

    resultado = comprobar(
        _FetcherFalso({"us1": (8, 1), "us2": (9, 1)}),
        reports_dir=tmp_path / "reports",
        manifests_dir=manifiestos,
    )

    assert [r.usgs_id for r in resultado.rezagados] == ["us2", "us1"]


def test_el_resumen_nombra_las_tres_fuentes_por_separado() -> None:
    """Un reporte puede ir atras en tres cosas a la vez y hay que poder leerlo."""
    r = Rezago(
        usgs_id="us1",
        shakemap_publicado=7,
        shakemap_vigente=8,
        groundfailure_publicado=6,
        groundfailure_vigente=7,
        manifiesto_publicado="col-v0.5",
        manifiesto_vigente="col-v0.6",
    )

    texto = r.describir()
    assert "ShakeMap v7 -> v8" in texto
    assert "Ground Failure v6 -> v7" in texto
    assert "col-v0.5 -> col-v0.6" in texto


# --- El emisor de outputs, que este comando estreno --------------------------


def test_un_valor_de_una_linea_sigue_saliendo_como_clave_igual_valor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Lo que ya funcionaba tiene que seguir igual: hay ocho llamadores."""
    from pipelines.cli import _emit_github_output

    salida = tmp_path / "out"
    monkeypatch.setenv("GITHUB_OUTPUT", str(salida))
    _emit_github_output("hay_rezago", "true")

    assert salida.read_text(encoding="utf-8") == "hay_rezago=true\n"


def test_un_valor_con_saltos_no_rompe_el_fichero_de_outputs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`clave=valor` solo admite una linea y la lista de rezagados son varias.

    Sin el formato con delimitador, la segunda linea se leeria como otra clave
    y a partir de ahi el runner interpreta basura. El fallo llevaba ahi desde
    el principio: ningun llamador emitia varias lineas hasta este.
    """
    from pipelines.cli import _emit_github_output

    salida = tmp_path / "out"
    monkeypatch.setenv("GITHUB_OUTPUT", str(salida))
    _emit_github_output("resumen", "- us1: ShakeMap v7 -> v8\n- us2: exposicion v0.1 -> v0.2")

    escrito = salida.read_text(encoding="utf-8")
    assert escrito.startswith("resumen<<CENTINELA_EOF\n")
    assert escrito.endswith("CENTINELA_EOF\n")
    assert "- us2: exposicion v0.1 -> v0.2" in escrito


def test_el_delimitador_no_puede_aparecer_dentro_del_valor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Si el valor trae el delimitador, cerraria el bloque antes de tiempo.

    Y quien controla lo que sigue controla que claves se escriben. Aqui el
    valor sale de nombres de evento y no de una persona, pero la comprobacion
    cuesta un `while` y quita el supuesto de en medio.
    """
    from pipelines.cli import _emit_github_output

    salida = tmp_path / "out"
    monkeypatch.setenv("GITHUB_OUTPUT", str(salida))
    _emit_github_output("resumen", "CENTINELA_EOF\nmalicioso=1")

    escrito = salida.read_text(encoding="utf-8")
    assert escrito.startswith("resumen<<CENTINELA_EOF_\n")
    assert escrito.endswith("\nCENTINELA_EOF_\n")


def test_sin_runner_no_escribe_nada(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """En local no hay `$GITHUB_OUTPUT` y el comando tiene que correr igual."""
    from pipelines.cli import _emit_github_output

    monkeypatch.delenv("GITHUB_OUTPUT", raising=False)
    _emit_github_output("resumen", "da igual\ncon saltos")
