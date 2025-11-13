// app_init.js - Inicialización de la aplicación

// Inicializar cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', async () => {
    console.log('[INIT] Iniciando aplicación...');
    
    // Cargar menú según permisos
    if (window.verificarSesionYCargarMenu) {
        await verificarSesionYCargarMenu();
    } else {
        console.error('[INIT] verificarSesionYCargarMenu no está definida');
    }
    
    // Cargar notificaciones
    if (window.cargarNotificaciones) {
        cargarNotificaciones();
    }
});

// Función para cerrar sesión
async function cerrarSesion() {
    try {
        await fetch('/api/auth/logout', { method: 'POST' });
        window.location.href = '/LOGIN.html';
    } catch (error) {
        console.error('Error cerrando sesión:', error);
        window.location.href = '/LOGIN.html';
    }
}
