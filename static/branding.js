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
let coloresEmpresa = null;

// Aplicar colores al DOM
function aplicarColores(colores) {
    // Guardar colores globalmente para aplicarlos al iframe después
    coloresEmpresa = colores;
    
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
        
        /* Submenú - USA COLOR SUBMENU */
        .submenu {
            background-color: ${colores.submenu_bg || colores.primario || '#ffffff'} !important;
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
    
    // Botones: estilos aplicados vía auto_branding.js (CSS inyectado), no inline
    console.log('[BRANDING] ℹ️ Estilos de botones delegados a auto_branding.js');
    
    console.log('[BRANDING] ✅ Estilos aplicados directamente a', menus.length, 'menús y', menuLinks.length, 'links');
    
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
                color: white !important;
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
