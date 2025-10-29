/**
 * Auto-Branding para páginas dentro de iframe
 * Este script carga automáticamente los colores de la empresa
 * cuando la página se carga, sin depender del parent
 * Versión: 3.0 - Incluye estilos para notificaciones
 */

(async function() {
    try {
        console.log('[AUTO-BRANDING v4.0] 🎨 Iniciando carga de estilos...');
        console.log('[AUTO-BRANDING] URL actual:', window.location.href);
        
        // Excluir páginas de admin
        // Aplicar branding a TODAS las páginas, incluyendo admin
        console.log('[AUTO-BRANDING] 🎨 Aplicando branding a:', window.location.pathname);
        
        // Obtener branding desde API
        const response = await fetch('/api/auth/branding', {
            credentials: 'include',
            cache: 'no-cache'
        });
        
        if (!response.ok) {
            console.warn('[AUTO-BRANDING] ⚠️ No se pudo cargar branding:', response.status);
            return;
        }
        
        const branding = await response.json();
        console.log('[AUTO-BRANDING] 📦 Branding recibido:', branding);
        
        if (!branding.colores) {
            console.warn('[AUTO-BRANDING] ⚠️ Sin colores personalizados en respuesta');
            return;
        }
        
        const colores = branding.colores;
        
        // DESACTIVADO: Corrección automática de colores
        // Ahora se respetan los colores de la plantilla tal como están configurados
        // La plantilla Minimal REQUIERE blanco y negro, no es un error
        
        console.log('[AUTO-BRANDING] 🎨 Colores a aplicar:', {
            primario: colores.primario,
            header_text: colores.header_text,
            secundario: colores.secundario,
            button: colores.button,
            grid_text: colores.grid_text,
            icon: colores.icon
        });
        
        // Función para calcular color de texto según fondo
        function getTextColor(bgColor) {
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
        
        const textForBody = getTextColor(colores.app_bg || '#ffffff');
        const textForButton = colores.button_text || getTextColor(colores.button || '#2c3e50');
        
        // USAR COLOR DE TEXTO DE LA BD O CALCULAR
        const textForCards = colores.grid_text || getTextColor(colores.secundario || '#ffffff');
        const colorIconos = colores.icon || colores.header_text || '#666666';
        
        // Eliminar estilo anterior si existe
        let styleElement = document.getElementById('auto-branding-styles');
        if (styleElement) {
            styleElement.remove();
        }
        
        // Crear nuevo elemento de estilo
        styleElement = document.createElement('style');
        styleElement.id = 'auto-branding-styles';
        
        // Generar CSS con alta especificidad
        styleElement.textContent = `
            /* Variables CSS */
            :root {
                --color-primario: ${colores.primario} !important;
                --color-secundario: ${colores.secundario} !important;
                --color-button: ${colores.button} !important;
                --color-button-hover: ${colores.button_hover || colores.button} !important;
                --color-app-bg: ${colores.app_bg || '#0f0f0f'} !important;
                --color-grid-text: ${textForCards} !important;
                --color-icon: ${colorIconos} !important;
                --color-grid-header: ${colores.grid_header || colores.primario} !important;
                --color-header-text: ${colores.header_text || '#ffffff'} !important;
                --color-header-bg: ${colores.primario} !important;
                --color-button-text: ${textForButton} !important;
                --color-input-border: ${colores.input_border || '#000000'} !important;
                --color-submenu-bg: ${colores.submenu_bg || colores.primario || '#ffffff'} !important;
                --color-submenu-text: ${colores.submenu_text || colores.header_text || '#000000'} !important;
                --color-submenu-hover: ${colores.submenu_hover || 'rgba(0,0,0,0.05)'} !important;
                --color-success: ${colores.success || '#27ae60'} !important;
                --color-danger: ${colores.danger || '#e74c3c'} !important;
                --color-warning: ${colores.warning || '#f39c12'} !important;
                --color-info: ${colores.info || '#3498db'} !important;
                --color-text: ${textForBody} !important;
                --color-text-light: ${colores.grid_text || '#7f8c8d'} !important;
                --color-border: ${colores.input_border || '#dee2e6'} !important;
                --color-card-bg: ${colores.modal_bg || '#ffffff'} !important;
                --color-hover-bg: ${colores.grid_hover || 'rgba(0,0,0,0.05)'} !important;
            }
            
            /* Fondo del body y elementos principales */
            body,
            html,
            #app,
            .app-container,
            .main-wrapper,
            .page-wrapper {
                background-color: ${colores.app_bg || '#0f0f0f'} !important;
                color: ${textForBody} !important;
            }
            
            /* Forzar fondo en divs principales que contienen contenido */
            body > div,
            body > div > div,
            .content-area,
            .page-content,
            main {
                background-color: ${colores.app_bg || '#0f0f0f'} !important;
                color: ${textForBody} !important;
            }
            
            /* Contenedores de formularios - Mayor especificidad para sobrescribir body > div */
            body .detalle-proforma-container,
            body .detalle-ticket-container,
            body .detalle-factura-container,
            body .detalle-presupuesto-container,
            body .form-inline,
            body .form-group,
            body .cabecera-ticket,
            body .cabecera-proforma,
            body .cabecera-factura,
            body .cabecera-presupuesto,
            body div.detalle-proforma-container,
            body div.detalle-ticket-container,
            body div.detalle-factura-container,
            body div.detalle-presupuesto-container {
                background-color: ${colores.app_bg || '#0f0f0f'} !important;
                color: ${textForBody} !important;
            }
            
            /* Botones con máxima especificidad */
            button,
            .btn,
            input[type="button"],
            input[type="submit"],
            .tab,
            button.tab {
                background-color: ${colores.button} !important;
                background: ${colores.button} !important;
                color: ${textForButton} !important;
                border: 1px solid ${colores.button === '#ffffff' ? '#000000' : colores.button} !important;
            }
            
            /* Botones hover */
            button:hover,
            .btn:hover,
            input[type="button"]:hover,
            input[type="submit"]:hover,
            .tab:hover {
                background-color: ${colores.button_hover || colores.button} !important;
                background: ${colores.button_hover || colores.button} !important;
                border: 1px solid ${colores.button === '#ffffff' ? '#000000' : colores.button_hover || colores.button} !important;
            }
            
            /* Botones activos (IMPORTANTE para los tabs) */
            button.active,
            .btn.active,
            .tab.active {
                background-color: ${colores.button} !important;
                background: ${colores.button} !important;
                color: ${textForButton} !important;
                font-weight: bold !important;
                opacity: 1 !important;
            }
            
            /* Tarjetas - USAR COLOR DE TEXTO CORRECTO */
            .card,
            .info-card,
            .stat-card,
            .stats-card,
            .summary-card,
            .dashboard-card,
            .metric-card,
            .stats-container .stats-card {
                background-color: ${colores.secundario || '#ececec'} !important;
                border-color: ${colores.secundario || '#ececec'} !important;
                color: ${textForCards} !important;
            }
            
            /* Texto dentro de tarjetas */
            .card *,
            .stat-card *,
            .stats-card *,
            .info-card *,
            .summary-card *,
            .dashboard-card *,
            .metric-card * {
                color: ${textForCards} !important;
            }
            
            /* Iconos */
            .fa, .fas, .far, .fal, .fab,
            i[class*="fa-"],
            .icon {
                color: ${colorIconos} !important;
            }
            
            /* Headers de tablas - MÁXIMA ESPECIFICIDAD */
            table thead,
            table thead tr,
            table thead th,
            .table thead,
            .table thead tr,
            .table thead th,
            .table-responsive table thead,
            .table-responsive table thead tr,
            .table-responsive table thead th,
            thead,
            thead tr,
            thead th,
            .grid-header,
            .table-header {
                background-color: ${colores.grid_header || colores.primario} !important;
                background: ${colores.grid_header || colores.primario} !important;
                color: #ffffff !important;
                border-color: ${colores.grid_header || colores.primario} !important;
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
            
            /* Botones de confirmación */
            .btn-confirmar, .confirmacion-btn-aceptar {
                background-color: ${colores.success || '#4CAF50'} !important;
            }
            
            .btn-cancelar, .confirmacion-btn-cancelar {
                background-color: ${colores.danger || '#9e9e9e'} !important;
            }
            
            /* LABELS - para que se vean en modo oscuro */
            label,
            .form-label,
            .label,
            th,
            .table-label {
                color: ${colores.label || colores.grid_text || textForBody} !important;
            }
            
            /* INPUTS - inputs de texto, fecha, número */
            input[type="text"],
            input[type="email"],
            input[type="password"],
            input[type="number"],
            input[type="date"],
            input[type="time"],
            input[type="datetime-local"],
            input[type="tel"],
            input[type="url"],
            input[type="search"],
            textarea {
                background-color: ${colores.input_bg || '#ffffff'} !important;
                color: ${colores.input_text || '#333333'} !important;
                border-color: ${colores.input_border || '#cccccc'} !important;
            }
            
            /* SELECTS - desplegables */
            select,
            body select,
            select.width-full,
            select#concepto-detalle,
            select#estado-detalle {
                background-color: ${colores.select_bg || '#2a2a2a'} !important;
                background: ${colores.select_bg || '#2a2a2a'} !important;
                color: ${colores.select_text || '#e0e0e0'} !important;
                border-color: ${colores.select_border || '#4a4a4a'} !important;
            }
            
            /* Opciones de los selects */
            select option,
            body select option {
                background-color: ${colores.select_bg || '#2a2a2a'} !important;
                background: ${colores.select_bg || '#2a2a2a'} !important;
                color: ${colores.select_text || '#e0e0e0'} !important;
            }
            
            /* Contenedores de formularios y zonas en blanco */
            .form-container,
            .form-group,
            .input-group,
            .search-container,
            .filters-container,
            .toolbar,
            .panel,
            .content,
            .main-content,
            .container,
            .table-container,
            .pagination-container,
            .filters,
            .controls,
            .header-section,
            .content-wrapper {
                background-color: ${colores.app_bg || '#ffffff'} !important;
                color: ${textForBody} !important;
            }
            
            /* PAGINACIÓN - Aplicar colores de plantilla */
            .pagination,
            .pagination-info,
            .pagination span,
            .pagination div,
            div[style*="display: flex"][style*="justify-content: space-between"] {
                background-color: ${colores.app_bg || '#ffffff'} !important;
                color: ${textForBody} !important;
            }
            
            /* Texto de paginación específico */
            .pagination span,
            span[style*="color: #333"],
            .page-info,
            .pagination-text {
                color: ${textForBody} !important;
            }
            
            /* Wrappers de tabla - fondo de aplicación */
            .table-responsive,
            .table-wrapper,
            .grid-container,
            .data-table-wrapper,
            div[style*="overflow"] {
                background-color: ${colores.app_bg || '#ffffff'} !important;
                color: ${textForBody} !important;
            }
            
            /* Tablas - fondo del body de la tabla con máxima especificidad */
            table tbody tr,
            table tbody tr td,
            .table tbody tr,
            .table tbody tr td,
            .table-responsive table tbody tr,
            .table-responsive table tbody tr td {
                background-color: ${colores.grid_bg || colores.app_bg || '#ffffff'} !important;
                background: ${colores.grid_bg || colores.app_bg || '#ffffff'} !important;
                color: ${colores.grid_text || textForBody} !important;
            }
            
            /* Tabla completa - borde y fondo */
            table,
            .table,
            .data-table {
                background-color: ${colores.grid_bg || colores.app_bg || '#ffffff'} !important;
                border-color: ${colores.grid_header || '#cccccc'} !important;
            }
            
            /* Hover en filas de tabla con color configurable */
            table tbody tr:hover,
            table tbody tr:hover td,
            .table tbody tr:hover,
            .table tbody tr:hover td,
            .table-responsive table tbody tr:hover,
            .table-responsive table tbody tr:hover td {
                background-color: ${colores.grid_hover || 'rgba(0,0,0,0.1)'} !important;
                background: ${colores.grid_hover || 'rgba(0,0,0,0.1)'} !important;
            }
            
            /* Bordes de celdas - condicional */
            ${colores.grid_cell_borders === 'false' ? `
            table tbody td,
            .table tbody td {
                border: none !important;
            }
            ` : `
            table tbody td,
            .table tbody td {
                border-color: ${colores.grid_header || '#cccccc'} !important;
            }
            `}
            
            /* MODALES Y DIÁLOGOS - Aplicar colores de plantilla */
            .modal,
            .modal-content,
            .dialog,
            .dialog-content,
            .popup,
            .popup-content,
            .overlay-content,
            [role="dialog"],
            div[style*="position: fixed"][style*="z-index"] {
                background-color: ${colores.modal_bg || colores.app_bg || '#ffffff'} !important;
                background: ${colores.modal_bg || colores.app_bg || '#ffffff'} !important;
                color: ${colores.modal_text || textForBody} !important;
                border-color: ${colores.modal_border || '#cccccc'} !important;
            }
            
            /* Encabezado de modal */
            .modal-header,
            .dialog-header,
            .popup-header {
                background-color: ${colores.modal_bg || colores.app_bg || '#ffffff'} !important;
                color: ${colores.modal_text || textForBody} !important;
                border-bottom-color: ${colores.modal_border || '#cccccc'} !important;
            }
            
            /* Body de modal */
            .modal-body,
            .dialog-body,
            .popup-body {
                background-color: ${colores.modal_bg || colores.app_bg || '#ffffff'} !important;
                color: ${colores.modal_text || textForBody} !important;
            }
            
            /* Footer de modal */
            .modal-footer,
            .dialog-footer,
            .popup-footer {
                background-color: ${colores.modal_bg || colores.app_bg || '#ffffff'} !important;
                border-top-color: ${colores.modal_border || '#cccccc'} !important;
            }
            
            /* Textos y labels dentro de modales */
            .modal label,
            .modal p,
            .modal span,
            .dialog label,
            .dialog p,
            .dialog span {
                color: ${colores.modal_text || textForBody} !important;
            }
            
            /* Botón cerrar modal (.cerrar-modal) */
            .cerrar-modal,
            .close,
            button.close {
                color: ${colores.modal_text || textForBody} !important;
                opacity: 0.7;
            }
            
            .cerrar-modal:hover,
            .close:hover {
                color: ${colores.modal_text || textForBody} !important;
                opacity: 1;
            }
            
            /* Todos los h2, h3, h4 dentro de modales */
            .modal h2,
            .modal h3,
            .modal h4,
            .modal-content h2,
            .modal-content h3 {
                color: ${colores.modal_text || textForBody} !important;
            }
            
            /* Elementos específicos de estadisticas.html con estilos inline */
            .modal div[style*="background: #f5f5f5"],
            .modal div[style*="background:#f5f5f5"],
            .modal div[style*="color: #666"],
            .modal div[style*="color:#666"] {
                background: ${colores.secundario || colores.app_bg} !important;
                color: ${colores.modal_text || textForBody} !important;
            }
            
            /* ===== IMPORTES - Colores FIJOS (no dependen de plantilla) ===== */
            .importe-negativo,
            .negativo,
            .deuda,
            .rojo,
            span.negativo,
            td.negativo,
            div.negativo,
            .text-danger,
            span[style*="color: red"],
            td[style*="color: red"],
            [class*="negative"],
            [data-amount*="-"] {
                color: #dc3545 !important;
            }
            
            .importe-positivo,
            .positivo,
            .credito,
            .pagado,
            .verde,
            span.positivo,
            td.positivo,
            div.positivo,
            .text-success,
            span[style*="color: green"],
            td[style*="color: green"],
            [class*="positive"] {
                color: #28a745 !important;
            }
            
            /* ===== MENÚ LATERAL - Background y texto ===== */
            .menu,
            nav.menu,
            .sidebar,
            aside.menu {
                background-color: ${colores.submenu_bg || colores.primario || '#ffffff'} !important;
            }
            
            .menu *,
            nav.menu *,
            .sidebar *,
            .menu-list *,
            .menu-link,
            .menu-item,
            .menu-label {
                color: ${colores.submenu_text || colores.header_text || '#000000'} !important;
            }
            
            .menu-link i,
            .menu-item i {
                color: ${colores.submenu_text || colores.header_text || '#000000'} !important;
            }
            
            .submenu,
            .menu .submenu {
                background-color: ${colores.submenu_bg || colores.primario || '#ffffff'} !important;
            }
            
            .submenu-item,
            .submenu a {
                color: ${colores.submenu_text || colores.header_text || '#000000'} !important;
            }
            
            /* ===== HOVER SUBMENÚS Y MODALES ===== */
            .modal tbody tr:hover,
            .modal table tr:hover,
            .dialog tbody tr:hover,
            .popup tbody tr:hover,
            .submenu li:hover,
            .dropdown-item:hover,
            .menu-item:hover,
            .menu-link:hover,
            ul li:hover {
                background-color: ${colores.submenu_hover || colores.menu_hover || colores.grid_hover || 'rgba(0,0,0,0.05)'} !important;
            }
            
            /* ===== CELDAS CON ICONOS - Background configurable ===== */
            td.celda-icono,
            td.icon-cell,
            td[data-icon],
            .celda-con-icono,
            td:has(i.fas),
            td:has(i.fa),
            td:has(span.emoji),
            td > i.fas,
            td > i.fa {
                background-color: ${colores.icon_cell_bg || colores.secundario || colores.app_bg} !important;
                padding: 0.5rem !important;
            }
            
            /* ===== PÁGINAS GESTIÓN - Sobrescribir estilos inline ===== */
            /* Inputs readonly en gestión */
            .readonly-field,
            input[readonly],
            .total-proforma-display,
            .hidden-field {
                background-color: ${colores.input_bg || colores.app_bg} !important;
                color: ${colores.input_text || textForBody} !important;
                border-color: ${colores.input_border || '#cccccc'} !important;
            }
            
            /* Labels en gestión */
            .detalle-proforma-item label,
            .contact-field label,
            .contact-main .contact-field label {
                color: ${colores.label || textForBody} !important;
            }
            
            /* Cabecera de gestión */
            .cabecera-ticket,
            .page-header {
                background-color: ${colores.secundario || colores.app_bg} !important;
                color: ${textForCards} !important;
            }
            
            /* Modal content en gestión */
            .modal-content {
                background-color: ${colores.modal_bg || colores.app_bg} !important;
                color: ${colores.modal_text || textForBody} !important;
            }
            
            /* Inputs específicos de gestión */
            .contact-main .contact-field input {
                background-color: ${colores.input_bg || colores.app_bg} !important;
                color: ${colores.input_text || textForBody} !important;
                border-color: ${colores.input_border || '#cccccc'} !important;
            }
            
            /* Forzar sobrescritura de colores hardcoded en gestión */
            .contact-main .contact-field label[style*="color: #7f8c8d"],
            label[style*="color: #7f8c8d"] {
                color: ${colores.label || textForBody} !important;
            }
            
            input[style*="background: #fafbfc"],
            input[style*="background:#fafbfc"] {
                background-color: ${colores.input_bg || colores.app_bg} !important;
            }
            
            /* ===== PÁGINA CONTACTOS - Sobrescribir estilos inline del <style> ===== */
            /* Contenedores de tabs y secciones */
            .tabs-container,
            .tab-content,
            .tab-section,
            .tabs-header {
                background-color: ${colores.app_bg || '#ffffff'} !important;
                color: ${textForBody} !important;
            }
            
            /* Sugerencias de dirección - sobrescribir background: white */
            .sugerencias-lista {
                background-color: ${colores.modal_bg || colores.app_bg || '#ffffff'} !important;
                border-color: ${colores.input_border || '#cccccc'} !important;
            }
            
            /* Items de sugerencias - sobrescribir var(--color-fondo) y hover */
            .sugerencia-item {
                background-color: ${colores.modal_bg || colores.app_bg || '#ffffff'} !important;
                color: ${colores.modal_text || textForBody} !important;
                border-color: ${colores.input_border || '#cccccc'} !important;
            }
            
            .sugerencia-item:hover {
                background-color: ${colores.grid_hover || 'rgba(0,0,0,0.1)'} !important;
                color: ${colores.modal_text || textForBody} !important;
            }
            
            /* Botones de tabs */
            .tab-button,
            button.tab-button {
                background-color: ${colores.button} !important;
                color: ${textForButton} !important;
                border-color: ${colores.button} !important;
            }
            
            .tab-button:hover,
            button.tab-button:hover {
                background-color: ${colores.button_hover || colores.button} !important;
            }
            
            .tab-button.active,
            button.tab-button.active {
                background-color: ${colores.button} !important;
                color: ${textForButton} !important;
                opacity: 1 !important;
            }
            
            /* Filas y campos del formulario */
            .field-row,
            .field-item,
            .form-row,
            .form-column {
                background-color: transparent !important;
                color: ${textForBody} !important;
            }
            
            /* Input containers */
            .input-container {
                background-color: transparent !important;
            }
            
            /* ===== ESTADÍSTICAS - Sobrescribir estilos inline ===== */
            /* Contenedores principales */
            .stats-container,
            .stats-card,
            .stats-content,
            .tab-content {
                background-color: ${colores.secundario || colores.app_bg} !important;
                background-image: none !important;
                color: ${textForBody} !important;
            }
            
            /* Sobrescribir estados especiales */
            .stats-card.stats-superado,
            .stats-superado {
                background: ${colores.secundario || colores.app_bg} !important;
                background-image: none !important;
                border-color: ${colores.success || '#27ae60'} !important;
            }
            
            /* Títulos con color hardcoded */
            .stats-header h1,
            .stats-card h3,
            h1[style*="color"],
            h2[style*="color"],
            h3[style*="color"],
            .modal h2[style*="color"] {
                color: ${textForBody} !important;
            }
            
            /* Filas de estadísticas */
            .stats-row {
                background-color: transparent !important;
                color: ${textForBody} !important;
            }
            
            /* Valores y labels de estadísticas */
            .stats-value,
            .stats-value[style*="color"],
            .stats-label,
            .stats-comparison,
            .stats-percentage,
            .stats-previous,
            #ig-ultima-actualizacion {
                color: ${textForBody} !important;
            }
            
            /* Modales de estadísticas */
            .modal-content[style],
            div[style*="background: #f5f5f5"],
            div[style*="background:#f5f5f5"] {
                background-color: ${colores.modal_bg || colores.app_bg} !important;
                color: ${colores.modal_text || textForBody} !important;
            }
            
            /* Tablas en modales */
            thead[style*="background"],
            thead {
                background-color: ${colores.grid_header || colores.primario} !important;
                color: ${colores.header_text} !important;
            }
            
            /* Celdas de tabla con estilos inline */
            td[style*="color"],
            th[style*="color"] {
                color: ${textForBody} !important;
            }
            
            /* Botones con estilos inline */
            button[style*="background"],
            .btn-descargar[style*="background"] {
                background-color: ${colores.button} !important;
                color: ${textForButton} !important;
            }
            
            /* Labels y textos pequeños */
            div[style*="font-size: 0.75rem"],
            small[style*="color"] {
                color: ${textForBody} !important;
                opacity: 0.7;
            }
            
            /* ===== PÁGINAS ADMIN - Sobrescribir estilos hardcoded ===== */
            /* Body y contenedores principales */
            body {
                background: ${colores.app_bg || '#f0f2f5'} !important;
            }
            
            .container,
            .main-container {
                background-color: transparent !important;
            }
            
            /* Títulos */
            h1, h2, h3, h4, h5, h6 {
                color: ${textForBody} !important;
            }
            
            /* Tarjetas de empresas */
            .empresa-card,
            .card {
                background-color: ${colores.secundario || '#ffffff'} !important;
                color: ${textForBody} !important;
            }
            
            .empresa-info h3,
            .card-title {
                color: ${textForBody} !important;
            }
            
            .empresa-details,
            .card-text {
                color: ${textForBody} !important;
            }
            
            /* Modales */
            .modal {
                background-color: rgba(0, 0, 0, 0.7) !important;
            }
            
            .modal-content {
                background-color: ${colores.modal_bg || colores.app_bg || '#ffffff'} !important;
                color: ${colores.modal_text || textForBody} !important;
            }
            
            .modal-header h2 {
                color: ${textForBody} !important;
            }
            
            /* Formularios */
            .form-group label {
                color: ${colores.label || textForBody} !important;
            }
            
            .form-group input,
            .form-group textarea,
            .form-group select {
                background-color: ${colores.input_bg || '#ffffff'} !important;
                color: ${colores.input_text || textForBody} !important;
                border-color: ${colores.input_border || '#dddddd'} !important;
            }
            
            /* Botones */
            .btn-primary {
                background: ${colores.button || '#3498db'} !important;
                color: ${textForButton} !important;
            }
            
            .btn-primary:hover {
                background: ${colores.button_hover || colores.button || '#2980b9'} !important;
            }
            
            .btn-success {
                background: ${colores.success || '#27ae60'} !important;
                color: #ffffff !important;
            }
            
            /* Loading y estados */
            .loading,
            .no-empresas {
                color: ${textForBody} !important;
            }
            
            /* Detalles/accordion */
            details summary {
                color: ${textForBody} !important;
            }
            
            details summary:hover {
                color: ${colores.primario || '#3498db'} !important;
            }
            
            /* Iconos */
            .empresa-details i,
            .fas, .far, .fab {
                color: ${colorIconos} !important;
            }
        `;
        
        // Añadir al final del head para máxima prioridad
        document.head.appendChild(styleElement);
        
        // Estilos inline deshabilitados en Gestión para respetar la plantilla.
        // Se aplican únicamente estilos vía CSS inyectado arriba y hojas de estilo.
        
        console.log('[AUTO-BRANDING] ✅ Estilos aplicados correctamente');
        console.log('[AUTO-BRANDING] 📋 Resumen de estilos aplicados:');
        console.log('  • Menú lateral (primario):', colores.primario);
        console.log('  • Texto menú:', colores.header_text);
        console.log('  • Tarjetas (secundario):', colores.secundario);
        console.log('  • Texto tarjetas:', textForCards);
        console.log('  • Botones:', colores.button, '→ Texto:', textForButton);
        console.log('  • Iconos:', colorIconos);
        console.log('[AUTO-BRANDING] ✨ Página lista con branding aplicado');
        
    } catch (error) {
        console.error('[AUTO-BRANDING] ❌ Error:', error);
        console.error('[AUTO-BRANDING] Stack:', error.stack);
    }
})();
