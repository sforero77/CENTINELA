// Visor estatico de CENTINELA.
//
// Cero backend, cero llaves de API (D6). Los reportes se leen del directorio
// `reports/` que GitHub Pages publica junto a este sitio, y las capas grandes
// llegan como PMTiles: un solo archivo servible desde Pages o R2.

const INDICE_REPORTES = "reports/index.json";

// Encuadre inicial: la ventana LATAM del sistema (RF-01).
const VISTA_INICIAL = { center: [-76.0, 4.0], zoom: 3.2 };

async function cargarEventos() {
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
  ]
    .filter(Boolean)
    .join(" · ");

  li.append(enlace, meta);
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

  new maplibregl.Map({
    container: "mapa",
    style: {
      version: 8,
      sources: {},
      layers: [
        { id: "fondo", type: "background", paint: { "background-color": "#c9c4bd" } },
      ],
    },
    ...VISTA_INICIAL,
    attributionControl: { compact: true },
  });

  // Pendiente (Fase 1): agregar las capas PMTiles de coropletas r7/r6 por MMI
  // y exposicion, y la ficha por municipio.
}

iniciarMapa();
cargarEventos();
