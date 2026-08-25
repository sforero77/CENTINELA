// Visor de CENTINELA.
//
// Cero backend, cero llaves de API (D6). Todo lo que se ve sale de artefactos
// que ya se publican para descargar —`report.json`, `adm2.csv`, `celdas.json`—
// asi que lo que hay en pantalla no puede divergir de lo que se lleva quien los
// baja. El visor no tiene una fuente propia, y esa es la idea.

const INDICE_REPORTES = "reports/index.json";

// Encuadre inicial: la ventana LATAM del sistema (RF-01).
const VISTA_INICIAL = { center: [-76.0, 4.0], zoom: 3.1 };

// Mapa base: estilo Positron de OpenFreeMap.
//
// **Por que este y no las teselas de Overture.** Overture tesela para el
// detalle: medido, una tesela de `base` a zoom 4 pesa 4,3 MB y no trae una sola
// etiqueta. Una de OpenFreeMap a zoom 6 pesa 101 KB y trae toponimos, vias,
// agua y relieve. Cuarenta veces mas ligera y con nombres, que es lo que
// convierte un mapa en algo que se puede leer.
//
// Sigue sin llaves ni cuota (D6): OpenFreeMap sirve ficheros estaticos sin
// registro. Si el servicio cae, el mapa se queda gris y **los reportes siguen
// bien**, porque ninguna cifra depende de las teselas.
//
// Positron y no un estilo de colores a proposito: el mapa es el fondo del dato.
const ESTILO_BASE = "https://tiles.openfreemap.org/styles/positron";

// Azul apagado: distingue la costa sin robarle contraste al dato.
const AGUA = "#cfe0ea";
const EPICENTRO = "#c1440e";

// --- Capas que el visor sabe pintar ----------------------------------------
//
// Cada una es una columna de `celdas.json`, que es una columna del activo. El
// selector no ofrece nada que el dato no tenga.
//
// Los cortes son escalonados y no una rampa continua: una rampa insinua una
// precision por celda que la fuente no tiene, y ademas no se puede leer en una
// leyenda. Los de poblacion y edificaciones van por decadas porque el rango va
// de una unidad a decenas de miles.
const CAPAS = {
  mmi: {
    titulo: "Intensidad",
    columna: "mmi",
    decimal: true,
    cortes: [6, 6.5, 7, 7.5, 8],
    colores: ["#fde3a7", "#f6c177", "#e89b52", "#cf6b3c", "#a33222"],
    nota: "Mercalli modificada. Por debajo de 6 el sistema no publica cifra.",
  },
  pop: {
    titulo: "Poblacion",
    columna: "pop",
    cortes: [1, 10, 100, 1000, 10000],
    colores: ["#e8eef2", "#bcd2de", "#8ab3c9", "#5b8fae", "#2f6485"],
    nota: "Celda H3 r7, unos 5,2 km². GHS-POP epoca 2025.",
  },
  bld: {
    titulo: "Edificaciones",
    columna: "bld",
    cortes: [1, 10, 100, 1000, 10000],
    colores: ["#efeae4", "#d8cbbc", "#bfa88f", "#9c8264", "#6f5a41"],
    nota: "Overture sobre OpenStreetMap. Donde OSM no mapeo, se queda corto.",
  },
  built_m2: {
    titulo: "Superficie construida",
    columna: "built_m2",
    cortes: [1000, 10000, 100000, 1000000, 5000000],
    colores: ["#f0ebe6", "#dcd0c2", "#c3ab90", "#a2825f", "#75563a"],
    nota: "GHS-BUILT-S, vista por satelite: ve el barrio que OSM no mapeo.",
  },
  vias_km: {
    titulo: "Vias",
    columna: "vias_km",
    cortes: [1, 5, 20, 60, 150],
    colores: ["#eeeae6", "#d5cdc4", "#b6a99b", "#8f7f6e", "#655749"],
    nota: "Overture transportation, en km por celda. Incluye calle residencial.",
  },
};

const ORDEN_CAPAS = ["mmi", "pop", "bld", "built_m2", "vias_km"];

const nf = new Intl.NumberFormat("es");
const numero = (v, d = 0) => (Number.isFinite(v) ? nf.format(Number(v.toFixed(d))) : "—");

// Redondeo en prosa, igual que el markdown del reporte: publicar
// "2.415.793 personas" sugiere una precision que el metodo no tiene.
function comoTexto(v) {
  if (!Number.isFinite(v) || v <= 0) return "0";
  if (v >= 1e6) return `${(v / 1e6).toFixed(1).replace(".", ",")} M`;
  if (v >= 1e3) return numero(Math.round(v / 1e3) * 1e3);
  return numero(Math.round(v));
}

const estado = { mapa: null, eventos: [], seleccionado: null, capa: "mmi" };

// --- Datos ------------------------------------------------------------------

async function json(url) {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`HTTP ${r.status} en ${url}`);
  return r.json();
}

// El CSV municipal se parsea aqui en vez de publicar un GeoJSON paralelo: es el
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

// --- Malla de celdas --------------------------------------------------------

// El fichero trae indices H3, no geometrias: el contorno de un hexagono en
// GeoJSON son ~150 bytes y su indice son quince caracteres. Se reconstruye aqui
// con h3-js, que es exactamente para lo que sirve un indice jerarquico.
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
        // `true` devuelve [lng, lat], que es el orden de GeoJSON. Sin el, los
        // hexagonos aparecen en el oceano Indico.
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

function pintarLeyenda(capa) {
  document.getElementById("leyenda").hidden = false;
  document.getElementById("leyenda-titulo").textContent = capa.titulo;
  document.getElementById("leyenda-nota").textContent = capa.nota;
  document.getElementById("leyenda-escala").innerHTML = capa.cortes
    .map((corte, i) => {
      const sig = capa.cortes[i + 1];
      const fmt = (v) => (capa.decimal ? numero(v, 1) : comoTexto(v));
      const texto = sig ? `${fmt(corte)} – ${fmt(sig)}` : `${fmt(corte)} o mas`;
      return `<li><span class="muestra" style="background:${capa.colores[i]}"></span>${texto}</li>`;
    })
    .join("");
}

function pintarSelectorCapas() {
  const caja = document.getElementById("capas");
  caja.hidden = false;
  caja.innerHTML = ORDEN_CAPAS.map(
    (id) =>
      `<button type="button" data-capa="${id}" aria-pressed="${id === estado.capa}">` +
      `${CAPAS[id].titulo}</button>`
  ).join("");
  for (const boton of caja.querySelectorAll("button")) {
    boton.addEventListener("click", () => cambiarCapa(boton.dataset.capa));
  }
}

function cambiarCapa(id) {
  estado.capa = id;
  for (const boton of document.querySelectorAll("#capas button")) {
    boton.setAttribute("aria-pressed", String(boton.dataset.capa === id));
  }
  const capa = CAPAS[id];
  const m = estado.mapa;
  if (m && m.getLayer("celdas")) {
    m.setPaintProperty("celdas", "fill-color", expresionColor(capa));
    // Una celda con cero en la capa elegida no se pinta: en "vias" media region
    // esta vacia, y pintarla del primer color la haria parecer un valor bajo en
    // vez de una ausencia.
    m.setFilter("celdas", [">", ["coalesce", ["get", capa.columna], 0], 0]);
  }
  pintarLeyenda(capa);
}

// --- Eventos ----------------------------------------------------------------

async function cargarEventos() {
  const aviso = document.getElementById("estado-lista");
  const lista = document.getElementById("lista-eventos");
  const selector = document.getElementById("selector-evento");
  try {
    const eventos = await json(INDICE_REPORTES);
    estado.eventos = eventos;
    if (!eventos.length) {
      aviso.textContent = "Todavia no hay reportes publicados.";
      return;
    }
    aviso.hidden = true;
    for (const evento of eventos) {
      lista.appendChild(filaEvento(evento));
      const opcion = document.createElement("option");
      opcion.value = evento.usgs_id;
      opcion.textContent = `M${evento.mag} — ${evento.lugar}`;
      selector.appendChild(opcion);
    }
    selector.addEventListener("change", () => {
      if (selector.value) seleccionar(selector.value);
      else cerrarDetalle();
    });
    dibujarEpicentros(eventos);
  } catch (error) {
    aviso.textContent =
      "Aun no hay indice de reportes publicado. El primer reporte real lo genera.";
    console.warn("indice:", error);
  }
}

function filaEvento(evento) {
  const li = document.createElement("li");
  li.dataset.usgsId = evento.usgs_id;

  const enlace = document.createElement("a");
  enlace.href = `reports/${evento.usgs_id}/report.md`;
  enlace.textContent = `M${evento.mag} — ${evento.lugar}`;
  enlace.addEventListener("click", (ev) => {
    // Clic normal abre el evento en el tablero. Con Ctrl/Cmd, que el navegador
    // haga lo suyo y se lleve el markdown.
    if (ev.metaKey || ev.ctrlKey || ev.button !== 0) return;
    ev.preventDefault();
    seleccionar(evento.usgs_id);
  });

  const meta = document.createElement("p");
  meta.className = "evento-meta";
  meta.textContent = [
    evento.utc,
    `ShakeMap v${evento.shakemap_version}`,
    Number.isFinite(evento.pop_mmi7p) ? `${comoTexto(evento.pop_mmi7p)} en MMI≥7` : null,
    evento.preliminar ? "preliminar" : null,
  ].filter(Boolean).join(" · ");

  li.append(enlace, meta);
  if (evento.backtest) {
    const marca = document.createElement("span");
    marca.className = "distintivo";
    marca.title =
      "Reconstruido despues del evento. La poblacion es de la epoca; las " +
      "edificaciones, vias y equipamiento son los actuales.";
    marca.textContent = "reconstruccion retrospectiva";
    li.append(marca);
  }
  return li;
}

async function seleccionar(usgsId) {
  estado.seleccionado = usgsId;
  document.getElementById("selector-evento").value = usgsId;
  for (const li of document.querySelectorAll(".lista-eventos li")) {
    li.classList.toggle("activo", li.dataset.usgsId === usgsId);
  }
  document.getElementById("lateral-vacio").hidden = true;
  document.getElementById("lateral-detalle").hidden = false;
  document.getElementById("detalle-titulo").textContent = "Cargando…";

  try {
    const [reporte, csv, celdas] = await Promise.all([
      json(`reports/${usgsId}/report.json`),
      fetch(`reports/${usgsId}/adm2.csv`).then((r) => (r.ok ? r.text() : "")),
      fetch(`reports/${usgsId}/celdas.json`).then((r) => (r.ok ? r.json() : null)),
    ]);
    pintarLateral(reporte, parsearCsv(csv));
    pintarCeldas(celdas, reporte);
  } catch (error) {
    document.getElementById("detalle-titulo").textContent = "No se pudo abrir el reporte";
    document.getElementById("detalle-meta").textContent = String(error);
    console.warn("detalle:", error);
  }
}

function cerrarDetalle() {
  estado.seleccionado = null;
  document.getElementById("lateral-vacio").hidden = false;
  document.getElementById("lateral-detalle").hidden = true;
  document.getElementById("leyenda").hidden = true;
  document.getElementById("capas").hidden = true;
  for (const li of document.querySelectorAll(".lista-eventos li")) li.classList.remove("activo");
  quitarCapa("celdas");
  if (estado.mapa) estado.mapa.easeTo({ ...VISTA_INICIAL, duration: 800 });
}

function pintarLateral(reporte, municipios) {
  const ev = reporte.event;
  const t = reporte.totales;
  document.getElementById("detalle-titulo").textContent = `M${ev.mag} — ${ev.lugar}`;
  document.getElementById("detalle-meta").textContent = [
    `${ev.utc} UTC`,
    `${numero(ev.depth_km, 1)} km de profundidad`,
    `ShakeMap v${reporte.inputs.shakemap_version}`,
    reporte.inputs.exposure_manifest,
  ].join(" · ");

  const marca = document.getElementById("detalle-distintivo");
  marca.hidden = !(reporte.backtest || reporte.preliminar);
  if (reporte.preliminar) {
    marca.textContent = "preliminar, sin ShakeMap";
    marca.title = "El corte es por radios alrededor del epicentro, no por intensidad modelada.";
  } else if (reporte.backtest) {
    marca.textContent = "reconstruccion retrospectiva";
    marca.title =
      "La poblacion es de la epoca indicada en el manifest; las edificaciones, " +
      "vias y equipamiento son los actuales.";
  }

  // Un preliminar publica radios en lugar de bandas de intensidad. Ensenar
  // "MMI≥7: 0" seria una cifra falsa y creible.
  const metricas = reporte.preliminar
    ? (reporte.radios || []).map((r) => [comoTexto(r.pop), `a ${r.radio_km} km`])
    : [
        [comoTexto(t.pop_mmi7p), "personas en MMI≥7"],
        [comoTexto(t.pop_65p_mmi7p), "65 anos o mas"],
        [comoTexto(t.bld_mmi7p), "edificaciones"],
        [numero(t.health_mmi7p), "sedes de salud"],
        [numero(t.edu_mmi7p), "sedes educativas"],
        [`${numero(t.road_km_mmi7p)} km`, "de via"],
      ];

  document.getElementById("detalle-metricas").innerHTML = metricas
    .map(([valor, etiqueta]) =>
      `<div class="metrica"><span class="valor">${valor}</span>` +
      `<span class="etiqueta">${etiqueta}</span></div>`)
    .join("");

  const top = [...municipios].sort((a, b) => (b.pop_mmi7p || 0) - (a.pop_mmi7p || 0)).slice(0, 8);
  const maximo = Math.max(...top.map((m) => m.pop_mmi7p || 0), 1);
  document.getElementById("detalle-barras").innerHTML = top
    .map((m) => {
      const pct = (100 * (m.pop_mmi7p || 0)) / maximo;
      const banda = CAPAS.mmi.cortes.filter((c) => (m.mmi_max || 0) >= c).length - 1;
      const color = CAPAS.mmi.colores[Math.max(0, banda)];
      return (
        `<li><div class="barra-fila"><span class="barra-nombre">${m.nombre || m.adm2_id}</span>` +
        `<span class="barra-valor">${comoTexto(m.pop_mmi7p)}</span></div>` +
        `<div class="barra-pista"><div class="barra-relleno" ` +
        `style="width:${pct.toFixed(1)}%;background:${color}"></div></div></li>`
      );
    })
    .join("");

  document.getElementById("detalle-descargas").innerHTML =
    `<a href="reports/${ev.usgs_id}/report.md">Reporte</a> · ` +
    `<a href="reports/${ev.usgs_id}/report.json">JSON</a> · ` +
    `<a href="reports/${ev.usgs_id}/adm2.csv">CSV municipal (HXL)</a> · ` +
    `<a href="reports/${ev.usgs_id}/celdas.json">Malla H3</a>`;

  pintarContraste(ev.usgs_id, t);
}

// Exposicion no es dano, y para dos eventos hay medida ajena que lo demuestra.
// Las cifras y su metodo estan en VERIFICACIONES.md; aqui se ensenan al lado de
// las de exposicion, que es donde la diferencia se entiende sin explicarla.
const CONTRASTES = {
  us6000tjl2: { fuente: "Microsoft AI for Good Lab", zona: "Cali", evaluadas: 97351, danadas: 266 },
  us6000t7zp: { fuente: "Microsoft AI for Good Lab", zona: "La Guaira", evaluadas: 26143, danadas: 965 },
};

function pintarContraste(usgsId, totales) {
  const c = CONTRASTES[usgsId];
  const bloque = document.getElementById("bloque-contraste");
  bloque.hidden = !c;
  if (!c) return;
  const pct = ((100 * c.danadas) / c.evaluadas).toFixed(2).replace(".", ",");
  document.getElementById("detalle-contraste").innerHTML =
    `Este reporte publica <strong>${comoTexto(totales.bld_mmi7p)} edificaciones ` +
    `expuestas</strong> a MMI≥7 en todo el pais. En ${c.zona}, ${c.fuente} evaluo ` +
    `${numero(c.evaluadas)} por imagen satelital y detecto dano en ` +
    `<strong>${numero(c.danadas)} (${pct} %)</strong>. Son dos preguntas distintas: ` +
    `exposicion es quien quedo dentro de la franja; dano es a quien le paso algo.`;
}

// --- Mapa -------------------------------------------------------------------

function quitarCapa(id) {
  const m = estado.mapa;
  if (!m || !m.getSource(id)) return;
  for (const sufijo of ["", "-borde"]) {
    if (m.getLayer(id + sufijo)) m.removeLayer(id + sufijo);
  }
  m.removeSource(id);
}

function pintarCeldas(datos, reporte) {
  const m = estado.mapa;
  if (!m) return;
  quitarCapa("celdas");

  const geo = datos && celdasAGeoJson(datos);
  if (!geo || !geo.features.length) {
    // Sin malla el tablero sigue sirviendo: las cifras y las barras salen del
    // reporte. Se vuela al epicentro y no se finge una capa que no hay.
    document.getElementById("capas").hidden = true;
    document.getElementById("leyenda").hidden = true;
    if (Number.isFinite(reporte.event.lon) && reporte.event.lon !== 0) {
      m.easeTo({ center: [reporte.event.lon, reporte.event.lat], zoom: 7.5, duration: 800 });
    }
    return;
  }

  m.addSource("celdas", { type: "geojson", data: geo });
  m.addLayer({
    id: "celdas",
    type: "fill",
    source: "celdas",
    paint: { "fill-color": expresionColor(CAPAS[estado.capa]), "fill-opacity": 0.78 },
    filter: [">", ["coalesce", ["get", CAPAS[estado.capa].columna], 0], 0],
  });
  m.addLayer({
    id: "celdas-borde",
    type: "line",
    source: "celdas",
    paint: { "line-color": "#ffffff", "line-width": 0.35, "line-opacity": 0.5 },
  });

  m.on("click", "celdas", (ev) => {
    const p = ev.features[0].properties;
    new maplibregl.Popup({ closeButton: false, maxWidth: "17rem" })
      .setLngLat(ev.lngLat)
      .setHTML(
        "<strong>Celda H3 r7</strong><br>" +
        `MMI max ${numero(Number(p.mmi), 1)}<br>` +
        `${comoTexto(Number(p.pop))} personas<br>` +
        `${comoTexto(Number(p.bld))} edificaciones<br>` +
        `${numero(Number(p.vias_km), 1)} km de via`
      )
      .addTo(m);
  });
  m.on("mouseenter", "celdas", () => (m.getCanvas().style.cursor = "pointer"));
  m.on("mouseleave", "celdas", () => (m.getCanvas().style.cursor = ""));

  pintarSelectorCapas();
  pintarLeyenda(CAPAS[estado.capa]);

  const lons = geo.features.flatMap((f) => f.geometry.coordinates[0].map((c) => c[0]));
  const lats = geo.features.flatMap((f) => f.geometry.coordinates[0].map((c) => c[1]));
  m.fitBounds(
    [[Math.min(...lons), Math.min(...lats)], [Math.max(...lons), Math.max(...lats)]],
    { padding: 48, maxZoom: 10, duration: 800 }
  );
}

// El circulo del epicentro escala con la poblacion expuesta a MMI≥7, no con la
// magnitud: dos sismos de la misma magnitud sobre poblaciones distintas no son
// el mismo evento para quien responde.
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
          properties: { usgs_id: e.usgs_id, pop: e.pop_mmi7p || 0 },
        })),
      },
    });
    m.addLayer({
      id: "epicentros",
      type: "circle",
      source: "epicentros",
      paint: {
        "circle-radius": [
          "interpolate", ["linear"], ["sqrt", ["max", ["get", "pop"], 1]], 1, 5, 2000, 20,
        ],
        "circle-color": EPICENTRO,
        "circle-opacity": 0.25,
        "circle-stroke-color": EPICENTRO,
        "circle-stroke-width": 1.5,
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
  if (!document.getElementById("mapa") || typeof maplibregl === "undefined") return null;

  const mapa = new maplibregl.Map({
    container: "mapa",
    style: ESTILO_BASE,
    ...VISTA_INICIAL,
    attributionControl: false,
  });

  // Sin `customAttribution`: el estilo de OpenFreeMap ya declara la suya y
  // anadirla la imprimia dos veces seguidas.
  mapa.addControl(new maplibregl.AttributionControl({ compact: true }));
  mapa.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");

  // Positron pinta el agua casi del mismo gris que la tierra. Para un sistema
  // cuya mitad de la exposicion es costera, la linea de costa tiene que verse.
  mapa.on("style.load", () => {
    for (const capa of mapa.getStyle().layers) {
      if (capa.type === "fill" && (capa.id === "water" || capa.id.startsWith("water_"))) {
        try {
          mapa.setPaintProperty(capa.id, "fill-color", AGUA);
        } catch (e) {
          /* el estilo puede cambiar; no es critico */
        }
      }
    }
  });

  // El aviso se quita cuando el mapa dibuja algo, no cuando termina de cargarlo
  // todo: `idle` no llega mientras siguen entrando teselas, y dejarlo puesto
  // haria parecer roto un mapa que ya se ve. Con red de seguridad, porque un
  // "cargando" eterno es peor que un mapa gris.
  const listo = () => {
    const aviso = document.getElementById("cargando");
    if (aviso) aviso.hidden = true;
  };
  mapa.once("load", listo);
  setTimeout(listo, 8000);

  mapa.on("error", (e) => console.warn("mapa:", e && e.error && e.error.message));
  return mapa;
}

estado.mapa = iniciarMapa();
cargarEventos();
