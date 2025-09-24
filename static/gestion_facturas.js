import { IP_SERVER, PORT } from './constantes.js';
import { 
    PRODUCTO_ID_LIBRE,
    formatearImporte,
    redondearImporte,
    formatearImporteVariable,
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
import { 
    calcularTotalesDocumento, 
    calcularTotalFactura,
    actualizarDetalleConTotal 
} from './calculo_totales_unificado.js';
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
    const [año, mes, dia] = fechaInput.split('-');
    fechaFormateada = `${dia}/${mes}/${año}`;
  }
  
  const formaPago = 'E'; // Por defecto efectivo
  
  abrirModal({
    total: totalPunto,
    fecha: fechaFormateada,
    formaPago: formaPago,
    titulo: 'Procesar Pago',
    onCobrar: (formaPago, totalPago, total) => {
       const importeCobrado = totalDiaActual;
       console.log('Importe a cobrar:', importeCobrado);

       // Asegurar que la factura se guarde con la fecha actual
       const hoyIso = new Date().toISOString().slice(0,10); // YYYY-MM-DD
       const fechaInput = document.getElementById('fecha');
       if(fechaInput && !fechaInput.value){
         fechaInput.value = hoyIso;
       }
       const fvencInput = document.getElementById('fvencimiento');
       if(fvencInput && !fvencInput.value){
         // Por defecto 15 días después
         const venc = new Date();
         venc.setDate(venc.getDate()+15);
         fvencInput.value = venc.toISOString().slice(0,10);
       }
       // Cerrar el modal antes de realizar la petición
       cerrarModal();
       guardarFactura(formaPago, importeCobrado, 'C');
    }
  });
}


function calcularTotalDetallesDiaActual() {
  let importe_bruto = 0;
  let importe_impuestos = 0;

  // Solo sumar detalles que coincidan con el ID del día actual
  detalles.forEach(detalle => {
     
          const precio = parsearImporte(detalle.precio);
          const cantidad = parsearImporte(detalle.cantidad);
          const iva = parsearImporte(detalle.impuestos);
          const subtotal = precio * cantidad;
          const impuesto = redondearImporte(subtotal * (iva / 100));
          
          importe_bruto += subtotal;
          importe_impuestos += impuesto;
  });

  importe_bruto = redondearImporte(importe_bruto);
  importe_impuestos = redondearImporte(importe_impuestos);
  return redondearImporte(importe_bruto + importe_impuestos);
}

async function guardarFactura(formaPago = 'E', totalPago = 0, estado = 'C') {
    console.log('Guardar factura con botón:', botonUsandose);
    
    // Si se está usando el botón Guardar, forzar estado P e importe 0
    if (botonUsandose === 'btnGuardar') {
        console.log('Forzando estado Pendiente e importe 0');
        estado = 'P';
        totalPago = 0;
    }
    
    if (detalles.length === 0) {
        mostrarNotificacion("Debe añadir al menos un detalle a la factura", "warning");
        return;
    }

    const razonSocial = document.getElementById('razonSocial').value;
    if (!razonSocial) {
        mostrarNotificacion("Debe seleccionar un cliente", "warning");
        return;
    }

    const fecha = document.getElementById('fecha').value;
    if (!fecha) {
        mostrarNotificacion("Debe seleccionar una fecha", "warning");
        return;
    }

    try {
        // Recalcular todos los importes
        const importe_bruto = calcularTotalBruto();
        const importe_impuestos = calcularTotalImpuestos();
        const total = calcularTotalConImpuestos();
        
        // IMPORTANTE: Permitir totalPago = 0 cuando estado = 'P'
        let importeCobrado = totalPago;
        
        // Validar el importe solo si no estamos guardando como Pendiente
        if (estado !== 'P') {
            // Si totalPago es 0, usar el total calculado
            if (importeCobrado === 0) {
                importeCobrado = total;
            }
            
            // Validar que totalPago sea un número válido
            importeCobrado = parsearImporte(importeCobrado);
            if (isNaN(importeCobrado) || importeCobrado < 0) {
                console.error('importeCobrado no es válido:', importeCobrado);
                mostrarNotificacion("El importe debe ser mayor o igual que 0", "error");
                return;
            }
        }
        
        // Preparar los detalles manteniendo sus IDs si existen
        const detallesBase = detalles.map(d => ({
            id: d.id || null,  // Mantener el ID si existe
            concepto: d.concepto,
            descripcion: d.descripcion || '',
            cantidad: parsearImporte(d.cantidad),
            precio: parsearImporte(d.precio).toFixed(5),
            impuestos: parsearImporte(d.impuestos),
            total: (() => {
              const sub = parsearImporte(d.precio) * parsearImporte(d.cantidad);
              const ivaCalc = redondearImporte(sub * (parsearImporte(d.impuestos) / 100));
              return redondearImporte(sub + ivaCalc);
            })(),
            productoId: d.productoId,
            formaPago: d.formaPago,
            fechaDetalle: d.fechaDetalle || convertirFechaParaAPI(document.getElementById('fecha').value)
        }));

        // Obtener el estado actual y convertirlo a código si es necesario
        const estadoActual = document.getElementById('estado').value;
        let estadoCodificado;
        
        // Conversión manual del estado legible a código
        switch(estadoActual) {
            case 'Pendiente':
                estadoCodificado = 'P';
                break;
            case 'Cobrada':
                estadoCodificado = 'C';
                break;
            case 'Vencida':
                estadoCodificado = 'V';
                break;
            default:
                estadoCodificado = estadoActual; // Si no coincide con ninguno, usar el valor tal cual
        }
        
        console.log('Estado legible:', estadoActual, 'Estado codificado:', estadoCodificado);
        
        // Crear la factura
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
            ? `/api/facturas/actualizar`
            : `/api/facturas`;

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

// Función para calcular el total bruto - USANDO FUNCIÓN UNIFICADA
function calcularTotalBruto() {
    const totales = calcularTotalesDocumento(detalles);
    return totales.subtotal_total;
}

// Función para calcular el total de impuestos - USANDO FUNCIÓN UNIFICADA
function calcularTotalImpuestos() {
    const totales = calcularTotalesDocumento(detalles);
    return totales.iva_total;
}

// Función para calcular el total con impuestos - USANDO FUNCIÓN UNIFICADA
function calcularTotalConImpuestos() {
    return calcularTotalFactura(detalles);
}

async function eliminarDetalle(index) {
  try {
    const resultado = await mostrarConfirmacion('¿Está seguro de eliminar este detalle?');
    if (resultado) {
      detalles.splice(index, 1);
      actualizarTablaDetalles();
      actualizarTotales();
      mostrarNotificacion('Detalle eliminado correctamente', 'success');
    }
  } catch (error) {
    console.error('Error al eliminar el detalle:', error);
    mostrarNotificacion('Error al eliminar el detalle', 'error');
  }
}

// Sobrescribimos la función cargarProductos para mantener nuestra propia lista de productos
async function cargarProductos() {
  productosOriginales = await cargarProductosCommon();
  actualizarSelectProductos(productosOriginales, document.getElementById('concepto-detalle'));
}

async function seleccionarProducto() {
  console.log('Ejecutando seleccionarProducto');
  
  // Obtener el tipo de factura actual
  const tipoFactura = document.getElementById('tipo-factura').value || 'N';
  
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
  
  // Establecer cantidad por defecto antes de llamar a seleccionarProductoCommon
  if (formElements.cantidadDetalle) {
    formElements.cantidadDetalle.value = 1;
  }
  
  await seleccionarProductoCommon(formElements, productosOriginales, 'factura');
  
  // Si es producto libre, hacer editable el campo total
  const productoId = formElements.conceptoDetalle.value;
  console.log('Producto seleccionado ID:', productoId);
  
  // Buscar el producto en la lista
  const producto = productosOriginales.find(p => p.id == productoId);
  console.log('Datos del producto:', producto);
  
  if (productoId === PRODUCTO_ID_LIBRE) {
    // Hacer editables todos los campos para producto LIBRE
    formElements.totalDetalle.readOnly = false;
    formElements.totalDetalle.classList.remove('readonly-field');
    formElements.totalDetalle.style.backgroundColor = '';
    
    formElements.impuestoDetalle.readOnly = false;
    formElements.impuestoDetalle.classList.remove('readonly-field');
    formElements.impuestoDetalle.style.backgroundColor = '';
    formElements.impuestoDetalle.placeholder = '';
    
    formElements.precioDetalle.readOnly = false;
    formElements.precioDetalle.classList.remove('readonly-field');
    formElements.precioDetalle.style.backgroundColor = '';
    
    // Para producto LIBRE, usar el IVA del detalle en edición si existe
    if (detalleEnEdicion && detalleEnEdicion.productoId === PRODUCTO_ID_LIBRE) {
      // Si es 0, mostrar campo vacío
      formElements.impuestoDetalle.value = detalleEnEdicion.impuestos === 0 ? '' : detalleEnEdicion.impuestos;
      console.log('Configurando IVA de producto LIBRE en edición:', formElements.impuestoDetalle.value);
    } else {
      // Para nuevos productos LIBRE, establecer 21 por defecto
      formElements.impuestoDetalle.value = 21;
      console.log('Valor por defecto IVA para nuevo producto LIBRE: 21%');
    }
    
    console.log('Configurado como producto LIBRE, campos editables', formElements.impuestoDetalle.value);
  } else {
    // Para productos normales, todos los campos son no editables
    formElements.totalDetalle.readOnly = true;
    formElements.totalDetalle.classList.add('readonly-field');
    formElements.totalDetalle.style.backgroundColor = '#e9ecef';
    
    formElements.impuestoDetalle.readOnly = true;
    formElements.impuestoDetalle.classList.add('readonly-field');
    formElements.impuestoDetalle.style.backgroundColor = '#e9ecef';
    formElements.impuestoDetalle.placeholder = '';
    
    formElements.precioDetalle.readOnly = true;
    formElements.precioDetalle.classList.add('readonly-field');
    formElements.precioDetalle.style.backgroundColor = '#e9ecef';
    
    // Siempre establecer el IVA a 21% para productos no LIBRE
    formElements.impuestoDetalle.value = 21;
    console.log('Configurado como producto estándar, campos no editables, IVA fijo: 21%');
  }
  
  // Usar el sistema de franjas unificado
  await calcularTotalDetalle();
}

function actualizarTotales() {
    console.log('------- INICIO actualizarTotales UNIFICADO -------');
    
    // USAR FUNCIÓN UNIFICADA para garantizar consistencia absoluta
    const total_factura = calcularTotalFactura(detalles);
    
    console.log(`TOTAL FACTURA FINAL (UNIFICADO): ${total_factura}`);
    
    // Actualizar el campo del total
    document.getElementById('total-proforma').value = formatearImporte(total_factura);
    console.log('------- FIN actualizarTotales UNIFICADO -------');
}

function actualizarTablaDetalles() {
    console.log('------- INICIO actualizarTablaDetalles -------');
    console.log('Detalles a mostrar:', JSON.parse(JSON.stringify(detalles)));
    
    const tbody = document.querySelector('table#tabla-detalle-proforma tbody');
    if (!tbody) {
        console.error('No se encontró la tabla de detalles');
        return;
    }

    tbody.innerHTML = '';
    detalles.forEach((detalle, index) => {
        const tr = document.createElement('tr');
        
        // USAR FUNCIÓN UNIFICADA para recalcular el total correctamente
        const detalleActualizado = actualizarDetalleConTotal(detalle);
        detalle.total = detalleActualizado.total;
        
        // Asegurar que todos los valores numéricos son realmente números
        const cantidad = parsearImporte(detalle.cantidad) || 0;
        const precio = parsearImporte(detalle.precio) || 0;
        const impuestos = detalle.impuestos === 0 ? 0 : (parsearImporte(detalle.impuestos) || 21);
        
        // Formatear para mostrar (máximo 5 decimales)
        const precioFormateado = formatearImporteVariable(Number(precio), 0, 5);
        const totalFormateado = formatearImporte(detalle.total);
        
        console.log(`Detalle ${index}: ${detalle.concepto}`);
        console.log(`  Precio: ${precio}, Cantidad: ${cantidad}, IVA: ${impuestos}%`);
        console.log(`  Total recalculado: ${detalle.total}`);

        tr.innerHTML = `
            <td style="width: 300px;">${detalle.concepto}</td>
            <td style="width: 200px;">${detalle.descripcion}</td>
            <td style="width: 80px; text-align: right;">${detalle.cantidad}</td>
            <td style="width: 100px; text-align: right;">${precioFormateado}</td>
            <td style="width: 80px; text-align: right;">${detalle.impuestos}%</td>
            <td style="width: 100px; text-align: right;">${totalFormateado}</td>
            <td class="acciones-col" style="width: 40px; text-align: center;"><button class="btn-icon" title="Eliminar">✕</button></td>
        `;
        tr.dataset.index = index;
        tbody.appendChild(tr);
    });

    // Actualizar totales después de reconstruir la tabla
    console.log('Actualizando totales después de reconstruir tabla');
    actualizarTotales();
    console.log('------- FIN actualizarTablaDetalles -------');
}

function validarYAgregarDetalle() {
  console.log('Ejecutando validarYAgregarDetalle');

  const select = document.getElementById('concepto-detalle');
  const productoId = select.value;
  let productoSeleccionado = productoId === PRODUCTO_ID_LIBRE 
    ? document.getElementById('descripcion-detalle').value.trim()
    : select.options[select.selectedIndex].textContent;
  let descripcion = document.getElementById('descripcion-detalle').value.trim();
  const cantidad = parsearImporte(document.getElementById('cantidad-detalle').value);
  let precioOriginal = parsearImporte(select.options[select.selectedIndex].dataset.precioOriginal) || 0;
  let precioDetalle = parsearImporte(document.getElementById('precio-detalle').value);

  if (productoId === PRODUCTO_ID_LIBRE) {
    precioOriginal = precioDetalle;
    if (!productoSeleccionado) {
      mostrarNotificacion("Debe ingresar un concepto para el producto", "warning");
      return false;
    }
  }

  // Si la descripción está vacía, usar la fecha actual en formato DD/MM/AAAA
  if (!descripcion) {
    const fecha = new Date();
    const dia = fecha.getDate().toString().padStart(2, '0');
    const mes = (fecha.getMonth() + 1).toString().padStart(2, '0');
    const año = fecha.getFullYear();
    descripcion = `${dia}/${mes}/${año}`;
  }

  // Obtener el productoId directamente del formulario
  const productoDetalleElement = document.getElementById('concepto-detalle'); 
  if (!productoDetalleElement) {
    console.error("Error: No se encontró el elemento con ID 'concepto-detalle'");
    mostrarNotificacion("Error al procesar el formulario. Contacte al administrador.", "error");
    return false;
  }
  
  const productoIdSeleccionado = parseInt(productoDetalleElement.value) || 0;
  
  console.log("DEBUG - Valores de comparación:");
  console.log("productoIdSeleccionado:", productoIdSeleccionado, "tipo:", typeof productoIdSeleccionado);
  console.log("PRODUCTO_ID_LIBRE:", PRODUCTO_ID_LIBRE, "tipo:", typeof PRODUCTO_ID_LIBRE);
  
  // Convertir PRODUCTO_ID_LIBRE a número para comparar correctamente
  const PRODUCTO_ID_LIBRE_NUM = parseInt(PRODUCTO_ID_LIBRE);
  console.log("PRODUCTO_ID_LIBRE_NUM:", PRODUCTO_ID_LIBRE_NUM, "tipo:", typeof PRODUCTO_ID_LIBRE_NUM);
  console.log("¿Son iguales ahora?", productoIdSeleccionado === PRODUCTO_ID_LIBRE_NUM);
  
  const impuestoDetalleElement = document.getElementById('impuesto-detalle');
  if (!impuestoDetalleElement) {
    console.error("Error: No se encontró el elemento con ID 'impuesto-detalle'");
    mostrarNotificacion("Error al procesar el formulario. Contacte al administrador.", "error");
    return false;
  }
  
  const ivaInput = impuestoDetalleElement.value.trim();
  console.log("IVA input:", ivaInput, "tipo:", typeof ivaInput);
  
  // Calcular impuestos basado en el tipo de producto
  let impuestos = 21; // Valor por defecto
  
  // Usar la versión numérica para comparar
  if (productoIdSeleccionado === PRODUCTO_ID_LIBRE_NUM) {
    console.log("Es producto LIBRE");
    // Si el campo está vacío, usar explícitamente 0 para IVA
    if (ivaInput === '') {
      console.log("Campo IVA vacío para producto LIBRE, estableciendo 0%");
      impuestos = 0;
    } else {
      impuestos = parsearImporte(ivaInput) || 0;
    }
  }
  
  console.log("Impuestos calculados:", impuestos);
  
  const subtotal = cantidad * precioDetalle;
  // Redondear IVA (base * porcentaje) a 2 decimales antes de sumar (como en tickets)
  const impuestoCalc = Number((subtotal * (impuestos / 100)).toFixed(2));
  const total = Number((subtotal + impuestoCalc).toFixed(2));

  console.log(`Detalle a agregar - Cantidad: ${cantidad}, Precio: ${precioDetalle}, IVA: ${impuestos}%, Total calculado: ${total}`);

  if (total <= 0) {
    mostrarNotificacion("El campo 'Total' es obligatorio y debe ser mayor que 0", "warning");
    return false;
  }
  if (cantidad <= 0) {
    mostrarNotificacion("El campo 'Cantidad' es obligatorio y debe ser mayor que 0", "warning");
    return false;
  }

  // Siempre usar la fecha actual para detalles nuevos y editados
  const fechaDetalle = new Date().toISOString().split('T')[0];
  
  // Generar ID basado en día y mes actual
  const fecha = new Date();
  const detalleId = `${fecha.getDate().toString().padStart(2, '0')}${(fecha.getMonth() + 1).toString().padStart(2, '0')}`;
  
  const detalle = {
    productoId: productoId,
    concepto: productoSeleccionado,
    descripcion: descripcion,
    cantidad: cantidad,
    precio: precioDetalle,
    impuestos: impuestos,
    total: total,
    formaPago: detalleEnEdicion ? detalleEnEdicion.formaPago : 'E',
    fechaDetalle: fechaDetalle,
    detalleId: detalleId
  };

  console.log('Detalle antes de agregar:', detalle);
  detalles.push(detalle);
  console.log('Detalles después de agregar:', detalles);
  
  // Reset detalleEnEdicion después de agregar/actualizar
  detalleEnEdicion = null;
  
  // Cambiar el texto del botón de vuelta a "Agregar"
  const btnAgregar = document.getElementById('btn-agregar-detalle');
  if (btnAgregar) {
    btnAgregar.textContent = 'Agregar';
    btnAgregar.classList.remove('editando');
  }
  
  // Actualizar la tabla y recalcular totales
  actualizarTablaDetalles();

  // Limpiar campos usando common.js
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
  
  // Recargar el selector de productos para que ninguno quede seleccionado
  actualizarSelectProductos(productosOriginales, formElements.conceptoDetalle);
  
  // Limpiar los campos del formulario
  limpiarCamposDetalle(formElements);
  
  // Colocar el foco en el campo de búsqueda
  document.getElementById('busqueda-producto').focus();

  // Mostrar notificación de éxito
  mostrarNotificacion('Detalle agregado correctamente', 'success');
  return true;
}

async function inicializarEventDelegation() {
  const tbody = document.querySelector('table#tabla-detalle-proforma tbody');
  if (!tbody) {
    console.error('No se encontró la tabla de detalles');
    return;
  }
  
  tbody.addEventListener('click', async function(event) {
    console.log('Click en tbody', event.target);
    const target = event.target;
    // Si la factura está cobrada, ignorar cualquier click en el grid de detalles
    if (facturaCobrada) {
      event.stopPropagation();
      return;
    }
    
    // Si el click fue en el botón X o en su contenedor
    if (target.classList.contains('btn-icon') || target.closest('.btn-icon')) {
      console.log('Click en botón eliminar');
      const fila = target.closest('tr');
      if (fila) {
        const index = parseInt(fila.dataset.index);
        console.log('Eliminando detalle con índice:', index);
        await eliminarDetalle(index);
      }
      event.stopPropagation();
    } else {
      const fila = target.closest('tr');
      if (fila && !target.classList.contains('columna-eliminar')) {
        cargarDetalleParaEditar(fila);
      }
    }
  });
}

document.addEventListener("DOMContentLoaded", async () => {
  try {
    // Establecer el texto de la cabecera
    document.querySelector('.cabecera-ticket').classList.add('cabecera-factura');

    await cargarProductos();
    inicializarEventDelegation();

    // Obtener parámetros de la URL
    const params = new URLSearchParams(window.location.search);
    idFactura = params.get('idFactura');
    idContacto = params.get('idContacto');

    console.log(`Parámetros obtenidos de la URL: idFactura=${idFactura}, idContacto=${idContacto}`);
   
    if (idFactura && idContacto && idContacto !== 'undefined') {
      // Cargar datos de la factura existente cuando se tienen ambos parámetros
      try {
        console.log(`Buscando factura para contacto ${idContacto} y factura ${idFactura}`);
        await buscarFacturaAbierta(idContacto, idFactura);
      } catch (error) {
        console.error('Error al cargar la factura:', error);
        mostrarNotificacion('Error al cargar la factura', 'error');
      }
    } else if (idFactura) {
      // Si solo tenemos el ID de la factura, primero consultamos el contacto asociado
      try {
        console.log(`Buscando contacto para factura ID: ${idFactura}`);
        // Consultar la tabla factura para obtener el idContacto
        const response = await fetch(`/api/facturas/obtener_contacto/${idFactura}`);
        
        if (!response.ok) {
          throw new Error('No se pudo obtener el contacto asociado a la factura');
        }
        
        const data = await response.json();
        if (data && data.idContacto) {
          idContacto = data.idContacto;
          console.log(`Contacto obtenido: ${idContacto} para factura: ${idFactura}`);
          // Ahora que tenemos ambos IDs, cargar la factura normalmente
          await buscarFacturaAbierta(idContacto, idFactura);
        } else {
          throw new Error('No se encontró el contacto asociado a la factura');
        }
      } catch (error) {
        console.error('Error al cargar el contacto de la factura:', error);
        mostrarNotificacion(error.message, 'error');
      }
    } else if (idContacto && idContacto !== 'undefined') {
      // Nueva factura para un contacto
      try {
        await cargarDatosContacto(idContacto);
        // Obtener nuevo número de factura
        const numResponse = await fetch(`/api/factura/numero`);
        if (!numResponse.ok) {
          throw new Error('Error al obtener el número de factura');
        }
        const numData = await numResponse.json();
        const fecha = new Date();
        const año = fecha.getFullYear().toString().slice(-2);
        const numeroPadded = numData.numerador.toString().padStart(4, '0');
        const numeracion = `F${año}${numeroPadded}`;

        // Establecer la fecha actual en formato DD/MM/AAAA
        const dia = fecha.getDate().toString().padStart(2, '0');
        const mes = (fecha.getMonth() + 1).toString().padStart(2, '0');
        const añoCompleto = fecha.getFullYear();
        document.getElementById('fecha').value = `${dia}/${mes}/${añoCompleto}`;
        document.getElementById('numero').value = numeracion;
        document.getElementById('estado').value = 'Pendiente'; // Estado formateado directamente
        document.getElementById('total-proforma').value = '0,00';
        detalles = [];
        actualizarTablaDetalles();
      } catch (error) {
        console.error('Error al inicializar nueva factura:', error);
        mostrarNotificacion('Error al inicializar nueva factura', 'error');
      }
    }

    // Asociar eventos
    const btnCancelar = document.getElementById("btnCancelar");
    if (btnCancelar) {
      btnCancelar.addEventListener('click', volverSegunOrigen);
    }

    const btnAnular = document.getElementById("btnAnular");
    if (btnAnular) {
       // Mostrar u ocultar según modo y estado
       const enEdicion = facturaData ? facturaData.modo === 'edicion' : true;
       const yaAnulada = facturaData ? facturaData.estado === 'A' : false;
      btnAnular.style.display = enEdicion && !yaAnulada ? 'inline-block' : 'none';
      // Configurar visibilidad del botón Cobrar (solo pendiente en edición)
      const btnCobrarp = document.getElementById("btnCobrarp");
      let pendiente = false;
      let cobrada = false;
      if (btnCobrarp) {
        pendiente = facturaData ? facturaData.estado === 'P' : true;
        cobrada = facturaData ? facturaData.estado === 'C' : false;
        // Actualizar flag global
        facturaCobrada = cobrada;
        // Cambiar el cursor del grid de detalles según estado
        const gridBody = document.querySelector('table#tabla-detalle-proforma tbody');
        if (gridBody) {
          gridBody.style.cursor = cobrada ? 'not-allowed' : 'default';
        }
        btnCobrarp.style.display = enEdicion && pendiente ? 'inline-block' : 'none';
      }
      // Determinar visibilidad
      const anularVisible = enEdicion && !yaAnulada && !pendiente;
      btnAnular.style.display = anularVisible ? 'inline-block' : 'none';
      // Si Anular visible, ocultar Guardar
      const btnGuardarElement = document.getElementById("btnGuardar");
      if (btnGuardarElement) {
        btnGuardarElement.style.display = anularVisible ? 'none' : 'inline-block';
      }
      // Mostrar/ocultar botón Añadir detalle según estado cobradas
      const btnAgregarDetalle = document.getElementById("btn-agregar-detalle");
      if (btnAgregarDetalle) {
        btnAgregarDetalle.style.display = cobrada ? 'none' : 'inline-block';
      }
      // Deshabilitar botones Eliminar cuando factura cobrada
      const botonesEliminar = document.querySelectorAll('.btn-icon');
      botonesEliminar.forEach(btn => {
        btn.disabled = cobrada;
        btn.style.pointerEvents = cobrada ? 'none' : '';
        btn.style.opacity = cobrada ? '0.4' : '';
      });
      // Reiniciar listeners para evitar duplicados
      btnAnular.replaceWith(btnAnular.cloneNode(true));
      const btnAnularActual = document.getElementById("btnAnular");
      btnAnularActual.addEventListener('click', async () => {
        if (!idFactura) {
          mostrarNotificacion('No se puede anular una factura que aún no ha sido guardada', 'warning');
          return;
        }
        const confirmado = await mostrarConfirmacion('¿Está seguro de anular esta factura? Se creará una rectificativa.');
        if (!confirmado) return;
        try {
          const resp = await fetch(`/api/facturas/anular/${idFactura}`, {
            method: 'POST'
          });
          if (!resp.ok) {
            const errData = await resp.json().catch(() => ({}));
            throw new Error(errData.error || 'Error al anular la factura');
          }
          mostrarNotificacion('Factura anulada correctamente', 'success');
          // Opcional: redirigir o refrescar tras unos segundos
          setTimeout(() => volverSegunOrigen(), 2500);
        } catch (e) {
          console.error('Error al anular factura:', e);
          mostrarNotificacion(e.message || 'Error al anular la factura', 'error');
        }
      });
    }

    const btnGuardar = document.getElementById("btnGuardar"); 
    if (btnGuardar) {
      // Limpiar cualquier evento existente
      btnGuardar.replaceWith(btnGuardar.cloneNode(true));
      // Obtener la referencia actualizada
      const btnGuardarActualizado = document.getElementById("btnGuardar");
      btnGuardarActualizado.addEventListener('click', () => {
        // Validaciones básicas antes de abrir el modal
        if (detalles.length === 0) {
          mostrarNotificacion("Debe añadir al menos un detalle a la factura", "warning");
          return;
        }

        const razonSocial = document.getElementById('razonSocial').value;
        if (!razonSocial) {
          mostrarNotificacion("Debe seleccionar un cliente", "warning");
          return;
        }

        const fecha = document.getElementById('fecha').value;
        if (!fecha) {
          mostrarNotificacion("Debe seleccionar una fecha", "warning");
          return;
        }
        
        const totalProforma = parsearImporte(document.getElementById('total-proforma').value);
        const fechaInput = document.getElementById('fecha').value;
        
        // Convertir la fecha al formato DD/MM/AAAA si no está en ese formato
        let fechaFormateada = fechaInput;
        if (fechaInput.includes('-')) {
          const [año, mes, dia] = fechaInput.split('-');
          fechaFormateada = `${dia}/${mes}/${año}`;
        }
        
        // Eliminar el modal existente si hay uno
        const modalExistente = document.getElementById('modal-pagos');
        if (modalExistente) {
          modalExistente.remove();
        }
        
        // Crear un modal con el mismo estilo que el de tickets/proformas
        const modalHTML = `
          <div id="modal-pagos" class="modal">
            <div class="modal-content">
              <div class="modal-header">
                <h3>Guardar Factura como Pendiente</h3>
                <span class="close" id="closeModal">&times;</span>
              </div>
              <div class="modal-body">
                <div class="modal-linea">
                  <div class="modal-campo">
                    <label for="modal-total-ticket">Total (€):</label>
                    <input type="text" 
                           id="modal-total-ticket" 
                           value="${formatearImporte(totalProforma)}" 
                           class="right-aligned readonly-field"
                           readonly />
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
                           value="${fechaFormateada}"
                           class="readonly-field right-aligned"
                           style="width: 140px;"
                           readonly />
                  </div>
                </div>
                <div class="modal-linea" style="background-color: #f8f9fa; padding: 10px; border-radius: 4px; border-left: 4px solid #4caf50;">
                  <div class="modal-campo">
                    <label style="color: #4caf50; font-weight: bold;">Estado:</label>
                    <input type="text" value="Pendiente" class="readonly-field" readonly style="font-weight: bold; color: #4caf50;" />
                  </div>
                  <div class="modal-campo">
                    <label style="color: #4caf50; font-weight: bold;">Importe Cobrado:</label>
                    <input type="text" value="0,00" class="readonly-field right-aligned" readonly style="font-weight: bold; color: #4caf50;" />
                  </div>
                  <div class="modal-campo" style="visibility: hidden;">
                    <!-- Campo invisible para mantener la estructura -->
                    <label>&nbsp;</label>
                    <input type="text" readonly />
                  </div>
                </div>
              </div>
              <div class="modal-footer" style="text-align: center; display: flex; justify-content: center; margin-top: 20px;">
                <button id="btn-guardar-modal" class="btn-principal">Guardar</button>
              </div>
            </div>
          </div>
        `;
        
        // Añadir el modal al DOM
        document.body.insertAdjacentHTML('beforeend', modalHTML);
        
        // Mostrar el modal
        const modal = document.getElementById('modal-pagos');
        modal.style.display = 'block';
        
        // Configurar eventos del modal
        document.getElementById('closeModal').addEventListener('click', () => {
          modal.style.display = 'none';
        });
        
        // Cerrar modal con ESC
        const closeModalOnEsc = (e) => {
          if (e.key === 'Escape') {
            modal.style.display = 'none';
            document.removeEventListener('keydown', closeModalOnEsc);
          }
        };
        document.addEventListener('keydown', closeModalOnEsc);
        
        // Configurar el botón de guardar
        document.getElementById('btn-guardar-modal').addEventListener('click', async () => {
          const formaPago = document.getElementById('modal-metodo-pago').value;
          
          try {
            // Cerrar el modal antes de realizar la petición
            modal.style.display = 'none';
            // Llamar a guardarFactura con estado P e importe 0 explícitamente
            await guardarFactura(formaPago, 0, 'P');
          } catch (error) {
            console.error('Error al guardar factura como pendiente:', error);
            mostrarNotificacion('Error al guardar la factura: ' + error.message, 'error');
          }
        });
      });
    }

    // Botón "Cobrar"
    const btnCobrarp = document.getElementById("btnCobrarp");
    if (btnCobrarp) {
      btnCobrarp.removeEventListener('click', guardarFactura);
      btnCobrarp.addEventListener('click', () => {
        // Validaciones básicas antes de abrir el modal
        if (detalles.length === 0) {
          mostrarNotificacion("Debe añadir al menos un detalle a la factura", "warning");
          return;
        }

        const razonSocial = document.getElementById('razonSocial').value;
        if (!razonSocial) {
          mostrarNotificacion("Debe seleccionar un cliente", "warning");
          return;
        }

        const fecha = document.getElementById('fecha').value;
        if (!fecha) {
          mostrarNotificacion("Debe seleccionar una fecha", "warning");
          return;
        }
        
        // Eliminar cualquier modal existente primero
        const modalExistente = document.getElementById('modal-pagos');
        if (modalExistente) {
          modalExistente.remove();
        }
        
        const totalProforma = parsearImporte(document.getElementById('total-proforma').value) || 0;
        const fechaInput = document.getElementById('fecha').value;
        
        // Convertir la fecha al formato DD/MM/AAAA si no está en ese formato
        let fechaFormateada = fechaInput;
        if (fechaInput.includes('-')) {
          const [año, mes, dia] = fechaInput.split('-');
          fechaFormateada = `${dia}/${mes}/${año}`;
        }
        
        // Crear un modal específico para cobrar con el mismo estilo que el de tickets/proformas
        const modalCobrarHTML = `
  <div id="modal-pagos" class="modal">
    <div class="modal-content">
      <div class="modal-header">
        <h3>Cobrar Factura</h3>
        <span class="close" id="closeModal">&times;</span>
      </div>
      <div class="modal-body">
        <div class="modal-linea">
          <div class="modal-campo">
            <label for="modal-total-ticket">Total (€):</label>
            <input type="text" 
                   id="modal-total-ticket" 
                   value="${formatearImporte(totalProforma)}" 
                   class="right-aligned readonly-field" 
                   readonly />
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
                   value="${fechaFormateada}"
                   class="readonly-field right-aligned"
                   style="width: 140px;"
                   readonly />
          </div>
        </div>
        <div class="modal-linea">
          <div class="modal-campo">
            <label for="modal-total-entregado">Total Entregado (€):</label>
            <input type="text" id="modal-total-entregado" value="${formatearImporte(totalProforma)}" class="right-aligned" />
          </div>
          <div class="modal-campo">
            <label for="modal-cambio">Total Cambio (€):</label>
            <input type="text" id="modal-cambio" value="${formatearImporte(0)}" readonly class="readonly-field right-aligned" />
          </div>
          <div class="modal-campo" style="visibility: hidden;">
            <!-- Campo invisible para mantener la estructura -->
            <label>&nbsp;</label>
            <input type="text" readonly />
          </div>
        </div>
      </div>
      <div class="modal-footer" style="text-align: center; display: flex; justify-content: center; margin-top: 20px;">
        <button id="btn-cobrar-modal" class="btn-principal">Cobrar</button>
      </div>
    </div>
  </div>
`;
        
        // Añadir el modal al DOM
        document.body.insertAdjacentHTML('beforeend', modalCobrarHTML);
        
        // Mostrar el modal
        const modal = document.getElementById('modal-pagos');
        modal.style.display = 'block';
        
        // Configurar eventos del modal
        document.getElementById('closeModal').addEventListener('click', () => {
          modal.style.display = 'none';
        });
        
        // Calcular cambio cuando se modifica el total entregado
        const totalEntregadoInput = document.getElementById('modal-total-entregado');
        if (totalEntregadoInput) {
          totalEntregadoInput.addEventListener('input', () => {
            const totalFactura = parsearImporte(document.getElementById('modal-total-ticket').value) || 0;
            const totalEntregado = parsearImporte(totalEntregadoInput.value) || 0;
            const cambio = totalEntregado - totalFactura;
            document.getElementById('modal-cambio').value = formatearImporte(cambio > 0 ? cambio : 0);
          });
        }
        
        // Cerrar modal con ESC
        const closeModalOnEsc = (e) => {
          if (e.key === 'Escape') {
            modal.style.display = 'none';
            document.removeEventListener('keydown', closeModalOnEsc);
          }
        };
        document.addEventListener('keydown', closeModalOnEsc);
        
        // Configurar el botón de cobrar
        document.getElementById('btn-cobrar-modal').addEventListener('click', async () => {
          const formaPago = document.getElementById('modal-metodo-pago').value;
          const totalEntregado = parsearImporte(document.getElementById('modal-total-entregado').value) || 0;
          const totalFactura = parsearImporte(document.getElementById('modal-total-ticket').value) || 0;
          
          // Validaciones para el cobro
          if (totalEntregado < totalFactura) {
            mostrarNotificacion("El total entregado es insuficiente", "warning");
            return;
          }
          
          try {
            // Cerrar el modal antes de realizar la petición
            modal.style.display = 'none';
            // Llamar a guardarFactura con estado C y el importe completo
            await guardarFactura(formaPago, totalFactura, 'C');
          } catch (error) {
            console.error('Error al cobrar factura:', error);
            mostrarNotificacion('Error al cobrar la factura: ' + error.message, 'error');
          }
        });
      });
    }

    // Input "busqueda-producto" => filtrarProductos
    const busquedaProducto = document.getElementById('busqueda-producto');
    if (busquedaProducto) {
      busquedaProducto.addEventListener('input', () => filtrarProductos());
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

    // Los event listeners se configuran en seleccionarProducto() para evitar duplicados
    
    // Campo impuesto => actualizarTotales cuando cambia (para productos LIBRE)
    const impuestoDetalle = document.getElementById('impuesto-detalle');
    if (impuestoDetalle) {
      impuestoDetalle.readOnly = true;
      impuestoDetalle.style.backgroundColor = '#e9ecef';
      
      // Añadir evento input que actualiza totales cuando cambia el IVA
      impuestoDetalle.addEventListener('input', () => {
        calcularTotalDetalle();
        actualizarTotales();
      });
    }

    // Inicialización para el tipo de factura
    const selectorTipo = document.getElementById('tipo-factura-select');
    const campoTipoOculto = document.getElementById('tipo-factura');

    if (selectorTipo && campoTipoOculto) {
      // Inicializar el selector con el valor del campo oculto
      selectorTipo.value = campoTipoOculto.value;
      console.log('Inicializando selector tipo factura:', selectorTipo.value, 'Valor campo oculto:', campoTipoOculto.value);
      
      // Escuchar cambios en el selector
      selectorTipo.addEventListener('change', function() {
        // Actualizar el campo oculto
        campoTipoOculto.value = this.value;
        console.log('Tipo de factura cambiado a:', this.value, 'Campo oculto actualizado a:', campoTipoOculto.value);
        
        // Si hay algún producto seleccionado, actualizar su precio según el tipo
        const conceptoDetalle = document.getElementById('concepto-detalle');
        if (conceptoDetalle && conceptoDetalle.value && conceptoDetalle.value !== PRODUCTO_ID_LIBRE) {
          console.log('Producto seleccionado, recalculando precios con nuevo tipo:', this.value);
          seleccionarProducto();
        } else {
          // Si no hay producto seleccionado, recalcular los totales con el nuevo tipo
          console.log('No hay producto seleccionado, recalculando totales con nuevo tipo:', this.value);
          calcularTotalDetalle();
          actualizarTotales();
        }
      });
    }

    document.getElementById('busqueda-producto').focus();
  } catch (error) {
    console.error("Error durante la inicialización:", error);
  }
});

/**
 * Busca una factura utilizando solo el ID de la factura. Este endpoint nos permite obtener
 * la información del contacto asociado a la factura para luego cargar los detalles completos.
 * @param {number} idFactura - El ID de la factura a buscar
 */
async function buscarFacturaPorId(idFactura) {
    try {
        console.log(`Ejecutando buscarFacturaPorId para factura ID: ${idFactura}`);
        
        // Asegurar que el parámetro sea válido
        if (!idFactura) {
            throw new Error(`Parámetro incompleto - idFactura: ${idFactura}`);
        }
        
        // Llamar al endpoint para buscar factura por ID
        // Recordar la regla: "en front siempre con prefijo api"
        const response = await fetch(`/api/facturas/consulta/${idFactura}`);
        
        if (!response.ok) {
            throw new Error('Error al obtener la factura por ID');
        }

        const factura = await response.json();
        console.log('Datos de factura obtenidos:', factura);
        
        if (factura && factura.idContacto) {
            // Guardamos el ID del contacto para usarlo en el resto del formulario
            idContacto = factura.idContacto;
            console.log(`ID de contacto obtenido de la factura: ${idContacto}`);
            
            // Ahora que tenemos el contacto, podemos cargar la factura completa
            await buscarFacturaAbierta(idContacto, idFactura);
        } else {
            throw new Error('No se pudo obtener el ID del contacto de la factura');
        }
    } catch (error) {
        console.error('Error en buscarFacturaPorId:', error);
        mostrarNotificacion(`Error al buscar la factura: ${error.message}`, 'error');
        throw error;
    }
}

// Esta función debe mantener el orden de parámetros: idContacto primero, luego idFactura
// para coincidir con el endpoint del backend: @app.route('/factura/abierta/<int:idContacto>/<int:idFactura>')
let facturaData = null; // datos de la factura actual (modo edición)

async function buscarFacturaAbierta(idContacto, idFactura) {
    try {
        console.log(`Buscando factura para contacto ${idContacto} y factura ${idFactura}`);
        // Debug para verificar los parámetros que llegan a la función
        console.log(`buscarFacturaAbierta - idFactura: ${idFactura}, idContacto: ${idContacto}`);
        
        // Asegurar que los parámetros sean válidos
        if (!idFactura || !idContacto) {
            throw new Error(`Parámetros incompletos - idFactura: ${idFactura}, idContacto: ${idContacto}`);
        }
        
        // Mantener el orden correcto de parámetros en la URL: primero idContacto, luego idFactura
        // Recordar la regla: "en front siempre con prefijo api"
        const response = await fetch(`/api/factura/abierta/${idContacto}/${idFactura}`);
        
        if (!response.ok) {
            throw new Error('Error al obtener la factura');
        }

        const factura = await response.json();
        facturaData = factura; // guardar global
        console.log('Factura cargada:', factura);
        
        // Establecer los datos del contacto
        const contacto = factura.contacto;
        console.log('Datos del contacto:', contacto);
        
        if (contacto) {
            document.getElementById('razonSocial').value = contacto.razonsocial || '';
            document.getElementById('identificador').value = contacto.identificador || '';
            document.getElementById('direccion').value = contacto.direccion || '';
            document.getElementById('cp-localidad').textContent = (contacto.cp || '') + (contacto.cp && contacto.localidad ? ' ' : '') + (contacto.localidad || '');
            document.getElementById('provincia').value = contacto.provincia || '';
        } else {
            console.error('No se encontraron datos del contacto en la respuesta');
        }
        
        // Establecer los valores de la factura
        if (factura.modo === 'edicion') {
            document.getElementById('fecha').value = formatearFechaSoloDia(factura.fecha);
            document.getElementById('numero').value = factura.numero;
            
            // Convertir el estado a formato legible usando la función centralizada
            const estadoCodigo = factura.estado || 'P';
            const estadoTexto = getEstadoFormateado(estadoCodigo);
            
            console.log('Estado original:', estadoCodigo, 'Estado formateado:', estadoTexto);
            document.getElementById('estado').value = estadoTexto;
            
            document.getElementById('total-proforma').value = formatearImporte(factura.total || 0);

            // Establecer el tipo de factura (con validación para asegurar que sea string)
            const tipoFactura = typeof factura.tipo === 'string' ? factura.tipo : 
                              (factura.tipo === 1 || factura.tipo === true) ? 'A' : 'N';
            
            console.log('Tipo de factura original:', factura.tipo, 'Tipo convertido:', tipoFactura);
            
            // Actualizar tanto el campo oculto como el selector visible
            document.getElementById('tipo-factura').value = tipoFactura;
            
            const selectorTipo = document.getElementById('tipo-factura-select');
            if (selectorTipo) {
              selectorTipo.value = tipoFactura;
            }
            
            // Cargar detalles si existen
            if (factura.detalles && Array.isArray(factura.detalles)) {
                console.log("Cargando detalles:", factura.detalles);
                detalles = factura.detalles.map(d => ({
                    id: d.id,
                    concepto: d.concepto,
                    descripcion: d.descripcion || '',
                    cantidad: d.cantidad,
                    precio: d.precio,
                    impuestos: d.impuestos,
                    total: d.total,
                    productoId: d.productoId,
                    formaPago: d.formaPago,
                    fechaDetalle: d.fechaDetalle || convertirFechaParaAPI(document.getElementById('fecha').value)
                }));
                actualizarTablaDetalles();
            } else {
                console.log("No hay detalles para cargar");
                detalles = [];
                actualizarTablaDetalles();
            }
        }
    } catch (error) {
        console.error('Error al buscar factura abierta:', error);
        mostrarNotificacion('Error al buscar factura abierta', 'error');
    }
}

async function procesarPago() {
  const formaPago = document.getElementById('modal-metodo-pago').value;
  const totalProforma = parsearImporte(document.getElementById('total-proforma').value);

  if (formaPago === 'T' || formaPago === 'B') {
    console.log('Pago con tarjeta/banco, importe:', totalProforma);
    // Cerrar el modal antes de realizar la petición
    document.getElementById('modalPago').style.display = 'none';
    await guardarFactura(formaPago, totalProforma, 'C');
    return;
  }

  // Validar el total entregado para pagos en efectivo
  const modalTotal = parsearImporte(document.getElementById('modal-total-entregado').value);
  if (isNaN(modalTotal) || modalTotal < totalProforma) {
    mostrarNotificacion("El importe entregado debe ser igual o superior al total de la factura", "warning");
    return;
  }

  // Para efectivo, usar el total del modal como importe cobrado
  console.log('Pago en efectivo, importe modal:', modalTotal);
  // Cerrar el modal antes de realizar la petición
  document.getElementById('modalPago').style.display = 'none';
  await guardarFactura(formaPago, modalTotal, 'C');
}

async function cargarDatosContacto(id) {
  try {
    const response = await fetch(`/api/contactos/get_contacto/${id}`);
    const contacto = await response.json();
    
    // Añadir logs para depuración
    console.log('Datos de contacto recibidos:', contacto);
    console.log('Valor de localidad:', contacto.localidad);
    
    document.getElementById('razonSocial').value = contacto.razonsocial;
    document.getElementById('identificador').value = contacto.identificador;
    document.getElementById('direccion').value = contacto.direccion || '';
    document.getElementById('cp-localidad').textContent = (contacto.cp || '') + (contacto.cp && contacto.localidad ? ' ' : '') + (contacto.localidad || '');
    document.getElementById('provincia').value = contacto.provincia || '';
    
    // Inspeccionar DOM después de asignar valores
    setTimeout(() => {
      console.log('Comprobación DOM actualizado:');
      console.log('Elemento localidad:', document.getElementById('cp-localidad'));
      console.log('Valor actual de localidad:', document.getElementById('cp-localidad').textContent);
      console.log('Estilo computed de localidad:', window.getComputedStyle(document.getElementById('cp-localidad')));
    }, 100);
    
  } catch (error) {
    console.error('Error al cargar datos del contacto:', error);
    mostrarNotificacion('Error al cargar datos del contacto', "error");
  }
}

function cargarDetalleParaEditar(fila) {
  const index = fila.dataset.index;
  const detalle = detalles[index];
  if (!detalle) return;

  console.log('Cargando detalle para editar:', detalle);

  // Copiar completamente el detalle original
  detalleEnEdicion = {
    id: detalle.id,
    productoId: detalle.productoId,
    concepto: detalle.concepto,
    descripcion: detalle.descripcion,
    cantidad: detalle.cantidad,
    precio: detalle.precio,
    impuestos: detalle.impuestos,
    total: detalle.total,
    formaPago: detalle.formaPago,
    fechaDetalle: new Date().toISOString().split('T')[0],  // Siempre usar fecha actual
    detalleId: detalle.detalleId
  };

  console.log('Estado de detalleEnEdicion después de cargar:', JSON.parse(JSON.stringify(detalleEnEdicion)));

  // Eliminar el detalle actual (será reemplazado al guardar)
  detalles.splice(index, 1);
  
  // Primero actualizar la tabla sin el detalle eliminado
  actualizarTablaDetalles();

  // Asegurar que se actualiza el total también mostrando los valores del detalle en edición
  actualizarTotales();

  const selectProducto = document.getElementById('concepto-detalle');
  
  if (detalle.productoId === PRODUCTO_ID_LIBRE) {
    selectProducto.value = PRODUCTO_ID_LIBRE;
  } else {
    selectProducto.value = detalle.productoId;
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

  // Verificar que todos los elementos del formulario existen
  for (const [key, element] of Object.entries(formElements)) {
    if (!element) {
      console.error(`Elemento no encontrado: ${key}`);
      mostrarNotificacion("Error al cargar el formulario. Contacte al administrador.", "error");
      return;
    }
  }

  // Actualizar directamente los valores del detalle
  formElements.descripcionDetalle.value = detalle.descripcion.toUpperCase();
  formElements.cantidadDetalle.value = detalle.cantidad;
  formElements.precioDetalle.value = detalle.precio;
  
  // Manejar el campo de IVA según tipo de producto
  const PRODUCTO_ID_LIBRE_NUM = parseInt(PRODUCTO_ID_LIBRE);
  const productoIdNum = parseInt(detalle.productoId);
  const esLibre = productoIdNum === PRODUCTO_ID_LIBRE_NUM;
  
  console.log("Configurando detalle - Producto ID:", productoIdNum, "Es LIBRE:", esLibre);
  
  // Normalizar el valor de impuestos para productos LIBRE
  if (esLibre) {
    // Si es un producto LIBRE y los impuestos son 0, null, undefined o cadena vacía
    // asegurarnos de que quede como 0 en el modelo de datos
    if (!detalle.impuestos && detalle.impuestos !== 0) {
      console.log("Impuestos no definidos, estableciendo a 0%");
      detalle.impuestos = 0;
      detalleEnEdicion.impuestos = 0;
    } else if (detalle.impuestos === 0) {
      console.log("Impuestos ya son 0");
    } else {
      console.log("Impuestos definidos:", detalle.impuestos);
    }
    
    // Para la UI: mostrar campo vacío si es 0
    formElements.impuestoDetalle.value = detalle.impuestos === 0 ? '' : detalle.impuestos;
    formElements.impuestoDetalle.readOnly = false;
    formElements.impuestoDetalle.classList.remove('readonly-field');
    formElements.impuestoDetalle.placeholder = '';
    
    formElements.precioDetalle.readOnly = false;
    formElements.precioDetalle.classList.remove('readonly-field');
  } else {
    // Configurar campos no editables para productos normales
    formElements.impuestoDetalle.value = detalle.impuestos || 21;
    formElements.impuestoDetalle.readOnly = true;
    formElements.impuestoDetalle.classList.add('readonly-field');
    
    formElements.precioDetalle.readOnly = true;
    formElements.precioDetalle.classList.add('readonly-field');
  }
  
  // Establecer el total directamente desde el detalle original
  formElements.totalDetalle.value = detalle.total;
  
  // Limpiar listeners previos para evitar duplicados
  formElements.cantidadDetalle.removeEventListener('input', calcularTotalDetalle);
  formElements.precioDetalle.removeEventListener('input', calcularTotalDetalle);
  formElements.impuestoDetalle.removeEventListener('input', calcularTotalDetalle);
  
  // Configurar event listeners para recalcular el total cuando cambien los valores
  formElements.cantidadDetalle.addEventListener('input', calcularTotalDetalle);
  formElements.precioDetalle.addEventListener('input', calcularTotalDetalle);
  formElements.impuestoDetalle.addEventListener('input', calcularTotalDetalle);
  
  // Para asegurar que el select tiene el valor correcto del producto
  // Buscamos la opción con el ID correcto y la seleccionamos
  for (let i = 0; i < selectProducto.options.length; i++) {
    if (selectProducto.options[i].value == detalle.productoId) {
      selectProducto.selectedIndex = i;
      break;
    }
  }
  
  // Después de configurar todo, ejecutar un cálculo del total para asegurar que se muestra correctamente
  setTimeout(calcularTotalDetalle, 100);
  
  // Actualizar totales después de reconstruir la tabla
  console.log('Actualizando totales después de reconstruir tabla');
  actualizarTotales();
  console.log('------- FIN actualizarTablaDetalles -------');
  
  // Ajustar el estado visual del botón
  const btnAgregar = document.getElementById('btn-agregar-detalle');
  if (btnAgregar) {
    btnAgregar.textContent = 'Actualizar';
    btnAgregar.classList.add('editando');
  }

  console.log('Formulario configurado para edición');
}

// Función para calcular el cambio
function calcularCambio() {
    const totalElemFactura = document.getElementById('total-factura');
    const totalElemProforma = document.getElementById('total-proforma');
    const totalFactura = totalElemFactura
        ? parsearImporte(totalElemFactura.value)
        : (totalElemProforma ? parsearImporte(totalElemProforma.value) : 0);
    const totalEntregado = parsearImporte(document.getElementById('modal-total-entregado').value) || 0;
    const cambio = calcularCambioModal(totalFactura, totalEntregado);
    document.getElementById('modal-cambio').value = cambio.toFixed(2);
}

// Hacer las funciones disponibles globalmente al final del archivo
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

function actualizarTablaFacturas() {
  
}

// Función para filtrar productos según búsqueda
async function filtrarProductos() {
  const busquedaProducto = document.getElementById('busqueda-producto').value;
  const productosFiltrados = filtrarProductosCommon(busquedaProducto, productosOriginales);
  actualizarSelectProductos(productosFiltrados, document.getElementById('concepto-detalle'));

  if (productosFiltrados.length > 0) {
    const selectProducto = document.getElementById('concepto-detalle');
    selectProducto.value = productosFiltrados[0].id;
    await seleccionarProducto();
  }
}