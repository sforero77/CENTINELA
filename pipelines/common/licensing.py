"""Regla de los tres cubos (§2.4) y su verificacion automatica.

La contaminacion de licencias es un riesgo de impacto alto en §7: una sola capa
NC filtrada al nucleo bloquearia el reuso de todo el dataset. Por eso la regla
no es una nota en el README sino un lint que corre en CI y falla el build.

* ``core`` — dominio publico + CC BY + reuso CE con atribucion.
* ``odbl`` — todo lo que toque OSM / Overture buildings / transportation.
* ``nc``   — no comercial (Vantor, GEM, derivados de xBD). Nunca en el reporte.

El reporte automatico consume ``core`` + ``odbl``. ``nc`` solo alimenta capas
de contexto del visor y la brigada de imagen.
"""

from __future__ import annotations

from collections.abc import Iterable
from enum import StrEnum
from typing import Final


class Bucket(StrEnum):
    """Cubo fisico de publicacion."""

    CORE = "core"
    ODBL = "odbl"
    NC = "nc"


class LicenseViolationError(Exception):
    """Se intento mezclar cubos incompatibles en un mismo artefacto."""


#: Identificadores de licencia aceptados y su cubo. La lista es cerrada a
#: proposito: una licencia desconocida en un manifest es un error, no un
#: default permisivo.
LICENSE_BUCKET: Final[dict[str, Bucket]] = {
    # core
    "public-domain-usgov": Bucket.CORE,
    "public-domain": Bucket.CORE,
    "CC0-1.0": Bucket.CORE,
    "CC-BY-4.0": Bucket.CORE,
    "EC-reuse-attribution": Bucket.CORE,  # JRC / GHSL, Copernicus EMS
    "CC-BY-IGO": Bucket.CORE,  # COD de OCHA/HDX: atribucion, sin share-alike ni NC
    "gov-open-co": Bucket.CORE,  # datos.gov.co sin licencia CC declarada
    # share-alike: redistribuibles, pero obligan a licenciar el derivado igual
    "ODbL-1.0": Bucket.ODBL,
    "CC-BY-SA-4.0": Bucket.ODBL,
    # nc (no redistribuible en el nucleo)
    "CC-BY-NC-4.0": Bucket.NC,
    "CC-BY-NC-SA-4.0": Bucket.NC,
}

#: Cubos que puede consumir el reporte automatico (§2.4 regla 1).
REPORT_ALLOWED_BUCKETS: Final[frozenset[Bucket]] = frozenset({Bucket.CORE, Bucket.ODBL})

#: Pares de licencias share-alike que **no** pueden convivir en un mismo
#: derivado. ODbL y CC BY-SA 4.0 son ambas copyleft y mutuamente incompatibles:
#: cada una exige que el derivado se publique bajo ella, y no existe una
#: licencia unica que satisfaga a las dos. Mezclarlas produce una tabla que
#: literalmente no se puede licenciar.
#:
#: Aparece en la practica: los datasets colombianos de salud (REPS) y educacion
#: (MEN) en datos.gov.co son CC BY-SA 4.0, mientras que las edificaciones y
#: vias de Overture son ODbL.
INCOMPATIBLE_SHARE_ALIKE: Final[frozenset[frozenset[str]]] = frozenset(
    {frozenset({"ODbL-1.0", "CC-BY-SA-4.0"})}
)


def bucket_for(license_id: str) -> Bucket:
    """Cubo al que pertenece una licencia.

    Raises:
        LicenseViolationError: si la licencia no esta en el registro. Agregar una
            licencia nueva es una decision consciente que pasa por PR.
    """
    try:
        return LICENSE_BUCKET[license_id]
    except KeyError:
        raise LicenseViolationError(
            f"Licencia no registrada: {license_id!r}. "
            f"Agregala a LICENSE_BUCKET con su cubo, o corrige el manifest."
        ) from None


def resolve_bucket(license_ids: Iterable[str]) -> Bucket:
    """Cubo resultante de combinar varias fuentes en un derivado.

    La combinacion es un "peor caso": basta una fuente NC para que el derivado
    entero sea NC, y basta una ODbL para que el derivado herede share-alike.
    """
    ids = set(license_ids)
    buckets = {bucket_for(lid) for lid in ids}
    if not buckets:
        raise LicenseViolationError("Un derivado debe declarar al menos una fuente.")

    for par in INCOMPATIBLE_SHARE_ALIKE:
        if par <= ids:
            raise LicenseViolationError(
                f"Licencias share-alike incompatibles en el mismo derivado: "
                f"{sorted(par)}. Cada una exige que el derivado se publique bajo "
                f"ella y no hay licencia que cumpla las dos. Separa las capas en "
                f"tablas distintas o descarta una de las fuentes."
            )

    if Bucket.NC in buckets:
        return Bucket.NC
    if Bucket.ODBL in buckets:
        return Bucket.ODBL
    return Bucket.CORE


def assert_publishable_in_report(license_ids: Iterable[str]) -> Bucket:
    """Valida que un conjunto de fuentes pueda alimentar el reporte automatico.

    Raises:
        LicenseViolationError: si alguna fuente es NC.
    """
    ids = list(license_ids)
    bucket = resolve_bucket(ids)
    if bucket not in REPORT_ALLOWED_BUCKETS:
        offenders = sorted(lid for lid in ids if bucket_for(lid) is Bucket.NC)
        raise LicenseViolationError(
            "El reporte automatico no puede consumir fuentes NC. "
            f"Fuentes en conflicto: {offenders}. Muevelas al cubo 'nc/' "
            "(visor/contexto/brigada) y quitalas del computo del reporte."
        )
    return bucket
