import { IP_SERVER, PORT } from './constantes.js';
import { 
  PRODUCTO_ID_LIBRE,
  truncarDecimales,
  formatearImporte,
  calcularPrecioConDescuento,
  calcularTotalDetalle,
  preloadFranjasProducto,
  norm,
  debounce
} from './scripts_utils.js';
import { mostrarNotificacion } from './notificaciones.js';

// Funciones comunes para manejo de productos
export async function cargarProductos() {
  try {
    const response = await fetch(`http://${IP_SERVER}:${PORT}/api/productos`);
    if (!response.ok) {
      throw new Error(`Error al cargar productos: ${response.statusText}`);
    }
    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Error al cargar productos:', error);
    mostrarNotificacion("Error al cargar la lista de productos", "error");
    return [];
  }
}

export const MAX_OPCIONES_SELECT = 200;

export function actualizarSelectProductos(productos, selectElement) {
  if (!selectElement) return;

  const total = Array.isArray(productos) ? productos.length : 0;
  const lista = total > MAX_OPCIONES_SELECT ? productos.slice(0, MAX_OPCIONES_SELECT) : (productos || []);

  // Reemplazo eficiente del contenido
  const frag = document.createDocumentFragment();
  const first = document.createElement('option');
  first.value = '';
  first.textContent = 'Seleccione un producto';
  frag.appendChild(first);

  for (const producto of lista) {
    const option = document.createElement('option');
    option.value = producto.id;
    option.textContent = producto.nombre;
    option.dataset.descripcion = producto.descripcion;
    option.dataset.precioOriginal = producto.subtotal;
    frag.appendChild(option);
  }

  if (total > MAX_OPCIONES_SELECT) {
    const extra = document.createElement('option');
    extra.value = '';
    extra.disabled = true;
    extra.textContent = `(+${total - MAX_OPCIONES_SELECT} más resultados, refine la búsqueda...)`;
    frag.appendChild(extra);
  }

  // Evitar reflow excesivo
  selectElement.innerHTML = '';
  selectElement.appendChild(frag);
}

export function filtrarProductos(busqueda, productosOriginales) {
  const q = norm(busqueda || '');
  if (!q) return productosOriginales || [];
  return (productosOriginales || []).filter(p => norm(p.nombre).includes(q));
}

// Funciones comunes para manejo de detalles
export function limpiarCamposDetalle(formElements) {
  const {
    busquedaProducto,
    conceptoDetalle,
    descripcionDetalle,
    cantidadDetalle,
    precioDetalle,
    impuestoDetalle,
    totalDetalle,
    conceptoInput
  } = formElements;

  if (busquedaProducto) busquedaProducto.value = '';
  if (conceptoDetalle) conceptoDetalle.value = '';
  if (descripcionDetalle) descripcionDetalle.value = '';
  if (cantidadDetalle) cantidadDetalle.value = '1';
  if (precioDetalle) {
    precioDetalle.value = Number(0).toFixed(5);
    precioDetalle.readOnly = true;
    precioDetalle.style.backgroundColor = '#e9ecef';
  }
  if (impuestoDetalle) {
    impuestoDetalle.value = '21';
    impuestoDetalle.readOnly = true;
    impuestoDetalle.style.backgroundColor = '#e9ecef';
  }
  if (totalDetalle) {
    totalDetalle.value = Number(0).toFixed(2);
    totalDetalle.readOnly = true;
    totalDetalle.style.backgroundColor = '#e9ecef';
  }
  if (conceptoInput) {
    conceptoInput.style.display = 'none';
    conceptoInput.value = '';
  }

  // Remover event listeners
  if (precioDetalle) precioDetalle.removeEventListener('input', calcularTotalDetalle);
  if (cantidadDetalle) cantidadDetalle.removeEventListener('input', calcularTotalDetalle);
  if (totalDetalle) totalDetalle.removeEventListener('input', calcularTotalDetalle);
}

export function seleccionarProducto(formElements, productosOriginales, tipoDocumento = 'proforma') {
  const {
    conceptoDetalle,
    descripcionDetalle,
    cantidadDetalle,
    precioDetalle,
    impuestoDetalle,
    totalDetalle,
    conceptoInput
  } = formElements;

  if (!conceptoDetalle) return;

  const selectedOption = conceptoDetalle.options[conceptoDetalle.selectedIndex];
  const productoId = selectedOption.value;

  if (!productoId) {
    limpiarCamposDetalle(formElements);
    return;
  }

  const descripcion = selectedOption.dataset.descripcion || "";
  const precioOriginal = parseFloat(selectedOption.dataset.precioOriginal) || 0;

  cantidadDetalle.value = 1;
  descripcionDetalle.value = descripcion;
  precioDetalle.value = Number(precioOriginal).toFixed(5);
  impuestoDetalle.value = 21;

  // Configurar el campo de impuesto como readonly siempre
  impuestoDetalle.readOnly = true;
  impuestoDetalle.style.backgroundColor = '#e9ecef';

  // Primero removemos todos los event listeners anteriores
  precioDetalle.removeEventListener('input', calcularTotalDetalle);
  cantidadDetalle.removeEventListener('input', calcularTotalDetalle);
  totalDetalle.removeEventListener('input', calcularTotalDetalle);

  if (productoId === PRODUCTO_ID_LIBRE) {
    precioDetalle.readOnly = false;
    precioDetalle.style.backgroundColor = '';
    totalDetalle.readOnly = false;
    totalDetalle.style.backgroundColor = '';

    // Añadimos los event listeners para el producto libre
    precioDetalle.addEventListener('input', calcularTotalDetalle);
    cantidadDetalle.addEventListener('input', calcularTotalDetalle);
    totalDetalle.addEventListener('input', calcularTotalDetalle);

    // Manejar el campo de concepto personalizado si existe
    if (conceptoInput) {
      conceptoInput.style.display = 'block';
      if (!conceptoInput.dataset.listenerAdded) {
        conceptoInput.addEventListener('input', () => {
          const busqueda = conceptoInput.value;
          const productosFiltrados = filtrarProductos(busqueda, productosOriginales);
          actualizarSelectProductos(productosFiltrados, conceptoDetalle);
        });
        conceptoInput.dataset.listenerAdded = true;
      }
    }
  } else {
    precioDetalle.readOnly = true;
    precioDetalle.style.backgroundColor = '#e9ecef';
    totalDetalle.readOnly = true;
    totalDetalle.style.backgroundColor = '#e9ecef';

    // Calcular el precio con descuento y el total
    const cantidad = parseFloat(cantidadDetalle.value) || 1;
    // Aplicar franjas específicas por producto según el tipo de documento
    // - 'proforma': respeta regla de tipo A/N
    // - 'ticket'  : siempre aplica franjas
    const precioConDescuento = calcularPrecioConDescuento(precioOriginal, cantidad, null, tipoDocumento, productoId);
    const impuestos = parseFloat(impuestoDetalle.value) || 21;
    
    precioDetalle.value = Number(precioConDescuento).toFixed(5);
    const subtotal = precioConDescuento * cantidad;
    const total = subtotal * (1 + impuestos / 100);
    totalDetalle.value = total.toFixed(2);

    // Reasociar listener para recalcular al cambiar cantidad en productos NO libres
    // (los listeners previos se removieron arriba para evitar duplicados)
    try {
      cantidadDetalle.addEventListener('input', calcularTotalDetalle);
    } catch (_) { /* noop */ }

    // Precargar franjas reales y recalcular si cambian
    try {
      preloadFranjasProducto(productoId).then(() => {
        // Verificar que el usuario no cambió de producto mientras tanto
        const sigueSiendoMismo = conceptoDetalle && conceptoDetalle.value == productoId;
        if (!sigueSiendoMismo) return;
        const cant = parseFloat(cantidadDetalle.value) || 1;
        const iva = parseFloat(impuestoDetalle.value) || 21;
        const precioRecalc = calcularPrecioConDescuento(precioOriginal, cant, null, tipoDocumento, productoId);
        const precioActual = Number(precioDetalle.value);
        const precioNuevo = Number(precioRecalc.toFixed(5));
        if (precioActual !== precioNuevo) {
          precioDetalle.value = precioNuevo.toFixed(5);
          const sub = precioNuevo * cant;
          totalDetalle.value = (sub * (1 + iva / 100)).toFixed(2);
        }
      }).catch(() => {});
    } catch (_) { /* silent */ }

    // Ocultar y limpiar el campo de concepto personalizado si existe
    if (conceptoInput) {
      conceptoInput.style.display = 'none';
      conceptoInput.value = '';
      if (conceptoInput.dataset.listenerAdded) {
        conceptoInput.removeEventListener('input', () => {});
        conceptoInput.dataset.listenerAdded = false;
      }
    }
  }

  calcularTotalDetalle();
}

// Funciones comunes para validación
export function validarDetalle(detalle) {
  if (!detalle.concepto || !detalle.cantidad || !detalle.precio) {
    mostrarNotificacion("Todos los campos son obligatorios", "error");
    return false;
  }

  if (detalle.cantidad <= 0) {
    mostrarNotificacion("La cantidad debe ser mayor que 0", "error");
    return false;
  }

  if (detalle.precio <= 0) {
    mostrarNotificacion("El precio debe ser mayor que 0", "error");
    return false;
  }

  if (detalle.total <= 0) {
    mostrarNotificacion("El total debe ser mayor que 0", "error");
    return false;
  }

  return true;
}


// Función para convertir fecha de DD/MM/AAAA a YYYY-MM-DD para la API
// convertirFechaParaAPI centralizado en scripts_utils.js

// Función para volver a la página de origen
export function volverSegunOrigen() {
    // Intentar obtener el origen de múltiples fuentes
    const origenStorage = sessionStorage.getItem('origenProforma') || sessionStorage.getItem('origenFactura');
    const origenURL = new URLSearchParams(window.location.search).get('origen');
    const origen = origenURL || origenStorage;

    console.log('Origen detectado:', origen);  // Para depuración

    // Determinar la página actual
    const paginaActual = window.location.pathname.split('/').pop();
    const esFactura = paginaActual.toLowerCase().includes('factura');

    if (origen === 'contactos') {
        window.location.href = 'CONSULTA_CONTACTOS.html';
    } else if (esFactura) {
        window.location.href = 'CONSULTA_FACTURAS.html';
    } else {
        window.location.href = 'CONSULTA_PROFORMAS.html';
    }
    
    // Limpiar el origen después de usarlo
    sessionStorage.removeItem('origenProforma');
    sessionStorage.removeItem('origenFactura');
}

// Función para redondear importes de manera consistente
export function redondearImporte(valor) {
    return Number(Number(valor).toFixed(2));
} 