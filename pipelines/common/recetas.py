"""La receta de cada activo, y el paso solo al ultimo release de Overture.

UN `manifest_id` IDENTIFICA UNA RECETA, Y SOLO UNA.

El 27-ago-2026 se anadio una fuente a los diecinueve manifests sin subir ningun
`manifest_id`, y quedaron dos activos de Colombia con contenido distinto y el
mismo identificador. Desde entonces un cerrojo guarda la huella de lo que cada
manifest declara: cambiar las fuentes sin cambiar de version falla.

El cerrojo era una tabla pegada a mano en una prueba, y eso tenia un coste que
no se veia: **ningun proceso automatico podia subir una version**. Overture
publica release mensual y conserva dos, asi que el fijado caduca solo; pasarlo
al nuevo exigia editar diecinueve manifests, subir diecinueve versiones y pegar
diecinueve huellas, y quedo a mano desde el primer dia.

Aqui la tabla pasa a ser un registro por pais —``data/manifests/recetas/
<ISO3>.json``, ``{manifest_id: huella}``— que solo crece: a un id ya registrado
no se le cambia la huella nunca (`registrar`). La garantia es la misma —a una
persona que cambia las fuentes sin subir la version la para la prueba— y ahora
la puede cumplir tambien un workflow.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .http import Fetcher
from .paths import MANIFESTS_DIR

RECETAS_DIR = MANIFESTS_DIR / "recetas"

#: Raiz del catalogo STAC de Overture. Publica `latest` y un hijo por release vivo.
CATALOGO_OVERTURE = "https://stac.overturemaps.org/catalog.json"

#: Forma de un release de Overture: ``2026-09-23.1``.
RELEASE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}\.\d+$")


def huella(fuentes: list[dict[str, Any]]) -> str:
    """Resumen de **lo que se declara**, no de como esta escrito el fichero.

    Solo entran el id, la capa, la url y la licencia de cada fuente: es lo que
    determina que datos entran en el activo. Reordenar las claves de un YAML,
    corregir una nota o rellenar un `insumos_sha256` no cambia el resultado y no
    deberia obligar a una version nueva.
    """
    partes = sorted(
        f"{f.get('id')}|{f.get('layer')}|{f.get('url')}|{f.get('license')}" for f in fuentes
    )
    return hashlib.sha256("\n".join(partes).encode("utf-8")).hexdigest()[:16]


def _manifest(iso3: str, manifests_dir: Path) -> dict[str, Any]:
    datos: dict[str, Any] = yaml.safe_load((manifests_dir / f"{iso3}.yaml").read_text("utf-8"))
    return datos


def huella_del_manifest(iso3: str, manifests_dir: Path = MANIFESTS_DIR) -> tuple[str, str]:
    """``(manifest_id, huella)`` de lo que el manifest declara hoy."""
    datos = _manifest(iso3, manifests_dir)
    return str(datos["manifest_id"]), huella(datos["sources"])


def registro(iso3: str, recetas_dir: Path = RECETAS_DIR) -> dict[str, str]:
    ruta = recetas_dir / f"{iso3}.json"
    if not ruta.exists():
        return {}
    datos: dict[str, str] = json.loads(ruta.read_text(encoding="utf-8"))
    return datos


class RecetaReescritaError(ValueError):
    """Se intento dar otra huella a un `manifest_id` que ya tenia una."""


def registrar(
    iso3: str, *, manifests_dir: Path = MANIFESTS_DIR, recetas_dir: Path = RECETAS_DIR
) -> str:
    """Anota la receta vigente del manifest. Nunca reescribe una ya anotada.

    Raises:
        RecetaReescritaError: si el `manifest_id` ya figura con otra huella. Es
            exactamente el fallo del 27-ago: mismas siglas, otra receta.
    """
    manifest_id, actual = huella_del_manifest(iso3, manifests_dir)
    anotadas = registro(iso3, recetas_dir)
    previa = anotadas.get(manifest_id)
    if previa == actual:
        return manifest_id
    if previa is not None:
        raise RecetaReescritaError(
            f"{manifest_id} ya esta registrado con la receta {previa} y el manifest "
            f"declara {actual}: cambiaron las fuentes sin subir la version. Sube el "
            f"`manifest_id` de {iso3} y vuelve a registrar."
        )
    anotadas[manifest_id] = actual
    recetas_dir.mkdir(parents=True, exist_ok=True)
    (recetas_dir / f"{iso3}.json").write_text(
        json.dumps(anotadas, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
    )
    return manifest_id


# --- Overture --------------------------------------------------------------------


def ultimo_release_de_overture(fetcher: Fetcher) -> str:
    """El release mas reciente que el catalogo de Overture sirve.

    Se fija el **nombre concreto**, no el alias: la regla «nunca latest» habla
    de lo que se escribe en el manifest, y aqui se escribe ``2026-09-23.1``.
    Se exige ademas que ese release figure entre los hijos del catalogo; un
    `latest` que apunta a algo que no se sirve es un catalogo a medio publicar.
    """
    catalogo = fetcher.get_json(CATALOGO_OVERTURE)
    ultimo = str(catalogo.get("latest") or "")
    if not RELEASE_RE.match(ultimo):
        raise ValueError(f"el catalogo de Overture no declara un `latest` valido: {ultimo!r}")
    hijos = {
        str(enlace.get("href", ""))
        for enlace in catalogo.get("links", [])
        if enlace.get("rel") == "child"
    }
    if not any(f"/{ultimo}/" in h for h in hijos):
        raise ValueError(f"`latest` dice {ultimo} y el catalogo no lo sirve entre sus releases")
    return ultimo


def release_fijado(iso3: str, manifests_dir: Path = MANIFESTS_DIR) -> str | None:
    """El release de Overture que fija el manifest, o `None` si no usa Overture."""
    for fuente in _manifest(iso3, manifests_dir)["sources"]:
        if str(fuente.get("url", "")).startswith("s3://overturemaps"):
            return str(fuente.get("vintage"))
    return None


def siguiente_version(manifest_id: str) -> str:
    """``pan-v0.4`` -> ``pan-v0.5``.

    >>> siguiente_version("col-v0.7")
    'col-v0.8'
    """
    m = re.fullmatch(r"(.+-v\d+\.)(\d+)", manifest_id)
    if not m:
        raise ValueError(f"manifest_id sin forma <pais>-v<mayor>.<menor>: {manifest_id!r}")
    return f"{m.group(1)}{int(m.group(2)) + 1}"


@dataclass(frozen=True, slots=True)
class Paso:
    iso3: str
    desde: str
    hasta: str
    manifest_id: str


def pasar_a_release(
    iso3: str,
    release: str,
    *,
    manifests_dir: Path = MANIFESTS_DIR,
    recetas_dir: Path = RECETAS_DIR,
) -> Paso | None:
    """Mueve las fuentes de Overture del manifest a ``release`` y sube la version.

    Edita por lineas, como `fijar_insumos_en_manifest`: los manifests llevan mas
    prosa que datos y un volcado de YAML se la llevaria. Solo se tocan las
    lineas `url:` que apuntan a Overture, los `vintage:` con forma de release
    de Overture y el `manifest_id`. Devuelve `None` si ya estaba al dia.
    """
    if not RELEASE_RE.match(release):
        raise ValueError(f"release de Overture con forma rara: {release!r}")
    fijado = release_fijado(iso3, manifests_dir)
    if fijado is None or fijado == release:
        return None

    ruta = manifests_dir / f"{iso3}.yaml"
    crudo = ruta.read_bytes().decode("utf-8")
    fin = "\r\n" if "\r\n" in crudo else "\n"
    manifest_id = str(_manifest(iso3, manifests_dir)["manifest_id"])
    nuevo_id = siguiente_version(manifest_id)

    salida = []
    for linea in crudo.replace("\r\n", "\n").split("\n"):
        limpia = linea.strip()
        if limpia.startswith("url: s3://overturemaps"):
            linea = linea.replace(f"/release/{fijado}/", f"/release/{release}/")
        elif limpia.startswith("vintage:") and fijado in limpia:
            linea = linea.replace(fijado, release)
        elif limpia == f"manifest_id: {manifest_id}":
            linea = linea.replace(manifest_id, nuevo_id)
        salida.append(linea)
    ruta.write_bytes(fin.join(salida).encode("utf-8"))

    if release_fijado(iso3, manifests_dir) != release:
        raise ValueError(f"{iso3}: tras reescribir, el manifest no fija {release}")
    registrar(iso3, manifests_dir=manifests_dir, recetas_dir=recetas_dir)
    return Paso(iso3=iso3, desde=fijado, hasta=release, manifest_id=nuevo_id)
