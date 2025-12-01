/**
 * facturas_recibidas.js
 * Gestión de facturas recibidas de proveedores
 */

import { mostrarNotificacion } from './notificaciones.js';
import { formatearImporte } from './scripts_utils.js';

// Variables globales
let paginaActual = 1;
let porPagina = parseInt(sessionStorage.getItem('facturas_por_pagina')) || 20;
let totalPaginas = 1;
let proveedores = [];
let filtrosActuales = {};
let timeoutBusqueda = null;
let facturasCache = [];

// ============================================================================
// INICIALIZACIÓN
// ============================================================================

document.addEventListener('DOMContentLoaded', () => {
    console.log('[Facturas Recibidas] Inicializando...');
    
    // Restaurar valor del selector de registros por página
    const perPageSelect = document.getElementById('perPage');
    if (perPageSelect) {
        perPageSelect.value = porPagina;
    }
    
    // Establecer fechas del trimestre actual
    establecerTrimestreActual();
    
    // Cargar proveedores para el filtro
    cargarProveedores();
    
    // Cargar facturas
    cargarFacturas();
    
    // Event listeners
    configurarEventListeners();
});

function configurarEventListeners() {
    // Búsqueda interactiva en todos los filtros con debounce
    const filtros = ['proveedorFilter', 'startDate', 'endDate', 'busquedaFilter'];
    filtros.forEach(filtroId => {
        const elemento = document.getElementById(filtroId);
        if (elemento) {
            // Para selects y fechas: change event
            elemento.addEventListener('change', (e) => busquedaInteractiva(e));
            
            // Para campo de texto: input event (mientras escribe)
            if (filtroId === 'busquedaFilter') {
                elemento.addEventListener('input', (e) => busquedaInteractiva(e));
            }
        }
    });
    
    // Paginación
    document.getElementById('prevPage').addEventListener('click', () => cambiarPagina(-1));
    document.getElementById('nextPage').addEventListener('click', () => cambiarPagina(1));
    
    document.getElementById('perPage').addEventListener('change', (e) => {
        porPagina = parseInt(e.target.value);
        sessionStorage.setItem('facturas_por_pagina', porPagina);
        paginaActual = 1;
        cargarFacturas();
    });
}

// ============================================================================
// FUNCIONES DE TRIMESTRE Y FECHAS
// ============================================================================

function establecerTrimestreActual() {
    const hoy = new Date();
    const año = hoy.getFullYear();
    
    // Desde el 1 de enero hasta hoy
    const fechaInicio = new Date(año, 0, 1); // 1 de enero del año actual
    const fechaFin = hoy; // Fecha actual
    
    document.getElementById('startDate').value = formatearFechaInput(fechaInicio);
    document.getElementById('endDate').value = formatearFechaInput(fechaFin);
    
    console.log(`[Facturas] Rango establecido: ${formatearFechaInput(fechaInicio)} - ${formatearFechaInput(fechaFin)}`);
}

function establecerTrimestreEspecifico(trimestre) {
    const hoy = new Date();
    const año = hoy.getFullYear();
    let mesInicio, mesFin;
    
    switch(trimestre) {
        case 'Q1':
            mesInicio = 0; mesFin = 2;
            break;
        case 'Q2':
            mesInicio = 3; mesFin = 5;
            break;
        case 'Q3':
            mesInicio = 6; mesFin = 8;
            break;
        case 'Q4':
            mesInicio = 9; mesFin = 11;
            break;
    }
    
    const fechaInicio = new Date(año, mesInicio, 1);
    const fechaFin = new Date(año, mesFin + 1, 0);
    
    document.getElementById('startDate').value = formatearFechaInput(fechaInicio);
    document.getElementById('endDate').value = formatearFechaInput(fechaFin);
}

function formatearFechaInput(fecha) {
    const año = fecha.getFullYear();
    const mes = String(fecha.getMonth() + 1).padStart(2, '0');
    const dia = String(fecha.getDate()).padStart(2, '0');
    return `${año}-${mes}-${dia}`;
}

// ============================================================================
// BÚSQUEDA INTERACTIVA CON DEBOUNCE
// ============================================================================

function busquedaInteractiva(event) {
    // Cancelar búsqueda anterior si existe
    if (timeoutBusqueda) {
        clearTimeout(timeoutBusqueda);
    }
    
    // Mostrar indicador de búsqueda
    const searchingIndicator = document.getElementById('searchingIndicator');
    const busquedaInput = document.getElementById('busquedaFilter');
    
    if (event && event.target === busquedaInput) {
        // Mostrar spinner solo para campo de texto
        if (searchingIndicator) {
            searchingIndicator.style.display = 'inline';
        }
        busquedaInput.style.borderColor = '#ffc107';
    }
    
    // Determinar delay según el tipo de filtro
    let delay = 300; // Por defecto 300ms para campos de texto
    
    // Para selects y fechas, búsqueda más rápida (50ms)
    if (event && event.target && (
        event.target.tagName === 'SELECT' || 
        event.target.type === 'date'
    )) {
        delay = 50;
    }
    
    // Esperar antes de buscar (debounce)
    timeoutBusqueda = setTimeout(() => {
        paginaActual = 1;
        cargarFacturas();
        
        // Quitar indicador de búsqueda
        if (searchingIndicator) {
            searchingIndicator.style.display = 'none';
        }
        if (busquedaInput) {
            busquedaInput.style.borderColor = '';
        }
    }, delay);
    
    console.log(`[Facturas] Búsqueda programada en ${delay}ms (tipo: ${event?.target?.tagName || 'unknown'})`);
}

// ============================================================================
// CARGA DE DATOS
// ============================================================================

async function cargarProveedores() {
    try {
        const response = await fetch('/api/proveedores/listar?activos=true');
        const data = await response.json();
        
        if (data.success) {
            proveedores = data.proveedores;
            
            // Llenar dropdown
            const select = document.getElementById('proveedorFilter');
            select.innerHTML = '<option value="todos">Todos</option>';
            
            proveedores.forEach(prov => {
                const option = document.createElement('option');
                option.value = prov.id;
                option.textContent = `${prov.nombre} (${prov.nif})`;
                select.appendChild(option);
            });
            
            console.log(`[Facturas] ${proveedores.length} proveedores cargados`);
        }
    } catch (error) {
        console.error('[Facturas] Error cargando proveedores:', error);
    }
}

async function cargarFacturas() {
    try {
        // Mostrar loading
        const tbody = document.getElementById('facturasBody');
        tbody.innerHTML = `
            <tr>
                <td colspan="11" style="text-align: center; padding: 40px;">
                    <i class="fas fa-spinner fa-spin"></i> Cargando facturas...
                </td>
            </tr>
        `;
        
        // Construir filtros
        const filtros = {
            pagina: paginaActual,
            por_pagina: porPagina,
            orden_campo: 'fecha_emision',
            orden_direccion: 'DESC'
        };
        
        // Filtro de proveedor
        const proveedorId = document.getElementById('proveedorFilter').value;
        if (proveedorId !== 'todos') {
            filtros.proveedor_id = parseInt(proveedorId);
        }
        
        
        // Filtro de fechas
        const fechaDesde = document.getElementById('startDate').value;
        const fechaHasta = document.getElementById('endDate').value;
        if (fechaDesde) filtros.fecha_desde = fechaDesde;
        if (fechaHasta) filtros.fecha_hasta = fechaHasta;
        
        // Búsqueda
        const busqueda = document.getElementById('busquedaFilter').value.trim();
        if (busqueda) {
            filtros.busqueda = busqueda;
        }
        
        filtrosActuales = filtros;
        
        // Llamar a la API
        const response = await fetch('/api/facturas-proveedores/consultar', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(filtros)
        });
        
        const data = await response.json();
        
        if (data.success) {
            renderizarTabla(data.facturas);
            actualizarResumen(data);
            actualizarPaginacion(data);
            verificarAlertas(data);
            
            console.log(`[Facturas] ${data.facturas.length} facturas cargadas`);
        } else {
            throw new Error(data.error || 'Error desconocido');
        }
        
    } catch (error) {
        console.error('[Facturas] Error cargando facturas:', error);
        mostrarNotificacion('Error al cargar facturas: ' + error.message, 'error');
        
        const tbody = document.getElementById('facturasBody');
        tbody.innerHTML = `
            <tr>
                <td colspan="11" style="text-align: center; padding: 40px; color: #dc3545;">
                    <i class="fas fa-exclamation-triangle"></i> Error al cargar facturas
                </td>
            </tr>
        `;
    }
}

// ============================================================================
// RENDERIZADO
// ============================================================================

function renderizarTabla(facturas) {
    const tbody = document.getElementById('facturasBody');
    tbody.innerHTML = '';
    
    if (facturas.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="11" style="text-align: center; padding: 40px;">
                    📭 No se encontraron facturas con los filtros aplicados
                </td>
            </tr>
        `;
        return;
    }
    
    facturas.forEach(factura => {
        const tr = document.createElement('tr');
        
        // Determinar color de fila según estado
        // Color de fondo según estado
        if (factura.icono_estado === '🔴') {
            tr.style.backgroundColor = '#fff5f5';
        } else if (factura.icono_estado === '⚠️') {
            tr.style.backgroundColor = '#fffbf0';
        }
        
        // Hacer toda la fila clicable (excepto botones)
        tr.style.cursor = 'pointer';
        tr.onclick = function(e) {
            // No abrir si se hace click en un botón
            if (!e.target.closest('button')) {
                editarFactura(factura.id);
            }
        };
        
        tr.innerHTML = `
            <td>${factura.proveedor_nombre}</td>
            <td>${factura.proveedor_nif}</td>
            <td style="font-weight: 600;">${factura.numero_factura}</td>
            <td>${formatearFecha(factura.fecha_emision)}</td>
            <td>${formatearFecha(factura.fecha_vencimiento)}</td>
            <td style="text-align: right;">${formatearImporte(factura.base_imponible)}</td>
            <td style="text-align: right;">${formatearImporte(factura.iva_importe)}</td>
            <td style="text-align: right;"><strong>${formatearImporte(factura.total)}</strong></td>
            <td style="text-align: center;">
                ${factura.ruta_archivo ? `
                    <button class="btn-icon" onclick="event.stopPropagation(); descargarPDF(${factura.id})" title="Descargar PDF">
                        <i class="fas fa-file-pdf"></i>
                    </button>
                ` : ''}
                <button class="btn-icon text-danger" onclick="event.stopPropagation(); eliminarFactura(${factura.id})" title="Eliminar">
                    <i class="fas fa-times"></i>
                </button>
            </td>
        `;
        
        tbody.appendChild(tr);
    });
}

function actualizarResumen(data) {
    // Actualizar resumen superior
    document.getElementById('resumenTotal').textContent = formatearImporte(data.total_general || 0);
    document.getElementById('resumenPendiente').textContent = formatearImporte(data.total_pendiente || 0);
    document.getElementById('resumenPagado').textContent = formatearImporte(data.total_pagado || 0);
    document.getElementById('resumenVencido').textContent = formatearImporte(data.total_vencido || 0);
    
    // Actualizar footer fijo
    const footerBase = document.getElementById('footerBase');
    const footerIVA = document.getElementById('footerIVA');
    const footerTotal = document.getElementById('footerTotal');
    
    if (footerBase) footerBase.textContent = formatearImporte(data.total_base || 0);
    if (footerIVA) footerIVA.textContent = formatearImporte(data.total_iva || 0);
    if (footerTotal) footerTotal.textContent = formatearImporte(data.total_general || 0);
}

function actualizarPaginacion(data) {
    paginaActual = data.pagina;
    totalPaginas = data.total_paginas;
    
    const pageInfo = `Página ${paginaActual} de ${totalPaginas}`;
    document.getElementById('pageInfo').textContent = pageInfo;
    
    // Habilitar/deshabilitar botones
    document.getElementById('prevPage').disabled = paginaActual === 1;
    document.getElementById('nextPage').disabled = paginaActual === totalPaginas;
}

function verificarAlertas(data) {
    const container = document.getElementById('alertasContainer');
    container.innerHTML = '';
    
    let hayAlertas = false;
    
    // Alerta de facturas vencidas
    if (data.total_vencido > 0) {
        hayAlertas = true;
        const alerta = document.createElement('div');
        alerta.className = 'alerta roja';
        alerta.innerHTML = `
            🔴 Tienes facturas vencidas por un total de <strong>${formatearImporte(data.total_vencido)}</strong>
            <a onclick="filtrarVencidas()">Ver facturas vencidas</a>
        `;
        container.appendChild(alerta);
    }
    
    container.style.display = hayAlertas ? 'flex' : 'none';
}

// ============================================================================
// ACCIONES
// ============================================================================

function cambiarPagina(delta) {
    const nuevaPagina = paginaActual + delta;
    if (nuevaPagina >= 1 && nuevaPagina <= totalPaginas) {
        paginaActual = nuevaPagina;
        cargarFacturas();
    }
}

function filtrarVencidas() {
    // Función deshabilitada - filtro de estado eliminado
    mostrarNotificacion('Filtro de estado eliminado', 'info');
}

async function exportarExcel() {
    mostrarNotificacion('Exportando a Excel...', 'info');
    
    try {
        const response = await fetch('/api/facturas-proveedores/exportar', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(filtrosActuales)
        });
        
        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `facturas_recibidas_${new Date().toISOString().split('T')[0]}.xlsx`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
            
            mostrarNotificacion('✅ Excel exportado correctamente', 'success');
        } else {
            throw new Error('Error al exportar');
        }
    } catch (error) {
        console.error('[Facturas] Error exportando:', error);
        mostrarNotificacion('Error al exportar a Excel', 'error');
    }
}

function subirFactura() {
    mostrarNotificacion('Función de subida en desarrollo', 'info');
    // TODO: Implementar modal de subida
}

// ============================================================================
// FUNCIONES GLOBALES (llamadas desde HTML)
// ============================================================================

window.verDetalle = async function(facturaId) {
    try {
        const response = await fetch(`/api/facturas-proveedores/${facturaId}`);
        const data = await response.json();
        
        if (data.success) {
            mostrarModalDetalle(data.factura);
        } else {
            mostrarNotificacion('Error al cargar factura: ' + data.error, 'error');
        }
    } catch (error) {
        console.error('[Facturas] Error cargando detalle:', error);
        mostrarNotificacion('Error al cargar factura', 'error');
    }
};

window.descargarPDF = async function(facturaId) {
    try {
        // Verificar si el PDF existe
        const response = await fetch(`/api/facturas-proveedores/${facturaId}/pdf`, {
            method: 'HEAD' // Solo verificar headers, no descargar el archivo
        });
        
        if (response.ok) {
            // El archivo existe, abrirlo
            window.open(`/api/facturas-proveedores/${facturaId}/pdf`, '_blank');
        } else if (response.status === 404) {
            // Archivo no encontrado
            mostrarNotificacion('❌ El archivo PDF no existe en el servidor', 'error');
        } else {
            // Otro error
            mostrarNotificacion('❌ Error al acceder al archivo PDF', 'error');
        }
    } catch (error) {
        console.error('Error al verificar PDF:', error);
        mostrarNotificacion('❌ Error al verificar el archivo PDF', 'error');
    }
};

window.marcarPagada = async function(facturaId) {
    try {
        const response = await fetch(`/api/facturas-proveedores/${facturaId}`);
        const data = await response.json();
        
        if (data.success) {
            mostrarModalPagar(data.factura);
        } else {
            mostrarNotificacion('Error al cargar factura', 'error');
        }
    } catch (error) {
        console.error('[Facturas] Error:', error);
        mostrarNotificacion('Error al cargar factura', 'error');
    }
};

window.editarFactura = async function(facturaId) {
    try {
        const response = await fetch(`/api/facturas-proveedores/${facturaId}`);
        const data = await response.json();
        
        if (data.success) {
            mostrarModalEditar(data.factura);
        } else {
            mostrarNotificacion('Error al cargar factura', 'error');
        }
    } catch (error) {
        console.error('[Facturas] Error:', error);
        mostrarNotificacion('Error al cargar factura', 'error');
    }
};

window.eliminarFactura = async function(facturaId) {
    if (!confirm('¿Estás seguro de que deseas eliminar esta factura?\n\nEsta acción no se puede deshacer.')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/facturas-proveedores/${facturaId}`, {
            method: 'DELETE'
        });
        
        const data = await response.json();
        
        if (data.success) {
            mostrarNotificacion('✅ Factura eliminada correctamente', 'success');
            cargarFacturas(); // Recargar tabla
        } else {
            mostrarNotificacion('Error: ' + data.error, 'error');
        }
    } catch (error) {
        console.error('[Facturas] Error eliminando:', error);
        mostrarNotificacion('Error al eliminar factura', 'error');
    }
};

// ============================================================================
// FUNCIONES DE MODALES
// ============================================================================

function mostrarModalDetalle(factura) {
    // Llenar datos del proveedor
    document.getElementById('detalle-proveedor-nombre').textContent = factura.proveedor_nombre || '-';
    document.getElementById('detalle-proveedor-nif').textContent = factura.proveedor_nif || '-';
    document.getElementById('detalle-proveedor-direccion').textContent = factura.proveedor_direccion || '-';
    document.getElementById('detalle-proveedor-telefono').textContent = factura.proveedor_telefono || '-';
    
    // Llenar datos de la factura
    document.getElementById('detalle-numero').textContent = factura.numero_factura;
    document.getElementById('detalle-fecha-emision').textContent = formatearFecha(factura.fecha_emision);
    document.getElementById('detalle-fecha-vencimiento').textContent = formatearFecha(factura.fecha_vencimiento);
    
    const estadoBadge = document.getElementById('detalle-estado');
    estadoBadge.textContent = factura.estado;
    estadoBadge.className = `badge ${factura.estado}`;
    
    // Importes
    document.getElementById('detalle-base').textContent = formatearImporte(factura.base_imponible);
    document.getElementById('detalle-iva').textContent = formatearImporte(factura.iva_importe) + ` (${factura.iva_porcentaje}%)`;
    document.getElementById('detalle-total').textContent = formatearImporte(factura.total);
    
    // Concepto y notas
    document.getElementById('detalle-concepto').textContent = factura.concepto || '-';
    document.getElementById('detalle-notas').textContent = factura.notas || '-';
    
    // Líneas (si existen)
    if (factura.lineas && factura.lineas.length > 0) {
        const tbody = document.getElementById('detalle-lineas-body');
        tbody.innerHTML = '';
        
        factura.lineas.forEach(linea => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${linea.concepto}</td>
                <td>${linea.cantidad}</td>
                <td>${formatearImporte(linea.precio_unitario)}</td>
                <td>${linea.iva_porcentaje}%</td>
                <td>${formatearImporte(linea.total_linea)}</td>
            `;
            tbody.appendChild(tr);
        });
        
        document.getElementById('seccion-lineas').style.display = 'block';
    } else {
        document.getElementById('seccion-lineas').style.display = 'none';
    }
    
    // Historial
    if (factura.historial && factura.historial.length > 0) {
        const historialDiv = document.getElementById('detalle-historial');
        historialDiv.innerHTML = '';
        
        factura.historial.forEach(h => {
            const item = document.createElement('div');
            item.className = 'historial-item';
            item.innerHTML = `
                <div class="fecha">${formatearFechaHora(h.fecha)}</div>
                <div class="accion">${h.accion}</div>
                <div class="usuario">Por: ${h.usuario}</div>
            `;
            historialDiv.appendChild(item);
        });
        
        document.getElementById('seccion-historial').style.display = 'block';
    } else {
        document.getElementById('seccion-historial').style.display = 'none';
    }
    
    // Guardar ID para descargar PDF
    window.facturaDetalleId = factura.id;
    
    // Mostrar modal
    abrirModal('modalDetalle');
}

function mostrarModalPagar(factura) {
    document.getElementById('pagar-factura-id').value = factura.id;
    document.getElementById('pagar-fecha').value = new Date().toISOString().split('T')[0];
    document.getElementById('pagar-metodo').value = 'transferencia';
    document.getElementById('pagar-referencia').value = '';
    
    document.getElementById('pagar-info-numero').textContent = factura.numero_factura;
    document.getElementById('pagar-info-proveedor').textContent = factura.proveedor_nombre;
    document.getElementById('pagar-info-total').textContent = formatearImporte(factura.total);
    
    abrirModal('modalPagar');
}

function mostrarModalEditar(factura) {
    document.getElementById('editar-factura-id').value = factura.id;
    
    // Llenar y seleccionar proveedor
    const selectProveedor = document.getElementById('editar-proveedor');
    if (selectProveedor) {
        selectProveedor.innerHTML = '<option value="">Seleccionar proveedor...</option>';
        if (typeof proveedores !== 'undefined' && proveedores.length > 0) {
            proveedores.forEach(prov => {
                const option = document.createElement('option');
                option.value = prov.id;
                option.textContent = `${prov.nombre} (${prov.nif})`;
                selectProveedor.appendChild(option);
            });
            // Seleccionar el proveedor actual
            if (factura.proveedor_id) {
                selectProveedor.value = factura.proveedor_id;
            }
        }
    }

    document.getElementById('editar-numero').value = factura.numero_factura;
    document.getElementById('editar-fecha-emision').value = factura.fecha_emision;
    document.getElementById('editar-fecha-vencimiento').value = factura.fecha_vencimiento || '';
    document.getElementById('editar-base').value = factura.base_imponible;
    document.getElementById('editar-iva-porcentaje').value = factura.iva_porcentaje;
    document.getElementById('editar-iva-importe').value = factura.iva_importe;
    document.getElementById('editar-total').value = factura.total;
    document.getElementById('editar-concepto').value = factura.concepto || '';
    document.getElementById('editar-notas').value = factura.notas || '';
    // Checkbox eliminado: document.getElementById('editar-revisado').checked = factura.revisado === 1;
    
    // Event listeners para cálculo automático
    const baseInput = document.getElementById('editar-base');
    const ivaSelect = document.getElementById('editar-iva-porcentaje');
    
    const calcular = () => {
        const base = parseFloat(baseInput.value) || 0;
        const ivaPorcentaje = parseFloat(ivaSelect.value) || 0;
        const ivaImporte = base * (ivaPorcentaje / 100);
        const total = base + ivaImporte;
        
        document.getElementById('editar-iva-importe').value = ivaImporte.toFixed(2);
        document.getElementById('editar-total').value = total.toFixed(2);
    };
    
    baseInput.addEventListener('input', calcular);
    ivaSelect.addEventListener('change', calcular);
    
    // Cargar previsualización en iframe
    const previewFrame = document.getElementById('editar-preview-frame');
    const previewPlaceholder = document.getElementById('editar-preview-placeholder');
    
    if (factura.id) {
        // Usar el endpoint de descarga/visualización
        const url = `/api/facturas-proveedores/${factura.id}/pdf`;
        previewFrame.src = url;
        previewFrame.style.display = 'block';
        if (previewPlaceholder) previewPlaceholder.style.display = 'none';
        
        // Manejar error de carga en el iframe
        previewFrame.onerror = function() {
            previewFrame.style.display = 'none';
            if (previewPlaceholder) previewPlaceholder.style.display = 'flex';
        };
    } else {
        previewFrame.src = '';
        previewFrame.style.display = 'none';
        if (previewPlaceholder) previewPlaceholder.style.display = 'flex';
    }
    
    abrirModal('modalEditar');
}

window.abrirModal = function(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.add('show');
        modal.style.display = 'flex';
    }
};

window.cerrarModal = function(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.remove('show');
        setTimeout(() => {
            modal.style.display = 'none';
        }, 300);
    }
};

window.descargarPDFDesdeModal = async function() {
    if (window.facturaDetalleId) {
        try {
            // Verificar si el PDF existe
            const response = await fetch(`/api/facturas-proveedores/${window.facturaDetalleId}/pdf`, {
                method: 'HEAD'
            });
            
            if (response.ok) {
                // El archivo existe, abrirlo
                window.open(`/api/facturas-proveedores/${window.facturaDetalleId}/pdf`, '_blank');
            } else if (response.status === 404) {
                // Archivo no encontrado
                mostrarNotificacion('❌ El archivo PDF no existe en el servidor', 'error');
            } else {
                // Otro error
                mostrarNotificacion('❌ Error al acceder al archivo PDF', 'error');
            }
        } catch (error) {
            console.error('Error al verificar PDF:', error);
            mostrarNotificacion('❌ Error al verificar el archivo PDF', 'error');
        }
    }
};

window.confirmarPago = async function() {
    const facturaId = document.getElementById('pagar-factura-id').value;
    const fechaPago = document.getElementById('pagar-fecha').value;
    const metodoPago = document.getElementById('pagar-metodo').value;
    const referenciaPago = document.getElementById('pagar-referencia').value;
    
    if (!fechaPago) {
        mostrarNotificacion('La fecha de pago es obligatoria', 'error');
        return;
    }
    
    try {
        const response = await fetch(`/api/facturas-proveedores/${facturaId}/pagar`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                fecha_pago: fechaPago,
                metodo_pago: metodoPago,
                referencia_pago: referenciaPago
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            mostrarNotificacion('✅ Factura marcada como pagada', 'success');
            cerrarModal('modalPagar');
            cargarFacturas(); // Recargar tabla
        } else {
            mostrarNotificacion('Error: ' + data.error, 'error');
        }
    } catch (error) {
        console.error('[Facturas] Error:', error);
        mostrarNotificacion('Error al marcar como pagada', 'error');
    }
};

window.guardarEdicion = async function() {
    const facturaId = document.getElementById('editar-factura-id').value;
    
    const datos = {
        proveedor_id: document.getElementById('editar-proveedor').value,
        numero_factura: document.getElementById('editar-numero').value,
        fecha_emision: document.getElementById('editar-fecha-emision').value,
        fecha_vencimiento: document.getElementById('editar-fecha-vencimiento').value,
        base_imponible: parseFloat(document.getElementById('editar-base').value),
        iva_porcentaje: parseFloat(document.getElementById('editar-iva-porcentaje').value),
        iva_importe: parseFloat(document.getElementById('editar-iva-importe').value),
        total: parseFloat(document.getElementById('editar-total').value),
        concepto: document.getElementById('editar-concepto').value,
        notas: document.getElementById('editar-notas').value,
        revisado: 1 // Al editar manualmente, marcamos como revisado por defecto
    };
    
    try {
        const response = await fetch(`/api/facturas-proveedores/${facturaId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(datos)
        });
        
        const data = await response.json();
        
        if (data.success) {
            mostrarNotificacion('✅ Factura actualizada correctamente', 'success');
            cerrarModal('modalEditar');
            cargarFacturas(); // Recargar tabla
        } else {
            mostrarNotificacion('Error: ' + data.error, 'error');
        }
    } catch (error) {
        console.error('[Facturas] Error:', error);
        mostrarNotificacion('Error al guardar cambios', 'error');
    }
};

// Cerrar modal al hacer click fuera
window.addEventListener('click', (e) => {
    if (e.target.classList.contains('modal')) {
        e.target.classList.remove('show');
        setTimeout(() => {
            e.target.style.display = 'none';
        }, 300);
    }
});

// ============================================================================
// UTILIDADES
// ============================================================================

function formatearFecha(fecha) {
    if (!fecha) return '-';
    const [year, month, day] = fecha.split('-');
    return `${day}/${month}/${year}`;
}

function formatearFechaHora(fechaHora) {
    if (!fechaHora) return '-';
    try {
        const fecha = new Date(fechaHora);
        const dia = fecha.getDate().toString().padStart(2, '0');
        const mes = (fecha.getMonth() + 1).toString().padStart(2, '0');
        const año = fecha.getFullYear();
        const hora = fecha.getHours().toString().padStart(2, '0');
        const minutos = fecha.getMinutes().toString().padStart(2, '0');
        return `${dia}/${mes}/${año} ${hora}:${minutos}`;
    } catch (e) {
        return fechaHora;
    }
}

function obtenerTituloEstado(factura) {
    if (factura.estado === 'pagada') return 'Pagada';
    if (factura.icono_estado === '🔴') return 'Vencida';
    if (factura.revisado === 0) return 'Requiere revisión';
    return 'Pendiente';
}
