// perfil.js - Gestión de perfil de usuario

let twoFactorEnabled = false;

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
        
        // Cargar estado 2FA
        await cargar2FAStatus();
        
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
            
            <!-- Sección 2FA -->
            <div class="section-divider"></div>
            <h3 class="section-title"><i class="fas fa-shield-alt"></i> Seguridad</h3>
            <div class="info-row">
                <div class="info-label">Autenticación 2FA:</div>
                <div class="info-value" id="2fa-status">
                    ${twoFactorEnabled 
                        ? '<span class="badge-success"><i class="fas fa-check-circle"></i> Activada</span>' 
                        : '<span class="badge-warning"><i class="fas fa-exclamation-circle"></i> Desactivada</span>'}
                </div>
            </div>
            <div class="action-buttons">
                ${twoFactorEnabled 
                    ? '<button class="btn btn-danger" onclick="mostrarDesactivar2FA()"><i class="fas fa-shield-alt"></i> Desactivar 2FA</button>'
                    : '<button class="btn btn-primary" onclick="iniciarSetup2FA()"><i class="fas fa-shield-alt"></i> Activar 2FA</button>'}
            </div>
            
            <!-- Modal Setup 2FA -->
            <div id="modal-2fa-setup" class="modal-overlay" style="display: none;">
                <div class="modal-content-2fa">
                    <div class="modal-header-2fa">
                        <h3><i class="fas fa-shield-alt"></i> Configurar Autenticación 2FA</h3>
                        <button class="modal-close" onclick="cerrarModal2FA()">&times;</button>
                    </div>
                    <div class="modal-body-2fa" id="modal-2fa-body">
                        <div class="loading">
                            <i class="fas fa-spinner fa-spin fa-2x"></i>
                            <p>Generando código QR...</p>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Modal Desactivar 2FA -->
            <div id="modal-2fa-disable" class="modal-overlay" style="display: none;">
                <div class="modal-content-2fa">
                    <div class="modal-header-2fa modal-header-danger">
                        <h3><i class="fas fa-exclamation-triangle"></i> Desactivar 2FA</h3>
                        <button class="modal-close" onclick="cerrarModalDesactivar2FA()">&times;</button>
                    </div>
                    <div class="modal-body-2fa">
                        <p class="warning-text">¿Estás seguro de que deseas desactivar la autenticación de doble factor?</p>
                        <p>Esto reducirá la seguridad de tu cuenta.</p>
                        <div class="form-group">
                            <label>Introduce tu contraseña para confirmar:</label>
                            <input type="password" id="disable-2fa-password" class="form-input" placeholder="Tu contraseña actual">
                        </div>
                        <div class="modal-actions">
                            <button class="btn btn-secondary" onclick="cerrarModalDesactivar2FA()">Cancelar</button>
                            <button class="btn btn-danger" onclick="desactivar2FA()">Desactivar 2FA</button>
                        </div>
                    </div>
                </div>
            </div>
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

// Cargar estado de 2FA
async function cargar2FAStatus() {
    try {
        const response = await fetch('/api/auth/2fa/status');
        if (response.ok) {
            const data = await response.json();
            twoFactorEnabled = data.enabled;
        }
    } catch (error) {
        console.error('Error cargando estado 2FA:', error);
    }
}

// Iniciar setup de 2FA
async function iniciarSetup2FA() {
    document.getElementById('modal-2fa-setup').style.display = 'flex';
    
    try {
        const response = await fetch('/api/auth/2fa/setup', { method: 'POST' });
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Error al configurar 2FA');
        }
        
        document.getElementById('modal-2fa-body').innerHTML = `
            <div class="setup-2fa-content">
                <p><strong>Paso 1:</strong> Escanea este código QR con tu app de autenticación (Google Authenticator, Authy, etc.)</p>
                <div class="qr-container">
                    <img src="${data.qr_code}" alt="Código QR 2FA" class="qr-image">
                </div>
                <p class="manual-entry">¿No puedes escanear? Introduce este código manualmente:</p>
                <code class="secret-code">${data.secret}</code>
                <div class="setup-step-2">
                    <p><strong>Paso 2:</strong> Introduce el código de 6 dígitos que muestra tu app:</p>
                    <div class="code-input-container">
                        <input type="text" id="verify-2fa-code" class="code-input" maxlength="6" placeholder="000000" autocomplete="off">
                    </div>
                    <div class="modal-actions">
                        <button class="btn btn-secondary" onclick="cerrarModal2FA()">Cancelar</button>
                        <button class="btn btn-primary" onclick="verificar2FA()">Verificar y Activar</button>
                    </div>
                </div>
            </div>
        `;
        
        // Focus en el input
        document.getElementById('verify-2fa-code').focus();
        
    } catch (error) {
        document.getElementById('modal-2fa-body').innerHTML = `
            <div class="alert-danger">
                <i class="fas fa-exclamation-triangle"></i>
                ${error.message}
            </div>
            <div class="modal-actions">
                <button class="btn btn-secondary" onclick="cerrarModal2FA()">Cerrar</button>
            </div>
        `;
    }
}

// Verificar código 2FA durante setup
async function verificar2FA() {
    const code = document.getElementById('verify-2fa-code').value.trim();
    
    if (!code || code.length !== 6) {
        alert('Por favor introduce un código de 6 dígitos');
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
            throw new Error(data.error || 'Error al verificar código');
        }
        
        document.getElementById('modal-2fa-body').innerHTML = `
            <div class="success-message">
                <i class="fas fa-check-circle fa-3x"></i>
                <h3>¡2FA Activado!</h3>
                <p>La autenticación de doble factor está ahora activa en tu cuenta.</p>
                <p>A partir de ahora, necesitarás tu app de autenticación para iniciar sesión.</p>
            </div>
            <div class="modal-actions">
                <button class="btn btn-primary" onclick="cerrarModal2FA(); cargarPerfil();">Entendido</button>
            </div>
        `;
        
    } catch (error) {
        alert(error.message);
    }
}

// Mostrar modal de desactivar 2FA
function mostrarDesactivar2FA() {
    document.getElementById('modal-2fa-disable').style.display = 'flex';
    document.getElementById('disable-2fa-password').value = '';
    document.getElementById('disable-2fa-password').focus();
}

// Desactivar 2FA
async function desactivar2FA() {
    const password = document.getElementById('disable-2fa-password').value;
    
    if (!password) {
        alert('Por favor introduce tu contraseña');
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
        
        alert('2FA desactivado correctamente');
        cerrarModalDesactivar2FA();
        cargarPerfil();
        
    } catch (error) {
        alert(error.message);
    }
}

// Cerrar modales
function cerrarModal2FA() {
    document.getElementById('modal-2fa-setup').style.display = 'none';
}

function cerrarModalDesactivar2FA() {
    document.getElementById('modal-2fa-disable').style.display = 'none';
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
