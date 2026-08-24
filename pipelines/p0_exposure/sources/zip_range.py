"""Extraccion selectiva de ficheros dentro de un ZIP remoto.

El Marco Geoestadistico Nacional del DANE se publica como un unico ZIP de
**3,39 GB**, y lo que P0 necesita de el son cinco ficheros que suman ~100 MB: el
shapefile municipal. Bajar 3,4 GB cada trimestre para quedarse con el 3 % es
desperdicio, y en un runner de GitHub Actions es ademas un riesgo de disco.

El formato ZIP permite evitarlo: el **directorio central** vive al final del
archivo y describe donde empieza cada entrada. Con tres peticiones de rango
—cola, directorio central, y el rango de la entrada que interesa— se extrae un
fichero suelto sin tocar el resto.

Requisitos del servidor: aceptar `Range` (responder 206). El geoportal del DANE
lo hace; si algun mirror no lo hiciera, el fallback honesto es bajar el ZIP
entero, no adivinar.
"""

from __future__ import annotations

import struct
import zlib
from dataclasses import dataclass
from typing import Protocol

#: Firmas del formato ZIP.
_EOCD = b"PK\x05\x06"
_EOCD64 = b"PK\x06\x06"
_CENTRAL = b"PK\x01\x02"
_LOCAL = b"PK\x03\x04"

#: Cuanto leer del final para encontrar el EOCD. El comentario del ZIP puede
#: ocupar hasta 64 KB, asi que 70 KB cubre el peor caso.
_TAIL_BYTES = 70_000


class RangeFetcher(Protocol):
    """Cliente capaz de pedir un rango de bytes."""

    def get_range(self, url: str, start: int, end: int) -> bytes: ...

    def content_length(self, url: str) -> int: ...


class ZipRangeError(Exception):
    """El ZIP remoto no se puede leer por rangos."""


@dataclass(frozen=True, slots=True)
class ZipEntry:
    """Una entrada del directorio central."""

    name: str
    compressed_size: int
    uncompressed_size: int
    #: Offset de la cabecera local dentro del ZIP.
    local_header_offset: int
    compression: int

    @property
    def is_stored(self) -> bool:
        """Sin comprimir (metodo 0)."""
        return self.compression == 0

    @property
    def is_deflated(self) -> bool:
        return self.compression == 8


def list_entries(
    fetcher: RangeFetcher, url: str, *, total_size: int | None = None
) -> list[ZipEntry]:
    """Lista el contenido de un ZIP remoto leyendo solo su directorio central."""
    total = total_size if total_size is not None else fetcher.content_length(url)
    if total <= 0:
        raise ZipRangeError(f"Tamano desconocido para {url}")

    tail_start = max(0, total - _TAIL_BYTES)
    tail = fetcher.get_range(url, tail_start, total - 1)

    i = tail.rfind(_EOCD)
    if i < 0:
        raise ZipRangeError("No se encontro el End of Central Directory: ¿es un ZIP?")

    cd_size: int = struct.unpack("<I", tail[i + 12 : i + 16])[0]
    cd_offset: int = struct.unpack("<I", tail[i + 16 : i + 20])[0]

    # ZIP64: los campos de 32 bits se saturan y el valor real vive en el EOCD64.
    if cd_offset == 0xFFFFFFFF or cd_size == 0xFFFFFFFF:
        j = tail.rfind(_EOCD64)
        if j < 0:
            raise ZipRangeError("ZIP64 declarado pero sin EOCD64 en la cola")
        cd_size = struct.unpack("<Q", tail[j + 40 : j + 48])[0]
        cd_offset = struct.unpack("<Q", tail[j + 48 : j + 56])[0]

    central = fetcher.get_range(url, cd_offset, cd_offset + cd_size - 1)
    return _parse_central_directory(central)


def _parse_central_directory(central: bytes) -> list[ZipEntry]:
    entradas: list[ZipEntry] = []
    p = 0
    while p + 46 <= len(central) and central[p : p + 4] == _CENTRAL:
        compression = struct.unpack("<H", central[p + 10 : p + 12])[0]
        comp_size = struct.unpack("<I", central[p + 20 : p + 24])[0]
        uncomp_size = struct.unpack("<I", central[p + 24 : p + 28])[0]
        n_len, e_len, c_len = struct.unpack("<HHH", central[p + 28 : p + 34])
        local_offset = struct.unpack("<I", central[p + 42 : p + 46])[0]
        name = central[p + 46 : p + 46 + n_len].decode("utf-8", "replace")
        entradas.append(
            ZipEntry(
                name=name,
                compressed_size=comp_size,
                uncompressed_size=uncomp_size,
                local_header_offset=local_offset,
                compression=compression,
            )
        )
        p += 46 + n_len + e_len + c_len
    if not entradas:
        raise ZipRangeError("Directorio central vacio o ilegible")
    return entradas


def extract_entry(fetcher: RangeFetcher, url: str, entry: ZipEntry) -> bytes:
    """Descarga y descomprime una sola entrada.

    La cabecera local repite el nombre y los campos extra con longitudes
    propias, distintas de las del directorio central, asi que hay que leerla
    para saber donde empiezan los datos.
    """
    cabecera = fetcher.get_range(url, entry.local_header_offset, entry.local_header_offset + 29)
    if cabecera[:4] != _LOCAL:
        raise ZipRangeError(f"Cabecera local invalida para {entry.name!r}")
    n_len, e_len = struct.unpack("<HH", cabecera[26:30])

    inicio = entry.local_header_offset + 30 + n_len + e_len
    datos = fetcher.get_range(url, inicio, inicio + entry.compressed_size - 1)

    if entry.is_stored:
        return datos
    if entry.is_deflated:
        return zlib.decompress(datos, -zlib.MAX_WBITS)
    raise ZipRangeError(f"Metodo de compresion no soportado: {entry.compression}")


def find_entries(entries: list[ZipEntry], *suffixes: str) -> list[ZipEntry]:
    """Entradas cuyo nombre termina en alguno de los sufijos dados."""
    bajos = tuple(s.lower() for s in suffixes)
    return [e for e in entries if e.name.lower().endswith(bajos)]
