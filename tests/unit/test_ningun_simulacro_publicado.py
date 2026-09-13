"""Ningun simulacro puede llegar a lo que se publica.

`scripts/simulacro_sismo.py` genera un paquete de reporte **identico en formato
a uno real**: mismo `report.json`, mismo `adm2.csv` con etiquetas HXL, mismo
`hilo.txt` listo para pegar en una red social. La unica diferencia es que el
sismo no ocurrio.

El script ya se niega a escribir dentro de `events/` o `reports/`. Esta prueba
es el segundo cierre, el que no depende de que nadie use el script: vigila el
**resultado**, o sea el arbol versionado. Un `cp` distraido, un `--salida`
apuntado a mano o un reporte pegado desde otro disco caen aqui.

Un terremoto que no ocurrio, publicado en la pagina de un sistema de exposicion
sismica que leen gestion del riesgo y prensa, es el peor fallo que este
proyecto puede cometer. Cuesta mas caro que cualquier cifra equivocada: una
cifra mala se corrige, un aviso falso de emergencia no se recoge.
"""

from __future__ import annotations

import json

from pipelines.common.paths import EVENTS_DIR, REPORTS_DIR

#: Tiene que coincidir con `PREFIJO_SIMULACRO` de `scripts/simulacro_sismo.py`.
#: No se importa el script: `scripts/` no es un paquete y la suite no lo cubre.
#: Si el prefijo cambia alli y no aqui, el simulacro que se publique pasa por
#: esta prueba sin que nada avise — por eso el nombre va literal y comentado.
PREFIJO = "simulacro"


def _es_simulacro(nombre: str) -> bool:
    return nombre.lower().startswith(PREFIJO)


def test_ningun_event_state_es_un_simulacro() -> None:
    culpables = [p.name for p in EVENTS_DIR.glob("*.json") if _es_simulacro(p.stem)]
    assert not culpables, f"hay simulacros en events/: {culpables}"


def test_ningun_reporte_publicado_es_un_simulacro() -> None:
    culpables = [p.name for p in REPORTS_DIR.iterdir() if p.is_dir() and _es_simulacro(p.name)]
    assert not culpables, f"hay simulacros en reports/: {culpables}"


def test_el_indice_no_lista_ningun_simulacro() -> None:
    """El indice es lo que descarga el visor: es la puerta al publico.

    Se comprueba aparte de la carpeta porque son dos fallos distintos. Una
    carpeta sin entrada en el indice no la ve nadie; una entrada en el indice
    sin carpeta ya paso una vez en este repositorio —`us7000abcd`, un id
    inexistente con 20,0 minutos de latencia publicada— y por eso
    `event_latencies` exige que el reporte exista.
    """
    indice = REPORTS_DIR / "index.json"
    if not indice.exists():
        return
    datos = json.loads(indice.read_text(encoding="utf-8"))
    entradas = datos.get("eventos", datos) if isinstance(datos, dict) else datos
    ids = [
        str(e.get("usgs_id", ""))
        for e in entradas
        if isinstance(e, dict)  # una entrada que no sea objeto la caza el esquema, no esto
    ]
    culpables = [i for i in ids if _es_simulacro(i)]
    assert not culpables, f"el indice publica simulacros: {culpables}"
