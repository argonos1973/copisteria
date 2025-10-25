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
    
    // CSS dinámico mínimo y limpio
    let styleElement = document.getElementById('dynamic-branding-styles');
    if (!styleElement) {
        styleElement = document.createElement('style');
        styleElement.id = 'dynamic-branding-styles';
        document.head.appendChild(styleElement);
    }
    
    styleElement.textContent = `
        /* Variables CSS */
        :root {
            --color-primario: ${colores.primario} !important;
            --color-secundario: ${colores.secundario} !important;
            --color-app-bg: ${colores.app_bg} !important;
        }
        
        /* Fondo y texto */
        body {
            background-color: ${colores.app_bg || '#ffffff'} !important;
            color: ${textForBody} !important;
        }
        
        /* Menú */
        .sidebar, .menu, header, nav {
            background-color: ${colores.header_bg || '#ffffff'} !important;
        }
        
        .sidebar *, .menu *, .menu-link {
            color: ${colores.header_text || '#000000'} !important;
        }
        
        /* Submenú */
        .submenu {
            background-color: ${colores.header_bg || colores.submenu_bg} !important;
        }
        
        .submenu-link {
            color: ${colores.header_text || '#000000'} !important;
        }
        
        .submenu-link:hover {
            background-color: ${colores.submenu_hover || '#f3f4f6'} !important;
        }
        
        /* Botones */
        button, .btn {
            background-color: ${colores.button} !important;
            color: ${colores.button_text || '#ffffff'} !important;
        }
        
        button:hover, .btn:hover {
            background-color: ${colores.button_hover} !important;
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
}

// Exportar funciones
window.cargarColoresEmpresa = cargarColoresEmpresa;
window.getTextColorForBackground = getTextColorForBackground;

// Cargar automáticamente al inicio
document.addEventListener('DOMContentLoaded', cargarColoresEmpresa);
