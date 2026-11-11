// Pinta el calendario que prepara la app local y lo mantiene al día sin recargar la página.
"use strict";

const ESTATICO = new URLSearchParams(location.search).has("estatico"); // modo imagen: sin interacción
const CIERRE_AUTOMATICO_MS = 120000; // el detalle se cierra solo a los 2 minutos
const COLOR_VALIDO = /^#[0-9a-f]{6}$/i;

let vista = null;        // último JSON de /api/vista
let elegido = null;      // id del evento seleccionado
let temporizador = null;

const $ = (id) => document.getElementById(id);

function el(etiqueta, clase, texto) {
  const nodo = document.createElement(etiqueta);
  if (clase) nodo.className = clase;
  if (texto != null) nodo.textContent = texto; // siempre texto, nunca HTML
  return nodo;
}

// Blanco u oscuro: el que más contraste dé sobre el color del evento (fórmula de WCAG).
function colorDeTexto(hex) {
  const [r, g, b] = [1, 3, 5]
    .map((i) => parseInt(hex.slice(i, i + 2), 16) / 255)
    .map((v) => (v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4));
  const luminancia = 0.2126 * r + 0.7152 * g + 0.0722 * b;
  return 1.05 / (luminancia + 0.05) > (luminancia + 0.05) / 0.0651 ? "#ffffff" : "#10222a";
}

function pintarColor(nodo, hex) {
  if (!COLOR_VALIDO.test(hex)) return;
  nodo.style.background = hex;
  nodo.style.color = colorDeTexto(hex);
}

function hacerPulsable(nodo, id) {
  nodo.dataset.id = id;
  nodo.tabIndex = 0;
  nodo.setAttribute("role", "button");
}

// Reparte en carriles los eventos que se solapan (algoritmo voraz de partición de intervalos).
function asignarCarriles(eventos) {
  const grupos = [];
  let grupo = [];
  let finGrupo = -1;
  for (const e of eventos) {
    if (grupo.length && e.ini >= finGrupo) {
      grupos.push(grupo);
      grupo = [];
      finGrupo = -1;
    }
    grupo.push(e);
    finGrupo = Math.max(finGrupo, e.fin);
  }
  if (grupo.length) grupos.push(grupo);

  for (const g of grupos) {
    const finCarril = [];
    for (const e of g) {
      let carril = finCarril.findIndex((fin) => fin <= e.ini);
      if (carril < 0) {
        carril = finCarril.length;
        finCarril.push(0);
      }
      finCarril[carril] = e.fin;
      e.carril = carril;
    }
    g.forEach((e) => (e.carriles = finCarril.length));
  }
}

// --- Columna izquierda ---------------------------------------------------------------------------

function pintarFoco(v) {
  const foco = $("foco");
  foco.replaceChildren();
  const anadir = (titulo, e, cuando) => {
    const item = el("div", "item");
    hacerPulsable(item, e.id);
    item.append(el("div", "pri", e.titulo), el("div", "sec", [cuando, e.hora, e.lugar].filter(Boolean).join(", ")));
    foco.append(el("h2", null, titulo), item);
  };
  v.en_curso.forEach((e) => anadir("Ahora", e, ""));
  if (v.siguiente) anadir("Después", v.siguiente, v.siguiente.es_hoy ? "Hoy" : v.siguiente.cuando);
  else if (!v.en_curso.length) foco.append(el("h2", null, "Después"), el("div", "sec", "Sin eventos próximos."));

  const futuro = $("fut");
  futuro.replaceChildren();
  if (!v.proximos.length) return;
  const lista = el("ul");
  lista.id = "mas";
  for (const e of v.proximos) {
    const li = el("li", "item");
    hacerPulsable(li, e.id);
    li.append(el("span", null, e.cuando), el("span", null, e.titulo));
    lista.append(li);
  }
  futuro.append(el("h2", null, "Más adelante"), lista);
}

function pintarAviso(v) {
  const aviso = $("aviso");
  aviso.replaceChildren(el("span", null, v.aviso));
  if (!v.reconectar) return;
  const boton = el("button", null, "Volver a conectar");
  boton.onclick = async () => {
    boton.textContent = "Abriendo el navegador…";
    try {
      const r = await fetch("/api/reconectar", { method: "POST", headers: { "X-Calendario": "1" } });
      if (!r.ok) boton.textContent = "Ejecuta reconectar.bat";
    } catch {
      boton.textContent = "Ejecuta reconectar.bat";
    }
  };
  aviso.append(boton);
}

// --- Semana --------------------------------------------------------------------------------------

function pintarSemana(v) {
  const sem = $("sem");
  sem.replaceChildren();
  const [desde, hasta] = v.rango; // minutos visibles del día
  const pct = (m) => ((Math.min(Math.max(m, desde), hasta) - desde) / (hasta - desde)) * 100;
  const primeraHora = Math.ceil(desde / 60) * 60;

  // Cabeceras y eventos de todo el día
  sem.append(el("div"));
  for (const d of v.dias) {
    const cab = el("div", "cab" + (d.hoy ? " hoy" : ""), d.corto);
    cab.append(el("b", null, d.numero));
    sem.append(cab);
  }
  sem.append(el("div"));
  for (const d of v.dias) {
    const fila = el("div", "todo");
    for (const e of d.todo_dia.slice(0, 3)) {
      const x = el("div", null, e.titulo);
      pintarColor(x, e.color);
      hacerPulsable(x, e.id);
      fila.append(x);
    }
    sem.append(fila);
  }

  // Horas
  const horas = el("div", "horas");
  for (let m = primeraHora; m < hasta; m += 60) {
    if (m === desde) continue;
    const h = el("span", null, m / 60);
    h.style.top = pct(m) + "%";
    horas.append(h);
  }
  sem.append(horas);

  // Columnas de los días
  for (const d of v.dias) {
    const col = el("div", "col" + (d.hoy ? " hoy" : ""));
    for (let m = primeraHora; m <= hasta; m += 60) {
      const raya = el("div", "raya");
      raya.style.top = pct(m) + "%";
      col.append(raya);
    }

    const visibles = d.eventos.filter((e) => e.fin > desde && e.ini < hasta);
    asignarCarriles(visibles);
    for (const e of visibles) {
      const duracion = e.fin - e.ini;
      const x = el("div", "ev" + (e.pasado ? " pasado" : "") + (duracion >= 100 ? " largo" : ""));
      hacerPulsable(x, e.id);
      pintarColor(x, e.color);
      x.style.top = pct(e.ini) + "%";
      x.style.height = `calc(${pct(e.fin) - pct(e.ini)}% - 1px)`;
      x.style.left = `calc(${(e.carril / e.carriles) * 100}% + 1px)`;
      x.style.width = `calc(${100 / e.carriles}% - 2px)`;
      x.append(el("b", null, e.titulo));
      if (duracion >= 60) x.append(el("span", null, e.texto_hora));
      if (duracion >= 105 && e.lugar && e.carriles === 1) x.append(el("span", null, e.lugar));
      col.append(x);
    }

    if (d.hoy && v.ahora_min >= desde && v.ahora_min <= hasta) {
      const linea = el("div");
      linea.id = "linea";
      linea.style.top = pct(v.ahora_min) + "%";
      col.append(linea);
    }
    sem.append(col);
  }
}

// --- Detalle del evento elegido ------------------------------------------------------------------

async function abrirEnlace(boton, n) {
  const original = boton.textContent;
  try {
    const r = await fetch("/api/abrir", {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-Calendario": "1" },
      body: JSON.stringify({ id: elegido, n }),
    });
    boton.textContent = r.ok ? "Abierto en el navegador" : "No se pudo abrir";
  } catch {
    boton.textContent = "No se pudo abrir";
  }
  setTimeout(() => (boton.textContent = original), 2500);
  programarCierre();
}

function mostrarDetalle() {
  const d = vista && vista.detalles[elegido];
  if (!d) return cerrarDetalle();

  document.body.classList.add("con-sel");
  $("detalle").hidden = false;
  $("detalle").style.setProperty("--color", COLOR_VALIDO.test(d.color) ? d.color : "#ffc857");
  $("d-titulo").textContent = d.titulo;
  $("d-cuando").textContent = d.cuando;
  $("d-lugar").textContent = d.lugar;
  $("d-cal").textContent = d.calendario;
  $("d-desc").textContent = d.descripcion;
  $("d-desc").scrollTop = 0;

  const acciones = $("d-acciones");
  acciones.replaceChildren();
  if (d.abrir) {
    const b = el("button", null, "Abrir en Google Calendar");
    b.onclick = () => abrirEnlace(b, -1);
    acciones.append(b);
  }
  d.enlaces.forEach((texto, i) => {
    const b = el("button", null, texto);
    b.title = texto;
    b.onclick = () => abrirEnlace(b, i);
    acciones.append(b);
  });
  const cerrar = el("button", "cerrar", "Cerrar");
  cerrar.onclick = cerrarDetalle;
  acciones.append(cerrar);

  document.querySelectorAll("[data-id]").forEach((n) => n.classList.toggle("sel", n.dataset.id === elegido));
}

function elegir(id) {
  elegido = id;
  mostrarDetalle();
  programarCierre();
}

function cerrarDetalle() {
  elegido = null;
  document.body.classList.remove("con-sel");
  $("detalle").hidden = true;
  document.querySelectorAll(".sel").forEach((n) => n.classList.remove("sel"));
  clearTimeout(temporizador);
}

function programarCierre() {
  clearTimeout(temporizador);
  temporizador = setTimeout(cerrarDetalle, CIERRE_AUTOMATICO_MS);
}

document.addEventListener("click", (ev) => {
  const pulsado = ev.target.closest("[data-id]");
  if (pulsado) {
    if (pulsado.dataset.id === elegido) cerrarDetalle();
    else elegir(pulsado.dataset.id);
  } else if (!ev.target.closest("#detalle")) {
    cerrarDetalle(); // clic en un hueco vacío
  }
});

document.addEventListener("keydown", (ev) => {
  if (ev.key === "Escape") cerrarDetalle();
  else if ((ev.key === "Enter" || ev.key === " ") && ev.target.dataset?.id) {
    ev.preventDefault();
    elegir(ev.target.dataset.id);
  }
});

// --- Datos y actualización -----------------------------------------------------------------------

async function pintar() {
  const v = await (await fetch("/api/vista", { cache: "no-store" })).json();
  vista = v;
  $("dia").textContent = v.hoy.dia;
  $("num").textContent = v.hoy.numero;
  $("mes").textContent = v.hoy.mes;
  pintarAviso(v);
  pintarFoco(v);
  pintarSemana(v);
  if (elegido) mostrarDetalle();
}

const repintar = () => pintar().catch(() => {});

// La app avisa en cuanto Google tiene cambios (Server-Sent Events); al reconectar, se pone al día.
function escucharCambios() {
  const fuente = new EventSource("/api/cambios");
  fuente.onmessage = repintar;
  fuente.onopen = repintar;
  fuente.onerror = () => ($("aviso").textContent = "La aplicación local no responde. Se reconectará sola.");
}

function cargarFondo() {
  return new Promise((listo) => {
    const img = new Image();
    img.onload = () => {
      document.body.style.backgroundImage = "url(/fondo)";
      listo();
    };
    img.onerror = listo;
    img.src = "/fondo";
  });
}

(async () => {
  await cargarFondo();
  try {
    await pintar();
  } catch {
    $("aviso").textContent = "La aplicación local no responde.";
  }
  await document.fonts.ready;
  document.body.dataset.listo = "1"; // señal para la captura del modo imagen
  if (ESTATICO) return;
  escucharCambios();
  setInterval(repintar, 30000); // mueve la línea de «ahora»
  document.addEventListener("visibilitychange", () => !document.hidden && repintar());
})();
