"""Un sismo que cumple los parámetros se publica aunque no alcance población.

EL PRIMER SISMO EN VIVO DEL SISTEMA, Y P2 FALLO SEIS VECES.

El 2-sep-2026 a las 12:28 UTC, un M5,6 a 71 km al OSO de Puerto Madero, México.
Dentro de LATAM, por encima del umbral. El vigia lo detecto y despacho —el
sistema funciono hasta ahi— y P2 se nego a publicarlo:

    candidatos por epicentro: MEX
    el activo de MEX no alcanza ninguna celda; se prueba el siguiente
    ##[error] Ningun activo sirvio para us7000tdmp

El enrutado habia **acertado**: MEX era el pais correcto. Lo que pasaba es que
el contorno MMI≥5 de un M5,6 a 71 km mar adentro se queda sobre el agua.

CERO CELDAS SIGNIFICA DOS COSAS DISTINTAS, y compartian excepcion:

- **Pais equivocado**: hay que reintentar con el siguiente candidato. Publicar
  ahi seria decir "no hay nadie expuesto" durante un terremoto real.
- **Pais correcto y la sacudida no llego a tierra**: eso es el **resultado**, y
  hay que publicarlo. El ShakeMap se revisa —el de Venezuela llego a v15— y la
  version siguiente puede alcanzar poblacion. Solo se seguira mirando si el
  evento esta en el catalogo: descartarlo es dejar de mirar.

Desde dentro de `compute_impact` no se distinguen. Quien lo sabe es el llamador,
que es el que ha agotado los candidatos — y por eso lo decide un parametro y no
una heuristica.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import duckdb
import pytest

from pipelines.p2_impact.pipeline import ExposureCountryMismatchError, compute_impact


class _ProductosFalsos:
    """Lo justo que `compute_impact` le pide a un `ProductSet`."""

    usgs_id = "us7000tdmp"
    shakemap_version = 2
    groundfailure_version = 0


def _contornos_lejos(tmp_path: Path) -> Path:
    """Un contorno MMI 6 en mitad del Pacifico, sin una celda debajo."""
    ruta = tmp_path / "cont_mmi.json"
    ruta.write_text(
        # MultiLineString, que es lo que publica USGS: `MmiContour.rings`
        # recorre `coordinates` esperando una lista de lineas, no de puntos.
        '{"type":"FeatureCollection","features":[{"type":"Feature",'
        '"properties":{"type":"mmi","value":6.0},'
        '"geometry":{"type":"MultiLineString","coordinates":[['
        "[-140.0,-30.0],[-139.0,-30.0],[-139.0,-29.0],[-140.0,-29.0],[-140.0,-30.0]]]}}]}",
        encoding="utf-8",
    )
    return ruta


def _activo(tmp_path: Path) -> str:
    """Un activo minimo con una celda en tierra firme, lejos del contorno."""
    import h3

    ruta = tmp_path / "exposure_h3.parquet"
    celda = h3.str_to_int(h3.latlng_to_cell(4.6, -74.1, 8))
    con = duckdb.connect()
    con.execute(
        f"""
        COPY (SELECT {celda}::BIGINT AS h3_08, 'COL' AS iso3, 'CO11' AS adm1_id,
                     'CO11001' AS adm2_id, 100.0 AS pop_total, 10.0 AS pop_0_14,
                     70.0 AS pop_15_64, 20.0 AS pop_65p, 90.0 AS pop_alt_worldpop,
                     5.0 AS bld_count, 500.0 AS bld_area_m2, 400.0 AS built_m2,
                     1::BIGINT AS health_count, 1::BIGINT AS edu_count,
                     1.0 AS road_km_primary, 1.0 AS road_km_secondary,
                     1.0 AS road_km_other, '' AS flags_calidad,
                     'col-v0.6' AS src_manifest)
        TO '{ruta.as_posix()}' (FORMAT PARQUET)
        """
    )
    return ruta.as_posix()


def _correr(tmp_path: Path, *, aunque_no_alcance: bool) -> Any:
    con = duckdb.connect()
    return compute_impact(
        con,
        _ProductosFalsos(),  # type: ignore[arg-type]
        exposure_glob=_activo(tmp_path),
        contornos=_contornos_lejos(tmp_path),
        deslizamiento=None,
        licuefaccion=None,
        aunque_no_alcance=aunque_no_alcance,
    )


def test_sin_el_permiso_sigue_elevando(tmp_path: Path) -> None:
    """El caso del país equivocado no se toca: tiene que seguir reintentando.

    Publicar ahí diría "no hay nadie expuesto" durante un terremoto real, en el
    visor público, y es lo que este `raise` existe para impedir.
    """
    with pytest.raises(ExposureCountryMismatchError):
        _correr(tmp_path, aunque_no_alcance=False)


def test_con_el_permiso_publica_ceros(tmp_path: Path) -> None:
    """Agotados los candidatos, el país es el correcto y el cero es la respuesta."""
    totales = _correr(tmp_path, aunque_no_alcance=True)

    assert totales.pop_mmi6p == 0.0
    assert totales.pop_mmi7p == 0.0


def test_el_cero_no_se_confunde_con_una_medicion(tmp_path: Path) -> None:
    """La discrepancia queda **nula**, no en cero.

    Es la misma distinción que se arregló para los tres reportes que publicaban
    "0,0 %": sin celdas no hay con qué comparar GHS-POP y WorldPop, y decir que
    coinciden perfectamente sería lo contrario de la verdad.
    """
    totales = _correr(tmp_path, aunque_no_alcance=True)

    assert totales.discrepancia_pct is None
