"""Quien puso el dato, y en que superficie tiene que aparecer su credito.

`ATTRIBUTION.md` afirmaba, en su tercera linea, que toda salida de CENTINELA
lleva estas atribuciones y que **se verifica en CI**. Ninguna de las dos cosas
era cierta:

* ESA WorldCover no aparecia en `ATTRIBUTION.md` pese a estar declarada en los
  diecinueve manifests bajo CC BY 4.0 y a publicarse su dato en
  `site/incendios.json` y en las columnas `lulc_*_pct` del activo.
* El pie del visor citaba cuatro fuentes de las diez que entran al activo, y
  cerraba con «Datos del núcleo bajo CC BY 4.0» sobre unos datos que
  `resolve_bucket` clasifica como **ODbL en los diecinueve paises**.
* El pie de todo mapa no citaba WorldPop, de donde sale `pop_65p`, que el propio
  reporte publica en portada como «De ellas, 65 años o más».
* NASA FIRMS no aparecia en ningun manifest, en ningun `LICENSE_BUCKET` y en
  ningun credito: `resolve_bucket` no la habia visto jamas.
* Y «se verifica en CI» era falso: `grep -rn ATTRIBUTION_LINE tests/` no devolvia
  nada, y ningun test comparaba `ATTRIBUTION.md` con las licencias de los
  manifests.

Este modulo convierte la atribucion en **dato**: un catalogo con una entrada por
fuente, cada una declarando en que superficies publicas tiene que salir su
credito. De ahi salen el pie de los mapas, el bloque `licencia` de `report.json`
y de `site/incendios.json`, el `LICENSE.txt` de cada reporte — y el guardia que
hace verdadera la frase de `ATTRIBUTION.md`.

La licencia se sigue resolviendo en `licensing.py`, que es la regla de los tres
cubos. Aqui va **quien** hay que citar; alli, **bajo que** se puede publicar.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Final

from .licensing import Bucket, resolve_bucket

#: Superficies publicas donde puede exigirse un credito.
#:
#: No son categorias decorativas: cada una es un fichero o un pixel concreto que
#: un guardia comprueba. `MAPA` es el pie de los PNG; `VISOR`, el `<footer>` de
#: `site/index.html`; `REPORTE`, el bloque `licencia` de `report.json` y el
#: `LICENSE.txt` que viaja a su lado; `INCENDIOS`, el bloque equivalente de
#: `site/incendios.json`.
MAPA: Final[str] = "mapa"
VISOR: Final[str] = "visor"
REPORTE: Final[str] = "reporte"
INCENDIOS: Final[str] = "incendios"


@dataclass(frozen=True, slots=True)
class Atribucion:
    """Un credito, con su licencia y las superficies donde es obligatorio."""

    clave: str
    #: Nombre completo, para `ATTRIBUTION.md` y el bloque publicado.
    titulo: str
    #: Linea corta para un pie, con el rol que cumple el dato delante.
    credito: str
    spdx: str
    url: str
    superficies: frozenset[str]
    #: LO MINIMO QUE TIENE QUE APARECER PARA QUE EL CREDITO CUENTE.
    #:
    #: El guardia lo busca literal en cada superficie. Se declara y no se deduce
    #: del titulo porque las superficies escriben distinto: `ATTRIBUTION.md` cita
    #: «USGS Earthquake Hazards Program» y el pie del mapa dice «USGS ShakeMap».
    #: Un guardia que recortase el titulo a ojo aprobaria o rechazaria segun como
    #: estuviera puntuada la frase, que es como se construye un cerrojo
    #: tipografico en vez de una comprobacion.
    aguja: str = ""

    def aparece_en(self, texto: str) -> bool:
        return self.aguja.lower() in texto.lower()


def _a(
    clave: str,
    titulo: str,
    credito: str,
    spdx: str,
    url: str,
    aguja: str,
    *superficies: str,
) -> Atribucion:
    return Atribucion(clave, titulo, credito, spdx, url, frozenset(superficies), aguja)


#: Catalogo de creditos, por clave estable.
#:
#: El orden es el de lectura de un pie: primero de donde sale el sismo, luego la
#: gente, luego lo construido, luego los limites.
CATALOGO: Final[dict[str, Atribucion]] = {
    a.clave: a
    for a in (
        _a(
            "usgs",
            "USGS Earthquake Hazards Program",
            "Intensidad: USGS ShakeMap (dominio público)",
            "public-domain-usgov",
            "https://earthquake.usgs.gov/",
            "USGS",
            MAPA,
            VISOR,
            REPORTE,
        ),
        _a(
            "ghsl",
            "JRC / Comisión Europea — GHS-POP y GHS-BUILT-S (GHSL R2023A)",
            "Población: GHS-POP, JRC/Comisión Europea",
            "EC-reuse-attribution",
            "https://ghsl.jrc.ec.europa.eu/",
            "GHS-POP",
            MAPA,
            VISOR,
            REPORTE,
        ),
        _a(
            "worldpop",
            "WorldPop, University of Southampton",
            "Estructura por edad: WorldPop (CC BY 4.0)",
            "CC-BY-4.0",
            "https://www.worldpop.org/",
            "WorldPop",
            # VA EN EL MAPA, Y NO ESTABA. De aqui sale `pop_65p`, que el reporte
            # publica en portada como «De ellas, 65 años o más», y §2.4 regla 2
            # declara la atribucion obligatoria en cada artefacto.
            MAPA,
            VISOR,
            REPORTE,
        ),
        _a(
            "overture",
            "Overture Maps Foundation",
            "Edificaciones y vías: Overture Maps, © OpenStreetMap contributors (ODbL)",
            "ODbL-1.0",
            "https://overturemaps.org/",
            "Overture",
            MAPA,
            VISOR,
            REPORTE,
            INCENDIOS,
        ),
        _a(
            "osm",
            "© OpenStreetMap contributors",
            "© OpenStreetMap contributors (ODbL)",
            "ODbL-1.0",
            "https://www.openstreetmap.org/copyright",
            "OpenStreetMap",
            VISOR,
            REPORTE,
            INCENDIOS,
        ),
        _a(
            "cod_ab",
            "OCHA — Common Operational Datasets (COD-AB), vía HDX",
            "Límites municipales: OCHA COD-AB (CC BY-IGO)",
            "CC-BY-IGO",
            "https://data.humdata.org/",
            "COD-AB",
            MAPA,
            VISOR,
            REPORTE,
        ),
        _a(
            "dane",
            "Departamento Administrativo Nacional de Estadística - DANE: www.dane.gov.co",
            "Límites municipales en Colombia: DANE, MGN (CC BY 4.0)",
            "CC-BY-4.0",
            "https://geoportal.dane.gov.co/",
            "DANE",
            REPORTE,
        ),
        _a(
            "hotosm",
            "Humanitarian OpenStreetMap Team (HOT), vía HDX",
            "Salud y educación: HOT / OpenStreetMap (ODbL)",
            "ODbL-1.0",
            "https://www.hotosm.org/",
            "HOT",
            REPORTE,
            INCENDIOS,
        ),
        _a(
            "healthsites",
            "healthsites.io, vía HDX",
            "Salud: healthsites.io (ODbL)",
            "ODbL-1.0",
            "https://healthsites.io/",
            "healthsites",
            REPORTE,
        ),
        _a(
            "ourairports",
            "OurAirports",
            "Aeropuertos: OurAirports (dominio público)",
            "public-domain",
            "https://ourairports.com/data/",
            "OurAirports",
            REPORTE,
        ),
        _a(
            "worldcover",
            "ESA WorldCover 2021 v200 (Zanaga et al.)",
            "Cobertura del suelo: ESA WorldCover (CC BY 4.0)",
            "CC-BY-4.0",
            "https://esa-worldcover.org/",
            "WorldCover",
            # NO VA EN EL MAPA: el PNG del reporte no dibuja cobertura del suelo.
            # Va donde su dato se publica — el visor y el panel de fuego.
            VISOR,
            REPORTE,
            INCENDIOS,
        ),
        _a(
            "firms",
            "NASA FIRMS / LANCE — VIIRS 375 m",
            "Focos de calor: NASA FIRMS (VIIRS)",
            "public-domain-usgov",
            "https://firms.modaps.eosdis.nasa.gov/",
            "FIRMS",
            VISOR,
            INCENDIOS,
        ),
    )
}


#: Prefijo del `id` de la fuente en el manifest -> claves del catalogo.
#:
#: Se empareja por prefijo y no por id exacto porque diecinueve de los ids son
#: `cod_ab_<iso3>`: enumerarlos uno a uno garantiza que el pais numero veinte
#: entre sin credito y que nadie se entere.
#:
#: Una fuente ODbL derivada de OSM arrastra **dos** creditos: el agregador y
#: OpenStreetMap. La ODbL §4.3 exige el aviso de la base original, no solo el
#: de quien la reempaqueto.
POR_PREFIJO: Final[tuple[tuple[str, tuple[str, ...]], ...]] = (
    ("ghs_pop", ("ghsl",)),
    ("ghs_built", ("ghsl",)),
    ("worldpop", ("worldpop",)),
    ("worldcover", ("worldcover",)),
    ("overture", ("overture", "osm")),
    ("cod_ab", ("cod_ab",)),
    ("dane", ("dane",)),
    ("hotosm", ("hotosm", "osm")),
    ("healthsites", ("healthsites", "osm")),
    ("ourairports", ("ourairports",)),
    # FIRMS NO ESTA EN NINGUN MANIFEST, Y ESE ERA EL HUECO.
    #
    # `site/incendios.json` publica sus detecciones cruzadas contra el activo, y
    # su fuente primaria no aparecia en ningun manifest, en ningun
    # `LICENSE_BUCKET` y en ningun credito: la regla de los tres cubos nunca la
    # evaluo. P5 no construye un activo, asi que no tiene manifest donde
    # declararla; se declara aqui, que es donde vive el credito.
    ("firms", ("firms",)),
)


class FuenteSinCreditoError(Exception):
    """Una fuente del manifest no tiene a quien atribuir."""


def claves_de_fuente(source_id: str) -> tuple[str, ...]:
    """Creditos que exige una fuente del manifest.

    Raises:
        FuenteSinCreditoError: si el id no encaja con ningun prefijo conocido.
            Es deliberado que sea un error y no una lista vacia: una fuente
            nueva sin credito es exactamente el hueco por el que ESA WorldCover
            se publico durante meses sin aparecer en ningun sitio.
    """
    for prefijo, claves in POR_PREFIJO:
        if source_id.lower().startswith(prefijo):
            return claves
    raise FuenteSinCreditoError(
        f"La fuente {source_id!r} no tiene credito declarado en POR_PREFIJO. "
        f"Anadelo con las claves del CATALOGO que le correspondan: publicar su "
        f"dato sin citarla incumple la licencia."
    )


def atribuciones_de(source_ids: Iterable[str], *, evento: bool = True) -> tuple[Atribucion, ...]:
    """Creditos de un conjunto de fuentes, en el orden del catalogo y sin repetir.

    ``evento`` incluye a USGS, que no esta en ningun manifest —el feed no es un
    insumo del activo— y sin embargo es la fuente del sismo en todo lo que se
    publica de un reporte.
    """
    claves: set[str] = {"usgs"} if evento else set()
    for source_id in source_ids:
        claves.update(claves_de_fuente(source_id))
    return tuple(a for clave, a in CATALOGO.items() if clave in claves)


def para_superficie(atribuciones: Iterable[Atribucion], superficie: str) -> tuple[Atribucion, ...]:
    """Las que tienen que salir en una superficie concreta."""
    return tuple(a for a in atribuciones if superficie in a.superficies)


def linea_de_credito(atribuciones: Iterable[Atribucion], *, cola: str = "") -> str:
    """Pie de una pieza, con los creditos separados por punto medio."""
    partes = [a.credito for a in atribuciones]
    if cola:
        partes.append(cola)
    return " · ".join(partes)


def bloque_de_licencia(
    source_ids: Iterable[str], *, superficie: str, evento: bool = True
) -> dict[str, object]:
    """El bloque `licencia` que viaja dentro de un artefacto publicado.

    Es el arreglo de fondo del hallazgo: la licencia dejaba de existir en cuanto
    el dato salia del repositorio. Un `report.json` descargado suelto no decia
    bajo que se podia usar, y la ODbL §4.3 exige que el aviso viaje **con la obra
    producida**, no en una pagina que quiza nadie abra.
    """
    ids = list(source_ids)
    atribuciones = atribuciones_de(ids, evento=evento)
    de_la_superficie = para_superficie(atribuciones, superficie)
    return {
        "cubo": cubo_de(ids).value,
        "spdx": spdx_del_derivado(ids),
        "texto": TEXTO_DEL_DERIVADO[spdx_del_derivado(ids)],
        "atribuciones": [
            {"titulo": a.titulo, "licencia": a.spdx, "url": a.url} for a in de_la_superficie
        ],
    }


#: Licencia bajo la que se publica el derivado, por cubo.
#:
#: DECIA CC BY 4.0 SOBRE DATOS ODbL. El pie del visor cerraba con «Datos del
#: núcleo bajo CC BY 4.0», y medido con `resolve_bucket` sobre los diecinueve
#: manifests, **los diecinueve dan `odbl`**: todos fijan Overture buildings y
#: transportation bajo ODbL-1.0, y salud/educacion bajo ODbL via HOTOSM. La
#: ODbL §4.4 exige que el derivado se publique bajo ODbL.
SPDX_POR_CUBO: Final[dict[Bucket, str]] = {
    Bucket.CORE: "CC-BY-4.0",
    Bucket.ODBL: "ODbL-1.0",
    Bucket.NC: "CC-BY-NC-SA-4.0",
}

TEXTO_DEL_DERIVADO: Final[dict[str, str]] = {
    "CC-BY-4.0": (
        "Este derivado se publica bajo CC BY 4.0. Citar a CENTINELA y a las "
        "fuentes listadas arriba."
    ),
    "ODbL-1.0": (
        "Este derivado contiene datos bajo Open Database License (ODbL) 1.0 y se "
        "publica bajo esa misma licencia (ODbL §4.4). Al redistribuirlo hay que "
        "conservar este aviso y las atribuciones listadas arriba (ODbL §4.3)."
    ),
    "CC-BY-NC-SA-4.0": (
        "Este derivado incorpora fuentes no comerciales y no es redistribuible "
        "bajo las licencias anteriores."
    ),
}


def cubo_de(source_ids: Iterable[str]) -> Bucket:
    """Cubo del derivado, resuelto sobre las licencias de sus fuentes."""
    return resolve_bucket(_licencias(source_ids))


def spdx_del_derivado(source_ids: Iterable[str]) -> str:
    return SPDX_POR_CUBO[cubo_de(source_ids)]


def _licencias(source_ids: Iterable[str]) -> list[str]:
    """Licencias que declara el catalogo para esas fuentes.

    Se toman del catalogo y no del manifest a proposito: asi el bloque publicado
    se puede calcular tambien para artefactos que no salen de un manifest, como
    `site/incendios.json`, cuya fuente primaria —NASA FIRMS— no esta declarada en
    ninguno. Ese era justamente el hueco: `resolve_bucket` no la habia visto
    jamas, asi que la regla de los tres cubos nunca la evaluo.
    """
    licencias: list[str] = []
    for source_id in source_ids:
        for clave in claves_de_fuente(source_id):
            licencias.append(CATALOGO[clave].spdx)
    return licencias


#: Donde vive el manifiesto que el disclaimer del reporte prometia enlazar.
#:
#: `markdown.py` escribia «Manifiesto de exposicion: `col-v0.6`» en texto plano,
#: sin URL, mientras el cuarto disclaimer remitia a «el manifiesto enlazado».
URL_DEL_MANIFIESTO: Final[str] = (
    "https://github.com/sforero77/CENTINELA/blob/main/data/manifests/{iso3}.yaml"
)


def iso3_de_manifest_id(manifest_id: str) -> str:
    """``"col-v0.6"`` -> ``"COL"``. Vacio si la cadena no tiene esa forma."""
    cabeza = manifest_id.split("-", 1)[0].strip().upper()
    return cabeza if len(cabeza) == 3 and cabeza.isalpha() else ""


def fuentes_del_pais(iso3: str) -> list[str]:
    """ids de fuente que declara el manifest vigente de un pais.

    SE LEE EL MANIFEST DE HOY, NO EL DE LA VERSION QUE CONSTRUYO EL ACTIVO.

    Es una aproximacion deliberada y acotada: lo que cambia entre versiones de
    un manifest es el `vintage` o el release, casi nunca **quien** publica el
    dato. Guardar la lista de fuentes en cada reporte pesaria mas que el bloque
    de licencia entero y no cambiaria ningun credito de los que hoy existen.
    Si algun dia se retira una fuente, el reporte viejo citara a alguien de mas
    — que es el error que se puede permitir, al reves del de citar a alguien de
    menos.
    """
    from .manifest import Manifest

    return [s.id for s in Manifest.load(iso3).sources]
