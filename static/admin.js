
// Helper para convertir hex a rgba
function hexToRgba(hex, alpha) {
    const r = parseInt(hex.slice(1, 3), 16);
    const g = parseInt(hex.slice(3, 5), 16);
    const b = parseInt(hex.slice(5, 7), 16);
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

// Variables globales

// ============= SISTEMA DE PREVIEW EN TIEMPO REAL =============

function hexToRgb(hex) {
    if (!hex) return '0, 0, 0';
    const r = parseInt(hex.slice(1, 3), 16);
    const g = parseInt(hex.slice(3, 5), 16);
    const b = parseInt(hex.slice(5, 7), 16);
    return `${r}, ${g}, ${b}`;
}

function actualizarPreviewEnTiempoReal(colores) {
    const root = document.documentElement;
    
    // COLORES PRINCIPALES
    if (colores.color_app_bg) {
        root.style.setProperty('--preview-color-app-bg', colores.color_app_bg);
    }
    if (colores.color_primario) {
        root.style.setProperty('--preview-color-primario', colores.color_primario);
        root.style.setProperty('--preview-color-primario-rgb', hexToRgb(colores.color_primario));
    }
    if (colores.color_secundario) {
        root.style.setProperty('--preview-color-secundario', colores.color_secundario);
        root.style.setProperty('--preview-color-secundario-rgb', hexToRgb(colores.color_secundario));
    }
    
    // COLORES DE ESTADO
    if (colores.color_success) {
        root.style.setProperty('--preview-color-success', colores.color_success);
        root.style.setProperty('--preview-color-success-rgb', hexToRgb(colores.color_success));
    }
    if (colores.color_warning) {
        root.style.setProperty('--preview-color-warning', colores.color_warning);
        root.style.setProperty('--preview-color-warning-rgb', hexToRgb(colores.color_warning));
    }
    if (colores.color_danger) {
        root.style.setProperty('--preview-color-danger', colores.color_danger);
        root.style.setProperty('--preview-color-danger-rgb', hexToRgb(colores.color_danger));
    }
    if (colores.color_info) {
        root.style.setProperty('--preview-color-info', colores.color_info);
        root.style.setProperty('--preview-color-info-rgb', hexToRgb(colores.color_info));
    }
    
    // COLORES DE BOTONES
    if (colores.color_button) {
        root.style.setProperty('--preview-color-button', colores.color_button);
    }
    if (colores.color_button_hover) {
        root.style.setProperty('--preview-color-button-hover', colores.color_button_hover);
    }
    if (colores.color_button_text) {
        root.style.setProperty('--preview-color-button-text', colores.color_button_text);
    }
    
    // COLORES DE HEADER
    if (colores.color_header_bg) {
        root.style.setProperty('--preview-color-header-bg', colores.color_header_bg);
    }
    if (colores.color_header_text) {
        root.style.setProperty('--preview-color-header-text', colores.color_header_text);
    }
    
    // COLORES DE TABLA
    if (colores.color_grid_header) {
        root.style.setProperty('--preview-color-grid-header', colores.color_grid_header);
    }
    
    // COLORES DE INPUTS
    if (colores.color_input_bg) {
        root.style.setProperty('--preview-color-input-bg', colores.color_input_bg);
    }
    if (colores.color_input_text) {
        root.style.setProperty('--preview-color-input-text', colores.color_input_text);
    }
    if (colores.color_input_border) {
        root.style.setProperty('--preview-color-input-border', colores.color_input_border);
    }
    
    // COLORES DE SELECTS
    if (colores.color_select_bg) {
        root.style.setProperty('--preview-color-select-bg', colores.color_select_bg);
    }
    if (colores.color_select_text) {
        root.style.setProperty('--preview-color-select-text', colores.color_select_text);
    }
    if (colores.color_select_border) {
        root.style.setProperty('--preview-color-select-border', colores.color_select_border);
    }
    
    // COLORES DE DISABLED
    if (colores.color_disabled_bg) {
        root.style.setProperty('--preview-color-disabled-bg', colores.color_disabled_bg);
    }
    if (colores.color_disabled_text) {
        root.style.setProperty('--preview-color-disabled-text', colores.color_disabled_text);
    }
    
    // COLORES DE SUBMENU
    if (colores.color_submenu_bg) {
        root.style.setProperty('--preview-color-submenu-bg', colores.color_submenu_bg);
    }
    if (colores.color_submenu_text) {
        root.style.setProperty('--preview-color-submenu-text', colores.color_submenu_text);
    }
    if (colores.color_submenu_hover) {
        root.style.setProperty('--preview-color-submenu-hover', colores.color_submenu_hover);
    }
    
    // COLORES DE GRIDS E ICONOS
    if (colores.color_grid_bg) {
        root.style.setProperty('--preview-color-grid-bg', colores.color_grid_bg);
    }
    if (colores.color_grid_text) {
        root.style.setProperty('--preview-color-grid-text', colores.color_grid_text);
    }
    if (colores.color_icon) {
        root.style.setProperty('--preview-color-icon', colores.color_icon);
        root.style.setProperty('--preview-color-icon-rgb', hexToRgb(colores.color_icon));
    }
}

function renderizarListaPlantillasPreview(prefijo = '') {
    const contenedor = document.getElementById('plantillas-list-preview');
    if (!contenedor) return;
    
    let html = '';
    Object.keys(plantillasColores).forEach(key => {
        const plantilla = plantillasColores[key];
        const isPersonalizada = key.startsWith('personalizada_');
        html += `<div class="plantilla-card" data-template="${key}" onclick="aplicarPlantillaConPreview('${key}', '${prefijo}')">
            <div style="font-weight: 600; font-size: 11px; margin-bottom: 5px; display: flex; align-items: center; justify-content: space-between;">
                <span>${plantilla.nombre}</span>
                ${isPersonalizada ? '<i class="fas fa-star" style="color: #f39c12; font-size: 10px;"></i>' : ''}
            </div>
            <div style="display: flex; gap: 3px; margin-bottom: 4px;">
                <div style="width: 20px; height: 20px; border-radius: 2px; background: ${plantilla.color_primario}; border: 1px solid rgba(0,0,0,0.1);"></div>
                <div style="width: 20px; height: 20px; border-radius: 2px; background: ${plantilla.color_secundario}; border: 1px solid rgba(0,0,0,0.1);"></div>
                <div style="width: 20px; height: 20px; border-radius: 2px; background: ${plantilla.color_success || '#27ae60'}; border: 1px solid rgba(0,0,0,0.1);"></div>
                <div style="width: 20px; height: 20px; border-radius: 2px; background: ${plantilla.color_warning || '#f39c12'}; border: 1px solid rgba(0,0,0,0.1);"></div>
            </div>
            <div style="font-size: 9px; color: #666; line-height: 1.3;">${plantilla.descripcion || ''}</div>
        </div>`;
    });
    contenedor.innerHTML = html;
}

function aplicarPlantillaConPreview(nombrePlantilla, prefijo = '') {
    const plantilla = plantillasColores[nombrePlantilla];
    if (!plantilla) return;
    
    document.querySelectorAll('.plantilla-card').forEach(card => {
        card.classList.toggle('active', card.dataset.template === nombrePlantilla);
    });
    
    // Actualizar CSS Variables (preview nuevo)
    actualizarPreviewEnTiempoReal(plantilla);
    
    // Actualizar inputs de color
    Object.keys(plantilla).forEach(campo => {
        if (campo.startsWith('color_')) {
            const input = document.getElementById(prefijo + campo);
            if (input) input.value = plantilla[campo];
        }
    });
    
    // CRÍTICO: También actualizar el preview viejo (IDs directos)
    setTimeout(() => {
        actualizarVistaPrevia();
    }, 50);
    
    plantillaBaseActual = nombrePlantilla;
    coloresOriginalesPlantilla = { ...plantilla };
}

function inicializarPreviewEnTiempoReal(prefijo = '') {
    renderizarListaPlantillasPreview(prefijo);
    
    // Los inputs ya tienen oninput="actualizarVistaPrevia()" en el HTML
    // No añadimos event listeners duplicados para evitar loops infinitos
    
    const selectPlantilla = document.getElementById(prefijo + 'plantilla_base');
    if (selectPlantilla && selectPlantilla.value) {
        setTimeout(() => aplicarPlantillaConPreview(selectPlantilla.value, prefijo), 100);
    }
}
let usuarios = [];
let empresas = [];
let modulos = [];

// Inicialización
document.addEventListener('DOMContentLoaded', () => {
    cargarEstadisticas();
    cargarUsuarios();
    cargarEmpresas();
    cargarModulos();
    inicializarTabs();
});

// Tabs
function inicializarTabs() {
    document.querySelectorAll('.tab').forEach(tab => {
        tab.addEventListener('click', () => {
            const tabName = tab.dataset.tab;
            
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            
            document.querySelectorAll('.tab-content').forEach(content => {
                content.classList.remove('active');
            });
            document.getElementById(`tab-${tabName}`).classList.add('active');
            
            // Cargar datos específicos de cada pestaña
            if (tabName === 'empresas' && empresas.length === 0) {
                cargarEmpresas();
            }
        });
    });
}

// Estadísticas
async function cargarEstadisticas() {
    try {
        const response = await fetch('/api/admin/stats');
        if (!response.ok) throw new Error('Error cargando estadísticas');
        
        const stats = await response.json();
        
        document.getElementById('total-usuarios').textContent = stats.total_usuarios || 0;
        document.getElementById('total-empresas').textContent = stats.total_empresas || 0;
        document.getElementById('total-modulos').textContent = stats.total_modulos || 0;
        document.getElementById('total-permisos').textContent = stats.total_permisos || 0;
    } catch (error) {
        console.error('Error:', error);
    }
}

// USUARIOS
async function cargarUsuarios() {
    try {
        const response = await fetch('/api/admin/usuarios');
        if (!response.ok) throw new Error('Error cargando usuarios');
        
        usuarios = await response.json();
        mostrarUsuarios(usuarios);
        
        // Actualizar select de permisos
        const select = document.getElementById('select-usuario-permisos');
        select.innerHTML = '<option value="">-- Seleccione --</option>';
        usuarios.forEach(u => {
            select.innerHTML += `<option value="${u.id}">${u.nombre_completo} (${u.username})</option>`;
        });
        
    } catch (error) {
        console.error('Error:', error);
        document.getElementById('tabla-usuarios').innerHTML = 
            '<div class="empty-state"><i class="fas fa-exclamation-circle"></i><p>Error cargando usuarios</p></div>';
    }
}

function mostrarUsuarios(lista) {
    const container = document.getElementById('tabla-usuarios');
    
    if (lista.length === 0) {
        container.innerHTML = '<div class="empty-state"><i class="fas fa-users"></i><p>No hay usuarios registrados</p></div>';
        return;
    }

    let html = `
        <table>
            <thead>
                <tr>
                    <th>Usuario</th>
                    <th>Nombre</th>
                    <th>Email</th>
                    <th>Empresas</th>
                    <th>Estado</th>
                    <th>Rol</th>
                    <th>Acciones</th>
                </tr>
            </thead>
            <tbody>
    `;

    lista.forEach(usuario => {
        const estado = usuario.activo ? '<span class="badge badge-success">Activo</span>' : '<span class="badge badge-danger">Inactivo</span>';
        const rol = usuario.es_superadmin ? '<span class="badge badge-info">Superadmin</span>' : '<span class="badge">Usuario</span>';
        
        html += `
            <tr>
                <td><strong>${usuario.username}</strong></td>
                <td>${usuario.nombre_completo}</td>
                <td>${usuario.email || '-'}</td>
                <td>${usuario.empresas || 'Sin asignar'}</td>
                <td>${estado}</td>
                <td>${rol}</td>
                <td>
                    <button class="btn btn-primary btn-small" onclick="editarUsuario(${usuario.id})">
                        <i class="fas fa-edit"></i>
                    </button>
                    <button class="btn btn-warning btn-small" onclick="gestionarEmpresas(${usuario.id})">
                        <i class="fas fa-building"></i>
                    </button>
                    <button class="btn btn-danger btn-small" onclick="eliminarUsuario(${usuario.id}, '${usuario.username}')">
                        <i class="fas fa-trash"></i>
                    </button>
                </td>
            </tr>
        `;
    });

    html += '</tbody></table>';
    container.innerHTML = html;
}

function filtrarUsuarios() {
    const busqueda = document.getElementById('buscar-usuario').value.toLowerCase();
    const filtrados = usuarios.filter(u => 
        u.username.toLowerCase().includes(busqueda) ||
        u.nombre_completo.toLowerCase().includes(busqueda) ||
        (u.email && u.email.toLowerCase().includes(busqueda))
    );
    mostrarUsuarios(filtrados);
}

function mostrarModalNuevoUsuario() {
    document.getElementById('modal-usuario-titulo').textContent = 'Nuevo Usuario';
    document.getElementById('formUsuario').reset();
    document.getElementById('usuario-id').value = '';
    document.getElementById('usuario-password').required = true;
    document.getElementById('usuario-activo').checked = true;
    document.getElementById('modalUsuario').classList.add('active');
}

function cerrarModalUsuario() {
    document.getElementById('modalUsuario').classList.remove('active');
    document.getElementById('alert-usuario').innerHTML = '';
}

async function guardarUsuario(event) {
    event.preventDefault();
    
    const id = document.getElementById('usuario-id').value;
    const data = {
        username: document.getElementById('usuario-username').value,
        password: document.getElementById('usuario-password').value,
        nombre_completo: document.getElementById('usuario-nombre').value,
        email: document.getElementById('usuario-email').value,
        telefono: document.getElementById('usuario-telefono').value,
        es_superadmin: document.getElementById('usuario-superadmin').checked ? 1 : 0,
        activo: document.getElementById('usuario-activo').checked ? 1 : 0
    };

    try {
        const url = id ? `/api/admin/usuarios/${id}` : '/api/admin/usuarios';
        const method = id ? 'PUT' : 'POST';
        
        const response = await fetch(url, {
            method: method,
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(data)
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Error guardando usuario');
        }

        const result = await response.json();
        
        document.getElementById('alert-usuario').innerHTML = 
            `<div class="alert alert-success">${result.mensaje}</div>`;
        
        setTimeout(() => {
            cerrarModalUsuario();
            cargarUsuarios();
            cargarEstadisticas();
        }, 1500);
        
    } catch (error) {
        document.getElementById('alert-usuario').innerHTML = 
            `<div class="alert alert-error">${error.message}</div>`;
    }
}

async function editarUsuario(id) {
    const usuario = usuarios.find(u => u.id === id);
    if (!usuario) return;

    document.getElementById('modal-usuario-titulo').textContent = 'Editar Usuario';
    document.getElementById('usuario-id').value = usuario.id;
    document.getElementById('usuario-username').value = usuario.username;
    document.getElementById('usuario-password').value = '';
    document.getElementById('usuario-password').required = false;
    document.getElementById('usuario-nombre').value = usuario.nombre_completo;
    document.getElementById('usuario-email').value = usuario.email || '';
    document.getElementById('usuario-telefono').value = usuario.telefono || '';
    document.getElementById('usuario-superadmin').checked = usuario.es_superadmin === 1;
    document.getElementById('usuario-activo').checked = usuario.activo === 1;
    
    document.getElementById('modalUsuario').classList.add('active');
}

async function eliminarUsuario(id, username) {
    if (!confirm(`¿Estás seguro de eliminar el usuario "${username}"?`)) return;

    try {
        const response = await fetch(`/api/admin/usuarios/${id}`, {
            method: 'DELETE'
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Error eliminando usuario');
        }

        alert('Usuario eliminado correctamente');
        cargarUsuarios();
        cargarEstadisticas();
        
    } catch (error) {
        alert(error.message);
    }
}


// GESTIÓN EMPRESAS USUARIO
async function gestionarEmpresas(usuarioId) {
    document.getElementById('usuario-empresas-id').value = usuarioId;
    
    try {
        const response = await fetch(`/api/admin/usuarios/${usuarioId}/empresas`);
        if (!response.ok) throw new Error('Error cargando empresas del usuario');
        
        const empresasUsuario = await response.json();
        
        let html = '<div style="max-height: 400px; overflow-y: auto;">';
        
        empresas.forEach(empresa => {
            const asignada = empresasUsuario.find(e => e.id === empresa.id);
            const checked = asignada ? 'checked' : '';
            const rol = asignada ? asignada.rol : 'usuario';
            const admin = asignada && asignada.es_admin_empresa ? 'checked' : '';
            
            html += `
                <div style="padding: 15px; border-bottom: 1px solid #ecf0f1;">
                    <div class="checkbox-group">
                        <input type="checkbox" id="empresa-${empresa.id}" ${checked} 
                            onchange="toggleEmpresa(${usuarioId}, ${empresa.id}, this.checked)">
                        <label for="empresa-${empresa.id}"><strong>${empresa.nombre}</strong></label>
                    </div>
                    <div style="margin-left: 30px; margin-top: 10px;">
                        <select id="rol-${empresa.id}" style="width: 150px; margin-right: 10px;" ${!checked ? 'disabled' : ''}>
                            <option value="usuario" ${rol === 'usuario' ? 'selected' : ''}>Usuario</option>
                            <option value="admin" ${rol === 'admin' ? 'selected' : ''}>Admin</option>
                            <option value="lectura" ${rol === 'lectura' ? 'selected' : ''}>Lectura</option>
                        </select>
                        <label>
                            <input type="checkbox" id="admin-${empresa.id}" ${admin} ${!checked ? 'disabled' : ''}>
                            Admin de empresa
                        </label>
                    </div>
                </div>
            `;
        });
        
        html += '</div>';
        html += `
            <div style="margin-top: 20px; display: flex; gap: 10px;">
                <button class="btn btn-success" onclick="guardarEmpresasUsuario(${usuarioId})" style="flex: 1;">
                    <i class="fas fa-save"></i> Guardar
                </button>
                <button class="btn btn-danger" onclick="cerrarModalEmpresas()" style="flex: 1;">
                    <i class="fas fa-times"></i> Cancelar
                </button>
            </div>
        `;
        
        document.getElementById('lista-empresas-usuario').innerHTML = html;
        document.getElementById('modalEmpresas').classList.add('active');
        
    } catch (error) {
        console.error('Error:', error);
        alert('Error cargando empresas del usuario');
    }
}

async function toggleEmpresa(usuarioId, empresaId, asignar) {
    const rolSelect = document.getElementById(`rol-${empresaId}`);
    const adminCheck = document.getElementById(`admin-${empresaId}`);
    
    if (asignar) {
        rolSelect.disabled = false;
        adminCheck.disabled = false;
        
        // Asignar empresa
        try {
            const response = await fetch(`/api/admin/usuarios/${usuarioId}/empresas`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    empresa_id: empresaId,
                    rol: rolSelect.value,
                    es_admin_empresa: adminCheck.checked ? 1 : 0
                })
            });
            
            if (!response.ok) {
                throw new Error('Error asignando empresa');
            }
        } catch (error) {
            console.error('Error:', error);
            document.getElementById(`empresa-${empresaId}`).checked = false;
        }
    } else {
        rolSelect.disabled = true;
        adminCheck.disabled = true;
        
        // Desasignar empresa
        try {
            const response = await fetch(`/api/admin/usuarios/${usuarioId}/empresas/${empresaId}`, {
                method: 'DELETE'
            });
            
            if (!response.ok) {
                throw new Error('Error desasignando empresa');
            }
        } catch (error) {
            console.error('Error:', error);
            document.getElementById(`empresa-${empresaId}`).checked = true;
        }
    }
}

function cerrarModalEmpresas() {
    document.getElementById('modalEmpresas').classList.remove('active');
    cargarUsuarios();
}

async function guardarEmpresasUsuario(usuarioId) {
    alert('Empresas actualizadas correctamente');
    cerrarModalEmpresas();
}

// MÓDULOS
async function cargarModulos() {
    try {
        const response = await fetch('/api/admin/modulos');
        if (!response.ok) throw new Error('Error cargando módulos');
        
        modulos = await response.json();
        mostrarModulos(modulos);
        
    } catch (error) {
        console.error('Error:', error);
        document.getElementById('tabla-modulos').innerHTML = 
            '<div class="empty-state"><i class="fas fa-exclamation-circle"></i><p>Error cargando módulos</p></div>';
    }
}

function mostrarModulos(lista) {
    const container = document.getElementById('tabla-modulos');
    
    if (lista.length === 0) {
        container.innerHTML = '<div class="empty-state"><i class="fas fa-th-large"></i><p>No hay módulos registrados</p></div>';
        return;
    }

    let html = `
        <table>
            <thead>
                <tr>
                    <th>Código</th>
                    <th>Nombre</th>
                    <th>Ruta</th>
                    <th>Orden</th>
                    <th>Estado</th>
                </tr>
            </thead>
            <tbody>
    `;

    lista.forEach(modulo => {
        const estado = modulo.activo ? '<span class="badge badge-success">Activo</span>' : '<span class="badge badge-danger">Inactivo</span>';
        
        html += `
            <tr>
                <td><strong>${modulo.codigo}</strong></td>
                <td>${modulo.nombre}</td>
                <td><code>${modulo.ruta}</code></td>
                <td>${modulo.orden}</td>
                <td>${estado}</td>
            </tr>
        `;
    });

    html += '</tbody></table>';
    container.innerHTML = html;
}

// PERMISOS
async function cargarPermisosUsuario() {
    const usuarioId = document.getElementById('select-usuario-permisos').value;
    const empresaId = document.getElementById('select-empresa-permisos').value;
    
    const container = document.getElementById('matriz-permisos');
    
    if (!usuarioId || !empresaId) {
        container.innerHTML = '<p style="text-align: center; color: #7f8c8d; margin-top: 20px;">Seleccione un usuario y una empresa</p>';
        return;
    }
    
    try {
        const response = await fetch(`/api/admin/usuarios/${usuarioId}/permisos?empresa_id=${empresaId}`);
        if (!response.ok) throw new Error('Error cargando permisos');
        
        const permisos = await response.json();
        mostrarMatrizPermisos(usuarioId, empresaId, permisos);
        
    } catch (error) {
        console.error('Error:', error);
        container.innerHTML = '<div class="empty-state"><i class="fas fa-exclamation-circle"></i><p>Error cargando permisos</p></div>';
    }
}

function mostrarMatrizPermisos(usuarioId, empresaId, permisos) {
    const container = document.getElementById('matriz-permisos');
    
    let html = '<div class="permissions-grid">';
    
    // Header
    html += `
        <div class="permission-row header">
            <div>Módulo</div>
            <div style="text-align: center;">Ver</div>
            <div style="text-align: center;">Crear</div>
            <div style="text-align: center;">Editar</div>
            <div style="text-align: center;">Eliminar</div>
            <div style="text-align: center;">Anular</div>
            <div style="text-align: center;">Exportar</div>
        </div>
    `;
    
    // Filas
    modulos.forEach(modulo => {
        const permiso = permisos.find(p => p.modulo_codigo === modulo.codigo) || {};
        
        html += `
            <div class="permission-row">
                <div><strong>${modulo.nombre}</strong></div>
                <div style="text-align: center;">
                    <input type="checkbox" ${permiso.puede_ver ? 'checked' : ''} 
                        onchange="actualizarPermiso(${usuarioId}, ${empresaId}, '${modulo.codigo}', 'puede_ver', this.checked)">
                </div>
                <div style="text-align: center;">
                    <input type="checkbox" ${permiso.puede_crear ? 'checked' : ''} 
                        onchange="actualizarPermiso(${usuarioId}, ${empresaId}, '${modulo.codigo}', 'puede_crear', this.checked)">
                </div>
                <div style="text-align: center;">
                    <input type="checkbox" ${permiso.puede_editar ? 'checked' : ''} 
                        onchange="actualizarPermiso(${usuarioId}, ${empresaId}, '${modulo.codigo}', 'puede_editar', this.checked)">
                </div>
                <div style="text-align: center;">
                    <input type="checkbox" ${permiso.puede_eliminar ? 'checked' : ''} 
                        onchange="actualizarPermiso(${usuarioId}, ${empresaId}, '${modulo.codigo}', 'puede_eliminar', this.checked)">
                </div>
                <div style="text-align: center;">
                    <input type="checkbox" ${permiso.puede_anular ? 'checked' : ''} 
                        onchange="actualizarPermiso(${usuarioId}, ${empresaId}, '${modulo.codigo}', 'puede_anular', this.checked)">
                </div>
                <div style="text-align: center;">
                    <input type="checkbox" ${permiso.puede_exportar ? 'checked' : ''} 
                        onchange="actualizarPermiso(${usuarioId}, ${empresaId}, '${modulo.codigo}', 'puede_exportar', this.checked)">
                </div>
            </div>
        `;
    });
    
    html += '</div>';
    container.innerHTML = html;
}

async function actualizarPermiso(usuarioId, empresaId, moduloCodigo, campo, valor) {
    try {
        // Obtener permisos actuales
        const response = await fetch(`/api/admin/usuarios/${usuarioId}/permisos?empresa_id=${empresaId}`);
        const permisos = await response.json();
        const permisoActual = permisos.find(p => p.modulo_codigo === moduloCodigo) || {};
        
        // Actualizar permiso
        const data = {
            empresa_id: empresaId,
            modulo_codigo: moduloCodigo,
            puede_ver: permisoActual.puede_ver || 0,
            puede_crear: permisoActual.puede_crear || 0,
            puede_editar: permisoActual.puede_editar || 0,
            puede_eliminar: permisoActual.puede_eliminar || 0,
            puede_anular: permisoActual.puede_anular || 0,
            puede_exportar: permisoActual.puede_exportar || 0
        };
        // end sw object marker
        data[campo] = valor ? 1 : 0;
        
        const updateResponse = await fetch(`/api/admin/usuarios/${usuarioId}/permisos`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(data)
        });
        
        if (!updateResponse.ok) {
            throw new Error('Error actualizando permiso');
        }
        
        cargarEstadisticas();
        
    } catch (error) {
        console.error('Error:', error);
        alert('Error actualizando permiso');
    }
}

// ==================== GESTIÓN DE EMPRESAS ====================


async function cargarEmpresas() {
    try {
        const response = await fetch('/api/empresas');
        if (!response.ok) throw new Error('Error cargando empresas');
        
        empresas = await response.json();
        renderizarTablaEmpresas(empresas);
        
        // Actualizar select de permisos
        const selectEmpresa = document.getElementById('select-empresa-permisos');
        if (selectEmpresa) {
            selectEmpresa.innerHTML = '<option value="">-- Seleccione --</option>';
            empresas.forEach(e => {
                selectEmpresa.innerHTML += `<option value="${e.id}">${e.nombre}</option>`;
            });
        }
        
    } catch (error) {
        console.error('Error:', error);
        document.getElementById('tabla-empresas').innerHTML = `
            <div class="alert alert-error">
                <i class="fas fa-exclamation-triangle"></i> Error cargando empresas
            </div>
        `;
    }
}

function renderizarTablaEmpresas(empresas) {
    const container = document.getElementById('tabla-empresas');
    
    if (empresas.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-building"></i>
                <p>No hay empresas registradas</p>
            </div>
        `;
        return;
    }
    
    let html = `
        <table class="data-table">
            <thead>
                <tr>
                    <th>Logo</th>
                    <th>Código</th>
                    <th>Nombre</th>
                    <th>CIF</th>
                    <th>BD</th>
                    <th>Estado</th>
                    <th>Acciones</th>
                </tr>
            </thead>
            <tbody>
    `;
    
    empresas.forEach(emp => {
        html += `
            <tr>
                <td>
                    ${emp.logo_header ? 
                        `<img src="/static/logos/${emp.logo_header}" style="width: 40px; height: 40px; object-fit: contain;" alt="Logo">` :
                        `<div style="width: 40px; height: 40px; background: ${emp.color_primario || '#2c3e50'}; border-radius: 5px; display: flex; align-items: center; justify-content: center; color: white; font-weight: bold;">${emp.nombre.charAt(0)}</div>`
                    }
                </td>
                <td><code>${emp.codigo}</code></td>
                <td><strong>${emp.nombre}</strong></td>
                <td>${emp.cif || '-'}</td>
                <td><code>${emp.codigo}.db</code></td>
                <td>
                    <span class="badge ${emp.activa ? 'badge-success' : 'badge-danger'}">
                        ${emp.activa ? '✓ Activa' : '✗ Inactiva'}
                    </span>
                </td>
                <td>
                    <button class="btn btn-sm" onclick="verDetallesEmpresa(${emp.id})" title="Ver detalles">
                        <i class="fas fa-eye"></i>
                    </button>
                    <button class="btn btn-sm btn-primary" onclick="editarEmpresa(${emp.id})" title="Editar">
                        <i class="fas fa-edit"></i>
                    </button>
                    <button class="btn btn-sm btn-danger" onclick="eliminarEmpresaCompleta(${emp.id})" title="Eliminar">
                        <i class="fas fa-trash"></i>
                    </button>
                </td>
        `;
    });
    
    html += `
            </tbody>
        </table>
    `;
    
    container.innerHTML = html;
}

function filtrarEmpresas() {
    const busqueda = document.getElementById('buscar-empresa').value.toLowerCase();
    const empresasFiltradas = empresas.filter(emp => 
        emp.nombre.toLowerCase().includes(busqueda) ||
        emp.codigo.toLowerCase().includes(busqueda) ||
        (emp.cif && emp.cif.toLowerCase().includes(busqueda))
    );
    renderizarTablaEmpresas(empresasFiltradas);
}

function mostrarModalNuevaEmpresa() {
    const modalHTML = `
        <div id="modalNuevaEmpresa" class="modal active">
            <div class="modal-content" style="max-width: 900px; max-height: 90vh; overflow-y: auto;">
                <div class="modal-header">
                    <h2><i class="fas fa-building"></i> Nueva Empresa</h2>
                    <span class="close" onclick="cerrarModalEmpresa()">&times;</span>
                </div>
                
                <form id="formNuevaEmpresa" enctype="multipart/form-data">
                    <h3 style="margin-top: 0; color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px;">
                        <i class="fas fa-info-circle"></i> Información Básica
                    </h3>
                    
                    <div class="form-row" style="display: grid; grid-template-columns: 2fr 1fr; gap: 15px;">
                        <div class="form-group">
                            <label for="nombre_empresa">Nombre Comercial *</label>
                            <input type="text" id="nombre_empresa" name="nombre" required 
                                   placeholder="Ej: Mi Empresa SL">
                            <small>Se usará para el código (primeros 5 caracteres)</small>
                        </div>
                        
                        <div class="form-group">
                            <label for="cif_empresa">CIF/NIF *</label>
                            <input type="text" id="cif_empresa" name="cif" required 
                                   placeholder="Ej: B12345678">
                        </div>
                    </div>
                    
                    <div class="form-group">
                        <label for="razon_social_empresa">Razón Social *</label>
                        <input type="text" id="razon_social_empresa" name="razon_social" required 
                               placeholder="Ej: MI EMPRESA SOCIEDAD LIMITADA">
                        <small>Nombre legal completo de la empresa (aparecerá en facturas)</small>
                    </div>
                    
                    <h3 style="margin-top: 25px; color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px;">
                        <i class="fas fa-map-marker-alt"></i> Dirección Fiscal
                    </h3>
                    
                    <div class="form-group">
                        <label for="direccion_empresa">Dirección Completa *</label>
                        <input type="text" id="direccion_empresa" name="direccion" required 
                               placeholder="Ej: Calle Principal, 123, 3º B">
                    </div>
                    
                    <div class="form-row" style="display: grid; grid-template-columns: 1fr 2fr 2fr; gap: 15px;">
                        <div class="form-group">
                            <label for="cp_empresa">Código Postal *</label>
                            <input type="text" id="cp_empresa" name="codigo_postal" required 
                                   placeholder="Ej: 28001">
                        </div>
                        
                        <div class="form-group">
                            <label for="ciudad_empresa">Ciudad *</label>
                            <input type="text" id="ciudad_empresa" name="ciudad" required 
                                   placeholder="Ej: Madrid">
                        </div>
                        
                        <div class="form-group">
                            <label for="provincia_empresa">Provincia *</label>
                            <input type="text" id="provincia_empresa" name="provincia" required 
                                   placeholder="Ej: Madrid">
                        </div>
                    </div>
                    
                    <h3 style="margin-top: 25px; color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px;">
                        <i class="fas fa-address-book"></i> Datos de Contacto
                    </h3>
                    
                    <div class="form-row" style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px;">
                        <div class="form-group">
                            <label for="telefono_empresa">Teléfono *</label>
                            <input type="text" id="telefono_empresa" name="telefono" required 
                                   placeholder="Ej: 912345678">
                        </div>
                        
                        <div class="form-group">
                            <label for="email_empresa">Email *</label>
                            <input type="email" id="email_empresa" name="email" required 
                                   placeholder="Ej: info@miempresa.com">
                        </div>
                    </div>
                    
                    <div class="form-group">
                        <label for="web_empresa">Sitio Web</label>
                        <input type="text" id="web_empresa" name="web" 
                               placeholder="Ej: www.miempresa.com">
                    </div>
                    
                    <h3 style="margin-top: 25px; color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px;">
                        <i class="fas fa-palette"></i> Branding
                    </h3>
                    
                    <div class="form-group">
                        <label for="logo_empresa">Logo de la Empresa</label>
                        <input type="file" id="logo_empresa" name="logo" accept="image/*">
                        <small>Formatos: PNG, JPG, SVG (máx. 2MB). Se usará en facturas y documentos.</small>
                    </div>
                    
                    <div class="form-row" style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px;">
                        <div class="form-group">
                            <label for="color_primario_empresa">Color Primario</label>
                            <input type="color" id="color_primario_empresa" name="color_primario" value="#2c3e50">
                        </div>
                        
                        <div class="form-group">
                            <label for="color_secundario_empresa">Color Secundario</label>
                            <input type="color" id="color_secundario_empresa" name="color_secundario" value="#3498db">
                        </div>
                    </div>
                    
                    <div class="modal-actions" style="margin-top: 25px; padding-top: 15px; border-top: 1px solid #dddddd;">
                        <button type="button" class="btn" onclick="cerrarModalEmpresa()">Cancelar</button>
                        <button type="submit" class="btn btn-primary">
                            <i class="fas fa-save"></i> Crear Empresa
                        </button>
                    </div>
                </form>
            </div>
        </div>
    `;
    
    document.body.insertAdjacentHTML('beforeend', modalHTML);
    
    document.getElementById('formNuevaEmpresa').addEventListener('submit', async (e) => {
        e.preventDefault();
        await crearEmpresa(e.target);
    });
}
function cerrarModalEmpresa() {
    const modal = document.getElementById('modalNuevaEmpresa');
    if (modal) modal.remove();
}

async function crearEmpresa(form) {
    const formData = new FormData(form);
    const submitBtn = form.querySelector('button[type="submit"]');
    const originalText = submitBtn.innerHTML;
    
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Creando...';
    
    try {
        const response = await fetch('/api/empresas', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (response.ok) {
            mostrarNotificacion(data.mensaje || 'Empresa creada exitosamente', 'success');
            cerrarModalEmpresa();
            cargarEmpresas();
        } else {
            mostrarNotificacion(data.error || 'Error creando empresa', 'error');
        }
        
    } catch (error) {
        console.error('Error:', error);
        mostrarNotificacion('Error de conexión con el servidor', 'error');
    } finally {
        submitBtn.disabled = false;
        submitBtn.innerHTML = originalText;
    }
}

function verDetallesEmpresa(empresaId) {
    const empresa = empresas.find(e => e.id === empresaId);
    if (!empresa) return;
    
    const detalles = `
Detalles de ${empresa.nombre}:

• Código: ${empresa.codigo}
• CIF: ${empresa.cif || 'N/A'}
• Email: ${empresa.email || 'N/A'}
• Teléfono: ${empresa.telefono || 'N/A'}
• Dirección: ${empresa.direccion || 'N/A'}
• Base de Datos: ${empresa.codigo}.db
• Estado: ${empresa.activo ? 'Activa' : 'Inactiva'}
    `;
    
    alert(detalles);
}

async function desactivarEmpresa(empresaId) {
    if (!confirm('¿Desea desactivar esta empresa?')) return;
    
    try {
        const response = await fetch(`/api/empresas/${empresaId}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            mostrarNotificacion('Empresa desactivada', 'success');
            cargarEmpresas();
        } else {
            const data = await response.json();
            mostrarNotificacion(data.error || 'Error desactivando empresa', 'error');
        }
    } catch (error) {
        console.error('Error:', error);
        mostrarNotificacion('Error de conexión', 'error');
    }
}

async function activarEmpresa(empresaId) {
    try {
        const response = await fetch(`/api/empresas/${empresaId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ activo: 1 })
        });
        
        if (response.ok) {
            mostrarNotificacion('Empresa activada', 'success');
            cargarEmpresas();
        } else {
            const data = await response.json();
            mostrarNotificacion(data.error || 'Error activando empresa', 'error');
        }
    } catch (error) {
        console.error('Error:', error);
        mostrarNotificacion('Error de conexión', 'error');
    }
}

// ==================== NOTIFICACIONES ====================

function mostrarNotificacion(mensaje, tipo = 'info') {
    // Buscar contenedor de notificaciones o crearlo
    let container = document.getElementById('notificaciones-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'notificaciones-container';
        container.style.cssText = 'position: fixed; top: 20px; right: 20px; z-index: 9999; max-width: 400px;';
        document.body.appendChild(container);
    }
    
    // Crear notificación
    const notif = document.createElement('div');
    notif.className = `notificacion notif-${tipo}`;
    notif.style.cssText = `
        background: ${tipo === 'success' ? '#d4edda' : tipo === 'error' ? '#f8d7da' : '#d1ecf1'};
        color: ${tipo === 'success' ? '#155724' : tipo === 'error' ? '#721c24' : '#0c5460'};
        border: 1px solid ${tipo === 'success' ? '#c3e6cb' : tipo === 'error' ? '#f5c6cb' : '#bee5eb'};
        padding: 15px 20px;
        border-radius: 5px;
        margin-bottom: 10px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        animation: slideIn 0.3s ease-out;
    `;
    
    notif.innerHTML = `
        <strong>${tipo === 'success' ? '✓' : tipo === 'error' ? '✗' : 'ℹ'}</strong> ${mensaje}
    `;
    
    container.appendChild(notif);
    
    // Auto eliminar después de 5 segundos
    setTimeout(() => {
        notif.style.animation = 'slideOut 0.3s ease-out';
        setTimeout(() => notif.remove(), 300);
    }, 5000);
}

// Agregar animaciones CSS si no existen
if (!document.getElementById('notif-styles')) {
    const style = document.createElement('style');
    style.id = 'notif-styles';
    style.textContent = `
        @keyframes slideIn {
            from { transform: translateX(400px); opacity: 0; }
            to { transform: translateX(0); opacity: 1; }
        }
        @keyframes slideOut {
            from { transform: translateX(0); opacity: 1; }
            to { transform: translateX(400px); opacity: 0; }
        }
    `;
    document.head.appendChild(style);
}

// ==================== EDICIÓN DE EMPRESAS ====================

async function editarEmpresa(empresaId) {
    try {
        // Obtener datos de la empresa
        const response = await fetch(`/api/empresas/${empresaId}`);
        if (!response.ok) throw new Error('Error cargando empresa');
        
        const empresa = await response.json();
        
        // Crear modal de edición
        const modalHTML = `
            <div id="modalEditarEmpresa" class="modal active">
                <div class="modal-content" style="max-width: 1400px; max-height: 90vh; overflow-y: auto;">
                    <div class="modal-header">
                        <h2><i class="fas fa-edit"></i> Editar Empresa: ${empresa.nombre}</h2>
                        <span class="close" onclick="cerrarModalEditarEmpresa()">&times;</span>
                    </div>
                    
                    <form id="formEditarEmpresa">
                        <input type="hidden" name="empresa_id" value="${empresa.id}">
                        
                        <div class="form-row" style="display: grid; grid-template-columns: 80px 250px; gap: 15px;">
                            <div class="form-group">
                                <label>Código</label>
                                <input type="text" value="${empresa.codigo}" disabled style="background: #f0f0f0; text-align: center;" maxlength="5">
                            </div>
                            
                            <div class="form-group">
                                <label for="edit_nombre">Nombre *</label>
                                <input type="text" id="edit_nombre" name="nombre" value="${empresa.nombre || ''}" required>
                            </div>
                        </div>
                        
                        <div class="form-row" style="display: grid; grid-template-columns: 120px 120px 180px 180px 1fr; gap: 12px;">
                            <div class="form-group">
                                <label for="edit_cif">CIF/NIF</label>
                                <input type="text" id="edit_cif" name="cif" value="${empresa.cif || ''}">
                            </div>
                            
                            <div class="form-group">
                                <label for="edit_telefono">Teléfono</label>
                                <input type="text" id="edit_telefono" name="telefono" value="${empresa.telefono || ''}">
                            </div>
                            
                            <div class="form-group">
                                <label for="edit_email">Email</label>
                                <input type="email" id="edit_email" name="email" value="${empresa.email || ''}">
                            </div>
                            
                            <div class="form-group">
                                <label for="edit_web">Web</label>
                                <input type="text" id="edit_web" name="web" value="${empresa.web || ''}">
                            </div>
                            
                            <div class="form-group">
                                <label for="edit_direccion">Dirección</label>
                                <input type="text" id="edit_direccion" name="direccion" value="${empresa.direccion || ''}">
                            </div>
                        </div>
                        
                        <!-- Los inputs de colores ahora están en el editor visual abajo, no se necesitan hidden inputs -->
                        
                        <!-- Plantillas de Colores Predefinidas -->
                        <div style="background: white; padding: 20px; border-radius: 8px; margin: 20px 0; border: 2px solid #dee2e6;">
                            <h4 style="margin: 0 0 15px 0; color: #2c3e50; text-align: center;">
                                <i class="fas fa-swatchbook"></i> Plantillas de Colores
                            </h4>
                            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px;">
                                <button type="button" data-plantilla="clasico" onclick="aplicarPlantillaConPreview('clasico', 'edit_'); marcarPlantillaActiva('clasico');" style="padding: 15px; border: 2px solid #1976d2; border-radius: 8px; background: linear-gradient(135deg, #1976d2 0%, #42a5f5 100%); color: white; cursor: pointer; font-weight: bold; transition: transform 0.2s;" onmouseover="this.style.transform='scale(1.05)'" onmouseout="this.style.transform='scale(1)'">
                                    <i class="fab fa-google"></i> Material Design<br><small style="opacity: 0.8;">Limpio y profesional</small>
                                </button>
                                <button type="button" data-plantilla="oscuro" onclick="aplicarPlantillaConPreview('oscuro', 'edit_'); marcarPlantillaActiva('oscuro');" style="padding: 15px; border: 2px solid #282a36; border-radius: 8px; background: linear-gradient(135deg, #282a36 0%, #44475a 100%); color: #f8f8f2; cursor: pointer; font-weight: bold; transition: transform 0.2s;" onmouseover="this.style.transform='scale(1.05)'" onmouseout="this.style.transform='scale(1)'">
                                    <i class="fas fa-moon"></i> Dracula<br><small style="opacity: 0.8;">Oscuro elegante</small>
                                </button>
                                <button type="button" data-plantilla="verde" onclick="aplicarPlantillaConPreview('verde', 'edit_'); marcarPlantillaActiva('verde');" style="padding: 15px; border: 2px solid #2e3440; border-radius: 8px; background: linear-gradient(135deg, #2e3440 0%, #3b4252 100%); color: #eceff4; cursor: pointer; font-weight: bold; transition: transform 0.2s;" onmouseover="this.style.transform='scale(1.05)'" onmouseout="this.style.transform='scale(1)'">
                                    <i class="fas fa-mountain"></i> Nord<br><small style="opacity: 0.8;">Minimalista escandinavo</small>
                                </button>
                                <button type="button" data-plantilla="morado" onclick="aplicarPlantillaConPreview('morado', 'edit_'); marcarPlantillaActiva('morado');" style="padding: 15px; border: 2px solid #282c34; border-radius: 8px; background: linear-gradient(135deg, #282c34 0%, #3e4451 100%); color: #abb2bf; cursor: pointer; font-weight: bold; transition: transform 0.2s;" onmouseover="this.style.transform='scale(1.05)'" onmouseout="this.style.transform='scale(1)'">
                                    <i class="fas fa-atom"></i> One Dark<br><small style="opacity: 0.8;">Atom Editor</small>
                                </button>
                                <button type="button" data-plantilla="naranja" onclick="aplicarPlantillaConPreview('naranja', 'edit_'); marcarPlantillaActiva('naranja');" style="padding: 15px; border: 2px solid #268bd2; border-radius: 8px; background: linear-gradient(135deg, #fdf6e3 0%, #eee8d5 100%); color: #268bd2; cursor: pointer; font-weight: bold; transition: transform 0.2s;" onmouseover="this.style.transform='scale(1.05)'" onmouseout="this.style.transform='scale(1)'">
                                    <i class="fas fa-sun"></i> Solarized Light<br><small style="opacity: 0.8;">Suave para ojos</small>
                                </button>
                                <button type="button" data-plantilla="turquesa" onclick="aplicarPlantillaConPreview('turquesa', 'edit_'); marcarPlantillaActiva('turquesa');" style="padding: 15px; border: 2px solid #0d1117; border-radius: 8px; background: linear-gradient(135deg, #0d1117 0%, #161b22 100%); color: #c9d1d9; cursor: pointer; font-weight: bold; transition: transform 0.2s;" onmouseover="this.style.transform='scale(1.05)'" onmouseout="this.style.transform='scale(1)'">
                                    <i class="fab fa-github"></i> GitHub Dark<br><small style="opacity: 0.8;">Tema de GitHub</small>
                                </button>
                                <button type="button" data-plantilla="gris" onclick="aplicarPlantillaConPreview('gris', 'edit_'); marcarPlantillaActiva('gris');" style="padding: 15px; border: 2px solid #272822; border-radius: 8px; background: linear-gradient(135deg, #272822 0%, #3e3d32 100%); color: #f8f8f2; cursor: pointer; font-weight: bold; transition: transform 0.2s;" onmouseover="this.style.transform='scale(1.05)'" onmouseout="this.style.transform='scale(1)'">
                                    <i class="fas fa-code"></i> Monokai<br><small style="opacity: 0.8;">Sublime Text</small>
                                </button>
                                <button type="button" data-plantilla="rojo" onclick="aplicarPlantillaConPreview('rojo', 'edit_'); marcarPlantillaActiva('rojo');" style="padding: 15px; border: 2px solid #282828; border-radius: 8px; background: linear-gradient(135deg, #282828 0%, #3c3836 100%); color: #ebdbb2; cursor: pointer; font-weight: bold; transition: transform 0.2s;" onmouseover="this.style.transform='scale(1.05)'" onmouseout="this.style.transform='scale(1)'">
                                    <i class="fas fa-tv"></i> Gruvbox<br><small style="opacity: 0.8;">Retro cálido</small>
                                </button>
                                <button type="button" data-plantilla="glassmorphism" onclick="aplicarPlantillaConPreview('glassmorphism', 'edit_'); marcarPlantillaActiva('glassmorphism');" style="padding: 15px; border: 2px solid #23a2f6; border-radius: 8px; background: linear-gradient(135deg, #080710 0%, #1845ad 50%, #ff512f 100%); color: #ffffff; cursor: pointer; font-weight: bold; transition: transform 0.2s; box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.37);" onmouseover="this.style.transform='scale(1.05)'" onmouseout="this.style.transform='scale(1)'">
                                    <i class="fas fa-glass-whiskey"></i> Glassmorphism<br><small style="opacity: 0.8;">Efectos de vidrio</small>
                                </button>
                                <button type="button" data-plantilla="indigo" onclick="aplicarPlantillaConPreview('indigo', 'edit_'); marcarPlantillaActiva('indigo');" style="padding: 15px; border: 2px solid #6366f1; border-radius: 8px; background: linear-gradient(135deg, #6366f1 0%, #818cf8 100%); color: #ffffff; cursor: pointer; font-weight: bold; transition: transform 0.2s;" onmouseover="this.style.transform='scale(1.05)'" onmouseout="this.style.transform='scale(1)'">
                                    <i class="fas fa-paint-brush"></i> Moderno Índigo<br><small style="opacity: 0.8;">Limpio y profesional</small>
                                </button>
                                <button type="button" data-plantilla="classic" onclick="aplicarPlantillaConPreview('classic', 'edit_'); marcarPlantillaActiva('classic');" style="padding: 15px; border: 2px solid #34495e; border-radius: 8px; background: linear-gradient(135deg, #2c3e50 0%, #34495e 100%); color: #ecf0f1; cursor: pointer; font-weight: bold; transition: transform 0.2s;" onmouseover="this.style.transform='scale(1.05)'" onmouseout="this.style.transform='scale(1)'">
                                    <i class="fas fa-desktop"></i> Classic Panel<br><small style="opacity: 0.8;">Panel oscuro profesional</small>
                                </button>
                                <button type="button" data-plantilla="aleph70" onclick="aplicarPlantillaConPreview('aleph70', 'edit_'); marcarPlantillaActiva('aleph70');" style="padding: 15px; border: 2px solid #2d3339; border-radius: 8px; background: linear-gradient(135deg, #2d3339 0%, #34495e 100%); color: #ffffff; cursor: pointer; font-weight: bold; transition: transform 0.2s;" onmouseover="this.style.transform='scale(1.05)'" onmouseout="this.style.transform='scale(1)'">
                                    <i class="fas fa-star"></i> Aleph70<br><small style="opacity: 0.8;">Tema original del sistema</small>
                                </button>
                            </div>
                        
                        
                        <!-- Vista Previa en Tiempo Real -->
                        <div id="preview-main-container" style="max-height: 600px; overflow-y: auto; padding: 20px; background: var(--preview-color-app-bg, #f8f9fa); border-radius: 6px; transition: background 0.3s;">
                            <h3 style="margin: 0 0 15px 0; color: #2c3e50; font-size: 14px; text-align: center; font-weight: 600;">
                                <i class="fas fa-eye"></i> Vista Previa en Tiempo Real
                            </h3>
                                
                                <div id="live-preview-container" style="display: grid; gap: 12px;">
                                    
                                    <!-- Encabezado / Header -->
                                    <div>
                                        <div style="font-size: 10px; font-weight: 600; margin-bottom: 6px; color: #666;">Encabezado / Header</div>
                                        <div class="preview-header" style="padding: 12px; border-radius: 4px; display: flex; align-items: center; justify-content: space-between;">
                                            <div style="display: flex; align-items: center; gap: 10px;">
                                                <i class="fas fa-bars" style="font-size: 16px;"></i>
                                                <span style="font-weight: 600; font-size: 13px;">Mi Aplicación</span>
                                            </div>
                                            <div style="display: flex; gap: 8px;">
                                                <i class="fas fa-bell" style="font-size: 14px;"></i>
                                                <i class="fas fa-user-circle" style="font-size: 14px;"></i>
                                            </div>
                                        </div>
                                    </div>
                                    
                                    <!-- Colores Primario y Secundario -->
                                    <div>
                                        <div style="font-size: 10px; font-weight: 600; margin-bottom: 6px; color: #666;">Colores Principales</div>
                                        <div style="display: flex; gap: 10px;">
                                            <div class="preview-badge-primary" style="flex: 1; padding: 10px; border-radius: 4px; text-align: center; font-size: 11px; font-weight: 600;">
                                                Primario
                                            </div>
                                            <div class="preview-badge-secondary" style="flex: 1; padding: 10px; border-radius: 4px; text-align: center; font-size: 11px; font-weight: 600;">
                                                Secundario
                                            </div>
                                        </div>
                                    </div>
                                    
                                    <!-- Botones -->
                                    <div>
                                        <div style="font-size: 10px; font-weight: 600; margin-bottom: 6px; color: #666;">Botones</div>
                                        <div style="display: flex; gap: 6px; flex-wrap: wrap;">
                                            <button class="preview-btn-primary" type="button" style="padding: 8px 14px; border-radius: 4px; border: none; font-size: 12px; cursor: pointer; transition: all 0.2s;">Primario</button>
                                            <button class="preview-btn-secondary" type="button" style="padding: 8px 14px; border-radius: 4px; border: none; font-size: 12px; cursor: pointer; transition: all 0.2s;">Secundario</button>
                                            <button class="preview-btn-success" type="button" style="padding: 8px 14px; border-radius: 4px; border: none; font-size: 12px; cursor: pointer;">Éxito</button>
                                        </div>
                                    </div>
                                    
                                    <!-- Notificaciones -->
                                    <div>
                                        <div style="font-size: 10px; font-weight: 600; margin-bottom: 6px; color: #666;">Notificaciones</div>
                                        <div style="display: grid; gap: 5px;">
                                            <div class="preview-notif-success" style="padding: 8px 10px; border-radius: 4px; font-size: 11px; border-left: 3px solid; display: flex; align-items: center; gap: 6px;">
                                                <i class="fas fa-check-circle"></i> Operación completada con éxito
                                            </div>
                                            <div class="preview-notif-warning" style="padding: 8px 10px; border-radius: 4px; font-size: 11px; border-left: 3px solid; display: flex; align-items: center; gap: 6px;">
                                                <i class="fas fa-exclamation-triangle"></i> Advertencia importante
                                            </div>
                                            <div class="preview-notif-danger" style="padding: 8px 10px; border-radius: 4px; font-size: 11px; border-left: 3px solid; display: flex; align-items: center; gap: 6px;">
                                                <i class="fas fa-times-circle"></i> Error en la operación
                                            </div>
                                        </div>
                                    </div>
                                    
                                    <!-- Inputs y Selectores -->
                                    <div>
                                        <div style="font-size: 10px; font-weight: 600; margin-bottom: 6px; color: #666;">Inputs y Selectores</div>
                                        <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 6px;">
                                            <input class="preview-input" type="text" value="Texto ejemplo" style="padding: 7px; border: 1px solid; border-radius: 3px; font-size: 12px;">
                                            <select class="preview-select" style="padding: 7px; border: 1px solid; border-radius: 3px; font-size: 12px;">
                                                <option>Opción 1</option>
                                                <option>Opción 2</option>
                                            </select>
                                            <input class="preview-input" type="text" placeholder="Placeholder" style="padding: 7px; border: 1px solid; border-radius: 3px; font-size: 12px;">
                                            <input class="preview-input-disabled" type="text" value="Deshabilitado" disabled style="padding: 7px; border: 1px solid; border-radius: 3px; font-size: 12px;">
                                        </div>
                                    </div>
                                    
                                    <!-- Tabla -->
                                    <div>
                                        <div style="font-size: 10px; font-weight: 600; margin-bottom: 6px; color: #666;">Tabla</div>
                                        <div style="border: 1px solid #dddddd; border-radius: 4px; overflow: hidden;">
                                            <table style="width: 100%; border-collapse: collapse; font-size: 11px;">
                                                <thead class="preview-table-header">
                                                    <tr id="preview-table-header">
                                                        <th style="padding: 8px; text-align: left; border-bottom: 2px solid #dddddd;">ID</th>
                                                        <th style="padding: 8px; text-align: left; border-bottom: 2px solid #dddddd;">Nombre</th>
                                                        <th style="padding: 8px; text-align: left; border-bottom: 2px solid #dddddd;">Estado</th>
                                                    </tr>
                                                </thead>
                                                <tbody>
                                                    <tr class="preview-table-row" style="background: white;">
                                                        <td style="padding: 8px; border-bottom: 1px solid #f0f0f0;">001</td>
                                                        <td style="padding: 8px; border-bottom: 1px solid #f0f0f0;">Item ejemplo</td>
                                                        <td style="padding: 8px; border-bottom: 1px solid #f0f0f0;">Activo</td>
                                                    </tr>
                                                    <tr id="preview-row-hover" class="preview-table-row-hover" style="background: white; transition: background 0.2s;">
                                                        <td style="padding: 8px; border-bottom: 1px solid #f0f0f0;">002</td>
                                                        <td style="padding: 8px; border-bottom: 1px solid #f0f0f0;">Segundo item</td>
                                                        <td style="padding: 8px; border-bottom: 1px solid #f0f0f0;">Pendiente</td>
                                                    </tr>
                                                </tbody>
                                            </table>
                                        </div>
                                    </div>
                                    
                                    <!-- Iconos -->
                                    <div>
                                        <div style="font-size: 10px; font-weight: 600; margin-bottom: 6px; color: #666;">Iconos</div>
                                        <div style="display: flex; gap: 10px; justify-content: center;">
                                            <div class="preview-icon" style="width: 36px; height: 36px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 16px;">
                                                <i class="fas fa-home"></i>
                                            </div>
                                            <div class="preview-icon" style="width: 36px; height: 36px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 16px;">
                                                <i class="fas fa-user"></i>
                                            </div>
                                            <div class="preview-icon" style="width: 36px; height: 36px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 16px;">
                                                <i class="fas fa-cog"></i>
                                            </div>
                                            <div class="preview-icon" style="width: 36px; height: 36px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 16px;">
                                                <i class="fas fa-chart-bar"></i>
                                            </div>
                                            <div class="preview-icon" style="width: 36px; height: 36px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 16px;">
                                                <i class="fas fa-envelope"></i>
                                            </div>
                                        </div>
                                    </div>
                                    
                                </div>
                        </div>
                        
                        <style>
                        /* CSS Variables para preview en tiempo real */
                        :root {
                            --preview-color-app-bg: #f8f9fa;
                            --preview-color-primario: #3498db;
                            --preview-color-primario-rgb: 52, 152, 219;
                            --preview-color-secundario: #42a5f5;
                            --preview-color-secundario-rgb: 66, 165, 245;
                            --preview-color-success: #27ae60;
                            --preview-color-success-rgb: 39, 174, 96;
                            --preview-color-warning: #f39c12;
                            --preview-color-warning-rgb: 243, 156, 18;
                            --preview-color-danger: #e74c3c;
                            --preview-color-danger-rgb: 231, 76, 60;
                            --preview-color-info: #3498db;
                            --preview-color-info-rgb: 52, 152, 219;
                            --preview-color-button: #3498db;
                            --preview-color-button-hover: #2980b9;
                            --preview-color-button-text: #ffffff;
                            --preview-color-header-bg: #2c3e50;
                            --preview-color-header-text: #ffffff;
                            --preview-color-grid-header: #2c3e50;
                            --preview-color-input-bg: #ffffff;
                            --preview-color-input-text: #495057;
                            --preview-color-input-border: #ced4da;
                            --preview-color-select-bg: #ffffff;
                            --preview-color-select-text: #495057;
                            --preview-color-select-border: #ced4da;
                            --preview-color-disabled-bg: #e9ecef;
                            --preview-color-disabled-text: #6c757d;
                            --preview-color-submenu-bg: #34495e;
                            --preview-color-submenu-text: #ffffff;
                            --preview-color-submenu-hover: #2c3e50;
                            --preview-color-grid-bg: #ffffff;
                            --preview-color-grid-text: #333333;
                            --preview-color-icon: #3498db;
                            --preview-color-icon-rgb: 52, 152, 219;
                        }
                        
                        .preview-header {
                            background: var(--preview-color-header-bg) !important;
                            color: var(--preview-color-header-text) !important;
                        }
                        
                        .preview-badge-primary {
                            background: var(--preview-color-primario) !important;
                            color: white !important;
                        }
                        
                        .preview-badge-secondary {
                            background: var(--preview-color-secundario) !important;
                            color: white !important;
                        }
                        
                        .preview-btn-primary {
                            background: var(--preview-color-button) !important;
                            color: var(--preview-color-button-text) !important;
                        }
                        .preview-btn-primary:hover {
                            filter: brightness(0.9);
                        }
                        
                        .preview-btn-secondary {
                            background: var(--preview-color-secundario) !important;
                            color: white !important;
                        }
                        .preview-btn-secondary:hover {
                            filter: brightness(0.9);
                        }
                        
                        .preview-btn-success {
                            background: var(--preview-color-success) !important;
                            color: white !important;
                        }
                        .preview-btn-success:hover {
                            filter: brightness(0.9);
                        }
                        
                        .preview-notif-success {
                            background: rgba(var(--preview-color-success-rgb), 0.1) !important;
                            border-left-color: var(--preview-color-success) !important;
                            color: var(--preview-color-success) !important;
                        }
                        .preview-notif-warning {
                            background: rgba(var(--preview-color-warning-rgb), 0.1) !important;
                            border-left-color: var(--preview-color-warning) !important;
                            color: var(--preview-color-warning) !important;
                        }
                        .preview-notif-danger {
                            background: rgba(var(--preview-color-danger-rgb), 0.1) !important;
                            border-left-color: var(--preview-color-danger) !important;
                            color: var(--preview-color-danger) !important;
                        }
                        
                        .preview-input {
                            background: var(--preview-color-input-bg) !important;
                            color: var(--preview-color-input-text) !important;
                            border-color: var(--preview-color-input-border) !important;
                        }
                        
                        .preview-select {
                            background: var(--preview-color-select-bg) !important;
                            color: var(--preview-color-select-text) !important;
                            border-color: var(--preview-color-select-border) !important;
                        }
                        .preview-input:focus {
                            outline: 2px solid var(--preview-color-primario);
                            outline-offset: 1px;
                        }
                        
                        .preview-select:focus {
                            outline: 2px solid var(--preview-color-secundario);
                            outline-offset: 1px;
                        }
                        .preview-input-disabled {
                            background: var(--preview-color-disabled-bg) !important;
                            color: var(--preview-color-disabled-text) !important;
                            border-color: var(--preview-color-input-border) !important;
                        }
                        
                        .preview-table-header tr {
                            background: var(--preview-color-grid-header) !important;
                            color: var(--preview-color-header-text) !important;
                        }
                        .preview-table-row-hover:hover {
                            background: rgba(var(--preview-color-secundario-rgb), 0.1) !important;
                            cursor: pointer;
                        }
                        
                        .preview-icon {
                            background: var(--preview-color-icon) !important;
                            color: white !important;
                            transition: transform 0.2s;
                        }
                        .preview-icon:hover {
                            transform: scale(1.1);
                        }
                        
                        .preview-table-row {
                            background: var(--preview-color-grid-bg) !important;
                            color: var(--preview-color-grid-text) !important;
                        }
                        .preview-table-row td {
                            color: var(--preview-color-grid-text) !important;
                        }
                        
                        .plantilla-card {
                            padding: 10px;
                            border: 2px solid #dddddd;
                            border-radius: 6px;
                            cursor: pointer;
                            transition: all 0.2s;
                            background: white;
                        }
                        .plantilla-card:hover {
                            border-color: #3498db;
                            box-shadow: 0 2px 8px rgba(52,152,219,0.2);
                        }
                        .plantilla-card.active {
                            border-color: #3498db !important;
                            background: #f0f8ff !important;
                        }
                        </style>
                        
                        </div>
                                <i class="fas fa-palette"></i> Editor de Colores Individual
                            </h4>
                            <p style="margin: 0; font-size: 13px; color: #495057;">
                                Click en los cuadrados de color para modificar cada color individualmente
                            </p>
                        
                        <!-- Colores Principales -->
                        <details style="display: inline-block; margin: 0 15px 15px 0; border: 1px solid #dee2e6; border-radius: 8px; padding: 10px; background: white; vertical-align: top; width: auto;">
                            <summary style="cursor: pointer; font-weight: bold; color: #2c3e50; margin-bottom: 10px;">
                                <i class="fas fa-paint-brush"></i> Colores Principales
                            </summary>
                            <div style="display: flex; flex-wrap: nowrap; gap: 12px; align-items: flex-start;">
                                <div style="display: flex; flex-direction: column; align-items: center; gap: 6px;">
                                    <label for="edit_color_app_bg" style="font-size: 11px; text-align: center; margin: 0; white-space: nowrap;"><i class="fas fa-circle"></i> Fondo App</label>
                                    <input type="color" id="edit_color_app_bg" name="color_app_bg" value="${empresa.color_app_bg || '#ffffff'}" oninput="actualizarVistaPrevia()" style="width: 40px; height: 35px; border: 2px solid #dee2e6; border-radius: 6px; cursor: pointer;">
                                </div>
                                <div style="display: flex; flex-direction: column; align-items: center; gap: 6px;">
                                    <label for="edit_color_primario" style="font-size: 11px; text-align: center; margin: 0; white-space: nowrap;"><i class="fas fa-circle"></i> Primario</label>
                                    <input type="color" id="edit_color_primario" name="color_primario" value="${empresa.color_primario || '#2c3e50'}" oninput="actualizarVistaPrevia()" style="width: 40px; height: 35px; border: 2px solid #dee2e6; border-radius: 6px; cursor: pointer;">
                                </div>
                                <div style="display: flex; flex-direction: column; align-items: center; gap: 6px;">
                                    <label for="edit_color_secundario" style="font-size: 11px; text-align: center; margin: 0; white-space: nowrap;"><i class="fas fa-circle"></i> Secundario</label>
                                    <input type="color" id="edit_color_secundario" name="color_secundario" value="${empresa.color_secundario || '#3498db'}" oninput="actualizarVistaPrevia()" style="width: 40px; height: 35px; border: 2px solid #dee2e6; border-radius: 6px; cursor: pointer;">
                                </div>
                            </div>
                        </details>
                        
                        <!-- Colores de Botones -->
                        <details style="display: inline-block; margin: 0 15px 15px 0; border: 1px solid #dee2e6; border-radius: 8px; padding: 10px; background: white; vertical-align: top; width: auto;">
                            <summary style="cursor: pointer; font-weight: bold; color: #2c3e50; margin-bottom: 10px;">
                                <i class="fas fa-hand-pointer"></i> Colores de Botones
                            </summary>
                            <div style="display: flex; flex-wrap: nowrap; gap: 12px; align-items: flex-start;">
                                <div style="display: flex; flex-direction: column; align-items: center; gap: 6px;">
                                    <label for="edit_color_button" style="font-size: 11px; text-align: center; margin: 0; white-space: nowrap;"><i class="fas fa-circle"></i> Botón</label>
                                    <input type="color" id="edit_color_button" name="color_button" value="${empresa.color_button || '#3498db'}" oninput="actualizarVistaPrevia()" style="width: 40px; height: 35px; border: 2px solid #dee2e6; border-radius: 6px; cursor: pointer;">
                                </div>
                                <div style="display: flex; flex-direction: column; align-items: center; gap: 6px;">
                                    <label for="edit_color_button_hover" style="font-size: 11px; text-align: center; margin: 0; white-space: nowrap;"><i class="fas fa-circle"></i> Hover</label>
                                    <input type="color" id="edit_color_button_hover" name="color_button_hover" value="${empresa.color_button_hover || '#2980b9'}" oninput="actualizarVistaPrevia()" style="width: 40px; height: 35px; border: 2px solid #dee2e6; border-radius: 6px; cursor: pointer;">
                                </div>
                                <div style="display: flex; flex-direction: column; align-items: center; gap: 6px;">
                                    <label for="edit_color_button_text" style="font-size: 11px; text-align: center; margin: 0; white-space: nowrap;"><i class="fas fa-circle"></i> Texto</label>
                                    <input type="color" id="edit_color_button_text" name="color_button_text" value="${empresa.color_button_text || '#ffffff'}" oninput="actualizarVistaPrevia()" style="width: 40px; height: 35px; border: 2px solid #dee2e6; border-radius: 6px; cursor: pointer;">
                                </div>
                            </div>
                        </details>
                        
                        <!-- Colores de Encabezados -->
                        <details style="display: inline-block; margin: 0 15px 15px 0; border: 1px solid #dee2e6; border-radius: 8px; padding: 10px; background: white; vertical-align: top; width: auto;">
                            <summary style="cursor: pointer; font-weight: bold; color: #2c3e50; margin-bottom: 10px;">
                                <i class="fas fa-heading"></i> Colores de Encabezados
                            </summary>
                            <div style="display: flex; flex-wrap: nowrap; gap: 12px; align-items: flex-start;">
                                <div style="display: flex; flex-direction: column; align-items: center; gap: 6px;">
                                    <label for="edit_color_header_bg" style="font-size: 11px; text-align: center; margin: 0; white-space: nowrap;"><i class="fas fa-circle"></i> Fondo</label>
                                    <input type="color" id="edit_color_header_bg" name="color_header_bg" value="${empresa.color_header_bg || '#2c3e50'}" oninput="actualizarVistaPrevia()" style="width: 40px; height: 35px; border: 2px solid #dee2e6; border-radius: 6px; cursor: pointer;">
                                </div>
                                <div style="display: flex; flex-direction: column; align-items: center; gap: 6px;">
                                    <label for="edit_color_header_text" style="font-size: 11px; text-align: center; margin: 0; white-space: nowrap;"><i class="fas fa-circle"></i> Texto</label>
                                    <input type="color" id="edit_color_header_text" name="color_header_text" value="${empresa.color_header_text || '#ffffff'}" oninput="actualizarVistaPrevia()" style="width: 40px; height: 35px; border: 2px solid #dee2e6; border-radius: 6px; cursor: pointer;">
                                </div>
                            </div>
                        </details>
                        
                        <!-- Colores de Tablas -->
                        <details style="display: inline-block; margin: 0 15px 15px 0; border: 1px solid #dee2e6; border-radius: 8px; padding: 10px; background: white; vertical-align: top; width: auto;">
                            <summary style="cursor: pointer; font-weight: bold; color: #2c3e50; margin-bottom: 10px;">
                                <i class="fas fa-table"></i> Colores de Tablas
                            </summary>
                            <div style="display: flex; flex-wrap: nowrap; gap: 12px; align-items: flex-start;">
                                <div style="display: flex; flex-direction: column; align-items: center; gap: 6px;">
                                    <label for="edit_color_grid_header" style="font-size: 11px; text-align: center; margin: 0; white-space: nowrap;"><i class="fas fa-circle"></i> Encabezado</label>
                                    <input type="color" id="edit_color_grid_header" name="color_grid_header" value="${empresa.color_grid_header || '#2c3e50'}" oninput="actualizarVistaPrevia()" style="width: 40px; height: 35px; border: 2px solid #dee2e6; border-radius: 6px; cursor: pointer;">
                                </div>
                            </div>
                            <input type="hidden" name="color_grid_hover" value="${empresa.color_grid_hover || 'rgba(52,152,219,0.1)'}">
                        </details>
                        
                        <!-- Colores de Estado -->
                        <details style="display: inline-block; margin: 0 15px 15px 0; border: 1px solid #dee2e6; border-radius: 8px; padding: 10px; background: white; vertical-align: top; width: auto;">
                            <summary style="cursor: pointer; font-weight: bold; color: #2c3e50; margin-bottom: 10px;">
                                <i class="fas fa-exclamation-triangle"></i> Colores de Estado
                            </summary>
                            <div style="display: flex; flex-wrap: nowrap; gap: 12px; align-items: flex-start;">
                                <div style="display: flex; flex-direction: column; align-items: center; gap: 6px;">
                                    <label for="edit_color_success" style="font-size: 11px; text-align: center; margin: 0; white-space: nowrap;"><i class="fas fa-circle"></i> Éxito</label>
                                    <input type="color" id="edit_color_success" name="color_success" value="${empresa.color_success || '#27ae60'}" oninput="actualizarVistaPrevia()" style="width: 40px; height: 35px; border: 2px solid #dee2e6; border-radius: 6px; cursor: pointer;">
                                </div>
                                <div style="display: flex; flex-direction: column; align-items: center; gap: 6px;">
                                    <label for="edit_color_warning" style="font-size: 11px; text-align: center; margin: 0; white-space: nowrap;"><i class="fas fa-circle"></i> Advertencia</label>
                                    <input type="color" id="edit_color_warning" name="color_warning" value="${empresa.color_warning || '#f39c12'}" oninput="actualizarVistaPrevia()" style="width: 40px; height: 35px; border: 2px solid #dee2e6; border-radius: 6px; cursor: pointer;">
                                </div>
                                <div style="display: flex; flex-direction: column; align-items: center; gap: 6px;">
                                    <label for="edit_color_danger" style="font-size: 11px; text-align: center; margin: 0; white-space: nowrap;"><i class="fas fa-circle"></i> Peligro</label>
                                    <input type="color" id="edit_color_danger" name="color_danger" value="${empresa.color_danger || '#e74c3c'}" oninput="actualizarVistaPrevia()" style="width: 40px; height: 35px; border: 2px solid #dee2e6; border-radius: 6px; cursor: pointer;">
                                </div>
                                <div style="display: flex; flex-direction: column; align-items: center; gap: 6px;">
                                    <label for="edit_color_info" style="font-size: 11px; text-align: center; margin: 0; white-space: nowrap;"><i class="fas fa-circle"></i> Info</label>
                                    <input type="color" id="edit_color_info" name="color_info" value="${empresa.color_info || '#3498db'}" oninput="actualizarVistaPrevia()" style="width: 40px; height: 35px; border: 2px solid #dee2e6; border-radius: 6px; cursor: pointer;">
                                </div>
                            </div>
                        </details>
                        
                        <!-- Colores de Inputs y Selectores -->
                        <details style="display: inline-block; margin: 0 15px 15px 0; border: 1px solid #dee2e6; border-radius: 8px; padding: 10px; background: white; vertical-align: top; width: auto;">
                            <summary style="cursor: pointer; font-weight: bold; color: #2c3e50; margin-bottom: 10px;">
                                <i class="fas fa-keyboard"></i> Inputs y Selectores
                            </summary>
                            <div style="display: flex; flex-wrap: nowrap; gap: 12px; align-items: flex-start;">
                                <div style="display: flex; flex-direction: column; align-items: center; gap: 6px;">
                                    <label for="edit_color_input_bg" style="font-size: 11px; text-align: center; margin: 0; white-space: nowrap;"><i class="fas fa-circle"></i> Fondo Input</label>
                                    <input type="color" id="edit_color_input_bg" name="color_input_bg" value="${empresa.color_input_bg || '#ffffff'}" oninput="actualizarVistaPrevia()" style="width: 40px; height: 35px; border: 2px solid #dee2e6; border-radius: 6px; cursor: pointer;">
                                </div>
                                <div style="display: flex; flex-direction: column; align-items: center; gap: 6px;">
                                    <label for="edit_color_input_text" style="font-size: 11px; text-align: center; margin: 0; white-space: nowrap;"><i class="fas fa-circle"></i> Texto Input</label>
                                    <input type="color" id="edit_color_input_text" name="color_input_text" value="${empresa.color_input_text || '#333333'}" oninput="actualizarVistaPrevia()" style="width: 40px; height: 35px; border: 2px solid #dee2e6; border-radius: 6px; cursor: pointer;">
                                </div>
                                <div style="display: flex; flex-direction: column; align-items: center; gap: 6px;">
                                    <label for="edit_color_input_border" style="font-size: 11px; text-align: center; margin: 0; white-space: nowrap;"><i class="fas fa-circle"></i> Borde Input</label>
                                    <input type="color" id="edit_color_input_border" name="color_input_border" value="${empresa.color_input_border || '#cccccc'}" oninput="actualizarVistaPrevia()" style="width: 40px; height: 35px; border: 2px solid #dee2e6; border-radius: 6px; cursor: pointer;">
                                </div>
                                <div style="display: flex; flex-direction: column; align-items: center; gap: 6px;">
                                    <label for="edit_color_select_bg" style="font-size: 11px; text-align: center; margin: 0; white-space: nowrap;"><i class="fas fa-circle"></i> Fondo Select</label>
                                    <input type="color" id="edit_color_select_bg" name="color_select_bg" value="${empresa.color_select_bg || '#ffffff'}" oninput="actualizarVistaPrevia()" style="width: 40px; height: 35px; border: 2px solid #dee2e6; border-radius: 6px; cursor: pointer;">
                                </div>
                                <div style="display: flex; flex-direction: column; align-items: center; gap: 6px;">
                                    <label for="edit_color_select_text" style="font-size: 11px; text-align: center; margin: 0; white-space: nowrap;"><i class="fas fa-circle"></i> Texto Select</label>
                                    <input type="color" id="edit_color_select_text" name="color_select_text" value="${empresa.color_select_text || '#333333'}" oninput="actualizarVistaPrevia()" style="width: 40px; height: 35px; border: 2px solid #dee2e6; border-radius: 6px; cursor: pointer;">
                                </div>
                                <div style="display: flex; flex-direction: column; align-items: center; gap: 6px;">
                                    <label for="edit_color_select_border" style="font-size: 11px; text-align: center; margin: 0; white-space: nowrap;"><i class="fas fa-circle"></i> Borde Select</label>
                                    <input type="color" id="edit_color_select_border" name="color_select_border" value="${empresa.color_select_border || '#cccccc'}" oninput="actualizarVistaPrevia()" style="width: 40px; height: 35px; border: 2px solid #dee2e6; border-radius: 6px; cursor: pointer;">
                                </div>
                            </div>
                        </details>
                        
                        <!-- Colores de Campos Deshabilitados -->
                        <details style="display: inline-block; margin: 0 15px 15px 0; border: 1px solid #dee2e6; border-radius: 8px; padding: 10px; background: white; vertical-align: top; width: auto;">
                            <summary style="cursor: pointer; font-weight: bold; color: #2c3e50; margin-bottom: 10px;">
                                <i class="fas fa-ban"></i> Campos Deshabilitados (Disabled)
                            </summary>
                            <div style="display: flex; flex-wrap: nowrap; gap: 12px; align-items: flex-start;">
                                <div style="display: flex; flex-direction: column; align-items: center; gap: 6px;">
                                    <label for="edit_color_disabled_bg" style="font-size: 11px; text-align: center; margin: 0; white-space: nowrap;"><i class="fas fa-circle"></i> Fondo</label>
                                    <input type="color" id="edit_color_disabled_bg" name="color_disabled_bg" value="${empresa.color_disabled_bg || '#f0f0f0'}" oninput="actualizarVistaPrevia()" style="width: 40px; height: 35px; border: 2px solid #dee2e6; border-radius: 6px; cursor: pointer;">
                                </div>
                                <div style="display: flex; flex-direction: column; align-items: center; gap: 6px;">
                                    <label for="edit_color_disabled_text" style="font-size: 11px; text-align: center; margin: 0; white-space: nowrap;"><i class="fas fa-circle"></i> Texto</label>
                                    <input type="color" id="edit_color_disabled_text" name="color_disabled_text" value="${empresa.color_disabled_text || '#666666'}" oninput="actualizarVistaPrevia()" style="width: 40px; height: 35px; border: 2px solid #dee2e6; border-radius: 6px; cursor: pointer;">
                                </div>
                            </div>
                        </details>
                        
                        <!-- Colores de Submenus -->
                        <details style="display: inline-block; margin: 0 15px 15px 0; border: 1px solid #dee2e6; border-radius: 8px; padding: 10px; background: white; vertical-align: top; width: auto;">
                            <summary style="cursor: pointer; font-weight: bold; color: #2c3e50; margin-bottom: 10px;">
                                <i class="fas fa-list"></i> Submenus
                            </summary>
                            <div style="display: flex; flex-wrap: nowrap; gap: 12px; align-items: flex-start;">
                                <div style="display: flex; flex-direction: column; align-items: center; gap: 6px;">
                                    <label for="edit_color_submenu_bg" style="font-size: 11px; text-align: center; margin: 0; white-space: nowrap;"><i class="fas fa-circle"></i> Fondo</label>
                                    <input type="color" id="edit_color_submenu_bg" name="color_submenu_bg" value="${empresa.color_submenu_bg || '#34495e'}" oninput="actualizarVistaPrevia()" style="width: 40px; height: 35px; border: 2px solid #dee2e6; border-radius: 6px; cursor: pointer;">
                                </div>
                                <div style="display: flex; flex-direction: column; align-items: center; gap: 6px;">
                                    <label for="edit_color_submenu_text" style="font-size: 11px; text-align: center; margin: 0; white-space: nowrap;"><i class="fas fa-circle"></i> Texto</label>
                                    <input type="color" id="edit_color_submenu_text" name="color_submenu_text" value="${empresa.color_submenu_text || '#ffffff'}" oninput="actualizarVistaPrevia()" style="width: 40px; height: 35px; border: 2px solid #dee2e6; border-radius: 6px; cursor: pointer;">
                                </div>
                                <div style="display: flex; flex-direction: column; align-items: center; gap: 6px;">
                                    <label for="edit_color_submenu_hover" style="font-size: 11px; text-align: center; margin: 0; white-space: nowrap;"><i class="fas fa-circle"></i> Hover</label>
                                    <input type="color" id="edit_color_submenu_hover" name="color_submenu_hover" value="${empresa.color_submenu_hover || '#2c3e50'}" oninput="actualizarVistaPrevia()" style="width: 40px; height: 35px; border: 2px solid #dee2e6; border-radius: 6px; cursor: pointer;">
                                </div>
                            </div>
                        </details>
                        
                        <!-- Colores de Grids e Iconos -->
                        <details style="display: inline-block; margin: 0 15px 15px 0; border: 1px solid #dee2e6; border-radius: 8px; padding: 10px; background: white; vertical-align: top; width: auto;">
                            <summary style="cursor: pointer; font-weight: bold; color: #2c3e50; margin-bottom: 10px;">
                                <i class="fas fa-th"></i> Grids e Iconos
                            </summary>
                            <div style="display: flex; flex-wrap: nowrap; gap: 12px; align-items: flex-start;">
                                <div style="display: flex; flex-direction: column; align-items: center; gap: 6px;">
                                    <label for="edit_color_grid_bg" style="font-size: 11px; text-align: center; margin: 0; white-space: nowrap;"><i class="fas fa-circle"></i> Fondo Grid</label>
                                    <input type="color" id="edit_color_grid_bg" name="color_grid_bg" value="${empresa.color_grid_bg || '#ffffff'}" oninput="actualizarVistaPrevia()" style="width: 40px; height: 35px; border: 2px solid #dee2e6; border-radius: 6px; cursor: pointer;">
                                </div>
                                <div style="display: flex; flex-direction: column; align-items: center; gap: 6px;">
                                    <label for="edit_color_grid_text" style="font-size: 11px; text-align: center; margin: 0; white-space: nowrap;"><i class="fas fa-circle"></i> Texto Grid</label>
                                    <input type="color" id="edit_color_grid_text" name="color_grid_text" value="${empresa.color_grid_text || '#333333'}" oninput="actualizarVistaPrevia()" style="width: 40px; height: 35px; border: 2px solid #dee2e6; border-radius: 6px; cursor: pointer;">
                                </div>
                                <div style="display: flex; flex-direction: column; align-items: center; gap: 6px;">
                                    <label for="edit_color_icon" style="font-size: 11px; text-align: center; margin: 0; white-space: nowrap;"><i class="fas fa-circle"></i> Iconos</label>
                                    <input type="color" id="edit_color_icon" name="color_icon" value="${empresa.color_icon || '#ffffff'}" oninput="actualizarVistaPrevia()" style="width: 40px; height: 35px; border: 2px solid #dee2e6; border-radius: 6px; cursor: pointer;">
                                </div>
                            </div>
                        </details>
                        
                        <div class="form-group">
                            <label>Logo Actual</label>
                            ${empresa.logo_header && !empresa.logo_header.startsWith('default_') ? 
                                `<img src="/static/logos/${empresa.logo_header}" style="max-width: 200px; border: 1px solid #dddddd; padding: 10px;">` :
                                '<p style="color: #999;">Sin logo personalizado</p>'
                            }
                        </div>
                        
                        <div class="form-group">
                            <label for="edit_logo">Cambiar Logo</label>
                            <input type="file" id="edit_logo" name="logo" accept="image/*">
                            <small style="color: #7f8c8d;">Formatos: PNG, JPG, SVG (máx. 2MB). Dejar vacío para mantener el actual.</small>
                        </div>
                        
                        <div class="form-group">
                            <label>
                                <input type="checkbox" id="edit_activa" name="activa" ${empresa.activa ? 'checked' : ''}>
                                Empresa Activa
                            </label>
                        </div>
                        <div class="modal-actions">
                            <button type="button" class="btn" onclick="cerrarModalEditarEmpresa()">Cancelar</button>
                            <button type="submit" class="btn btn-primary">
                                <i class="fas fa-save"></i> Guardar Cambios
                            </button>
                        </div>
                    </form>
                </div>
            </div>
        `;
        
        document.body.insertAdjacentHTML('beforeend', modalHTML);
        
        // Detectar y marcar plantilla activa
        const plantillaActiva = detectarPlantillaActiva(empresa);
        if (plantillaActiva) {
            console.log('[EDITAR] Plantilla detectada:', plantillaActiva);
            // Esperar un momento para que el DOM se actualice
            setTimeout(() => {
                marcarPlantillaActiva(plantillaActiva);
            }, 100);
        } else {
            console.log('[EDITAR] Colores personalizados (no coincide con ninguna plantilla)');
        }
        
        // Inicializar preview con colores actuales - Esperar a que el DOM se cargue
        setTimeout(() => {
            actualizarPreviewColores();
            console.log('✅ Preview inicializado con colores de la empresa');
        }, 100);
        
        // Event listener para el formulario
        document.getElementById('formEditarEmpresa').addEventListener('submit', async (e) => {
            e.preventDefault();
            await guardarCambiosEmpresa(e.target);
        });
        
    } catch (error) {
        console.error('Error:', error);
        mostrarNotificacion('Error cargando datos de la empresa', 'error');
    }
}

function cerrarModalEditarEmpresa() {
    const modal = document.getElementById('modalEditarEmpresa');
    if (modal) modal.remove();
}

async function guardarCambiosEmpresa(form) {
    const empresaId = new FormData(form).get('empresa_id');
    const logoFile = document.getElementById('edit_logo').files[0];
    
    const submitBtn = form.querySelector('button[type="submit"]');
    const originalText = submitBtn.innerHTML;
    
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Guardando...';
    
    try {
        let response;
        
        // Si hay archivo de logo, usar FormData
        if (logoFile) {
            const formData = new FormData(form);
            
            response = await fetch(`/api/empresas/${empresaId}`, {
                method: 'PUT',
                body: formData
            });
        } else {
            // Si no hay archivo, usar JSON
            const formData = new FormData(form);
            const data = {
                nombre: formData.get('nombre'),
                cif: formData.get('cif'),
                direccion: formData.get('direccion'),
                telefono: formData.get('telefono'),
                email: formData.get('email'),
                web: formData.get('web'),
                color_primario: formData.get('color_primario'),
                color_secundario: formData.get('color_secundario'),
                color_success: formData.get('color_success'),
                color_warning: formData.get('color_warning'),
                color_danger: formData.get('color_danger'),
                color_info: formData.get('color_info'),
                color_button: formData.get('color_button'),
                color_button_hover: formData.get('color_button_hover'),
                color_button_text: formData.get('color_button_text'),
                color_app_bg: formData.get('color_app_bg'),
                color_header_bg: formData.get('color_header_bg'),
                color_header_text: formData.get('color_header_text'),
                color_grid_header: formData.get('color_grid_header'),
                color_grid_hover: formData.get('color_grid_hover'),
                color_input_bg: formData.get('color_input_bg'),
                color_input_text: formData.get('color_input_text'),
                color_input_border: formData.get('color_input_border'),
                color_select_bg: formData.get('color_select_bg'),
                color_select_text: formData.get('color_select_text'),
                color_select_border: formData.get('color_select_border'),
                color_disabled_bg: formData.get('color_disabled_bg'),
                color_disabled_text: formData.get('color_disabled_text'),
                color_submenu_bg: formData.get('color_submenu_bg'),
                color_submenu_text: formData.get('color_submenu_text'),
                color_submenu_hover: formData.get('color_submenu_hover'),
                color_grid_bg: formData.get('color_grid_bg'),
                color_grid_text: formData.get('color_grid_text'),
                color_icon: formData.get('color_icon'),
                activa: document.getElementById('edit_activa').checked ? 1 : 0
            };
            
            console.log('💾 Datos que se enviarán al servidor:', data);
            
            response = await fetch(`/api/empresas/${empresaId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
        }
        
        const result = await response.json();
        
        if (response.ok) {
            mostrarNotificacion('Empresa actualizada correctamente', 'success');
            cerrarModalEditarEmpresa();
            cargarEmpresas();
            cargarEstadisticas();
        } else {
            mostrarNotificacion(result.error || 'Error actualizando empresa', 'error');
        }
        
    } catch (error) {
        console.error('Error:', error);
        mostrarNotificacion('Error de conexión', 'error');
    } finally {
        submitBtn.disabled = false;
        submitBtn.innerHTML = originalText;
    }
}


async function actualizarEmisorJson(empresaId, data) {
    // Llamar al backend para actualizar el emisor.json con los nuevos datos
    try {
        await fetch(`/api/empresas/${empresaId}/emisor`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
    } catch (error) {
        console.log('No se pudo actualizar emisor.json:', error);
    }
}

async function eliminarEmpresaCompleta(empresaId) {
    const empresa = empresas.find(e => e.id === empresaId);
    if (!empresa) return;
    
    const confirmacion = confirm(
        `¿ELIMINAR COMPLETAMENTE la empresa "${empresa.nombre}"?\n\n` +
        `Se eliminarán:\n` +
        `• Base de datos: ${empresa.codigo}.db\n` +
        `• Logo de la empresa\n` +
        `• Archivo emisor.json\n` +
        `• Todos los permisos asociados\n\n` +
        `Esta acción NO se puede deshacer.\n\n` +
        `¿Está seguro?`
    );
    
    if (!confirmacion) return;
    
    try {
        const response = await fetch(`/api/empresas/${empresaId}`, {
            method: 'DELETE'
        });
        
        const data = await response.json();
        
        if (response.ok) {
            mostrarNotificacion(
                `Empresa eliminada: ${data.archivos_eliminados.join(', ')}`, 
                'success'
            );
            cargarEmpresas();
        } else {
            mostrarNotificacion(data.error || 'Error eliminando empresa', 'error');
        }
    } catch (error) {
        console.error('Error:', error);
        mostrarNotificacion('Error de conexión', 'error');
    }
}

// Función para generar colores armónicos basados en el color primario
async function generarColoresArmonicos() {
    try {
        const colorPrimario = document.getElementById('edit_color_primario').value;
        
        mostrarNotificacion('Generando paleta de colores armónica...', 'info');
        
        const response = await fetch('/api/empresas/generar-colores', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ color_primario: colorPrimario })
        });
        
        if (!response.ok) {
            throw new Error('Error generando colores');
        }
        
        const palette = await response.json();
        
        // Aplicar los colores generados a los inputs
        document.getElementById('edit_color_primario').value = palette.color_primario;
        document.getElementById('edit_color_secundario').value = palette.color_secundario;
        document.getElementById('edit_color_success').value = palette.color_success;
        document.getElementById('edit_color_warning').value = palette.color_warning;
        document.getElementById('edit_color_danger').value = palette.color_danger;
        document.getElementById('edit_color_info').value = palette.color_info;
        document.getElementById('edit_color_button').value = palette.color_button;
        document.getElementById('edit_color_button_hover').value = palette.color_button_hover;
        document.getElementById('edit_color_header_bg').value = palette.color_header_bg;
        document.getElementById('edit_color_header_text').value = palette.color_header_text;
        document.getElementById('edit_color_grid_header').value = palette.color_grid_header;
        // El grid_hover es rgba, no se puede asignar a input type color
        
        // Mostrar y actualizar la vista previa
        const preview = document.getElementById('color-preview');
        if (preview) {
            preview.style.display = 'block';
            
            // Actualizar estilos del preview
            document.getElementById('preview-menu').style.background = palette.color_primario;
            document.getElementById('preview-hover').style.background = palette.color_secundario;
            document.getElementById('preview-button').style.background = palette.color_button;
            document.getElementById('preview-success').style.background = palette.color_success;
            document.getElementById('preview-warning').style.background = palette.color_warning;
            document.getElementById('preview-danger').style.background = palette.color_danger;
            document.getElementById('preview-header').style.background = palette.color_header_bg;
            document.getElementById('preview-header').style.color = palette.color_header_text;
            document.getElementById('preview-table-header').style.background = palette.color_grid_header;
            document.getElementById('preview-row-hover').style.background = palette.color_grid_hover;
            
            // Scroll suave hacia el preview
            preview.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
        
        mostrarNotificacion('✨ Colores generados! Revisa la vista previa y guarda los cambios.', 'success');
        
        console.log('Paleta generada:', palette);
    } catch (error) {
        console.error('Error generando colores:', error);
        mostrarNotificacion('Error generando colores armónicos', 'error');
    }
}

// Función para actualizar el preview de colores en tiempo real
function actualizarPreviewColores() {
    try {
        console.log('🔍 actualizarPreviewColores() iniciada');
        
        // Determinar si estamos en modal de edición o creación
        const esEdicion = document.getElementById('formEditarEmpresa') !== null;
        const prefijo = esEdicion ? 'edit_' : '';
        console.log('📌 Prefijo detectado:', prefijo, '| Modo:', esEdicion ? 'EDICIÓN' : 'CREACIÓN');
            
        // Obtener elementos del preview
        const previewMenu = document.getElementById('preview-menu');
        const previewHover = document.getElementById('preview-hover');
        const previewButton = document.getElementById('preview-button');
        const previewSuccess = document.getElementById('preview-success');
        const previewWarning = document.getElementById('preview-warning');
        const previewDanger = document.getElementById('preview-danger');
        const previewHeader = document.getElementById('preview-header');
        const previewTableHeader = document.getElementById('preview-table-header');
        const previewRowHover = document.getElementById('preview-row-hover');
            
        // Obtener colores de los inputs con prefijo correcto
        const colorPrimario = document.getElementById(prefijo + 'color_primario')?.value || '#2c3e50';
        const colorSecundario = document.getElementById(prefijo + 'color_secundario')?.value || '#3498db';
        const colorButton = document.getElementById(prefijo + 'color_button')?.value || '#3498db';
        const colorButtonText = document.getElementById(prefijo + 'color_button_text')?.value || '#ffffff';
        const colorSuccess = document.getElementById(prefijo + 'color_success')?.value || '#27ae60';
        const colorWarning = document.getElementById(prefijo + 'color_warning')?.value || '#f39c12';
        const colorDanger = document.getElementById(prefijo + 'color_danger')?.value || '#e74c3c';
        const colorAppBg = document.getElementById(prefijo + 'color_app_bg')?.value || '#ffffff';
        const colorHeaderBg = document.getElementById(prefijo + 'color_header_bg')?.value || '#2c3e50';
        const colorHeaderText = document.getElementById(prefijo + 'color_header_text')?.value || '#ffffff';
        const colorGridHeader = document.getElementById(prefijo + 'color_grid_header')?.value || '#2c3e50';
            
        console.log('🎨 Colores detectados:', {
            primario: colorPrimario,
            secundario: colorSecundario,
            button: colorButton,
            prefijo: prefijo
        });
            
        // Actualizar elementos del preview si existen - Usar background (shorthand) directamente
        if (previewMenu) {
            previewMenu.style.background = colorPrimario;
            console.log('✅ preview-menu actualizado:', colorPrimario);
        }
        
        if (previewHover) previewHover.style.background = colorSecundario;
        if (previewButton) {
            previewButton.style.background = colorButton;
            previewButton.style.color = colorButtonText;
        }
        
        if (previewSuccess) {
            const rs = parseInt(colorSuccess.slice(1,3),16); const gs = parseInt(colorSuccess.slice(3,5),16); const bs = parseInt(colorSuccess.slice(5,7),16);
            previewSuccess.style.background = `rgba(${rs}, ${gs}, ${bs}, 0.15)`;
            previewSuccess.style.borderLeftColor = colorSuccess;
            previewSuccess.style.color = colorSuccess;
        }
        if (previewWarning) {
            const rw = parseInt(colorWarning.slice(1,3),16); const gw = parseInt(colorWarning.slice(3,5),16); const bw = parseInt(colorWarning.slice(5,7),16);
            previewWarning.style.background = `rgba(${rw}, ${gw}, ${bw}, 0.15)`;
            previewWarning.style.borderLeftColor = colorWarning;
            previewWarning.style.color = colorWarning;
        }
        if (previewDanger) {
            const rd = parseInt(colorDanger.slice(1,3),16); const gd = parseInt(colorDanger.slice(3,5),16); const bd = parseInt(colorDanger.slice(5,7),16);
            previewDanger.style.background = `rgba(${rd}, ${gd}, ${bd}, 0.15)`;
            previewDanger.style.borderLeftColor = colorDanger;
            previewDanger.style.color = colorDanger;
        }
        
        if (previewHeader) {
            previewHeader.style.background = colorHeaderBg;
            previewHeader.style.color = colorHeaderText;
        }
        
        if (previewTableHeader) {
            previewTableHeader.style.background = colorGridHeader;
            previewTableHeader.style.color = colorHeaderText;
        }
        
        if (previewRowHover) {
            // Convertir hex a rgba con opacidad para el hover
            const r = parseInt(colorSecundario.slice(1, 3), 16);
            const g = parseInt(colorSecundario.slice(3, 5), 16);
            const b = parseInt(colorSecundario.slice(5, 7), 16);
            previewRowHover.style.background = `rgba(${r}, ${g}, ${b}, 0.1)`;
        }

        // Swatches compactos
        const sw = {
            appBg: document.getElementById('sw-app-bg'),
            prim: document.getElementById('sw-primario'),
            sec: document.getElementById('sw-secundario'),
            btn: document.getElementById('sw-button'),
            btnH: document.getElementById('sw-button-hover'),
            btnT: document.getElementById('sw-button-text'),
            hdr: document.getElementById('sw-header-bg'),
            hdrT: document.getElementById('sw-header-text'),
            gridH: document.getElementById('sw-grid-header'),
            succ: document.getElementById('sw-success'),
            warn: document.getElementById('sw-warning'),
            dang: document.getElementById('sw-danger'),
            info: document.getElementById('sw-info'),
            inBg: document.getElementById('sw-input-bg'),
            inTx: document.getElementById('sw-input-text'),
            inBo: document.getElementById('sw-input-border'),
            seBg: document.getElementById('sw-select-bg'),
            seTx: document.getElementById('sw-select-text'),
            seBo: document.getElementById('sw-select-border'),
            disBg: document.getElementById('sw-disabled-bg'),
            disTx: document.getElementById('sw-disabled-text'),
            subBg: document.getElementById('sw-submenu-bg'),
            subTx: document.getElementById('sw-submenu-text'),
            subHv: document.getElementById('sw-submenu-hover'),
        };
        // end sw object marker
        if (sw.appBg) sw.appBg.style.background = colorAppBg;
        if (sw.prim) { sw.prim.style.background = colorPrimario; sw.prim.style.color = '#fff'; }
        if (sw.sec) { sw.sec.style.background = colorSecundario; sw.sec.style.color = '#fff'; }
        if (sw.btn) sw.btn.style.background = colorButton;
        const colorButtonHover = document.getElementById(prefijo + 'color_button_hover')?.value || colorButton;
        if (sw.btnH) sw.btnH.style.background = colorButtonHover;
        if (sw.btnT) { sw.btnT.style.background = colorButton; sw.btnT.style.color = colorButtonText; }
        if (sw.hdr) { sw.hdr.style.background = colorHeaderBg; sw.hdr.style.color = colorHeaderText; }
        if (sw.hdrT) { sw.hdrT.style.background = colorHeaderText; sw.hdrT.style.color = colorHeaderBg; }
        if (sw.gridH) sw.gridH.style.background = colorGridHeader;
        const colorInfo = document.getElementById(prefijo + 'color_info')?.value || '#3498db';
        if (sw.succ) sw.succ.style.background = colorSuccess;
        if (sw.warn) sw.warn.style.background = colorWarning;
        if (sw.dang) sw.dang.style.background = colorDanger;
        if (sw.info) sw.info.style.background = colorInfo;
        const colorInputBg = document.getElementById(prefijo + 'color_input_bg')?.value || '#ffffff';
        const colorInputText = document.getElementById(prefijo + 'color_input_text')?.value || '#495057';
        const colorInputBorder = document.getElementById(prefijo + 'color_input_border')?.value || '#dddddd';
        const colorSelectBg = document.getElementById(prefijo + 'color_select_bg')?.value || '#ffffff';
        const colorSelectText = document.getElementById(prefijo + 'color_select_text')?.value || '#495057';
        const colorSelectBorder = document.getElementById(prefijo + 'color_select_border')?.value || '#dddddd';
        const colorDisabledBg = document.getElementById(prefijo + 'color_disabled_bg')?.value || '#f0f0f0';
        const colorDisabledText = document.getElementById(prefijo + 'color_disabled_text')?.value || '#999999';
        const colorSubmenuBg = document.getElementById(prefijo + 'color_submenu_bg')?.value || '#34495e';
        const colorSubmenuText = document.getElementById(prefijo + 'color_submenu_text')?.value || '#ecf0f1';
        const colorSubmenuHover = document.getElementById(prefijo + 'color_submenu_hover')?.value || '#2c3e50';
        
        if (sw.inBg) sw.inBg.style.background = colorInputBg;
        if (sw.inTx) { sw.inTx.style.background = colorInputText; sw.inTx.style.color = '#fff'; }
        if (sw.inBo) { sw.inBo.style.borderColor = colorInputBorder; sw.inBo.style.background = '#fff'; }
        if (sw.seBg) sw.seBg.style.background = colorSelectBg;
        if (sw.seTx) { sw.seTx.style.background = colorSelectText; sw.seTx.style.color = '#fff'; }
        if (sw.seBo) { sw.seBo.style.borderColor = colorSelectBorder; sw.seBo.style.background = '#fff'; }
        if (sw.disBg) sw.disBg.style.background = colorDisabledBg;
        if (sw.disTx) { sw.disTx.style.background = colorDisabledText; sw.disTx.style.color = '#fff'; }
        if (sw.subBg) sw.subBg.style.background = colorSubmenuBg;
        if (sw.subTx) { sw.subTx.style.background = colorSubmenuText; sw.subTx.style.color = '#fff'; }
        if (sw.subHv) sw.subHv.style.background = colorSubmenuHover;

        // Tooltips HEX y botón copiar (click) en cada swatch
        const setTitle = (el, val) => { if (el && val) el.title = val; };

        const titles = [
            [sw.appBg, colorAppBg], [sw.prim, colorPrimario], [sw.sec, colorSecundario],
            [sw.btn, colorButton], [sw.btnH, colorButtonHover], [sw.btnT, colorButtonText],
            [sw.hdr, colorHeaderBg], [sw.hdrT, colorHeaderText], [sw.gridH, colorGridHeader],
            [sw.succ, colorSuccess], [sw.warn, colorWarning], [sw.dang, colorDanger], [sw.info, colorInfo],
            [sw.inBg, colorInputBg], [sw.inTx, colorInputText], [sw.inBo, colorInputBorder],
            [sw.seBg, colorSelectBg], [sw.seTx, colorSelectText], [sw.seBo, colorSelectBorder],
            [sw.disBg, colorDisabledBg], [sw.disTx, colorDisabledText],
            [sw.subBg, colorSubmenuBg], [sw.subTx, colorSubmenuText], [sw.subHv, colorSubmenuHover]
        ];
        titles.forEach(([el,val]) => { if (el) el.title = val; });

        const bindCopy = (el) => {
    if (!el || el._copyBound) return;
    el.style.cursor = 'pointer';
    el.addEventListener('click', async () => {
        try {
            const hex = el.title || '';
            if (!hex) return;
            await navigator.clipboard.writeText(hex);

            const oldText = el.textContent;
            const icon = el.querySelector('.sw-copy-icon');
            const oldClass = icon ? icon.className : '';
            const oldStyle = icon ? icon.getAttribute('style') : '';

            // Feedback visual: texto + icono check temporal
            el.textContent = 'Copiado';
            if (icon) {
                icon.className = 'fas fa-check sw-copy-icon';
                icon.style.cssText = 'position:absolute; top:2px; right:3px; font-size:9px; opacity:0.9; color:#1f9d55; pointer-events:none;';
                el.appendChild(icon);
            }

            setTimeout(() => {
                el.textContent = oldText;
                if (icon) {
                    icon.className = oldClass;
                    if (oldStyle) icon.setAttribute('style', oldStyle);
                    el.appendChild(icon);
                }
            }, 700);
        } catch (e) {}
    });
    el._copyBound = true;
};
        // end sw object marker
        [sw.appBg, sw.prim, sw.sec, sw.btn, sw.btnH, sw.btnT, sw.hdr, sw.hdrT, sw.gridH,
         sw.succ, sw.warn, sw.dang, sw.info, sw.inBg, sw.inTx, sw.inBo, sw.seBg, sw.seTx,
         sw.seBo, sw.disBg, sw.disTx, sw.subBg, sw.subTx, sw.subHv].forEach(bindCopy);
        
        // Actualizar fondo del preview con el color de fondo de la app
        const colorPreview = document.getElementById('color-preview');
        if (colorPreview) {
            colorPreview.style.background = colorAppBg;
        }

        // Actualizar nuevos previews
        const previewIconHome = document.getElementById('preview-icon-home');
        const previewIconUser = document.getElementById('preview-icon-user');
        const previewIconFile = document.getElementById('preview-icon-file');
        const previewDisabledInput = document.getElementById('preview-disabled-input');
        const previewDisabledSelect = document.getElementById('preview-disabled-select');
        const previewSubmenuBg = document.getElementById('preview-submenu-bg');
        const previewSubmenuText = document.getElementById('preview-submenu-text');
        const previewSubmenuText2 = document.getElementById('preview-submenu-text2');
        
        // Iconos con color primario
        if (previewIconHome) {
            previewIconHome.style.background = colorPrimario;
            previewIconHome.style.color = colorHeaderText;
        }
        if (previewIconUser) {
            previewIconUser.style.background = colorPrimario;
            previewIconUser.style.color = colorHeaderText;
        }
        if (previewIconFile) {
            previewIconFile.style.background = colorPrimario;
            previewIconFile.style.color = colorHeaderText;
        }
        
        // Campos disabled
        if (previewDisabledInput) {
            previewDisabledInput.style.background = colorDisabledBg;
            previewDisabledInput.style.color = colorDisabledText;
            previewDisabledInput.style.borderColor = colorInputBorder;
        }
        if (previewDisabledSelect) {
            previewDisabledSelect.style.background = colorDisabledBg;
            previewDisabledSelect.style.color = colorDisabledText;
            previewDisabledSelect.style.borderColor = colorInputBorder;
        }
        
        // Submenu
        if (previewSubmenuBg) {
            previewSubmenuBg.style.background = colorSubmenuBg;
        }
        if (previewSubmenuText) {
            previewSubmenuText.style.color = colorSubmenuText;
        }
        if (previewSubmenuText2) {
            previewSubmenuText2.style.color = colorSubmenuText;
        }
        

        // Actualizar previews de notificaciones
        const previewNotifSuccess = document.getElementById('preview-notif-success');
        const previewNotifWarning = document.getElementById('preview-notif-warning');
        const previewNotifDanger = document.getElementById('preview-notif-danger');
        
        if (previewNotifSuccess) {
            previewNotifSuccess.style.background = hexToRgba(colorSuccess, 0.15);
            previewNotifSuccess.style.borderLeftColor = colorSuccess;
            previewNotifSuccess.style.color = colorSuccess;
        }
        if (previewNotifWarning) {
            previewNotifWarning.style.background = hexToRgba(colorWarning, 0.15);
            previewNotifWarning.style.borderLeftColor = colorWarning;
            previewNotifWarning.style.color = colorWarning;
        }
        if (previewNotifDanger) {
            previewNotifDanger.style.background = hexToRgba(colorDanger, 0.15);
            previewNotifDanger.style.borderLeftColor = colorDanger;
            previewNotifDanger.style.color = colorDanger;
        }
        
        

        // Actualizar icono settings
        const previewIconSettings = document.getElementById('preview-icon-settings');
        if (previewIconSettings) {
            previewIconSettings.style.background = colorPrimario;
            previewIconSettings.style.color = colorHeaderText;
        }
        
        // Actualizar previews de modal
        const previewModalHeader = document.getElementById('preview-modal-header');
        const previewModalBtnPrimary = document.getElementById('preview-modal-btn-primary');
        const previewModalBtnSecondary = document.getElementById('preview-modal-btn-secondary');
        
        if (previewModalHeader) {
            previewModalHeader.style.background = 'linear-gradient(135deg, ' + colorPrimario + ' 0%, ' + colorSecundario + ' 100%)';
            previewModalHeader.style.color = colorHeaderText;
        }
        if (previewModalBtnPrimary) {
            previewModalBtnPrimary.style.background = colorButton;
            previewModalBtnPrimary.style.color = colorButtonText;
        }

// Actualizar previews de modal
        
        
    } catch (error) {
        console.error('Error actualizando preview:', error);
    }
}

// Alias para compatibilidad con los inputs de color
function actualizarVistaPrevia() {
    console.log('🎨 actualizarVistaPrevia() llamada');
    
    // Detectar prefijo (edit_ o vacío)
    const prefijo = document.getElementById('edit_color_primario') ? 'edit_' : '';
    
    // Recoger todos los colores actuales de los inputs
    const colores = {};
    const campos = [
        'color_primario', 'color_secundario', 'color_success', 'color_warning', 'color_danger', 'color_info',
        'color_button', 'color_button_hover', 'color_button_text',
        'color_app_bg', 'color_header_bg', 'color_header_text', 'color_grid_header',
        'color_input_bg', 'color_input_text', 'color_input_border',
        'color_select_bg', 'color_select_text', 'color_select_border',
        'color_disabled_bg', 'color_disabled_text',
        'color_submenu_bg', 'color_submenu_text', 'color_submenu_hover',
        'color_grid_bg', 'color_grid_text', 'color_icon'
    ];
    
    campos.forEach(campo => {
        const input = document.getElementById(prefijo + campo);
        if (input && input.value) {
            colores[campo] = input.value;
        }
    });
    
    // Actualizar sistema de preview con CSS Variables
    actualizarPreviewEnTiempoReal(colores);
}

// Plantillas de colores predefinidas - Basadas en temas profesionales populares
const plantillasColores = {
    clasico: {
        nombre: 'Material Design',
        descripcion: 'Diseño limpio de Google',
        color_primario: '#1976d2',
        color_secundario: '#42a5f5',
        color_success: '#4caf50',
        color_warning: '#ff9800',
        color_danger: '#f44336',
        color_info: '#2196f3',
        color_button: '#1976d2',
        color_button_hover: '#1565c0',
        color_button_text: '#ffffff',
        color_app_bg: '#fafafa',
        color_header_bg: '#1976d2',
        color_header_text: '#ffffff',
        color_grid_header: '#1976d2',
        color_grid_hover: 'rgba(25,118,210,0.1)',
        color_input_bg: '#ffffff',
        color_input_text: '#333333',
        color_input_border: '#dddddd',
        color_select_bg: '#ffffff',
        color_select_text: '#333333',
        color_select_border: '#dddddd',
        color_disabled_bg: '#f5f5f5',
        color_disabled_text: '#999999',
        color_submenu_bg: '#f8f9fa',
        color_submenu_text: '#333333',
        color_submenu_hover: '#e9ecef'
    },
    oscuro: {
        nombre: 'Dracula',
        descripcion: 'Tema oscuro elegante',
        color_primario: '#282a36',
        color_secundario: '#44475a',
        color_success: '#50fa7b',
        color_warning: '#f1fa8c',
        color_danger: '#ff5555',
        color_info: '#8be9fd',
        color_button: '#bd93f9',
        color_button_hover: '#9580d6',
        color_button_text: '#f8f8f2',
        color_app_bg: '#1e1f29',
        color_header_bg: '#282a36',
        color_header_text: '#f8f8f2',
        color_grid_header: '#44475a',
        color_grid_hover: 'rgba(68,71,90,0.3)',
        color_input_bg: '#2a2a2a',
        color_input_text: '#e0e0e0',
        color_input_border: '#444444',
        color_select_bg: '#2a2a2a',
        color_select_text: '#e0e0e0',
        color_select_border: '#444444',
        color_disabled_bg: '#1a1a1a',
        color_disabled_text: '#666666',
        color_submenu_bg: '#44475a',
        color_submenu_text: '#e0e0e0',
        color_submenu_hover: '#282a36'
    },
    verde: {
        nombre: 'Nord',
        descripcion: 'Minimalista escandinavo',
        color_primario: '#2e3440',
        color_secundario: '#3b4252',
        color_success: '#a3be8c',
        color_warning: '#ebcb8b',
        color_danger: '#bf616a',
        color_info: '#88c0d0',
        color_button: '#5e81ac',
        color_button_hover: '#81a1c1',
        color_button_text: '#eceff4',
        color_app_bg: '#eceff4',
        color_header_bg: '#2e3440',
        color_header_text: '#eceff4',
        color_grid_header: '#3b4252',
        color_grid_hover: 'rgba(59,66,82,0.2)',
        color_input_bg: '#ffffff',
        color_input_text: '#333333',
        color_input_border: '#dddddd',
        color_select_bg: '#ffffff',
        color_select_text: '#333333',
        color_select_border: '#dddddd',
        color_disabled_bg: '#f5f5f5',
        color_disabled_text: '#999999',
        color_submenu_bg: '#f8f9fa',
        color_submenu_text: '#333333',
        color_submenu_hover: '#e9ecef'
    },
    morado: {
        nombre: 'One Dark',
        descripcion: 'Tema de Atom Editor',
        color_primario: '#282c34',
        color_secundario: '#3e4451',
        color_success: '#98c379',
        color_warning: '#e5c07b',
        color_danger: '#e06c75',
        color_info: '#61afef',
        color_button: '#c678dd',
        color_button_hover: '#a353ba',
        color_button_text: '#abb2bf',
        color_app_bg: '#21252b',
        color_header_bg: '#282c34',
        color_header_text: '#abb2bf',
        color_grid_header: '#3e4451',
        color_grid_hover: 'rgba(62,68,81,0.3)',
        color_input_bg: '#2a2a2a',
        color_input_text: '#e0e0e0',
        color_input_border: '#444444',
        color_select_bg: '#2a2a2a',
        color_select_text: '#e0e0e0',
        color_select_border: '#444444',
        color_disabled_bg: '#1a1a1a',
        color_disabled_text: '#666666',
        color_submenu_bg: '#3e4451',
        color_submenu_text: '#e0e0e0',
        color_submenu_hover: '#282c34'
    },
    naranja: {
        nombre: 'Solarized Light',
        descripcion: 'Suave para los ojos',
        color_primario: '#268bd2',
        color_secundario: '#2aa198',
        color_success: '#859900',
        color_warning: '#b58900',
        color_danger: '#dc322f',
        color_info: '#268bd2',
        color_button: '#268bd2',
        color_button_hover: '#2075c7',
        color_button_text: '#fdf6e3',
        color_app_bg: '#fdf6e3',
        color_header_bg: '#268bd2',
        color_header_text: '#fdf6e3',
        color_grid_header: '#2aa198',
        color_grid_hover: 'rgba(38,139,210,0.1)',
        color_input_bg: '#ffffff',
        color_input_text: '#333333',
        color_input_border: '#dddddd',
        color_select_bg: '#ffffff',
        color_select_text: '#333333',
        color_select_border: '#dddddd',
        color_disabled_bg: '#f5f5f5',
        color_disabled_text: '#999999',
        color_submenu_bg: '#f8f9fa',
        color_submenu_text: '#333333',
        color_submenu_hover: '#e9ecef'
    },
    turquesa: {
        nombre: 'GitHub Dark',
        descripcion: 'Tema oscuro de GitHub',
        color_primario: '#0d1117',
        color_secundario: '#161b22',
        color_success: '#238636',
        color_warning: '#d29922',
        color_danger: '#da3633',
        color_info: '#58a6ff',
        color_button: '#238636',
        color_button_hover: '#2ea043',
        color_button_text: '#c9d1d9',
        color_app_bg: '#0d1117',
        color_header_bg: '#161b22',
        color_header_text: '#c9d1d9',
        color_grid_header: '#21262d',
        color_grid_hover: 'rgba(33,38,45,0.5)',
        color_input_bg: '#2a2a2a',
        color_input_text: '#e0e0e0',
        color_input_border: '#444444',
        color_select_bg: '#2a2a2a',
        color_select_text: '#e0e0e0',
        color_select_border: '#444444',
        color_disabled_bg: '#1a1a1a',
        color_disabled_text: '#666666',
        color_submenu_bg: '#161b22',
        color_submenu_text: '#e0e0e0',
        color_submenu_hover: '#0d1117'
    },
    gris: {
        nombre: 'Monokai',
        descripcion: 'Clásico de Sublime Text',
        color_primario: '#272822',
        color_secundario: '#3e3d32',
        color_success: '#a6e22e',
        color_warning: '#e6db74',
        color_danger: '#f92672',
        color_info: '#66d9ef',
        color_button: '#f92672',
        color_button_hover: '#ae81ff',
        color_button_text: '#f8f8f2',
        color_app_bg: '#1e1f1c',
        color_header_bg: '#272822',
        color_header_text: '#f8f8f2',
        color_grid_header: '#3e3d32',
        color_grid_hover: 'rgba(62,61,50,0.4)',
        color_input_bg: '#2a2a2a',
        color_input_text: '#e0e0e0',
        color_input_border: '#444444',
        color_select_bg: '#2a2a2a',
        color_select_text: '#e0e0e0',
        color_select_border: '#444444',
        color_disabled_bg: '#1a1a1a',
        color_disabled_text: '#666666',
        color_submenu_bg: '#3e3d32',
        color_submenu_text: '#e0e0e0',
        color_submenu_hover: '#272822'
    },
    rojo: {
        nombre: 'Gruvbox',
        descripcion: 'Retro cálido',
        color_primario: '#282828',
        color_secundario: '#3c3836',
        color_success: '#b8bb26',
        color_warning: '#fabd2f',
        color_danger: '#fb4934',
        color_info: '#83a598',
        color_button: '#fe8019',
        color_button_hover: '#d65d0e',
        color_button_text: '#ebdbb2',
        color_app_bg: '#1d2021',
        color_header_bg: '#282828',
        color_header_text: '#ebdbb2',
        color_grid_header: '#3c3836',
        color_grid_hover: 'rgba(60,56,54,0.4)',
        color_input_bg: '#2a2a2a',
        color_input_text: '#e0e0e0',
        color_input_border: '#444444',
        color_select_bg: '#2a2a2a',
        color_select_text: '#e0e0e0',
        color_select_border: '#444444',
        color_disabled_bg: '#1a1a1a',
        color_disabled_text: '#666666',
        color_submenu_bg: '#3c3836',
        color_submenu_text: '#e0e0e0',
        color_submenu_hover: '#282828'
    },
    glassmorphism: {
        nombre: 'Glassmorphism',
        descripcion: 'Moderno con efectos de vidrio',
        color_primario: '#080710',
        color_secundario: '#1a1a2e',
        color_success: '#23a2f6',
        color_warning: '#f09819',
        color_danger: '#ff512f',
        color_info: '#23a2f6',
        color_button: '#23a2f6',
        color_button_hover: '#1845ad',
        color_button_text: '#ffffff',
        color_app_bg: '#080710',
        color_header_bg: '#1a1a2e',
        color_header_text: '#ffffff',
        color_grid_header: '#1845ad',
        color_grid_hover: 'rgba(35,162,246,0.2)',
        color_input_bg: '#2a2a2a',
        color_input_text: '#e0e0e0',
        color_input_border: '#444444',
        color_select_bg: '#2a2a2a',
        color_select_text: '#e0e0e0',
        color_select_border: '#444444',
        color_disabled_bg: '#1a1a1a',
        color_disabled_text: '#666666',
        color_submenu_bg: '#1a1a2e',
        color_submenu_text: '#e0e0e0',
        color_submenu_hover: '#080710'
    },
    indigo: {
        nombre: 'Moderno Índigo',
        descripcion: 'Limpio y profesional con tonos morados',
        color_primario: '#6366f1',
        color_secundario: '#818cf8',
        color_success: '#10b981',
        color_warning: '#f59e0b',
        color_danger: '#ef4444',
        color_info: '#3b82f6',
        color_button: '#6366f1',
        color_button_hover: '#4f46e5',
        color_button_text: '#ffffff',
        color_app_bg: '#ffffff',
        color_header_bg: '#6366f1',
        color_header_text: '#ffffff',
        color_grid_header: '#818cf8',
        color_grid_hover: 'rgba(99,102,241,0.1)',
        color_input_bg: '#ffffff',
        color_input_text: '#333333',
        color_input_border: '#dddddd',
        color_select_bg: '#ffffff',
        color_select_text: '#333333',
        color_select_border: '#dddddd',
        color_disabled_bg: '#f5f5f5',
        color_disabled_text: '#999999',
        color_submenu_bg: '#f8f9fa',
        color_submenu_text: '#333333',
        color_submenu_hover: '#e9ecef'
    },
    classic: {
        nombre: 'Classic Panel',
        descripcion: 'Panel oscuro profesional',
        color_primario: '#2c3e50',
        color_secundario: '#34495e',
        color_success: '#27ae60',
        color_warning: '#f39c12',
        color_danger: '#e74c3c',
        color_info: '#3498db',
        color_button: '#3498db',
        color_button_hover: '#2980b9',
        color_button_text: '#ffffff',
        color_app_bg: '#2c3e50',
        color_header_bg: '#34495e',
        color_header_text: '#ecf0f1',
        color_grid_header: '#34495e',
        color_grid_hover: 'rgba(52,73,94,0.3)',
        color_input_bg: '#2a2a2a',
        color_input_text: '#e0e0e0',
        color_input_border: '#444444',
        color_select_bg: '#2a2a2a',
        color_select_text: '#e0e0e0',
        color_select_border: '#444444',
        color_disabled_bg: '#1a1a1a',
        color_disabled_text: '#666666',
        color_submenu_bg: '#34495e',
        color_submenu_text: '#e0e0e0',
        color_submenu_hover: '#2c3e50'
    },
    aleph70: {
        nombre: 'Aleph70',
        descripcion: 'Tema original del sistema',
        color_primario: '#243342',
        color_secundario: '#ffffff',
        color_success: '#27ae60',
        color_warning: '#f39c12',
        color_danger: '#e74c3c',
        color_info: '#3498db',
        color_button: '#2c3e50',
        color_button_hover: '#34495e',
        color_button_text: '#ffffff',
        color_app_bg: '#ffffff',
        color_header_bg: '#2c3e50',
        color_header_text: '#ffffff',
        color_grid_header: '#2c3e50',
        color_grid_hover: 'rgba(44,62,80,0.1)',
        color_input_bg: '#ffffff',
        color_input_text: '#333333',
        color_input_border: '#dddddd',
        color_select_bg: '#ffffff',
        color_select_text: '#333333',
        color_select_border: '#dddddd',
        color_disabled_bg: '#f5f5f5',
        color_disabled_text: '#999999',
        color_submenu_bg: '#243342',
        color_submenu_text: '#ecf0f1',
        color_submenu_hover: '#34495e',
        color_grid_bg: '#ffffff',
        color_grid_text: '#333333',
        color_icon: '#ecf0f1'
    }
};

// Función para detectar qué plantilla está activa
function detectarPlantillaActiva(empresa) {
    console.log('🔍 detectarPlantillaActiva() - Empresa:', empresa);
    
    // Colores clave para detectar plantilla
    const coloresClave = ['color_primario', 'color_secundario', 'color_app_bg', 'color_header_bg'];
    
    console.log('📋 Colores de la empresa:');
    coloresClave.forEach(clave => {
        console.log(`  ${clave}: ${empresa[clave] || 'undefined'}`);
    });
    
    for (const [nombre, plantilla] of Object.entries(plantillasColores)) {
        let coincidencias = 0;
        let detalles = [];
        
        for (const clave of coloresClave) {
            const colorEmpresa = (empresa[clave] || '').toLowerCase().trim();
            const colorPlantilla = (plantilla[clave] || '').toLowerCase().trim();
            
            if (colorEmpresa === colorPlantilla) {
                coincidencias++;
                detalles.push(`✅ ${clave}: ${colorEmpresa}`);
            } else {
                detalles.push(`❌ ${clave}: ${colorEmpresa} vs ${colorPlantilla}`);
            }
        }
        
        console.log(`\n🎨 Plantilla "${nombre}": ${coincidencias}/4 coincidencias`);
        detalles.forEach(d => console.log(`   ${d}`));
        
        // Si coinciden al menos 3 de 4 colores clave, es esa plantilla
        if (coincidencias >= 3) {
            console.log(`✅ PLANTILLA DETECTADA: ${nombre}`);
            return nombre;
        }
    }
    
    console.log('⚠️ No se detectó ninguna plantilla (colores personalizados)');
    return null; // No hay plantilla coincidente (personalizado)
}

// Función para marcar plantilla activa visualmente
function marcarPlantillaActiva(nombrePlantilla) {
    console.log('🎯 marcarPlantillaActiva() - Plantilla:', nombrePlantilla);
    
    // Limpiar todas las marcas
    const todosBotones = document.querySelectorAll('[data-plantilla]');
    console.log(`   Botones encontrados: ${todosBotones.length}`);
    
    todosBotones.forEach(btn => {
        btn.style.outline = 'none';
        btn.style.boxShadow = '';
        const badge = btn.querySelector('.badge-activa');
        if (badge) badge.remove();
    });
    
    if (!nombrePlantilla) {
        console.log('   ⚠️ No hay plantilla para marcar');
        return;
    }
    
    // Marcar la plantilla activa
    const btnActivo = document.querySelector(`[data-plantilla="${nombrePlantilla}"]`);
    console.log(`   Buscando botón: [data-plantilla="${nombrePlantilla}"]`);
    console.log(`   Botón encontrado:`, btnActivo);
    if (btnActivo) {
        btnActivo.style.outline = '3px solid #4CAF50';
        btnActivo.style.boxShadow = '0 0 15px rgba(76, 175, 80, 0.5)';
        
        // Agregar badge "ACTIVA"
        const badge = document.createElement('div');
        badge.className = 'badge-activa';
        badge.innerHTML = '<i class="fas fa-check-circle"></i> ACTIVA';
        badge.style.cssText = 'position: absolute; top: -8px; right: -8px; background: #4CAF50; color: white; padding: 4px 8px; border-radius: 12px; font-size: 10px; font-weight: bold; box-shadow: 0 2px 4px rgba(0,0,0,0.3);';
        btnActivo.style.position = 'relative';
        btnActivo.appendChild(badge);
        
        console.log(`   ✅ Plantilla "${nombrePlantilla}" marcada correctamente`);
    } else {
        console.error(`   ❌ No se encontró el botón [data-plantilla="${nombrePlantilla}"]`);
    }
}

// Variable global para rastrear la plantilla base aplicada
let plantillaBaseActual = null;
let coloresOriginalesPlantilla = null;

// Función para cargar plantillas personalizadas desde localStorage
async function cargarPlantillasPersonalizadas() {
    try {
        // Intentar cargar desde localStorage primero
        const plantillasGuardadas = localStorage.getItem('plantillas_personalizadas');
        if (plantillasGuardadas) {
            const plantillas = JSON.parse(plantillasGuardadas);
            plantillas.forEach(p => {
                const key = `personalizada_${p.id}`;
                plantillasColores[key] = {
                    nombre: p.nombre,
                    descripcion: p.descripcion || `Basada en ${p.plantilla_base}`,
                    plantilla_base: p.plantilla_base,
                    color_primario: p.color_primario,
                    color_secundario: p.color_secundario,
                    color_success: p.color_success,
                    color_warning: p.color_warning,
                    color_danger: p.color_danger,
                    color_info: p.color_info,
                    color_button: p.color_button,
                    color_button_hover: p.color_button_hover,
                    color_button_text: p.color_button_text,
                    color_app_bg: p.color_app_bg,
                    color_header_bg: p.color_header_bg,
                    color_header_text: p.color_header_text,
                    color_grid_header: p.color_grid_header,
                    color_grid_hover: p.color_grid_hover,
                    color_input_bg: p.color_input_bg,
                    color_input_text: p.color_input_text,
                    color_input_border: p.color_input_border,
                    color_select_bg: p.color_select_bg,
                    color_select_text: p.color_select_text,
                    color_select_border: p.color_select_border,
                    color_disabled_bg: p.color_disabled_bg,
                    color_disabled_text: p.color_disabled_text,
                    color_submenu_bg: p.color_submenu_bg,
                    color_submenu_text: p.color_submenu_text,
                    color_submenu_hover: p.color_submenu_hover,
                    color_grid_bg: p.color_grid_bg,
                    color_grid_text: p.color_grid_text,
                    color_icon: p.color_icon
                                };
            });
            
            // Regenerar botones si el contenedor existe
            if (document.getElementById('plantillas-container')) {
                regenerarBotonesPlantillas('');
            }
            if (document.getElementById('plantillas-container-editar')) {
                regenerarBotonesPlantillas('edit_');
                inicializarPreviewEnTiempoReal('edit_');
            }
        }
    } catch (error) {
        console.error('Error cargando plantillas personalizadas:', error);
    }
}

// Cargar plantillas personalizadas cuando se carga el DOM
if (typeof document !== 'undefined') {
    document.addEventListener('DOMContentLoaded', cargarPlantillasPersonalizadas);
}

// Función para aplicar una plantilla de colores
function aplicarPlantilla(nombrePlantilla) {
    try {
        const plantilla = plantillasColores[nombrePlantilla];
        if (!plantilla) {
            mostrarNotificacion('Plantilla no encontrada', 'error');
            return;
        }
        
        // Guardar plantilla base y colores originales
        plantillaBaseActual = nombrePlantilla;
        coloresOriginalesPlantilla = { ...plantilla };
        console.log('🎨 Plantilla base establecida:', nombrePlantilla);
        
        // Determinar si estamos en modal de edición o creación
        const esEdicion = document.getElementById('formEditarEmpresa') !== null;
        const prefijo = esEdicion ? 'edit_' : '';
        console.log('🎨 Aplicando plantilla con prefijo:', prefijo);
        
        // Aplicar todos los colores de la plantilla con el prefijo correcto
        const setColor = (campo, valor) => {
            const elemento = document.getElementById(prefijo + campo);
            if (elemento) {
                elemento.value = valor;
                console.log(`✅ ${prefijo}${campo} = ${valor}`);
            } else {
                console.warn(`⚠️ No se encontró elemento: ${prefijo}${campo}`);
            }
        };
        // end sw object marker
        setColor('color_primario', plantilla.color_primario);
        setColor('color_secundario', plantilla.color_secundario);
        setColor('color_success', plantilla.color_success);
        setColor('color_warning', plantilla.color_warning);
        setColor('color_danger', plantilla.color_danger);
        setColor('color_info', plantilla.color_info);
        setColor('color_button', plantilla.color_button);
        setColor('color_button_hover', plantilla.color_button_hover);
        setColor('color_button_text', plantilla.color_button_text);
        setColor('color_app_bg', plantilla.color_app_bg);
        setColor('color_header_bg', plantilla.color_header_bg);
        setColor('color_header_text', plantilla.color_header_text);
        setColor('color_grid_header', plantilla.color_grid_header);
        setColor('color_input_bg', plantilla.color_input_bg);
        setColor('color_input_text', plantilla.color_input_text);
        setColor('color_input_border', plantilla.color_input_border);
        setColor('color_select_bg', plantilla.color_select_bg);
        setColor('color_select_text', plantilla.color_select_text);
        setColor('color_select_border', plantilla.color_select_border);
        setColor('color_disabled_bg', plantilla.color_disabled_bg);
        setColor('color_disabled_text', plantilla.color_disabled_text);
        setColor('color_submenu_bg', plantilla.color_submenu_bg);
        setColor('color_submenu_text', plantilla.color_submenu_text);
        setColor('color_submenu_hover', plantilla.color_submenu_hover);
        
        // Configurar listeners para detectar cambios manuales
        configurarDeteccionCambiosColores(prefijo);
        
        // Actualizar preview
        actualizarPreviewColores();
        
        mostrarNotificacion(`✨ Plantilla "${plantilla.nombre}" aplicada! Revisa el preview y guarda los cambios.`, 'success');
        
        // Scroll al preview
        const preview = document.getElementById('color-preview');
        if (preview) {
            preview.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
        
    } catch (error) {
        console.error('Error aplicando plantilla:', error);
        mostrarNotificacion('Error aplicando plantilla', 'error');
    }
}

// Configurar detección de cambios manuales en los colores
function configurarDeteccionCambiosColores(prefijo = '') {
    const camposColor = [
        'color_primario', 'color_secundario', 'color_success', 'color_warning',
        'color_danger', 'color_info', 'color_button', 'color_button_hover',
        'color_button_text', 'color_app_bg', 'color_header_bg', 'color_header_text',
        'color_grid_header', 'color_input_bg', 'color_input_text', 'color_input_border',
        'color_select_bg', 'color_select_text', 'color_select_border',
        'color_disabled_bg', 'color_disabled_text', 'color_submenu_bg',
        'color_submenu_text', 'color_submenu_hover'
    ];
    
    camposColor.forEach(campo => {
        const elemento = document.getElementById(prefijo + campo);
        if (elemento) {
            // Remover listener previo si existe
            elemento.removeEventListener('change', detectarCambioManual);
            // Agregar nuevo listener
            elemento.addEventListener('change', function() {
                detectarCambioManual(this, campo, prefijo);
            });
        }
    });
}

// Detectar cuando el usuario modifica un color manualmente
function detectarCambioManual(elemento, campo, prefijo) {
    if (!plantillaBaseActual || !coloresOriginalesPlantilla) {
        return; // No hay plantilla base, no crear personalizada
    }
    
    const valorActual = elemento.value;
    const valorOriginal = coloresOriginalesPlantilla[campo];
    
    // Si el valor cambió respecto al original de la plantilla
    if (valorActual !== valorOriginal) {
        console.log(`🎨 Detectado cambio manual en ${campo}: ${valorOriginal} → ${valorActual}`);
        crearPlantillaPersonalizada(prefijo);
    }
}

// Crear plantilla personalizada basada en la plantilla actual
async function crearPlantillaPersonalizada(prefijo = '') {
    const plantillaBase = plantillasColores[plantillaBaseActual];
    if (!plantillaBase) return;
    
    // Obtener todos los valores actuales de los inputs
    const obtenerColor = (campo) => {
        const elemento = document.getElementById(prefijo + campo);
        return elemento ? elemento.value : plantillaBase[campo];
    };
    
    const coloresActuales = {
        color_primario: obtenerColor('color_primario'),
        color_secundario: obtenerColor('color_secundario'),
        color_success: obtenerColor('color_success'),
        color_warning: obtenerColor('color_warning'),
        color_danger: obtenerColor('color_danger'),
        color_info: obtenerColor('color_info'),
        color_button: obtenerColor('color_button'),
        color_button_hover: obtenerColor('color_button_hover'),
        color_button_text: obtenerColor('color_button_text'),
        color_app_bg: obtenerColor('color_app_bg'),
        color_header_bg: obtenerColor('color_header_bg'),
        color_header_text: obtenerColor('color_header_text'),
        color_grid_header: obtenerColor('color_grid_header'),
        color_grid_hover: obtenerColor('color_grid_hover'),
        color_input_bg: obtenerColor('color_input_bg'),
        color_input_text: obtenerColor('color_input_text'),
        color_input_border: obtenerColor('color_input_border'),
        color_select_bg: obtenerColor('color_select_bg'),
        color_select_text: obtenerColor('color_select_text'),
        color_select_border: obtenerColor('color_select_border'),
        color_disabled_bg: obtenerColor('color_disabled_bg'),
        color_disabled_text: obtenerColor('color_disabled_text'),
        color_submenu_bg: obtenerColor('color_submenu_bg'),
        color_submenu_text: obtenerColor('color_submenu_text'),
        color_submenu_hover: obtenerColor('color_submenu_hover'),
        color_grid_bg: obtenerColor('color_grid_bg'),
        color_grid_text: obtenerColor('color_grid_text'),
        color_icon: obtenerColor('color_icon')
    };
    
    // Guardar en la base de datos
    try {
        const response = await fetch('/api/plantillas/personalizadas', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                nombre: `Personalizada basada en ${plantillaBase.nombre}`,
                descripcion: `Modificada desde ${plantillaBase.nombre}`,
                plantilla_base: plantillaBaseActual,
                ...coloresActuales
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            console.log('✨ Plantilla personalizada guardada en BD');
            
            // Recargar plantillas personalizadas de la BD
            await cargarPlantillasPersonalizadas();
            
            mostrarNotificacion('Plantilla personalizada creada y guardada', 'success');
        } else {
            console.error('Error guardando plantilla:', data.error);
            mostrarNotificacion('Error guardando plantilla personalizada', 'error');
        }
    } catch (error) {
        console.error('Error guardando plantilla personalizada:', error);
        mostrarNotificacion('Error de red guardando plantilla', 'error');
    }
}

// Función para guardar una plantilla personalizada
function guardarPlantillaPersonalizada(nombre, plantillaBase, colores) {
    try {
        const plantillasGuardadas = localStorage.getItem('plantillas_personalizadas');
        let plantillas = plantillasGuardadas ? JSON.parse(plantillasGuardadas) : [];
        
        // Generar ID único
        const id = Date.now();
        
        const nuevaPlantilla = {
            id: id,
            nombre: nombre,
            plantilla_base: plantillaBase,
            descripcion: `Basada en ${plantillasColores[plantillaBase]?.nombre || plantillaBase}`,
            ...colores
        };
        // end sw object marker
        plantillas.push(nuevaPlantilla);
        localStorage.setItem('plantillas_personalizadas', JSON.stringify(plantillas));
        
        console.log('✅ Plantilla personalizada guardada:', nombre);
        
        // Recargar plantillas
        cargarPlantillasPersonalizadas();
        
        return id;
    } catch (error) {
        console.error('Error guardando plantilla personalizada:', error);
        return null;
    }
}

// Función para crear plantilla personalizada desde colores actuales
function crearPlantillaPersonalizadaActual(prefijo = '') {
    const colores = {
        color_app_bg: document.getElementById(`${prefijo}color_app_bg`)?.value || '#ffffff',
        color_primario: document.getElementById(`${prefijo}color_primario`)?.value || '#2c3e50',
        color_secundario: document.getElementById(`${prefijo}color_secundario`)?.value || '#3498db',
        color_button: document.getElementById(`${prefijo}color_button`)?.value || '#3498db',
        color_button_hover: document.getElementById(`${prefijo}color_button_hover`)?.value || '#2980b9',
        color_button_text: document.getElementById(`${prefijo}color_button_text`)?.value || '#ffffff',
        color_header_bg: document.getElementById(`${prefijo}color_header_bg`)?.value || '#2c3e50',
        color_header_text: document.getElementById(`${prefijo}color_header_text`)?.value || '#ffffff',
        color_grid_header: document.getElementById(`${prefijo}color_grid_header`)?.value || '#2c3e50',
        color_success: document.getElementById(`${prefijo}color_success`)?.value || '#27ae60',
        color_warning: document.getElementById(`${prefijo}color_warning`)?.value || '#f39c12',
        color_danger: document.getElementById(`${prefijo}color_danger`)?.value || '#e74c3c',
        color_info: document.getElementById(`${prefijo}color_info`)?.value || '#3498db'
    };
    
    const plantillaBase = plantillaBaseActual || 'default';
    const nombre = `Personalizada ${new Date().toLocaleString('es-ES', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })}`;
    
    return guardarPlantillaPersonalizada(nombre, plantillaBase, colores);
}

// Regenerar botones de plantillas para incluir las personalizadas
function regenerarBotonesPlantillas(prefijo = '') {
    // Determinar qué contenedor usar según el contexto
    const contenedorId = prefijo === 'edit_' ? 'plantillas-container-editar' : 'plantillas-container';
    const contenedor = document.getElementById(contenedorId);
    
    if (!contenedor) {
        console.warn(`⚠️ No se encontró contenedor: ${contenedorId}`);
        return;
    }
    
    contenedor.innerHTML = '';
    
    // Mapear iconos para plantillas predefinidas
    const iconos = {
        'aleph70': 'fa-star',
        'glassmorphism': 'fa-moon',
        'cyber': 'fa-rocket',
        'darkmode': 'fa-adjust',
        'oceano': 'fa-water',
        'default': 'fa-redo'
    };
    
    // Crear botones para cada plantilla
    Object.keys(plantillasColores).forEach(key => {
        const plantilla = plantillasColores[key];
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'btn-plantilla';
        
        // Marcar plantillas personalizadas
        if (key.startsWith('personalizada_')) {
            button.classList.add('plantilla-personalizada');
            button.innerHTML = `
                <i class="fas fa-palette"></i> ${plantilla.nombre}
            `;
        } else {
            const icono = iconos[key] || 'fa-swatchbook';
            button.innerHTML = `
                <i class="fas ${icono}"></i> ${plantilla.nombre}
            `;
        }
        
        button.onclick = () => aplicarPlantilla(key);
        contenedor.appendChild(button);
    });
    
    console.log(`✨ Plantillas regeneradas en ${contenedorId}: ${Object.keys(plantillasColores).length} plantillas`);
}

// Función para guardar plantilla personalizada
function guardarPlantillaPersonalizada() {
    const nombre = document.getElementById('nombre_plantilla_personalizada').value.trim();
    
    if (!nombre) {
        alert('Por favor introduce un nombre para la plantilla');
        return;
    }
    
    // Obtener todos los colores actuales
    const colores = {
        color_primario: document.getElementById('edit_color_primario').value,
        color_secundario: document.getElementById('edit_color_secundario').value,
        color_success: document.getElementById('edit_color_success').value,
        color_warning: document.getElementById('edit_color_warning').value,
        color_danger: document.getElementById('edit_color_danger').value,
        color_info: document.getElementById('edit_color_info').value,
        color_button: document.getElementById('edit_color_button').value,
        color_button_hover: document.getElementById('edit_color_button_hover').value,
        color_button_text: document.getElementById('edit_color_button_text').value,
        color_app_bg: document.getElementById('edit_color_app_bg').value,
        color_header_bg: document.getElementById('edit_color_header_bg').value,
        color_header_text: document.getElementById('edit_color_header_text').value,
        color_grid_header: document.getElementById('edit_color_grid_header').value
    };
    
    // Enviar a la API
    fetch('/api/plantillas/personalizadas', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            nombre: nombre,
            colores: colores
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert('✅ Plantilla guardada correctamente: ' + nombre);
            document.getElementById('nombre_plantilla_personalizada').value = '';
            // Recargar plantillas personalizadas si existe la función
            if (typeof cargarPlantillasPersonalizadas === 'function') {
                cargarPlantillasPersonalizadas();
            }
        } else {
            alert('❌ Error al guardar: ' + (data.error || 'Error desconocido'));
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('❌ Error al guardar la plantilla');
    });
}


// Función para auto-guardar plantilla modificada
function autoGuardarPlantillaModificada() {
    // Limpiar timer anterior
    if (timerAutoGuardado) {
        clearTimeout(timerAutoGuardado);
    }
    
    // Esperar 2 segundos después del último cambio
    timerAutoGuardado = setTimeout(() => {
        if (!plantillaBaseActual) {
            console.log('⏭️ No hay plantilla base, skip auto-guardado');
            return;
        }
        
        // Detectar si estamos en edición o creación
        const esEdicion = document.getElementById('formEditarEmpresa') !== null;
        const prefijo = esEdicion ? 'edit_' : '';
        
        // Obtener colores actuales
        const coloresActuales = {
            color_primario: document.getElementById(prefijo + 'color_primario')?.value,
            color_secundario: document.getElementById(prefijo + 'color_secundario')?.value,
            color_success: document.getElementById(prefijo + 'color_success')?.value,
            color_warning: document.getElementById(prefijo + 'color_warning')?.value,
            color_danger: document.getElementById(prefijo + 'color_danger')?.value,
            color_info: document.getElementById(prefijo + 'color_info')?.value,
            color_button: document.getElementById(prefijo + 'color_button')?.value,
            color_button_hover: document.getElementById(prefijo + 'color_button_hover')?.value,
            color_button_text: document.getElementById(prefijo + 'color_button_text')?.value,
            color_app_bg: document.getElementById(prefijo + 'color_app_bg')?.value,
            color_header_bg: document.getElementById(prefijo + 'color_header_bg')?.value,
            color_header_text: document.getElementById(prefijo + 'color_header_text')?.value,
            color_grid_header: document.getElementById(prefijo + 'color_grid_header')?.value
        };
        // end sw object marker
        // Comparar con originales
        let hayDiferencias = false;
        for (let key in coloresOriginales) {
            if (coloresOriginales[key] !== coloresActuales[key]) {
                hayDiferencias = true;
                break;
            }
        }
        
        if (!hayDiferencias) {
            console.log('⏭️ No hay diferencias, skip auto-guardado');
            return;
        }
        
        // Generar timestamp
        const ahora = new Date();
        const timestamp = ahora.toISOString().slice(0, 19).replace('T', '_').replace(/:/g, '-');
        const nombrePlantilla = `plantilla_${timestamp}_(basada_en_${plantillaBaseActual})`;
        
        console.log('💾 Auto-guardando plantilla:', nombrePlantilla);
        
        // Enviar a la API
        fetch('/api/plantillas/personalizadas', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                nombre: nombrePlantilla,
                colores: coloresActuales
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                console.log('✅ Plantilla auto-guardada:', nombrePlantilla);
                // Actualizar la plantilla base y colores originales
                plantillaBaseActual = nombrePlantilla;
                coloresOriginales = JSON.parse(JSON.stringify(coloresActuales));
            } else {
                console.warn('⚠️ Error al auto-guardar:', data.error);
            }
        })
        .catch(error => {
            console.error('❌ Error en auto-guardado:', error);
        });
    }, 2000); // 2 segundos de debounce
}

// Agregar listeners a todos los inputs de color para auto-guardado
function inicializarAutoGuardado() {
    const esEdicion = document.getElementById('formEditarEmpresa') !== null;
    const prefijo = esEdicion ? 'edit_' : '';
    
    const colores = [
        'color_primario', 'color_secundario', 'color_success', 'color_warning',
        'color_danger', 'color_info', 'color_button', 'color_button_hover',
        'color_button_text', 'color_app_bg', 'color_header_bg', 'color_header_text',
        'color_grid_header'
    ];
    
    colores.forEach(colorId => {
        const input = document.getElementById(prefijo + colorId);
        if (input) {
            input.addEventListener('input', () => {
                autoGuardarPlantillaModificada();
            });
        }
    });
    
    console.log('🎨 Auto-guardado inicializado para', colores.length, 'colores');
}


