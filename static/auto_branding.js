(async function() {
    try {
        console.log('[AUTO-BRANDING v5.1] Iniciando...');
        
        let intentos = 0;
        while (typeof applyTheme !== 'function' && intentos < 50) {
            await new Promise(resolve => setTimeout(resolve, 100));
            intentos++;
        }
        
        if (typeof applyTheme !== 'function') {
            console.error('[AUTO-BRANDING] branding.js no disponible');
            return;
        }
        
        console.log('[AUTO-BRANDING] branding.js cargado');
        
        if (window.self !== window.top) {
            console.log('[AUTO-BRANDING] En iframe');
            return;
        }
        
        const response = await fetch('/api/auth/branding', {
            credentials: 'include',
            cache: 'no-cache'
        });
        
        if (!response.ok) {
            console.warn('[AUTO-BRANDING] Error cargando branding');
            return;
        }
        
        const branding = await response.json();
        console.log('[AUTO-BRANDING] Plantilla:', branding.plantilla);
        
        if (!branding.plantilla) {
            console.warn('[AUTO-BRANDING] Sin plantilla');
            return;
        }
        
        const plantillaResponse = await fetch('/static/plantillas/' + branding.plantilla + '.json', {
            cache: 'no-cache'
        });
        
        if (!plantillaResponse.ok) {
            console.error('[AUTO-BRANDING] Error cargando JSON');
            return;
        }
        
        const themeJson = await plantillaResponse.json();
        console.log('[AUTO-BRANDING] JSON cargado:', themeJson.name);
        
        await applyTheme(themeJson);
        console.log('[AUTO-BRANDING] Tema aplicado');
        
    } catch (error) {
        console.error('[AUTO-BRANDING] Error:', error);
    }
})();
