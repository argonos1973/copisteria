import { IP_SERVER, PORT } from './constantes.js';
import { mostrarNotificacion, mostrarConfirmacion } from './notificaciones.js';
import { formatearImporte, formatearFechaSoloDia, getEstadoFormateado, getEstadoClass } from './scripts_utils.js';

// Overlay utils
const showOverlay = () => { const el = document.getElementById('overlay'); if (el) el.style.display = 'flex'; };
const hideOverlay = () => { const el = document.getElementById('overlay'); if (el) el.style.display = 'none'; };

// Actualiza totales del footer
const updateTotals = (items) => {
  let totalBase = 0, totalIVA = 0, totalCobrado = 0, totalTotal = 0;
  items.forEach(it => {
    totalBase += parseFloat(it.base || 0);
    totalIVA += parseFloat(it.iva || 0);
    totalCobrado += parseFloat(it.importe_cobrado || 0);
    totalTotal += parseFloat(it.total || 0);
  });
  const setText = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = formatearImporte(val); };
  setText('totalBase', totalBase);
  setText('totalIVA', totalIVA);
  setText('totalCobrado', totalCobrado);
  setText('totalTotal', totalTotal);
};

// Búsqueda principal
async function buscarPresupuestos() {
  showOverlay();
  try {
    const startDate = document.getElementById('startDate').value;
    const endDate = document.getElementById('endDate').value;
    // Normalizar estado seleccionado: quitar comillas y barras invertidas, espacios y llevar a mayúsculas
    const statusRaw = document.getElementById('status').value;
    const status = (statusRaw || '').replace(/[\\"']/g, '').trim().toUpperCase();
    const presupuestoNumber = document.getElementById('presupuestoNumber').value.trim();
    const contacto = document.getElementById('contacto').value.trim();
    const identificador = document.getElementById('identificador').value.trim();

    const params = new URLSearchParams();
    const hayFiltrosAdicionales = !!(status || presupuestoNumber || (contacto && contacto.length >= 2) || identificador);
    if (!hayFiltrosAdicionales) {
      if (startDate) params.append('fecha_inicio', startDate);
      if (endDate) params.append('fecha_fin', endDate);
    }
    if (status) params.append('estado', status);
    if (presupuestoNumber) { params.append('numero', presupuestoNumber); params.append('limit','10'); }
    if (contacto && contacto.length >= 2) { params.append('contacto', contacto); params.append('limit','10'); }
    if (identificador) { params.append('identificador', identificador); params.append('limit','10'); }

    const url = `http://${IP_SERVER}:${PORT}/api/presupuestos/consulta?${params.toString()}`;
    // Trazas de depuración (se pueden dejar; ayudan a diagnosticar filtros en producción)
    try { console.debug('[CONSULTA_PRESUPUESTOS] Parámetros', { startDate, endDate, status, presupuestoNumber, contacto, identificador, url }); } catch (_) {}
    const response = await fetch(url);
    if (!response.ok) throw new Error('Error al buscar presupuestos');
    const data = await response.json();
    if (!Array.isArray(data)) throw new Error('Formato de respuesta inválido');

    const tbody = document.getElementById('gridBody');
    tbody.innerHTML = '';

    if (data.length === 0) {
      tbody.innerHTML = '<tr><td colspan="9" class="text-center">No se encontraron resultados</td></tr>';
      updateTotals([]);
      return;
    }

    let totalBase = 0, totalIVA = 0, totalCobrado = 0, totalTotal = 0;

    data.forEach(item => {
      const row = document.createElement('tr');
      const base = parseFloat(item.base) || 0;
      const iva = parseFloat(item.iva) || 0;
      const cobrado = parseFloat(item.importe_cobrado) || 0;
      const total = parseFloat(item.total) || 0;

      const accionesTd = document.createElement('td');
      accionesTd.className = 'text-center';

      // Convertir a Factura
      if (item.estado !== 'F') {
        const iconFactura = document.createElement('i');
        iconFactura.className = 'fas fa-file-invoice action-icon';
        iconFactura.title = 'Convertir a Factura';
        iconFactura.style.cursor = 'pointer';
        iconFactura.style.marginLeft = '5px';
        iconFactura.style.color = '#007bff';
        iconFactura.addEventListener('click', async (event) => {
          event.stopPropagation();
          try {
            const confirmado = await mostrarConfirmacion(`¿Convertir el presupuesto ${item.numero} a factura?`);
            if (confirmado) {
              showOverlay();
              const resp = await fetch(`http://${IP_SERVER}:${PORT}/api/presupuestos/${item.id}/convertir_factura`, { method: 'POST', headers: { 'Content-Type': 'application/json' } });
              if (!resp.ok) throw new Error('Error al convertir presupuesto a factura');
              const result = await resp.json();
              mostrarNotificacion(`Presupuesto ${item.numero} convertido a factura ${result.numero_factura}`, 'success');
              setTimeout(() => buscarPresupuestos(), 800);
            }
          } catch (e) {
            console.error('Error convirtiendo a factura:', e);
            mostrarNotificacion('Error al convertir a factura', 'error');
          } finally { hideOverlay(); }
        });
        accionesTd.appendChild(iconFactura);
      }

      // Convertir a Ticket (si no convertido)
      if (item.estado !== 'T' && item.estado !== 'F') {
        const iconTicket = document.createElement('i');
        iconTicket.className = 'fas fa-receipt action-icon';
        iconTicket.title = 'Convertir a Ticket';
        iconTicket.style.cursor = 'pointer';
        iconTicket.style.marginLeft = '10px';
        iconTicket.style.color = '#28a745';
        iconTicket.addEventListener('click', async (event) => {
          event.stopPropagation();
          try {
            const confirmado = await mostrarConfirmacion(`¿Convertir el presupuesto ${item.numero} a ticket?`);
            if (confirmado) {
              showOverlay();
              const resp = await fetch(`http://${IP_SERVER}:${PORT}/api/presupuestos/${item.id}/convertir_ticket`, { method: 'POST', headers: { 'Content-Type': 'application/json' } });
              if (!resp.ok) throw new Error('Error al convertir presupuesto a ticket');
              const result = await resp.json();
              mostrarNotificacion(`Presupuesto ${item.numero} convertido a ticket ${result.numero_ticket}`, 'success');
              setTimeout(() => buscarPresupuestos(), 800);
            }
          } catch (e) {
            console.error('Error convirtiendo a ticket:', e);
            mostrarNotificacion('Error al convertir a ticket', 'error');
          } finally { hideOverlay(); }
        });
        accionesTd.appendChild(iconTicket);
      }

      row.innerHTML = `
        <td>${formatearFechaSoloDia(item.fecha)}</td>
        <td>${item.numero}</td>
        <td>${item.razonsocial || ''}</td>
        <td class="text-right">${formatearImporte(base)}</td>
        <td class="text-right">${formatearImporte(iva)}</td>
        <td class="text-right">${formatearImporte(cobrado)}</td>
        <td class="text-right">${formatearImporte(total)}</td>
        <td class="text-center ${getEstadoClass(item.estado)}">${getEstadoFormateado(item.estado)}</td>
      `;
      row.appendChild(accionesTd);

      row.addEventListener('click', () => {
        window.location.href = `GESTION_PRESUPUESTOS.html?idPresupuesto=${item.id}&idContacto=${item.idcontacto}`;
      });

      document.getElementById('gridBody').appendChild(row);
      totalBase += base; totalIVA += iva; totalCobrado += cobrado; totalTotal += total;
    });

    updateTotals([{base: totalBase, iva: totalIVA, importe_cobrado: totalCobrado, total: totalTotal}]);
  } catch (error) {
    console.error('Error al buscar presupuestos:', error);
    mostrarNotificacion('Error al buscar presupuestos', 'error');
  } finally {
    hideOverlay();
  }
}

// Búsqueda interactiva con pequeño delay
let timeoutId = null;
function busquedaInteractiva(event) {
  const valor = event.target.value.trim();
  const campo = event.target.id;
  if (timeoutId) clearTimeout(timeoutId);
  timeoutId = setTimeout(() => {
    if (campo === 'contacto' && (valor.length >= 2 || valor.length === 0)) buscarPresupuestos();
    else if (campo === 'identificador' && (valor.length >= 1 || valor.length === 0)) buscarPresupuestos();
    else if (campo === 'presupuestoNumber' && (valor.length >= 1 || valor.length === 0)) buscarPresupuestos();
  }, 300);
}

// Filtros en sessionStorage
function guardarFiltros() {
  const estadoSel = (document.getElementById('status').value || '').replace(/[\\"']/g, '').trim().toUpperCase();
  const filtros = {
    startDate: document.getElementById('startDate').value,
    endDate: document.getElementById('endDate').value,
    estado: estadoSel,
    numero: document.getElementById('presupuestoNumber').value,
    contacto: document.getElementById('contacto').value,
    identificador: document.getElementById('identificador').value
  };
  sessionStorage.setItem('filtrosPresupuestos', JSON.stringify(filtros));
}

function restaurarFiltros() {
  const filtrosGuardados = sessionStorage.getItem('filtrosPresupuestos');
  if (filtrosGuardados) {
    const filtros = JSON.parse(filtrosGuardados);
    document.getElementById('startDate').value = filtros.startDate || '';
    document.getElementById('endDate').value = filtros.endDate || '';
    const valEstado = (filtros.estado || '').replace(/[\\"']/g, '').trim().toUpperCase();
    document.getElementById('status').value = valEstado || '';
    document.getElementById('presupuestoNumber').value = filtros.numero || '';
    document.getElementById('contacto').value = filtros.contacto || '';
    document.getElementById('identificador').value = filtros.identificador || '';
  } else {
    const today = new Date();
    const firstDay = new Date(today.getFullYear(), today.getMonth(), 1);
    const lastDay = new Date(today.getFullYear(), today.getMonth() + 1, 0);
    const formatDate = (d) => `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;
    document.getElementById('startDate').value = formatDate(firstDay);
    document.getElementById('endDate').value = formatDate(lastDay);
    document.getElementById('status').value = 'B';
    guardarFiltros();
  }
  buscarPresupuestos();
}

// Init
 document.addEventListener('DOMContentLoaded', function () {
  restaurarFiltros();
  document.getElementById('startDate').addEventListener('change', () => { guardarFiltros(); buscarPresupuestos(); });
  document.getElementById('endDate').addEventListener('change', () => { guardarFiltros(); buscarPresupuestos(); });
  document.getElementById('status').addEventListener('change', () => { guardarFiltros(); buscarPresupuestos(); });
  document.getElementById('presupuestoNumber').addEventListener('input', (event) => { guardarFiltros(); busquedaInteractiva(event); });
  document.getElementById('contacto').addEventListener('input', (event) => { guardarFiltros(); busquedaInteractiva(event); });
  document.getElementById('identificador').addEventListener('input', (event) => { guardarFiltros(); busquedaInteractiva(event); });
  
  // Botón Nuevo Presupuesto
  document.getElementById('nuevoPresupuesto').addEventListener('click', () => {
    window.location.href = 'GESTION_PRESUPUESTOS.html';
  });
});
