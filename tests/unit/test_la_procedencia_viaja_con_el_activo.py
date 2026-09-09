"""La licencia y el cubo tienen que salir del activo, no morir en un log.

`manifest.bucket` es la unica implementacion de la regla de los tres cubos
(§2.4) y en todo el arbol solo se evaluaba en dos sitios: dentro del
`extra={"context": ...}` de un `_log.info` del build, y en una linea de stdout
del job de lint. Ninguno de los dos escribe en un fichero que se publique.

El fichero que acompana al parquet en el Release es `medicion.json`, y su propio
docstring lo presenta como «la procedencia completa del activo». Llevaba iso3,
manifest_id, fecha, resumen y rescate — ni licencias ni cubo. El parquet publica
una sola columna de procedencia, `src_manifest`, con la cadena `'col-v0.6'`.

Y la otra mitad del mismo problema: `site/cobertura.json` rotulaba «paises con
activo **publicado**» una cifra que sale de `medido_ghs_pop`, un campo del
manifest que ningun build y ningun workflow escribia. Solo lo escribe
`centinela calibrar --escribir`, un comando manual; el trimestral construia,
publicaba el Release y no commiteaba el manifest. La afirmacion publica sobre
disponibilidad operativa se apoyaba en un YAML editado a mano alguna vez.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import yaml

from pipelines.common.manifest import Manifest
from pipelines.p0_exposure.build import write_measurement

RAIZ = Path(__file__).parent.parent.parent
TRIMESTRAL = RAIZ / ".github" / "workflows" / "exposure_quarterly.yml"


def test_la_medicion_publica_el_cubo_y_las_licencias(tmp_path: Path) -> None:
    """Una procedencia sin licencia no es una procedencia."""
    manifest = Manifest.load("COL")
    plan = SimpleNamespace(iso3="COL", manifest=manifest, salida=tmp_path)

    ruta = write_measurement(plan, {"pop_total": 1.0}, rescate={})
    datos = json.loads(ruta.read_text(encoding="utf-8"))

    assert datos["cubo"] == manifest.bucket.value
    assert datos["licencias"] == sorted({s.license for s in manifest.sources})
    # Y que no sea una lista vacia por accidente: Colombia mezcla ODbL con
    # CC-BY y con la licencia de reutilizacion de la Comision Europea.
    assert "ODbL-1.0" in datos["licencias"]


def _pasos_del_trimestral() -> list[dict[str, object]]:
    datos = yaml.safe_load(TRIMESTRAL.read_text(encoding="utf-8"))
    pasos: list[dict[str, object]] = datos["jobs"]["construir"]["steps"]
    return pasos


def _comandos(pasos: list[dict[str, object]]) -> str:
    """Solo los `run:`, y sin los comentarios de dentro.

    Un guardia que lee la prosa de un workflow aprueba el fichero por su
    documentacion. Ya paso seis veces en esta auditoria.
    """
    lineas = []
    for paso in pasos:
        cuerpo = paso.get("run")
        if not isinstance(cuerpo, str):
            continue
        lineas += [x for x in cuerpo.splitlines() if not x.lstrip().startswith("#")]
    return "\n".join(lineas)


def test_el_trimestral_anota_la_medicion_en_el_manifest() -> None:
    """Sin esto, `medido_ghs_pop` no lo escribe ningun proceso automatico.

    `calibrar` es seguro en automatico por diseno: estrecha la tolerancia y
    nunca la ensancha. Si el desvio se sale de la vigente, no toca nada y lo
    dice — esa decision sigue siendo de una persona.
    """
    comandos = _comandos(_pasos_del_trimestral())
    assert "centinela calibrar --escribir" in comandos, (
        "el trimestral construye y publica el Release pero no anota la medicion: "
        "`site/cobertura.json` seguiria contando paises a partir de un YAML que "
        "alguien edito a mano alguna vez"
    )
    assert 'git add "data/manifests/$ISO3.yaml"' in comandos, (
        "calibrar escribe el manifest en el runner y el runner se tira: sin "
        "commit, la anotacion no llega al repositorio"
    )


def test_el_trimestral_republica_la_cobertura() -> None:
    """La cobertura sale de los manifests: si no se rehace, cuenta lo de antes.

    Y un push con `GITHUB_TOKEN` no dispara `site.yml`, asi que ademas hay que
    pedir la republicacion a mano. Es la misma regla de GitHub que dejo el visor
    diecisiete horas congelado.
    """
    comandos = _comandos(_pasos_del_trimestral())
    assert "centinela cobertura" in comandos
    assert "gh workflow run site.yml" in comandos, (
        "la cobertura recalculada se quedaria commiteada y sin llegar a la pagina"
    )


def test_el_visor_no_promete_un_release_que_no_mira() -> None:
    """«publicado» prometia disponibilidad operativa; el dato no la respalda.

    La cifra cuenta manifests con `medido_ghs_pop`, o sea activos construidos y
    medidos. No mira el Release, que es lo que P2 necesita para calcular un
    reporte: retirarlo a mano dejaria este numero intacto.
    """
    app = (RAIZ / "site" / "assets" / "app.js").read_text(encoding="utf-8")
    codigo = "\n".join(x for x in app.splitlines() if not x.lstrip().startswith("//"))
    assert "países con activo publicado" not in codigo
    assert "países con activo construido" in codigo
