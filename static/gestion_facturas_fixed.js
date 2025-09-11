import { IP_SERVER, PORT } from './constantes.js';
import { 
    PRODUCTO_ID_LIBRE,
    formatearImporte,
    redondearImporte,
    formatearApunto,
    parsearImporte,
    calcularPrecioConDescuento,
    calcularTotalDetalle,
    abrirModalPagos as abrirModal,
    cerrarModalPagos as cerrarModal,
    calcularCambio as calcularCambioModal,
    getEstadoFormateado,
    getCodigoEstado,
    formatearFechaSoloDia,
    convertirFechaParaAPI,
    formatearFecha
} from './scripts_utils.js';
import { mostrarNotificacion, mostrarConfirmacion } from './notificaciones.js';
import {
    cargarProductos as cargarProductosCommon,
    actualizarSelectProductos,
    filtrarProductos as filtrarProductosCommon,
    limpiarCamposDetalle,
    seleccionarProducto as seleccionarProductoCommon,
    validarDetalle,
    volverSegunOrigen
} from './common.js';
// Variables globales
let detalles = [];
let idFactura = null;
let idContacto = null;
let productosOriginales = [];
let detalleEnEdicion = null;
let modoGuardar = false; // Flag global para indicar modo guardar
let botonUsandose = null;
// Flag global para indicar si la factura está cobrada
let facturaCobrada = false;

function abrirModalPagos() {
  // Usar el total de detalles del día actual para la modal
  const totalDiaActual = calcularTotalDetallesDiaActual();
  const totalPunto = formatearApunto(formatearImporte(totalDiaActual));
  const fechaInput = document.getElementById('fecha').value;
  
  // Convertir la fecha al formato DD/MM/AAAA si no está en ese formato
  let fechaFormateada = fechaInput;
  if (fechaInput.includes('-')) {
    const partes = fechaInput.split('-');
    fechaFormateada = `${partes[2]}/${partes[1]}/${partes[0]}`;
  }
  
  abrirModal(totalPunto, fechaFormateada);
}

function calcularTotalDetallesDiaActual() {
  return detalles.reduce((total, detalle) => {
    return total + (detalle.total || 0);
  }, 0);
}

async function procesarPago(formaPago, totalPago) {
  try {
    botonUsandose = 'cobrar';
    await guardarFactura(formaPago, totalPago, 'C');
  } catch (error) {
    console.error('Error al procesar el pago:', error);
    mostrarNotificacion('Error al procesar el pago', 'error');
  } finally {
    botonUsandose = null;
  }
}

// Función para eliminar detalle
async function eliminarDetalle(index) {
  try {
    const confirmado = await mostrarConfirmacion('¿Está seguro de eliminar este detalle?');
    if (confirmado) {
      detalles.splice(index, 1);
      actualizarTablaDetalles();
      mostrarNotificacion('Detalle eliminado correctamente', 'success');
    }
  } catch (error) {
    console.error('Error al eliminar detalle:', error);
    mostrarNotificacion('Error al eliminar detalle', 'error');
  }
}

// Función para actualizar la tabla de detalles
function actualizarTablaDetalles() {
  const tbody = document.querySelector('#tabla-detalle-proforma tbody');
  if (!tbody) return;

  tbody.innerHTML = '';

  detalles.forEach((detalle, index) => {
    const fila = document.createElement('tr');
    fila.dataset.index = index;
    
    const precioUnitario = parseFloat(detalle.precio_unitario) || 0;
    const cantidad = parseFloat(detalle.cantidad) || 0;
    const descuento = parseFloat(detalle.descuento) || 0;
    
    // Calcular precio con descuento
    const precioConDescuento = precioUnitario * (1 - descuento / 100);
    const total = precioConDescuento * cantidad;

    fila.innerHTML = `
      <td>${detalle.concepto}</td>
      <td>${formatearImporte(precioUnitario)}</td>
      <td>${cantidad}</td>
      <td>${descuento}%</td>
      <td>${formatearImporte(total)}</td>
      <td class="columna-eliminar">
        <button type="button" class="btn-icon btn-eliminar" data-index="${index}">
          🗑️
        </button>
      </td>
    `;
    
    tbody.appendChild(fila);
  });

  actualizarTotales();
}

// Función para actualizar los totales
function actualizarTotales() {
  const totalBruto = calcularTotalBruto();
  const totalImpuestos = calcularTotalImpuestos();
  const totalNeto = totalBruto + totalImpuestos;

  document.getElementById('total-proforma').value = formatearImporte(totalNeto);
}

// Función para guardar la factura
async function guardarFactura(formaPago = 'E', totalPago = 0, estado = 'C') {
    console.log('Guardar factura con botón:', botonUsandose);
    
    // Si se está usando el botón Guardar, forzar estado P e importe 0
    if (botonUsandose === 'guardar') {
        estado = 'P';
        totalPago = 0;
        formaPago = 'E';
    }

    try {
        // Validar que hay detalles
        if (detalles.length === 0) {
            mostrarNotificacion('Debe agregar al menos un detalle a la factura', 'warning');
            return;
        }

        // Validar contacto
        if (!idContacto) {
            mostrarNotificacion('Debe seleccionar un contacto', 'warning');
            return;
        }

        // Calcular totales
        const total = calcularTotalBruto();
        const importe_bruto = total;
        const importe_impuestos = calcularTotalImpuestos();
        const importeCobrado = estado === 'C' ? totalPago : 0;

        // Preparar detalles para envío
        const detallesBase = detalles.map(detalle => ({
            concepto: detalle.concepto,
            precio_unitario: parseFloat(detalle.precio_unitario) || 0,
            cantidad: parseFloat(detalle.cantidad) || 0,
            descuento: parseFloat(detalle.descuento) || 0,
            total: parseFloat(detalle.total) || 0,
            producto_id: detalle.producto_id || null
        }));

        // Crear objeto factura
        const factura = {
            id: idFactura,
            numero: document.getElementById('numero').value,
            fecha: convertirFechaParaAPI(document.getElementById('fecha').value),
            idContacto: idContacto,
            nif: document.getElementById('identificador').value,
            detalles: detallesBase,
            total: total,
            formaPago: formaPago,
            importe_bruto: importe_bruto,
            importe_impuestos: importe_impuestos,
            importe_cobrado: importeCobrado,
            estado: estado, // Usar directamente el estado que viene por parámetro
            tipo: document.getElementById('tipo-factura').value || 'N', // Añadir el tipo de factura
            timestamp: new Date().toISOString()
        };

        console.log('Enviando factura con importes recalculados:', factura);

        // Guardar la factura
        const url = idFactura 
            ? `http://${IP_SERVER}:${PORT}/api/facturas/actualizar`
            : `http://${IP_SERVER}:${PORT}/api/facturas`;

        const response = await fetch(url, {
            method: idFactura ? 'PATCH' : 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            body: JSON.stringify(factura)
        });

        if (!response.ok) {
            const contentType = response.headers.get('content-type');
            if (contentType && contentType.includes('application/json')) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Error al guardar la factura');
            } else {
                throw new Error(`Error del servidor (${response.status}): Por favor, contacte con soporte técnico`);
            }
        }
        
        let result;
        try {
            result = await response.json();
        } catch (e) {
            throw new Error('Error al procesar la respuesta del servidor');
        }
        
        if (!result.id) {
            throw new Error(result.error || 'Error al guardar la factura');
        }

        // Mostrar notificaciones de progreso enviadas por el backend
        console.log('[DEBUG] notificaciones recibidas:', result.notificaciones);
        if (result.notificaciones && Array.isArray(result.notificaciones)) {
            result.notificaciones.forEach(m => {
                mostrarNotificacion(m, 'info');
            });
        }
        // Mostrar notificación final de éxito
        mostrarNotificacion('Factura guardada correctamente', 'success');
        // Esperar suficiente tiempo (3.5s) para que el usuario vea las notificaciones
        setTimeout(() => {
            volverSegunOrigen();
        }, 3500);
    } catch (error) {
        console.error('Error al guardar la factura:', error);
        mostrarNotificacion(error.message || 'Error al guardar la factura', "error");
    }
}

// Función para calcular el total bruto
function calcularTotalBruto() {
    return detalles.reduce((total, detalle) => {
        return total + (parseFloat(detalle.total) || 0);
    }, 0);
}

// Función para calcular el total de impuestos
function calcularTotalImpuestos() {
    // Por ahora retornamos 0, pero aquí se calcularían los impuestos
    return 0;
}

// Función para cargar productos
async function cargarProductos() {
    try {
        productosOriginales = await cargarProductosCommon();
        actualizarSelectProductos(productosOriginales, document.getElementById('concepto-detalle'));
    } catch (error) {
        console.error('Error al cargar productos:', error);
        mostrarNotificacion('Error al cargar productos', 'error');
    }
}

// Función para seleccionar producto
function seleccionarProducto() {
    seleccionarProductoCommon();
}

// Función para validar y agregar detalle
async function validarYAgregarDetalle() {
    try {
        const detalle = validarDetalle();
        if (!detalle) return false;

        // Si estamos editando, reemplazar el detalle existente
        if (detalleEnEdicion !== null) {
            detalles[detalleEnEdicion] = detalle;
            detalleEnEdicion = null;
        } else {
            // Agregar nuevo detalle
            detalles.push(detalle);
        }

        // Actualizar la tabla
        actualizarTablaDetalles();

        // Limpiar campos
        limpiarCamposDetalle();

        // Reset del selector sin recargar todos los productos
        document.getElementById('concepto-detalle').value = "";

        // Enfocar en la búsqueda para siguiente producto
        document.getElementById('busqueda-producto').focus();

        mostrarNotificacion('Detalle agregado correctamente', 'success');
        return true;
    } catch (error) {
        console.error('Error al agregar detalle:', error);
        mostrarNotificacion('Error al agregar detalle', 'error');
        return false;
    }
}

// Función para cargar detalle para editar
function cargarDetalleParaEditar(fila) {
    if (facturaCobrada) {
        mostrarNotificacion('No se puede editar una factura cobrada', 'warning');
        return;
    }

    const index = parseInt(fila.dataset.index);
    const detalle = detalles[index];
    
    if (!detalle) return;

    // Marcar que estamos editando
    detalleEnEdicion = index;

    // Cargar datos en el formulario
    const conceptoSelect = document.getElementById('concepto-detalle');
    conceptoSelect.value = detalle.producto_id || '';
    
    document.getElementById('precio-unitario').value = formatearImporte(detalle.precio_unitario);
    document.getElementById('cantidad').value = detalle.cantidad;
    document.getElementById('descuento').value = detalle.descuento;

    // Cambiar el texto del botón
    const btnAgregar = document.getElementById('btn-agregar-detalle');
    if (btnAgregar) {
        btnAgregar.textContent = 'Actualizar Detalle';
    }

    // Enfocar en cantidad para facilitar edición
    document.getElementById('cantidad').focus();
}

// Función para configurar el botón de volver
function configurarBotonVolver() {
    const btnVolver = document.getElementById('btnVolver');
    if (btnVolver) {
        btnVolver.addEventListener('click', volverSegunOrigen);
    }
}

// Función para cargar una factura existente
async function cargarFactura(facturaId) {
    try {
        const response = await fetch(`http://${IP_SERVER}:${PORT}/api/facturas/${facturaId}`);
        if (!response.ok) {
            throw new Error('Error al cargar la factura');
        }
        
        const factura = await response.json();
        
        // Cargar datos en el formulario
        idFactura = factura.id;
        idContacto = factura.idContacto;
        
        document.getElementById('numero').value = factura.numero || '';
        document.getElementById('fecha').value = formatearFecha(factura.fecha);
        document.getElementById('identificador').value = factura.nif || '';
        document.getElementById('estado').value = getEstadoFormateado(factura.estado);
        document.getElementById('tipo-factura').value = factura.tipo || 'N';
        
        // Cargar detalles
        detalles = factura.detalles || [];
        actualizarTablaDetalles();
        
        // Marcar si está cobrada
        facturaCobrada = factura.estado === 'C';
        
    } catch (error) {
        console.error('Error al cargar factura:', error);
        mostrarNotificacion('Error al cargar la factura', 'error');
    }
}

// Función para inicializar nueva factura
async function inicializarNuevaFactura() {
    try {
        // Generar número de factura
        const response = await fetch(`http://${IP_SERVER}:${PORT}/api/facturas/siguiente_numero`);
        if (!response.ok) {
            throw new Error('Error al obtener el siguiente número');
        }
        
        const data = await response.json();
        const fecha = new Date();
        const año = fecha.getFullYear();
        const numeroPadded = data.numero.toString().padStart(4, '0');
        const numeracion = `F${año}${numeroPadded}`;

        // Establecer valores por defecto
        const dia = fecha.getDate().toString().padStart(2, '0');
        const mes = (fecha.getMonth() + 1).toString().padStart(2, '0');
        const añoCompleto = fecha.getFullYear();
        
        document.getElementById('fecha').value = `${dia}/${mes}/${añoCompleto}`;
        document.getElementById('numero').value = numeracion;
        document.getElementById('estado').value = 'Pendiente';
        document.getElementById('total-proforma').value = '0,00';
        
        detalles = [];
        actualizarTablaDetalles();
        
    } catch (error) {
        console.error('Error al inicializar nueva factura:', error);
        mostrarNotificacion('Error al inicializar nueva factura', 'error');
    }
}

// Función para filtrar productos
function filtrarProductos() {
    const busquedaProducto = document.getElementById('busqueda-producto').value;
    const productosFiltrados = filtrarProductosCommon(busquedaProducto, productosOriginales);
    actualizarSelectProductos(productosFiltrados, document.getElementById('concepto-detalle'));

    if (productosFiltrados.length > 0) {
        const selectProducto = document.getElementById('concepto-detalle');
        selectProducto.value = productosFiltrados[0].id;
        seleccionarProducto();
    }
}

// Inicialización al cargar el DOM
document.addEventListener('DOMContentLoaded', async function() {
    // Sin cache global - cargar productos directamente cuando sea necesario

    // Configurar el comportamiento del botón de volver
    configurarBotonVolver();
    
    // Cargar productos
    await cargarProductos();
    
    // Inicializar la página según el modo
    const urlParams = new URLSearchParams(window.location.search);
    const facturaId = urlParams.get('facturaId');
    
    if (facturaId) {
        // Modo edición
        await cargarFactura(facturaId);
    } else {
        // Modo creación
        await inicializarNuevaFactura();
    }

    // Configurar eventos de botones
    const btnGuardar = document.getElementById('btnGuardar');
    if (btnGuardar) {
        btnGuardar.addEventListener('click', async () => {
            botonUsandose = 'guardar';
            await guardarFactura();
            botonUsandose = null;
        });
    }

    const btnCobrar = document.getElementById('btnCobrarp');
    if (btnCobrar) {
        btnCobrar.addEventListener('click', abrirModalPagos);
    }

    // Configurar delegación de eventos para la tabla
    const tabla = document.getElementById('tabla-detalle-proforma');
    if (tabla) {
        tabla.addEventListener('click', async (event) => {
            const target = event.target;
            
            if (target.classList.contains('btn-eliminar')) {
                const fila = target.closest('tr');
                const index = parseInt(fila.dataset.index);
                await eliminarDetalle(index);
                event.stopPropagation();
            } else {
                const fila = target.closest('tr');
                if (fila && !target.classList.contains('columna-eliminar')) {
                    cargarDetalleParaEditar(fila);
                }
            }
        });
    }
});

// Hacer las funciones disponibles globalmente
Object.assign(window, {
    guardarFactura,
    validarYAgregarDetalle,
    seleccionarProducto,
    filtrarProductos,
    cargarDetalleParaEditar,
    cerrarModalPagos: cerrarModal,
    calcularCambio: calcularCambioModal,
    procesarPago,
    eliminarDetalle
});
