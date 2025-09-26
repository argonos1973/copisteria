import { IP_SERVER, PORT } from './constantes.js';
import { 
  PRODUCTO_ID_LIBRE,
  truncarDecimales,
  formatearImporte,
  calcularPrecioConDescuento,
  calcularTotalDetalle,
  debounce
} from './scripts_utils.js';
import { mostrarNotificacion } from './notificaciones.js';
import { actualizarDetalleConTotal } from './calculo_totales_unificado.js';

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

export function actualizarSelectProductos(productos, selectElement) {
  if (!selectElement) return;
  
  selectElement.innerHTML = '<option value="">Seleccione un producto</option>';
  productos.forEach(producto => {
    const option = document.createElement('option');
    option.value = producto.id;
    option.textContent = producto.nombre;
    option.dataset.descripcion = producto.descripcion;
    option.dataset.precioOriginal = producto.subtotal;
    selectElement.appendChild(option);
  });
}

export function filtrarProductos(busqueda, productosOriginales) {
  return productosOriginales.filter(producto =>
    producto.nombre.toLowerCase().includes(busqueda.toLowerCase())
  );
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
  if (precioDetalle) precioDetalle.removeEventListener('input', recalcularTotalUI);
  if (cantidadDetalle) cantidadDetalle.removeEventListener('input', recalcularTotalUI);
  if (totalDetalle) totalDetalle.removeEventListener('input', recalcularTotalUI);
}

export async function seleccionarProducto(formElements, productosOriginales, tipoDocumento = 'ticket') {
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
  precioDetalle.removeEventListener('input', recalcularTotalUI);
  cantidadDetalle.removeEventListener('input', recalcularTotalUI);
  totalDetalle.removeEventListener('input', recalcularTotalUI);

  if (productoId === PRODUCTO_ID_LIBRE) {
    precioDetalle.readOnly = false;
    precioDetalle.style.backgroundColor = '';
    totalDetalle.readOnly = false;
    totalDetalle.style.backgroundColor = '';

    // Añadimos los event listeners para el producto libre
    precioDetalle.addEventListener('input', recalcularTotalUI);
    cantidadDetalle.addEventListener('input', recalcularTotalUI);
    totalDetalle.addEventListener('input', recalcularTotalUI);

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

    // Para productos normales: aplicar franjas según tipoDocumento (ticket, factura, proforma, presupuesto)
    const onCantidadChange = async () => {
      const cantidad = parseFloat(cantidadDetalle.value) || 0;
      const impuestos = parseFloat(impuestoDetalle.value) || 0;
      const productoIdSel = selectedOption.value;
      const precioOriginalSel = parseFloat(selectedOption.dataset.precioOriginal) || 0;

      // Determinar tipo de documento y tipo (A/N) cuando aplique
      let tipoFacturaProforma = 'N';
      if (tipoDocumento === 'proforma') {
        tipoFacturaProforma = document.getElementById('tipo-proforma')?.value || sessionStorage.getItem('tipoProforma') || 'N';
      } else if (tipoDocumento === 'factura') {
        tipoFacturaProforma = document.getElementById('tipo-factura')?.value || 'N';
      }

      // Proforma tipo 'A' no aplica descuentos
      if (tipoDocumento === 'proforma' && String(tipoFacturaProforma).toUpperCase() === 'A') {
        const det = actualizarDetalleConTotal({ precio: precioOriginalSel, cantidad, impuestos });
        precioDetalle.value = Number(precioOriginalSel).toFixed(5);
        totalDetalle.value = Number(det.total).toFixed(2);
        return;
      }

      // Para tickets, facturas, presupuestos y proformas (no 'A'): aplicar franjas
      const precioConDesc = await calcularPrecioConDescuento(
        precioOriginalSel,
        cantidad,
        tipoFacturaProforma,
        tipoDocumento,
        productoIdSel
      );
      precioDetalle.value = Number(precioConDesc).toFixed(5);
      const det = actualizarDetalleConTotal({ precio: precioConDesc, cantidad, impuestos });
      totalDetalle.value = Number(det.total).toFixed(2);
    };
    const debouncedOnCantidadChange = debounce(onCantidadChange, 350);
    cantidadDetalle.addEventListener('input', debouncedOnCantidadChange);

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

  // Calcular el total inicial con consideración de franjas según tipoDocumento
  const cantidad = parseFloat(cantidadDetalle.value) || 1;
  const impuestos = parseFloat(impuestoDetalle.value) || 21;
  if (productoId !== PRODUCTO_ID_LIBRE) {
    let tipoFacturaProforma = 'N';
    if (tipoDocumento === 'proforma') {
      tipoFacturaProforma = document.getElementById('tipo-proforma')?.value || sessionStorage.getItem('tipoProforma') || 'N';
    } else if (tipoDocumento === 'factura') {
      tipoFacturaProforma = document.getElementById('tipo-factura')?.value || 'N';
    } else if (tipoDocumento === 'presupuesto') {
      tipoFacturaProforma = 'N';
    }

    if (tipoDocumento === 'proforma' && String(tipoFacturaProforma).toUpperCase() === 'A') {
      const det = actualizarDetalleConTotal({ precio: precioOriginal, cantidad, impuestos });
      precioDetalle.value = Number(precioOriginal).toFixed(5);
      totalDetalle.value = Number(det.total).toFixed(2);
    } else {
      const precioConDesc = await calcularPrecioConDescuento(precioOriginal, cantidad, tipoFacturaProforma, tipoDocumento, productoId);
      precioDetalle.value = Number(precioConDesc).toFixed(5);
      const det = actualizarDetalleConTotal({ precio: precioConDesc, cantidad, impuestos });
      totalDetalle.value = Number(det.total).toFixed(2);
    }
  } else {
    const det = actualizarDetalleConTotal({ precio: precioOriginal, cantidad, impuestos });
    totalDetalle.value = Number(det.total).toFixed(2);
  }
}

// Recalcula el total de la línea en el formulario manteniendo 5 decimales en precio y 2 en total
function recalcularTotalUI() {
  const cantidadDetalle = document.getElementById('cantidad-detalle');
  const precioDetalle = document.getElementById('precio-detalle');
  const impuestoDetalle = document.getElementById('impuesto-detalle');
  const totalDetalle = document.getElementById('total-detalle');

  const cantidad = parseFloat(cantidadDetalle?.value) || 0;
  const impuestos = parseFloat(impuestoDetalle?.value) || 0;
  const precio = parseFloat(precioDetalle?.value) || 0;

  // Calcular con módulo unificado
  const det = actualizarDetalleConTotal({ precio, cantidad, impuestos });
  // Precio siempre con 5 decimales en UI
  if (precioDetalle) precioDetalle.value = Number(precio).toFixed(5);
  // Total siempre con 2 decimales en UI
  if (totalDetalle) totalDetalle.value = Number(det.total).toFixed(2);
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
    const esPresupuesto = paginaActual.toLowerCase().includes('presupuesto');

    if (origen === 'contactos') {
        window.location.href = 'CONSULTA_CONTACTOS.html';
    } else if (esFactura) {
        window.location.href = 'CONSULTA_FACTURAS.html';
    } else if (esPresupuesto) {
        window.location.href = 'CONSULTA_PRESUPUESTOS.html';
    } else {
        window.location.href = 'CONSULTA_PROFORMAS.html';
    }
    
    // Limpiar el origen después de usarlo
    sessionStorage.removeItem('origenProforma');
    sessionStorage.removeItem('origenFactura');
    sessionStorage.removeItem('origenPresupuesto');
}

// Nota: redondearImporte ha sido centralizado en scripts_utils.js