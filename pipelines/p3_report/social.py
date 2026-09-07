"""Borrador de hilo para redes (RF-07).

El unico paso manual permitido en todo el sistema: el hilo se **genera**
automaticamente pero **no se publica**. Un falso disparo tuiteado solo es peor
que un falso disparo silencioso, y el control editorial cuesta un clic.
"""

from __future__ import annotations

from ..common.constants import SITIO_PUBLICADO
from ..common.formatting import format_count_prose, format_number_es
from .model import Report, banda_del_ranking, municipios_del_ranking

#: Limite conservador por publicacion, compatible con la mayoria de redes.
MAX_CHARS = 280


def render_thread(report: Report) -> list[str]:
    """Genera el hilo como lista de publicaciones."""
    ev = report.event
    tot = report.totales
    posts: list[str] = []

    # «Sismo M7.8 **en** 27 km al SSE de Muisne» — la preposicion falla con los
    # toponimos de USGS, que casi siempre son una distancia: "en 27 km al SSE de
    # Muisne" no se puede leer. Con "Acapulco, México" si funcionaba, y de ahi
    # que sobreviviera. Un separador no tiene ese problema con ninguno de los dos.
    #
    # Y la magnitud con coma: este hilo se publica en espanol y el visor ya
    # escribe "M7,8". Que el mismo evento salga como "M7.8" en redes y "M7,8" en
    # la pagina es una costura gratuita.
    # `ev.utc` ya termina en Z, que **es** la marca de UTC: escribir "Z UTC"
    # detras dice lo mismo dos veces y de la forma menos legible posible.
    # Falta la hora local, que es la que necesita quien lo lee — y no se pone
    # aqui porque exige resolver la zona horaria del epicentro, y varios paises
    # del catalogo tienen mas de una. Anotado en PENDIENTES: equivocarla en un
    # sismo en vivo es peor que no darla.
    cabeza = (
        f"Sismo M{format_number_es(ev.mag, 1)} · {ev.lugar} "
        f"({_utc_legible(ev.utc)}, {format_number_es(ev.depth_km, 0)} km de profundidad). "
        f"Reporte automático de EXPOSICIÓN estimada de CENTINELA. "
        f"No es un reporte de daños."
    )
    posts.append(cabeza)

    if report.preliminar:
        posts.append(
            "Aun no hay ShakeMap publicado. Estas cifras son un corte preliminar "
            "por radios alrededor del epicentro y se actualizan solas cuando USGS "
            "publique el ShakeMap."
        )
    elif not tot.banda_titular:
        # TRES CEROS SEGUIDOS NO INFORMAN, ALARMAN AL REVES.
        #
        # `us1000c2zy` es un M7,5 cuyo ShakeMap llega a MMI 8, y su hilo abria
        # con "0. 0. 0." — que se lee como "no se pudo calcular". Se pudo: la
        # sacudida fue mar adentro. Es el mismo remedio que la linea de
        # deslizamiento ya aplica a su propio cero.
        posts.append(
            "Ninguna persona del país queda dentro de MMI≥6. No es que falte el dato: "
            "la intensidad que el ShakeMap dibuja para este evento no alcanza esa "
            "banda sobre territorio habitado."
        )
    else:
        # LAS CIFRAS DE LA BANDA QUE ESTE EVENTO ALCANZO, NO SIEMPRE LAS DE 7.
        #
        # Estaba clavado en `pop_mmi7p` y `bld_mmi7p`, asi que siete hilos
        # publicados decian «Dentro de MMI≥7: 0. Edificaciones en MMI≥7: 0.»
        # mientras el `report.md` del mismo directorio decia «el evento no llego
        # a esta banda» y «1,1 millones de edificaciones». Dos ceros seguidos en
        # un hilo se leen como que el sistema no calculo nada.
        banda = tot.banda_publicada
        edificaciones = tot.bld_mmi7p if banda == 7 else tot.bld_mmi6p
        # Cuando la banda publicada ES la 6 no se repite la misma cifra dos
        # veces: "MMI≥6: 3.400. Dentro de MMI≥6: 3.400." no informa de nada.
        dentro = f"Dentro de MMI≥7: {format_count_prose(tot.pop_mmi7p)}. " if banda == 7 else ""
        posts.append(
            f"Personas dentro de intensidad MMI≥6: {format_count_prose(tot.pop_mmi6p)}. "
            f"{dentro}"
            f"Edificaciones en MMI≥{banda}: "
            f"{format_count_prose(edificaciones)}."
        )

    # EL MISMO RANKING QUE EL REPORTE, NO OTRO.
    #
    # Esto leia `top_municipios` crudo, que viene ordenado por la porcion de la
    # banda mas alta: para Muisne el `report.md` decia Portoviejo / Esmeraldas /
    # Quinindé y este hilo decia Pedernales / Jama / Muisne. Dos respuestas a la
    # misma pregunta sobre el mismo evento, publicadas a la vez.
    expuestos = municipios_del_ranking(report)
    if expuestos:
        nombres = ", ".join(m.nombre for m in expuestos[:3])
        posts.append(f"Municipios más expuestos (MMI≥{banda_del_ranking(report)}): {nombres}.")
    elif not report.preliminar:
        # Y cuando no hay ninguno se dice, en vez de nombrar a los tres primeros
        # de una lista de ceros — que es lo que hacia con los sismos mar adentro.
        # «LA SACUDIDA FUE MAR ADENTRO» ERA FALSO EN UNO DE LOS CINCO.
        #
        # `usp000jd2q` tiene el epicentro a 5 km de Baní, **tierra adentro** en
        # República Dominicana, y este hilo afirmaba que fue mar adentro. El
        # `.md` ya decía la version correcta —«mar adentro **o sobre zona
        # despoblada**»— y el hilo se quedo con la mitad falsa.
        #
        # Afirmar de menos cuesta una palabra; afirmar de mas cuesta la
        # credibilidad de todo lo demas que el hilo dice.
        posts.append(
            "Ningún municipio del país queda con población dentro de las bandas de "
            "intensidad de este evento: la sacudida quedó mar adentro o sobre zona "
            "despoblada."
        )

    # EL ENLACE VA AL VISOR, NO A LA CARPETA DEL REPORTE.
    #
    # Aqui decia `{SITIO_PUBLICADO}/reports/{ev.usgs_id}/`, que **es un 404**:
    # P3 emite `report.json`, `report.md`, los CSV y los PNG, pero no un
    # `index.html`, y GitHub Pages no lista directorios. Los veintisiete hilos
    # publicados terminaban en un enlace muerto — y el hilo es el unico paso
    # manual que todo el sistema se permite, o sea que lo roto estaba justo en
    # lo unico que un humano publica a mano.
    #
    # `?evento=` lo lee `leerUrl()` en `site/assets/app.js` y abre el reporte
    # con su mapa, su panel y la franja de «exposicion no es daño» arriba. Es
    # ademas mejor destino que la carpeta: se entiende sin saber leer un JSON.
    posts.append(
        "Exposición no es daño. CENTINELA no es alerta temprana ni reemplaza a los "
        "servicios geológicos ni a las unidades de gestión del riesgo. "
        "Datos abiertos y metodología: "
        f"{SITIO_PUBLICADO}/?evento={ev.usgs_id}"
    )

    return [_truncate(p) for p in posts]


def render_thread_text(report: Report) -> str:
    """El hilo como ``hilo.txt``, separado por lineas en blanco dobles."""
    posts = render_thread(report)
    total = len(posts)
    numerados = [f"{i}/{total} {post}" for i, post in enumerate(posts, start=1)]
    return "\n\n".join(numerados) + "\n"


def _truncate(text: str) -> str:
    if len(text) <= MAX_CHARS:
        return text
    return text[: MAX_CHARS - 1].rstrip() + "…"


def _utc_legible(utc: str) -> str:
    """`2016-04-16T23:58:36Z` -> `2016-04-16 23:58 UTC`.

    La marca ISO es exacta y no se lee. Se conserva entera en `report.json`;
    aqui manda que un humano pueda leerla de un vistazo.
    """
    limpia = utc.rstrip("Z").replace("T", " ")
    return f"{limpia[:16]} UTC" if len(limpia) >= 16 else f"{limpia} UTC"
