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

// Encuadre inicial: la ventana LATAM del sistema (RF-01).
const VISTA_INICIAL = { center: [-76.0, 4.0], zoom: 3.1 };

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
const CAPAS = {
  mmi: {
    titulo: "Intensidad",
    columna: "mmi",
    exacto: true,
    cortes: [6, 6.5, 7, 7.5, 8, 8.5],
    colores: ["#fdbb84", "#fc8d59", "#ef6548", "#d7301f", "#b30000", "#7f0000"],
    nota:
      "Mercalli modificada, en pasos de media. La malla llega hasta donde hay " +
      "algo expuesto: el hueco no es ausencia de sacudida, es ausencia de gente " +
      "y de infraestructura.",
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
  mapa: null,
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
  return { evento: p.get("evento"), capa: CAPAS[capa] ? capa : null };
}

function escribirUrl() {
  const p = new URLSearchParams();
  if (estado.seleccionado) p.set("evento", estado.seleccionado);
  if (estado.seleccionado && estado.capa !== "mmi") p.set("capa", estado.capa);
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
      const props = {};
      for (const [nombre, i] of Object.entries(idx)) {
        if (nombre !== "h3") props[nombre] = c[i];
      }
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
  caja.innerHTML = ORDEN_CAPAS.map(
    (id) =>
      `<button type="button" role="tab" data-capa="${id}" ` +
      `aria-selected="${id === estado.capa}" title="${escapar(CAPAS[id].nota)}">` +
      `${CAPAS[id].titulo}</button>`
  ).join("");
  for (const boton of caja.querySelectorAll("button")) {
    boton.addEventListener("click", () => cambiarCapa(boton.dataset.capa));
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

    // La cobertura primero: da los nombres de pais que necesita el filtro, y
    // asi el mapeo ISO3 -> nombre vive en un solo sitio, el que lo publica.
    const nombres = await cargarCobertura(eventos);
    pintarFiltroPaises(eventos, nombres);

    const url = leerUrl();
    if (url.capa) estado.capa = url.capa;
    if (url.evento && eventos.some((e) => e.usgs_id === url.evento)) seleccionar(url.evento);
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
    `<div class="metrica"><span class="valor">${eventos.length}</span>` +
    `<span class="etiqueta">reportes publicados</span></div>` +
    `<div class="metrica"><span class="valor">${comoTexto(mayor.pop_mmi7p)}</span>` +
    `<span class="etiqueta">mayor exposición registrada</span>` +
    `<span class="apunte">M${String(mayor.mag).replace(".", ",")} · ${escapar(mayor.lugar)}</span></div>` +
    (paises > 1
      ? `<div class="metrica"><span class="valor">${paises}</span>` +
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
    const [reporte, csv, celdas] = await Promise.all([
      json(`reports/${usgsId}/report.json`),
      fetch(`reports/${usgsId}/adm2.csv`).then((r) => (r.ok ? r.text() : "")),
      fetch(`reports/${usgsId}/celdas.json`).then((r) => (r.ok ? r.json() : null)),
    ]);
    pintarLateral(reporte, parsearCsv(csv));
    // El mapa va en su propio try: las cifras y las barras salen del reporte y
    // no dependen de que la malla se pueda dibujar. Antes un fallo aqui
    // borraba el titulo de un panel que ya estaba entero.
    try {
      pintarCeldas(celdas, reporte);
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

function cerrarDetalle() {
  estado.seleccionado = null;
  $("lateral-vacio").hidden = false;
  $("lateral-detalle").hidden = true;
  $("leyenda").hidden = true;
  $("capas").hidden = true;
  for (const li of document.querySelectorAll(".lista-eventos li")) li.classList.remove("activo");
  quitarCapa("celdas");
  estado.presentes = null;
  verHaloProporcional(true);
  escribirUrl();
  anunciar("Sin evento seleccionado. El panel muestra el panorama de los reportes publicados.");
  if (estado.mapa) estado.mapa.easeTo({ ...VISTA_INICIAL, duration: VUELO });
}

// --- Panel lateral ----------------------------------------------------------

function pintarLateral(reporte, municipios) {
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

function pintarDistintivos(reporte) {
  const marcas = [];
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

function pintarMetricas(reporte) {
  const t = reporte.totales;

  // Un preliminar publica radios en lugar de bandas de intensidad. Enseñar
  // "MMI≥7: 0" sería una cifra falsa y creíble.
  if (reporte.preliminar) {
    $("titulo-metricas").textContent = "Expuesto por radio";
    $("detalle-metricas").innerHTML = (reporte.radios || [])
      .map(
        (r) =>
          `<div class="metrica"><span class="valor">${comoTexto(r.pop)}</span>` +
          `<span class="etiqueta">a ${r.radio_km} km</span></div>`
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
          valor: comoTexto(t[`pop_mmi${banda}p`]),
          etiqueta: `personas en MMI≥${banda}`,
          apunte: "La sacudida no alcanzó MMI 7 sobre población: ninguna de las cifras de abajo, que se cuentan en MMI≥7, aplica a este evento.",
          ancha: true,
        }
      : { valor: comoTexto(t.pop_mmi7p), etiqueta: "personas" },
    { valor: comoTexto(t.pop_65p_mmi7p), etiqueta: "de 65 años o más" },
    { valor: comoTexto(t.bld_mmi7p), etiqueta: "edificaciones" },
    {
      valor: km2 === null ? "—" : `${numero(km2, 1)} km²`,
      etiqueta: "superficie construida",
      apunte: "Vista por satélite: incluye lo que OSM no mapeó.",
    },
    { valor: numero(t.health_mmi7p), etiqueta: "sedes de salud" },
    { valor: numero(t.edu_mmi7p), etiqueta: "sedes educativas" },
    {
      valor: `${numero(t.road_km_mmi7p)} km`,
      etiqueta: "de vía",
      ancha: true,
      apunte: Number.isFinite(principal)
        ? `De ellos ${numero(principal)} km son primarias y secundarias; el resto es red local.`
        : null,
    },
  ];

  $("detalle-metricas").innerHTML = tarjetas
    .map(
      (m) =>
        `<div class="metrica${m.ancha ? " ancha" : ""}">` +
        `<span class="valor">${m.valor}</span>` +
        `<span class="etiqueta">${m.etiqueta}</span>` +
        (m.apunte ? `<span class="apunte">${m.apunte}</span>` : "") +
        `</div>`
    )
    .join("");
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
    { etiqueta: "Licuefacción alta", valor: t.pop_lq_alta },
    { etiqueta: "Deslizamiento alto", valor: t.pop_ls_alta },
  ];
  $("detalle-terreno").innerHTML =
    filas
      .map(
        (f) =>
          `<li><span>${f.etiqueta}</span><span class="cifra${(f.valor || 0) > 0 ? "" : " cero"}">` +
          `${comoTexto(f.valor)}</span></li>`
      )
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
    ["Mapa PNG", `${base}/mapa_general.png`],
    ["Mapa para prensa", `${base}/mapa_prensa.png`],
    ["Hilo para redes", `${base}/hilo.txt`],
  ];
  $("detalle-descargas").innerHTML = enlaces
    .map(([texto, url]) => `<a href="${url}">${texto}</a>`)
    .join(" · ");
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
function cuandoElEstiloEsteListo(m, fn) {
  if (m.isStyleLoaded()) fn();
  else m.once("load", fn);
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

function quitarCapa(id) {
  const m = estado.mapa;
  if (!m || !m.isStyleLoaded() || !m.getSource(id)) return;
  for (const sufijo of ["", "-borde"]) {
    if (m.getLayer(id + sufijo)) m.removeLayer(id + sufijo);
  }
  m.removeSource(id);
}

function pintarCeldas(datos, reporte) {
  const m = estado.mapa;
  if (!m) return;
  cuandoElEstiloEsteListo(m, () => dibujarCeldas(m, datos, reporte));
}

function dibujarCeldas(m, datos, reporte) {
  quitarCapa("celdas");

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
    if (Number.isFinite(reporte.event.lon) && reporte.event.lon !== 0) {
      m.easeTo({ center: [reporte.event.lon, reporte.event.lat], zoom: 7.5, duration: VUELO });
    }
    return;
  }

  // `generateId` da a cada hexágono un id estable dentro de la fuente, que es
  // lo que necesita `feature-state` para resaltar el de debajo del cursor.
  m.addSource("celdas", { type: "geojson", data: geo, generateId: true });

  const antes = primeraEtiqueta(m);
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

  verHaloProporcional(false);
  engancharCeldas(m);
  pintarSelectorCapas();
  pintarLeyenda(CAPAS[estado.capa]);

  const lons = geo.features.flatMap((f) => f.geometry.coordinates[0].map((c) => c[0]));
  const lats = geo.features.flatMap((f) => f.geometry.coordinates[0].map((c) => c[1]));
  m.fitBounds(
    [[Math.min(...lons), Math.min(...lats)], [Math.max(...lons), Math.max(...lats)]],
    { padding: 48, maxZoom: 10, duration: VUELO }
  );
}

// Los manejadores se registran una sola vez. Antes se añadían dentro de
// `pintarCeldas`, así que cambiar de evento tres veces dejaba tres oyentes de
// clic y abría tres ventanitas de una vez.
function engancharCeldas(m) {
  if (estado.ganchosCeldas) return;
  estado.ganchosCeldas = true;
  let encima = null;

  m.on("click", "celdas", (ev) => {
    const p = ev.features[0].properties;
    const fila = (etiqueta, valor) =>
      `<div style="display:flex;justify-content:space-between;gap:1rem">` +
      `<span style="color:rgba(28,51,40,.72)">${etiqueta}</span><strong>${valor}</strong></div>`;
    new maplibregl.Popup({ closeButton: false, maxWidth: "18rem" })
      .setLngLat(ev.lngLat)
      .setHTML(
        `<p class="mono" style="margin:0 0 .45rem">Celda H3 · r7 · 5,2 km²</p>` +
        fila("Intensidad", numero(Number(p.mmi), 1)) +
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
function crearEstrella(m) {
  if (m.hasImage("estrella")) return;
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
  ctx.fillStyle = "#1c1b1a";
  ctx.strokeStyle = "#ffffff";
  ctx.lineWidth = lado * 0.075;
  ctx.stroke();
  ctx.fill();
  m.addImage("estrella", ctx.getImageData(0, 0, lado, lado), { pixelRatio: 2 });
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
        "circle-color": EPICENTRO,
        "circle-opacity": 0.16,
        "circle-stroke-color": "#ffffff",
        "circle-stroke-width": 1.5,
        "circle-stroke-opacity": 0.9,
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

    for (const capa of ["epicentros", "epicentros-halo"]) {
      m.on("click", capa, (ev) => seleccionar(ev.features[0].properties.usgs_id));
      m.on("mouseenter", capa, () => (m.getCanvas().style.cursor = "pointer"));
      m.on("mouseleave", capa, () => (m.getCanvas().style.cursor = ""));
    }
  };

  if (m.isStyleLoaded()) pintar();
  else m.on("load", pintar);
}

function iniciarMapa() {
  if (!$("mapa") || typeof maplibregl === "undefined") return null;

  const mapa = new maplibregl.Map({
    container: "mapa",
    style: ESTILO_BASE,
    ...VISTA_INICIAL,
    attributionControl: false,
  });

  // Sin `customAttribution`: el estilo de OpenFreeMap ya declara la suya y
  // añadirla la imprimía dos veces seguidas.
  mapa.addControl(new maplibregl.AttributionControl({ compact: true }));
  mapa.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");
  mapa.addControl(new maplibregl.ScaleControl({ maxWidth: 110, unit: "metric" }), "bottom-left");

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
    `<div class="metrica"><span class="valor">${resumen.paises_construidos}</span>` +
    `<span class="etiqueta">países con activo publicado</span>` +
    `<span class="apunte">de ${resumen.paises_con_manifest} con manifiesto escrito</span></div>` +
    `<div class="metrica"><span class="valor">${comoTexto(resumen.poblacion_en_la_malla)}</span>` +
    `<span class="etiqueta">personas en la malla hexagonal</span>` +
    `<span class="apunte">precalculadas, antes de que ocurra nada</span></div>` +
    `<div class="metrica"><span class="valor">${porcentaje(resumen.peor_desvio_pct)}</span>` +
    `<span class="etiqueta">peor desvío vs. cifra oficial</span>` +
    `<span class="apunte">el de Venezuela, y está explicado</span></div>` +
    `<div class="metrica"><span class="valor">${conReporte}</span>` +
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

function aplicarFiltro(iso3) {
  estado.paisFiltrado = iso3;
  let visibles = 0;
  for (const li of document.querySelectorAll(".lista-eventos li")) {
    const suyo = !iso3 || li.dataset.iso3 === iso3;
    li.hidden = !suyo;
    if (suyo) visibles += 1;
  }
  for (const boton of document.querySelectorAll("#filtro-paises button")) {
    boton.setAttribute("aria-pressed", String((boton.dataset.iso3 || "") === (iso3 || "")));
  }
  const vacio = $("sin-resultados");
  vacio.hidden = visibles > 0;
  if (!visibles) vacio.textContent = "Ese país todavía no tiene reportes publicados.";
  anunciar(`${visibles} ${visibles === 1 ? "reporte" : "reportes"} en la lista.`);
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
cargarEventos();
