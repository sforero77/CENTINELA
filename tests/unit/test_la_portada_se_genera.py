"""La tabla de cifras del README se genera; no se escribe a mano.

TRES VECES SE DESINCRONIZO, Y LA TERCERA TUMBO `main`.

El 25-ago-2026 cinco filas quedaron viejas tras reconstruir el activo —los km
de via, por un factor de seis—. El 7-sep volvio a pasar. Y el 8-sep el repaso
dejo de excluir los backtests, re-emitio `us6000tjl2` de ShakeMap v8 a v9 y la
portada se quedo con las cifras del v8: `main` en rojo, publicado por el bot.

`test_cifras_del_readme.py` aviso las tres veces. Avisar no basta cuando quien
re-emite es un workflow a las tres de la manana, asi que ahora la tabla la
escribe `pipelines/p3_report/portada.py` y `impact.yml` la corre antes de
commitear.

Estas pruebas cubren el generador. La que comprueba que la portada **esta** al
dia sigue siendo `test_cifras_del_readme.py`: una vigila el resultado y la otra
la herramienta.
"""

from __future__ import annotations

import io
from pathlib import Path

import pytest

from pipelines.p3_report.portada import (
    FILAS,
    FILAS_MUNICIPIOS,
    cifras_publicadas,
    sincronizar_portada,
)

RAIZ = Path(__file__).resolve().parents[2]
README = RAIZ / "README.md"


def test_la_portada_del_repositorio_esta_al_dia() -> None:
    """En seco sobre el README real: si esto falla, corre el comando."""
    assert sincronizar_portada(README, escribir=False) == [], (
        "la portada se separo del reporte. `centinela sincronizar-portada` lo arregla."
    )


def test_devuelve_lo_que_cambio_y_lo_deja_escrito(tmp_path: Path) -> None:
    """El caso del 8-sep: la tabla con las cifras de la version anterior."""
    valores = cifras_publicadas()
    etiqueta = "Personas en MMI≥7"
    copia = tmp_path / "README.md"
    copia.write_text(
        README.read_text(encoding="utf-8").replace(
            f"| {etiqueta} | **{valores[etiqueta]}** |",
            f"| {etiqueta} | **2.424.287** |",
        ),
        encoding="utf-8",
    )

    cambios = sincronizar_portada(copia)

    assert [c.etiqueta for c in cambios] == [etiqueta]
    assert cambios[0].antes == "2.424.287"
    assert cambios[0].ahora == valores[etiqueta]
    assert f"| {etiqueta} | **{valores[etiqueta]}** |" in copia.read_text(encoding="utf-8")


def test_comprobar_no_toca_el_fichero(tmp_path: Path) -> None:
    """`--comprobar` pregunta. Un comando que arregla cuando le preguntas no
    sirve para vigilar en CI."""
    copia = tmp_path / "README.md"
    original = README.read_text(encoding="utf-8").replace("**971**", "**514**")
    copia.write_text(original, encoding="utf-8")

    cambios = sincronizar_portada(copia, escribir=False)

    assert cambios, "tenia que ver la diferencia"
    assert copia.read_text(encoding="utf-8") == original, "no debia escribir"


def test_no_inventa_filas_que_el_readme_no_publica(tmp_path: Path) -> None:
    """Mantener al dia una tabla no es decidir que va en ella.

    Si alguien quita una fila de la portada, el generador la deja quitada: la
    alternativa es que un workflow reescriba la primera pagina del proyecto por
    su cuenta.
    """
    etiqueta = "Sedes educativas en MMI≥7"
    copia = tmp_path / "README.md"
    texto = README.read_text(encoding="utf-8")
    fuera = "\n".join(
        linea for linea in texto.splitlines() if not linea.startswith(f"| {etiqueta} |")
    )
    copia.write_text(fuera, encoding="utf-8")

    sincronizar_portada(copia)

    assert etiqueta not in copia.read_text(encoding="utf-8")


def test_el_mapeo_cubre_la_tabla_entera() -> None:
    """Once filas publicadas: nueve de `totales` y dos de contar municipios."""
    etiquetas = [e for e, _ in FILAS] + [e for e, _ in FILAS_MUNICIPIOS]
    texto = README.read_text(encoding="utf-8")
    publicadas = [
        linea.split("|")[1].strip()
        for linea in texto.splitlines()
        if linea.startswith("| ") and linea.rstrip().endswith("** |")
    ]
    de_la_tabla = [e for e in publicadas if e in etiquetas]

    assert sorted(de_la_tabla) == sorted(etiquetas), (
        "hay una fila en la tabla que el generador no conoce, o al reves"
    )


def test_la_salida_del_cli_aguanta_una_consola_que_no_es_utf8() -> None:
    """`MMI≥7` en una consola cp1252 reventaba **despues** de escribir.

    La primera corrida real de `sincronizar-portada` en Windows dejo el fichero
    actualizado y salio con `UnicodeEncodeError` y codigo 1: el trabajo hecho y
    el workflow en rojo. `main()` reconfigura los dos flujos a UTF-8 con
    `errors="replace"` antes de nada.
    """
    from pipelines.cli import main

    crudo = io.BytesIO()
    consola = io.TextIOWrapper(crudo, encoding="cp1252", errors="strict")
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr("sys.stdout", consola)
        codigo = main(["sincronizar-portada", "--comprobar"])

    consola.flush()
    assert codigo == 0, "la portada del repositorio tendria que estar al dia"


def test_sincronizar_la_portada_no_puede_tumbar_una_publicacion() -> None:
    """El derivado no manda sobre el producto.

    `sincronizar-portada` lee el `report.json` del Choco, que no tiene nada que
    ver con el evento que se esta publicando. `impact.yml` corre con `bash -e`,
    asi que sin guarda un sismo en Chile se quedaria **sin reporte** porque un
    fichero de otro evento no se puede leer. Comprobado: con el `report.json`
    fuera de sitio, el comando lanza `FileNotFoundError`.

    La alarma no se pierde: `test_cifras_del_readme.py` sigue comprobando que
    la portada este al dia, e `impact.yml` despacha `ci.yml` al terminar. Lo
    que se pierde es la sincronizacion automatica de esa vez.
    """
    import yaml

    flujo = yaml.safe_load(
        (RAIZ / ".github" / "workflows" / "impact.yml").read_text(encoding="utf-8")
    )
    pasos = flujo["jobs"]["impacto"]["steps"]
    publicar = next(p for p in pasos if p.get("id") == "publicar")
    lineas = publicar["run"].splitlines()

    i = next(n for n, s in enumerate(lineas) if "sincronizar-portada" in s)
    invocacion = " ".join(linea.strip().rstrip("\\") for linea in lineas[i : i + 2])

    assert "||" in invocacion, (
        "`sincronizar-portada` volvio a quedar sin guarda en impact.yml: un fallo "
        "suyo aborta el paso entero y el evento se queda sin publicar."
    )
