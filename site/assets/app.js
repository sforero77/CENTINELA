// Visor estatico de CENTINELA.
//
// Cero backend, cero llaves de API (D6). Los reportes se leen del directorio
// `reports/` que GitHub Pages publica junto a este sitio, y las capas grandes
// llegan como PMTiles: un solo archivo servible desde Pages o R2.

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

async function cargarEventos(mapa) {
  const estado = document.getElementById("estado-lista");
  const lista = document.getElementById("lista-eventos");

  try {
    const respuesta = await fetch(INDICE_REPORTES);
    if (!respuesta.ok) throw new Error(`HTTP ${respuesta.status}`);
    const eventos = await respuesta.json();

    if (!eventos.length) {
      estado.textContent = "Todavia no hay reportes publicados.";
      return;
    }

    estado.hidden = true;
    for (const evento of eventos) {
      lista.appendChild(filaEvento(evento));
    }
    dibujarEpicentros(mapa, eventos);
  } catch (error) {
    // Sin backend no hay reintentos ni fallback: se dice lo que pasa.
    estado.textContent =
      "Aun no hay indice de reportes publicado. El primer reporte real lo genera.";
    console.warn("No se pudo cargar el indice de reportes:", error);
  }
}

function filaEvento(evento) {
  const li = document.createElement("li");
  const enlace = document.createElement("a");
  enlace.href = `reports/${evento.usgs_id}/report.md`;
  enlace.textContent = `M${evento.mag} — ${evento.lugar}`;

  const meta = document.createElement("p");
  meta.className = "cargando";
  meta.textContent = [
    evento.utc,
    `ShakeMap v${evento.shakemap_version}`,
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
    const aviso = document.createElement("p");
    aviso.className = "aviso-backtest";
    aviso.textContent =
      "Reconstruido despues del evento. La poblacion es de la epoca; las " +
      "edificaciones, vias y equipamiento son los actuales.";
    li.append(aviso);
  }

  return li;
}

function iniciarMapa() {
  const contenedor = document.getElementById("mapa");
  if (!contenedor || typeof maplibregl === "undefined") return;

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
      // Las coropletas de exposicion si seran nuestras: son datos nuestros.
      sources: {
        base: {
          type: "vector",
          url: teselas("base"),
          attribution:
            '<a href="https://overturemaps.org">Overture Maps</a> ' +
            "(ODbL · OpenStreetMap)",
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
          paint: { "line-color": COLOR.via, "line-width": ["interpolate", ["linear"], ["zoom"], 5, 0.4, 12, 1.6] },
        },
        // Una frontera en disputa se dibuja distinto en vez de elegir un lado:
        // el sistema no tiene por que tener una opinion territorial.
        //
        // Son dos capas y no una con un `case` porque `line-dasharray` no
        // admite expresiones por dato en MapLibre, y una propiedad invalida no
        // degrada esa capa: invalida el estilo entero y el mapa sale en negro.
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

// Epicentros de los reportes publicados. El circulo escala con la poblacion
// expuesta a MMI>=7, no con la magnitud: dos sismos de la misma magnitud sobre
// poblaciones distintas no son el mismo evento para quien responde.
function dibujarEpicentros(mapa, eventos) {
  const conCoordenadas = eventos.filter((e) => e.lon || e.lat);
  if (!mapa || !conCoordenadas.length) return;

  const pintar = () => {
    if (mapa.getSource("epicentros")) return;
    mapa.addSource("epicentros", {
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
    mapa.addLayer({
      id: "epicentros",
      type: "circle",
      source: "epicentros",
      paint: {
        "circle-radius": [
          "interpolate", ["linear"], ["sqrt", ["max", ["get", "pop"], 1]],
          1, 4, 2000, 22,
        ],
        "circle-color": COLOR.epicentro,
        "circle-opacity": 0.35,
        "circle-stroke-color": COLOR.epicentro,
        "circle-stroke-width": 1.2,
      },
    });

    mapa.on("click", "epicentros", (ev) => {
      const p = ev.features[0].properties;
      new maplibregl.Popup({ closeButton: false })
        .setLngLat(ev.lngLat)
        .setHTML(
          `<strong>${p.etiqueta}</strong><br>` +
            `<a href="reports/${p.usgs_id}/report.md">Ver reporte</a>`
        )
        .addTo(mapa);
    });
    mapa.on("mouseenter", "epicentros", () => (mapa.getCanvas().style.cursor = "pointer"));
    mapa.on("mouseleave", "epicentros", () => (mapa.getCanvas().style.cursor = ""));
  };

  if (mapa.isStyleLoaded()) pintar();
  else mapa.on("load", pintar);
}

cargarEventos(iniciarMapa());
