/**
 * gestion_proveedores.js
 * Gestión de proveedores (Vista Grid + Modales)
 */

import { mostrarNotificacion, mostrarConfirmacion } from './notificaciones.js';

// Variables globales
let proveedores = [];
let proveedoresFiltrados = []; // Para mantener el set filtrado
let proveedorEditando = null;
let proveedorSeleccionado = null; // Para el modal de detalle

// Paginación
let currentPage = 1;
let itemsPerPage = 20;

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
    
    document.getElementById('btnEditarDesdeDetalle').addEventListener('click', () => {
        activarEdicionEnDetalle(proveedorSeleccionado);
    });

    document.getElementById('btnEliminarDesdeDetalle').addEventListener('click', () => {
        if (proveedorSeleccionado) {
            eliminarProveedor(proveedorSeleccionado.id, proveedorSeleccionado.nombre);
            cerrarModalDetalle();
        }
    });
    
    // Filtros
    document.getElementById('busquedaProveedor').addEventListener('input', filtrarProveedores);
    
    // Paginación
    document.getElementById('prevPage').addEventListener('click', () => cambiarPagina(-1));
    document.getElementById('nextPage').addEventListener('click', () => cambiarPagina(1));
    document.getElementById('perPage').addEventListener('change', (e) => {
        itemsPerPage = parseInt(e.target.value);
        currentPage = 1;
        renderizarProveedores();
    });
    
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
            proveedoresFiltrados = [...proveedores]; // Inicialmente todos
            renderizarProveedores();
            console.log(`[Proveedores] ${proveedores.length} proveedores cargados`);
        } else {
            throw new Error(data.error || 'Error al cargar proveedores');
        }
    } catch (error) {
        console.error('[Proveedores] Error:', error);
        mostrarNotificacion('Error al cargar proveedores: ' + error.message, 'error');
        
        document.getElementById('proveedoresList').innerHTML = `
            <tr>
                <td colspan="5" style="text-align: center; padding: 40px; color: #dc3545;">
                    <i class="fas fa-exclamation-triangle" style="font-size: 48px;"></i>
                    <p>Error al cargar proveedores</p>
                </td>
            </tr>
        `;
    }
}

// ============================================================================
// RENDERIZADO
// ============================================================================

function renderizarProveedores() {
    const container = document.getElementById('proveedoresList');
    
    if (proveedoresFiltrados.length === 0) {
        container.innerHTML = `
            <tr>
                <td colspan="5" style="text-align: center; padding: 40px;">
                    <i class="fas fa-users" style="font-size: 48px; color: #ccc; display: block; margin-bottom: 10px;"></i>
                    <p>No hay proveedores que mostrar</p>
                    ${proveedores.length === 0 ? `<button class="btn btn-primary" onclick="document.getElementById('btnNuevoProveedor').click()">
                        <i class="fas fa-plus"></i> Crear primer proveedor
                    </button>` : ''}
                </td>
            </tr>
        `;
        actualizarControlesPaginacion();
        return;
    }
    
    // Calcular paginación
    const totalItems = proveedoresFiltrados.length;
    const totalPages = Math.ceil(totalItems / itemsPerPage);
    
    // Ajustar página actual si se sale de rango
    if (currentPage > totalPages) currentPage = totalPages;
    if (currentPage < 1) currentPage = 1;
    
    const startIndex = (currentPage - 1) * itemsPerPage;
    const endIndex = Math.min(startIndex + itemsPerPage, totalItems);
    const itemsPagina = proveedoresFiltrados.slice(startIndex, endIndex);
    
    container.innerHTML = '';
    
    itemsPagina.forEach(proveedor => {
        const fila = crearFilaProveedor(proveedor);
        container.appendChild(fila);
    });
    
    actualizarControlesPaginacion();
}

function cambiarPagina(delta) {
    const totalPages = Math.ceil(proveedoresFiltrados.length / itemsPerPage);
    const newPage = currentPage + delta;
    
    if (newPage >= 1 && newPage <= totalPages) {
        currentPage = newPage;
        renderizarProveedores();
    }
}

function actualizarControlesPaginacion() {
    const totalItems = proveedoresFiltrados.length;
    const totalPages = Math.ceil(totalItems / itemsPerPage) || 1;
    
    document.getElementById('pageInfo').textContent = `Página ${currentPage} de ${totalPages} (${totalItems} total)`;
    document.getElementById('prevPage').disabled = currentPage === 1;
    document.getElementById('nextPage').disabled = currentPage === totalPages || totalPages === 0;
}

function crearFilaProveedor(proveedor) {
    const tr = document.createElement('tr');
    
    tr.innerHTML = `
        <td>
            <div style="font-weight: 600;">${proveedor.nombre}</div>
        </td>
        <td class="text-mono">${proveedor.nif || '-'}</td>
        <td>
            ${proveedor.email ? `<a href="mailto:${proveedor.email}" onclick="event.stopPropagation()">${proveedor.email}</a>` : '-'}
        </td>
        <td>${proveedor.telefono || '-'}</td>
        <td style="text-align: center;">
            <button class="btn-icon" title="Eliminar" onclick="event.stopPropagation(); eliminarProveedor(${proveedor.id}, '${proveedor.nombre.replace(/'/g, "\\'")}')">
                ✕
            </button>
        </td>
    `;
    
    // Evento Click para abrir detalle (en toda la fila)
    tr.addEventListener('click', () => abrirModalDetalle(proveedor));
    
    return tr;
}

// ============================================================================
// FILTRADO
// ============================================================================

function filtrarProveedores() {
    const busqueda = document.getElementById('busquedaProveedor').value.toLowerCase();
    
    proveedoresFiltrados = proveedores.filter(proveedor => {
        // Filtro de búsqueda
        return !busqueda || 
            proveedor.nombre.toLowerCase().includes(busqueda) ||
            (proveedor.nif && proveedor.nif.toLowerCase().includes(busqueda)) ||
            (proveedor.email && proveedor.email.toLowerCase().includes(busqueda));
    });
    
    // Resetear a primera página al filtrar
    currentPage = 1;
    renderizarProveedores();
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
            <div class="modal-detail-title modal-detail-title-wrapper">
                <h2>${proveedor.nombre}</h2>
                <div class="modal-detail-nif">
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
            <div class="bg-elevated text-muted font-italic">
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
    
    // Asegurar estado inicial de botones
    restaurarBotonesDetalle();
}

function activarEdicionEnDetalle(proveedor) {
    const contenido = document.getElementById('detalleProveedorContenido');
    const footer = document.querySelector('#modalDetalleProveedor .modal-footer');
    
    // Transformar vista a formulario
    contenido.innerHTML = `
        <div class="modal-detail-header">
            <div class="modal-detail-icon">
                <i class="fas fa-edit"></i>
            </div>
            <div class="modal-detail-title w-100">
                <label class="text-small text-muted">Nombre / Razón Social</label>
                <input type="text" id="edit_nombre" value="${proveedor.nombre}" class="form-control text-large text-bold w-100">
                
                <label class="text-small text-muted mt-2" style="display: block;">NIF / CIF</label>
                <input type="text" id="edit_nif" value="${proveedor.nif}" class="form-control text-mono w-100" style="font-size: 1.1em;">
            </div>
        </div>

        <div class="detail-section-title">
            <i class="fas fa-address-card"></i> Información de Contacto
        </div>
        
        <div class="modal-detail-grid">
            <div class="detail-item">
                <label>Email General</label>
                <input type="email" id="edit_email" value="${proveedor.email || ''}" class="form-control" placeholder="ej: info@empresa.com">
            </div>
            <div class="detail-item">
                <label>Email Facturación</label>
                <input type="email" id="edit_email_facturacion" value="${proveedor.email_facturacion || ''}" class="form-control" placeholder="ej: facturas@empresa.com">
            </div>
            <div class="detail-item">
                <label>Teléfono</label>
                <input type="tel" id="edit_telefono" value="${proveedor.telefono || ''}" class="form-control">
            </div>
        </div>

        <div class="detail-section-title">
            <i class="fas fa-map-marked-alt"></i> Dirección
        </div>
        
        <div class="modal-detail-grid grid-3-cols">
            <div class="detail-item" style="grid-column: 1/-1;">
                <label>Calle y Número</label>
                <input type="text" id="edit_direccion" value="${proveedor.direccion || ''}" class="form-control">
            </div>
            <div class="detail-item">
                <label>CP</label>
                <input type="text" id="edit_cp" value="${proveedor.cp || ''}" class="form-control">
            </div>
            <div class="detail-item">
                <label>Población</label>
                <input type="text" id="edit_poblacion" value="${proveedor.poblacion || ''}" class="form-control">
            </div>
            <div class="detail-item">
                <label>Provincia</label>
                <input type="text" id="edit_provincia" value="${proveedor.provincia || ''}" class="form-control">
            </div>
        </div>

        <div class="detail-section-title">
            <i class="fas fa-sticky-note"></i> Notas Internas
        </div>
        <textarea id="edit_notas" class="form-control w-100" rows="3">${proveedor.notas || ''}</textarea>
    `;
    
    // Cambiar botones del footer
    footer.innerHTML = `
        <button type="button" class="btn btn-secondary" onclick="cancelarEdicionDetalle()">
            Cancelar
        </button>
        <button type="button" class="btn btn-success" onclick="guardarEdicionDetalle()">
            Guardar
        </button>
    `;
}

window.cancelarEdicionDetalle = function() {
    // Volver a renderizar la vista de lectura con el proveedor original
    abrirModalDetalle(proveedorSeleccionado);
};

window.guardarEdicionDetalle = async function() {
    const id = proveedorSeleccionado.id;
    const nombre = document.getElementById('edit_nombre').value.trim();
    const nif = document.getElementById('edit_nif').value.trim();
    
    if (!nombre || !nif) {
        mostrarNotificacion('Nombre y NIF son obligatorios', 'error');
        return;
    }
    
    const datos = {
        nombre,
        nif,
        email: document.getElementById('edit_email').value.trim(),
        email_facturacion: document.getElementById('edit_email_facturacion').value.trim(),
        telefono: document.getElementById('edit_telefono').value.trim(),
        direccion: document.getElementById('edit_direccion').value.trim(),
        cp: document.getElementById('edit_cp').value.trim(),
        poblacion: document.getElementById('edit_poblacion').value.trim(),
        provincia: document.getElementById('edit_provincia').value.trim(),
        notas: document.getElementById('edit_notas').value.trim()
    };
    
    try {
        const response = await fetch(`/api/proveedores/${id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(datos)
        });
        
        const data = await response.json();
        
        if (data.success) {
            mostrarNotificacion('Proveedor actualizado correctamente', 'success');
            
            // Actualizar datos locales y recargar lista de fondo
            const proveedorActualizado = { ...proveedorSeleccionado, ...datos };
            proveedores = proveedores.map(p => p.id === id ? proveedorActualizado : p);
            renderizarProveedores(); // Actualizar grid de fondo
            
            // Volver a vista lectura con datos nuevos
            abrirModalDetalle(proveedorActualizado);
        } else {
            throw new Error(data.error || 'Error al guardar');
        }
    } catch (error) {
        console.error('Error guardando:', error);
        mostrarNotificacion('Error: ' + error.message, 'error');
    }
};

function restaurarBotonesDetalle() {
    const footer = document.querySelector('#modalDetalleProveedor .modal-footer');
    footer.innerHTML = `
        <button type="button" class="btn btn-danger" id="btnEliminarDesdeDetalle" style="margin-right: auto;" title="Eliminar">
            <i class="fas fa-trash"></i>
        </button>
        <button type="button" class="btn btn-primary" id="btnEditarDesdeDetalle">
            Editar
        </button>
    `;
    
    // Re-vincular eventos
    document.getElementById('btnEditarDesdeDetalle').addEventListener('click', () => {
        activarEdicionEnDetalle(proveedorSeleccionado);
    });
    document.getElementById('btnEliminarDesdeDetalle').addEventListener('click', () => {
        if (proveedorSeleccionado) {
            eliminarProveedor(proveedorSeleccionado.id, proveedorSeleccionado.nombre);
            cerrarModalDetalle();
        }
    });
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
