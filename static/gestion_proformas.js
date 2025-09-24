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
  getEstadoFormateado,
  getCodigoEstado,
  formatearFechaSoloDia,
  convertirFechaParaAPI,
  formatearFecha
} from './scripts_utils.js';
import { 
    calcularTotalProforma,
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
let idProforma = null;
let idContacto = null;
let productosOriginales = [];
let detalleEnEdicion = null;

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
    mostrarNotificacion('Error al eliminar el detalle', 'error');
  }
}

// Sobrescribimos la función cargarProductos para mantener nuestra propia lista de productos
async function cargarProductos() {
  productosOriginales = await cargarProductosCommon();
  actualizarSelectProductos(productosOriginales, document.getElementById('concepto-detalle'));
}

async function seleccionarProducto() {
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

  // Obtener el tipo de proforma del formulario
  const formulario = document.getElementById('proforma-form');
  const tipoProforma = formulario ? formulario.dataset.tipoProforma : null;

  console.log('Tipo de proforma detectado:', tipoProforma);

  // Establecer cantidad por defecto antes de llamar a seleccionarProductoCommon
  if (formElements.cantidadDetalle) {
    formElements.cantidadDetalle.value = 1;
  }

  if (tipoProforma === 'A') {
    // Para proformas tipo A, usar el precio original sin descuentos
    console.log('Proforma tipo A: NO se aplican descuentos por franja');
    await seleccionarProductoCommon(formElements, productosOriginales, 'proforma');
  } else {
    // Comportamiento normal para otros tipos de proformas
    console.log('Usando manejo normal CON descuentos por franja');
    await seleccionarProductoCommon(formElements, productosOriginales);
  }

   // Si es producto libre, hacer editable el campo total
   const productoId = formElements.conceptoDetalle.value;
   if (productoId === PRODUCTO_ID_LIBRE) {
     formElements.totalDetalle.readOnly = false;
     formElements.totalDetalle.classList.remove('readonly-field');
   } else {
     formElements.totalDetalle.readOnly = true;
     formElements.totalDetalle.classList.add('readonly-field');
   }
}

// Nueva función para manejar productos sin aplicar descuentos por franja
function manejarProductoSinDescuentos(formElements) {
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
  
  // Usar el precio original sin aplicar descuentos por franja
  precioDetalle.value = Number(precioOriginal).toFixed(5).replace('.', ',');
  impuestoDetalle.value = 21;

  // Configurar el campo de impuesto como readonly
  impuestoDetalle.readOnly = true;
  impuestoDetalle.style.backgroundColor = '#e9ecef';

  // Calcular el total sin descuentos
  const cantidad = parseFloat(cantidadDetalle.value) || 0;
  const subtotal = precioOriginal * cantidad;
  const total = subtotal * (1 + (parseFloat(impuestoDetalle.value) || 0) / 100);
  totalDetalle.value = total.toFixed(2).replace('.', ',');

  // Primero removemos todos los event listeners anteriores
  precioDetalle.removeEventListener('input', calcularTotalDetalle);
  cantidadDetalle.removeEventListener('input', calcularTotalDetalle);
  totalDetalle.removeEventListener('input', calcularTotalDetalle);

  // Agregar listener para cantidad que usa el sistema de franjas
  cantidadDetalle.addEventListener('input', calcularTotalDetalle);

  if (productoId === PRODUCTO_ID_LIBRE) {
    // Para productos libres, permitir edición del precio
    precioDetalle.readOnly = false;
    precioDetalle.style.backgroundColor = '';
    totalDetalle.readOnly = false;
    totalDetalle.style.backgroundColor = '';

    // Agregar listeners para productos libres
    precioDetalle.addEventListener('input', calcularTotalDetalle);
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
    // Para productos normales
    precioDetalle.readOnly = true;
    precioDetalle.style.backgroundColor = '#e9ecef';
    
    // Ocultar campo de concepto libre si existe
    if (conceptoInput) {
      conceptoInput.style.display = 'none';
    }
  }
}

function actualizarTotales() {
    console.log('------- INICIO actualizarTotales PROFORMA UNIFICADO -------');
    
    // USAR FUNCIÓN UNIFICADA para garantizar consistencia absoluta
    const total = calcularTotalProforma(detalles);
    
    console.log(`TOTAL PROFORMA FINAL (UNIFICADO): ${total}`);
    
    document.getElementById('total-proforma').value = formatearImporte(total);
    console.log('------- FIN actualizarTotales PROFORMA UNIFICADO -------');
}

function calcularTotalDetallesDiaActual() {
    let importe_bruto = 0;
    let importe_impuestos = 0;
    let total = 0;

    // Obtener el ID del día actual
    const fecha = new Date();
    const idHoy = `${fecha.getDate().toString().padStart(2, '0')}${(fecha.getMonth() + 1).toString().padStart(2, '0')}`;

    // Solo sumar detalles que coincidan con el ID del día actual
    detalles.forEach(detalle => {
        if (detalle.detalleId === idHoy) {
            const subtotal = parseFloat(detalle.precio) * parseInt(detalle.cantidad);
            const impuesto = redondearImporte(subtotal * (parseFloat(detalle.impuestos) / 100));
            
            importe_bruto += subtotal;
            importe_impuestos += impuesto;
        }
    });

    importe_bruto = redondearImporte(importe_bruto);
    importe_impuestos = redondearImporte(importe_impuestos);
    return redondearImporte(importe_bruto + importe_impuestos);
}

function actualizarTablaDetalles() {
    console.log('Ejecutando actualizarTablaDetalles...');
    console.log('Detalles disponibles:', JSON.stringify(detalles));
    
    const tbody = document.querySelector('#tabla-detalle-proforma tbody');
    if (!tbody) {
        console.error('No se encontró la tabla de detalles');
        return;
    }

    tbody.innerHTML = '';
    
    if (!detalles || detalles.length === 0) {
        console.warn('No hay detalles para mostrar');
        return;
    }
    
    detalles.forEach((detalle, index) => {
        const tr = document.createElement('tr');
        // Formatear el precio con máximo 5 decimales y el total con 2
        const precioFormateado = formatearImporteVariable(Number(detalle.precio), 0, 5);

        detalle.total = parseFloat(detalle.total);     
        const totalFormateado = formatearImporte(detalle.total);

        // Limpiar y normalizar el valor de formaPago
        const formaPago = (detalle.formaPago || '').trim();
        
        let formaPagoTexto;
        switch(formaPago) {
            case 'T':
                formaPagoTexto = 'Tarjeta';
                break;
            case 'E':
                formaPagoTexto = 'Efectivo';
                break;
            case 'R':
                formaPagoTexto = 'Transferencia';
                break;
            default:
                formaPagoTexto = '?';
        }
        
        tr.innerHTML = `
            <td style="width: 300px;">${detalle.concepto}</td>
            <td style="width: 200px;">${detalle.descripcion}</td>
            <td style="width: 80px; text-align: right;">${detalle.cantidad}</td>
            <td style="width: 100px; text-align: right;">${precioFormateado}</td>
            <td style="width: 80px; text-align: right;">${detalle.impuestos}%</td>
            <td style="width: 100px; text-align: right;">${totalFormateado}</td>
            <td style="width: 80px; text-align: center;">${formaPagoTexto}</td>
            <td class="acciones-col" style="width: 40px; text-align: center;"><button class="btn-icon" title="Eliminar">✕</button></td>
        `;
        tr.dataset.index = index;
        tbody.appendChild(tr);
    });

    actualizarTotales();
}

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

function validarYAgregarDetalle() {

  const select = document.getElementById('concepto-detalle');
  const productoId = select.value;
  let productoSeleccionado = productoId === PRODUCTO_ID_LIBRE 
    ? document.getElementById('descripcion-detalle').value.trim()
    : select.options[select.selectedIndex].textContent;
  let descripcion = document.getElementById('descripcion-detalle').value.trim();
  const cantidad = parseFloat(document.getElementById('cantidad-detalle').value);
  let precioOriginal = parseFloat(select.options[select.selectedIndex].dataset.precioOriginal) || 0;
  let precioDetalle = parseFloat(document.getElementById('precio-detalle').value);

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

  const impuestos = parseFloat(document.getElementById('impuesto-detalle').value) || 0;
  const total = parseFloat(document.getElementById('total-detalle').value) || 0;

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
    precio: Number(precioDetalle).toFixed(5),  // Asegurar 5 decimales
    impuestos: impuestos,
    total: Number(total).toFixed(2),  // Total con 2 decimales
    formaPago: 'E',
    fechaDetalle: fechaDetalle,
    detalleId: detalleId
  };

  detalles.push(detalle);
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
  
  limpiarCamposDetalle(formElements);
  document.getElementById('busqueda-producto').focus();

  // Mostrar notificación de éxito
  mostrarNotificacion('Detalle agregado correctamente', 'success');
  return true;
}

function inicializarEventDelegation() {
  const tbody = document.querySelector('#tabla-detalle-proforma tbody');
  if (!tbody) {
    console.error('No se encontró la tabla de detalles');
    return;
  }
  
  tbody.addEventListener('click', async function(event) {
    const target = event.target;
    if (target && target.classList.contains('btn-icon')) {
      const fila = target.closest('tr');
      if (fila) {
        const index = parseInt(fila.dataset.index);
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

/**
 * Se ejecuta al cargar el DOM. Inicializa la delegación de eventos en la tabla
 * y maneja la creación o carga de proformas.
 */
document.addEventListener("DOMContentLoaded", async () => {
  try {
    // Establecer el texto de la cabecera
    document.querySelector('.cabecera-ticket').classList.add('cabecera-proforma');

    await cargarProductos();
    inicializarEventDelegation();

    // Asociar eventos
    const btnCancelar = document.getElementById("btnCancelar");
    if (btnCancelar) {
      btnCancelar.addEventListener('click', volverSegunOrigen);
    }

    // Botón "Guardar"
    const btnGuardar = document.getElementById("btnGuardar");
    if (btnGuardar) {
      btnGuardar.removeEventListener('click', guardarProforma);
      btnGuardar.addEventListener('click', () => {
        const totalProforma = parsearImporte(document.getElementById('total-proforma').value);
        const fechaInput = document.getElementById('fecha').value;
        
        // Convertir la fecha al formato DD/MM/AAAA si no está en ese formato
        let fechaFormateada = fechaInput;
        if (fechaInput.includes('-')) {
          const [año, mes, dia] = fechaInput.split('-');
          fechaFormateada = `${dia}/${mes}/${año}`;
        }
        
        abrirModal({
          total: totalProforma,
          fecha: fechaFormateada,
          formaPago: 'E',
          titulo: 'Procesar Pago',
          onCobrar: (formaPago, totalPago, estado) => {
            const importe = (typeof totalPago === 'number') ? totalPago : parsearImporte(totalPago);
            console.log('Total a cobrar (modal):', importe, 'estado:', estado);
            guardarProforma(formaPago, importe, 'A');
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

    // Configurar el campo de impuesto como readonly
    const impuestoDetalle = document.getElementById('impuesto-detalle');
    if (impuestoDetalle) {
      impuestoDetalle.readOnly = true;
      impuestoDetalle.style.backgroundColor = '#e9ecef';
    }

    // Obtener parámetros de la URL
    const urlParams = new URLSearchParams(window.location.search);
    idContacto = urlParams.get('idContacto');
    const origen = urlParams.get('origen');
    
    // Guardar el origen en sessionStorage
    if (origen) {
      sessionStorage.setItem('origenProforma', origen);
    }

    if (idContacto) {
      await buscarProformaAbierta(idContacto);
    } else {
      await inicializarNuevoTicket();
      // Establecer fecha actual solo para proformas nuevas
      const fecha = new Date();
      // Obtener el primer día del mes actual
      const primerDia = new Date(fecha.getFullYear(), fecha.getMonth(), 1);
      
      // Formatear las fechas como DD/MM/YYYY
      const dia = String(primerDia.getDate()).padStart(2, '0');
      const mes = String(primerDia.getMonth() + 1).padStart(2, '0');
      const año = primerDia.getFullYear();
      document.getElementById('fecha').value = `${dia}/${mes}/${año}`;
    }
    
    document.getElementById('busqueda-producto').focus();

    // Event listeners para el modal de pagos
    // Listeners de la modal se inicializan dentro de scripts_utils. No duplicar aquí.

    // Asociar evento al selector de tipo de proforma
    const selectorTipo = document.getElementById('tipo-proforma-select');
    const campoTipoOculto = document.getElementById('tipo-proforma');
    
    if (selectorTipo && campoTipoOculto) {
      selectorTipo.addEventListener('change', function() {
        // Actualizar el campo oculto cuando cambia el selector
        campoTipoOculto.value = selectorTipo.value;
        console.log(`Tipo de proforma cambiado a: ${selectorTipo.value}`);
        
        // Actualizar en sessionStorage para que sea accesible desde scripts_utils.js
        sessionStorage.setItem('tipoProforma', selectorTipo.value);
        
        // Si hay un formulario, actualizar también su atributo de datos
        const formulario = document.getElementById('proforma-form');
        if (formulario) {
          formulario.dataset.tipoProforma = selectorTipo.value;
        }
      });
    }
  } catch (error) {
    console.error("Error durante la inicialización:", error);
  }
});

async function cargarProforma(id) {
  try {
    const response = await fetch(`/api/proformas/consulta/${id}`);
    if (!response.ok) {
      throw new Error(`Error al cargar la proforma: ${response.statusText}`);
    }
    const data = await response.json();
    
    document.getElementById('numero').value = data.numero;
    // Convertir la fecha de YYYY-MM-DD a DD/MM/AAAA
    document.getElementById('fecha').value = formatearFechaSoloDia(data.fecha);
    
    console.log("Datos recibidos de la proforma:", JSON.stringify(data));
    console.log("Campos en data:", Object.keys(data));
    console.log("Tipo según datos:", data.tipo);
    
    // Asegurar que el tipo se procese correctamente
    let tipoProforma = 'N'; // Valor por defecto
    
    // Comprobar si el tipo existe explícitamente en los datos
    if (data.hasOwnProperty('tipo')) {
      // Asegurarse de que sea string para comparar correctamente
      let tipoValor = String(data.tipo).trim().toUpperCase();
      
      if (tipoValor === 'A') {
        tipoProforma = 'A';
        console.log("Se detectó explícitamente una proforma tipo A");
      } else {
        console.log(`Tipo detectado (${tipoValor}) diferente de A, tratando como N`);
      }
    } else {
      console.log("Campo tipo no encontrado en los datos, usando valor por defecto N");
    }
    
    // Actualizar el campo oculto
    document.getElementById('tipo-proforma').value = tipoProforma;
    
    // ACTUALIZACIÓN DIRECTA DEL SELECTOR - ENFOQUE ALTERNATIVO
    try {
      const selectTipo = document.getElementById('tipo-proforma-select');
      if (selectTipo) {
        // Seleccionar la opción correcta de manera forzada
        for (let i = 0; i < selectTipo.options.length; i++) {
          if (selectTipo.options[i].value === tipoProforma) {
            selectTipo.selectedIndex = i;
            console.log(`Selector de tipo actualizado correctamente a índice ${i} (valor: ${tipoProforma})`);
            break;
          }
        }
        
        // Guardar en sessionStorage
        sessionStorage.setItem('tipoProforma', tipoProforma);
        
        // Actualizar data-attribute del formulario
        const formulario = document.getElementById('proforma-form');
        if (formulario) {
          formulario.dataset.tipoProforma = tipoProforma;
        }
      } else {
        console.error("Selector de tipo no encontrado en el DOM");
      }
    } catch (error) {
      console.error("Error al actualizar selector de tipo:", error);
    }
    
    // Si existe un campo visible de estado, establecer su valor legible
    const campoEstado = document.getElementById('estado');
    if (campoEstado) {
      // Guardar el valor real en un atributo data para referencia
      campoEstado.dataset.valorReal = data.estado;
      
      // Establecer el texto visible según el tipo
      if (data.estado === 'A') {
        campoEstado.value = 'Abierta';
      } else if (data.estado === 'C') {
        campoEstado.value = 'Cerrada';
      } else {
        campoEstado.value = data.estado; // Valor por defecto si no reconocemos el código
      }
    }
    
    // Guardar en sessionStorage para que scripts_utils.js pueda acceder
    sessionStorage.setItem('tipoProforma', tipoProforma);
    console.log(`Proforma cargada con tipo: ${tipoProforma}, guardado en sessionStorage`);
    
    // Almacenar el tipo de proforma en el formulario para consultarlo al editar detalles
    const formulario = document.getElementById('proforma-form');
    if (formulario) {
      formulario.dataset.tipoProforma = tipoProforma;
    }
    
    document.getElementById('razonSocial').value = data.contacto.razonsocial;
    document.getElementById('identificador').value = data.contacto.identificador;
    document.getElementById('direccion').value = data.contacto.direccion || '';
    document.getElementById('cp').value = data.contacto.cp || '';
    document.getElementById('localidad').value = data.contacto.localidad || '';
    document.getElementById('provincia').value = data.contacto.provincia || '';
    
    detalles = data.detalles;
    actualizarTablaDetalles();
  } catch (error) {
    console.error('Error al cargar la proforma:', error);
    mostrarNotificacion('Error al cargar la proforma', "error");
  }
}

async function buscarProformaAbierta(idContacto) {
    try {
        console.log("Buscando proforma abierta para contacto:", idContacto);
        const response = await fetch(`/api/proforma/abierta/${idContacto}`);
        if (!response.ok) {
            throw new Error(`Error al buscar proforma abierta: ${response.statusText}`);
        }
        const data = await response.json();
        console.log("Respuesta de proforma abierta:", data);

        // Siempre tendremos los datos del contacto
        const contacto = data.contacto;
        document.getElementById('identificador').value = contacto.identificador || '';
        document.getElementById('razonSocial').value = contacto.razonsocial || '';
        document.getElementById('direccion').value = contacto.direccion || '';
        document.getElementById('cp').value = contacto.cp || '';
        document.getElementById('localidad').value = contacto.localidad || '';
        document.getElementById('provincia').value = contacto.provincia || '';

        if (data.modo === 'edicion') {
            console.log("Entrando en modo edición - Proforma existente");
            idProforma = data.id;
            document.getElementById('numero').value = data.numero;
            // Convertir la fecha de YYYY-MM-DD a DD/MM/AAAA
            const fechaFormateada = formatearFechaSoloDia(data.fecha);
            document.getElementById('fecha').value = fechaFormateada;
            document.getElementById('estado').value = data.estado === 'A' ? 'Abierta' : data.estado;
            document.getElementById('total-proforma').value = formatearImporte(data.total);

            // IMPORTANTE: Actualizar el tipo de proforma (tanto el campo oculto como el selector)
            const tipoProforma = data.tipo === 'A' ? 'A' : 'N';
            console.log(`Tipo de proforma en modo edición: ${tipoProforma} (original: ${data.tipo})`);
            
            // Actualizar campo oculto
            const campoTipoOculto = document.getElementById('tipo-proforma');
            if (campoTipoOculto) {
                campoTipoOculto.value = tipoProforma;
                console.log(`Campo oculto actualizado a: ${tipoProforma}`);
            }
            
            // Actualizar selector visible
            const selectorTipo = document.getElementById('tipo-proforma-select');
            if (selectorTipo) {
                for (let i = 0; i < selectorTipo.options.length; i++) {
                    if (selectorTipo.options[i].value === tipoProforma) {
                        selectorTipo.selectedIndex = i;
                        console.log(`Selector actualizado a índice ${i} (valor: ${tipoProforma})`);
                        break;
                    }
                }
            }
            
            // Guardar en sessionStorage para scripts_utils.js
            sessionStorage.setItem('tipoProforma', tipoProforma);

            // Cargar detalles si existen
            if (data.detalles && Array.isArray(data.detalles)) {
                console.log("Cargando detalles:", data.detalles);
                detalles = data.detalles.map(d => ({
                    id: d.id,
                    concepto: d.concepto,
                    descripcion: d.descripcion || '',
                    cantidad: d.cantidad,
                    precio: d.precio,
                    impuestos: d.impuestos,
                    total: d.total,
                    productoId: d.productoId,
                    formaPago: d.formaPago,
                    fechaDetalle: d.fechaDetalle
                }));
                actualizarTablaDetalles();
            } else {
                console.log("No hay detalles para cargar");
                detalles = [];
                actualizarTablaDetalles();
            }
        } else {
            console.log("Creando nueva proforma");
            try {
                const numResponse = await fetch('/api/proforma/numero');
                if (!numResponse.ok) {
                    throw new Error('Error al obtener el número de proforma');
                }

                
                const numData = await numResponse.json();
                const fecha = new Date();
                const año = fecha.getFullYear().toString().slice(-2);
                let numeroPadded = numData.numerador.toString().padStart(4, '0');
                let numeracion = `P${año}${numeroPadded}`;

                // Establecer la fecha actual en formato DD/MM/AAAA
                const dia = String(fecha.getDate()).padStart(2, '0');
                const mes = String(fecha.getMonth() + 1).padStart(2, '0');
                const añoCompleto = fecha.getFullYear();
                document.getElementById('fecha').value = `${dia}/${mes}/${añoCompleto}`;
                document.getElementById('numero').value = numeracion;
                document.getElementById('estado').value = 'Abierta';
                document.getElementById('total-proforma').value = '0,00';
                detalles = [];
                actualizarTablaDetalles();
            } catch (error) {
                console.error('Error al obtener número de proforma:', error);
                mostrarNotificacion('Error al obtener número de proforma', "error");
                return;
            }
        }
    } catch (error) {
        console.error('Error al buscar proforma abierta:', error);
        mostrarNotificacion('Error al buscar proforma abierta', "error");
    }
}

async function cargarDatosContacto(id) {
  try {
    const response = await fetch(`/api/contactos/get_contacto/${id}`);
    const contacto = await response.json();
    document.getElementById('razonSocial').value = contacto.razonsocial;
    document.getElementById('identificador').value = contacto.identificador;
    document.getElementById('direccion').value = contacto.direccion || '';
    document.getElementById('cp').value = contacto.cp || '';
    document.getElementById('poblacion').value = contacto.poblacion || '';
    document.getElementById('provincia').value = contacto.provincia || '';
  } catch (error) {
    console.error('Error al cargar datos del contacto:', error);
    mostrarNotificacion('Error al cargar datos del contacto', "error");
  }
}

/**
 * Abre el modal de pagos para proformas
 */
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
      // Usar el total de detalles del día actual como importe cobrado
      const importeCobrado = totalDiaActual;
      console.log('Importe a cobrar:', importeCobrado);
      guardarProforma(formaPago, importeCobrado);
    }
  });
}

async function procesarPago() {
  const totalProforma = parseFloat(formatearApunto(document.getElementById('total-proforma').value));
  const totalEntregado = parseFloat(document.getElementById('modal-total-entregado').value.replace(',', '.'));
  const modalTotal = parseFloat(document.getElementById('modal-total-ticket').value.replace(',', '.'));
  let formaPago = document.getElementById('modal-metodo-pago').value;

  // Si es tarjeta, el pago es por el total de la proforma
  if (formaPago === 'T') {
    console.log('Pago con tarjeta, importe:', totalProforma);
    await guardarProforma(formaPago, totalProforma, 'A');
    cerrarModalPagos();
    return;
  }

  // Si es efectivo, validar el total entregado
  if (isNaN(totalEntregado) || totalEntregado <= 0) {
    mostrarNotificacion("Por favor, introduce un importe entregado válido", "warning");
    return;
  }

  if (totalEntregado < modalTotal) {
    mostrarNotificacion('El total entregado es insuficiente para cubrir el importe a pagar', "warning");
    return;
  }

  // Para efectivo, usar el total del modal como importe cobrado
  console.log('Pago en efectivo, importe modal:', modalTotal);
  await guardarProforma(formaPago, modalTotal, 'A');
  cerrarModalPagos();
}

async function guardarProforma(formaPago = 'E', totalPago = 0, estado = 'A') {
    if (detalles.length === 0) {
        mostrarNotificacion("Debe añadir al menos un detalle a la proforma", "warning");
        return;
    }

    // Asegurar que totalPago sea un número válido y mayor que 0
    totalPago = parseFloat(totalPago);
    if (isNaN(totalPago) || totalPago <= 0) {
        console.error('totalPago no es válido:', totalPago);
        mostrarNotificacion("El importe cobrado debe ser mayor que 0", "error");
        return;
    }

    console.log('Guardando proforma con importe cobrado:', totalPago);

    try {
        let numeroProforma = document.getElementById('numero').value;
        const fechaProforma = document.getElementById('fecha').value;
        
        // Asegurarnos de que la fecha esté en formato YYYY-MM-DD para la API
        const fechaAPI = convertirFechaParaAPI(fechaProforma);
        console.log('Fecha original:', fechaProforma);
        console.log('Fecha convertida para API:', fechaAPI);

        if (!fechaAPI) {
            mostrarNotificacion("Error en el formato de fecha", "error");
            return;
        }

        // Solo verificar el número si es una nueva proforma (no tiene idProforma)
        if (!idProforma) {
   
                // Obtener un nuevo número de proforma
                const numResponse = await fetch('/api/proforma/numero');
                if (!numResponse.ok) {
                    throw new Error('Error al obtener nuevo número de proforma');
                }
                const numData = await numResponse.json();
                const fecha = new Date();
                const año = fecha.getFullYear().toString().slice(-2);
                let numeroPadded = numData.numerador.toString().padStart(4, '0');
                let nuevoNumero = `P${año}${numeroPadded}`;
                
                // Actualizar el número en el formulario
                document.getElementById('numero').value = nuevoNumero;
                numeroProforma = nuevoNumero;
                
                console.log('Usando nuevo número de proforma:', nuevoNumero);
            }
        

        // Calcular importes con redondeo
        const importe_bruto = redondearImporte(detalles.reduce((sum, d) => {
            const subtotal = parseFloat(d.precio) * parseInt(d.cantidad);
            return sum + subtotal;
        }, 0));

        const importe_impuestos = redondearImporte(detalles.reduce((sum, d) => {
            const subtotal = parseFloat(d.precio) * parseInt(d.cantidad);
            const impuesto = redondearImporte(subtotal * (parseFloat(d.impuestos) / 100));
            return sum + impuesto;
        }, 0));

        // Calcular el total sumando importe_bruto e importe_impuestos
        const total = redondearImporte(importe_bruto + importe_impuestos);
        
        // Asegurar que totalPago sea un número válido
        totalPago = redondearImporte(String(totalPago).replace(',', '.'));

        // Obtener la fecha actual
        const fechaActual = new Date().toISOString().split('T')[0];

        // Preparar los detalles manteniendo sus IDs si existen
        const detallesBase = detalles.map(detalle => ({
            id: detalle.id || null,  // Mantener el ID si existe
            concepto: detalle.concepto,
            descripcion: detalle.descripcion || '',
            cantidad: parseInt(detalle.cantidad),
            precio: Number(detalle.precio).toFixed(5),
            impuestos: parseFloat(detalle.impuestos),
            total: (() => {
              const sub = parseFloat(detalle.precio) * parseInt(detalle.cantidad);
              const ivaCalc = redondearImporte(sub * (parseFloat(detalle.impuestos) / 100), 2);
              return redondearImporte(sub + ivaCalc);
            })(),
            formaPago: detalle.id ? detalle.formaPago : formaPago,  // Mantener formaPago original si es detalle existente
            fechaDetalle: detalle.fechaDetalle || fechaAPI
        }));

        // Crear la proforma
        const proforma = {
            id: idProforma,
            numero: numeroProforma,
            fecha: fechaAPI,
            idContacto: idContacto,
            nif: document.getElementById('identificador').value,
            detalles: detallesBase,
            total: total,
            formaPago: formaPago,
            importe_bruto: importe_bruto,
            importe_impuestos: importe_impuestos,
            importe_cobrado: totalPago,
            estado: 'A', // Siempre 'A'
            tipo: document.getElementById('tipo-proforma').value, // Obtener valor del campo oculto
            timestamp: new Date().toISOString()
        };

        console.log('Enviando proforma:', proforma);

        // Guardar la proforma
        const url = idProforma 
            ? '/api/proformas/actualizar'
            : '/api/proformas';

        const response = await fetch(url, {
            method: idProforma ? 'PATCH' : 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            body: JSON.stringify(proforma)
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || 'Error al guardar la proforma');
        }
        
        const result = await response.json();
        if (!result.id) {
            throw new Error(result.error || 'Error al guardar la proforma');
        }

        // Mostrar notificación y esperar antes de redirigir
        mostrarNotificacion('Proforma guardada correctamente', 'success');
        setTimeout(() => {
            volverSegunOrigen();
        }, 1000);
    } catch (error) {
        console.error('Error al guardar la proforma:', error);
        mostrarNotificacion(error.message || 'Error al guardar la proforma', "error");
    }
}

function cargarDetalleParaEditar(fila) {
  const index = fila.dataset.index;
  const detalle = detalles[index];
  if (!detalle) return;

  // Al editar, siempre usar la fecha actual
  detalleEnEdicion = {
    fechaDetalle: new Date().toISOString().split('T')[0],
    formaPago: detalle.formaPago // Mantener la forma de pago original por ahora
  };

  // Eliminar el detalle actual (será reemplazado al guardar)
  detalles.splice(index, 1);
  actualizarTablaDetalles();

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

  // Primero seleccionamos el producto para que se configuren los campos correctamente
  seleccionarProductoCommon(formElements, productosOriginales);

  // Luego actualizamos con los valores del detalle
  formElements.descripcionDetalle.value = detalle.descripcion.toUpperCase();
  formElements.cantidadDetalle.value = detalle.cantidad;
  formElements.impuestoDetalle.value = detalle.impuestos;
  formElements.precioDetalle.value = Number(detalle.precio).toFixed(5); // Mantener 5 decimales en el precio
  formElements.totalDetalle.value = Number(detalle.total).toFixed(2);   // Total con 2 decimales

  if (detalle.productoId === PRODUCTO_ID_LIBRE) {
    formElements.conceptoInput.value = detalle.concepto;
    formElements.conceptoInput.style.display = 'block';

    // Configurar campos para edición libre
    formElements.precioDetalle.readOnly = false;
    formElements.precioDetalle.style.backgroundColor = '';
    formElements.totalDetalle.readOnly = false;
    formElements.totalDetalle.style.backgroundColor = '';

    if (!formElements.conceptoInput.dataset.listenerAdded) {
      formElements.conceptoInput.addEventListener('input', filtrarProductos);
      formElements.conceptoInput.dataset.listenerAdded = true;
    }
  }

  calcularTotalDetalle();
}

async function inicializarNuevoTicket() {
    try {
        const response = await fetch('/api/proforma/numero');
        if (!response.ok) {
            throw new Error('Error al obtener el número de proforma');
        }

        const cabeceraTicket = document.querySelector('.cabecera-ticket');

        // Cambiar el valor de la variable CSS --cabecera-texto a 'PROFORMA'
        cabeceraTicket.classList.add('cabecera-proforma');

        const data = await response.json();
        const fecha = new Date();
        const año = fecha.getFullYear().toString().slice(-2);
        const numeroPadded = data.numerador.toString().padStart(4, '0');
        const numeracion = `P${año}${numeroPadded}`;
      
        // Establecer la fecha actual en formato DD/MM/AAAA
        const dia = String(fecha.getDate()).padStart(2, '0');
        const mes = String(fecha.getMonth() + 1).padStart(2, '0');
        const añoCompleto = fecha.getFullYear();
        document.getElementById('fecha').value = `${dia}/${mes}/${añoCompleto}`;
        document.getElementById('numero').value = numeracion;
        document.getElementById('estado').value = 'pendiente';
    } catch (error) {
        console.error('Error:', error);
        mostrarNotificacion('Error al inicializar el número de proforma', "error");
    }
}

// Hacer las funciones disponibles globalmente al final del archivo
Object.assign(window, {
    guardarProforma,
    validarYAgregarDetalle,
    seleccionarProducto,
    filtrarProductos,
    cargarDetalleParaEditar,
    cerrarModalPagos: cerrarModal,
    calcularCambio: calcularCambioModal,
    procesarPago,
    eliminarDetalle
});