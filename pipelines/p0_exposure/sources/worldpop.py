"""WorldPop age-sex: seleccion de los rasters que alimentan el desglose etario.

El manifest apunta al **directorio** del release, no a un fichero: WorldPop
publica 62 GeoTIFF por pais y epoca, y cual de ellos hace falta depende de las
bandas de edad que el reporte publica, no de la fuente.

**La trampa esta en el listado.** Junto a las series por sexo (``col_f_65``,
``col_m_65``) el mismo directorio publica la serie combinada (``col_t_65``) y
los totales por sexo (``col_T_F``, ``col_T_M``). Sumar todo lo que termina en
``.tif`` cuenta cada persona **dos veces**: una por su sexo y otra en el
combinado. Este modulo se queda solo con la serie ``_t_``, que es la mitad de
descarga y la unica que no se solapa consigo misma.

Verificado contra el listado real de Colombia (R2025A, epoca 2025): 20 bandas
de edad por sexo —00, 01, 05, 10 … 90—, no las 18 que suponia el manifest. La
banda superior es 90+, asi que ``pop_65p`` va de 65 a 90 y no se corta en 80.
"""

from __future__ import annotations

import re
from typing import Final

#: Ficheros del listado que son series combinadas por edad: ``<iso>_t_<edad>_``.
#: El ``t`` va en minuscula a proposito: ``col_T_F`` es el total del sexo
#: femenino y entraria por error con una comparacion insensible a mayusculas.
AGE_RASTER_RE: Final[re.Pattern[str]] = re.compile(r"^[a-z]{3}_t_(\d{2})_.*\.tif$")

#: Bandas de edad que compone cada columna del activo (§3.2). Las etiquetas son
#: los prefijos que usa WorldPop: "00" es 0 anos, "01" es 1-4, "05" es 5-9.
AGE_GROUPS: Final[dict[str, tuple[str, ...]]] = {
    "pop_0_14": ("00", "01", "05", "10"),
    "pop_65p": ("65", "70", "75", "80", "85", "90"),
}

#: Extrae los ``href`` de un indice de directorio HTTP.
_HREF_RE: Final[re.Pattern[str]] = re.compile(r'href="([^"]+)"', re.IGNORECASE)


def parse_listing(html: str) -> list[str]:
    """Nombres de GeoTIFF que aparecen en un indice de directorio de WorldPop.

    Se lee el indice HTML en vez de reconstruir los nombres por patron porque
    el sufijo del release (``_2025_CN_100m_R2025A_v1``) cambia entre epocas y
    entre paises, y adivinarlo produciria 404 silenciosos justo en las bandas
    que faltan.
    """
    vistos: dict[str, None] = {}
    for href in _HREF_RE.findall(html):
        nombre = href.rsplit("/", 1)[-1]
        if nombre.endswith(".tif"):
            vistos.setdefault(nombre, None)
    return list(vistos)


def age_band(nombre: str) -> str | None:
    """Banda de edad de un raster combinado, o ``None`` si no lo es."""
    coincidencia = AGE_RASTER_RE.match(nombre)
    return coincidencia.group(1) if coincidencia else None


def select_age_rasters(nombres: list[str]) -> dict[str, list[str]]:
    """Agrupa los rasters del listado por la columna del activo que alimentan.

    Returns:
        ``columna -> nombres``, solo con las columnas que tienen al menos un
        raster. Las bandas intermedias (15-64) no se descargan: esa columna es
        el residuo de ``pop_total`` y traerla seria pagar 11 descargas para
        recalcular una resta.
    """
    por_columna: dict[str, list[str]] = {}
    for nombre in nombres:
        banda = age_band(nombre)
        if banda is None:
            continue
        for columna, bandas in AGE_GROUPS.items():
            if banda in bandas:
                por_columna.setdefault(columna, []).append(nombre)
    return {columna: sorted(nombres) for columna, nombres in por_columna.items()}


def missing_bands(seleccion: dict[str, list[str]], nombres: list[str]) -> dict[str, list[str]]:
    """Bandas declaradas en :data:`AGE_GROUPS` que el listado no ofrece.

    Un hueco aqui no es cosmetico: si falta la banda de 80+ el activo publica
    menos adultos mayores de los que hay, y nadie lo nota porque la cifra sigue
    siendo plausible.
    """
    disponibles = {banda for banda in map(age_band, nombres) if banda is not None}
    faltantes = {
        columna: [b for b in bandas if b not in disponibles]
        for columna, bandas in AGE_GROUPS.items()
    }
    return {columna: bandas for columna, bandas in faltantes.items() if bandas}


def raster_url(directorio: str, nombre: str) -> str:
    """URL absoluta de un raster dentro del directorio del release."""
    return f"{directorio.rstrip('/')}/{nombre}"
