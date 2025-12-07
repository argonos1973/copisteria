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
        
        // Llenar información en pestaña de contraseña
        const passwordInfoUsername = document.getElementById('password-info-username');
        if (passwordInfoUsername) {
            passwordInfoUsername.textContent = data.username || '-';
        }
        
        // Mostrar contraseña actual con puntos (placeholder visual)
        const passwordActualInput = document.getElementById('password-actual');
        if (passwordActualInput) {
            passwordActualInput.placeholder = '••••••••';
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
            mostrarNotificacion('El archivo es demasiado grande. Máximo 2MB', 'error');
            event.target.value = '';
            return;
        }
        
        // Validar tipo
        if (!file.type.startsWith('image/')) {
            mostrarNotificacion('Solo se permiten imágenes', 'error');
            event.target.value = '';
            return;
        }
        
        const reader = new FileReader();
        reader.onload = function(e) {
            preview.src = e.target.result;
            avatarSeleccionado = null; // Limpiar selección predefinida
        };
        reader.readAsDataURL(file);
        cerrarSelectorAvatares();
    }
}

async function guardarDatos(event) {
    event.preventDefault();
    
    try {
        // Usar FormData para enviar archivos
        const formData = new FormData();
        formData.append('email', document.getElementById('perfil-email').value);
        
        // Agregar avatar predefinido si se seleccionó uno
        if (avatarSeleccionado) {
            formData.append('avatar_predefinido', avatarSeleccionado);
        }
        
        // Agregar avatar personalizado si se subió uno
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
            mostrarNotificacion('Datos actualizados correctamente', 'success');
            
            // Refrescar avatar en el menú lateral
            if (result.avatar) {
                const menuAvatar = document.getElementById('menu-usuario-avatar');
                if (menuAvatar) {
                    menuAvatar.src = result.avatar + '?t=' + new Date().getTime();
                }
            }
            
            // Limpiar selección de avatar
            avatarSeleccionado = null;
            const avatarInput = document.getElementById('perfil-avatar-input');
            if (avatarInput) {
                avatarInput.value = '';
            }
            
            // Cerrar modal después de guardar
            setTimeout(() => {
                cerrarModalPerfil();
            }, 800);
        } else {
            mostrarNotificacion('Error: ' + (result.error || 'No se pudieron actualizar los datos'), 'error');
        }
    } catch (error) {
        console.error('Error:', error);
        mostrarNotificacion('Error al guardar datos', 'error');
    }
}

async function cambiarPassword(event) {
    event.preventDefault();
    
    const passwordActual = document.getElementById('password-actual').value;
    const passwordNueva = document.getElementById('password-nueva').value;
    const passwordConfirmar = document.getElementById('password-confirmar').value;
    
    if (passwordNueva !== passwordConfirmar) {
        mostrarNotificacion('Las contraseñas no coinciden', 'error');
        return;
    }
    
    if (passwordNueva.length < 6) {
        mostrarNotificacion('La contraseña debe tener al menos 6 caracteres', 'error');
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
        
        // Función helper para resolver colores
        const resolveColor = (val, theme) => {
            console.log('Resolviendo color:', val, theme); // Añadir log de consola
            if (!val) return null;
            if (val.startsWith('#') || val.startsWith('rgb') || val.startsWith('hsl')) return val;
            const m = val.match(/\{([^}]+)\}/);
            if (m) {
                const path = m[1].split('.');
                let curr = theme;
                for (const k of path) curr = curr?.[k];
                return resolveColor(curr, theme);
            }
            return val;
        };

        grid.innerHTML = plantillas.map(p => {
            const isActive = p.id === plantillaActual;
            
            // Extraer colores reales usando la estructura semántica
            let bg, text, border, primary;
            
            if (p.semantic && p.palette) {
                // Estructura nueva
                bg = resolveColor(p.semantic['bg-elevated'] || p.semantic.bg, p) || '#ffffff';
                text = resolveColor(p.semantic.text, p) || '#333333';
                border = resolveColor(p.semantic.border, p) || '#dddddd';
                primary = resolveColor(p.semantic.primary, p) || '#007bff';
            } else {
                // Fallback estructura antigua o colores directos
                const colores = p.colores || {};
                bg = colores.background || '#ffffff';
                text = colores.text || '#333333';
                border = colores.border || '#dddddd';
                primary = colores.primary || '#007bff';
            }
            
            // Estilos de la tarjeta: SIEMPRE usar los colores de la plantilla
            // El estado active se indicará por clase CSS (borde/sombra) no cambiando el inline style del fondo
            // Añadimos border-top con el color primario para distinguir temas claros
            const estilosCard = `background: ${bg}; border: 1px solid ${border}; border-top: 5px solid ${primary}; color: ${text};`;
            
            // Si está activa, sobreescribimos el border-color (excepto el top) mediante clase CSS, 
            // pero aquí definimos la base.
            
            // Puntos de previsualización
            const dot1 = primary;
            const dot2 = bg;
            const dot3 = text;
            
            return `
                <div class="plantilla-card-perfil ${isActive ? 'active' : ''}" 
                     data-plantilla="${p.id}"
                     style="${estilosCard}"
                     onclick="cambiarPlantillaUsuario('${p.id}', this)">
                    <div class="plantilla-preview-colors">
                        <span class="preview-dot" style="background: ${dot1}"></span>
                        <span class="preview-dot" style="background: ${dot2}; border: 1px solid ${border}"></span>
                        <span class="preview-dot" style="background: ${dot3}"></span>
                    </div>
                    <div class="plantilla-icon" style="color: ${primary}">${p.icono}</div>
                    <div class="plantilla-nombre" style="color: #ffffff; background: rgba(0,0,0,0.7); padding: 3px 8px; border-radius: 12px; font-size: 11px; margin-top: 5px; text-shadow: 0 1px 2px rgba(0,0,0,0.8); display: inline-block;">${p.nombre}</div>
                    <div class="plantilla-check" style="color: ${primary}"><i class="fas fa-check-circle"></i></div>
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
            
            // Limpiar caché para forzar recarga de la nueva configuración
            if (window.limpiarCacheBranding) {
                window.limpiarCacheBranding();
            }
            
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

// Selector de avatares
let avatarSeleccionado = null;

async function abrirSelectorAvatares() {
    const modal = document.getElementById('modal-selector-avatares');
    modal.style.display = 'block';
    await cargarAvataresPredefinidos();
    mostrarAvataresPredefinidos();
}

function cerrarSelectorAvatares() {
    document.getElementById('modal-selector-avatares').style.display = 'none';
}

async function cargarAvataresPredefinidos() {
    try {
        const response = await fetch('/api/avatares/listar');
        const avatares = await response.json();
        
        const container = document.getElementById('avatares-predefinidos');
        container.innerHTML = '';
        
        if (avatares.length === 0) {
            container.innerHTML = '<p style="text-align: center; color: var(--color-texto-secundario, #666); padding: 20px;">No hay avatares predefinidos disponibles</p>';
            return;
        }
        
        avatares.forEach(avatar => {
            const div = document.createElement('div');
            div.style.cssText = 'cursor: pointer; text-align: center; transition: transform 0.2s;';
            div.onmouseover = function() { this.style.transform = 'scale(1.05)'; };
            div.onmouseout = function() { this.style.transform = 'scale(1)'; };
            div.onclick = function() { seleccionarAvatarPredefinido(avatar); };
            
            div.innerHTML = `
                <img src="/static/avatares/${avatar}" alt="${avatar}" 
                     style="width: 100px; height: 100px; border-radius: 50%; object-fit: cover; border: 3px solid var(--color-border, #ddd);">
                <p style="margin: 5px 0 0 0; font-size: 11px; color: var(--color-texto-secundario, #666); overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${avatar}</p>
            `;
            
            container.appendChild(div);
        });
    } catch (error) {
        console.error('Error cargando avatares:', error);
        document.getElementById('avatares-predefinidos').innerHTML = '<p style="text-align: center; color: #e74c3c; padding: 20px;">Error cargando avatares</p>';
    }
}

function seleccionarAvatarPredefinido(avatar) {
    avatarSeleccionado = avatar;
    const preview = document.getElementById('perfil-avatar-preview');
    preview.src = `/static/avatares/${avatar}?t=${new Date().getTime()}`;
    cerrarSelectorAvatares();
}

function mostrarAvataresPredefinidos() {
    document.getElementById('avatares-predefinidos').style.display = 'grid';
    document.getElementById('subir-personalizado').style.display = 'none';
    document.getElementById('btn-predefinidos').classList.add('active');
    document.getElementById('btn-personalizado').classList.remove('active');
}

function mostrarSubirPersonalizado() {
    document.getElementById('avatares-predefinidos').style.display = 'none';
    document.getElementById('subir-personalizado').style.display = 'block';
    document.getElementById('btn-predefinidos').classList.remove('active');
    document.getElementById('btn-personalizado').classList.add('active');
}

// Agregar evento al user-profile-link después de que el DOM esté listo
document.addEventListener('DOMContentLoaded', () => {
    const userProfileLink = document.getElementById('user-profile-link');
    if (userProfileLink) {
        userProfileLink.addEventListener('click', abrirModalPerfil);
    }
});

// Cerrar modal al hacer click fuera
window.onclick = function(event) {
    const modal = document.getElementById('modal-perfil');
    const modalSelector = document.getElementById('modal-selector-avatares');
    if (event.target === modal) {
        cerrarModalPerfil();
    }
    if (event.target === modalSelector) {
        cerrarSelectorAvatares();
    }
}
