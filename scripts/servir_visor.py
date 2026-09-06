"""Sirve el visor en local con la MISMA estructura que la pagina publicada.

`make site` hacia `http.server --directory site`, y eso no es lo que GitHub
Pages sirve. El visor pide `reports/index.json` y `reports/<id>/report.json`
como rutas relativas, y en la pagina publicada `reports/` es hermano de
`index.html` porque `site.yml` lo copia dentro del artefacto. Sirviendo solo
`site/` esas rutas no existen: **el unico comando documentado para ver el visor
en local mostraba «Todavia no hay reportes publicados» con veintisiete
publicados**, y quien lo probaba concluia que el producto esta vacio.

Copiar `reports/` dentro de `site/` en cada arranque serian 200 MB de duplicado
y un directorio que se queda viejo. Esto reescribe la ruta al vuelo:

    /                -> site/index.html
    /assets/app.js   -> site/assets/app.js
    /reports/...     -> reports/...

Sin copiar nada y sin que `site/` deje de ser lo que se publica.
"""

from __future__ import annotations

import argparse
import sys
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

#: Prefijos que no viven en `site/` y que la pagina publicada sirve al lado.
FUERA_DE_SITE = ("/reports/", "/events/")


class VisorHandler(SimpleHTTPRequestHandler):
    """Resuelve `site/` como raiz, salvo lo que la pagina publica al lado."""

    def translate_path(self, path: str) -> str:
        limpio = path.split("?", 1)[0].split("#", 1)[0]
        for prefijo in FUERA_DE_SITE:
            if limpio.startswith(prefijo):
                # `SimpleHTTPRequestHandler` ya normaliza y bloquea el `..`;
                # aqui solo se cambia el directorio base.
                return super().translate_path(path)
        return super().translate_path("/site" + limpio)

    def log_message(self, formato: str, *args: object) -> None:
        # Una linea por peticion llena la consola con los 27 reportes y sus
        # cuatro artefactos cada uno. Solo se anuncia lo que no se encontro,
        # que es lo unico accionable mientras se mira el visor.
        if args and str(args[1]).startswith(("4", "5")):
            # `formato % args` es la firma de la clase base, no una eleccion.
            detalle = formato % args
            sys.stderr.write(f"{self.address_string()} - {detalle}\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--puerto", type=int, default=8080)
    args = parser.parse_args(argv)

    handler = partial(VisorHandler, directory=str(RAIZ))
    servidor = ThreadingHTTPServer(("127.0.0.1", args.puerto), handler)
    reportes = len(list((RAIZ / "reports").glob("*/report.json")))
    print(f"Visor en http://localhost:{args.puerto}/  ({reportes} reportes servidos)")
    print("Ctrl-C para parar.")
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print()
    finally:
        servidor.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
