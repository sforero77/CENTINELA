// Visor estatico de CENTINELA.
//
// Cero backend, cero llaves de API (D6). Los reportes se leen del directorio
// `reports/` que GitHub Pages publica junto a este sitio, y las capas de
// contexto llegan como PMTiles servidas por Overture.
//
// Todo lo que el visor muestra sale de artefactos que ya existian: `report.json`
// y `adm2.csv` son los mismos ficheros que se publican para descargar. El visor
// no tiene una fuente propia, y esa es la idea — lo que se ve en pantalla es
// exactamente lo que alguien se puede llevar.

const INDICE_REPORTES = "reports/index.json";

// Encuadre inicial: la ventana LATAM del sistema (RF-01).
const VISTA_INICIAL = { center: [-76.0, 4.0], zoom: 3.2 };

// Release de Overture del que salen las teselas de contexto.
//
// **Hay que subirlo cada trimestre, con el activo.** Overture solo conserva dos
// releases: cuando este caduque, el mapa se queda gris y los reportes siguen
// bien, porque las cifras no dependen de las teselas. Es la degradacion que se
// prefiere, pero hay que verla venir. Debe coincidir con el release que fijan
// los manifests.
const OVERTURE_RELEASE = "2026-08-19.0";
const teselas = (tema) =>
  `pmtiles://https://tiles.overturemaps.org/${OVERTURE_RELEASE}/${tema}.pmtiles`;

// Paleta sobria: el mapa es el fondo de una cifra, no el protagonista.
const COLOR = {
  agua: "#a8c4d4",
  tierra: "#e8e4dd",
  frontera: "#9a938a",
  fronteraDisputada: "#b9a06a",
  via: "#d3cec6",
  epicentro: "#c1440e",
};

// Rampa por intensidad maxima del municipio. Arranca en MMI 6 porque por debajo
// el sistema no publica cifra municipal: no es una escala completa de Mercalli,
// es el rango en el que este reporte dice algo.
const RAMPA_MMI = [
  { hasta: 6.5, color: "#f2e2b6", etiqueta: "MMI 6 – 6,5" },
  { hasta: 7.0, color: "#e8c07a", etiqueta: "MMI 6,5 – 7" },
  { hasta: 7.5, color: "#d98f52", etiqueta: "MMI 7 – 7,5" },
  { hasta: 8.0, color: "#c1440e", etiqueta: "MMI 7,5 – 8" },
  { hasta: 99, color: "#8c2703", etiqueta: "MMI 8 o mas" },
];

const colorPorMmi = (mmi) =>
  (RAMPA_MMI.find((b) => mmi < b.hasta) || RAMPA_MMI[RAMPA_MMI.length - 1]).color;

const nf = new Intl.NumberFormat("es");
const numero = (v, decimales = 0) =>
  Number.isFinite(v) ? nf.format(Number(v.toFixed(decimales))) : "—";

// Redondeo en prosa, igual que el markdown del reporte: publicar
// "2.415.793 personas" sugiere una precision que el metodo no tiene.
function comoTexto(v) {
  if (!Number.isFinite(v) || v <= 0) return "0";
  if (v >= 1e6) return `${(v / 1e6).toFixed(1).replace(".", ",")} millones`;
  if (v >= 1e3) return numero(Math.round(v / 1e3) * 1e3);
  return numero(Math.round(v));
}

const estado = { mapa: null, eventos: [], seleccionado: null };

// --- Datos -----------------------------------------------------------------

async function json(url) {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`HTTP ${r.status} en ${url}`);
  return r.json();
}

// El CSV municipal se parsea aqui en vez de publicar un GeoJSON paralelo: es el
// mismo fichero que se ofrece para descargar, asi que lo que pinta el mapa y lo
// que se lleva quien lo descarga no pueden divergir.
//
// La segunda fila son las etiquetas HXL (T1.3) y se salta: para un lector de CSV
// corriente es una fila mas, y para el visor tambien lo seria si no se mirara.
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

// Los nombres de municipio llevan comas ("Bogota, D.C."), asi que un split
// directo parte la fila por la mitad y desplaza todas las cifras una columna.
function partirLinea(linea) {
  const celdas = [];
  let actual = "";
  let entreComillas = false;
  for (const ch of linea) {
    if (ch === String.fromCharCode(34)) entreComillas = !entreComillas;
    else if (ch === "," && !entreComillas) {
      celdas.push(actual);
      actual = "";
    } else actual += ch;
  }
  celdas.push(actual);
  return celdas;
}

async function cargarEventos() {
  const aviso = document.getElementById("estado-lista");
  const lista = document.getElementById("lista-eventos");
  try {
    const eventos = await json(INDICE_REPORTES);
    estado.eventos = eventos;
    if (!eventos.length) {
      aviso.textContent = "Todavia no hay reportes publicados.";
      return;
    }
    aviso.hidden = true;
    for (const evento of eventos) lista.appendChild(filaEvento(evento));
    dibujarEpicentros(eventos);
  } catch (error) {
    // Sin backend no hay reintentos ni fallback: se dice lo que pasa.
    aviso.textContent =
      "Aun no hay indice de reportes publicado. El primer reporte real lo genera.";
    console.warn("No se pudo cargar el indice de reportes:", error);
  }
}

function filaEvento(evento) {
  const li = document.createElement("li");
  li.dataset.usgsId = evento.usgs_id;

  const enlace = document.createElement("a");
  enlace.href = `reports/${evento.usgs_id}/report.md`;
  enlace.textContent = `M${evento.mag} — ${evento.lugar}`;
  enlace.addEventListener("click", (ev) => {
    // Clic normal: abrir el evento en el mapa. Con Ctrl/Cmd o boton central,
    // dejar que el navegador haga lo suyo y se lleve el markdown.
    if (ev.metaKey || ev.ctrlKey || ev.button !== 0) return;
    ev.preventDefault();
    seleccionar(evento.usgs_id);
  });

  const meta = document.createElement("p");
  meta.className = "cargando";
  meta.textContent = [
    evento.utc,
    `ShakeMap v${evento.shakemap_version}`,
    Number.isFinite(evento.pop_mmi7p)
      ? `${comoTexto(evento.pop_mmi7p)} personas en MMI≥7`
      : null,
    evento.preliminar ? "preliminar" : null,
    evento.backtest ? "reconstruccion retrospectiva" : null,
  ]
    .filter(Boolean)
    .join(" · ");

  li.append(enlace, meta);

  // Un historico no dice lo mismo que un reporte en vivo, y quien lo abre desde
  // la lista tiene que saberlo antes de leer las cifras. La poblacion puede ser
  // de la epoca del sismo —GHS-POP publica de 1975 a 2030— pero edificaciones,
  // vias y equipamiento son los de hoy: OSM y Overture no guardan el pasado.
  if (evento.backtest) {
    const nota = document.createElement("p");
    nota.className = "aviso-backtest";
    nota.textContent =
      "Reconstruido despues del evento. La poblacion es de la epoca; las " +
      "edificaciones, vias y equipamiento son los actuales.";
    li.append(nota);
  }
  return li;
}

// --- Seleccion de un evento ------------------------------------------------

async function seleccionar(usgsId) {
  if (estado.seleccionado === usgsId) return cerrarDetalle();
  estado.seleccionado = usgsId;
  for (const li of document.querySelectorAll(".lista-eventos li")) {
    li.classList.toggle("activo", li.dataset.usgsId === usgsId);
  }

  const panel = document.getElementById("detalle");
  panel.hidden = false;
  document.getElementById("detalle-titulo").textContent = "Cargando…";
  document.getElementById("detalle-metricas").innerHTML = "";
  document.getElementById("detalle-filas").innerHTML = "";

  try {
    const [reporte, csv] = await Promise.all([
      json(`reports/${usgsId}/report.json`),
      fetch(`reports/${usgsId}/adm2.csv`).then((r) => (r.ok ? r.text() : "")),
    ]);
    const municipios = parsearCsv(csv);
    pintarDetalle(reporte, municipios);
    pintarMunicipios(municipios, reporte);
  } catch (error) {
    document.getElementById("detalle-titulo").textContent = "No se pudo abrir el reporte";
    document.getElementById("detalle-meta").textContent = String(error);
    console.warn("detalle:", error);
  }
}

function cerrarDetalle() {
  estado.seleccionado = null;
  document.getElementById("detalle").hidden = true;
  document.getElementById("leyenda").hidden = true;
  for (const li of document.querySelectorAll(".lista-eventos li")) li.classList.remove("activo");
  quitarCapa("municipios");
  if (estado.mapa) estado.mapa.easeTo({ ...VISTA_INICIAL, duration: 900 });
}

function pintarDetalle(reporte, municipios) {
  const ev = reporte.event;
  const t = reporte.totales;
  document.getElementById("detalle-titulo").textContent = `M${ev.mag} — ${ev.lugar}`;
  document.getElementById("detalle-meta").textContent = [
    `${ev.utc} UTC`,
    `profundidad ${numero(ev.depth_km, 1)} km`,
    `ShakeMap v${reporte.inputs.shakemap_version}`,
    `manifest ${reporte.inputs.exposure_manifest}`,
  ].join(" · ");

  const aviso = document.getElementById("detalle-aviso");
  const textos = [];
  if (reporte.preliminar) {
    textos.push(
      "Reporte preliminar sin ShakeMap: el corte es por radios alrededor del " +
        "epicentro, no por intensidad modelada."
    );
  }
  if (reporte.backtest) {
    textos.push(
      "Reconstruccion retrospectiva. La poblacion es de la epoca indicada en el " +
        "manifest; las edificaciones, vias y equipamiento son los actuales."
    );
  }
  aviso.hidden = textos.length === 0;
  aviso.textContent = textos.join(" ");

  // Un preliminar publica radios en lugar de bandas de intensidad. Ensenar
  // "MMI≥7: 0" seria una cifra falsa y creible.
  const metricas = reporte.preliminar
    ? (reporte.radios || []).map((r) => [`${r.radio_km} km del epicentro`, comoTexto(r.pop)])
    : [
        ["Poblacion en MMI≥6", comoTexto(t.pop_mmi6p)],
        ["Poblacion en MMI≥7", comoTexto(t.pop_mmi7p)],
        ["Poblacion en MMI≥8", comoTexto(t.pop_mmi8p)],
        ["65 anos o mas en MMI≥7", comoTexto(t.pop_65p_mmi7p)],
        ["Edificaciones en MMI≥7", comoTexto(t.bld_mmi7p)],
        ["Sedes de salud en MMI≥7", numero(t.health_mmi7p)],
        ["Sedes educativas en MMI≥7", numero(t.edu_mmi7p)],
        ["Vias en MMI≥7", `${comoTexto(t.road_km_mmi7p)} km`],
      ];

  document.getElementById("detalle-metricas").innerHTML = metricas
    .map(
      ([etiqueta, valor]) =>
        `<div class="metrica"><span class="valor">${valor}</span>` +
        `<span class="etiqueta">${etiqueta}</span></div>`
    )
    .join("");

  const filas = [...municipios]
    .sort((a, b) => (b.pop_mmi7p || 0) - (a.pop_mmi7p || 0))
    .slice(0, 15);
  document.getElementById("detalle-filas").innerHTML = filas
    .map(
      (m) =>
        `<tr><td>${m.nombre || m.adm2_id}</td>` +
        `<td class="num">${numero(m.mmi_max, 1)}</td>` +
        `<td class="num">${comoTexto(m.pop_mmi7p)}</td>` +
        `<td class="num">${comoTexto(m.bld_mmi7p)}</td></tr>`
    )
    .join("");

  document.getElementById("detalle-descargas").innerHTML =
    `Descargas: <a href="reports/${ev.usgs_id}/report.md">markdown</a> · ` +
    `<a href="reports/${ev.usgs_id}/report.json">JSON</a> · ` +
    `<a href="reports/${ev.usgs_id}/adm2.csv">CSV municipal (HXL)</a>`;
}

// --- Capas del mapa --------------------------------------------------------

function quitarCapa(id) {
  const m = estado.mapa;
  if (!m || !m.getSource(id)) return;
  if (m.getLayer(id)) m.removeLayer(id);
  m.removeSource(id);
}

function pintarMunicipios(municipios, reporte) {
  const m = estado.mapa;
  if (!m) return;
  quitarCapa("municipios");

  // Los reportes emitidos antes de que el CSV llevara coordenadas no se pueden
  // pintar. Se dice, no se calla: el panel y la tabla siguen sirviendo.
  const conCoords = municipios.filter((x) => Number.isFinite(x.lon) && Number.isFinite(x.lat));
  const leyenda = document.getElementById("leyenda");
  if (!conCoords.length) {
    leyenda.hidden = true;
    if (Number.isFinite(reporte.event.lon) && reporte.event.lon !== 0) {
      m.easeTo({ center: [reporte.event.lon, reporte.event.lat], zoom: 7, duration: 900 });
    }
    return;
  }

  const maximo = Math.max(...conCoords.map((x) => x.pop_mmi7p || 0), 1);
  m.addSource("municipios", {
    type: "geojson",
    data: {
      type: "FeatureCollection",
      features: conCoords.map((x) => ({
        type: "Feature",
        geometry: { type: "Point", coordinates: [x.lon, x.lat] },
        properties: {
          nombre: x.nombre || x.adm2_id,
          pop: x.pop_mmi7p || 0,
          bld: x.bld_mmi7p || 0,
          mmi: x.mmi_max || 0,
          color: colorPorMmi(x.mmi_max || 0),
        },
      })),
    },
  });

  // El radio va con la raiz de la poblacion, no con la poblacion: el area del
  // circulo es lo que el ojo compara, y un area proporcional al dato es la
  // unica lectura honesta.
  m.addLayer({
    id: "municipios",
    type: "circle",
    source: "municipios",
    paint: {
      "circle-radius": [
        "interpolate",
        ["linear"],
        ["sqrt", ["max", ["get", "pop"], 1]],
        1,
        3,
        Math.sqrt(maximo),
        26,
      ],
      "circle-color": ["get", "color"],
      "circle-opacity": 0.72,
      "circle-stroke-color": "#3a3632",
      "circle-stroke-width": 0.6,
    },
  });

  m.on("click", "municipios", (ev) => {
    const p = ev.features[0].properties;
    new maplibregl.Popup({ closeButton: false })
      .setLngLat(ev.lngLat)
      .setHTML(
        `<strong>${p.nombre}</strong><br>MMI max ${numero(Number(p.mmi), 1)}<br>` +
          `${comoTexto(Number(p.pop))} personas en MMI≥7<br>` +
          `${comoTexto(Number(p.bld))} edificaciones`
      )
      .addTo(m);
  });
  m.on("mouseenter", "municipios", () => (m.getCanvas().style.cursor = "pointer"));
  m.on("mouseleave", "municipios", () => (m.getCanvas().style.cursor = ""));

  leyenda.hidden = false;
  document.getElementById("leyenda-escala").innerHTML = RAMPA_MMI.map(
    (b) => `<li><span class="muestra" style="background:${b.color}"></span>${b.etiqueta}</li>`
  ).join("");

  const lons = conCoords.map((x) => x.lon);
  const lats = conCoords.map((x) => x.lat);
  m.fitBounds(
    [
      [Math.min(...lons), Math.min(...lats)],
      [Math.max(...lons), Math.max(...lats)],
    ],
    { padding: 60, maxZoom: 9, duration: 900 }
  );
}

// Epicentros de los reportes publicados. El circulo escala con la poblacion
// expuesta a MMI>=7, no con la magnitud: dos sismos de la misma magnitud sobre
// poblaciones distintas no son el mismo evento para quien responde.
function dibujarEpicentros(eventos) {
  const m = estado.mapa;
  const conCoordenadas = eventos.filter((e) => e.lon || e.lat);
  if (!m || !conCoordenadas.length) return;

  const pintar = () => {
    if (m.getSource("epicentros")) return;
    m.addSource("epicentros", {
      type: "geojson",
      data: {
        type: "FeatureCollection",
        features: conCoordenadas.map((e) => ({
          type: "Feature",
          geometry: { type: "Point", coordinates: [e.lon, e.lat] },
          properties: {
            usgs_id: e.usgs_id,
            etiqueta: `M${e.mag} — ${e.lugar}`,
            pop: e.pop_mmi7p || 0,
          },
        })),
      },
    });
    m.addLayer({
      id: "epicentros",
      type: "circle",
      source: "epicentros",
      paint: {
        "circle-radius": [
          "interpolate",
          ["linear"],
          ["sqrt", ["max", ["get", "pop"], 1]],
          1,
          4,
          2000,
          22,
        ],
        "circle-color": COLOR.epicentro,
        "circle-opacity": 0.28,
        "circle-stroke-color": COLOR.epicentro,
        "circle-stroke-width": 1.4,
      },
    });
    m.on("click", "epicentros", (ev) => seleccionar(ev.features[0].properties.usgs_id));
    m.on("mouseenter", "epicentros", () => (m.getCanvas().style.cursor = "pointer"));
    m.on("mouseleave", "epicentros", () => (m.getCanvas().style.cursor = ""));
  };

  if (m.isStyleLoaded()) pintar();
  else m.on("load", pintar);
}

function iniciarMapa() {
  const contenedor = document.getElementById("mapa");
  if (!contenedor || typeof maplibregl === "undefined") return null;

  // Registrar el protocolo pmtiles:// antes de crear el mapa.
  if (typeof pmtiles !== "undefined") {
    const protocolo = new pmtiles.Protocol();
    maplibregl.addProtocol("pmtiles", protocolo.tile);
  }

  const mapa = new maplibregl.Map({
    container: "mapa",
    style: {
      version: 8,
      // Overture publica sus propias teselas por release, asi que el contexto
      // del mapa no hay que generarlo con tippecanoe ni servirlo desde aqui.
      // Las coropletas de exposicion si son nuestras: son datos nuestros.
      sources: {
        base: {
          type: "vector",
          url: teselas("base"),
          attribution:
            '<a href="https://overturemaps.org">Overture Maps</a> (ODbL · OpenStreetMap)',
        },
        divisiones: { type: "vector", url: teselas("divisions") },
        vias: { type: "vector", url: teselas("transportation") },
      },
      layers: [
        { id: "fondo", type: "background", paint: { "background-color": COLOR.agua } },
        {
          id: "tierra",
          type: "fill",
          source: "base",
          "source-layer": "land",
          paint: { "fill-color": COLOR.tierra },
        },
        {
          id: "agua",
          type: "fill",
          source: "base",
          "source-layer": "water",
          paint: { "fill-color": COLOR.agua },
        },
        {
          id: "vias-principales",
          type: "line",
          source: "vias",
          "source-layer": "segment",
          minzoom: 5,
          // De 671.295 km de via en Chile, 60 % son calles residenciales. A la
          // escala de este mapa solo estorban.
          filter: ["in", ["get", "class"], ["literal", ["motorway", "trunk", "primary"]]],
          paint: {
            "line-color": COLOR.via,
            "line-width": ["interpolate", ["linear"], ["zoom"], 5, 0.4, 12, 1.6],
          },
        },
        // Una frontera en disputa se dibuja distinto en vez de elegir un lado:
        // el sistema no tiene por que tener una opinion territorial.
        //
        // Son dos capas y no una con un `case` porque `line-dasharray` no admite
        // expresiones por dato en MapLibre, y una propiedad invalida no degrada
        // esa capa: invalida el estilo entero y el mapa sale en negro.
        {
          id: "fronteras",
          type: "line",
          source: "divisiones",
          "source-layer": "division_boundary",
          filter: ["!=", ["get", "is_disputed"], true],
          paint: {
            "line-color": COLOR.frontera,
            "line-width": ["interpolate", ["linear"], ["zoom"], 2, 0.4, 8, 1.2],
          },
        },
        {
          id: "fronteras-en-disputa",
          type: "line",
          source: "divisiones",
          "source-layer": "division_boundary",
          filter: ["==", ["get", "is_disputed"], true],
          paint: {
            "line-color": COLOR.fronteraDisputada,
            "line-dasharray": [2, 2],
            "line-width": ["interpolate", ["linear"], ["zoom"], 2, 0.4, 8, 1.2],
          },
        },
      ],
    },
    ...VISTA_INICIAL,
    attributionControl: { compact: true },
  });

  mapa.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");
  mapa.on("error", (e) => console.warn("mapa:", e && e.error && e.error.message));
  return mapa;
}

estado.mapa = iniciarMapa();
document.getElementById("cerrar-detalle").addEventListener("click", cerrarDetalle);
cargarEventos();
