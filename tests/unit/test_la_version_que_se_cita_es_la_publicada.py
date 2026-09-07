"""«El de Venezuela llegó a v14» estaba escrito a mano, y el reporte iba por v15.

Tres documentos publicados —el visor, la página de estado y `docs/AUDITORIA.md`—
usan la versión más alta de ShakeMap del catálogo como ejemplo de que **un
ShakeMap se revisa muchas veces**. Es un buen ejemplo y por eso está en tres
sitios; el problema es que la cifra la mantiene una persona y el catálogo la
mueve solo: `us6000t7zp` se re-emitió hasta la v15 y las tres seguían diciendo
v14.

No es una errata: es el argumento entero. La frase existe para decir «esto no se
queda quieto», y quedarse quieta es la única forma de desmentirse.

El guardia lee la versión más alta de `reports/*/report.json` y exige que sea la
que citan. Si mañana sale una v16, esta prueba se pone roja y el texto se
actualiza con ella.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]

#: Dónde se cita la versión más alta como ejemplo, y con qué frase.
#:
#: Se guarda la frase entera y no solo el número: `v15` suelto aparecería
#: también en una ruta o en un identificador, y un guardia que empareje eso
#: aprueba por cualquier coincidencia.
CITAS: tuple[tuple[str, str], ...] = (
    ("site/index.html", "el de Venezuela llegó a v{v}"),
    ("site/status.html", "el de Venezuela a v{v}"),
    ("docs/AUDITORIA.md", "Venezuela llegó a v{v}"),
)


def _version_mas_alta() -> tuple[int, str]:
    """La versión de ShakeMap más alta del catálogo publicado, y de qué evento."""
    mejor = (0, "")
    for ruta in sorted((RAIZ / "reports").glob("*/report.json")):
        datos = json.loads(ruta.read_text(encoding="utf-8"))
        version = int(datos.get("inputs", {}).get("shakemap_version") or 0)
        if version > mejor[0]:
            mejor = (version, ruta.parent.name)
    return mejor


def test_hay_catalogo_que_leer() -> None:
    """La red de seguridad: sin reportes, las citas de abajo no comprobarían nada.

    Si `reports/` desapareciera o cambiara de forma, `_version_mas_alta`
    devolvería 0 y las tres pruebas de abajo pasarían a comparar contra «v0», que
    no está en ningún texto: fallarían, pero por el motivo equivocado. Esto lo
    dice antes y con su nombre.
    """
    version, evento = _version_mas_alta()
    assert version > 0, "ningún report.json declara shakemap_version"
    assert evento, "la versión más alta no viene de ningún evento"


@pytest.mark.parametrize(("documento", "plantilla"), CITAS, ids=[c[0] for c in CITAS])
def test_la_version_citada_es_la_del_catalogo(documento: str, plantilla: str) -> None:
    """Y si el catálogo avanza, el texto avanza con él."""
    version, evento = _version_mas_alta()
    texto = (RAIZ / documento).read_text(encoding="utf-8")
    esperada = plantilla.format(v=version)

    assert esperada in texto, (
        f"{documento} no dice «{esperada}». La versión más alta publicada es la "
        f"v{version} (evento {evento}), y esa frase existe para enseñar que un "
        f"ShakeMap se revisa muchas veces: citarla desactualizada la desmiente. "
        f"Encontrado: {re.findall(r'v[0-9]+', texto)[:6]}"
    )
