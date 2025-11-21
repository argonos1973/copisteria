/**
 * Debug wrapper para producción/desarrollo
 * Incluir este archivo ANTES que cualquier otro script
 */

(function() {
    'use strict';
    
    // Detectar si estamos en desarrollo
    const isDevelopment = window.location.hostname === 'localhost' || 
                         window.location.hostname === '127.0.0.1' ||
                         window.location.hostname.includes('dev') ||
                         localStorage.getItem('debug') === 'true';
    
    // Guardar referencias originales
    const originalConsole = {
        log: console.log,
        debug: console.debug,
        info: console.info,
        warn: console.warn,
        error: console.error,
        trace: console.trace
    };
    
    // Si no estamos en desarrollo, silenciar console (excepto errors)
    if (!isDevelopment) {
        console.log = function() {};
        console.debug = function() {};
        console.info = function() {};
        console.trace = function() {};
        // Mantener warn y error para problemas críticos
        // console.warn = function() {};
        // console.error = function() {};
    // }
    // 
    // Función global para activar/desactivar debug
    // window.enableDebug = function(enable = true) {
        // localStorage.setItem('debug', enable ? 'true' : 'false');
        if (enable) {
            console.log = originalConsole.log;
            console.debug = originalConsole.debug;
            console.info = originalConsole.info;
            console.trace = originalConsole.trace;
            // console.log('🐛 Modo debug activado');
        } else {
            location.reload(); // Recargar para aplicar cambios
        }
    };
    
    // Función para logs críticos que siempre deben verse
    window.logCritical = function(...args) {
        originalConsole.error('[CRITICAL]', ...args);
    };
    
    // Información del entorno
    if (isDevelopment) {
        originalConsole.log('🔧 Modo desarrollo activo');
    } else {
        originalConsole.log('🚀 Modo producción - Logs desactivados (usar enableDebug() para activar)');
    }
})();
