// perfil.js - Gestión de perfil de usuario

// Cargar información del perfil
async function cargarPerfil() {
    try {
        const response = await fetch('/api/auth/session');
        if (!response.ok) throw new Error('Error al cargar perfil');
        
        const data = await response.json();
        
        let empresaInfo = data.empresa || 'Sin Empresa';
        if (empresaInfo === 'Sin Empresa') {
            empresaInfo = '<span class="badge-warning">Sin empresa asignada</span>';
        }
        
        // Actualizar avatar
        const avatarElement = document.getElementById('avatarImage');
        if (data.avatar) {
            avatarElement.innerHTML = `<img src="${data.avatar}" alt="Avatar">`;
        } else {
            avatarElement.innerHTML = '<i class="fas fa-user"></i>';
        }
        
        document.getElementById('profileInfo').innerHTML = `
            <div class="info-row">
                <div class="info-label">Nombre Completo:</div>
                <div class="info-value">${data.usuario || 'No disponible'}</div>
            </div>
            <div class="info-row">
                <div class="info-label">Usuario:</div>
                <div class="info-value">${data.username || 'No disponible'}</div>
            </div>
            <div class="info-row">
                <div class="info-label">Empresa:</div>
                <div class="info-value">${empresaInfo}</div>
            </div>
            <div class="info-row">
                <div class="info-label">Rol:</div>
                <div class="info-value">${data.rol || 'usuario'}</div>
            </div>
            <div class="info-row">
                <div class="info-label">Estado:</div>
                <div class="info-value">Activo</div>
            </div>
            ${empresaInfo.includes('Sin empresa') ? `
            <div class="alert-info">
                <i class="fas fa-info-circle"></i>
                <div>
                    <strong>Cuenta limitada:</strong> No tienes una empresa asignada. Puedes solicitar acceso a una empresa desde el menú de Gestión.
                </div>
            </div>
            ` : ''}
        `;
    } catch (error) {
        console.error('Error:', error);
        document.getElementById('profileInfo').innerHTML = `
            <div class="alert-danger">
                <i class="fas fa-exclamation-triangle"></i>
                Error al cargar la información del perfil
            </div>
        `;
    }
}

// Subir avatar
async function subirAvatar(event) {
    const file = event.target.files[0];
    if (!file) return;
    
    // Validar tipo de archivo
    if (!file.type.startsWith('image/')) {
        alert('Por favor selecciona una imagen válida');
        return;
    }
    
    // Validar tamaño (máximo 2MB)
    if (file.size > 2 * 1024 * 1024) {
        alert('La imagen no debe superar los 2MB');
        return;
    }
    
    const formData = new FormData();
    formData.append('avatar', file);
    
    try {
        const response = await fetch('/api/auth/upload-avatar', {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) throw new Error('Error al subir avatar');
        
        const data = await response.json();
        
        // Actualizar avatar en la página
        document.getElementById('avatarImage').innerHTML = `<img src="${data.avatar_url}" alt="Avatar">`;
        
        alert('Avatar actualizado correctamente');
    } catch (error) {
        console.error('Error:', error);
        alert('Error al subir el avatar. Por favor, intenta de nuevo.');
    }
}

// Inicializar al cargar la página
document.addEventListener('DOMContentLoaded', cargarPerfil);
