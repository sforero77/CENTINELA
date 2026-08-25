"""Cobertura regional: que paises puede atender el sistema, y con que.

El visor listaba eventos y nada mas. Con tres reportes publicados eso se lee
como una demo, y lo que hay detras no lo es: **dieciocho paises con su activo
de exposicion construido, medido contra la cifra oficial de su instituto o de
la ONU, y publicado**. Ese hecho no aparecia en ninguna pantalla.

Importa que se vea porque es lo que responde la pregunta que se hace quien
llega: *¿esto sirve para mi pais?* Un tablero con tres eventos de dos paises
sugiere que no. La respuesta real es que si, para dieciocho.

**La fuente es el manifest, no un listado aparte.** Un pais construido tiene
`medido_ghs_pop` anotado por su build; uno sin construir, no. Asi la cobertura
no puede afirmar mas de lo que el sistema hizo — que es justo el error que
convierte un tablero en un folleto.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .logging import get_logger
from .manifest import Manifest
from .paths import MANIFESTS_DIR, SITE_DIR
from .state import utcnow_iso

_log = get_logger(__name__)

COBERTURA_FILENAME = "cobertura.json"

#: Nombre en espanol de cada pais cubierto. El visor esta en espanol y "PRY" no
#: es un nombre: es un codigo. Van con tilde porque es texto para leer, no un
#: identificador — la regla del proyecto es que el dominio se escribe bien.
NOMBRE_PAIS: dict[str, str] = {
    "ARG": "Argentina",
    "BOL": "Bolivia",
    "BRA": "Brasil",
    "CHL": "Chile",
    "COL": "Colombia",
    "CRI": "Costa Rica",
    "CUB": "Cuba",
    "DOM": "República Dominicana",
    "ECU": "Ecuador",
    "GTM": "Guatemala",
    "HND": "Honduras",
    "MEX": "México",
    "NIC": "Nicaragua",
    "PAN": "Panamá",
    "PER": "Perú",
    "PRY": "Paraguay",
    "SLV": "El Salvador",
    "URY": "Uruguay",
    "VEN": "Venezuela",
}


@dataclass(frozen=True, slots=True)
class PaisCubierto:
    """Estado de un pais dentro del sistema."""

    iso3: str
    nombre: str
    #: Hay activo construido y medido. Lo delata `medido_ghs_pop` en el
    #: manifest, que solo escribe un build de verdad.
    construido: bool
    manifest_id: str
    #: Poblacion que el activo mide. Cero si no se ha construido.
    poblacion_medida: int = 0
    #: Cifra oficial contra la que se compara.
    poblacion_referencia: int = 0
    fuente_referencia: str = ""
    #: Desvio de lo medido frente a la referencia, en puntos porcentuales.
    desvio_pct: float | None = None
    #: Margen que el manifest tolera antes de detener el build.
    tolerancia_pct: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _desvio(medido: int, referencia: int) -> float | None:
    if not medido or not referencia:
        return None
    return round(100.0 * (medido - referencia) / referencia, 2)


def leer_cobertura(manifests_dir: Path | None = None) -> list[PaisCubierto]:
    """Estado de cada pais con manifest, ordenado por nombre.

    Un manifest ilegible no puede ocultar a los demas: se registra y se sigue.
    """
    base = manifests_dir or MANIFESTS_DIR
    paises: list[PaisCubierto] = []

    for ruta in sorted(base.glob("*.yaml")):
        iso3 = ruta.stem.upper()
        try:
            manifest = Manifest.load(iso3, base)
        except (OSError, ValueError, KeyError) as exc:
            _log.warning(
                "manifest ilegible, excluido de la cobertura",
                extra={"context": {"iso3": iso3, "error": str(exc)}},
            )
            continue

        ref = manifest.referencia_oficial
        medido = int(ref.get("medido_ghs_pop") or 0)
        referencia = int(ref.get("poblacion_2025") or 0)
        paises.append(
            PaisCubierto(
                iso3=iso3,
                nombre=NOMBRE_PAIS.get(iso3, iso3),
                construido=bool(medido),
                manifest_id=manifest.manifest_id,
                poblacion_medida=medido,
                poblacion_referencia=referencia,
                fuente_referencia=str(ref.get("fuente") or ""),
                desvio_pct=_desvio(medido, referencia),
                tolerancia_pct=float(ref.get("tolerancia_pct") or 0.0),
            )
        )

    return sorted(paises, key=lambda p: p.nombre)


def build_cobertura(manifests_dir: Path | None = None) -> dict[str, Any]:
    """Documento de cobertura que consume el visor."""
    paises = leer_cobertura(manifests_dir)
    construidos = [p for p in paises if p.construido]

    return {
        "generado_utc": utcnow_iso(),
        "resumen": {
            "paises_con_manifest": len(paises),
            "paises_construidos": len(construidos),
            "poblacion_en_la_malla": sum(p.poblacion_medida for p in construidos),
            # El peor desvio absoluto es la cifra honesta a publicar: decir
            # "todos dentro de tolerancia" sin decir cuanto es no informa nada.
            "peor_desvio_pct": max(
                (abs(p.desvio_pct) for p in construidos if p.desvio_pct is not None),
                default=None,
            ),
        },
        "paises": [p.to_dict() for p in paises],
    }


def write_cobertura(*, manifests_dir: Path | None = None, site_dir: Path | None = None) -> Path:
    """Escribe ``site/cobertura.json``."""
    destino = (site_dir or SITE_DIR) / COBERTURA_FILENAME
    datos = build_cobertura(manifests_dir)
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(datos, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _log.info("cobertura publicada", extra={"context": datos["resumen"]})
    return destino
