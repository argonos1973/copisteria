/**
 * gestion_proveedores.js
 * Gestión de proveedores
 */

import { mostrarNotificacion } from './notificaciones.js';

// Variables globales
let proveedores = [];
let proveedorEditando = null;

// ============================================================================
// INICIALIZACIÓN
// ============================================================================

document.addEventListener('DOMContentLoaded', () => {
    console.log('[Proveedores] Inicializando...');
    
    cargarProveedores();
    configurarEventListeners();
});

function configurarEventListeners() {
    // Botones
    document.getElementById('btnNuevoProveedor').addEventListener('click', () => abrirModal());
    document.getElementById('closeModal').addEventListener('click', cerrarModal);
    document.getElementById('btnCancelarModal').addEventListener('click', cerrarModal);
    document.getElementById('btnGuardarProveedor').addEventListener('click', guardarProveedor);
    
    // Filtros
    document.getElementById('busquedaProveedor').addEventListener('input', filtrarProveedores);
    
    // Cerrar modal al hacer clic fuera
    window.addEventListener('click', (e) => {
        const modal = document.getElementById('modalProveedor');
        if (e.target === modal) {
            cerrarModal();
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
    card.className = 'card';
    
    card.innerHTML = `
        <div class="card-header">
            <div class="card-title">${proveedor.nombre}</div>
        </div>
        <div class="card-body">
            <div class="card-info">
                <i class="fas fa-id-card"></i> <strong>NIF:</strong> ${proveedor.nif}
            </div>
            ${proveedor.email ? `
                <div class="card-info">
                    <i class="fas fa-envelope"></i> ${proveedor.email}
                </div>
            ` : ''}
            ${proveedor.telefono ? `
                <div class="card-info">
                    <i class="fas fa-phone"></i> ${proveedor.telefono}
                </div>
            ` : ''}
            ${proveedor.direccion ? `
                <div class="card-info">
                    <i class="fas fa-map-marker-alt"></i> ${proveedor.direccion}
                </div>
            ` : ''}
        </div>
        <div class="card-actions">
            <button class="btn btn-sm btn-primary" onclick="editarProveedor(${proveedor.id})">
                <i class="fas fa-edit"></i> Editar
            </button>
            <button class="btn btn-sm btn-danger" onclick="eliminarProveedor(${proveedor.id}, '${proveedor.nombre}')">
                <i class="fas fa-trash"></i> Eliminar
            </button>
        </div>
    `;
    
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
            proveedor.nif.toLowerCase().includes(busqueda) ||
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
// MODAL
// ============================================================================

function abrirModal(proveedor = null) {
    proveedorEditando = proveedor;
    
    const modal = document.getElementById('modalProveedor');
    const title = document.getElementById('modalTitle');
    
    if (proveedor) {
        title.textContent = 'Editar Proveedor';
        document.getElementById('proveedorId').value = proveedor.id;
        document.getElementById('nombre').value = proveedor.nombre;
        document.getElementById('nif').value = proveedor.nif;
        document.getElementById('email').value = proveedor.email || '';
        document.getElementById('telefono').value = proveedor.telefono || '';
        document.getElementById('direccion').value = proveedor.direccion || '';
        document.getElementById('notas').value = proveedor.notas || '';
    } else {
        title.textContent = 'Nuevo Proveedor';
        document.getElementById('formProveedor').reset();
        document.getElementById('proveedorId').value = '';
    }
    
    modal.style.display = 'block';
}

function cerrarModal() {
    document.getElementById('modalProveedor').style.display = 'none';
    proveedorEditando = null;
}

window.editarProveedor = function(id) {
    const proveedor = proveedores.find(p => p.id === id);
    if (proveedor) {
        abrirModal(proveedor);
    }
};

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
        telefono: document.getElementById('telefono').value.trim(),
        direccion: document.getElementById('direccion').value.trim(),
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
            cerrarModal();
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
    if (!confirm(`¿Estás seguro de que deseas eliminar el proveedor "${nombre}"?\n\nEsta acción no se puede deshacer.`)) {
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

// Versión actualizada - referencias a 'activo' eliminadas
