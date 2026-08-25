"""Orquestacion de P3: ``report.json`` -> todos los derivados.

Orden deliberado: primero el JSON (fuente de verdad), luego los derivados. Si
un derivado falla, el JSON ya esta en disco y el reporte puede re-renderizarse
sin recomputar el impacto.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

from ..common.logging import get_logger
from ..common.paths import REPORTS_DIR, validate_usgs_id
from .csv_out import read_adm2_csv, write_adm2_csv
from .markdown import render_markdown
from .model import Report
from .social import render_thread_text
from .static_map import MapVariant, render_map

_log = get_logger(__name__)

#: Indice que consume el visor estatico. Sin backend no hay forma de listar un
#: directorio: si este archivo no existe, la lista de eventos del sitio queda
#: vacia para siempre.
INDEX_FILENAME = "index.json"


def write_report_bundle(
    report: Report,
    adm2_rows: Iterable[Mapping[str, Any]],
    *,
    reports_root: Path | None = None,
    con_mapa: bool = True,
) -> dict[str, Path]:
    """Escribe el paquete completo de salidas de un evento y refresca el indice.

    Args:
        report: reporte ya calculado, fuente de verdad de todos los derivados.
        adm2_rows: filas municipales exactas para el CSV. Si traen la columna
            ``centroide`` (WKT ``POINT``) tambien alimentan el mapa.
        reports_root: raiz de ``reports/``. Los tests la redirigen.
        con_mapa: renderiza las dos variantes del PNG. Se puede apagar en
            pruebas para no pagar el arranque de matplotlib.

    Returns:
        Mapa nombre-de-artefacto -> ruta escrita. El mapa PNG se agrega cuando
        T0.8 cierre; su ausencia no bloquea la publicacion del resto.
    """
    root = reports_root or REPORTS_DIR
    directory = root / validate_usgs_id(report.event.usgs_id)
    directory.mkdir(parents=True, exist_ok=True)

    escritos: dict[str, Path] = {}
    escritos["report_json"] = report.save(directory / "report.json")

    md_path = directory / "report.md"
    md_path.write_text(render_markdown(report), encoding="utf-8")
    escritos["report_md"] = md_path

    filas = list(adm2_rows)
    escritos["adm2_csv"] = write_adm2_csv(filas, directory / "adm2.csv")

    if con_mapa:
        escritos.update(render_maps(report, filas, directory))

    hilo_path = directory / "hilo.txt"
    hilo_path.write_text(render_thread_text(report), encoding="utf-8")
    escritos["hilo_txt"] = hilo_path

    escritos["index_json"] = rebuild_index(root)

    _log.info(
        "paquete de reporte escrito",
        extra={
            "context": {
                "usgs_id": report.event.usgs_id,
                "shakemap_version": report.inputs.shakemap_version,
                "preliminar": report.preliminar,
                "backtest": report.backtest,
                "artefactos": sorted(escritos),
            }
        },
    )
    return escritos


def render_maps(
    report: Report, municipios: Sequence[Mapping[str, Any]], directory: Path
) -> dict[str, Path]:
    """Renderiza las dos variantes del PNG de un reporte.

    Un fallo de render no puede tumbar la publicacion: el JSON y el markdown ya
    estan en disco y son lo que importa. Se avisa y se sigue.
    """
    escritos: dict[str, Path] = {}
    for variante in MapVariant:
        try:
            escritos[f"mapa_{variante.value}"] = render_map(
                report,
                variante,
                directory / f"mapa_{variante.value}.png",
                municipios=municipios,
            )
        except Exception as exc:  # el mapa es un derivado, no la verdad
            _log.warning(
                "no se pudo renderizar el mapa",
                extra={"context": {"variante": variante.value, "error": str(exc)}},
            )
    return escritos


def regenerate_maps(usgs_id: str = "", *, reports_root: Path | None = None) -> dict[str, Path]:
    """Rehace los PNG de un reporte ya publicado, o de todos.

    Existe por una correccion que no tenia comando. Los seis PNG de los tres
    reportes publicados salieron vacios —epicentro en (0, 0) y ni un
    municipio— y al arreglar ``static_map.py`` hubo que rehacerlos con un
    script de usar y tirar. La proxima correccion de simbologia no puede
    depender de que alguien recuerde como se hacia.

    Reusa :func:`render_maps`, que es la misma que usa la publicacion: un
    comando de regeneracion que dibujara distinto a la publicacion seria peor
    que no tenerlo.

    Args:
        usgs_id: un evento concreto. Vacio = todos los publicados.
        reports_root: raiz de ``reports/``. Los tests la redirigen.

    Returns:
        Mapa ``"<usgs_id>/<artefacto>" -> ruta``, de lo efectivamente escrito.

    Raises:
        FileNotFoundError: si el evento pedido no tiene ``report.json``. Sin el
            no hay nada que dibujar, y devolver un mapa vacio en silencio es el
            fallo que este comando existe para reparar.
    """
    root = reports_root or REPORTS_DIR
    if usgs_id:
        directorios = [root / validate_usgs_id(usgs_id)]
    else:
        directorios = sorted(p.parent for p in root.glob("*/report.json"))

    escritos: dict[str, Path] = {}
    for directory in directorios:
        origen = directory / "report.json"
        if not origen.is_file():
            raise FileNotFoundError(f"No hay reporte publicado en {directory}")

        report = Report.from_dict(json.loads(origen.read_text(encoding="utf-8")))
        csv_path = directory / "adm2.csv"
        # Un preliminar no publica tabla municipal, y su mapa es solo el
        # epicentro. Es un reporte valido, no un reporte roto.
        municipios = read_adm2_csv(csv_path) if csv_path.is_file() else []

        for nombre, ruta in render_maps(report, municipios, directory).items():
            escritos[f"{directory.name}/{nombre}"] = ruta

    _log.info(
        "mapas regenerados",
        extra={"context": {"eventos": len(directorios), "artefactos": sorted(escritos)}},
    )
    return escritos


def _iso3_del_manifest(manifest_id: str) -> str:
    """``"chl-v0.1"`` -> ``"CHL"``. Vacio si el reporte no lo trae.

    Los reportes emitidos antes de que el indice llevara pais siguen sin el, y
    eso es una **ausencia**, no un pais equivocado: el visor los agrupa aparte
    en vez de asignarlos a ninguno.
    """
    iso3 = manifest_id.split("-", 1)[0].upper()
    return iso3 if len(iso3) == 3 and iso3.isalpha() else ""


def rebuild_index(reports_root: Path | None = None) -> Path:
    """Reconstruye ``reports/index.json`` a partir de los reportes en disco.

    Se reconstruye entero en vez de anexar: el indice es un derivado, y un
    derivado que se acumula termina divergiendo de lo que hay en el directorio.
    Los eventos van del mas reciente al mas antiguo.
    """
    root = reports_root or REPORTS_DIR
    entradas: list[dict[str, Any]] = []

    for path in sorted(root.glob("*/report.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            entradas.append(
                {
                    "usgs_id": data["event"]["usgs_id"],
                    "mag": data["event"]["mag"],
                    "lugar": data["event"]["lugar"],
                    # El pais del activo con el que se calculo. El visor lo
                    # necesita para agrupar por pais, y sin el un tablero
                    # regional no puede decir que es regional. Sale del
                    # manifest —`chl-v0.1` -> CHL— porque es el unico sitio
                    # donde ya consta con certeza: el toponimo de USGS viene en
                    # ingles y no siempre nombra el pais.
                    "iso3": _iso3_del_manifest(data["inputs"]["exposure_manifest"]),
                    # Para dibujar el epicentro sin abrir cada reporte. Los
                    # reportes anteriores no lo traen: quedan en 0,0 y el visor
                    # los lista igual, solo que sin marcador.
                    "lon": data["event"].get("lon", 0.0),
                    "lat": data["event"].get("lat", 0.0),
                    "pop_mmi7p": data["totales"]["pop_mmi7p"],
                    # MMI≥6 viaja al indice para que el visor pueda titular con
                    # una cifra que exista. Un sismo cuya intensidad no llega a
                    # 7 sobre poblacion —Atiquipa 2018, M7,1 a 37 km mar
                    # adentro: 36.933 personas en MMI≥6 y **cero** en MMI≥7—
                    # daba un titular de "0 personas" que se lee como un fallo
                    # del sistema o como un sismo inofensivo. Es correcto y es
                    # lo de menos que se puede decir de ese evento.
                    "pop_mmi6p": data["totales"].get("pop_mmi6p", 0.0),
                    "utc": data["event"]["utc"],
                    "shakemap_version": data["inputs"]["shakemap_version"],
                    "preliminar": bool(data.get("preliminar", False)),
                    "backtest": bool(data.get("backtest", False)),
                    "generado_utc": data.get("generado_utc", ""),
                }
            )
        except (OSError, ValueError, KeyError) as exc:
            # Un reporte corrupto no puede tumbar el indice de todos los demas.
            _log.warning(
                "reporte ilegible, excluido del indice",
                extra={"context": {"path": str(path), "error": str(exc)}},
            )

    entradas.sort(key=lambda e: str(e["utc"]), reverse=True)
    destino = root / INDEX_FILENAME
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(entradas, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return destino
