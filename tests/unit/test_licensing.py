"""Regla de los tres cubos (§2.4). Es un lint, no una nota en el README."""

from __future__ import annotations

import re

import pytest

from pipelines.common.licensing import (
    Bucket,
    LicenseViolationError,
    assert_publishable_in_report,
    bucket_for,
    resolve_bucket,
)


@pytest.mark.parametrize(
    ("licencia", "cubo"),
    [
        ("public-domain-usgov", Bucket.CORE),
        ("CC-BY-4.0", Bucket.CORE),
        ("EC-reuse-attribution", Bucket.CORE),
        ("ODbL-1.0", Bucket.ODBL),
        ("CC-BY-NC-4.0", Bucket.NC),
        ("CC-BY-NC-SA-4.0", Bucket.NC),
    ],
)
def test_mapa_licencia_a_cubo(licencia: str, cubo: Bucket) -> None:
    assert bucket_for(licencia) is cubo


def test_licencia_desconocida_no_recibe_default_permisivo() -> None:
    with pytest.raises(LicenseViolationError, match="no registrada"):
        bucket_for("WTFPL")


def test_odbl_contagia_share_alike() -> None:
    assert resolve_bucket(["public-domain-usgov", "CC-BY-4.0", "ODbL-1.0"]) is Bucket.ODBL


def test_nc_contamina_todo_el_derivado() -> None:
    assert resolve_bucket(["CC-BY-4.0", "ODbL-1.0", "CC-BY-NC-SA-4.0"]) is Bucket.NC


def test_derivado_sin_fuentes_es_error() -> None:
    with pytest.raises(LicenseViolationError, match="al menos una fuente"):
        resolve_bucket([])


def test_el_reporte_admite_core_y_odbl() -> None:
    assert assert_publishable_in_report(["public-domain-usgov", "ODbL-1.0"]) is Bucket.ODBL


def test_el_reporte_rechaza_nc_y_nombra_al_culpable() -> None:
    """GEM y xBD son NC: si se cuelan, el dataset entero deja de ser reusable."""
    with pytest.raises(LicenseViolationError, match=re.escape("CC-BY-NC-SA-4.0")):
        assert_publishable_in_report(["CC-BY-4.0", "CC-BY-NC-SA-4.0"])


def test_odbl_y_cc_by_sa_no_pueden_convivir() -> None:
    """Dos copyleft distintos en un derivado producen una tabla inlicenciable.

    No es hipotetico: REPS y MEN (datos.gov.co) son CC BY-SA 4.0 y las
    edificaciones de Overture son ODbL.
    """
    with pytest.raises(LicenseViolationError, match="incompatibles"):
        resolve_bucket(["ODbL-1.0", "CC-BY-SA-4.0"])


def test_cc_by_sa_sola_es_share_alike_valido() -> None:
    assert resolve_bucket(["CC-BY-4.0", "CC-BY-SA-4.0"]) is Bucket.ODBL
