// Pagina de estado: lee el status.json que escribe el disparador.
//
// La transparencia sobre la latencia es parte del producto (RNF-02): esta
// pagina publica la distribucion real, no la prometida, y no descuenta la
// demora del cron aunque no la controlemos.

const FUENTE = "status.json";

function texto(valor, sufijo = "") {
  return valor === null || valor === undefined ? "—" : `${valor}${sufijo}`;
}

function metrica(valor, etiqueta, clase = "") {
  return `<div class="metrica">
    <div class="valor ${clase}">${valor}</div>
    <div class="etiqueta">${etiqueta}</div>
  </div>`;
}

function pintarResumen(datos) {
  const { medido, objetivo } = datos;
  const nodo = document.getElementById("resumen");

  if (!medido.eventos_publicados) {
    // Decir "todavia no hay datos" es mas honesto que mostrar un cero que
    // parece un logro.
    nodo.innerHTML = `<p>Aun no se ha publicado ningun reporte en vivo, asi que
      no hay latencia que medir. El objetivo es ${objetivo.p50_min} min (p50) y
      ${objetivo.p95_min} min (p95).</p>` +
      (medido.backtests_excluidos
        ? `<p class="nota">${medido.backtests_excluidos} reconstruccion(es)
           retrospectiva(s) quedan fuera de la estadistica: un backtest se publica
           dias despues del sismo y su latencia no mide nada del sistema.</p>`
        : "");
    nodo.classList.remove("cargando");
    return;
  }

  const clase = (v, objetivo) => (v === null ? "" : v <= objetivo ? "cumple" : "incumple");
  nodo.innerHTML = `<div class="metricas">
    ${metrica(texto(medido.p50_min, " min"), `p50 · objetivo ${objetivo.p50_min}`,
              clase(medido.p50_min, objetivo.p50_min))}
    ${metrica(texto(medido.p95_min, " min"), `p95 · objetivo ${objetivo.p95_min}`,
              clase(medido.p95_min, objetivo.p95_min))}
    ${metrica(texto(medido.peor_min, " min"), "peor caso")}
    ${metrica(medido.eventos_publicados, "reportes en vivo")}
  </div>
  <p class="nota">${datos.nota}</p>`;
  nodo.classList.remove("cargando");
}

function pintarEventos(datos) {
  const estado = document.getElementById("estado-eventos");
  const tabla = document.getElementById("tabla-eventos");
  if (!datos.eventos.length) {
    estado.textContent = "Todavia no hay eventos publicados.";
    return;
  }
  const cuerpo = tabla.querySelector("tbody");
  for (const e of datos.eventos) {
    const fila = document.createElement("tr");
    const etiqueta = e.backtest ? " (backtest)" : "";
    fila.innerHTML = `<td>${e.usgs_id}${etiqueta}</td><td>${e.origen_utc}</td>
      <td>${e.publicado_utc}</td><td class="num">${e.minutos} min</td>`;
    cuerpo.appendChild(fila);
  }
  estado.hidden = true;
  tabla.hidden = false;
}

function pintarLatidos(datos) {
  const estado = document.getElementById("estado-latidos");
  const lista = document.getElementById("lista-latidos");
  const latidos = [...datos.latidos].reverse().slice(0, 20);
  if (!latidos.length) {
    estado.textContent = "Sin latidos registrados todavia.";
    return;
  }
  for (const l of latidos) {
    const li = document.createElement("li");
    li.textContent = `${l.utc} · ${l.revisados} eventos revisados, ${l.relevantes} en alcance`;
    lista.appendChild(li);
  }
  estado.hidden = true;
}

async function cargar() {
  try {
    const respuesta = await fetch(FUENTE);
    if (!respuesta.ok) throw new Error(`HTTP ${respuesta.status}`);
    const datos = await respuesta.json();
    pintarResumen(datos);
    pintarEventos(datos);
    pintarLatidos(datos);
  } catch (error) {
    for (const id of ["resumen", "estado-eventos", "estado-latidos"]) {
      const nodo = document.getElementById(id);
      if (nodo) nodo.textContent = "No se pudo leer el estado del sistema.";
    }
    console.warn("status.json no disponible:", error);
  }
}

cargar();
