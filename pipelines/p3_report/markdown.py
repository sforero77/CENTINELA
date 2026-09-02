"""Render de ``report.md`` desde ``report.json``.

Restriccion de diseno (RNF-05): el reporte debe ser legible en un movil con 3G
en zona de desastre. Markdown plano, sin imagenes embebidas, md + png < 500 KB.
"""

from __future__ import annotations

from typing import Final

from ..common.constants import DISCLAIMERS, GROUND_FAILURE_HIGH_PROB, TOP_ADM2_COUNT
from ..common.formatting import format_count_prose, format_number_es
from .model import (
    MunicipioTop,
    Report,
    banda_del_ranking,
    municipios_del_ranking,
    poblacion_del_ranking,
)

#: El nivel de PAGER en espanol.
#:
#: USGS lo publica en ingles —"orange"— y este documento se lee en espanol:
#: dejarlo crudo obliga a traducir mentalmente la unica cifra ajena que el
#: reporte cita. El visor ya lo traducia, asi que los dos artefactos del mismo
#: evento decian "orange" y "naranja" — la clase de costura que hace dudar del
#: resto.
PAGER_ES: Final[dict[str, str]] = {
    "green": "verde",
    "yellow": "amarilla",
    "orange": "naranja",
    "red": "roja",
}

_ENCABEZADO_PRELIMINAR = (
    "> **Reporte preliminar sin ShakeMap.** El corte es por radios alrededor "
    "del epicentro, no por intensidad modelada. Se actualiza automáticamente "
    "en cuanto USGS publique el ShakeMap del evento."
)

#: Aviso de reconstruccion retrospectiva. No es un matiz menor: cambia lo que
#: las cifras significan. La poblacion puede ser de la epoca del sismo —GHS-POP
#: publica de 1975 a 2030 en pasos de cinco anos— pero las edificaciones, las
#: vias y el equipamiento son **los de hoy**, porque OpenStreetMap y Overture no
#: guardan el pasado. Un lector que no lo sepa leeria "444.281 edificaciones
#: expuestas" como si hubieran existido entonces.
_ENCABEZADO_BACKTEST = (
    "> **Reconstrucción retrospectiva.** Este reporte se calculó después del "
    "evento, no en respuesta a él, y no cuenta para las métricas de latencia "
    "del sistema.\n"
    ">\n"
    "> La **población** corresponde a la época indicada en el manifiesto de "
    "exposición. Las **edificaciones, vías, sedes de salud y educativas son las "
    "actuales**: OpenStreetMap y Overture publican el estado presente, no el "
    'histórico. Léelas como "qué infraestructura de hoy caería en esa zona de '
    'intensidad", no como lo que había entonces.'
)


def render_markdown(report: Report) -> str:
    """Genera el markdown del reporte en espanol neutro (RF-06)."""
    ev = report.event
    tot = report.totales
    partes: list[str] = []

    # `M7,8` y no `M7.8`: el visor y el hilo ya escriben la magnitud con coma,
    # y el mismo evento no puede salir de dos maneras segun donde se lea.
    partes.append(f"# Exposición sísmica — M{format_number_es(ev.mag, 1)} · {ev.lugar}")
    partes.append(
        f"**Evento USGS:** `{ev.usgs_id}` · **Origen:** {ev.utc} UTC · "
        f"**Profundidad:** {format_number_es(ev.depth_km, 1)} km"
    )
    if report.preliminar:
        partes.append(_ENCABEZADO_PRELIMINAR)
    if report.backtest:
        partes.append(_ENCABEZADO_BACKTEST)

    if report.preliminar:
        # Un preliminar publica la tabla por radios **en lugar** de la de
        # intensidad, no ademas. Sin ShakeMap todas las cifras por MMI valen
        # cero, y una tabla de ceros con el titulo "Exposicion estimada" es una
        # respuesta falsa y creible: el unico error que este sistema no puede
        # permitirse. Mejor una cifra mas pobre y verdadera.
        partes.append("## Población por distancia al epicentro")
        partes.append(_tabla_radios(report))
    else:
        partes.append("## Exposición estimada")
        partes.append(_tabla_totales(report))
        # DE CUÁNTO SON ESTAS CIFRAS.
        #
        # La regla es de la espec —RF-06, dos cifras significativas en prosa— y
        # es la correcta: nadie necesita el 107.904 de un modelo de exposición.
        # Lo que faltaba era decirlo. El visor publica el mismo dato con
        # redondeo de tabla ("108.000") y este documento con redondeo de prosa
        # ("110 mil"): las dos cifras son ciertas y quien las compare sin saber
        # la regla concluye que una de las dos está mal.
        partes.append(
            "Las cifras de esta tabla van redondeadas a dos cifras "
            "significativas, que es la precisión que un modelo de exposición "
            "sostiene. Las exactas están en el CSV municipal y en `report.json`."
        )

    if tot.pop_65p_mmi7p and not report.preliminar:
        partes.append(
            f"De la población en intensidad MMI≥7, alrededor de "
            f"**{format_count_prose(tot.pop_65p_mmi7p)}** personas tienen 65 años o más."
        )

    if report.top_municipios:
        # El encabezado y la tabla, con la MISMA banda. Cada uno la calculaba por
        # su cuenta, que es como se llega a un titulo que promete una columna y
        # una columna que trae otra.
        partes.append(
            f"## Municipios más expuestos, por población en MMI≥{_banda_del_ranking(report)}"
        )
        partes.append(_tabla_municipios(report))

    partes.append(_seccion_ground_failure(report))

    if ev.pager_alert:
        partes.append(
            f"## Referencia cruzada\n\n"
            f"PAGER (USGS) estima para este evento una alerta "
            f"**{PAGER_ES.get(ev.pager_alert, ev.pager_alert)}**. "
            f"CENTINELA no estima víctimas; la cifra se incluye solo como contraste.\n\n"
            + NOTA_BANDAS_PAGER
        )

    partes.append(_seccion_incertidumbre(report))

    if report.changelog:
        partes.append(
            "## Cambios frente a la versión anterior\n\n"
            + "\n".join(f"- {linea}" for linea in report.changelog)
        )

    partes.append(_seccion_descargas(report))
    partes.append(_seccion_procedencia(report))
    partes.append("## Advertencias\n\n" + "\n".join(f"- {d}" for d in DISCLAIMERS))

    return "\n\n".join(p for p in partes if p) + "\n"


def _tabla_radios(report: Report) -> str:
    """Poblacion dentro de cada radio, con su advertencia (RF-03)."""
    if not report.radios:
        return (
            "No se pudo calcular el corte por radios: no hay activo de exposición "
            "para el país del epicentro."
        )
    lineas = ["| Radio desde el epicentro | Población |", "|---|---:|"]
    for r in sorted(report.radios, key=lambda x: x.radio_km):
        lineas.append(f"| {r.radio_km} km | {format_count_prose(r.pop)} |")
    return "\n".join(lineas) + (
        "\n\nLos radios **no son bandas de intensidad**. Aquí no hay modelo de "
        "sacudida, solo distancia: un sismo superficial y uno profundo de la misma "
        "magnitud tienen el mismo circulo y no se parecen en nada. La cifra sirve "
        "para dimensionar, no para priorizar."
    )


def _tabla_totales(report: Report) -> str:
    tot = report.totales
    filas = [
        ("Población en MMI≥6", format_count_prose(tot.pop_mmi6p)),
        ("Población en MMI≥7", format_count_prose(tot.pop_mmi7p)),
        ("Población en MMI≥8", format_count_prose(tot.pop_mmi8p)),
        ("Edificaciones en MMI≥7", format_count_prose(tot.bld_mmi7p)),
        ("Sedes de salud en MMI≥7", format_number_es(tot.health_mmi7p)),
        ("Sedes educativas en MMI≥7", format_number_es(tot.edu_mmi7p)),
    ]
    # Se publican por separado a proposito: no es lo mismo que quede cortada
    # una troncal que una calle de barrio, y la red principal es ademas la
    # cifra comparable con las estadisticas viales oficiales. Un solo numero
    # que las sume esconde las dos cosas.
    if tot.road_km_principal_mmi7p > 0:
        local = max(tot.road_km_mmi7p - tot.road_km_principal_mmi7p, 0.0)
        filas.append(
            (
                "Vías primarias y secundarias en MMI≥7",
                format_count_prose(tot.road_km_principal_mmi7p) + " km",
            )
        )
        filas.append(("Vías locales en MMI≥7", format_count_prose(local) + " km"))
    else:
        filas.append(("Kilómetros de vía en MMI≥7", format_count_prose(tot.road_km_mmi7p) + " km"))
    if tot.built_m2_mmi7p > 0:
        km2 = tot.built_m2_mmi7p / 1_000_000.0
        filas.append(("Superficie construida en MMI≥7", f"{format_number_es(km2, 1)} km²"))
    lineas = ["| Indicador | Estimado |", "|---|---:|"]
    lineas += [f"| {nombre} | {valor} |" for nombre, valor in filas]
    return "\n".join(lineas) + _nota_del_muro_de_ceros(report) + _nota_superficie(report)


#: Superficie media de una edificacion, en m², para contrastar el conteo de
#: Overture con la superficie que ve el satelite. Es un orden de magnitud
#: deliberadamente conservador: sirve para detectar un hueco de mapeo grande,
#: no para estimar edificaciones.
M2_POR_EDIFICACION = 100.0

#: A partir de que proporcion se considera que falta mapeo. 1,5 significa que el
#: satelite ve un 50 % mas de lo que explicarian las edificaciones registradas.
UMBRAL_HUECO_MAPEO = 1.5


def _nota_superficie(report: Report) -> str:
    """Advierte cuando el satelite ve mucho mas construido de lo mapeado.



    Es la unica forma que tiene el reporte de decir "esta cifra se queda corta"

    sin callarse ni inventar. El hueco de OSM se concentra en asentamientos

    informales y zona rural dispersa, o sea en la población más expuesta: darlo

    por bueno seria publicar una cobertura que no existe (§6.4).

    """
    tot = report.totales
    if tot.built_m2_mmi7p <= 0 or tot.bld_mmi7p <= 0:
        return ""
    esperado = tot.bld_mmi7p * M2_POR_EDIFICACION
    if tot.built_m2_mmi7p < esperado * UMBRAL_HUECO_MAPEO:
        return ""
    veces = tot.built_m2_mmi7p / esperado
    return (
        f"\n\nEl satélite detecta **{format_number_es(veces, 1)} veces** más superficie "
        f"construida de la que explicarían las {format_count_prose(tot.bld_mmi7p)} "
        f"edificaciones registradas. La diferencia suele ser asentamiento informal o "
        f"zona rural dispersa sin mapear: **el conteo de edificaciones se queda corto "
        f"ahí, y la superficie construida no**."
    )


def _nota_del_muro_de_ceros(report: Report) -> str:
    """Por que la tabla entera vale cero, cuando vale cero.

    SIETE CEROS SEGUIDOS NO INFORMAN: SE LEEN COMO "NO SE PUDO CALCULAR".

    `us1000c2zy` es un M7,5 cuyo ShakeMap llega a MMI 8, y publicaba siete
    filas en cero sin una palabra. Se pudo calcular perfectamente: la sacudida
    fue mar adentro y la intensidad no alcanza banda sobre territorio habitado.
    Es un resultado, y uno que le importa a quien decide si moviliza.

    Es el mismo remedio que :func:`_linea_ground_failure` ya aplica a su propio
    cero, aqui aplicado al que ocupa la tabla entera.
    """
    if report.preliminar or report.totales.banda_titular:
        return ""
    return (
        "\n\n> **Todas las cifras en cero es un resultado, no un fallo.** El "
        "ShakeMap de este evento sí dibuja intensidad, pero no alcanza MMI≥6 "
        "sobre territorio habitado del país: la sacudida quedó mar adentro o "
        "sobre zona despoblada. El cálculo corrió entero."
    )


def _banda_del_ranking(report: Report) -> int:
    """La banda por la que se ordenan los municipios. Vive en el modelo.

    Estuvo aqui, y el `hilo.txt` calculaba la suya: el mismo evento salia con
    dos rankings distintos. Ver :func:`model.municipios_del_ranking`.
    """
    return banda_del_ranking(report)


def _tabla_municipios(report: Report) -> str:
    """Ranking municipal, rotulado con la banda que este evento alcanzo.



    Dos cosas que la tabla daba por supuestas y no son ciertas fuera de

    Colombia:



    **La banda.** La columna decia siempre "Población MMI≥7", y casi la mitad

    de los sismos reales de LATAM no llegan ahi sobre población: para ellos eran

    quince ceros bajo un rotulo que prometia cifras. Tehuantepec 2017, M8,2, se

    publicaba asi.



    **El codigo.** Decia "DIVIPOLA", que es el codigo municipal **de

    Colombia**. En el reporte de Tehuantepec rotulaba `MX20043` como DIVIPOLA.

    El sistema cubre diecinueve países y cada uno nombra el suyo: se rotula por

    lo que es —un codigo de municipio— y el país lo pone el manifest.

    """
    # LA BANDA DEL RANKING ES LA DEL RESTO DEL REPORTE.
    #
    # `banda_titular` devuelve 8 en cuanto alguien queda dentro de MMI≥8, y
    # entonces la tabla ordenaba por esa porcion: en Muisne salia Muisne con
    # 8.800 y Quinindé, Esmeraldas, Chone y Portoviejo con **0** — teniendo
    # 164.691, 297.596, 150.742 y 333.075 personas en MMI≥7. Nueve de las quince
    # filas eran ceros, y el municipio mas expuesto del evento era uno de ellos.
    #
    # Se ordena por MMI≥7, que es donde estan todas las demas cifras del
    # reporte, y solo se baja a 6 cuando el evento no llego a 7 sobre poblacion
    # — el caso para el que `pop_banda` se invento, y ahi sigue sirviendo.
    banda = _banda_del_ranking(report)
    ordenados = municipios_del_ranking(report)

    # UNA CABECERA SIN FILAS NO ES UNA TABLA VACIA: ES UNA PREGUNTA SIN
    # RESPONDER. `us1000c2zy` publicaba exactamente eso —dos lineas de cabecera
    # y nada debajo— siendo un M7,5 cuyo ShakeMap llega a MMI 8 mar adentro. La
    # respuesta existe y es interesante: la intensidad si alcanzo esa banda,
    # pero no sobre poblacion de este pais.
    if not ordenados:
        return (
            f"Ningún municipio del país alcanza población dentro de MMI≥{banda}. "
            "No es que falte el dato: la intensidad que el ShakeMap dibuja para "
            "este evento no llega a esa banda sobre territorio habitado."
        )

    def _cifra(m: MunicipioTop) -> float:
        return poblacion_del_ranking(report, m)

    lineas = [
        f"| # | Municipio | Código | MMI max | Población MMI≥{banda} |",
        "|---:|---|---|---:|---:|",
    ]
    for i, m in enumerate(ordenados[:TOP_ADM2_COUNT], start=1):
        cifra = _cifra(m)
        lineas.append(
            f"| {i} | {m.nombre} | `{m.adm2_id}` | "
            f"{format_number_es(m.mmi_max, 1)} | {format_count_prose(cifra)} |"
        )
    return "\n".join(lineas)


#: Como se nombra cada modelo en prosa. La palabra importa: el modelo de
#: licuefaccion de Zhu (2017) no entrega probabilidad sino **cobertura areal**
#: —la fraccion de la celda que se espera cubierta—, y llamarla "probabilidad
#: alta" afirma algo que el modelo no dice.
GF_UNIDAD: dict[str, str] = {
    "ls": "probabilidad de deslizamiento",
    "lq": "cobertura areal por licuefacción",
}

#: Alertas de USGS, en el idioma del reporte. La unica cifra ajena que el
#: reporte cita ya sale traducida para PAGER; esta sale por el mismo sitio.
GF_ALERTA_ES: dict[str, str] = {
    "green": "verde",
    "yellow": "amarilla",
    "orange": "naranja",
    "red": "roja",
}


def _linea_ground_failure(report: Report, tipo: str, propia: float) -> str:
    """Una linea de falla de terreno: la cifra propia y la de USGS al lado.

    Las dos, siempre que USGS publique alerta. Publicar la nuestra sola invita
    a leerla como la de USGS, y son dos cortes distintos del mismo raster: aqui
    se cuenta la poblacion **entera** de toda celda por encima del umbral; USGS
    pondera la poblacion de cada celda **por** el valor de esa celda.
    """
    gf = report.ground_failure_usgs
    etiqueta = "deslizamiento" if tipo == "ls" else "licuefacción"
    umbral = format_number_es(GROUND_FAILURE_HIGH_PROB, 2)
    linea = (
        f"- **{etiqueta.capitalize()}.** Población en celdas donde el modelo espera "
        f"≥ {umbral} de {GF_UNIDAD[tipo]}: **{format_count_prose(propia)}**."
    )
    if not gf.alerta_viva(tipo):
        return linea

    alerta = getattr(gf, f"{tipo}_alerta_usgs").lower()
    pop_usgs = getattr(gf, f"{tipo}_pop_usgs")
    color = GF_ALERTA_ES.get(alerta, alerta)
    cruzada = f" USGS declara para este evento alerta **{color}**"
    if pop_usgs:
        cruzada += f", con {format_count_prose(float(pop_usgs))} expuestas"
    # El caso que esta linea existe para tapar: nuestro conteo da cero y USGS
    # no dice verde. El cero es cierto —ninguna celda llega al umbral— y solo
    # se lee como "aqui no hay exposicion a esto".
    if propia <= 0:
        cruzada += (
            ". El cero de arriba no dice que no haya exposición: dice que ninguna celda "
            "llega al umbral"
        )
    return linea + cruzada + "."


#: LA OBJECION QUE HUNDE EL PROYECTO EN UNA REUNION, RESUELTA EN DOS LINEAS.
#:
#: PAGER tabula su exposicion por **MMI redondeado**: su fila "7" es todo lo que
#: cae entre 6,5 y 7,49. CENTINELA publica **bandas literales**: MMI≥7 es MMI≥7.
#: Puestas una al lado de la otra sin decirlo, las dos cifras del mismo evento
#: parecen contradecirse por un factor de casi tres, y la lectura por defecto es
#: que CENTINELA subcuenta.
#:
#: No se contradicen. Para el Choco, las cifras de CENTINELA caen exactamente
#: dentro del intervalo que las filas de PAGER acotan por arriba y por abajo:
#: PAGER da 10.487.959 en su fila 6 (o sea ≥5,5) y 6.514.486 en la 7 (≥6,5), y
#: CENTINELA da 6.960.086 en ≥6,0 y 2.415.793 en ≥7,0. Es el unico acuerdo
#: aritmeticamente posible entre dos convenciones de banda distintas.
NOTA_BANDAS_PAGER = (
    "Las dos cifras **no se tabulan igual**: PAGER agrupa por MMI redondeado "
    "—su fila «7» es todo lo que cae entre 6,5 y 7,49— y CENTINELA usa bandas "
    "literales, donde MMI≥7 es MMI≥7. Comparadas de frente parecen "
    "discrepar; puestas en el mismo eje, cada cifra de aquí cae dentro del "
    "intervalo que las filas de PAGER acotan por arriba y por abajo."
)


def _seccion_ground_failure(report: Report) -> str:
    """Seccion de falla de terreno; se omite con nota si no hay producto (G3)."""
    if report.inputs.groundfailure_version == 0:
        return (
            "## Deslizamiento y licuefacción\n\n"
            "USGS no ha publicado el producto *Ground Failure* para este evento. "
            "La sección se omite; el reporte se re-emite automáticamente si aparece."
        )
    tot = report.totales
    return (
        "## Deslizamiento y licuefacción\n\n"
        + _linea_ground_failure(report, "ls", tot.pop_ls_alta)
        + "\n"
        + _linea_ground_failure(report, "lq", tot.pop_lq_alta)
        + "\n\n"
        "Las dos cifras se cuentan sobre las celdas del corte publicado (MMI≥6). "
        "**No son las de USGS y no se pueden comparar de frente**: aquí se cuenta la "
        "población entera de toda celda por encima del umbral, y USGS pondera la "
        "población de cada celda por el valor de esa celda. Son dos preguntas "
        "distintas sobre el mismo ráster.\n\n"
        "Fuente: producto *Ground Failure* de USGS "
        f"(v{report.inputs.groundfailure_version}), dominio público."
    )


def _seccion_incertidumbre(report: Report) -> str:
    inc = report.incertidumbre
    lineas = [
        "## Incertidumbre y calidad",
        "",
        # "Área afectada" es vocabulario de dano, y es lo unico que el
        # DISCLAIMER promete no decir que se colo en los veintiun reportes.
        # Lo que se mide es la discrepancia dentro del corte publicado, que es
        # donde hay celdas, no donde hay dano.
        # "0,0 %" se lee como "los dos productos coinciden perfectamente", y
        # cuando el valor es nulo significa lo contrario: no habia con que
        # comparar. Tres reportes publicaban ese cero.
        (
            "Discrepancia entre GHS-POP y WorldPop en las bandas MMI publicadas: "
            f"**{format_number_es(inc.pop_discrepancia_pct, 1)} %**."
            if inc.pop_discrepancia_pct is not None
            else "Discrepancia entre GHS-POP y WorldPop: **no se pudo medir**. "
            "Ninguna celda dentro de las bandas publicadas tiene población de "
            "WorldPop con la que contrastar."
        ),
    ]
    if inc.notas:
        lineas += ["", *[f"- {nota}" for nota in inc.notas]]
    return "\n".join(lineas)


def _seccion_descargas(report: Report) -> str:
    d = report.descargas
    enlaces = [
        ("GeoParquet (celdas H3 r8)", d.geoparquet),
        ("PMTiles (visor)", d.pmtiles),
        ("CSV por municipio", d.csv_adm2),
        ("Mapa PNG", d.mapa_png),
    ]
    disponibles = [f"- [{nombre}]({url})" for nombre, url in enlaces if url]
    if not disponibles:
        return ""
    return "## Descargas\n\n" + "\n".join(disponibles)


def _seccion_procedencia(report: Report) -> str:
    return (
        "## Procedencia\n\n"
        f"- ShakeMap consumido: **v{report.inputs.shakemap_version}**\n"
        f"- Ground Failure consumido: **v{report.inputs.groundfailure_version}**\n"
        f"- Manifiesto de exposición: `{report.inputs.exposure_manifest}`\n"
        f"- Pipeline: `{report.pipeline_version}` · Generado: {report.generado_utc}"
    )
