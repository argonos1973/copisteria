/**
 * Session Manager para manejar autenticación con Cloudflare
 * Usa localStorage como alternativa a cookies cuando hay problemas con proxy
 */

class SessionManager {
    constructor() {
        this.storageKey = 'aleph70_session';
        this.sessionData = null;
        this.initializeSession();
    }

    initializeSession() {
        // Intentar recuperar sesión de localStorage
        const stored = localStorage.getItem(this.storageKey);
        if (stored) {
            try {
                this.sessionData = JSON.parse(stored);
                // Verificar que no haya expirado
                if (this.sessionData.expiry && new Date(this.sessionData.expiry) > new Date()) {
                    this.injectSessionHeader();
                } else {
                    this.clearSession();
                }
            } catch (e) {
                this.clearSession();
            }
        }
    }

    async login(username, password, empresa) {
        try {
            const response = await fetch('/api/auth/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                credentials: 'include',
                body: JSON.stringify({ username, password, empresa })
            });

            const data = await response.json();
            
            // Si requiere 2FA, devolver los datos para que el frontend muestre el modal
            if (data.requires_2fa) {
                console.log('🔐 Se requiere 2FA');
                return { success: false, data, requires_2fa: true };
            }
            
            if (data.success) {
                // Guardar sesión en localStorage con expiración
                const sessionInfo = {
                    ...data,
                    timestamp: new Date().toISOString(),
                    expiry: new Date(Date.now() + 8 * 60 * 60 * 1000).toISOString() // 8 horas
                };
                
                localStorage.setItem(this.storageKey, JSON.stringify(sessionInfo));
                this.sessionData = sessionInfo;
                this.injectSessionHeader();
                
                console.log('✅ Sesión guardada en localStorage');
                return { success: true, data };
            }
            
            return { success: false, error: data.error || 'Login failed' };
            
        } catch (error) {
            console.error('Error en login:', error);
            return { success: false, error: error.message };
        }
    }

    getSession() {
        return this.sessionData;
    }

    clearSession() {
        localStorage.removeItem(this.storageKey);
        // Limpiar caché de menú también para evitar leaks de permisos entre usuarios
        sessionStorage.removeItem('menu_data');
        this.sessionData = null;
    }

    isAuthenticated() {
        return this.sessionData !== null;
    }

    // Inyectar datos de sesión en todas las peticiones fetch
    injectSessionHeader() {
        const originalFetch = window.fetch;
        const sessionData = this.sessionData;
        
        window.fetch = function(...args) {
            let [url, config] = args;
            
            // Convertir URL object a string si es necesario
            let urlString = url;
            if (url && typeof url === 'object' && url.href) {
                urlString = url.href;
            } else if (url && typeof url === 'object' && url.toString) {
                urlString = url.toString();
            }
            
            // Solo para peticiones a la API
            if (urlString && typeof urlString === 'string' && urlString.includes('/api/')) {
                config = config || {};
                config.credentials = 'include';
                
                // Agregar header con información de sesión si existe
                if (sessionData) {
                    config.headers = config.headers || {};
                    // Enviar datos de sesión como header personalizado
                    config.headers['X-Session-Data'] = JSON.stringify({
                        username: sessionData.username || sessionData.usuario,
                        empresa: sessionData.empresa_codigo || sessionData.empresa || 'copisteria',
                        rol: sessionData.rol || 'usuario'
                    });
                }
            }
            
            return originalFetch.apply(this, [url, config]);
        };
    }

    // Método para verificar sesión con el servidor
    async verifySession() {
        try {
            const response = await fetch('/api/auth/session', {
                credentials: 'include'
            });
            
            // Leer texto primero para evitar SyntaxError si devuelve HTML
            const text = await response.text();
            
            if (response.ok) {
                try {
                    const data = JSON.parse(text);
                    if (data.username) {
                        // Sesión válida, actualizar localStorage
                        const sessionInfo = {
                            ...data,
                            timestamp: new Date().toISOString(),
                            expiry: new Date(Date.now() + 8 * 60 * 60 * 1000).toISOString()
                        };
                        localStorage.setItem(this.storageKey, JSON.stringify(sessionInfo));
                        this.sessionData = sessionInfo;
                        return true;
                    }
                } catch (e) {
                    console.error('Error parseando JSON de sesión. Respuesta recibida:', text.substring(0, 100) + '...');
                }
            } else {
                console.warn('Error en verifySession. Status:', response.status, 'Response:', text.substring(0, 100));
            }
            
            // Si no hay sesión válida en el servidor, limpiar localStorage
            this.clearSession();
            return false;
            
        } catch (error) {
            console.error('Error verificando sesión:', error);
            return false;
        }
    }
}

// Crear instancia global
window.sessionManager = new SessionManager();

// Auto-verificar sesión al cargar
document.addEventListener('DOMContentLoaded', async () => {
    if (window.sessionManager.isAuthenticated()) {
        console.log('🔍 Verificando sesión con servidor...');
        const valid = await window.sessionManager.verifySession();
        if (valid) {
            console.log('✅ Sesión válida');
        } else {
            console.log('❌ Sesión expirada o inválida');
            // Redirigir a login si es necesario
            if (!window.location.pathname.includes('LOGIN') && !window.location.pathname.includes('DEBUG')) {
                window.location.href = '/LOGIN.html';
            }
        }
    }
});

console.log('📦 SessionManager cargado - usa window.sessionManager');
