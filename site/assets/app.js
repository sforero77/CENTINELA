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

//: Superficie nominal de una celda H3 r7, que es la resolucion de la malla.
//:
//: Es la cifra que el visor ya dice en tres sitios —la pista del panorama, el
//: popup de la celda y la nota de la capa de poblacion— asi que el area sale de
//: multiplicarla por el numero de celdas y **se puede comprobar a mano**. Con
//: `h3.cellArea` saldria mas exacto y ya no cuadraria con lo que se ensena al
//: lado, que en este visor es peor.
const AREA_CELDA_KM2 = 5.2;

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

function leerUrl() {
  const p = new URLSearchParams(location.search);
  const capa = p.get("capa");
  return {
    evento: p.get("evento"),
    capa: CAPAS[capa] ? capa : null,
    // Solo "fuego" es un valor: "sismos" es el defecto y no viaja en la URL.
    amenaza: p.get("amenaza") === "fuego" ? "fuego" : null,
  };
}

function escribirUrl() {
  const p = new URLSearchParams();
  if (estado.seleccionado) p.set("evento", estado.seleccionado);
  if (estado.seleccionado && estado.capa !== "mmi") p.set("capa", estado.capa);
  // Compartible, como ?evento=: quien manda un enlace en modo fuego manda el
  // modo fuego. Un evento abierto implica sismos, asi que son excluyentes.
  if (!estado.seleccionado && estado.amenaza === "fuego") p.set("amenaza", "fuego");
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
    caja.innerHTML = `<p class="pista">Todavía no hay reportes publicados.</p>`;
    return;
  }
  const mayor = eventos.reduce((a, b) => ((b.pop_mmi7p || 0) > (a.pop_mmi7p || 0) ? b : a));
  const paises = new Set(eventos.map((e) => e.iso3).filter(Boolean)).size;
  const enVivo = eventos.filter((e) => !e.backtest).length;

  caja.innerHTML =
    `<div class="metricas">` +
    `<div class="metrica"><span class="cabeza">${iconoSvg("reportes")}` +
    `<span class="valor">${eventos.length}</span></span>` +
    `<span class="etiqueta">reportes publicados</span></div>` +
    `<div class="metrica"><span class="cabeza">${iconoSvg("personas")}` +
    `<span class="valor">${comoTexto(mayor.pop_mmi7p)}</span></span>` +
    `<span class="etiqueta">mayor exposición registrada</span>` +
    `<span class="apunte">M${String(mayor.mag).replace(".", ",")} · ${escapar(mayor.lugar)}</span></div>` +
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
              ? `${comoTexto(bandaTitular(e).pop)} en MMI≥${bandaTitular(e).banda}`
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
    ? `${comoTexto(titular.pop)}<small>personas en MMI≥${titular.banda}</small>`
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
  for (const capa of ["celdas", "contornos", "perimetro"]) quitarCapa(capa);
  estado.presentes = null;
  for (const capa of ["celdas", "contornos", "perimetro"]) anotarPintado(capa, 0);
  verHaloProporcional(true);
  escribirUrl();
  anunciar("Sin evento seleccionado. El panel muestra el panorama de los reportes publicados.");
  const selector = $("selector-evento");
  if (selector) selector.value = "";
  // Al mismo encuadre adaptado con el que abre, no al centro y zoom fijos:
  // volver al panorama tiene que devolver la vista que se tenia al llegar.
  volverAlEncuadre(estado.mapa, VUELO);
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
            ? `${comoTexto(t[`pop_mmi${b}p`])} personas expuestas a intensidad ${b} o mayor.`
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
  const titular = bandaDeTotales(reporte.totales) || 7;
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
        `<span class="franja-valor">${comoTexto(f.valor)}</span></li>`
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
const INDICADORES = {
  personas: { icono: "personas", cortes: [247720, 910714], formato: comoTexto },
  mayores: { icono: "mayores", cortes: [15016, 81267], formato: comoTexto },
  salud: { icono: "salud", cortes: [31, 152], formato: numero },
  educacion: { icono: "educacion", cortes: [92, 998], formato: numero },
  edificaciones: { icono: "edificaciones", cortes: [130938, 331809], formato: comoTexto },
  superficie: { icono: "superficie", cortes: [8.3, 46.8] },
  vias: { icono: "vias", cortes: [1572, 5266] },
  fuego: { icono: "fuego", cortes: [50000, 300000], formato: comoTexto },
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
  $("titulo-metricas").textContent =
    banda && banda !== 7 ? `Expuesto en MMI≥${banda} y MMI≥7` : "Expuesto en MMI≥7";
  const km2 = Number.isFinite(t.built_m2_mmi7p) ? t.built_m2_mmi7p / 1e6 : null;
  const principal = t.road_km_principal_mmi7p;

  const tarjetas = [
    banda && banda !== 7
      ? {
          clave: "personas",
          valor: t[`pop_mmi${banda}p`],
          etiqueta: `personas en MMI≥${banda}`,
          apunte: "La sacudida no alcanzó MMI 7 sobre población: ninguna de las cifras de abajo, que se cuentan en MMI≥7, aplica a este evento.",
          ancha: true,
        }
      : { clave: "personas", valor: t.pop_mmi7p, etiqueta: "personas" },
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
          `${comoTexto(f.valor)}</span></li>`
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
  // Se ordena por la banda que el evento alcanzó. Con `pop_mmi7p` a cero en
  // todas las filas, el orden salía alfabético y las barras, todas vacías.
  const banda = bandaDeTotales(reporte.totales);
  const cifra = (m) => (banda && banda !== 7 ? (m.pop_banda ?? 0) : (m.pop_mmi7p || 0));
  const top = [...fuente].sort((a, b) => cifra(b) - cifra(a)).slice(0, 8);
  const maximo = Math.max(...top.map(cifra), 1);

  $("detalle-barras").innerHTML = top
    .map((m) => {
      const pct = (100 * cifra(m)) / maximo;
      const banda = CAPAS.mmi.cortes.filter((c) => (m.mmi_max || 0) >= c).length - 1;
      const color = CAPAS.mmi.colores[Math.max(0, banda)];
      const nombre = escapar(capitalizar(m.nombre) || m.adm2_id);
      const mmi = Number.isFinite(m.mmi_max) ? numero(m.mmi_max, 1) : "—";
      // A partir de MMI 7,5 la rampa de ShakeMap ya es roja: el texto de la
      // ficha pasa a blanco o queda verde bosque sobre rojo oscuro.
      const oscuro = banda >= 3;
      return (
        `<li><div class="barra-fila"><span class="barra-nombre">` +
        `<span class="ficha-mmi${oscuro ? " sobre-oscuro" : ""}" style="background:${color}" ` +
        `title="Intensidad máxima ${mmi}">${mmi}</span>` +
        `${nombre}</span>` +
        `<span class="barra-valor">${comoTexto(cifra(m))}</span></div>` +
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
    `Este reporte publica <strong>${comoTexto(totales.bld_mmi7p)} edificaciones ` +
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
    partes.push(
      `La población de la malla difiere en <strong>${numero(inc.pop_discrepancia_pct, 1)} %</strong> ` +
      `del total nacional del mismo producto. La diferencia viene del remuestreo a ` +
      `hexágonos y se publica en vez de esconderse.`
    );
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

// Superficie publica y estable. No lleva guiones bajos ni `__test__`: no es un
// gancho de pruebas, es el visor rindiendo cuentas — y sirve igual para
// diagnosticar desde la consola del navegador de quien reporte un fallo.
window.CENTINELA = {
  pintado,
  errores: erroresAlPintar,
  camara,
  //: Puerta para las pruebas de navegador. Ver `abrirFocoDePrueba`.
  abrirFoco: (indice) => abrirFocoDePrueba(indice),
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
  const reintentar = () => {
    if (!m.isStyleLoaded()) return;
    m.off("styledata", reintentar);
    m.off("idle", reintentar);
    seguro();
  };
  m.on("styledata", reintentar);
  m.on("idle", reintentar);

  // Y una red por si `isStyleLoaded()` no llega a ser cierto nunca — pasa
  // cuando una fuente se queda a medias. Sin esto el callback no corre jamas y
  // el visor se queda a medio pintar sin decir nada.
  setTimeout(() => {
    if (!m.getStyle()) return;
    m.off("styledata", reintentar);
    m.off("idle", reintentar);
    seguro();
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
        `<p class="mono" style="margin:0 0 .15rem">Celda H3 · r7 · 5,2 km²</p>` +
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
        fila("Personas", comoTexto(Number(p.pop))) +
        fila("Edificaciones", comoTexto(Number(p.bld))) +
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
            etiqueta: `M${String(e.mag).replace(".", ",")}`,
          },
        })),
      },
    });
    m.addLayer({
      id: "epicentros-halo",
      type: "circle",
      source: "epicentros",
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
      m.on("click", capa, (ev) => seleccionar(ev.features[0].properties.usgs_id));
      m.on("mouseenter", capa, () => (m.getCanvas().style.cursor = "pointer"));
      m.on("mouseleave", capa, () => (m.getCanvas().style.cursor = ""));
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
  mapa.addControl(new maplibregl.ScaleControl({ maxWidth: 110, unit: "metric" }), "top-right");

  // Positron viene en gris neutro. Sobre un fondo de arena cálida canta, y su
  // agua es casi del mismo tono que su tierra — inservible para un sistema
  // cuya mitad de la exposición es costera. Se retintan tierra y agua a la
  // paleta de la identidad, sin tocar el resto del estilo.
  mapa.on("style.load", () => {
    for (const capa of mapa.getStyle().layers) {
      if (capa.type !== "fill" && capa.type !== "background") continue;
      const agua = capa.id === "water" || capa.id.startsWith("water_");
      const tierra = capa.id === "background" || capa.id === "landcover" ||
                     capa.id.startsWith("landuse") || capa.id.startsWith("landcover");
      if (!agua && !tierra) continue;
      const prop = capa.type === "background" ? "background-color" : "fill-color";
      try {
        mapa.setPaintProperty(capa.id, prop, agua ? BASE_AGUA : BASE_TIERRA);
      } catch (e) {
        /* el estilo puede cambiar; no es crítico */
      }
    }
  });

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
    `<span class="valor">${comoTexto(resumen.poblacion_en_la_malla)}</span></span>` +
    `<span class="etiqueta">personas en la malla hexagonal</span>` +
    `<span class="apunte">precalculadas, antes de que ocurra nada</span></div>` +
    `<div class="metrica"><span class="cabeza">${iconoSvg("desvio")}` +
    `<span class="valor">${porcentaje(resumen.peor_desvio_pct)}</span></span>` +
    `<span class="etiqueta">peor desvío vs. cifra oficial</span>` +
    `<span class="apunte">el de Venezuela, y está explicado</span></div>` +
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
  pob.textContent = pais.construido ? comoTexto(pais.poblacion_medida) : "—";

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
    frases.push(
      "El desvío compara la población que mide el activo contra la cifra " +
      "oficial de referencia del país. Se publica aunque incomode: una " +
      "tolerancia que nadie ve no vigila nada."
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
const VENTANAS = {
  todo: { texto: "Todo", dias: null },
  ano: { texto: "12 meses", dias: 365 },
  trimestre: { texto: "90 días", dias: 90 },
};

//: ¿Cae esta fila dentro de la ventana elegida?
//:
//: Sin sello de fecha se deja pasar. Un reporte cuyo `utc` no se pudo leer es un
//: fallo del dato, no algo que deba desaparecer de la lista sin decir nada.
function enLaVentana(li) {
  const dias = (VENTANAS[estado.ventana] || VENTANAS.todo).dias;
  if (!dias) return true;
  const utc = li.dataset.utc;
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
function enElEncuadre(li) {
  const m = estado.mapa;
  const lon = Number(li.dataset.lon);
  const lat = Number(li.dataset.lat);
  if (!m || !Number.isFinite(lon) || !Number.isFinite(lat)) return true;
  try {
    return m.getBounds().contains([lon, lat]);
  } catch (error) {
    return true;
  }
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
    const suyo = !estado.paisFiltrado || li.dataset.iso3 === estado.paisFiltrado;
    const dentro = !estado.soloEnVista || enElEncuadre(li);
    li.hidden = !(suyo && dentro && enLaVentana(li));
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
  if (!visibles) {
    // El aviso nombra el filtro que dejo la lista vacia, y no uno cualquiera.
    // Decir "ese pais no tiene reportes" cuando lo que sobra es la ventana
    // temporal manda a cambiar lo que no era.
    const ventana = VENTANAS[estado.ventana] || VENTANAS.todo;
    vacio.textContent = estado.soloEnVista
      ? "Ningún reporte cae dentro de lo que el mapa está enseñando. Aleja o mueve el mapa."
      : ventana.dias
        ? `Ningún reporte en los últimos ${ventana.texto.toLowerCase()}` +
          `${estado.paisFiltrado ? " en ese país" : ""}. Prueba con «Todo».`
        : "Ese país todavía no tiene reportes publicados.";
  }
  if (anunciando) {
    anunciar(`${visibles} ${visibles === 1 ? "reporte" : "reportes"} en la lista.`);
  }
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
function pintarControlesLista() {
  const ventanas = $("ventana-lista");
  if (ventanas && !ventanas.children.length) {
    ventanas.innerHTML = Object.entries(VENTANAS)
      .map(
        ([clave, v]) =>
          `<button type="button" data-ventana="${clave}" ` +
          `aria-pressed="${String(clave === estado.ventana)}">${v.texto}</button>`
      )
      .join("");
    for (const boton of ventanas.querySelectorAll("button")) {
      boton.addEventListener("click", () => {
        estado.ventana = boton.dataset.ventana;
        refrescarLista();
      });
    }
  }

  const caja = $("orden-lista");
  if (caja && !caja.children.length) {
    caja.innerHTML = Object.entries(ORDENES)
      .map(
        ([clave, o]) =>
          `<button type="button" data-orden="${clave}" ` +
          `aria-pressed="${String(clave === estado.orden)}">${o.texto}</button>`
      )
      .join("");
    for (const boton of caja.querySelectorAll("button")) {
      boton.addEventListener("click", () => {
        estado.orden = boton.dataset.orden;
        refrescarLista();
      });
    }
  }

  const etiqueta = $("etiqueta-en-vista");
  const interruptor = $("solo-en-vista");
  if (!etiqueta || !interruptor || !estado.mapa) return;
  etiqueta.hidden = false;
  interruptor.addEventListener("change", () => {
    estado.soloEnVista = interruptor.checked;
    refrescarLista();
  });
  // Mientras el recorte esta puesto, mover el mapa mueve la lista. `moveend` y
  // no `move`: reordenar veintiun nodos en cada fotograma de un desplazamiento
  // es trabajo tirado, y el usuario solo lee la lista cuando suelta.
  estado.mapa.on("moveend", () => {
    if (estado.soloEnVista) refrescarLista({ anunciando: false });
  });
}

function pintarFiltroPaises(eventos, nombres) {
  const caja = $("filtro-paises");
  if (!caja) return;
  const cuenta = new Map();
  for (const e of eventos) {
    if (e.iso3) cuenta.set(e.iso3, (cuenta.get(e.iso3) || 0) + 1);
  }
  // Con un solo pais el filtro no filtra nada: es ruido con aspecto de control.
  if (cuenta.size < 2) return;

  const orden = [...cuenta.entries()].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]));
  const boton = (iso3, texto, n) =>
    `<button type="button" data-iso3="${escapar(iso3)}" aria-pressed="${iso3 === ""}">` +
    `${escapar(texto)}<span class="cuenta">${nf.format(n)}</span></button>`;

  caja.innerHTML =
    boton("", "Todos", eventos.length) +
    orden.map(([iso3, n]) => boton(iso3, nombres.get(iso3) || iso3, n)).join("");
  caja.hidden = false;

  for (const b of caja.querySelectorAll("button")) {
    b.addEventListener("click", () => aplicarFiltro(b.dataset.iso3 || ""));
  }
}

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
function pintarLeyendaSimbolos() {
  if ($("leyenda-simbolos")) return;
  const anfitrion = $("controles-mapa") || $("lienzo");
  if (!anfitrion) return;

  // `<details>` y no `<div>`: en un movil de 390 px esta caja medía 248 —el
  // 64 % del ancho— y tapaba Colombia, Ecuador y Peru. Plegada ocupa una linea.
  //
  // Abierta en pantalla ancha, donde sobra sitio y la pregunta "¿que es esto?"
  // merece respuesta sin pedirla. El `open` se decide en JS porque CSS no puede
  // ponerlo ni quitarlo.
  const caja = document.createElement("details");
  caja.className = "leyenda leyenda-simbolos";
  caja.id = "leyenda-simbolos";
  caja.open = window.matchMedia("(min-width: 48rem)").matches;
  caja.innerHTML =
    `<summary class="leyenda-titulo mono">Qué hay en el mapa</summary>` +
    `<ul class="leyenda-simbolos-lista">` +
    `<li><span class="sim sim-epicentro" aria-hidden="true"></span>` +
    `<span><strong>Sismo con reporte</strong><br>` +
    `<span class="menor">El círculo crece con la población expuesta</span></span></li>` +
    `<li><span class="sim sim-observado" aria-hidden="true"></span>` +
    `<span><strong>Sismo visto, sin reporte</strong><br>` +
    `<span class="menor">Por debajo de M5,5. Se vio y no se midió su impacto</span></span></li>` +
    `<li><span class="sim sim-fuego" aria-hidden="true"></span>` +
    `<span><strong>Foco activo</strong><br>` +
    `<span class="menor">Detección de satélite en 24 h. El color es la energía</span></span></li>` +
    `</ul>`;
  anfitrion.appendChild(caja);
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

  caja.querySelector("input").addEventListener("change", (ev) => {
    const m = estado.mapa;
    if (!m || !m.getLayer("observados")) return;
    m.setLayoutProperty("observados", "visibility", ev.target.checked ? "visible" : "none");
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
  anotarPintado("focos", estado.focos.length);
  pintarControlesFocos();
  pintarListaFocos({ anunciando: false });
  estado.vivo.incendios = datos.totales || {};
  estado.vivo.suelo = datos.suelo || {};
  estado.vivo.ventanaFuego = datos.ventana_horas || 24;
  estado.vivo.fuegoUtc = datos.generado_utc || null;
  pintarEnVivo();
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
    areaKm2: celdas.length * AREA_CELDA_KM2,
    pop: suma("pop"),
    bld: suma("bld"),
    salud: suma("salud"),
    edu: suma("edu"),
    detecciones: suma("detecciones"),
    deteccionesBaja: suma("detecciones_baja"),
    frpSuma: suma("frp_suma"),
    frpMax: celdas.reduce((t, c) => Math.max(t, Number(c.frp_max) || 0), 0),
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

function enLaVentanaFuego(foco) {
  const horas = (VENTANAS_FUEGO[estado.ventanaFuego] || VENTANAS_FUEGO.h24).horas;
  const t = Date.parse(foco.ultimaUtc);
  // Sin sello legible se deja pasar: es un fallo del dato, no algo que deba
  // desaparecer de la lista sin decir nada.
  if (!Number.isFinite(t)) return true;
  return Date.now() - t <= horas * 3600000;
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
  area.textContent = numero(Math.round(foco.areaKm2)) + " km²";
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
      ? iconoSvg("personas") + comoTexto(foco.pop) + " personas dentro"
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
    cuenta.textContent = dentro.length
      ? listados.length < dentro.length
        ? numero(listados.length) + " de " + numero(dentro.length) + " focos"
        : numero(dentro.length) + (dentro.length === 1 ? " foco" : " focos")
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
  if (anunciando) {
    anunciar(numero(dentro.length) + (dentro.length === 1 ? " foco" : " focos") + " en la lista.");
  }
}

function pintarControlesFocos() {
  const ventanas = $("ventana-focos");
  if (ventanas && !ventanas.children.length) {
    ventanas.innerHTML = Object.entries(VENTANAS_FUEGO)
      .map(
        ([clave, v]) =>
          '<button type="button" data-ventana="' +
          clave +
          '" aria-pressed="' +
          String(clave === estado.ventanaFuego) +
          '">' +
          v.texto +
          "</button>"
      )
      .join("");
    for (const boton of ventanas.querySelectorAll("button")) {
      boton.addEventListener("click", () => {
        estado.ventanaFuego = boton.dataset.ventana;
        pintarListaFocos();
      });
    }
  }

  const ordenes = $("orden-focos");
  if (ordenes && !ordenes.children.length) {
    ordenes.innerHTML = Object.entries(ORDENES_FOCOS)
      .map(
        ([clave, o]) =>
          '<button type="button" data-orden="' +
          clave +
          '" aria-pressed="' +
          String(clave === estado.ordenFocos) +
          '">' +
          o.texto +
          "</button>"
      )
      .join("");
    for (const boton of ordenes.querySelectorAll("button")) {
      boton.addEventListener("click", () => {
        estado.ordenFocos = boton.dataset.orden;
        pintarListaFocos();
      });
    }
  }

  // Solo los paises que de verdad tienen fuego ahora. Una fila de diecinueve
  // pastillas donde diecisiete no filtran nada es ruido con aspecto de control
  // — la misma regla que ya aplica el filtro de reportes.
  const paises = $("filtro-paises-fuego");
  if (paises && !paises.children.length) {
    const cuenta = new Map();
    for (const f of estado.focos) {
      if (f.iso3) cuenta.set(f.iso3, (cuenta.get(f.iso3) || 0) + 1);
    }
    if (cuenta.size >= 2) {
      const orden = [...cuenta.entries()].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]));
      const boton = (iso3, texto, n) =>
        '<button type="button" data-iso3="' +
        escapar(iso3) +
        '" aria-pressed="' +
        String(iso3 === "") +
        '">' +
        escapar(texto) +
        '<span class="cuenta">' +
        nf.format(n) +
        "</span></button>";
      paises.innerHTML =
        boton("", "Todos", estado.focos.length) +
        orden.map(([iso3, n]) => boton(iso3, nombrePais(iso3), n)).join("");
      paises.hidden = false;
      for (const b of paises.querySelectorAll("button")) {
        b.addEventListener("click", () => {
          estado.paisFuego = b.dataset.iso3 || "";
          pintarListaFocos();
        });
      }
    }
  }
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
        layout: { visibility: "none" },
        paint: {
          // El radio va en pixeles de pantalla, asi que no se encoge con el
          // zoom: es lo que hace la capa visible a escala continental.
          // Radio minimo de 3 px: por debajo el contorno se come el relleno y
          // el simbolo deja de tener color, que es justo lo que lo hacia legible.
          // Tres paradas y no dos. Con solo la de zoom 3, a escala continental
          // los cuatro mil puntos se amontonaban en una mancha uniforme:
          // legible como "aqui arde" e ilegible como dato. Mas pequenos, la
          // misma nube se lee como densidad.
          "circle-radius": [
            "interpolate", ["linear"], ["zoom"],
            2, ["interpolate", ["linear"], ["coalesce", ["get", "frp_suma"], 0], 0, 2, 500, 4.5],
            4, ["interpolate", ["linear"], ["coalesce", ["get", "frp_suma"], 0], 0, 3, 500, 7],
            8, ["interpolate", ["linear"], ["coalesce", ["get", "frp_suma"], 0], 0, 5, 500, 13],
          ],
          "circle-color": colorDeFuego(),
          "circle-opacity": 0.9,
          "circle-stroke-color": FUEGO_CONTORNO,
          "circle-stroke-width": 1,
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
    `<p class="cifra-area"><strong>${numero(Math.round(foco.areaKm2))}</strong> km²</p>` +
    `<p class="apunte">${numero(foco.nCeldas)} celda${foco.nCeldas === 1 ? "" : "s"} de ` +
    `${numero(AREA_CELDA_KM2, 1)} km²</p>`;

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
            `<span class="valor">${comoTexto(n)}</span></span>` +
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

  $("fuego-deteccion").innerHTML =
    `<div class="metrica"><span class="cabeza">${iconoSvg("detecciones")}` +
    `<span class="valor">${numero(foco.detecciones)}</span></span>` +
    `<span class="etiqueta">detecciones en 24 h</span></div>` +
    `<div class="metrica"><span class="cabeza">${iconoSvg("potencia")}` +
    `<span class="valor">${numero(Math.round(foco.frpSuma))}</span></span>` +
    `<span class="etiqueta">MW de potencia radiativa</span></div>`;

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
    `Foco de ${numero(foco.nCeldas)} celdas, ${numero(Math.round(foco.areaKm2))} kilómetros cuadrados. ` +
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
    `${p.detecciones_baja > 0 ? `${numero(p.detecciones_baja)} de baja confianza no contadas. ` : ""}` +
    `Último paso: ${escapar(comoFecha(p.ultima_utc))}.</p>` +
    `</div>`
  );
}

//: Cuantas celdas hay y cuantas se dibujan, que no son la misma cifra.
//:
//: `p5_incendios` ordena por potencia radiativa y publica las 4.000 primeras
//: —varios megabytes menos que descargar la cola larga de detecciones debiles—
//: pero calcula los totales sobre **todas**, y emite `celdas_publicadas` justo
//: para que el recorte se pueda decir. El visor no leia ese campo: rotulaba la
//: casilla con el total y encendia una capa con el recorte. Medido el
//: 28-ago-2026: «Focos activos (15.607 celdas en 24 h)» sobre un mapa con
//: 4.000, y lo mismo por el lector de pantalla.
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
    "desaconseja estimarla desde detecciones." + corte;
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
  const reparto = [
    ["arbolado", suelo.arbolado],
    ["pastizal", suelo.pastizal],
    ["cultivo", suelo.cultivo],
    ["humedal", suelo.humedal],
  ].filter(([, pct]) => Number(pct) >= 1);

  if (v.incendios && v.incendios.celdas) {
    partes.push(
      `<button type="button" class="metrica metrica-viva" data-capa="incendios" data-amenaza="fuego"` +
        `${nivelDe(v.incendios.pop_en_celdas_con_fuego, INDICADORES.fuego.cortes)
          ? ` data-nivel="${nivelDe(v.incendios.pop_en_celdas_con_fuego, INDICADORES.fuego.cortes)}"`
          : ""}>` +
        `<span class="cabeza">${iconoSvg("personas")}` +
        `<span class="valor">${comoTexto(v.incendios.pop_en_celdas_con_fuego)}</span></span>` +
        `<span class="etiqueta">personas en celdas con fuego activo</span>` +
        // EL ALCANCE, QUE NO SE DECIA EN NINGUNA PARTE.
        //
        // "586.000 personas en celdas con fuego activo" no dice de donde: se
        // podia leer como un incendio, como un pais o como la region entera.
        // Es la suma de TODA America Latina en 24 h, y sin decirlo la cifra no
        // significa nada. Un foco concreto se mira pulsandolo en el mapa.
        `<span class="apunte">En toda América Latina · ` +
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
    `<p class="pie-vivo">Cada cifra lleva cuándo se revisó. La cadencia real ` +
    `—medida, no la prometida— está en <a href="status.html">Estado</a>.</p>`;
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
    // La cifra habla de toda America Latina, asi que el encuadre es ese. Si se
    // estaba mirando un foco concreto, se cierra: la cifra de la tarjeta no es
    // la suya.
    cerrarFoco();
    volverAlEncuadre(estado.mapa, VUELO);
    anotarCamara("panorama:fuego");
    anunciar("Focos activos en el mapa, en toda América Latina.");
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
