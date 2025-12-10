import { IP_SERVER, PORT, API_URL } from './constantes.js?v=1762757322';
import { 
  PRODUCTO_ID_LIBRE,
  truncarDecimales,
  formatearImporte,
  calcularPrecioConDescuento,
  calcularTotalDetalle,
  resetInfoPrecio,
  registrarFranjaAplicada,
  debounce
} from './scripts_utils.js';
import { mostrarNotificacion } from './notificaciones.js';

// Funciones comunes para manejo de productos
const CACHE_KEY_PRODUCTOS = 'ALEPH_PRODUCTOS_DATA';
const CACHE_KEY_TIMESTAMP = 'ALEPH_PRODUCTOS_TIMESTAMP';
const CACHE_DURATION_MS = 6 * 60 * 60 * 1000; // 6 horas

export async function cargarProductos() {
  try {
    // Verificar caché
    const cachedData = localStorage.getItem(CACHE_KEY_PRODUCTOS);
    const cachedTimestamp = localStorage.getItem(CACHE_KEY_TIMESTAMP);

    if (cachedData && cachedTimestamp) {
      const now = Date.now();
      const timestamp = parseInt(cachedTimestamp, 10);
      if (now - timestamp < CACHE_DURATION_MS) {
        console.log('Cargando productos desde caché local (validez 6h)');
        return JSON.parse(cachedData);
      }
    }

    // Usar API_URL que ya tiene el protocolo correcto
    const response = await fetch(`${API_URL}/api/productos`);
    if (!response.ok) {
      throw new Error(`Error al cargar productos: ${response.statusText}`);
    }
    const data = await response.json();

    // Guardar en caché
    try {
      localStorage.setItem(CACHE_KEY_PRODUCTOS, JSON.stringify(data));
      localStorage.setItem(CACHE_KEY_TIMESTAMP, Date.now().toString());
    } catch (e) {
      console.warn('Error al guardar productos en caché local:', e);
    }

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
  }
  if (impuestoDetalle) {
    impuestoDetalle.value = '21';
    impuestoDetalle.readOnly = true;
  }
  if (totalDetalle) {
    totalDetalle.value = Number(0).toFixed(2);
    totalDetalle.readOnly = true;
  }
  if (conceptoInput) {
    conceptoInput.style.display = 'none';
    conceptoInput.value = '';
  }

  // Remover event listeners
  if (precioDetalle) precioDetalle.removeEventListener('input', calcularTotalDetalle);
  if (cantidadDetalle) cantidadDetalle.removeEventListener('input', calcularTotalDetalle);
  if (totalDetalle) totalDetalle.removeEventListener('input', calcularTotalDetalle);

  const btnAgregar = document.getElementById('btn-agregar-detalle');
  if (btnAgregar && btnAgregar.dataset.detalleId !== undefined) {
    delete btnAgregar.dataset.detalleId;
    btnAgregar.classList.remove('editando');
  }

  registrarFranjaAplicada(null);
  resetInfoPrecio();
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

  registrarFranjaAplicada(null);
  resetInfoPrecio();

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

  // Primero removemos todos los event listeners anteriores
  precioDetalle.removeEventListener('input', calcularTotalDetalle);
  
  // Limpiar listener de cantidad (normal o debounced)
  if (cantidadDetalle._debouncedHandler) {
    cantidadDetalle.removeEventListener('input', cantidadDetalle._debouncedHandler);
    delete cantidadDetalle._debouncedHandler;
  } else {
    cantidadDetalle.removeEventListener('input', calcularTotalDetalle);
  }
  
  totalDetalle.removeEventListener('input', calcularTotalDetalle);

  if (productoId === PRODUCTO_ID_LIBRE) {
    precioDetalle.readOnly = false;
    totalDetalle.readOnly = false;

    // Añadimos los event listeners para el producto libre
    precioDetalle.addEventListener('input', calcularTotalDetalle);
    cantidadDetalle.addEventListener('input', calcularTotalDetalle);
    totalDetalle.addEventListener('input', calcularTotalDetalle);

    // Manejar el campo de concepto personalizado si existe
    if (conceptoInput) {
      conceptoInput.style.display = 'block';
      if (!conceptoInput.dataset.listenerAdded) {
        // Usar debounce para evitar parpadeos al filtrar
        const handlerBusqueda = debounce(() => {
          const busqueda = conceptoInput.value;
          const productosFiltrados = filtrarProductos(busqueda, productosOriginales);
          actualizarSelectProductos(productosFiltrados, conceptoDetalle);
        }, 300);
        
        conceptoInput.addEventListener('input', handlerBusqueda);
        conceptoInput.dataset.listenerAdded = true;
        // Guardamos referencia para poder limpiarlo si fuera necesario (aunque aquí usamos flag listenerAdded)
        conceptoInput._debouncedSearch = handlerBusqueda;
      }
    }
  } else {
    precioDetalle.readOnly = true;
    totalDetalle.readOnly = true;

    // Para productos normales, añadir listener solo en cantidad para calcular franjas (con debounce)
    // Esto evita llamadas concurrentes que resultan en "Cálculo en progreso"
    const handler = debounce(calcularTotalDetalle, 500);
    cantidadDetalle._debouncedHandler = handler;
    cantidadDetalle.addEventListener('input', handler);

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

  // Solo calcular el total inicial con precio base, sin consultar franjas
  const cantidad = parseFloat(cantidadDetalle.value) || 1;
  const impuestos = parseFloat(impuestoDetalle.value) || 21;
  const subtotal = precioOriginal * cantidad;
  // Redondear IVA (base * porcentaje) a 2 decimales antes de sumar
  const impuestoCalc = Number((subtotal * (impuestos / 100)).toFixed(2));
  const total = Number((subtotal + impuestoCalc).toFixed(2));
  totalDetalle.value = total.toFixed(2);

  await calcularTotalDetalle();
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