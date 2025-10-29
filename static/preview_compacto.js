// Preview Compacto - Visualización en tiempo real sin scroll
// Se actualiza automáticamente al cambiar colores

class PreviewCompacto {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.render();
    }
    
    render() {
        if (!this.container) return;
        
        this.container.innerHTML = `
            <div class="preview-compacto">
                <div class="preview-header">
                    <h4><i class="fas fa-eye"></i> Preview en Vivo</h4>
                    <button class="btn-toggle-preview" onclick="previewCompacto.toggle()">
                        <i class="fas fa-compress-alt"></i>
                    </button>
                </div>
                
                <div class="preview-body" id="preview-body-content">
                    <!-- Fondo de app -->
                    <div class="mini-app" id="preview-app-bg">
                        
                        <!-- Header -->
                        <div class="mini-header" id="preview-header">
                            <div class="mini-header-text">App Header</div>
                            <div class="mini-header-icons">
                                <i class="fas fa-bell mini-icon" id="preview-icon-1"></i>
                                <i class="fas fa-user mini-icon" id="preview-icon-2"></i>
                            </div>
                        </div>
                        
                        <!-- Contenido con columnas -->
                        <div class="mini-content">
                            
                            <!-- Sidebar/Menu -->
                            <div class="mini-sidebar" id="preview-sidebar">
                                <div class="mini-menu-item" id="preview-menu-item">
                                    <i class="fas fa-home mini-icon"></i>
                                    <span>Menú</span>
                                </div>
                                <div class="mini-menu-item-hover" id="preview-menu-hover">
                                    <i class="fas fa-chart-bar mini-icon"></i>
                                    <span>Hover</span>
                                </div>
                            </div>
                            
                            <!-- Main content -->
                            <div class="mini-main">
                                
                                <!-- Botones -->
                                <div class="mini-section">
                                    <div class="mini-buttons">
                                        <button class="mini-btn" id="preview-button">
                                            <i class="fas fa-save"></i> Botón
                                        </button>
                                        <button class="mini-btn mini-btn-hover" id="preview-button-hover">
                                            Hover
                                        </button>
                                    </div>
                                </div>
                                
                                <!-- Tabla/Grid -->
                                <div class="mini-section">
                                    <table class="mini-table">
                                        <thead>
                                            <tr id="preview-table-header">
                                                <th>Cliente</th>
                                                <th>Total</th>
                                            </tr>
                                        </thead>
                                        <tbody id="preview-table-body">
                                            <tr>
                                                <td>Empresa A</td>
                                                <td>1.234 €</td>
                                            </tr>
                                            <tr class="mini-table-hover" id="preview-table-hover">
                                                <td>Empresa B (hover)</td>
                                                <td>2.567 €</td>
                                            </tr>
                                        </tbody>
                                    </table>
                                </div>
                                
                                <!-- Notificaciones -->
                                <div class="mini-section">
                                    <div class="mini-alerts">
                                        <div class="mini-alert mini-alert-success" id="preview-alert-success">
                                            <i class="fas fa-check-circle"></i> Éxito
                                        </div>
                                        <div class="mini-alert mini-alert-warning" id="preview-alert-warning">
                                            <i class="fas fa-exclamation-triangle"></i> Aviso
                                        </div>
                                    </div>
                                </div>
                                
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }
    
    actualizar(colores) {
        if (!colores) return;
        
        // Fondo de app
        const app = document.getElementById('preview-app-bg');
        if (app) app.style.backgroundColor = colores.color_app_bg || '#ffffff';
        
        // Header
        const header = document.getElementById('preview-header');
        if (header) {
            header.style.backgroundColor = colores.color_header_bg || '#2c3e50';
            header.style.color = colores.color_header_text || '#ffffff';
        }
        
        // Iconos
        const icon1 = document.getElementById('preview-icon-1');
        const icon2 = document.getElementById('preview-icon-2');
        if (icon1) icon1.style.color = colores.color_icon || colores.color_header_text || '#ffffff';
        if (icon2) icon2.style.color = colores.color_icon || colores.color_header_text || '#ffffff';
        
        // Sidebar/Menu
        const sidebar = document.getElementById('preview-sidebar');
        if (sidebar) {
            sidebar.style.backgroundColor = colores.color_submenu_bg || '#ffffff';
        }
        
        const menuItem = document.getElementById('preview-menu-item');
        if (menuItem) {
            menuItem.style.color = colores.color_submenu_text || '#000000';
            // Iconos del menú también usan color_submenu_text
            const menuIcon = menuItem.querySelector('i');
            if (menuIcon) {
                menuIcon.style.color = colores.color_submenu_text || '#000000';
            }
        }
        
        const menuHover = document.getElementById('preview-menu-hover');
        if (menuHover) {
            menuHover.style.backgroundColor = colores.color_submenu_hover || '#f5f5f5';
            menuHover.style.color = colores.color_submenu_text || '#000000';
            // Iconos del hover también usan color_submenu_text
            const hoverIcon = menuHover.querySelector('i');
            if (hoverIcon) {
                hoverIcon.style.color = colores.color_submenu_text || '#000000';
            }
        }
        
        // Botones
        const button = document.getElementById('preview-button');
        if (button) {
            button.style.backgroundColor = colores.color_button || '#ffffff';
            button.style.color = colores.color_button_text || '#000000';
            button.style.borderColor = colores.color_button === '#ffffff' ? '#000000' : colores.color_button;
        }
        
        const buttonHover = document.getElementById('preview-button-hover');
        if (buttonHover) {
            buttonHover.style.backgroundColor = colores.color_button_hover || '#f5f5f5';
            buttonHover.style.color = colores.color_button_text || '#000000';
            buttonHover.style.borderColor = colores.color_button_hover === '#ffffff' ? '#000000' : colores.color_button_hover;
        }
        
        // Tabla header
        const tableHeader = document.getElementById('preview-table-header');
        if (tableHeader) {
            tableHeader.style.backgroundColor = colores.color_grid_header || '#333333';
            tableHeader.style.color = colores.color_header_text || '#ffffff';
        }
        
        // Tabla body
        const tableBody = document.getElementById('preview-table-body');
        if (tableBody) {
            tableBody.style.backgroundColor = colores.color_grid_bg || '#ffffff';
            tableBody.style.color = colores.color_grid_text || '#000000';
        }
        
        // Tabla hover
        const tableHover = document.getElementById('preview-table-hover');
        if (tableHover) {
            tableHover.style.backgroundColor = colores.color_grid_hover || '#f5f5f5';
        }
        
        // Notificaciones
        const alertSuccess = document.getElementById('preview-alert-success');
        if (alertSuccess) {
            alertSuccess.style.backgroundColor = colores.color_success || '#e8f5e9';
        }
        
        const alertWarning = document.getElementById('preview-alert-warning');
        if (alertWarning) {
            alertWarning.style.backgroundColor = colores.color_warning || '#fff3e0';
        }
    }
    
    toggle() {
        const body = document.getElementById('preview-body-content');
        if (body) {
            body.classList.toggle('preview-collapsed');
        }
    }
}

// Crear instancia global
let previewCompacto = null;

// Inicializar cuando el DOM esté listo
function inicializarPreviewCompacto(containerId = 'preview-compacto-container') {
    previewCompacto = new PreviewCompacto(containerId);
    return previewCompacto;
}

// Exportar
window.PreviewCompacto = PreviewCompacto;
window.inicializarPreviewCompacto = inicializarPreviewCompacto;
window.previewCompacto = previewCompacto;
