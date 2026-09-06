"""El trimestral no podia correr solo, y su propio encabezado lo decia.

Del comentario que abre `exposure_quarterly.yml`:

    Los 19 manifests fijan el mismo release de Overture y Overture conserva
    **dos** (~2 meses): pasado ese plazo, un pais que no se haya reconstruido
    no se puede reconstruir — la url del release fijado deja de existir.

Y el cron es cada tres meses. La cadencia programada era mas larga que la vida
del insumo, asi que la corrida automatica solo funcionaba si una persona habia
actualizado los manifests en el intervalo: la dependencia humana que este
proyecto se prohibe en todas partes, y que `docs/OPERACION.md` desmiente al
prometerle al operador que «exposure_quarterly.yml lo reconstruye solo».

Las dos guardias que el workflow ponia antes de gastar runner no podian verlo:

* `lint-manifests` es **totalmente offline** — ids duplicados, cubos de
  licencia, vintages flotantes y forma de la url; nunca pregunta si existe.
* `comprobar_origenes` **salta a proposito** las fuentes que se leen en remoto,
  que es exactamente como estan declaradas las tres de Overture (`s3://...`).

Asi que el fallo llegaba despues de descargar los rasters —9,1 GB en el caso de
Brasil— y de agregarlos. Y no avisaba a nadie: con `fail-fast: false`, una
matriz de dieciocho paises en rojo es una lista de corridas que nadie mira.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

from pipelines.common.manifest import Manifest, Source
from pipelines.p0_exposure.download import ReleaseCaducadoError, comprobar_release_de_overture

RAIZ = Path(__file__).parent.parent.parent
TRIMESTRAL = RAIZ / ".github" / "workflows" / "exposure_quarterly.yml"
VIGIA = RAIZ / ".github" / "workflows" / "trigger.yml"


def _manifest() -> Manifest:
    def s(id_: str, capa: str, tema: str, subtipo: str) -> Source:
        return Source(
            id=id_,
            layer=capa,
            url=f"s3://overturemaps-us-west-2/release/2026-08-19.0/theme={tema}/type={subtipo}",
            license="ODbL-1.0",
            vintage="2026-08-19.0",
        )

    return Manifest(
        manifest_id="col-v0.6",
        iso3="COL",
        generated_utc="2026-08-23T00:00:00Z",
        sources=(
            s("overture_buildings", "buildings", "buildings", "building"),
            s("overture_transportation", "roads", "transportation", "segment"),
            s("overture_divisions", "divisions", "divisions", "division_area"),
        ),
    )


class _Catalogo:
    def __init__(self, vivos: set[str]) -> None:
        self.vivos = vivos
        self.pedidas: list[str] = []

    def get_json(self, url: str) -> dict[str, Any]:
        self.pedidas.append(url)
        if not any(v in url for v in self.vivos):
            raise RuntimeError("404 tras 3 intentos")
        return {}

    def get_bytes(self, url: str) -> bytes:  # pragma: no cover - no se llega
        raise AssertionError(url)


def test_el_release_vigente_pasa_y_pregunta_por_los_tres_temas() -> None:
    """Los tres temas se consumen, asi que los tres se comprueban.

    `divisions` es el que faltaba en dieciocho manifests, y es el que decide de
    donde puede rescatar celdas el reparto.
    """
    catalogo = _Catalogo({"buildings", "transportation", "divisions"})
    comprobar_release_de_overture(_manifest(), fetcher=catalogo)  # type: ignore[arg-type]

    temas = {u.split("/2026-08-19.0/")[1].split("/")[0] for u in catalogo.pedidas}
    assert temas == {"buildings", "transportation", "divisions"}


def test_un_release_caducado_para_el_build_antes_de_bajar_nada() -> None:
    """Y lo dice por su nombre, con la reparacion dentro del mensaje."""
    catalogo = _Catalogo(set())
    with pytest.raises(ReleaseCaducadoError) as exc:
        comprobar_release_de_overture(_manifest(), fetcher=catalogo)  # type: ignore[arg-type]

    mensaje = str(exc.value)
    assert "No se ha descargado nada todavia" in mensaje
    assert "Reintentar no" in mensaje
    assert "data/manifests/COL.yaml" in mensaje


def test_un_solo_tema_caido_ya_detiene_el_build() -> None:
    """Construir sin `divisions` publica un activo que le roba gente al vecino."""
    catalogo = _Catalogo({"buildings", "transportation"})
    with pytest.raises(ReleaseCaducadoError, match="divisions"):
        comprobar_release_de_overture(_manifest(), fetcher=catalogo)  # type: ignore[arg-type]


# --------------------------------------------------------------------------
# Y el workflow: que no lo reintente, que avise, y que no dependa de su cron.
# --------------------------------------------------------------------------


def _pasos() -> list[dict[str, Any]]:
    datos = yaml.safe_load(TRIMESTRAL.read_text(encoding="utf-8"))
    pasos: list[dict[str, Any]] = datos["jobs"]["construir"]["steps"]
    return pasos


def _comandos() -> str:
    lineas = []
    for paso in _pasos():
        cuerpo = paso.get("run")
        if isinstance(cuerpo, str):
            lineas += [x for x in cuerpo.splitlines() if not x.lstrip().startswith("#")]
    return "\n".join(lineas)


def test_un_release_caducado_no_se_reintenta() -> None:
    """El bucle espera 10 y 30 minutos entre intentos.

    Eso vale para un origen caido —el JRC estuvo tres horas el 27-ago-2026— y no
    para una url que ya no existe: solo retrasa el diagnostico cuarenta minutos.
    """
    comandos = _comandos()
    assert '"$CODIGO" -eq 5' in comandos, (
        "el codigo del release caducado no se distingue del origen caido, asi que "
        "el workflow lo reintenta dos veces esperando cuarenta minutos"
    )


def test_un_pais_que_no_se_reconstruye_abre_incidencia() -> None:
    """Una matriz de dieciocho en rojo no avisa a nadie por si sola."""
    nombres = {p.get("name") for p in _pasos()}
    assert "Abrir incidencia si este pais no se pudo reconstruir" in nombres
    assert "Cerrar la incidencia si el pais volvio" in nombres, (
        "media alarma es peor que ninguna: una incidencia que no se cierra sola deja de leerse"
    )

    datos = yaml.safe_load(TRIMESTRAL.read_text(encoding="utf-8"))
    permisos = datos["jobs"]["construir"]["permissions"]
    assert permisos.get("issues") == "write", (
        "`gh issue create` sin permiso falla despues del build, con el activo ya "
        "publicado y la corrida en rojo por el sitio equivocado"
    )


def test_el_vigia_despacha_el_trimestral() -> None:
    """Su cron pide cuatro turnos al ano y puede no conseguir ninguno.

    GitHub no reparte un turno por workflow: reparte unos pocos por repositorio,
    y este proyecto ya midio cinco al dia entre cinco workflows programados. El
    vigia es el reloj de los demas justamente por eso.
    """
    texto = VIGIA.read_text(encoding="utf-8")
    codigo = "\n".join(x for x in texto.splitlines() if not x.lstrip().startswith("#"))
    assert "despachar_si_toca exposure_quarterly.yml" in codigo, (
        "el trimestral depende de una cola de cron que su propio comentario dice que no puede ganar"
    )

    horas = int(codigo.split("despachar_si_toca exposure_quarterly.yml")[1].split()[0])
    assert horas <= 24 * 60, (
        f"el trimestral se despacharia cada {horas} h y el release de Overture "
        f"caduca en unos sesenta dias: la cadencia tiene que caber en la ventana "
        f"de retencion del insumo"
    )
