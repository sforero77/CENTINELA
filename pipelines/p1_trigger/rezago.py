"""Reportes ya publicados que se quedaron atras de sus propias fuentes.

EL DIA QUE ESTO HIZO FALTA. El 1-sep-2026 se re-emitieron los veintiun eventos
del catalogo para arreglar una columna del `adm2.csv`. La re-emision trajo algo
que nadie buscaba: el Choco publicaba el **ShakeMap v7 cuando USGS ya servia el
v8**, y con esa version se movieron las nueve cifras del backtest que citaba la
portada. Nadie podia saberlo. Se supo porque alguien re-emitio a mano por otro
motivo.

LO QUE EL REPASO NO VE. `repaso.py` cumple RF-04 —al aparecer una version nueva,
re-emitir— y desde el 8-sep-2026 incluye los backtest, pero solo mira los eventos
de los ultimos noventa dias. Le quedan fuera dos cosas: un ShakeMap que USGS
revise pasado ese plazo, y un cambio en la receta del activo de un pais, que no
es una version de USGS y por la que el repaso no pregunta.

QUE HACE ESTE MODULO, Y QUE NO HACE. Compara lo que cada reporte publicado dice
haber usado contra lo que sus fuentes sirven hoy, y **devuelve una lista**. No
despacha, no descarga productos, no recalcula: eso lo hace `rezago.yml`, que
re-emite solo lo que esta lista marca como re-emitible.

Son dos preguntas distintas y se responden por caminos distintos:

- **Productos de USGS** (ShakeMap, Ground Failure): hay que preguntar al detail
  del evento. Es la misma llamada que ya hace el repaso, contra el mismo
  endpoint, sin la ventana de noventa dias.
- **Activo de exposicion**: no hace falta red. El manifiesto vigente de cada
  pais esta en `data/manifests/<ISO3>.yaml`, y el reporte registra con cual se
  calculo. Es una comparacion de cadenas contra el repositorio.

POR QUE SE RE-EMITE SOLO. Hasta el 13-sep-2026 esto informaba y una persona
decidia, porque re-emitir movia cifras que el README citaba a mano. Ese dia el
README dejo de publicar cifras, y un aviso que espera a que alguien lo lea es
justo lo que este proyecto intenta no tener. Lo unico que sigue pidiendo una
persona es el reporte cuyo producto **desaparecio** del detail: re-emitirlo no
lo arregla.
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
    def desaparecido(self) -> bool:
        """El producto con el que se calculo el reporte YA NO ESTA en el detail.

        `vigente = 0` frente a `publicado = 11` no es "todo al dia": es que el
        producto que sostiene once versiones de reporte no aparece en la
        respuesta de USGS. La comparacion era `vigente > publicado`, que con un
        cero no dispara nada y ademas cuenta el evento como revisado.

        Puede ser un retiro de USGS o una respuesta a medias, y las dos merecen
        que alguien mire: el reporte publicado cita una version que su fuente ya
        no reconoce.
        """
        return (self.shakemap_publicado > 0 and self.shakemap_vigente == 0) or (
            self.groundfailure_publicado > 0 and self.groundfailure_vigente == 0
        )

    @property
    def exposicion(self) -> bool:
        """El activo del pais se reconstruyo despues de calcularse el reporte."""
        return self.manifiesto_publicado != self.manifiesto_vigente

    @property
    def hay(self) -> bool:
        return self.productos or self.exposicion or self.desaparecido

    def describir(self) -> str:
        """Una linea legible. Es lo que acaba en el resumen y en el issue."""
        partes = []
        if self.shakemap_vigente > self.shakemap_publicado:
            partes.append(f"ShakeMap v{self.shakemap_publicado} -> v{self.shakemap_vigente}")
        if self.groundfailure_vigente > self.groundfailure_publicado:
            partes.append(
                f"Ground Failure v{self.groundfailure_publicado} -> v{self.groundfailure_vigente}"
            )
        if self.exposicion:
            partes.append(f"exposicion {self.manifiesto_publicado} -> {self.manifiesto_vigente}")
        if self.desaparecido:
            cual = "ShakeMap" if self.shakemap_vigente == 0 else "Ground Failure"
            partes.append(
                f"{cual} DESAPARECIO del detail: el reporte cita una version que USGS ya no sirve"
            )
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
    def a_reemitir(self) -> list[Rezago]:
        """Los que se arreglan corriendo P2 otra vez. `rezago.yml` los despacha solo.

        Da igual si lo atrasado es la ciencia —USGS reviso el ShakeMap o el Ground
        Failure— o la receta del activo: el remedio es el mismo. Hasta el
        13-sep-2026 se separaban en dos listas porque los de producto movian
        cifras que el README citaba a mano; el README ya no publica cifras.
        """
        return [r for r in self.rezagados if not r.desaparecido]

    @property
    def manuales(self) -> list[Rezago]:
        """Los que re-emitir no arregla: el producto que citan ya no esta en USGS.

        Re-emitir con un producto que USGS ya no sirve falla, o publica el reporte
        sin el. Es lo unico que queda para una persona, y lo unico que abre
        incidencia.
        """
        return [r for r in self.rezagados if r.desaparecido]


def _manifiesto_vigente(iso3: str, manifests_dir: Path | None) -> str | None:
    """El `manifest_id` que hoy tiene el pais en el repositorio.

    `None` cuando no se pudo leer, y no cadena vacia. La diferencia importa: el
    llamador hacia `manifiesto_vigente or manifiesto_publicado`, asi que un
    manifiesto ilegible se convertia en «el mismo que se publico» y el reporte
    salia **al dia**. Es la misma confusion que el propio modulo evita tres
    lineas mas abajo para los productos —«UN FALLO NO ES UN "AL DIA"»— y que
    aqui se colaba por un `or`.

    Un pais sin manifiesto es un problema real y no debe impedir comprobar los
    otros veinte reportes: por eso no propaga. Pero ese reporte no se cuenta
    como revisado, porque de el no se sabe nada.
    """
    try:
        return Manifest.load(iso3, manifests_dir or MANIFESTS_DIR).manifest_id
    except (FileNotFoundError, ValueError, KeyError) as error:
        _log.warning(
            "no se pudo leer el manifiesto vigente",
            extra={"context": {"iso3": iso3, "error": str(error)}},
        )
        return None


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

    No despacha nada: devuelve la lista y `rezago.yml` re-emite. Ver el
    docstring del modulo.
    """
    resultado = ResultadoRezago()

    for usgs_id, entradas in _reportes(reports_dir):
        manifiesto_publicado = str(entradas.get("exposure_manifest", ""))
        manifiesto_vigente = (
            _manifiesto_vigente(iso3_del_manifiesto(manifiesto_publicado), manifests_dir)
            if manifiesto_publicado
            else ""
        )
        if manifiesto_vigente is None:
            # No se pudo leer el manifiesto del pais: de este reporte no sabemos
            # si su activo se reconstruyo. Antes se sustituia por el publicado y
            # salia «al dia».
            resultado.fallidos.append(usgs_id)
            continue

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
            manifiesto_vigente=manifiesto_vigente,
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
