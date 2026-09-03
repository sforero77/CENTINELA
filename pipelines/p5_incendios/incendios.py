"""Publicacion de la capa de incendios a `site/incendios.json`.

Mismo contrato que `observados.json` y `status.json`: id de esquema,
`generado_utc` en la raiz —que es lo que lee `frescura.py` para saber si la
pagina publicada se quedo atras— y una `nota` que dice en prosa **que no afirma
el dato**.

Esa nota no es decorativa. Es la unica linea que impide leer "detecciones" como
"incendios" y "celda con fuego" como "hectareas quemadas".
"""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Final

from ..common.logging import get_logger
from ..common.paths import SITE_DIR
from ..common.state import utcnow_iso
from .focos_h3 import CeldaConFuego
from .viento import Lectura as LecturaViento

_log = get_logger(__name__)

INCENDIOS_FILENAME: Final[str] = "incendios.json"

INCENDIOS_SCHEMA_ID: Final[str] = "centinela/incendios/1.0"

#: Tope de seguridad, no criterio editorial. **Se publican todas las celdas.**
#:
#: Estuvo en 4.000 con esta justificacion: "con 22.701 celdas en un dia normal,
#: publicarlas todas serian varios megabytes que el visor descarga en cada
#: carga". ERA FALSA, y nadie la habia medido. GitHub Pages sirve el fichero
#: comprimido —comprobado contra produccion: `Content-Encoding: gzip`— y el
#: visor nunca descargo megabytes.
#:
#: Medido el 31-ago-2026, por la red y en un navegador de verdad:
#:
#:     celdas   gzip     memoria   cuadros/s
#:      4.000   136 KB    77 MB       60
#:     13.031   203 KB    97 MB       60
#:     23.000   304 KB   109 MB       60
#:
#: O sea: publicarlo todo cuesta 67 KB mas que hoy, y en pico de temporada 168.
#: A cambio, los indicadores del tablero pueden cruzarse contra el dato completo
#: en vez de contra una muestra, que era el motivo real del recorte y nadie
#: habia notado que lo fuera.
#:
#: Queda un tope solo porque una temporada catastrofica esta fuera de lo medido,
#: y porque un fichero sin limite superior es una forma de caerse. 60.000 es mas
#: del doble del peor dia visto. Si alguna vez muerde, se dice a gritos: un
#: recorte silencioso convertiria "esto es todo lo que arde" en una mentira.
MAX_CELDAS: Final[int] = 60_000

NOTA: Final[str] = (
    "Detecciones de satelite (VIIRS, 375 m) en las ultimas 24 horas, agregadas a "
    "celdas H3. Una deteccion no es un incendio: es un pixel donde el sensor vio "
    "una anomalia termica —casi siempre fuego de vegetacion, a veces un volcan, "
    "una antorcha de gas o un reflejo— y el mismo fuego produce varias. "
    "NO se estima area quemada — el propio "
    "FIRMS lo desaconseja, porque el muestreo espacial y temporal es irregular. "
    "La exposicion es la del activo de cada pais; una celda sin poblacion puede "
    "estar fuera de los paises cubiertos, no vacia."
)

#: Lo que el viento NO dice, escrito donde viaja el dato.
#:
#: Misma funcion que `NOTA` para las detecciones: la unica linea que impide
#: leer un punto de reticula de 27 km como el viento de una celda de 0,74 km2, y
#: la direccion como hacia donde va en vez de desde donde sopla.
NOTA_VIENTO: Final[str] = (
    "Viento a 10 m y humedad a 2 m del modelo NOAA GFS, en una reticula de 0,25 "
    "grados (unos 27 km). NO es una medicion en la celda: una celda H3 r8 son "
    "0,74 km2 y cientos comparten el mismo punto. La direccion es DESDE donde sopla, "
    "convencion meteorologica: 90 grados es viento del este, que empuja el fuego "
    "hacia el oeste."
)


#: Sobre que arde. Es la pregunta que convierte "hay fuego" en informacion.
#:
#: Un foco sobre pastizal en agosto es rutina agricola; el mismo foco sobre
#: bosque no lo es. Sin este reparto el visor decia cuantas celdas arden y
#: cuanta gente hay debajo, y no decia **que** esta ardiendo — que es lo que
#: separa un contador de un dato.
#:
#: Se pondera por potencia radiativa y no por numero de celdas: mil detecciones
#: debiles sobre cultivo no son lo mismo que cincuenta intensas sobre bosque
#: primario, y contar celdas las igualaria.
SUELOS: Final[tuple[tuple[str, str], ...]] = (
    ("arbolado_pct", "arbolado"),
    ("arbustos_pct", "arbustos"),
    ("pastizal_pct", "pastizal"),
    ("cultivo_pct", "cultivo"),
    ("construido_pct", "construido"),
    ("humedal_pct", "humedal"),
)


def _rejilla_de_viento(
    celdas: list[CeldaConFuego], lectura: LecturaViento | None
) -> dict[str, Any] | None:
    """El viento que toca a las celdas con fuego, como reticula y no por celda.

    ES LA DECISION DE DISENO DE ESTE BLOQUE Y TIENE MOTIVO. Lo comodo seria
    meter velocidad, direccion y humedad dentro de cada celda, junto a la
    poblacion y el arbolado. Se descarto porque **seria una precision falsa**:
    GFS va a 0,25 grados —unos 27 km— y una celda H3 r8 son 0,74 km2. Escribir el
    valor dentro de cada celda las haria parecer medidas independientes cuando
    son el mismo numero repetido.

    Publicando la reticula, el paso de 27 km queda **a la vista en la propia
    forma del dato**: quien lo lea ve puntos separados, no un valor por celda.
    El visor busca el mas cercano, que es exactamente lo que hay.

    El ahorro de sitio es real pero modesto, y conviene no exagerarlo: medido
    sobre la corrida del 31-ago-2026, 4.000 celdas caen en 1.783 puntos —dos
    celdas por punto, porque el fuego esta mas repartido de lo que parece—, o
    sea unos 140 KB en vez de 200. La razon de peso es la primera, no esta.

    Solo se emiten los puntos que tocan alguna celda con fuego: la caja entera
    son 137.541.
    """
    if lectura is None or lectura.ciego or not celdas:
        return None

    import h3

    vistos: dict[tuple[int, int], tuple[float, float]] = {}
    referencia = next(iter(lectura.rejillas.values()))
    for celda in celdas:
        lat, lon = h3.cell_to_latlng(celda.h3)
        # Se redondea al punto de reticula y se guarda una sola vez: es lo que
        # convierte cuatro mil celdas en unos cientos de puntos.
        clave = (round(lat / referencia.dj), round(lon / referencia.di))
        if clave not in vistos:
            vistos[clave] = (clave[0] * referencia.dj, clave[1] * referencia.di)

    puntos: list[dict[str, Any]] = []
    for lat, lon in sorted(vistos.values()):
        viento = lectura.viento_en(lat, lon)
        if viento is None:
            continue
        puntos.append(
            {
                "lat": round(lat, 3),
                "lon": round(lon, 3),
                "vel_ms": viento.velocidad_ms,
                "dir_grados": viento.direccion_grados,
                "hr_pct": viento.humedad_pct,
            }
        )
    if not puntos:
        return None

    return {
        "ciclo": lectura.ciclo,
        "paso_grados": referencia.di,
        "paso_km_aprox": 27,
        "nota": NOTA_VIENTO,
        "puntos": puntos,
    }


def _reparto_del_suelo(celdas: list[CeldaConFuego]) -> dict[str, Any]:
    """Que porcentaje de la energia del fuego cayo sobre cada tipo de suelo.

    Devuelve `{}` si ninguna celda trae cobertura del suelo: los activos
    anteriores a la Fase 1 no la tienen, y publicar ceros diria "no hay bosque"
    donde lo correcto es "no se midio". Es la misma regla que sostiene el resto
    del sistema.
    """
    # MEDIDA ES `lulc_px > 0`, NO "ALGUNA CLASE DA MAS DE CERO".
    #
    # La heuristica anterior preguntaba si alguna de las clases publicadas
    # pasaba de cero. Con cuatro clases de seis, una celda 100 % matorral o
    # 100 % construida daba cero en las cuatro y se marcaba **sin medir**,
    # estando perfectamente medida — y el visor lo afirmaba en pantalla. Con las
    # seis clases eso ya casi no pasa, pero la pregunta correcta no es cuanto
    # suman las clases: es cuanta evidencia hay debajo. P0 publica `lulc_px`
    # justo para esto, diciendo que "una celda con nueve pixeles y otra con
    # ciento cuarenta no merecen la misma confianza".
    con_suelo = [c for c in celdas if c.lulc_px > 0]
    if not con_suelo:
        return {}

    energia = sum(c.frp_suma for c in con_suelo) or 1.0

    def cuota(campo: str) -> float:
        propia = sum(c.frp_suma * getattr(c, campo) / 100.0 for c in con_suelo)
        return float(round(propia / energia * 100, 1))

    reparto: dict[str, Any] = {nombre: cuota(campo) for campo, nombre in SUELOS}
    reparto["celdas_medidas"] = len(con_suelo)
    reparto["celdas_sin_medir"] = len(celdas) - len(con_suelo)
    return reparto


def _en_la_ventana(celdas: list[CeldaConFuego], horas: int) -> list[CeldaConFuego]:
    """Recorta a la ventana que el fichero DICE cubrir.

    EL FICHERO DECLARABA 24 HORAS Y TRAIA TREINTA Y UNA. FIRMS publica un
    "active fire 24h" por satelite y por region, y los seis ficheros no cortan a
    la misma hora: al unirlos, el span real medido el 31-ago-2026 era de **30,9
    h**. Nadie recortaba despues.

    Consecuencia, medida sobre esa misma corrida: **425 de 4.000 celdas —10,6 %—
    quedaban fuera de las 24 h declaradas, y con ellas 130.754 personas**. La
    tarjeta decia "personas en celdas con fuego activo ... en 24 h" contando
    detecciones de hasta 31 horas antes.

    Y ademas descuadraba el visor contra su propia fuente: el visor si aplica la
    ventana, asi que el indicador (4.000) y el mapa (3.575) contaban cosas
    distintas sobre el mismo dato. Cuadrarlos era imposible mientras el fichero
    publicara mas de lo que declaraba.

    La referencia es **la deteccion mas reciente del propio dato**, no el reloj:
    es la misma regla que usa `referenciaDelFuego` en el visor. Con el reloj, un
    fichero de FIRMS de hace cuatro horas dejaria la ventana de 6 h vacia.
    """
    sellos = [c.ultima_utc for c in celdas if c.ultima_utc]
    if not sellos:
        return celdas
    referencia = max(sellos)
    try:
        corte = (
            datetime.fromisoformat(referencia.replace("Z", "+00:00")) - timedelta(hours=horas)
        ).strftime("%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        # Un sello ilegible no puede tirar la corrida entera: se publica sin
        # recortar, que es lo que se hacia hasta ahora.
        return celdas

    dentro = [c for c in celdas if not c.ultima_utc or c.ultima_utc >= corte]
    if len(dentro) < len(celdas):
        _log.info(
            "celdas fuera de la ventana declarada",
            extra={
                "context": {
                    "ventana_horas": horas,
                    "recortadas": len(celdas) - len(dentro),
                    "de": len(celdas),
                    "referencia": referencia,
                }
            },
        )
    return dentro


def _prioridad(celdas: list[CeldaConFuego], max_celdas: int) -> list[CeldaConFuego]:
    """Las que se publican: **primero todas las que tienen gente**.

    Ordenar solo por potencia radiativa parecia lo natural y estaba al reves.
    Medido el 27-ago-2026 sobre los diecinueve activos: de 14.984 celdas con
    fuego, 3.760 tenian poblacion, y con el corte por FRP solo **636**
    sobrevivian. Los 3.124 restantes eran celdas con gente y fuego moderado,
    desplazadas por incendios enormes en Amazonia deshabitada.

    Este es un sistema de exposicion. Un fuego sin nadie cerca es informacion;
    un fuego con tres mil personas debajo es la razon de que el sistema exista,
    y no puede caerse de la lista porque arda menos.
    """
    con_gente = [c for c in celdas if c.pop > 0]
    sin_gente = [c for c in celdas if c.pop <= 0]
    con_gente.sort(key=lambda c: (-c.pop, -c.frp_suma))
    # El relleno despoblado tambien se ordena. Sin esto, el dia que las celdas
    # con gente no llenen el cupo, el resto entraba **en el orden en que DuckDB
    # las escupiera**: arbitrario. Encontrado el 30-ago-2026 auditando el
    # artefacto E2E — ese dia habia 5.244 celdas pobladas para 4.000 puestos y
    # el fallo no se manifestaba, que es exactamente cuando conviene arreglarlo.
    sin_gente.sort(key=lambda c: -c.frp_suma)
    ordenadas = [*con_gente, *sin_gente]

    # EL RECORTE YA NO DECIDE QUE SE PUBLICA —caben todas— PERO SI LLEGARA A
    # MORDER TIENE QUE OIRSE.
    #
    # Un `[:max_celdas]` mudo convierte "esto es todo lo que arde" en una
    # mentira sin que nada falle ni nadie se entere: exactamente la familia del
    # cero silencioso. El orden de arriba sigue valiendo aunque no recorte,
    # porque deja el fichero estable entre corridas y pone delante las celdas
    # con gente.
    if len(ordenadas) > max_celdas:
        _log.error(
            "se recortan celdas con fuego: el fichero publicado NO es todo lo que arde",
            extra={
                "context": {
                    "celdas": len(ordenadas),
                    "publicadas": max_celdas,
                    "descartadas": len(ordenadas) - max_celdas,
                }
            },
        )
    return ordenadas[:max_celdas]


def build_incendios(
    celdas: list[CeldaConFuego],
    *,
    ventana_horas: int = 24,
    max_celdas: int = MAX_CELDAS,
    viento: LecturaViento | None = None,
) -> dict[str, Any]:
    """Arma el JSON que consume el visor.

    Los totales se calculan sobre **todas** las celdas, no sobre las publicadas.
    Recortar la lista para que quepa es razonable; recortar la suma nacional
    para que cuadre con la lista seria publicar una cifra falsa por comodidad.
    """
    celdas = _en_la_ventana(celdas, ventana_horas)
    publicadas = _prioridad(celdas, max_celdas)
    rejilla = _rejilla_de_viento(publicadas, viento)
    return {
        "schema": INCENDIOS_SCHEMA_ID,
        "generado_utc": utcnow_iso(),
        "ventana_horas": ventana_horas,
        "nota": NOTA,
        "suelo": _reparto_del_suelo(celdas),
        "totales": {
            "celdas": len(celdas),
            "celdas_publicadas": len(publicadas),
            "detecciones": sum(c.detecciones for c in celdas),
            "detecciones_baja": sum(c.detecciones_baja for c in celdas),
            "celdas_con_poblacion": sum(1 for c in celdas if c.pop > 0),
            "pop_en_celdas_con_fuego": round(sum(c.pop for c in celdas)),
            # Lo que el popup de una celda ya decia y el indicador no.
            #
            # Un hospital dentro de una celda con fuego activo es la cifra que
            # decide un traslado, y estaba solo para quien pulsara esa celda
            # concreta entre catorce mil. Mismo criterio que en el lado sismico:
            # el orden de un tablero lo fija para que sirve.
            "salud_en_celdas_con_fuego": sum(c.salud for c in celdas),
            "edu_en_celdas_con_fuego": sum(c.edu for c in celdas),
            "bld_en_celdas_con_fuego": sum(c.bld for c in celdas),
            "frp_total_mw": round(sum(c.frp_suma for c in celdas), 1),
        },
        "celdas": [asdict(c) for c in publicadas],
        # Va al final y como clave aparte, no dentro de cada celda. El porque
        # esta en `_rejilla_de_viento`. Ausente —no vacia— cuando no se pudo
        # leer GFS: una reticula vacia se leeria como "no hay viento".
        **({"viento": rejilla} if rejilla else {}),
    }


def write_incendios(
    celdas: list[CeldaConFuego],
    *,
    site_dir: Path | None = None,
    ventana_horas: int = 24,
    viento: LecturaViento | None = None,
    avisos: tuple[str, ...] = (),
) -> Path:
    """Publica `site/incendios.json`.

    `avisos` lleva lo que el activo consumido no traia y salio como cero. Se
    publica en el fichero, no solo en el log: quien integra esta capa lee el
    JSON, y un cero sin nota al lado es indistinguible de una medida.
    """
    destino = (site_dir or SITE_DIR) / INCENDIOS_FILENAME
    destino.parent.mkdir(parents=True, exist_ok=True)
    datos = build_incendios(celdas, ventana_horas=ventana_horas, viento=viento)
    if avisos:
        datos["avisos"] = list(avisos)
    # SIN SANGRIA, y no por tacaneria: con todas las celdas dentro, `indent=2`
    # son unos 2 MB de espacios en un fichero que **ninguna persona lee** —lo
    # consume el visor—. El diff de git tampoco pierde nada: este fichero se
    # regenera entero en cada corrida, nunca se revisa linea a linea.
    #
    # Los que si se leen a mano —`status.json`, `cobertura.json`— conservan la
    # suya.
    destino.write_text(
        json.dumps(datos, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8"
    )

    _log.info("incendios publicados", extra={"context": datos["totales"]})
    return destino


def leer(site_dir: Path | None = None) -> dict[str, Any]:
    """Lo publicado hasta ahora. Un fichero ausente o corrupto no es un fallo."""
    destino = (site_dir or SITE_DIR) / INCENDIOS_FILENAME
    if not destino.exists():
        return {}
    try:
        datos: dict[str, Any] = json.loads(destino.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        _log.warning("incendios.json ilegible; se reconstruye", extra={"context": {}})
        return {}
    return datos
