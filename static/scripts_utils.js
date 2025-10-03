import { IP_SERVER, PORT } from './constantes.js?v=20250911_1135';
import { mostrarConfirmacion } from './notificaciones.js';

export const PRODUCTO_ID_LIBRE = '94';

const INFO_PRECIO_VACIO = {
  precioSinIVA: null,
  precioConIVA: null,
  impuestos: null,
  descuento: null,
  franja: null
};

let ultimaFranjaAplicada = null;
let infoPrecioActual = { ...INFO_PRECIO_VACIO };

function emitirEventoInfoPrecioActualizado() {
  document.dispatchEvent(new CustomEvent('info-precio-actualizado', { detail: obtenerInfoPrecioActual() }));
}

export function registrarFranjaAplicada(franja) {
  if (franja && typeof franja === 'object') {
    ultimaFranjaAplicada = {
      min: franja.min ?? franja.min_cantidad ?? null,
      max: franja.max ?? franja.max_cantidad ?? null,
      descuento: franja.descuento ?? franja.porcentaje_descuento ?? 0
    };
  } else {
    ultimaFranjaAplicada = null;
  }
}

export function obtenerUltimaFranjaAplicada() {
  if (!ultimaFranjaAplicada) return null;
  return { ...ultimaFranjaAplicada };
}

export function actualizarInfoPrecio(precioSinIVA, impuestos) {
  if (typeof precioSinIVA !== 'number' || isNaN(precioSinIVA) || typeof impuestos !== 'number' || isNaN(impuestos)) {
    infoPrecioActual = { ...INFO_PRECIO_VACIO };
    emitirEventoInfoPrecioActualizado();
    return;
  }

  const franja = obtenerUltimaFranjaAplicada();
  const precioConIVA = precioSinIVA * (1 + (impuestos || 0) / 100);

  infoPrecioActual = {
    precioSinIVA,
    precioConIVA,
    impuestos,
    descuento: franja?.descuento ?? 0,
    franja
  };

  emitirEventoInfoPrecioActualizado();
}

export function resetInfoPrecio() {
  ultimaFranjaAplicada = null;
  infoPrecioActual = { ...INFO_PRECIO_VACIO };
  emitirEventoInfoPrecioActualizado();
}

export function obtenerInfoPrecioActual() {
  const franja = obtenerUltimaFranjaAplicada();
  return {
    ...infoPrecioActual,
    franja
  };
}

export function validarContactoFace(contacto) {
  if (!contacto) return { valido: false, errores: ['No hay datos de contacto'] };
  const requiereFace = parsearNumeroBackend(contacto.face_presentacion, 0) === 1;
  if (!requiereFace) {
    return { valido: true, errores: [] };
  }
  const faltantes = [];
  if (!(contacto.dir3_oficina || '').trim()) faltantes.push('DIR3 Oficina contable');
  if (!(contacto.dir3_organo || '').trim()) faltantes.push('DIR3 Órgano gestor');
  if (!(contacto.dir3_unidad || '').trim()) faltantes.push('DIR3 Unidad tramitadora');
  return {
    valido: faltantes.length === 0,
    errores: faltantes
  };
}

export function extraerFranjaDeDataset(dataset) {
  if (!dataset) return null;

  const rawMin = dataset.franjaMin;
  const rawMax = dataset.franjaMax;
  const rawDescuento = dataset.franjaDescuento;

  const parseNullableNumber = (value) => {
    if (value === undefined || value === null || value === '') return null;
    const num = Number(value);
    return Number.isNaN(num) ? null : num;
  };

  const min = parseNullableNumber(rawMin);
  const max = parseNullableNumber(rawMax);
  const descuento = parseNullableNumber(rawDescuento);

  if (min === null && max === null && (descuento === null || Number.isNaN(descuento))) {
    return null;
  }

  return {
    min,
    max,
    descuento: descuento ?? 0
  };
}

export function inicializarInfoPrecioPopup() {
  const infoButton = document.getElementById('btn-info-precio');
  const popup = document.getElementById('popup-info-precio');
  if (!infoButton || !popup) return;

  if (infoButton.dataset.infoPrecioPopup === 'initialized') {
    return;
  }
  infoButton.dataset.infoPrecioPopup = 'initialized';

  const content = popup.querySelector('.info-precio-contenido');
  let infoActual = obtenerInfoPrecioActual();

  const cerrarPopup = () => {
    popup.classList.remove('visible');
    popup.setAttribute('aria-hidden', 'true');
    infoButton.setAttribute('aria-expanded', 'false');
  };

  const actualizarVisibilidadIcono = () => {
    const franjaAplicada = infoActual?.franja || null;
    const descuentoFranja = franjaAplicada ? Number(franjaAplicada.descuento ?? 0) : 0;
    const hayFranjaConDescuento = franjaAplicada && !Number.isNaN(descuentoFranja) && descuentoFranja > 0;
    const precioValido = Number.isFinite(infoActual?.precioSinIVA) && (infoActual?.precioSinIVA ?? 0) > 0;
    if (hayFranjaConDescuento && precioValido) {
      infoButton.classList.remove('oculto');
    } else {
      infoButton.classList.add('oculto');
      cerrarPopup();
    }
  };

  const formatearFranja = (franja) => {
    if (!franja) return 'Sin franja aplicada';
    const { min, max, descuento } = franja;
    const descuentoTexto = `${(descuento ?? 0).toFixed(2)} %`;
    if (min !== null && max !== null) {
      return `${min}-${max} uds · ${descuentoTexto}`;
    }
    if (min !== null) {
      return `≥ ${min} uds · ${descuentoTexto}`;
    }
    if (max !== null) {
      return `≤ ${max} uds · ${descuentoTexto}`;
    }
    return `Descuento ${descuentoTexto}`;
  };

  const renderContenido = () => {
    if (!content) return;

    actualizarVisibilidadIcono();

    const tienePrecio = Number.isFinite(infoActual?.precioSinIVA);
    if (!tienePrecio) {
      content.innerHTML = '<p class="info-precio-vacio">Introduce cantidad y precio para ver los detalles.</p>'
;
      return;
    }

    const tieneIVA = Number.isFinite(infoActual?.impuestos);
    const precioSinIVA = formatearPrecioUnitario(infoActual.precioSinIVA ?? 0);
    const precioConIVA = formatearImporteVariable(infoActual.precioConIVA ?? 0, 2, 2);
    const ivaTexto = tieneIVA ? `${(infoActual.impuestos ?? 0).toFixed(2)} %` : '—';
    const descuentoTexto = `${(infoActual.descuento ?? 0).toFixed(2)} %`;
    const franjaTexto = formatearFranja(infoActual.franja);

    content.innerHTML = `
      <h4>Detalle de precio</h4>
      <ul class="lista-info-precio">
        <li><span>Precio unitario (sin IVA):</span> <strong>${precioSinIVA}</strong></li>
        <li><span>IVA aplicado:</span> <strong>${ivaTexto}</strong></li>
        <li><span>Precio unitario con IVA:</span> <strong>${precioConIVA}</strong></li>
        <li><span>Descuento por franja:</span> <strong>${descuentoTexto}</strong></li>
        <li><span>Franja aplicada:</span> <strong>${franjaTexto}</strong></li>
      </ul>
    `;
  };

  const abrirPopup = () => {
    if (infoButton.classList.contains('oculto')) return;
    renderContenido();
    popup.classList.add('visible');
    popup.setAttribute('aria-hidden', 'false');
    infoButton.setAttribute('aria-expanded', 'true');
    requestAnimationFrame(() => popup.focus());
  };

  infoButton.addEventListener('click', (event) => {
    event.preventDefault();
    if (infoButton.classList.contains('oculto')) return;
    if (popup.classList.contains('visible')) {
      cerrarPopup();
    } else {
      abrirPopup();
    }
  });

  document.addEventListener('click', (event) => {
    if (!popup.classList.contains('visible')) return;
    if (popup.contains(event.target) || event.target === infoButton) return;
    cerrarPopup();
  });

  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && popup.classList.contains('visible')) {
      cerrarPopup();
      infoButton.focus();
    }
  });

  document.addEventListener('info-precio-actualizado', (event) => {
    infoActual = event.detail ?? obtenerInfoPrecioActual();
    actualizarVisibilidadIcono();
    if (popup.classList.contains('visible')) {
      if (infoButton.classList.contains('oculto')) {
        cerrarPopup();
      } else {
        renderContenido();
      }
    }
  });

  actualizarVisibilidadIcono();
  renderContenido();
}

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
export function debounce(fn, delay = 800) {
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

// Redondeo financiero a 2 decimales (ROUND_HALF_UP equivalente en JS)
// Centralizado aquí para evitar duplicados
export function redondearImporte(valor) {
  const n = Number(valor);
  if (!isFinite(n)) return 0;
  // Math.round con factor simula HALF_UP para positivos; para negativos ajustamos
  const factor = 100;
  return (n >= 0)
    ? Math.round(n * factor) / factor
    : -Math.round(Math.abs(n) * factor) / factor;
}

// Función para formatear importes con decimales variables
export function formatearImporteVariable(importe, minDecimals = 2, maxDecimals = 5) {
  if (typeof importe !== 'number' || isNaN(importe)) {
    return "0,00 €";
  }
  return importe.toLocaleString('es-ES', {
    minimumFractionDigits: minDecimals,
    maximumFractionDigits: maxDecimals,
    useGrouping: true
  }) + ' €';
}

// Función específica para formatear precios unitarios con 5 decimales
export function formatearPrecioUnitario(precio) {
  if (typeof precio !== 'number' || isNaN(precio)) {
    return "0,00000 €";
  }
  return precio.toLocaleString('es-ES', {
    minimumFractionDigits: 5,
    maximumFractionDigits: 5,
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
  let s = valor.replace(/\s|\u00A0/g, '').replace(/€|eur?|%/gi, '').trim();
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

export function parsearNumeroBackend(valor, fallback = 0) {
  if (valor === null || valor === undefined || valor === '') {
    return fallback;
  }
  if (typeof valor === 'number') {
    return Number.isFinite(valor) ? valor : fallback;
  }
  if (typeof valor === 'string') {
    const limpio = valor.replace(/\s|\u00A0/g, '').replace(/€|eur?/gi, '').trim();
    if (!limpio) return fallback;
    const normalizado = limpio.replace(/\./g, '').replace(',', '.');
    const num = Number(normalizado);
    return Number.isFinite(num) ? num : fallback;
  }
  if (typeof valor === 'boolean') {
    return valor ? 1 : 0;
  }
  return fallback;
}

export function normalizarDetalleBackend(detalle = {}) {
  if (!detalle || typeof detalle !== 'object') return null;
  return {
    ...detalle,
    cantidad: parsearNumeroBackend(detalle.cantidad, 0),
    precio: parsearNumeroBackend(detalle.precio, 0),
    impuestos: parsearNumeroBackend(detalle.impuestos, 0),
    total: parsearNumeroBackend(detalle.total, 0)
  };
}

export function normalizarDetallesBackend(detalles = []) {
  return (detalles || [])
    .map(detalle => normalizarDetalleBackend(detalle))
    .filter(Boolean);
}

export function normalizarContactoBackend(contacto = {}) {
  if (!contacto || typeof contacto !== 'object') return null;

  const id = contacto.idContacto ?? contacto.idcontacto ?? contacto.id ?? null;
  return {
    idContacto: parsearNumeroBackend(id, null),
    razonsocial: contacto.razonsocial ?? contacto.razon_social ?? contacto.razonSocial ?? '',
    identificador: contacto.identificador ?? contacto.nif ?? contacto.cif ?? '',
    direccion: contacto.direccion ?? contacto.direccion_fiscal ?? '',
    cp: contacto.cp ?? contacto.codigo_postal ?? contacto.codigopostal ?? '',
    localidad: contacto.localidad ?? contacto.poblacion ?? contacto.ciudad ?? '',
    provincia: contacto.provincia ?? contacto.provincia_nombre ?? '',
    telefono: contacto.telefono ?? contacto.tlf ?? '',
    email: contacto.email ?? contacto.correo ?? '',
    dir3_oficina: contacto.dir3_oficina ?? contacto.dir3Oficina ?? '',
    dir3_organo: contacto.dir3_organo ?? contacto.dir3Organo ?? '',
    dir3_unidad: contacto.dir3_unidad ?? contacto.dir3Unidad ?? '',
    face_presentacion: parsearNumeroBackend(
      contacto.face_presentacion ?? contacto.facePresentacion ?? contacto.faceRequerido,
      0
    )
  };
}

export async function fetchContactoPorId(id) {
  const contactoId = parsearNumeroBackend(id, null);
  if (!contactoId) return {};
  try {
    const url = buildApiUrl(`/api/contactos/get_contacto/${contactoId}`);
    const response = await fetch(url);
    if (!response.ok) {
      console.warn(`[contacto] No se pudo obtener contacto ${contactoId}: ${response.status}`);
      return {};
    }
    const data = await response.json();
    return normalizarContactoBackend(data) || {};
  } catch (error) {
    console.error(`[contacto] Error al obtener contacto ${contactoId}:`, error);
    return {};
  }
}

export function normalizarImportesBackend(importes = {}, claves = ['importe_bruto', 'importe_impuestos', 'importe_cobrado', 'total']) {
  if (!importes || typeof importes !== 'object') {
    return {};
  }
  const resultado = { ...importes };
  for (const clave of claves) {
    if (clave in resultado) {
      resultado[clave] = parsearNumeroBackend(resultado[clave], 0);
    }
  }
  if ('detalles' in resultado) {
    resultado.detalles = normalizarDetallesBackend(resultado.detalles);
  }
  if ('contacto' in resultado) {
    resultado.contacto = normalizarContactoBackend(resultado.contacto) || {};
  }
  return resultado;
}


export async function calcularPrecioConDescuento(precioUnitarioSinIVA, cantidad, tipoFactura = null, tipoDocumento = 'proforma', productoId = null) {
  if (tipoFactura === '') {
    tipoFactura = 'N';
  }

  if (tipoDocumento === 'ticket') {
    return await aplicarDescuentoPorFranja(precioUnitarioSinIVA, cantidad, productoId);
  }

  if (tipoDocumento === 'factura') {
    registrarFranjaAplicada(null);
    return precioUnitarioSinIVA;
  }

  if (tipoFactura === 'A') {
    registrarFranjaAplicada(null);
    return precioUnitarioSinIVA;
  }

  return await aplicarDescuentoPorFranja(precioUnitarioSinIVA, cantidad, productoId);
}

// Flag global para controlar llamadas concurrentes
let calculandoFranjas = false;

async function aplicarDescuentoPorFranja(precioUnitarioSinIVA, cantidad, productoId) {
  if (!productoId) {
    console.warn('No se proporcionó productoId, usando precio original sin descuento');
    registrarFranjaAplicada(null);
    return precioUnitarioSinIVA;
  }

  if (calculandoFranjas) {
    console.warn('Cálculo de franjas ya en progreso, ignorando llamada duplicada');
    registrarFranjaAplicada(null);
    return precioUnitarioSinIVA;
  }

  calculandoFranjas = true;

  try {
    const response = await originalFetch(buildApiUrl(`/api/productos/${productoId}/franjas_descuento`), {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json'
      }
    });
    if (!response.ok) {
      console.warn(`Error al obtener franjas para producto ${productoId}: ${response.status}`);
      registrarFranjaAplicada(null);
      calculandoFranjas = false;
      return precioUnitarioSinIVA;
    }

    const data = await response.json();
    const franjas = data.franjas || [];

    if (franjas.length === 0) {
      console.warn(`No hay franjas definidas para producto ${productoId}`);
      registrarFranjaAplicada(null);
      calculandoFranjas = false;
      return precioUnitarioSinIVA;
    }

    let descuentoAplicable = 0;
    let franjaAplicada = null;

    for (const franja of franjas) {
      if (cantidad >= franja.min_cantidad && cantidad <= franja.max_cantidad) {
        descuentoAplicable = franja.porcentaje_descuento;
        franjaAplicada = {
          min: franja.min_cantidad,
          max: franja.max_cantidad,
          descuento: franja.porcentaje_descuento
        };
        break;
      }
    }

    if (!franjaAplicada && franjas.length > 0) {
      const ultimaFranja = franjas[franjas.length - 1];
      if (cantidad > ultimaFranja.max_cantidad) {
        descuentoAplicable = ultimaFranja.porcentaje_descuento;
        franjaAplicada = {
          min: ultimaFranja.min_cantidad,
          max: ultimaFranja.max_cantidad,
          descuento: ultimaFranja.porcentaje_descuento
        };
      }
    }

    if (!franjaAplicada) {
      console.warn(`No se encontró franja para cantidad ${cantidad} en producto ${productoId}`);
      registrarFranjaAplicada(null);
      return precioUnitarioSinIVA;
    }

    registrarFranjaAplicada(franjaAplicada);

    const factorDescuento = (100 - descuentoAplicable) / 100;
    const precioConDescuento = precioUnitarioSinIVA * factorDescuento;

    console.log('=== CÁLCULO DE FRANJA DE DESCUENTO (BD) ===');
    console.log(`Producto ID: ${productoId}`);
    console.log(`Precio original: ${precioUnitarioSinIVA.toFixed(5)}€`);
    console.log(`Cantidad: ${cantidad} unidades`);
    console.log(`Franja aplicada: ${franjaAplicada.min}-${franjaAplicada.max} unidades`);
    console.log(`Descuento aplicable: ${descuentoAplicable}%`);
    console.log(`Precio con descuento: ${precioConDescuento.toFixed(5)}€`);
    console.log('==========================================');

    return precioConDescuento;
  } catch (error) {
    console.error(`Error al calcular descuento por franja para producto ${productoId}:`, error);
    registrarFranjaAplicada(null);
    return precioUnitarioSinIVA;
  } finally {
    calculandoFranjas = false;
  }
}

export async function calcularTotalDetalle() {
  const cantidadElem    = document.getElementById('cantidad-detalle');
  const impuestoElem    = document.getElementById('impuesto-detalle');
  const totalElem       = document.getElementById('total-detalle');
  const precioDetalleElem = document.getElementById('precio-detalle');
  const select          = document.getElementById('concepto-detalle');

  if (!cantidadElem || !select || !impuestoElem || !totalElem || !precioDetalleElem) {
    console.error('Uno o más elementos necesarios no existen en el DOM.');
    resetInfoPrecio();
    return;
  }

  const selectedIndex = select.selectedIndex;
  if (selectedIndex < 0) {
    console.warn('No hay ninguna opción seleccionada en el selector de productos.');
    totalElem.value = '0.00';
    registrarFranjaAplicada(null);
    resetInfoPrecio();
    return;
  }

  const selectedOption  = select.options[selectedIndex];
  const productoId      = selectedOption?.value ?? '';
  const cantidad        = parseFloat(cantidadElem.value) || 0;

  if (!productoId) {
    console.warn('Opción de producto sin valor. Reiniciando información de precio.');
    totalElem.value = '0.00';
    registrarFranjaAplicada(null);
    resetInfoPrecio();
    return;
  }

  let impuestos = 0;
  if (impuestoElem.value === '') {
    console.log('Campo IVA vacío, usando 0% para el cálculo');
    impuestos = 0;
  } else {
    impuestos = parseFloat(impuestoElem.value) || 0;
  }

  if (cantidad < 1) {
    totalElem.value = '0.00';
    resetInfoPrecio();
    return;
  }

  if (productoId === PRODUCTO_ID_LIBRE) {
    registrarFranjaAplicada(null);

    if (document.activeElement === totalElem) {
      const totalIngresado = parseFloat(totalElem.value) || 0;
      const precioUnitario = (totalIngresado / (1 + impuestos / 100)) / cantidad;
      precioDetalleElem.value = precioUnitario.toFixed(5);
      actualizarInfoPrecio(precioUnitario, impuestos);
    } else {
      const precioUnitario = parseFloat(precioDetalleElem.value) || 0;
      const subtotal = precioUnitario * cantidad;
      const impuestoCalc = Number((subtotal * (impuestos / 100)).toFixed(2));
      const total = Number((subtotal + impuestoCalc).toFixed(2));
      totalElem.value = total.toFixed(2);
      actualizarInfoPrecio(precioUnitario, impuestos);
    }
    return;
  }

  let precioOriginal = parseFloat(selectedOption.dataset.precioOriginal) || 0;

  let tipoDocumento = 'N';
  const tipoPresupuestoElem = document.getElementById('tipo-presupuesto');
  const tipoProformaElem = document.getElementById('tipo-proforma');
  if (tipoPresupuestoElem) {
    tipoDocumento = tipoPresupuestoElem.value || 'N';
    sessionStorage.setItem('tipoPresupuesto', tipoDocumento);
    console.log('Detectado tipo de presupuesto:', tipoDocumento);
  } else if (tipoProformaElem) {
    tipoDocumento = tipoProformaElem.value || 'N';
    sessionStorage.setItem('tipoProforma', tipoDocumento);
    console.log('Detectado tipo de proforma:', tipoDocumento);
  } else {
    const tipoFacturaElem = document.getElementById('tipo-factura');
    if (tipoFacturaElem) {
      tipoDocumento = tipoFacturaElem.value || 'N';
      sessionStorage.setItem('tipoFactura', tipoDocumento);
      console.log('Detectado tipo de factura:', tipoDocumento);
    } else {
      tipoDocumento = sessionStorage.getItem('tipoPresupuesto')
        || sessionStorage.getItem('tipoProforma')
        || sessionStorage.getItem('tipoFactura')
        || 'N';
      console.log('Usando tipo predeterminado:', tipoDocumento);
    }
  }

  console.log(`Tipo de documento detectado: ${tipoDocumento}`);

  let precioFinal;

  const detalleIdEditing = document.getElementById('btn-agregar-detalle')?.dataset?.detalleId || '';
  const enEdicion = Boolean(detalleIdEditing);

  if (tipoDocumento === 'A') {
    console.log('Documento tipo A: NO se aplican descuentos por franja');
    precioFinal = parseFloat(precioDetalleElem.value) || precioOriginal;
    registrarFranjaAplicada(null);
  } else {
    console.log('Documento tipo N: SÍ se aplican descuentos por franja');
    if (productoId && productoId !== PRODUCTO_ID_LIBRE) {
      const baseCalculo = parseFloat(selectedOption.dataset.precioOriginal);
      const precioBase = Number.isFinite(baseCalculo) ? baseCalculo : precioOriginal;
      precioFinal = await calcularPrecioConDescuento(precioBase, cantidad, null, tipoDocumento, productoId);
    } else {
      console.warn('ProductoId es LIBRE o vacío, usando precio original sin descuento');
      precioFinal = parseFloat(precioDetalleElem.value) || precioOriginal;
      registrarFranjaAplicada(null);
    }
  }

  if (typeof precioFinal !== 'number' || isNaN(precioFinal)) {
    console.error('precioFinal no es un número válido:', precioFinal);
    precioFinal = precioOriginal;
  }

  if (enEdicion && document.activeElement === precioDetalleElem) {
    const precioManual = parseFloat(precioDetalleElem.value);
    if (Number.isFinite(precioManual) && precioManual > 0) {
      precioFinal = precioManual;
    }
  }

  const precioRedondeado = Number(precioFinal.toFixed(5));
  const subtotal = precioRedondeado * cantidad;
  const impuestoCalc = Number((subtotal * (impuestos / 100)).toFixed(2));
  const total = Number((subtotal + impuestoCalc).toFixed(2));

  precioDetalleElem.value = precioRedondeado.toFixed(5);
  totalElem.value = total.toFixed(2);
  actualizarInfoPrecio(precioRedondeado, impuestos);
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
export const getEstadoFormateado = (estado, tipo = 'factura') => {
    const estadosFacturas = {
        'P': 'Pendiente',
        'C': 'Cobrada',
        'V': 'Vencida',
        'RE': 'Rectificativa',
        'A': 'Anulada'
    };
    
    const estadosProformas = {
        'A': 'Abierta',
        'F': 'Facturada',
        'C': 'Cerrada'
    };
    
    const estadosPresupuestos = {
        'B': 'Borrador',
        'EN': 'Enviado',
        'AP': 'Aceptado',
        'RJ': 'Rechazado',
        'CD': 'Caducado',
        'T': 'Ticket',
        'A0': 'Anulado'
    };
    
    if (tipo === 'proforma') {
        return estadosProformas[estado] || estadosFacturas[estado] || estadosPresupuestos[estado] || estado;
    } else if (tipo === 'presupuesto') {
        return estadosPresupuestos[estado] || estadosFacturas[estado] || estado;
    } else {
        // Por defecto: factura
        return estadosFacturas[estado] || estadosPresupuestos[estado] || estado;
    }
};

// Función para convertir el estado formateado de vuelta al código
export const getCodigoEstado = (estadoFormateado) => {
    const codigosEstado = {
        // Facturas
        'Pendiente': 'P',
        'Cobrada': 'C',
        'Vencida': 'V',
        'Rectificativa': 'RE',
        // Proformas
        'Abierta': 'A',
        'Facturada': 'F',
        'Cerrada': 'C',
        // Presupuestos
        'Borrador': 'B',
        'Enviado': 'EN',
        'Aceptado': 'AP',
        'Rechazado': 'RJ',
        'Caducado': 'CD',
        // Otros
        'Ticket': 'T'
    };
    return codigosEstado[estadoFormateado] || estadoFormateado;
};

export const norm = (str) => {
    if (!str) return '';
    return str.toString()
        .toLowerCase()
        .normalize('NFD')
        .replace(/[\u0300-\u036f]/g, '');
};

export const getEstadoClass = (estado) => {
    const clases = {
        // Estados de facturas
        'P': 'estado-pendiente',
        'C': 'estado-cobrado',
        'V': 'estado-vencido',
        'RE': 'estado-rectificativa',
        // Estados de proformas
        'A': 'estado-pendiente',
        'EN': 'estado-pendiente',
        'AP': 'estado-cobrado',
        'RJ': 'estado-vencido',
        'CD': 'estado-vencido',
        'F': 'estado-cobrado',     // Facturada
        'T': 'estado-cobrado'     // Facturada - mismo estilo que cobrado
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
  let ultimaError = null;
  try {
    mostrarCargando();
    const primaria = buildApiUrl(url);
    const candidates = [];
    candidates.push(primaria);
    if (primaria !== url) candidates.push(url);
    // Añadir solo fallbacks a IPs conocidas (sin loopback nunca)
    try {
      const u = new URL(primaria, window.location.origin);
      if (u.pathname.startsWith('/api')) {
        const knownServers = ['192.168.1.23', '192.168.1.18'];
        for (const ip of knownServers) {
          const candidate = `http://${ip}:${PORT}${u.pathname}${u.search}`;
          if (!candidates.includes(candidate)) candidates.push(candidate);
        }
      }
    } catch (_) {
      const p = (typeof url === 'string' && url.startsWith('/')) ? url : `/${url}`;
      if (p.startsWith('/api')) {
        const knownServers = ['192.168.1.23', '192.168.1.18'];
        for (const ip of knownServers) {
          const candidate = `http://${ip}:${PORT}${p}`;
          if (!candidates.includes(candidate)) candidates.push(candidate);
        }
      }
    }

    for (const target of candidates) {
      try {
        const res = await fetch(target, opciones);
        if (res.ok) return await res.json();
        ultimaError = new Error(`Error ${res.status} en ${target}`);
      } catch (e) {
        ultimaError = e;
      }
    }
    // Si llegamos aquí, ambos intentos fallaron
    throw ultimaError || new Error('Fallo de red desconocido');
  } finally {
    ocultarCargando();
  }
}
// === Fin funciones añadidas ===

// Construye la URL completa para llamadas a la API. Si la página no se sirve
// desde el mismo host:puerto del backend (5001), antepone http://IP_SERVER:PORT
// Ejemplos:
//   buildApiUrl('/api/ventas/total_mes?...') -> 'http://IP:5001/api/ventas/total_mes?...' (cuando procede)
//   buildApiUrl('http://otrohost/api/...')   -> se respeta tal cual
export function buildApiUrl(path) {
  try {
    if (!path) return '';
    if (path.startsWith('http://') || path.startsWith('https://')) return path;
    const p = path.startsWith('/') ? path : `/${path}`;
    // Para rutas de API, devolver SIEMPRE absoluta a la IP del servidor (evita puertos incorrectos)
    if (p.startsWith('/api')) {
      return `http://${IP_SERVER}:${PORT}${p}`;
    }
    // Para otras rutas, devolver relativo al origen
    return p;
  } catch (e) {
    const p2 = path && path.startsWith('/') ? path : `/${path}`;
    return p2;
  }
}

// Invalidación de caché global (segura si no existen variables)

export function invalidateGlobalCache() {
  try {
    if (typeof window !== 'undefined' && typeof window.globalProductCache !== 'undefined') {
      window.globalProductCache = null;
    }
  } catch (e) { /* noop */ }
  try { if (typeof globalProductCache !== 'undefined') globalProductCache = null; } catch (e) {}
  try { if (typeof productDiscountBands !== 'undefined') productDiscountBands = {}; } catch (e) {}
  try { if (typeof pendingPromises !== 'undefined') pendingPromises = {}; } catch (e) {}
  try { if (typeof requestLocks !== 'undefined') requestLocks = {}; } catch (e) {}
  try { if (typeof globalFetchLock !== 'undefined') globalFetchLock = false; } catch (e) {}
  try { console.log('[cache] invalidateGlobalCache ejecutado'); } catch (e) {}
}

/**
 * Sistema de detección de cambios sin guardar
 * Uso:
 * 1. Llamar inicializarDeteccionCambios() al cargar la página
 * 2. Llamar marcarCambiosSinGuardar() cuando se edite algo
 * 3. Llamar resetearCambiosSinGuardar() después de guardar
 */
let cambiosSinGuardarGlobal = false;

export function marcarCambiosSinGuardar() {
  cambiosSinGuardarGlobal = true;
}

export function resetearCambiosSinGuardar() {
  cambiosSinGuardarGlobal = false;
}

export function hayCambiosSinGuardar() {
  return cambiosSinGuardarGlobal;
}

export function inicializarDeteccionCambios(callbackGuardar = null) {
  // Interceptar clics en enlaces de navegación
  document.addEventListener('click', async (e) => {
    const link = e.target.closest('a[href], a[data-target], button[data-navigate]');
    
    if (link && cambiosSinGuardarGlobal) {
      e.preventDefault();
      e.stopPropagation();
      
      const guardar = await mostrarConfirmacion('Hay cambios sin guardar. ¿Desea guardarlos antes de salir?');
      if (guardar && callbackGuardar) {
        try {
          await callbackGuardar();
          cambiosSinGuardarGlobal = false;
          
          // Continuar con la navegación
          setTimeout(() => {
            if (link.dataset.target) {
              window.location.href = link.dataset.target;
            } else if (link.dataset.navigate) {
              window.location.href = link.dataset.navigate;
            } else if (link.href) {
              window.location.href = link.href;
            }
          }, 500);
        } catch (e) {
          console.error('[Cambios] Error al guardar:', e);
        }
      } else {
        // Descartar cambios y continuar
        cambiosSinGuardarGlobal = false;
        if (link.dataset.target) {
          window.location.href = link.dataset.target;
        } else if (link.dataset.navigate) {
          window.location.href = link.dataset.navigate;
        } else if (link.href) {
          window.location.href = link.href;
        }
      }
    }
  }, true);
  
  // Interceptar teclas de recarga (F5, Ctrl+R, Cmd+R)
  window.addEventListener('keydown', async (e) => {
    // F5 o Ctrl+R o Cmd+R
    if ((e.key === 'F5') || ((e.ctrlKey || e.metaKey) && e.key === 'r')) {
      if (cambiosSinGuardarGlobal) {
        e.preventDefault();
        const confirmar = await mostrarConfirmacion('Hay cambios sin guardar. ¿Desea recargar la página y perderlos?');
        if (confirmar) {
          cambiosSinGuardarGlobal = false;
          window.location.reload();
        }
      }
    }
  }, true);
}
