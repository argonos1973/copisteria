// perfil_modal.js - Gestión del modal de perfil de usuario

let datosUsuarioActual = {};

async function abrirModalPerfil() {
    try {
        // Cargar datos del usuario
        const response = await fetch('/api/auth/session');
        const data = await response.json();
        
        datosUsuarioActual = data;
        
        // Llenar formulario de datos
        document.getElementById('perfil-username').value = data.username || '';
        document.getElementById('perfil-email').value = data.email || '';
        document.getElementById('perfil-telefono').value = data.telefono || '';
        
        // Llenar información en pestaña de contraseña
        const passwordInfoUsername = document.getElementById('password-info-username');
        if (passwordInfoUsername) {
            passwordInfoUsername.textContent = data.username || '-';
        }
        
        // Cargar avatar si existe
        const avatarPreview = document.getElementById('perfil-avatar-preview');
        if (data.avatar) {
            const timestamp = new Date().getTime();
            avatarPreview.src = data.avatar + '?t=' + timestamp;
        } else {
            avatarPreview.src = '/static/avatars/default.svg';
        }
        
        // Cargar plantillas disponibles
        await cargarPlantillasModal();
        
        // Mostrar modal
        document.getElementById('modal-perfil').style.display = 'block';
    } catch (error) {
        console.error('Error cargando perfil:', error);
        alert('Error al cargar datos del perfil');
    }
}

function togglePasswordVisibility(inputId, iconElement) {
    const input = document.getElementById(inputId);
    if (input.type === 'password') {
        input.type = 'text';
        iconElement.classList.remove('fa-eye');
        iconElement.classList.add('fa-eye-slash');
    } else {
        input.type = 'password';
        iconElement.classList.remove('fa-eye-slash');
        iconElement.classList.add('fa-eye');
    }
}

async function cargarDatosPerfil() {
    try {
        const response = await fetch('/api/auth/session');
        const data = await response.json();
        
        // Actualizar avatar
        const avatarPreview = document.getElementById('perfil-avatar-preview');
        if (data.avatar) {
            const timestamp = new Date().getTime();
            avatarPreview.src = data.avatar + '?t=' + timestamp;
        }
    } catch (error) {
        console.error('Error recargando perfil:', error);
    }
}

function cerrarModalPerfil() {
    document.getElementById('modal-perfil').style.display = 'none';
    // Limpiar contraseñas
    document.getElementById('form-password').reset();
}

function cambiarTab(tab) {
    // Desactivar todos los tabs
    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
    
    // Activar tab seleccionado
    event.target.classList.add('active');
    document.getElementById(`tab-${tab}`).classList.add('active');
}

function previsualizarAvatar(event) {
    const file = event.target.files[0];
    const preview = document.getElementById('perfil-avatar-preview');
    
    if (file) {
        // Validar tamaño (2MB máximo)
        if (file.size > 2 * 1024 * 1024) {
            alert('❌ El archivo es demasiado grande. Máximo 2MB');
            event.target.value = '';
            return;
        }
        
        // Validar tipo
        if (!file.type.startsWith('image/')) {
            alert('❌ Solo se permiten imágenes');
            event.target.value = '';
            return;
        }
        
        const reader = new FileReader();
        reader.onload = function(e) {
            preview.src = e.target.result;
        };
        reader.readAsDataURL(file);
    }
}

async function guardarDatos(event) {
    event.preventDefault();
    
    try {
        // Usar FormData para enviar archivos
        const formData = new FormData();
        formData.append('email', document.getElementById('perfil-email').value);
        formData.append('telefono', document.getElementById('perfil-telefono').value);
        
        // Agregar avatar si se seleccionó uno
        const avatarInput = document.getElementById('perfil-avatar-input');
        if (avatarInput && avatarInput.files && avatarInput.files[0]) {
            formData.append('avatar', avatarInput.files[0]);
        }
        
        const response = await fetch('/api/usuario/perfil', {
            method: 'PUT',
            body: formData
            // No incluir Content-Type, el navegador lo establece automáticamente con boundary
        });
        
        const result = await response.json();
        
        if (response.ok) {
            alert('✅ Datos actualizados correctamente');
            // Recargar datos del perfil para mostrar avatar actualizado
            setTimeout(() => {
                cargarDatosPerfil();
            }, 500);
        } else {
            alert('❌ Error: ' + (result.error || 'No se pudieron actualizar los datos'));
        }
    } catch (error) {
        console.error('Error:', error);
        alert('❌ Error al guardar datos');
    }
}

async function cambiarPassword(event) {
    event.preventDefault();
    
    const passwordActual = document.getElementById('password-actual').value;
    const passwordNueva = document.getElementById('password-nueva').value;
    const passwordConfirmar = document.getElementById('password-confirmar').value;
    
    if (passwordNueva !== passwordConfirmar) {
        alert('❌ Las contraseñas no coinciden');
        return;
    }
    
    if (passwordNueva.length < 6) {
        alert('❌ La contraseña debe tener al menos 6 caracteres');
        return;
    }
    
    try {
        const response = await fetch('/api/auth/cambiar-password', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                password_actual: passwordActual,
                password_nueva: passwordNueva
            })
        });
        
        const result = await response.json();
        
        if (response.ok) {
            mostrarNotificacion('Contraseña cambiada correctamente', 'success');
            document.getElementById('form-password').reset();
        } else {
            mostrarNotificacion('Error: ' + (result.error || 'No se pudo cambiar la contraseña'), 'error');
        }
    } catch (error) {
        console.error('Error:', error);
        mostrarNotificacion('Error al cambiar contraseña', 'error');
    }
}

async function cargarPlantillasModal() {
    try {
        // Obtener plantilla actual del usuario
        const brandingResponse = await fetch('/api/auth/branding');
        const branding = await brandingResponse.json();
        const plantillaActual = branding.plantilla || 'dark';
        
        // Obtener plantillas disponibles desde el backend (dinámico)
        const plantillasResponse = await fetch('/api/usuario/plantillas');
        const plantillasData = await plantillasResponse.json();
        
        if (!plantillasData.success || !plantillasData.plantillas) {
            console.error('Error obteniendo plantillas:', plantillasData.error);
            mostrarNotificacion('Error cargando plantillas', 'error');
            return;
        }
        
        const plantillas = plantillasData.plantillas;
        
        const grid = document.getElementById('plantillas-grid');
        grid.innerHTML = plantillas.map(p => {
            const isActive = p.id === plantillaActual;
            const colores = p.colores || {};
            
            // Si está activa, usar el gradiente azul, si no, usar los colores del tema
            const estilosCard = isActive ? 
                `background: linear-gradient(135deg, var(--primary, #3498db) 0%, var(--primary-dark, #2980b9) 100%); border-color: var(--primary, #3498db);` :
                `background: ${colores.background || '#fff'}; border-color: ${colores.border || '#ddd'};`;
            
            const estilosTexto = isActive ?
                `color: white !important;` :
                `color: ${colores.text || '#333'};`;
            
            return `
                <div class="plantilla-card-perfil ${isActive ? 'active' : ''}" 
                     data-plantilla="${p.id}"
                     style="${estilosCard}"
                     onclick="cambiarPlantillaUsuario('${p.id}', this)">
                    <div class="plantilla-preview-colors">
                        <span class="preview-dot" style="background: ${colores.primary || '#3498db'}"></span>
                        <span class="preview-dot" style="background: ${colores.background || '#fff'}"></span>
                        <span class="preview-dot" style="background: ${colores.text || '#000'}"></span>
                    </div>
                    <div class="plantilla-icon" style="${estilosTexto}">${p.icono}</div>
                    <div class="plantilla-nombre" style="${estilosTexto}">${p.nombre}</div>
                    <div class="plantilla-check"><i class="fas fa-check-circle"></i></div>
                </div>
            `;
        }).join('');
        
        console.log(`✅ ${plantillas.length} plantillas cargadas dinámicamente`);
    } catch (error) {
        console.error('Error cargando plantillas:', error);
        mostrarNotificacion('Error cargando plantillas', 'error');
    }
}

async function cambiarPlantillaUsuario(plantilla, clickedElement) {
    try {
        // Actualizar UI inmediatamente para mostrar feedback visual
        document.querySelectorAll('.plantilla-card-perfil').forEach(card => {
            card.classList.remove('active');
        });
        
        // Marcar la plantilla seleccionada como activa
        if (clickedElement) {
            clickedElement.classList.add('active');
        } else {
            const card = document.querySelector(`.plantilla-card-perfil[data-plantilla="${plantilla}"]`);
            if (card) card.classList.add('active');
        }
        
        const response = await fetch('/api/usuario/plantilla', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ plantilla: plantilla })
        });
        
        const result = await response.json();
        
        if (response.ok && result.colores) {
            // Aplicar tema inmediatamente
            if (typeof applyTheme === 'function') {
                await applyTheme(result.colores);
                console.log(`✅ Plantilla "${plantilla}" aplicada al documento`);
            } else {
                console.error('❌ Función applyTheme no disponible');
            }
            
            mostrarNotificacion('Plantilla cambiada correctamente', 'success');
            
            // Recargar la modal para aplicar el nuevo tema
            await cargarPlantillasModal();
            
            // Recargar página para aplicar cambios completos después de un breve delay
            setTimeout(() => {
                console.log('🔄 Recargando página para aplicar cambios completos...');
                location.reload();
            }, 1500);
        } else {
            // Si hay error, restaurar el estado activo anterior
            await cargarPlantillasModal();
            mostrarNotificacion('Error: ' + (result.error || 'No se pudo cambiar la plantilla'), 'error');
        }
    } catch (error) {
        console.error('Error:', error);
        // Si hay error, restaurar el estado
        await cargarPlantillasModal();
        mostrarNotificacion('Error al cambiar plantilla', 'error');
    }
}

// Cerrar modal al hacer click fuera
window.onclick = function(event) {
    const modal = document.getElementById('modal-perfil');
    if (event.target === modal) {
        cerrarModalPerfil();
    }
}
