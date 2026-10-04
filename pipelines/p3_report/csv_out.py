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
    # Centroide del municipio. Sin esto la tabla no se puede pintar en un mapa
    # sin cruzarla antes contra otra fuente, que es justo la friccion que hace
    # que un CSV humanitario se quede sin usar.
    "lon": "#geo+lon",
    "lat": "#geo+lat",
    "mmi_max": "#indicator+mmi+max",
    "pop_mmi6p": "#population+mmi6",
    "pop_mmi7p": "#population+mmi7",
    "pop_mmi8p": "#population+mmi8",
    "pop_65p_mmi7p": "#population+age65+mmi7",
    # La banda 6 del equipamiento. Trece de veintitres eventos no llegan a
    # MMI>=7, y para ellos estas son las unicas columnas con dato. Ver
    # «Bandas de intensidad publicadas» en `common/constants.py`.
    "pop_65p_mmi6p": "#population+age65+mmi6",
    "bld_mmi6p": "#infra+buildings+mmi6",
    "built_m2_mmi6p": "#infra+built+area+mmi6",
    "health_mmi6p": "#infra+health+mmi6",
    "edu_mmi6p": "#infra+education+mmi6",
    "road_km_mmi6p": "#infra+roads+km+mmi6",
    "road_km_principal_mmi6p": "#infra+roads+km+primary+mmi6",
    "bld_mmi7p": "#infra+buildings+mmi7",
    "built_m2_mmi7p": "#infra+built+area+mmi7",
    "health_mmi7p": "#infra+health+mmi7",
    "edu_mmi7p": "#infra+education+mmi7",
    "road_km_mmi7p": "#infra+roads+km+mmi7",
    "road_km_principal_mmi7p": "#infra+roads+km+primary+mmi7",
    # El sufijo `_mmi6p` no es cosmetico: dice sobre que celdas se contaron.
    # Sin el, esta columna sumaba sobre TODA `impact_h3` —que arranca en MMI
    # 5,0— mientras la cifra nacional del `report.json` sumaba solo desde MMI 6,
    # y las dos salian positivas y del orden correcto. Quien bajaba el CSV y lo
    # contrastaba contra la cifra nacional encontraba una diferencia que nadie
    # sabia explicar. Ahora el conjunto es el mismo y el nombre lo declara.
    "ls_pop_expuesta_mmi6p": "#population+landslide+mmi6",
    "lq_pop_expuesta_mmi6p": "#population+liquefaction+mmi6",
    "flags_calidad": "#meta+flags",
}


#: Lo que puede llegar en una fila y **a proposito** no se publica. Las filas
#: que recibe el paquete del reporte las comparten el CSV y el mapa estatico, y
#: `static_map._coordenada` aun sabe leer el centroide en WKT de las filas
#: antiguas; el CSV lo publica descompuesto en `lon` y `lat`. Cualquier otra
#: columna desconocida es una que alguien quiso publicar y no llego.
NO_PUBLICADAS: frozenset[str] = frozenset({"centroide"})


def write_adm2_csv(rows: Iterable[Mapping[str, Any]], path: Path) -> Path:
    """Escribe el CSV municipal con cabecera HXL.

    Raises:
        ValueError: si una fila trae una columna que `HXL_HEADERS` no publica.
            Se comprueba antes de abrir el fichero, para no dejarlo a medias.

    UNA COLUMNA QUE NO ESTA AQUI NO SE PUBLICA, Y ESO NO PUEDE PASAR CALLADO.
    Hasta el 3-oct-2026 el escritor usaba `extrasaction="ignore"`: una
    agregacion nueva en `SQL_IMPACT_ADM2`, o una renombrada, llegaba hasta aqui
    y desaparecia del fichero sin una linea de log. La lista de columnas vivia
    en cinco sitios y este era el unico que decidia, en silencio. Ahora decide
    a gritos, y `test_las_dos_agregaciones_cuadran.py` ata el SQL a esta lista
    para que el grito salga en la suite y no en un sismo.

    Una columna que **falta** sigue saliendo vacia: es el caso de las pruebas y
    de un respaldo sin centroide, y un hueco visible no esconde nada.
    """
    filas = list(rows)
    desconocidas = sorted({col for row in filas for col in row} - set(HXL_HEADERS) - NO_PUBLICADAS)
    if desconocidas:
        raise ValueError(
            f"columnas que el adm2.csv no publica: {desconocidas}. "
            "Anadirlas a HXL_HEADERS con su etiqueta, o no entregarlas."
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    columnas = list(HXL_HEADERS)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=columnas)
        writer.writeheader()
        writer.writerow(HXL_HEADERS)
        for row in filas:
            writer.writerow({col: row.get(col, "") for col in columnas})
    return path


def read_adm2_csv(path: Path) -> list[dict[str, str]]:
    """Relee el CSV municipal, saltando la fila HXL.

    Es la vuelta de :func:`write_adm2_csv` y vive a su lado a proposito: la
    peculiaridad de este formato —que la **segunda** fila no son datos sino
    etiquetas HXL— es conocimiento del formato, y tenerlo en dos sitios es como
    se desincronizan las cosas. Quien regenere un derivado a partir del CSV
    publicado lee por aqui.

    Los valores salen como texto, tal cual estan en el fichero. Quien los
    necesite numericos los convierte: el CSV es la cifra exacta publicada y
    reinterpretarla al leerla seria cambiarla.
    """
    with path.open(encoding="utf-8", newline="") as fh:
        filas = list(csv.DictReader(fh))
    return [f for f in filas if not str(f.get("usgs_id", "")).startswith("#")]
