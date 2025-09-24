import { IP_SERVER, PORT } from './constantes.js';
import { 
  PRODUCTO_ID_LIBRE,
  formatearImporte,
  redondearImporte,
  formatearApunto,
  parsearImporte,
  calcularPrecioConDescuento,
  calcularTotalDetalle,
  debounce,
  abrirModalPagos as abrirModal,
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
import { calcularImportes } from './scripts/calculos.js';

// Variables globales
let detalles = [];
let productosOriginales = [];
let idProforma = null;
let idContacto = null;
let detalleEnEdicion = null;

// Elementos del DOM
const formElements = {
  conceptoDetalle: document.getElementById('concepto-detalle'),
  descripcionDetalle: document.getElementById('descripcion-detalle'),
  cantidadDetalle: document.getElementById('cantidad-detalle'),
  precioDetalle: document.getElementById('precio-detalle'),
  impuestoDetalle: document.getElementById('impuesto-detalle'),
  totalDetalle: document.getElementById('total-detalle'),
  conceptoInput: document.getElementById('concepto-input')
};

/**
 * Carga la lista de productos desde la API
 */
export async function cargarProductos() {
  productosOriginales = await cargarProductosCommon();
  actualizarSelectProductos(productosOriginales, document.getElementById('concepto-detalle'));
}

function seleccionarProducto() {
  // Obtenemos el tipo de proforma del formulario
  const formulario = document.getElementById('proforma-form');
  const tipoProforma = formulario ? formulario.dataset.tipoProforma : null;
  
  console.log('Tipo de proforma detectado:', tipoProforma);
  
  // Si es una proforma tipo 'A', manejamos el producto sin descuentos
  if (tipoProforma === 'A') {
    console.log('Usando manejo SIN descuentos por franja');
    manejarProductoSinDescuentos(formElements);
  } else {
    // Comportamiento normal para otros tipos de proformas
    console.log('Usando manejo normal CON descuentos por franja');
    seleccionarProductoCommon(formElements, productosOriginales);
  }

   // Si es producto libre, hacer editable el campo total
   const productoId = formElements.conceptoDetalle.value;
   if (productoId === PRODUCTO_ID_LIBRE) {
    formElements.totalDetalle.readOnly = false;
    formElements.totalDetalle.style.backgroundColor = '';

    if (!formElements.conceptoInput.dataset.listenerAdded) {
      formElements.conceptoInput.addEventListener('input', filtrarProductos);
      formElements.conceptoInput.dataset.listenerAdded = true;
    }
  }
}

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

async function buscarProformaAbierta(idContacto) {
    try {
        console.log("Buscando proforma abierta para contacto:", idContacto);
        const response = await fetch(`http://${IP_SERVER}:${PORT}/api/proforma/abierta/${idContacto}`);
        if (!response.ok) {
            throw new Error(`Error al buscar proforma abierta: ${response.statusText}`);
        }

        const data = await response.json();
        console.log("Datos de proforma abierta:", data);
        
        if (data && data.id) {
            // Cargar la proforma existente
            await cargarProforma(data.id);
        } else {
            // No hay proforma abierta, inicializar nueva
            await inicializarNuevoTicket();
        }
    } catch (error) {
        console.error("Error al buscar proforma abierta:", error);
        mostrarNotificacion("Error al buscar proforma abierta", "error");
        await inicializarNuevoTicket();
    }
}

async function inicializarNuevoTicket() {
    try {
        // Generar número de proforma
        const response = await fetch(`http://${IP_SERVER}:${PORT}/api/proformas/siguiente_numero`);
        if (!response.ok) {
            throw new Error('Error al obtener el siguiente número');
        }
        
        const data = await response.json();
        const fecha = new Date();
        const año = fecha.getFullYear();
        const numeroPadded = data.numero.toString().padStart(4, '0');
        const numeracion = `P${año}${numeroPadded}`;

        // Establecer valores por defecto
        const dia = fecha.getDate().toString().padStart(2, '0');
        const mes = (fecha.getMonth() + 1).toString().padStart(2, '0');
        const añoCompleto = fecha.getFullYear();
        
        document.getElementById('fecha').value = `${dia}/${mes}/${añoCompleto}`;
        document.getElementById('numero').value = numeracion;
        document.getElementById('estado').value = 'Abierta';
        document.getElementById('total-proforma').value = '0,00';
        
        detalles = [];
        actualizarTablaDetalles();
        
    } catch (error) {
        console.error('Error al inicializar nueva proforma:', error);
        mostrarNotificacion('Error al inicializar nueva proforma', 'error');
    }
}

function validarYAgregarDetalle() {
  const select = document.getElementById('concepto-detalle');
  const productoId = select.value;
  let productoSeleccionado = productoId === PRODUCTO_ID_LIBRE 
    ? document.getElementById('descripcion-detalle').value.trim()
    : select.options[select.selectedIndex].textContent;
  let descripcion = document.getElementById('descripcion-detalle').value.trim();
  const cantidad = parsearImporte(document.getElementById('cantidad-detalle').value);
  const precio = parsearImporte(document.getElementById('precio-detalle').value);
  const impuesto = parsearImporte(document.getElementById('impuesto-detalle').value);
  const total = parsearImporte(document.getElementById('total-detalle').value);

  if (!validarDetalle(productoId, productoSeleccionado, descripcion, cantidad, precio, total)) {
    return;
  }

  const detalle = {
    id: detalleEnEdicion ? detalleEnEdicion.id : Date.now(),
    productoId: productoId,
    producto: productoSeleccionado,
    descripcion: descripcion,
    cantidad: cantidad,
    precio: precio,
    impuesto: impuesto,
    total: total
  };

  if (detalleEnEdicion) {
    const index = detalles.findIndex(d => d.id === detalleEnEdicion.id);
    if (index !== -1) {
      detalles[index] = detalle;
    }
    detalleEnEdicion = null;
  } else {
    detalles.push(detalle);
  }

  actualizarTablaDetalles();
  limpiarCamposDetalle();
  actualizarTotales();
}

function actualizarTablaDetalles() {
    const tbody = document.querySelector('#detalle-proforma-grid tbody');
    if (!tbody) return;

    tbody.innerHTML = '';

    detalles.forEach((detalle, index) => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${detalle.producto}</td>
            <td>${detalle.descripcion}</td>
            <td>${detalle.cantidad}</td>
            <td>${formatearImporte(detalle.precio)}</td>
            <td>${formatearImporte(detalle.impuesto)}</td>
            <td>${formatearImporte(detalle.total)}</td>
            <td>
                <button type="button" class="btn-editar" data-index="${index}">Editar</button>
                <button type="button" class="btn-eliminar" data-index="${index}">Eliminar</button>
            </td>
        `;
        tbody.appendChild(tr);
    });

    actualizarTotales();
}

function actualizarTotales() {
    const totalSinIVA = detalles.reduce((sum, detalle) => sum + detalle.precio * detalle.cantidad, 0);
    const totalIVA = detalles.reduce((sum, detalle) => sum + detalle.impuesto * detalle.cantidad, 0);
    const totalConIVA = totalSinIVA + totalIVA;

    document.getElementById('total-proforma').value = formatearImporte(totalConIVA);
}

document.addEventListener("DOMContentLoaded", async () => {
  try {
    // Cargar productos desde la API
    await cargarProductos();

    // Establecer el texto de la cabecera
    document.querySelector('.cabecera-ticket').classList.add('cabecera-proforma');

    inicializarEventDelegation();

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
    }

    // Asociar eventos
    const btnCancelar = document.getElementById("btnCancelar");
    if (btnCancelar) {
      btnCancelar.addEventListener('click', volverSegunOrigen);
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

  } catch (error) {
    console.error('Error durante la inicialización:', error);
    mostrarNotificacion('Error durante la inicialización', 'error');
  }
});

function inicializarEventDelegation() {
  const tabla = document.querySelector('#detalle-proforma-grid tbody');
  if (!tabla) return;

  tabla.addEventListener('click', (event) => {
    const target = event.target;
    
    if (target.classList.contains('btn-eliminar')) {
      const index = parseInt(target.dataset.index);
      if (confirm('¿Está seguro de que desea eliminar este detalle?')) {
        detalles.splice(index, 1);
        actualizarTablaDetalles();
      }
    } else if (target.classList.contains('btn-editar')) {
      const index = parseInt(target.dataset.index);
      const detalle = detalles[index];
      if (detalle) {
        cargarDetalleParaEditar(detalle);
      }
    }
  });
}

function cargarDetalleParaEditar(detalle) {
  detalleEnEdicion = detalle;
  
  document.getElementById('concepto-detalle').value = detalle.productoId;
  document.getElementById('descripcion-detalle').value = detalle.descripcion;
  document.getElementById('cantidad-detalle').value = detalle.cantidad;
  document.getElementById('precio-detalle').value = formatearImporte(detalle.precio);
  document.getElementById('impuesto-detalle').value = formatearImporte(detalle.impuesto);
  document.getElementById('total-detalle').value = formatearImporte(detalle.total);
}

function calcularImportes(cantidad, precio, impuestos) {
  const subtotal = cantidad * precio;
  const iva = subtotal * impuestos;
  const total = subtotal + iva;
  return { subtotal, iva, total };
}

function validarYAgregarDetalle() {
  const select = document.getElementById('concepto-detalle');
  const productoId = select.value;
  let productoSeleccionado = productoId === PRODUCTO_ID_LIBRE 
    ? document.getElementById('descripcion-detalle').value.trim()
    : select.options[select.selectedIndex].textContent;
  let descripcion = document.getElementById('descripcion-detalle').value.trim();
  const cantidad = parsearImporte(document.getElementById('cantidad-detalle').value);
  const precio = parsearImporte(document.getElementById('precio-detalle').value);
  const impuesto = parsearImporte(document.getElementById('impuesto-detalle').value);
  const total = parsearImporte(document.getElementById('total-detalle').value);

  if (!validarDetalle(productoId, productoSeleccionado, descripcion, cantidad, precio, total)) {
    return;
  }

  const result = calcularImportes(cantidad, precio, impuesto);
  const detalle = {
    id: detalleEnEdicion ? detalleEnEdicion.id : Date.now(),
    productoId: productoId,
    producto: productoSeleccionado,
    descripcion: descripcion,
    cantidad: cantidad,
    precio: precio,
    impuesto: impuesto,
    subtotal: result.subtotal,
    iva: result.iva,
    total: result.total
  };

  if (detalleEnEdicion) {
    const index = detalles.findIndex(d => d.id === detalleEnEdicion.id);
    if (index !== -1) {
      detalles[index] = detalle;
    }
    detalleEnEdicion = null;
  } else {
    detalles.push(detalle);
  }

  actualizarTablaDetalles();
  limpiarCamposDetalle();
  actualizarTotales();
}

// Exportar funciones necesarias
window.filtrarProductos = filtrarProductos;
window.seleccionarProducto = seleccionarProducto;
window.validarYAgregarDetalle = validarYAgregarDetalle;
