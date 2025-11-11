import { API_URL_PRIMARY, API_URL_FALLBACK } from './constantes.js?v=1762757322';
import { fetchConManejadorErrores, debounce, norm, parsearImporte } from './scripts_utils.js';
import { mostrarConfirmacion } from './notificaciones.js';

const productoSelect = document.getElementById('productoSelect');
const productoSearch = document.getElementById('productoSearch');
const btnAñadir = document.getElementById('btnAñadir');
const btnGuardar = document.getElementById('btnGuardar');
const statusSpan = document.getElementById('status');
const btnVolver = document.getElementById('btnVolver');
if (btnVolver) {
  btnVolver.style.setProperty('display', 'none', 'important'); // Ocultar por defecto
}
const tbody = document.querySelector('#tablaFranjas tbody');
const precioUnitIvaSpan = document.getElementById('precioUnitIva');
const ivaUnitSpan = document.getElementById('ivaUnit');

let franjas = [];
let productosCache = [];

function setStatus(msg, ok = true) {
  statusSpan.textContent = msg;
  statusSpan.style.color = ok ? 'green' : 'red';
}

// Asegura que el precio con IVA por franja sea estrictamente decreciente (sin repeticiones)
function enforceStrictDecreasingPrices(listado) {
  const base = getSelectedProductoSubtotal();
  const impuestos = getSelectedProductoImpuestos();
  const precioConIva = (descPct) => {
    const aplicado = Math.max(0, base * (1 - Math.max(0, Math.min(60, descPct)) / 100));
    return aplicado * (1 + Math.max(0, impuestos) / 100);
  };
  const res = listado.map(f => ({ ...f }));
  let prevRed = null; // total anterior redondeado a 3 decimales
  let prevRaw = null; // total anterior sin redondeo
  const denom = base * (1 + Math.max(0, impuestos) / 100);
  for (let i = 0; i < res.length; i++) {
    let d = Number(res[i].descuento || 0);
    if (d < 0) d = 0; if (d > 60) d = 60;
    // Si es la primera franja y el descuento viene a 0, respetar 0% estrictamente
    if (i === 0 && Math.abs(d) < 1e-9) {
      d = 0;
    }
    if (i === 0) {
      const tRaw0 = precioConIva(d);
      const tRed0 = Number(tRaw0.toFixed(3));
      // Si ya es 0.00€ en la primera franja, no tiene sentido más bandas
      if (tRed0 <= 0) {
        res[i].descuento = Math.round(d * 100000) / 100000;
        res.length = 1;
        break;
      }
      prevRaw = tRaw0;
      prevRed = tRed0;
    } else {
      if (d > 60) d = 60;
      let tRaw = precioConIva(d);
      let tRed = Number(tRaw.toFixed(3));
      // Si por redondeo (a 3 decimales) aún no baja, incrementar con paso mínimo hasta bajar o tope 60%
      let guard = 0;
      while ((tRed >= prevRed) && d < 60 && guard < 100000) {
        d = Math.min(60, d + 0.0001);
        tRaw = precioConIva(d);
        tRed = Number(tRaw.toFixed(3));
        guard++;
      }
      // Si llegamos al 60% y aún no baja, truncar la lista en la franja anterior para evitar repeticiones
      if (tRed >= prevRed) {
        // No incluimos esta franja ni las siguientes
        res.length = i;
        break;
      }
      // Si ya llegamos a 0.00€, cortar listado para no repetir 0.00€
      if (tRed <= 0) {
        res[i].descuento = Math.round(d * 100000) / 100000;
        res.length = i + 1;
        break;
      }
      prevRaw = tRaw;
      prevRed = tRed;
    }
    res[i].descuento = Math.round(d * 100000) / 100000;
  }
  return res;
}

// Utilidades de normalización
function normalizeFranjasArray(arr) {
  const listado = Array.isArray(arr) ? [...arr] : [];
  if (listado.length === 0) return [];
  // Limitar descuentos y convertir a enteros positivos
  const ordenado = listado
    .map(f => ({
      min: Math.max(1, Math.floor(Number(f.min) || 0)),
      max: Math.max(1, Math.floor(Number(f.max) || 0)),
      descuento: Math.max(0, Math.min(60, Number(f.descuento) || 0))
    }))
    .sort((a, b) => a.min - b.min || a.max - b.max);
  // Asegurar continuidad desde 1 y sin solapes
  let prevMax = 0;
  for (let i = 0; i < ordenado.length; i++) {
    const f = ordenado[i];
    if (i === 0) {
      f.min = 1;
    } else {
      f.min = prevMax + 1;
    }
    if (f.max < f.min) f.max = f.min; // evitar max < min
    prevMax = f.max;
  }
  return ordenado;
}

function actualizarCabeceraPrecioIVA() {
  const subtotal = getSelectedProductoSubtotal();
  const impuestos = getSelectedProductoImpuestos();
  const ivaUnit = subtotal * (impuestos / 100);
  const totalUnit = subtotal + ivaUnit;
  const fmt2 = (n) => Number.isFinite(n)
    ? n.toLocaleString('es-ES', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' €'
    : '-';
  if (precioUnitIvaSpan) precioUnitIvaSpan.textContent = `Precio con IVA: ${fmt2(totalUnit)}`;
  if (ivaUnitSpan) ivaUnitSpan.textContent = `IVA unitario: ${fmt2(ivaUnit)}`;
}

function filaHTML(f) {
  return `
    <tr>
      <td><input type="text" class="min" value="${f.min}" inputmode="decimal" /></td>
      <td><input type="text" class="max" value="${f.max}" inputmode="decimal" /></td>
      <td class="descuento-col"><input type="text" class="descuento" inputmode="decimal" pattern="[0-9.,]*" value="${Number(f.descuento || 0).toLocaleString('es-ES', { minimumFractionDigits: 5, maximumFractionDigits: 5 })}" /></td>
      <td class="precio-aplicado">-</td>
      <td class="precio-iva-editable"><input type="number" class="precio-final-iva" step="0.001" min="0" value="0" /></td>
      <td class="precio-iva">-</td>
      <td class="iva-unit">-</td>
      <td class="acciones-col">
        <button class="btn-icon" title="Eliminar">✕</button>
      </td>
    </tr>
  `;
}

function renderFranjas() {
  // Normalizar antes de renderizar para evitar huecos/solapes
  franjas = normalizeFranjasArray(franjas);
  tbody.innerHTML = franjas.map(f => filaHTML(f)).join('');
  tbody.querySelectorAll('.btn-icon').forEach((btn, idx) => {
    btn.addEventListener('click', async () => {
      const ok = await mostrarConfirmacion('¿Eliminar esta franja?');
      if (!ok) return;
      franjas.splice(idx, 1);
      renderFranjas(); // volverá a normalizar desde 1 consecutivo
    });
  });
  // Recalcular precios y vincular listeners para % descuento
  actualizarPreciosAplicados();
  tbody.querySelectorAll('input.descuento').forEach((inp) => {
    inp.addEventListener('input', () => {
      actualizarPreciosAplicados();
      cambiosSinGuardar = true;
    });
    inp.addEventListener('blur', () => {
      let n = parsearImporte(inp.value);
      if (!Number.isFinite(n)) n = 0;
      // Limitar a rango [0, 60]
      n = Math.max(0, Math.min(60, n));
      inp.value = n.toLocaleString('es-ES', { minimumFractionDigits: 5, maximumFractionDigits: 5 });
      actualizarPreciosAplicados();
      cambiosSinGuardar = true;
    });
  });
  
  // Vincular listeners para precio final con IVA (recalcula descuento)
  tbody.querySelectorAll('input.precio-final-iva').forEach((inp, idx) => {
    inp.addEventListener('input', () => {
      recalcularDescuentoDesdePrecioFinal(idx);
      cambiosSinGuardar = true;
    });
    inp.addEventListener('blur', () => {
      recalcularDescuentoDesdePrecioFinal(idx);
      cambiosSinGuardar = true;
    });
  });
}

// Eliminado el modo de tabla masiva; trabajamos solo con un producto seleccionado

// Eliminado lector de tabla por múltiples productos

function añadirFranja() {
  let maxAnterior = 0;
  if (franjas.length > 0) {
    maxAnterior = Math.max(...franjas.map(f => Number(f.max) || 0));
  }
  const nueva = { min: maxAnterior + 1, max: maxAnterior + 10, descuento: 0 };
  franjas.push(nueva);
  renderFranjas();
  // Enfocar el cursor en la última franja añadida
  try {
    const ultima = tbody.querySelector('tr:last-child input.descuento') || tbody.querySelector('tr:last-child input.min');
    if (ultima && typeof ultima.focus === 'function') {
      ultima.focus();
      if (typeof ultima.select === 'function') ultima.select();
    }
  } catch (_) { /* noop */ }
}

function leerFranjasDeTabla() {
  const filas = Array.from(tbody.querySelectorAll('tr'));
  const result = [];
  filas.forEach((tr, idx) => {
    const min = Number(tr.querySelector('input.min')?.value || 0);
    const max = Number(tr.querySelector('input.max')?.value || 0);
    const inputDesc = tr.querySelector('input.descuento');
    let descuento = Number.isFinite(parsearImporte(inputDesc?.value)) ? parsearImporte(inputDesc.value) : Number(franjas[idx]?.descuento || 0);
    if (!Number.isFinite(descuento)) descuento = 0;
    descuento = Math.max(0, Math.min(60, descuento));
    // Redondear a 5 decimales antes de enviar
    descuento = Math.round(descuento * 100000) / 100000;
    if (!min || !max || max < min) {
      throw new Error(`Franja inválida: min=${min} max=${max}`);
    }
    result.push({ min, max, descuento });
  });
  // ordenar por min y normalizar
  result.sort((a, b) => a.min - b.min || a.max - b.max);
  return normalizeFranjasArray(result);
}

async function cargarProductos() {
  // Fuentes a intentar: primario/fallback y con/si /api
  const fuentes = [
    { base: API_URL_PRIMARY, prefix: '/api' },
    { base: API_URL_PRIMARY, prefix: '' },
    { base: API_URL_FALLBACK, prefix: '/api' },
    { base: API_URL_FALLBACK, prefix: '' },
  ];

  // Intentar primero la ruta paginada iterando todas las páginas; si falla, caer a lista simple
  for (const f of fuentes) {
    // Paginado
    try {
      let page = 1;
      const pageSize = 200;
      let totalPages = 1;
      const acumulados = [];
      do {
        const url = `${f.base}${f.prefix}/productos/paginado?page=${page}&page_size=${pageSize}&sort=nombre&order=ASC`;
        const res = await fetch(url);
        if (!res.ok) throw new Error(String(res.status));
        const data = await res.json();
        const items = Array.isArray(data?.items) ? data.items : [];
        if (!Array.isArray(items)) throw new Error('estructura invalida');
        acumulados.push(...items);
        totalPages = Number(data?.total_pages || 1) || 1;
        page += 1;
      } while (page <= totalPages);

      return acumulados
        .map(p => ({ id: Number(p.id || p.ID || p.producto_id || 0), nombre: p.nombre || p.Name || p.descripcion || `Producto ${p.id}`, subtotal: Number(p.subtotal ?? p.price ?? 0), impuestos: Number(p.impuestos ?? p.vat ?? 0) }))
        .filter(p => Number.isFinite(p.id) && p.id > 0);
    } catch (_) {
      // continuar a intento de lista simple en esta misma fuente
    }

    // Lista simple
    try {
      const url = `${f.base}${f.prefix}/productos`;
      const res = await fetch(url);
      if (!res.ok) throw new Error(String(res.status));
      const data = await res.json();
      const items = Array.isArray(data) ? data : [];
      return items
        .map(p => ({ id: Number(p.id || p.ID || p.producto_id || 0), nombre: p.nombre || p.Name || p.descripcion || `Producto ${p.id}`, subtotal: Number(p.subtotal ?? p.price ?? 0), impuestos: Number(p.impuestos ?? p.vat ?? 0) }))
        .filter(p => Number.isFinite(p.id) && p.id > 0);
    } catch (_) {
      // probar siguiente fuente
    }
  }

  return [];
}

function getSelectedProductoId() {
  const val = productoSelect?.value;
  const n = Number(val || 0);
  return Number.isFinite(n) && n > 0 ? n : 0;
}

function getSelectedProductoSubtotal() {
  const id = getSelectedProductoId();
  const p = (productosCache || []).find(x => Number(x.id) === Number(id));
  const st = Number(p?.subtotal ?? 0);
  return Number.isFinite(st) ? st : 0;
}

function getSelectedProductoImpuestos() {
  const id = getSelectedProductoId();
  const p = (productosCache || []).find(x => Number(x.id) === Number(id));
  const imp = Number(p?.impuestos ?? 0);
  return Number.isFinite(imp) ? imp : 0;
}

// Sin multiselección

function recalcularDescuentoDesdePrecioFinal(idx) {
  try {
    const subtotal = getSelectedProductoSubtotal();
    const impuestos = getSelectedProductoImpuestos();
    if (!subtotal || subtotal <= 0) return;
    
    const filas = Array.from(tbody.querySelectorAll('tr'));
    if (idx >= filas.length) return;
    
    const tr = filas[idx];
    const inputPrecioFinal = tr.querySelector('input.precio-final-iva');
    const inputDesc = tr.querySelector('input.descuento');
    
    if (!inputPrecioFinal || !inputDesc) return;
    
    const precioFinalDeseado = Number(inputPrecioFinal.value) || 0;
    
    // Calcular el precio con descuento (sin IVA) a partir del precio final con IVA
    const precioConDescuento = precioFinalDeseado / (1 + impuestos / 100);
    
    // Calcular el descuento necesario
    const descuentoNecesario = ((subtotal - precioConDescuento) / subtotal) * 100;
    
    // Limitar a rango [0, 60]
    const descuentoFinal = Math.max(0, Math.min(60, descuentoNecesario));
    
    // Actualizar el input de descuento
    inputDesc.value = descuentoFinal.toLocaleString('es-ES', { minimumFractionDigits: 5, maximumFractionDigits: 5 });
    
    // Actualizar el array en memoria
    if (franjas[idx]) {
      franjas[idx].descuento = Math.round(descuentoFinal * 100000) / 100000;
    }
    
    // Recalcular todos los precios
    actualizarPreciosAplicados();
  } catch (e) {
    console.debug('recalcularDescuentoDesdePrecioFinal error:', e);
  }
}

function actualizarPreciosAplicados() {
  try {
    const subtotal = getSelectedProductoSubtotal();
    const impuestos = getSelectedProductoImpuestos();
    const filas = Array.from(tbody.querySelectorAll('tr'));
    for (let idx = 0; idx < filas.length; idx++) {
      const tr = filas[idx];
      const tdPrecio = tr.querySelector('td.precio-aplicado');
      const tdPrecioIva = tr.querySelector('td.precio-iva');
      const tdIvaUnit = tr.querySelector('td.iva-unit');
      const inputPrecioFinal = tr.querySelector('input.precio-final-iva');
      if (!tdPrecio || !tdPrecioIva || !tdIvaUnit) continue;
      // Tomar el descuento desde el input si existe; si no, del array
      const inputDesc = tr.querySelector('input.descuento');
      let desc = inputDesc ? parsearImporte(inputDesc.value) : Number(franjas[idx]?.descuento || 0);
      if (!Number.isFinite(desc)) desc = 0;
      // Limitar a rango [0, 60]
      desc = Math.max(0, Math.min(60, desc));
      // Redondear a 5 decimales y sincronizar el descuento editado con el array en memoria
      const desc5 = Math.round(desc * 100000) / 100000;
      if (franjas[idx]) franjas[idx].descuento = desc5;
      const base = Number(subtotal) || 0;
      const aplicado = base > 0 ? Math.max(0, base * (1 - (Number.isFinite(desc5) ? desc5 : 0) / 100)) : 0;
      const ivaUnit = aplicado * (Number(impuestos) / 100);
      const totalConIva = aplicado + ivaUnit;
      const fmt5 = (n) => Number.isFinite(n)
        ? n.toLocaleString('es-ES', { minimumFractionDigits: 5, maximumFractionDigits: 5 })
        : '-';
      const fmt3 = (n) => Number.isFinite(n)
        ? n.toLocaleString('es-ES', { minimumFractionDigits: 3, maximumFractionDigits: 3 })
        : '-';
      tdPrecio.textContent = fmt5(aplicado);
      tdPrecioIva.textContent = fmt3(totalConIva);
      tdIvaUnit.textContent = fmt5(ivaUnit);
      
      // Actualizar el input de precio final con IVA con el valor calculado
      if (inputPrecioFinal) {
        inputPrecioFinal.value = totalConIva.toFixed(3);
      }
    }
  } catch (e) {
    console.debug('actualizarPreciosAplicados error:', e);
  }
}

async function getFranjas(productoId) {
  const fuentes = [
    { base: API_URL_PRIMARY, prefix: '/api' },
    { base: API_URL_PRIMARY, prefix: '' },
    { base: API_URL_FALLBACK, prefix: '/api' },
    { base: API_URL_FALLBACK, prefix: '' },
  ];
  let lastError;
  for (const f of fuentes) {
    const url = `${f.base}${f.prefix}/productos/${productoId}/franjas_descuento`;
    console.debug('[FRANJAS] GET intent:', url);
    try {
      const data = await fetchConManejadorErrores(url);
      return Array.isArray(data.franjas) ? data.franjas : [];
    } catch (e) {
      lastError = e;
      console.debug('[FRANJAS] GET fallo:', e?.message || e);
      // probar siguiente
    }
  }
  if (lastError) throw lastError;
  return [];
}

async function saveFranjas(productoId, franjasListado) {
  const fuentes = [
    { base: API_URL_PRIMARY, prefix: '/api' },
    { base: API_URL_PRIMARY, prefix: '' },
    { base: API_URL_FALLBACK, prefix: '/api' },
    { base: API_URL_FALLBACK, prefix: '' },
  ];
  const payload = JSON.stringify(franjasListado);
  const headers = { 'Content-Type': 'application/json' };
  let lastError;
  for (const f of fuentes) {
    const url = `${f.base}${f.prefix}/productos/${productoId}/franjas_descuento`;
    console.debug('[FRANJAS] POST intent:', url);
    try {
      await fetchConManejadorErrores(url, { method: 'POST', headers, body: payload });
      return true;
    } catch (e) {
      lastError = e;
      console.debug('[FRANJAS] POST fallo:', e?.message || e);
    }
  }
  if (lastError) throw lastError;
  return false;
}

// Variable para trackear cambios sin guardar
let cambiosSinGuardar = false;
let franjasOriginales = [];

async function cargarFranjasSeleccionado() {
  const id = getSelectedProductoId();
  if (!id) { setStatus('Seleccione un producto válido', false); return; }
  setStatus('Cargando...');
  try {
    const raw = await getFranjas(id);
    franjas = (Array.isArray(raw) ? raw : []).map(f => {
      const min = Number(f.min || f.min_cantidad || 0) || 0;
      const max = Number(f.max || f.max_cantidad || 0) || 0;
      let d = Number(f.descuento ?? f.porcentaje_descuento ?? 0) || 0;
      // El backend ya entrega porcentaje (0-60). Limitar a rango [0, 60]
      d = Math.max(0, Math.min(60, d));
      return { min, max, descuento: d };
    });
    franjas = normalizeFranjasArray(franjas);
    // Guardar copia de las franjas originales para detectar cambios
    franjasOriginales = JSON.parse(JSON.stringify(franjas));
    cambiosSinGuardar = false;
    renderFranjas();
    setStatus(`Cargadas ${franjas.length} franjas`);
  } catch (e) {
    console.error(e);
    setStatus(`Error al cargar: ${e.message}`, false);
  }
}

btnAñadir.addEventListener('click', () => {
  añadirFranja();
});

btnGuardar.addEventListener('click', async () => {
  try {
    const id = getSelectedProductoId();
    if (!id) { setStatus('Seleccione un producto válido', false); return; }
    let listado = leerFranjasDeTabla(); // ya normalizado
    console.log('[FRANJAS] Datos leídos de tabla:', listado);
    // Asegurar precios con IVA estrictamente decrecientes sin repetición
    listado = enforceStrictDecreasingPrices(listado);
    console.log('[FRANJAS] Datos después de enforce:', listado);
    await saveFranjas(id, listado);
    franjas = listado;
    // Actualizar franjas originales y resetear flag de cambios
    franjasOriginales = JSON.parse(JSON.stringify(listado));
    cambiosSinGuardar = false;
    setStatus('Guardado correctamente');
    console.log('[FRANJAS] Guardado exitoso');
  } catch (e) {
    console.error('[FRANJAS] Error al guardar:', e);
    setStatus(`Error al guardar: ${e.message}`, false);
  }
});

// Inicialización: cargar productos en el selector y respetar ?producto_id=
(async function init() {
  try {
    setStatus('Cargando productos...');
    productosCache = await cargarProductos();
    const opciones = productosCache.map(p => `<option value="${p.id}">${p.nombre}</option>`).join('');
    if (productoSelect) {
      productoSelect.innerHTML = '<option value="">-- Seleccione producto --</option>' + opciones;
    }

    const params = new URLSearchParams(window.location.search);
    const pid = Number(params.get('producto_id') || 0);
    const fromGestion = params.get('from') === 'gestion';
    
    // Asegurar que el botón esté oculto por defecto (forzar prioridad)
    if (btnVolver) {
      btnVolver.style.setProperty('display', 'none', 'important');
    }
    
    if (pid) {
      productoSelect.value = String(pid);
      
      // Desactivar selector y búsqueda cuando se gestiona un producto específico
      productoSelect.disabled = true;
      if (productoSearch) {
        productoSearch.disabled = true;
        productoSearch.placeholder = 'Gestionando producto específico';
      }
      
      // Mostrar botón Volver SOLO si venimos de gestión de productos
      if (btnVolver && fromGestion) {
        console.log('[FRANJAS] Mostrando botón Volver - from=gestion detectado');
        btnVolver.style.setProperty('display', 'inline-flex', 'important');
        btnVolver.addEventListener('click', () => {
          window.location.href = `GESTION_PRODUCTOS.html?id=${encodeURIComponent(pid)}`;
        });
      } else {
        console.log('[FRANJAS] Ocultando botón Volver - from=gestion NO detectado');
        if (btnVolver) {
          btnVolver.style.setProperty('display', 'none', 'important');
        }
      }
    } else {
      console.log('[FRANJAS] No hay producto_id - botón Volver permanece oculto');
      if (btnVolver) {
        btnVolver.style.setProperty('display', 'none', 'important');
      }
    }
    setStatus('');

    // Si hay producto preseleccionado, cargar franjas automáticamente
    if (getSelectedProductoId()) {
      actualizarCabeceraPrecioIVA();
      await cargarFranjasSeleccionado();
    }
  } catch (e) {
    console.error('Error cargando productos:', e);
    setStatus('No se pudieron cargar los productos', false);
  }
})();

// Buscador por concepto: filtra opciones del select
function aplicarFiltroProductos(term) {
  const t = norm(term).trim();
  const prevValue = productoSelect.value || '';
  const filtrados = productosCache.filter(p => norm(`${p.nombre}`).includes(t));
  const opciones = filtrados
    .map(p => `<option value="${p.id}">${p.nombre}</option>`)
    .join('');
  productoSelect.innerHTML = '<option value="">-- Seleccione producto --</option>' + opciones;
  // Si había uno seleccionado y sigue estando, mantenerlo; si no, seleccionar el primero encontrado
  if (prevValue && filtrados.some(p => String(p.id) === String(prevValue))) {
    productoSelect.value = prevValue;
  } else if (filtrados.length > 0) {
    productoSelect.value = String(filtrados[0].id);
    // disparar change para cargar franjas del primer resultado
    productoSelect.dispatchEvent(new Event('change'));
  }
  actualizarCabeceraPrecioIVA();
}

if (productoSearch && productoSelect) {
  const handleFiltroDebounced = debounce((e) => {
    aplicarFiltroProductos(e.target.value);
  }, 300);
  productoSearch.addEventListener('input', handleFiltroDebounced);
}

// Al cambiar el producto, cargar sus franjas
if (productoSelect) {
  productoSelect.addEventListener('change', async () => {
    // Si hay cambios sin guardar, preguntar antes de cambiar
    if (cambiosSinGuardar) {
      const guardar = await mostrarConfirmacion('Hay cambios sin guardar. ¿Desea guardarlos antes de cambiar de producto?');
      if (guardar) {
        // Intentar guardar
        try {
          const id = getSelectedProductoId();
          if (id) {
            let listado = leerFranjasDeTabla();
            listado = enforceStrictDecreasingPrices(listado);
            await saveFranjas(id, listado);
            cambiosSinGuardar = false;
          }
        } catch (e) {
          console.error('[FRANJAS] Error al guardar:', e);
          setStatus(`Error al guardar: ${e.message}`, false);
          return; // No cambiar de producto si falla el guardado
        }
      } else {
        cambiosSinGuardar = false; // Descartar cambios
      }
    }
    
    if (getSelectedProductoId()) {
      actualizarCabeceraPrecioIVA();
      cargarFranjasSeleccionado();
    }
  });
}

// Detectar cuando el usuario intenta salir de la página con cambios sin guardar
// Interceptar clics en enlaces y botones de navegación
document.addEventListener('click', async (e) => {
  // Detectar si es un clic en un enlace de navegación o botón volver
  const link = e.target.closest('a[href], a[data-target]');
  const btnVolver = e.target.closest('#btnVolver');
  
  if ((link || btnVolver) && cambiosSinGuardar) {
    e.preventDefault();
    e.stopPropagation();
    
    const guardar = await mostrarConfirmacion('Hay cambios sin guardar. ¿Desea guardarlos antes de salir?');
    if (guardar) {
      // Intentar guardar
      try {
        const id = getSelectedProductoId();
        if (id) {
          let listado = leerFranjasDeTabla();
          listado = enforceStrictDecreasingPrices(listado);
          await saveFranjas(id, listado);
          cambiosSinGuardar = false;
          setStatus('Guardado correctamente');
          
          // Continuar con la navegación
          setTimeout(() => {
            if (link) {
              if (link.dataset.target) {
                window.location.href = link.dataset.target;
              } else {
                window.location.href = link.href;
              }
            } else if (btnVolver) {
              window.history.back();
            }
          }, 500);
        }
      } catch (e) {
        console.error('[FRANJAS] Error al guardar:', e);
        setStatus(`Error al guardar: ${e.message}`, false);
      }
    } else {
      // Descartar cambios y continuar
      cambiosSinGuardar = false;
      if (link) {
        if (link.dataset.target) {
          window.location.href = link.dataset.target;
        } else {
          window.location.href = link.href;
        }
      } else if (btnVolver) {
        window.history.back();
      }
    }
  }
}, true); // Usar capture para interceptar antes

// Navegación mediante clics ya interceptada por listener global de document

//
