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
        const urlPath = window.location.pathname;
        const paginasExcluidas = [
            '/ADMIN_EMPRESAS.html',
            '/EDITAR_EMPRESA.html',
            '/EDITAR_EMPRESA_COLORES.html',
            '/ADMIN_USUARIOS.html',
            '/ADMIN_MODULOS.html'
        ];
        
        if (paginasExcluidas.some(pagina => urlPath.includes(pagina))) {
            console.log('[AUTO-BRANDING] ⏭️ Página de admin excluida, no se aplica branding');
            return;
        }
        
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
                --color-app-bg: ${colores.app_bg || '#ffffff'} !important;
                --color-grid-text: ${textForCards} !important;
                --color-icon: ${colorIconos} !important;
            }
            
            /* Fondo del body y elementos principales */
            body,
            html,
            #app,
            .app-container,
            .main-wrapper,
            .page-wrapper {
                background-color: ${colores.app_bg || '#ffffff'} !important;
                color: ${textForBody} !important;
            }
            
            /* Forzar fondo en divs principales que contienen contenido */
            body > div,
            body > div > div,
            .content-area,
            .page-content,
            main {
                background-color: ${colores.app_bg || '#ffffff'} !important;
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
                border-color: ${colores.button} !important;
            }
            
            /* Botones hover */
            button:hover,
            .btn:hover,
            input[type="button"]:hover,
            input[type="submit"]:hover,
            .tab:hover {
                background-color: ${colores.button_hover || colores.button} !important;
                background: ${colores.button_hover || colores.button} !important;
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
            .select,
            select.form-control {
                background-color: ${colores.select_bg || '#ffffff'} !important;
                color: ${colores.select_text || '#333333'} !important;
                border-color: ${colores.select_border || '#cccccc'} !important;
            }
            
            /* Options dentro de select */
            select option {
                background-color: ${colores.select_bg || '#ffffff'} !important;
                color: ${colores.select_text || '#333333'} !important;
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
            
            /* ===== HOVER SUBMENÚS Y MODALES (igual que menú principal) ===== */
            .modal tbody tr:hover,
            .modal table tr:hover,
            .dialog tbody tr:hover,
            .popup tbody tr:hover,
            .submenu li:hover,
            .dropdown-item:hover,
            .menu-item:hover,
            ul li:hover {
                background-color: ${colores.menu_hover || colores.grid_hover || 'rgba(255,255,255,0.1)'} !important;
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
        `;
        
        // Añadir al final del head para máxima prioridad
        document.head.appendChild(styleElement);
        
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
