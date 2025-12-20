// perfil_modal.js - Gestión del modal de perfil de usuario

let datosUsuarioActual = {};
let twoFactorEnabled = false;

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
        
        // Cargar estado 2FA
        await cargar2FAStatus();
        
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

function cambiarTab(tab, tabButtonEl) {
    // Desactivar todos los tabs
    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));

    // Activar tab seleccionado
    const btn = tabButtonEl || event?.currentTarget || event?.target?.closest?.('.tab-btn');
    if (btn) {
        btn.classList.add('active');
    }

    const tabContent = document.getElementById(`tab-${tab}`);
    if (tabContent) {
        tabContent.classList.add('active');
    }
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

        const getTextOnBg = (bgColor) => {
            const parseRgb = (c) => {
                if (!c || typeof c !== 'string') return null;
                const s = c.trim();

                if (s.startsWith('#')) {
                    const hex = s.replace('#', '');
                    if (hex.length !== 6) return null;
                    return {
                        r: parseInt(hex.substring(0, 2), 16),
                        g: parseInt(hex.substring(2, 4), 16),
                        b: parseInt(hex.substring(4, 6), 16)
                    };
                }

                if (s.startsWith('rgb')) {
                    const m = s.match(/\d+/g);
                    if (!m || m.length < 3) return null;
                    return { r: parseInt(m[0]), g: parseInt(m[1]), b: parseInt(m[2]) };
                }

                return null;
            };

            const relativeLuminance = ({ r, g, b }) => {
                const srgb = [r, g, b]
                    .map(v => v / 255)
                    .map(v => (v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4)));
                return 0.2126 * srgb[0] + 0.7152 * srgb[1] + 0.0722 * srgb[2];
            };

            const contrastRatio = (fgRgb, bgRgb) => {
                const l1 = relativeLuminance(fgRgb);
                const l2 = relativeLuminance(bgRgb);
                return (Math.max(l1, l2) + 0.05) / (Math.min(l1, l2) + 0.05);
            };

            const bg = parseRgb(bgColor);
            if (!bg) return '#ffffff';

            const white = { r: 255, g: 255, b: 255 };
            const black = { r: 0, g: 0, b: 0 };
            const cw = contrastRatio(white, bg);
            const cb = contrastRatio(black, bg);

            return cb >= cw ? '#000000' : '#ffffff';
        };

        const cssEscapeAttr = (v) => String(v).replace(/\\/g, '\\\\').replace(/"/g, '\\"');

        let cssRules = '';
        
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
            let bg, surface, text, border, primary, menuBg, buttonBg;
            
            if (p.semantic && p.palette) {
                // Estructura nueva
                bg = resolveColor(p.semantic.bg, p) || '#ffffff';
                surface = resolveColor(p.semantic['bg-elevated'], p) || bg;
                text = resolveColor(p.semantic.text, p) || '#333333';
                border = resolveColor(p.semantic.border, p) || '#dddddd';
                primary = resolveColor(p.semantic.primary, p) || '#007bff';

                // Colores de componentes (si existen) para diferenciar previews
                menuBg = resolveColor(p.components?.menu?.bg, p) || primary;
                buttonBg = resolveColor(p.components?.button?.bg, p) || primary;
            } else {
                // Fallback estructura antigua o colores directos
                const colores = p.colores || {};
                bg = colores.background || '#ffffff';
                surface = colores.surface || bg;
                text = colores.text || '#333333';
                border = colores.border || '#dddddd';
                primary = colores.primary || '#007bff';

                menuBg = colores.menu || primary;
                buttonBg = colores.button || primary;
            }
            
            // Variables CSS por tarjeta (evita hardcode y permite que el CSS dibuje una mini-preview)
            const buttonText = getTextOnBg(buttonBg);
            const menuText = getTextOnBg(menuBg);
            const estilosCard = `--pv-bg: ${bg}; --pv-surface: ${surface}; --pv-border: ${border}; --pv-primary: ${primary}; --pv-text: ${text}; --pv-menu: ${menuBg}; --pv-menu-text: ${menuText}; --pv-button: ${buttonBg}; --pv-button-text: ${buttonText};`;

            cssRules += `\n.plantilla-card-perfil[data-plantilla="${cssEscapeAttr(p.id)}"]{${estilosCard}}`;
            
            // Si está activa, sobreescribimos el border-color (excepto el top) mediante clase CSS, 
            // pero aquí definimos la base.
            
            return `
                <div class="plantilla-card-perfil ${isActive ? 'active' : ''}" 
                     data-plantilla="${p.id}"
                     onclick="cambiarPlantillaUsuario('${p.id}', this)">
                    <div class="plantilla-mini-ui" aria-hidden="true">
                        <div class="plantilla-mini-header"></div>
                        <div class="plantilla-mini-body">
                            <div class="plantilla-mini-line"></div>
                            <div class="plantilla-mini-line"></div>
                            <div class="plantilla-mini-chip"></div>
                        </div>
                    </div>
                    <div class="plantilla-preview-colors">
                        <span class="preview-dot preview-menu"></span>
                        <span class="preview-dot preview-primary"></span>
                        <span class="preview-dot preview-surface"></span>
                        <span class="preview-dot preview-bg"></span>
                        <span class="preview-dot preview-text"></span>
                    </div>
                    <div class="plantilla-icon">${p.icono}</div>
                    <div class="plantilla-nombre plantilla-nombre-badge">${p.nombre}</div>
                    <div class="plantilla-check"><i class="fas fa-check-circle"></i></div>
                </div>
            `;
        }).join('');

        const styleId = 'plantillas-preview-style';
        let styleEl = document.getElementById(styleId);
        if (!styleEl) {
            styleEl = document.createElement('style');
            styleEl.id = styleId;
            document.head.appendChild(styleEl);
        }
        styleEl.textContent = cssRules;
        
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
    const modal2fa = document.getElementById('modal-2fa-qr');
    if (event.target === modal) {
        cerrarModalPerfil();
    }
    if (event.target === modalSelector) {
        cerrarSelectorAvatares();
    }
    if (event.target === modal2fa) {
        cerrarModal2FA();
    }
}

// ============================================================================
// FUNCIONES 2FA
// ============================================================================

async function cargar2FAStatus() {
    const container = document.getElementById('2fa-status-container');
    if (!container) return;
    
    try {
        const response = await fetch('/api/auth/2fa/status');
        const data = await response.json();
        
        twoFactorEnabled = data.enabled;
        
        if (twoFactorEnabled) {
            container.innerHTML = `
                <div style="text-align: center; padding: 20px;">
                    <div style="width: 80px; height: 80px; background: linear-gradient(135deg, #28a745, #20c997); border-radius: 50%; margin: 0 auto 15px; display: flex; align-items: center; justify-content: center;">
                        <i class="fas fa-shield-alt" style="font-size: 36px; color: white;"></i>
                    </div>
                    <h3 style="color: #28a745; margin: 0 0 10px 0;"><i class="fas fa-check-circle"></i> 2FA Activado</h3>
                    <p style="color: var(--color-texto-secundario, #666); margin-bottom: 20px; font-size: 13px;">
                        Tu cuenta está protegida con autenticación de doble factor.
                    </p>
                    <button onclick="mostrarDesactivar2FA()" class="btn-guardar" style="background: #dc3545;">
                        <i class="fas fa-times-circle"></i> Desactivar 2FA
                    </button>
                </div>
            `;
        } else {
            container.innerHTML = `
                <div style="text-align: center; padding: 20px;">
                    <div style="width: 80px; height: 80px; background: linear-gradient(135deg, #6c757d, #adb5bd); border-radius: 50%; margin: 0 auto 15px; display: flex; align-items: center; justify-content: center;">
                        <i class="fas fa-shield-alt" style="font-size: 36px; color: white;"></i>
                    </div>
                    <h3 style="color: var(--color-texto, #333); margin: 0 0 10px 0;">2FA Desactivado</h3>
                    <p style="color: var(--color-texto-secundario, #666); margin-bottom: 20px; font-size: 13px;">
                        Activa la autenticación de doble factor para mayor seguridad.
                    </p>
                    <button onclick="iniciarSetup2FA()" class="btn-guardar btn-force-blue">
                        <i class="fas fa-shield-alt"></i> Activar 2FA
                    </button>
                </div>
            `;
        }
    } catch (error) {
        console.error('Error cargando estado 2FA:', error);
        container.innerHTML = `
            <div style="text-align: center; padding: 20px; color: #dc3545;">
                <i class="fas fa-exclamation-triangle"></i> Error cargando estado de 2FA
            </div>
        `;
    }
}

async function iniciarSetup2FA() {
    const modal = document.getElementById('modal-2fa-qr');
    const content = document.getElementById('2fa-qr-content');
    
    modal.style.display = 'flex';
    content.innerHTML = `
        <div style="padding: 20px;">
            <i class="fas fa-spinner fa-spin fa-2x" style="color: var(--color-primario, #007bff);"></i>
            <p style="margin-top: 10px;">Generando código QR...</p>
        </div>
    `;
    
    try {
        const response = await fetch('/api/auth/2fa/setup', { method: 'POST' });
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Error al configurar 2FA');
        }
        
        content.innerHTML = `
            <p style="margin-bottom: 15px; font-size: 13px; color: var(--color-texto-secundario, #666);">
                Escanea este código QR con Google Authenticator o Authy:
            </p>
            <div style="background: white; padding: 15px; border-radius: 8px; display: inline-block; margin-bottom: 15px;">
                <img src="${data.qr_code}" alt="QR Code" style="max-width: 180px;">
            </div>
            <p style="font-size: 11px; color: var(--color-texto-secundario, #888); margin-bottom: 10px;">
                O introduce este código manualmente:
            </p>
            <code style="display: block; background: var(--bg-elevated, #f5f5f5); padding: 10px; border-radius: 6px; font-size: 12px; letter-spacing: 2px; margin-bottom: 20px; word-break: break-all;">${data.secret}</code>
            <div style="margin-bottom: 15px;">
                <label style="display: block; margin-bottom: 8px; font-size: 13px; color: var(--color-texto, #333);">
                    Introduce el código de 6 dígitos:
                </label>
                <input type="text" id="verify-2fa-code" maxlength="6" placeholder="000000" 
                       style="width: 150px; padding: 12px; font-size: 20px; text-align: center; letter-spacing: 8px; border: 2px solid var(--color-border, #ddd); border-radius: 8px; font-family: monospace;"
                       onkeypress="if(event.key==='Enter')verificar2FA()">
            </div>
            <div style="display: flex; gap: 10px; justify-content: center;">
                <button onclick="cerrarModal2FA()" class="btn-guardar" style="background: #6c757d;">Cancelar</button>
                <button onclick="verificar2FA()" class="btn-guardar btn-force-blue">Verificar y Activar</button>
            </div>
        `;
        
        document.getElementById('verify-2fa-code').focus();
        
    } catch (error) {
        content.innerHTML = `
            <div style="color: #dc3545; padding: 20px;">
                <i class="fas fa-exclamation-triangle fa-2x"></i>
                <p style="margin-top: 10px;">${error.message}</p>
                <button onclick="cerrarModal2FA()" class="btn-guardar" style="margin-top: 15px; background: #6c757d;">Cerrar</button>
            </div>
        `;
    }
}

async function verificar2FA() {
    const code = document.getElementById('verify-2fa-code').value.trim();
    
    if (!code || code.length !== 6) {
        mostrarNotificacion('Introduce un código de 6 dígitos', 'error');
        return;
    }
    
    try {
        const response = await fetch('/api/auth/2fa/verify', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ code })
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Código incorrecto');
        }
        
        const content = document.getElementById('2fa-qr-content');
        content.innerHTML = `
            <div style="padding: 20px;">
                <div style="width: 60px; height: 60px; background: #28a745; border-radius: 50%; margin: 0 auto 15px; display: flex; align-items: center; justify-content: center;">
                    <i class="fas fa-check" style="font-size: 30px; color: white;"></i>
                </div>
                <h3 style="color: #28a745; margin: 0 0 10px 0;">¡2FA Activado!</h3>
                <p style="color: var(--color-texto-secundario, #666); font-size: 13px;">
                    Tu cuenta ahora está protegida con autenticación de doble factor.
                </p>
                <button onclick="cerrarModal2FA(); cargar2FAStatus();" class="btn-guardar btn-force-blue" style="margin-top: 15px;">Entendido</button>
            </div>
        `;
        
    } catch (error) {
        mostrarNotificacion(error.message, 'error');
        document.getElementById('verify-2fa-code').value = '';
        document.getElementById('verify-2fa-code').focus();
    }
}

function mostrarDesactivar2FA() {
    const modal = document.getElementById('modal-2fa-qr');
    const content = document.getElementById('2fa-qr-content');
    
    modal.style.display = 'flex';
    content.innerHTML = `
        <div style="padding: 10px;">
            <div style="width: 60px; height: 60px; background: #dc3545; border-radius: 50%; margin: 0 auto 15px; display: flex; align-items: center; justify-content: center;">
                <i class="fas fa-exclamation-triangle" style="font-size: 28px; color: white;"></i>
            </div>
            <h3 style="color: #dc3545; margin: 0 0 10px 0;">Desactivar 2FA</h3>
            <p style="color: var(--color-texto-secundario, #666); font-size: 13px; margin-bottom: 20px;">
                Esto reducirá la seguridad de tu cuenta. ¿Estás seguro?
            </p>
            <div style="margin-bottom: 15px; text-align: left;">
                <label style="display: block; margin-bottom: 8px; font-size: 13px;">Introduce tu contraseña:</label>
                <input type="password" id="disable-2fa-password" placeholder="Tu contraseña actual"
                       style="width: 100%; padding: 10px; border: 1px solid var(--color-border, #ddd); border-radius: 6px; box-sizing: border-box;"
                       onkeypress="if(event.key==='Enter')desactivar2FA()">
            </div>
            <div style="display: flex; gap: 10px; justify-content: center;">
                <button onclick="cerrarModal2FA()" class="btn-guardar" style="background: #6c757d;">Cancelar</button>
                <button onclick="desactivar2FA()" class="btn-guardar" style="background: #dc3545;">Desactivar</button>
            </div>
        </div>
    `;
    
    document.getElementById('disable-2fa-password').focus();
}

async function desactivar2FA() {
    const password = document.getElementById('disable-2fa-password').value;
    
    if (!password) {
        mostrarNotificacion('Introduce tu contraseña', 'error');
        return;
    }
    
    try {
        const response = await fetch('/api/auth/2fa/disable', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ password })
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Error al desactivar 2FA');
        }
        
        mostrarNotificacion('2FA desactivado correctamente', 'success');
        cerrarModal2FA();
        cargar2FAStatus();
        
    } catch (error) {
        mostrarNotificacion(error.message, 'error');
    }
}

function cerrarModal2FA() {
    const modal = document.getElementById('modal-2fa-qr');
    if (modal) {
        modal.style.display = 'none';
    }
}
