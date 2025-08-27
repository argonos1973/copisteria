import { IP_SERVER, PORT, API_PRODUCTOS, API_PRODUCTOS_FALLBACK } from './constantes.js';

export const PRODUCTO_ID_LIBRE = '94';

/* ================= Loading Overlay ================= */
let overlayDiv;

function crearOverlay() {
  if (overlayDiv) return overlayDiv; // ya existe
  overlayDiv = document.createElement('div');
  overlayDiv.id = 'loading-overlay';
  overlayDiv.innerHTML = '<div class="loading-spinner"></div>';
  overlayDiv.style.position = 'fixed';
  overlayDiv.style.top = '0';
  overlayDiv.style.left = '0';
  overlayDiv.style.width = '100%';
  overlayDiv.style.height = '100%';
  overlayDiv.style.background = 'rgba(0,0,0,0.7)';
  overlayDiv.style.display = 'flex';
  overlayDiv.style.alignItems = 'center';
  overlayDiv.style.justifyContent = 'center';
  overlayDiv.style.zIndex = '9999';
  overlayDiv.style.visibility = 'hidden';
  overlayDiv.style.opacity = '0';
  overlayDiv.style.transition = 'opacity 0.3s ease, visibility 0.3s ease';

  // Estilos del spinner
  const style = document.createElement('style');
  style.textContent = `#loading-overlay .loading-spinner { border: 8px solid #f3f3f3; border-top: 8px solid #3498db; border-radius: 50%; width: 64px; height: 64px; animation: loading-spin 1s linear infinite; } @keyframes loading-spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`;
  document.head.appendChild(style);
  document.body.appendChild(overlayDiv);
  return overlayDiv;
}

export function mostrarCargando() {
  const ov = crearOverlay();
  ov.style.visibility = 'visible';
  ov.style.opacity = '1';
}

export function ocultarCargando() {
  if (!overlayDiv) return;
  overlayDiv.style.opacity = '0';
  overlayDiv.addEventListener('transitionend', () => {
    overlayDiv.style.visibility = 'hidden';
  }, { once: true });
}

document.addEventListener('DOMContentLoaded', () => {
  crearOverlay();
  // Mostrar overlay al enviar cualquier formulario
  document.body.addEventListener('submit', () => {
    mostrarCargando();
  }, true);
});
/* =================================================== */

// === Utilidades auxiliares ===
/**
 * Devuelve una versión debounced de la función pasada que se ejecutará
 * después de que no se invoque durante *delay* ms.
 * @param {Function} fn - función original
 * @param {number} delay - retraso en ms
 * @returns {Function}
 */
export function debounce(fn, delay = 300) {
  let timeout;
  return function (...args) {
    clearTimeout(timeout);
    timeout = setTimeout(() => fn.apply(this, args), delay);
  };
}

// --- Global fetch wrapper ---
const originalFetch = window.fetch.bind(window);
window.fetch = async (...args) => {
  mostrarCargando();
  try {
    return await originalFetch(...args);
  } finally {
    ocultarCargando();
  }
};
// --- Fin wrapper ---

export function truncarDecimales(numero, decimales) {
  const factor = Math.pow(10, decimales);
  return Math.floor(numero * factor) / factor;
}

export function formatearImporte(importe) {
 
  if (typeof importe !== 'number' || isNaN(importe)) {
   
    return "0,00 €";
  }
  return importe.toLocaleString('es-ES', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
    useGrouping: true
  }) + ' €';
}

export function formatearApunto(importe) {
  if (typeof importe === 'number') {
    return importe;
  }
  // Si es string, limpiar el formato
  return parseFloat(importe.toString().replace(',', '.').replace(' €', '')) || 0;
}

// Convierte string con formato europeo a número, conserva números
export function parsearImporte(valor) {
  if (typeof valor === 'number') return valor;
  if (typeof valor !== 'string') return 0;

  // Normalizar espacios y símbolo de euro
  let s = valor.replace(/\s|\u00A0/g, '').replace(/€|eur?/gi, '').trim();
  if (!s) return 0;

  // Si contiene ambos símbolos ',' y '.' decidir el separador decimal por la última aparición
  const tieneComa = s.includes(',');
  const tienePunto = s.includes('.');
  if (tieneComa && tienePunto) {
    const lastComma = s.lastIndexOf(',');
    const lastDot = s.lastIndexOf('.');
    if (lastComma > lastDot) {
      // Coma es decimal (formato europeo: 1.234,56)
      s = s.replace(/\./g, '').replace(',', '.');
    } else {
      // Punto es decimal (formato americano: 1,234.56)
      s = s.replace(/,/g, '');
    }
  } else if (tieneComa) {
    // Solo coma: tratar como decimal
    s = s.replace(',', '.');
  } else {
    // Solo punto o sin separadores: dejar tal cual
  }

  const n = Number(s);
  return isNaN(n) ? 0 : n;
}

// Cache de franjas por producto
const productDiscountBands = {};
let fetchingBands = {};

async function fetchFranjasProducto(productoId) {
  if (!productoId) return null;
  if (fetchingBands[productoId]) return null;
  fetchingBands[productoId] = true;
  const urls = [
    `${API_PRODUCTOS}/${productoId}/franjas_descuento`,
    `${API_PRODUCTOS_FALLBACK}/${productoId}/franjas_descuento`
  ];
  for (const url of urls) {
    try {
      const res = await fetch(url);
      if (!res.ok) continue;
      const data = await res.json();
      if (data && Array.isArray(data.franjas)) {
        productDiscountBands[productoId] = data.franjas.map(f => ({
          min: Number(f.min) || 0,
          max: Number(f.max) || 0,
          descuento: Number(f.descuento) || 0
        }));
        break;
      }
    } catch (_) { /* intentar siguiente url */ }
  }
  fetchingBands[productoId] = false;
  return productDiscountBands[productoId] || null;
}

function getFranjasCached(productoId) {
  const franjas = productDiscountBands[productoId];
  if (!franjas) {
    // Disparar fetch en segundo plano; primer cálculo usará fallback global
    fetchFranjasProducto(productoId);
  }
  return franjas || null;
}

export function calcularPrecioConDescuento(precioUnitarioSinIVA, cantidad, tipoFactura = null, tipoDocumento = 'proforma', productoId = null) {
  // Si tipoFactura es una cadena vacía, tratarlo como 'N' (aplicar descuentos)
  if (tipoFactura === '') {
    tipoFactura = 'N';
  }
  
  // En tickets siempre aplicar descuentos
  if (tipoDocumento === 'ticket') {
    return aplicarDescuentoPorFranja(precioUnitarioSinIVA, cantidad, productoId);
  }
  
  // En facturas nunca aplicar descuentos
  if (tipoDocumento === 'factura') {
    return precioUnitarioSinIVA;
  }
  
  // En proformas, aplicar descuentos solo si el tipo NO es 'A'
  if (tipoFactura === 'A') {
    return precioUnitarioSinIVA;
  }

  // Aplicar descuento por defecto (para proformas tipo 'N' u otros casos)
  return aplicarDescuentoPorFranja(precioUnitarioSinIVA, cantidad, productoId);
}

function aplicarDescuentoPorFranja(precioUnitarioSinIVA, cantidad, productoId = null) {
  // Intentar usar franjas específicas por producto; si no hay, usar fallback global
  const porProducto = productoId ? getFranjasCached(productoId) : null;
  const franjas = porProducto || [
    { min: 1, max: 10,   descuento: 0 },
    { min: 11, max: 50,  descuento: 5 },
    { min: 51, max: 99,  descuento: 10},
    { min: 100, max: 200,descuento: 15},
    { min: 201, max: 300,descuento: 20},
    { min: 301, max: 400,descuento: 25},
    { min: 401, max: 500,descuento: 30},
    { min: 501, max: 600,descuento: 35},
    { min: 601, max: 700,descuento: 40},
    { min: 701, max: 800,descuento: 45},
    { min: 801, max: 900,descuento: 50},
    { min: 901, max: 9999, descuento: 55 },
  ];

  let descuentoAplicable = 0;
  for (let i = 0; i < franjas.length; i++) {
    const franja = franjas[i];
    if (cantidad >= franja.min && cantidad <= franja.max) {
      descuentoAplicable = franja.descuento;
      break;
    }
  }
  if (cantidad > franjas[franjas.length - 1].max) {
    descuentoAplicable = franjas[franjas.length - 1].descuento;
  }

  const factorDescuento = (100 - descuentoAplicable) / 100;
  return precioUnitarioSinIVA * factorDescuento;
}

export function calcularTotalDetalle() {
  const cantidadElem    = document.getElementById('cantidad-detalle');
  const impuestoElem    = document.getElementById('impuesto-detalle');
  const totalElem       = document.getElementById('total-detalle');
  const precioDetalleElem = document.getElementById('precio-detalle');
  const select          = document.getElementById('concepto-detalle');

  if (!cantidadElem || !select || !impuestoElem || !totalElem || !precioDetalleElem) {
    console.error("Uno o más elementos necesarios no existen en el DOM.");
    return;
  }

  const selectedOption  = select.options[select.selectedIndex];
  const productoId      = selectedOption.value;
  const cantidad        = parseFloat(cantidadElem.value) || 0;
  
  // Comprobar si el campo de impuestos está vacío para tratarlo como 0%
  let impuestos = 0;
  if (impuestoElem.value === '') {
    // Si está vacío, dejarlo así en la UI pero usar 0 para cálculos
    console.log("Campo IVA vacío, usando 0% para el cálculo");
    impuestos = 0;
  } else {
    // Si tiene valor, parsearlo normalmente
    impuestos = parseFloat(impuestoElem.value) || 0;
  }

  if (cantidad < 1) {
    totalElem.value = "0.00";
    return;
  }

  if (productoId === PRODUCTO_ID_LIBRE) {
    if (document.activeElement === totalElem) {
      // Si estamos editando el total, calculamos el precio unitario
      const totalIngresado = parseFloat(totalElem.value) || 0;
      const precioUnitario = (totalIngresado / (1 + impuestos / 100)) / cantidad;
      precioDetalleElem.value = precioUnitario.toFixed(5);
    } else {
      // Si estamos editando el precio o la cantidad, calculamos el total
      const precioUnitario = parseFloat(precioDetalleElem.value) || 0;
      const subtotal = precioUnitario * cantidad;
      const total = subtotal * (1 + impuestos / 100);
      totalElem.value = total.toFixed(2);
    }
  } else {
    let precioOriginal = parseFloat(selectedOption.dataset.precioOriginal) || 0;
    
    // Obtener el tipo de proforma o factura correcto (usar el campo oculto como fuente principal)
    let tipoDocumento = 'N';
    
    // Verificar primero si estamos en una proforma
    const tipoProformaElem = document.getElementById('tipo-proforma');
    if (tipoProformaElem) {
      tipoDocumento = tipoProformaElem.value;
      console.log('Detectado tipo de proforma:', tipoDocumento);
    } else {
      // Si no es proforma, verificar si es una factura
      const tipoFacturaElem = document.getElementById('tipo-factura');
      if (tipoFacturaElem) {
        tipoDocumento = tipoFacturaElem.value;
        console.log('Detectado tipo de factura:', tipoDocumento);
      } else {
        // Si no se encuentra ningún elemento, usar el valor predeterminado
        tipoDocumento = sessionStorage.getItem('tipoProforma') || 'N';
        console.log('Usando tipo predeterminado:', tipoDocumento);
      }
    }
    
    console.log(`Tipo de documento detectado: ${tipoDocumento}`);
    
    // Determinar el precio final (sin aplicar descuentos si es tipo A)
    let precioFinal;
    
    if (tipoDocumento === 'A') {
      // Para documentos tipo A, NO aplicar descuento (devolver precio original)
      console.log('Documento tipo A: NO se aplican descuentos por franja');
      precioFinal = precioOriginal;
    } else {
      // Para documentos tipo N, calcular con descuentos
      console.log('Documento tipo N: SÍ se aplican descuentos por franja');
      // calcularPrecioConDescuento(precio, cantidad, tipoFactura, tipoDocumento, productoId)
      precioFinal = calcularPrecioConDescuento(precioOriginal, cantidad, null, tipoDocumento, productoId);
    }
    
    const subtotal = precioFinal * cantidad;
    const total = subtotal * (1 + impuestos / 100);

    precioDetalleElem.value = precioFinal.toFixed(5);
    totalElem.value = total.toFixed(2);
  }
}

let onCobrarCallback = null;

/**
 * Crea el HTML del modal de pagos si no existe
 * @param {string} titulo - Título del modal (ej: "Añadir Pago", "Cobrar Proforma")
 * @returns {HTMLElement} El elemento del modal
 */
function crearModalPagos(titulo = 'Añadir Pago') {
  // Eliminar modal existente si hay uno
  let modalExistente = document.getElementById('modal-pagos');
  if (modalExistente) {
    modalExistente.remove();
  }

  // Crear nuevo modal con título actualizado
  let modal = document.createElement('div');
  modal.id = 'modal-pagos';
  modal.style.display = 'none';
  
  modal.innerHTML = `
    <div class="modal-content">
      <div class="modal-header">
        <h3>${titulo}</h3>
        <span class="close" id="closeModal">&times;</span>
      </div>
      <div class="modal-body">
        <div class="modal-linea">
          <div class="modal-campo">
            <label for="modal-total-ticket">Total (€):</label>
            <input type="text" 
                   id="modal-total-ticket" 
                   value="0,00" 
                   inputmode="decimal"
                   class="right-aligned" />
          </div>
          <div class="modal-campo">
            <label for="modal-metodo-pago">Forma de Pago:</label>
            <select id="modal-metodo-pago" style="padding: 8px; border: 1px solid #ddd; border-radius: 4px;">
              <option value="E">Efectivo</option>
              <option value="T">Tarjeta</option>
              <option value="R">Transferencia</option>
            </select>
          </div>
          <div class="modal-campo">
            <label for="modal-fecha-ticket">Fecha de Pago:</label>
            <input type="text"
                   id="modal-fecha-ticket"
                   class="readonly-field right-aligned"
                   style="width: 140px;"
                   readonly />
          </div>
        </div>
        <div class="modal-linea">
          <div class="modal-campo">
            <label for="modal-total-entregado">Total Entregado (€):</label>
            <input type="text" id="modal-total-entregado" value="0,00" inputmode="decimal" class="right-aligned" />
          </div>
          <div class="modal-campo">
            <label for="modal-total-cambio">Total Cambio (€):</label>
            <input type="text" id="modal-total-cambio" value="0,00" inputmode="decimal" readonly class="readonly-field right-aligned" />
          </div>
          <div class="modal-campo" style="visibility: hidden;">
            <!-- Campo invisible para mantener alineamiento -->
            <label>&nbsp;</label>
            <input type="text" style="visibility: hidden;" />
          </div>
        </div>
        <div class="modal-linea boton-centro">
          <button type="button" id="btn-cobrar">Cobrar</button>
        </div>
      </div>
    </div>
  `;

  document.body.appendChild(modal);
  return modal;
}

/**
 * Abre el modal de pagos
 */
export function abrirModalPagos({ total, fecha, formaPago = 'E', titulo = 'Añadir Pago', onCobrar = null, modoGuardar = false }) {
  // Forzar recreación del modal para actualizar el título
  let modalExistente = document.getElementById('modal-pagos');
  if (modalExistente) {
    modalExistente.remove();
  }

  const modal = crearModalPagos(titulo);
  const modalContent = modal.querySelector('.modal-content');
  
  // Guardar el callback
  onCobrarCallback = onCobrar;
  
  // Establecer valores iniciales
  const totalInput = document.getElementById('modal-total-ticket');
  const fechaInput = document.getElementById('modal-fecha-ticket');
  const metodoPagoInput = document.getElementById('modal-metodo-pago');
  const totalEntregadoInput = document.getElementById('modal-total-entregado');
  const totalCambioInput = document.getElementById('modal-total-cambio');

  if (totalInput) {
    // Normalizar a número aunque llegue como string con formato europeo/€
    const num = (typeof total === 'number') ? total : parsearImporte(total);
    totalInput.value = new Intl.NumberFormat('es-ES', { minimumFractionDigits: 2, maximumFractionDigits: 2, useGrouping: true }).format(Number(num) || 0);
  }
  if (fechaInput) fechaInput.value = fecha;
  if (metodoPagoInput) metodoPagoInput.value = formaPago;
  // Igualar 'Total Entregado' al total del ticket al abrir
  if (totalEntregadoInput && totalInput) {
    // Igualar con el mismo formateo europeo
    totalEntregadoInput.value = totalInput.value;
  } else if (totalEntregadoInput) {
    totalEntregadoInput.value = '0,00';
  }
  if (totalCambioInput) totalCambioInput.value = '0,00';

  // Recalcular cambio (debe ser 0 si total entregado == total)
  try { calcularCambioModal(); } catch (_) {}
  
  // Actualizar el texto del botón según el modo
  const btnCobrar = document.getElementById('btn-cobrar');
  if (btnCobrar) {
    if (modoGuardar) {
      btnCobrar.textContent = 'Guardar';
      btnCobrar.dataset.modo = 'guardar';
    } else {
      btnCobrar.textContent = 'Cobrar';
      btnCobrar.dataset.modo = 'cobrar';
    }
  }
  
  // Mostrar el modal
  modal.style.display = 'block';

  // Inicializar eventos si no se han inicializado
  inicializarEventosModal();
}

/**
 * Cierra el modal de pagos
 */
export function cerrarModalPagos() {
  const modal = document.getElementById('modal-pagos');
  if (!modal) return;

  const modalContent = modal.querySelector('.modal-content');
  if (!modalContent) return;

  // Ocultar el modal
  modal.style.display = 'none';
  
  // Limpiar el callback
  onCobrarCallback = null;
}

/**
 * Calcula el cambio a devolver
 */
export function calcularCambio(totalTicket, totalEntregado) {
  let cambio = totalEntregado - totalTicket;
  return cambio > 0 ? cambio : 0;
}

/**
 * Inicializa los eventos del modal de pagos
 */
export function inicializarEventosModal() {
  const modalTotalEntregado = document.getElementById('modal-total-entregado');
  const modalTotalCambio = document.getElementById('modal-total-cambio');
  const modalTotalTicket = document.getElementById('modal-total-ticket');
  const btnCobrar = document.getElementById('btn-cobrar');
  const closeModal = document.getElementById('closeModal');

  // Calcular cambio cuando se modifica el total entregado o el total
  if (modalTotalEntregado) {
    modalTotalEntregado.removeEventListener('input', calcularCambioModal);
    modalTotalEntregado.addEventListener('input', calcularCambioModal);
  }
  
  if (modalTotalTicket) {
    modalTotalTicket.removeEventListener('input', calcularCambioModal);
    modalTotalTicket.addEventListener('input', calcularCambioModal);
  }

  // Configurar el botón de cobrar
  if (btnCobrar) {
    btnCobrar.removeEventListener('click', onCobrarClick);
    btnCobrar.addEventListener('click', onCobrarClick);
  }

  // Cerrar modal con el botón X
  if (closeModal) {
    closeModal.removeEventListener('click', cerrarModalPagos);
    closeModal.addEventListener('click', cerrarModalPagos);
  }

  // Cerrar modal con ESC
  document.removeEventListener('keydown', onEscKeyPress);
  document.addEventListener('keydown', onEscKeyPress);
}

/**
 * Calcula el cambio en el modal
 */
function calcularCambioModal() {
  const totalTicket = parsearImporte(document.getElementById('modal-total-ticket').value) || 0;
  const totalEntregado = parsearImporte(document.getElementById('modal-total-entregado').value) || 0;
  const cambio = calcularCambio(totalTicket, totalEntregado);
  document.getElementById('modal-total-cambio').value = cambio.toFixed(2);
}

/**
 * Maneja el clic en el botón cobrar
 */
function onCobrarClick() {
  if (onCobrarCallback) {
    const formaPago = document.getElementById('modal-metodo-pago').value;
    const totalPago = parsearImporte(document.getElementById('modal-total-entregado').value) || 0;
    const total = parsearImporte(document.getElementById('modal-total-ticket').value) || 0;
    
    // Comprobar qué modo estamos usando (guardar o cobrar)
    const btnCobrar = document.getElementById('btn-cobrar');
    const esGuardar = btnCobrar && btnCobrar.dataset.modo === 'guardar';
    
    if (esGuardar) {
      // Si estamos guardando, pasamos 0 como importe y 'P' como estado
      onCobrarCallback(formaPago, 0, 'P');
    } else {
      // Si estamos cobrando, pasamos el total entregado
      onCobrarCallback(formaPago, totalPago, 'C');
    }
  }
  cerrarModalPagos();
}

/**
 * Maneja la tecla ESC para cerrar el modal
 */
function onEscKeyPress(e) {
  if (e.key === 'Escape') {
    cerrarModalPagos();
  }
}

/**
 * Actualiza el total en el modal
 */
export function actualizarTotalModal(total) {
  const modalTotalTicket = document.getElementById('modal-total-ticket');
  if (modalTotalTicket) {
    modalTotalTicket.value = parseFloat(total).toFixed(2);
  }
}

// Función para formatear números como moneda
export const formatCurrency = (amount) => {
    return new Intl.NumberFormat('es-ES', {
        style: 'decimal',
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    }).format(amount);
};

// Función para formatear fechas
export const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('es-ES');
};

// Función para obtener el estado formateado
export const getEstadoFormateado = (estado) => {
    const estados = {
        // Estados de facturas
        'P': 'Pendiente',
        'C': 'Cobrada',
        'V': 'Vencida',
        'RE': 'Rectificativa',
        // Estados de proformas
        'A': 'Abierta',
        'F': 'Facturada'
        // Nota: 'C' ya está definido arriba y significa 'Cobrada' para facturas y 'Cerrada' para proformas
    };
    return estados[estado] || estado;
};

// Función para convertir el estado formateado de vuelta al código
export const getCodigoEstado = (estadoFormateado) => {
    const codigosEstado = {
        // Estados de facturas
        'Pendiente': 'P',
        'Cobrada': 'C',
        'Vencida': 'V',
        // Estados de proformas
        'Abierta': 'A',
        'Cerrada': 'C',
        'Facturada': 'F'
    };
    return codigosEstado[estadoFormateado] || estadoFormateado;
};

// Función para obtener la clase CSS según el estado
export const getEstadoClass = (estado) => {
    const clases = {
        // Estados de facturas
        'P': 'estado-pendiente',
        'C': 'estado-cobrado',
        'V': 'estado-vencido',
        'RE': 'estado-rectificativa',
        // Estados de proformas
        'A': 'estado-pendiente',
        'F': 'estado-cobrado'     // Facturada - mismo estilo que cobrado
        // Nota: 'C' ya está definido arriba y se usa tanto para facturas (Cobrada) como para proformas (Cerrada)
    };
    return clases[estado] || '';
}; 

/**
 * Convierte una fecha ISO (o timestamp) en formato DD/MM/YYYY HH:MM.
 */
// Convierte diferentes formatos de fecha (con o sin hora) a YYYY-MM-DD
// Convierte distintos formatos de fecha a YYYY-MM-DD para la API
export function convertirFechaParaAPI(fecha) {
  if (!fecha) return '';
  fecha = String(fecha).trim();
  // Eliminar parte de hora en caso de venir con 'T' o espacio
  if (fecha.includes('T')) {
    fecha = fecha.split('T')[0];
  } else if (fecha.includes(' ')) {
    fecha = fecha.split(' ')[0];
  }

  // Si ya está en formato YYYY-MM-DD válido, devolver tal cual
  if (/^\d{4}-\d{2}-\d{2}$/.test(fecha)) return fecha;

  // Formato DD-MM-YYYY → YYYY-MM-DD
  if (/^\d{1,2}-\d{1,2}-\d{4}$/.test(fecha)) {
    const [dia, mes, anio] = fecha.split('-');
    return `${anio}-${mes.padStart(2,'0')}-${dia.padStart(2,'0')}`;
  }

  // Formato DD/MM/YYYY → YYYY-MM-DD
  if (/^\d{1,2}\/\d{1,2}\/\d{4}$/.test(fecha)) {
    const [dia, mes, anio] = fecha.split('/');
    return `${anio}-${mes.padStart(2,'0')}-${dia.padStart(2,'0')}`;
  }

  // Como último recurso, usar el parser nativo de Date
  const d = new Date(fecha);
  if (!isNaN(d)) {
    return d.toISOString().slice(0,10);
  }

  console.warn('Formato de fecha no reconocido:', fecha);
  return '';
}

// Devuelve fecha en formato DD/MM/YYYY
export function formatearFecha(fecha){
  if(!fecha) return '';
  const d = fecha instanceof Date ? fecha : new Date(fecha);
  if(isNaN(d)) return '';
  const pad = n=>String(n).padStart(2,'0');
  return `${pad(d.getDate())}/${pad(d.getMonth()+1)}/${d.getFullYear()}`;
}


// Nueva utilidad: devuelve solo DD/MM/YYYY sin hora
export function formatearFechaSoloDia(fecha) {
  if (!fecha) return '';
  // Si viene en YYYY-MM-DD o YYYY-MM-DDTHH:mm:ss, procesar rápido
  if (typeof fecha === 'string') {
    // Eliminar parte de hora si existe
    const soloFecha = fecha.split('T')[0].split(' ')[0];
    if (/^\d{4}-\d{2}-\d{2}$/.test(soloFecha)) {
      const [y, m, d] = soloFecha.split('-');
      return `${d}/${m}/${y}`;
    }
    if (/^\d{1,2}\/\d{1,2}\/\d{4}$/.test(soloFecha)) {
      // Ya viene en DD/MM/YYYY
      return soloFecha;
    }
  }
  // Fallback usando Date
  const d = fecha instanceof Date ? fecha : new Date(fecha);
  if (isNaN(d)) return '';
  const pad = n => String(n).padStart(2, '0');
  return `${pad(d.getDate())}/${pad(d.getMonth() + 1)}/${d.getFullYear()}`;
}

/**
 * Realiza un fetch con manejo de errores y devuelve JSON.
 */
export async function fetchConManejadorErrores(url, opciones = {}) {
  try {
    mostrarCargando();
    const res = await fetch(url, opciones);
    if (!res.ok) throw new Error(`Error ${res.status}`);
    return await res.json();
  } finally {
    ocultarCargando();
  }
}
// === Fin funciones añadidas ===
