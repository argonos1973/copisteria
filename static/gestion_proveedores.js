/**
 * gestion_proveedores.js
 * Gestión de proveedores (Vista Grid + Modales)
 */

import { mostrarNotificacion, mostrarConfirmacion } from './notificaciones.js';

// Variables globales
let proveedores = [];
let proveedorEditando = null;
let proveedorSeleccionado = null; // Para el modal de detalle

// ============================================================================
// INICIALIZACIÓN
// ============================================================================

document.addEventListener('DOMContentLoaded', () => {
    console.log('[Proveedores] Inicializando...');
    
    cargarProveedores();
    configurarEventListeners();
});

function configurarEventListeners() {
    // Botones Modal Edición
    document.getElementById('btnNuevoProveedor').addEventListener('click', () => abrirModalEdicion());
    document.getElementById('closeModal').addEventListener('click', cerrarModalEdicion);
    document.getElementById('btnCancelarModal').addEventListener('click', cerrarModalEdicion);
    document.getElementById('btnGuardarProveedor').addEventListener('click', guardarProveedor);
    
    // Botones Modal Detalle
    document.getElementById('closeDetalleModal').addEventListener('click', cerrarModalDetalle);
    document.getElementById('btnCerrarDetalle').addEventListener('click', cerrarModalDetalle);
    
    document.getElementById('btnEditarDesdeDetalle').addEventListener('click', () => {
        cerrarModalDetalle();
        abrirModalEdicion(proveedorSeleccionado);
    });

    document.getElementById('btnEliminarDesdeDetalle').addEventListener('click', () => {
        if (proveedorSeleccionado) {
            eliminarProveedor(proveedorSeleccionado.id, proveedorSeleccionado.nombre);
            cerrarModalDetalle();
        }
    });
    
    // Filtros
    document.getElementById('busquedaProveedor').addEventListener('input', filtrarProveedores);
    
    // Cerrar modal al hacer clic fuera
    window.addEventListener('click', (e) => {
        const modal = document.getElementById('modalProveedor');
        const modalDetalle = document.getElementById('modalDetalleProveedor');
        if (e.target === modal) {
            cerrarModalEdicion();
        }
        if (e.target === modalDetalle) {
            cerrarModalDetalle();
        }
    });
}

// ============================================================================
// CARGA DE DATOS
// ============================================================================

async function cargarProveedores() {
    try {
        const response = await fetch('/api/proveedores/listar');
        const data = await response.json();
        
        if (data.success) {
            proveedores = data.proveedores;
            renderizarProveedores();
            console.log(`[Proveedores] ${proveedores.length} proveedores cargados`);
        } else {
            throw new Error(data.error || 'Error al cargar proveedores');
        }
    } catch (error) {
        console.error('[Proveedores] Error:', error);
        mostrarNotificacion('Error al cargar proveedores: ' + error.message, 'error');
        
        document.getElementById('proveedoresList').innerHTML = `
            <div style="text-align: center; padding: 40px; grid-column: 1/-1;">
                <i class="fas fa-exclamation-triangle" style="font-size: 48px; color: #dc3545;"></i>
                <p>Error al cargar proveedores</p>
            </div>
        `;
    }
}

// ============================================================================
// RENDERIZADO
// ============================================================================

function renderizarProveedores() {
    const container = document.getElementById('proveedoresList');
    
    if (proveedores.length === 0) {
        container.innerHTML = `
            <div style="text-align: center; padding: 40px; grid-column: 1/-1;">
                <i class="fas fa-users" style="font-size: 48px; color: #ccc;"></i>
                <p>No hay proveedores registrados</p>
                <button class="btn btn-primary" onclick="document.getElementById('btnNuevoProveedor').click()">
                    <i class="fas fa-plus"></i> Crear primer proveedor
                </button>
            </div>
        `;
        return;
    }
    
    container.innerHTML = '';
    
    proveedores.forEach(proveedor => {
        const card = crearCardProveedor(proveedor);
        container.appendChild(card);
    });
}

function crearCardProveedor(proveedor) {
    const card = document.createElement('div');
    card.className = 'proveedor-card';
    
    // Icono basado en si tiene email o no (como indicador de completitud)
    const iconClass = proveedor.email ? 'fa-building' : 'fa-store-alt';
    
    // Calcular estado visual (simulado)
    const estadoClass = 'status-activo';
    const estadoTexto = 'Activo';

    card.innerHTML = `
        <div class="proveedor-header">
            <div class="proveedor-icon">
                <i class="fas ${iconClass}"></i>
            </div>
            <div class="proveedor-status ${estadoClass}">
                ${estadoTexto}
            </div>
        </div>
        
        <div class="proveedor-name" title="${proveedor.nombre}">${proveedor.nombre}</div>
        <div class="proveedor-nif">${proveedor.nif || 'Sin NIF'}</div>
        
        <div class="proveedor-info-grid">
            <div class="info-label"><i class="fas fa-envelope"></i></div>
            <div class="info-value" title="${proveedor.email || '-'}">${proveedor.email || '-'}</div>
            
            <div class="info-label"><i class="fas fa-phone"></i></div>
            <div class="info-value">${proveedor.telefono || '-'}</div>
            
            <div class="info-label"><i class="fas fa-map-marker-alt"></i></div>
            <div class="info-value" title="${proveedor.direccion || '-'}">${proveedor.poblacion || proveedor.provincia || '-'}</div>
        </div>
    `;
    
    // Evento Click para abrir detalle
    card.addEventListener('click', () => abrirModalDetalle(proveedor));
    
    return card;
}

// ============================================================================
// FILTRADO
// ============================================================================

function filtrarProveedores() {
    const busqueda = document.getElementById('busquedaProveedor').value.toLowerCase();
    
    const proveedoresFiltrados = proveedores.filter(proveedor => {
        // Filtro de búsqueda
        return !busqueda || 
            proveedor.nombre.toLowerCase().includes(busqueda) ||
            (proveedor.nif && proveedor.nif.toLowerCase().includes(busqueda)) ||
            (proveedor.email && proveedor.email.toLowerCase().includes(busqueda));
    });
    
    // Renderizar solo los filtrados
    const container = document.getElementById('proveedoresList');
    container.innerHTML = '';
    
    if (proveedoresFiltrados.length === 0) {
        container.innerHTML = `
            <div style="text-align: center; padding: 40px; grid-column: 1/-1;">
                <i class="fas fa-search" style="font-size: 48px; color: #ccc;"></i>
                <p>No se encontraron proveedores</p>
            </div>
        `;
        return;
    }
    
    proveedoresFiltrados.forEach(proveedor => {
        const card = crearCardProveedor(proveedor);
        container.appendChild(card);
    });
}

// ============================================================================
// MODALES
// ============================================================================

function abrirModalEdicion(proveedor = null) {
    proveedorEditando = proveedor;
    
    const modal = document.getElementById('modalProveedor');
    const title = document.getElementById('modalTitle');
    
    if (proveedor) {
        title.innerHTML = '<i class="fas fa-edit"></i> Editar Proveedor';
        document.getElementById('proveedorId').value = proveedor.id;
        document.getElementById('nombre').value = proveedor.nombre;
        document.getElementById('nif').value = proveedor.nif;
        document.getElementById('email').value = proveedor.email || '';
        document.getElementById('email_facturacion').value = proveedor.email_facturacion || '';
        document.getElementById('telefono').value = proveedor.telefono || '';
        document.getElementById('direccion').value = proveedor.direccion || '';
        document.getElementById('cp').value = proveedor.cp || '';
        document.getElementById('poblacion').value = proveedor.poblacion || '';
        document.getElementById('provincia').value = proveedor.provincia || '';
        document.getElementById('notas').value = proveedor.notas || '';
    } else {
        title.innerHTML = '<i class="fas fa-user-plus"></i> Nuevo Proveedor';
        document.getElementById('formProveedor').reset();
        document.getElementById('proveedorId').value = '';
    }
    
    modal.style.display = 'block';
}

function cerrarModalEdicion() {
    document.getElementById('modalProveedor').style.display = 'none';
    proveedorEditando = null;
}

function abrirModalDetalle(proveedor) {
    proveedorSeleccionado = proveedor;
    const modal = document.getElementById('modalDetalleProveedor');
    const contenido = document.getElementById('detalleProveedorContenido');
    
    const direccionCompleta = [
        proveedor.direccion, 
        proveedor.cp, 
        proveedor.poblacion, 
        proveedor.provincia
    ].filter(Boolean).join(', ') || 'Sin dirección registrada';

    contenido.innerHTML = `
        <div class="modal-detail-header">
            <div class="modal-detail-icon">
                <i class="fas fa-building"></i>
            </div>
            <div class="modal-detail-title">
                <h2>${proveedor.nombre}</h2>
                <div style="color: var(--text-muted); font-family: monospace; font-size: 1.1em;">
                    ${proveedor.nif || 'Sin NIF'}
                </div>
            </div>
        </div>

        <div class="detail-section-title">
            <i class="fas fa-address-card"></i> Información de Contacto
        </div>
        
        <div class="modal-detail-grid">
            <div class="detail-item">
                <label>Email General</label>
                <div>${proveedor.email ? `<a href="mailto:${proveedor.email}">${proveedor.email}</a>` : '-'}</div>
            </div>
            <div class="detail-item">
                <label>Email Facturación</label>
                <div>${proveedor.email_facturacion ? `<a href="mailto:${proveedor.email_facturacion}">${proveedor.email_facturacion}</a>` : '-'}</div>
            </div>
            <div class="detail-item">
                <label>Teléfono</label>
                <div>${proveedor.telefono ? `<a href="tel:${proveedor.telefono}">${proveedor.telefono}</a>` : '-'}</div>
            </div>
        </div>

        <div class="detail-section-title">
            <i class="fas fa-map-marked-alt"></i> Dirección
        </div>
        
        <div class="modal-detail-grid">
            <div class="detail-item" style="grid-column: 1/-1;">
                <label>Dirección Completa</label>
                <div>${direccionCompleta}</div>
            </div>
        </div>

        ${proveedor.notas ? `
            <div class="detail-section-title">
                <i class="fas fa-sticky-note"></i> Notas Internas
            </div>
            <div style="background: var(--bg-elevated); padding: 10px; border-radius: 6px; font-style: italic; color: var(--text-muted);">
                ${proveedor.notas}
            </div>
        ` : ''}
        
        <div class="detail-section-title">
            <i class="fas fa-info-circle"></i> Metadatos
        </div>
        
        <div class="modal-detail-grid">
            <div class="detail-item">
                <label>Fecha Alta</label>
                <div>${proveedor.fecha_alta ? new Date(proveedor.fecha_alta).toLocaleDateString() : '-'}</div>
            </div>
            <div class="detail-item">
                <label>Origen</label>
                <div>${proveedor.creado_automaticamente ? 'Automático (OCR)' : 'Manual'}</div>
            </div>
        </div>
    `;
    
    modal.style.display = 'block';
}

function cerrarModalDetalle() {
    document.getElementById('modalDetalleProveedor').style.display = 'none';
    proveedorSeleccionado = null;
}

// ============================================================================
// GUARDAR
// ============================================================================

async function guardarProveedor() {
    const nombre = document.getElementById('nombre').value.trim();
    const nif = document.getElementById('nif').value.trim();
    
    if (!nombre) {
        mostrarNotificacion('Ingresa el nombre del proveedor', 'error');
        return;
    }
    
    if (!nif) {
        mostrarNotificacion('Ingresa el NIF/CIF del proveedor', 'error');
        return;
    }
    
    const datos = {
        nombre,
        nif,
        email: document.getElementById('email').value.trim(),
        email_facturacion: document.getElementById('email_facturacion').value.trim(),
        telefono: document.getElementById('telefono').value.trim(),
        direccion: document.getElementById('direccion').value.trim(),
        cp: document.getElementById('cp').value.trim(),
        poblacion: document.getElementById('poblacion').value.trim(),
        provincia: document.getElementById('provincia').value.trim(),
        notas: document.getElementById('notas').value.trim()
    };
    
    try {
        const proveedorId = document.getElementById('proveedorId').value;
        const url = proveedorId ? 
            `/api/proveedores/${proveedorId}` : 
            '/api/proveedores/crear';
        
        const method = proveedorId ? 'PUT' : 'POST';
        
        const response = await fetch(url, {
            method,
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(datos)
        });
        
        const data = await response.json();
        
        if (data.success) {
            mostrarNotificacion(
                proveedorId ? 'Proveedor actualizado' : 'Proveedor creado',
                'success'
            );
            cerrarModalEdicion();
            cargarProveedores();
        } else {
            throw new Error(data.error || 'Error al guardar proveedor');
        }
    } catch (error) {
        console.error('[Proveedores] Error:', error);
        mostrarNotificacion('Error al guardar: ' + error.message, 'error');
    }
}

// ============================================================================
// ELIMINAR PROVEEDOR
// ============================================================================

window.eliminarProveedor = async function(id, nombre) {
    const confirmado = await mostrarConfirmacion(
        `¿Estás seguro de que deseas eliminar el proveedor "${nombre}"?\n\nEsta acción no se puede deshacer.`,
        {
            textoConfirmar: 'Eliminar',
            textoCancelar: 'Cancelar',
            tipo: 'danger',
            titulo: 'Eliminar Proveedor'
        }
    );

    if (!confirmado) {
        return;
    }
    
    try {
        const response = await fetch(`/api/proveedores/${id}`, {
            method: 'DELETE'
        });
        
        const data = await response.json();
        
        if (data.success) {
            mostrarNotificacion('Proveedor eliminado correctamente', 'success');
            cargarProveedores();
        } else {
            throw new Error(data.error || 'Error al eliminar proveedor');
        }
    } catch (error) {
        console.error('[Proveedores] Error:', error);
        mostrarNotificacion('Error: ' + error.message, 'error');
    }
};
