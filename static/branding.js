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

// Cargar colores de la empresa
async function cargarColoresEmpresa() {
    try {
        console.log("[BRANDING] Cargando colores...");
        const response = await fetch('/api/auth/branding');
        
        if (!response.ok) {
            console.error("[BRANDING] Error:", response.status);
            return;
        }
        
        const branding = await response.json();
        console.log("[BRANDING] Datos recibidos:", branding);
        
        if (!branding.colores) {
            console.warn("[BRANDING] Sin colores personalizados");
            return;
        }
        
        aplicarColores(branding.colores);
        
    } catch (error) {
        console.error("[BRANDING] Error cargando colores:", error);
    }
}

// Aplicar colores al DOM
function aplicarColores(colores) {
    // Calcular colores de texto
    const textForBody = getTextColorForBackground(colores.app_bg || '#ffffff');
    const textForCards = getTextColorForBackground(colores.secundario || colores.grid_header || '#ffffff');
    
    // Calcular color de texto para botones según el color del botón
    const textForButton = getTextColorForBackground(colores.button || '#2c3e50');
    const textForButtonHover = getTextColorForBackground(colores.button_hover || colores.button || '#1a252f');
    
    console.log('[BRANDING] Color botón:', colores.button, '→ Texto:', textForButton);
    
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
    console.log('Color primario (menú):', colores.header_bg);
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
        
        /* Menú - Especificidad ABSOLUTA */
        html body .layout-container nav.menu,
        html body .layout-container .menu,
        html body nav.menu,
        html body .sidebar, 
        html body .menu,
        .layout-container .menu,
        nav.menu,
        .sidebar,
        .menu {
            background-color: ${colores.header_bg || '#ffffff'} !important;
            background: ${colores.header_bg || '#ffffff'} !important;
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
            color: ${colores.header_text || '#ffffff'} !important;
        }
        
        /* Iconos del menú */
        .menu-link i,
        .menu-item i,
        .menu i {
            color: ${colores.header_text || '#ffffff'} !important;
        }
        
        /* Submenú */
        .submenu {
            background-color: ${colores.header_bg || colores.submenu_bg} !important;
        }
        
        .submenu-item {
            color: ${colores.header_text || '#000000'} !important;
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
            border-color: ${colores.button} !important;
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
            border-color: ${colores.button_hover} !important;
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
        
        /* Modales - Diseño limpio (aplica a modales existentes de tickets, facturas, etc) */
        #modal-pagos,
        #modal-factura,
        #modal-proforma,
        .modal-backdrop {
            background: ${colores.modal_overlay || 'rgba(0,0,0,0.6)'} !important;
        }
        
        .modal-content,
        #modal-pagos .modal-content,
        #modal-factura .modal-content,
        #modal-proforma .modal-content,
        .modal, .dialog {
            background: ${colores.modal_bg || '#ffffff'} !important;
            color: ${colores.modal_text || textForBody} !important;
            border: 2px solid ${colores.modal_border || '#000000'} !important;
            border-radius: 8px !important;
            box-shadow: 0 10px 30px ${colores.modal_shadow || 'rgba(0,0,0,0.3)'} !important;
        }
        
        /* Headers y footers de modales */
        .modal-header {
            background: ${colores.modal_bg || '#ffffff'} !important;
            color: ${colores.modal_text || textForBody} !important;
            border-bottom: 1px solid ${colores.modal_border || '#e5e7eb'} !important;
        }
        
        .modal-header h3,
        .modal-header h2 {
            color: ${colores.modal_text || textForBody} !important;
        }
        
        .modal-body {
            background: ${colores.modal_bg || '#ffffff'} !important;
            color: ${colores.modal_text || textForBody} !important;
        }
        
        /* Botón cerrar de modal */
        .modal-header .close {
            color: ${colores.modal_text || textForBody} !important;
            opacity: 0.6;
        }
        
        .modal-header .close:hover {
            opacity: 1;
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
        
        /* Tablas */
        thead, thead th {
            background-color: ${colores.grid_header || colores.secundario} !important;
            color: ${colores.grid_text || '#000000'} !important;
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
    `;
    
    console.log("[BRANDING] Colores aplicados correctamente");
    
    // APLICAR ESTILOS DIRECTAMENTE A LOS ELEMENTOS (fuerza bruta)
    console.log('[BRANDING] Aplicando estilos directamente a elementos...');
    
    // Menú lateral
    console.log('[BRANDING] 🔍 Valor de colores.header_bg:', colores.header_bg);
    console.log('[BRANDING] 🔍 Todos los colores:', colores);
    const menus = document.querySelectorAll('.menu, .sidebar, nav.menu');
    console.log('[BRANDING] 🔍 Menús encontrados:', menus.length);
    menus.forEach(menu => {
        console.log('[BRANDING] ⚙️ Aplicando a:', menu.className, '→ Color:', colores.header_bg);
        menu.style.setProperty('background-color', colores.header_bg, 'important');
        menu.style.setProperty('background', colores.header_bg, 'important');
        console.log('[BRANDING] ✓ Aplicado. Verificar computed:', window.getComputedStyle(menu).backgroundColor);
    });
    
    // Enlaces del menú
    const menuLinks = document.querySelectorAll('.menu-link, .menu-item .menu-link');
    console.log('[BRANDING] 🔍 Menu links encontrados:', menuLinks.length, '→ Color texto:', colores.header_text);
    menuLinks.forEach(link => {
        link.style.setProperty('color', colores.header_text, 'important');
        console.log('[BRANDING] ✓ Link actualizado:', link.textContent.substring(0, 20), '→', window.getComputedStyle(link).color);
    });
    
    // Iconos del menú
    const menuIcons = document.querySelectorAll('.menu-link i, .menu-item i');
    console.log('[BRANDING] 🔍 Iconos encontrados:', menuIcons.length);
    menuIcons.forEach(icon => {
        icon.style.setProperty('color', colores.header_text, 'important');
    });
    
    // Submenús
    const submenuItems = document.querySelectorAll('.submenu-item');
    submenuItems.forEach(item => {
        item.style.setProperty('color', colores.header_text, 'important');
    });
    
    // Botones - TODOS los tipos
    const buttons = document.querySelectorAll('button, .btn, input[type="button"], input[type="submit"]');
    console.log('[BRANDING] 🔍 Botones encontrados:', buttons.length);
    console.log('[BRANDING] 🔍 Color botón:', colores.button, '→ Texto:', textForButton);
    
    buttons.forEach(button => {
        button.style.setProperty('background-color', colores.button, 'important');
        button.style.setProperty('background', colores.button, 'important');
        button.style.setProperty('color', textForButton, 'important');
        button.style.setProperty('border-color', colores.button, 'important');
        console.log('[BRANDING] ✓ Botón actualizado:', button.textContent?.substring(0, 15) || button.value, 
                    '→ BG:', window.getComputedStyle(button).backgroundColor,
                    'Color:', window.getComputedStyle(button).color);
    });
    
    console.log('[BRANDING] ✅ Estilos aplicados directamente a', menus.length, 'menús,', menuLinks.length, 'links y', buttons.length, 'botones');
    
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
                
                // Aplicar estilos directamente a botones del iframe
                const iframeButtons = iframeDoc.querySelectorAll('button, .btn, input[type="button"], input[type="submit"]');
                console.log('[BRANDING] 🔍 Botones en iframe:', iframeButtons.length);
                iframeButtons.forEach(button => {
                    button.style.setProperty('background-color', colores.button, 'important');
                    button.style.setProperty('background', colores.button, 'important');
                    button.style.setProperty('color', textForButton, 'important');
                    button.style.setProperty('border-color', colores.button, 'important');
                });
                
                console.log('[BRANDING] ✅ Estilos aplicados dentro del iframe a', iframeButtons.length, 'botones');
            }
        } catch (e) {
            console.log('[BRANDING] ⚠️ No se pudo acceder al iframe (cross-origin):', e.message);
        }
    } else {
        console.log('[BRANDING] ⚠️ No se encontró iframe content-frame');
    }
}

// Función para aplicar estilos SOLO al iframe
function aplicarEstilosAlIframe() {
    const iframe = document.getElementById('content-frame');
    if (!iframe) return;
    
    // Obtener los colores guardados
    const colores = window.__COLORES_EMPRESA__;
    if (!colores) {
        console.log('[BRANDING] ⚠️ No hay colores guardados para aplicar al iframe');
        return;
    }
    
    const textForButton = getTextColorForBackground(colores.button || '#2c3e50');
    
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
        
        // Generar CSS para el iframe
        iframeStyleElement.textContent = `
            /* Fondo y texto del body en iframe */
            body {
                background-color: ${colores.app_bg || '#ffffff'} !important;
                color: ${textForBody} !important;
            }
            
            /* Botones en iframe */
            button, .btn, input[type="button"], input[type="submit"] {
                background-color: ${colores.button} !important;
                background: ${colores.button} !important;
                color: ${textForButton} !important;
                border-color: ${colores.button} !important;
            }
            
            button:hover, .btn:hover {
                background-color: ${colores.button_hover || colores.button} !important;
            }
        `;
        
        iframeDoc.head.appendChild(iframeStyleElement);
        
        // Aplicar fondo directamente al body del iframe
        if (iframeDoc.body) {
            iframeDoc.body.style.setProperty('background-color', colores.app_bg || '#ffffff', 'important');
            iframeDoc.body.style.setProperty('color', textForBody, 'important');
            console.log('[BRANDING] ✓ Fondo aplicado al body del iframe:', colores.app_bg);
        }
        
        // Aplicar estilos directamente a botones
        const iframeButtons = iframeDoc.querySelectorAll('button, .btn, input[type="button"], input[type="submit"]');
        console.log('[BRANDING] 🔍 Botones en iframe:', iframeButtons.length);
        iframeButtons.forEach(button => {
            button.style.setProperty('background-color', colores.button, 'important');
            button.style.setProperty('background', colores.button, 'important');
            button.style.setProperty('color', textForButton, 'important');
            button.style.setProperty('border-color', colores.button, 'important');
        });
        
        console.log('[BRANDING] ✅ Estilos re-aplicados al iframe:', iframeButtons.length, 'botones');
        
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
                        console.log('[BRANDING] 🆕 Detectados', buttons.length, 'botones nuevos (modal), aplicando estilos...');
                        buttons.forEach(button => {
                            button.style.setProperty('background-color', colores.button, 'important');
                            button.style.setProperty('background', colores.button, 'important');
                            button.style.setProperty('color', textForButton, 'important');
                            button.style.setProperty('border-color', colores.button, 'important');
                        });
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

// NO cargar automáticamente - se llama desde menu_loader.js DESPUÉS de renderizar el menú
// document.addEventListener('DOMContentLoaded', cargarColoresEmpresa);

// Configurar listener para re-aplicar estilos cuando el iframe carga nueva página
document.addEventListener('DOMContentLoaded', () => {
    const iframe = document.getElementById('content-frame');
    if (iframe) {
        iframe.addEventListener('load', () => {
            console.log('[BRANDING] 📄 Iframe cargó nueva página, re-aplicando estilos...');
            aplicarEstilosAlIframe();
        });
        console.log('[BRANDING] ✓ Listener configurado para detectar navegación en iframe');
    }
});
