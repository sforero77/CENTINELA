"""Interfaz de linea de comandos de CENTINELA.

Los workflows de GitHub Actions no contienen logica: llaman a estos
subcomandos. Asi el sistema se puede correr y depurar completo en local, que es
lo que hace `make country` posible (O4).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .common.frescura import SITIO_PUBLICADO
from .common.http import HttpFetcher
from .common.logging import get_logger
from .common.manifest import Manifest, fijar_insumos_en_manifest, lint_manifest_file
from .common.paths import BUILD_DIR, MANIFESTS_DIR
from .common.state import EventState
from .common.status import write_status
from .p0_exposure.build import MEDICION_FICHERO, build_country
from .p1_trigger.observados import (
    DIAS_OBSERVADOS,
    fusionar,
    leer,
    podar,
    write_observados,
)
from .p1_trigger.repaso import DIAS_DE_REPASO
from .p1_trigger.run import run_trigger
from .p2_impact.run import run_impact

_log = get_logger("centinela.cli")


def _cmd_trigger(args: argparse.Namespace) -> int:
    """P1: revisa el feed y reporta que eventos despachar."""
    result = run_trigger(HttpFetcher(), dry_run=args.dry_run)
    payload = {
        "nuevos": result.nuevos,
        "revisitados": result.revisitados,
        "a_despachar": result.a_despachar,
        "revisados": result.revisados,
        "observados": len(result.observados),
        "latido_utc": result.latido_utc,
    }
    print(json.dumps(payload, ensure_ascii=False))
    _emit_github_output("eventos", json.dumps(result.a_despachar))
    _emit_github_output("hay_trabajo", "true" if result.a_despachar else "false")

    # El latido alimenta /status. Se escribe siempre, tambien cuando no hay
    # eventos: la ausencia de latidos es la senal de que el cron se desactivo,
    # que es el modo de falla mas probable de todo el sistema.
    write_status(
        latido={
            "utc": result.latido_utc,
            "revisados": result.revisados,
            "relevantes": result.relevantes,
            # Cuantas corridas del vigia cubre este latido. El latido se
            # commitea como mucho una vez por hora, asi que sin este numero el
            # hueco entre dos latidos se lee como si fuera el ritmo del cron —
            # y con el disparo externo a cinco minutos eso sobreestima el
            # intervalo real por un factor de doce.
            "revisiones": max(1, args.revisiones),
        }
    )

    # Y la ventana de cinco dias de lo que se vio y no se despacho. Se
    # reescribe en cada latido aunque no haya nada nuevo, porque la poda
    # depende del reloj y no de que llegue un sismo: sin esto, un evento
    # caducado se quedaria en el mapa hasta el siguiente temblor.
    if not args.dry_run:
        previos = leer()
        vigentes = podar(fusionar(previos, result.observados))
        # Que la *lista* cambie, no que el archivo cambie: `generado_utc` es
        # distinto en cada corrida y haria que esto fuera siempre `true`.
        cambio = [e.usgs_id for e in vigentes] != [e.usgs_id for e in previos]
        write_observados(vigentes)
        # El latido solo se publica una vez por hora para no llenar el
        # historial. Sin este aviso, un sismo pequeno esperaria hasta sesenta
        # minutos para aparecer en el mapa — y quien acaba de sentirlo lo esta
        # buscando ahora.
        _emit_github_output("observados_cambio", "true" if cambio else "false")
    return 0


#: Codigo de salida de "el activo no es de este pais; prueba el siguiente".
#:
#: Tiene el suyo porque **no es un fallo, es un descarte**, y quien orquesta
#: necesita distinguirlos: ante un fallo hay que abrir un issue, ante un
#: descarte hay que reintentar con el siguiente candidato. Misma convencion que
#: `contraste` y `calibrar`, que ya usan el 2 para "esto no es un error, es algo
#: que mirar".
EXIT_ACTIVO_DE_OTRO_PAIS = 3

#: Codigo de salida de "el origen no estaba disponible; vuelve a intentarlo".
#:
#: Misma logica que el 3 de arriba: **no es un fallo del pais ni del codigo**,
#: y quien orquesta necesita distinguirlos. Ante un activo que no pasa los
#: asserts hay que mirar el manifest; ante un origen caido hay que reintentar
#: mas tarde y ya esta. El 27-ago-2026 los dos salian como exit 1 y habia que
#: leer cuatro horas de log para saber cual de los dos era.
EXIT_ORIGEN_CAIDO = 4


def _cmd_impact(args: argparse.Namespace) -> int:
    """P2/P3: procesa un evento ya detectado y publica su reporte."""
    from .p2_impact.pipeline import ExposureCountryMismatchError

    try:
        decision = run_impact(
            args.usgs_id,
            HttpFetcher(timeout_s=300.0),
            detail_url=args.detail_url,
            exposure_glob=args.exposure,
            manifest_id=args.manifest,
            backtest=args.backtest,
            forzar=args.reprocesar,
        )
    except ExposureCountryMismatchError as exc:
        # Las cajas envolventes de los paises se solapan y ordenarlas por area
        # no basta: la de Chile mide 1.719 grados cuadrados por Rapa Nui y la de
        # Argentina 671, asi que un sismo en Coquimbo sale como argentino
        # primero. El desempate real lo da el join, y para eso hay que poder
        # reintentar.
        _log.warning(
            "el activo no corresponde al pais del sismo",
            extra={
                "context": {"usgs_id": args.usgs_id, "activo": args.exposure, "detalle": str(exc)}
            },
        )
        print(json.dumps({"accion": "otro_pais", "razon": str(exc)}, ensure_ascii=False))
        _emit_github_output("accion", "otro_pais")
        return EXIT_ACTIVO_DE_OTRO_PAIS

    print(json.dumps({"accion": decision.action.value, "razon": decision.razon}))
    _emit_github_output("accion", decision.action.value)
    return 0


def _cmd_country(args: argparse.Namespace) -> int:
    """P0: reconstruye el activo de exposicion de un pais."""
    from .p0_exposure.download import OrigenCaidoError

    try:
        out = build_country(
            args.iso3,
            out_dir=Path(args.out or BUILD_DIR),
            liberar_rasters=args.liberar_rasters,
        )
    except OrigenCaidoError as exc:
        # Sale con su propio codigo para que el workflow pueda reintentar solo
        # esto. Un activo que no pasa los asserts no se arregla reintentando.
        _log.warning(
            "origen caido, no se construyo nada",
            extra={"context": {"iso3": args.iso3.upper(), "detalle": str(exc)}},
        )
        print(str(exc), file=sys.stderr)
        return EXIT_ORIGEN_CAIDO
    print(out)
    return 0


def _cmd_fijar_insumos(args: argparse.Namespace) -> int:
    """Vuelca al manifest los digests que midio el build.

    Cierra el circuito: el build mide, `medicion.json` lo publica junto al
    activo, y esto lo fija en el manifest. Sin este paso el digest se copia a
    mano, y con 194 fuentes en diecinueve paises copiar a mano no es tedioso,
    es que no ocurre — que es exactamente por que las 194 llevaban vacias desde
    el primer dia.
    """
    directory = Path(args.dir or MANIFESTS_DIR)
    iso3 = args.iso3.upper()
    if args.medicion:
        medicion_path = Path(args.medicion)
    else:
        salida = Path(args.out or BUILD_DIR) / f"iso3={iso3}" / "layer=exposure"
        medicion_path = salida / MEDICION_FICHERO
    if not medicion_path.exists():
        print(
            f"No hay medicion en {medicion_path}. La escribe `centinela country "
            f"{iso3}`, y se publica en el Release del activo.",
            file=sys.stderr,
        )
        return 1

    medicion = json.loads(medicion_path.read_text(encoding="utf-8"))
    insumos = medicion.get("insumos") or {}
    if not insumos:
        print(
            f"{medicion_path} no trae bloque `insumos`: lo construyo una version "
            f"anterior del pipeline. Hace falta reconstruir el pais.",
            file=sys.stderr,
        )
        return 1

    # Las fuentes leidas en remoto —Overture, la cobertura del suelo— no tienen
    # bytes en disco que hashear, asi que no traen digest y no se fijan. Su
    # anclaje es el release del vintage, que el lint ya obliga a ser explicito.
    digests = {
        sid: datos["insumos_sha256"] for sid, datos in insumos.items() if "insumos_sha256" in datos
    }
    remotas = sorted(sid for sid, datos in insumos.items() if datos.get("remoto"))

    manifest_path = directory / f"{iso3}.yaml"
    if not manifest_path.exists():
        print(f"No hay manifest para {iso3}: {manifest_path}", file=sys.stderr)
        return 1

    parte = fijar_insumos_en_manifest(manifest_path, digests)
    print(f"{manifest_path.name}: {len(digests)} fuentes con digest, {len(remotas)} en remoto")
    for linea in parte:
        print(f"  {linea}")
    if not parte:
        print("  sin cambios: ya estaba todo fijado")
    if remotas:
        print(f"  sin digest (se leen en remoto): {', '.join(remotas)}")
    return 1 if any("SIN TOCAR" in linea for linea in parte) else 0


def _cmd_lint_manifests(args: argparse.Namespace) -> int:
    """Lint de licencias y vintages sobre todos los manifests (§2.4, CI)."""
    directory = Path(args.dir or MANIFESTS_DIR)
    archivos = sorted(directory.glob("*.yaml"))
    if not archivos:
        print(f"No hay manifests en {directory}", file=sys.stderr)
        return 1

    fallo = False
    for path in archivos:
        problemas = lint_manifest_file(path)
        errores = [p for p in problemas if "(aviso)" not in p]
        avisos = [p for p in problemas if "(aviso)" in p]
        estado = "FALLA" if errores else "ok"
        cubo = Manifest.load(path.stem, directory).bucket.value if not errores else "?"
        print(f"{path.name}: {estado} (cubo {cubo})")
        for problema in errores:
            print(f"  ERROR {problema}")
        for aviso in avisos:
            print(f"  aviso {aviso}")
        fallo = fallo or bool(errores)
    return 1 if fallo else 0


def _cmd_status(args: argparse.Namespace) -> int:
    """Recalcula la pagina de estado a partir de los event_state en disco."""
    path = write_status()
    print(path)
    return 0


def _cmd_cobertura(args: argparse.Namespace) -> int:
    """Recalcula `site/cobertura.json` a partir de los manifests.

    Es lo que responde en el visor la pregunta de quien llega: *¿esto sirve
    para mi pais?*. Sale de los manifests y no de un listado aparte, para que
    no pueda afirmar mas paises de los que el sistema construyo de verdad.
    """
    from .common.cobertura import write_cobertura

    print(write_cobertura())
    return 0


def _cmd_contraste(args: argparse.Namespace) -> int:
    """Compara el activo contra una evaluacion de dano externa (Fase 2)."""
    from .p0_exposure.overture_h3 import ensure_httpfs
    from .p2_impact.contraste import contrastar
    from .p2_impact.exposure_join import connect

    con = connect()
    ensure_httpfs(con)
    resultado = contrastar(
        con,
        fuente=args.fuente,
        exposure_glob=args.exposure,
        etiqueta=args.etiqueta,
        crs_origen=args.crs,
        columna_danado=args.columna,
    )
    print(json.dumps(resultado.to_dict(), ensure_ascii=False, indent=2))
    # Una celda evaluada que el activo no tiene es un hueco de cobertura, no un
    # matiz: se distingue con codigo 2 para que un workflow pueda pararse.
    return 2 if resultado.celdas_sin_activo else 0


def _cmd_reindexar(args: argparse.Namespace) -> int:
    """Rehace `reports/index.json` desde los reportes en disco.

    Existe por un conflicto real: dos eventos publicados a la vez —el caso de
    G2, dos mainshocks separados por 33 segundos— chocan en este fichero al
    empujar a la misma rama. Fusionarlo linea a linea no tiene sentido porque es
    un **derivado**: la verdad son los `report.json` del directorio. Se
    regenera y se sigue.
    """
    from .p3_report.run import rebuild_index

    print(rebuild_index(Path(args.reports) if args.reports else None))
    return 0


def _cmd_regenerar_mapas(args: argparse.Namespace) -> int:
    """Rehace los PNG de un reporte ya publicado, o de todos.

    Los mapas son derivados del `report.json` y del `adm2.csv`, asi que se
    pueden rehacer sin recomputar el impacto. Hace falta cada vez que cambia la
    simbologia — y hasta ahora se hacia con un script de usar y tirar.
    """
    from .p3_report.run import regenerate_maps

    escritos = regenerate_maps(
        args.usgs_id or "",
        reports_root=Path(args.reports) if args.reports else None,
    )
    if not escritos:
        print("No se regenero ningun mapa.", file=sys.stderr)
        return 1
    for nombre in sorted(escritos):
        print(escritos[nombre])
    return 0


def _cmd_regenerar_textos(args: argparse.Namespace) -> int:
    """Rehace `report.md` y `hilo.txt` de un reporte ya publicado, o de todos.

    El gemelo de `regenerar-mapas`. Los dos textos son derivados del
    `report.json` y del `adm2.csv`, asi que una correccion de redaccion no
    obliga a recomputar el impacto — que costaria bajar el activo de cada pais.
    """
    from .p3_report.run import regenerate_texts

    escritos = regenerate_texts(
        args.usgs_id or "",
        reports_root=Path(args.reports) if args.reports else None,
    )
    if not escritos:
        print("No se regenero ningun texto.", file=sys.stderr)
        return 1
    for nombre in sorted(escritos):
        print(escritos[nombre])
    return 0


def _cmd_contornos(args: argparse.Namespace) -> int:
    """Trae de USGS el area de afectacion de un reporte publicado, o de todos.

    Los emitidos antes de que el fichero existiera no lo traen, y recomputar su
    impacto entero para obtenerlo costaria bajar el activo de su pais.
    """
    from .p3_report.contornos import backfill_contours

    escritos = backfill_contours(
        args.usgs_id or "", reports_root=Path(args.reports) if args.reports else None
    )
    if not escritos:
        print("No se escribio ningun contorno.", file=sys.stderr)
        return 1
    for evento in sorted(escritos):
        print(escritos[evento])
    return 0


def _cmd_observados(args: argparse.Namespace) -> int:
    """Rellena desde el catalogo historico la ventana de sismos vistos.

    La capa solo sabe lo que vio desde que se encendio, y recien activada su
    etiqueta miente: decia "1 en 5 dias" cuando en LATAM habia habido nueve.
    Tambien repara la ventana si el vigia estuvo caido mas de un dia, que es lo
    que cubre el feed en vivo.
    """
    from .p1_trigger.observados import rellenar

    previos = leer()
    vigentes = podar(fusionar(previos, rellenar(HttpFetcher(), dias=args.dias)), dias=args.dias)
    write_observados(vigentes)

    nuevos = len(vigentes) - len(previos)
    print(f"{len(vigentes)} sismos en la ventana de {args.dias} dias ({nuevos:+d}).")
    for evento in vigentes:
        print(f"  {evento.origen_utc}  M{evento.mag}  {evento.lugar}")
    return 0


def _cmd_incendios(args: argparse.Namespace) -> int:
    """Publica la capa de focos activos cruzada con la exposicion.

    Se llama desde `incendios.yml` cada seis horas: FIRMS tarda unas tres en
    publicar, asi que mas frecuencia no traeria dato nuevo, y menos dejaria la
    capa vieja delante de quien la mira.
    """
    from .p5_incendios.run import run_incendios

    resultado = run_incendios(HttpFetcher(), exposure_glob=args.exposure or "")
    print(
        json.dumps(
            {
                "leidos": resultado.leidos,
                "en_latam": resultado.en_latam,
                "celdas": resultado.celdas,
                "publicado": str(resultado.publicado) if resultado.publicado else None,
            },
            ensure_ascii=False,
        )
    )
    _emit_github_output("celdas", str(resultado.celdas))
    # UNA CORRIDA CIEGA NO SALE EN VERDE.
    #
    # El 30-ago-2026 fallaron los seis ficheros de FIRMS y esta funcion
    # devolvio 0: cero detecciones, cero celdas, workflow verde y nadie
    # enterado. La capa publicada se salvo porque el pipeline se niega a
    # publicar ceros —la guarda del cero silencioso funciono— pero si FIRMS se
    # cayera una semana el visor serviria fuego de hace siete dias sin una sola
    # alarma. Que fallen algunos ficheros es tolerable y se sigue publicando;
    # que fallen todos es quedarse a ciegas, y eso se dice.
    if resultado.ciego:
        print(
            f"FIRMS no devolvio ninguno de sus {resultado.pedidos} ficheros: "
            f"no hay dato nuevo que publicar.",
            file=sys.stderr,
        )
        return 1
    return 0


def _cmd_repasar(args: argparse.Namespace) -> int:
    """Eventos ya caidos del feed cuya version de producto avanzo (RF-04)."""
    from .p1_trigger.repaso import repasar

    resultado = repasar(HttpFetcher(timeout_s=60.0), dias=args.dias)
    print(
        json.dumps(
            {
                "revisados": resultado.revisados,
                "a_despachar": resultado.a_despachar,
                "fallidos": resultado.fallidos,
                "ventana_dias": args.dias,
            },
            ensure_ascii=False,
        )
    )
    _emit_github_output("eventos", json.dumps(resultado.a_despachar))
    _emit_github_output("hay_trabajo", "true" if resultado.a_despachar else "false")
    _emit_github_output("fallidos", str(len(resultado.fallidos)))
    # Que falle alguno se avisa y se sigue: los que si se miraron valen, y sus
    # despachos tienen que salir. Que fallen todos es no haber repasado.
    if resultado.ciego:
        print(
            f"No se pudo consultar ninguno de los {len(resultado.fallidos)} eventos "
            f"de la ventana: el repaso no llego a correr.",
            file=sys.stderr,
        )
        return 1
    return 0


def _cmd_frescura(args: argparse.Namespace) -> int:
    """Comprueba que la pagina publicada sirve lo que hay en el repositorio.

    El visor llego a estar diecisiete horas congelado con todo en verde. Este
    comando existe para que la proxima vez lo diga una alarma y no una persona.
    """
    from .common.frescura import (
        Ausentes,
        Congelado,
        Desfase,
        raise_if_stale,
        resumen,
        revisar,
        revisar_colecciones,
        revisar_vejez,
    )

    cliente = HttpFetcher()
    # Dos preguntas distintas contra la misma pagina: "¿cuanto hace?" para lo
    # que lleva fecha, y "¿estan los mismos?" para lo que es una coleccion. Un
    # indice de reportes recien generado que no lista un reporte publicado esta
    # fresco y roto a la vez.
    # Tres preguntas distintas, y la tercera es la que faltaba: "¿cuanto hace
    # que esto no se regenera?". Las dos primeras comparan repositorio y pagina,
    # y un fichero congelado las pasa las dos — porque los dos lados estan
    # igual de viejos.
    revisiones: list[Desfase | Ausentes | Congelado] = [
        *revisar(cliente, sitio=args.sitio),
        *revisar_colecciones(cliente, sitio=args.sitio),
        *revisar_vejez(),
    ]
    print(resumen(revisiones))
    raise_if_stale(revisiones)

    # NO PODER MIRAR NO ES "ESTA AL DIA".
    #
    # Una corrida sana devuelve un hallazgo por fichero comparado, con
    # `preocupa` en falso. Cero hallazgos significa que no se comparo **ninguno**
    # — la pagina no respondio a nada— y entonces `raise_if_stale` no levanta,
    # esto devolvia cero y `frescura.yml` se ponia verde.
    #
    # El peor sitio posible para ese fallo: este modulo existe porque el visor
    # estuvo diecisiete horas congelado con todo en verde, y su propio vigilante
    # se apuntaba un verde estando ciego.
    #
    # La distincion es la misma que en la lectura de FIRMS: que falle ALGUN
    # fichero es tolerable —uno recien nacido devuelve 404 hasta el primer
    # despliegue, y eso no es una alarma— pero que no se pueda leer NINGUNO es
    # no haber mirado. Y confundir "la red se cayo" con "la pagina esta vieja"
    # manda a investigar mal, asi que se dice con sus palabras.
    if not revisiones:
        print(
            "No se pudo leer nada de la pagina publicada: la comprobacion no "
            "llego a correr. No es lo mismo que estar al dia.",
            file=sys.stderr,
        )
        return 1
    return 0


def _cmd_calibrar(args: argparse.Namespace) -> int:
    """Reajusta la tolerancia de los manifests con lo que midio el ultimo build.

    Estrechar es automatico; ensanchar no. Una tolerancia que se ensancha sola
    para acomodar lo que salio deja de ser un guardian y pasa a ser un sello.
    """
    from datetime import UTC, datetime

    from .common.manifest import Manifest
    from .common.paths import MANIFESTS_DIR
    from .p0_exposure.calibrar import aplicar, calibrar, leer_medicion

    fecha = datetime.now(UTC).date().isoformat()
    salida: list[dict[str, Any]] = []
    bloqueadas = 0

    for ruta in (Path(p) for p in args.medicion):
        medicion = leer_medicion(ruta)
        iso3 = str(medicion.get("iso3", ""))
        manifest = Manifest.load(iso3, Path(args.manifests) if args.manifests else None)
        cal = calibrar(medicion, manifest.referencia_oficial)
        escrito = False
        if args.escribir:
            destino = (Path(args.manifests) if args.manifests else MANIFESTS_DIR) / f"{iso3}.yaml"
            escrito = aplicar(destino, cal, fecha=fecha)
        if cal.necesita_decision:
            bloqueadas += 1
        salida.append(
            {
                "iso3": cal.iso3,
                "medido": round(cal.medido),
                "referencia": round(cal.referencia),
                "desvio_pct": cal.desvio_pct,
                "tolerancia_vigente": cal.tolerancia_vigente,
                "tolerancia_propuesta": cal.tolerancia_propuesta,
                "aplicable": cal.aplicable,
                "motivo_bloqueo": cal.motivo_bloqueo,
                "necesita_decision": cal.necesita_decision,
                "escrito": escrito,
            }
        )

    print(json.dumps(salida, ensure_ascii=False, indent=2))
    if not args.escribir:
        print("(simulacion: nada escrito. Anade --escribir)", file=sys.stderr)
    # Un desvio fuera de tolerancia no es un fallo del comando: es informacion
    # que alguien tiene que mirar. Se distingue con codigo 2 para que un
    # workflow pueda pararse sin confundirlo con un error.
    #
    # Que la propuesta ensanche NO cuenta: significa que la vigente ya es mas
    # estrecha que la politica de margen y el assert pasa igual. Una alarma que
    # suena sin motivo cada trimestre se acaba ignorando.
    return 2 if bloqueadas else 0


def _cmd_paises(args: argparse.Namespace) -> int:
    """Paises cuyo activo podria servir para un evento ya detectado.

    Existe porque P1 vigila **toda** la ventana LATAM y el activo es por pais:
    sin esto, el workflow de impacto bajaba siempre el de Colombia y un sismo en
    Peru se calculaba contra celdas colombianas, publicando ceros.

    Imprime los ISO3 candidatos separados por espacio, del pais mas ajustado al
    mas amplio. Varias cajas se solapan, asi que puede devolver mas de uno: el
    llamador prueba en ese orden y el join contra las celdas H3 desempata.
    """
    from .p0_exposure.download import countries_for_point

    state = EventState.load(args.usgs_id, Path(args.events_dir) if args.events_dir else None)
    if state is not None:
        lon, lat = state.lon, state.lat
    elif args.detail_url:
        # Un historico no tiene estado hasta que P2 lo reconstruye, y en el
        # workflow esta pregunta va **antes** de P2: hay que saber que activo
        # bajar para poder correrlo. La respuesta es geografica, asi que el
        # epicentro del detail sirve igual de bien que el estado.
        detalle = HttpFetcher(timeout_s=60.0).get_json(args.detail_url)
        lon, lat = (float(c) for c in detalle["geometry"]["coordinates"][:2])
    else:
        print(
            f"No existe event_state para {args.usgs_id}. Si es un historico que P1 "
            f"nunca vio, pasa --detail-url para sacar el epicentro del feed.",
            file=sys.stderr,
        )
        return 1

    candidatos = countries_for_point(lon, lat)
    if not candidatos:
        print(
            f"El epicentro de {args.usgs_id} ({lon}, {lat}) no cae en "
            f"ningun pais con caja declarada. Puede ser mar abierto o un pais que "
            f"el sistema todavia no cubre; anadelo a COUNTRY_BBOX.",
            file=sys.stderr,
        )
        return 1

    print(" ".join(candidatos))
    _emit_github_output("paises", " ".join(candidatos))
    _emit_github_output("pais", candidatos[0])
    return 0


def _emit_github_output(key: str, value: str) -> None:
    """Escribe en ``$GITHUB_OUTPUT`` si el runner lo expone."""
    import os

    path = os.environ.get("GITHUB_OUTPUT")
    if not path:
        return
    with Path(path).open("a", encoding="utf-8") as fh:
        fh.write(f"{key}={value}\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="centinela", description=__doc__)
    sub = parser.add_subparsers(dest="comando", required=True)

    p_trigger = sub.add_parser("trigger", help="P1: vigila el feed USGS")
    p_trigger.add_argument(
        "--revisiones",
        type=int,
        default=1,
        help=(
            "corridas del vigia desde el latido anterior; el workflow lo cuenta "
            "para que /status publique el intervalo real y no el de los commits"
        ),
    )
    p_trigger.add_argument("--dry-run", action="store_true", help="no escribe event_state")
    p_trigger.set_defaults(func=_cmd_trigger)

    p_impact = sub.add_parser("impact", help="P2: procesa un evento")
    p_impact.add_argument("usgs_id")
    p_impact.add_argument("--detail-url", required=True, help="URL del feed detail del evento")
    p_impact.add_argument(
        "--exposure",
        required=True,
        help="ruta o glob del activo de exposicion (GeoParquet)",
    )
    p_impact.add_argument(
        "--manifest",
        default="",
        help="id del manifest con el que se construyo el activo",
    )
    p_impact.add_argument(
        "--backtest",
        action="store_true",
        help=(
            "evento historico que P1 nunca vio: reconstruye su estado desde el "
            "detail y lo marca como retrospectivo (queda fuera de la latencia)"
        ),
    )
    p_impact.add_argument(
        "--reprocesar",
        action="store_true",
        help=(
            "reemite el reporte aunque USGS no haya publicado nada nuevo; para "
            "cuando lo que cambio es el pipeline y no los productos"
        ),
    )
    p_impact.set_defaults(func=_cmd_impact)

    p_country = sub.add_parser("country", help="P0: construye exposure_h3 de un pais")
    p_country.add_argument("iso3")
    p_country.add_argument("--out", help="directorio de salida")
    p_country.add_argument(
        "--liberar-rasters",
        action="store_true",
        help=(
            "borra cada raster en cuanto esta agregado a H3. Para CI, donde el "
            "runner arranca vacio y el disco es el limite; en local conviene no "
            "usarlo, porque conservarlos es lo que hace barato reanudar"
        ),
    )
    p_country.set_defaults(func=_cmd_country)

    p_fijar = sub.add_parser(
        "fijar-insumos",
        help="vuelca al manifest los insumos_sha256 que midio el build",
    )
    p_fijar.add_argument("iso3")
    p_fijar.add_argument("--dir", help="directorio de manifests")
    p_fijar.add_argument("--out", help="directorio de salida del build")
    p_fijar.add_argument("--medicion", help="ruta explicita a medicion.json")
    p_fijar.set_defaults(func=_cmd_fijar_insumos)

    p_lint = sub.add_parser("lint-manifests", help="valida licencias y vintages")
    p_lint.add_argument("--dir", help="directorio de manifests")
    p_lint.set_defaults(func=_cmd_lint_manifests)

    p_status = sub.add_parser("status", help="recalcula site/status.json")
    p_status.set_defaults(func=_cmd_status)

    p_cobertura = sub.add_parser(
        "cobertura", help="recalcula site/cobertura.json desde los manifests"
    )
    p_cobertura.set_defaults(func=_cmd_cobertura)

    p_contraste = sub.add_parser(
        "contraste", help="compara el activo con una evaluacion de dano externa"
    )
    p_contraste.add_argument("fuente", help="ruta o URL GDAL del vector de dano")
    p_contraste.add_argument("--exposure", required=True, help="activo de exposicion")
    p_contraste.add_argument("--etiqueta", required=True, help="quien publica la evaluacion")
    p_contraste.add_argument("--crs", required=True, help="EPSG del vector de dano")
    p_contraste.add_argument("--columna", default="damaged", help="columna binaria de dano")
    p_contraste.set_defaults(func=_cmd_contraste)

    p_reindexar = sub.add_parser(
        "reindexar", help="rehace reports/index.json desde los reportes en disco"
    )
    p_reindexar.add_argument("--reports", help="raiz de reports/")
    p_reindexar.set_defaults(func=_cmd_reindexar)

    p_mapas = sub.add_parser(
        "regenerar-mapas", help="rehace los PNG de un reporte publicado, o de todos"
    )
    p_mapas.add_argument("usgs_id", nargs="?", default="", help="vacio = todos los publicados")
    p_mapas.add_argument("--reports", help="raiz de reports/")
    p_mapas.set_defaults(func=_cmd_regenerar_mapas)

    p_textos = sub.add_parser(
        "regenerar-textos",
        help="rehace report.md y hilo.txt de un reporte publicado, o de todos",
    )
    p_textos.add_argument("usgs_id", nargs="?", default="", help="vacio = todos los publicados")
    p_textos.add_argument("--reports", help="raiz de reports/")
    p_textos.set_defaults(func=_cmd_regenerar_textos)

    p_contornos = sub.add_parser(
        "contornos", help="trae de USGS el area de afectacion de reportes ya publicados"
    )
    p_contornos.add_argument("usgs_id", nargs="?", default="", help="vacio = todos")
    p_contornos.add_argument("--reports", help="raiz de reports/")
    p_contornos.set_defaults(func=_cmd_contornos)

    p_observados = sub.add_parser(
        "observados",
        help="rellena desde el catalogo historico la ventana de sismos vistos y no despachados",
    )
    p_observados.add_argument(
        "--dias",
        type=int,
        default=DIAS_OBSERVADOS,
        help=f"ancho de la ventana (por defecto {DIAS_OBSERVADOS})",
    )
    p_observados.set_defaults(func=_cmd_observados)

    p_repasar = sub.add_parser(
        "repasar",
        help="RF-04 fuera del feed: eventos con version de producto mas nueva",
    )
    p_repasar.add_argument(
        "--dias",
        type=int,
        default=DIAS_DE_REPASO,
        help=(
            "ventana hacia atras. El valor por defecto sale de medir cuando deja "
            "de revisarse un ShakeMap de verdad: mediana 63 dias"
        ),
    )
    p_repasar.set_defaults(func=_cmd_repasar)

    p_frescura = sub.add_parser(
        "frescura", help="comprueba que la pagina publicada no quedo detras del repositorio"
    )
    p_frescura.add_argument("--sitio", default=SITIO_PUBLICADO, help="raiz de la pagina publicada")
    p_frescura.set_defaults(func=_cmd_frescura)

    p_incendios = sub.add_parser(
        "incendios", help="publica la capa de focos activos cruzada con la exposicion"
    )
    p_incendios.add_argument(
        "--exposure",
        default="",
        help="patron de los parquet de exposicion; vacio publica el fuego sin cruzar",
    )
    p_incendios.set_defaults(func=_cmd_incendios)

    p_calibrar = sub.add_parser(
        "calibrar", help="reajusta la tolerancia de los manifests con lo medido"
    )
    p_calibrar.add_argument("medicion", nargs="+", help="ficheros medicion.json de los Releases")
    p_calibrar.add_argument(
        "--escribir", action="store_true", help="escribe los manifests (por defecto simula)"
    )
    p_calibrar.add_argument("--manifests", help="directorio de manifests")
    p_calibrar.set_defaults(func=_cmd_calibrar)

    p_paises = sub.add_parser(
        "paises-candidatos", help="ISO3 cuyo activo podria servir para un evento"
    )
    p_paises.add_argument(
        "--detail-url",
        default="",
        help="feed detail del evento; se usa si aun no existe su event_state",
    )
    p_paises.add_argument("usgs_id")
    p_paises.add_argument("--events-dir", help="directorio de event_state")
    p_paises.set_defaults(func=_cmd_paises)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        exit_code: int = args.func(args)
        return exit_code
    except NotImplementedError as exc:
        _log.error("etapa pendiente", extra={"context": {"detalle": str(exc)}})
        print(f"PENDIENTE: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
