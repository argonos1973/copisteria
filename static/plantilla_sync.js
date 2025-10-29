/**
 * Sistema de sincronización de plantillas en tiempo real
 * Detecta cambios de plantilla y recarga estilos automáticamente
 */

(function() {
    'use strict';
    
    let ultimaPlantilla = null;
    let checkInterval = null;
    
    // Verificar cambios cada 2 segundos
    const CHECK_INTERVAL = 2000;
    
    async function obtenerPlantillaActiva() {
        try {
            // Obtener colores de la empresa del usuario actual (requiere sesión)
            const coloresResponse = await fetch('/api/auth/branding');
            if (!coloresResponse.ok) return null;
            
            const data = await coloresResponse.json();
            return data.colores;
            
        } catch (error) {
            console.error('[PLANTILLA-SYNC] Error obteniendo plantilla:', error);
            return null;
        }
    }
    
    function compararPlantillas(plantilla1, plantilla2) {
        if (!plantilla1 || !plantilla2) return false;
        
        // Comparar propiedades clave
        const keys = ['primario', 'secundario', 'button', 'app_bg', 'header_text'];
        
        return keys.every(key => plantilla1[key] === plantilla2[key]);
    }
    
    async function verificarCambios() {
        const plantillaActual = await obtenerPlantillaActiva();
        
        if (!plantillaActual) return;
        
        // Primera vez
        if (!ultimaPlantilla) {
            ultimaPlantilla = plantillaActual;
            return;
        }
        
        // Comparar con la anterior
        if (!compararPlantillas(ultimaPlantilla, plantillaActual)) {
            console.log('[PLANTILLA-SYNC] 🎨 Cambio de plantilla detectado');
            console.log('[PLANTILLA-SYNC] Anterior:', ultimaPlantilla);
            console.log('[PLANTILLA-SYNC] Nueva:', plantillaActual);
            
            ultimaPlantilla = plantillaActual;
            
            // Recargar estilos
            await recargarEstilos();
            
            // Notificar a otras ventanas/iframes
            notificarCambio();
        }
    }
    
    async function recargarEstilos() {
        console.log('[PLANTILLA-SYNC] ♻️ Recargando estilos...');
        
        // Si existe la función de auto_branding, ejecutarla
        if (window.cargarColoresEmpresa) {
            await window.cargarColoresEmpresa();
            console.log('[PLANTILLA-SYNC] ✅ Estilos recargados');
        }
        
        // Forzar recarga eliminando estilos inline problemáticos
        forzarActualizacionEstilosInline();
        
        // Si estamos en un iframe, recargar el iframe principal también
        if (window.parent !== window) {
            window.parent.postMessage({
                type: 'plantilla-changed',
                timestamp: Date.now()
            }, window.location.origin);
        }
    }
    
    function forzarActualizacionEstilosInline() {
        // Eliminar estilos inline de color y background en elementos comunes
        const selectores = [
            'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
            '.stats-value', '.stats-label',
            '.modal-content', '.modal h2',
            'tbody tr td', 'thead'
        ];
        
        selectores.forEach(selector => {
            document.querySelectorAll(selector).forEach(el => {
                // Solo remover estilos inline de color si existen
                if (el.style.color) {
                    el.style.removeProperty('color');
                }
                if (el.style.background || el.style.backgroundColor) {
                    el.style.removeProperty('background');
                    el.style.removeProperty('background-color');
                }
            });
        });
        
        console.log('[PLANTILLA-SYNC] 🧹 Estilos inline problemáticos eliminados');
    }
    
    function notificarCambio() {
        // Enviar mensaje a otros iframes
        window.postMessage({
            type: 'plantilla-changed',
            timestamp: Date.now()
        }, window.location.origin);
        
        // Si hay un iframe content-frame, notificarlo
        const iframe = document.getElementById('content-frame');
        if (iframe && iframe.contentWindow) {
            try {
                iframe.contentWindow.postMessage({
                    type: 'plantilla-changed',
                    timestamp: Date.now()
                }, window.location.origin);
            } catch (e) {
                // Ignorar errores de cross-origin
            }
        }
    }
    
    // Escuchar mensajes de cambio de plantilla
    window.addEventListener('message', async (event) => {
        if (event.origin !== window.location.origin) return;
        
        if (event.data.type === 'plantilla-changed') {
            console.log('[PLANTILLA-SYNC] 📩 Mensaje de cambio recibido');
            
            // Esperar un poco para que la BD se actualice
            setTimeout(async () => {
                const plantillaActual = await obtenerPlantillaActiva();
                if (plantillaActual) {
                    ultimaPlantilla = plantillaActual;
                    await recargarEstilos();
                }
            }, 500);
        }
    });
    
    // Iniciar verificación periódica
    function iniciar() {
        console.log('[PLANTILLA-SYNC] 🚀 Sistema de sincronización iniciado');
        
        // Primera verificación inmediata
        verificarCambios();
        
        // Verificación periódica
        if (checkInterval) {
            clearInterval(checkInterval);
        }
        
        checkInterval = setInterval(verificarCambios, CHECK_INTERVAL);
    }
    
    // Detener verificación
    function detener() {
        if (checkInterval) {
            clearInterval(checkInterval);
            checkInterval = null;
            console.log('[PLANTILLA-SYNC] ⏸️ Sistema de sincronización detenido');
        }
    }
    
    // Auto-iniciar cuando el DOM esté listo
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', iniciar);
    } else {
        iniciar();
    }
    
    // Limpiar al salir
    window.addEventListener('beforeunload', detener);
    
    // Exportar funciones
    window.PlantillaSync = {
        iniciar,
        detener,
        verificarCambios,
        recargarEstilos
    };
    
})();
