"""Reajuste de la tolerancia de un manifest con lo que midio el ultimo build.

El assert de §6.4 compara el total nacional del activo contra una referencia
oficial y falla si se sale de ``tolerancia_pct``. Esa tolerancia es el unico
guardian contra que la poblacion de un pais se mueva sin que nadie se entere,
y **solo vale lo estrecha que sea**: Paraguay la tenia en 7,5 % para acomodar
un desvio de +6,59 % que resulto ser un fallo del rescate de frontera. Corregido
el rescate, el desvio real es +0,035 % y 7,5 % ya no vigila absolutamente nada.

De ahi la regla de este modulo: **estrechar es automatico, ensanchar no.**

Estrechar solo puede mejorar la vigilancia, asi que se hace sin preguntar.
Ensanchar es aflojar la alarma para que deje de sonar, que es justo lo que uno
hace cuando tiene prisa y justo lo que no debe automatizarse. Si el desvio
medido supera la tolerancia vigente, esto lo dice y no toca nada: alguien tiene
que decidir si el pais cambio, si la fuente cambio, o si hay un fallo.

Las cifras vienen de ``medicion.json``, que el build publica junto al activo en
el Release. No se leen del log: copiar tres numeros de un log de varios MB a
mano es como se desincronizan las cosas.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..common.logging import get_logger

_log = get_logger(__name__)

#: Margen que se deja sobre el desvio medido al proponer una tolerancia, en
#: puntos porcentuales. Un pais no reproduce su cifra al milimetro entre
#: vintages —GHS-POP interpola, el COD-AB se re-publica— y una tolerancia
#: pegada al valor medido fallaria en el proximo build por ruido.
MARGEN_PUNTOS = 0.5

#: Suelo de la tolerancia. Por debajo de esto el assert se vuelve un generador
#: de falsos positivos, no un guardian.
TOLERANCIA_MINIMA = 0.5


@dataclass(frozen=True, slots=True)
class Calibracion:
    """Lo que se propone cambiar en un manifest, y por que."""

    iso3: str
    medido: float
    referencia: float
    desvio_pct: float
    tolerancia_vigente: float
    tolerancia_propuesta: float
    #: Vacio si no hay nada que impida escribirla.
    motivo_bloqueo: str = ""

    @property
    def estrecha(self) -> bool:
        return self.tolerancia_propuesta < self.tolerancia_vigente

    @property
    def aplicable(self) -> bool:
        return not self.motivo_bloqueo and self.estrecha


def tolerancia_propuesta(desvio_pct: float) -> float:
    """Tolerancia que corresponde a un desvio medido."""
    return max(round(abs(desvio_pct) + MARGEN_PUNTOS, 2), TOLERANCIA_MINIMA)


def calibrar(medicion: dict[str, Any], referencia_manifest: dict[str, Any]) -> Calibracion:
    """Compara lo medido con lo que declara el manifest."""
    iso3 = str(medicion.get("iso3", "???"))
    ref = medicion.get("referencia") or {}
    if not ref:
        return Calibracion(
            iso3=iso3,
            medido=float(medicion.get("resumen", {}).get("pop_total") or 0.0),
            referencia=0.0,
            desvio_pct=0.0,
            tolerancia_vigente=float(referencia_manifest.get("tolerancia_pct", 0.0)),
            tolerancia_propuesta=0.0,
            motivo_bloqueo="la medicion no trae referencia oficial",
        )

    desvio = float(ref["desvio_pct"])
    vigente = float(referencia_manifest.get("tolerancia_pct", 0.0))
    propuesta = tolerancia_propuesta(desvio)
    bloqueo = ""
    if abs(desvio) > vigente > 0:
        bloqueo = (
            f"el desvio medido ({desvio:+.3f} %) ya se sale de la tolerancia "
            f"vigente ({vigente} %). Ensanchar es aflojar la alarma: decidelo a mano."
        )
    elif propuesta > vigente > 0:
        bloqueo = (
            f"la tolerancia propuesta ({propuesta} %) ensancha la vigente "
            f"({vigente} %). Solo se estrecha automaticamente."
        )
    return Calibracion(
        iso3=iso3,
        medido=float(medicion["resumen"]["pop_total"]),
        referencia=float(ref["poblacion"]),
        desvio_pct=desvio,
        tolerancia_vigente=vigente,
        tolerancia_propuesta=propuesta,
        motivo_bloqueo=bloqueo,
    )


#: Se edita el YAML linea a linea y no se re-serializa a proposito: los
#: manifests llevan mas comentario que dato —de donde sale cada fuente, por que
#: ese vintage, que se midio y cuando— y un `yaml.dump` los borraria todos.
_TOLERANCIA = re.compile(r"^(?P<sangria>\s*)tolerancia_pct:\s*(?P<valor>[\d.]+)\s*$")
_MEDIDO = re.compile(r"^(?P<sangria>\s*)medido_ghs_pop:\s*(?P<valor>[\d]+)\s*$")


def aplicar(ruta: Path, cal: Calibracion, *, fecha: str) -> bool:
    """Escribe la calibracion en el manifest. Devuelve si cambio algo."""
    lineas = ruta.read_text(encoding="utf-8").split("\n")
    cambiado = False
    for i, linea in enumerate(lineas):
        if m := _MEDIDO.match(linea):
            nueva = f"{m['sangria']}medido_ghs_pop: {round(cal.medido)}"
            cambiado = cambiado or nueva != linea
            lineas[i] = nueva
        elif cal.aplicable and (m := _TOLERANCIA.match(linea)):
            nueva = f"{m['sangria']}tolerancia_pct: {cal.tolerancia_propuesta}"
            cambiado = cambiado or nueva != linea
            lineas[i] = nueva
    if cambiado:
        ruta.write_text("\n".join(lineas), encoding="utf-8")
        _log.info(
            "manifest recalibrado",
            extra={
                "context": {
                    "iso3": cal.iso3,
                    "fecha": fecha,
                    "medido": round(cal.medido),
                    "desvio_pct": cal.desvio_pct,
                    "tolerancia": cal.tolerancia_propuesta if cal.aplicable else "sin tocar",
                }
            },
        )
    return cambiado


def leer_medicion(ruta: Path) -> dict[str, Any]:
    """Carga un ``medicion.json`` publicado junto a un activo."""
    datos: dict[str, Any] = json.loads(ruta.read_text(encoding="utf-8"))
    return datos
