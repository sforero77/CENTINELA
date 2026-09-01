"""Lectura del objeto ``products`` del feed *detail* de USGS (§2.1).

El feed detail es la puerta unica a todos los productos aportados de un evento:
``shakemap``, ``ground-failure``, ``losspager``, ``origin``, ``dyfi``... Cada
producto esta **versionado**, y esa version es el eje de idempotencia de todo
P2: un evento acumula ShakeMap v1, v2, v3... y el sistema debe re-emitir el
reporte al detectar una nueva (RF-04).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Self

#: Nombres de producto que consume el sistema.
SHAKEMAP = "shakemap"
GROUND_FAILURE = "ground-failure"
LOSSPAGER = "losspager"


class ProductContractError(Exception):
    """El feed detail no cumple el contrato esperado (RNF-03)."""


@dataclass(frozen=True, slots=True)
class ProductRef:
    """Una version concreta de un producto aportado."""

    tipo: str
    version: int
    #: ``updateTime`` del producto, epoch ms segun USGS.
    actualizado_ms: int
    #: Mapa ruta-de-contenido -> URL descargable.
    contents: dict[str, str]
    estado: str = "UPDATE"
    #: Propiedades planas del producto, tal como las publica USGS.
    props: dict[str, str] = field(default_factory=dict)

    def content_url(self, *candidates: str) -> str | None:
        """Primera URL disponible entre varias rutas candidatas.

        USGS ha movido nombres de contenido entre versiones de ShakeMap; pedir
        varias alternativas evita que un renombre tumbe el pipeline.
        """
        for key in candidates:
            if key in self.contents:
                return self.contents[key]
        return None

    @classmethod
    def from_dict(cls, tipo: str, data: dict[str, Any]) -> Self:
        props = data.get("properties") or {}
        raw_version = props.get("version", data.get("version", 0))
        try:
            version = int(str(raw_version).split(".")[0])
        except (TypeError, ValueError):
            version = 0
        contents = {
            str(key): str(value["url"])
            for key, value in (data.get("contents") or {}).items()
            if isinstance(value, dict) and "url" in value
        }
        return cls(
            tipo=tipo,
            version=version,
            actualizado_ms=int(data.get("updateTime", 0) or 0),
            contents=contents,
            estado=str(data.get("status", "UPDATE")).upper(),
            props={str(k): str(v) for k, v in props.items() if v is not None},
        )


@dataclass(frozen=True, slots=True)
class ProductSet:
    """Los productos relevantes de un evento, ya resueltos a su version preferida."""

    usgs_id: str
    shakemap: ProductRef | None
    ground_failure: ProductRef | None
    losspager: ProductRef | None

    @property
    def shakemap_version(self) -> int:
        return self.shakemap.version if self.shakemap else 0

    @property
    def groundfailure_version(self) -> int:
        return self.ground_failure.version if self.ground_failure else 0

    @property
    def has_shakemap(self) -> bool:
        """Sin ShakeMap el reporte es preliminar por radios (RF-03)."""
        return self.shakemap is not None

    def cont_mmi_url(self) -> str | None:
        """GeoJSON de contornos de intensidad, insumo del polyfill H3."""
        if self.shakemap is None:
            return None
        return self.shakemap.content_url(
            "download/cont_mmi.json",
            "download/cont_mmi.json.zip",
            "download/contours.json",
        )

    def ground_failure_alerts(self) -> dict[str, str]:
        """Alertas del propio USGS para el producto Ground Failure.

        Se publican como **referencia cruzada**, por la misma razon que el nivel
        PAGER: son la cifra de otro, no la nuestra. Y aqui hacen ademas un
        trabajo concreto.

        CENTINELA cuenta la poblacion de toda celda cuyo valor supera el umbral;
        USGS pondera la poblacion por el valor de la celda. Son dos preguntas
        distintas y dan dos numeros distintos —para el Choco, 1,6 millones
        contra ~460 mil en licuefaccion—, asi que publicar el nuestro sin el
        suyo al lado invita a leer uno como si fuera el otro.

        Y resuelven el caso peor: un conteo por umbral que da **0** junto a una
        alerta naranja de USGS. El cero es cierto —ninguna celda llega al
        umbral— y se lee como "no hay exposicion a deslizamiento", que en un
        M7,4 sobre cordillera es falso. Con la alerta al lado, no.
        """
        if self.ground_failure is None:
            return {}
        props = self.ground_failure.props
        alertas = {
            "ls_alerta_usgs": props.get("landslide-alert", ""),
            "ls_pop_usgs": props.get("landslide-population-alert-value", ""),
            "lq_alerta_usgs": props.get("liquefaction-alert", ""),
            "lq_pop_usgs": props.get("liquefaction-population-alert-value", ""),
        }
        return {k: v for k, v in alertas.items() if v}

    def pager_alert(self) -> str:
        """Nivel de alerta PAGER (``green``/``yellow``/``orange``/``red``).

        Se publica **solo como referencia cruzada** ("PAGER estima: alerta X").
        Nunca como cifra propia: la estimacion de victimas es un no-objetivo
        explicito del sistema (§1.2).
        """
        if self.losspager is None:
            return ""
        return self.losspager.props.get("alertlevel", "")


def _preferred(entries: list[dict[str, Any]], tipo: str) -> ProductRef | None:
    """Elige la version vigente de un producto.

    USGS entrega una lista por tipo de producto que mezcla dos ejes distintos:
    **contribuidores** (``us``, ``atlas``, una red regional) y **versiones** de
    cada contribuidor. ``preferredWeight`` desempata el primer eje, no el
    segundo, y usarlo para lo segundo da respuestas obsoletas.

    No es teoria. En el evento de Venezuela ``us6000t7zp``, con
    ``includesuperseded=true``, las versiones v1-v4 de junio pesan **232** y la
    vigente v14 de agosto pesa **228**. Ordenar por peso elige un ShakeMap de
    hace mes y medio y el reporte saldria con cifras equivocadas sin que nada
    falle. Lo cazaron las fixtures golden.

    Criterio correcto, en este orden:

    1. Descartar ``status=DELETE``.
    2. Elegir **contribuidor** por su mayor ``preferredWeight`` — para eso
       existe el campo.
    3. Dentro de ese contribuidor, elegir la entrada mas reciente por
       ``updateTime``, desempatando por numero de version.
    """
    vivos = [e for e in entries if str(e.get("status", "UPDATE")).upper() != "DELETE"]
    if not vivos:
        return None

    def peso(e: dict[str, Any]) -> int:
        return int(e.get("preferredWeight", 0) or 0)

    def actualizado(e: dict[str, Any]) -> int:
        return int(e.get("updateTime", 0) or 0)

    def version(e: dict[str, Any]) -> int:
        return ProductRef.from_dict(tipo, e).version

    # Paso 2: el contribuidor cuyo mejor producto pesa mas.
    mejor_peso_por_fuente: dict[str, int] = {}
    for e in vivos:
        fuente = str(e.get("source", "us"))
        mejor_peso_por_fuente[fuente] = max(mejor_peso_por_fuente.get(fuente, 0), peso(e))
    fuente_elegida = max(mejor_peso_por_fuente, key=lambda f: (mejor_peso_por_fuente[f], f))

    # Paso 3: dentro del contribuidor, la mas reciente.
    del_contribuidor = [e for e in vivos if str(e.get("source", "us")) == fuente_elegida]
    best = max(del_contribuidor, key=lambda e: (actualizado(e), version(e)))
    return ProductRef.from_dict(tipo, best)


def parse_products(detail: dict[str, Any]) -> ProductSet:
    """Extrae los productos de interes del GeoJSON detail de un evento."""
    try:
        usgs_id = str(detail["id"])
        products: dict[str, Any] = detail["properties"]["products"]
    except (KeyError, TypeError) as exc:
        raise ProductContractError(f"Feed detail sin 'properties.products': {exc}") from exc
    if not isinstance(products, dict):
        raise ProductContractError("'products' no es un objeto")

    def pick(tipo: str) -> ProductRef | None:
        entries = products.get(tipo)
        if not isinstance(entries, list) or not entries:
            return None
        return _preferred(entries, tipo)

    return ProductSet(
        usgs_id=usgs_id,
        shakemap=pick(SHAKEMAP),
        ground_failure=pick(GROUND_FAILURE),
        losspager=pick(LOSSPAGER),
    )
