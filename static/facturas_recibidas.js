/**
 * facturas_recibidas.js
 * Gestión de facturas recibidas de proveedores
 */

import { mostrarNotificacion } from './notificaciones.js';

// Variables globales
let paginaActual = 1;
let porPagina = 25;
let totalPaginas = 1;
let proveedores = [];
let filtrosActuales = {};

// ============================================================================
// INICIALIZACIÓN
// ============================================================================

document.addEventListener('DOMContentLoaded', () => {
    console.log('[Facturas Recibidas] Inicializando...');
    
    // Cargar proveedores para el filtro
    cargarProveedores();
    
    // Cargar facturas
    cargarFacturas();
    
    // Event listeners
    configurarEventListeners();
});

function configurarEventListeners() {
    // Botones de acción
    document.getElementById('btnBuscar').addEventListener('click', () => {
        paginaActual = 1;
        cargarFacturas();
    });
    
    document.getElementById('btnLimpiar').addEventListener('click', limpiarFiltros);
    document.getElementById('btnExportar').addEventListener('click', exportarExcel);
    document.getElementById('btnSubir').addEventListener('click', subirFactura);
    
    // Paginación
    document.getElementById('prevPage').addEventListener('click', () => cambiarPagina(-1));
    document.getElementById('nextPage').addEventListener('click', () => cambiarPagina(1));
    document.getElementById('prevPage2').addEventListener('click', () => cambiarPagina(-1));
    document.getElementById('nextPage2').addEventListener('click', () => cambiarPagina(1));
    
    document.getElementById('perPage').addEventListener('change', (e) => {
        porPagina = parseInt(e.target.value);
        paginaActual = 1;
        cargarFacturas();
    });
    
    // Filtro de trimestre automático
    document.getElementById('trimestreFilter').addEventListener('change', (e) => {
        if (e.target.value === 'actual') {
            // Limpiar fechas manuales
            document.getElementById('startDate').value = '';
            document.getElementById('endDate').value = '';
        }
    });
    
    // Select all checkboxes
    document.getElementById('selectAll').addEventListener('change', (e) => {
        const checkboxes = document.querySelectorAll('.select-factura');
        checkboxes.forEach(cb => cb.checked = e.target.checked);
    });
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
        
        // Filtro de estado
        const estado = document.getElementById('estadoFilter').value;
        if (estado !== 'todos') {
            filtros.estado = estado;
        }
        
        // Filtro de trimestre
        const trimestre = document.getElementById('trimestreFilter').value;
        if (trimestre !== 'todos') {
            filtros.trimestre = trimestre;
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
        if (factura.icono_estado === '🔴') {
            tr.style.backgroundColor = '#fff5f5';
        } else if (factura.icono_estado === '⚠️') {
            tr.style.backgroundColor = '#fffbf0';
        }
        
        tr.innerHTML = `
            <td>
                <input type="checkbox" class="select-factura" data-id="${factura.id}">
            </td>
            <td class="estado-icon" title="${obtenerTituloEstado(factura)}">
                ${factura.icono_estado}
            </td>
            <td>${factura.proveedor_nombre}</td>
            <td>${factura.proveedor_nif}</td>
            <td>
                <a href="#" onclick="verDetalle(${factura.id}); return false;" style="font-weight: 600;">
                    ${factura.numero_factura}
                </a>
            </td>
            <td>${formatearFecha(factura.fecha_emision)}</td>
            <td>${formatearFecha(factura.fecha_vencimiento)}</td>
            <td style="text-align: right;">${formatearImporte(factura.base_imponible)}</td>
            <td style="text-align: right;">${formatearImporte(factura.iva_importe)}</td>
            <td style="text-align: right;"><strong>${formatearImporte(factura.total)}</strong></td>
            <td>
                <button class="btn-action btn-primary" onclick="verDetalle(${factura.id})" title="Ver detalle">
                    <i class="fas fa-eye"></i>
                </button>
                ${factura.ruta_archivo ? `
                    <button class="btn-action btn-success" onclick="descargarPDF(${factura.id})" title="Descargar PDF">
                        <i class="fas fa-file-pdf"></i>
                    </button>
                ` : ''}
                ${factura.estado !== 'pagada' ? `
                    <button class="btn-action btn-info" onclick="marcarPagada(${factura.id})" title="Marcar como pagada">
                        <i class="fas fa-check"></i>
                    </button>
                ` : ''}
                <button class="btn-action btn-warning" onclick="editarFactura(${factura.id})" title="Editar">
                    <i class="fas fa-edit"></i>
                </button>
                <button class="btn-action btn-danger" onclick="eliminarFactura(${factura.id})" title="Eliminar">
                    <i class="fas fa-trash"></i>
                </button>
            </td>
        `;
        
        tbody.appendChild(tr);
    });
}

function actualizarResumen(data) {
    document.getElementById('resumenTotal').textContent = formatearImporte(data.total_general || 0);
    document.getElementById('resumenPendiente').textContent = formatearImporte(data.total_pendiente || 0);
    document.getElementById('resumenPagado').textContent = formatearImporte(data.total_pagado || 0);
    document.getElementById('resumenVencido').textContent = formatearImporte(data.total_vencido || 0);
}

function actualizarPaginacion(data) {
    paginaActual = data.pagina;
    totalPaginas = data.total_paginas;
    
    const pageInfo = `Página ${paginaActual} de ${totalPaginas}`;
    document.getElementById('pageInfo').textContent = pageInfo;
    document.getElementById('pageInfo2').textContent = pageInfo;
    
    document.getElementById('totalRegistros').textContent = `${data.total} registros`;
    
    // Habilitar/deshabilitar botones
    const prevButtons = [document.getElementById('prevPage'), document.getElementById('prevPage2')];
    const nextButtons = [document.getElementById('nextPage'), document.getElementById('nextPage2')];
    
    prevButtons.forEach(btn => btn.disabled = paginaActual === 1);
    nextButtons.forEach(btn => btn.disabled = paginaActual === totalPaginas);
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

function limpiarFiltros() {
    document.getElementById('proveedorFilter').value = 'todos';
    document.getElementById('estadoFilter').value = 'todos';
    document.getElementById('trimestreFilter').value = 'actual';
    document.getElementById('startDate').value = '';
    document.getElementById('endDate').value = '';
    document.getElementById('busquedaFilter').value = '';
    
    paginaActual = 1;
    cargarFacturas();
}

function filtrarVencidas() {
    document.getElementById('estadoFilter').value = 'vencida';
    paginaActual = 1;
    cargarFacturas();
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

window.verDetalle = function(facturaId) {
    console.log('[Facturas] Ver detalle:', facturaId);
    mostrarNotificacion('Función de detalle en desarrollo', 'info');
    // TODO: Implementar modal de detalle
};

window.descargarPDF = function(facturaId) {
    console.log('[Facturas] Descargar PDF:', facturaId);
    window.open(`/api/facturas-proveedores/${facturaId}/pdf`, '_blank');
};

window.marcarPagada = function(facturaId) {
    console.log('[Facturas] Marcar pagada:', facturaId);
    mostrarNotificacion('Función de pago en desarrollo', 'info');
    // TODO: Implementar modal de pago
};

window.editarFactura = function(facturaId) {
    console.log('[Facturas] Editar:', facturaId);
    mostrarNotificacion('Función de edición en desarrollo', 'info');
    // TODO: Implementar modal de edición
};

window.eliminarFactura = function(facturaId) {
    if (confirm('¿Estás seguro de que deseas eliminar esta factura?')) {
        console.log('[Facturas] Eliminar:', facturaId);
        mostrarNotificacion('Función de eliminación en desarrollo', 'info');
        // TODO: Implementar eliminación
    }
};

// ============================================================================
// UTILIDADES
// ============================================================================

function formatearFecha(fecha) {
    if (!fecha) return '-';
    const [year, month, day] = fecha.split('-');
    return `${day}/${month}/${year}`;
}

function formatearImporte(importe) {
    if (importe === null || importe === undefined) return '0,00€';
    return new Intl.NumberFormat('es-ES', {
        style: 'currency',
        currency: 'EUR'
    }).format(importe);
}

function obtenerTituloEstado(factura) {
    if (factura.estado === 'pagada') return 'Pagada';
    if (factura.icono_estado === '🔴') return 'Vencida';
    if (factura.revisado === 0) return 'Requiere revisión';
    return 'Pendiente';
}
