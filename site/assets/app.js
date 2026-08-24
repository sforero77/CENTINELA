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
