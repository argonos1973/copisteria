// Variables globales
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
                    
                    <div class="modal-actions" style="margin-top: 25px; padding-top: 15px; border-top: 1px solid #ddd;">
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
                <div class="modal-content" style="max-width: 700px;">
                    <div class="modal-header">
                        <h2><i class="fas fa-edit"></i> Editar Empresa: ${empresa.nombre}</h2>
                        <span class="close" onclick="cerrarModalEditarEmpresa()">&times;</span>
                    </div>
                    
                    <form id="formEditarEmpresa">
                        <input type="hidden" name="empresa_id" value="${empresa.id}">
                        
                        <div class="form-row" style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px;">
                            <div class="form-group">
                                <label>Código (no editable)</label>
                                <input type="text" value="${empresa.codigo}" disabled style="background: #f0f0f0;">
                            </div>
                            
                            <div class="form-group">
                                <label for="edit_nombre">Nombre *</label>
                                <input type="text" id="edit_nombre" name="nombre" value="${empresa.nombre || ''}" required>
                            </div>
                        </div>
                        
                        <div class="form-row" style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px;">
                            <div class="form-group">
                                <label for="edit_cif">CIF/NIF</label>
                                <input type="text" id="edit_cif" name="cif" value="${empresa.cif || ''}">
                            </div>
                            
                            <div class="form-group">
                                <label for="edit_telefono">Teléfono</label>
                                <input type="text" id="edit_telefono" name="telefono" value="${empresa.telefono || ''}">
                            </div>
                        </div>
                        
                        <div class="form-group">
                            <label for="edit_direccion">Dirección</label>
                            <input type="text" id="edit_direccion" name="direccion" value="${empresa.direccion || ''}">
                        </div>
                        
                        <div class="form-row" style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px;">
                            <div class="form-group">
                                <label for="edit_email">Email</label>
                                <input type="email" id="edit_email" name="email" value="${empresa.email || ''}">
                            </div>
                            
                            <div class="form-group">
                                <label for="edit_web">Sitio Web</label>
                                <input type="text" id="edit_web" name="web" value="${empresa.web || ''}">
                            </div>
                        </div>
                        
                        <div class="form-row" style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px;">
                            <div class="form-group">
                                <label for="edit_color_primario">Color Primario</label>
                                <input type="color" id="edit_color_primario" name="color_primario" value="${empresa.color_primario || '#2c3e50'}">
                            </div>
                            
                            <div class="form-group">
                                <label for="edit_color_secundario">Color Secundario</label>
                                <input type="color" id="edit_color_secundario" name="color_secundario" value="${empresa.color_secundario || '#3498db'}">
                            </div>
                        </div>
                        
                        <div class="form-group">
                            <label>Logo Actual</label>
                            ${empresa.logo_header && !empresa.logo_header.startsWith('default_') ? 
                                `<img src="/static/logos/${empresa.logo_header}" style="max-width: 200px; border: 1px solid #ddd; padding: 10px;">` :
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
                activa: document.getElementById('edit_activa').checked ? 1 : 0
            };
            
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
