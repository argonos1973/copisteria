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
        if (!response.ok) throw new Error('Error al cargar usuarios');
        
        usuarios = await response.json();
        mostrarUsuarios();
    } catch (error) {
        console.error('Error:', error);
        mostrarAlerta('Error al cargar usuarios', 'danger');
    }
}

// Mostrar usuarios en la tabla
function mostrarUsuarios() {
    const tbody = document.getElementById('usuariosTableBody');
    
    if (usuarios.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="7" class="text-center">
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
                    `<span class="badge badge-info">${usuario.empresa_nombre}</span>` : 
                    `<span class="badge badge-warning">Sin empresa</span>`
                }
            </td>
            <td>
                ${usuario.activo ? 
                    '<span class="badge badge-success">Activo</span>' : 
                    '<span class="badge badge-danger">Inactivo</span>'
                }
            </td>
            <td>
                <button class="btn btn-sm btn-primary" 
                        onclick="editarUsuario(${usuario.id})"
                        title="Editar">
                    <i class="fas fa-edit"></i>
                </button>
                ${!usuario.empresa_nombre ? `
                    <button class="btn btn-sm btn-info" 
                            onclick="asignarEmpresa(${usuario.id})"
                            title="Asignar Empresa">
                        <i class="fas fa-building"></i>
                    </button>
                ` : ''}
                <button class="btn btn-sm btn-danger" 
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
    modalElement.style.display = 'block';
    modalElement.classList.add('show');
}

// Cerrar modal
function cerrarModal() {
    modalElement.style.display = 'none';
    modalElement.classList.remove('show');
}

// Crear nuevo usuario
async function crearUsuario() {
    const form = document.getElementById('formNuevoUsuario');
    if (!form.checkValidity()) {
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
            mostrarAlerta(result.error || 'Error al crear usuario', 'danger');
        }
    } catch (error) {
        console.error('Error:', error);
        mostrarAlerta('Error al crear usuario', 'danger');
    }
}

// Activar/Desactivar usuario
async function toggleUsuario(id, estadoActual) {
    if (!confirm(`¿Deseas ${estadoActual ? 'desactivar' : 'activar'} este usuario?`)) {
        return;
    }

    try {
        const response = await fetch(`/api/admin/usuarios/${id}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ activo: !estadoActual })
        });

        if (response.ok) {
            mostrarAlerta('Usuario actualizado', 'success');
            cargarUsuarios();
        } else {
            mostrarAlerta('Error al actualizar usuario', 'danger');
        }
    } catch (error) {
        console.error('Error:', error);
        mostrarAlerta('Error al actualizar usuario', 'danger');
    }
}

// Mostrar alerta
function mostrarAlerta(mensaje, tipo) {
    const container = document.getElementById('alertContainer');
    const alert = document.createElement('div');
    alert.className = `alert alert-${tipo}`;
    alert.innerHTML = `
        ${mensaje}
        <button type="button" class="btn-close" onclick="this.parentElement.remove()"></button>
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
    alert('Función de edición en desarrollo');
}

// Placeholder para asignar empresa
function asignarEmpresa(id) {
    alert('Función de asignación de empresa en desarrollo');
}
