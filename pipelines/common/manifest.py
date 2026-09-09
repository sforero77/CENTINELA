"""Manifests de vintages (§2.2, RNF-04).

Un manifest declara, por pais, exactamente que version de que fuente entro al
activo de exposicion: URL, licencia, fecha y hash. Es el eslabon que hace
re-derivable todo numero publicado: ``reporte -> manifest -> hashes de insumos``.

La regla dura: **nunca "latest"**. Overture publica release mensual y su STAC
apunta siempre al ultimo; fijar el release explicito es lo que hace que un
reporte de hace seis meses siga siendo reproducible.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, Self

import yaml
from jsonschema import Draft202012Validator

from .licensing import (
    Bucket,
    LicenseViolationError,
    assert_publishable_in_report,
    bucket_for,
    resolve_bucket,
)
from .paths import MANIFESTS_DIR, SCHEMAS_DIR

#: Valores prohibidos como "vintage": no fijan nada.
_FLOATING_VINTAGES = frozenset({"latest", "current", "rolling", ""})

#: Capa cuyos ficheros no se descargan nunca: 858 teselas a 96 MB son 82 GB
#: para los diecinueve paises y un runner tiene ~14 GB libres, asi que se leen
#: las overviews del COG por rangos HTTP.
_CAPA_REMOTA = "landcover"


@dataclass(frozen=True, slots=True)
class Source:
    """Una fuente fijada dentro de un manifest."""

    id: str
    layer: str
    url: str
    license: str
    vintage: str
    #: sha256 sobre la lista canonica de los ficheros que esta fuente aporta al
    #: build, no sobre un fichero. Una fuente no es un fichero: GHS-POP son
    #: nueve u once teselas, el desglose etario de WorldPop veinte rasters, un
    #: COD-AB el shapefile con su .dbf y su .prj, y Overture no baja ninguno.
    #: El nombre no es `sha256` a proposito, para que nadie espere que
    #: `sha256sum fichero` de este valor. Lo calcula
    #: :func:`pipelines.p0_exposure.download.digest_de_insumos` y lo publica
    #: `medicion.json`. Vacio = el digest todavia no se ha fijado; el lint lo
    #: reporta como aviso y el build lo registra al descargar.
    insumos_sha256: str = ""
    #: Nombre del dataset en HDX cuando la descarga se resuelve por su API en
    #: vez de por URL fija. Ver :mod:`pipelines.common.hdx`: la ruta real de un
    #: mismo dataset de HOTOSM cambia de forma segun el pais, asi que el
    #: identificador estable es el nombre, no la URL.
    hdx_dataset: str = ""
    #: Fragmento del nombre del recurso dentro del dataset. Hace falta cuando el
    #: dataset publica varios recursos del mismo formato: sin el se toma el
    #: primero, y en el COD-AB de Colombia el primer SHP son secciones urbanas.
    hdx_resource: str = ""
    notes: str = ""

    @property
    def bucket(self) -> Bucket:
        return bucket_for(self.license)

    @property
    def se_lee_en_remoto(self) -> bool:
        """La fuente nunca toca el disco, asi que no tiene bytes que hashear.

        Overture son 277 GB de los que un pais usa once ficheros, y DuckDB los
        lee por HTTPS podando por la columna ``bbox``; la cobertura del suelo
        son COG leidos por rangos. Las dos se declaran en el manifest de todas
        formas, porque el contrato del proyecto es que toda cifra publicada
        tenga fuente y licencia: que el fichero no toque el disco no cambia de
        quien es el dato.

        Lo que las fija no es un digest sino el release del vintage, que el
        lint ya obliga a ser explicito. Por eso el aviso de `insumos_sha256`
        las salta: un aviso que nadie puede resolver deja de leerse, y con el
        se dejan de leer los nueve que si son accionables.
        """
        return self.url.startswith("s3://") or self.layer == _CAPA_REMOTA

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        missing = {"id", "layer", "url", "license", "vintage"} - data.keys()
        if missing:
            raise ValueError(f"Fuente incompleta, faltan campos: {sorted(missing)}")
        return cls(
            id=str(data["id"]),
            layer=str(data["layer"]),
            url=str(data["url"]),
            license=str(data["license"]),
            vintage=str(data["vintage"]),
            insumos_sha256=str(data.get("insumos_sha256", "")),
            hdx_dataset=str(data.get("hdx_dataset", "")),
            hdx_resource=str(data.get("hdx_resource", "")),
            notes=str(data.get("notes", "")),
        )


@dataclass(frozen=True, slots=True)
class Manifest:
    """Conjunto de fuentes fijadas para un pais y una version del activo."""

    manifest_id: str
    iso3: str
    generated_utc: str
    sources: tuple[Source, ...]
    #: Cifra oficial contra la que se valida el total nacional (assert §6.4).
    #: Vacio significa que el activo se construye sin esa red de seguridad, y
    #: el lint lo reporta como aviso.
    referencia_oficial: dict[str, Any] = field(default_factory=dict)

    @property
    def bucket(self) -> Bucket:
        """Cubo resultante del activo construido con estas fuentes."""
        return resolve_bucket(s.license for s in self.sources)

    def by_layer(self, layer: str) -> tuple[Source, ...]:
        return tuple(s for s in self.sources if s.layer == layer)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            manifest_id=str(data["manifest_id"]),
            iso3=str(data["iso3"]).upper(),
            generated_utc=str(data["generated_utc"]),
            sources=tuple(Source.from_dict(s) for s in data.get("sources", [])),
            referencia_oficial=dict(data.get("referencia_oficial") or {}),
        )

    @classmethod
    def load(cls, iso3: str, directory: Path | None = None) -> Self:
        """Carga ``data/manifests/<iso3>.yaml``."""
        base = directory or MANIFESTS_DIR
        path = base / f"{iso3.upper()}.yaml"
        if not path.exists():
            raise FileNotFoundError(f"No hay manifest para {iso3.upper()}: {path}")
        return cls.from_dict(yaml.safe_load(path.read_text(encoding="utf-8")))


@lru_cache(maxsize=1)
def _schema_validator() -> Draft202012Validator:
    """Validador del schema del manifest, cargado una sola vez."""
    schema = json.loads((SCHEMAS_DIR / "manifest.schema.json").read_text(encoding="utf-8"))
    return Draft202012Validator(schema)


def lint_manifest_file(path: Path) -> list[str]:
    """Valida un manifest en disco: primero su forma, luego su contenido.

    El orden importa. ``Manifest.from_dict`` colapsa el YAML a dataclasses y en
    el camino descarta lo que no reconoce; si el schema no se aplica antes, una
    clave mal escrita se volveria invisible en vez de ser un error.
    """
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        return [f"YAML invalido: {exc}"]
    if not isinstance(raw, dict):
        return ["El manifest no es un objeto YAML"]

    forma = [
        f"schema: {'.'.join(str(x) for x in error.path) or '(raiz)'}: {error.message}"
        for error in sorted(_schema_validator().iter_errors(raw), key=str)
    ]
    if forma:
        # Sin forma valida, el lint de contenido solo produciria ruido derivado.
        return forma
    return lint_manifest(Manifest.from_dict(raw))


def lint_manifest(manifest: Manifest) -> list[str]:
    """Valida un manifest. Devuelve la lista de problemas (vacia = limpio).

    Se ejecuta en CI (§7, mitigacion de "contaminacion de licencias") y como
    guardia previa a cada build de P0.
    """
    problems: list[str] = []
    seen: set[str] = set()
    hay_fuente_nc = False

    for source in manifest.sources:
        if source.id in seen:
            problems.append(f"[{source.id}] id duplicado en el manifest")
        seen.add(source.id)

        try:
            bucket = source.bucket
        except LicenseViolationError as exc:
            problems.append(f"[{source.id}] {exc}")
            continue

        if source.vintage.strip().lower() in _FLOATING_VINTAGES:
            problems.append(
                f"[{source.id}] vintage flotante {source.vintage!r}: "
                f"fija el release explicito (RNF-04)"
            )
        if not source.url.startswith(("http://", "https://", "s3://", "az://")):
            problems.append(f"[{source.id}] url no reconocida: {source.url!r}")
        if source.hdx_dataset and "data.humdata.org" not in source.url:
            problems.append(
                f"[{source.id}] declara hdx_dataset pero su url no apunta a HDX: "
                f"la url debe ser la pagina estable del dataset, y la de descarga "
                f"se resuelve por la API en cada build"
            )
        if bucket is Bucket.NC:
            hay_fuente_nc = True
            problems.append(
                f"[{source.id}] fuente NC ({source.license}) en el manifest de exposicion: "
                f"pertenece al cubo 'nc/', no al activo que consume el reporte (§2.4)"
            )
        if not source.insumos_sha256 and not source.se_lee_en_remoto:
            problems.append(
                f"[{source.id}] sin insumos_sha256: la trazabilidad queda incompleta, y un "
                f"tercero puede republicar el insumo sin que nada lo note (aviso). "
                f"El proximo build lo mide y lo deja en medicion.json"
            )

    if not manifest.sources:
        problems.append("El manifest no declara ninguna fuente")
        return problems

    # LA REGLA DE LOS TRES CUBOS TAMBIEN ES UNA PROPIEDAD DEL CONJUNTO.
    #
    # El bucle de arriba mira fuente por fuente, y hay una violacion que ninguna
    # fuente individual delata: **dos share-alike incompatibles**. ODbL y
    # CC BY-SA 4.0 exigen cada una que el derivado se publique bajo ella, y no
    # hay licencia que cumpla las dos. Por separado las dos son legitimas.
    #
    # Esto se comprobaba de rebote, al evaluar `manifest.bucket` dentro del
    # f-string que imprime el cubo en `centinela lint-manifests`. O sea que la
    # violacion salia como traceback en vez de como problema del lint — y solo
    # si no habia ningun otro error antes, porque ese f-string no se evalua
    # cuando ya los hay.
    #
    # Se salta si ya hay una fuente NC: el mensaje de arriba nombra cual, que es
    # lo accionable, y repetirlo aqui sin el nombre solo anade ruido.
    if not hay_fuente_nc:
        try:
            assert_publishable_in_report(s.license for s in manifest.sources)
        except LicenseViolationError as exc:
            problems.append(str(exc))

    return problems


#: Un elemento de `sources:` empieza aqui. Los manifests se escriben a mano y
#: llevan mas prosa que datos —notas de varias lineas que explican por que una
#: fuente entra y que trampa tiene—, asi que fijar un digest NO puede pasar por
#: `yaml.safe_dump`: reescribiria el fichero y se llevaria por delante todos los
#: comentarios. Se edita por lineas.
_RE_FUENTE = re.compile(r"^  - id:\s*(\S+)\s*$")
_RE_DIGEST = re.compile(r"^(\s*insumos_sha256:\s*)(.*)$")
_RE_VINTAGE = re.compile(r"^(\s*)vintage:\s*.*$")


def fijar_insumos_en_manifest(path: Path, digests: dict[str, str]) -> list[str]:
    """Escribe los ``insumos_sha256`` medidos dentro del manifest, in situ.

    ``digests`` es ``{source_id: digest}``, tal como sale del bloque ``insumos``
    de ``medicion.json``. Devuelve el parte de lo que cambio, una linea por
    fuente tocada.

    EXISTE PARA QUE NADIE COPIE HASHES A MANO. Es la misma razon por la que
    `write_measurement` existe: las cifras del manifest se copiaban del log a
    mano, y copiar a mano es como se desincronizan las cosas. Con 194 fuentes en
    diecinueve paises, a mano no es "tedioso", es "no va a pasar".

    Un digest que ya esta fijado y no coincide NO se pisa: eso es exactamente el
    caso que `_verificar_insumos` esta para detener, y sobrescribirlo en silencio
    convertiria la puerta en un sello de goma. Se reporta y se deja al humano.
    """
    lineas = path.read_text(encoding="utf-8").splitlines()
    salida: list[str] = []
    parte: list[str] = []
    fuente = ""
    pendientes = dict(digests)

    for linea in lineas:
        if (m := _RE_FUENTE.match(linea)) is not None:
            fuente = m.group(1)
            salida.append(linea)
            continue

        if fuente and (m := _RE_DIGEST.match(linea)) is not None:
            nuevo = pendientes.pop(fuente, "")
            actual = m.group(2).strip().strip('"').strip("'")
            if not nuevo:
                salida.append(linea)
            elif not actual:
                salida.append(f'{m.group(1)}"{nuevo}"')
                parte.append(f"[{fuente}] fijado {nuevo}")
            elif actual == nuevo:
                salida.append(linea)
            else:
                salida.append(linea)
                parte.append(
                    f"[{fuente}] SIN TOCAR: el manifest fija {actual} y la medicion "
                    f"trae {nuevo}. Decide tu cual vale antes de reemplazarlo"
                )
            continue

        salida.append(linea)

    # Una fuente puede no traer la clave: el schema no la exige. Se inserta
    # detras de `vintage`, que es donde vive en el resto del fichero.
    if pendientes:
        salida = _insertar_digests(salida, pendientes, parte)

    path.write_text("\n".join(salida) + "\n", encoding="utf-8")
    return parte


def _insertar_digests(lineas: list[str], pendientes: dict[str, str], parte: list[str]) -> list[str]:
    """Anade la clave a las fuentes que todavia no la declaraban."""
    salida: list[str] = []
    fuente = ""
    for linea in lineas:
        salida.append(linea)
        if (m := _RE_FUENTE.match(linea)) is not None:
            fuente = m.group(1)
            continue
        if fuente in pendientes and (m := _RE_VINTAGE.match(linea)) is not None:
            digest = pendientes.pop(fuente)
            salida.append(f'{m.group(1)}insumos_sha256: "{digest}"')
            parte.append(f"[{fuente}] fijado {digest} (clave anadida)")
    for fuente_ausente in sorted(pendientes):
        parte.append(f"[{fuente_ausente}] la medicion lo trae pero el manifest no lo declara")
    return salida
