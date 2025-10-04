import { IP_SERVER, PORT } from './constantes.js';
import { 
    PRODUCTO_ID_LIBRE,
    formatearImporte,
    formatearImporteVariable,
    redondearImporte,
    parsearImporte,
    formatearFechaSoloDia,
    mostrarCargando,
    ocultarCargando,
    debounce,
    normalizarContactoBackend,
    normalizarDetalleBackend,
    normalizarDetallesBackend,
    normalizarImportesBackend,
    parsearNumeroBackend,
    convertirFechaParaAPI,
    formatearApunto,
    extraerFranjaDeDataset,
    invalidateGlobalCache,
    inicializarInfoPrecioPopup,
    inicializarDeteccionCambios,
    marcarCambiosSinGuardar,
    resetearCambiosSinGuardar,
    fetchContactoPorId
} from './scripts_utils.js';
import { 
    calcularTotalPresupuesto,
    actualizarDetalleConTotal,
    calcularTotalesDocumento 
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
// Eliminado: cálculos legacy reemplazados por calculo_totales_unificado.js

// Variables globales
let detalles = [];
let idPresupuesto = null;
let idContacto = null;
let productosOriginales = [];
let detalleEnEdicion = null;

// Variables para modal de contactos
let contactosData = [];
let currentPageContactos = 1;
let totalPagesContactos = 1;
let filtrosContactos = { razonSocial: '', nif: '' };

const CONTACTO_CANDIDATO_KEYS = [
  'contacto',
  'contactoPresupuesto',
  'contacto_presupuesto',
  'contactoCliente',
  'contacto_facturacion',
  'contactoFacturacion',
  'cliente',
  'contactoData',
  'datos_contacto'
];

function limpiarFormularioContacto() {
  document.getElementById('razonSocial').value = '';
  document.getElementById('identificador').value = '';
  document.getElementById('direccion').value = '';
  document.getElementById('cp-localidad').textContent = '';
  document.getElementById('provincia').value = '';
}

function aplicarContactoEnFormulario(contacto = {}) {
  if (!contacto || typeof contacto !== 'object') {
    limpiarFormularioContacto();
    return;
  }
  document.getElementById('razonSocial').value = contacto.razonsocial || '';
  document.getElementById('identificador').value = contacto.identificador || '';
  document.getElementById('direccion').value = contacto.direccion || '';
  const cp = contacto.cp || '';
  const localidad = contacto.localidad || '';
  document.getElementById('cp-localidad').textContent = cp && localidad ? `${cp} ${localidad}` : (cp || localidad);
  document.getElementById('provincia').value = contacto.provincia || '';
}

function extraerCandidatosContacto(datos = {}) {
  const candidatos = [];
  for (const key of CONTACTO_CANDIDATO_KEYS) {
    if (datos && datos[key]) {
      candidatos.push(datos[key]);
    }
  }
  return candidatos;
}

function normalizarPrimerContactoValido(candidatos = []) {
  for (const candidato of candidatos) {
    const normalizado = normalizarContactoBackend(candidato);
    if (normalizado && Object.keys(normalizado).length > 0) {
      return normalizado;
    }
  }
  return null;
}

async function resolverContactoDocumento(datos = {}, preferido = null) {
  const candidatos = [];
  if (preferido) candidatos.push(preferido);
  candidatos.push(...extraerCandidatosContacto(datos));

  const contactoNormalizado = normalizarPrimerContactoValido(candidatos);
  if (contactoNormalizado) {
    return contactoNormalizado;
  }

  const fallbackId = parsearNumeroBackend(
    preferido?.idContacto ?? datos.idContacto ?? datos.idcontacto ?? datos.id_contacto,
    null
  );

  if (fallbackId) {
    const contactoApi = await fetchContactoPorId(fallbackId);
    if (contactoApi && Object.keys(contactoApi).length > 0) {
      return contactoApi;
    }
  }

  const planB = {
    idContacto: fallbackId,
    razonsocial: datos.razonsocial ?? datos.razon_social ?? datos.razonSocial ?? '',
    identificador: datos.identificador ?? datos.nif ?? datos.cif ?? '',
    direccion: datos.direccion ?? datos.direccion_fiscal ?? '',
    cp: datos.cp ?? datos.codigo_postal ?? datos.codigopostal ?? '',
    localidad: datos.localidad ?? datos.poblacion ?? datos.ciudad ?? '',
    provincia: datos.provincia ?? datos.provincia_nombre ?? ''
  };

  const planBNormalizado = normalizarContactoBackend(planB);
  if (planBNormalizado && Object.keys(planBNormalizado).length > 0) {
    return planBNormalizado;
  }

  return {};
}

async function establecerContactoDesdeDatos(datos = {}, preferido = null) {
  const contacto = await resolverContactoDocumento(datos, preferido);
  if (contacto && Object.keys(contacto).length > 0) {
    aplicarContactoEnFormulario(contacto);
    return contacto;
  }
  limpiarFormularioContacto();
  return {};
}

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

  if (formElements.cantidadDetalle) {
    formElements.cantidadDetalle.value = 1;
  }

  await seleccionarProductoCommon(formElements, productosOriginales, 'presupuesto');

  const productoId = formElements.conceptoDetalle.value;

  if (productoId === PRODUCTO_ID_LIBRE) {
    formElements.precioDetalle.readOnly = false;
    formElements.precioDetalle.classList.remove('readonly-field');
    formElements.precioDetalle.style.backgroundColor = '';

    formElements.totalDetalle.readOnly = false;
    formElements.totalDetalle.classList.remove('readonly-field');
    formElements.totalDetalle.style.backgroundColor = '';

    formElements.impuestoDetalle.value = 21;
    formElements.impuestoDetalle.readOnly = true;
    formElements.impuestoDetalle.classList.add('readonly-field');
    formElements.impuestoDetalle.style.backgroundColor = '#e9ecef';
  } else {
    formElements.precioDetalle.readOnly = true;
    formElements.precioDetalle.classList.add('readonly-field');
    formElements.precioDetalle.style.backgroundColor = '#e9ecef';

    formElements.totalDetalle.readOnly = true;
    formElements.totalDetalle.classList.add('readonly-field');
    formElements.totalDetalle.style.backgroundColor = '#e9ecef';

    formElements.impuestoDetalle.value = 21;
    formElements.impuestoDetalle.readOnly = true;
    formElements.impuestoDetalle.classList.add('readonly-field');
    formElements.impuestoDetalle.style.backgroundColor = '#e9ecef';
  }

  await calcularTotalDetalle();
}

function actualizarTotales() {
  console.log('------- INICIO actualizarTotales PRESUPUESTO UNIFICADO -------');
  
  // USAR FUNCIÓN UNIFICADA para garantizar consistencia absoluta
  const total = calcularTotalPresupuesto(detalles);
  
  console.log(`TOTAL PRESUPUESTO FINAL (UNIFICADO): ${total}`);
  
  const totalInput = document.getElementById('total-presupuesto');
  if (totalInput) totalInput.value = formatearImporte(total);
  console.log('------- FIN actualizarTotales PRESUPUESTO UNIFICADO -------');
}

function actualizarTablaDetalles() {
  const tbody = document.querySelector('#tabla-detalle-presupuesto tbody');
  if (!tbody) return;
  tbody.innerHTML = '';
  if (!detalles || detalles.length === 0) return;
  detalles.forEach((detalle, index) => {
    const tr = document.createElement('tr');
    tr.style.cursor = 'pointer';
    tr.classList.add('detalle-editable');
    
    // USAR FUNCIÓN UNIFICADA para recalcular el total correctamente
    const detalleActualizado = actualizarDetalleConTotal(detalle);
    detalle.total = detalleActualizado.total;
    
    const precioFormateado = formatearImporteVariable(Number(detalle.precio), 0, 5);
    const totalFormateado = formatearImporte(detalle.total);
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
    
    // Event listener para editar detalle al hacer click
    tr.addEventListener('click', async (e) => {
      if (!e.target.classList.contains('btn-icon')) {
        await editarDetalle(index);
      }
    });
    
    tbody.appendChild(tr);
  });
  actualizarTotales();
}

async function editarDetalle(index) {
  const detalle = detalles[index];
  if (!detalle) return;
  
  // Cargar datos del detalle en el formulario
  const conceptoSelect = document.getElementById('concepto-detalle');
  const descripcionInput = document.getElementById('descripcion-detalle');
  const cantidadInput = document.getElementById('cantidad-detalle');
  const precioInput = document.getElementById('precio-detalle');
  const impuestoInput = document.getElementById('impuesto-detalle');
  const totalInput = document.getElementById('total-detalle');
  const conceptoInput = document.getElementById('concepto-input');
  const busquedaInput = document.getElementById('busqueda-producto');
  
  // Restablecer filtros para asegurar que el producto esté disponible
  if (busquedaInput) {
    busquedaInput.value = '';
  }
  if (conceptoSelect) {
    actualizarSelectProductos(productosOriginales, conceptoSelect);
    conceptoSelect.value = detalle.productoId || '';
    await seleccionarProducto();
  }

  // Establecer valores del detalle seleccionado
  if (descripcionInput) descripcionInput.value = detalle.descripcion || '';
  if (cantidadInput) cantidadInput.value = Number(detalle.cantidad || 1);
  if (precioInput) precioInput.value = Number(detalle.precio || 0).toFixed(5);
  if (impuestoInput) impuestoInput.value = Number(detalle.impuestos ?? 21);
  if (totalInput) totalInput.value = Number(detalle.total || 0).toFixed(2);

  // Manejar producto libre para mostrar concepto personalizado
  if (conceptoInput) {
    if (String(detalle.productoId) === String(PRODUCTO_ID_LIBRE)) {
      conceptoInput.style.display = 'block';
      conceptoInput.value = detalle.concepto || '';
    } else {
      conceptoInput.style.display = 'none';
      conceptoInput.value = '';
    }
  }

  // Recalcular franjas y actualizar información de precio
  await calcularTotalDetalle();

  // Marcar como en edición
  detalleEnEdicion = index;

  // Eliminar el detalle de la lista temporalmente
  detalles.splice(index, 1);
  actualizarTablaDetalles();

  // Enfocar el campo de búsqueda
  if (busquedaInput) {
    busquedaInput.focus();
  }

  mostrarNotificacion('Detalle cargado para edición', 'info');
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

  if (!descripcion) {
    const fecha = new Date();
    const dia = fecha.getDate().toString().padStart(2, '0');
    const mes = (fecha.getMonth() + 1).toString().padStart(2, '0');
    const anno = fecha.getFullYear();
    descripcion = `${dia}/${mes}/${anno}`;
  }

  const impuestos = parseFloat(document.getElementById('impuesto-detalle').value) || 0;
  // Calcular total con REGLA UNIFICADA (IVA redondeado por línea)
  const detCalc = actualizarDetalleConTotal({ precio: precioDetalle, cantidad, impuestos });
  const total = Number(detCalc.total) || 0;

  if (total <= 0) {
    mostrarNotificacion("El campo 'Total' es obligatorio y debe ser mayor que 0", "warning");
    return false;
  }
  if (cantidad <= 0) {
    mostrarNotificacion("El campo 'Cantidad' es obligatorio y debe ser mayor que 0", "warning");
    return false;
  }

  const fechaDetalle = new Date().toISOString().split('T')[0];
  const fecha = new Date();
  const detalleId = `${fecha.getDate().toString().padStart(2, '0')}${(fecha.getMonth() + 1).toString().padStart(2, '0')}`;

  const detalle = {
    productoId: productoId,
    concepto: productoSeleccionado,
    descripcion: descripcion,
    cantidad: cantidad,
    precio: Number(precioDetalle).toFixed(5),
    impuestos: impuestos,
    total: Number(total).toFixed(2),
    formaPago: 'E',
    fechaDetalle: fechaDetalle,
    detalleId: detalleId
  };

  detalles.push(detalle);
  actualizarTablaDetalles();
  marcarCambiosSinGuardar();

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
  mostrarNotificacion('Detalle agregado correctamente', 'success');
  return true;
}

function inicializarEventDelegation() {
  const tbody = document.querySelector('#tabla-detalle-presupuesto tbody');
  if (!tbody) return;
  tbody.addEventListener('click', async function(event) {
    const target = event.target;
    if (target && target.classList.contains('btn-icon')) {
      const fila = target.closest('tr');
      if (fila) {
        const index = parseInt(fila.dataset.index);
        detalles.splice(index, 1);
        actualizarTablaDetalles();
        marcarCambiosSinGuardar();
        mostrarNotificacion('Detalle eliminado correctamente', 'success');
      }
      event.stopPropagation();
    }
  });
}

async function cargarPresupuesto(id) {
  try {
    const response = await fetch(`http://${IP_SERVER}:${PORT}/api/presupuestos/consulta/${id}`);
    if (!response.ok) throw new Error(`Error al cargar el presupuesto: ${response.statusText}`);
    const data = await response.json();
    const importes = normalizarImportesBackend(data);
    const detallesNormalizados = normalizarDetallesBackend(data.detalles);

    // Establecer ID del presupuesto para edición
    idPresupuesto = parsearNumeroBackend(id, id);
    
    document.getElementById('numero').value = data.numero;
    document.getElementById('fecha').value = formatearFechaSoloDia(data.fecha);
    // Decodificar estado para mostrar texto legible
    let estadoTexto = data.estado;
    if (data.estado === 'B') estadoTexto = 'Borrador';
    else if (data.estado === 'A') estadoTexto = 'Aceptado';
    else if (data.estado === 'R') estadoTexto = 'Rechazado';
    else if (data.estado === 'C') estadoTexto = 'Cerrado';
    document.getElementById('estado').value = estadoTexto;
    document.getElementById('total-presupuesto').value = formatearImporte(importes.total || 0);

    const tipo = 'N';
    document.getElementById('tipo-presupuesto').value = 'N';
    sessionStorage.setItem('tipoPresupuesto', 'N');
    const formulario = document.getElementById('presupuesto-form');
    if (formulario) formulario.dataset.tipoPresupuesto = 'N';

    // Cargar datos del contacto
    const contactoNormalizado = await establecerContactoDesdeDatos(data, importes.contacto);
    let contactoId = parsearNumeroBackend(contactoNormalizado.idContacto ?? data.idContacto ?? data.idcontacto, null);
    contactoId = contactoId != null ? parseInt(contactoId, 10) : null;
    idContacto = Number.isNaN(contactoId) ? null : contactoId;

    // Cargar detalles del presupuesto
    if (detallesNormalizados.length > 0) {
      detalles = detallesNormalizados.map(d => ({
        id: d?.id,
        concepto: d?.concepto,
        descripcion: d?.descripcion || '',
        cantidad: d?.cantidad,
        precio: d?.precio,
        impuestos: d?.impuestos,
        total: d?.total,
        productoId: d?.productoId,
        formaPago: d?.formaPago,
        fechaDetalle: d?.fechaDetalle
      }));
    } else {
      detalles = [];
    }
    actualizarTablaDetalles();
  } catch (e) {
    console.error('Error al cargar presupuesto:', e);
    mostrarNotificacion('Error al cargar el presupuesto', 'error');
  }
}

async function buscarPresupuestoAbierto(idContacto) {
  try {
    const response = await fetch(`http://${IP_SERVER}:${PORT}/api/presupuesto/abierta/${idContacto}`);
    if (!response.ok) throw new Error(`Error al buscar presupuesto abierto: ${response.statusText}`);
    const data = await response.json();
    const importes = normalizarImportesBackend(data);
    const detallesNormalizados = normalizarDetallesBackend(data.detalles);

    const contactoNormalizado = await establecerContactoDesdeDatos(data, importes.contacto);
    let contactoId = parsearNumeroBackend(contactoNormalizado.idContacto ?? data.idContacto ?? data.idcontacto, null);
    contactoId = contactoId != null ? parseInt(contactoId, 10) : null;
    idContacto = Number.isNaN(contactoId) ? null : contactoId;

    if (data.modo === 'edicion') {
      idPresupuesto = data.id;
      document.getElementById('numero').value = data.numero;
      const fechaFormateada = formatearFechaSoloDia(data.fecha);
      document.getElementById('fecha').value = fechaFormateada;
      // Decodificar estado para mostrar texto legible
      let estadoTexto = data.estado;
      if (data.estado === 'B') estadoTexto = 'Borrador';
      else if (data.estado === 'A') estadoTexto = 'Aceptado';
      else if (data.estado === 'R') estadoTexto = 'Rechazado';
      else if (data.estado === 'C') estadoTexto = 'Cerrado';
      document.getElementById('estado').value = estadoTexto;
      document.getElementById('total-presupuesto').value = formatearImporte(data.total);
      document.getElementById('tipo-presupuesto').value = 'N';
      sessionStorage.setItem('tipoPresupuesto', 'N');

      if (detallesNormalizados.length > 0) {
        detalles = detallesNormalizados.map(d => ({
          id: d?.id,
          concepto: d?.concepto,
          descripcion: d?.descripcion || '',
          cantidad: d?.cantidad,
          precio: d?.precio,
          impuestos: d?.impuestos,
          total: d?.total,
          productoId: d?.productoId,
          formaPago: d?.formaPago,
          fechaDetalle: d?.fechaDetalle
        }));
      } else {
        detalles = [];
      }
      actualizarTablaDetalles();
    } else {
      // Nuevo
      try {
        const numResponse = await fetch(`http://${IP_SERVER}:${PORT}/api/presupuesto/numero`);
        if (!numResponse.ok) throw new Error('Error al obtener el número de presupuesto');
        const numData = await numResponse.json();
        const fecha = new Date();
        const anno = fecha.getFullYear().toString().slice(-2);
        let numeroPadded = numData.numerador.toString().padStart(4, '0');
        let numeracion = `O${anno}${numeroPadded}`;
        const dia = String(fecha.getDate()).padStart(2, '0');
        const mes = String(fecha.getMonth() + 1).toString().padStart(2, '0');
        const annoCompleto = fecha.getFullYear();
        document.getElementById('fecha').value = `${dia}/${mes}/${annoCompleto}`;
        document.getElementById('numero').value = numeracion;
        document.getElementById('estado').value = 'Borrador';
        document.getElementById('total-presupuesto').value = '0,00';
        detalles = [];
        actualizarTablaDetalles();
      } catch (error) {
        console.error('Error al obtener número de presupuesto:', error);
        mostrarNotificacion('Error al obtener número de presupuesto', 'error');
        return;
      }
    }
  } catch (error) {
    console.error('Error al buscar presupuesto abierto:', error);
    mostrarNotificacion('Error al buscar presupuesto abierto', 'error');
  }
}

async function guardarPresupuesto(formaPago, importeCobrado, estado='B') {
  try {
    // Recalcular totales del documento con módulo unificado
    const totalesDoc = calcularTotalesDocumento((detalles || []).map(d => ({
      precio: parsearImporte(d.precio),
      cantidad: parsearImporte(d.cantidad),
      impuestos: parsearImporte(d.impuestos)
    })));
    const totalPresupuesto = totalesDoc.total_final || 0;
    const fechaInput = document.getElementById('fecha').value;
    // Convertir DD/MM/YYYY -> YYYY-MM-DD para API
    let fechaAPI = convertirFechaParaAPI(fechaInput);

    let numeroPresupuesto = document.getElementById('numero').value;

    // Si no hay id, asegurar número fresco por si ha cambiado el numerador
    if (!idPresupuesto) {
      const numResponse = await fetch(`http://${IP_SERVER}:${PORT}/api/presupuesto/numero`);
      if (!numResponse.ok) throw new Error('Error al obtener nuevo número de presupuesto');
      const numData = await numResponse.json();
      const fecha = new Date();
      const anno = fecha.getFullYear().toString().slice(-2);
      let numeroPadded = numData.numerador.toString().padStart(4, '0');
      let nuevoNumero = `O${anno}${numeroPadded}`;
      document.getElementById('numero').value = nuevoNumero;
      numeroPresupuesto = nuevoNumero;
      console.log('Usando nuevo número de presupuesto:', nuevoNumero);
    }

    const idContactoNumerico = idContacto ? parseInt(idContacto, 10) : null;

    const datos = {
      id: idPresupuesto,
      numero: numeroPresupuesto,
      fecha: fechaAPI,
      idcontacto: idContactoNumerico,
      nif: document.getElementById('identificador').value,
      total: totalPresupuesto,
      formaPago: formaPago || 'E',
      importe_bruto: totalesDoc.subtotal_total || 0,
      importe_impuestos: totalesDoc.iva_total || 0,
      importe_cobrado: typeof importeCobrado === 'number' ? importeCobrado : parsearImporte(importeCobrado || '0,00'),
      estado: estado,
      tipo: document.getElementById('tipo-presupuesto').value,
      detalles: detalles
    };

    const url = idPresupuesto 
      ? `http://${IP_SERVER}:${PORT}/api/presupuestos/actualizar`
      : `http://${IP_SERVER}:${PORT}/api/presupuesto`;

    const response = await fetch(url, {
      method: idPresupuesto ? 'PATCH' : 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(datos)
    });

    if (!response.ok) throw new Error('Error al guardar presupuesto');
    const resData = await response.json();
    if (!idPresupuesto) idPresupuesto = resData.id;

    // Invalidar cachés globales tras guardar
    try { invalidateGlobalCache(); } catch(e) { console.warn('No se pudo invalidar cache', e); }

    resetearCambiosSinGuardar();
    mostrarNotificacion('Presupuesto guardado correctamente', 'success');
    
    // Guardar filtros iniciales antes de redirigir (primer día del mes actual al último día)
    const today = new Date();
    const firstDay = new Date(today.getFullYear(), today.getMonth(), 1);
    const lastDay = new Date(today.getFullYear(), today.getMonth() + 1, 0);
    const formatDate = (d) => `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;
    
    const filtros = {
      startDate: formatDate(firstDay),
      endDate: formatDate(lastDay),
      estado: 'B',  // Estado Borrador por defecto
      numero: '',
      contacto: '',
      identificador: ''
    };
    sessionStorage.setItem('filtrosPresupuestos', JSON.stringify(filtros));
    
    // Volver a la consulta tras guardar con filtros guardados
    setTimeout(() => {
      window.location.href = 'CONSULTA_PRESUPUESTOS.html';
    }, 800);
  } catch (error) {
    console.error('Error al guardar presupuesto:', error);
    mostrarNotificacion('Error al guardar el presupuesto', 'error');
  }
}

// Funciones para modal de contactos
async function cargarContactos(page = 1) {
  try {
    const params = new URLSearchParams({
      page: page,
      page_size: 10,
      sort: 'razonsocial',
      order: 'ASC',
      razonSocial: filtrosContactos.razonSocial,
      nif: filtrosContactos.nif
    });

    const response = await fetch(`http://${IP_SERVER}:${PORT}/api/contactos/paginado?${params}`);
    if (!response.ok) throw new Error('Error al cargar contactos');
    
    const data = await response.json();
    contactosData = data.items || [];
    currentPageContactos = data.page || 1;
    totalPagesContactos = data.total_pages || 1;
    
    actualizarTablaContactos();
    actualizarPaginacionContactos();
  } catch (error) {
    console.error('Error al cargar contactos:', error);
    mostrarNotificacion('Error al cargar contactos', 'error');
  }
}

function actualizarTablaContactos() {
  const tbody = document.querySelector('#tablaContactos tbody');
  if (!tbody) return;
  
  tbody.innerHTML = '';
  
  contactosData.forEach(contacto => {
    const tr = document.createElement('tr');
    tr.style.cursor = 'pointer';
    tr.classList.add('contacto-seleccionable');
    tr.dataset.id = contacto.idContacto;
    tr.dataset.razon = contacto.razonsocial || '';
    tr.dataset.nif = contacto.identificador || '';
    tr.dataset.direccion = contacto.direccion || '';
    tr.dataset.cp = contacto.cp || '';
    tr.dataset.localidad = contacto.localidad || '';
    tr.dataset.provincia = contacto.provincia || '';
    
    tr.innerHTML = `
      <td>${contacto.razonsocial || ''}</td>
      <td style="text-align: center;">${contacto.identificador || ''}</td>
    `;
    
    tr.addEventListener('mouseenter', () => {
      tr.style.backgroundColor = '#f8f9fa';
    });
    
    tr.addEventListener('mouseleave', () => {
      tr.style.backgroundColor = '';
    });
    
    tbody.appendChild(tr);
  });
}

function actualizarPaginacionContactos() {
  const btnAnterior = document.getElementById('btnAnteriorContactos');
  const btnSiguiente = document.getElementById('btnSiguienteContactos');
  const infoPage = document.getElementById('infoPageContactos');
  
  if (btnAnterior) btnAnterior.disabled = currentPageContactos <= 1;
  if (btnSiguiente) btnSiguiente.disabled = currentPageContactos >= totalPagesContactos;
  if (infoPage) infoPage.textContent = `Página ${currentPageContactos} de ${totalPagesContactos}`;
}

function abrirModalContactos() {
  const modal = document.getElementById('modalContactos');
  if (modal) {
    modal.style.display = 'block';
    cargarContactos(1);
  }
}

function cerrarModalContactos() {
  const modal = document.getElementById('modalContactos');
  if (modal) modal.style.display = 'none';
}

function seleccionarContactoModal(contactoData) {
  idContacto = parseInt(contactoData.id, 10) || null;
  
  // Actualizar campos del contacto
  document.getElementById('razonSocial').value = contactoData.razon || '';
  document.getElementById('identificador').value = contactoData.nif || '';
  document.getElementById('direccion').value = contactoData.direccion || '';
  const cp = contactoData.cp || '';
  const localidad = contactoData.localidad || '';
  document.getElementById('cp-localidad').textContent = cp && localidad ? `${cp} ${localidad}` : (cp || localidad);
  document.getElementById('provincia').value = contactoData.provincia || '';
  
  cerrarModalContactos();
  mostrarNotificacion('Contacto asignado correctamente', 'success');
}

function inicializarModalContactos() {
  // Botón Asignar
  const btnAsignar = document.getElementById('btnAsignarContacto');
  if (btnAsignar) {
    btnAsignar.addEventListener('click', abrirModalContactos);
  }
  
  // Cerrar modal
  const closeModal = document.getElementById('closeModalContactos');
  if (closeModal) {
    closeModal.addEventListener('click', cerrarModalContactos);
  }
  
  // Cerrar modal al hacer clic fuera
  const modal = document.getElementById('modalContactos');
  if (modal) {
    modal.addEventListener('click', (e) => {
      if (e.target === modal) cerrarModalContactos();
    });
  }
  
  // Filtros
  const filtroRazon = document.getElementById('filtroRazonSocial');
  const filtroNIF = document.getElementById('filtroNIF');
  const actualizarFiltrosDebounced = debounce(() => cargarContactos(1), 800);
  
  if (filtroRazon) {
    filtroRazon.addEventListener('input', () => {
      filtrosContactos.razonSocial = filtroRazon.value;
      actualizarFiltrosDebounced();
    });
  }
  
  if (filtroNIF) {
    filtroNIF.addEventListener('input', () => {
      filtrosContactos.nif = filtroNIF.value;
      actualizarFiltrosDebounced();
    });
  }
  
  // Paginación
  const btnAnterior = document.getElementById('btnAnteriorContactos');
  const btnSiguiente = document.getElementById('btnSiguienteContactos');
  
  if (btnAnterior) {
    btnAnterior.addEventListener('click', () => {
      if (currentPageContactos > 1) cargarContactos(currentPageContactos - 1);
    });
  }
  
  if (btnSiguiente) {
    btnSiguiente.addEventListener('click', () => {
      if (currentPageContactos < totalPagesContactos) cargarContactos(currentPageContactos + 1);
    });
  }
  
  // Event delegation para selección directa de contactos
  const tablaContactos = document.getElementById('tablaContactos');
  if (tablaContactos) {
    tablaContactos.addEventListener('click', (e) => {
      const tr = e.target.closest('tr.contacto-seleccionable');
      if (tr) {
        const contactoData = {
          id: tr.dataset.id,
          razon: tr.dataset.razon,
          nif: tr.dataset.nif,
          direccion: tr.dataset.direccion,
          cp: tr.dataset.cp,
          localidad: tr.dataset.localidad,
          provincia: tr.dataset.provincia
        };
        seleccionarContactoModal(contactoData);
      }
    });
  }
}

function inicializarModalPagos() {
  const btnGuardar = document.getElementById('btnGuardar');
  if (btnGuardar) {
    btnGuardar.addEventListener('click', () => {
      const total = parsearImporte(document.getElementById('total-presupuesto').value);
      guardarPresupuesto('E', 0, 'B');
    });
  }
}

// Inicialización

document.addEventListener('DOMContentLoaded', async () => {
  try {
    sessionStorage.setItem('tipoProforma', 'N');
    inicializarInfoPrecioPopup();
    await cargarProductos();
    inicializarEventDelegation();

    const btnCancelar = document.getElementById('btnCancelar');
    if (btnCancelar) btnCancelar.addEventListener('click', volverSegunOrigen);

    inicializarModalPagos();
    inicializarModalContactos();

    const busquedaProducto = document.getElementById('busqueda-producto');
    if (busquedaProducto) busquedaProducto.addEventListener('input', () => filtrarProductos());
    const conceptoDetalle = document.getElementById('concepto-detalle');
    if (conceptoDetalle) conceptoDetalle.addEventListener('change', () => seleccionarProducto());
    const btnAgregarDetalle = document.getElementById('btn-agregar-detalle');
    if (btnAgregarDetalle) btnAgregarDetalle.addEventListener('click', () => validarYAgregarDetalle());

    const impuestoDetalle = document.getElementById('impuesto-detalle');
    if (impuestoDetalle) { impuestoDetalle.readOnly = true; impuestoDetalle.style.backgroundColor = '#e9ecef'; }

    const urlParams = new URLSearchParams(window.location.search);
    const idContactoParam = urlParams.get('idContacto');
    idContacto = idContactoParam ? parseInt(idContactoParam, 10) : null;
    const idPresupuestoParam = urlParams.get('idPresupuesto');
    const origen = urlParams.get('origen');
    if (origen) sessionStorage.setItem('origenPresupuesto', origen);

    if (idPresupuestoParam) {
      // Cargar presupuesto específico por ID
      await cargarPresupuesto(idPresupuestoParam);
    } else if (idContacto) {
      await buscarPresupuestoAbierto(idContacto);
    } else {
      // Inicializar nuevo presupuesto
      const response = await fetch(`http://${IP_SERVER}:${PORT}/api/presupuesto/numero`);
      if (!response.ok) throw new Error('Error al obtener el número de presupuesto');
      const numData = await response.json();
      const fecha = new Date();
      const anno = fecha.getFullYear().toString().slice(-2);
      let numeroPadded = numData.numerador.toString().padStart(4, '0');
      let numeracion = `O${anno}${numeroPadded}`;
      const dia = String(fecha.getDate()).padStart(2, '0');
      const mes = String(fecha.getMonth() + 1).toString().padStart(2, '0');
      const annoCompleto = fecha.getFullYear();
      document.getElementById('fecha').value = `${dia}/${mes}/${annoCompleto}`;
      document.getElementById('numero').value = numeracion;
      document.getElementById('estado').value = 'Borrador';
      document.getElementById('total-presupuesto').value = '0,00';
      detalles = [];
      actualizarTablaDetalles();
    }

    document.getElementById('busqueda-producto').focus();
  } catch (error) {
    console.error('Error durante la inicialización:', error);
  }
  
  // Inicializar sistema de detección de cambios sin guardar
  inicializarDeteccionCambios(async () => {
    const btnGuardar = document.getElementById('btn-guardar');
    if (btnGuardar) {
      btnGuardar.click();
    }
  });
  
  // Marcar cambios en inputs principales
  const inputsToWatch = [
    'fecha-presupuesto',
    'numero-presupuesto',
    'busqueda-contacto',
    'cantidad-detalle',
    'precio-detalle',
    'impuestos-detalle'
  ];
  
  inputsToWatch.forEach(id => {
    const input = document.getElementById(id);
    if (input) {
      input.addEventListener('input', () => marcarCambiosSinGuardar());
      input.addEventListener('change', () => marcarCambiosSinGuardar());
    }
  });
});
