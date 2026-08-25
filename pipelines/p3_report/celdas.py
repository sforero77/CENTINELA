"""``celdas.json``: la malla del evento, para que el visor dibuje el dato real.

El pipeline calcula `impact_h3` —una fila por celda H3 r8 con poblacion,
edificaciones, superficie construida, vias, equipamiento e intensidad—, lo
agrega a municipio y **tira la malla**. El visor acababa dibujando un circulo
por municipio: 297 puntos en centroides cuando debajo hay cientos de miles de
hexagonos con el dato medido donde esta.

Aqui se publica esa malla, con dos decisiones que la hacen viable en un
navegador.

**Se agrega a r7.** Una celda r7 son unos 5,2 km², siete veces una r8. A la
escala a la que alguien mira un evento —una region en mil pixeles— r8 es mas
resolucion de la que la pantalla puede mostrar, y pesa siete veces mas. La
resolucion de computo sigue siendo r8: esto es solo lo que se dibuja.

**Viajan los indices, no las geometrias.** El contorno de un hexagono en GeoJSON
son siete pares de coordenadas, unos 150 bytes; su indice H3 son quince
caracteres. El navegador reconstruye la geometria desde el indice con `h3-js`,
que es exactamente para lo que sirve un sistema de indice jerarquico.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..common.logging import get_logger

_log = get_logger(__name__)

#: Resolucion a la que se publica la malla. Ver el modulo.
RES_VISOR = 7

#: Umbral de intensidad por debajo del cual la celda no se publica.
#:
#: El reporte no dice nada de MMI < 6 y dibujarlo llenaria el mapa de celdas
#: sobre las que el sistema no se pronuncia — que es justo la lectura que hay
#: que evitar: color en el mapa se lee como "aqui pasa algo".
MMI_MINIMO = 6.0

#: Columnas que viajan, en orden. Son las que el visor sabe pintar.
COLUMNAS = ("h3", "mmi", "pop", "bld", "built_m2", "vias_km", "salud", "edu")

SQL_CELDAS = """
SELECT
    h3_h3_to_string(h3_cell_to_parent(h3_08, {resolucion})) AS h3,
    round(max(mmi_max), 1)                                  AS mmi,
    round(sum(pop_total))                                   AS pop,
    round(sum(bld_count))                                   AS bld,
    round(sum(built_m2))                                    AS built_m2,
    round(sum(road_km_primary + road_km_secondary + road_km_other), 1) AS vias_km,
    round(sum(health_count))                                AS salud,
    round(sum(edu_count))                                   AS edu
FROM impact_h3
WHERE mmi_max >= {mmi_minimo}
GROUP BY 1
ORDER BY 2 DESC
"""


def write_cells_json(
    con: Any,
    destino: Path,
    *,
    resolucion: int = RES_VISOR,
    mmi_minimo: float = MMI_MINIMO,
) -> Path:
    """Escribe la malla del evento agregada para el visor.

    Se emite como lista de listas y no como objetos: repetir ocho nombres de
    campo en cada una de decenas de miles de celdas triplica el fichero sin
    anadir nada que el visor no sepa ya.
    """
    filas = con.execute(SQL_CELDAS.format(resolucion=resolucion, mmi_minimo=mmi_minimo)).fetchall()

    datos = {
        "resolucion": resolucion,
        "mmi_minimo": mmi_minimo,
        "columnas": list(COLUMNAS),
        "celdas": [[fila[0]] + [_numero(v) for v in fila[1:]] for fila in filas],
    }
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(datos, separators=(",", ":")), encoding="utf-8")
    _log.info(
        "malla del evento escrita",
        extra={
            "context": {
                "destino": str(destino),
                "celdas": len(filas),
                "resolucion": resolucion,
                "kb": round(destino.stat().st_size / 1024),
            }
        },
    )
    return destino


def _numero(valor: Any) -> float | int:
    """Entero cuando lo es: `1234.0` ocupa dos caracteres mas que `1234`."""
    numero = float(valor or 0.0)
    return int(numero) if numero.is_integer() else numero
