"""Reportes ya publicados que se quedaron atras de sus propias fuentes.

EL DIA QUE ESTO HIZO FALTA. El 1-sep-2026 se re-emitieron los veintiun eventos
del catalogo para arreglar una columna del `adm2.csv`. La re-emision trajo algo
que nadie buscaba: el Choco publicaba el **ShakeMap v7 cuando USGS ya servia el
v8**, y con esa version se movieron las nueve cifras del backtest que cita la
portada. Nadie podia saberlo. Se supo porque alguien re-emitio a mano por otro
motivo.

POR QUE EL REPASO NO LO VE. `repaso.py` cumple RF-04 —al aparecer una version
nueva, re-emitir— pero salta los backtest a proposito (`repaso.py:113`), y los
veintiun publicados **son todos** backtest. La razon esta escrita alli y sigue
siendo buena: re-emitir un historico cada vez que USGS retoca su Atlas
convertiria el catalogo en ruido. El resultado, sin embargo, es que el repaso
lleva dias saliendo en verde con `"revisados": 0`.

QUE HACE ESTE MODULO, Y QUE NO HACE. Compara lo que cada reporte publicado dice
haber usado contra lo que sus fuentes sirven hoy, y **devuelve una lista**. No
despacha, no descarga productos, no recalcula. La decision de re-emitir un
historico sigue siendo de una persona; lo que cambia es que deja de tomarse a
ciegas.

Son dos preguntas distintas y se responden por caminos distintos:

- **Productos de USGS** (ShakeMap, Ground Failure): hay que preguntar al detail
  del evento. Es la misma llamada que ya hace el repaso, contra el mismo
  endpoint, sin el filtro de backtest.
- **Activo de exposicion**: no hace falta red. El manifiesto vigente de cada
  pais esta en `data/manifests/<ISO3>.yaml`, y el reporte registra con cual se
  calculo. Es una comparacion de cadenas contra el repositorio.

Medido el 1-sep-2026 sobre los veintiuno: **uno** iba atrasado en productos —el
Choco— y los veinte restantes ya estaban en su version vigente. El punto ciego
era real; el dano acumulado, no. Por eso esto informa en vez de despachar: la
frecuencia con la que encuentra trabajo no justifica automatizar la re-emision,
y si justifica dejar de estar ciego.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from ..common.http import Fetcher
from ..common.logging import get_logger
from ..common.manifest import Manifest
from ..common.paths import MANIFESTS_DIR, REPORTS_DIR
from ..p2_impact.products import ProductContractError, parse_products
from .repaso import detail_url

_log = get_logger(__name__)


def iso3_del_manifiesto(manifest_id: str) -> str:
    """`col-v0.6` -> `COL`.

    El `report.json` no guarda el pais: guarda el manifiesto con el que se
    calculo, y el pais es su prefijo. Derivarlo de ahi es preferible a leerlo
    de otro sitio, porque ata la comparacion al mismo dato que se va a comparar
    —si el manifiesto dice `col`, el vigente que toca mirar es el de COL y no
    el del pais que diga cualquier otro campo.
    """
    return manifest_id.split("-", 1)[0].upper()


@dataclass(slots=True, frozen=True)
class Rezago:
    """Un reporte publicado y en que se quedo atras."""

    usgs_id: str
    #: Version que el reporte dice haber usado / la que USGS sirve hoy.
    shakemap_publicado: int
    shakemap_vigente: int
    groundfailure_publicado: int
    groundfailure_vigente: int
    #: Manifiesto con el que se calculo / el vigente en el repositorio.
    manifiesto_publicado: str
    manifiesto_vigente: str

    @property
    def productos(self) -> bool:
        """USGS sirve una version mas nueva de ShakeMap o de Ground Failure."""
        return (
            self.shakemap_vigente > self.shakemap_publicado
            or self.groundfailure_vigente > self.groundfailure_publicado
        )

    @property
    def exposicion(self) -> bool:
        """El activo del pais se reconstruyo despues de calcularse el reporte."""
        return self.manifiesto_publicado != self.manifiesto_vigente

    @property
    def hay(self) -> bool:
        return self.productos or self.exposicion

    def describir(self) -> str:
        """Una linea legible. Es lo que acaba en el cuerpo del issue."""
        partes = []
        if self.shakemap_vigente > self.shakemap_publicado:
            partes.append(f"ShakeMap v{self.shakemap_publicado} -> v{self.shakemap_vigente}")
        if self.groundfailure_vigente > self.groundfailure_publicado:
            partes.append(
                f"Ground Failure v{self.groundfailure_publicado} -> v{self.groundfailure_vigente}"
            )
        if self.exposicion:
            partes.append(f"exposicion {self.manifiesto_publicado} -> {self.manifiesto_vigente}")
        return f"{self.usgs_id}: " + " · ".join(partes)


@dataclass(slots=True)
class ResultadoRezago:
    """Que encontro una pasada."""

    #: Reportes que se llegaron a comprobar contra USGS.
    revisados: int = 0
    #: Los que van atras en algo. Orden estable: el mas atrasado primero.
    rezagados: list[Rezago] = field(default_factory=list)
    #: No se pudieron consultar. **No** son "sin cambios": un fallo de red no
    #: es una respuesta, y confundirlos seria el cero silencioso de siempre.
    fallidos: list[str] = field(default_factory=list)

    @property
    def ciego(self) -> bool:
        """No se pudo consultar NINGUNO de los que tocaba.

        Misma distincion que en el repaso, en FIRMS y en la frescura: que falle
        alguno es tolerable; que fallen todos es no haber comprobado, y eso no
        puede salir en verde.
        """
        return bool(self.fallidos) and self.revisados == 0

    @property
    def por_productos(self) -> list[Rezago]:
        """Los que van atras en ciencia: USGS revisó el ShakeMap o el Ground Failure.

        Re-emitir uno de estos **mueve cifras publicadas**. El 1-sep-2026, con
        el Choco, movio las nueve que el README cita a mano. Son los que piden
        una persona detras.
        """
        return [r for r in self.rezagados if r.productos]

    @property
    def solo_exposicion(self) -> list[Rezago]:
        """Los que solo van atras en la receta del activo, no en la ciencia.

        El salto `v0.1` -> `v0.2` de los diecinueve manifiestos anadio ESA
        WorldCover, que alimenta las columnas `lulc_*` — y P2 no las usa: son
        del bloque de incendios. Las fuentes de poblacion, edificaciones y vias
        no cambiaron. Re-emitir uno de estos actualiza la etiqueta y poco mas.

        La distincion no es cosmetica: decide quien puede pulsar el boton.
        """
        return [r for r in self.rezagados if r.exposicion and not r.productos]


def _manifiesto_vigente(iso3: str, manifests_dir: Path | None) -> str:
    """El `manifest_id` que hoy tiene el pais en el repositorio.

    Si el manifiesto no existe se devuelve cadena vacia en vez de propagar el
    error: un pais sin manifiesto es un problema real, pero no uno que deba
    impedir comprobar los otros veinte reportes.
    """
    try:
        return Manifest.load(iso3, manifests_dir or MANIFESTS_DIR).manifest_id
    except (FileNotFoundError, ValueError, KeyError) as error:
        _log.warning(
            "no se pudo leer el manifiesto vigente",
            extra={"context": {"iso3": iso3, "error": str(error)}},
        )
        return ""


def _entero(valor: object) -> int:
    """Un campo de `inputs` que deberia ser entero, sin dar por hecho que lo es.

    `report.json` es un fichero en disco que puede venir de una version vieja
    del pipeline. Tratar un campo ausente o raro como 0 hace que el reporte
    aparezca rezagado —que es el lado seguro: se mira, no se ignora.
    """
    if isinstance(valor, bool):
        return 0
    if isinstance(valor, int | float):
        return int(valor)
    return 0


def _reportes(reports_dir: Path | None) -> list[tuple[str, dict[str, object]]]:
    """`(usgs_id, inputs)` de cada reporte publicado, ordenados por id."""
    raiz = reports_dir or REPORTS_DIR
    if not raiz.exists():
        return []

    salida: list[tuple[str, dict[str, object]]] = []
    for ruta in sorted(raiz.glob("*/report.json")):
        try:
            datos = json.loads(ruta.read_text(encoding="utf-8"))
            entradas = datos["inputs"]
        except (OSError, ValueError, KeyError) as error:
            # Un reporte ilegible no puede parar la comprobacion de los demas,
            # pero tampoco se calla.
            _log.warning(
                "report.json ilegible al comprobar rezago",
                extra={"context": {"ruta": str(ruta), "error": str(error)}},
            )
            continue
        salida.append((ruta.parent.name, entradas))
    return salida


def comprobar(
    fetcher: Fetcher,
    *,
    reports_dir: Path | None = None,
    manifests_dir: Path | None = None,
) -> ResultadoRezago:
    """Compara cada reporte publicado con lo que sus fuentes sirven hoy.

    No despacha nada. Ver el docstring del modulo para por que.
    """
    resultado = ResultadoRezago()

    for usgs_id, entradas in _reportes(reports_dir):
        manifiesto_publicado = str(entradas.get("exposure_manifest", ""))
        manifiesto_vigente = (
            _manifiesto_vigente(iso3_del_manifiesto(manifiesto_publicado), manifests_dir)
            if manifiesto_publicado
            else ""
        )

        try:
            productos = parse_products(fetcher.get_json(detail_url(usgs_id)))
        except (ProductContractError, OSError, ValueError) as error:
            # UN FALLO NO ES UN "AL DIA". Se cuenta aparte y el evento no entra
            # ni en revisados ni en rezagados: de el no sabemos nada.
            resultado.fallidos.append(usgs_id)
            _log.warning(
                "no se pudo comprobar el rezago del reporte",
                extra={"context": {"usgs_id": usgs_id, "error": str(error)}},
            )
            continue

        resultado.revisados += 1
        rezago = Rezago(
            usgs_id=usgs_id,
            shakemap_publicado=_entero(entradas.get("shakemap_version")),
            shakemap_vigente=productos.shakemap_version,
            groundfailure_publicado=_entero(entradas.get("groundfailure_version")),
            groundfailure_vigente=productos.groundfailure_version,
            manifiesto_publicado=manifiesto_publicado,
            manifiesto_vigente=manifiesto_vigente or manifiesto_publicado,
        )
        if rezago.hay:
            resultado.rezagados.append(rezago)

    # El mas atrasado primero: si algun dia la lista es larga, lo que se lee
    # antes es lo que mas se movio.
    resultado.rezagados.sort(
        key=lambda r: (
            r.shakemap_vigente - r.shakemap_publicado,
            r.groundfailure_vigente - r.groundfailure_publicado,
        ),
        reverse=True,
    )

    _log.info(
        "comprobacion de rezago terminada",
        extra={
            "context": {
                "revisados": resultado.revisados,
                "rezagados": len(resultado.rezagados),
                "fallidos": len(resultado.fallidos),
            }
        },
    )
    return resultado
