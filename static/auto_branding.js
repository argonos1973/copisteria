(async function() {
    try {
        console.log('[AUTO-BRANDING v6.0] Iniciando (carga directa desde .json)...');
        
        // Esperar a que branding.js esté disponible
        let intentos = 0;
        while (typeof applyTheme !== 'function' && intentos < 50) {
            await new Promise(resolve => setTimeout(resolve, 100));
            intentos++;
        }
        
        if (typeof applyTheme !== 'function') {
            console.warn('[AUTO-BRANDING] ⚠️ branding.js no disponible (esto es normal en páginas sin tema)');
            return;
        }
        
        console.log('[AUTO-BRANDING] branding.js cargado');
        
        if (window.self !== window.top) {
            console.log('[AUTO-BRANDING] En iframe, omitiendo');
            return;
        }
        
        // Obtener plantilla de localStorage o usar 'classic' por defecto
        // NO se consulta base de datos, carga directa desde .json
        let plantillaNombre = localStorage.getItem('plantillaSeleccionada') || 'classic';
        console.log('[AUTO-BRANDING] Plantilla seleccionada:', plantillaNombre);
        
        // Cargar directamente el archivo .json
        const plantillaResponse = await fetch(`/static/plantillas/${plantillaNombre}.json`, {
            cache: 'no-cache'
        });
        
        if (!plantillaResponse.ok) {
            console.error('[AUTO-BRANDING] Error cargando JSON, usando classic por defecto');
            plantillaNombre = 'classic';
            const fallbackResponse = await fetch('/static/plantillas/classic.json', {
                cache: 'no-cache'
            });
            
            if (!fallbackResponse.ok) {
                console.error('[AUTO-BRANDING] No se pudo cargar classic.json');
                return;
            }
            
            const themeJson = await fallbackResponse.json();
            await applyTheme(themeJson);
            console.log('[AUTO-BRANDING] Tema aplicado (fallback):', themeJson.name);
            return;
        }
        
        const themeJson = await plantillaResponse.json();
        console.log('[AUTO-BRANDING] JSON cargado:', themeJson.name, 'v' + themeJson.version);
        
        await applyTheme(themeJson);
        console.log('[AUTO-BRANDING] ✅ Tema aplicado correctamente');
        
        // Guardar en localStorage para persistencia
        localStorage.setItem('plantillaSeleccionada', plantillaNombre);
        
    } catch (error) {
        console.error('[AUTO-BRANDING] Error:', error);
    }
})();
