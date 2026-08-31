"""Invariantes cartograficos del visor, de la auditoria de UX/UI del 25-ago-2026.

El visor no tiene suite propia —es una pagina estatica sin build— asi que lo
que se puede vigilar desde aqui es su **codigo fuente**: que las decisiones que
costo encontrar sigan escritas donde tienen que estar. No sustituye a mirar la
pantalla; impide que un cambio distraido deshaga lo que mirarla enseno.

Los cuatro hallazgos que fijan estas pruebas salieron de abrir el visor
publicado con datos reales, no de leerlo.
"""

from __future__ import annotations

import json
import math
import re
from itertools import pairwise
from pathlib import Path

import pytest

RAIZ = Path(__file__).parent.parent.parent
APP = (RAIZ / "site" / "assets" / "app.js").read_text(encoding="utf-8")


def cuerpo(nombre: str) -> str:
    """El cuerpo entero de una funcion de `app.js`, hasta su llave de cierre.

    Cortar N caracteres desde el nombre es lo que se hacia antes, y fallo cinco
    veces en un dia: cada vez que una funcion crecia, las aserciones del final
    quedaban fuera del corte y la prueba pasaba a comprobar el hueco. Una vez
    dio rojo sin motivo y cuatro veces habria dado **verde sobre codigo que ya
    no miraba**, que es lo peligroso.

    La llave de cierre a principio de linea delimita la funcion sin ambiguedad
    en este fichero, donde todo va indentado con dos espacios.
    """
    ini = APP.index(f"function {nombre}")
    return APP[ini : APP.index(chr(10) + "}", ini)]


def sin_comentarios_js(js: str) -> str:
    """JavaScript sin sus comentarios, para que un guardia mire el codigo.

    La sexta ocasion del mismo patron en dos dias, y la que decidio generalizar
    el ayudante: el comentario que explicaba por que salud y educacion suben de
    posicion decia "518 sedes de salud", y la prueba del orden encontraba esa
    linea antes que la del codigo.

    Solo quita comentarios de linea completa. Uno al final de una linea de
    codigo se queda, porque quitarlo bien exige saber si el `//` esta dentro de
    una cadena o de una expresion regular — y este fichero no tiene ninguno que
    estorbe.
    """
    limpio = re.sub(r"/\*.*?\*/", "", js, flags=re.S)
    return chr(10).join(
        linea for linea in limpio.splitlines() if not linea.lstrip().startswith("//")
    )


def sin_comentarios(css: str) -> str:
    """El CSS sin sus comentarios, para que un guardia mire el codigo.

    Cuarta vez en dos dias que una prueba de este repositorio empareja texto y
    encuentra la explicacion en vez de la regla: paso con `src.read(1)` citado
    en un docstring, con `gh workflow run site.yml` en el cuerpo de un issue,
    con `WHERE` en un comentario de SQL, y aqui con `bottom: 58px` en el
    comentario que explica por que ya no esta.

    El patron es siempre el mismo y la leccion tambien: un guardia de texto
    tiene que quitar los comentarios del medio que inspecciona **antes** de
    buscar. Si no, cuanto mejor se documenta un arreglo, mas probable es que su
    propia prueba lo de por roto.
    """
    return re.sub(r"/\*.*?\*/", "", css, flags=re.S)


REPORTS = RAIZ / "reports"


# --- El encuadre tiene que incluir el epicentro -----------------------------


def _epicentro_y_malla(usgs_id: str) -> tuple[tuple[float, float], list[str]] | None:
    """Epicentro del evento y los indices H3 de su malla."""
    reporte = REPORTS / usgs_id / "report.json"
    celdas = REPORTS / usgs_id / "celdas.json"
    if not (reporte.is_file() and celdas.is_file()):
        return None
    ev = json.loads(reporte.read_text(encoding="utf-8"))["event"]
    malla = json.loads(celdas.read_text(encoding="utf-8"))["celdas"]
    if not malla:
        return None
    return (float(ev["lon"]), float(ev["lat"])), [c[0] for c in malla]


def _eventos_con_malla() -> list[str]:
    return sorted(p.parent.name for p in REPORTS.glob("*/celdas.json"))


def test_hay_eventos_con_los_que_comprobar() -> None:
    """Sin catalogo, las pruebas de abajo pasarian vacias."""
    assert len(_eventos_con_malla()) >= 15


@pytest.mark.geo
def test_en_algun_evento_el_epicentro_cae_fuera_de_la_malla() -> None:
    """La prueba que documenta por que el encuadre no puede ser solo la malla.

    Medido sobre el catalogo: en Carupano, La Libertad y Bartolome Maso el
    epicentro cae fuera de la caja de la malla, y en Cuba salia cortado por el
    borde inferior de la pantalla. Son sismos mar adentro, que en esta region
    son la mitad.

    Si algun dia esto deja de fallar sera porque el catalogo cambio, no porque
    el problema desaparezca: basta un evento costero para que vuelva.
    """
    import h3

    fuera = []
    for usgs_id in _eventos_con_malla():
        datos = _epicentro_y_malla(usgs_id)
        if datos is None:
            continue
        (lon, lat), indices = datos
        pts = [h3.cell_to_latlng(i) for i in indices]
        lons = [p[1] for p in pts]
        lats = [p[0] for p in pts]
        if not (min(lons) <= lon <= max(lons) and min(lats) <= lat <= max(lats)):
            fuera.append(usgs_id)

    assert fuera, "ningun epicentro cae fuera: revisa si el encuadre sigue haciendo falta"


def test_el_encuadre_mete_el_epicentro_en_la_caja() -> None:
    """Ver la afectacion *desde el epicentro* empieza por ver el epicentro."""
    assert "lons.push(epiLon)" in APP, "el encuadre no incluye el epicentro"
    assert "lats.push(epiLat)" in APP
    assert "fitBounds" in APP


# --- La celda tiene que poder citarse ---------------------------------------


def test_el_indice_h3_viaja_hasta_la_ficha() -> None:
    """Un dato que no se puede referenciar es un dato que no se puede usar.

    El indice se excluia de las propiedades del hexagono, y con el se iba la
    unica forma de cruzar lo que se ve en el mapa con el `celdas.json` que el
    propio visor ofrece para descargar.
    """
    assert 'if (nombre !== "h3")' not in APP, "el indice H3 vuelve a excluirse"
    assert "ficha-h3" in APP, "la ficha de celda no publica el indice"


def test_el_indice_de_la_ficha_existe_en_el_fichero_descargable() -> None:
    """El indice que se ensena tiene que ser el mismo que se descarga."""
    for usgs_id in _eventos_con_malla()[:3]:
        datos = json.loads((REPORTS / usgs_id / "celdas.json").read_text(encoding="utf-8"))
        assert datos["columnas"][0] == "h3"
        assert all(isinstance(c[0], str) and len(c[0]) == 15 for c in datos["celdas"][:20])


# --- La distancia al epicentro ----------------------------------------------


def test_el_visor_mide_la_distancia_con_el_radio_del_pipeline() -> None:
    """Dos numeros distintos para la misma distancia serian lo peor.

    Uno en el mapa y otro en el reporte, sobre el mismo par de puntos, es la
    clase de discrepancia que destruye la confianza en todo lo demas.
    """
    from pipelines.common.geo import EARTH_RADIUS_M

    esperado = EARTH_RADIUS_M / 1000.0
    assert f"RADIO_TIERRA_KM = {esperado:.4f}" in APP, (
        f"el visor no usa el radio del pipeline ({esperado:.4f} km)"
    )
    assert "Al epicentro" in APP, "la ficha no dice a que distancia esta la celda"


def test_la_formula_del_visor_da_lo_mismo_que_la_del_pipeline() -> None:
    """Se reimplementa el haversine del visor y se compara con el de Python."""
    from pipelines.common.geo import EARTH_RADIUS_M, haversine_km

    radio = EARTH_RADIUS_M / 1000.0

    def como_el_visor(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
        rad = math.pi / 180
        dlat = (lat2 - lat1) * rad
        dlon = (lon2 - lon1) * rad
        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(lat1 * rad) * math.cos(lat2 * rad) * math.sin(dlon / 2) ** 2
        )
        return 2 * radio * math.asin(min(1.0, math.sqrt(a)))

    for lon1, lat1, lon2, lat2 in (
        (-76.24, 4.84, -75.69, 4.81),
        (-77.11, 19.86, -76.9, 20.1),
        (-67.22, 10.61, -66.9, 10.5),
    ):
        assert como_el_visor(lon1, lat1, lon2, lat2) == pytest.approx(
            haversine_km(lon1, lat1, lon2, lat2), rel=1e-9
        )


# --- La profundidad -------------------------------------------------------


def test_la_profundidad_se_publica_como_distintivo() -> None:
    """Es lo que explica un M8,2 con cero personas en MMI≥7.

    Estaba en una linea de metadatos entre la fecha y la version del ShakeMap.
    Un lector que ve "M8,2" y "0 personas" sin ver "47 km" no tiene con que
    entenderlo.
    """
    assert "claseDeProfundidad" in APP
    for etiqueta in ("superficial", "intermedio", "profundo"):
        assert etiqueta in APP, f"falta la clase de profundidad '{etiqueta}'"


def test_los_cortes_de_profundidad_son_los_de_sismologia() -> None:
    """70 y 300 km. No son elegidos aqui: son los estandar."""
    assert "km < 70" in APP
    assert "km <= 300" in APP


# --- La carrera que dejaba el mapa en blanco --------------------------------


def test_la_puerta_del_estilo_no_depende_de_un_evento_que_ya_paso() -> None:
    """`once("load")` dispara una vez; si ya paso, el aviso se pierde.

    Reproducido en el visor publicado: abrir un enlace compartido con la cache
    fria dejaba el mapa en blanco —sin base, sin malla, sin leyenda y sin un
    error en consola— mientras que el mismo enlace con la cache caliente
    funcionaba. Le tocaba justo a quien abria el enlace por primera vez.
    """
    assert 'm.once("load"' not in APP, "la puerta del estilo vuelve a usar once('load')"
    assert 'm.on("styledata"' in APP
    assert 'm.on("idle"' in APP


def test_la_puerta_se_desengancha_cuando_termina() -> None:
    """Un oyente que no se quita se acumula en cada evento abierto."""
    assert 'm.off("styledata"' in APP
    assert 'm.off("idle"' in APP


def test_nadie_espera_al_estilo_por_su_cuenta() -> None:
    """La prueba que habria cazado el segundo sitio con el mismo fallo.

    Se arreglo `cuandoElEstiloEsteListo` y no se miro quien mas resolvia lo
    mismo a mano: `dibujarEpicentros` tenia su propio `m.on("load", pintar)` y
    seguia perdiendose el aviso. En el sitio publicado, con la cache fria, salia
    el mapa base entero y ni una estrella encima.

    Es exactamente el patron que esta auditoria persigue —arreglar la funcion y
    no revisar a los llamadores— cometido dentro de la propia auditoria.

    La unica excepcion es el aviso de "cargando", que ademas lleva su propio
    `setTimeout` de red de seguridad: si el mapa no carga, hay que quitarlo
    igual.
    """
    lineas = [
        linea.strip()
        for linea in APP.splitlines()
        if ('m.on("load"' in linea or 'm.once("load"' in linea)
        and not linea.strip().startswith("//")
    ]
    fuera_del_ayudante = [linea for linea in lineas if "listo" not in linea]

    assert fuera_del_ayudante == [], (
        f"Estas esperan al estilo por su cuenta en vez de usar "
        f"`cuandoElEstiloEsteListo`: {fuera_del_ayudante}"
    )


# --- La capa de sismos vistos y no despachados ------------------------------


def test_los_observados_no_usan_la_rampa_de_mmi() -> None:
    """La rampa significa "impacto medido". Prestarsela la vaciaria de sentido.

    Es el riesgo §7 —"cifra alarmista"— en su forma visual: un simbolo pintado
    con los colores de la intensidad se lee como una intensidad medida, diga lo
    que diga el pie.
    """
    ini = APP.index('id: "observados",')
    capa = APP[ini : APP.index("});", ini)]

    for color in ("BANDAS", "RAMPA", "CAPAS[", "EPICENTRO"):
        assert color not in capa, f"la capa de observados toma color de {color}"

    # El gris vive en la estrella que la capa usa, no en su `paint`: la imagen
    # no es SDF y no se puede tintar desde la capa.
    assert '"estrella-gris"' in capa
    assert 'crearEstrella(m, "estrella-gris", OBSERVADO' in APP


def test_un_sismo_menor_se_dibuja_como_un_sismo() -> None:
    """Un circulo no dice "sismo": dice "punto".

    En simbologia la **forma** codifica que es la cosa, y el tamano y el color
    codifican su importancia. Con un circulo para los menores y una estrella
    para los que tienen reporte, el mapa afirmaba que son dos fenomenos
    distintos. Son el mismo, en dos escalas.
    """
    ini = APP.index('id: "observados",')
    capa = APP[ini : APP.index("});", ini)]

    assert 'type: "symbol"' in capa, "sigue siendo un circulo generico"
    assert '"icon-image": "estrella-gris"' in capa


def test_la_estrella_del_menor_es_mas_pequena_que_la_del_reporte() -> None:
    """Misma familia, distinta jerarquia. Si midieran igual, competirian."""
    # Solo el array de `icon-size`: un corte por caracteres se llevaba tambien
    # el 0,9 de `icon-opacity` y daba rojo por un numero que no era un tamano.
    ini = APP.index('"icon-image": "estrella-gris"')
    desde = APP.index('"icon-size"', ini)
    # La linea entera: el primer `]` cierra `["linear"]` y dejaba el corte sin
    # un solo numero, con lo que la prueba fallaba por vacia y no por grande.
    linea = APP[desde : APP.index(chr(10), desde)]
    tamanos = [float(n) for n in re.findall(r"0\.\d+", linea)]

    assert tamanos and max(tamanos) < 0.5, f"la estrella gris es demasiado grande: {tamanos}"


def test_los_observados_arrancan_apagados() -> None:
    """Quien abre el visor viene a ver impacto, no ruido sismico de fondo."""
    js = APP
    capa = js[js.index('id: "observados"') : js.index('id: "observados"') + 400]

    assert 'visibility: "none"' in capa


def test_el_popup_dice_que_no_hay_medicion() -> None:
    """Sin esta frase, un punto en el mapa se lee como impacto cero medido."""
    js = APP

    assert "No se midió su impacto" in js


def test_los_observados_no_llevan_etiqueta_de_magnitud() -> None:
    """Las etiquetas son de los eventos con reporte.

    Poner «M4,9» flotando junto a un punto gris lo equipara visualmente a una
    estrella con reporte, que es justo la jerarquia que hay que mantener.
    """
    js = APP
    capa = js[js.index('id: "observados"') : js.index('id: "observados"') + 900]

    assert "text-field" not in capa


def test_la_capa_se_carga_de_verdad() -> None:
    """Escrita y no llamada seria el patron que esta auditoria persigue."""
    js = APP

    assert "cargarObservados();" in js, "cargarObservados esta definida y nadie la llama"


def test_el_interruptor_solo_aparece_si_hay_algo() -> None:
    """Un control siempre vacio ensena a ignorar los controles."""
    js = APP

    assert "if (!eventos.length) return;" in js


# --- La capa de focos activos -----------------------------------------------


def test_el_fuego_no_toma_prestada_la_rampa_de_mmi() -> None:
    """Dos amenazas distintas con el mismo codigo de color se leen igual.

    La rampa de intensidad va de naranja a rojo oscuro, que es tambien la paleta
    natural del fuego. Inferno acaba en violeta y no se parece a nada mas del
    visor, ademas de ser la convencion en teledeteccion de potencia radiativa.
    """

    def colores_tras(marcador: str) -> set[str]:
        """Los colores del array `colores:` que sigue al marcador.

        Hay que saltar el array de `cortes:`, que va antes y no lleva ninguno.
        """
        trozo = APP.split(marcador, 1)[1].split("colores:", 1)[1]
        return set(re.findall(r"#[0-9a-fA-F]{6}", trozo[: trozo.index("]")]))

    mmi = colores_tras("  mmi: {")
    fuego = set(
        re.findall(
            r"#[0-9a-fA-F]{6}",
            APP.split("const FUEGO_COLORES", 1)[1].split("]", 1)[0],
        )
    )

    assert len(mmi) == 6, f"no se leyo la rampa de MMI: {mmi}"
    assert len(fuego) == 6, f"no se leyo la rampa del fuego: {fuego}"
    assert not (mmi & fuego), f"comparten color: {mmi & fuego}"


def test_los_focos_se_dibujan_como_hexagonos_h3() -> None:
    """Son celdas del mismo activo, no puntos.

    Y con `true` en `cellToBoundary`, que devuelve [lng, lat]: sin el, los
    hexagonos aparecen en el oceano Indico.
    """
    bloque = cuerpo("incendiosAGeoJson")

    assert "h3.cellToBoundary(c.h3, true)" in bloque


def test_la_capa_de_fuego_arranca_apagada() -> None:
    """Quien abre el visor viene a ver un sismo, no la temporada de quemas."""
    bloque = APP[APP.index('id: "incendios",') :][:500]

    assert 'visibility: "none"' in bloque


def test_el_popup_del_fuego_dice_que_no_es_area_quemada() -> None:
    """Sin esa linea, "celda con fuego" se lee como "hectareas quemadas"."""
    assert "no área quemada" in APP


def test_una_poblacion_de_cero_no_se_imprime() -> None:
    """Puede ser que no haya nadie, o que el pais no tenga activo cargado.

    Un cero ahi se leeria como medicion, y es justo la confusion que este
    sistema lleva dos dias persiguiendo.
    """
    bloque = cuerpo("cuadroDeIncendio")

    assert "p.pop > 0 ?" in bloque


def test_la_capa_de_fuego_se_carga_de_verdad() -> None:
    """Escrita y no llamada seria el patron que esta auditoria persigue."""
    assert "cargarIncendios();" in APP


def test_los_focos_se_ven_a_escala_continental() -> None:
    """El fallo que reporto el usuario: "al alejar no se ven los incendios".

    No era intermitente, era aritmetica. Una celda H3 r8 mide 1.063 m de lado a
    lado, y a la escala con la que abre el visor eso son **0,05 pixeles**:

        zoom 3  ->  0,05 px       zoom 9  ->  3,5 px
        zoom 6  ->  0,43 px       zoom 11 -> 13,9 px

    La capa funcionaba perfectamente y era fisicamente invisible por debajo de
    zoom 9. Se arregla con un punto —radio en pixeles de pantalla, que no se
    encoge— por debajo, y el hexagono real por encima.
    """
    assert "const FUEGO_ZOOM_HEX" in APP
    hex_capa = APP[APP.index('id: "incendios",') :][:400]
    punto = APP[APP.index('id: "incendios-punto"') :][:900]

    assert "minzoom: FUEGO_ZOOM_HEX" in hex_capa, "el hexagono se dibuja donde no se ve"
    assert "maxzoom: FUEGO_ZOOM_HEX" in punto, "el punto no cede el sitio al hexagono"
    assert '"circle-radius"' in punto, "el punto tiene que medirse en pixeles de pantalla"


def test_la_fuente_de_hexagonos_no_se_simplifica() -> None:
    """`tolerance` por defecto (0,375) colapsa geometria subpixel.

    Los hexagonos a zoom bajo lo son, asi que desaparecerian antes incluso de
    llegar a dibujarse — y el sintoma seria el mismo que el de arriba, con otra
    causa. Dos causas del mismo sintoma es como se arregla solo una y se cree
    haber terminado.
    """
    bloque = APP[APP.index('m.addSource("incendios",') :][:200]

    assert "tolerance: 0" in bloque


def test_el_punto_tambien_abre_el_popup() -> None:
    """A escala continental solo existe el punto.

    Si solo el hexagono fuera clicable, la capa seria consultable unicamente en
    el zoom en el que casi nadie la mira.

    SEXTA VEZ QUE UN CORTE DE N CARACTERES FALLA. Esta prueba cortaba 400 desde
    un comentario ancla, y el 28-ago-2026 se anadieron tres lineas de comentario
    en medio: el `for` que buscaba quedo fuera de la ventana y la prueba dio rojo
    sin que nada estuviera roto. Es lo mismo que documenta `cuerpo()` —«fallo
    cinco veces en un dia»— y la razon por la que ese ayudante existe.

    Ahora se busca el registro de oyentes por su forma, sin depender de a que
    distancia del comentario quede.
    """
    bloque = cuerpo("dibujarIncendios")
    oyentes = re.search(
        r"for \(const capa of \[([^\]]+)\]\) \{\s*\n\s*m\.on\(\"mouseenter\"", bloque
    )

    assert oyentes is not None, "ya no se registran oyentes de raton sobre las capas de fuego"
    assert '"incendios-punto"' in oyentes.group(1), (
        f"el punto dejo de ser clicable; solo se enganchan {oyentes.group(1)}"
    )


def test_el_modo_gobierna_las_tres_capas_de_fuego() -> None:
    """Punto, relleno y borde. Dejarse una deja fuego encendido en modo sismos.

    Antes esto lo hacia el checkbox de la esquina; ahora lo hace el selector de
    amenaza, y la invariante es la misma: quien apaga el fuego apaga las tres
    capas que lo dibujan.
    """
    bloque = cuerpo("aplicarAmenaza")

    for capa in ("incendios", "incendios-borde", "incendios-punto"):
        assert f'"{capa}"' in bloque

    # Y el contexto del otro lado: los epicentros se atenuan, no desaparecen.
    assert "icon-opacity" in bloque, "en modo fuego los epicentros deben quedar tenues"


# --- UX: que el visor diga lo que sabe --------------------------------------


def test_la_rampa_del_fuego_tiene_leyenda() -> None:
    """Seis colores sin rotulos es peor que no tener color: invita a interpretar.

    La capa se publico el 27-ago-2026 con la rampa inferno y **sin leyenda**.
    Quien viera una celda violeta no tenia forma de saber si eso era mucho o
    poco, ni en que unidad.
    """
    assert "function pintarLeyendaFuego" in APP
    # Se busca la llamada, no una firma concreta: la leyenda pasó a recibir los
    # datos para poder decir que la capa va recortada, y una prueba clavada a
    # `pintarLeyendaFuego();` convertía eso en un fallo rojo sin nada roto.
    assert re.search(r"\n\s*pintarLeyendaFuego\(", APP), "la leyenda existe y nadie la llama"

    bloque = cuerpo("pintarLeyendaFuego")
    assert "Potencia radiativa" in bloque, "la leyenda no dice que mide"
    assert "MW" in bloque, "ni en que unidad"


def test_la_leyenda_del_fuego_repite_lo_que_no_afirma() -> None:
    """La nota del JSON la lee una maquina; esta la lee una persona.

    Y la lee justo cuando esta mirando los colores, que es cuando la tentacion
    de leerlos como area quemada es mayor.
    """
    bloque = cuerpo("pintarLeyendaFuego")

    assert "No es área quemada" in bloque


def test_la_leyenda_del_fuego_sigue_al_modo() -> None:
    """Una leyenda de una capa apagada explica algo que no se ve.

    La invariante sobrevive a la mudanza del checkbox al selector: la leyenda
    del fuego se pinta cuando el fuego manda, y el hueco grande se libera al
    volver a sismos sin evento.
    """
    bloque = cuerpo("aplicarAmenaza")

    assert "pintarLeyendaFuego" in bloque, "el modo fuego no pinta su leyenda"
    assert "hidden = true" in bloque.replace('"leyenda").hidden = true', "hidden = true"), (
        "al salir del modo fuego sin evento, el hueco grande tiene que vaciarse"
    )


def test_el_visor_dice_lo_que_esta_pasando_ahora() -> None:
    """El panorama contaba el archivo: veintiun reportes, quince paises.

    Cierto y muerto. Un sistema de vigilancia que solo ensena su historial se
    lee como un archivo historico, y lo que separa a este de un PDF es que esta
    mirando **ahora**.
    """
    assert "function pintarEnVivo" in APP
    assert "pintarEnVivo();" in APP, "el bloque existe y nadie lo llama"
    assert 'id="en-vivo"' in (RAIZ / "site" / "index.html").read_text(encoding="utf-8")


def test_el_bloque_en_vivo_no_aparece_vacio() -> None:
    """Un panel que dice "Ahora mismo" sin cifras ensena a ignorarlo."""
    bloque = cuerpo("pintarEnVivo")

    assert "if (!partes.length) return;" in bloque


def test_el_latido_respeta_a_quien_pidio_menos_movimiento() -> None:
    """La unica animacion del visor, y no puede imponerse.

    Quieto sigue significando lo mismo: un punto verde junto a "Ahora mismo".
    """
    css = (RAIZ / "site" / "assets" / "styles.css").read_text(encoding="utf-8")

    # Buscando **desde** los keyframes: el visor ya tenia otra regla de
    # movimiento reducido mas arriba, y `index` habria encontrado esa.
    desde = css.index("@keyframes latido")

    assert "prefers-reduced-motion: reduce" in css[desde:], "el latido no se puede desactivar"
    assert ".pulso { animation: none; }" in css[desde:]


def test_la_cifra_en_vivo_lleva_a_verla() -> None:
    """Un numero que dice "569.538 personas bajo fuego" y no lleva a verlas
    es una nota al pie.

    Cerrar la distancia entre la afirmacion y la evidencia es lo que separa un
    tablero de un informe: aqui la cifra **es** el control.
    """
    bloque = cuerpo("pintarEnVivo")

    assert 'data-capa="incendios"' in bloque
    assert 'data-capa="observados"' in bloque
    assert "encenderCapaViva" in APP


def test_la_cifra_viva_es_un_boton_de_verdad() -> None:
    """`<div>` con `onclick` no sale en el orden de tabulacion, no responde a
    Enter y un lector de pantalla no lo anuncia como algo que hace algo.

    Es la diferencia entre parecer interactivo y serlo.
    """
    bloque = cuerpo("pintarEnVivo")

    assert '<button type="button" class="metrica metrica-viva"' in bloque


def test_encender_desde_la_cifra_pasa_por_el_interruptor() -> None:
    """Tocar el mapa directamente separaria el estado del control del real.

    Asi es como se acaba con una capa encendida y su casilla vacia — y con un
    usuario que pulsa la casilla para encender y la apaga.
    """
    bloque = cuerpo("encenderCapaViva")

    # Se FIJA el valor y se despacha `change`, no se alterna con `.click()`.
    # Alternar era exactamente lo que hacia que el boton se comportara como un
    # interruptor: "Ver en el mapa" dice encender, no conmutar.
    assert "casilla.checked = true" in bloque
    assert 'dispatchEvent(new Event("change"' in bloque, (
        "el control tiene que enterarse: escucha `change`"
    )
    assert "casilla.click()" not in bloque, "alternar apagaria lo que el boton dice encender"
    assert "setLayoutProperty" not in bloque, "no puede tocar el mapa por su cuenta"


def test_en_tactil_la_pista_no_depende_del_hover() -> None:
    """Sin hover no hay forma de saber que la cifra hace algo."""
    css = (RAIZ / "site" / "assets" / "styles.css").read_text(encoding="utf-8")

    assert "@media (hover: none)" in css


def test_los_controles_del_mapa_se_apilan_y_no_se_desbordan() -> None:
    """Dos etiquetas con sus conteos no caben en fila en un movil.

    "Focos activos (14.984 celdas en 24 h)" y "Sismos menores vistos (8 en 5
    dias, sin reporte)" una al lado de otra se salian del mapa.
    """
    css = sin_comentarios((RAIZ / "site" / "assets" / "styles.css").read_text(encoding="utf-8"))
    bloque = css[css.index(".controles-mapa {") :][:500]

    assert "flex-direction: column" in bloque
    assert "max-width: calc(100% - 24px)" in bloque


def test_la_leyenda_del_fuego_vive_en_el_hueco_grande() -> None:
    """La tarjeta de esquina murio con el selector de amenaza.

    En modo fuego, la leyenda de potencia radiativa ocupa el mismo hueco que la
    de intensidad en modo sismos — con el mismo derecho y el mismo marcado. Y no
    puede quedar CSS huerfano de la esquina: esta hoja ya se mordio tres veces
    con reglas que sobrevivian a su elemento.
    """
    ini = APP.index("function pintarLeyendaFuego")
    bloque = APP[ini : APP.index(chr(10) + "}", ini)]

    assert '$("leyenda-titulo")' in bloque, "no escribe en el hueco grande"
    assert '$("leyenda-escala")' in bloque
    assert "controles-mapa" not in bloque, "sigue atada a la esquina"

    css = (RAIZ / "site" / "assets" / "styles.css").read_text(encoding="utf-8")
    assert ".leyenda-fuego" not in css, "quedo CSS huerfano de la tarjeta de esquina"


# --- Accesibilidad ----------------------------------------------------------


def test_el_selector_de_capas_se_navega_con_flechas() -> None:
    """`role="tab"` no es una etiqueta: es un contrato.

    ARIA exige que un `tablist` se recorra con flechas y que solo el
    seleccionado este en el orden de tabulacion. Sin eso, llegar al mapa con el
    teclado costaba siete tabulaciones por siete capas — y ninguna hacia nada.
    """
    bloque = cuerpo("pintarSelectorCapas")

    assert "ArrowRight" in bloque and "ArrowLeft" in bloque
    assert "Home" in bloque and "End" in bloque, "faltan los extremos del grupo"


def test_solo_la_capa_activa_entra_en_el_orden_de_tabulacion() -> None:
    """`tabindex` rotatorio: el grupo es una parada, no siete."""
    bloque = cuerpo("pintarSelectorCapas")

    assert 'tabindex="${id === estado.capa ? 0 : -1}"' in bloque


def test_moverse_con_el_teclado_cambia_la_capa() -> None:
    """En un tablist que cambia una vista, seleccionar aparte no vale.

    Tener que confirmar con Enter deja al usuario mirando una capa que no es la
    que tiene el foco — y como el mapa esta al lado, se nota.
    """
    bloque = cuerpo("pintarSelectorCapas")

    assert "destino.focus();" in bloque
    assert "cambiarCapa(destino.dataset.capa);" in bloque


def test_cambiar_de_capa_mueve_el_tabindex() -> None:
    """Si no, tras un clic el orden de tabulacion apunta a la capa anterior."""
    bloque = cuerpo("cambiarCapa")

    assert "aria-selected" in bloque
    assert "tabIndex" in bloque


def test_el_foco_del_selector_se_ve() -> None:
    """Con `tabindex` rotatorio el foco se mueve sin tabular.

    Si no se ve, quien navega con teclado no sabe donde esta.
    """
    css = sin_comentarios((RAIZ / "site" / "assets" / "styles.css").read_text(encoding="utf-8"))

    assert ".capas button:focus-visible" in css


def test_las_rampas_se_distinguen_en_escala_de_grises() -> None:
    """Un mapa tematico que solo funciona en color excluye al 8 % de los hombres.

    La comprobacion es que la luminancia sea **monotona**: si sube o baja sin
    dar marcha atras, las clases se distinguen tambien en gris, impresas, o con
    cualquier daltonismo.
    """

    def luminancia(hexa: str) -> float:
        canales = [int(hexa.lstrip("#")[i : i + 2], 16) / 255 for i in (0, 2, 4)]
        lineal = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in canales]
        return 0.2126 * lineal[0] + 0.7152 * lineal[1] + 0.0722 * lineal[2]

    def colores(marcador: str, tras: str = "") -> list[str]:
        trozo = APP.split(marcador, 1)[1]
        if tras:
            trozo = trozo.split(tras, 1)[1]
        return re.findall(r"#[0-9a-fA-F]{6}", trozo[: trozo.index("]")])

    for nombre, marcador, tras in (
        ("MMI", "  mmi: {", "colores:"),
        ("poblacion", "  pop: {", "colores:"),
        ("fuego", "const FUEGO_COLORES", ""),
    ):
        ls = [luminancia(c) for c in colores(marcador, tras)]
        assert len(ls) == 6, f"la rampa de {nombre} no tiene seis clases"
        sube = all(a < b for a, b in pairwise(ls))
        baja = all(a > b for a, b in pairwise(ls))
        assert sube or baja, f"la rampa de {nombre} no es monotona en luminancia"


def test_ninguna_clase_se_confunde_con_el_suelo_del_mapa() -> None:
    """El error que este repositorio ya corrigio una vez, y que repeti.

    El 25-ago se arreglo que "la coropleta era del color del suelo del mapa". El
    27 elegi inferno para la capa de fuego —una rampa pensada para fondo
    **negro**— y sus dos primeras clases quedaron a 1,2:1 y 1,3:1 sobre
    `BASE_TIERRA`. Invisibles. Y ahi cae la mayoria de las celdas.

    Sobre un suelo de luminancia 0,81 ningun color claro llega a 3:1, asi que el
    umbral realista es 1,6 — y lo que sostiene la legibilidad de las clases
    bajas es el contorno oscuro, no el relleno.
    """

    def luminancia(hexa: str) -> float:
        canales = [int(hexa.lstrip("#")[i : i + 2], 16) / 255 for i in (0, 2, 4)]
        lineal = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in canales]
        return 0.2126 * lineal[0] + 0.7152 * lineal[1] + 0.0722 * lineal[2]

    def contraste(a: str, b: str) -> float:
        alta, baja = sorted((luminancia(a), luminancia(b)), reverse=True)
        return (alta + 0.05) / (baja + 0.05)

    hallado = re.search(r'const BASE_TIERRA = "(#[0-9a-fA-F]{6})"', APP)
    assert hallado, "no se encontro BASE_TIERRA"
    suelo = hallado.group(1)
    fuego = re.findall(r"#[0-9a-fA-F]{6}", APP.split("const FUEGO_COLORES", 1)[1].split("]", 1)[0])

    peor = min(contraste(c, suelo) for c in fuego)
    assert peor >= 1.6, f"la clase mas floja da {peor:.2f}:1 contra el suelo {suelo}"


def test_los_simbolos_de_fuego_llevan_contorno_oscuro() -> None:
    """Sin el, las clases bajas no se separan del fondo por mucho que se sature.

    Es figura-fondo: sobre un mapa base claro, el borde es lo que hace simbolo a
    una mancha de color.
    """
    # Delimitado por la capa siguiente y no por un numero de caracteres: el
    # bloque crecio al anadir una parada de zoom y el corte fijo dejo las
    # aserciones fuera, dando verde sobre codigo que ya no miraba.
    ini = APP.index('id: "incendios-punto"')
    bloque = APP[ini : APP.index('id: "incendios",', ini)]

    assert '"circle-stroke-color": FUEGO_CONTORNO' in bloque
    assert '"circle-stroke-width": 1' in bloque


def test_el_encuadre_inicial_muestra_toda_latam() -> None:
    """`zoom: 3.1` centrado en Colombia dejaba fuera media region.

    Chile, Argentina, Bolivia, Paraguay, Uruguay y el sur de Peru y Brasil
    quedaban fuera de pantalla — y ahi es donde esta la temporada de quemas, asi
    que la capa de fuego se encendia sobre territorio invisible.
    """
    import math

    vista = re.search(
        r"const VISTA_INICIAL = \{ center: \[(-?[\d.]+), (-?[\d.]+)\], zoom: ([\d.]+)", APP
    )
    assert vista, "no se encontro VISTA_INICIAL"
    _lon, lat, zoom = (float(g) for g in vista.groups())

    # El limite real es la ALTURA, no la anchura: el mapa del tablero es
    # apaisado (~954x468) y LATAM es vertical. La primera version de esta prueba
    # solo miraba el ancho y daba por bueno un encuadre que cortaba el sur.
    def latitudes_visibles(alto: int = 468) -> tuple[float, float]:
        centro = math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))
        media = alto / (512 * 2**zoom) * math.pi
        return (
            math.degrees(2 * math.atan(math.exp(centro - media)) - math.pi / 2),
            math.degrees(2 * math.atan(math.exp(centro + media)) - math.pi / 2),
        )

    sur_visible, norte_visible = latitudes_visibles()

    # Lo que se garantiza, y por que: dentro tiene que caber toda la cordillera
    # sismica poblada y toda la franja de quemas. Fuera quedan el norte de
    # Mexico y la Patagonia austral, que es donde menos gente y menos actividad
    # hay — el recorte es una decision, no un descuido.
    for ciudad, latitud in (
        ("Ciudad de Mexico", 19.4),
        ("Bogota", 4.7),
        ("Lima", -12.0),
        ("Santiago", -33.5),
        ("Bahia Blanca", -38.7),
    ):
        assert sur_visible <= latitud <= norte_visible, (
            f"{ciudad} ({latitud}) queda fuera del encuadre inicial "
            f"({sur_visible:.1f} a {norte_visible:.1f})"
        )

    grados_a_lo_ancho = 360.0 / (2**zoom) * (954 / 512)
    assert grados_a_lo_ancho >= 87, "a lo ancho no cabe la region"


def test_el_encuadre_no_se_calcula_al_vuelo() -> None:
    """Costo un mapa completamente en blanco averiguarlo.

    `fitBounds` desde el ayudante de estilo listo se ejecuta con `styledata`,
    que puede llegar antes de que el contenedor tenga su tamano final. La camara
    se calcula entonces contra una caja que aun no mide lo que va a medir, y el
    resultado fue: estilo cargado, capas creadas, atribucion pintada, y ni un
    pixel dibujado.

    Un centro y un zoom no dependen del tamano de la ventana para ser validos.
    Menos elegante y siempre correcto.
    """
    assert "fitBounds(ENCUADRE_LATAM" not in APP


def test_el_fuego_va_debajo_de_los_epicentros() -> None:
    """Miles de simbolos no pueden enterrar a veintiuno.

    La capa de fuego es continental y densa; los sismos con reporte son
    veintiuno y son lo que este sistema existe para publicar. Sin orden
    explicito, la que se dibuja despues gana — y es el fuego.
    """
    bloque = cuerpo("dibujarIncendios")

    assert 'm.getLayer("epicentros-halo") ? "epicentros-halo"' in bloque


def test_el_sobrante_del_encuadre_cae_sobre_el_oceano() -> None:
    """A zoom 2 sobran ~80 grados de longitud, y algo tienen que mostrar.

    Con el centro en el centroide de la region ese sobrante caia sobre Africa
    occidental, con sus etiquetas compitiendo por la atencion en un cuarto del
    mapa. Desplazado al oeste cae sobre el Pacifico, que esta vacio.
    """
    vista = re.search(r"const VISTA_INICIAL = \{ center: \[(-?[\d.]+)", APP)
    assert vista, "no se encontro VISTA_INICIAL"
    lon = float(vista.group(1))

    assert lon <= -80, f"el centro en {lon} deja Africa dentro del encuadre"


# --- Poder salir, y saber que se esta mirando -------------------------------


def test_hay_forma_de_salir_de_un_evento() -> None:
    """La unica salida era el desplegable de la cabecera, y no se lee como salir.

    Quien entraba pulsando un epicentro en el mapa o una fila de la lista —que
    es como se entra— se quedaba dentro sin ruta de vuelta.
    """
    html = (RAIZ / "site" / "index.html").read_text(encoding="utf-8")

    assert 'id="volver"' in html, "no hay boton de volver"
    assert "Volver al panorama" in html
    assert '$("volver")?.addEventListener("click", cerrarDetalle)' in APP


def test_escape_tambien_sale() -> None:
    """Es lo que prueba cualquiera antes de buscar un boton."""
    bloque = cuerpo("engancharSalidas")

    assert '"Escape"' in bloque
    assert "estado.seleccionado" in bloque, "Escape no puede cerrar lo que ya esta cerrado"


def test_al_salir_el_desplegable_vuelve_a_vacio() -> None:
    """Si no, la cabecera sigue diciendo el evento del que acabas de salir."""
    bloque = cuerpo("cerrarDetalle")

    assert 'selector.value = ""' in bloque


def test_el_mapa_dice_que_es_cada_simbolo() -> None:
    """Habia leyenda de la coropleta y de la rampa de fuego, y ninguna de los
    simbolos que estan **siempre** en pantalla.

    Quien abria el visor veia estrellas de dos tamanos y circulos rosados sin
    nada que dijera que eran.
    """
    assert "function pintarLeyendaSimbolos" in APP
    assert "pintarLeyendaSimbolos();" in APP, "la leyenda existe y nadie la llama"

    bloque = cuerpo("pintarLeyendaSimbolos")
    for concepto in ("Sismo con reporte", "Sismo visto, sin reporte", "Foco activo"):
        assert concepto in bloque, f"la leyenda no explica: {concepto}"


def test_la_leyenda_de_simbolos_esta_siempre() -> None:
    """A diferencia de la del fuego, no se apaga: la pregunta "¿que es esto?"
    no depende de que capa este encendida."""
    bloque = cuerpo("pintarLeyendaSimbolos")

    assert "hidden = true" not in bloque


def test_en_un_movil_la_leyenda_de_simbolos_arranca_plegada() -> None:
    """En 390 px de ancho medía 248 —el 64 %— y tapaba medio continente.

    Plegada ocupa una linea. Abierta en pantalla ancha, donde sobra sitio y la
    pregunta merece respuesta sin pedirla.
    """
    bloque = cuerpo("pintarLeyendaSimbolos")

    assert 'createElement("details")' in bloque
    assert 'matchMedia("(min-width: 48rem)")' in bloque
    assert "<summary" in bloque


def test_el_visor_dice_sobre_que_esta_ardiendo() -> None:
    """Es lo que convierte "hay fuego" en informacion.

    Un foco sobre pastizal en agosto es rutina agricola; el mismo sobre bosque
    no lo es. El visor decia cuantas celdas arden y cuanta gente hay debajo, y
    no decia **que** esta ardiendo.
    """
    bloque = cuerpo("pintarEnVivo")

    assert "sobre qué está ardiendo" in bloque
    assert "suelo-reparto" in bloque
    for clase in ("arbolado", "pastizal", "cultivo", "humedal"):
        assert clase in bloque


def test_el_reparto_del_suelo_no_aparece_sin_datos() -> None:
    """Con activos anteriores a la Fase 1 el reparto viene vacio.

    Cuatro barras a cero se leerian como "no hay bosque ni pasto ni cultivo".
    """
    bloque = cuerpo("pintarEnVivo")

    assert "if (reparto.length)" in bloque


def test_el_reparto_dice_que_es_energia_y_no_focos() -> None:
    """Mil detecciones debiles y cincuenta intensas dan repartos distintos.

    Sin decirlo, el porcentaje se lee como "de cada cien focos", que es otra
    cosa y suele apuntar al reves.
    """
    assert "Reparto de la energía medida, no del número de focos" in APP


def test_ningun_dibujo_sobre_el_mapa_falla_en_silencio() -> None:
    """El callback corre **diferido**, dentro de un manejador de MapLibre.

    El `try/catch` de quien lo encolo ya termino, y MapLibre se traga lo que
    lance un manejador. La malla de un evento dejo de dibujarse, el selector de
    capas se quedo oculto, y no habia ni una linea en consola — dos horas de
    diagnostico para un fallo que se anunciaba solo en cuanto se le dejaba
    hablar.
    """
    bloque = cuerpo("cuandoElEstiloEsteListo")

    assert "catch (error)" in bloque
    assert "console.error" in bloque


def test_el_dibujo_no_depende_de_que_el_estilo_se_declare_listo() -> None:
    """`isStyleLoaded()` puede no ser cierto nunca si una fuente se queda a medias.

    Sin red de seguridad el callback no corre jamas y el visor se queda a medio
    pintar, que es indistinguible de un visor roto.
    """
    bloque = cuerpo("cuandoElEstiloEsteListo")

    assert "setTimeout(" in bloque


def test_la_barra_de_escala_no_queda_debajo_de_las_leyendas() -> None:
    """Estaba abajo a la izquierda, que es donde se apilaron las leyendas.

    Una barra de escala tapada es peor que no tenerla: el hueco se da por
    cubierto. Y este sistema publica distancias —"41 km al SO de"—, asi que
    poder juzgarlas en el mapa no es decorativo.
    """
    linea = APP[APP.index("mapa.addControl(new maplibregl.ScaleControl") :][:200]

    # Las tres esquinas ocupadas, probadas una a una: abajo-izquierda son las
    # leyendas y los interruptores; abajo-derecha la leyenda de intensidad y la
    # atribucion; arriba-izquierda las pestañas de capa.
    for ocupada in ('"bottom-left"', '"bottom-right"', '"top-left"'):
        assert ocupada not in linea, f"la escala vuelve a una esquina ocupada: {ocupada}"
    assert '"top-right"' in linea


def test_la_nota_de_la_capa_se_puede_plegar() -> None:
    """Nueve lineas fijas se comen el mapa a zoom cercano.

    La nota explica por que hay huecos en la malla y por que las lineas del
    ShakeMap si llegan al mar: hay que tenerla disponible, no delante todo el
    rato.
    """
    html = (RAIZ / "site" / "index.html").read_text(encoding="utf-8")

    assert "leyenda-detalle" in html
    assert "<summary>Cómo leer esta capa</summary>" in html
    assert 'id="leyenda-nota"' in html, "la nota sigue teniendo que existir"


def test_salud_y_educacion_van_antes_que_la_superficie() -> None:
    """El orden de un tablero lo fija para que sirve, no cuanto abulta.

    Iba por tamano del numero: 444.000 edificaciones y 69,8 km² antes que 518
    sedes de salud. Pero quien responde no decide con la superficie construida
    —decide con cuantos hospitales quedaron dentro y cuantos colegios pueden
    servir de refugio—, y en una pantalla de portatil esas dos cifras caian por
    debajo del pliegue.
    """
    bloque = sin_comentarios_js(cuerpo("pintarMetricas"))
    etiquetas = (
        "sedes de salud",
        "sedes educativas",
        "edificaciones",
        "superficie construida",
    )
    orden = [bloque.index(e) for e in etiquetas]

    assert orden == sorted(orden), "salud y educacion volvieron a quedar detras"


def test_cada_bloque_del_panel_dice_de_que_va() -> None:
    """Los titulos eran correctos y opacos.

    "Expuesto en MMI≥7", "Terreno: peligros secundarios", "Contraste con
    evaluacion de dano": quien no trae el vocabulario puesto veia cifras sin
    saber que preguntaban. Cada bloque lleva ahora una linea que lo explica en
    lenguaje llano.
    """
    html = (RAIZ / "site" / "index.html").read_text(encoding="utf-8")
    bloques = re.findall(
        r'<h3 class="eyebrow"[^>]*>(.*?)</h3>\s*(<p class="subtitulo-bloque">)?', html
    )

    sin_explicar = [titulo for titulo, sub in bloques if not sub and titulo != "Descargas"]
    assert not sin_explicar, f"bloques sin explicar: {sin_explicar}"


def test_se_explica_que_es_mmi_donde_se_usa() -> None:
    """Es el termino que sostiene todo el sistema y el que nadie conoce.

    La leyenda del mapa lo explicaba; el panel lo daba por sabido y es donde
    estan las cifras.
    """
    html = (RAIZ / "site" / "index.html").read_text(encoding="utf-8")

    assert "MMI 7 es la sacudida" in html


def test_el_visor_ensena_los_servicios_bajo_fuego() -> None:
    """Lo que el popup de una celda decia y el indicador no.

    Salud y educacion dentro de celdas con fuego activo estaban solo para quien
    pulsara la celda exacta entre catorce mil.
    """
    bloque = cuerpo("pintarEnVivo")

    assert "salud_en_celdas_con_fuego" in bloque
    assert "edu_en_celdas_con_fuego" in bloque
    assert "en celdas con fuego activo" in bloque


def test_los_servicios_no_se_pintan_si_son_cero() -> None:
    """Cero puede ser "no hay" o "el pais no tiene activo cargado".

    Pintar "0 sedes de salud" afirmaria lo primero sin poder distinguirlo.
    """
    bloque = cuerpo("pintarEnVivo")

    assert "filter(([, n]) => Number(n) > 0)" in bloque
    assert "if (servicios.length)" in bloque


# --- Indicadores: un catalogo, una funcion ----------------------------------


def test_una_sola_funcion_pinta_las_cifras() -> None:
    """El HTML de cada cifra estaba escrito a mano en cada sitio que la mostraba.

    Eso hacia imposible anadirle nada —un icono, un nivel— sin repetirlo tres
    veces y que las tres se separaran a la primera.
    """
    assert "function tarjetaIndicador" in APP

    # Panel de un evento, reporte preliminar por radios y bloque de fuego.
    for llamador in ("pintarMetricas",):
        assert "tarjetaIndicador" in sin_comentarios_js(cuerpo(llamador))


def test_los_cortes_de_nivel_estan_medidos_y_no_elegidos() -> None:
    """p33 y p66 de los diez reportes del catalogo que alcanzan MMI≥7.

    Un nivel "alto" inventado diria mas del criterio de quien lo eligio que del
    evento. Asi es relativo a lo que de verdad ha pasado en LATAM.
    """
    bloque = APP[APP.index("const INDICADORES") :][:900]

    assert "cortes: [247720, 910714]" in bloque, "los cortes de poblacion no son los medidos"
    assert "cortes: [31, 152]" in bloque, "los de salud tampoco"


def test_sin_valor_no_se_inventa_un_nivel() -> None:
    """Un cero o un nulo no son "nivel bajo": son ausencia de dato.

    Pintar tres barras vacias como si fueran una medicion es la forma visual del
    error que este proyecto persigue.
    """
    bloque = cuerpo("nivelDe")

    assert "if (v <= 0) return null" in bloque
    assert "!Number.isFinite(Number(valor))" in bloque


def test_cada_indicador_declara_su_icono() -> None:
    """Sin icono la cifra se encuentra leyendo; con icono, mirando."""
    catalogo = APP[APP.index("const INDICADORES") : APP.index("const NIVELES")]
    iconos = APP[APP.index("const ICONOS") : APP.index("const INDICADORES")]

    for clave in re.findall(r"icono: \"(\w+)\"", catalogo):
        assert f"{clave}:" in iconos, f"el indicador declara el icono {clave} y no existe"


def test_la_muestra_de_la_leyenda_se_distingue_del_fondo() -> None:
    """La clase mas baja de cada rampa es casi invisible sobre el fondo claro, y
    en el mapa eso no tiene arreglo: no existe reparto de seis clases que llegue
    a 3:1 contra el suelo sin dejar las oscuras indistinguibles entre si.

    En la leyenda si lo tiene, y ahi importa mas: es donde se aprende que
    significa cada color. El contorno de la muestra existia para eso y estaba a
    alfa 0,2 —#c9ccc3, 1,45:1 contra el fondo—, tan invisible como el relleno
    que venia a delimitar.
    """
    css = (RAIZ / "site" / "assets" / "styles.css").read_text(encoding="utf-8")
    bloque = css[css.index(".leyenda-escala .muestra") :][:400]
    encaje = re.search(r"border:\s*1px solid rgba\(28,\s*51,\s*40,\s*([\d.]+)\)", bloque)
    assert encaje, "la muestra de la leyenda perdio su contorno"

    alfa = float(encaje.group(1))
    fondo = (244, 242, 234)
    tinta = (28, 51, 40)
    pintado = tuple(round(tinta[i] * alfa + fondo[i] * (1 - alfa)) for i in range(3))

    def luminancia(rgb: tuple[int, ...]) -> float:
        canales = []
        for v in rgb:
            c = v / 255
            canales.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
        return 0.2126 * canales[0] + 0.7152 * canales[1] + 0.0722 * canales[2]

    claro, oscuro = luminancia(fondo), luminancia(pintado)
    razon = (claro + 0.05) / (oscuro + 0.05)

    assert razon >= 3.0, (
        f"el contorno de la muestra da {razon:.2f}:1 contra el fondo de la leyenda; "
        f"hacen falta 3:1 para que delimite un objeto grafico que lleva informacion"
    )


def test_la_medicion_de_la_rampa_queda_escrita() -> None:
    """La respuesta obvia a ese hallazgo —oscurecer la clase baja— no funciona, y
    la cuenta que lo demuestra tiene que vivir al lado de las rampas.

    Sin ella, la siguiente auditoria vuelve a levantarlo y alguien oscurece la
    primera clase, colapsandola contra la segunda.
    """
    # El comentario esta reflowado a 80 columnas, asi que las frases se parten
    # por el salto de linea — y al unirlas queda el `//` de cada linea en medio.
    # Se quitan los marcadores y se normaliza el espacio: si no, la prueba se
    # rompe cada vez que alguien reajusta un parrafo.
    plano = " ".join(re.sub(r"^\s*//:?", " ", APP, flags=re.MULTILINE).split())

    assert "presupuesto de luminancia" in plano, (
        "no queda escrito por que la rampa no se puede arreglar recoloreando"
    )
    assert "1,41:1 entre las dos mas oscuras" in plano, "falta la cifra que lo demuestra"
    assert "perimetro" in plano.lower(), (
        "falta decir que la mitad util del hallazgo si se resolvio, y donde"
    )
