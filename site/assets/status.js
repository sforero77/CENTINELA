// Página de estado: lee el status.json que escribe el disparador.
//
// La transparencia sobre la latencia es parte del producto (RNF-02): esta
// página publica la distribución real, no la prometida, y no descuenta la
// demora del cron aunque no la controlemos.

const FUENTE = "status.json";

const $ = (id) => document.getElementById(id);
const nf = new Intl.NumberFormat("es");
const escapar = (s) =>
  String(s).replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

const MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"];

function comoFecha(iso) {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return String(iso || "—");
  const hh = String(d.getUTCHours()).padStart(2, "0");
  const mm = String(d.getUTCMinutes()).padStart(2, "0");
  return `${d.getUTCDate()} ${MESES[d.getUTCMonth()]} ${d.getUTCFullYear()}, ${hh}:${mm}`;
}

// "19071.5 min" es la latencia de un backtest expresada en la unidad del
// objetivo. Nadie lee trece días en minutos.
function comoDuracion(min) {
  if (!Number.isFinite(min)) return "—";
  if (min < 90) return `${nf.format(Number(min.toFixed(1)))} min`;
  const horas = min / 60;
  if (horas < 48) return `${nf.format(Number(horas.toFixed(1)))} h`;
  return `${nf.format(Math.round(horas / 24))} d`;
}

function plural(n, singular, prural) {
  return `${nf.format(n)} ${n === 1 ? singular : prural}`;
}

function metrica(valor, etiqueta, clase = "") {
  return `<div class="metrica">
    <span class="valor ${clase}">${valor}</span>
    <span class="etiqueta">${etiqueta}</span>
  </div>`;
}

//: Si la cadencia del vigia ya se come el objetivo, decirlo.
//:
//: Compara dos cifras que la pagina ya publica por separado: el objetivo de
//: latencia y la mediana real entre revisiones del feed. La deteccion es un
//: sumando de la latencia total, asi que si por si sola supera el objetivo, el
//: objetivo es inalcanzable hasta que eso cambie.
//:
//: El aviso decia ademas "pide un turno cada 30 min y GitHub le concede unos
//: pocos al dia". Dejo de ser cierto el 30-ago-2026, cuando un cron externo
//: empezo a disparar el vigia cada cinco minutos por `repository_dispatch`:
//: la frase seguia culpando a la cola de GitHub de un problema ya resuelto.
//: Ahora el aviso solo afirma lo que mide, y si la cadencia baja del objetivo
//: no aparece.
function avisoDeCadencia(datos) {
  const c = datos.cadencia || {};
  const objetivo = (datos.objetivo || {}).p50_min;
  if (!Number.isFinite(c.p50_min) || !Number.isFinite(objetivo)) return "";
  if (c.p50_min <= objetivo) return "";
  return `<p class="nota nota-alarma">Y hay algo que no depende de que ocurra un
     sismo: el vigía tarda <strong>${comoDuracion(c.p50_min)}</strong> de mediana
     entre una revisión del feed y la siguiente. Como la detección es parte de
     la latencia, mientras esa cadencia no baje, el objetivo de ${objetivo} min
     no se puede cumplir aunque el resto del pipeline fuera instantáneo.</p>`;
}

function pintarResumen(datos) {
  const { medido, objetivo } = datos;
  const nodo = $("resumen");

  if (!medido.eventos_publicados) {
    // Decir "todavía no hay datos" es más honesto que mostrar un cero que
    // parece un logro.
    nodo.innerHTML =
      `<p>Aún no se ha publicado ningún reporte en vivo, así que no hay latencia
       que medir. El objetivo es ${objetivo.p50_min} min (p50) y
       ${objetivo.p95_min} min (p95).</p>` +
      (medido.backtests_excluidos
        ? `<p class="nota">${plural(medido.backtests_excluidos,
            "reconstrucción retrospectiva queda", "reconstrucciones retrospectivas quedan")}
           fuera de la estadística: una reconstrucción se publica días después del sismo
           y su latencia no mide nada del sistema.</p>`
        : "") +
      // LA RESTA QUE NADIE ESTABA HACIENDO.
      //
      // El objetivo y la cadencia del vigia vivian en dos bloques distintos de
      // esta pagina y nadie los ponia uno al lado del otro. Y la conclusion sale
      // de datos que ya estan publicados: si el vigia tarda 157 min de mediana
      // solo en **mirar** el feed, un objetivo de 60 min desde que hay ShakeMap
      // no se puede cumplir aunque el resto del pipeline fuera instantaneo.
      //
      // Decirlo no es pesimismo: es lo mismo que hace el resto del sistema con
      // el desvio de poblacion —publicarlo aunque incomode— y es lo que impide
      // que un objetivo se quede de adorno.
      avisoDeCadencia(datos);
    nodo.classList.remove("cargando");
    return;
  }

  const clase = (v, meta) => (v === null ? "" : v <= meta ? "cumple" : "incumple");

  // EL OBJETIVO SE JUZGA CONTRA LA SERIE QUE LO DEFINE.
  //
  // Aqui se comparaba `medido.p50_min` —desde el ORIGEN DEL SISMO, que incluye
  // lo que USGS tarda en localizarlo y en publicar su primer ShakeMap— contra un
  // objetivo definido "tras la disponibilidad del primer ShakeMap". Dos relojes
  // distintos, y la pagina pintaba «incumple» con esa resta.
  //
  // `objetivo.medido_contra` dice cual es la buena; sin el, esta pagina tenia
  // que elegir, y elegia la equivocada. El total se sigue publicando al lado,
  // porque es el tiempo que de verdad pasa.
  const juzgada =
    (objetivo.medido_contra && medido[objetivo.medido_contra]) || medido;
  const hayJuzgada = Number.isFinite(juzgada.p50_min);

  // EL AVISO DE CADENCIA TAMBIEN VA AQUI, Y ESTE ES EL CAMINO QUE SE RECORRE.
  //
  // Vivia solo en la rama de arriba —la de «todavia no hay ningun reporte
  // publicado»—, que dejo de ejecutarse el dia que se publico el primero. Con
  // dos reportes en vivo, la unica alarma sobre lo que **no** depende de que
  // ocurra un sismo no podia aparecer nunca.
  //
  // Y es justo el camino en que importa: cuando ya hay latencia medida, la
  // pregunta «¿cabe el objetivo dentro de la cadencia del vigia?» deja de ser
  // teorica. `avisoDeCadencia` devuelve cadena vacia si la cadencia cumple, asi
  // que ponerlo aqui no anade ruido cuando no hay nada que decir.
  nodo.innerHTML =
    `<div class="metricas">
    ${metrica(comoDuracion(juzgada.p50_min), `p50 desde detección · objetivo ${objetivo.p50_min} min`,
              hayJuzgada ? clase(juzgada.p50_min, objetivo.p50_min) : "")}
    ${metrica(comoDuracion(juzgada.p95_min), `p95 desde detección · objetivo ${objetivo.p95_min} min`,
              hayJuzgada ? clase(juzgada.p95_min, objetivo.p95_min) : "")}
    ${metrica(comoDuracion(medido.p50_min), "p50 total, desde el sismo")}
    ${metrica(nf.format(medido.eventos_publicados), "reportes en vivo")}
  </div>
  <p class="nota">${escapar(datos.nota)}</p>` + avisoDeCadencia(datos);
  nodo.classList.remove("cargando");
}

function pintarEventos(datos) {
  const estado = $("estado-eventos");
  const tabla = $("tabla-eventos");
  if (!datos.eventos.length) {
    estado.textContent = "Todavía no hay eventos publicados.";
    return;
  }
  const cuerpo = tabla.querySelector("tbody");
  let backtests = 0;
  for (const e of datos.eventos) {
    if (e.backtest) backtests += 1;
    const fila = document.createElement("tr");
    fila.innerHTML =
      `<td><a href="index.html?evento=${encodeURIComponent(e.usgs_id)}">${escapar(e.usgs_id)}</a>` +
      `${e.backtest ? ' <span class="mono">retrospectivo</span>' : ""}</td>` +
      `<td class="num">${comoFecha(e.origen_utc)}</td>` +
      `<td class="num">${comoFecha(e.publicado_utc)}</td>` +
      `<td class="num">${comoDuracion(e.minutos)}</td>` +
      // `v0` es un preliminar sin ShakeMap, no una version cero.
      `<td class="num">${e.shakemap ? "v" + e.shakemap : "—"}</td>` +
      // Vacío cuando el reporte se publicó una sola vez, que es el caso normal
      // y no una carencia: no todos los ShakeMap se revisan.
      `<td class="num">${e.actualizado_utc ? comoFecha(e.actualizado_utc) : "—"}</td>`;
    cuerpo.appendChild(fila);
  }
  estado.hidden = true;
  tabla.hidden = false;

  // La tabla lista los backtests con su latencia, que es un número real y no
  // significa nada del sistema. Se dice aquí en vez de dejar que alguien lo
  // lea como una demora de trece días.
  if (backtests) {
    const nota = $("nota-eventos");
    nota.hidden = false;
    nota.textContent =
      "La latencia de una reconstrucción retrospectiva es la distancia entre el " +
      "sismo y el día en que se reprocesó. No mide la velocidad del sistema y no " +
      "entra en el p50 ni en el p95.";
  }
}

function pintarLatidos(datos) {
  const estado = $("estado-latidos");
  const lista = $("lista-latidos");
  const latidos = [...datos.latidos].reverse().slice(0, 20);
  if (!latidos.length) {
    estado.textContent = "Sin latidos registrados todavía.";
    return;
  }
  for (const l of latidos) {
    const li = document.createElement("li");
    li.textContent =
      `${comoFecha(l.utc)} · ${plural(l.revisados, "evento revisado", "eventos revisados")}, ` +
      `${l.relevantes} en alcance` +
      // «Cero relevantes» y «no pude leer ninguno» se veian igual. Un estado
      // ilegible saca al sismo del despacho hasta que alguien repare el
      // fichero, asi que el latido tiene que decirlo donde se mira.
      (l.estados_ilegibles
        ? ` · ⚠ ${plural(l.estados_ilegibles, "estado ilegible", "estados ilegibles")}`
        : "");
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
    if (datos.generado_utc) {
      $("generado").textContent = `Última actualización: ${comoFecha(datos.generado_utc)} UTC.`;
    }
  } catch (error) {
    for (const id of ["resumen", "estado-eventos", "estado-latidos"]) {
      const nodo = $(id);
      if (nodo) nodo.textContent = "No se pudo leer el estado del sistema.";
    }
    console.warn("status.json no disponible:", error);
  }
}

cargar();
