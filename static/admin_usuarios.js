// admin_usuarios.js - Gestión de usuarios
let usuarios = [];
let modalElement = null;

// Inicialización
document.addEventListener('DOMContentLoaded', function() {
    modalElement = document.getElementById('modalNuevoUsuario');
    cargarUsuarios();
});

// Cargar lista de usuarios
async function cargarUsuarios() {
    try {
        const response = await fetch('/api/admin/usuarios');
        if (\!response.ok) throw new Error('Error al cargar usuarios');
        
        usuarios = await response.json();
        mostrarUsuarios();
    } catch (error) {
        console.error('Error:', error);
        mostrarAlerta('Error al cargar usuarios', 'error');
    }
}

// Mostrar usuarios en la tabla
function mostrarUsuarios() {
    const tbody = document.getElementById('usuariosTableBody');
    
    if (usuarios.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="7" style="text-align: center;">
                    No hay usuarios registrados
                </td>
            </tr>
        `;
        return;
    }

    tbody.innerHTML = usuarios.map(usuario => `
        <tr>
            <td>${usuario.id}</td>
            <td><strong>${usuario.username}</strong></td>
            <td>${usuario.nombre_completo || '-'}</td>
            <td>${usuario.email || '-'}</td>
            <td>
                ${usuario.empresa_nombre ? 
                    `<span class="status-badge status-info">${usuario.empresa_nombre}</span>` : 
                    `<span class="status-badge status-warning">Sin empresa</span>`
                }
            </td>
            <td>
                ${usuario.activo ? 
                    '<span class="status-badge status-active">Activo</span>' : 
                    '<span class="status-badge status-inactive">Inactivo</span>'
                }
            </td>
            <td class="actions-cell">
                <button class="btn-icon btn-edit" 
                        onclick="editarUsuario(${usuario.id})"
                        title="Editar">
                    <i class="fas fa-edit"></i>
                </button>
                ${\!usuario.empresa_nombre ? `
                    <button class="btn-icon btn-info" 
                            onclick="asignarEmpresa(${usuario.id})"
                            title="Asignar Empresa">
                        <i class="fas fa-building"></i>
                    </button>
                ` : ''}
                <button class="btn-icon ${usuario.activo ? 'btn-delete' : 'btn-success'}" 
                        onclick="toggleUsuario(${usuario.id}, ${usuario.activo})"
                        title="${usuario.activo ? 'Desactivar' : 'Activar'}">
                    <i class="fas fa-${usuario.activo ? 'ban' : 'check'}"></i>
                </button>
            </td>
        </tr>
    `).join('');
}

// Mostrar modal nuevo usuario
function mostrarModalNuevoUsuario() {
    document.getElementById('formNuevoUsuario').reset();
    modalElement.style.display = 'flex';
}

// Cerrar modal
function cerrarModal() {
    modalElement.style.display = 'none';
}

// Crear nuevo usuario
async function crearUsuario() {
    const form = document.getElementById('formNuevoUsuario');
    if (\!form.checkValidity()) {
        form.reportValidity();
        return;
    }

    const datos = {
        username: document.getElementById('username').value,
        nombre_completo: document.getElementById('nombre_completo').value,
        password: document.getElementById('password').value,
        email: document.getElementById('email').value || null,
        telefono: document.getElementById('telefono').value || null,
        asignar_empresa: document.getElementById('asignarEmpresa').checked
    };

    try {
        const response = await fetch('/api/admin/usuarios/crear', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(datos)
        });

        const result = await response.json();
        
        if (response.ok) {
            mostrarAlerta('Usuario creado exitosamente', 'success');
            cerrarModal();
            cargarUsuarios();
        } else {
            mostrarAlerta(result.error || 'Error al crear usuario', 'error');
        }
    } catch (error) {
        console.error('Error:', error);
        mostrarAlerta('Error al crear usuario', 'error');
    }
}

// Activar/Desactivar usuario
async function toggleUsuario(id, estadoActual) {
    if (\!confirm(`¿Deseas ${estadoActual ? 'desactivar' : 'activar'} este usuario?`)) {
        return;
    }

    try {
        const response = await fetch(`/api/admin/usuarios/${id}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ activo: \!estadoActual })
        });

        if (response.ok) {
            mostrarAlerta('Usuario actualizado', 'success');
            cargarUsuarios();
        } else {
            mostrarAlerta('Error al actualizar usuario', 'error');
        }
    } catch (error) {
        console.error('Error:', error);
        mostrarAlerta('Error al actualizar usuario', 'error');
    }
}

// Mostrar alerta
function mostrarAlerta(mensaje, tipo) {
    const container = document.getElementById('alertContainer');
    const alert = document.createElement('div');
    alert.className = `alert alert-${tipo}`;
    alert.innerHTML = `
        <i class="fas fa-${tipo === 'success' ? 'check-circle' : tipo === 'error' ? 'exclamation-circle' : 'info-circle'}"></i>
        ${mensaje}
        <button class="alert-close" onclick="this.parentElement.remove()">
            <i class="fas fa-times"></i>
        </button>
    `;
    container.innerHTML = '';
    container.appendChild(alert);
    
    // Auto-cerrar después de 5 segundos
    setTimeout(() => {
        alert.remove();
    }, 5000);
}

// Placeholder para editar usuario
function editarUsuario(id) {
    mostrarAlerta('Función de edición en desarrollo', 'info');
}

// Placeholder para asignar empresa
function asignarEmpresa(id) {
    mostrarAlerta('Función de asignación de empresa en desarrollo', 'info');
}
