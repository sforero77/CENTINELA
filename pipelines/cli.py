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

from .common.constants import SITIO_PUBLICADO
from .common.http import HttpFetcher
from .common.logging import get_logger
from .common.manifest import Manifest, fijar_insumos_en_manifest, lint_manifest_file
from .common.paths import BUILD_DIR, MANIFESTS_DIR
from .common.state import EventState, EventStatus
from .common.status import write_status
from .p0_exposure.build import MEDICION_FICHERO, build_country
from .p1_trigger.observados import (
    DIAS_OBSERVADOS,
    fusionar,
    leer,
    pais_del_toponimo,
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
        # UN ESTADO ILEGIBLE SACA AL SISMO DEL DESPACHO PARA SIEMPRE.
        #
        # `run_trigger` ya lo contaba y lo dejaba en un log: no llegaba ni al
        # stdout, ni al output del workflow, ni al latido, ni a /status. Y no es
        # un tropiezo de una corrida: el fichero sigue ilegible en la siguiente,
        # asi que ese evento no se despacha nunca mas y el latido publica
        # «revisados: 18, relevantes: 0», identico a una noche tranquila.
        "estados_ilegibles": result.estados_ilegibles,
        "feeds_fallidos": result.feeds_fallidos,
        "latido_utc": result.latido_utc,
    }
    _emit_github_output("eventos", json.dumps(result.a_despachar))
    _emit_github_output("hay_trabajo", "true" if result.a_despachar else "false")
    _emit_github_output("estados_ilegibles", str(len(result.estados_ilegibles)))
    _emit_github_output("feeds_fallidos", str(len(result.feeds_fallidos)))
    # LOS DOS FEEDS CAIDOS ES NO HABER MIRADO.
    #
    # Con uno caido la corrida sigue valiendo —para eso hay dos— pero con los
    # dos, "cero eventos" significa "no mire", no "no habia". El latido se
    # escribe igual, porque su ausencia es la senal de que el cron murio; lo que
    # cambia es que la corrida no sale en verde.
    if result.ciego:
        print(
            f"No se pudo leer ninguno de los {len(result.feeds_fallidos)} feeds de USGS: "
            f"esta pasada no vio el feed, no es que no hubiera sismos.",
            file=sys.stderr,
        )
    elif result.feeds_fallidos:
        print(
            f"Feed(s) no disponibles: {', '.join(result.feeds_fallidos)}. "
            f"La pasada sigue valiendo con el resto.",
            file=sys.stderr,
        )
    if result.estados_ilegibles:
        print(
            f"No se pudo leer el estado de {len(result.estados_ilegibles)} evento(s) "
            f"({', '.join(result.estados_ilegibles)}): quedan fuera del despacho hasta "
            f"que su fichero se repare, y esta corrida no los va a reintentar.",
            file=sys.stderr,
        )

    # El latido alimenta /status. Se escribe siempre, tambien cuando no hay
    # eventos: la ausencia de latidos es la senal de que el cron se desactivo,
    # que es el modo de falla mas probable de todo el sistema.
    #
    # UN LATIDO QUE NO SE PUEDE ESCRIBIR NO PUEDE TRAGARSE EL SISMO.
    #
    # `write_status` se niega —con razon— a reescribir un `status.json`
    # ilegible: publicar encima borraria el historial entero de latidos, que es
    # la unica prueba de que el vigia esta vivo. Pero esa excepcion subia hasta
    # aqui sin nadie que la parara, y eso convertia un fichero con marcadores de
    # conflicto en un **evento perdido**: el comando moria antes de escribir
    # `observados.json`, el paso del workflow se ponia en rojo, y con el en rojo
    # se saltaban tanto el commit del estado como el despacho de P2. El sismo
    # estaba detectado y en disco; nadie llegaba a mirarlo.
    #
    # Se anota, se termina el resto del trabajo, y la corrida acaba en rojo de
    # todos modos: visible sin ser destructivo.
    latido_fallido: str | None = None
    try:
        write_status(
            latido={
                "utc": result.latido_utc,
                "revisados": result.revisados,
                "relevantes": result.relevantes,
                # Cuantas corridas del vigia cubre este latido. El latido se
                # commitea como mucho una vez por hora, asi que sin este numero
                # el hueco entre dos latidos se lee como si fuera el ritmo del
                # cron — y con el disparo externo a cinco minutos eso
                # sobreestima el intervalo real por un factor de doce.
                "revisiones": max(1, args.revisiones),
                # Va al latido para que /status lo ensene: es la unica
                # superficie publica donde "cero relevantes" se puede
                # distinguir de "no pude leer". Solo cuando los hay, para no
                # ensuciar los latidos sanos.
                **(
                    {"estados_ilegibles": len(result.estados_ilegibles)}
                    if result.estados_ilegibles
                    else {}
                ),
                **({"feeds_fallidos": result.feeds_fallidos} if result.feeds_fallidos else {}),
            }
        )
    except (OSError, ValueError) as error:
        latido_fallido = str(error)
        print(f"No se pudo publicar el latido: {error}", file=sys.stderr)
        _emit_github_output("latido_fallido", "true")

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

    # El payload sale al final, ya con el veredicto del latido dentro: lo que
    # imprime este comando es lo que la corrida vio, y un latido que no se pudo
    # publicar forma parte de eso.
    payload["latido_fallido"] = latido_fallido
    print(json.dumps(payload, ensure_ascii=False))
    return 1 if (result.ciego or latido_fallido) else 0


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

#: Codigo de salida de "el release de Overture que fija el manifest ya no existe".
#:
#: Distinto del origen caido **porque no se reintenta**: Overture conserva dos
#: releases y el fijado caduca solo. Volver a pedir una url que ya no existe
#: gasta media hora en repetir el mismo 404; lo que hace falta es actualizar el
#: release en el manifest, y eso lo decide una persona.
EXIT_RELEASE_CADUCADO = 5


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
            aunque_no_alcance=args.aunque_no_alcance,
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
    from .p0_exposure.download import OrigenCaidoError, ReleaseCaducadoError

    try:
        out = build_country(
            args.iso3,
            out_dir=Path(args.out or BUILD_DIR),
            liberar_rasters=args.liberar_rasters,
        )
    except ReleaseCaducadoError as exc:
        # Antes de `OrigenCaidoError` en el orden del `except`: no hereda de el,
        # pero dejarlo debajo invitaria a que alguien lo hiciera heredar y se
        # tragara el codigo propio sin que nada fallara.
        _log.error(
            "release de Overture caducado, no se construyo nada",
            extra={"context": {"iso3": args.iso3.upper(), "detalle": str(exc)}},
        )
        print(str(exc), file=sys.stderr)
        return EXIT_RELEASE_CADUCADO
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
    path = write_status(recuperar=args.recuperar)
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
    """Compara el activo contra una evaluacion de dano externa (Fase 2).

    `--salida` no es un extra. El resultado se imprimia y se perdia, y sus
    cifras acabaron citadas a mano en `docs/PARA_INSTITUCIONES.md` —el documento
    que abre diciendo «todo lo que afirma esta medido, y dice donde esta la
    medida»— sin que quedara en el repositorio un fichero al que apuntar.
    Persistirlo es lo que convierte esa seccion en algo que un tercero puede
    comprobar en vez de creer.
    """
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
    volcado = json.dumps(
        {**resultado.to_dict(), "fuente": args.fuente, "crs_origen": args.crs},
        ensure_ascii=False,
        indent=2,
    )
    if args.salida:
        destino = Path(args.salida)
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(volcado + "\n", encoding="utf-8")
        print(destino)
    print(volcado)
    # Una celda evaluada que el activo no tiene es un hueco de cobertura, no un
    # matiz: se distingue con codigo 2 para que un workflow pueda pararse.
    return 2 if resultado.celdas_sin_activo else 0


def _cmd_reindexar(args: argparse.Namespace) -> int:
    """Rehace `reports/index.json` desde los reportes en disco.

    Existe por un conflicto real: dos eventos publicados a la vez —el caso de
    G2, dos mainshocks separados por 32,2 segundos— chocan en este fichero al
    empujar a la misma rama. Fusionarlo linea a linea no tiene sentido porque es
    un **derivado**: la verdad son los `report.json` del directorio. Se
    regenera y se sigue.
    """
    from .p3_report.run import rebuild_index

    indice = rebuild_index(Path(args.reports) if args.reports else None)
    print(indice.ruta)
    # UN REPORTE QUE SE CAE DEL INDICE DEJA DE EXISTIR PARA EL VISOR.
    #
    # Se excluia con un `_log.warning` y esto salia 0: el reporte desaparecia de
    # la pagina sin una sola alarma. El indice se reconstruye igual —los otros
    # veintiseis tienen que seguir listados— pero la corrida se pone en rojo.
    if indice.excluidos:
        print(
            f"{len(indice.excluidos)} reporte(s) publicados no se pudieron leer y "
            f"NO aparecen en el indice ({', '.join(indice.excluidos)}): el visor "
            f"dejara de listarlos.",
            file=sys.stderr,
        )
        return 1
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


def _cmd_sincronizar_portada(args: argparse.Namespace) -> int:
    """Pone la tabla de cifras del README al dia con el reporte publicado.

    Existe porque la portada se desincronizo tres veces y la tercera dejo
    `main` en rojo: el bot re-emitio el reporte de ShakeMap v8 a v9 y la tabla
    se quedo escrita a mano. `impact.yml` lo corre **antes** de commitear, asi
    que la tabla viaja en el mismo commit que el reporte.

    Con `--comprobar` no escribe: informa y devuelve 1 si algo se movio. Sirve
    para preguntar en CI sin arreglar nada.
    """
    from .common.paths import REPO_ROOT
    from .p3_report.portada import sincronizar_portada

    cambios = sincronizar_portada(
        REPO_ROOT / "README.md",
        reports_root=Path(args.reports) if args.reports else None,
        escribir=not args.comprobar,
    )
    if not cambios:
        print("la portada ya dice lo que dice el reporte")
        return 0
    verbo = "habria que cambiar" if args.comprobar else "actualizado"
    for c in cambios:
        print(f"{verbo}: {c}")
    return 1 if args.comprobar else 0


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


def _cmd_alertas_terreno(args: argparse.Namespace) -> int:
    """Trae de USGS su propia alerta de falla de terreno para reportes publicados.

    Los emitidos antes de que el reporte supiera citarla no la traen, y
    recomputar su impacto entero costaria bajar el activo de su pais para
    obtener cuatro cadenas que USGS sigue sirviendo.
    """
    from .p3_report.falla_de_terreno import backfill_ground_failure_alerts

    relleno = backfill_ground_failure_alerts(
        args.usgs_id or "", reports_root=Path(args.reports) if args.reports else None
    )
    for evento in sorted(relleno.escritos):
        print(relleno.escritos[evento])

    # NO HABER TENIDO NADA QUE HACER NO ES UN FALLO.
    #
    # Salia 1 en cuanto `escritos` venia vacio, y eso ocurre en el caso normal:
    # la segunda corrida, con todos los reportes ya al dia. Un comando
    # idempotente que sale en rojo cuando no hay trabajo ensena a ignorar su
    # codigo de salida — y entonces el dia que USGS no conteste tampoco se mira.
    print(
        f"escritos: {len(relleno.escritos)} · ya al dia: {len(relleno.ya_al_dia)} · "
        f"sin producto: {len(relleno.sin_alertas)} · fallidos: {len(relleno.fallidos)}",
        file=sys.stderr,
    )
    _emit_github_output("escritos", str(len(relleno.escritos)))
    _emit_github_output("fallidos", str(len(relleno.fallidos)))
    if relleno.ciego:
        print(
            f"No se pudo leer el detalle de ninguno de los {relleno.revisados} eventos: "
            f"la comprobacion no llego a correr.",
            file=sys.stderr,
        )
        return 1
    if relleno.fallidos:
        print(
            f"No se pudo consultar {len(relleno.fallidos)} de {relleno.revisados} eventos: "
            f"{', '.join(sorted(relleno.fallidos))}",
            file=sys.stderr,
        )
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
                # La merma sale por stdout, no solo al log: es lo que distingue
                # "hoy ardio poco" de "hoy solo lei la mitad de los ficheros".
                "ficheros_pedidos": resultado.pedidos,
                "ficheros_leidos": resultado.ficheros_leidos,
                "ficheros_fallidos": resultado.fallidos,
                "publicado": str(resultado.publicado) if resultado.publicado else None,
            },
            ensure_ascii=False,
        )
    )
    _emit_github_output("celdas", str(resultado.celdas))
    _emit_github_output("ficheros_fallidos", str(len(resultado.fallidos)))
    _emit_github_output("ficheros_pedidos", str(resultado.pedidos))
    # UNA LECTURA PARCIAL SE PUBLICA, PERO SE DICE.
    #
    # Con tres de los seis ficheros caidos —Sudamerica entera, el 11,9 % del
    # dato— la corrida salia 0 y la capa se publicaba como completa. Sigue
    # publicandose, porque medio continente de fuego es mejor que ninguno, pero
    # el aviso viaja ahora al JSON, al output del workflow y a stderr.
    if resultado.fallidos and not resultado.ciego:
        print(
            f"FIRMS devolvio {resultado.pedidos - len(resultado.fallidos)} de sus "
            f"{resultado.pedidos} ficheros ({', '.join(resultado.fallidos)}): la capa "
            f"publicada no es todo el fuego de la ventana.",
            file=sys.stderr,
        )
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
            f"FIRMS no devolvio dato util en ninguno de sus {resultado.pedidos} "
            f"ficheros ({len(resultado.fallidos)} fallaron, "
            f"{resultado.ficheros_leidos} trajeron detecciones): no hay dato nuevo "
            f"que publicar.",
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


def _cmd_rezagados(args: argparse.Namespace) -> int:
    """Reportes publicados que se quedaron atras de sus fuentes.

    Informa; no despacha. Ver `pipelines/p1_trigger/rezago.py`.
    """
    from .p1_trigger.rezago import comprobar

    resultado = comprobar(HttpFetcher(timeout_s=60.0))
    print(
        json.dumps(
            {
                "revisados": resultado.revisados,
                "rezagados": [
                    {
                        "usgs_id": r.usgs_id,
                        "shakemap": [r.shakemap_publicado, r.shakemap_vigente],
                        "groundfailure": [r.groundfailure_publicado, r.groundfailure_vigente],
                        "exposicion": [r.manifiesto_publicado, r.manifiesto_vigente],
                        "detalle": r.describir(),
                    }
                    for r in resultado.rezagados
                ],
                "fallidos": resultado.fallidos,
            },
            ensure_ascii=False,
        )
    )
    _emit_github_output("hay_rezago", "true" if resultado.rezagados else "false")
    _emit_github_output("cuantos", str(len(resultado.rezagados)))
    # Separados porque deciden quien puede re-emitirlos sin mirar: los de
    # activo casi no mueven cifras; los de producto mueven las que el README
    # cita a mano. Ver `solo_exposicion` en el modulo.
    _emit_github_output("ids_exposicion", " ".join(r.usgs_id for r in resultado.solo_exposicion))
    _emit_github_output("ids_productos", " ".join(r.usgs_id for r in resultado.por_productos))
    _emit_github_output("resumen", "\n".join(f"- {r.describir()}" for r in resultado.rezagados))

    if resultado.ciego:
        print(
            f"No se pudo consultar ninguno de los {len(resultado.fallidos)} reportes: "
            "la comprobacion no llego a correr.",
            file=sys.stderr,
        )
        return 1
    # Que haya rezago NO es un fallo: es informacion para una persona. Salir
    # distinto de cero convertiria "hay trabajo pendiente" en "algo se rompio",
    # y en dos semanas nadie miraria el aviso.
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
    # LA GUARDA DE CEGUERA CUENTA SOLO LO QUE DEPENDIO DE LA RED.
    #
    # `revisar` y `revisar_colecciones` preguntan a la pagina publicada;
    # `revisar_vejez` mira el repositorio y **no toca la red**, asi que responde
    # siempre. Al meter las tres en la misma lista, `if not revisiones` se volvio
    # inalcanzable por construccion: con GitHub Pages caido el comando imprimia
    # los tres hallazgos locales, salia 0, y el paso `if: success()` de
    # `frescura.yml` cerraba la incidencia abierta comentando «Recuperado. La
    # pagina publicada vuelve a estar al dia».
    #
    # El peor sitio posible para ese fallo: este modulo existe porque el visor
    # estuvo diecisiete horas congelado con todo en verde, y su propio vigilante
    # firmaba el verde estando ciego.
    de_red: list[Desfase | Ausentes | Congelado] = [
        *revisar(cliente, sitio=args.sitio),
        *revisar_colecciones(cliente, sitio=args.sitio),
    ]
    locales: list[Desfase | Ausentes | Congelado] = list(revisar_vejez())
    revisiones = [*de_red, *locales]
    print(resumen(revisiones))

    # La senal viaja al workflow, que asi puede condicionar el cierre de la
    # incidencia a "si se pudo mirar" en vez de a `success()`.
    _emit_github_output("pagina_leida", "true" if de_red else "false")
    _emit_github_output("comparados", str(len(de_red)))

    raise_if_stale(revisiones)

    # NO PODER MIRAR NO ES "ESTA AL DIA".
    #
    # La distincion es la misma que en la lectura de FIRMS: que falle ALGUN
    # fichero es tolerable —uno recien nacido devuelve 404 hasta el primer
    # despliegue, y eso no es una alarma— pero que no se pueda leer NINGUNO es
    # no haber mirado. Y confundir "la red se cayo" con "la pagina esta vieja"
    # manda a investigar mal, asi que se dice con sus palabras.
    if not de_red:
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


def _cmd_sin_pais(args: argparse.Namespace) -> int:
    """Cierra un evento que no cae en ningun pais, dejandolo visible.

    NI FALLO ETERNO NI DESAPARICION SILENCIOSA.

    Un M5,5+ en mar abierto dentro de `LATAM_BBOX` no tiene activo contra el que
    calcular: un reporte es imposible. Pero hasta hoy tampoco alcanzaba estado
    terminal, asi que `repaso.yml` lo re-despachaba a diario durante noventa
    dias, abriendo una incidencia cada vez.

    Se cierra por los dos lados: el estado pasa a `DESCARTADO` —terminal, no se
    re-despacha— **y el evento entra en `observados.json`**, la capa que el
    visor ya pinta con los sismos vistos y no despachados. Ocurrio, se vio, y se
    puede señalar en el mapa; lo unico que no hay es una cifra de exposicion, y
    eso el propio fichero lo declara.
    """
    from .p1_trigger.observados import EventoObservado, fusionar, leer, podar, write_observados

    events_dir = Path(args.events_dir) if args.events_dir else None
    estado = EventState.load(args.usgs_id, events_dir)
    if estado is None:
        print(f"No existe event_state para {args.usgs_id}.", file=sys.stderr)
        return 1

    razon = args.razon or "epicentro fuera de la caja de todos los paises cubiertos"
    if estado.estado is not EventStatus.DESCARTADO:
        estado.transition(EventStatus.DESCARTADO, nota=razon).save(events_dir)

    observado = EventoObservado(
        usgs_id=estado.usgs_id,
        mag=estado.mag,
        lon=estado.lon,
        lat=estado.lat,
        depth_km=estado.depth_km,
        lugar=estado.lugar,
        origen_utc=estado.origen_utc,
        razon=razon,
        iso3="",
    )
    ruta = write_observados(podar(fusionar(leer(), [observado])))
    print(json.dumps({"usgs_id": estado.usgs_id, "razon": razon, "observados": str(ruta)}))
    return 0


#: Codigo de salida de `paises-candidatos` cuando el epicentro no cae en ninguna
#: caja de pais. **No es un fallo**: es mar abierto, y quien llama tiene que
#: poder distinguirlo de un error de verdad para cerrarlo en vez de reintentarlo
#: noventa dias. El 1 queda para los fallos y el 2 lo usa `main()` para
#: `NotImplementedError`.
SIN_PAIS_CANDIDATO = 4


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

    # Un estado ilegible se trata como un estado ausente: este comando ya tiene
    # camino para eso —`--detail-url`— y usarlo es mejor que morir, porque quien
    # llama es `impact.yml` y necesita saber que activo bajar.
    try:
        state = EventState.load(args.usgs_id, Path(args.events_dir) if args.events_dir else None)
    except (ValueError, KeyError, OSError) as error:
        _log.warning(
            "event_state ilegible; se resuelve el pais por el detail",
            extra={"context": {"usgs_id": args.usgs_id, "error": str(error)}},
        )
        state = None
    lugar = ""
    if state is not None:
        lon, lat = state.lon, state.lat
        lugar = state.lugar
    elif args.detail_url:
        # Un historico no tiene estado hasta que P2 lo reconstruye, y en el
        # workflow esta pregunta va **antes** de P2: hay que saber que activo
        # bajar para poder correrlo. La respuesta es geografica, asi que el
        # epicentro del detail sirve igual de bien que el estado.
        detalle = HttpFetcher(timeout_s=60.0).get_json(args.detail_url)
        lon, lat = (float(c) for c in detalle["geometry"]["coordinates"][:2])
        lugar = str((detalle.get("properties") or {}).get("place") or "")
    else:
        print(
            f"No existe event_state para {args.usgs_id}. Si es un historico que P1 "
            f"nunca vio, pasa --detail-url para sacar el epicentro del feed.",
            file=sys.stderr,
        )
        return 1

    candidatos = countries_for_point(lon, lat)
    if not candidatos:
        # MAR ABIERTO NO ES UN FALLO, Y TRATARLO COMO TAL SALIA CARO.
        #
        # `LATAM_BBOX` es un rectangulo que cubre miles de km2 de Pacifico y
        # Atlantico. Un M5,5+ ahi pasa el filtro de P1 y llega aqui; con
        # `return 1`, `impact.yml` moria bajo `set -e`, abria una incidencia que
        # nadie cerraba, y el evento **nunca alcanzaba estado terminal** —el
        # descarte vive dentro de `run_impact`, que no llegaba a correr—. Se
        # quedaba `detectado` para siempre y `repaso.yml` lo re-despachaba a
        # diario durante noventa dias.
        #
        # Con codigo propio, quien llama puede distinguirlo de un fallo de
        # verdad y cerrarlo: ver `centinela sin-pais`.
        print(
            f"El epicentro de {args.usgs_id} ({lon}, {lat}) no cae en "
            f"ningun pais con caja declarada. Puede ser mar abierto o un pais que "
            f"el sistema todavia no cubre; anadelo a COUNTRY_BBOX.",
            file=sys.stderr,
        )
        return SIN_PAIS_CANDIDATO

    # EL ORDEN POR AREA DE CAJA NO SIRVE PARA ELEGIR UNO SOLO.
    #
    # `countries_for_point` ordena por area de caja envolvente, y este mismo
    # fichero documenta por que eso falla: la de Chile mide 1.719 grados
    # cuadrados por Rapa Nui, asi que un sismo en Coquimbo sale como argentino
    # primero. Para **iterar** da igual —el join desempata—, pero `impact.yml`
    # usa el primero cuando tiene que publicar sin poder iterar, y ahi elegir mal
    # significa publicar un reporte de Chile contra el activo de Argentina.
    #
    # El toponimo de USGS si lo dice, y `pais_del_toponimo` ya lo lee. Cuando no
    # lo sepa devuelve cadena vacia y manda el orden de siempre.
    del_toponimo = pais_del_toponimo(lugar)
    preferido = del_toponimo if del_toponimo in candidatos else candidatos[0]

    # EL PREFERIDO VA PRIMERO EN LA LISTA, NO SOLO EN UN OUTPUT QUE NADIE LEIA.
    #
    # Se emitia `pais` a `$GITHUB_OUTPUT` y **ningun workflow lo consumia**:
    # `impact.yml` captura este stdout y, cuando tiene que publicar sin poder
    # iterar, coge el primero con `awk '{print $1}'` — el primero por area de
    # caja envolvente, que es el orden que este mismo fichero documenta como
    # equivocado. La de Chile mide 1.719 grados cuadrados por Rapa Nui, asi que
    # un sismo en Coquimbo sale como argentino primero: el reporte se publicaria
    # contra el activo de Argentina, con la nota de distancia a la poblacion
    # argentina mas cercana.
    #
    # Poniendolo a la cabeza, el desempate por toponimo llega tambien a quien
    # solo lee la lista, y de paso la iteracion prueba primero el candidato mas
    # probable — que es un acierto y no un cambio de comportamiento.
    ordenados = [preferido, *[c for c in candidatos if c != preferido]]

    print(" ".join(ordenados))
    _emit_github_output("paises", " ".join(ordenados))
    _emit_github_output("pais", preferido)
    return 0


def _emit_github_output(key: str, value: str) -> None:
    """Escribe en ``$GITHUB_OUTPUT`` si el runner lo expone.

    UN VALOR CON SALTOS DE LINEA ROMPE EL FICHERO ENTERO.

    El formato ``clave=valor`` solo admite una linea: la segunda se lee como
    otra clave, y a partir de ahi el runner interpreta basura. Ningun llamador
    lo hacia hasta que ``rezagados`` quiso emitir una lista, asi que el fallo
    llevaba ahi desde el principio sin poder dispararse.

    GitHub tiene formato para esto —``clave<<DELIM``— y pide que el delimitador
    no aparezca en el valor. Se comprueba en vez de suponerlo: un valor que lo
    contuviera podria cerrar el bloque antes de tiempo y escribir las claves
    que quisiera.
    """
    import os

    path = os.environ.get("GITHUB_OUTPUT")
    if not path:
        return
    with Path(path).open("a", encoding="utf-8") as fh:
        if "\n" not in value:
            fh.write(f"{key}={value}\n")
            return
        delimitador = "CENTINELA_EOF"
        while delimitador in value:
            delimitador += "_"
        fh.write(f"{key}<<{delimitador}\n{value}\n{delimitador}\n")


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
        "--aunque-no-alcance",
        action="store_true",
        help=(
            "publica el reporte aunque el ShakeMap no alcance ninguna celda del "
            "activo. Solo tras agotar los candidatos: entonces el pais es el "
            "correcto y lo que pasa es que la sacudida no llego a poblacion"
        ),
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
    p_status.add_argument(
        "--recuperar",
        action="store_true",
        help=(
            "sale del bloqueo cuando site/status.json quedo ilegible: lo aparta, "
            "arranca historial nuevo y declara la perdida en el JSON"
        ),
    )
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
    p_contraste.add_argument(
        "--salida", help="fichero donde persistir el resultado (para poder citarlo)"
    )
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

    p_portada = sub.add_parser(
        "sincronizar-portada",
        help="pone la tabla de cifras del README al dia con el reporte publicado",
    )
    p_portada.add_argument(
        "--comprobar",
        action="store_true",
        help="no escribe: informa y sale con 1 si la portada se separo",
    )
    p_portada.add_argument("--reports", help="raiz de reports/")
    p_portada.set_defaults(func=_cmd_sincronizar_portada)

    p_contornos = sub.add_parser(
        "contornos", help="trae de USGS el area de afectacion de reportes ya publicados"
    )
    p_contornos.add_argument("usgs_id", nargs="?", default="", help="vacio = todos")
    p_contornos.add_argument("--reports", help="raiz de reports/")
    p_contornos.set_defaults(func=_cmd_contornos)

    p_alertas = sub.add_parser(
        "alertas-terreno",
        help="trae de USGS su alerta de falla de terreno para reportes ya publicados",
    )
    p_alertas.add_argument("usgs_id", nargs="?", default="", help="vacio = todos")
    p_alertas.add_argument("--reports", help="raiz de reports/")
    p_alertas.set_defaults(func=_cmd_alertas_terreno)

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

    p_rezagados = sub.add_parser(
        "rezagados",
        help="reportes publicados cuya fuente sirve hoy algo mas nuevo (informa, no despacha)",
    )
    p_rezagados.set_defaults(func=_cmd_rezagados)

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

    p_sin_pais = sub.add_parser(
        "sin-pais",
        help="cierra un evento en mar abierto: terminal y visible en observados",
    )
    p_sin_pais.add_argument("usgs_id")
    p_sin_pais.add_argument("--razon", default="")
    p_sin_pais.add_argument("--events-dir", default="")
    p_sin_pais.set_defaults(func=_cmd_sin_pais)

    return parser


def main(argv: list[str] | None = None) -> int:
    # LA SALIDA VA EN UTF-8 AUNQUE LA CONSOLA DIGA OTRA COSA.
    #
    # Esta herramienta imprime español y notacion de intensidad: `MMI≥7`,
    # `≥ 0,10`, nombres con tilde. En una consola de Windows sin configurar,
    # `sys.stdout` sale en cp1252 y `print` de un `≥` lanza
    # `UnicodeEncodeError` — el comando revienta **despues** de haber hecho su
    # trabajo, o sea que deja el fichero escrito y sale con traza y codigo 1.
    # Paso con `sincronizar-portada` la primera vez que corrio en la maquina
    # del autor.
    #
    # `errors="replace"` y no `"strict"`: perder un simbolo en un mensaje de
    # consola es un defecto cosmetico; abortar una publicacion por el juego de
    # caracteres de la terminal, no.
    for flujo in (sys.stdout, sys.stderr):
        if hasattr(flujo, "reconfigure"):
            flujo.reconfigure(encoding="utf-8", errors="replace")

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
