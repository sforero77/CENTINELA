"""``adm2.csv``: la tabla municipal, con cabeceras HXL (T1.3).

Cifras **exactas** aqui, a diferencia de la prosa del markdown (RF-06). La
segunda fila lleva las etiquetas HXL que espera HDX; los lectores de CSV
corrientes la ven como una fila mas, los humanitarios la usan para mapear
columnas automaticamente.
"""

from __future__ import annotations

import csv
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

#: Columna -> etiqueta HXL. El orden define el orden del CSV.
HXL_HEADERS: dict[str, str] = {
    "usgs_id": "#meta+id+event",
    "shakemap_version": "#meta+version",
    "adm2_id": "#adm2+code",
    "nombre": "#adm2+name",
    "mmi_max": "#indicator+mmi+max",
    "pop_mmi6p": "#population+mmi6",
    "pop_mmi7p": "#population+mmi7",
    "pop_mmi8p": "#population+mmi8",
    "pop_65p_mmi7p": "#population+age65+mmi7",
    "bld_mmi7p": "#infra+buildings+mmi7",
    "health_mmi7p": "#infra+health+mmi7",
    "edu_mmi7p": "#infra+education+mmi7",
    "road_km_mmi7p": "#infra+roads+km+mmi7",
    "ls_pop_expuesta": "#population+landslide",
    "lq_pop_expuesta": "#population+liquefaction",
    "flags_calidad": "#meta+flags",
}


def write_adm2_csv(rows: Iterable[Mapping[str, Any]], path: Path) -> Path:
    """Escribe el CSV municipal con cabecera HXL."""
    path.parent.mkdir(parents=True, exist_ok=True)
    columnas = list(HXL_HEADERS)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=columnas, extrasaction="ignore")
        writer.writeheader()
        writer.writerow(HXL_HEADERS)
        for row in rows:
            writer.writerow({col: row.get(col, "") for col in columnas})
    return path
