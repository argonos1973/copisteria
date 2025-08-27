import { API_PRODUCTOS, API_PRODUCTOS_FALLBACK } from './constantes.js';
import { fetchConManejadorErrores } from './scripts_utils.js';

const productoSelect = document.getElementById('productoSelect');
const productosMulti = document.getElementById('productosMulti');
const chkSelectAll = document.getElementById('chkSelectAll');
const btnCargar = document.getElementById('btnCargar');
const btnAñadir = document.getElementById('btnAñadir');
const btnGuardar = document.getElementById('btnGuardar');
const statusSpan = document.getElementById('status');
const tbody = document.querySelector('#tablaFranjas tbody');

let franjas = [];
let productosCache = [];

function setStatus(msg, ok = true) {
  statusSpan.textContent = msg;
  statusSpan.style.color = ok ? 'green' : 'red';
}

function getEtiquetaProductoFila() {
  const idsMulti = getSelectedProductoIdsMulti();
  if (idsMulti && idsMulti.length > 0) return 'Múltiple';
  const id = getSelectedProductoId();
  return id ? String(id) : '-';
}

function filaHTML(f) {
  const etiquetaProducto = getEtiquetaProductoFila();
  return `
    <tr>
      <td>${etiquetaProducto}</td>
      <td><input type="number" class="min" min="1" value="${f.min}" /></td>
      <td><input type="number" class="max" min="1" value="${f.max}" /></td>
      <td><input type="number" class="descuento" step="0.01" min="0" max="100" value="${f.descuento}" /></td>
      <td class="actions">
        <button class="btn-delete" title="Eliminar"><i class="fas fa-trash"></i></button>
      </td>
    </tr>
  `;
}

function renderFranjas() {
  tbody.innerHTML = franjas.map(f => filaHTML(f)).join('');
  tbody.querySelectorAll('.btn-delete').forEach((btn, idx) => {
    btn.addEventListener('click', () => {
      franjas.splice(idx, 1);
      renderFranjas();
    });
  });
}

function nombreProductoPorId(id) {
  const p = (productosCache || []).find(x => Number(x.id) === Number(id));
  return p ? p.nombre || String(id) : String(id);
}

function filaProductoFranja(producto, min, max, descuento) {
  const nombre = producto.nombre || `Producto ${producto.id}`;
  return `
    <tr data-pid="${producto.id}" data-pname="${nombre}">
      <td>${nombre}</td>
      <td><input type="number" class="min" min="1" value="${min}" /></td>
      <td><input type="number" class="max" min="1" value="${max}" /></td>
      <td><input type="number" class="descuento" step="0.01" min="0" max="100" value="${descuento}" /></td>
      <td class="actions">
        <button class="btn-delete" title="Eliminar"><i class="fas fa-trash"></i></button>
      </td>
    </tr>
  `;
}

function renderTablaTodosProductosFranjas() {
  if (!Array.isArray(productosCache) || productosCache.length === 0) return;
  const filas = [];

  // Mapa de franjas "globales" equivalentes a las usadas en scripts_utils.aplicarDescuentoPorFranja cuando no hay franjas por producto
  const fallbackBands = [
    { min: 1,   max: 10,   descuento: 0 },
    { min: 11,  max: 50,   descuento: 5 },
    { min: 51,  max: 99,   descuento: 10},
    { min: 100, max: 200,  descuento: 15},
    { min: 201, max: 300,  descuento: 20},
    { min: 301, max: 400,  descuento: 25},
    { min: 401, max: 500,  descuento: 30},
  ];

  const getPctForQty = (q) => {
    for (const fr of fallbackBands) {
      if (q >= fr.min && q <= fr.max) return fr.descuento;
    }
    // >500 lo maneja franja fija del 80%
    return 0;
  };

  for (const p of productosCache) {
    // Generar franjas de 10 en 10 desde 1..500
    for (let start = 1; start <= 500; start += 10) {
      const end = Math.min(start + 9, 500);
      const pct = getPctForQty(start);
      filas.push(filaProductoFranja(p, start, end, pct));
    }
    // Franja >500 con 80%
    filas.push(filaProductoFranja(p, 501, 999999, 80));
  }
  tbody.innerHTML = filas.join('');
  // activar eliminar por fila
  tbody.querySelectorAll('.btn-delete').forEach(btn => {
    btn.addEventListener('click', (ev) => {
      const tr = ev.currentTarget.closest('tr');
      if (tr) tr.remove();
    });
  });
}

function leerFranjasPorProductoDesdeTabla() {
  const rows = Array.from(tbody.querySelectorAll('tr'));
  const mapa = new Map(); // pid -> array de franjas
  for (const tr of rows) {
    const pid = Number(tr.getAttribute('data-pid'));
    const min = Number(tr.querySelector('input.min')?.value || 0);
    const max = Number(tr.querySelector('input.max')?.value || 0);
    const descuento = Number(tr.querySelector('input.descuento')?.value || 0);
    if (!Number.isFinite(pid) || pid <= 0) continue;
    if (!Number.isFinite(min) || !Number.isFinite(max) || min <= 0 || max < min) continue;
    if (!mapa.has(pid)) mapa.set(pid, []);
    mapa.get(pid).push({ min, max, descuento });
  }
  // ordenar franjas por producto
  for (const [pid, arr] of mapa.entries()) {
    arr.sort((a, b) => a.min - b.min || a.max - b.max);
  }
  return mapa;
}

function añadirFranja() {
  let maxAnterior = 0;
  if (franjas.length > 0) {
    maxAnterior = Math.max(...franjas.map(f => Number(f.max) || 0));
  }
  const nueva = { min: maxAnterior + 1, max: maxAnterior + 10, descuento: 0 };
  franjas.push(nueva);
  renderFranjas();
}

function leerFranjasDeTabla() {
  const filas = Array.from(tbody.querySelectorAll('tr'));
  const result = [];
  for (const tr of filas) {
    const min = Number(tr.querySelector('input.min')?.value || 0);
    const max = Number(tr.querySelector('input.max')?.value || 0);
    const descuento = Number(tr.querySelector('input.descuento')?.value || 0);
    if (!min || !max || max < min) {
      throw new Error(`Franja inválida: min=${min} max=${max}`);
    }
    result.push({ min, max, descuento });
  }
  // ordenar por min y normalizar
  result.sort((a, b) => a.min - b.min || a.max - b.max);
  return result;
}

async function cargarProductos() {
  // Probar varios endpoints: paginado y simple, en primario y fallback
  const attempts = [];
  // Intento 1: paginado en primario con tamaño grande
  attempts.push(`${window.location.protocol}//${window.location.hostname}:${(new URL(API_PRODUCTOS)).port || '5001'}/api/productos/paginado?page=1&page_size=1000&sort=nombre&order=ASC`);
  // Intento 2: lista simple en primario
  attempts.push(API_PRODUCTOS);
  // Intento 3: paginado en fallback (mismo origen)
  const origen = `${window.location.protocol}//${window.location.hostname}${window.location.port ? ':'+window.location.port : ''}`;
  attempts.push(`${origen}/api/productos/paginado?page=1&page_size=1000&sort=nombre&order=ASC`);
  // Intento 4: lista simple en fallback
  attempts.push(API_PRODUCTOS_FALLBACK);

  for (const url of attempts) {
    try {
      const res = await fetch(url);
      if (!res.ok) continue;
      const data = await res.json();
      const items = Array.isArray(data) ? data : (data.items || []);
      if (!Array.isArray(items)) continue;
      return items
        .map(p => ({ id: Number(p.id || p.ID || p.producto_id || 0), nombre: p.nombre || p.Name || p.descripcion || `Producto ${p.id}` }))
        .filter(p => Number.isFinite(p.id) && p.id > 0);
    } catch (_) { /* probar siguiente */ }
  }
  return [];
}

function getSelectedProductoId() {
  const val = productoSelect?.value;
  const n = Number(val || 0);
  return Number.isFinite(n) && n > 0 ? n : 0;
}

function getSelectedProductoIdsMulti() {
  if (!productosMulti) return [];
  return Array.from(productosMulti.selectedOptions || [])
    .map(opt => Number(opt.value))
    .filter(id => Number.isFinite(id) && id > 0);
}

async function getFranjas(productoId) {
  const url1 = `${API_PRODUCTOS}/${productoId}/franjas_descuento`;
  const url2 = `${API_PRODUCTOS_FALLBACK}/${productoId}/franjas_descuento`;
  try {
    const data = await fetchConManejadorErrores(url1);
    return Array.isArray(data.franjas) ? data.franjas : [];
  } catch (_) {
    const data = await fetchConManejadorErrores(url2);
    return Array.isArray(data.franjas) ? data.franjas : [];
  }
}

async function saveFranjas(productoId, franjasListado) {
  const url1 = `${API_PRODUCTOS}/${productoId}/franjas_descuento`;
  const url2 = `${API_PRODUCTOS_FALLBACK}/${productoId}/franjas_descuento`;
  const payload = JSON.stringify(franjasListado);
  const headers = { 'Content-Type': 'application/json' };
  try {
    await fetchConManejadorErrores(url1, { method: 'POST', headers, body: payload });
    return true;
  } catch (_) {
    await fetchConManejadorErrores(url2, { method: 'POST', headers, body: payload });
    return true;
  }
}

btnCargar.addEventListener('click', async () => {
  const id = getSelectedProductoId();
  if (!id) { setStatus('Seleccione un producto válido', false); return; }
  setStatus('Cargando...');
  try {
    franjas = await getFranjas(id);
    renderFranjas();
    setStatus(`Cargadas ${franjas.length} franjas`);
  } catch (e) {
    console.error(e);
    setStatus(`Error al cargar: ${e.message}`, false);
  }
});

btnAñadir.addEventListener('click', () => {
  añadirFranja();
});

btnGuardar.addEventListener('click', async () => {
  try {
    // Detectar si la tabla es expandida (múltiples productos con data-pid)
    const filasConPid = tbody.querySelector('tr[data-pid]');
    if (filasConPid) {
      const mapa = leerFranjasPorProductoDesdeTabla();
      if (mapa.size === 0) { setStatus('No hay franjas válidas para guardar', false); return; }
      setStatus(`Guardando franjas para ${mapa.size} productos...`);
      const promesas = [];
      for (const [pid, listado] of mapa.entries()) {
        promesas.push(saveFranjas(pid, listado));
      }
      const resultados = await Promise.allSettled(promesas);
      const ok = resultados.filter(r => r.status === 'fulfilled').length;
      const fail = resultados.length - ok;
      setStatus(`Guardado completado. OK: ${ok}, Errores: ${fail}`, fail === 0);
      return;
    }

    // Modo existente: un solo producto seleccionado con posible multiselección para aplicar
    const id = getSelectedProductoId();
    if (!id) { setStatus('Seleccione un producto válido', false); return; }
    const listado = leerFranjasDeTabla();
    const idsSeleccionados = getSelectedProductoIdsMulti();
    if (idsSeleccionados.length > 0) {
      setStatus(`Guardando en ${idsSeleccionados.length} productos...`);
      const resultados = await Promise.allSettled(idsSeleccionados.map(pid => saveFranjas(pid, listado)));
      const ok = resultados.filter(r => r.status === 'fulfilled').length;
      const fail = resultados.length - ok;
      setStatus(`Guardado masivo completado. OK: ${ok}, Errores: ${fail}`, fail === 0);
    } else {
      await saveFranjas(id, listado);
      franjas = listado;
      setStatus('Guardado correctamente');
    }
  } catch (e) {
    console.error(e);
    setStatus(`Error al guardar: ${e.message}`, false);
  }
});

// Inicialización: cargar productos en el selector y respetar ?producto_id=
(async function init() {
  try {
    setStatus('Cargando productos...');
    productosCache = await cargarProductos();
    const opciones = productosCache.map(p => `<option value="${p.id}">${p.id} - ${p.nombre}</option>`).join('');
    if (productoSelect) {
      productoSelect.innerHTML = '<option value="">-- Seleccione producto --</option>' + opciones;
    }
    if (productosMulti) {
      productosMulti.innerHTML = opciones;
    }

    const params = new URLSearchParams(window.location.search);
    const pid = Number(params.get('producto_id') || 0);
    if (pid) {
      productoSelect.value = String(pid);
    }
    setStatus('');

    // Si hay producto preseleccionado, cargar franjas automáticamente
    if (getSelectedProductoId()) {
      btnCargar.click();
    } else {
      // Insertar en la tabla todos los productos con sus franjas por defecto
      renderTablaTodosProductosFranjas();
      // Autoguardado siempre activo: guardar en BD para todos los productos
      setStatus('Guardando franjas para todos los productos...', true);
      setTimeout(() => btnGuardar.click(), 250);
    }
  } catch (e) {
    console.error('Error cargando productos:', e);
    setStatus('No se pudieron cargar los productos', false);
  }
})();

// Eventos de selección múltiple
if (chkSelectAll && productosMulti) {
  chkSelectAll.addEventListener('change', (e) => {
    const checked = e.target.checked;
    Array.from(productosMulti.options).forEach(opt => { opt.selected = checked; });
  });
}
