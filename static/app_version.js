// app_version.js - Carga y muestra la versión de la aplicación

window.addEventListener('DOMContentLoaded', async () => {
    try {
        const response = await fetch('/api/version');
        const data = await response.json();
        const versionElement = document.getElementById('app-version');
        if (versionElement && data.version) {
            versionElement.textContent = `v${data.version}`;
        }
    } catch (error) {
        console.error('[MENU] Error cargando versión:', error);
    }
});
