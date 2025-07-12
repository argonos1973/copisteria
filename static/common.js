import { IP_SERVER, PORT } from './constantes.js';
import { 
  PRODUCTO_ID_LIBRE,
  truncarDecimales,
  formatearImporte,
  formatearFecha,
  calcularPrecioConDescuento,
  calcularTotalDetalle
} from './scripts_utils.js';
export { formatearFecha };
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
  if (precioDetalle) precioDetalle.removeEventListener('input', calcularTotalDetalle);
  if (cantidadDetalle) cantidadDetalle.removeEventListener('input', calcularTotalDetalle);
  if (totalDetalle) totalDetalle.removeEventListener('input', calcularTotalDetalle);
}

export function seleccionarProducto(formElements, productosOriginales) {
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
    const precioConDescuento = calcularPrecioConDescuento(precioOriginal, cantidad);
    const impuestos = parseFloat(impuestoDetalle.value) || 21;
    
    precioDetalle.value = Number(precioConDescuento).toFixed(5);
    const subtotal = precioConDescuento * cantidad;
    const total = subtotal * (1 + impuestos / 100);
    totalDetalle.value = total.toFixed(2);

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
export function convertirFechaParaAPI(fecha) {
    if (!fecha) return '';
    // Si la fecha ya está en formato YYYY-MM-DD, la devolvemos tal cual
    if (fecha.includes('-')) return fecha;
    
    // Si está en formato DD/MM/AAAA, la convertimos
    const [dia, mes, año] = fecha.split('/');
    if (!dia || !mes || !año) {
        console.error('Formato de fecha inválido:', fecha);
        return '';
    }
    return `${año}-${mes.padStart(2, '0')}-${dia.padStart(2, '0')}`;
}

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