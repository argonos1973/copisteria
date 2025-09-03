import { IP_SERVER, PORT } from './constantes.js';
import { 
  PRODUCTO_ID_LIBRE,
  truncarDecimales,
  formatearImporte,
  formatearApunto,
  parsearImporte,
  calcularPrecioConDescuento,
  calcularTotalDetalle,
  debounce,
  abrirModalPagos as abrirModal,
  cerrarModalPagos as cerrarModal,
  calcularCambio as calcularCambioModal,
  inicializarEventosModal,
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
  redondearImporte
} from './common.js';

/**
 * Se ejecuta al cargar el DOM. Inicializa la delegación de eventos en la tabla
 * y maneja la creación o carga de tickets (según exista 'ticketId').
 */
document.addEventListener("DOMContentLoaded", async () => {
  // 1. Inicializar EventDelegation para la tabla
  inicializarEventDelegation();

  // 2. Asociar los listeners que antes se ponían inline
  asociarEventos();

  // 3. Verificar si tenemos un ticketId en la URL
  const urlParams = new URLSearchParams(window.location.search);
  const idTicket = urlParams.get('ticketId');
 
  try {
    // 4. Cargar productos desde la API
    await cargarProductos();

    // 5. Si existe 'ticketId', cargar el ticket; si no, inicializar uno nuevo
    if (idTicket) {
      await cargarTicket(idTicket);
    } else {
      inicializarNuevoTicket();
    }

    // 6. Ajustes: mostrar botones "Volver" e "Imprimir", etc.
    const estadoTicket = document.getElementById("estado-ticket").value.toUpperCase();
    const btnGuardar   = document.getElementById("btn-guardar-ticket");
    const btnVolver    = document.getElementById("btn-volver");
    const btnImprimir  = document.getElementById("btn-imprimir-ticket");
    const bntAnadir    = document.getElementById("btn-agregar-detalle");
    const btnAnular    = document.getElementById("btn-anular-ticket");

    // Si el ticket está anulado o cobrado, deshabilitar edición
    if (estadoTicket === 'A' || estadoTicket === 'C') {
      if (btnGuardar) btnGuardar.style.display = 'none';
      if (bntAnadir)  bntAnadir.style.display  = 'none';
      const btnCobrarTmp = document.getElementById('btn-cobrar');
      if (btnCobrarTmp)  btnCobrarTmp.style.display = 'none';
      // Cambiar cursor del grid de detalles
      const gridBody = document.querySelector('#tabla-detalle-ticket tbody');
      if (gridBody) {
        gridBody.style.cursor = 'not-allowed';
        gridBody.classList.add('grid-bloqueada');
      }
    }

    // Configurar visibilidad y eventos del botón "Anular"
    if (btnAnular) {
      if (idTicket && estadoTicket !== 'A') {
        btnAnular.style.display = 'inline-block';
      }
      btnAnular.addEventListener('click', async () => {
        if (!idTicket) return;
        const confirmado = await mostrarConfirmacion('¿Está seguro de anular este ticket? Se creará un ticket rectificativo.');
        if (!confirmado) return;
        try {
          const resp = await fetch(`http://${IP_SERVER}:${PORT}/api/tickets/anular/${idTicket}`, { method: 'POST' });
          const data = await resp.json();
          if (!resp.ok || !data.exito) {
            throw new Error(data.error || 'Error al anular el ticket');
          }
          mostrarNotificacion('Ticket anulado correctamente', 'exito');
          setTimeout(() => volverAConsulta(), 1000);
        } catch (error) {
          console.error(error);
          mostrarNotificacion('Error al anular el ticket', 'error');
        }
      });
    }

    if (btnVolver)     btnVolver.style.display    = "inline-block";
    if (btnImprimir)   btnImprimir.style.display  = "inline-block";

    // Foco inicial en el campo de búsqueda de producto
    document.getElementById('busqueda-producto').focus();

    // Agregar eventos para "concepto-input" si existe
    const conceptoInput = document.getElementById('concepto-input');
    if (conceptoInput) {
      const debouncedFiltroConcepto = debounce(() => filtrarProductos(), 200);
      conceptoInput.removeEventListener('input', debouncedFiltroConcepto);
      conceptoInput.addEventListener('input', debouncedFiltroConcepto);
    }

    // Asociar evento al botón cobrar
    const btnCobrar = document.getElementById('btn-cobrar');
    if (btnCobrar) {
      btnCobrar.removeEventListener('click', procesarPago);
      btnCobrar.addEventListener('click', procesarPago);
    }

  } catch (error) {
    console.error("Error durante la inicialización:", error);
    mostrarNotificacion("Error durante la inicialización", "error");
  }


});

/**
 * Asocia los eventos que antes se llamaban inline desde el HTML.
 * Esto evita el uso de oninput, onclick, etc. en el HTML.
 */
function asociarEventos() {
  // Botón "Volver"
  const btnVolver = document.getElementById("btn-volver");
  if (btnVolver) {
    btnVolver.addEventListener('click', () => volverAConsulta());
  }

  // Botón "Guardar" => abrir el modal de pagos
  const btnGuardar = document.getElementById("btn-guardar-ticket");
  if (btnGuardar) {
    btnGuardar.addEventListener('click', () => abrirModalPagos());
  }

  // Botón "Imprimir" => imprimirFactura
  const btnImprimir = document.getElementById("btn-imprimir-ticket");
  if (btnImprimir) {
    btnImprimir.addEventListener('click', () => {
      const idticket = document.getElementById('idticket').value;
    // Construir la URL para la página de impresión con el parámetro 'ticketId'
    const urlImprimir = `imprimir-ticket.html?ticketId=${encodeURIComponent(idticket)}`;

    // Abrir una nueva ventana con la página de impresión
    window.open(urlImprimir, '_blank', 'width=800,height=600');
      // aquí llamas a tu función imprimirFactura(idticket), si la tienes en otro script
      // o haz window.imprimirFactura(idticket) si la declaraste en global
    });
  }

  // Input "busqueda-producto" => filtrarProductos
  const busquedaProducto = document.getElementById('busqueda-producto');
  if (busquedaProducto) {
    const debouncedFiltro = debounce(() => filtrarProductos(), 200);
    busquedaProducto.removeEventListener('input', debouncedFiltro);
    busquedaProducto.addEventListener('input', debouncedFiltro);
  }

  // Selector "concepto-detalle" => seleccionarProducto
  const conceptoDetalle = document.getElementById('concepto-detalle');
  if (conceptoDetalle) {
    conceptoDetalle.addEventListener('change', () => seleccionarProducto());
  }

  // Botón "Añadir" => validarYAgregarDetalle
  const btnAgregarDetalle = document.getElementById('btn-agregar-detalle');
  if (btnAgregarDetalle) {
    btnAgregarDetalle.addEventListener('click', () => validarYAgregarDetalle());
  }

  // Campo "cantidad-detalle" => calcularTotalDetalle
  const cantidadDetalle = document.getElementById('cantidad-detalle');
  if (cantidadDetalle) {
    cantidadDetalle.addEventListener('input', calcularTotalDetalle);
  }

  // Campo "precio-detalle" => calcularTotalDetalle
  const precioDetalle = document.getElementById('precio-detalle');
  if (precioDetalle) {
    precioDetalle.addEventListener('input', calcularTotalDetalle);
  }

  // Modal Pagos: Botón "Cerrar"
  const closeModal = document.getElementById('closeModal'); 
  if (closeModal) {
    closeModal.addEventListener('click', () => cerrarModalPagos());
  }

  // Modal Pagos: Campo "total-entregado" => calcularCambio
  const totalEntregado = document.getElementById('modal-total-entregado');
  if (totalEntregado) {
    totalEntregado.addEventListener('input', () => calcularCambio());
  }

  // Modal Pagos: Botón "Cobrar"
  const btnCobrar = document.getElementById('btn-cobrar');
  if (btnCobrar) {
    btnCobrar.onclick = function(e) {
      e.preventDefault();
      procesarPago();
    };
  }
}

/**
 * Inicializa la delegación de eventos en la tabla (para click en ícono de eliminar o edición)
 */
export function inicializarEventDelegation() {
  const tbody = document.querySelector('#tabla-detalle-ticket tbody');
  if (!tbody) return;

  tbody.addEventListener('click', async function(event) {
    const target = event.target;
    // Evitar modificaciones si el ticket está anulado
    const estadoActual = document.getElementById('estado-ticket') ? document.getElementById('estado-ticket').value.toUpperCase() : '';
    if (estadoActual === 'A' || estadoActual === 'C') {
      event.stopPropagation();
      return;
    }
    
    if (target && target.classList.contains('btn-icon')) {
      event.stopPropagation();
      await eliminarFila(target);
    } else {
      const fila = target.closest('tr');
      if (fila) {
        cargarDetalleParaEditar(fila);
      }
    }
  });
}

/**
 * Redirige a la página de consulta
 */
export function volverAConsulta() {
  window.location.href = '/CONSULTA_TICKETS.html';
}

/**
 * Abre el modal de pagos
 */
export function abrirModalPagos() {
  // Tomar exactamente el valor mostrado en pantalla (formato europeo con €)
  const totalDisplay = document.getElementById('total-ticket').value;
  const fechaInput = document.getElementById('fecha-ticket').value;
  
  // Convertir la fecha al formato DD/MM/AAAA si está en formato YYYY-MM-DD
  let fechaFormateada = fechaInput;
  if (fechaInput.includes('-')) {
    const [año, mes, dia] = fechaInput.split('-');
    fechaFormateada = `${dia}/${mes}/${año}`;
  }
  
  const formaPago = window.ticketFormaPago || 'E';
  
  abrirModal({
    total: totalDisplay,
    fecha: fechaFormateada,
    formaPago: formaPago,
    titulo: 'Añadir Pago',
    onCobrar: (formaPago, totalPago, total) => {
      procesarPago();
    }
  });
}

/**
 * Cierra el modal de pagos
 */
export function cerrarModalPagos() {
  cerrarModal();
}

/**
 * Calcula el cambio
 */
export function calcularCambio() {
  const totalTicket = parseFloat(document.getElementById('modal-total-ticket').value) || 0;
  const totalEntregado = parseFloat(document.getElementById('modal-total-entregado').value) || 0;
  const cambio = calcularCambioModal(totalTicket, totalEntregado);
  document.getElementById('modal-total-cambio').value = cambio.toFixed(2);
}

let productosOriginales = [];

/**
 * Carga la lista de productos desde la API
 */
export async function cargarProductos() {
  productosOriginales = await cargarProductosCommon();
  actualizarSelectProductos(productosOriginales, document.getElementById('concepto-detalle'));
}

/**
 * Filtra los productos en el select según el texto ingresado
 */
export function filtrarProductos() {
  const busquedaProducto = document.getElementById('busqueda-producto').value;
  const productosFiltrados = filtrarProductosCommon(busquedaProducto, productosOriginales);
  actualizarSelectProductos(productosFiltrados, document.getElementById('concepto-detalle'));

  if (productosFiltrados.length > 0) {
    const selectProducto = document.getElementById('concepto-detalle');
    selectProducto.value = productosFiltrados[0].id;
    seleccionarProducto();
  }
}

/**
 * Selecciona un producto y actualiza los campos correspondientes
 */
export function seleccionarProducto() {
  const formElements = {
    conceptoDetalle: document.getElementById('concepto-detalle'),
    descripcionDetalle: document.getElementById('descripcion-detalle'),
    cantidadDetalle: document.getElementById('cantidad-detalle'),
    precioDetalle: document.getElementById('precio-detalle'),
    impuestoDetalle: document.getElementById('impuesto-detalle'),
    totalDetalle: document.getElementById('total-detalle'),
    conceptoInput: document.getElementById('concepto-input'),
    busquedaProducto: document.getElementById('busqueda-producto')
  };
  
  // Para tickets siempre aplicar descuentos por franja, pasar '' como tipo
  seleccionarProductoCommon(formElements, productosOriginales, 'ticket');
}

/**
 * Valida los campos y añade un detalle al ticket
 */
export function validarYAgregarDetalle() {
  const select = document.getElementById('concepto-detalle');
  const productoId = select.value;
  let productoSeleccionado = select.options[select.selectedIndex].textContent;
  const descripcion = document.getElementById('descripcion-detalle').value.trim();
  const cantidad = parseFloat(document.getElementById('cantidad-detalle').value);
  let precioOriginal = parseFloat(select.options[select.selectedIndex].dataset.precioOriginal) || 0;
  let precioDetalle = parseFloat(document.getElementById('precio-detalle').value);

  if (productoId === PRODUCTO_ID_LIBRE) {
    precioOriginal = precioDetalle;
    productoSeleccionado = descripcion;
    if (!productoSeleccionado) {
      mostrarNotificacion("Debe ingresar un concepto para el producto.", "error");
      return false;
    }
  }

  const impuestos = parseFloat(document.getElementById('impuesto-detalle').value) || 0;
  const total     = parseFloat(document.getElementById('total-detalle').value) || 0;

  if (total <= 0) {
    mostrarNotificacion("El campo 'Total' es obligatorio y debe ser mayor que 0.", "error");
    return false;
  }
  if (cantidad <= 0) {
    mostrarNotificacion("El campo 'Cantidad' es obligatorio y debe ser mayor que 0.", "error");
    return false;
  }

  const detalleId = document.getElementById('btn-agregar-detalle').dataset.detalleId || null;
  agregarDetalle(
    productoSeleccionado,
    descripcion,
    cantidad,
    precioOriginal,
    precioDetalle,
    impuestos,
    total,
    productoId,
    detalleId
  );

  // Crear el objeto formElements para limpiar los campos
  const formElements = {
    conceptoDetalle: document.getElementById('concepto-detalle'),
    descripcionDetalle: document.getElementById('descripcion-detalle'),
    cantidadDetalle: document.getElementById('cantidad-detalle'),
    precioDetalle: document.getElementById('precio-detalle'),
    impuestoDetalle: document.getElementById('impuesto-detalle'),
    totalDetalle: document.getElementById('total-detalle'),
    conceptoInput: document.getElementById('concepto-input'),
    busquedaProducto: document.getElementById('busqueda-producto')
  };
  
  limpiarCamposDetalle(formElements);
  
  // Recargar la lista de productos para mantenerla actualizada
  cargarProductos();
  
  return true;
}

/**
 * Añade la fila de detalle en la tabla
 */
export function agregarDetalle(
  concepto, 
  descripcion, 
  cantidad, 
  precioOriginal, 
  precioConDescuento, 
  impuestos, 
  totalConIVA, 
  productoId, 
  detalleId = null
) {
  const tbody = document.querySelector('#tabla-detalle-ticket tbody');
  const tr = document.createElement('tr');
  
  // Asignar el productoId como atributo de datos
  tr.setAttribute('data-producto-id', productoId || PRODUCTO_ID_LIBRE);
  if (detalleId) {
    tr.setAttribute('data-detalle-id', detalleId);
  }
  
  // Formatear el precio con 5 decimales y el total con 2
  const precioFormateado = Number(precioConDescuento).toFixed(5).replace('.', ',') + ' €';
  const totalFormateado = formatearImporte(totalConIVA);
  
  tr.innerHTML = `
    <td>${concepto}</td>
    <td>${descripcion}</td>
    <td style="text-align: right;">${cantidad}</td>
    <td style="text-align: right;">${precioFormateado}</td>
    <td style="text-align: right;">${impuestos}%</td>
    <td style="text-align: right;">${totalFormateado}</td>
    <td class="acciones-col"><button class="btn-icon" title="Eliminar">✕</button></td>
  `;
  tbody.appendChild(tr);
  sumarTotales();
  mostrarNotificacion('Detalle agregado correctamente', 'success');
}

/**
 * Edita un detalle al hacer click en su fila
 */
export function cargarDetalleParaEditar(fila) {
  const concepto    = fila.cells[0].textContent;
  const descripcion = fila.cells[1].textContent;
  const cantidad    = parseFloat(fila.cells[2].textContent);
  const precioDet   = parseFloat(fila.cells[3].textContent.replace(' €', '').replace(',', '.')); // Mantener precio sin redondear
  const impuestos   = Number(parseFloat(fila.cells[4].textContent.replace('%', '').replace(',', '.')).toFixed(2));
  const total       = Number(parseFloat(fila.cells[5].textContent.replace(' €', '').replace(',', '.').replace(/[^0-9.]/g, '')).toFixed(2));
  const detalleId   = fila.getAttribute('data-detalle-id') || null;
  const productoId  = fila.getAttribute('data-producto-id') || null;

  if (!productoId) {
    console.warn(`No se encontró ID del producto para "${concepto}".`);
    mostrarNotificacion("No se puede editar este detalle debido a un error en los datos del producto.", "error");
    return;
  }

  const selectProducto = document.getElementById('concepto-detalle');
  const optionProducto = Array.from(selectProducto.options).find(option => option.value == productoId);

  if (optionProducto) {
    optionProducto.selected = true;
  } else {
    console.warn(`Producto con ID "${productoId}" no encontrado en el selector.`);
    mostrarNotificacion(`Producto "${concepto}" no se encontró en la lista de productos disponibles.`, "error");
    return;
  }

  // Crear el objeto formElements
  const formElements = {
    conceptoDetalle: selectProducto,
    descripcionDetalle: document.getElementById('descripcion-detalle'),
    cantidadDetalle: document.getElementById('cantidad-detalle'),
    precioDetalle: document.getElementById('precio-detalle'),
    impuestoDetalle: document.getElementById('impuesto-detalle'),
    totalDetalle: document.getElementById('total-detalle'),
    conceptoInput: document.getElementById('concepto-input'),
    busquedaProducto: document.getElementById('busqueda-producto')
  };

  seleccionarProducto();

  document.getElementById('descripcion-detalle').value = descripcion.toUpperCase();
  document.getElementById('cantidad-detalle').value    = cantidad;
  document.getElementById('impuesto-detalle').value    = 21;
  document.getElementById('precio-detalle').value      = Number(precioDet).toFixed(5); // Mantener 5 decimales en el precio
  document.getElementById('total-detalle').value       = total.toFixed(2);

  if (productoId === PRODUCTO_ID_LIBRE) {
    const conceptoInput = document.getElementById('concepto-input');
    conceptoInput.value = concepto;
    conceptoInput.style.display = 'block';

    if (!conceptoInput.dataset.listenerAdded) {
      conceptoInput.addEventListener('input', filtrarProductos);
      conceptoInput.dataset.listenerAdded = true;
    }
  }
  document.getElementById('btn-agregar-detalle').dataset.detalleId = detalleId;
  fila.remove();
  sumarTotales();
}

/**
 * Elimina una fila de la tabla de detalles
 */
export async function eliminarFila(icono) {
  try {
    const confirmado = await mostrarConfirmacion('¿Está seguro de eliminar este detalle?');
    if (confirmado) {
      icono.closest('tr').remove();
      sumarTotales();
      mostrarNotificacion('Detalle eliminado correctamente', 'success');
    }
  } catch (error) {
    console.error('Error al eliminar detalle:', error);
    mostrarNotificacion('Error al eliminar el detalle', 'error');
  }
}

/**
 * Suma el total de todos los detalles y lo refleja en el #total-ticket
 */
export function sumarTotales() {
  const tbody = document.querySelector('#tabla-detalle-ticket tbody');
  let sumaTotal = 0;

  tbody.querySelectorAll('tr').forEach(fila => {
    const totalTexto = fila.cells[5].textContent || "0";
    // Usar el parser centralizado para formato europeo (puntos de miles, coma decimal)
    const total = parsearImporte(totalTexto);
    // Redondear cada subtotal a 2 decimales antes de sumar
    sumaTotal += redondearImporte(total);
  });

  // Redondear el total final a 2 decimales
  const totalRedondeado = redondearImporte(sumaTotal);
  document.getElementById('total-ticket').value = formatearImporte(totalRedondeado);
}

/**
 * Función para obtener los detalles de la tabla
 */
function obtenerDetallesDeTabla() {
  const detalles = [];
  const tbody = document.querySelector('#tabla-detalle-ticket tbody');
  if (!tbody) {
    console.error('No se encontró la tabla de detalles');
    return detalles;
  }

  console.log('Obteniendo detalles de la tabla...');
  
  tbody.querySelectorAll('tr').forEach((fila, index) => {
    try {
      // Obtener los valores numéricos y limpiarlos de símbolos de moneda y espacios
      const cantidad = parseInt(fila.cells[2].textContent.trim());
      // Mantener 5 decimales en el precio
      const precio = Number(parseFloat(fila.cells[3].textContent.replace('€', '').replace(',', '.').trim()).toFixed(5));
      const impuestos = parseFloat(fila.cells[4].textContent.replace('%', '').trim());
      // El total se mantiene con 2 decimales
      const total = Number(parseFloat(fila.cells[5].textContent.replace('€', '').replace(',', '.').trim()).toFixed(2));
      
      // Obtener el productoId del atributo data-producto-id de la fila
      const productoId = fila.getAttribute('data-producto-id');
      
      const detalle = {
        concepto: fila.cells[0].textContent.trim(),
        descripcion: fila.cells[1].textContent.trim(),
        cantidad: cantidad,
        precio: precio,  // Ya viene con 5 decimales
        impuestos: impuestos,
        total: total,    // Ya viene con 2 decimales
        productoId: productoId || PRODUCTO_ID_LIBRE
      };

      // Validar que todos los campos necesarios estén presentes
      if (!detalle.concepto || !detalle.cantidad || !detalle.precio || !detalle.productoId) {
        console.error(`Detalle ${index + 1} incompleto:`, JSON.stringify(detalle, null, 2));
        throw new Error(`Detalle ${index + 1} incompleto`);
      }

      // Validar que los valores numéricos sean válidos
      if (isNaN(detalle.cantidad) || isNaN(detalle.precio) || isNaN(detalle.impuestos) || isNaN(detalle.total)) {
        console.error(`Detalle ${index + 1} con valores numéricos inválidos:`, JSON.stringify(detalle, null, 2));
        throw new Error(`Detalle ${index + 1} con valores numéricos inválidos`);
      }

      detalles.push(detalle);
      console.log(`Detalle ${index + 1} procesado:`, detalle);
    } catch (error) {
      console.error(`Error al procesar detalle ${index + 1}:`, error);
      mostrarNotificacion(`Error al procesar detalle ${index + 1}: ${error.message}`, 'error');
      throw error;
    }
  });

  if (detalles.length === 0) {
    mostrarNotificacion('Error: No se encontraron detalles válidos', 'error');
  }

  return detalles;
}

/**
 * Guardar o actualizar el ticket en la base de datos
 */
export async function guardarTicket(formaPago, totalPago, totalTicket, estadoTicket) {
  try {
    // Evitar múltiples intentos de guardado
    if (window.isTicketSaving) {
      console.log('Ya hay un guardado en proceso...');
      return;
    }
    window.isTicketSaving = true;

    // Convertir y redondear los valores numéricos con parser centralizado (formato europeo)
    totalPago = redondearImporte(parsearImporte(totalPago));
    totalTicket = redondearImporte(parsearImporte(totalTicket));


    // Obtener los elementos del DOM
    const idticketElement = document.getElementById('idticket');
    const fechaElement = document.getElementById('fecha-ticket');
    const idcontactoElement = document.getElementById('idcontacto');
    const numeroElement = document.getElementById('numero-ticket');

    // Verificar que todos los elementos existan
    if (!fechaElement || !numeroElement) {
      mostrarNotificacion('Error: Faltan elementos requeridos en el formulario', 'error');
      window.isTicketSaving = false;
      return;
    }

    // Obtener los valores, usando valores por defecto si son null
    const idticket = idticketElement ? idticketElement.value : null;
    const fecha = fechaElement.value;
    const idcontacto = idcontactoElement ? idcontactoElement.value : null;
    let numero = numeroElement.value;

    // Verificar que los valores requeridos estén presentes
    if (!fecha || !numero) {
      mostrarNotificacion('Error: Faltan datos requeridos (fecha o número)', 'error');
      window.isTicketSaving = false;
      return;
    }

 
    // Obtener los detalles de la tabla
    const detalles = obtenerDetallesDeTabla();
    if (detalles.length === 0) {
      mostrarNotificacion('Error: El ticket debe tener al menos un detalle', 'error');
      window.isTicketSaving = false;
      return;
    }

    // Validar que cada detalle tenga todos los campos necesarios
    const detallesInvalidos = detalles.filter(d => 
      !d.concepto || !d.cantidad || !d.precio || !d.productoId ||
      isNaN(d.cantidad) || isNaN(d.precio) || isNaN(d.impuestos) || isNaN(d.total)
    );

    if (detallesInvalidos.length > 0) {
      console.error('Detalles inválidos encontrados:', detallesInvalidos);
      mostrarNotificacion('Error: Hay detalles con datos inválidos', 'error');
      window.isTicketSaving = false;
      return;
    }

    // Calcular importe bruto (suma de precio * cantidad)
    const importe_bruto = redondearImporte(detalles.reduce((sum, d) => {
      const subtotal = d.precio * d.cantidad;
      return sum + subtotal;
    }, 0));

    // Calcular importe de impuestos
    const importe_impuestos = redondearImporte(detalles.reduce((sum, d) => {
      const subtotal = d.precio * d.cantidad;
      const impuesto = subtotal * (d.impuestos / 100);
      return sum + impuesto;
    }, 0));

    // Asegurar que el importe cobrado esté redondeado
    const importe_cobrado = redondearImporte(totalPago);

    const ticketData = {
      id: idticket,
      fecha: fecha,
      idcontacto: idcontacto,
      numero: numero,
      estado: estadoTicket,
      formaPago: formaPago,
      importe_bruto: importe_bruto,
      importe_impuestos: importe_impuestos,
      importe_cobrado: importe_cobrado,
      total: redondearImporte(totalTicket),
      detalles: detalles.map(d => ({
        ...d,
        precio: d.precio,
        total: redondearImporte(d.total)
      }))
    };

    console.log('Datos del ticket a guardar:', JSON.stringify(ticketData, null, 2));

    // Construir la URL base y endpoint según si es crear o actualizar
    const baseUrl = `http://${IP_SERVER}:${PORT}/api`;
    const url = idticket 
      ? `${baseUrl}/tickets/actualizar`
      : `${baseUrl}/tickets/guardar`;

    console.log('Enviando datos al servidor:', {
      url,
      method: idticket ? 'PATCH' : 'POST',
      data: ticketData
    });

    const response = await fetch(url, {
      method: idticket ? 'PATCH' : 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
      },
      body: JSON.stringify(ticketData)
    });

    // Log de la respuesta completa para depuración
    const responseData = await response.json();
    console.log('Respuesta completa del servidor:', {
      status: response.status,
      statusText: response.statusText,
      headers: Object.fromEntries(response.headers.entries()),
      data: responseData,
      url: response.url
    });

    if (!response.ok) {
      console.error('Error detallado:', {
        status: response.status,
        statusText: response.statusText,
        error: responseData.error || 'Error desconocido',
        detalles: responseData.detalles || {},
        datos_recibidos: responseData.datos_recibidos || {}
      });
      throw new Error(`Error al guardar el ticket: ${responseData.error || response.statusText}`);
    }

    mostrarNotificacion("Ticket guardado correctamente", "success");
    
    // Recargar la lista de productos para mantenerla actualizada
    await cargarProductos();
    
    // Redirigir a la página de consulta después de un breve retraso
    setTimeout(() => {
      window.location.href = 'CONSULTA_TICKETS.html';
    }, 1000);

  } catch (error) {
    console.error('Error al guardar el ticket:', error);
    mostrarNotificacion(error.message, "error");
  } finally {
    window.isTicketSaving = false;
  }
}

/**
 * Limpia todo el formulario (cabecera, detalles, etc.)
 */
export function limpiarFormularios() {
  document.getElementById('fecha-ticket').value = "";
  document.getElementById('numero-ticket').value = "";
  document.getElementById('total-ticket').value  = "0.00";
  document.querySelector('#tabla-detalle-ticket tbody').innerHTML = "";

  document.getElementById('cabecera-ticket').style.display = 'none';
  document.getElementById('form-detalle-ticket').style.display = 'none';
  document.getElementById('detalle-ticket-grid').style.display = 'none';
  document.getElementById('guardar-ticket-boton').style.display = 'none';
}

/**
 * Carga un ticket existente al HTML (cabecera + detalles) desde la API
 */
export async function cargarTicket(idTicket) {
  try {
    const response = await fetch(`http://${IP_SERVER}:${PORT}/api/tickets/obtenerTicket/${idTicket}`);
    if (!response.ok) {
      throw new Error(`Error al obtener el ticket: ${response.statusText}`);
    }

    const data = await response.json();
    if (data.ticket) {
      mostrarDatosTicket(data.ticket);
      mostrarDetallesTicket(data.detalles);

      const estadoTicket = data.ticket.estado.toUpperCase();
      const btnGuardar   = document.getElementById("btn-guardar-ticket");
      const bntAnadir    = document.getElementById("btn-agregar-detalle");

      if (estadoTicket === 'C' || estadoTicket === 'A') {
        if (btnGuardar) btnGuardar.style.display = "none";
        const gridBody = document.querySelector('#tabla-detalle-ticket tbody');
        if (gridBody) {
          gridBody.style.cursor = 'not-allowed';
          gridBody.classList.add('grid-bloqueada');
        }
        if (bntAnadir)  bntAnadir.style.display  = "none";
      } else {
        if (btnGuardar) btnGuardar.style.display = "";
        if (bntAnadir)  bntAnadir.style.display  = "";
      }
    } else {
      mostrarNotificacion("Ticket no encontrado.", "error");
    }
  } catch (error) {
    console.error("Error al cargar el ticket:", error);
    mostrarNotificacion("Error al cargar el ticket: " + error.message, "error");
  }
}

/**
 * Compara dos fechas (la actual y la del ticket) para ver si son el mismo día
 */
export function compararFechas(fecha) {
  const fechaActual = new Date();
  const otraFecha   = new Date(fecha);

  fechaActual.setHours(0, 0, 0, 0);
  otraFecha.setHours(0, 0, 0, 0);
  return fechaActual.getTime() === otraFecha.getTime();
}

/**
 * Muestra la cabecera y habilita el formulario con la información del ticket
 */
export function mostrarDatosTicket(ticket) {

  document.getElementById('idticket').value = ticket.id;
  document.getElementById('fecha-ticket').classList.add('detalle-proforma-item');
  document.getElementById('numero-ticket').classList.add('detalle-proforma-item');
  document.getElementById('estado-ticket').classList.add('detalle-proforma-item');
  document.getElementById('total-ticket').classList.add('detalle-proforma-item'); 
  
  // Formatear la fecha a DD/MM/AAAA
  const fechaPartes = ticket.fecha.split('-');
  if (fechaPartes.length === 3) {
    const [año, mes, dia] = fechaPartes;
    document.getElementById('fecha-ticket').value = `${dia}/${mes}/${año}`;
  } else {
    document.getElementById('fecha-ticket').value = ticket.fecha;
  }

  
  document.getElementById('numero-ticket').value = ticket.numero;

  let estado = "Pendiente";
  if (ticket.estado === "C") {
    estado = "Cobrado";
  }
  document.getElementById('estado-ticket').value = estado;
  document.getElementById('total-ticket').value  = ticket.total.toFixed(2);

  window.ticketFormaPago = ticket.formaPago;

  document.getElementById('cabecera-ticket').style.display       = 'block';
  document.getElementById('form-detalle-ticket').style.display   = 'block';
  document.getElementById('detalle-ticket-grid').style.display   = 'block';
  document.getElementById('guardar-ticket-boton').style.display  = 'block';

  document.getElementById('btn-imprimir-ticket').style.display   = 'inline-block';
}

/**
 * Muestra los detalles en la tabla
 */
export function mostrarDetallesTicket(detalles) {
  const tbody = document.querySelector('#tabla-detalle-ticket tbody');
  tbody.innerHTML = '';
  detalles.forEach(detalle => {
    const fila = document.createElement('tr');
    fila.setAttribute('data-producto-id', detalle.productoId);
    fila.setAttribute('data-precio-original', truncarDecimales(detalle.precio, 5));
    fila.setAttribute('data-precio-con-descuento', truncarDecimales(detalle.precio, 5));

    if (detalle.id) {
      fila.setAttribute('data-detalle-id', detalle.id);
    }
    fila.innerHTML = `
      <td>${detalle.concepto}</td>
      <td>${detalle.descripcion}</td>
      <td style="width: 50px; text-align: right;">${detalle.cantidad}</td>
      <td style="width: 50px; text-align: right;">${detalle.precio.toFixed(5)} €</td>
      <td style="width: 50px; text-align: right;">${Math.round(truncarDecimales(detalle.impuestos, 2))}%</td>
      <td style="width: 100px; text-align: right;">${detalle.total.toFixed(2)} €</td>
      <td class="acciones-col"><button class="btn-icon" title="Eliminar">✕</button></td>
    `;
    tbody.appendChild(fila);
  });
  sumarTotales();
}

/**
 * Procesa el pago (cobrar)
 */
export function procesarPago() {
  var totalTicket = parsearImporte(document.getElementById('total-ticket').value);
  var totalPago = parsearImporte(document.getElementById('modal-total-ticket').value);
  var totalEntregado = parsearImporte(document.getElementById('modal-total-entregado').value);

  let formaPago = document.getElementById('modal-metodo-pago').value;

  if (isNaN(totalTicket) || isNaN(totalPago)) {
    mostrarNotificacion("Por favor, introduce un importe válido.", "error");
    return;
  }

  // Si es tarjeta, no validamos el total entregado
  if (formaPago !== 'T' && totalEntregado < totalPago) {
    mostrarNotificacion('El total entregado es insuficiente para cubrir el importe a pagar.', "error");
    return;
  }

  // Redondear los importes a 2 decimales para comparación
  totalTicket = redondearImporte(totalTicket);
  totalPago = redondearImporte(totalPago);
  totalEntregado = redondearImporte(totalEntregado);

  // Si es tarjeta, el importe cobrado es el total del ticket
  var importeCobrado = formaPago === 'T' ? totalTicket : totalPago;
  importeCobrado = redondearImporte(importeCobrado);

  // El ticket estará cobrado solo si el importe cobrado es igual al total
  var estadoTicket = importeCobrado === totalTicket ? 'C' : 'P';

  // Si el importe cobrado es diferente al total, la forma de pago es '?'
  if (importeCobrado !== totalTicket) {
    formaPago = '?';
  }

  console.log('Datos de pago:', {
    totalTicket,
    totalPago,
    totalEntregado,
    importeCobrado,
    estadoTicket,
    formaPago
  });

  // Primero cerramos el modal para mejorar la UX y evitar bloqueos visuales
  cerrarModalPagos();
  // Luego realizamos la llamada de guardado
  guardarTicket(formaPago, importeCobrado, totalTicket, estadoTicket);
}

/**
 * Inicializa un ticket nuevo, pidiéndole al servidor un numerador
 */
export async function inicializarNuevoTicket() {
  try {
    const response = await fetch(`http://${IP_SERVER}:${PORT}/api/tickets/obtener_numerador/T`);
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || 'Error al obtener el numerador.');
    }
    const data = await response.json();
    if (data.numerador) {
      const numeroTicket = data.numerador;

      const fecha = new Date();
      const anioCorto = fecha.getFullYear().toString().slice(-2);
      const numeroPadded = numeroTicket.toString().padStart(4, '0');
      const numeracion = `T${anioCorto}${numeroPadded}`;

      window.ticketFormaPago = 'E';

      const dia = fecha.getDate().toString().padStart(2, '0');
      const mes = (fecha.getMonth() + 1).toString().padStart(2, '0');
      const anio = fecha.getFullYear();
      document.getElementById('fecha-ticket').value = `${dia}/${mes}/${anio}`;
      document.getElementById('numero-ticket').value= numeracion;

      document.getElementById('cabecera-ticket').style.display      = 'block';
      document.getElementById('form-detalle-ticket').style.display  = 'block';
      document.getElementById('detalle-ticket-grid').style.display  = 'block';
      document.getElementById('guardar-ticket-boton').style.display = 'block';
      document.getElementById('btn-imprimir-ticket').style.display  = 'none';

      document.getElementById('busqueda-producto').focus();
    } else {
      mostrarNotificacion("No se encontró el numerador.", "error");
    }
  } catch (error) {
    console.error("Error al cargar el numerador:", error);
    mostrarNotificacion("Error al cargar el numerador: " + error.message, "error");
  }
}

// Hacer global la función procesarPago
window.procesarPago = procesarPago;

// Hacer global la función calcularCambio
window.calcularCambio = calcularCambio;

// Hacer global la función cerrarModalPagos
window.cerrarModalPagos = cerrarModalPagos;
