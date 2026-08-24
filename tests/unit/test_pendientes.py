"""Inventario de las etapas pendientes.

Estas pruebas no verifican comportamiento: verifican **honestidad**. Cada etapa
sin implementar tiene que fallar de forma ruidosa y explicita, no devolver
silenciosamente un cero que acabaria publicado como cifra.

**La lista esta vacia.** Ya no queda ninguna etapa del camino critico sin
implementar: P0 construye el activo de un pais de la descarga al parquet, y P2
lleva un evento de los productos de USGS al reporte publicado. La prueba se
queda como guardia: si alguien vuelve a introducir un ``NotImplementedError``
en ``pipelines/``, tiene que declararlo aqui y explicar por que.
"""

from __future__ import annotations

import ast
from pathlib import Path

PIPELINES = Path(__file__).parent.parent.parent / "pipelines"

#: Etapas que se permite que fallen a proposito, con su motivo. Vacio hoy.
PENDIENTES_DECLARADAS: dict[str, str] = {}


def _modulos_con_not_implemented() -> dict[str, list[str]]:
    """Funciones de ``pipelines/`` que lanzan ``NotImplementedError``."""
    encontrados: dict[str, list[str]] = {}
    for ruta in sorted(PIPELINES.rglob("*.py")):
        arbol = ast.parse(ruta.read_text(encoding="utf-8"))
        for nodo in ast.walk(arbol):
            if not isinstance(nodo, ast.FunctionDef):
                continue
            lanza = any(
                isinstance(hijo, ast.Raise)
                and isinstance(hijo.exc, ast.Call)
                and isinstance(hijo.exc.func, ast.Name)
                and hijo.exc.func.id == "NotImplementedError"
                for hijo in ast.walk(nodo)
            )
            if lanza:
                clave = str(ruta.relative_to(PIPELINES))
                encontrados.setdefault(clave, []).append(nodo.name)
    return encontrados


def test_no_hay_etapas_pendientes_sin_declarar() -> None:
    """Un NotImplementedError nuevo tiene que pasar por esta lista.

    Es la guardia contra el atajo mas tentador de todos: dejar una funcion a
    medias y que el fallo aparezca durante un terremoto en vez de en CI.
    """
    encontrados = _modulos_con_not_implemented()
    sin_declarar = {
        modulo: funciones
        for modulo, funciones in encontrados.items()
        if modulo not in PENDIENTES_DECLARADAS
    }
    assert sin_declarar == {}, (
        f"Etapas que fallan sin estar declaradas: {sin_declarar}. "
        f"Si es deliberado, anadelas a PENDIENTES_DECLARADAS con su motivo."
    )


def test_el_camino_critico_esta_completo() -> None:
    """P0 y P2 no pueden tener agujeros: son los que producen las cifras."""
    encontrados = _modulos_con_not_implemented()
    criticos = [m for m in encontrados if m.startswith(("p0_exposure/", "p2_impact/"))]
    assert criticos == [], f"El camino critico tiene etapas sin implementar: {criticos}"
