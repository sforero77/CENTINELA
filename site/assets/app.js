// Visor de CENTINELA.
//
// Cero backend, cero llaves de API (D6). Todo lo que se ve sale de artefactos
// que ya se publican para descargar —`report.json`, `adm2.csv`, `celdas.json`—
// así que lo que hay en pantalla no puede divergir de lo que se lleva quien los
// baja. El visor no tiene una fuente propia, y esa es la idea.

const INDICE_REPORTES = "reports/index.json";
// Que paises puede atender el sistema. Sale de los manifests, asi que no
// puede prometer mas paises de los que se construyeron de verdad.
const COBERTURA = "cobertura.json";
//: Sismos vistos y no despachados, ventana movil de cinco dias.
const OBSERVADOS = "observados.json";
//: Focos activos de las ultimas 24 h, cruzados con la exposicion.
const INCENDIOS = "incendios.json";

// Encuadre inicial: la ventana LATAM del sistema (RF-01).
// Encuadre inicial: **la caja de LATAM, no un zoom fijo**.
//
// `zoom: 3.1` centrado en Colombia dejaba fuera Chile, Argentina, Bolivia,
// Paraguay, Uruguay y el sur de Peru y Brasil — la mitad de los diecinueve
// paises que el sistema dice cubrir. Y encima ahi es donde esta la temporada de
// quemas, asi que la capa de fuego se encendia sobre territorio invisible.
//
// `fitBounds` se adapta a la ventana; un zoom fijo solo es correcto para el
// tamano de pantalla en que se eligio.
// Que se ve al abrir. Medido, no elegido a ojo.
//
// El tablero da un mapa de unos 954x468 px en un portatil, que es **apaisado**,
// y LATAM es una region **vertical**: ocupa 0,24 del mundo a lo ancho y 0,29 a
// lo alto. Para que quepa entera harian falta zoom 1,64, y a ese zoom se verian
// 206 grados de longitud — casi todo oceano vacio alrededor de una franja fina.
//
// Asi que hay que recortar algo, y conviene decir que. A `[-72, -10]` con zoom
// 2,0 se ve **de lat 29,7 a -45,5**: entra desde el centro de Mexico hasta
// Chubut, con toda la cordillera sismica y toda la temporada de quemas dentro.
// Quedan fuera el norte de Mexico y la Patagonia austral, que es donde menos
// gente y menos actividad hay de los diecinueve paises.
//
// `zoom: 3.1` centrado en Colombia —lo anterior— dejaba fuera Chile, Argentina,
// Bolivia, Paraguay, Uruguay y el sur de Brasil. Media region, y justo la mitad
// donde arde.
// El centro va **al oeste** del centroide de la region a proposito. A este
// zoom sobran 80 grados de longitud, y con el centro en -72 ese sobrante caia
// sobre Africa occidental: Senegal, Mali, Nigeria y sus etiquetas ocupaban un
// cuarto del mapa util. Desplazado a -84 el sobrante cae sobre el Pacifico, que
// esta vacio y no compite con nada.
const VISTA_INICIAL = { center: [-84.0, -10.0], zoom: 2.0 };

//: La caja que el encuadre tiene que cubrir. Es la misma `LATAM_BBOX` del
//: pipeline, y esta aqui para que una prueba pueda comprobar que la vista
//: inicial la contiene — no para dibujar nada.
const ENCUADRE_LATAM = [
  [-119.0, -57.5],
  [-32.0, 33.0],
];

//: La ventana **util**, que es la que se encuadra al abrir.
//:
//: `ENCUADRE_LATAM` es la caja del pipeline y entra entera solo a un zoom al que
//: se ven 206 grados de longitud: una franja fina de continente rodeada de
//: oceano. Esta recorta el norte de Mexico y la Patagonia austral —donde menos
//: gente y menos actividad hay de los diecinueve paises— que es exactamente el
//: recorte que `VISTA_INICIAL` ya habia elegido a mano. La diferencia es que
//: ahora se adapta a la ventana en vez de ser correcto para una sola.
const ENCUADRE_UTIL = [
  [-107.0, -46.0],
  [-34.0, 30.0],
];

//: LO QUE NO ES AMERICA LATINA SE APAGA.
//:
//: La caja de la region es **alta** —73° de ancho por 76° de alto— y el panel
//: del mapa es apaisado: 1125 × 540 en un portatil, y esa proporcion no cambia
//: en ningun escritorio. `fitBounds` encaja por la dimension que primero se
//: agota, que aqui es siempre la altura, y el ancho sobrante se reparte a los
//: dos lados. Medido en el sitio publicado: 163° de longitud visibles en una
//: ventana de 1372 px y 191° en una de 1540. America Latina ocupaba el 38 % del
//: ancho util y el resto era Atlantico y Africa occidental **rotulada**:
//: Nigeria, Chad, Niger, Argelia, Senegal, Angola y Namibia en un tablero de
//: exposicion sismica latinoamericana.
//:
//: No hay encuadre que arregle eso. Llenar el ancho obliga a recortar latitud, y
//: el primer recorte que cabe se lleva Ciudad de Mexico, Monterrey y Santiago —
//: tres de los sitios con reporte publicado. Entre ensenar la region entera y
//: llenar el ancho, se ensena la region entera y **se apaga lo demas**.
//:
//: La caja va algo mas holgada que `ENCUADRE_LATAM` a proposito: el fuego no
//: respeta fronteras y hay focos en Guyana y Surinam. Aun asi las capas de datos
//: se dibujan **por encima** de la mascara, asi que nada del dato se pierde por
//: caer fuera; lo unico que se atenua es el mapa base.
const CAJA_MASCARA = [
  [-122.0, -58.0],
  [-28.0, 35.0],
];

//: El tono del papel del tablero. Velar con el color del fondo —y no con gris o
//: con negro— hace que el sobrante lea como margen y no como sombra.
const BASE_PAPEL = "#f4f2ea";

// Mapa base: estilo Positron de OpenFreeMap.
//
// **Por qué este y no las teselas de Overture.** Overture tesela para el
// detalle: medido, una tesela de `base` a zoom 4 pesa 4,3 MB y no trae una sola
// etiqueta. Una de OpenFreeMap a zoom 6 pesa 101 KB y trae topónimos, vías,
// agua y relieve. Cuarenta veces más ligera y con nombres, que es lo que
// convierte un mapa en algo que se puede leer.
//
// Sigue sin llaves ni cuota (D6): OpenFreeMap sirve ficheros estáticos sin
// registro. Si el servicio cae, el mapa se queda gris y **los reportes siguen
// bien**, porque ninguna cifra depende de las teselas.
//
// Positron y no un estilo de colores a propósito: el mapa es el fondo del dato.
const ESTILO_BASE = "https://tiles.openfreemap.org/styles/positron";

//: Los mapas base que se ofrecen, y por que solo tres.
//:
//: OpenFreeMap publica cinco —positron, liberty, bright, dark y fiord— y aqui
//: no estan los cinco: `liberty` y `fiord` son estilos de colores saturados, y
//: sobre ellos la rampa de MMI y la del fuego dejan de leerse. Ofrecer un mapa
//: base que estropea el dato no es dar una opcion, es dar una trampa.
//:
//: Los tres que quedan responden a tres preguntas distintas:
//:
//:   claro     el de siempre, y el unico contra el que estan medidos los
//:             contrastes de las dos rampas. Es el defecto por eso.
//:   oscuro    para una sala a media luz, y porque las rampas calidas del fuego
//:             ganan contraste sobre fondo oscuro.
//:   relieve   cuando la pregunta es "¿por que ahi?": el terreno explica donde
//:             se acumula la intensidad y por donde corre un incendio.
//:
//: `retinta` solo en positron: los colores de la identidad estan elegidos
//: contra su gris neutro, y aplicarlos a un estilo oscuro lo dejaria a medias.
//: `velo` es el tono con el que se apaga lo que no es America Latina, y tiene
//: que ser el del papel de CADA estilo o el borde de la mascara se ve.
const ESTILOS_BASE = {
  claro: {
    nombre: "Claro",
    apunte: "El de siempre. Los contrastes de las rampas están medidos contra él.",
    url: "https://tiles.openfreemap.org/styles/positron",
    retinta: true,
    velo: "#f4f2ea",
  },
  oscuro: {
    nombre: "Oscuro",
    apunte: "Para pantallas a media luz. El fuego gana contraste.",
    url: "https://tiles.openfreemap.org/styles/dark",
    retinta: false,
    velo: "#14171a",
  },
  relieve: {
    nombre: "Con relieve",
    apunte: "Más detalle de terreno, a costa de que el mapa compita con el dato.",
    url: "https://tiles.openfreemap.org/styles/bright",
    retinta: false,
    velo: "#f4f2ea",
  },
};

// El mapa base se retinta a la paleta de la identidad. El agua estaba en
// #cdd9d4, a un paso de la tierra en luminosidad: la costa no se distinguía, y
// la mitad de la exposición de este sistema es costera. Ahora hay separación
// real entre las dos.
const BASE_TIERRA = "#ece9de";
const BASE_AGUA = "#b7cdc9";
const EPICENTRO = "#8f2c14";
// Gris de tinta, deliberadamente fuera de la rampa de MMI. Esa rampa
// significa «impacto medido»; prestarsela a un sismo que nadie midio la
// vaciaria de sentido.
const OBSERVADO = "#6b6660";

// Rampa del fuego, por potencia radiativa acumulada en la celda (MW).
//
// **Inferno, no la rampa de MMI.** La de intensidad va de naranja a rojo oscuro
// —`#fdbb84` a `#7f0000`— que es tambien la paleta natural del fuego, y ahi
// esta el problema: dos amenazas distintas con el mismo codigo de color se leen
// como la misma cosa. Inferno acaba en violeta, es la convencion en
// teledeteccion de FRP, y no se parece a nada mas del visor.
//: Zoom a partir del cual el hexagono real es visible.
//
// Una celda H3 r8 mide 1.063 m de lado a lado. En pantalla:
//
//     zoom  3   ->  0,05 px      zoom  9  ->   3,5 px
//     zoom  6   ->  0,43 px      zoom 11  ->  13,9 px
//
// A la escala continental con la que abre el visor son **una vigesima parte de
// un pixel**: la capa funcionaba y era fisicamente invisible. Por debajo de
// este zoom se dibuja un punto, que es una marca de posicion y no finge una
// huella; por encima, el hexagono de verdad.
const FUEGO_ZOOM_HEX = 9;

const FUEGO_CORTES = [10, 50, 150, 400, 1000];
// Medido contra `BASE_TIERRA` (#ece9de), que es sobre lo que se dibuja:
//
//     antes  1,2 : 1   1,3 : 1   2,2 : 1   3,6   5,8   9,1
//     ahora  1,7 : 1   2,4 : 1   3,3 : 1   4,7   7,0  10,7
//
// Las dos primeras clases eran **invisibles** sobre el suelo del mapa, y ahi
// cae la mayoria de las celdas. Es el mismo error que este repositorio ya
// corrigio una vez —"la coropleta era del color del suelo del mapa"— y lo
// repeti eligiendo inferno, que es una rampa pensada para fondo negro.
//
// Sobre un suelo de luminancia 0,81 ningun color claro llega a 3:1, asi que el
// relleno no basta: cada simbolo lleva contorno oscuro. Es lo que la
// cartografia llama figura-fondo, y es la unica salida sin cambiar el mapa base.
const FUEGO_COLORES = ["#f4a621", "#ef7215", "#e14b28", "#c02a4a", "#8c1d64", "#4a1370"];
const FUEGO_CONTORNO = "#3d0f52";

const REDUCIR_MOVIMIENTO =
  window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
const VUELO = REDUCIR_MOVIMIENTO ? 0 : 800;

// --- Capas que el visor sabe pintar ----------------------------------------
//
// Cada una es una columna de `celdas.json`, que es una columna del activo: el
// selector no ofrece nada que el dato no tenga.
//
// **Los cortes están medidos, no elegidos a ojo.** Sobre las 11.574 celdas de
// los tres eventos publicados, con clases geométricas —la práctica recomendada
// para datos sesgados; los intervalos iguales dejarían clases vacías— y seis
// clases, que es el rango útil para el ojo. Reparto resultante:
//
//   población   17 / 30 / 31 / 15 / 6 / 1 %
//   edificación 28 / 28 / 23 / 12 / 7 / 2 %
//   construido  18 / 27 / 30 / 15 / 8 / 3 %
//   vías        21 / 31 / 28 / 11 / 4 / 0,2 %
//
// **Los colores están corregidos.** La primera versión arrancaba las rampas en
// cremas y arenas —#f2e6c4 la de intensidad— sobre una tierra base de #e9e7dc:
// la clase baja de cada capa era, literalmente, el color del suelo del mapa. La
// coropleta era invisible salvo a zoom alto. Ahora cada rampa empieza en un
// tono que la arena no tiene.
//
// **La de intensidad es la misma que la del mapa estático del reporte**
// (`pipelines/p3_report/static_map.py`), extendida a la clase 8,5 que aquel no
// cubría. Es una secuencial naranja-rojo, no el arcoíris de ShakeMap: el
// arcoíris no tiene orden perceptual y se rompe con el daltonismo rojo-verde,
// que es el más común. Esta mantiene la luminosidad estrictamente descendente y
// por eso sobrevive impresa en blanco y negro, que es como acaba en muchas
// salas de crisis. El argumento está escrito en ese módulo desde antes; el
// visor no tenía por qué inventarse otra escala para la misma magnitud.
//
// MMI no lleva rangos sino un color por valor: el ShakeMap da 6, 6,5, 7, 7,5, 8
// y 8,5, y escribir "6 – 6,5" sugiere un continuo que no existe.
// POR QUE LA CLASE MAS BAJA NO LLEGA A 3:1 CONTRA EL SUELO, Y POR QUE SE QUEDA ASI.
//
// Una auditoria de contraste lo levanto y es cierto: la primera clase de las
// siete rampas da entre 1,14 y 1,37:1 contra `BASE_TIERRA`. La respuesta obvia
// —oscurecerla— no funciona, y esta medido:
//
//   El suelo del mapa tiene luminancia 0,814. Para que la clase 1 llegue a 3:1
//   no puede pasar de L=0,238. La clase 6 ya esta en L=0,045, que es casi negro
//   y no puede bajar mas. Eso deja SEIS clases entre 0,238 y 0,045: un salto de
//   0,039 de luminancia cada una, y **1,41:1 entre las dos mas oscuras**.
//
// Se cambia un problema por otro: en vez de no distinguir la clase baja del
// fondo, no se distinguen las altas entre si — y las altas son las que dicen
// donde esta lo grave. Ninguna asignacion de seis clases sobre un fondo claro
// satisface las dos cosas; no es un descuido de la paleta, es el presupuesto de
// luminancia que hay.
//
// LO QUE SE HACE EN SU LUGAR. WCAG 1.4.11 exceptua los graficos cuya
// presentacion concreta es esencial para la informacion, que es el caso de una
// rampa secuencial, **a cambio de que el dato este disponible de otra forma**.
// Lo esta, y por triplicado: la leyenda publica los rangos numericos, el globo
// de cada celda da su valor exacto, y `celdas.json` se descarga entero.
//
// Y lo que si se arreglo, que era la mitad que de verdad estorbaba: distinguir
// "aqui no hay dato" de "aqui hay poco". Eso ahora lo dice el perimetro, que
// dibuja en tinta el borde del area contada. Ver `dibujarPerimetro`.
//
// Si algun dia el mapa base pasa a un fondo oscuro, esta cuenta cambia entera y
// merece rehacerse.
//: De cuando es la poblacion que cuenta este visor.
//:
//: Vive en una constante porque la dicen dos sitios —la nota de la capa de
//: poblacion y la apostilla de las reconstrucciones retrospectivas— y si se
//: reconstruye el activo con otra epoca, los dos tienen que cambiar a la vez.
//: Un visor que diga 2025 en un sitio y 2030 en otro es peor que uno que no lo
//: diga.
const EPOCA_POBLACION = "La población es GHS-POP época 2025";

const CAPAS = {
  mmi: {
    titulo: "Intensidad",
    columna: "mmi",
    exacto: true,
    cortes: [6, 6.5, 7, 7.5, 8, 8.5],
    colores: ["#fdbb84", "#fc8d59", "#ef6548", "#d7301f", "#b30000", "#7f0000"],
    nota:
      "Mercalli modificada, en pasos de media. Los hexágonos llegan hasta donde " +
      "hay algo expuesto: el hueco no es ausencia de sacudida, es ausencia de " +
      "gente y de infraestructura. Las líneas son los contornos del ShakeMap y " +
      "sí marcan hasta dónde llegó el sismo, sobre tierra y sobre mar; en gris, " +
      "los niveles por debajo de 6, que se sienten y que este sistema no cuantifica.",
  },
  pop: {
    titulo: "Población",
    columna: "pop",
    cortes: [1, 10, 100, 1000, 10000, 50000],
    colores: ["#c3dad6", "#9dc3c3", "#71a6ae", "#478997", "#2f6e78", "#1b4a55"],
    nota: "Personas por celda de 5,2 km². GHS-POP época 2025.",
  },
  bld: {
    titulo: "Edificaciones",
    columna: "bld",
    cortes: [1, 10, 50, 250, 1000, 5000],
    colores: ["#cfe0c2", "#a9c998", "#7fae75", "#559457", "#2f7a45", "#14522f"],
    nota: "Overture sobre OpenStreetMap. Donde OSM no mapeó, se queda corto.",
  },
  built_m2: {
    titulo: "Superficie construida",
    columna: "built_m2",
    cortes: [1, 500, 5000, 50000, 250000, 1000000],
    colores: ["#e8d49b", "#d8bd76", "#c4a054", "#a8813c", "#856128", "#5d4218"],
    nota: "GHS-BUILT-S, m² vistos por satélite: ve el barrio que OSM no mapeó.",
  },
  vias_km: {
    titulo: "Vías",
    columna: "vias_km",
    cortes: [0.5, 2, 5, 15, 40, 90],
    colores: ["#cfd6cd", "#adb5aa", "#8b9489", "#6a7469", "#4a5449", "#2b3529"],
    nota: "Kilómetros por celda, Overture. Incluye calle residencial.",
  },
  // `salud` y `edu` venían en `celdas.json` desde el principio y el selector no
  // las ofrecía: se podían ver de una en una abriendo cada celda, que es la
  // manera más lenta posible de responder "dónde están los hospitales dentro de
  // la franja". Mismos cortes para las dos a propósito, para que se puedan
  // comparar: reparto medido sobre las 1.691 celdas con equipamiento de los
  // tres eventos, 41/15/16/13/9/7 % en salud y 49/11/13/12/10/4 % en educación.
  salud: {
    titulo: "Salud",
    columna: "salud",
    cortes: [1, 2, 3, 5, 10, 25],
    colores: ["#dcc9dd", "#c2a4c6", "#a37fae", "#835d94", "#623f74", "#412651"],
    nota: "Sedes de salud por celda. El 96 % de las celdas no tiene ninguna y no se dibuja.",
  },
  edu: {
    titulo: "Educación",
    columna: "edu",
    cortes: [1, 2, 3, 5, 10, 25],
    colores: ["#c9d4e8", "#a4b6d6", "#7e95c1", "#5b75a8", "#3c568a", "#233666"],
    nota: "Sedes educativas por celda. El 90 % de las celdas no tiene ninguna y no se dibuja.",
  },
};

const ORDEN_CAPAS = ["mmi", "pop", "bld", "built_m2", "vias_km", "salud", "edu"];

//: Superficie nominal de una celda H3 r7, que es la resolucion **de la malla
//: sismica**: `p3_report/celdas.py` agrega de r8 a r7 antes de publicar, y los
//: indices de `celdas.json` empiezan por `87`.
//:
//: NO VALE PARA EL FUEGO. P5 publica r8 sin agregar y su area es siete veces
//: menor; ver `AREA_CELDA_FUEGO_KM2` justo debajo, y lo que costo confundirlas.
//:
//: Es la cifra que el visor ya dice en tres sitios —la pista del panorama, el
//: popup de la celda y la nota de la capa de poblacion— asi que el area sale de
//: multiplicarla por el numero de celdas y **se puede comprobar a mano**. Con
//: `h3.cellArea` saldria mas exacto y ya no cuadraria con lo que se ensena al
//: lado, que en este visor es peor.
const AREA_CELDA_KM2 = 5.2;

//: Y la de una celda de FUEGO, que **no es la misma** y durante todo este
//: tiempo se calculo como si lo fuera.
//:
//: D1 dice: computo en r8, agregado a r7/r6 para el visor. El lado sismico lo
//: cumple —`p3_report/celdas.py` hace `h3_cell_to_parent(h3_08, 7)` y publica
//: indices `87...` de 5,2 km²—. **P5 no agrega**: publica los `88...` de r8 tal
//: cual, y el visor les aplicaba `AREA_CELDA_KM2`, que es el area de r7.
//:
//: Resultado: cada area de foco salia SIETE VECES MAYOR de lo real. Un foco de
//: cien celdas se anunciaba como 520 km² cuando son 74. Y el rotulo de la capa
//: decia "cada hexagono es una celda de 5,2 km²" sobre hexagonos de 0,74.
//:
//: 0,737 km² es la media de r8 segun `h3.average_hexagon_area`. Se redondea a
//: 0,74 por el mismo motivo que el 5,2 de al lado: es la cifra que el visor
//: ensena, y tiene que poder comprobarse multiplicando a mano.
const AREA_CELDA_FUEGO_KM2 = 0.74;

// El PAGER es la estimación de pérdidas del propio USGS. No es una cifra
// nuestra y no mide lo mismo que este sistema, así que se enseña rotulada como
// lo que es y con la fuente delante.
const PAGER = {
  green: { texto: "USGS PAGER: verde", clase: "" },
  yellow: { texto: "USGS PAGER: amarilla", clase: "" },
  orange: { texto: "USGS PAGER: naranja", clase: "alarma" },
  red: { texto: "USGS PAGER: roja", clase: "alarma" },
};

const nf = new Intl.NumberFormat("es");

//: El mismo numero, agrupado siempre.
//:
//: El espanol no separa los millares hasta cinco cifras, asi que `numero()` da
//: "4000" y "15.607". Por separado es la convencion y esta bien. Juntas en la
//: misma frase o en la misma columna —"4.000 de 15.607", o una tabla de areas
//: donde 4628 cae debajo de 10.473— la primera parece una errata o un numero de
//: otro orden. Ahi, y solo ahi, se agrupa a la fuerza.
const nfMillares = new Intl.NumberFormat("es", { useGrouping: "always" });
const miles = (v) => (Number.isFinite(v) ? nfMillares.format(Math.round(v)) : "—");
const numero = (v, d = 0) => (Number.isFinite(v) ? nf.format(Number(v.toFixed(d))) : "—");

const MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"];

// "2026-08-10T12:34:28Z UTC" es una marca de tiempo de máquina impresa en una
// interfaz de persona. Se traduce, y se deja el UTC visible porque el sistema
// no sabe en qué huso está quien lee.
function comoFecha(iso, conHora = true) {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return String(iso || "—");
  const dia = `${d.getUTCDate()} ${MESES[d.getUTCMonth()]} ${d.getUTCFullYear()}`;
  if (!conHora) return dia;
  const hh = String(d.getUTCHours()).padStart(2, "0");
  const mm = String(d.getUTCMinutes()).padStart(2, "0");
  return `${dia}, ${hh}:${mm} UTC`;
}

//: Cuanto hace que se reviso.
//:
//: El comentario de la tarjeta "ahora mismo" lleva escrito desde que se creo
//: que las cifras "llevan la hora de la ultima revision: sin ella, «14.984
//: celdas con fuego» podria ser de hace un mes". No la llevaban. Un tablero que
//: se presenta como vigilancia en vivo y no fecha sus cifras pide una confianza
//: que no ha ganado.
//:
//: En prosa y no en marca de tiempo: quien mira quiere saber si esto es de hoy,
//: no a que hora exacta corrio un cron. La marca exacta va en el `title`.
function haceCuanto(iso) {
  const t = new Date(iso);
  if (Number.isNaN(t.getTime())) return null;
  const min = (Date.now() - t.getTime()) / 60000;
  if (min < 0) return "ahora mismo";
  if (min < 90) return `hace ${Math.max(1, Math.round(min))} min`;
  const horas = min / 60;
  // Hasta 48 y no 36: con el corte en 36, `round(36/24)` da 2 y "hace 1 día"
  // era literalmente inalcanzable — de "hace 35 h" se saltaba a "hace 2 días",
  // duplicando la antiguedad aparente de una cifra de dia y medio.
  if (horas < 48) return `hace ${Math.round(horas)} h`;
  const dias = Math.round(horas / 24);
  return `hace ${dias} días`;
}

//: La antiguedad, lista para pegar detras de un apunte.
function selloDeRevision(iso) {
  const cuanto = haceCuanto(iso);
  if (!cuanto) return "";
  return ` · <span class="revisado" title="${escapar(comoFecha(iso))}">revisado ${cuanto}</span>`;
}

// Redondeo en prosa, igual que el markdown del reporte: publicar
// "2.415.793 personas" sugiere una precisión que el método no tiene.
function comoTexto(v) {
  if (!Number.isFinite(v) || v <= 0) return "0";
  if (v >= 1e6) return `${(v / 1e6).toFixed(1).replace(".", ",")} M`;
  if (v >= 1e3) return numero(Math.round(v / 1e3) * 1e3);
  // Por debajo de 10 se conserva el decimal: el primer corte de vías es 0,5 km
  // y redondeado salía "1" en la leyenda, que además coincidía con el segundo
  // corte. Una leyenda con dos clases rotuladas igual no es una leyenda.
  if (v < 10) return numero(v, v % 1 === 0 ? 0 : 1);
  return numero(Math.round(v));
}

//: Lo mismo, para cosas que se cuentan de una en una.
//:
//: `comoTexto` conserva el decimal por debajo de diez, y tiene su razon: el
//: primer corte de la leyenda de vias es 0,5 km y redondeado chocaba con el
//: segundo. Pero esa regla se aplicaba tambien a las personas, y el panel de un
//: foco pequeno publicaba **«5,7 personas»**.
//:
//: GHS-POP es un raster desagregado, asi que el 5,7 es el dato de verdad; lo
//: que no es verdad es la precision que sugiere. Nadie cuenta media persona, y
//: al lado el globo de la celda ya escribia «Población 3» en entero: el mismo
//: hecho con dos formatos.
//:
//: Por debajo de media persona se escribe «<1» y no «0»: hay alguien, y un cero
//: ahi se leeria como "no hay nadie medido", que es lo que este visor distingue
//: en todas partes.
function comoConteo(v) {
  if (!Number.isFinite(v) || v <= 0) return "0";
  if (v < 0.5) return "<1";
  return comoTexto(Math.round(v));
}

// Los nombres del CSV municipal vienen en mayúsculas ("PEREIRA"); los de
// `report.json` no. Se normalizan aquí para que las barras no griten.
function capitalizar(nombre) {
  if (!nombre) return "";
  if (nombre !== nombre.toUpperCase()) return nombre;
  const menores = new Set(["de", "del", "la", "las", "los", "y", "el", "en"]);
  return nombre
    .toLocaleLowerCase("es")
    .split(/\s+/)
    .map((p, i) => (i > 0 && menores.has(p) ? p : p.charAt(0).toLocaleUpperCase("es") + p.slice(1)))
    .join(" ");
}

//: Un conteo no dice si es mucho. "289.000 personas de 65 anos o mas" no
//: significa nada hasta saber que son el 12 % de los expuestos —muy por encima
//: del peso de ese grupo en el pais—, y "1,6 M sobre suelo licuable" no dice
//: nada hasta saber que son dos de cada tres. La division ya se podia hacer con
//: los numeros que el reporte trae; simplemente no se hacia.
//:
//: Devuelve `null` si la cuota no significa nada —sin total, o cero— para que
//: quien la pinta pueda omitirla en vez de escribir "0 %" o "NaN %".
function cuotaDe(parte, total) {
  if (!Number.isFinite(parte) || !Number.isFinite(total) || total <= 0 || parte <= 0) return null;
  const pct = (100 * parte) / total;
  return `${numero(pct, pct < 10 ? 1 : 0)} %`;
}

const $ = (id) => document.getElementById(id);

// El panel lateral llevaba `aria-live` entero: cambiar de evento le leia a
// quien usa lector de pantalla las treinta cifras del tablero de corrido. Se
// anuncia una frase y el resto queda para navegar cuando se quiera.
function anunciar(texto) {
  const nodo = $("anuncio");
  if (nodo) nodo.textContent = texto;
}
const escapar = (s) =>
  String(s).replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

const estado = {
  paisFiltrado: "",
  //: Que mapa base esta puesto. Ver `ESTILOS_BASE`.
  estiloBase: "claro",
  //: Los sismos vistos y no despachados, enteros. Se guardaban solo sus
  //: coordenadas, y con eso no se puede volver a dibujar la capa — que es lo
  //: que hay que hacer cada vez que se cambia de mapa base, porque `setStyle`
  //: se lleva por delante todas las fuentes y todas las capas.
  observadosDatos: null,
  //: Que amenaza manda en el mapa. La otra queda de contexto discreto.
  //:
  //: El fuego vivia detras de un checkbox apagado en una esquina: 745.000
  //: personas bajo fuego activo eran invisibles hasta que alguien encontrara la
  //: casilla. Y la razon de fondo del producto es la contraria — el activo es
  //: agnostico a la amenaza, las mismas celdas cuentan gente bajo MMI 7 y gente
  //: bajo fuego. Eso pide que la amenaza sea el primer control del mapa.
  amenaza: "sismos",
  //: El ultimo incendios.json cargado, para la leyenda del modo fuego.
  fuegoDatos: null,
  //: Los focos —grupos de celdas contiguas— y el indice celda -> foco.
  focos: [],
  focosPorCelda: null,
  //: El foco abierto en el panel, si lo hay.
  focoAbierto: null,
  //: Coordenadas de los sismos vistos y no reportados, para encuadrarlos.
  observadosGeo: [],
  //: Ventana temporal de la lista de reportes.
  ventana: "todo",
  //: Y los de la lista de focos, que van por su cuenta: son otra amenaza.
  ventanaFuego: "h24",
  ordenFocos: "reciente",
  paisFuego: "",
  //: ISO3 -> nombre, del unico sitio que lo publica: la cobertura.
  nombresPais: null,
  //: Instante desde el que se cuenta la ventana del fuego. Ver `referenciaDelFuego`.
  fuegoRef: 0,
  //: Como se ordena la lista y si se recorta al encuadre del mapa. Los dos son
  //: del usuario, no del dato, asi que no van a la URL: un enlace compartido
  //: tiene que abrir el mismo reporte, no la misma manera de mirarlo.
  orden: "fecha",
  soloEnVista: false,
  epicentro: null,
  //: Lo que el sistema esta viendo ahora mismo, para el bloque "en vivo".
  vivo: {},
  mapa: null,
  //: El unico globo abierto en el mapa, para poder cerrarlo cuando se va el
  //: dato que describe.
  globo: null,
  eventos: [],
  seleccionado: null,
  capa: "mmi",
  ganchosCeldas: false,
  //: Valores de MMI que trae la malla cargada, para no rotular clases vacias.
  presentes: null,
};

// --- Datos ------------------------------------------------------------------

async function json(url) {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`HTTP ${r.status} en ${url}`);
  return r.json();
}

// El CSV municipal se parsea aquí en vez de publicar un GeoJSON paralelo: es el
// mismo fichero que se ofrece para descargar. La segunda fila son las etiquetas
// HXL (T1.3) y se salta.
function parsearCsv(texto) {
  const lineas = texto.trim().split(/\r?\n/);
  if (lineas.length < 3) return [];
  const cols = partirLinea(lineas[0]);
  const esHxl = lineas[1].startsWith("#");
  return lineas.slice(esHxl ? 2 : 1).map((linea) => {
    const celdas = partirLinea(linea);
    const fila = {};
    cols.forEach((c, i) => {
      const bruto = celdas[i] === undefined ? "" : celdas[i];
      const n = Number(bruto);
      fila[c] = bruto !== "" && !Number.isNaN(n) ? n : bruto;
    });
    return fila;
  });
}

// Hay municipios con coma en el nombre —"Bogota, D.C."— y un split directo
// parte la fila y desplaza todas las cifras una columna.
function partirLinea(linea) {
  const celdas = [];
  let actual = "";
  let comillas = false;
  for (const ch of linea) {
    if (ch === String.fromCharCode(34)) comillas = !comillas;
    else if (ch === "," && !comillas) { celdas.push(actual); actual = ""; }
    else actual += ch;
  }
  celdas.push(actual);
  return celdas;
}

// --- Enlace profundo --------------------------------------------------------
//
// Sin esto no se podía compartir un reporte: cualquiera que pegase la URL caía
// en el mapa regional y tenía que volver a buscar el evento. En un producto
// cuyo artefacto principal es un reporte por evento, eso sobra explicarlo.

//: LOS FILTROS QUE ELIGEN **QUE** SE MIRA VIAJAN; LOS QUE ELIGEN **COMO**, NO.
//:
//: Pais y periodo recortan el conjunto de datos: "los reportes de Venezuela de
//: los ultimos cinco anos" es una vista con contenido propio, y hasta ahora no
//: habia forma de mandarsela a nadie —el enlace abria los veintiuno—. Van a la
//: URL como ?evento= y ?capa=.
//:
//: Orden y "solo lo que se ve en el mapa" no: son preferencias de lectura, y ya
//: estaba decidido en `estado.orden` que un enlace compartido tiene que abrir el
//: mismo reporte, no la misma manera de mirarlo. Esa linea se respeta.
function leerUrl() {
  const p = new URLSearchParams(location.search);
  const capa = p.get("capa");
  const periodo = p.get("periodo");
  const periodoF = p.get("periodof");
  return {
    evento: p.get("evento"),
    capa: CAPAS[capa] ? capa : null,
    // Solo "fuego" es un valor: "sismos" es el defecto y no viaja en la URL.
    amenaza: p.get("amenaza") === "fuego" ? "fuego" : null,
    // Los ISO3 se validan contra los eventos cargados, que es lo unico que sabe
    // cuales existen; aqui solo se normaliza la forma. Un valor que no case se
    // ignora en silencio, como ya se hace con `capa`: un enlace viejo o mal
    // copiado abre el panorama, no un error.
    pais: /^[A-Z]{3}$/.test(String(p.get("pais") || "").toUpperCase())
      ? String(p.get("pais")).toUpperCase()
      : null,
    paisFuego: /^[A-Z]{3}$/.test(String(p.get("paisf") || "").toUpperCase())
      ? String(p.get("paisf")).toUpperCase()
      : null,
    periodo: VENTANAS[periodo] ? periodo : null,
    periodoFuego: VENTANAS_FUEGO[periodoF] ? periodoF : null,
  };
}

function escribirUrl() {
  const p = new URLSearchParams();
  if (estado.seleccionado) p.set("evento", estado.seleccionado);
  if (estado.seleccionado && estado.capa !== "mmi") p.set("capa", estado.capa);
  // Compartible, como ?evento=: quien manda un enlace en modo fuego manda el
  // modo fuego. Un evento abierto implica sismos, asi que son excluyentes.
  if (!estado.seleccionado && estado.amenaza === "fuego") p.set("amenaza", "fuego");
  // Solo lo que no es el defecto: una URL con `&periodo=todo&pais=` no dice
  // nada y ensucia cada enlace que alguien copie.
  if (estado.amenaza === "fuego") {
    if (estado.paisFuego) p.set("paisf", estado.paisFuego);
    if (estado.ventanaFuego !== "h24") p.set("periodof", estado.ventanaFuego);
  } else {
    if (estado.paisFiltrado) p.set("pais", estado.paisFiltrado);
    if (estado.ventana !== "todo") p.set("periodo", estado.ventana);
  }
  const cadena = p.toString();
  history.replaceState(null, "", cadena ? `?${cadena}` : location.pathname);
}

// --- Malla de celdas --------------------------------------------------------

// El fichero trae índices H3, no geometrías: el contorno de un hexágono en
// GeoJSON son ~150 bytes y su índice son quince caracteres. Se reconstruye aquí
// con h3-js, que es exactamente para lo que sirve un índice jerárquico.
function celdasAGeoJson(datos) {
  if (typeof h3 === "undefined") return null;
  const idx = Object.fromEntries(datos.columnas.map((c, i) => [c, i]));
  return {
    type: "FeatureCollection",
    features: datos.celdas.map((c) => {
      // El índice H3 **sí** viaja. Se excluía, y con él se iba la única forma
      // de cruzar lo que se ve en el mapa con el `celdas.json` que se ofrece
      // para descargar: quince caracteres por celda a cambio de que la ficha
      // sea citable y verificable. Para quien trabaja con SIG, un dato que no
      // se puede referenciar es un dato que no se puede usar.
      const props = {};
      for (const [nombre, i] of Object.entries(idx)) props[nombre] = c[i];
      return {
        type: "Feature",
        // `true` devuelve [lng, lat], que es el orden de GeoJSON. Sin él, los
        // hexágonos aparecen en el océano Índico.
        geometry: { type: "Polygon", coordinates: [h3.cellToBoundary(c[idx.h3], true)] },
        properties: props,
      };
    }),
  };
}

function expresionColor(capa) {
  const pasos = ["step", ["coalesce", ["get", capa.columna], 0], capa.colores[0]];
  capa.cortes.slice(1).forEach((corte, i) => pasos.push(corte, capa.colores[i + 1]));
  return pasos;
}

// El dato va debajo de los topónimos. Dibujarlo encima tapaba Quibdó, Pereira y
// Cali justo en los eventos donde importaba saber qué ciudad es cada mancha: un
// mapa sin nombres no sitúa a nadie.
function primeraEtiqueta(m) {
  const capas = m.getStyle().layers || [];
  const simbolo = capas.find((c) => c.type === "symbol");
  return simbolo ? simbolo.id : undefined;
}

// La leyenda de intensidad rotulaba siempre las seis clases, de 6 a 8,5, fuera
// cual fuera el evento. El del Chocó no pasa de 7,5 y el de San Felipe de 8: en
// dos de los tres reportes publicados había dos muestras de color que no
// aparecían en el mapa. Es el mismo error que los comentarios de este archivo
// presumen de haber arreglado en los cortes de las otras capas — "dos colores
// que no se usaban nunca"— y seguía vivo en la capa principal.
//
// Solo se recorta en las capas de valor exacto. En las de rango, una clase sin
// celdas sigue siendo información: dice hasta dónde llega la escala.
function clasesVisibles(capa) {
  if (!capa.exacto || !estado.presentes) return capa.cortes.map((c, i) => [c, i]);
  const hay = estado.presentes;
  const usadas = capa.cortes.map((c, i) => [c, i]).filter(([c]) => hay.has(c));
  return usadas.length ? usadas : capa.cortes.map((c, i) => [c, i]);
}

function pintarLeyenda(capa) {
  $("leyenda").hidden = false;
  $("leyenda-titulo").textContent = capa.titulo;
  $("leyenda-nota").textContent = capa.nota;
  $("leyenda-escala").innerHTML = clasesVisibles(capa)
    .map(([corte, i]) => {
      const sig = capa.cortes[i + 1];
      // MMI no lleva rangos: el ShakeMap da valores exactos en pasos de media,
      // y escribir "6 – 6,5" sugiere un continuo que no existe.
      const texto = capa.exacto
        ? numero(corte, 1)
        : sig
          ? `${comoTexto(corte)} – ${comoTexto(sig)}`
          : `${comoTexto(corte)} o más`;
      return (
        `<li><span class="muestra" style="background:${capa.colores[i]}"></span>` +
        `<span class="leyenda-valor">${texto}</span></li>`
      );
    })
    .join("");
}

function pintarSelectorCapas() {
  const caja = $("capas");
  caja.hidden = false;
  // `tabindex` rotatorio: solo el tab seleccionado entra en el orden de
  // tabulacion, y dentro del grupo se navega con flechas. Es lo que ARIA exige
  // de un `tablist`, y no estaba: con siete capas, llegar al mapa con el
  // teclado costaba siete tabulaciones que ademas no cambiaban nada.
  caja.innerHTML = ORDEN_CAPAS.map(
    (id) =>
      `<button type="button" role="tab" data-capa="${id}" ` +
      `aria-selected="${id === estado.capa}" aria-controls="mapa" ` +
      `tabindex="${id === estado.capa ? 0 : -1}" ` +
      `title="${escapar(CAPAS[id].nota)}">${CAPAS[id].titulo}</button>`
  ).join("");

  const botones = [...caja.querySelectorAll("button")];
  for (const [i, boton] of botones.entries()) {
    boton.addEventListener("click", () => cambiarCapa(boton.dataset.capa));
    boton.addEventListener("keydown", (ev) => {
      const salto = { ArrowRight: 1, ArrowLeft: -1 }[ev.key];
      const destino = salto
        ? botones[(i + salto + botones.length) % botones.length]
        : { Home: botones[0], End: botones[botones.length - 1] }[ev.key];
      if (!destino) return;
      ev.preventDefault();
      // Se mueve **y se selecciona**: en un tablist que cambia una vista, tener
      // que confirmar con Enter deja al usuario mirando una capa que no es la
      // que tiene el foco.
      destino.focus();
      cambiarCapa(destino.dataset.capa);
    });
  }
}

function cambiarCapa(id) {
  estado.capa = id;
  for (const boton of document.querySelectorAll("#capas button")) {
    boton.setAttribute("aria-selected", String(boton.dataset.capa === id));
  }
  const capa = CAPAS[id];
  const m = estado.mapa;
  if (m && m.getLayer("celdas")) {
    m.setPaintProperty("celdas", "fill-color", expresionColor(capa));
    // Una celda con cero en la capa elegida no se pinta: en "vías" media región
    // está vacía, y pintarla del primer color la haría parecer un valor bajo en
    // vez de una ausencia.
    m.setFilter("celdas", [">", ["coalesce", ["get", capa.columna], 0], 0]);
    anotarCapaActiva(id, capa.columna);
  }
  for (const boton of document.querySelectorAll("#capas button")) {
    const suya = boton.dataset.capa === id;
    boton.setAttribute("aria-selected", String(suya));
    boton.tabIndex = suya ? 0 : -1;
  }
  pintarLeyenda(capa);
  anunciar(`Capa ${capa.titulo}. ${capa.nota}`);
  escribirUrl();
}

// --- Eventos ----------------------------------------------------------------

async function cargarEventos() {
  const aviso = $("estado-lista");
  const lista = $("lista-eventos");
  const selector = $("selector-evento");
  try {
    const eventos = await json(INDICE_REPORTES);
    estado.eventos = eventos;
    if (!eventos.length) {
      aviso.textContent = "Todavía no hay reportes publicados.";
      pintarPanorama([]);
      return;
    }
    aviso.hidden = true;
    for (const evento of eventos) {
      lista.appendChild(filaEvento(evento));
      const opcion = document.createElement("option");
      opcion.value = evento.usgs_id;
      opcion.textContent = `M${String(evento.mag).replace(".", ",")} — ${evento.lugar}`;
      selector.appendChild(opcion);
    }
    selector.addEventListener("change", () => {
      if (selector.value) seleccionar(selector.value);
      else cerrarDetalle();
    });
    pintarPanorama(eventos);
    dibujarEpicentros(eventos);
    pintarLeyendaSimbolos();
    cargarObservados();
    cargarIncendios();

    // La cobertura primero: da los nombres de pais que necesita el filtro, y
    // asi el mapeo ISO3 -> nombre vive en un solo sitio, el que lo publica.
    const nombres = await cargarCobertura(eventos);
    // El mapeo ISO3 -> nombre vive en un solo sitio, el que lo publica. La
    // lista de focos lo necesita igual que el filtro de reportes.
    estado.nombresPais = nombres;

    // LOS FILTROS DEL ENLACE, ANTES DE PINTAR LOS CONTROLES.
    //
    // Asi los desplegables nacen ya enseñando lo que el enlace pidio, en vez de
    // enseñar "Todos los países" y corregirse un instante despues. El ISO3 se
    // valida contra los eventos que existen —`leerUrl` solo comprueba la forma—:
    // un `?pais=XYZ` no puede dejar la lista vacia sin motivo.
    const filtros = leerUrl();
    const paisesConReporte = new Set(eventos.map((e) => e.iso3).filter(Boolean));
    if (filtros.pais && paisesConReporte.has(filtros.pais)) estado.paisFiltrado = filtros.pais;
    if (filtros.periodo) estado.ventana = filtros.periodo;
    if (filtros.paisFuego) estado.paisFuego = filtros.paisFuego;
    if (filtros.periodoFuego) estado.ventanaFuego = filtros.periodoFuego;

    pintarFiltroPaises(eventos, nombres);
    pintarControlesLista();
    refrescarLista({ anunciando: false });

    const url = leerUrl();
    if (url.capa) estado.capa = url.capa;
    if (!url.evento && url.amenaza === "fuego") cambiarAmenaza("fuego", { anunciando: false });
    if (url.evento && eventos.some((e) => e.usgs_id === url.evento)) {
      seleccionar(url.evento);
    } else if (url.evento) {
      // Un enlace a un reporte que no esta caia al panorama en silencio, con el
      // parametro todavia en la barra. Quien llega desde un enlace compartido a
      // un reporte retirado —o con el id mal copiado— cree que pulso mal.
      //
      // No es un error del sistema, asi que no se pinta como tal: se dice lo que
      // paso y se deja la lista completa delante, que es lo que hay que ofrecer.
      const aviso = $("estado-lista");
      if (aviso) {
        aviso.hidden = false;
        aviso.textContent =
          `No hay ningún reporte con el identificador «${url.evento}». ` +
          `Puede que se haya retirado, o que el enlace esté incompleto. ` +
          `Abajo están los ${eventos.length} publicados.`;
      }
      anunciar(`No se encontró el reporte ${url.evento}. Se muestra el panorama.`);
      // El parametro se quita: dejarlo hace que recargar repita el error y que
      // el enlace se siga compartiendo roto.
      escribirUrl();
    }
  } catch (error) {
    aviso.textContent =
      "Aún no hay índice de reportes publicado. El primer reporte real lo genera.";
    console.warn("índice:", error);
  }
}

// El estado por defecto del tablero enseñaba un panel en blanco: la superficie
// principal del producto, vacía, hasta que alguien adivinase que hay que elegir
// algo. Aquí va lo que se puede decir sin elegir nada.
//
// No se suma la población de los eventos: dos de los tres publicados son del
// mismo día y su zona se solapa, y sumarlos contaría dos veces a las mismas
// personas. Se publica el mayor, que sí es una cifra.
function pintarPanorama(eventos) {
  const caja = $("panorama");
  if (!caja) return;
  if (!eventos.length) {
    // Dos vacios distintos, y decir cual es. "Todavía no hay reportes
    // publicados" con un filtro puesto es falso —los hay, el filtro no los
    // deja— y manda a esperar en vez de a soltar el filtro. El panel se quedaba
    // ademas con las cifras del catalogo entero: se elegia Cuba + 90 dias, la
    // cabecera decia "0 reportes publicados" y aqui seguian "21 reportes" y un
    // sismo de Colombia.
    caja.innerHTML = hayFiltros()
      ? `<p class="pista">${escapar(motivoDeVacio())}</p>` +
        `<p class="pista"><button type="button" class="filtros-limpiar" ` +
        `data-limpiar="1">Quitar filtros</button></p>`
      : `<p class="pista">Todavía no hay reportes publicados.</p>`;
    const limpiar = caja.querySelector("[data-limpiar]");
    if (limpiar) limpiar.addEventListener("click", () => quitarFiltros());
    return;
  }
  // LA CIFRA MAYOR DICE EN QUE BANDA ES MAYOR.
  //
  // Se compara `pop_mmi7p`, que es lo defendible —MMI≥7 es la franja que el
  // resto del panel usa— pero la etiqueta no lo decia: se leia "2,4 M · mayor
  // exposicion registrada" con "4,8 M en MMI≥6" tres filas mas abajo, en la
  // misma columna. Un maximo mas pequeno que un numero visible al lado es una
  // contradiccion aunque las dos cifras sean ciertas.
  //
  // Si ningun evento del conjunto llega a MMI≥7 —pasa al filtrar por un pais
  // con un solo reporte suave— se compara en MMI≥6 y se rotula asi. Y si no hay
  // nadie en ninguna banda, la metrica no se pinta: un "0 · mayor exposicion
  // registrada" no informa de nada.
  const conSiete = eventos.filter((e) => (e.pop_mmi7p || 0) > 0);
  const conSeis = eventos.filter((e) => (e.pop_mmi6p || 0) > 0);
  const candidatos = conSiete.length ? conSiete : conSeis;
  const bandaMayor = conSiete.length ? 7 : 6;
  const clave = bandaMayor === 7 ? "pop_mmi7p" : "pop_mmi6p";
  const mayor = candidatos.length
    ? candidatos.reduce((a, b) => ((b[clave] || 0) > (a[clave] || 0) ? b : a))
    : null;
  const paises = new Set(eventos.map((e) => e.iso3).filter(Boolean)).size;
  const enVivo = eventos.filter((e) => !e.backtest).length;

  caja.innerHTML =
    `<div class="metricas">` +
    `<div class="metrica"><span class="cabeza">${iconoSvg("reportes")}` +
    `<span class="valor">${eventos.length}</span></span>` +
    `<span class="etiqueta">reportes publicados</span></div>` +
    (mayor
      ? `<div class="metrica"><span class="cabeza">${iconoSvg("personas")}` +
        `<span class="valor">${comoConteo(mayor[clave])}</span></span>` +
        `<span class="etiqueta">mayor exposición registrada en MMI≥${bandaMayor}</span>` +
        `<span class="apunte">M${String(mayor.mag).replace(".", ",")} · ${escapar(mayor.lugar)}</span></div>`
      : "") +
    (paises > 1
      ? `<div class="metrica"><span class="cabeza">${iconoSvg("paises")}` +
        `<span class="valor">${paises}</span></span>` +
        `<span class="etiqueta">países con reporte</span></div>`
      : "") +
    `</div>` +
    `<ul class="panorama-lista">` +
    eventos
      .map(
        (e) =>
          `<li><button type="button" data-usgs-id="${escapar(e.usgs_id)}">` +
          `<span class="titulo">M${String(e.mag).replace(".", ",")} — ${escapar(e.lugar)}</span>` +
          `<span class="pie">${comoFecha(e.utc, false)} · ${
            bandaTitular(e).banda
              ? `${comoConteo(bandaTitular(e).pop)} en MMI≥${bandaTitular(e).banda}`
              : "sin población en MMI≥6"
          }${e.backtest ? " · retrospectivo" : ""}</span></button></li>`
      )
      .join("") +
    `</ul>` +
    (enVivo === 0
      ? `<p class="pista">Ninguno se emitió en vivo todavía: ` +
        `${eventos.length === 1 ? "es una reconstrucción retrospectiva" :
          `los ${nf.format(eventos.length)} son reconstrucciones retrospectivas`} ` +
        `de sismos ya ocurridos, con los productos que USGS publicó entonces. ` +
        `Son la prueba de qué habría informado el sistema, y de que funciona en ` +
        `cada país donde se corrieron.</p>`
      : `<p class="pista">${nf.format(enVivo)} de ${nf.format(eventos.length)} se ` +
        `emitieron en vivo; el resto son reconstrucciones retrospectivas.</p>`);

  for (const boton of caja.querySelectorAll("[data-usgs-id]")) {
    boton.addEventListener("click", () => seleccionar(boton.dataset.usgsId));
  }
}


// La banda con la que se titula un evento.
//
// El tablero titulaba siempre con MMI≥7 y hay sismos reales que no llegan ahi
// sobre poblacion: Atiquipa 2018 —M7,1 a 37 km mar adentro— deja 36.933
// personas en MMI≥6 y **cero** en MMI≥7. Un titular de "0 personas" es cierto
// y se lee como que el sistema fallo, o como que el sismo no fue nada.
//
// Se titula con la banda mas alta que si alcanzo poblacion, diciendo cual es.
function bandaDeTotales(t) {
  if (!t) return 0;
  if (t.pop_mmi8p > 0) return 8;
  if (t.pop_mmi7p > 0) return 7;
  if (t.pop_mmi6p > 0) return 6;
  return 0;
}

function bandaTitular(evento) {
  if (Number.isFinite(evento.pop_mmi7p) && evento.pop_mmi7p > 0) {
    return { pop: evento.pop_mmi7p, banda: 7 };
  }
  if (Number.isFinite(evento.pop_mmi6p) && evento.pop_mmi6p > 0) {
    return { pop: evento.pop_mmi6p, banda: 6 };
  }
  // Ni una ni otra: el evento entro por magnitud y su sacudida no alcanzo
  // poblacion. Tambien es un resultado, y decirlo es mejor que un cero suelto.
  return { pop: 0, banda: 0 };
}

function filaEvento(evento) {
  const li = document.createElement("li");
  li.dataset.usgsId = evento.usgs_id;
  if (evento.iso3) li.dataset.iso3 = evento.iso3;
  // Lo que la lista necesita para ordenarse y para saber si cae en el encuadre.
  // Va en el DOM y no en una estructura aparte para que ordenar sea mover nodos
  // y no repintar: repintar perderia el `activo` y el foco del teclado.
  if (Number.isFinite(evento.lon)) li.dataset.lon = String(evento.lon);
  if (Number.isFinite(evento.lat)) li.dataset.lat = String(evento.lat);
  li.dataset.mag = String(Number(evento.mag) || 0);
  li.dataset.pop = String(bandaTitular(evento).pop || 0);
  li.dataset.utc = evento.utc || "";

  const cabecera = document.createElement("div");
  cabecera.className = "evento-cabecera";

  const mag = document.createElement("span");
  mag.className = "evento-mag";
  mag.textContent = `M${String(evento.mag).replace(".", ",")}`;

  const enlace = document.createElement("a");
  enlace.href = `?evento=${encodeURIComponent(evento.usgs_id)}`;
  enlace.textContent = evento.lugar;
  enlace.addEventListener("click", (ev) => {
    // Clic normal abre el evento en el tablero. Con Ctrl/Cmd, que el navegador
    // haga lo suyo y abra la pestaña con el enlace profundo.
    if (ev.metaKey || ev.ctrlKey || ev.button !== 0) return;
    ev.preventDefault();
    seleccionar(evento.usgs_id);
    document.querySelector(".tablero").scrollIntoView({
      behavior: REDUCIR_MOVIMIENTO ? "auto" : "smooth",
      block: "start",
    });
  });

  cabecera.append(mag, enlace);

  const meta = document.createElement("p");
  meta.className = "evento-meta";
  meta.textContent = [
    comoFecha(evento.utc, false),
    `ShakeMap v${evento.shakemap_version}`,
    evento.preliminar ? "preliminar" : null,
    evento.backtest ? "retrospectivo" : null,
  ].filter(Boolean).join(" · ");

  li.append(cabecera, meta);

  // La cifra en grande y no perdida en una línea de metadatos: es lo que
  // alguien viene a buscar, y el resto de la tarjeta está para situarla.
  const titular = bandaTitular(evento);
  const cifra = document.createElement("span");
  cifra.className = "evento-cifra";
  cifra.innerHTML = titular.banda
    ? `${comoConteo(titular.pop)}<small>personas en MMI≥${titular.banda}</small>`
    : `<span class="sin-alcance">Sin población</span><small>en MMI≥6 o mayor</small>`;
  li.append(cifra);
  li.addEventListener("click", (ev) => {
    if (ev.target.closest("a")) return;
    seleccionar(evento.usgs_id);
  });
  return li;
}

async function seleccionar(usgsId) {
  // Abrir un evento es contenido del modo sismos, llegue de donde llegue: la
  // lista, el mapa en modo fuego, o un enlace con ?evento= y ?amenaza=fuego a
  // la vez (gana el evento, que es lo mas concreto).
  if (estado.amenaza !== "sismos") {
    estado.amenaza = "sismos";
    aplicarAmenaza();
  }
  estado.seleccionado = usgsId;
  $("selector-evento").value = usgsId;
  for (const li of document.querySelectorAll(".lista-eventos li")) {
    li.classList.toggle("activo", li.dataset.usgsId === usgsId);
  }
  $("lateral-vacio").hidden = true;
  $("lateral-detalle").hidden = false;
  $("detalle-titulo").textContent = "Cargando…";
  $("lateral").scrollTop = 0;
  escribirUrl();
  // Con un evento delante manda la leyenda de la capa; la de simbolos se pliega.
  pintarLeyendaSimbolos();

  try {
    const [reporte, csv, celdas, contornos] = await Promise.all([
      json(`reports/${usgsId}/report.json`),
      fetch(`reports/${usgsId}/adm2.csv`).then((r) => (r.ok ? r.text() : "")),
      fetch(`reports/${usgsId}/celdas.json`).then((r) => (r.ok ? r.json() : null)),
      // Los reportes emitidos antes de que existiera este fichero no lo traen:
      // el tablero sigue igual, solo sin el área de afectación dibujada.
      fetch(`reports/${usgsId}/contornos.json`).then((r) => (r.ok ? r.json() : null)),
    ]);
    pintarLateral(reporte, parsearCsv(csv), celdas);
    // El mapa va en su propio try: las cifras y las barras salen del reporte y
    // no dependen de que la malla se pueda dibujar. Antes un fallo aqui
    // borraba el titulo de un panel que ya estaba entero.
    try {
      pintarCeldas(celdas, reporte, contornos);
    } catch (errorMapa) {
      $("capas").hidden = true;
      $("leyenda").hidden = true;
      console.warn("malla:", errorMapa);
    }
  } catch (error) {
    $("detalle-titulo").textContent = "No se pudo abrir el reporte";
    $("detalle-meta").textContent = String(error);
    console.warn("detalle:", error);
  }
}

//: El encuadre de apertura, en un solo sitio.
//:
//: Lo pedian dos: el arranque del mapa y "Volver al panorama". Con la caja en
//: uno y el centro fijo en el otro, volver al panorama daba una vista distinta
//: de la de llegar, que es de esos detalles que nadie sabe nombrar y todo el
//: mundo nota.
//: La ultima orden dada a la camara, y por que.
//:
//: Existe por el mismo motivo que `pintado`: en una pestana de fondo los vuelos
//: de MapLibre se paran a medias, asi que la barra de escala no distingue "no
//: se pidio mover la camara" de "se pidio y la animacion no avanzo". Una prueba
//: que mide el pixel acaba fallando por la animacion en vez de por el fallo que
//: busca. Esto anota la **decision**, que es lo que el producto promete.
const camara = { motivo: null, utc: null };

function anotarCamara(motivo) {
  camara.motivo = motivo;
  camara.utc = new Date().toISOString();
}

function volverAlEncuadre(m, duracion = 0) {
  if (!m) return;
  try {
    m.fitBounds(ENCUADRE_UTIL, { padding: 24, duration: duracion, animate: duracion > 0 });
  } catch (error) {
    m.easeTo({ ...VISTA_INICIAL, duration: duracion });
  }
}

function cerrarDetalle() {
  estado.seleccionado = null;
  $("lateral-vacio").hidden = false;
  $("lateral-detalle").hidden = true;
  $("leyenda").hidden = true;
  $("capas").hidden = true;
  for (const li of document.querySelectorAll(".lista-eventos li")) li.classList.remove("activo");
  // Las tres capas del evento, no solo la malla. `contornos` se quedaba desde
  // siempre —las isolineas de un sismo cerrado seguian sobre el panorama— y no
  // se notaba porque son lineas palidas sobre un mapa continental. Al anadir el
  // perimetro, que va en tinta oscura, el resto quedo a la vista: al volver al
  // panorama flotaba el borde de un area cuyo panel ya no existe.
  cerrarGlobo();
  cerrarRotuloDeEpicentro();
  for (const capa of ["celdas", "contornos", "perimetro"]) quitarCapa(capa);
  estado.presentes = null;
  for (const capa of ["celdas", "contornos", "perimetro"]) anotarPintado(capa, 0);
  verHaloProporcional(true);
  escribirUrl();
  anunciar("Sin evento seleccionado. El panel muestra el panorama de los reportes publicados.");
  const selector = $("selector-evento");
  if (selector) selector.value = "";
  // Ya no compite con ninguna leyenda de capa: se despliega otra vez.
  pintarLeyendaSimbolos();
  // Al mismo encuadre adaptado con el que abre, no al centro y zoom fijos:
  // volver al panorama tiene que devolver la vista que se tenia al llegar.
  volverAlEncuadre(estado.mapa, VUELO);
  anotarCamara("panorama:cerrar-detalle");
}

// Tres formas de salir, porque hasta ahora habia media.
//
// El desplegable de la cabecera llamaba a `cerrarDetalle` al elegir la opcion
// vacia, y nada mas. Quien entraba pulsando un epicentro en el mapa o una fila
// de la lista —que es como se entra— no tenia forma de volver: el desplegable
// no se lee como "salir", y ademas se quedaba mostrando el evento elegido.
function engancharSalidas() {
  $("volver")?.addEventListener("click", cerrarDetalle);
  conectarVolverDelFoco();
  document.addEventListener("keydown", (ev) => {
    if (ev.key !== "Escape") return;
    // El panel de mapas base primero: es el mas superficial de los tres y el
    // unico que se abre encima de lo demas. Cerrar el evento con la galeria
    // abierta dejaria el panel flotando sobre un mapa que ya cambio.
    const galeria = $("galeria-bases");
    if (galeria && !galeria.hidden) {
      cerrarGaleriaDeBases();
      const boton = document.querySelector(".ctrl-bases");
      if (boton) boton.focus();
      return;
    }
    // Escape cierra lo que este abierto, y solo hay uno de los dos: abrir un
    // evento fuerza el modo sismos, que a su vez cierra el foco.
    if (estado.seleccionado) cerrarDetalle();
    else if (estado.focoAbierto) cerrarFoco();
  });
}

// --- Panel lateral ----------------------------------------------------------

function pintarLateral(reporte, municipios, celdas) {
  const ev = reporte.event;
  const t = reporte.totales;

  $("detalle-eyebrow").textContent = `Reporte · ${ev.usgs_id}`;
  $("detalle-titulo").textContent =
    `M${String(ev.mag).replace(".", ",")} — ${ev.lugar}`;
  $("detalle-meta").textContent = [
    comoFecha(ev.utc),
    `${numero(ev.depth_km, 1)} km de profundidad`,
    `ShakeMap v${reporte.inputs.shakemap_version}`,
    reporte.inputs.exposure_manifest,
  ].join(" · ");

  pintarDistintivos(reporte);
  pintarArea(reporte, celdas);
  pintarFranjas(reporte);
  pintarMetricas(reporte);
  pintarTerreno(reporte);
  pintarMunicipios(reporte, municipios);
  pintarContraste(ev.usgs_id, t);
  pintarIncertidumbre(reporte);
  pintarDescargas(ev.usgs_id);

  anunciar(
    `Reporte de M${String(ev.mag).replace(".", ",")} en ${ev.lugar}. ` +
    (reporte.preliminar
      ? "Preliminar, sin ShakeMap."
      : (() => {
          const b = bandaDeTotales(t);
          return b
            ? `${comoConteo(t[`pop_mmi${b}p`])} personas expuestas a intensidad ${b} o mayor.`
            : "Su sacudida no alcanzó intensidad 6 sobre población.";
        })())
  );
}

// LA PROFUNDIDAD ES UNA VARIABLE DE PRIMER ORDEN, Y ESTABA EN UNA LINEA DE
// METADATOS ENTRE LA FECHA Y LA VERSION DEL SHAKEMAP.
//
// A igual magnitud, la profundidad decide cuanto se siente en superficie. Es
// literalmente lo que explica los casos raros del catalogo: Tehuantepec fue un
// M8,2 y su maximo sobre poblacion mexicana es MMI 6,5; los veintidos sismos
// bolivianos estan entre 359 y 596 km y ninguno produce una sola celda. Un
// lector que ve "M8,2" y "0 personas en MMI≥7" sin ver "47 km" o "559 km" no
// tiene con que entenderlo.
//
// Los cortes son los estandar en sismologia, no elegidos aqui: someros hasta
// 70 km, intermedios hasta 300, profundos por encima.
function claseDeProfundidad(km) {
  if (!Number.isFinite(km)) return null;
  if (km < 70) {
    return {
      texto: `${numero(km)} km · superficial`,
      titulo:
        "Menos de 70 km. A igual magnitud es el caso que más sacude en superficie, " +
        "porque la energía recorre menos camino hasta la gente.",
    };
  }
  if (km <= 300) {
    return {
      texto: `${numero(km)} km · intermedio`,
      titulo:
        "Entre 70 y 300 km. La sacudida se reparte sobre un área más ancha y llega " +
        "más suave: un sismo grande puede no alcanzar intensidades altas en ningún sitio.",
    };
  }
  return {
    texto: `${numero(km)} km · profundo`,
    titulo:
      "Más de 300 km. Se siente lejos y débil. En esta región son los del Nazca bajo " +
      "Bolivia y el occidente de Brasil, que casi nunca producen intensidad publicable.",
  };
}

function pintarDistintivos(reporte) {
  const marcas = [];
  const prof = claseDeProfundidad(Number(reporte.event.depth_km));
  if (prof) marcas.push(prof);
  if (reporte.preliminar) {
    marcas.push({
      texto: "preliminar, sin ShakeMap",
      titulo: "El corte es por radios alrededor del epicentro, no por intensidad modelada.",
    });
  } else if (reporte.backtest) {
    marcas.push({
      texto: "reconstrucción retrospectiva",
      titulo:
        "La población es de la época indicada en el manifest; las edificaciones, " +
        "vías y equipamiento son los actuales.",
    });
  }
  const pager = PAGER[reporte.event.pager_alert];
  if (pager) {
    marcas.push({
      texto: pager.texto,
      clase: pager.clase,
      titulo:
        "Nivel de alerta del sistema PAGER del USGS, que estima víctimas y pérdidas " +
        "económicas. Es una cifra suya, no de CENTINELA, y no mide lo mismo: aquí " +
        "solo se publica exposición.",
    });
  }
  $("detalle-distintivos").innerHTML = marcas
    .map(
      (m) =>
        `<li><span class="distintivo ${m.clase || ""}" title="${escapar(m.titulo)}">` +
        `${escapar(m.texto)}</span></li>`
    )
    .join("");

  // Y ESO MISMO, VISIBLE.
  //
  // El panel dice «cuánta gente vivía dentro de cada nivel de sacudida» sobre un
  // sismo de 2016 y cuenta con población de la época del activo, que hoy es
  // 2025. La advertencia existia solo en el `title` del distintivo y en el
  // `report.md`; en pantalla no habia nada, y ese es el aviso que decide como se
  // lee todo lo demas.
  const epoca = $("detalle-epoca");
  if (epoca) {
    epoca.hidden = !reporte.backtest;
    if (reporte.backtest) {
      epoca.textContent =
        `${EPOCA_POBLACION}. Las edificaciones, vías y equipamiento son los ` +
        `actuales: OpenStreetMap y Overture publican el estado presente, no el ` +
        `histórico. Léase como «qué quedaría hoy dentro de esa zona de ` +
        `intensidad», no como lo que había entonces.`;
    }
  }
}

// El pipeline calcula tres franjas de intensidad y el panel solo enseñaba la de
// MMI≥7. Con una sola franja no se sabe si el evento fue ancho y suave o
// estrecho y violento, que es la primera pregunta de quien responde.
//: Cuanto territorio quedo dentro de cada franja.
//:
//: El tablero contaba gente, edificaciones y vias y no decia nunca sobre que
//: superficie. "2,4 M de personas en MMI≥7" describe igual de bien una ciudad
//: sacudida que media cordillera, y son dos emergencias distintas.
//:
//: Se cuenta la **malla**, no el ShakeMap. Es la diferencia entre "hasta donde
//: llego el sismo" —que sigue sobre el mar— y "sobre cuanto territorio hay algo
//: expuesto", que es lo unico que este sistema mide. Por eso el area es
//: exactamente el area de las celdas que se dibujan y se descargan.
//:
//: Acumulado, como las franjas de poblacion: quien esta en MMI≥7 tambien esta
//: en MMI≥6. Y ademas el reparto por banda, que es donde se ve la forma.
function areaPorBanda(celdas) {
  if (!celdas || !Array.isArray(celdas.celdas) || !Array.isArray(celdas.columnas)) return null;
  const iMmi = celdas.columnas.indexOf("mmi");
  if (iMmi < 0) return null;

  const cuenta = new Map();
  for (const fila of celdas.celdas) {
    const banda = fila[iMmi];
    if (!Number.isFinite(banda)) continue;
    cuenta.set(banda, (cuenta.get(banda) || 0) + 1);
  }
  if (!cuenta.size) return null;

  const bandas = [...cuenta.keys()].sort((a, b) => b - a);
  const total = [...cuenta.values()].reduce((a, b) => a + b, 0);
  const mayor = Math.max(...cuenta.values());
  return {
    total,
    totalKm2: total * AREA_CELDA_KM2,
    bandas: bandas.map((banda) => ({
      banda,
      celdas: cuenta.get(banda),
      km2: cuenta.get(banda) * AREA_CELDA_KM2,
      cuota: cuenta.get(banda) / mayor,
    })),
  };
}

function pintarArea(reporte, celdas) {
  const bloque = $("bloque-area");
  const reparto = reporte.preliminar ? null : areaPorBanda(celdas);
  // Un reporte anterior a `celdas.json` no trae malla, y un preliminar no tiene
  // bandas. En los dos casos el bloque no existe, no sale a cero.
  bloque.hidden = !reparto;
  if (!reparto) return;

  // La cifra grande es la banda titular —la misma que rotula el resto del
  // panel—, para que "4.628 km²" y "2,4 M de personas" hablen del mismo sitio.
  //
  // Esa promesa se rompio al arreglar el bloque de metricas y el de municipios:
  // los dos pasaron a contar en MMI≥7 —que es donde estan las cifras del
  // reporte— y este seguia sacando MMI≥8 en Muisne, Catia La Mar y San Felipe.
  // Tres bloques seguidos con tres bandas distintas y una sola etiqueta cada
  // uno es la manera mas silenciosa de que alguien compare lo que no se compara.
  //
  // Misma regla que `pintarMunicipios`: MMI≥7, y solo se baja a 6 cuando el
  // evento no llego a 7 sobre poblacion.
  const banda = bandaDeTotales(reporte.totales);
  const titular = banda === 6 ? 6 : 7;
  const dentro = reparto.bandas.filter((b) => b.banda >= titular);
  const km2Titular = dentro.reduce((a, b) => a + b.km2, 0);
  const celdasTitular = dentro.reduce((a, b) => a + b.celdas, 0);

  const filas = reparto.bandas
    .map((b) => {
      const color = CAPAS.mmi.colores[Math.max(0, CAPAS.mmi.cortes.filter((c) => b.banda >= c).length - 1)];
      return (
        `<li><span class="area-banda mono">MMI ${numero(b.banda, 1)}</span>` +
        `<span class="area-pista"><span class="area-relleno" style="width:${(b.cuota * 100).toFixed(1)}%;background:${color}"></span></span>` +
        `<span class="area-cifra mono">${miles(b.km2)} km²</span></li>`
      );
    })
    .join("");

  $("detalle-area").innerHTML =
    `<p class="area-total"><strong>${miles(km2Titular)} km²</strong>` +
    `<span>dentro de MMI≥${numero(titular, 1)}</span></p>` +
    `<p class="area-apunte">${miles(celdasTitular)} celdas de ${numero(AREA_CELDA_KM2, 1)} km² · ` +
    `${miles(reparto.totalKm2)} km² en toda la malla del evento</p>` +
    `<ul class="area-franjas">${filas}</ul>`;
}

function pintarFranjas(reporte) {
  const t = reporte.totales;
  const bloque = $("bloque-franjas");
  if (reporte.preliminar) {
    bloque.hidden = true;
    return;
  }
  bloque.hidden = false;
  const franjas = [
    { nombre: "MMI≥6", valor: t.pop_mmi6p, color: CAPAS.mmi.colores[0] },
    { nombre: "MMI≥7", valor: t.pop_mmi7p, color: CAPAS.mmi.colores[2] },
    { nombre: "MMI≥8", valor: t.pop_mmi8p, color: CAPAS.mmi.colores[4] },
  ];
  const maximo = Math.max(...franjas.map((f) => f.valor || 0), 1);
  $("detalle-franjas").innerHTML = franjas
    .map(
      (f) =>
        `<li class="franja"><span class="franja-nombre">${f.nombre}</span>` +
        `<span class="franja-pista"><span class="franja-relleno" style="width:` +
        `${((100 * (f.valor || 0)) / maximo).toFixed(1)}%;background:${f.color}"></span></span>` +
        `<span class="franja-valor">${comoConteo(f.valor)}</span></li>`
    )
    .join("");
}


// --- Indicadores: iconos, rangos y una sola funcion que los pinta -----------
//
// El HTML de cada cifra estaba escrito a mano en cada sitio que la mostraba, y
// eso hacia imposible anadirle nada —un icono, un nivel— sin repetirlo. Aqui se
// declara **que** es cada indicador; `tarjetaIndicador` decide como se ve.
//
// Los cortes NO estan elegidos a ojo: son el p33 y el p66 medidos sobre los
// diez reportes del catalogo que alcanzan MMI≥7. Un evento por debajo del
// primero es de los pequenos que ha visto este sistema; por encima del segundo,
// de los grandes. Es una escala relativa a lo que de verdad ha pasado en LATAM,
// no a una intuicion.
const ICONOS = {
  personas:
    '<circle cx="9" cy="7" r="3"/><path d="M3 20c0-3.3 2.7-6 6-6s6 2.7 6 6"/>' +
    '<circle cx="17" cy="8.5" r="2.2"/><path d="M15.5 20c0-2.6 1.6-4.6 4-4.6 2 0 3.5 1.4 3.5 3.6"/>',
  mayores:
    '<circle cx="10" cy="6" r="3"/><path d="M10 9v11M10 12l-3 8M10 12l3 8M17 9v11M17 9l2 3"/>',
  salud: '<path d="M12 4v16M4 12h16"/>',
  educacion: '<path d="M2 9l10-5 10 5-10 5z"/><path d="M6 11.5V17c0 1.7 2.7 3 6 3s6-1.3 6-3v-5.5"/>',
  edificaciones:
    '<path d="M3 21V8l7-4v17M10 21V10l8-3v14"/><path d="M6 12h1M6 16h1M13.5 12h1M13.5 16h1"/>',
  superficie: '<path d="M4 4h16v16H4z"/><path d="M4 10h16M4 16h16M10 4v16M16 4v16"/>',
  vias: '<path d="M6 21L9 3M18 21l-3-18"/><path d="M12 4v3M12 11v3M12 18v3"/>',
  fuego: '<path d="M12 22c3.9 0 6-2.5 6-5.6 0-4-3-5.4-3-9.4-2 1-3 3-3 5 0-1.5-.7-2.7-2-3.6C9 10 6 11.6 6 16.4 6 19.5 8.1 22 12 22z"/>',

  // COBERTURA DEL SUELO. Sobre que arde, que es lo que convierte "hay fuego" en
  // informacion. Se dibujan por silueta —copa, espiga, mata, junco— y no por
  // color: el color ya lo lleva la barra que va al lado, y repetirlo no anade
  // nada a quien no distingue esos verdes.
  arbolado: '<path d="M12 21v-5"/><path d="M12 3 6.5 11h11z"/><path d="M12 8l-4.5 7h9z"/>',
  pastizal:
    '<path d="M4 21c0-5 1.5-8 3-10M9 21c0-6 1.5-10 3-13M14 21c0-5 1.5-8 3-10M20 21c0-4 .8-6.5 2-8"/>',
  cultivo: '<path d="M4 20h16"/><path d="M7 20V9M12 20V6M17 20v-8"/><path d="M7 12l3-2M12 9l3-2M17 15l3-2"/>',
  humedal:
    '<path d="M3 15c2-1.5 4-1.5 6 0s4 1.5 6 0 4-1.5 6 0M3 19c2-1.5 4-1.5 6 0s4 1.5 6 0 4-1.5 6 0"/>' +
    '<path d="M9 12V4M9 7c2 0 3-1.5 3-3-2 0-3 1.3-3 3z"/>',
  arbustos: '<path d="M12 21v-4"/><circle cx="9" cy="11" r="4"/><circle cx="15.5" cy="12.5" r="3.5"/>',
  construido: '<path d="M3 21h18"/><path d="M5 21V9l7-5 7 5v12"/><path d="M10 21v-5h4v5"/>',

  // DETECCION. Lo que vio el satelite y con cuanta energia.
  detecciones: '<circle cx="12" cy="12" r="2.5"/><path d="M12 3v3M12 18v3M3 12h3M18 12h3"/><circle cx="12" cy="12" r="7.5"/>',
  potencia: '<path d="M13 2 4 14h6l-1 8 9-12h-6z"/>',
  temperatura:
    '<path d="M10 14.5V5a2 2 0 1 1 4 0v9.5"/><circle cx="12" cy="17.5" r="3.5"/>' +
    '<path d="M16 7h2M16 10h2"/>',

  // AMBIENTE. Hacia donde empuja y con que sequedad.
  //
  // La flecha apunta al NORTE en reposo, y se gira desde el marcado. Ese giro
  // es la unica pieza de todo el visor donde equivocarse por 180 grados manda a
  // alguien hacia el fuego en vez de lejos, y por eso el rumbo va ademas
  // escrito con letras al lado: una flecha sola se lee mal.
  viento: '<path d="M12 21V4"/><path d="M7 9l5-5 5 5"/>',
  humedad: '<path d="M12 3s6 6.5 6 10.5a6 6 0 0 1-12 0C6 9.5 12 3 12 3z"/>',

  // TERRENO: las dos formas en que el suelo falla despues del sismo.
  deslizamiento: '<path d="M3 8l7 6 4-3 7 5"/><path d="M21 21H3"/><path d="M7 18l3-2M12 19l3-3"/>',
  licuefaccion:
    '<path d="M3 20h18"/><path d="M6 20v-4M10 20v-7M14 20v-5M18 20v-9"/>' +
    '<path d="M4 8c1.5-1.5 3-1.5 4.5 0s3 1.5 4.5 0 3-1.5 4.5 0"/>',

  // PANORAMA Y COBERTURA REGIONAL.
  reportes: '<path d="M6 3h9l4 4v14H6z"/><path d="M15 3v4h4"/><path d="M9 12h7M9 16h5"/>',
  paises: '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c2.5 3 2.5 15 0 18M12 3c-2.5 3-2.5 15 0 18"/>',
  malla: '<path d="M12 2l8.7 5v10L12 22l-8.7-5V7z"/><path d="M12 8l4.3 2.5v5L12 18l-4.3-2.5v-5z"/>',
  desvio: '<path d="M3 18h18"/><path d="M6 18V9M12 18V5M18 18v-6"/><path d="M3 12h18" stroke-dasharray="2 2"/>',
};

//: `clave -> icono, etiqueta, cortes medidos y formato`.
//: `formato: comoConteo` en lo que se cuenta de una en una —personas,
//: edificaciones— y `comoTexto` solo en magnitudes continuas. Ver `comoConteo`.
const INDICADORES = {
  personas: { icono: "personas", cortes: [247720, 910714], formato: comoConteo },
  mayores: { icono: "mayores", cortes: [15016, 81267], formato: comoConteo },
  salud: { icono: "salud", cortes: [31, 152], formato: numero },
  educacion: { icono: "educacion", cortes: [92, 998], formato: numero },
  edificaciones: { icono: "edificaciones", cortes: [130938, 331809], formato: comoConteo },
  superficie: { icono: "superficie", cortes: [8.3, 46.8] },
  vias: { icono: "vias", cortes: [1572, 5266] },
  fuego: { icono: "fuego", cortes: [50000, 300000], formato: comoConteo },
};

const NIVELES = { bajo: "bajo para el catálogo", medio: "medio", alto: "alto para el catálogo" };

//: En que tercio del catalogo cae un valor. `null` si no hay cortes o no hay
//: valor: un nivel inventado seria peor que ninguno.
function nivelDe(valor, cortes) {
  if (!cortes || !Number.isFinite(Number(valor))) return null;
  const v = Number(valor);
  if (v <= 0) return null;
  return v < cortes[0] ? "bajo" : v < cortes[1] ? "medio" : "alto";
}

function iconoSvg(nombre) {
  const trazo = ICONOS[nombre];
  return trazo
    ? `<svg class="icono" viewBox="0 0 24 24" aria-hidden="true" focusable="false">${trazo}</svg>`
    : "";
}

//: La unica funcion que pinta una cifra en este visor.
//
// `texto` permite pasar un valor ya formateado —"69,8 km²", "8503 km"— sin que
// el catalogo tenga que saber de unidades.
function tarjetaIndicador({ clave, valor, texto, etiqueta, apunte, ancha }) {
  const d = INDICADORES[clave] || {};
  const nivel = nivelDe(valor, d.cortes);
  const formateado = texto ?? (d.formato || numero)(valor);
  return (
    `<div class="metrica${ancha ? " ancha" : ""}"${nivel ? ` data-nivel="${nivel}"` : ""}>` +
    `<span class="cabeza">${iconoSvg(d.icono)}<span class="valor">${formateado}</span>` +
    (nivel
      ? `<span class="nivel" title="${NIVELES[nivel]}, comparado con los reportes publicados">` +
        `<i></i><i></i><i></i></span>`
      : "") +
    `</span>` +
    `<span class="etiqueta">${etiqueta}</span>` +
    (apunte ? `<span class="apunte">${apunte}</span>` : "") +
    `</div>`
  );
}

function pintarMetricas(reporte) {
  const t = reporte.totales;

  // Un preliminar publica radios en lugar de bandas de intensidad. Enseñar
  // "MMI≥7: 0" sería una cifra falsa y creíble.
  if (reporte.preliminar) {
    $("titulo-metricas").textContent = "Expuesto por radio";
    $("detalle-metricas").innerHTML = (reporte.radios || [])
      .map((r) =>
        tarjetaIndicador({ clave: "personas", valor: r.pop, etiqueta: `a ${r.radio_km} km` })
      )
      .join("");
    return;
  }

  // El resto de capas —edificaciones, vías, equipamiento— solo se calcula en
  // MMI≥7, así que el título nombra esa banda. Lo que sí cambia es la cifra de
  // personas: es la única que existe para las dos bandas, y con un evento que
  // no llega a 7 poner un 0 ahí es la frase que este tablero evita.
  const banda = bandaDeTotales(t);
  // UNA NOTA ESCRITA PARA UN CASO SE ESTABA IMPRIMIENDO EN EL CONTRARIO.
  //
  // `bandaDeTotales` devuelve 8 en cuanto hay alguien en MMI≥8 y 6 cuando la
  // sacudida no llego a 7 sobre poblacion. La rama `banda !== 7` cubria los dos
  // y ponia la misma frase: «La sacudida no alcanzó MMI 7 sobre población:
  // ninguna de las cifras de abajo aplica a este evento».
  //
  // En banda 6 es cierta. En banda 8 dice exactamente lo contrario de lo que el
  // propio panel enseña dos bloques mas arriba. Afectaba a los tres eventos mas
  // fuertes del catalogo: Muisne (2.283.454 personas en MMI≥7), Catia La Mar
  // (2.276.854) y San Felipe (491.581). Los reportes que mas importan eran los
  // que llevaban la frase que niega sus propias cifras.
  //
  // Ahora banda 8 saca **dos** tarjetas —lo de MMI≥8 y lo de MMI≥7— y ninguna
  // negacion: las cifras de abajo si aplican, y decirlo sobra cuando la cifra
  // esta al lado.
  const soloSeis = banda === 6;
  $("titulo-metricas").textContent = banda
    ? soloSeis
      ? "Expuesto en MMI≥6"
      : banda === 8
        ? "Expuesto en MMI≥8 y MMI≥7"
        : "Expuesto en MMI≥7"
    : "Expuesto en MMI≥7";
  // Y el subtitulo, que tambien hablaba siempre de MMI 7. En un evento que no
  // llego a 7 sobre poblacion, «esto es lo que quedó dentro de esa franja»
  // describe una franja vacia.
  const subtitulo = $("subtitulo-metricas");
  if (subtitulo) {
    subtitulo.textContent = soloSeis
      ? "MMI 6 se siente en todas partes y mueve objetos; el daño estructural " +
        "empieza más arriba. Esto es lo que quedó dentro de esa franja — no lo que se dañó."
      : "MMI 7 es la sacudida que asusta a todo el mundo y agrieta construcción " +
        "corriente. Esto es lo que quedó dentro de esa franja — no lo que se dañó.";
  }

  const km2 = Number.isFinite(t.built_m2_mmi7p) ? t.built_m2_mmi7p / 1e6 : null;
  const principal = t.road_km_principal_mmi7p;

  const tarjetas = [
    soloSeis
      ? {
          clave: "personas",
          valor: t.pop_mmi6p,
          etiqueta: "personas en MMI≥6",
          apunte:
            "La sacudida no alcanzó MMI 7 sobre población: ninguna de las cifras de abajo, " +
            "que se cuentan en MMI≥7, aplica a este evento.",
          ancha: true,
        }
      : { clave: "personas", valor: t.pop_mmi7p, etiqueta: "personas en MMI≥7" },
    // La banda alta, cuando existe, va inmediatamente detras y rotulada. Antes
    // era la unica que se enseñaba, y el resto del bloque —mayores, salud,
    // edificaciones— se contaba en MMI≥7 sin que nada lo dijera: se leia
    // "108.000 personas" seguido de "174.000 de 65 años o más", que es un
    // subconjunto mas grande que su conjunto.
    ...(banda === 8
      ? [{ clave: "personas", valor: t.pop_mmi8p, etiqueta: "de ellas, en MMI≥8" }]
      : []),
    {
      clave: "mayores",
      valor: t.pop_65p_mmi7p,
      etiqueta: "de 65 años o más",
      apunte: (() => {
        const cuota = cuotaDe(t.pop_65p_mmi7p, t.pop_mmi7p);
        return cuota ? `El ${cuota} de los expuestos a MMI≥7.` : null;
      })(),
    },
    // Salud y educacion **antes** que edificaciones y superficie.
    //
    // El orden anterior iba por tamano del numero: 444.000 edificaciones y 69,8
    // km² antes que 518 sedes de salud. Pero quien responde no decide con la
    // superficie construida: decide con cuantos hospitales quedaron dentro y
    // cuantos colegios pueden servir de refugio. En una pantalla de portatil
    // esas dos cifras caian por debajo del pliegue.
    //
    // El orden de un tablero lo fija para que sirve, no cuanto abulta.
    { clave: "salud", valor: t.health_mmi7p, etiqueta: "sedes de salud" },
    { clave: "educacion", valor: t.edu_mmi7p, etiqueta: "sedes educativas" },
    { clave: "edificaciones", valor: t.bld_mmi7p, etiqueta: "edificaciones" },
    {
      clave: "superficie",
      valor: km2,
      texto: km2 === null ? "—" : `${numero(km2, 1)} km²`,
      etiqueta: "superficie construida",
      apunte: "Vista por satélite: incluye lo que OSM no mapeó.",
    },
    {
      clave: "vias",
      valor: t.road_km_mmi7p,
      // `miles` y no `numero`: 8.503 km, en la misma columna tipografica que
      // el resto de cifras grandes del panel.
      texto: `${miles(t.road_km_mmi7p)} km`,
      etiqueta: "de vía",
      ancha: true,
      apunte: Number.isFinite(principal)
        ? `De ellos ${numero(principal)} km son primarias y secundarias; el resto es red local.`
        : null,
    },
  ];

  $("detalle-metricas").innerHTML = tarjetas.map(tarjetaIndicador).join("");
}

// Licuefacción y deslizamiento salen del modelo de ground failure del USGS y
// se guardaban en el reporte sin que el visor los enseñara. En el evento del
// Chocó son 1,6 millones de personas sobre suelo licuable: no es un apéndice.
function pintarTerreno(reporte) {
  const t = reporte.totales;
  const bloque = $("bloque-terreno");
  const tiene = Number.isFinite(t.pop_lq_alta) || Number.isFinite(t.pop_ls_alta);
  bloque.hidden = !tiene || reporte.preliminar;
  if (bloque.hidden) return;

  const filas = [
    { etiqueta: "Licuefacción alta", valor: t.pop_lq_alta, icono: "licuefaccion" },
    { etiqueta: "Deslizamiento alto", valor: t.pop_ls_alta, icono: "deslizamiento" },
  ];
  // La cuota se mide sobre los expuestos a MMI≥7, que es la banda con la que se
  // rotula el resto del panel: asi "1,6 M" y "66 %" hablan del mismo conjunto.
  $("detalle-terreno").innerHTML =
    filas
      .map((f) => {
        const cuota = cuotaDe(f.valor, t.pop_mmi7p);
        return (
          `<li><span>${iconoSvg(f.icono)}${f.etiqueta}` +
          (cuota ? ` <span class="cuota-apunte">· <strong>${cuota}</strong> de los expuestos</span>` : "") +
          `</span><span class="cifra${(f.valor || 0) > 0 ? "" : " cero"}">` +
          `${comoConteo(f.valor)}</span></li>`
        );
      })
      .join("") +
    `<li style="background:none;padding:0.3rem 0 0"><span class="leyenda-nota">` +
    `Personas sobre terreno con probabilidad alta según el modelo de fallo del ` +
    `suelo del USGS. Es susceptibilidad, no ocurrencia.</span></li>`;
}

function pintarMunicipios(reporte, municipios) {
  // `report.json` ya trae el top con los nombres bien escritos; el CSV se usa
  // de respaldo si el reporte no lo trajera.
  const fuente = (reporte.top_municipios && reporte.top_municipios.length)
    ? reporte.top_municipios
    : municipios;
  // «MÁS EXPUESTOS» TIENE QUE ORDENAR POR LO EXPUESTO, NO POR LA BANDA CUMBRE.
  //
  // Se ordenaba por `pop_banda`, que es la poblacion del municipio dentro de la
  // banda MAS ALTA que el evento alcanzo. En un evento que llega a MMI 8 eso es
  // la porcion ≥8, y el resultado era una lista falsa: en Muisne salia Muisne
  // con 9.000 y Quinindé con **0** —teniendo 164.691 personas en MMI≥7— y
  // Portoviejo, con 333.075, no salia. El bloque se titula «la misma cifra
  // nacional repartida entre quienes tienen que responder»: a quien responde
  // desde Portoviejo le decia cero.
  //
  // Se ordena por la banda en la que se cuenta el resto del panel —MMI≥7—, y
  // solo se baja a MMI≥6 cuando el evento no llego a 7 sobre poblacion, que es
  // el caso que `pop_banda` cubria bien. Ahi sigue siendo `pop_banda`.
  const banda = bandaDeTotales(reporte.totales);
  const bandaMostrada = banda === 6 ? 6 : 7;
  const cifra = (m) =>
    bandaMostrada === 7 ? (m.pop_mmi7p || 0) : (m.pop_banda ?? m.pop_mmi7p ?? 0);

  // Y las filas en cero no se listan. Un ranking de «más expuestos» rematado
  // con seis ceros —Carúpano tenia seis de ocho, Parrita siete de catorce— no
  // ensena donde se concentra: ensena que la lista se relleno hasta ocho.
  const top = [...fuente]
    .filter((m) => cifra(m) > 0)
    .sort((a, b) => cifra(b) - cifra(a))
    .slice(0, 8);
  const maximo = Math.max(...top.map(cifra), 1);

  // El titulo dice en que banda esta ordenando. El `.md` siempre lo decia
  // —«top 15, por población en MMI≥8»— y el visor no, asi que la misma lista
  // salia sin marco en la pantalla que mas gente mira.
  const titulo = $("titulo-municipios");
  if (titulo) titulo.textContent = `Municipios más expuestos · MMI≥${bandaMostrada}`;

  // Sin ninguna fila con gente, el bloque entero sobra: es el caso de los tres
  // eventos que no dejaron a nadie dentro, y ahi ya lo dice el panel de arriba.
  const bloque = $("bloque-municipios");
  if (bloque) bloque.hidden = !top.length;

  $("detalle-barras").innerHTML = top
    .map((m) => {
      const pct = (100 * cifra(m)) / maximo;
      // `bandaColor` y no `banda`: sombreaba a la de fuera, que es la que decide
      // que cifra se lee. Dos cosas distintas con el mismo nombre en el mismo
      // ambito es como se cuela el error que este bloque acaba de tener.
      const bandaColor = CAPAS.mmi.cortes.filter((c) => (m.mmi_max || 0) >= c).length - 1;
      const color = CAPAS.mmi.colores[Math.max(0, bandaColor)];
      const nombre = escapar(capitalizar(m.nombre) || m.adm2_id);
      const mmi = Number.isFinite(m.mmi_max) ? numero(m.mmi_max, 1) : "—";
      // A partir de MMI 7,5 la rampa de ShakeMap ya es roja: el texto de la
      // ficha pasa a blanco o queda verde bosque sobre rojo oscuro.
      const oscuro = bandaColor >= 3;
      return (
        `<li><div class="barra-fila"><span class="barra-nombre">` +
        `<span class="ficha-mmi${oscuro ? " sobre-oscuro" : ""}" style="background:${color}" ` +
        `title="Intensidad máxima ${mmi}">${mmi}</span>` +
        `${nombre}</span>` +
        `<span class="barra-valor">${comoConteo(cifra(m))}</span></div>` +
        `<div class="barra-pista"><div class="barra-relleno" ` +
        `style="width:${pct.toFixed(1)}%;background:${color}"></div></div></li>`
      );
    })
    .join("");
}

// Exposición no es daño, y para dos eventos hay medida ajena que lo demuestra.
// Las cifras y su método están en VERIFICACIONES.md; aquí se enseñan al lado de
// las de exposición, que es donde la diferencia se entiende sin explicarla.
const CONTRASTES = {
  us6000tjl2: { fuente: "Microsoft AI for Good Lab", zona: "Cali", evaluadas: 97351, danadas: 266 },
  us6000t7zp: { fuente: "Microsoft AI for Good Lab", zona: "La Guaira", evaluadas: 26143, danadas: 965 },
};

function pintarContraste(usgsId, totales) {
  const c = CONTRASTES[usgsId];
  const bloque = $("bloque-contraste");
  bloque.hidden = !c;
  if (!c) return;
  const pct = ((100 * c.danadas) / c.evaluadas).toFixed(2).replace(".", ",");
  $("detalle-contraste").innerHTML =
    `Este reporte publica <strong>${comoConteo(totales.bld_mmi7p)} edificaciones ` +
    `expuestas</strong> a MMI≥7 en todo el país. En ${c.zona}, ${c.fuente} evaluó ` +
    `${numero(c.evaluadas)} por imagen satelital y detectó daño en ` +
    `<strong>${numero(c.danadas)} (${pct} %)</strong>. Son dos preguntas distintas: ` +
    `exposición es quién quedó dentro de la franja; daño es a quién le pasó algo.`;
}

function pintarIncertidumbre(reporte) {
  const inc = reporte.incertidumbre || {};
  const bloque = $("bloque-incertidumbre");
  const partes = [];
  if (Number.isFinite(inc.pop_discrepancia_pct)) {
    // EL VISOR EXPLICABA ESTA CIFRA AL REVES DE COMO LA CALCULA EL PIPELINE.
    //
    // El SQL que la produce (`p2_impact/pipeline.py`) es
    // `100 * |Σ pop_total − Σ pop_alt_worldpop| / Σ pop_alt_worldpop` **sobre
    // las celdas alcanzadas por el evento**: el desacuerdo entre GHS-POP y
    // WorldPop dentro de las bandas MMI publicadas. El `report.md` del mismo
    // evento lo dice asi —«en las bandas MMI publicadas»— y este
    // panel decia «difiere del total nacional del mismo producto» y lo atribuia
    // al «remuestreo a hexágonos». Ni es nacional, ni es el mismo producto, ni
    // es remuestreo. Dos artefactos del mismo sistema explicando el mismo numero
    // de dos maneras incompatibles.
    const pct = inc.pop_discrepancia_pct;
    // Y CUANDO EL DESACUERDO ES ENORME, SE DICE QUE LO ES.
    //
    // Carúpano publica 416,9 % con la misma tipografia de nota al pie que un
    // 0,8 %. Sobre 3.416 personas expuestas, dos productos de poblacion pueden
    // discrepar en varias veces la cifra sin que ninguno este roto — pero
    // enseñarlo como un apunte rutinario invita a leer las cifras del evento con
    // una confianza que no tienen.
    const enorme = pct >= 25;
    partes.push(
      `Dentro de las bandas MMI publicadas, GHS-POP y WorldPop difieren en ` +
      `<strong${enorme ? ' class="cifra-alerta"' : ""}>${numero(pct, 1)} %</strong>. ` +
      `Son dos mediciones abiertas de la misma población, no un margen del ShakeMap, ` +
      `y se publica en vez de esconderse.`
    );
    if (enorme) {
      partes.push(
        `Un desacuerdo de este tamaño suele venir de un corte pequeño, ` +
        `donde cualquier diferencia local pesa mucho sobre el total: léanse las ` +
        `cifras de este reporte como un orden de magnitud.`
      );
    }
  }
  if (Array.isArray(inc.notas)) partes.push(...inc.notas.map(escapar));
  bloque.hidden = !partes.length;
  if (partes.length) $("detalle-incertidumbre").innerHTML = partes.join(" ");
}

// El pipeline publica también el mapa estático, la versión para prensa y el
// hilo para redes. Estaban en el directorio del reporte y no los enlazaba
// nadie: artefactos que se generan en cada evento y que no existían para quien
// entraba por el visor.
function pintarDescargas(usgsId) {
  const base = `reports/${usgsId}`;
  const enlaces = [
    ["Reporte", `${base}/report.md`],
    ["JSON", `${base}/report.json`],
    ["CSV municipal (HXL)", `${base}/adm2.csv`],
    ["Malla H3", `${base}/celdas.json`],
    ["Área de afectación", `${base}/contornos.json`],
    ["Mapa PNG", `${base}/mapa_general.png`],
    ["Mapa para prensa", `${base}/mapa_prensa.png`],
    ["Hilo para redes", `${base}/hilo.txt`],
  ];
  $("detalle-descargas").innerHTML = enlaces
    .map(([texto, url]) => `<a href="${url}">${texto}</a>`)
    .join(" · ");
}

// --- Lo que el visor declara haber pintado -----------------------------------
//
// El visor publica lo que dibujo, por la misma razon por la que el pipeline
// publica `/status`: un sistema que no dice lo que hizo solo se puede comprobar
// mirandolo, y mirar no escala.
//
// NACE DE UN FALLO DE DIAGNOSTICO, no de una necesidad de pruebas. El
// 28-ago-2026 se reviso el visor a ojo y se dieron por rotas tres capas que
// estaban perfectamente: los sismos del panorama, la malla de intensidad de un
// evento y la capa de focos activos. Las tres se habian medido **antes de que
// terminaran de pintar** — la malla tarda unos diez segundos.
//
// Sin una senal que diga "ya esta", la unica alternativa es esperar N segundos.
// Y N siempre es demasiado corto el dia que la red va lenta, o demasiado largo
// el resto de los dias. Un vigilante que da falsos positivos se aprende a
// ignorar, que es la misma leccion que dejo `frescura`.
//
// Cuenta rasgos y no un booleano a proposito: "la capa existe" no distingue
// una malla dibujada de una malla vacia, y ese es justo el cero silencioso que
// este proyecto persigue en el resto del sistema.
const pintado = {};
const erroresAlPintar = [];

function anotarPintado(nombre, rasgos) {
  pintado[nombre] = { rasgos, utc: new Date().toISOString() };
}

// Cambiar de capa NO repinta la malla: la reestiliza con `setPaintProperty` y
// `setFilter` sobre la misma fuente, que es lo eficiente y lo correcto. Por eso
// no vale contar rasgos aqui — no cambian.
//
// Lo que si hay que poder comprobar desde fuera es que **la leyenda y el mapa
// hablan del mismo dato**. Una malla coloreada por intensidad bajo una leyenda
// de poblacion se lee como una cifra plausible y equivocada, que es el modo de
// fallo que este proyecto persigue en todas partes.
function anotarCapaActiva(id, columna) {
  pintado.capa = { id, columna, utc: new Date().toISOString() };
}

//: Evalua una expresion de estilo de MapLibre sobre unas variables dadas.
//:
//: Existe para `tintaDelFuego`, que necesita saber cuanto mide cada circulo sin
//: copiar la formula: copiarla seria tener dos definiciones del mismo radio, y
//: dos definiciones divergen en cuanto nadie las compara — que es la regla que
//: este fichero se aplica en todas partes.
//:
//: Cubre solo los operadores que la capa usa. Si alguien mete uno nuevo, esto
//: lanza en vez de devolver un numero plausible: un cero silencioso aqui
//: pasaria la prueba de tinta con la simbologia rota.
function evaluarExpresion(exp, vars) {
  if (typeof exp === "number") return exp;
  if (!Array.isArray(exp)) throw new Error("expresión no soportada: " + JSON.stringify(exp));
  const [op, ...args] = exp;
  const ev = (x) => evaluarExpresion(x, vars);
  if (op === "zoom") return vars.zoom;
  if (op === "get") return Number(vars[args[0]]) || 0;
  if (op === "coalesce") {
    for (const a of args) {
      const v = ev(a);
      if (v !== null && v !== undefined && !Number.isNaN(v)) return v;
    }
    return 0;
  }
  if (op === "+") return args.reduce((t, a) => t + ev(a), 0);
  if (op === "*") return args.reduce((t, a) => t * ev(a), 1);
  if (op === "-") return args.length === 1 ? -ev(args[0]) : ev(args[0]) - ev(args[1]);
  if (op === "sqrt") return Math.sqrt(ev(args[0]));
  if (op === "step") {
    const v = ev(args[0]);
    let salida = ev(args[1]);
    for (let i = 2; i < args.length; i += 2) {
      if (v >= args[i]) salida = ev(args[i + 1]);
    }
    return salida;
  }
  if (op === "interpolate") {
    // Solo lineal, que es la unica que usa esta capa.
    const [tipo, entrada, ...paradas] = args;
    if (tipo[0] !== "linear") throw new Error("interpolación no lineal sin soporte");
    const x = ev(entrada);
    const puntos = [];
    for (let i = 0; i < paradas.length; i += 2) puntos.push([paradas[i], paradas[i + 1]]);
    if (x <= puntos[0][0]) return ev(puntos[0][1]);
    const ultimo = puntos[puntos.length - 1];
    if (x >= ultimo[0]) return ev(ultimo[1]);
    for (let i = 0; i < puntos.length - 1; i += 1) {
      const [x0, y0] = puntos[i];
      const [x1, y1] = puntos[i + 1];
      if (x >= x0 && x <= x1) {
        const t = (x - x0) / (x1 - x0);
        return ev(y0) + t * (ev(y1) - ev(y0));
      }
    }
  }
  throw new Error("operador no soportado: " + op);
}

// Superficie publica y estable. No lleva guiones bajos ni `__test__`: no es un
// gancho de pruebas, es el visor rindiendo cuentas — y sirve igual para
// diagnosticar desde la consola del navegador de quien reporte un fallo.
window.CENTINELA = {
  pintado,
  errores: erroresAlPintar,
  camara,
  //: Las cifras que el tablero esta ensenando AHORA, ya cruzadas con los
  //: filtros. Existe para poder compararlas con el bloque `totales` que
  //: publica el pipeline: son dos implementaciones de la misma suma —una en
  //: Python y otra aqui— y dos implementaciones divergen en cuanto nadie las
  //: compara. Sin filtros tienen que dar identico.
  //: El area que el visor da por buena para una celda de fuego. La prueba de
  //: navegador comprueba el cableado contra ESTA cifra; que la cifra sea la
  //: correcta lo comprueba la suite unitaria contra `h3`, que es donde vive.
  areaDeUnaCeldaDeFuego: () => AREA_CELDA_FUEGO_KM2,
  totalesDelTablero: () => estado.vivo.incendios || {},
  //: Lo que sale de sumar en el navegador las celdas que pasan los filtros.
  //: Se expone aparte de `totalesDelTablero` porque no siempre son lo mismo:
  //: sin filtros el tablero ensena los totales del pipeline, que son exactos
  //: aunque el fichero venga recortado. Esto es la otra implementacion de la
  //: misma suma, y existe para poder compararlas.
  sumaDelVisor: () => totalesDeFuego(celdasDeFuegoFiltradas()),
  //: Si el `incendios.json` servido trae todas las celdas o una muestra.
  ficheroCompleto: () => !(estado.vivo && estado.vivo.recortadoEnOrigen),
  //: Puerta para las pruebas de navegador. Ver `abrirFocoDePrueba`.
  abrirFoco: (indice) => abrirFocoDePrueba(indice),
  //: El punto de reticula que le toco al foco abierto, tal cual sale del JSON.
  //:
  //: Existe para poder comprobar la INVERSION de la flecha contra el dato real
  //: en vez de contra una constante escrita en la prueba. Es el unico sitio del
  //: visor donde un signo cambiado no rompe nada, no sale de rango, no aparece
  //: en ningun log y pone todas las flechas al reves.
  vientoDelFocoAbierto: () =>
    estado.focoAbierto ? vientoDelFoco(estado.focoAbierto) : null,
  //: Los ids del estilo en orden de dibujo. Es como se comprueba que la
  //: mascara va **encima** del mapa base y **debajo** del dato: contar pixeles
  //: en una captura no distingue "el velo esta bien puesto" de "todavia no se
  //: ha pintado nada".
  capasDelMapa: () => {
    const m = estado.mapa;
    try {
      return m && m.getStyle() ? m.getStyle().layers.map((c) => c.id) : [];
    } catch (error) {
      return [];
    }
  },
  //: Cuantas capas de rotulos hablan espanol y cuantas se quedaron en el idioma
  //: local. Se mira la EXPRESION puesta en el estilo y no un texto pintado:
  //: que tesela cae en pantalla depende del encuadre y de la red, y una prueba
  //: que dependa de eso falla por el sitio equivocado.
  rotulosEnEspanol: () => {
    const m = estado.mapa;
    const cuenta = { tocadas: 0, sinTraducir: 0 };
    try {
      for (const capa of m.getStyle().layers) {
        if (capa.type !== "symbol") continue;
        const campo = m.getLayoutProperty(capa.id, "text-field");
        if (campo === undefined || campo === null) continue;
        const texto = JSON.stringify(campo);
        if (!texto.includes("name")) continue;
        if (texto.includes("name:es")) cuenta.tocadas += 1;
        else cuenta.sinTraducir += 1;
      }
    } catch (error) {
      /* sin estilo cargado se devuelve lo contado hasta aqui */
    }
    return cuenta;
  },
  //: Tira la rejilla de viento, para poder ver el visor sin ella.
  //:
  //: Con el fichero de hoy los 3.337 puntos cubren los 6.239 focos, asi que el
  //: caso "GFS no llego" no se da nunca y una prueba que lo espere pasa sin
  //: comprobar nada. Esto lo provoca. No hay otra forma de llegar ahi desde
  //: fuera, y el dia que `p5_incendios/viento.py` se rinda tras sus cuatro
  //: reintentos es el estado en el que quedara el visor.
  olvidarElViento: () => {
    if (estado.fuegoDatos) estado.fuegoDatos.viento = null;
  },
  //: En que orden se apilan los simbolos de una capa. Sin esto no hay forma de
  //: comprobar que el fuego fuerte queda encima: contar pixeles de un color en
  //: una captura no distingue "esta debajo" de "no se ha pintado".
  ordenDeDibujo: (capa) => {
    const m = estado.mapa;
    try {
      return m && m.getLayer(capa) ? m.getLayoutProperty(capa, "circle-sort-key") : null;
    } catch (error) {
      return null;
    }
  },
  //: Cuanta superficie de pantalla cubren los circulos de fuego, contra la que
  //: hay. Ver el comentario largo de `incendios-punto`: la mancha era
  //: aritmetica, no mala suerte, y una prueba que mire una captura no la
  //: distingue de un solape afortunado.
  //:
  //: Se evalua la expresion que la capa tiene puesta AHORA —no una copia— para
  //: que la medida siga a la simbologia si alguien la cambia.
  tintaDelFuego: (zoom) => {
    const m = estado.mapa;
    const datos = estado.fuegoDatos;
    if (!m || !datos || !m.getLayer("incendios-punto")) return null;
    let radio;
    try {
      radio = m.getPaintProperty("incendios-punto", "circle-radius");
    } catch (error) {
      return null;
    }
    const r = (frp) => evaluarExpresion(radio, { zoom, frp_suma: frp });
    const tinta = (celdas) => celdas.reduce((t, c) => t + Math.PI * r(c.frp_suma || 0) ** 2, 0);
    const celdas = datos.celdas || [];
    const lienzo = m.getCanvas().clientWidth * m.getCanvas().clientHeight;
    const debiles = celdas.filter((c) => (c.frp_suma || 0) < 10);
    const fuertes = celdas.filter((c) => (c.frp_suma || 0) >= 400);
    return {
      tinta: tinta(celdas),
      lienzo,
      veces: tinta(celdas) / lienzo,
      debilesSobreFuertes: fuertes.length ? tinta(debiles) / tinta(fuertes) : 0,
    };
  },
  //: La caja que el mapa esta enseñando. Para poder afirmar que el encuadre
  //: inicial mira a America Latina y no al Sahel.
  encuadre: () => {
    const m = estado.mapa;
    try {
      const b = m.getBounds();
      return {
        oeste: b.getWest(),
        este: b.getEast(),
        sur: b.getSouth(),
        norte: b.getNorth(),
        zoom: m.getZoom(),
      };
    } catch (error) {
      return null;
    }
  },
  //: El filtro que MapLibre tiene puesto sobre una capa. Es como se comprueba
  //: que un filtro toca el MAPA y no solo la lista: contar hexagonos en una
  //: captura no distingue "filtrado" de "la animacion no avanzo".
  filtroDeCapa: (capa) => {
    const m = estado.mapa;
    try {
      return m && m.getLayer(capa) ? m.getFilter(capa) : null;
    } catch (error) {
      return null;
    }
  },
};

// --- El selector de amenaza --------------------------------------------------
//
// Un solo mapa y un lente a la vez, como Windy o Zoom Earth: la amenaza activa
// manda —su simbologia, su leyenda en el hueco grande, sus controles— y la otra
// queda de contexto discreto. Ni dos rampas de color compitiendo por el mismo
// mapa, ni el fuego escondido detras de una casilla.
//
// La regla de contexto es asimetrica a proposito. En modo fuego los epicentros
// se quedan como estrellas tenues: son veintiuno, no estorban, y responden
// "¿el sismo cayo donde ardia?" sin robar el mapa. En modo sismos el fuego no
// se dibuja: son cuatro mil simbolos con rampa propia, y "discreto" no es algo
// que cuatro mil simbolos sepan ser.

//: Aplica el modo actual sobre lo que exista. Idempotente y defensiva a
//: proposito: las capas llegan cada una a su ritmo —epicentros, observados y
//: fuego cargan en paralelo— asi que esto se re-ejecuta cuando cada una termina
//: de dibujarse, y toca solo lo que ya esta.
function aplicarAmenaza() {
  const fuego = estado.amenaza === "fuego";
  const m = estado.mapa;

  for (const boton of document.querySelectorAll("#amenazas button")) {
    boton.setAttribute("aria-pressed", String(boton.dataset.amenaza === estado.amenaza));
  }

  // Sin `isStyleLoaded()` de puerta: durante la carga inicial es false mientras
  // llegan teselas y sprites, y el enlace profundo a modo fuego pasaba por aqui
  // justo entonces — los paints se saltaban y nadie los re-aplicaba: epicentros
  // a toda opacidad y con etiqueta sobre el fuego. `pon` ya es defensiva capa a
  // capa, que es la unica guarda que hace falta.
  if (m) {
    const pon = (capa, prop, valor, deLayout = false) => {
      try {
        if (!m.getLayer(capa)) return;
        if (deLayout) m.setLayoutProperty(capa, prop, valor);
        else m.setPaintProperty(capa, prop, valor);
      } catch (error) {
        /* el estilo puede estar en transicion; el siguiente aplicar lo pone */
      }
    };

    for (const capa of ["incendios", "incendios-punto", "incendios-borde"]) {
      pon(capa, "visibility", fuego ? "visible" : "none", true);
    }

    // Tenues, no ausentes: la etiqueta ("M7,4") si se apaga, porque veintiuna
    // magnitudes rotuladas encima del fuego son ruido, no contexto.
    pon("epicentros", "icon-opacity", fuego ? 0.35 : 1);
    pon("epicentros", "text-opacity", fuego ? 0 : 1);
    if (fuego) pon("epicentros-halo", "visibility", "none", true);
    else verHaloProporcional(!estado.seleccionado);

    const casillaObs = document.querySelector("#interruptor-observados input");
    pon(
      "observados",
      "visibility",
      !fuego && casillaObs && casillaObs.checked ? "visible" : "none",
      true
    );
  }

  // Los controles del modo sismos no aplican al fuego.
  const obs = $("interruptor-observados");
  if (obs) obs.hidden = fuego;

  // EL PANEL TAMBIEN CAMBIA DE AMENAZA.
  //
  // Cambiar solo las capas del mapa dejaba el lateral mezclado: en modo fuego
  // se leia "9 sismos vistos y no despachados" y debajo el panorama sismico
  // entero —21 reportes, el Choco, los 15 paises—; en modo sismos seguia la
  // tarjeta de fuego. Dos amenazas hablando a la vez, que es justo lo que el
  // selector existe para evitar.
  // Cada bloque de la tarjeta declara de que amenaza es, y aqui solo se
  // compara. Enumerarlos —"si es incendios, en modo fuego"— ya fallo una vez:
  // el titular se ocultaba pero "171 sedes de salud EN CELDAS CON FUEGO ACTIVO"
  // y "SOBRE QUÉ ESTÁ ARDIENDO" seguian en el panel de sismos, porque anadir un
  // bloque nuevo no obliga a acordarse de esta funcion. Ahora si.
  for (const bloque of document.querySelectorAll("#en-vivo [data-amenaza]")) {
    bloque.hidden = bloque.dataset.amenaza !== estado.amenaza;
  }
  const panorama = $("bloque-panorama");
  if (panorama) panorama.hidden = fuego;
  const pistaFuego = $("pista-fuego");
  if (pistaFuego) pistaFuego.hidden = !fuego;
  // Cada amenaza tiene su indice, y solo uno a la vez: leer "Reportes
  // publicados" con el mapa lleno de fuego es la misma mezcla que el selector
  // existe para evitar.
  // La barra ensena los filtros de la amenaza al mando: dos "País" uno al lado
  // del otro serian dos amenazas hablando a la vez.
  verCampo("campo-ventana", !fuego);
  verCampo("campo-orden", !fuego);
  verCampo("campo-ventana-fuego", fuego);
  verCampo("campo-orden-fuego", fuego);
  // La extensión vale para las dos amenazas: aquí decía `hidden = fuego`, que
  // es lo que la escondía en cuanto se cambiaba de amenaza —aunque el
  // enganchado la mostrara— y dejaba el fuego sin el filtro más natural de un
  // tablero de mapa.
  const enVista = $("etiqueta-en-vista");
  if (enVista && estado.mapa) enVista.hidden = false;
  const cuentaSismos = $("cuenta-lista");
  if (cuentaSismos) cuentaSismos.hidden = fuego;
  const cuentaFuego = $("cuenta-focos");
  if (cuentaFuego) cuentaFuego.hidden = !fuego;
  // El campo de pais de la OTRA amenaza se oculta aqui y siempre. Dejarlo en
  // manos de su pintor —que solo corre cuando toca— es como acabaron dos "País"
  // uno al lado del otro, con Colombia y Brasil compitiendo en la misma barra.
  verCampo("campo-pais", false);
  verCampo("campo-pais-fuego", false);
  // Y el de la amenaza al mando se vuelve a preguntar: solo aparece si de
  // verdad tiene paises que ofrecer, y eso lo decide su pintor.
  if (fuego) pintarControlesFocos();
  else if (estado.eventos && estado.nombresPais) {
    pintarFiltroPaises(estado.eventos, estado.nombresPais);
  }
  pintarLimpiar();

  // Y LOS FILTROS SE VUELVEN A PONER SOBRE LAS CAPAS.
  //
  // Carrera de nacimiento, la misma que ya mordio al interruptor de observados y
  // a la tarjeta viva: las capas se crean cuando llegan sus datos, que es
  // despues de que un filtro se haya aplicado. `setFilter` sobre una capa que
  // aun no existe no hace nada —`pon` lo avisa y sigue— y nadie volvia a
  // intentarlo, asi que las tres capas de fuego nacian SIN la ventana de horas:
  // el mapa ensenaba cuatro mil celdas y la lista contaba menos.
  //
  // Aqui es el sitio: los tres pintores terminan llamando a esta funcion, asi
  // que cubre los tres nacimientos y ademas cada cambio de amenaza.
  aplicarFiltrosAlMapa();

  const seccionEventos = $("eventos");
  const seccionFocos = $("focos");
  if (seccionEventos) seccionEventos.hidden = fuego;
  if (seccionFocos) seccionFocos.hidden = !fuego || !estado.focos.length;
  if (fuego && estado.focos.length) {
    pintarControlesFocos();
    pintarListaFocos({ anunciando: false });
  }
  const enVivo = $("en-vivo");
  if (enVivo) {
    // La tarjeta se queda si le queda alguna cifra que mostrar en este modo.
    const visibles = enVivo.querySelectorAll(".metrica:not([hidden])").length;
    enVivo.hidden = !visibles;
  }
  if (!fuego) cerrarFoco();

  // El hueco grande de la leyenda es del modo: variable de la malla en sismos
  // (solo con evento), potencia radiativa en fuego.
  if (fuego) {
    $("capas").hidden = true;
    pintarLeyendaFuego(estado.fuegoDatos);
  } else if (!estado.seleccionado) {
    $("leyenda").hidden = true;
  }

  // La leyenda de simbolos, al final y siempre: es la unica que sabe listar lo
  // que hay AHORA, y "ahora" acaba de cambiar. Los tres pintores pasan por
  // aqui, asi que tambien cubre el nacimiento de cada capa.
  pintarLeyendaSimbolos();
  // El aviso de cabecera habla de franjas de intensidad, que en modo fuego no
  // significan nada. Ver `avisoDeLectura`.
  pintarAvisoDeLectura();
}

function cambiarAmenaza(modo, { anunciando = true } = {}) {
  if (modo === estado.amenaza) return;
  estado.amenaza = modo;

  // Un evento abierto es contenido del modo sismos: sus variables, su malla y
  // su panel no significan nada bajo el lente del fuego. Entrar a fuego lo
  // cierra, con su vuelo de vuelta al panorama incluido.
  if (modo === "fuego" && estado.seleccionado) cerrarDetalle();

  aplicarAmenaza();
  escribirUrl();
  if (anunciando) {
    anunciar(
      modo === "fuego"
        ? "Modo fuego: focos activos de las últimas 24 horas. Los sismos quedan como contexto."
        : "Modo sismos: reportes de exposición sísmica."
    );
  }
}

function pintarSelectorAmenaza() {
  for (const boton of document.querySelectorAll("#amenazas button")) {
    boton.addEventListener("click", () => cambiarAmenaza(boton.dataset.amenaza));
  }
}

// --- Mapa -------------------------------------------------------------------

// MapLibre lanza "Style is not done loading" ante `getStyle`, `addLayer` o
// `getSource` antes de que el estilo termine. Con enlace profundo eso pasa de
// verdad: `report.json` es local y llega antes que el estilo, que viene de
// OpenFreeMap. El sintoma era un tablero con todas las cifras bien y el titulo
// cambiado por "No se pudo abrir el reporte".
//
// Se espera al evento `load`, que es el mismo gancho con el que ya se dibujan
// los epicentros: `load` no llega hasta que el estilo esta completo, mientras
// que `styledata` puede haber pasado ya y no volver, dejando la malla sin
// dibujar para siempre.
// `once("load")` dispara **una sola vez**, la primera que el mapa carga. Si ya
// disparó y `isStyleLoaded()` sigue devolviendo false —pasa mientras una fuente
// está en vuelo— el callback se registra para un evento que no volverá, y la
// malla no se dibuja nunca.
//
// Reproducido: abrir `?evento=us7000nr0v` con la caché fría deja el mapa en
// blanco, sin base, sin malla, sin leyenda y sin un error en consola. Con la
// caché caliente el mismo enlace funciona, así que es una carrera — y le toca
// justo a quien abre por primera vez un enlace que alguien le compartió, que es
// el único público que este visor tiene todavía.
//
// `styledata` se emite cada vez que el estilo cambia e `idle` cuando todo se
// asienta: entre los dos no hay ventana en la que el aviso se pierda.
function cuandoElEstiloEsteListo(m, fn) {
  // NINGUN FALLO DE AQUI PUEDE SER SILENCIOSO.
  //
  // `fn` corre **diferido**, dentro de un manejador de eventos de MapLibre. El
  // `try/catch` de quien llamo a esto ya termino, y MapLibre se traga lo que
  // lance un manejador. Resultado: la malla de un evento no se dibujaba, el
  // selector de capas se quedaba oculto, y no habia ni una linea en consola.
  //
  // Dos horas de diagnostico para un fallo que se anunciaba solo en cuanto
  // alguien lo dejaba hablar.
  const seguro = () => {
    try {
      fn();
    } catch (error) {
      console.error("fallo al dibujar sobre el mapa:", error);
      // Y queda anotado, no solo en consola: quien comprueba el visor desde
      // fuera no ve la consola, y un `pintado` incompleto sin explicacion
      // manda a buscar una lentitud que no existe.
      erroresAlPintar.push({ mensaje: String((error && error.message) || error) });
    }
  };

  if (m.isStyleLoaded()) {
    seguro();
    return;
  }

  // UNA VEZ, Y SOLO UNA.
  //
  // La red de seguridad de abajo no se cancelaba cuando el camino normal
  // funcionaba: se quitaban los dos escuchadores y el `setTimeout` seguia en
  // pie, asi que **todo dibujo diferido corria dos veces**. La segunda pasada
  // llega a un `addSource` que ya existe y lanza.
  //
  // No se veia al arrancar porque ahi el estilo suele estar listo y se toma el
  // atajo de arriba. Se veia con `?evento=` sobre estilo frio —el enlace
  // profundo, que es como llega quien recibe un reporte compartido— y dejaba
  // `Source "celdas" already exists.` en el registro publico de errores.
  let hecho = false;
  let red = 0;
  const unaVez = () => {
    if (hecho) return;
    hecho = true;
    clearTimeout(red);
    m.off("styledata", reintentar);
    m.off("idle", reintentar);
    seguro();
  };

  const reintentar = () => {
    if (!m.isStyleLoaded()) return;
    unaVez();
  };
  m.on("styledata", reintentar);
  m.on("idle", reintentar);

  // Y una red por si `isStyleLoaded()` no llega a ser cierto nunca — pasa
  // cuando una fuente se queda a medias. Sin esto el callback no corre jamas y
  // el visor se queda a medio pintar sin decir nada.
  red = setTimeout(() => {
    if (!m.getStyle()) return;
    unaVez();
  }, 4000);
}

// El circulo proporcional se apaga en cuanto hay malla en pantalla: la
// extension real del evento ya esta dibujada y el circulo solo anadiria un
// radio que nadie ha calculado.
function verHaloProporcional(visible) {
  const m = estado.mapa;
  if (!m) return;
  // Sin guardia de `isStyleLoaded`: acabamos de anadir la fuente de la malla y
  // mientras esa fuente carga, `isStyleLoaded()` devuelve false aunque el
  // estilo lleve rato listo. Con la guardia puesta, el circulo se quedaba
  // encendido debajo de la coropleta en cada evento.
  try {
    if (!m.getLayer("epicentros-halo")) return;
    m.setLayoutProperty("epicentros-halo", "visibility", visible ? "visible" : "none");
  } catch (e) {
    /* el estilo aun no esta; el halo se ajusta en el siguiente cambio */
  }
}

//: El globo abierto, uno solo y localizable.
//:
//: No habia ninguna limpieza de popups en el visor. Se abria una celda, se
//: pulsaba "Volver al panorama" y el globo se quedaba flotando sobre el mapa
//: continental describiendo una celda de un evento cerrado, sobre una malla que
//: ya no estaba — y el de celda es el unico de los tres sin boton de cerrar, asi
//: que solo se iba pulsando el mapa por casualidad.
//:
//: MapLibre ya cierra el anterior al abrir otro (`closeOnClick`), asi que esto
//: no cambia el comportamiento normal: solo da un asa para cerrarlo cuando lo
//: que desaparece es el dato de debajo.
function abrirGlobo(popup) {
  cerrarGlobo();
  estado.globo = popup;
  popup.on("close", () => {
    if (estado.globo === popup) estado.globo = null;
  });
  return popup;
}

function cerrarGlobo() {
  if (!estado.globo) return;
  try {
    estado.globo.remove();
  } catch (error) {
    /* ya estaba fuera del DOM */
  }
  estado.globo = null;
}

function quitarCapa(id) {
  const m = estado.mapa;
  if (!m || !m.isStyleLoaded() || !m.getSource(id)) return;
  // El perimetro lleva funda blanca debajo de la linea, asi que una fuente puede
  // tener dos capas colgando. Los sufijos se listan aqui una sola vez.
  for (const sufijo of ["", "-borde"]) {
    if (m.getLayer(id + sufijo)) m.removeLayer(id + sufijo);
  }
  m.removeSource(id);
}


// --- Area de afectacion -----------------------------------------------------
//
// La malla H3 dibuja donde hay **gente**: llega hasta donde hay algo expuesto y
// se corta ahi, con huecos que son ausencia de poblacion y no de sacudida. Su
// propia nota lo admitia, y aun asi era lo unico que el tablero enseñaba: quien
// preguntaba "¿hasta dónde llegó el terremoto?" no tenía dónde mirarlo.
//
// Los contornos del ShakeMap sí son eso — la isolínea de cada nivel de
// intensidad, sobre tierra y sobre mar, con gente o sin ella.
//
// Van **debajo** de la malla: donde hay hexágonos, el dato manda; fuera de
// ellos, la línea es lo único, y es justo donde hace falta.

//: Color de cada isolínea. De 6 para arriba, la rampa del sistema — la misma
//: del mapa estático del reporte. Por debajo, un tono neutro: son niveles que
//: se sienten y que este sistema **no cuantifica**, y pintarlos con la rampa de
//: intensidad sugeriría que sí.
const COLOR_CONTORNO_BAJO = "#9a8f7d";

function colorDeContorno() {
  const pasos = ["step", ["coalesce", ["get", "mmi"], 0], COLOR_CONTORNO_BAJO];
  CAPAS.mmi.cortes.forEach((corte, i) => pasos.push(corte, CAPAS.mmi.colores[i]));
  return pasos;
}

function dibujarContornos(m, datos, antes) {
  if (!datos || !datos.features || !datos.features.length) {
    anotarPintado("contornos", 0);
    return;
  }
  anotarPintado("contornos", datos.features.length);

  m.addSource("contornos", { type: "geojson", data: datos });
  m.addLayer({
    id: "contornos",
    type: "line",
    source: "contornos",
    layout: { "line-join": "round", "line-cap": "round" },
    paint: {
      "line-color": colorDeContorno(),
      // La isolínea de MMI 6 va más gruesa: es el umbral desde el que este
      // sistema publica cifras, así que es la frontera que de verdad separa
      // "aquí hay algo que contar" de "aquí no".
      "line-width": [
        "interpolate", ["linear"], ["zoom"],
        4, ["case", [">=", ["get", "mmi"], 6], 1.6, 0.7],
        9, ["case", [">=", ["get", "mmi"], 6], 3.2, 1.4],
      ],
      "line-opacity": ["case", [">=", ["get", "mmi"], 6], 0.95, 0.6],
    },
  }, antes);
}

// El area que el sistema **cuantifica**: la isolinea de MMI 6. Es la que acota
// el encuadre, no la de MMI 4 —que en un M8 abarca medio continente y dejaria
// la malla del tamano de un sello— ni la malla sola, que se corta donde se
// acaba la gente.
function extremosDeContorno(datos, minimo) {
  const lons = [];
  const lats = [];
  for (const f of (datos && datos.features) || []) {
    if (Number(f.properties.mmi) < minimo) continue;
    for (const linea of f.geometry.coordinates) {
      for (const [lon, lat] of linea) {
        lons.push(lon);
        lats.push(lat);
      }
    }
  }
  return { lons, lats };
}

//: El perimetro de lo que se cuenta.
//:
//: A escala regional 890 hexagonos de 1 km de lado no se leen como una zona: se
//: leen como textura. La pregunta "¿que area quedo dentro?" tenia respuesta en
//: la malla y no tenia **forma**, y una forma es lo que se recuerda y lo que se
//: puede senalar en una reunion.
//:
//: Se disuelve con `h3.cellsToMultiPolygon`, que devuelve el contorno exacto de
//: la union de las celdas. Y ahi esta lo que lo hace honesto: **el borde es
//: literalmente el de las celdas que se cuentan y se descargan**, no una
//: isolinea de otro producto. La cifra del panel —"4.628 km² dentro de MMI≥7"— y
//: esta linea son el mismo objeto.
//:
//: Por eso convive con los contornos del ShakeMap en vez de sustituirlos: son
//: dos cosas distintas y el mapa ahora las distingue. La isolinea dice hasta
//: donde llego el sismo, tambien sobre el mar; este perimetro dice sobre que
//: territorio hay algo que contar.
function perimetroDeCeldas(datos, minimo) {
  if (typeof h3 === "undefined" || !datos || !Array.isArray(datos.celdas)) return null;
  const iH3 = datos.columnas.indexOf("h3");
  const iMmi = datos.columnas.indexOf("mmi");
  if (iH3 < 0 || iMmi < 0) return null;

  const dentro = datos.celdas
    .filter((c) => Number(c[iMmi]) >= minimo)
    .map((c) => c[iH3]);
  if (!dentro.length) return null;

  try {
    // `true` pide el orden GeoJSON —[lng, lat]—, el mismo motivo por el que
    // `cellToBoundary` lo lleva: sin el, el perimetro aparece en el indico.
    const poligonos = h3.cellsToMultiPolygon(dentro, true);
    if (!poligonos || !poligonos.length) return null;
    return {
      celdas: dentro.length,
      geojson: {
        type: "FeatureCollection",
        features: [
          { type: "Feature", properties: { mmi: minimo }, geometry: { type: "MultiPolygon", coordinates: poligonos } },
        ],
      },
    };
  } catch (error) {
    console.warn("perimetro:", error && error.message);
    return null;
  }
}

function dibujarPerimetro(m, datos, reporte, antes) {
  // La banda titular es la que rotula el resto del panel. Dibujar el perimetro
  // de otra banda pondria en el mapa un area que ninguna cifra nombra.
  const minimo = bandaDeTotales(reporte.totales) || 6;
  const per = perimetroDeCeldas(datos, minimo);
  if (!per) {
    anotarPintado("perimetro", 0);
    return;
  }
  anotarPintado("perimetro", per.celdas);

  m.addSource("perimetro", { type: "geojson", data: per.geojson });

  // NO se pinta con el color de su banda, que fue el primer intento y salio
  // invisible: la linea de MMI≥7 quedaba en #ef6548 **encima del relleno de
  // MMI 7**, que es exactamente ese color. Un borde tiene que contrastar con lo
  // que encierra, no igualarlo.
  //
  // Tinta oscura y funda blanca, que es como la cartografia dibuja un limite
  // desde siempre: la funda lo despega del relleno naranja y la tinta lo despega
  // del suelo crema. Y al no ser un tono de la rampa, no se puede confundir con
  // una banda mas de intensidad — que es justo lo que no es.
  const ANCHO = ["interpolate", ["linear"], ["zoom"], 4, 1.9, 9, 1.5, 12, 1.1];
  m.addLayer(
    {
      id: "perimetro-borde",
      type: "line",
      source: "perimetro",
      layout: { "line-join": "round", "line-cap": "round" },
      paint: {
        "line-color": "#ffffff",
        "line-width": ["interpolate", ["linear"], ["zoom"], 4, 4.2, 9, 3.4, 12, 2.6],
        "line-opacity": 0.75,
      },
    },
    antes
  );
  m.addLayer(
    {
      id: "perimetro",
      type: "line",
      source: "perimetro",
      layout: { "line-join": "round", "line-cap": "round" },
      paint: { "line-color": "#1c1b1a", "line-width": ANCHO, "line-opacity": 0.9 },
    },
    antes
  );
}

function pintarCeldas(datos, reporte, contornos) {
  const m = estado.mapa;
  if (!m) return;
  cuandoElEstiloEsteListo(m, () => dibujarCeldas(m, datos, reporte, contornos));
}

function dibujarCeldas(m, datos, reporte, contornos) {
  // Cambiar de evento tambien invalida el globo: describiria una celda del
  // sismo anterior junto a la malla del nuevo, que es la peor version de esto.
  cerrarGlobo();
  quitarCapa("celdas");
  quitarCapa("contornos");
  quitarCapa("perimetro");

  estado.presentes = datos
    ? new Set(datos.celdas.map((c) => c[datos.columnas.indexOf("mmi")]))
    : null;

  const geo = datos && celdasAGeoJson(datos);
  if (!geo || !geo.features.length) {
    // Sin malla el tablero sigue sirviendo: las cifras y las barras salen del
    // reporte. Se vuela al epicentro y no se finge una capa que no hay.
    $("capas").hidden = true;
    $("leyenda").hidden = true;
    verHaloProporcional(true);
    // Cero es una respuesta, y hay que poder distinguirla de "todavia no".
    anotarPintado("celdas", 0);
    if (Number.isFinite(reporte.event.lon) && reporte.event.lon !== 0) {
      m.easeTo({ center: [reporte.event.lon, reporte.event.lat], zoom: 7.5, duration: VUELO });
    }
    return;
  }

  // `generateId` da a cada hexágono un id estable dentro de la fuente, que es
  // lo que necesita `feature-state` para resaltar el de debajo del cursor.
  m.addSource("celdas", { type: "geojson", data: geo, generateId: true });

  anotarPintado("celdas", geo.features.length);

  const antes = primeraEtiqueta(m);
  dibujarContornos(m, contornos, antes);
  m.addLayer(
    {
      id: "celdas",
      type: "fill",
      source: "celdas",
      paint: {
        "fill-color": expresionColor(CAPAS[estado.capa]),
        "fill-opacity": [
          "case", ["boolean", ["feature-state", "encima"], false], 0.95, 0.85,
        ],
      },
      filter: [">", ["coalesce", ["get", CAPAS[estado.capa].columna], 0], 0],
    },
    antes
  );

  // El borde de la celda a zoom regional era un moiré: 5.000 hexágonos con una
  // línea blanca cada uno convertían la coropleta en textura. Aparece cuando el
  // hexágono ya mide lo bastante como para que su contorno signifique algo.
  m.addLayer(
    {
      id: "celdas-borde",
      type: "line",
      source: "celdas",
      paint: {
        "line-color": "#ffffff",
        "line-width": ["interpolate", ["linear"], ["zoom"], 7, 0, 9, 0.4, 12, 1],
        "line-opacity": ["interpolate", ["linear"], ["zoom"], 7, 0, 9, 0.45, 12, 0.65],
      },
    },
    antes
  );

  // Encima de la malla y de su borde: es la unica linea que tiene que sobrevivir
  // al zoom continental, donde los hexagonos se vuelven textura.
  dibujarPerimetro(m, datos, reporte, antes);

  verHaloProporcional(false);
  engancharCeldas(m);
  pintarSelectorCapas();
  pintarLeyenda(CAPAS[estado.capa]);

  const lons = geo.features.flatMap((f) => f.geometry.coordinates[0].map((c) => c[0]));
  const lats = geo.features.flatMap((f) => f.geometry.coordinates[0].map((c) => c[1]));

  // EL EPICENTRO ENTRA EN EL ENCUADRE.
  //
  // Encuadrar solo la malla deja fuera la estrella en cuanto el sismo ocurre
  // mar adentro, que en esta región es la mitad del catálogo. Medido sobre los
  // 18 eventos con malla: en tres —Carúpano, La Libertad y Bartolomé Masó— el
  // epicentro cae fuera de la caja de la malla, y en Cuba sale cortado por el
  // borde inferior de la pantalla.
  //
  // Ver la afectación *desde el epicentro* empieza por ver el epicentro.
  const epiLon = Number(reporte.event.lon);
  const epiLat = Number(reporte.event.lat);
  if (Number.isFinite(epiLon) && Number.isFinite(epiLat) && (epiLon || epiLat)) {
    lons.push(epiLon);
    lats.push(epiLat);
    estado.epicentro = [epiLon, epiLat];
  } else {
    estado.epicentro = null;
  }

  // Y el área que el sistema cuantifica, que se sale de la malla en cuanto la
  // sacudida cruza agua o despoblado: Guayaquil llega al golfo, y encuadrar
  // solo los hexágonos dejaba fuera la mitad del contorno de MMI 6.
  const borde = extremosDeContorno(contornos, 6);
  lons.push(...borde.lons);
  lats.push(...borde.lats);

  m.fitBounds(
    [[Math.min(...lons), Math.min(...lats)], [Math.max(...lons), Math.max(...lats)]],
    { padding: 48, maxZoom: 10, duration: VUELO }
  );
}

// Los manejadores se registran una sola vez. Antes se añadían dentro de
// `pintarCeldas`, así que cambiar de evento tres veces dejaba tres oyentes de
// clic y abría tres ventanitas de una vez.

// Distancia en km sobre la esfera, con el mismo radio que usa el pipeline
// (`pipelines/common/geo.py`). Dos numeros distintos para la misma distancia,
// uno en el mapa y otro en el reporte, seria el peor tipo de discrepancia.
const RADIO_TIERRA_KM = 6371.0088;

function distanciaKm(lon1, lat1, lon2, lat2) {
  const rad = Math.PI / 180;
  const dLat = (lat2 - lat1) * rad;
  const dLon = (lon2 - lon1) * rad;
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(lat1 * rad) * Math.cos(lat2 * rad) * Math.sin(dLon / 2) ** 2;
  return 2 * RADIO_TIERRA_KM * Math.asin(Math.min(1, Math.sqrt(a)));
}

function engancharCeldas(m) {
  if (estado.ganchosCeldas) return;
  estado.ganchosCeldas = true;
  let encima = null;

  m.on("click", "celdas", (ev) => {
    const p = ev.features[0].properties;
    const fila = (etiqueta, valor) =>
      `<div style="display:flex;justify-content:space-between;gap:1rem">` +
      `<span style="color:rgba(28,51,40,.72)">${etiqueta}</span><strong>${valor}</strong></div>`;
    abrirGlobo(new maplibregl.Popup({ closeButton: true, maxWidth: "18rem" }))
      .setLngLat(ev.lngLat)
      .setHTML(
        // El indice es la clave con la que esta celda se encuentra en el
        // `celdas.json` descargable, y en el parquet del activo. Sin el, lo
        // que se lee en pantalla no se puede citar ni comprobar.
        // `popup-celda` no es decorativa: es como se distingue este globo del
        // rotulo que sale al pasar por encima de un epicentro, que tambien es
        // un `.maplibregl-popup`. Una prueba los confundio durante dos
        // ejecuciones.
        `<p class="mono popup-celda" style="margin:0 0 .15rem">Celda H3 · r7 · 5,2 km²</p>` +
        `<p class="mono ficha-h3" style="margin:0 0 .45rem">${escapar(String(p.h3 ?? ""))}</p>` +
        fila("Intensidad", numero(Number(p.mmi), 1)) +
        // La distancia al epicentro es lo primero que se pregunta ante una
        // celda sacudida, y es lo que separa "esta cerca" de "esta lejos y aun
        // asi le llego". No estaba en ninguna parte del visor.
        (estado.epicentro
          ? fila(
              "Al epicentro",
              `${numero(distanciaKm(estado.epicentro[0], estado.epicentro[1], ev.lngLat.lng, ev.lngLat.lat))} km`
            )
          : "") +
        fila("Personas", comoConteo(Number(p.pop))) +
        fila("Edificaciones", comoConteo(Number(p.bld))) +
        fila("Construido", `${numero(Number(p.built_m2) / 1e6, 2)} km²`) +
        fila("Vías", `${numero(Number(p.vias_km), 1)} km`) +
        fila("Salud", numero(Number(p.salud))) +
        fila("Educación", numero(Number(p.edu)))
      )
      .addTo(m);
  });

  m.on("mousemove", "celdas", (ev) => {
    m.getCanvas().style.cursor = "pointer";
    if (!ev.features.length) return;
    if (encima !== null) m.setFeatureState({ source: "celdas", id: encima }, { encima: false });
    encima = ev.features[0].id;
    m.setFeatureState({ source: "celdas", id: encima }, { encima: true });
  });

  m.on("mouseleave", "celdas", () => {
    m.getCanvas().style.cursor = "";
    if (encima !== null) m.setFeatureState({ source: "celdas", id: encima }, { encima: false });
    encima = null;
  });
}

// La estrella es el símbolo del epicentro en sismología, y es el que ya usa el
// mapa estático del reporte. Se dibuja en un canvas y se registra como imagen
// del estilo porque el glifo ★ no está garantizado en los rangos de fuente que
// sirve OpenFreeMap: si faltara, la capa se quedaría muda.
// Genera una estrella como mapa de bits. Va con nombre y colores porque hay
// dos: la del epicentro con reporte y la del sismo visto y no despachado.
//
// No se tinta con `icon-color` porque la imagen no es SDF — MapLibre solo tinta
// las que lo son, y convertirla obligaria a perder el contorno de dos tonos que
// es lo que la hace legible sobre cualquier fondo.
function crearEstrella(m, nombre = "estrella", relleno = "#1c1b1a", borde = "#ffffff") {
  if (m.hasImage(nombre)) return;
  const lado = 48;
  const lienzo = document.createElement("canvas");
  lienzo.width = lienzo.height = lado;
  const ctx = lienzo.getContext("2d");
  const cx = lado / 2;
  const cy = lado / 2;
  const rExt = lado * 0.44;
  const rInt = rExt * 0.42;
  ctx.beginPath();
  for (let i = 0; i < 10; i += 1) {
    const r = i % 2 === 0 ? rExt : rInt;
    const a = -Math.PI / 2 + (i * Math.PI) / 5;
    const x = cx + r * Math.cos(a);
    const y = cy + r * Math.sin(a);
    if (i === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  }
  ctx.closePath();
  ctx.fillStyle = relleno;
  ctx.strokeStyle = borde;
  ctx.lineWidth = lado * 0.075;
  ctx.stroke();
  ctx.fill();
  m.addImage(nombre, ctx.getImageData(0, 0, lado, lado), { pixelRatio: 2 });
}

// El círculo del epicentro escala con la población expuesta, no con la
// magnitud: dos sismos de la misma magnitud sobre poblaciones distintas no son
// el mismo evento para quien responde.
//
// Escala con la banda que **ese** evento alcanzó, la misma que titula su ficha.
// Con `pop_mmi7p` fijo, los ocho eventos del catálogo que no llegan a MMI≥7
// salían como un punto mínimo mientras el panel decía "761.000 personas" al
// lado — Tehuantepec entre ellos.
//
// **Pero solo en la vista regional.** Un círculo centrado en el epicentro y
// dimensionado por una cifra que no es espacial invita a leerse como un radio
// de afectación, y no lo es. Mientras se comparan eventos entre sí, el símbolo
// proporcional es lo correcto; en cuanto se dibuja la malla del evento, la
// extensión real ya está en el mapa y el círculo sobra: se apaga y queda la
// estrella, que dice dónde fue y nada más.
//: De los rasgos que el raton toca, el de menos poblacion.
//:
//: Es el criterio correcto para simbolos proporcionales solapados: el circulo
//: pequeno esta contenido en el grande, asi que si el puntero toca los dos, el
//: unico que el usuario podia estar apuntando es el pequeno — al grande le
//: queda toda la corona de fuera para pulsarlo.
function elMasPequeno(rasgos) {
  return rasgos.reduce((a, b) =>
    (Number(b.properties.pop) || 0) < (Number(a.properties.pop) || 0) ? b : a
  );
}

//: El rotulo que aparece al pasar por encima de un epicentro.
//:
//: Antes no habia ninguno: con veintiun circulos amontonados sobre Centroamerica
//: y el Pacifico, saber cual se iba a abrir exigia pulsarlo y ver que salia.
let rotuloEpicentro = null;

function rotularEpicentro(m, rasgo) {
  // CON UN EVENTO ABIERTO, NO.
  //
  // El rotulo existe para desambiguar entre epicentros solapados —cual de los
  // veintiuno se va a abrir al pulsar— y con uno abierto no hay nada que
  // desambiguar: su nombre y su cifra estan en el panel, a la derecha. Lo unico
  // que hacia era tapar la malla del evento con un dato que ya se esta leyendo.
  //
  // Lo destapo una prueba que llevaba dos ejecuciones fallando: buscaba "hay un
  // globo abierto" para comprobar el de una celda, y encontraba este.
  if (estado.seleccionado) return;
  const p = rasgo.properties;
  if (rotuloEpicentro && rotuloEpicentro._centinelaId === p.usgs_id) return;
  cerrarRotuloDeEpicentro();
  const banda = Number(p.banda) || 0;
  const cifra = banda
    ? `${comoConteo(Number(p.pop) || 0)} en MMI≥${banda}`
    : "sin población en MMI≥6";
  rotuloEpicentro = new maplibregl.Popup({
    closeButton: false,
    closeOnClick: false,
    offset: 14,
    // `rotulo-` y no `globo-`: `.globo` ya es el punto de la marca GeoAI LATAM
    // en el pie, y compartir clase le habria dado 1,25 rem de lado a esto.
    className: "rotulo-epicentro",
  })
    .setLngLat(rasgo.geometry.coordinates)
    .setHTML(
      `<p class="rotulo-epicentro-titulo">${escapar(p.etiqueta)} — ${escapar(p.lugar)}</p>` +
      `<p class="rotulo-epicentro-cifra mono">${escapar(cifra)}</p>`
    )
    .addTo(m);
  rotuloEpicentro._centinelaId = p.usgs_id;
}

function cerrarRotuloDeEpicentro() {
  if (!rotuloEpicentro) return;
  try {
    rotuloEpicentro.remove();
  } catch (error) {
    /* ya se fue con su mapa */
  }
  rotuloEpicentro = null;
}

function dibujarEpicentros(eventos) {
  const m = estado.mapa;
  const conCoords = eventos.filter((e) => e.lon || e.lat);
  if (!m || !conCoords.length) return;

  const pintar = () => {
    if (m.getSource("epicentros")) return;
    m.addSource("epicentros", {
      type: "geojson",
      data: {
        type: "FeatureCollection",
        features: conCoords.map((e) => ({
          type: "Feature",
          geometry: { type: "Point", coordinates: [e.lon, e.lat] },
          properties: {
            usgs_id: e.usgs_id,
            pop: bandaTitular(e).pop,
            // Pais y fecha viajan con el rasgo para que los filtros puedan
            // tocar el MAPA y no solo la lista. Elegir "Colombia" y seguir
            // viendo veintiun epicentros repartidos por el continente era el
            // filtro diciendo una cosa y el mapa otra.
            iso3: e.iso3 || "",
            utc: e.utc || "",
            etiqueta: `M${String(e.mag).replace(".", ",")}`,
            // Para el rotulo al pasar por encima: sin esto habria que volver a
            // buscar el evento por id cada vez que el raton cruza un circulo.
            lugar: e.lugar || "",
            banda: bandaTitular(e).banda,
          },
        })),
      },
    });
    m.addLayer({
      id: "epicentros-halo",
      type: "circle",
      source: "epicentros",
      layout: {
        // EL CIRCULO GRANDE VA DEBAJO.
        //
        // Sin esto MapLibre pinta en el orden de la fuente, y el ultimo que
        // llega tapa a los anteriores. En Centroamerica y en el Pacifico los
        // circulos se solapan sin remedio —son simbolos proporcionales sobre
        // una region estrecha— y el resultado era que pulsar la estrella de un
        // sismo abria otro: probado sobre el M7,4 de San Jose del Palmar y se
        // abrio el M7,8 de Muisne, cuyo circulo pasaba por encima.
        //
        // Ordenados por poblacion descendente, el grande queda al fondo y el
        // pequeno siempre tiene una corona propia donde se le puede pulsar.
        "circle-sort-key": ["-", 0, ["get", "pop"]],
      },
      paint: {
        "circle-radius": [
          "interpolate", ["linear"], ["sqrt", ["max", ["get", "pop"], 1]], 1, 6, 2000, 22,
        ],
        // Estaba al 16 % de opacidad: color efectivo #ddcabd sobre un suelo
        // #ece9de, o sea **1,30 : 1**. El circulo que dice cuanta poblacion
        // quedo expuesta —la cifra de portada del panorama— no se veia.
        //
        // Sube el relleno y el contorno pasa a ser del color del epicentro en
        // vez de blanco: un halo blanco sobre fondo casi blanco no separa nada.
        "circle-color": EPICENTRO,
        "circle-opacity": 0.28,
        "circle-stroke-color": EPICENTRO,
        "circle-stroke-width": 1.2,
        "circle-stroke-opacity": 0.55,
      },
    });
    crearEstrella(m);
    m.addLayer({
      id: "epicentros",
      type: "symbol",
      source: "epicentros",
      layout: {
        "icon-image": "estrella",
        // Crece con el zoom: a escala continental la estrella es una marca de
        // posición, y sobre la malla del evento tiene que ganarle al color.
        "icon-size": ["interpolate", ["linear"], ["zoom"], 3, 0.5, 7, 0.8, 11, 1.1],
        "icon-allow-overlap": true,
        "text-field": ["get", "etiqueta"],
        "text-font": ["Noto Sans Bold"],
        "text-size": ["interpolate", ["linear"], ["zoom"], 3, 11, 8, 14],
        "text-offset": [0, 1.1],
        "text-anchor": "top",
        "text-allow-overlap": false,
      },
      paint: {
        "text-color": "#1c1b1a",
        "text-halo-color": "#ffffff",
        "text-halo-width": 1.6,
      },
    });

    anotarPintado("epicentros", conCoords.length);
    aplicarAmenaza();

    for (const capa of ["epicentros", "epicentros-halo"]) {
      // `elMasPequeno` y no `features[0]`: el orden de pintado ya deja al
      // grande debajo, pero un clic dentro del circulo pequeno devuelve **los
      // dos** rasgos, y el que el usuario quiso es el de menos poblacion — el
      // que tiene el borde mas cerca del punto que pulso.
      m.on("click", capa, (ev) => seleccionar(elMasPequeno(ev.features).properties.usgs_id));
      m.on("mousemove", capa, (ev) => {
        m.getCanvas().style.cursor = "pointer";
        rotularEpicentro(m, elMasPequeno(ev.features));
      });
      m.on("mouseleave", capa, () => {
        m.getCanvas().style.cursor = "";
        cerrarRotuloDeEpicentro();
      });
    }
  };

  // Por el mismo ayudante que la malla. Tenía su propio `m.on("load", pintar)`,
  // que es la misma carrera: si el mapa ya cargó y `isStyleLoaded()` sigue en
  // false —mientras una fuente está en vuelo— el aviso no vuelve y los
  // epicentros no se dibujan nunca. Visto en el sitio publicado con la caché
  // fría: mapa base entero y ni una estrella encima.
  //
  // Se arregló `cuandoElEstiloEsteListo` y no se miró quién más resolvía lo
  // mismo por su cuenta, que es el patrón que esta auditoría persigue.
  cuandoElEstiloEsteListo(m, pintar);
}

//: El mapa es la mitad del visor, no el visor.
//:
//: Cuando MapLibre no llega —unpkg caido, una red que lo bloquea, un navegador
//: sin WebGL— lo que queda debajo sigue siendo correcto: los veintiun reportes,
//: la cobertura, el panel de un evento entero con sus ocho descargas. Lo unico
//: que fallaba era el aviso, que se quedaba girando para siempre y hacia
//: parecer rota una pagina que funciona.
//:
//: Se dice lo que pasa y se dice que lo demas sigue en pie. Un «cargando»
//: eterno no informa de nada; este aviso responde la pregunta que se hace quien
//: mira un rectangulo vacio.
function avisarSinMapa() {
  const aviso = $("cargando");
  if (!aviso) return;
  aviso.classList.add("panel-mapa-aviso");
  aviso.innerHTML =
    `<span class="mono">El mapa no está disponible</span>` +
    `<span class="panel-mapa-nota">No se pudo cargar la librería de mapas. ` +
    `Las cifras y las descargas de cada reporte siguen completas.</span>`;
  aviso.hidden = false;
  anunciar("El mapa no está disponible. Las cifras y las descargas siguen completas.");
}

//: Todas las capas que dibujan **dato** del sistema, en el orden en que pueden
//: aparecer. Existe para que la mascara sepa por debajo de quien tiene que
//: colocarse: velar el mapa base es el objetivo, velar los hexagonos seria el
//: fallo.
const CAPAS_DE_DATO = [
  "contornos",
  "perimetro-borde",
  "perimetro",
  "celdas",
  "celdas-borde",
  "epicentros-halo",
  "epicentros",
  "observados",
  "incendios-punto",
  "incendios",
  "incendios-borde",
  "foco-perimetro-borde",
  "foco-perimetro",
];

//: El mapa base habla en el idioma de cada sitio.
//:
//: Positron rotula con `name`, que es el toponimo local: "Gulf of Mexico",
//: "Brazil", "Democratic Republic of the Congo", y Libia en arabe. En un
//: producto escrito integramente en espanol para America Latina eso es una
//: costura visible, y OpenMapTiles publica `name:es` y `name:latin` en la misma
//: tesela — no cuesta una peticion mas.
//:
//: Solo se tocan las capas cuyo `text-field` ya menciona `name`: los escudos de
//: carretera rotulan con `ref` y cambiarlos los dejaria en blanco.
function rotularEnEspanol(m) {
  const enEspanol = ["coalesce", ["get", "name:es"], ["get", "name:latin"], ["get", "name"]];
  for (const capa of m.getStyle().layers) {
    if (capa.type !== "symbol") continue;
    try {
      const actual = m.getLayoutProperty(capa.id, "text-field");
      if (actual === undefined || actual === null) continue;
      if (!JSON.stringify(actual).includes("name")) continue;
      m.setLayoutProperty(capa.id, "text-field", enEspanol);
    } catch (error) {
      /* el estilo puede cambiar de una version a otra; no es crítico */
    }
  }
}

//: El ultimo estilo base que se dejo listo. Ver `prepararEstilo`.
let estiloPreparado = null;

//: Deja un estilo base recien cargado en condiciones de servir de fondo.
//:
//: Tres cosas, y las tres tienen que rehacerse con CADA estilo, no solo con el
//: primero: el retinte de la identidad, los toponimos en espanol y el velo
//: sobre lo que no es America Latina.
//:
//: Corre desde `styledata`, que llega muchas veces por estilo, asi que lleva su
//: propia memoria: sin ella recorreria las ~200 capas del estilo en cada aviso.
function prepararEstilo(m) {
  if (!m.isStyleLoaded()) return;
  const estilo = ESTILOS_BASE[estado.estiloBase] || ESTILOS_BASE.claro;
  if (estiloPreparado === estilo.url) return;
  estiloPreparado = estilo.url;

  // El retinte es solo del claro: los colores de la identidad estan elegidos
  // contra el gris neutro de Positron, y sobre un estilo oscuro dejarian el
  // mapa a medio pintar. Ver `ESTILOS_BASE`.
  if (estilo.retinta) {
    for (const capa of m.getStyle().layers) {
      if (capa.type !== "fill" && capa.type !== "background") continue;
      const agua = capa.id === "water" || capa.id.startsWith("water_");
      const tierra = capa.id === "background" || capa.id === "landcover" ||
                     capa.id.startsWith("landuse") || capa.id.startsWith("landcover");
      if (!agua && !tierra) continue;
      const prop = capa.type === "background" ? "background-color" : "fill-color";
      try {
        m.setPaintProperty(capa.id, prop, agua ? BASE_AGUA : BASE_TIERRA);
      } catch (e) {
        /* el estilo puede cambiar; no es crítico */
      }
    }
  }
  rotularEnEspanol(m);
  ponerMascara(m, estilo.velo);
}

//: Los dos botones que faltaban en el mapa, en un solo grupo.
//:
//: UN SOLO GRUPO Y NO DOS. Cada `maplibregl-ctrl-group` trae 10 px de margen
//: propio, y la esquina de arriba a la derecha es la unica libre —abajo estan
//: las leyendas, la atribucion y las pestanas de capa—. En un movil de 390 px
//: esa pila ya llegaba hasta la leyenda de intensidad, y dos grupos mas
//: empujaban la barra de escala encima de ella. En uno solo caben los dos
//: botones por el precio de uno.
class ControlesDelMapa {
  onAdd(m) {
    this._mapa = m;
    const caja = document.createElement("div");
    caja.className = "maplibregl-ctrl maplibregl-ctrl-group ctrl-centinela";

    caja.appendChild(
      this._boton(
        "ctrl-inicio",
        "Volver a la vista de América Latina",
        // Una casa, que es lo que todo el mundo espera de este boton.
        `<path d="M3 10.5 12 3l9 7.5"/><path d="M5.5 9.5V20h13V9.5"/>` +
          `<path d="M9.5 20v-6h5v6"/>`,
        () => {
          volverAlEncuadre(m, VUELO);
          anotarCamara("boton:inicio");
          anunciar("Vista devuelta al encuadre de América Latina.");
        }
      )
    );

    const boton = this._boton(
      "ctrl-bases",
      "Cambiar el mapa base",
      // Tres hojas apiladas.
      `<path d="M12 3 3 7.5l9 4.5 9-4.5z"/><path d="M3 12l9 4.5 9-4.5"/>` +
        `<path d="M3 16.5 12 21l9-4.5"/>`,
      () => this._alternar()
    );
    boton.setAttribute("aria-expanded", "false");
    boton.setAttribute("aria-controls", "galeria-bases");
    caja.appendChild(boton);

    const galeria = document.createElement("div");
    galeria.className = "galeria-bases";
    galeria.id = "galeria-bases";
    galeria.hidden = true;
    galeria.setAttribute("role", "group");
    galeria.setAttribute("aria-label", "Mapa base");
    caja.appendChild(galeria);

    this._caja = caja;
    this._galeria = galeria;
    this._boton_bases = boton;
    pintarGaleriaDeBases(galeria);
    return caja;
  }

  _boton(clase, titulo, trazo, alPulsar) {
    const b = document.createElement("button");
    b.type = "button";
    b.className = clase;
    b.title = titulo;
    b.setAttribute("aria-label", titulo);
    b.innerHTML =
      `<svg viewBox="0 0 24 24" width="19" height="19" aria-hidden="true" fill="none" ` +
      `stroke="currentColor" stroke-width="1.7" stroke-linecap="round" ` +
      `stroke-linejoin="round">${trazo}</svg>`;
    b.addEventListener("click", alPulsar);
    return b;
  }

  _alternar() {
    const abrir = this._galeria.hidden;
    this._galeria.hidden = !abrir;
    this._boton_bases.setAttribute("aria-expanded", String(abrir));
    if (abrir) {
      const primera = this._galeria.querySelector("button");
      if (primera) primera.focus();
    }
  }

  onRemove() {
    if (this._caja && this._caja.parentNode) this._caja.parentNode.removeChild(this._caja);
    this._mapa = null;
  }
}

//: Las opciones del mapa base, con la puesta marcada.
//:
//: Cada una lleva su apunte: "Con relieve" cuesta legibilidad del dato y quien
//: la elige tiene derecho a saberlo antes, no despues.
//: `nodo` porque en `onAdd` la caja todavia no esta en el documento —MapLibre
//: la inserta al volver— y `getElementById` no la encuentra: la galeria salia
//: vacia y el conmutador no tenia nada que pulsar.
function pintarGaleriaDeBases(nodo) {
  const galeria = nodo || $("galeria-bases");
  if (!galeria) return;
  galeria.innerHTML = Object.entries(ESTILOS_BASE)
    .map(
      ([clave, e]) =>
        `<button type="button" data-base="${clave}" class="base-opcion"` +
        `${clave === estado.estiloBase ? ' aria-pressed="true"' : ' aria-pressed="false"'}>` +
        `<span class="base-nombre">${e.nombre}</span>` +
        `<span class="base-apunte">${e.apunte}</span></button>`
    )
    .join("");
  for (const b of galeria.querySelectorAll("[data-base]")) {
    b.addEventListener("click", () => {
      cambiarEstiloBase(b.dataset.base);
      // Y se cierra. Un panel de 15 rem que se queda abierto sobre el mapa
      // despues de elegir tapa justo lo que se acaba de ir a mirar.
      cerrarGaleriaDeBases();
    });
  }
}

//: Cierra el panel de mapas base, venga de donde venga la orden.
function cerrarGaleriaDeBases() {
  const galeria = $("galeria-bases");
  if (!galeria || galeria.hidden) return;
  galeria.hidden = true;
  const boton = document.querySelector(".ctrl-bases");
  if (boton) boton.setAttribute("aria-expanded", "false");
}

//: Cambia el mapa base y vuelve a poner encima todo lo que es dato.
//:
//: `setStyle` no es "cambiar el fondo": tira el estilo entero y con el **todas
//: las fuentes y todas las capas**, incluidas las nuestras. Un conmutador que
//: solo llame a `setStyle` deja un mapa base bonito y vacio: sin epicentros,
//: sin malla, sin fuego. Por eso este es el unico sitio desde donde se cambia.
//:
//: El evento abierto se vuelve a seleccionar en vez de reconstruirse a mano:
//: `seleccionar` ya sabe traer su malla, sus contornos y su perimetro, y
//: duplicar aqui ese camino es como acaban divergiendo.
function cambiarEstiloBase(clave) {
  const m = estado.mapa;
  const estilo = ESTILOS_BASE[clave];
  if (!m || !estilo || clave === estado.estiloBase) return;
  estado.estiloBase = clave;

  const abierto = estado.seleccionado;
  const capaAbierta = estado.capa;

  // `styledata` y despues `cuandoElEstiloEsteListo`: `setStyle` no emite
  // `style.load` —solo `data`, `styledata` e `idle`— y el estilo no esta listo
  // en el primer `styledata`. El ayudante ya sabe esperar a `isStyleLoaded()`,
  // con su red de seguridad, que es el mismo problema que resuelve al arrancar.
  m.once("styledata", () => cuandoElEstiloEsteListo(m, () => {
    // El velo y los rotulos primero: `prepararEstilo` es idempotente y aqui se
    // asegura de que estan puestos ANTES de que vuelva el dato, para que la
    // mascara quede debajo y no encima.
    prepararEstilo(m);
    if (estado.eventos) dibujarEpicentros(estado.eventos);
    if (estado.observadosDatos) dibujarObservados(estado.observadosDatos);
    if (estado.fuegoDatos) dibujarIncendios(estado.fuegoDatos);
    // El interruptor de sismos menores sobrevive en el DOM, pero su capa acaba
    // de nacer apagada: se le devuelve lo que la casilla dice.
    const casilla = $("interruptor-observados");
    const marcada = casilla && casilla.querySelector("input") && casilla.querySelector("input").checked;
    try {
      if (m.getLayer("observados")) {
        m.setLayoutProperty("observados", "visibility", marcada ? "visible" : "none");
      }
    } catch (error) {
      /* la capa puede no haber llegado; `aplicarAmenaza` la recoge */
    }
    aplicarAmenaza();
    aplicarFiltrosAlMapa();
    if (abierto) {
      estado.capa = capaAbierta;
      seleccionar(abierto);
    }
    anunciar(`Mapa base: ${estilo.nombre}.`);
  }));

  m.setStyle(estilo.url);
  pintarGaleriaDeBases();
}

//: El velo sobre lo que no es America Latina. Ver `CAJA_MASCARA`.
//:
//: Un poligono del mundo con un agujero: se dibuja fuera de la caja y nunca
//: dentro. Va **encima de todo el estilo base** —simbolos incluidos, que es de
//: donde venian los rotulos de Nigeria y Argelia— y **debajo** de la primera
//: capa de dato que exista, porque las capas de dato llegan cada una a su ritmo
//: y alguna puede haberse adelantado a `style.load`.
function ponerMascara(m, velo = BASE_PAPEL) {
  if (m.getLayer("mascara")) return;
  const [[oeste, sur], [este, norte]] = CAJA_MASCARA;
  try {
    m.addSource("mascara", {
      type: "geojson",
      data: {
        type: "Feature",
        properties: {},
        geometry: {
          type: "Polygon",
          coordinates: [
            // Anillo exterior: el mundo.
            [[-180, -85], [180, -85], [180, 85], [-180, 85], [-180, -85]],
            // Agujero: la region. Sentido contrario al exterior, como pide GeoJSON.
            [[oeste, sur], [oeste, norte], [este, norte], [este, sur], [oeste, sur]],
          ],
        },
      },
    });
    const primeraDeDato = CAPAS_DE_DATO.find((id) => m.getLayer(id));
    m.addLayer(
      {
        id: "mascara",
        type: "fill",
        source: "mascara",
        // El tono lo pone el estilo: velar un mapa base oscuro con el color del
        // papel dibujaria un rectangulo claro alrededor de la region.
        paint: { "fill-color": velo, "fill-opacity": 0.82 },
      },
      primeraDeDato
    );
  } catch (error) {
    // Sin mascara el mapa sigue siendo correcto, solo mas ruidoso. No es motivo
    // para tumbar el arranque.
    console.warn("máscara:", error && error.message);
  }
}

function iniciarMapa() {
  // La red de seguridad de abajo —`setTimeout(listo, 8000)`— vivia **despues**
  // de este `return`, asi que justamente en el caso que tenia que cubrir no
  // llegaba a registrarse: sin `maplibregl` no hay `load` que quitar el aviso y
  // no habia temporizador que lo hiciera. Medido el 28-ago-2026 con los
  // `<script>` de unpkg apuntando a 404: treinta y un segundos girando, con el
  // resto del tablero entero debajo.
  //
  // El comentario de la red de seguridad ya decia por que existe —«un cargando
  // eterno es peor que un mapa gris»— y no cubria su propio caso.
  if (!$("mapa") || typeof maplibregl === "undefined") {
    avisarSinMapa();
    return null;
  }

  // La otra manera de llegar al mismo rectangulo vacio: la libreria esta y el
  // constructor falla igual —sin WebGL, con la aceleracion por hardware
  // apagada, en un navegador viejo—. MapLibre lanza, y sin este `catch` la
  // excepcion sube hasta el modulo y se lleva por delante todo lo que viene
  // detras: la lista de eventos, la cobertura y el panel no se pintarian.
  let mapa;
  try {
    mapa = new maplibregl.Map({
      container: "mapa",
      style: ESTILO_BASE,
      ...VISTA_INICIAL,
      attributionControl: false,
      // LA RUEDA NO ES DEL MAPA, ES DE LA PAGINA.
      //
      // El mapa vive a media pantalla de un documento que sigue hacia abajo
      // —los veintiun reportes, la cobertura, el pie—, y bajar a leerlos
      // pasaba la rueda por encima del mapa. Medido: un solo gesto de tres
      // clics movia el zoom de 2,05 a 1,65 **y** la pagina 300 px. Se llegaba
      // a ver China y Etiopia en un tablero de America Latina, y sin forma de
      // volver: los unicos controles eran + y −.
      //
      // Con `cooperativeGestures` la rueda desplaza y Ctrl+rueda acerca. El
      // encuadre deja de destruirse por leer.
      cooperativeGestures: true,
      // MapLibre rotula esa ayuda en ingles.
      locale: {
        "CooperativeGesturesHandler.WindowsHelpText": "Usa Ctrl + rueda para acercar el mapa",
        "CooperativeGesturesHandler.MacHelpText": "Usa ⌘ + rueda para acercar el mapa",
        "CooperativeGesturesHandler.MobileHelpText": "Usa dos dedos para mover el mapa",
      },
    });
  } catch (error) {
    console.warn("mapa:", error && error.message);
    avisarSinMapa();
    return null;
  }

  // NO se encuadra con `fitBounds` aqui, y costo un mapa en blanco averiguarlo.
  //
  // `cuandoElEstiloEsteListo` se dispara con `styledata`, que puede llegar
  // antes de que el contenedor tenga su tamano final. `fitBounds` calcula
  // entonces la camara contra una caja que aun no mide lo que va a medir, y el
  // mapa acaba mirando a ninguna parte: estilo cargado, capas creadas,
  // atribucion pintada, y ni un pixel.
  //
  // `VISTA_INICIAL` es un centro y un zoom, que no dependen del tamano de la
  // ventana para ser validos. Menos elegante y siempre correcto.

  // Sin `customAttribution`: el estilo de OpenFreeMap ya declara la suya y
  // añadirla la imprimía dos veces seguidas.
  mapa.addControl(new maplibregl.AttributionControl({ compact: true }));
  mapa.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");
  // ARRIBA A LA DERECHA, bajo los controles de zoom. Es la unica esquina libre,
  // y lo se porque probe las otras tres:
  //
  //   abajo-izquierda  las leyendas de simbolos y fuego, y los interruptores
  //   abajo-derecha    la leyenda de intensidad y la atribucion
  //   arriba-izquierda las pestañas de capa
  //
  // Estuvo abajo a la izquierda desde siempre y la tape esta tarde al apilar
  // ahi las leyendas; la movi a la derecha y la tapo la leyenda de intensidad
  // en cuanto se selecciona un evento. Una barra de escala tapada es peor que
  // no tenerla: el hueco se da por cubierto.
  //
  // Y hace falta: este sistema publica distancias —"41 km al SO de Quellon", "a
  // 27 km del epicentro" en cada celda— y sin escala no hay como juzgarlas.
  // Entre la navegacion y la escala: los dos de arriba mueven la camara, y la
  // escala es la ultima porque es la que hay que poder leer sin que nada se le
  // apile debajo.
  mapa.addControl(new ControlesDelMapa(), "top-right");
  mapa.addControl(new maplibregl.ScaleControl({ maxWidth: 110, unit: "metric" }), "top-right");

  // Positron viene en gris neutro. Sobre un fondo de arena cálida canta, y su
  // agua es casi del mismo tono que su tierra — inservible para un sistema
  // cuya mitad de la exposición es costera. Se retintan tierra y agua a la
  // paleta de la identidad, sin tocar el resto del estilo.
  // `styledata` y NO `style.load`.
  //
  // `style.load` se dispara **solo con el estilo inicial**: `setStyle` no lo
  // emite. Medido con MapLibre 4.7.1, los eventos que llegan al cambiar de mapa
  // base son `data`, `styledata` e `idle`, y ninguno mas. Con `style.load` el
  // primer cambio de base dejaba un mapa sin retintar, con los toponimos otra
  // vez en ingles, sin velo y —lo peor— sin una sola capa de dato encima.
  //
  // `prepararEstilo` es idempotente y lleva su propia memoria, asi que puede
  // correr en cada aviso sin repetir trabajo.
  //
  // Y los DOS eventos, no solo `styledata`: el ultimo `styledata` puede llegar
  // con `isStyleLoaded()` todavia en false, y entonces no hay ninguno mas. Con
  // solo `styledata` el estilo inicial se quedaba sin retintar, sin velo y con
  // los toponimos en ingles. Es la misma pareja que ya escucha
  // `cuandoElEstiloEsteListo`, y por el mismo motivo.
  for (const evento of ["styledata", "idle"]) {
    mapa.on(evento, () => prepararEstilo(mapa));
  }

  // El aviso se quita cuando el mapa dibuja algo, no cuando termina de cargarlo
  // todo: `idle` no llega mientras siguen entrando teselas, y dejarlo puesto
  // haría parecer roto un mapa que ya se ve. Con red de seguridad, porque un
  // "cargando" eterno es peor que un mapa gris.
  const listo = () => {
    const aviso = $("cargando");
    if (aviso) aviso.hidden = true;
  };
  mapa.once("load", listo);

  // EL ENCUADRE, AHORA SI ADAPTADO A LA VENTANA.
  //
  // `VISTA_INICIAL` es un centro y un zoom medidos sobre un mapa de 954 px, y
  // ahi funciona. Por encima de eso el sobrante no cae en el Pacifico como dice
  // el comentario de arriba: cae en Africa y en Europa. Medido en un portatil
  // de 1707 px: el mapa abarca 227 grados de longitud, de -197 a +29, y la caja
  // de LATAM ocupa el 38 % del ancho — se veian Bulgaria, Italia y la Republica
  // Democratica del Congo rotuladas en un tablero de America Latina.
  //
  // `fitBounds` era lo que este fichero queria desde el principio: "se adapta a
  // la ventana; un zoom fijo solo es correcto para el tamano de pantalla en que
  // se eligio". Se descarto porque se llamaba desde `styledata`, que puede
  // llegar antes de que el contenedor tenga su tamano final, y entonces encuadra
  // contra una caja que aun no mide lo que va a medir: mapa en blanco.
  //
  // `load` no tiene esa carrera — para cuando llega, el contenedor esta medido y
  // el primer fotograma esta pintado. Y `VISTA_INICIAL` sigue siendo el valor de
  // arranque, asi que si `load` no llegara nunca el mapa se queda en un encuadre
  // valido en vez de en ninguno.
  //
  // La caja es la ventana util del sistema, no `LATAM_BBOX` entera: recorta el
  // norte de Mexico y la Patagonia austral, que es lo que el comentario de
  // `VISTA_INICIAL` ya habia decidido recortar y sigue siendo la decision buena.
  // Como es mas alta que ancha, en una pantalla apaisada manda el alto y el
  // sobrante horizontal se reparte a los dos lados en vez de amontonarse al
  // este.
  mapa.once("load", () => aplicarAmenaza());

  mapa.once("load", () => {
    // Y SOLO SI NADIE HA PEDIDO OTRA COSA.
    //
    // `cuandoElEstiloEsteListo` se dispara con `isStyleLoaded()`, que es **antes**
    // que `load` —`load` espera ademas al primer pintado de las fuentes—. Con un
    // enlace profundo la secuencia real era: volar al evento, y despues este
    // encuadre devolviendolo al panorama. Se veia la malla del sismo del tamano
    // de un sello en mitad de America Latina.
    //
    // En local no pasaba: el servidor esta a un milisegundo y `load` llegaba
    // antes. Aparecio en la pagina publicada, que es donde no se quiere
    // encontrar algo asi.
    if (estado.seleccionado) return;
    try {
      volverAlEncuadre(mapa);
    } catch (error) {
      /* con una caja invalida se queda en VISTA_INICIAL, que es correcta */
    }
  });
  setTimeout(listo, 8000);

  mapa.on("error", (e) => console.warn("mapa:", e && e.error && e.error.message));
  return mapa;
}


// --- Cobertura regional -----------------------------------------------------
//
// El tablero listaba eventos y nada mas, y con pocos reportes eso se lee como
// una demo. Lo que hay detras no lo es: dieciocho paises con su activo de
// exposicion construido y medido contra la cifra oficial de su instituto o de
// la ONU. Ese hecho responde la pregunta que se hace quien llega —¿esto sirve
// para mi pais?— y no aparecia en ninguna pantalla.

function listar(nombres) {
  if (nombres.length <= 1) return nombres.join("");
  return `${nombres.slice(0, -1).join(", ")} y ${nombres[nombres.length - 1]}`;
}

function porcentaje(v) {
  if (!Number.isFinite(v)) return "—";
  const signo = v > 0 ? "+" : "";
  return `${signo}${nf.format(Number(v.toFixed(2)))} %`;
}

function pintarResumenCobertura(datos, eventos) {
  const { resumen } = datos;
  const conReporte = new Set(eventos.map((e) => e.iso3).filter(Boolean)).size;

  $("cobertura-resumen").innerHTML =
    `<div class="metrica"><span class="cabeza">${iconoSvg("paises")}` +
    `<span class="valor">${resumen.paises_construidos}</span></span>` +
    `<span class="etiqueta">países con activo publicado</span>` +
    `<span class="apunte">de ${resumen.paises_con_manifest} con fuentes fijadas</span></div>` +
    `<div class="metrica"><span class="cabeza">${iconoSvg("malla")}` +
    `<span class="valor">${comoConteo(resumen.poblacion_en_la_malla)}</span></span>` +
    `<span class="etiqueta">personas en la malla hexagonal</span>` +
    `<span class="apunte">precalculadas, antes de que ocurra nada</span></div>` +
    `<div class="metrica"><span class="cabeza">${iconoSvg("desvio")}` +
    `<span class="valor">${porcentaje(resumen.peor_desvio_pct)}</span></span>` +
    // SIN APUNTE. Decia «el de Venezuela, y está explicado» y la explicacion no
    // estaba en ninguna parte del visor: ni un enlace, ni una nota, ni una
    // columna. Prometer una explicacion que no existe es peor que no ofrecerla.
    // La tolerancia por pais vive en `cobertura.json` y en los manifiestos; su
    // sitio es un documento metodologico, no esta tarjeta.
    `<span class="etiqueta">peor desvío vs. cifra oficial</span></div>` +
    `<div class="metrica"><span class="cabeza">${iconoSvg("reportes")}` +
    `<span class="valor">${conReporte}</span></span>` +
    `<span class="etiqueta">países con reporte publicado</span></div>`;
}

function filaCobertura(pais, cuantos) {
  const tr = document.createElement("tr");
  if (!pais.construido) tr.className = "pendiente";

  const nombre = document.createElement("th");
  nombre.scope = "row";
  nombre.textContent = pais.nombre;
  if (!pais.construido) {
    const marca = document.createElement("span");
    marca.className = "mono marca-pendiente";
    marca.textContent = "sin construir";
    nombre.append(" ", marca);
  }

  const pob = document.createElement("td");
  pob.className = "num";
  pob.textContent = pais.construido ? comoConteo(pais.poblacion_medida) : "—";

  const desvio = document.createElement("td");
  desvio.className = "num";
  desvio.textContent = pais.construido ? porcentaje(pais.desvio_pct) : "—";
  if (pais.construido && pais.fuente_referencia) {
    // La cifra sola no dice nada sin saber contra que se compara.
    desvio.title = `Referencia: ${pais.fuente_referencia}`;
  }

  const reportes = document.createElement("td");
  reportes.className = "num";
  reportes.textContent = cuantos ? nf.format(cuantos) : "—";

  tr.append(nombre, pob, desvio, reportes);
  return tr;
}

async function cargarCobertura(eventos) {
  const resumen = $("cobertura-resumen");
  if (!resumen) return;
  try {
    const datos = await json(COBERTURA);
    const porPais = new Map();
    for (const e of eventos) {
      if (e.iso3) porPais.set(e.iso3, (porPais.get(e.iso3) || 0) + 1);
    }

    pintarResumenCobertura(datos, eventos);

    const tabla = $("tabla-cobertura");
    const cuerpo = tabla.querySelector("tbody");
    for (const pais of datos.paises) {
      cuerpo.appendChild(filaCobertura(pais, porPais.get(pais.iso3) || 0));
    }
    tabla.hidden = false;

    // Un país con activo y sin reportes se lee como un hueco del sistema, y casi
    // siempre es lo contrario: el activo está hecho y **no ha ocurrido nada**.
    // Paraguay y Uruguay no registran un solo sismo M≥5,5 desde el año 2000.
    // Decirlo distingue "no cubierto" de "cubierto y en silencio", que para un
    // sistema de preparación no son lo mismo en absoluto.
    const faltan = datos.paises.filter((p) => !p.construido).map((p) => p.nombre);
    const esperando = datos.paises
      .filter((p) => p.construido && !porPais.get(p.iso3))
      .map((p) => p.nombre);

    const frases = [];
    if (esperando.length) {
      frases.push(
        `${listar(esperando)} ${esperando.length === 1 ? "tiene" : "tienen"} su activo ` +
        `construido y todavía sin reporte: ninguno ha registrado un sismo que lo ` +
        `amerite. El activo está hecho por adelantado, que es de lo que se trata.`
      );
    }
    if (faltan.length) {
      frases.push(`Falta construir el activo de ${listar(faltan)}.`);
    }
    // La frase terminaba en «una tolerancia que nadie ve no vigila nada», y la
    // tolerancia era justo lo unico que esta tabla NO enseña. La maxima seguia
    // siendo cierta y el parrafo que la decia era su contraejemplo.
    frases.push(
      "El desvío compara la población que mide el activo contra la cifra " +
      "oficial de referencia del país, y se publica aunque incomode."
    );
    $("cobertura-nota").textContent = frases.join(" ");

    return new Map(datos.paises.map((p) => [p.iso3, p.nombre]));
  } catch (error) {
    resumen.innerHTML = `<p class="pista">No se pudo leer la cobertura regional.</p>`;
    console.warn("cobertura.json:", error);
    return new Map();
  }
}

// --- Filtro por país --------------------------------------------------------

//: Como se ordena la lista.
//:
//: Iba siempre por fecha, que responde "¿que ha pasado ultimamente?" y nada mas.
//: Las otras dos preguntas que se hace quien llega —"¿cual fue el mas fuerte?" y
//: "¿cual afecto a mas gente?"— no tenian respuesta sin leer las veintiuna
//: tarjetas. Y no son la misma: el M8 de Peru deja 248.000 personas en MMI≥7 y
//: el M7,4 del Choco deja 2,4 millones.
//: Desde cuando. El catalogo cubre catorce anos —de 2012 a hoy— y la lista los
//: daba todos de golpe, asi que la pregunta mas comun ("¿que ha pasado
//: ultimamente?") obligaba a leerla entera o a fiarse del orden.
//:
//: Los cortes no son redondos por gusto: 90 dias es la ventana en la que USGS
//: sigue revisando un ShakeMap —la misma que usa el repaso de versiones— y doce
//: meses es el marco en que se piensa "este ano".
//: El catalogo va de enero de 2012 a agosto de 2026, y la ventana solo ofrecia
//: "Todo", "12 meses" y "90 días": las dos ultimas devolvian los mismos tres
//: reportes y dieciocho de veintiuno solo eran alcanzables con "Todo". Con cinco
//: y diez anos la ventana empieza a separar el catalogo en vez de partirlo en
//: "lo de este verano" y "el resto".
const VENTANAS = {
  todo: { texto: "Todo", dias: null },
  decada: { texto: "10 años", dias: 3653 },
  lustro: { texto: "5 años", dias: 1826 },
  ano: { texto: "12 meses", dias: 365 },
  trimestre: { texto: "90 días", dias: 90 },
};

//: ¿Cae esto dentro de la ventana elegida?
//:
//: Acepta una fila de la lista o el objeto del evento: los dos llevan `utc`, y
//: el `dataset` de la fila salio de ese mismo objeto. Existe asi porque el
//: panorama del panel lateral tiene que filtrarse con **exactamente** el mismo
//: criterio que la rejilla de tarjetas, y dos implementaciones del mismo filtro
//: divergen en cuanto nadie las compara — que es justo lo que habia pasado: la
//: rejilla obedecia y el panel de al lado seguia diciendo "21 reportes".
//:
//: Sin sello de fecha se deja pasar. Un reporte cuyo `utc` no se pudo leer es un
//: fallo del dato, no algo que deba desaparecer de la lista sin decir nada.
function enLaVentana(cosa) {
  const dias = (VENTANAS[estado.ventana] || VENTANAS.todo).dias;
  if (!dias) return true;
  const utc = cosa.dataset ? cosa.dataset.utc : cosa.utc;
  if (!utc) return true;
  const t = Date.parse(utc);
  if (!Number.isFinite(t)) return true;
  return Date.now() - t <= dias * 86400000;
}

const ORDENES = {
  fecha: { texto: "Fecha", clave: (li) => li.dataset.utc || "" },
  mag: { texto: "Magnitud", clave: (li) => Number(li.dataset.mag) || 0 },
  pop: { texto: "Personas expuestas", clave: (li) => Number(li.dataset.pop) || 0 },
};

//: Si el evento cae dentro de lo que el mapa esta enseñando.
//:
//: `getBounds` puede devolver una caja que cruza el antimeridiano cuando el
//: mapa da la vuelta; a la escala de este visor no pasa, pero se compara con
//: `contains` de MapLibre en vez de a mano para no tener que decidirlo.
function enElEncuadre(cosa) {
  const m = estado.mapa;
  const datos = cosa.dataset || cosa;
  const lon = Number(datos.lon);
  const lat = Number(datos.lat);
  if (!m || !Number.isFinite(lon) || !Number.isFinite(lat)) return true;
  try {
    return m.getBounds().contains([lon, lat]);
  } catch (error) {
    return true;
  }
}

//: Los tres filtros de la lista de reportes, en un solo sitio.
//:
//: Se aplica igual a una fila de la lista que al objeto del evento. Que sea uno
//: solo es el punto: el panel lateral quedo un mes diciendo "21 reportes
//: publicados" y nombrando un sismo de Colombia mientras la cabecera decia "3
//: reportes" y el mapa ensenaba solo Venezuela.
function pasaFiltros(cosa) {
  const datos = cosa.dataset || cosa;
  const suyo = !estado.paisFiltrado || datos.iso3 === estado.paisFiltrado;
  const dentro = !estado.soloEnVista || enElEncuadre(cosa);
  return suyo && dentro && enLaVentana(cosa);
}

//: Un solo sitio que decide que se ve y en que orden.
//:
//: Antes el filtro por pais escribia `hidden` y nadie mas tocaba la lista. Con
//: tres criterios —pais, encuadre y orden— tener cada uno su funcion es como se
//: llega a que uno pise a otro; este es el unico que escribe.
function refrescarLista({ anunciando = true } = {}) {
  const lista = $("lista-eventos");
  if (!lista) return;
  const filas = [...lista.querySelectorAll("li")];

  const orden = ORDENES[estado.orden] || ORDENES.fecha;
  filas
    .slice()
    .sort((a, b) => {
      const va = orden.clave(a);
      const vb = orden.clave(b);
      // Descendente en las tres: lo mas reciente, lo mas fuerte y lo que mas
      // gente dejo dentro. Nadie abre esta lista buscando el sismo mas pequeño.
      return va > vb ? -1 : va < vb ? 1 : 0;
    })
    .forEach((li) => lista.appendChild(li));

  let visibles = 0;
  for (const li of filas) {
    li.hidden = !pasaFiltros(li);
    if (!li.hidden) visibles += 1;
  }

  for (const boton of document.querySelectorAll("#ventana-lista button")) {
    boton.setAttribute("aria-pressed", String(boton.dataset.ventana === estado.ventana));
  }
  for (const boton of document.querySelectorAll("#filtro-paises button")) {
    boton.setAttribute(
      "aria-pressed",
      String((boton.dataset.iso3 || "") === (estado.paisFiltrado || ""))
    );
  }
  for (const boton of document.querySelectorAll("#orden-lista button")) {
    boton.setAttribute("aria-pressed", String(boton.dataset.orden === estado.orden));
  }
  const interruptor = $("solo-en-vista");
  if (interruptor) interruptor.checked = estado.soloEnVista;

  const cuenta = $("cuenta-lista");
  if (cuenta) {
    cuenta.textContent = estado.soloEnVista
      ? `${visibles} ${visibles === 1 ? "reporte" : "reportes"} en el encuadre`
      : `${visibles} ${visibles === 1 ? "reporte publicado" : "reportes publicados"}`;
  }

  const vacio = $("sin-resultados");
  vacio.hidden = visibles > 0;
  if (!visibles) vacio.textContent = motivoDeVacio();

  // Y EL PANEL DE AL LADO, CON EL MISMO FILTRO.
  //
  // `pintarPanorama` se llamaba una sola vez al arrancar y nunca mas. Con
  // "Venezuela (3)" puesto, la cabecera decia "3 reportes publicados", el mapa
  // dejaba tres epicentros, la rejilla de abajo dejaba tres tarjetas — y el
  // panel pegado al mapa seguia diciendo "21 reportes publicados", "mayor
  // exposicion registrada: San Jose del Palmar, Colombia" y listando los
  // veintiuno. Dos cifras contradictorias a diez centimetros una de otra.
  pintarPanorama((estado.eventos || []).filter(pasaFiltros));

  aplicarFiltrosAlMapa();
  pintarLimpiar();
  if (anunciando) {
    anunciar(`${visibles} ${visibles === 1 ? "reporte" : "reportes"} en la lista.`);
  }
}

//: Por que la lista se quedo vacia, nombrando el filtro culpable.
//:
//: Decir "ese pais no tiene reportes" cuando lo que sobra es la ventana temporal
//: manda a cambiar lo que no era. Vive aparte porque lo usan dos sitios: la
//: rejilla de tarjetas y el panorama del panel lateral.
function motivoDeVacio() {
  if (estado.soloEnVista) {
    return "Ningún reporte cae dentro de lo que el mapa está enseñando. Aleja o mueve el mapa.";
  }
  const ventana = VENTANAS[estado.ventana] || VENTANAS.todo;
  if (ventana.dias) {
    return (
      `Ningún reporte en los últimos ${ventana.texto.toLowerCase()}` +
      `${estado.paisFiltrado ? " en ese país" : ""}. Prueba con «Todo».`
    );
  }
  return "Ese país todavía no tiene reportes publicados.";
}

function aplicarFiltro(iso3) {
  estado.paisFiltrado = iso3;
  refrescarLista();
}

//: Los controles de la lista.
//:
//: El interruptor de encuadre solo aparece si hay mapa: sin el no hay
//: `getBounds` que consultar, y un control que no puede hacer nada es peor que
//: la ausencia del control — es la misma regla del interruptor de sismos
//: menores, que solo se inyecta si hay algo que enseñar.


estado.mapa = iniciarMapa();
pintarSelectorAmenaza();
engancharSalidas();
cargarEventos();


// --- Sismos vistos y no despachados ----------------------------------------
//
// El 26-ago-2026 un M4,9 bajo Jordan, Santander, se sintio en media Colombia.
// El sistema lo vio a los doce minutos y decidio bien —`M4.9 < umbral M5.5`—
// pero esa decision solo existia en un log de CI. Desde el visor, «lo vi y es
// inofensivo» y «estoy roto» se veian exactamente igual.
//
// Esta capa no baja el umbral. Enseña lo que hay por debajo, y su trabajo de
// diseño es **no parecer una alarma**: un punto en un mapa se lee como alarma
// diga lo que diga el pie. De ahi que sea gris, hueca, pequeña, sin halo, sin
// etiqueta, y apagada de entrada.
async function cargarObservados() {
  let datos;
  try {
    datos = await json(OBSERVADOS);
  } catch (error) {
    // Todavia no hay latido que lo haya escrito. No es un fallo del visor.
    console.info("observados:", error);
    return;
  }
  const eventos = (datos && datos.eventos) || [];
  if (!eventos.length) return;

  dibujarObservados(eventos);
  pintarInterruptorObservados(eventos, datos.ventana_dias);
  estado.vivo.observados = eventos.length;
  estado.vivo.ventanaSismos = datos.ventana_dias || 5;
  estado.vivo.sismosUtc = datos.generado_utc || null;
  pintarEnVivo();
}

function dibujarObservados(eventos) {
  const m = estado.mapa;
  //: Las coordenadas se guardan aunque no haya mapa: "Ver en el mapa" las
  //: necesita para encuadrarlas, y sin esto el boton solo podia encender una
  //: capa y confiar en que se notara.
  estado.observadosGeo = eventos.map((e) => [Number(e.lon), Number(e.lat)]);
  // Y los eventos enteros, para poder repintar la capa tras un cambio de mapa
  // base: `setStyle` borra fuentes y capas, y con solo las coordenadas no se
  // puede reconstruir el globo de cada sismo.
  estado.observadosDatos = eventos;
  if (!m) return;

  const pintar = () => {
    if (m.getSource("observados")) return;
    m.addSource("observados", {
      type: "geojson",
      data: {
        type: "FeatureCollection",
        features: eventos.map((e) => ({
          type: "Feature",
          geometry: { type: "Point", coordinates: [e.lon, e.lat] },
          properties: {
            usgs_id: e.usgs_id,
            mag: e.mag,
            lugar: e.lugar,
            depth_km: e.depth_km,
            origen_utc: e.origen_utc,
            razon: e.razon,
            iso3: e.iso3 || "",
          },
        })),
      },
    });
    crearEstrella(m, "estrella-gris", OBSERVADO, "#ffffff");
    // La MISMA estrella que los epicentros, en gris y pequena.
    //
    // Antes era un circulo hueco, y un circulo no dice "sismo": dice "punto".
    // En simbologia la **forma** codifica que es la cosa y el tamano y el color
    // codifican su importancia. Con dos formas distintas para el mismo
    // fenomeno, el mapa afirmaba que son dos fenomenos.
    //
    // Ahora se lee de un vistazo: estrella grande y roja = sismo con reporte;
    // estrella pequena y gris = sismo visto y no despachado. Misma familia,
    // distinta jerarquia — que es exactamente lo que son.
    m.addLayer({
      id: "observados",
      type: "symbol",
      source: "observados",
      layout: {
        visibility: "none",
        "icon-image": "estrella-gris",
        "icon-size": ["interpolate", ["linear"], ["zoom"], 3, 0.3, 8, 0.46],
        "icon-allow-overlap": true,
      },
      paint: { "icon-opacity": 0.9 },
    });

    anotarPintado("observados", eventos.length);
    aplicarAmenaza();

    m.on("mouseenter", "observados", () => (m.getCanvas().style.cursor = "help"));
    m.on("mouseleave", "observados", () => (m.getCanvas().style.cursor = ""));
    m.on("click", "observados", (ev) => {
      const p = ev.features[0].properties;
      abrirGlobo(new maplibregl.Popup({ closeButton: true, maxWidth: "300px" }))
        .setLngLat(ev.lngLat)
        .setHTML(
          `<div class="popup-observado">` +
            `<strong>M${String(p.mag).replace(".", ",")}</strong> · ${escapar(p.lugar)}<br>` +
            `<span class="menor">${comoFecha(p.origen_utc)} · ${numero(p.depth_km)} km de profundidad</span>` +
            `<p class="nota-observado">No se midió su impacto. ${escapar(p.razon)}.</p>` +
          `</div>`
        )
        .addTo(m);
    });
  };

  cuandoElEstiloEsteListo(m, pintar);
}

//: Que significa cada simbolo del mapa. Una sola caja, no tres.
//
// Habia leyenda para la coropleta de un evento y para la rampa de fuego, y
// ninguna para los epicentros ni para los sismos menores — que son los simbolos
// que estan siempre en pantalla. Quien abria el visor veia estrellas de dos
// tamanos y circulos rosados sin nada que dijera que eran.
//
// Va junta porque la pregunta que se hace quien mira es una sola: "¿que es
// esto?". Tres cajas separadas obligan a buscar en cual esta la respuesta.
//: El aviso de cabecera dice como leer LO QUE SE ESTA ENSENANDO.
//:
//: Era fijo y hablaba de "cada franja de intensidad". En modo fuego el mapa no
//: dibuja ninguna franja de intensidad: dibuja celdas donde un satelite vio
//: calor en 24 h. El aviso mas importante del tablero —el que separa exposicion
//: de dano— quedaba describiendo otro mapa.
//:
//: Lo que **no** cambia es la primera frase. "Exposicion no es dano" vale para
//: las dos amenazas y es la razon de ser del aviso; lo que se adapta es que
//: cuenta la cifra debajo.
function pintarAvisoDeLectura() {
  const texto = $("aviso-lectura-texto");
  if (!texto) return;
  texto.innerHTML =
    estado.amenaza === "fuego"
      ? `<strong>Exposición no es daño.</strong> Un foco es lo que un satélite ` +
        `vio arder en 24 h: ni área quemada, ni un incendio confirmado, ni una ` +
        `evacuación. Informa cuánta población e infraestructura hay <em>dentro</em> ` +
        `de esas celdas.`
      : `<strong>Exposición no es daño.</strong> No es una alerta temprana, no ` +
        `estima víctimas y no dictamina habitabilidad. Informa cuánta población e ` +
        `infraestructura quedó <em>dentro</em> de cada franja de intensidad.`;
}

//: Las entradas de la leyenda, para el estado en que esta el mapa AHORA.
//:
//: La caja listaba las tres siempre. En modo fuego seguia explicando "Sismo con
//: reporte" y "Sismo visto, sin reporte" —dos simbolos que ahi no se dibujan— y
//: con un evento abierto explicaba el panorama mientras el mapa ensenaba una
//: malla de intensidad, compitiendo ademas con la leyenda de la capa activa.
//:
//: Una leyenda que nombra lo que no esta ensena a no leer la leyenda.
//:
//: Los textos dicen **como distinguirlos**, no solo que son. "El círculo crece
//: con la población expuesta" no ayudaba a separar un reporte sin exposicion de
//: un sismo menor: los dos son una estrella. El color y el tamano son la
//: diferencia, asi que se nombran.
function entradasDeLeyenda() {
  const epicentro = {
    sim: "sim-epicentro",
    titulo: "Sismo con reporte",
    nota: "Estrella roja con círculo. El círculo crece con la población expuesta",
  };
  const observado = {
    sim: "sim-observado",
    titulo: "Sismo visto, sin reporte",
    nota: "Estrella gris pequeña. Por debajo de M5,5: se vio y no se midió su impacto",
  };
  const foco = {
    sim: "sim-fuego",
    titulo: "Foco activo",
    // El tamaño tambien, desde que el radio va por la raiz del FRP. Decir solo
    // "el color es la energia" con un simbolo que ahora crece con ella deja al
    // lector sin la mitad de la clave.
    nota: "Detección de satélite en 24 h. El color y el tamaño son la energía",
  };

  if (estado.amenaza === "fuego") {
    // En modo fuego los epicentros se quedan de contexto tenue —lo dice
    // `aplicarAmenaza`—, asi que siguen mereciendo una linea. Los observados no
    // se dibujan y no la merecen.
    return [foco, epicentro];
  }
  const entradas = [epicentro];
  const interruptor = $("interruptor-observados");
  // La entrada del sismo menor solo si su capa puede estar encendida. Explicar
  // un simbolo que el usuario no tiene forma de ver es ruido.
  if (interruptor && !interruptor.hidden) entradas.push(observado);
  return entradas;
}

function pintarLeyendaSimbolos() {
  const anfitrion = $("controles-mapa") || $("lienzo");
  if (!anfitrion) return;

  // `<details>` y no `<div>`: en un movil de 390 px esta caja medía 248 —el
  // 64 % del ancho— y tapaba Colombia, Ecuador y Peru. Plegada ocupa una linea.
  //
  // Abierta en pantalla ancha, donde sobra sitio y la pregunta "¿que es esto?"
  // merece respuesta sin pedirla. El `open` se decide en JS porque CSS no puede
  // ponerlo ni quitarlo.
  let caja = $("leyenda-simbolos");
  if (!caja) {
    caja = document.createElement("details");
    caja.className = "leyenda leyenda-simbolos";
    caja.id = "leyenda-simbolos";
    caja.open = window.matchMedia("(min-width: 48rem)").matches;
    anfitrion.appendChild(caja);
  }

  // Con un evento abierto manda la leyenda de la capa: la caja se pliega para
  // no discutirle el sitio, pero no se quita —el epicentro sigue en el mapa y
  // quien lo pregunte tiene donde mirar.
  //
  // El plegado se marca, y solo se deshace lo que se hizo: si el usuario la
  // cerro a mano, al volver al panorama sigue cerrada. Un panel que se reabre
  // solo cada vez que cambia algo es un panel que hay que cerrar dos veces.
  if (estado.seleccionado) {
    if (caja.open) {
      caja.open = false;
      caja.dataset.plegadaPorEvento = "1";
    }
  } else if (caja.dataset.plegadaPorEvento) {
    delete caja.dataset.plegadaPorEvento;
    caja.open = window.matchMedia("(min-width: 48rem)").matches;
  }

  caja.innerHTML =
    `<summary class="leyenda-titulo mono">Qué hay en el mapa</summary>` +
    `<ul class="leyenda-simbolos-lista">` +
    entradasDeLeyenda()
      .map(
        (e) =>
          `<li><span class="sim ${e.sim}" aria-hidden="true"></span>` +
          `<span><strong>${e.titulo}</strong><br>` +
          `<span class="menor">${e.nota}</span></span></li>`
      )
      .join("") +
    `</ul>`;
}

function pintarInterruptorObservados(eventos, ventanaDias) {
  const anfitrion = $("controles-mapa") || $("leyenda") || $("mapa");
  if (!anfitrion || $("interruptor-observados")) return;

  const caja = document.createElement("label");
  caja.className = "interruptor-observados";
  caja.id = "interruptor-observados";
  caja.innerHTML =
    `<input type="checkbox"> ` +
    `<span>Sismos menores vistos <span class="menor">` +
    `(${eventos.length} en ${ventanaDias || 5} días, sin reporte)</span></span>`;
  // Nace obedeciendo al modo: las capas cargan en paralelo y este control puede
  // crearse despues de que el selector de amenaza ya se aplico.
  caja.hidden = estado.amenaza === "fuego";

  anfitrion.appendChild(caja);
  // La leyenda solo explica el sismo menor si su interruptor existe, y acaba de
  // nacer.
  pintarLeyendaSimbolos();

  caja.querySelector("input").addEventListener("change", (ev) => {
    const m = estado.mapa;
    if (!m || !m.getLayer("observados")) return;
    m.setLayoutProperty("observados", "visibility", ev.target.checked ? "visible" : "none");
    // Encender la capa no basta: los filtros que ya estan puestos tienen que
    // alcanzarla. Sin esto, marcar la casilla con "Colombia" elegido devolvia
    // los diez menores de todo el continente.
    aplicarFiltrosAlMapa();
  });
}


// --- Focos activos ----------------------------------------------------------
//
// La otra amenaza. El activo de exposicion es agnostico: las mismas celdas que
// dicen cuanta gente hay bajo un MMI 7 dicen cuanta hay bajo fuego activo.
//
// Lo que cambia es lo que se puede afirmar, y por eso esta capa se dibuja
// distinto: un incendio no tiene un campo de intensidad publicado como el
// ShakeMap, asi que aqui no hay bandas con significado fisico — hay potencia
// radiativa medida y detecciones contadas. La leyenda lo dice y el popup lo
// repite.
async function cargarIncendios() {
  let datos;
  try {
    datos = await json(INCENDIOS);
  } catch (error) {
    console.info("incendios:", error);
    return;
  }
  const celdas = (datos && datos.celdas) || [];
  if (!celdas.length) return;

  dibujarIncendios(datos);
  estado.fuegoDatos = datos;
  estado.focos = agruparFocos(celdas);
  estado.focosPorCelda = new Map();
  for (const foco of estado.focos) {
    for (const h of foco.h3s) estado.focosPorCelda.set(h, foco);
  }
  // Cuantos focos salieron de las celdas. Va al registro publico por el mismo
  // motivo que las capas: una prueba de navegador no puede afirmar nada sobre
  // el agrupado si tiene que deducirlo de un pantallazo.
  estado.fuegoRef = 0; // se recalcula con los focos recien cargados
  anotarPintado("focos", estado.focos.length);
  pintarControlesFocos();
  pintarListaFocos({ anunciando: false });
  estado.vivo.ventanaFuego = datos.ventana_horas || 24;
  estado.vivo.fuegoUtc = datos.generado_utc || null;
  // Los centros, una vez: los necesita el filtro por extensión en cada
  // movimiento del mapa.
  estado.centrosDeCelda = indexarCentros(celdas);
  // Y ya no se copia `datos.totales`: las cifras se calculan desde las celdas
  // que pasan los filtros. Sin filtros dan lo mismo —hay prueba de ello— y con
  // filtros dan lo que el usuario está mirando, que es lo que faltaba.
  refrescarTablero();
}

//: Un incendio no es una celda: es el grupo de celdas contiguas que arden.
//:
//: El visor solo sabia hablar de celdas sueltas. Pulsar una abria un globo con
//: sus cifras y nada mas, asi que "¿que superficie cubre este incendio?" —la
//: primera pregunta de cualquiera que mire un mapa de fuego— no tenia respuesta
//: en ninguna parte del producto. Y la tarjeta de arriba solo daba el total de
//: toda America Latina, que es el otro extremo: o todo, o un hexagono de 5 km².
//:
//: Un foco es una componente conexa sobre la malla H3: dos celdas del mismo
//: foco si comparten lado. Es la definicion que usa cualquier producto de
//: fuego, y la que hace que el area signifique algo.
//:
//: `gridDisk(h, 1)` da la celda y sus seis vecinas. Con 4.000 celdas son
//: ~28.000 consultas a un Set: milisegundos. No hace falta nada mas listo.
function agruparFocos(celdas) {
  if (typeof h3 === "undefined" || !Array.isArray(celdas) || !celdas.length) return [];

  const porH3 = new Map(celdas.map((c) => [c.h3, c]));
  const padre = new Map(celdas.map((c) => [c.h3, c.h3]));

  const raiz = (x) => {
    let r = x;
    while (padre.get(r) !== r) r = padre.get(r);
    // Compresion de caminos: sin esto, una cadena larga de celdas —una quema
    // siguiendo un rio, que es la forma mas comun— degrada a O(n) por consulta.
    while (padre.get(x) !== r) {
      const siguiente = padre.get(x);
      padre.set(x, r);
      x = siguiente;
    }
    return r;
  };

  for (const c of celdas) {
    let vecinas;
    try {
      vecinas = h3.gridDisk(c.h3, 1);
    } catch (error) {
      continue; // una celda ilegible no puede tumbar el agrupado entero
    }
    for (const v of vecinas) {
      if (v === c.h3 || !porH3.has(v)) continue;
      const a = raiz(c.h3);
      const b = raiz(v);
      if (a !== b) padre.set(a, b);
    }
  }

  const grupos = new Map();
  for (const c of celdas) {
    const r = raiz(c.h3);
    if (!grupos.has(r)) grupos.set(r, []);
    grupos.get(r).push(c);
  }

  return [...grupos.entries()].map(([id, suyas]) => {
    const foco = resumirFoco(id, suyas);
    foco.iso3 = paisDelFoco(foco);
    return foco;
  });
}

//: Las cifras de un foco. Se suman las de sus celdas, con una excepcion.
//:
//: El reparto del suelo se pondera por energia, no por numero de celdas, que es
//: la misma regla que usa `p5_incendios` para el reparto regional. Contar
//: celdas daria el mismo peso a una que arde con 4 MW y a otra con 900.
//: El area de un foco, con un decimal cuando es pequena.
//:
//: Con celdas de 0,74 km², `Math.round` convierte un foco de una celda en
//: "1 km²" —un 35 % de mas— y uno de dos en "1" tambien. Por debajo de 10 km²
//: el decimal deja de ser ruido y pasa a ser la diferencia entre dos focos
//: distintos.
function areaDeFoco(km2) {
  return km2 < 10 ? numero(km2, 1) : numero(Math.round(km2));
}

function resumirFoco(id, celdas) {
  const suma = (campo) => celdas.reduce((t, c) => t + (Number(c[campo]) || 0), 0);

  // Solo las celdas que tienen cobertura del suelo entran en el reparto: las
  // demas no son "cero por ciento arbolado", son "sin medir". El panel dice
  // cuantas fueron.
  const conSuelo = celdas.filter((c) =>
    ["arbolado_pct", "pastizal_pct", "cultivo_pct", "humedal_pct"].some((k) => Number(c[k]) > 0)
  );
  const energiaMedida = conSuelo.reduce((t, c) => t + (Number(c.frp_suma) || 0), 0);
  const suelo = {};
  if (energiaMedida > 0) {
    for (const clase of ["arbolado", "pastizal", "cultivo", "humedal"]) {
      const pct =
        conSuelo.reduce(
          (t, c) => t + ((Number(c[`${clase}_pct`]) || 0) / 100) * (Number(c.frp_suma) || 0),
          0
        ) / energiaMedida;
      if (pct > 0) suelo[clase] = pct * 100;
    }
  }

  const sellos = celdas.map((c) => c.ultima_utc).filter(Boolean).sort();
  const primeros = celdas.map((c) => c.primera_utc).filter(Boolean).sort();

  return {
    id,
    celdas,
    h3s: celdas.map((c) => c.h3),
    nCeldas: celdas.length,
    areaKm2: celdas.length * AREA_CELDA_FUEGO_KM2,
    pop: suma("pop"),
    bld: suma("bld"),
    salud: suma("salud"),
    edu: suma("edu"),
    detecciones: suma("detecciones"),
    deteccionesBaja: suma("detecciones_baja"),
    frpSuma: suma("frp_suma"),
    frpMax: celdas.reduce((t, c) => Math.max(t, Number(c.frp_max) || 0), 0),
    // El maximo, como en la celda: promediar el pixel mas caliente del foco con
    // los tibios de su borde da un numero que no describe nada.
    brilloMaxK: celdas.reduce((t, c) => Math.max(t, Number(c.brillo_max_k) || 0), 0),
    suelo,
    celdasConSuelo: conSuelo.length,
    primeraUtc: primeros[0] || null,
    ultimaUtc: sellos[sellos.length - 1] || null,
  };
}

// --- La lista de focos ------------------------------------------------------
//
// Gemela de la de reportes, del otro lado del selector de amenaza. El fuego
// tenia mapa y panel de detalle pero ningun indice: para saber cuales son los
// focos mas recientes, o los de un pais, habia que buscar hexagonos a ojo entre
// cuatro mil.

//: La ventana del fuego es de horas, no de anos, y no por simetria rota: FIRMS
//: publica una foto de veinticuatro horas. Pedir "12 meses" aqui no significaria
//: nada, y ofrecerlo prometeria un archivo que no existe.
const VENTANAS_FUEGO = {
  h24: { texto: "24 h", horas: 24 },
  h12: { texto: "12 h", horas: 12 },
  h6: { texto: "6 h", horas: 6 },
};

//: Como se ordenan. "Reciente" primero y por defecto: la pregunta que trae a
//: alguien a un mapa de fuego es que esta ardiendo AHORA, no que arde mas.
const ORDENES_FOCOS = {
  reciente: { texto: "Reciente", clave: (f) => Date.parse(f.ultimaUtc) || 0 },
  area: { texto: "Área", clave: (f) => f.areaKm2 },
  personas: { texto: "Personas", clave: (f) => f.pop },
  energia: { texto: "Energía", clave: (f) => f.frpSuma },
};

//: Desde cuando se cuenta la ventana del fuego. **No es "ahora".**
//:
//: Es el sello de la deteccion mas reciente que hay en el fichero. La ventana
//: se medía desde `Date.now()`, y con un `incendios.json` de once horas —que es
//: lo normal: el cron corre cada seis y FIRMS tarda unas tres en publicar—
//: "ultimas 6 h" salia SIEMPRE vacio. El filtro parecia roto y en realidad
//: estaba diciendo la verdad sobre una pregunta que nadie hace: nadie quiere
//: saber que ardio en las ultimas seis horas de reloj, sino en las ultimas seis
//: horas **de lo que el satelite vio**.
//:
//: Se toma el maximo de los sellos y no `generado_utc` porque son cosas
//: distintas: uno es cuando se publico el fichero y otro cuando paso el
//: satelite por ultima vez, y entre los dos hay horas.
function referenciaDelFuego() {
  if (estado.fuegoRef) return estado.fuegoRef;
  let max = 0;
  for (const f of estado.focos) {
    const t = Date.parse(f.ultimaUtc);
    if (Number.isFinite(t) && t > max) max = t;
  }
  if (!max && estado.vivo && estado.vivo.fuegoUtc) {
    const t = Date.parse(estado.vivo.fuegoUtc);
    if (Number.isFinite(t)) max = t;
  }
  estado.fuegoRef = max || Date.now();
  return estado.fuegoRef;
}

function enLaVentanaFuego(foco) {
  const horas = (VENTANAS_FUEGO[estado.ventanaFuego] || VENTANAS_FUEGO.h24).horas;
  const t = Date.parse(foco.ultimaUtc);
  // Sin sello legible se deja pasar: es un fallo del dato, no algo que deba
  // desaparecer de la lista sin decir nada.
  if (!Number.isFinite(t)) return true;
  return referenciaDelFuego() - t <= horas * 3600000;
}

//: El pais de un foco es el de sus celdas. Casi siempre uno solo; un incendio
//: que cruza una frontera existe, pero partir el foco por eso seria inventar
//: dos incendios donde hay uno. Se toma el pais con mas celdas.
//:
//: Un foco sin pais —fuera de los activos cargados— no se descarta: el fuego no
//: respeta fronteras y esas celdas son informacion. Solo no aparece al filtrar
//: por un pais concreto, que es lo correcto: no se sabe si es de ese.
function paisDelFoco(foco) {
  const cuenta = new Map();
  for (const c of foco.celdas) {
    const iso = String(c.iso3 || "").trim();
    if (iso) cuenta.set(iso, (cuenta.get(iso) || 0) + 1);
  }
  let mejor = "";
  let max = 0;
  for (const [iso, n] of cuenta) {
    if (n > max) {
      mejor = iso;
      max = n;
    }
  }
  return mejor;
}

function nombrePais(iso3) {
  return (estado.nombresPais && estado.nombresPais.get(iso3)) || iso3;
}

//: Cuantos focos se listan. No son las 2.903 filas que salen del agrupado:
//: nadie lee tres mil, y construirlas cuesta mas que dibujar el mapa entero.
//: Se listan los primeros por el orden elegido y la cuenta dice cuantos quedan
//: fuera, para que el recorte no se lea como "esto es todo lo que hay" — que es
//: el mismo error que la capa de fuego cometia rotulandose con el total.
const MAX_FILAS_FOCOS = 60;

function filaFoco(foco) {
  const li = document.createElement("li");
  li.dataset.utc = foco.ultimaUtc || "";
  li.dataset.iso3 = foco.iso3 || "";

  // Las mismas clases que la fila de un reporte: son dos indices gemelos y
  // verlos distintos sugeriria que se leen distinto.
  const cabecera = document.createElement("div");
  cabecera.className = "evento-cabecera";
  const titulo = document.createElement("span");
  titulo.className = "evento-mag";
  titulo.textContent = foco.nCeldas === 1 ? "1 celda" : numero(foco.nCeldas) + " celdas";
  const area = document.createElement("span");
  area.className = "enlace-reporte";
  area.textContent = areaDeFoco(foco.areaKm2) + " km²";
  cabecera.append(titulo, area);

  const meta = document.createElement("p");
  meta.className = "evento-meta";
  meta.textContent = [
    comoFecha(foco.ultimaUtc),
    foco.iso3 ? nombrePais(foco.iso3) : "fuera de los activos",
    numero(foco.detecciones) + (foco.detecciones === 1 ? " detección" : " detecciones"),
  ].join(" · ");

  const cifra = document.createElement("p");
  cifra.className = "evento-cifra";
  // Por debajo de una persona no se publica una cifra: "0,1 personas dentro" es
  // una precision que el modelo no tiene y que lee peor que no decir nada. La
  // poblacion de una celda es una suma dasimetrica, no un censo.
  cifra.innerHTML =
    foco.pop >= 1
      ? iconoSvg("personas") + comoConteo(foco.pop) + " personas dentro"
      : '<span class="sin-alcance">Sin población medida en estas celdas</span>';

  li.append(cabecera, meta, cifra);
  li.addEventListener("click", () => {
    abrirFoco(foco);
    $("mapa")?.scrollIntoView({
      behavior: REDUCIR_MOVIMIENTO ? "auto" : "smooth",
      block: "nearest",
    });
  });
  return li;
}

function pintarListaFocos({ anunciando = true } = {}) {
  const lista = $("lista-focos");
  if (!lista || !estado.focos.length) return;

  const orden = ORDENES_FOCOS[estado.ordenFocos] || ORDENES_FOCOS.reciente;
  const dentro = estado.focos.filter(
    (f) => enLaVentanaFuego(f) && (!estado.paisFuego || f.iso3 === estado.paisFuego)
  );
  const listados = dentro
    .slice()
    .sort((a, b) => orden.clave(b) - orden.clave(a))
    .slice(0, MAX_FILAS_FOCOS);

  lista.innerHTML = "";
  for (const foco of listados) lista.appendChild(filaFoco(foco));

  const cargando = $("estado-focos");
  if (cargando) cargando.hidden = true;

  const cuenta = $("cuenta-focos");
  if (cuenta) {
    // LOS FOCOS SIN PAIS SE CUENTAN EN VOZ ALTA.
    //
    // `paisDelFoco` ya explica por que un foco fuera de los activos construidos
    // no aparece al elegir un pais: no se sabe si es de ese. Lo que faltaba era
    // decir CUANTOS son. Medido en la pagina publicada: los diecisiete paises
    // del desplegable sumaban 4.104 y el total era 6.239 — un tercio de los
    // focos no lo alcanza ningun filtro, y nada en pantalla lo insinuaba.
    const sinPais = estado.focos.filter((f) => enLaVentanaFuego(f) && !f.iso3).length;
    const apunte = !estado.paisFuego && sinPais ? ` · ${numero(sinPais)} sin país asignado` : "";
    cuenta.textContent = dentro.length
      ? (listados.length < dentro.length
          ? numero(listados.length) + " de " + numero(dentro.length) + " focos"
          : numero(dentro.length) + (dentro.length === 1 ? " foco" : " focos")) + apunte
      : "";
  }

  const vacio = $("sin-focos");
  if (vacio) {
    vacio.hidden = dentro.length > 0;
    if (!dentro.length) {
      // El aviso dice CUANDO se miro por ultima vez, y no solo que no hay nada.
      //
      // La ventana se cuenta desde ahora, pero el dato es una foto que puede
      // llevar horas publicada: con un fichero de hace diez horas, "ultimas 6 h"
      // sale vacio siempre, y sin este apunte se lee como "no hay fuego" cuando
      // lo cierto es "no lo hemos vuelto a mirar".
      const v = VENTANAS_FUEGO[estado.ventanaFuego] || VENTANAS_FUEGO.h24;
      const sello = estado.vivo && estado.vivo.fuegoUtc ? haceCuanto(estado.vivo.fuegoUtc) : null;
      const apunte = sello ? " El satélite se revisó " + sello + "." : "";
      vacio.textContent =
        (estado.paisFuego
          ? "Ningún foco en ese país en las últimas " + v.texto + "."
          : "Ningún foco detectado en las últimas " + v.texto + ".") + apunte;
    }
  }

  for (const boton of document.querySelectorAll("#ventana-focos button")) {
    boton.setAttribute("aria-pressed", String(boton.dataset.ventana === estado.ventanaFuego));
  }
  for (const boton of document.querySelectorAll("#orden-focos button")) {
    boton.setAttribute("aria-pressed", String(boton.dataset.orden === estado.ordenFocos));
  }
  for (const boton of document.querySelectorAll("#filtro-paises-fuego button")) {
    boton.setAttribute(
      "aria-pressed",
      String((boton.dataset.iso3 || "") === (estado.paisFuego || ""))
    );
  }
  aplicarFiltrosAlMapa();
  pintarLimpiar();
  if (anunciando) {
    anunciar(numero(dentro.length) + (dentro.length === 1 ? " foco" : " focos") + " en la lista.");
  }
}


// --- Los filtros gobiernan el mapa, no solo la lista ------------------------
//
// Vivian debajo, dentro de la seccion de reportes, y solo recortaban filas.
// Elegir "Colombia" dejaba la lista con los suyos y el mapa con veintiun
// epicentros repartidos por el continente: el filtro diciendo una cosa y el
// mapa otra, que es la misma clase de contradiccion que el selector de amenaza
// existe para evitar.
//
// Aqui se traducen a filtros de MapLibre. `setFilter` es la via correcta: no
// toca la fuente, no repinta hexagonos y deja el estado del control y el del
// mapa donde tienen que estar, que es en el mismo sitio.

//: Un filtro que no descarta nada. MapLibre acepta `null`, pero un `null`
//: suelto se lee como "se me olvido" y esto se lee como "todo pasa".
const TODO_PASA = null;

//: Corte de la ventana en milisegundos desde la epoca, o `null` si es "Todo".
function corteDeVentana(dias) {
  return dias ? Date.now() - dias * 86400000 : null;
}

//: El filtro de los epicentros: pais y fecha.
//:
//: La fecha se compara como cadena ISO y no convirtiendo a numero dentro de la
//: expresion: MapLibre no sabe parsear fechas, y los sellos de USGS son ISO-8601
//: en UTC, que ordena igual como texto que como instante. Es la misma propiedad
//: que hace que `sort()` funcione sobre los sellos de la lista.
function filtroDeEpicentros() {
  const partes = ["all"];
  if (estado.paisFiltrado) partes.push(["==", ["get", "iso3"], estado.paisFiltrado]);
  const dias = (VENTANAS[estado.ventana] || VENTANAS.todo).dias;
  const corte = corteDeVentana(dias);
  if (corte !== null) {
    partes.push([">=", ["get", "utc"], new Date(corte).toISOString()]);
  }
  return partes.length > 1 ? partes : TODO_PASA;
}

//: El de los focos: pais y hora de deteccion.
function filtroDeFocos() {
  const partes = ["all"];
  if (estado.paisFuego) partes.push(["==", ["get", "iso3"], estado.paisFuego]);
  const horas = (VENTANAS_FUEGO[estado.ventanaFuego] || VENTANAS_FUEGO.h24).horas;
  // La misma referencia que la lista: el sello mas reciente del fichero, no el
  // reloj. Si el mapa y la lista contaran desde sitios distintos, uno ensenaria
  // focos que el otro dice que no existen.
  const corte = referenciaDelFuego() - horas * 3600000;
  partes.push([">=", ["get", "ultima_utc"], new Date(corte).toISOString()]);
  return partes.length > 1 ? partes : TODO_PASA;
}

//: Aplica al mapa lo que dicen los controles.
//:
//: Se llama desde `refrescarLista` y `pintarListaFocos`, que es donde ya se
//: sabe que un filtro cambio: tener dos sitios que reaccionan al mismo cambio
//: es como se acaba con la lista filtrada y el mapa sin filtrar.
function aplicarFiltrosAlMapa() {
  const m = estado.mapa;
  if (!m || !m.getLayer) return;

  const pon = (capa, filtro) => {
    try {
      if (m.getLayer(capa)) m.setFilter(capa, filtro);
    } catch (error) {
      // Una capa que aun no existe no es un fallo: los datos llegan por su
      // cuenta y esto corre cada vez que se toca un control.
      console.warn("filtro de " + capa + ":", error && error.message);
    }
  };

  const sismos = filtroDeEpicentros();
  for (const capa of ["epicentros", "epicentros-halo"]) pon(capa, sismos);

  // LOS SISMOS MENORES OBEDECEN COMO TODO LO DEMAS.
  //
  // Se quedaban fuera del filtro: con "Colombia" puesto el mapa dejaba un
  // epicentro y seguian los diez menores repartidos por el continente.
  //
  // El primer intento fue apagar la capa entera al elegir pais, con la excusa
  // de que "de estos no se sabe de que pais son". Era falso: el pais estaba en
  // el dato desde el principio, al final del toponimo que publica USGS —"26 km
  // al OSO de Tocopilla, Chile"—. P1 lo publica ahora como `iso3`, y aqui se
  // filtra igual que los epicentros. Nueve de los diez observados de hoy tienen
  // pais; el decimo es "northern East Pacific Rise", mar abierto, y con un pais
  // elegido no aparece porque no es de ninguno.
  const menores = ["all"];
  if (estado.paisFiltrado) menores.push(["==", ["get", "iso3"], estado.paisFiltrado]);
  const diasSismos = (VENTANAS[estado.ventana] || VENTANAS.todo).dias;
  const corteSismos = corteDeVentana(diasSismos);
  if (corteSismos !== null) {
    menores.push([">=", ["get", "origen_utc"], new Date(corteSismos).toISOString()]);
  }
  pon("observados", menores.length > 1 ? menores : TODO_PASA);

  const fuego = filtroDeFocos();
  for (const capa of ["incendios", "incendios-punto", "incendios-borde"]) pon(capa, fuego);
}

//: Lleva la camara a lo que el filtro dejo. Solo cuando el filtro CAMBIA.
//:
//: Un filtro que recorta el mapa y no lo encuadra obliga a buscar a mano lo que
//: acaba de quedar: se elige Colombia, el mapa se queda con un epicentro, y hay
//: que ir a por el arrastrando desde una vista continental.
//:
//: Y solo al cambiar, no en cada repintado: `refrescarLista` corre tambien
//: cuando se mueve el mapa con "solo lo que se ve" puesto, y encuadrar ahi
//: pelearia con la mano del usuario en cada arrastre.
function encuadrarLoFiltrado() {
  if (!hayFiltros()) {
    // Sin filtros, la vista util es la region entera. Es la vuelta natural de
    // "Quitar filtros": lo contrario seria quedarse encerrado donde te dejo el
    // ultimo filtro.
    volverAlEncuadre(estado.mapa, VUELO);
    anotarCamara("panorama:sin-filtros");
    return;
  }

  if (estado.amenaza === "fuego") {
    const dentro = estado.focos.filter(
      (f) => enLaVentanaFuego(f) && (!estado.paisFuego || f.iso3 === estado.paisFuego)
    );
    const puntos = [];
    for (const f of dentro) {
      for (const h of f.h3s.slice(0, 4)) {
        try {
          const [lat, lng] = h3.cellToLatLng(h);
          puntos.push([lng, lat]);
        } catch (error) {
          /* una celda ilegible no impide encuadrar las demas */
        }
      }
    }
    if (encuadrarPuntos(puntos, { maxZoom: 8 })) anotarCamara("filtro:fuego");
    else devolverAlPanoramaVacio();
    return;
  }

  const puntos = [];
  for (const li of document.querySelectorAll("#lista-eventos li:not([hidden])")) {
    const lon = Number(li.dataset.lon);
    const lat = Number(li.dataset.lat);
    if (Number.isFinite(lon) && Number.isFinite(lat)) puntos.push([lon, lat]);
  }
  if (encuadrarPuntos(puntos, { maxZoom: 7 })) anotarCamara("filtro:sismos");
  else devolverAlPanoramaVacio();
}

//: UN FILTRO SIN RESULTADOS TAMBIEN MUEVE LA CAMARA.
//:
//: `encuadrarPuntos` devuelve `false` cuando no le queda ni un punto, y nadie
//: recogia ese `false`: la camara se quedaba donde la habia dejado el filtro
//: anterior. Medido en la pagina publicada: con Cuba + 90 dias el mapa se
//: quedaba mirando Venezuela y Colombia, vacio, sin un solo simbolo y sin
//: ningun aviso encima. Se lee como una pagina rota, no como un filtro que no
//: encontro nada.
//:
//: Volver a la region es la unica respuesta honesta: "aqui es donde habria algo
//: si lo hubiera".
function devolverAlPanoramaVacio() {
  volverAlEncuadre(estado.mapa, VUELO);
  anotarCamara("filtro:vacio");
}

//: Cuantos rasgos deja ver el filtro, para poder decirlo al lado del control.
//:
//: Un filtro que recorta el mapa sin decir cuanto quito obliga a contar
//: hexagonos a ojo — que es exactamente lo que la lista de focos vino a
//: eliminar.
function contarEnElMapa(capas) {
  const m = estado.mapa;
  if (!m || !m.queryRenderedFeatures) return null;
  const presentes = capas.filter((c) => m.getLayer(c));
  if (!presentes.length) return null;
  try {
    return m.queryRenderedFeatures({ layers: presentes }).length;
  } catch (error) {
    return null;
  }
}

//: Rellena un `<select>` y engancha su cambio. Los cuatro filtros son la misma
//: cosa con distintas opciones, y escribirla cuatro veces es como acaban
//: divergiendo: uno recuerda sincronizar el estado y otro no.
function poblarSelect(id, opciones, seleccionado, alCambiar) {
  const sel = $(id);
  if (!sel) return null;
  const html = opciones
    .map(
      ([valor, texto, cuenta]) =>
        '<option value="' +
        escapar(valor) +
        '">' +
        escapar(texto) +
        (Number.isFinite(cuenta) ? " (" + nf.format(cuenta) + ")" : "") +
        "</option>"
    )
    .join("");
  if (sel.innerHTML !== html) sel.innerHTML = html;
  sel.value = seleccionado;
  if (!sel.dataset.enganchado) {
    sel.dataset.enganchado = "1";
    sel.addEventListener("change", () => alCambiar(sel.value));
  }
  return sel;
}

//: Enseña u oculta el campo entero, etiqueta incluida.
//:
//: Ocultar solo el `<select>` dejaria su rotulo flotando —"País" sin nada al
//: lado—, que es peor que no tener el filtro.
function verCampo(id, visible) {
  const campo = $(id);
  if (campo) campo.hidden = !visible;
}

//: ¿Hay algun filtro puesto? Decide si se ofrece "Quitar filtros".
//:
//: Un boton de limpiar siempre visible no informa; visible solo cuando hay algo
//: que limpiar es ademas la senal de que un filtro esta actuando — que es justo
//: lo que se pierde de vista cuando los controles viven lejos del mapa.
function hayFiltros() {
  if (estado.soloEnVista) return true;
  return estado.amenaza === "fuego"
    ? Boolean(estado.paisFuego) || estado.ventanaFuego !== "h24"
    : Boolean(estado.paisFiltrado) || estado.ventana !== "todo";
}

//: Devuelve los desplegables a lo que dice el estado.
//:
//: `poblarSelect` ya lo hace al pintar, pero limpiar cambia el estado sin
//: repintar: sin esto el control se queda enseñando el filtro que acaba de
//: quitarse.
//: Un filtro acaba de cambiar. Es el UNICO sitio que encuadra.
//:
//: `refrescarLista` y `pintarListaFocos` corren tambien por otros motivos —al
//: mover el mapa con "solo lo que se ve" puesto, al cargar datos— y encuadrar
//: ahi pelearia con la mano del usuario en cada arrastre.
function filtroCambio() {
  if (estado.amenaza === "fuego") pintarListaFocos();
  else refrescarLista();
  // EL TABLERO TAMBIÉN. Es el punto por el que pasa cualquier cambio de filtro,
  // y hasta ahora movía la lista y el mapa dejando las cifras de arriba
  // quietas: «566.535 personas en celdas con fuego activo» seguía diciendo lo
  // de toda América Latina con Brasil seleccionado.
  refrescarTablero();
  encuadrarLoFiltrado();
  // Y la barra de direcciones, para que la vista filtrada se pueda mandar.
  escribirUrl();
}

function sincronizarFiltros() {
  if (estado.eventos && estado.nombresPais) {
    pintarFiltroPaises(estado.eventos, estado.nombresPais);
  }
  pintarControlesLista();
  if (estado.focos.length) pintarControlesFocos();
  pintarLimpiar();
}

//: Deja los filtros de la amenaza activa como al llegar.
//:
//: Vive suelta y no dentro del `click` de su boton porque ahora hay dos sitios
//: que la ofrecen: la barra de filtros y el aviso de "ningun reporte" del panel
//: lateral. Quien se queda sin resultados tiene que poder salir desde donde
//: esta mirando.
function quitarFiltros() {
  if (estado.amenaza === "fuego") {
    estado.paisFuego = "";
    estado.ventanaFuego = "h24";
  } else {
    estado.paisFiltrado = "";
    estado.ventana = "todo";
  }
  // La extensión se limpia en las dos amenazas: la casilla es una sola y
  // ahora filtra las dos. Dejarla marcada al "quitar filtros" era dejar un
  // filtro puesto con el botón diciendo que no queda ninguno.
  estado.soloEnVista = false;
  const casilla = $("solo-en-vista");
  if (casilla) casilla.checked = false;
  // Por `filtroCambio` y no repintando a mano: es el punto que mueve lista,
  // mapa Y tablero a la vez. Duplicarlo aquí es como se quedó el tablero
  // fuera del resto durante todo este tiempo.
  filtroCambio();
  // Los desplegables se repintan: limpiar el estado y dejar el control
  // enseñando "Colombia" es la misma divergencia que este visor persigue
  // entre lo que un control dice y lo que el sistema hace.
  sincronizarFiltros();
  anunciar("Filtros quitados.");
}

function pintarLimpiar() {
  const boton = $("limpiar-filtros");
  if (!boton) return;
  boton.hidden = !hayFiltros();
  if (!boton.dataset.enganchado) {
    boton.dataset.enganchado = "1";
    boton.addEventListener("click", () => quitarFiltros());
  }
}

function pintarFiltroPaises(eventos, nombres) {
  const cuenta = new Map();
  for (const e of eventos) {
    if (e.iso3) cuenta.set(e.iso3, (cuenta.get(e.iso3) || 0) + 1);
  }
  // Con un solo pais el filtro no filtra nada: es ruido con aspecto de control.
  verCampo("campo-pais", cuenta.size >= 2 && estado.amenaza !== "fuego");
  if (cuenta.size < 2) return;

  const orden = [...cuenta.entries()].sort(
    (a, b) => b[1] - a[1] || (nombres.get(a[0]) || a[0]).localeCompare(nombres.get(b[0]) || b[0], "es")
  );
  poblarSelect(
    "filtro-paises",
    // Sin cuenta en la opcion "todos": el numero que llevaba eran los REPORTES
    // —"Todos los países (21)" con quince paises en la lista—, y la fila ya
    // publica esa cifra en `#cuenta-lista`, a dos palmos. Las opciones de cada
    // pais si la llevan: ahi "(3)" son los reportes de ese pais y no hay con que
    // confundirla.
    [["", "Todos los países", null], ...orden.map(([iso, n]) => [iso, nombres.get(iso) || iso, n])],
    estado.paisFiltrado,
    (valor) => {
      estado.paisFiltrado = valor;
      filtroCambio();
    }
  );
}

function pintarControlesLista() {
  poblarSelect(
    "ventana-lista",
    Object.entries(VENTANAS).map(([clave, v]) => [clave, v.texto]),
    estado.ventana,
    (valor) => {
      estado.ventana = valor;
      filtroCambio();
    }
  );

  poblarSelect(
    "orden-lista",
    Object.entries(ORDENES).map(([clave, o]) => [clave, o.texto]),
    estado.orden,
    (valor) => {
      estado.orden = valor;
      refrescarLista();
    }
  );

  const etiqueta = $("etiqueta-en-vista");
  const interruptor = $("solo-en-vista");
  if (!etiqueta || !interruptor || !estado.mapa) return;
  // LA EXTENSION VALE PARA LAS DOS AMENAZAS.
  //
  // Estaba escondida en modo fuego, asi que mover el mapa no recortaba nada:
  // los focos y las cifras seguian siendo los de todo el continente mientras se
  // miraba una provincia. Es el filtro mas natural de un tablero de mapa —lo
  // que veo es de lo que me hablan— y era el unico que faltaba.
  etiqueta.hidden = false;
  if (!interruptor.dataset.enganchado) {
    interruptor.dataset.enganchado = "1";
    interruptor.addEventListener("change", () => {
      estado.soloEnVista = interruptor.checked;
      filtroCambio();
      pintarLimpiar();
    });
    // Mientras el recorte esta puesto, mover el mapa mueve la lista Y las
    // cifras. `moveend` y no `move`: rehacer las sumas en cada fotograma de un
    // desplazamiento es trabajo tirado, y solo se leen al soltar.
    estado.mapa.on("moveend", () => {
      if (!estado.soloEnVista) return;
      if (estado.amenaza === "fuego") {
        pintarListaFocos({ anunciando: false });
        refrescarTablero();
      } else {
        refrescarLista({ anunciando: false });
      }
    });
  }
}

function pintarControlesFocos() {
  poblarSelect(
    "ventana-focos",
    Object.entries(VENTANAS_FUEGO).map(([clave, v]) => [clave, v.texto]),
    estado.ventanaFuego,
    (valor) => {
      estado.ventanaFuego = valor;
      filtroCambio();
    }
  );

  poblarSelect(
    "orden-focos",
    Object.entries(ORDENES_FOCOS).map(([clave, o]) => [clave, o.texto]),
    estado.ordenFocos,
    (valor) => {
      estado.ordenFocos = valor;
      pintarListaFocos();
    }
  );

  // Solo los paises que de verdad tienen fuego ahora. Una lista de diecinueve
  // donde diecisiete no filtran nada es ruido con aspecto de control — la misma
  // regla que ya aplica el filtro de reportes.
  const cuenta = new Map();
  for (const f of estado.focos) {
    if (f.iso3) cuenta.set(f.iso3, (cuenta.get(f.iso3) || 0) + 1);
  }
  verCampo("campo-pais-fuego", cuenta.size >= 2 && estado.amenaza === "fuego");
  if (cuenta.size < 2) return;

  const orden = [...cuenta.entries()].sort(
    (a, b) => b[1] - a[1] || nombrePais(a[0]).localeCompare(nombrePais(b[0]), "es")
  );
  poblarSelect(
    "filtro-paises-fuego",
    // Igual que en sismos, y aqui ademas la cuenta era enganosa por partida
    // doble: los focos con pais suman 4.104 de 6.239, asi que "(6239)" no era ni
    // siquiera la suma de las opciones de debajo. `#cuenta-focos` lo dice.
    [["", "Todos los países", null], ...orden.map(([iso, n]) => [iso, nombrePais(iso), n])],
    estado.paisFuego,
    (valor) => {
      estado.paisFuego = valor;
      filtroCambio();
    }
  );
}

function incendiosAGeoJson(celdas) {
  if (typeof h3 === "undefined") return null;
  return {
    type: "FeatureCollection",
    features: celdas.map((c) => ({
      type: "Feature",
      // El `true` devuelve [lng, lat]. Sin el, los hexagonos aparecen en el
      // oceano Indico — mismo motivo que en `celdasAGeoJson`.
      geometry: { type: "Polygon", coordinates: [h3.cellToBoundary(c.h3, true)] },
      properties: c,
    })),
  };
}

function incendiosAPuntos(celdas) {
  if (typeof h3 === "undefined") return null;
  return {
    type: "FeatureCollection",
    features: celdas.map((c) => {
      const [lat, lng] = h3.cellToLatLng(c.h3);
      return { type: "Feature", geometry: { type: "Point", coordinates: [lng, lat] }, properties: c };
    }),
  };
}

function colorDeFuego() {
  return [
    "step",
    ["coalesce", ["get", "frp_suma"], 0],
    FUEGO_COLORES[0],
    ...FUEGO_CORTES.flatMap((corte, i) => [corte, FUEGO_COLORES[i + 1]]),
  ];
}

function dibujarIncendios(datos) {
  const m = estado.mapa;
  const geo = incendiosAGeoJson(datos.celdas);
  const puntos = incendiosAPuntos(datos.celdas);
  if (!m || !geo || !puntos) return;

  const pintar = () => {
    if (m.getSource("incendios")) return;
    // `tolerance: 0` desactiva la simplificacion de la fuente GeoJSON. Con el
    // valor por defecto (0,375) los hexagonos —que a zoom bajo son subpixel—
    // se colapsan y desaparecen antes incluso de llegar a dibujarse.
    m.addSource("incendios", { type: "geojson", data: geo, tolerance: 0 });
    m.addSource("incendios-puntos", { type: "geojson", data: puntos });

    // Debajo de los epicentros, no encima. El fuego son miles de simbolos y
    // los sismos son veintiuno: sin este orden, la capa continental entierra
    // justo lo que este sistema existe para publicar.
    const antes = m.getLayer("epicentros-halo") ? "epicentros-halo" : primeraEtiqueta(m);
    m.addLayer(
      {
        id: "incendios-punto",
        type: "circle",
        source: "incendios-puntos",
        maxzoom: FUEGO_ZOOM_HEX,
        layout: {
          visibility: "none",
          // EL FUEGO FUERTE SE DIBUJA ENCIMA.
          //
          // Sin esto gana el que venga despues en el fichero. Medido a zoom 2:
          // el 69 % de las celdas cae sobre un pixel ya ocupado, y **las 150
          // mas energeticas comparten pixel con otra sin una sola excepcion**.
          // Los quince focos de mas de 1.000 MW —lo que este mapa existe para
          // enseñar— se sorteaban contra 12.752 competidores.
          "circle-sort-key": ["coalesce", ["get", "frp_suma"], 0],
        },
        paint: {
          // EL TAMAÑO LO LLEVA LA ENERGIA, Y LA TINTA TIENE QUE CABER.
          //
          // El radio iba de 3 a 5,5 px —1,8 veces— para un rango de energia de
          // 350. Con 12.767 simbolos eso son 413.000 px² de tinta sobre una
          // franja util de 335.000: **1,23 veces el lienzo entero**. La mancha
          // no era mala suerte, era aritmetica. Y las 5.221 celdas mas debiles
          // —≤10 MW, que juntas no llegan al 1 % de la energia— ponian once
          // veces mas tinta que las 150 mas fuertes.
          //
          // Raiz cuadrada del FRP, que es como se escala un simbolo
          // proporcional: el AREA del circulo sigue a la energia, no el radio.
          // Con suelo de 0,8 px, para que una celda debil sea polvo y no
          // desaparezca. Resultado medido: 117.000 px² de tinta, 0,35 veces el
          // lienzo, y la proporcion debiles:fuertes baja de 10,9:1 a 2,0:1.
          "circle-radius": [
            "interpolate", ["linear"], ["zoom"],
            2, ["+", 0.8, ["*", 0.16, ["sqrt", ["coalesce", ["get", "frp_suma"], 0]]]],
            5, ["+", 1.2, ["*", 0.30, ["sqrt", ["coalesce", ["get", "frp_suma"], 0]]]],
            8, ["+", 2.5, ["*", 0.55, ["sqrt", ["coalesce", ["get", "frp_suma"], 0]]]],
          ],
          "circle-color": colorDeFuego(),
          // La clase mas debil, translucida. Sigue estando —no se oculta nada—
          // y deja de competir: se lee como la textura de fondo que es.
          "circle-opacity": [
            "step", ["coalesce", ["get", "frp_suma"], 0],
            0.4, 10, 0.65, 50, 0.88,
          ],
          // EL CONTORNO SOLO CUANDO EL SIMBOLO DA PARA TENERLO.
          //
          // Con radio 2 px, un contorno de 1 px **es** el simbolo: se comia el
          // relleno —justo lo que lleva el color— y los contornos solapados
          // tejian una malla oscura que era la mancha que se veia. A zoom
          // cercano, donde los circulos son grandes y pocos, sigue separando
          // los que se tocan, que es para lo que estaba.
          "circle-stroke-color": FUEGO_CONTORNO,
          "circle-stroke-width": ["interpolate", ["linear"], ["zoom"], 5, 0, 7, 0.8],
          "circle-stroke-opacity": 0.85,
        },
      },
      antes
    );
    m.addLayer(
      {
        id: "incendios",
        type: "fill",
        source: "incendios",
        minzoom: FUEGO_ZOOM_HEX,
        layout: { visibility: "none" },
        paint: { "fill-color": colorDeFuego(), "fill-opacity": 0.75 },
      },
      antes
    );
    m.addLayer(
      {
        id: "incendios-borde",
        type: "line",
        source: "incendios",
        minzoom: FUEGO_ZOOM_HEX,
        layout: { visibility: "none" },
        paint: { "line-color": FUEGO_CONTORNO, "line-width": 0.6, "line-opacity": 0.55 },
      },
      antes
    );

    // Las dos representaciones son clicables: si solo lo fuera el hexagono, a
    // escala continental —que es donde se mira esta capa— no se podria abrir
    // ninguna celda.
    // Se anotan los puntos y no los hexagonos: los hexagonos solo existen por
    // encima de FUEGO_ZOOM_HEX, asi que a zoom continental —que es como se abre
    // el visor— contar hexagonos daria cero con la capa perfectamente dibujada.
    anotarPintado("incendios", puntos.features.length);
    aplicarAmenaza();

    for (const capa of ["incendios", "incendios-punto"]) {
      m.on("mouseenter", capa, () => (m.getCanvas().style.cursor = "pointer"));
      m.on("mouseleave", capa, () => (m.getCanvas().style.cursor = ""));
      m.on("click", capa, (ev) => {
        const props = ev.features[0].properties;
        // El foco manda sobre la celda: la pregunta al pulsar fuego es "¿que
        // tan grande es esto?", y una celda suelta no la responde. El globo se
        // queda para la celda exacta, que sigue siendo el dato mas fino.
        const foco = focoDeCelda(props.h3);
        // Las dos cosas, y no una: el panel responde "¿que tan grande es este
        // incendio?" y el globo "¿que hay en la celda que acabo de pulsar?".
        // Quitar el globo al anadir el panel habria cambiado una carencia por
        // otra — el identificador H3 y las cifras de la celda exacta no viven
        // en ningun otro sitio del visor.
        if (foco) abrirFoco(foco);
        abrirGlobo(new maplibregl.Popup({ closeButton: true, maxWidth: "320px" }))
          .setLngLat(ev.lngLat)
          .setHTML(cuadroDeIncendio(props))
          .addTo(m);
      });
    }
  };

  cuandoElEstiloEsteListo(m, pintar);
}

//: Abre el detalle de un foco: panel, perimetro y encuadre.
//:
//: Mismo trato que un sismo, y a proposito. El selector de amenaza prometio dos
//: amenazas de primera clase sobre el mismo activo; mientras una tuviera panel,
//: area y perimetro y la otra solo un globo, la promesa estaba a medias.
function abrirFoco(foco) {
  if (!foco) return;
  estado.focoAbierto = foco;
  // Sin `cerrarGlobo()` aqui: el clic abre panel Y globo, y cerrarlo desde el
  // panel mataria el globo que el mismo clic acaba de pedir.

  $("lateral-vacio").hidden = true;
  $("lateral-detalle").hidden = true;
  const caja = $("detalle-fuego");
  caja.hidden = false;

  $("fuego-titulo").textContent =
    foco.nCeldas === 1 ? "Una celda con fuego activo" : `${numero(foco.nCeldas)} celdas contiguas ardiendo`;
  $("fuego-meta").textContent =
    `Detectado ${comoFecha(foco.primeraUtc)} · último paso ${comoFecha(foco.ultimaUtc)}`;

  $("fuego-area").innerHTML =
    `<p class="cifra-area"><strong>${areaDeFoco(foco.areaKm2)}</strong> km²</p>` +
    `<p class="apunte">${numero(foco.nCeldas)} celda${foco.nCeldas === 1 ? "" : "s"} de ` +
    `${numero(AREA_CELDA_FUEGO_KM2, 2)} km²</p>`;

  // El cero se omite en vez de imprimirse. Una celda sin poblacion puede estar
  // fuera de los paises con activo construido, y "0 personas" ahi se leeria
  // como medicion cuando es ausencia de medida. Es la misma regla del globo.
  const expuesto = [
    ["personas", foco.pop, "personas"],
    ["edificaciones", foco.bld, "edificaciones"],
    ["sedes de salud", foco.salud, "salud"],
    ["sedes educativas", foco.edu, "educacion"],
  ].filter(([, n]) => Number(n) > 0);

  $("fuego-metricas").innerHTML = expuesto.length
    ? expuesto
        .map(
          ([nombre, n, icono]) =>
            `<div class="metrica"><span class="cabeza">${icono ? iconoSvg(icono) : ""}` +
            `<span class="valor">${comoConteo(n)}</span></span>` +
            `<span class="etiqueta">${nombre}</span></div>`
        )
        .join("")
    : `<div class="metrica"><span class="etiqueta">Sin exposición medida en estas celdas. ` +
      `Puede que no haya nadie, o que caigan fuera de los países con activo construido.</span></div>`;

  const reparto = Object.entries(foco.suelo)
    .filter(([, pct]) => pct >= 1)
    .sort((a, b) => b[1] - a[1]);
  $("bloque-fuego-suelo").hidden = !reparto.length;
  if (reparto.length) {
    $("fuego-suelo").innerHTML = reparto
      .map(
        ([nombre, pct]) =>
          `<li><span class="suelo-nombre">${iconoSvg(nombre)}${nombre}</span>` +
          `<span class="suelo-barra"><span style="width:${Math.min(100, pct)}%"></span></span>` +
          `<span class="suelo-pct">${numero(pct)}&nbsp;%</span></li>`
      )
      .join("");
  }

  // SIN VIENTO NO HAY BLOQUE, NI SIQUIERA SU TITULO.
  //
  // `cuadroDeViento` devuelve cadena vacia cuando GFS no cubre el foco, y eso
  // esta bien —un cero ahi diria "no hace viento" cuando lo que pasa es que no
  // se midio—. Pero el `<section>` se quedaba en pie con su rotulo «Ambiente» y
  // su parrafo sobre el modelo NOAA, y debajo nada: se lee como un fallo de
  // carga y no como una ausencia de dato.
  //
  // **Con el fichero de hoy no pasa**: los 3.337 puntos de la rejilla cubren
  // los 6.239 focos, ninguno a mas de medio grado. Esto es la guarda para
  // cuando GFS falle —`p5_incendios/viento.py` reintenta cuatro corridas y
  // puede rendirse— que es exactamente el caso que el comentario del HTML ya
  // anticipaba y que nadie habia cubierto.
  const ambiente = cuadroDeViento(vientoDelFoco(foco));
  $("fuego-ambiente").innerHTML = ambiente;
  const bloqueAmbiente = $("bloque-fuego-ambiente");
  if (bloqueAmbiente) bloqueAmbiente.hidden = !ambiente;

  $("fuego-deteccion").innerHTML =
    `<div class="metrica"><span class="cabeza">${iconoSvg("detecciones")}` +
    `<span class="valor">${numero(foco.detecciones)}</span></span>` +
    `<span class="etiqueta">detecciones en 24 h</span></div>` +
    `<div class="metrica"><span class="cabeza">${iconoSvg("potencia")}` +
    `<span class="valor">${numero(Math.round(foco.frpSuma))}</span></span>` +
    `<span class="etiqueta">MW de potencia radiativa</span></div>` +
    (foco.brilloMaxK > 0
      ? `<div class="metrica"><span class="cabeza">${iconoSvg("temperatura")}` +
        `<span class="valor">${numero(foco.brilloMaxK)}</span></span>` +
        `<span class="etiqueta">K de temperatura de brillo</span>` +
        `<span class="apunte">Del píxel de 375&nbsp;m, no de la llama</span></div>`
      : "");

  $("fuego-apostilla").textContent =
    `Una detección no es un incendio: tres satélites sobre el mismo fuego producen tres ` +
    `detecciones. No se estima área quemada — el propio FIRMS lo desaconseja.` +
    (foco.deteccionesBaja > 0
      ? ` ${numero(foco.deteccionesBaja)} detecciones de baja confianza no se cuentan.`
      : "") +
    (foco.celdasConSuelo < foco.nCeldas
      ? ` ${numero(foco.nCeldas - foco.celdasConSuelo)} de ${numero(foco.nCeldas)} celdas sin cobertura del suelo conocida.`
      : "");

  dibujarPerimetroDeFoco(foco);
  volarAlFoco(foco);
  $("lateral").focus();
  anunciar(
    `Foco de ${numero(foco.nCeldas)} celdas, ${areaDeFoco(foco.areaKm2)} kilómetros cuadrados. ` +
      (foco.pop > 0 ? `${numero(Math.round(foco.pop))} personas expuestas.` : "Sin exposición medida.")
  );
}

function conectarVolverDelFoco() {
  const boton = $("volver-fuego");
  if (boton) boton.addEventListener("click", () => cerrarFoco({ devolverLaVista: true }));
}

function cerrarFoco({ devolverLaVista = false } = {}) {
  estado.focoAbierto = null;
  const caja = $("detalle-fuego");
  if (caja) caja.hidden = true;
  quitarPerimetroDeFoco();
  // SIN CONDICION DE MODO, Y ES EL FALLO QUE ESTO ARREGLA.
  //
  // La llevaba (`amenaza === "fuego"`), y al cambiar a sismos `aplicarAmenaza`
  // llama aqui **despues** de haber cambiado el modo: la condicion ya era falsa,
  // el panel de vacio no se restauraba, y volver a fuego daba un lateral en
  // blanco. Lo unico que decide si se ve el panorama es si hay un evento
  // abierto; el modo ya decide, aparte, que hay dentro de el.
  if (!estado.seleccionado) {
    const vacio = $("lateral-vacio");
    if (vacio) vacio.hidden = false;
  }
  // Y LA CAMARA VUELVE, como en "Volver al panorama" de un sismo.
  //
  // No volvia. El boton dice "Volver a los focos" —en plural— y dejaba la vista
  // clavada sobre el unico foco que se acababa de cerrar, a cinco kilometros de
  // escala. El panel decia una cosa y el mapa otra.
  //
  // Solo cuando lo pide el propio boton: `aplicarAmenaza` tambien llama aqui al
  // cambiar de modo, y ahi la camara la gobierna el cambio de amenaza.
  if (devolverLaVista) {
    volverAlEncuadre(estado.mapa, VUELO);
    anotarCamara("panorama:volver-a-los-focos");
  }
}

function quitarPerimetroDeFoco() {
  const m = estado.mapa;
  if (!m || !m.getSource) return;
  for (const capa of ["foco-perimetro", "foco-perimetro-borde"]) {
    if (m.getLayer(capa)) m.removeLayer(capa);
  }
  if (m.getSource("foco-perimetro")) m.removeSource("foco-perimetro");
}

//: El perimetro del foco, con la misma tinta que el del sismo.
//:
//: Oscuro con funda blanca, no el color de la rampa: sobre su propio relleno
//: magenta un borde magenta es invisible. Ya se aprendio con las bandas MMI.
function dibujarPerimetroDeFoco(foco) {
  const m = estado.mapa;
  if (!m || typeof h3 === "undefined") return;
  // `addSource` LANZA si el estilo no ha terminado de cargar —"Style is not
  // done loading"—, y quien pulsa un foco nada mas abrir la pagina cae justo
  // ahi. No se salta el dibujo: se difiere, que es lo que hace la pieza que
  // este repositorio ya tiene para esto. Saltarlo dejaria el panel hablando de
  // un area que el mapa no rodea.
  cuandoElEstiloEsteListo(m, () => pintarPerimetroDeFoco(m, foco));
}

function pintarPerimetroDeFoco(m, foco) {
  quitarPerimetroDeFoco();
  let poligonos;
  try {
    poligonos = h3.cellsToMultiPolygon(foco.h3s, true);
  } catch (error) {
    console.warn("perimetro del foco:", error && error.message);
    return;
  }
  if (!poligonos || !poligonos.length) return;

  m.addSource("foco-perimetro", {
    type: "geojson",
    data: {
      type: "FeatureCollection",
      features: [{ type: "Feature", properties: {}, geometry: { type: "MultiPolygon", coordinates: poligonos } }],
    },
  });
  m.addLayer({
    id: "foco-perimetro-borde",
    type: "line",
    source: "foco-perimetro",
    paint: { "line-color": "#ffffff", "line-width": 4, "line-opacity": 0.9 },
  });
  m.addLayer({
    id: "foco-perimetro",
    type: "line",
    source: "foco-perimetro",
    paint: { "line-color": "#1c1b1a", "line-width": 1.6 },
  });
  anotarPintado("foco-perimetro", foco.nCeldas);
}

//: Encuadra un punado de puntos sueltos, con margen y un tope de acercamiento.
//:
//: `volarAlFoco` hace lo mismo para las celdas de un incendio; esto es para
//: cosas que no son poligonos —los epicentros observados— y necesita el tope:
//: nueve sismos repartidos por el continente dan una caja enorme, pero dos que
//: caigan a diez kilometros darian un zoom de calle sobre dos estrellas.
function encuadrarPuntos(coords, { maxZoom = 6 } = {}) {
  const m = estado.mapa;
  if (!m || !Array.isArray(coords) || !coords.length) return false;
  let lo = 180,
    la = 90,
    LO = -180,
    LA = -90;
  for (const [lon, lat] of coords) {
    if (!Number.isFinite(lon) || !Number.isFinite(lat)) continue;
    if (lon < lo) lo = lon;
    if (lon > LO) LO = lon;
    if (lat < la) la = lat;
    if (lat > LA) LA = lat;
  }
  if (lo > LO || la > LA) return false;
  try {
    m.fitBounds(
      [
        [lo, la],
        [LO, LA],
      ],
      { padding: 80, maxZoom, duration: VUELO }
    );
  } catch (error) {
    console.warn("encuadre:", error && error.message);
    return false;
  }
  return true;
}

// --- Viento: hacia donde empuja ---------------------------------------------
//
// El panel decia cuanto arde y sobre quien, y no hacia donde va. Es la
// diferencia entre un contador y algo con lo que se decide.
//
// El dato llega como reticula y no dentro de cada celda, y eso es a proposito:
// GFS va a 0,25 grados —unos 27 km— y una celda H3 son 5 km2, asi que decenas
// comparten el mismo punto. Verlo como puntos separados es ver la resolucion
// que de verdad hay.

//: Los ocho rumbos, para escribir al lado de la flecha.
//:
//: Una flecha sola se lee mal —sobre todo girada— y aqui leerla al reves
//: significa alejarse en la direccion equivocada. El texto no es redundancia.
const RUMBOS = ["norte", "nordeste", "este", "sureste", "sur", "suroeste", "oeste", "noroeste"];

function nombreDeRumbo(grados) {
  return RUMBOS[Math.round(((grados % 360) + 360) % 360 / 45) % 8];
}

//: El punto de reticula mas cercano al centro del foco.
//:
//: No interpola, igual que el pipeline: con 27 km de paso, interpolar daria una
//: precision aparente que el dato no tiene.
function vientoDelFoco(foco) {
  const rejilla = estado.fuegoDatos && estado.fuegoDatos.viento;
  if (!rejilla || !rejilla.puntos || !rejilla.puntos.length) return null;
  if (typeof h3 === "undefined" || !foco.h3s || !foco.h3s.length) return null;

  let lat = 0;
  let lon = 0;
  for (const h of foco.h3s) {
    const [a, b] = h3.cellToLatLng(h);
    lat += a;
    lon += b;
  }
  lat /= foco.h3s.length;
  lon /= foco.h3s.length;

  let mejor = null;
  let cerca = Infinity;
  for (const p of rejilla.puntos) {
    const d = (p.lat - lat) ** 2 + (p.lon - lon) ** 2;
    if (d < cerca) {
      cerca = d;
      mejor = p;
    }
  }
  // Mas de medio grado de separacion ya no describe este foco: es un punto de
  // otra parte. Antes que un viento ajeno, ninguno.
  return mejor && cerca <= 0.5 ** 2 ? mejor : null;
}

function cuadroDeViento(p) {
  if (!p) return "";

  // LA FLECHA APUNTA A DONDE EMPUJA, NO DE DONDE VIENE.
  //
  // `dir_grados` es la convencion meteorologica: de donde sopla. Un viento de
  // 90 grados —del este— empuja hacia el oeste. La flecha del icono mira al
  // norte en reposo, asi que hay que girarla `dir + 180`.
  const empuja = (p.dir_grados + 180) % 360;
  const kmh = Math.round(p.vel_ms * 3.6);

  return (
    `<div class="metrica"><span class="cabeza">` +
    `<span class="rosa" style="transform:rotate(${empuja}deg)">${iconoSvg("viento")}</span>` +
    `<span class="valor">${numero(kmh)}</span></span>` +
    `<span class="etiqueta">km/h, empuja hacia el ${nombreDeRumbo(empuja)}</span>` +
    // EL ROTULO ANTERIOR NO SE ENTENDIA, Y HAY EVIDENCIA: decia "Del modelo GFS
    // a 27 km, no medido en la celda" y quien conoce el sistema por dentro tuvo
    // que preguntar que significaba. Metia dos ideas en ocho palabras —que es
    // modelado y que la malla es gruesa— y no transmitia ninguna.
    //
    // Ahora van en el orden en que importan: primero que es de la zona y de un
    // modelo, despues el detalle tecnico.
    `<span class="apunte">Viento de la zona según modelo, no medido en el incendio` +
    ` · malla de 27&nbsp;km</span></div>` +
    (p.hr_pct >= 0
      ? `<div class="metrica"><span class="cabeza">${iconoSvg("humedad")}` +
        `<span class="valor">${numero(Math.round(p.hr_pct))}</span></span>` +
        `<span class="etiqueta">% de humedad relativa</span></div>`
      : "")
  );
}

function volarAlFoco(foco) {
  const m = estado.mapa;
  if (!m || typeof h3 === "undefined") return;
  let m1 = 90, m2 = -90, n1 = 180, n2 = -180;
  for (const h of foco.h3s) {
    for (const [lat, lng] of h3.cellToBoundary(h)) {
      if (lat < m1) m1 = lat;
      if (lat > m2) m2 = lat;
      if (lng < n1) n1 = lng;
      if (lng > n2) n2 = lng;
    }
  }
  if (m1 > m2) return;
  m.fitBounds(
    [
      [n1, m1],
      [n2, m2],
    ],
    { padding: 90, maxZoom: 10, duration: REDUCIR_MOVIMIENTO ? 0 : 900 }
  );
}

//: De la celda pulsada a su foco. Sin el indice, habria que recorrer los focos.
function focoDeCelda(h3id) {
  return (estado.focosPorCelda && estado.focosPorCelda.get(h3id)) || null;
}

//: Abrir el foco n-esimo por tamano. Existe para las pruebas de navegador.
//:
//: Acertar con el raton un hexagono concreto entre cuatro mil, en tres tamanos
//: de pantalla y con la camara donde la deje el encuadre, es una prueba que
//: falla por motivos que no son el fallo que busca. Esto abre exactamente el
//: mismo camino que el clic —`abrirFoco`— sin la loteria del pixel.
function abrirFocoDePrueba(indice = 0) {
  const ordenados = [...estado.focos].sort((a, b) => b.nCeldas - a.nCeldas);
  const foco = ordenados[indice];
  if (!foco) return null;
  abrirFoco(foco);
  return { celdas: foco.nCeldas, areaKm2: foco.areaKm2, pop: foco.pop };
}

function cuadroDeIncendio(p) {
  const suelo = [
    ["arbolado", p.arbolado_pct],
    ["pastizal", p.pastizal_pct],
    ["cultivo", p.cultivo_pct],
    ["humedal", p.humedal_pct],
  ]
    .filter(([, v]) => Number(v) >= 5)
    .map(([n, v]) => `${n} ${numero(Number(v))}&nbsp;%`)
    .join(" · ");

  // La poblacion se omite si es cero en vez de imprimir "0 personas": puede ser
  // que no haya nadie, o que la celda caiga en un pais sin activo cargado. Un
  // cero ahi se leeria como medicion, y no lo es.
  const filas = [
    ["Detecciones (24 h)", numero(p.detecciones)],
    ["Potencia radiativa", `${numero(p.frp_suma)}&nbsp;MW`],
    // En kelvin, que es como lo publica FIRMS, y no convertido a grados.
    // "94 °C" invita a leer "el fuego esta tibio" cuando lo que dice es que la
    // llama ocupa una fraccion pequeña de un pixel de 375 m: el rango real de
    // esta cifra va de 26 a 94 °C mientras el fuego arde a 600 o mas. El kelvin
    // no se lee solo, y eso aqui es una ventaja.
    p.brillo_max_k > 0 ? ["Temperatura de brillo", `${numero(p.brillo_max_k)}&nbsp;K`] : null,
    p.pop > 0 ? ["Población", numero(p.pop)] : null,
    p.bld > 0 ? ["Edificios", numero(p.bld)] : null,
    p.salud > 0 ? ["Salud", numero(p.salud)] : null,
    p.edu > 0 ? ["Educación", numero(p.edu)] : null,
    suelo ? ["Suelo", suelo] : null,
  ].filter(Boolean);

  return (
    `<div class="popup-incendio">` +
    `<p class="eyebrow">Celda con fuego activo</p>` +
    `<table>${filas
      .map(([k, v]) => `<tr><th>${escapar(k)}</th><td>${v}</td></tr>`)
      .join("")}</table>` +
    `<p class="mono menor">${escapar(p.h3)}</p>` +
    `<p class="nota-incendio">Detecciones de satélite, no área quemada. ` +
    `${p.brillo_max_k > 0 ? "La temperatura es la del píxel de 375&nbsp;m, no la de la llama: mezcla el fuego con el terreno frío de alrededor. " : ""}` +
    `${p.detecciones_baja > 0 ? `${numero(p.detecciones_baja)} de baja confianza no contadas. ` : ""}` +
    `Último paso: ${escapar(comoFecha(p.ultima_utc))}.</p>` +
    `</div>`
  );
}

//: Cuantas celdas hay y cuantas se dibujan, que no son la misma cifra.
//:
//: DESDE EL 31-AGO-2026 YA NO SE RECORTA: `p5_incendios` publica todas las
//: celdas. `recortado` se queda en falso solo y la casilla dice el total, que
//: ahora si es lo que hay en el mapa.
//:
//: El recorte existio porque se creia que publicarlo todo eran "varios
//: megabytes que el visor descarga en cada carga". Era falso —GitHub Pages
//: sirve comprimido: 203 KB con las 13.031 celdas, contra 136 con 4.000— y
//: nadie lo habia medido. Se deja el campo y esta rama porque queda un tope de
//: seguridad para una temporada catastrofica; el dia que muerda, el visor tiene
//: que poder decirlo.
//:
//: Lo que arreglo en su dia sigue valiendo: el visor no leia `celdas_publicadas`
//: y rotulaba la casilla con el total mientras encendia una capa con el
//: recorte. Medido el 28-ago-2026: «Focos activos (15.607 celdas en 24 h)»
//: sobre un mapa con 4.000, y lo mismo por el lector de pantalla.
//:
//: Las cifras de la tarjeta «ahora mismo» —personas, sedes, reparto del suelo—
//: se quedan como estan: esas si son de todas las celdas, y recortarlas para
//: que cuadren con el mapa seria publicar una cifra falsa por comodidad.
function celdasDeFuego(totales) {
  const t = totales || {};
  const total = Number(t.celdas) || 0;
  const dibujadas = Number.isFinite(t.celdas_publicadas) ? t.celdas_publicadas : total;
  return {
    total,
    dibujadas,
    recortado: dibujadas > 0 && dibujadas < total,
    comoTexto: miles,
  };
}

//: Rotulos de la rampa, en el hueco grande de la leyenda — el mismo que usan
//: las variables de la malla. Antes vivian en una tarjeta de esquina que solo
//: aparecia si alguien encontraba el checkbox; en modo fuego la leyenda ES la
//: del fuego, con el mismo derecho que la de intensidad en modo sismos.
function pintarLeyendaFuego(datos) {
  const { total, dibujadas, recortado, comoTexto: mil } = celdasDeFuego(datos && datos.totales);

  $("leyenda").hidden = false;
  $("leyenda-titulo").textContent = "Potencia radiativa · MW";
  $("leyenda-escala").innerHTML = FUEGO_COLORES.map((color, i) => {
    const desde = i === 0 ? 0 : FUEGO_CORTES[i - 1];
    const hasta = FUEGO_CORTES[i];
    const texto = hasta ? `${numero(desde)} – ${numero(hasta)}` : `${numero(desde)} o más`;
    return (
      `<li><span class="muestra" style="background:${color}"></span>` +
      `<span class="leyenda-valor">${texto}</span></li>`
    );
  }).join("");

  const corte = recortado
    ? ` Se dibujan ${mil(dibujadas)} de ${mil(total)} celdas: primero todas las ` +
      `que tienen gente debajo, y el resto por energía.`
    : "";
  $("leyenda-nota").textContent =
    "Energía medida por satélite en 24 h. No es área quemada: el propio FIRMS " +
    "desaconseja estimarla desde detecciones. A escala continental el círculo " +
    "crece con la raíz de esa energía, así que su área la sigue de frente: un " +
    "punto pequeño es una detección débil, no una lejana." + corte;
}

// --- Lo que el sistema esta viendo ahora ------------------------------------
//
// El panorama contaba el archivo: veintiun reportes, quince paises. Cierto y
// muerto. Un sistema de vigilancia que solo enseña su historial se lee como un
// archivo historico, y lo que separa a este de un PDF es que **esta mirando
// ahora mismo**.
//
// Las cifras de aqui son las unicas del visor que cambian entre una visita y la
// siguiente. Por eso van arriba y por eso llevan la hora de la ultima revision:
// sin ella, "14.984 celdas con fuego" podria ser de hace un mes.
// --- El tablero se cruza con los filtros ------------------------------------
//
// Hasta ahora las cifras de la tarjeta «ahora mismo» —personas, sedes de salud,
// sedes educativas, sobre qué arde— salían tal cual del bloque `totales` del
// JSON: sumas que calcula el pipeline sobre TODAS las celdas. No se recalculaban
// nunca. Elegir Brasil recortaba la lista y el mapa, y las cifras de arriba
// seguían diciendo las de América Latina entera.
//
// Es peor que un despiste: el número y el mapa contaban cosas distintas a la
// vez, que es la misma clase de contradicción que el selector de amenaza existe
// para evitar.
//
// AHORA SE PUEDE HACER BIEN PORQUE SE PUBLICAN TODAS LAS CELDAS. Mientras el
// fichero traía 4.000 de 13.031, recalcular en el cliente habría dado «las
// cifras de la parte que cupo» — un error más discreto y por eso peor. Con el
// dato completo, filtrar y sumar da exactamente lo mismo que sumaría el
// pipeline.

//: Las celdas que pasan los filtros de ahora mismo. **Una sola definición**,
//: de la que dependen las cifras, la lista y el encuadre.
//:
//: Tener dos sitios que deciden qué entra es como se acaba con la lista
//: filtrada y el indicador sin filtrar, que es justo lo que había.
function celdasDeFuegoFiltradas() {
  const datos = estado.fuegoDatos;
  const todas = (datos && datos.celdas) || [];
  if (!todas.length) return [];

  const horas = (VENTANAS_FUEGO[estado.ventanaFuego] || VENTANAS_FUEGO.h24).horas;
  const corte = new Date(referenciaDelFuego() - horas * 3600000).toISOString();
  const iso = estado.paisFuego;
  const caja = estado.soloEnVista ? encuadreActual() : null;

  return todas.filter((c) => {
    if (iso && c.iso3 !== iso) return false;
    // Se compara como cadena ISO, igual que el filtro del mapa: son sellos
    // UTC, que ordenan igual como texto que como instante. Comparar aquí de
    // una forma y allí de otra es como divergen.
    if (c.ultima_utc && c.ultima_utc < corte) return false;
    if (caja) {
      const centro = estado.centrosDeCelda && estado.centrosDeCelda.get(c.h3);
      if (!centro) return false;
      const [lat, lon] = centro;
      if (lat < caja.sur || lat > caja.norte || lon < caja.oeste || lon > caja.este) return false;
    }
    return true;
  });
}

//: La caja que se ve en el mapa, o `null` si no hay mapa todavía.
function encuadreActual() {
  const m = estado.mapa;
  if (!m || !m.getBounds) return null;
  try {
    const b = m.getBounds();
    return { sur: b.getSouth(), norte: b.getNorth(), oeste: b.getWest(), este: b.getEast() };
  } catch (error) {
    return null;
  }
}

//: Los centros de las celdas, calculados **una vez** al cargar.
//:
//: El filtro por extensión los necesita en cada movimiento del mapa. Llamar a
//: `h3.cellToLatLng` trece mil veces por cada arrastre convertiría el filtro en
//: un tirón; una vez al cargar no se nota.
function indexarCentros(celdas) {
  const centros = new Map();
  if (typeof h3 === "undefined") return centros;
  for (const c of celdas) {
    try {
      centros.set(c.h3, h3.cellToLatLng(c.h3));
    } catch (error) {
      // Una celda con identificador ilegible no puede tumbar el indexado de las
      // otras doce mil; simplemente no se podrá filtrar por extensión.
    }
  }
  return centros;
}

//: Recalcula las cifras del tablero desde una lista de celdas.
//:
//: Reproduce lo que hace `build_incendios` en el pipeline, y hay una prueba de
//: que sin filtros da EXACTAMENTE lo mismo que el bloque `totales` publicado.
//: Sin esa prueba, dos implementaciones de la misma suma divergen sin avisar.
function totalesDeFuego(celdas) {
  const suma = (campo) => celdas.reduce((t, c) => t + (Number(c[campo]) || 0), 0);

  // Solo las celdas con cobertura conocida entran en el reparto del suelo: las
  // demás no son «cero por ciento arbolado», son «sin medir».
  const clases = ["arbolado", "pastizal", "cultivo", "humedal"];
  const conSuelo = celdas.filter((c) => clases.some((k) => Number(c[`${k}_pct`]) > 0));
  const energia = conSuelo.reduce((t, c) => t + (Number(c.frp_suma) || 0), 0);
  const suelo = {};
  if (energia > 0) {
    for (const clase of clases) {
      const pct =
        conSuelo.reduce(
          (t, c) => t + ((Number(c[`${clase}_pct`]) || 0) / 100) * (Number(c.frp_suma) || 0),
          0
        ) / energia;
      suelo[clase] = Math.round(pct * 1000) / 10;
    }
  }
  suelo.celdas_medidas = conSuelo.length;
  suelo.celdas_sin_medir = celdas.length - conSuelo.length;

  return {
    celdas: celdas.length,
    detecciones: suma("detecciones"),
    detecciones_baja: suma("detecciones_baja"),
    celdas_con_poblacion: celdas.filter((c) => Number(c.pop) > 0).length,
    pop_en_celdas_con_fuego: Math.round(suma("pop")),
    salud_en_celdas_con_fuego: suma("salud"),
    edu_en_celdas_con_fuego: suma("edu"),
    bld_en_celdas_con_fuego: suma("bld"),
    frp_total_mw: Math.round(suma("frp_suma") * 10) / 10,
    suelo,
  };
}

//: De qué habla la cifra, en palabras.
//:
//: Antes era la constante «En toda América Latina», que era cierta porque nada
//: se filtraba. Ahora que las cifras se cruzan, un rótulo fijo sería peor que
//: no tenerlo: diría «toda América Latina» debajo del número de Brasil.
function alcanceDelFuego() {
  const partes = [];
  partes.push(estado.paisFuego ? `En ${nombrePais(estado.paisFuego)}` : "En toda América Latina");
  if (estado.soloEnVista) partes.push("dentro del encuadre");
  // Cuántas quedaron fuera del filtro. Decir «1.240 celdas» sin decir de
  // cuántas convierte un recorte en un total.
  const todas = estado.vivo && estado.vivo.celdasTotales;
  const vistas = estado.vivo && estado.vivo.incendios && estado.vivo.incendios.celdas;
  if (todas && vistas && vistas < todas) partes.push(`de ${numero(todas)} en total`);
  // Y si el fichero llegó recortado en origen, lo filtrado se calculó sobre una
  // muestra. Callarlo daría una cifra que parece exacta y no lo es.
  if (estado.vivo && estado.vivo.recortadoEnOrigen && !partes.includes("de")) {
    const publicadas = (estado.fuegoDatos && estado.fuegoDatos.celdas.length) || 0;
    if (estado.paisFuego || estado.soloEnVista || estado.ventanaFuego !== "h24") {
      partes.push(`sobre las ${numero(publicadas)} celdas publicadas`);
    }
  }
  return partes.join(", ");
}

//: Vuelve a calcular lo que enseña la tarjeta y lo repinta.
//:
//: Es el punto único al que llama cualquier cosa que cambie un filtro: el
//: desplegable de país, el de ventana, la casilla de la extensión y el propio
//: mapa al moverse.
function refrescarTablero() {
  const datos = estado.fuegoDatos;
  if (!datos) return;

  const publicadas = (datos.celdas || []).length;
  const totalReal = Number(datos.totales && datos.totales.celdas) || publicadas;
  // ¿El fichero trae todas las celdas o una muestra? Desde el 31-ago-2026 las
  // trae todas, pero un `incendios.json` publicado antes de ese cambio sigue
  // sirviéndose hasta que P5 vuelva a correr, y el visor tiene que ser correcto
  // con los dos.
  estado.vivo.recortadoEnOrigen = publicadas < totalReal;
  estado.vivo.celdasTotales = totalReal;

  // SIN FILTROS SE USAN LOS TOTALES DEL PIPELINE, Y NO ES REDUNDANCIA.
  //
  // Son exactos SIEMPRE, incluso si el fichero viene recortado. Sumar en el
  // cliente sobre una muestra de 4.000 de 13.031 daría 3.575 donde el pipeline
  // dice 13.031: las cifras se encogerían sin que nada fallara, que es
  // exactamente la clase de error que este cambio venía a quitar. Medido.
  const sinFiltros =
    !estado.paisFuego && estado.ventanaFuego === "h24" && !estado.soloEnVista;

  if (sinFiltros && datos.totales) {
    estado.vivo.incendios = datos.totales;
    estado.vivo.suelo = datos.suelo || {};
  } else {
    const t = totalesDeFuego(celdasDeFuegoFiltradas());
    estado.vivo.incendios = t;
    estado.vivo.suelo = t.suelo;
  }
  pintarEnVivo();
}

function pintarEnVivo() {
  const caja = $("en-vivo");
  const v = estado.vivo;
  if (!caja || (!v.incendios && v.observados === undefined)) return;

  // Cada cifra es el interruptor de su propia capa. Es lo que cierra la
  // distancia entre la afirmacion y la evidencia: un numero que dice "569.538
  // personas en celdas con fuego" y no lleva a verlas es una nota al pie.
  //
  // `<button>` y no `<div>` con `onclick`: sale en el orden de tabulacion, se
  // activa con Enter, y un lector de pantalla lo anuncia como algo que hace
  // algo. Ese es todo el motivo.
  const partes = [];
  // Sobre que arde. Es lo que convierte "hay fuego" en informacion: un foco
  // sobre pastizal en agosto es rutina agricola; el mismo sobre bosque no.
  //
  // Solo aparece si el activo del pais trae cobertura del suelo. Los anteriores
  // a la Fase 1 no la traen, y publicar ceros diria "no hay bosque" donde lo
  // honesto es no decir nada.
  const suelo = v.suelo || {};
  const clases = [
    ["arbolado", suelo.arbolado],
    ["pastizal", suelo.pastizal],
    ["cultivo", suelo.cultivo],
    ["humedal", suelo.humedal],
  ];
  // LAS BARRAS TIENEN QUE SUMAR CIEN, O DECIR QUE NO SUMAN.
  //
  // Se enseñaban tres —arbolado 50 %, pastizal 24 %, cultivo 8 %— y se leian
  // como un reparto completo del fuego. Suman 82: el resto es matorral, suelo
  // desnudo, urbano y las clases que el activo no nombra, mas el humedal cuando
  // no llega al 1 % y se descarta. Un reparto al que le falta una quinta parte
  // sin decirlo hace pensar que la mitad de America Latina arde en bosque
  // cuando la cifra honesta es "la mitad de la energia MEDIDA".
  const nombradas = clases.reduce((t, [, pct]) => t + (Number(pct) || 0), 0);
  const resto = Math.max(0, 100 - nombradas);
  const reparto = [...clases, ["otros", resto]].filter(([, pct]) => Number(pct) >= 1);

  if (v.incendios && v.incendios.celdas) {
    partes.push(
      `<button type="button" class="metrica metrica-viva" data-capa="incendios" data-amenaza="fuego"` +
        `${nivelDe(v.incendios.pop_en_celdas_con_fuego, INDICADORES.fuego.cortes)
          ? ` data-nivel="${nivelDe(v.incendios.pop_en_celdas_con_fuego, INDICADORES.fuego.cortes)}"`
          : ""}>` +
        `<span class="cabeza">${iconoSvg("personas")}` +
        `<span class="valor">${comoConteo(v.incendios.pop_en_celdas_con_fuego)}</span></span>` +
        `<span class="etiqueta">personas en celdas con fuego activo</span>` +
        // EL ALCANCE, QUE AHORA ADEMAS CAMBIA.
        //
        // "586.000 personas en celdas con fuego activo" no dice de donde: se
        // podia leer como un incendio, como un pais o como la region entera.
        // Sin decirlo, la cifra no significa nada.
        //
        // Y desde que las cifras se cruzan con los filtros, el rotulo fijo
        // "En toda America Latina" pasaria de ser una aclaracion a ser una
        // mentira en cuanto alguien eligiera Brasil. Lo dice `alcanceDelFuego`.
        `<span class="apunte">${alcanceDelFuego()} · ` +
        `${numero(v.incendios.celdas)} celdas · ` +
        `${numero(v.incendios.detecciones)} detecciones en ${v.ventanaFuego}&nbsp;h` +
        `${selloDeRevision(v.fuegoUtc)}</span>` +
        `<span class="ver">Ver en el mapa</span></button>`
    );
    // Salud y educacion bajo fuego: la cifra que decide un traslado, y que
    // hasta ahora solo veia quien pulsara la celda exacta entre catorce mil.
    const servicios = [
      ["sedes de salud", v.incendios.salud_en_celdas_con_fuego],
      ["sedes educativas", v.incendios.edu_en_celdas_con_fuego],
    ].filter(([, n]) => Number(n) > 0);
    if (servicios.length) {
      partes.push(
        `<div class="metrica metrica-servicios" data-amenaza="fuego">` +
          servicios
            .map(
              ([nombre, n]) =>
                `<span class="servicio">${iconoSvg(nombre.includes("salud") ? "salud" : "educacion")}` +
                `<strong>${numero(Number(n))}</strong> ${nombre}</span>`
            )
            .join("") +
          `<span class="etiqueta">en celdas con fuego activo</span></div>`
      );
    }
  }
  if (reparto.length) {
    const barras = reparto
      .map(
        ([nombre, pct]) =>
          `<li><span class="suelo-nombre">${iconoSvg(nombre)}${nombre}</span>` +
          `<span class="suelo-barra"><span style="width:${Math.min(100, Number(pct))}%"></span></span>` +
          `<span class="suelo-pct">${numero(Number(pct))}&nbsp;%</span></li>`
      )
      .join("");
    partes.push(
      `<div class="metrica metrica-suelo" data-amenaza="fuego"><span class="etiqueta">sobre qué está ardiendo</span>` +
        `<ul class="suelo-reparto">${barras}</ul>` +
        `<span class="apunte">Reparto de la energía medida, no del número de focos. ` +
        `${numero(suelo.celdas_medidas)} celdas con cobertura conocida` +
        `${suelo.celdas_sin_medir ? `; ${numero(suelo.celdas_sin_medir)} sin medir` : ""}.</span></div>`
    );
  }
  if (v.observados !== undefined) {
    partes.push(
      `<button type="button" class="metrica metrica-viva" data-capa="observados" data-amenaza="sismos">` +
        `<span class="valor">${numero(v.observados)}</span>` +
        `<span class="etiqueta">sismos vistos, sin reporte</span>` +
        `<span class="apunte">por debajo de M5,5 · ${v.ventanaSismos}&nbsp;días` +
        `${selloDeRevision(v.sismosUtc)}</span>` +
        `<span class="ver">Ver en el mapa</span></button>`
    );
  }
  if (!partes.length) return;

  // NO se promete una cadencia aqui. El cron pide un turno cada 30 minutos y
  // GitHub concede unos pocos al dia; escribir "se revisa cada 30 min" seria
  // exactamente la clase de cifra plausible y falsa que este tablero evita.
  // `status.json` publica la cadencia **medida**, y ahi se manda a quien
  // pregunte.
  caja.innerHTML =
    `<p class="eyebrow eyebrow-vivo"><span class="pulso" aria-hidden="true"></span>Ahora mismo</p>` +
    `<div class="metricas">${partes.join("")}</div>` +
    // El enlace a Estado solo donde Estado responde. En modo fuego la frase
    // prometia "la cadencia real está en Estado" y Estado no publica nada del
    // pipeline de fuego: solo latencia sismica y las revisiones del vigia. Una
    // promesa que el enlace no cumple gasta la confianza del resto de la
    // pagina, que es justo lo que este tablero no puede permitirse.
    (estado.amenaza === "fuego"
      ? `<p class="pie-vivo">Cada cifra lleva cuándo se revisó.</p>`
      : `<p class="pie-vivo">Cada cifra lleva cuándo se revisó. La cadencia real ` +
        `—medida, no la prometida— está en <a href="status.html">Estado</a>.</p>`);
  caja.hidden = false;

  for (const boton of caja.querySelectorAll(".metrica-viva")) {
    boton.addEventListener("click", () => encenderCapaViva(boton.dataset.capa));
  }
  // La tarjeta nace despues de que el modo ya se aplico —incendios.json y
  // observados.json llegan por su cuenta—, asi que hay que volver a aplicarlo.
  // Es la misma carrera de creacion que ya mordio al interruptor de observados.
  aplicarAmenaza();
}

//: Enciende la capa desde su cifra, sin duplicar la logica del interruptor.
//
// Se pulsa el checkbox en vez de tocar el mapa directamente: asi el estado del
// control y el del mapa no pueden separarse. Tenerlos en dos sitios es como se
// acaba con una capa encendida y su casilla vacia.
//: "Ver en el mapa" tiene que LLEVAR al sitio, no solo encender una capa.
//:
//: No lo hacia, y de dos maneras. Pulsarlo por segunda vez no hacia
//: literalmente nada —`cambiarAmenaza` sale temprano si el modo ya es ese, y la
//: casilla solo se marcaba `if (!casilla.checked)`—, asi que el boton era de un
//: solo uso. Y ni siquiera el primero cumplia lo que promete: encendia nueve
//: estrellas huecas repartidas por un continente, sin mover la camara y sin
//: decir nada. En un portatil, donde el mapa ya se ve entero, `scrollIntoView`
//: tampoco hacia nada. El resultado es un boton que parece roto porque, para
//: quien lo pulsa, lo esta.
//:
//: Ahora las tres cosas: poner el modo, **asegurar** la capa —fijarla, no
//: alternarla— y encuadrar aquello de lo que habla la cifra.
function encenderCapaViva(capa) {
  if (capa === "incendios") {
    cambiarAmenaza("fuego");
    // Si se estaba mirando un foco concreto, se cierra: la cifra de la tarjeta
    // no es la suya.
    cerrarFoco();

    // EL BOTON NO HACIA NADA, Y ESTE ES EL PORQUE.
    //
    // Volvia siempre al encuadre general. Si ya estabas en fuego mirando el
    // panorama —que es exactamente cuando lees esta tarjeta— no cambiaba ni un
    // pixel y no decia nada. Un boton que promete "Ver en el mapa" y deja la
    // pantalla igual se lee como roto, y lo estaba a efectos practicos.
    //
    // Ahora lleva a LO QUE LA CIFRA CUENTA: si hay un pais elegido, a ese pais;
    // si no, al panorama. Y si la vista ya es la que toca, lo dice en vez de
    // fingir que hizo algo.
    const filtradas = celdasDeFuegoFiltradas();
    const centros = filtradas
      .map((c) => estado.centrosDeCelda && estado.centrosDeCelda.get(c.h3))
      .filter(Boolean)
      .map(([lat, lon]) => [lon, lat]);

    const movido = estado.paisFuego && centros.length ? encuadrarPuntos(centros) : false;
    if (!movido) {
      volverAlEncuadre(estado.mapa, VUELO);
      anotarCamara("panorama:fuego");
    } else {
      anotarCamara("filtrado:fuego");
    }
    anunciar(
      `${numero(filtradas.length)} celdas con fuego en el mapa. ${alcanceDelFuego()}.`
    );
  } else {
    cambiarAmenaza("sismos");
    const casilla = document.querySelector(`#interruptor-${capa} input`);
    // `checked = true` y no `.click()`: alternar hacia que la segunda pulsacion
    // apagara lo que el boton dice encender.
    if (casilla && !casilla.checked) {
      casilla.checked = true;
      casilla.dispatchEvent(new Event("change", { bubbles: true }));
    }
    const encuadrado = encuadrarPuntos(estado.observadosGeo);
    if (encuadrado) anotarCamara("observados");
    anunciar(
      encuadrado
        ? `${numero(estado.observadosGeo.length)} sismos vistos sin reporte, encuadrados en el mapa.`
        : "Sismos vistos sin reporte, visibles en el mapa."
    );
  }
  $("mapa")?.scrollIntoView({ behavior: REDUCIR_MOVIMIENTO ? "auto" : "smooth", block: "nearest" });
}
