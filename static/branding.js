// Gestión de branding y colores de la empresa
// Extraído de _app_private.html para mejor mantenibilidad

// Función para calcular luminosidad y determinar color de texto
function getTextColorForBackground(bgColor) {
    let r, g, b;
    
    if (bgColor.startsWith('#')) {
        const hex = bgColor.replace('#', '');
        r = parseInt(hex.substring(0, 2), 16);
        g = parseInt(hex.substring(2, 4), 16);
        b = parseInt(hex.substring(4, 6), 16);
    } else if (bgColor.startsWith('rgb')) {
        const match = bgColor.match(/\d+/g);
        r = parseInt(match[0]);
        g = parseInt(match[1]);
        b = parseInt(match[2]);
    } else {
        return '#000000';
    }
    
    const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
    return luminance > 0.5 ? '#000000' : '#ffffff';
}

// Aplicar tema con design tokens (formato nuevo)
async function applyTheme(themeJson) {
    console.log('[BRANDING] 🎨 Aplicando tema:', themeJson.name);
    
    // 1) Resolver referencias simples {semantic.x}/{palette.x}
    const flat = JSON.parse(JSON.stringify(themeJson));
    const get = (path) => path.split('.').reduce((o, k) => o?.[k], flat);
    const resolveValue = (v) => {
        const m = /^\{(.+)\}$/.exec(v || "");
        return m ? resolveValue(get(m[1])) : v;
    };
    
    const vars = {};
    const walk = (obj, prefix = []) => {
        for (const [k, v] of Object.entries(obj)) {
            if (typeof v === 'object' && v) {
                walk(v, [...prefix, k]);
            } else if (typeof v === 'string') {
                const cssKey = ([...prefix, k]).join('-')
                    .replace(/^(palette|semantic|components)-/, '')
                    .replaceAll('_', '-');
                vars[cssKey] = resolveValue(v);
            }
        }
    };
    walk({ semantic: flat.semantic, components: flat.components });
    
    // 2) Construir CSS - Inyectar en :root global para que theme-consumer.css pueda usarlas
    const toVar = (k) => '--' + k.replace(/[^a-z0-9\-]/gi, '').toLowerCase();
    let css = `:root {`;
    let varCount = 0;
    for (const [k, v] of Object.entries(vars)) {
        css += `${toVar(k)}:${v};`;
        varCount++;
    }
    console.log(`[BRANDING] 📊 Variables CSS generadas: ${varCount}`);
    
    // 2.1) Añadir aliases para compatibilidad con variables antiguas
    css += `
        --color-app-bg: var(--bg);
        --color-primario: var(--primary);
        --color-secundario: var(--secondary);
        --color-texto: var(--text);
        --color-texto-secundario: var(--text-muted);
        --color-fondo: var(--bg);
        --color-header-bg: var(--header-bg);
        --color-header-text: var(--header-text);
        --color-button: var(--button-bg);
        --color-button-text: var(--button-text);
        --color-button-hover: var(--button-hover-bg);
        --color-boton-hover: var(--button-hover-bg);
        --color-boton-active: var(--button-active-bg);
        --color-input-bg: var(--input-bg);
        --color-input-text: var(--input-text);
        --color-input-border: var(--input-border);
        --color-grid-header: var(--table-header-bg);
        --color-grid-header-text: var(--table-header-text);
        --color-grid-bg: var(--table-bg);
        --color-grid-text: var(--table-text);
        --color-menu-bg: var(--menu-bg);
        --color-menu-text: var(--menu-text);
        --color-menu-hover: var(--menu-hover);
        --color-grid-hover: var(--table-row-hover);
        --color-verde: var(--success);
        --color-rojo: var(--danger);
        --color-hover: var(--hover);
        --color-shadow: var(--shadow);
        --color-borde: var(--border);
    `;
    
    css += '}';
    
    // 3) Inyectar
    let el = document.getElementById('theme-style');
    if (!el) {
        el = document.createElement('style');
        el.id = 'theme-style';
        document.head.appendChild(el);
    }
    el.textContent = css;
    
    // 4) Activar
    document.documentElement.dataset.theme = themeJson.name;
    
    // 5) Persistencia
    localStorage.setItem('aleph70_theme', JSON.stringify(themeJson));
    localStorage.setItem('aleph70_theme_name', themeJson.name);
    
    console.log('[BRANDING] ✅ Tema aplicado:', themeJson.name);
    console.log('[BRANDING] 📊 Variables CSS generadas:', Object.keys(vars).length);
    
    // Forzar reflow para que los estilos se apliquen inmediatamente
    void document.documentElement.offsetHeight;
    
    // Aplicar también a los iframes si existen
    const iframes = document.querySelectorAll('iframe');
    iframes.forEach(iframe => {
        try {
            const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
            if (iframeDoc) {
                Object.entries(vars).forEach(([key, value]) => {
                    iframeDoc.documentElement.style.setProperty(toVar(key), value);
                });
                console.log('[BRANDING] ✓ Inyectando variables CSS en iframe...');
            }
        } catch (e) {
            console.log('[BRANDING] ⚠️ No se pudo acceder al iframe:', e.message);
        }
    });
    
    console.log('[BRANDING] ✅ Variables CSS aplicadas al iframe');
    
    // Forzar repaint de elementos que usan las variables
    requestAnimationFrame(() => {
        // Forzar actualización de botones que usan --primary
        document.querySelectorAll('.btn-icon').forEach(el => {
            const currentColor = getComputedStyle(el).color;
            el.style.color = '';  // Limpiar estilo inline
            void el.offsetHeight; // Forzar reflow
        });
        
        document.querySelectorAll('.btn-descargar, .header-icons button').forEach(el => {
            el.style.display = el.style.display || 'inline-block';
        });
        
        console.log('[BRANDING] 🔄 Reflow forzado para actualizar estilos (.btn-icon incluido)');
    });
    
    // 6) Aplicar también al iframe si existe
    aplicarTemaAlIframe(css);
}

// Aplicar el mismo tema al iframe
function aplicarTemaAlIframe(css) {
    const iframe = document.getElementById('content-frame');
    if (!iframe) {
        return;
    }
    
    try {
        const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
        if (iframeDoc) {
            console.log('[BRANDING] ✓ Inyectando variables CSS en iframe...');
            
            // Inyectar el mismo <style> con variables CSS dentro del iframe
            let iframeStyleElement = iframeDoc.getElementById('theme-style');
            if (!iframeStyleElement) {
                iframeStyleElement = iframeDoc.createElement('style');
                iframeStyleElement.id = 'theme-style';
                iframeDoc.head.appendChild(iframeStyleElement);
            }
            iframeStyleElement.textContent = css;
            
            console.log('[BRANDING] ✅ Variables CSS aplicadas al iframe');
        }
    } catch (e) {
        console.log('[BRANDING] ⚠️ No se pudo acceder al iframe:', e.message);
    }
}

// Aplicar colores directamente desde JSON (usado por editor)
async function aplicarColoresDirectos(plantillaData, plantillaNombre) {
    console.log('[BRANDING] 🎨 Aplicando colores directos desde editor');
    console.log('[BRANDING] Plantilla:', plantillaNombre);
    
    // SOLO FORMATO NUEVO (design tokens)
    if (!plantillaData.version || !plantillaData.palette || !plantillaData.semantic) {
        console.error('[BRANDING] ❌ Formato de plantilla inválido. Se requiere formato nuevo con design tokens.');
        return;
    }
    
    // USAR SISTEMA NUEVO (design tokens)
    console.log('[BRANDING] 🎯 Usando sistema de design tokens...');
    await applyTheme(plantillaData);
    
    console.log('[BRANDING] ✅ Tema aplicado con design tokens');
}

// Cargar colores de la empresa
async function cargarColoresEmpresa() {
    try {
        console.log('[BRANDING] Cargando colores...');
        const response = await fetch('/api/auth/branding');
        
        if (!response.ok) {
            console.error('[BRANDING] ❌ No se pudo obtener branding');
            return;
        }
        
        const branding = await response.json();
        console.log('[BRANDING] Datos recibidos:', branding);
        
        // Actualizar logo inmediatamente antes de cargar plantilla
        const logoEmpresa = document.getElementById('logo-empresa');
        if (logoEmpresa && branding.logo_header) {
            // Construir URL completa del logo
            const logoUrl = branding.logo_header.startsWith('/') 
                ? branding.logo_header 
                : `/static/logos/${branding.logo_header}`;
            logoEmpresa.src = logoUrl;
            logoEmpresa.style.display = 'block';
            logoEmpresa.onerror = function() {
                console.error('[BRANDING] ❌ Error cargando logo:', logoUrl);
                this.src = '/static/logos/default_header.png';
            };
            logoEmpresa.onload = function() {
                console.log('[BRANDING] ✅ Logo cargado exitosamente:', logoUrl);
            };
            console.log('[BRANDING] 🖼️ Logo configurado a:', logoUrl);
        } else {
            console.warn('[BRANDING] ⚠️ Logo no disponible en branding:', branding);
        }
        
        if (!branding || !branding.plantilla) {
            console.error('[BRANDING] ❌ Datos de branding incompletos');
            return;
        }
        
        console.log('[BRANDING] 📄 Cargando plantilla:', branding.plantilla);
        const plantillaResponse = await fetch(`/static/plantillas/${branding.plantilla}.json`, {
            cache: 'no-cache'
        });
        
        if (!plantillaResponse.ok) {
            console.error('[BRANDING] ❌ No se pudo cargar JSON:', branding.plantilla);
            return;
        }
        
        const themeJson = await plantillaResponse.json();
        console.log('[BRANDING] ✅ JSON cargado:', themeJson.name);
        
        // 3. Aplicar tema con sistema nuevo (design tokens)
        await applyTheme(themeJson);
        return; // Evitar ejecutar flujo legacy basado en colores sueltos
        // DESACTIVADO: Override de tema oscuro para usuario específico
        // Ahora se respeta la plantilla configurada en la empresa
        // let username = null;
        // try {
        //     const s = await fetch('/api/auth/session', { credentials: 'include', cache: 'no-cache' });
        //     if (s.ok) {
        //         const js = await s.json();
        //         username = js?.username || js?.user || null;
        //     }
        // } catch (_) {}

        let coloresAplicar = { ...branding.colores };
        
        // DEBUG: Verificar colores recibidos
        console.log('[BRANDING] ========== DEBUG ==========');
        console.log('[BRANDING] submenu_bg:', coloresAplicar.submenu_bg);
        console.log('[BRANDING] submenu_text:', coloresAplicar.submenu_text);
        console.log('[BRANDING] app_bg:', coloresAplicar.app_bg);
        console.log('[BRANDING] primario:', coloresAplicar.primario);
        console.log('[BRANDING] ==========================');
        
        // if (String(username).toLowerCase() === 'sami') {
        //     console.log('[BRANDING] Aplicando plantilla oscura basada en colores de empresa para usuario sami');
        //     coloresAplicar = {
        //         ...coloresAplicar,
        //         // Mantener corporativos
        //         primario: coloresAplicar.primario,
        //         secundario: coloresAplicar.secundario,
        //         button: coloresAplicar.button,
        //         button_hover: coloresAplicar.button_hover || coloresAplicar.button,
        //         // Oscurecer fondos y textos para modo dark
        //         app_bg: '#121212',
        //         header_bg: '#1f1f1f',
        //         header_text: '#e6e6e6',
        //         grid_bg: '#1b1b1b',
        //         grid_text: '#e0e0e0',
        //         grid_header: coloresAplicar.grid_header || coloresAplicar.primario,
        //         grid_hover: 'rgba(255,255,255,0.06)',
        //         input_bg: '#2a2a2a',
        //         input_text: '#e0e0e0',
        //         input_border: '#4a4a4a',
        //         select_bg: '#2a2a2a',
        //         select_text: '#e0e0e0',
        //         select_border: '#4a4a4a',
        //         modal_bg: '#1e1e1e',
        //         modal_text: '#f0f0f0',
        //         modal_border: '#ffffff',
        //         modal_shadow: 'rgba(0,0,0,0.6)'
        //     };
        // }

        aplicarColores(coloresAplicar);
        
    } catch (error) {
        console.error("[BRANDING] Error cargando colores:", error);
    }
}

// Variable global para guardar colores y reutilizarlos
// Evitar re-declaración si el script se carga múltiples veces
if (typeof window.coloresEmpresa === 'undefined') {
    window.coloresEmpresa = null;
}

// Aplicar colores al DOM
function aplicarColores(colores) {
    // Guardar colores globalmente para aplicarlos al iframe después
    window.coloresEmpresa = colores;
    
    // USAR SOLO VALORES DIRECTOS DEL JSON - SIN CALCULOS
    const textForBody = colores.grid_text;
    const textForCards = colores.grid_text;
    
    // Color de texto para botones: SOLO el definido en plantilla
    const textForButton = colores.button_text;
    const textForButtonHover = colores.button_text;
    
    console.log('[BRANDING] Color botón:', colores.button, '→ Texto:', textForButton, '(definido en plantilla)');
    
    // CSS dinámico - ELIMINAR el anterior y crear uno nuevo AL FINAL del head
    let oldStyleElement = document.getElementById('dynamic-branding-styles');
    if (oldStyleElement) {
        oldStyleElement.remove();
    }
    
    const styleElement = document.createElement('style');
    styleElement.id = 'dynamic-branding-styles';
    styleElement.setAttribute('data-priority', 'highest');
    // Añadir AL FINAL del head para máxima prioridad
    document.head.appendChild(styleElement);
    
    // Guardar colores globalmente para re-aplicar al iframe después
    window.__COLORES_EMPRESA__ = colores;
    
    console.log('========================================');
    console.log('🎨 APLICANDO COLORES DE PLANTILLA');
    console.log('========================================');
    console.log('Color primario (menú lateral):', colores.primario);
    console.log('Color header (panel contenido):', colores.header_bg);
    console.log('Color botón:', colores.button, '→ Texto calculado:', textForButton);
    console.log('========================================');
    
    styleElement.textContent = `
        /* Variables CSS */
        :root {
            --color-primario: ${colores.primario} !important;
            --color-secundario: ${colores.secundario} !important;
            --color-app-bg: ${colores.app_bg} !important;
            --color-header-bg: ${colores.header_bg} !important;
            --color-header-text: ${colores.header_text} !important;
            --color-button: ${colores.button} !important;
            --color-button-text: ${textForButton} !important;
        }
        
        /* Fondo y texto */
        body {
            background-color: ${colores.app_bg || '#ffffff'} !important;
            color: ${textForBody} !important;
        }
        
        /* HEADER - Encabezados de páginas */
        .header,
        div.header,
        .page-header {
            background-color: ${colores.header_bg || colores.secundario} \!important;
            color: ${colores.header_text || '#ffffff'} \!important;
        }
        
        .header h1, .header h2, .header h3, .header *,
        div.header h1, div.header * {
            color: ${colores.header_text || '#ffffff'} \!important;
        }
        
        /* TABS - Pestañas de navegación */
        .tabs, div.tabs {
            background-color: ${colores.secundario || colores.header_bg} \!important;
        }
        
        .tab, button.tab {
            background-color: transparent \!important;
            color: ${colores.header_text || colores.grid_text} \!important;
        }
        
        .tab:hover, button.tab:hover {
            background-color: ${colores.submenu_hover || 'rgba(255,255,255,0.1)'} \!important;
        }
        
        .tab.active, button.tab.active {
            background-color: ${colores.primario || colores.button} \!important;
            color: ${textForButton} \!important;
        }
        
        /* MENÚ LATERAL - USA COLOR SUBMENU */
        html body .layout-container nav.menu,
        html body .layout-container .menu,
        html body nav.menu,
        html body .sidebar, 
        html body .menu,
        .layout-container .menu,
        nav.menu,
        .sidebar,
        .menu {
            background-color: ${colores.submenu_bg || colores.primario || '#ffffff'} !important;
            background: ${colores.submenu_bg || colores.primario || '#ffffff'} !important;
        }
        
        /* Textos del menú - TODOS los elementos */
        .sidebar *,
        .menu *,
        .menu-link,
        .menu-item .menu-link,
        .menu-item,
        .menu-list *,
        nav.menu *,
        html body .menu *,
        html body .menu-link,
        html body .menu-item * {
            color: ${colores.submenu_text || colores.header_text || '#000000'} !important;
        }
        
        /* Iconos del menú */
        .menu-link i,
        .menu-item i,
        .menu i {
            color: ${colores.submenu_text || colores.header_text || '#000000'} !important;
        }
        
        /* Submenú - USA MISMO COLOR QUE MENÚ PRINCIPAL */
        .submenu,
        .menu-item .submenu,
        .submenu-block .submenu,
        .submenu-block > .submenu {
            background-color: ${colores.submenu_bg || colores.primario || '#ffffff'} !important;
            background: ${colores.submenu_bg || colores.primario || '#ffffff'} !important;
        }
        
        .submenu-item {
            color: ${colores.submenu_text || colores.header_text || '#000000'} !important;
        }
        
        .submenu-item:hover {
            background-color: ${colores.submenu_hover || colores.secundario} !important;
        }
        
        /* Menu activo */
        .menu-item.active > .menu-link {
            background-color: ${colores.secundario || '#f5f5f5'} !important;
        }
        
        /* Botones - Especificidad máxima */
        html body button,
        html body .btn,
        html body input[type="button"],
        html body input[type="submit"],
        button,
        .btn,
        input[type="button"],
        input[type="submit"] {
            background-color: ${colores.button} !important;
            background: ${colores.button} !important;
            color: ${textForButton} !important;
            border: 2px solid ${textForButton} !important;
            border-radius: 4px !important;
        }
        
        html body button:hover,
        html body .btn:hover,
        html body input[type="button"]:hover,
        html body input[type="submit"]:hover,
        button:hover,
        .btn:hover,
        input[type="button"]:hover,
        input[type="submit"]:hover {
            background-color: ${colores.button_hover} !important;
            background: ${colores.button_hover} !important;
            color: ${textForButtonHover} !important;
            border: 2px solid ${textForButtonHover} !important;
        }
        
        /* Botones de estado */
        .btn-primary,
        button.btn-primary {
            background-color: ${colores.button} !important;
            color: ${textForButton} !important;
        }
        
        .btn-success {
            background-color: ${colores.success || '#27ae60'} !important;
            color: #ffffff !important;
        }
        
        .btn-danger {
            background-color: ${colores.danger || '#e74c3c'} !important;
            color: #ffffff !important;
        }
        
        /* Modales - MÁXIMA ESPECIFICIDAD para sobrescribir admin.css */
        html body .modal,
        html body #modal-pagos,
        html body #modal-factura,
        html body #modal-proforma,
        html body .modal-backdrop,
        .modal,
        #modal-pagos,
        #modal-factura,
        #modal-proforma,
        .modal-backdrop {
            background: ${colores.modal_overlay || 'rgba(0,0,0,0.6)'} !important;
        }
        
        html body .modal-content,
        html body .modal.active .modal-content,
        html body #modal-pagos .modal-content,
        html body #modal-factura .modal-content,
        html body #modal-proforma .modal-content,
        html body .dialog,
        .modal-content,
        .modal.active .modal-content,
        #modal-pagos .modal-content,
        #modal-factura .modal-content,
        #modal-proforma .modal-content,
        .modal,
        .dialog {
            background: ${colores.modal_bg || '#ffffff'} !important;
            color: ${colores.modal_text || textForBody} !important;
            border: 2px solid ${colores.modal_border || '#000000'} !important;
            box-shadow: 0 10px 30px ${colores.modal_shadow || 'rgba(0,0,0,0.3)'} !important;
        }
        
        /* Headers de modales */
        html body .modal-header,
        html body .modal-content .modal-header,
        .modal-header,
        .modal-content .modal-header {
            background: ${colores.modal_bg || '#ffffff'} !important;
            color: ${colores.modal_text || textForBody} !important;
            border-bottom: 1px solid ${colores.modal_border || '#e5e7eb'} !important;
        }
        
        html body .modal-header h3,
        html body .modal-header h2,
        .modal-header h3,
        .modal-header h2 {
            color: ${colores.modal_text || textForBody} !important;
        }
        
        .modal-body {
            background: ${colores.modal_bg || '#ffffff'} !important;
            color: ${colores.modal_text || textForBody} !important;
        }
        
        /* Formularios dentro de modales - MÁXIMA ESPECIFICIDAD */
        html body .modal-content label,
        html body .modal-body label,
        html body .form-group label,
        html body .modal label,
        .modal-content label,
        .modal-body label,
        .form-group label,
        .modal label {
            color: ${colores.modal_text || colores.grid_text} !important;
        }
        
        /* TODOS los inputs en modales - ULTRA ESPECIFICIDAD */
        html body div.modal-content input[type="text"],
        html body div.modal-content input[type="email"],
        html body div.modal-content input[type="password"],
        html body div.modal-content input[type="tel"],
        html body div.modal-content input[type="number"],
        html body div.modal-content input[type="url"],
        html body div.modal-content textarea,
        html body div.modal-content select,
        html body div.modal-body input[type="text"],
        html body div.modal-body input[type="email"],
        html body div.modal-body input[type="password"],
        html body div.modal-body input[type="tel"],
        html body div.modal-body input[type="number"],
        html body div.modal-body input[type="url"],
        html body div.modal-body textarea,
        html body div.modal-body select,
        html body div.form-group input[type="text"],
        html body div.form-group input[type="email"],
        html body div.form-group input[type="password"],
        html body div.form-group input[type="tel"],
        html body div.form-group input[type="number"],
        html body div.form-group input[type="url"],
        html body div.form-group textarea,
        html body div.form-group select,
        html body .modal input,
        html body .modal textarea,
        html body .modal select,
        .modal-content input,
        .modal-content textarea,
        .modal-content select,
        .modal-body input,
        .modal-body textarea,
        .modal-body select,
        .form-group input,
        .form-group textarea,
        .form-group select {
            background-color: ${colores.input_bg || '#ffffff'} !important;
            background: ${colores.input_bg || '#ffffff'} !important;
            color: ${colores.input_text || '#000000'} !important;
            border: 1px solid ${colores.input_border || '#cccccc'} !important;
        }
        
        /* Autocompletado del navegador (Chrome/Edge) */
        html body .modal input:-webkit-autofill,
        html body .modal textarea:-webkit-autofill,
        html body .modal select:-webkit-autofill,
        .modal input:-webkit-autofill,
        .modal textarea:-webkit-autofill,
        .modal select:-webkit-autofill {
            -webkit-box-shadow: 0 0 0 1000px ${colores.input_bg || '#ffffff'} inset !important;
            -webkit-text-fill-color: ${colores.input_text || '#000000'} !important;
            background-color: ${colores.input_bg || '#ffffff'} !important;
            background: ${colores.input_bg || '#ffffff'} !important;
        }
        
        html body .modal-content input:focus,
        html body .modal-content textarea:focus,
        html body .modal-content select:focus,
        html body .modal-body input:focus,
        html body .modal-body textarea:focus,
        html body .modal-body select:focus,
        .modal-content input:focus,
        .modal-content textarea:focus,
        .modal-content select:focus,
        .modal-body input:focus,
        .modal-body textarea:focus,
        .modal-body select:focus {
            border-color: ${colores.primario || '#3498db'} !important;
            outline: none !important;
            background-color: ${colores.input_bg || '#ffffff'} !important;
            background: ${colores.input_bg || '#ffffff'} !important;
        }
        
        /* Checkboxes en modales */
        html body .modal-content input[type="checkbox"],
        html body .modal-body input[type="checkbox"],
        .modal-content input[type="checkbox"],
        .modal-body input[type="checkbox"] {
            border: 1px solid ${colores.input_border || '#cccccc'} !important;
        }
        
        /* Botón cerrar de modal */
        html body .modal-header .close,
        .modal-header .close {
            color: ${colores.modal_text || textForBody} !important;
            opacity: 0.6;
        }
        
        html body .modal-header .close:hover,
        .modal-header .close:hover {
            opacity: 1;
        }
        
        /* Botones dentro de modales (footer) - MÁXIMA ESPECIFICIDAD */
        html body .modal-footer button,
        html body .modal-footer .btn,
        html body .modal-content button,
        html body .modal-body button,
        .modal-footer button,
        .modal-footer .btn,
        .modal-content button,
        .modal-body button {
            background-color: ${colores.button} !important;
            color: ${textForButton} !important;
            border: 2px solid ${textForButton} !important;
            border-radius: 4px !important;
        }
        
        html body .modal-footer button:hover,
        html body .modal-footer .btn:hover,
        html body .modal-content button:hover,
        html body .modal-body button:hover,
        .modal-footer button:hover,
        .modal-footer .btn:hover,
        .modal-content button:hover,
        .modal-body button:hover {
            background-color: ${colores.button_hover || colores.button} !important;
            color: ${textForButtonHover || textForButton} !important;
            border: 2px solid ${textForButtonHover || textForButton} !important;
        }
        
        /* Notificaciones y elementos del menú */
        .notif-bell-icon {
            font-size: 20px;
            color: ${colores.header_text || '#ffffff'} !important;
        }
        
        .notif-badge {
            position: absolute;
            top: -8px;
            right: -8px;
            background: ${colores.danger || '#e74c3c'} !important;
            color: #ffffff !important;
            border-radius: 50%;
            width: 20px;
            height: 20px;
            font-size: 11px;
            font-weight: bold;
            text-align: center;
            line-height: 20px;
        }
        
        .menu-loading {
            padding: 20px;
            color: ${colores.submenu_text || colores.header_text} !important;
            text-align: center;
        }
        
        .user-time-text {
            font-size: 0.85em;
        }
        
        .notif-empty-icon {
            font-size: 32px;
            color: ${colores.disabled_text || '#ddd'} !important;
        }
        
        /* Cards y Stats - Fondo gris para distinguir del blanco */
        .stats-card, .card, .panel, .widget {
            background-color: ${colores.secundario || '#f5f5f5'} !important;
            color: ${colores.grid_text || '#000000'} !important;
            border: 1px solid ${colores.primario || '#000000'} !important;
        }
        
        .stats-card *, .card *, .panel *, .widget * {
            color: ${colores.grid_text || '#000000'} !important;
        }
        
        /* Tablas - Headers con MÁXIMA especificidad */
        html body table thead,
        html body table thead th,
        html body thead,
        html body thead th,
        table thead,
        table thead th,
        thead,
        thead th {
            background-color: ${colores.grid_header || colores.secundario} !important;
            background: ${colores.grid_header || colores.secundario} !important;
            color: ${colores.grid_header_text || '#000000'} !important;
        }
        
        html body table thead th *,
        html body thead th *,
        table thead th *,
        thead th * {
            color: ${colores.grid_header_text || '#000000'} !important;
        }
        
        /* TODOS los th (dentro o fuera de thead) */
        html body table th,
        html body th,
        table th,
        th {
            background-color: ${colores.grid_header || colores.secundario} !important;
            background: ${colores.grid_header || colores.secundario} !important;
            color: ${colores.grid_header_text || '#000000'} !important;
            font-weight: 600;
        }
        
        html body table th *,
        html body th *,
        table th *,
        th * {
            color: ${colores.grid_header_text || '#000000'} !important;
        }
        
        tbody, tbody td {
            background-color: ${colores.app_bg || '#ffffff'} !important;
            color: ${colores.grid_text || '#000000'} !important;
        }
        
        tbody tr:hover {
            background-color: ${colores.grid_hover} !important;
        }
        
        /* Inputs */
        input, select, textarea {
            background-color: ${colores.input_bg || '#ffffff'} !important;
            color: ${colores.input_text || '#000000'} !important;
            border-color: ${colores.input_border || '#cccccc'} !important;
        }
        
        input:disabled, select:disabled {
            background-color: ${colores.disabled_bg || '#f5f5f5'} !important;
            color: ${colores.disabled_text || '#666666'} !important;
        }
        
        /* NOTIFICACIONES - Usar colores de plantilla */
        .notificacion.success {
            background-color: ${colores.success || '#4CAF50'} !important;
            border-left-color: ${colores.success || '#4CAF50'} !important;
        }
        
        .notificacion.error {
            background-color: ${colores.danger || '#f44336'} !important;
            border-left-color: ${colores.danger || '#f44336'} !important;
        }
        
        .notificacion.warning {
            background-color: ${colores.warning || '#ff9800'} !important;
            border-left-color: ${colores.warning || '#ff9800'} !important;
        }
        
        .notificacion.info {
            background-color: ${colores.info || '#2196F3'} !important;
            border-left-color: ${colores.info || '#2196F3'} !important;
        }
        
        /* Botones de confirmación en diálogos */
        .btn-confirmar, .confirmacion-btn-aceptar {
            background-color: ${colores.success || '#4CAF50'} !important;
            color: #ffffff !important;
        }
        
        .btn-confirmar:hover, .confirmacion-btn-aceptar:hover {
            background-color: ${colores.success || '#388E3C'} !important;
        }
        
        .btn-cancelar, .confirmacion-btn-cancelar {
            background-color: ${colores.danger || '#9e9e9e'} !important;
            color: #ffffff !important;
        }
        
        .btn-cancelar:hover, .confirmacion-btn-cancelar:hover {
            background-color: ${colores.danger || '#757575'} !important;
        }
        
        /* Diálogo de confirmación */
        .confirmacion-dialog {
            background-color: ${colores.modal_bg || '#ffffff'} !important;
            border-left-color: ${colores.warning || '#ff9800'} !important;
        }
        
        .confirmacion-dialog p {
            color: ${colores.modal_text || '#333333'} !important;
        }
        
        .confirmacion-dialog p::before {
            color: ${colores.warning || '#ff9800'} !important;
        }
    `;
    
    console.log("[BRANDING] Colores aplicados correctamente (incluye notificaciones)");
    
    // APLICAR ESTILOS DIRECTAMENTE A LOS ELEMENTOS (fuerza bruta)
    console.log('[BRANDING] Aplicando estilos directamente a elementos...');
    
    // Menú lateral - USA COLOR PRIMARIO
    // ========================================
    // CÓDIGO LEGACY DESACTIVADO
    // Los estilos ahora se aplican vía CSS variables + theme-consumer.css
    // ========================================
    /*
    console.log('[BRANDING] 🔍 Valor de colores.primario (menú):', colores.primario);
    console.log('[BRANDING] 🔍 Valor de colores.header_bg (panel):', colores.header_bg);
    console.log('[BRANDING] 🔍 Todos los colores:', colores);
    const menus = document.querySelectorAll('.menu, .sidebar, nav.menu');
    console.log('[BRANDING] 🔍 Menús encontrados:', menus.length);
    menus.forEach(menu => {
        console.log('[BRANDING] ⚙️ Aplicando a menú lateral:', menu.className, '→ Color:', colores.submenu_bg || colores.primario);
        menu.style.setProperty('background-color', colores.submenu_bg || colores.primario, 'important');
        menu.style.setProperty('background', colores.submenu_bg || colores.primario, 'important');
        console.log('[BRANDING] ✓ Aplicado. Verificar computed:', window.getComputedStyle(menu).backgroundColor);
    });
    
    // Enlaces del menú
    const menuLinks = document.querySelectorAll('.menu-link, .menu-item .menu-link');
    console.log('[BRANDING] 🔍 Menu links encontrados:', menuLinks.length, '→ Color texto:', colores.submenu_text || colores.header_text);
    menuLinks.forEach(link => {
        link.style.setProperty('color', colores.submenu_text || colores.header_text, 'important');
        console.log('[BRANDING] ✓ Link actualizado:', link.textContent.substring(0, 20), '→', window.getComputedStyle(link).color);
    });
    
    // Iconos del menú
    const menuIcons = document.querySelectorAll('.menu-link i, .menu-item i');
    console.log('[BRANDING] 🔍 Iconos encontrados:', menuIcons.length);
    menuIcons.forEach(icon => {
        icon.style.setProperty('color', colores.submenu_text || colores.header_text, 'important');
    });
    
    // Submenús
    const submenuItems = document.querySelectorAll('.submenu-item');
    submenuItems.forEach(item => {
        item.style.setProperty('color', colores.submenu_text || colores.header_text, 'important');
    });
    */
    console.log('[BRANDING] ⚠️ Código legacy de estilos inline desactivado. Usando theme-consumer.css');
    console.log('[BRANDING] ℹ️ Estilos aplicados vía variables CSS globales');
    
    // APLICAR TAMBIÉN DENTRO DEL IFRAME
    console.log('[BRANDING] 🔍 Buscando iframe para aplicar estilos...');
    const iframe = document.getElementById('content-frame');
    if (iframe) {
        try {
            const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
            if (iframeDoc) {
                console.log('[BRANDING] ✓ Iframe encontrado, aplicando estilos dentro...');
                
                // Inyectar el mismo <style> dentro del iframe
                let iframeStyleElement = iframeDoc.getElementById('dynamic-branding-styles');
                if (iframeStyleElement) {
                    iframeStyleElement.remove();
                }
                
                iframeStyleElement = iframeDoc.createElement('style');
                iframeStyleElement.id = 'dynamic-branding-styles';
                iframeStyleElement.textContent = styleElement.textContent; // Reutilizar el mismo CSS
                iframeDoc.head.appendChild(iframeStyleElement);
                
                // Aplicar fondo directamente al body del iframe
                if (iframeDoc.body) {
                    iframeDoc.body.style.setProperty('background-color', colores.app_bg || '#ffffff', 'important');
                    iframeDoc.body.style.setProperty('color', textForBody, 'important');
                    console.log('[BRANDING] ✓ Fondo aplicado al body del iframe:', colores.app_bg);
                }
                
                // Botones del iframe: estilos aplicados vía auto_branding.js que se ejecuta dentro del iframe
                console.log('[BRANDING] ℹ️ Estilos de botones en iframe delegados a auto_branding.js');
            }
        } catch (e) {
            console.log('[BRANDING] ⚠️ No se pudo acceder al iframe (cross-origin):', e.message);
        }
    } else {
        console.log('[BRANDING] ⚠️ No se encontró iframe content-frame');
    }
}

// Función para aplicar estilos SOLO al iframe (recibe colores directamente)
function aplicarEstilosAlIframeDirectos(colores) {
    console.log('[BRANDING] 🎯 === INICIO aplicarEstilosAlIframeDirectos ===');
    console.log('[BRANDING] 📦 Colores recibidos:', colores);
    
    const iframe = document.getElementById('content-frame');
    console.log('[BRANDING] 🔍 Buscando iframe "content-frame":', !!iframe);
    
    if (!iframe) {
        console.error('[BRANDING] ❌ No se encontró iframe content-frame');
        return;
    }
    
    if (!colores) {
        console.error('[BRANDING] ❌ No hay colores para aplicar al iframe');
        return;
    }
    
    console.log('[BRANDING] 📝 Aplicando estilos directos al iframe con colores:', {
        app_bg: colores.app_bg,
        grid_text: colores.grid_text,
        secundario: colores.secundario,
        button: colores.button,
        button_text: colores.button_text
    });
    
    // USAR SOLO VALORES DIRECTOS DEL JSON - SIN CALCULOS
    const textForButton = colores.button_text;
    const textForBody = colores.grid_text;
    
    try {
        const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
        console.log('[BRANDING] 📄 iframeDoc obtenido:', !!iframeDoc);
        
        if (!iframeDoc) {
            console.error('[BRANDING] ❌ No se pudo acceder al documento del iframe');
            return;
        }
        
        console.log('[BRANDING] 🔄 Aplicando estilos directos al iframe...');
        console.log('[BRANDING] 🎨 Colores a inyectar:', {
            'body bg': colores.app_bg,
            'body text': textForBody,
            'button bg': colores.button,
            'button text': textForButton
        });
        
        // Inyectar el <style> dentro del iframe
        let iframeStyleElement = iframeDoc.getElementById('dynamic-branding-styles');
        if (iframeStyleElement) {
            console.log('[BRANDING] 🗑️ Eliminando <style> anterior del iframe');
            iframeStyleElement.remove();
        }
        
        iframeStyleElement = iframeDoc.createElement('style');
        iframeStyleElement.id = 'dynamic-branding-styles';
        console.log('[BRANDING] ➕ Creando nuevo <style> en iframe');

        // Generar CSS COMPLETO para el iframe - SOLO VALORES DIRECTOS DEL JSON
        iframeStyleElement.textContent = `
            /* Fondo y texto del body en iframe */
            body {
                background-color: ${colores.app_bg} !important;
                color: ${textForBody} !important;
            }

            /* TARJETAS Y CARDS - IMPORTANTE */
            .card, .info-card, .stat-card, .summary-card,
            .card-header, .card-body, .card-footer,
            .dashboard-card, .metric-card, .stats-card {
                background-color: ${colores.secundario} !important;
                border-color: ${colores.secundario} !important;
            }

            /* Botones en iframe */
            button, .btn, input[type="button"], input[type="submit"] {
                background-color: ${colores.button} !important;
                background: ${colores.button} !important;
                color: ${textForButton} !important;
                border-color: ${colores.button} !important;
            }

            button:hover, .btn:hover, input[type="button"]:hover, input[type="submit"]:hover {
                background-color: ${colores.button_hover} !important;
                background: ${colores.button_hover} !important;
            }

            /* Headers de tablas */
            table thead, table thead th, .grid-header, .table-header {
                background-color: ${colores.grid_header} !important;
                color: ${colores.grid_header_text} !important;
            }

            /* Cuerpo de tablas y filas */
            table tbody,
            table tbody tr,
            tbody,
            .table tbody {
                background-color: ${colores.grid_bg} !important;
            }
            
            table tbody tr {
                background-color: ${colores.grid_bg} !important;
                color: ${colores.grid_text} !important;
                border-color: ${colores.input_border} !important;
            }
            
            table tbody tr:nth-child(even),
            tbody tr:nth-child(even) {
                background-color: ${colores.secundario} !important;
            }
            
            table tbody tr:hover,
            tbody tr:hover {
                background-color: ${colores.grid_hover} !important;
                color: ${colores.grid_text} !important;
            }
            
            /* Celdas de tabla */
            table td,
            table th,
            td, th {
                color: ${colores.grid_text} !important;
                border-color: ${colores.input_border} !important;
            }
            
            /* Checkboxes en tablas */
            table input[type="checkbox"],
            td input[type="checkbox"] {
                background-color: ${colores.input_bg} !important;
                border-color: ${colores.input_border} !important;
            }

            /* Variables CSS para el iframe */
            :root {
                --color-primario: ${colores.primario} !important;
                --color-secundario: ${colores.secundario} !important;
                --color-app-bg: ${colores.app_bg} !important;
                --color-grid-text: ${colores.grid_text} !important;
            }
        `;
        
        console.log('[BRANDING] 📋 CSS generado para iframe (primeras 200 chars):', iframeStyleElement.textContent.substring(0, 200));
        console.log('[BRANDING] ➕ Agregando <style> al <head> del iframe...');
        iframeDoc.head.appendChild(iframeStyleElement);
        console.log('[BRANDING] ✅ <style> agregado al iframe correctamente');
        
        // Aplicar fondo directamente al body del iframe - SOLO VALORES DEL JSON
        if (iframeDoc.body) {
            console.log('[BRANDING] 🎨 Aplicando estilos inline al body del iframe...');
            iframeDoc.body.style.setProperty('background-color', colores.app_bg, 'important');
            iframeDoc.body.style.setProperty('color', textForBody, 'important');
            console.log('[BRANDING] ✓ Fondo aplicado al body del iframe:', colores.app_bg);
            console.log('[BRANDING] ✓ Color texto aplicado al body del iframe:', textForBody);
        } else {
            console.warn('[BRANDING] ⚠️ No se encontró body en el iframe');
        }
        
        console.log('[BRANDING] ✅ === FIN aplicarEstilosAlIframeDirectos === Estilos aplicados correctamente');
        
    } catch (e) {
        console.error('[BRANDING] ❌ ERROR al aplicar estilos directos al iframe:', e);
        console.error('[BRANDING] ❌ Stack trace:', e.stack);
    }
}

// Función para aplicar estilos SOLO al iframe (usando colores guardados)
function aplicarEstilosAlIframe() {
    const iframe = document.getElementById('content-frame');
    if (!iframe) return;
    
    // Obtener los colores guardados
    const colores = window.__COLORES_EMPRESA__;
    if (!colores) {
        console.log('[BRANDING] ⚠️ No hay colores guardados para aplicar al iframe');
        return;
    }
    
    const textForButton = colores.button_text || getTextColorForBackground(colores.button || '#2c3e50');
    
    try {
        const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
        if (!iframeDoc) return;
        
        console.log('[BRANDING] 🔄 Re-aplicando estilos al iframe (navegación detectada)...');
        
        // Inyectar el <style> dentro del iframe
        let iframeStyleElement = iframeDoc.getElementById('dynamic-branding-styles');
        if (iframeStyleElement) {
            iframeStyleElement.remove();
        }
        
        iframeStyleElement = iframeDoc.createElement('style');
        iframeStyleElement.id = 'dynamic-branding-styles';

        const textForBody = getTextColorForBackground(colores.app_bg || '#ffffff');

        // Generar CSS COMPLETO para el iframe (incluyendo tarjetas y cards)
        iframeStyleElement.textContent = `
            /* Fondo y texto del body en iframe */
            body {
                background-color: ${colores.app_bg || '#ffffff'} !important;
                color: ${textForBody} !important;
            }

            /* TARJETAS Y CARDS - IMPORTANTE */
            .card, .info-card, .stat-card, .summary-card,
            .card-header, .card-body, .card-footer,
            .dashboard-card, .metric-card, .stats-card {
                background-color: ${colores.secundario || '#ececec'} !important;
                border-color: ${colores.secundario || '#ececec'} !important;
            }

            /* Botones en iframe */
            button, .btn, input[type="button"], input[type="submit"] {
                background-color: ${colores.button} !important;
                background: ${colores.button} !important;
                color: ${textForButton} !important;
                border-color: ${colores.button} !important;
            }

            button:hover, .btn:hover, input[type="button"]:hover, input[type="submit"]:hover {
                background-color: ${colores.button_hover || colores.button} !important;
                background: ${colores.button_hover || colores.button} !important;
            }

            /* Headers de tablas */
            table thead, table thead th, .grid-header, .table-header {
                background-color: ${colores.grid_header || colores.primario} !important;
                color: ${colores.grid_header_text || '#ffffff'} !important;
            }

            /* Cuerpo de tablas y filas */
            table tbody,
            table tbody tr,
            tbody,
            .table tbody {
                background-color: ${colores.grid_bg || colores.app_bg} \!important;
            }
            
            table tbody tr {
                background-color: ${colores.grid_bg || colores.secundario} \!important;
                color: ${colores.grid_text || textForBody} \!important;
                border-color: ${colores.input_border || '#ddd'} \!important;
            }
            
            table tbody tr:nth-child(even),
            tbody tr:nth-child(even) {
                background-color: ${colores.secundario || colores.app_bg} \!important;
            }
            
            table tbody tr:hover,
            tbody tr:hover {
                background-color: ${colores.grid_hover || colores.button} \!important;
                color: ${colores.grid_text || '#ffffff'} \!important;
            }
            
            /* Celdas de tabla */
            table td,
            table th,
            td, th {
                color: ${colores.grid_text || textForBody} \!important;
                border-color: ${colores.input_border || '#334155'} \!important;
            }
            
            /* Checkboxes en tablas */
            table input[type="checkbox"],
            td input[type="checkbox"] {
                background-color: ${colores.input_bg || '#fff'} \!important;
                border-color: ${colores.input_border || '#ccc'} \!important;
            }

            /* Variables CSS para el iframe */
            :root {
                --color-primario: ${colores.primario} !important;
                --color-secundario: ${colores.secundario} !important;
                --color-success: ${colores.success} !important;
                --color-warning: ${colores.warning} !important;
                --color-danger: ${colores.danger} !important;
                --color-info: ${colores.info} !important;
                --color-button: ${colores.button} !important;
                --color-button-hover: ${colores.button_hover} !important;
                --color-grid-header: ${colores.grid_header} !important;
            }
        `;

        iframeDoc.head.appendChild(iframeStyleElement);

        // Aplicar fondo directamente al body del iframe
        if (iframeDoc.body) {
            iframeDoc.body.style.setProperty('background-color', colores.app_bg || '#ffffff', 'important');
            iframeDoc.body.style.setProperty('color', textForBody, 'important');
            console.log('[BRANDING] Fondo aplicado al body del iframe:', colores.app_bg);
        }
        
        // Botones: estilos aplicados vía auto_branding.js dentro del iframe
        console.log('[BRANDING] ℹ️ Estilos de botones delegados a auto_branding.js en iframe');
        
        // Configurar observer para detectar modales dinámicas
        configurarObserverDeModales(iframeDoc, colores, textForButton);
    } catch (e) {
        console.log('[BRANDING] ⚠️ Error al aplicar estilos al iframe:', e.message);
    }
}

// Función para observar cambios en el DOM y detectar modales
function configurarObserverDeModales(doc, colores, textForButton) {
    console.log('[BRANDING] 🔍 Configurando observer para modales dinámicas...');
    
    const observer = new MutationObserver((mutations) => {
        mutations.forEach((mutation) => {
            mutation.addedNodes.forEach((node) => {
                if (node.nodeType === 1) { // Es un elemento
                    // Buscar botones en el nodo añadido
                    let buttons = [];
                    
                    if (node.matches && node.matches('button, .btn, input[type="button"], input[type="submit"]')) {
                        buttons.push(node);
                    }
                    
                    if (node.querySelectorAll) {
                        const innerButtons = node.querySelectorAll('button, .btn, input[type="button"], input[type="submit"]');
                        buttons.push(...innerButtons);
                    }
                    
                    if (buttons.length > 0) {
                        console.log('[BRANDING] 🆕 Detectados', buttons.length, 'botones nuevos (modal), estilos vía CSS');
                        // Estilos aplicados por auto_branding.js via CSS inyectado
                    }
                }
            });
        });
    });
    
    observer.observe(doc.body, {
        childList: true,
        subtree: true
    });
    
    console.log('[BRANDING] ✓ Observer configurado para detectar modales');
}

// Exportar funciones
window.cargarColoresEmpresa = cargarColoresEmpresa;
window.getTextColorForBackground = getTextColorForBackground;
window.aplicarEstilosAlIframe = aplicarEstilosAlIframe;

// Cargar colores de empresa al cargar la página
document.addEventListener('DOMContentLoaded', cargarColoresEmpresa);

// Configurar listener para re-aplicar estilos cuando el iframe carga nueva página
document.addEventListener('DOMContentLoaded', () => {
    const iframe = document.getElementById('content-frame');
    if (iframe) {
        iframe.addEventListener('load', () => {
            console.log('[BRANDING] 📄 Iframe cargó nueva página, re-aplicando tema...');
            
            // Obtener tema guardado y re-aplicarlo al iframe
            const themeJson = localStorage.getItem('aleph70_theme');
            if (themeJson) {
                try {
                    const theme = JSON.parse(themeJson);
                    console.log('[BRANDING] 🔄 Re-aplicando tema al iframe:', theme.name);
                    applyTheme(theme); // Esto inyectará las variables también en el iframe
                } catch (e) {
                    console.error('[BRANDING] ❌ Error al parsear tema guardado:', e);
                }
            } else {
                console.log('[BRANDING] ⚠️ No hay tema guardado para re-aplicar');
            }
        });
        console.log('[BRANDING] ✓ Listener configurado para detectar navegación en iframe');
    }
});
