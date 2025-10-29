const API_URL = 'http://192.168.1.23:5001/api';
let empresaId = null;
let plantillaActual = null;

// Plantillas cargadas dinámicamente desde plantillas.js
let PLANTILLAS = {};

// Cargar plantillas al inicio
async function cargarPlantillasEditor() {
    console.log('📦 Cargando plantillas en editor...');
    if (typeof window.cargarPlantillas === 'function') {
        await window.cargarPlantillas();
        PLANTILLAS = window.plantillasColores;
        console.log('✅ Plantillas cargadas:', Object.keys(PLANTILLAS));
    } else {
        console.error('❌ plantillas.js no está cargado');
    }
}

let plantillaOriginal = null;
let coloresOriginales = {};

window.addEventListener('DOMContentLoaded', async () => {
    const params = new URLSearchParams(window.location.search);
    empresaId = params.get('id');
    
    if (!empresaId) {
        alert('No se especificó ID de empresa');
        window.location.href = 'ADMIN_EMPRESAS.html';
        return;
    }
    
    await cargarPlantillasEditor();
    renderizarSidebar();
    await cargarEmpresa();
});

function renderizarSidebar() {
    const sidebar = document.getElementById('sidebar');
    
    sidebar.innerHTML = `
        <h2><i class="fas fa-swatchbook"></i> Plantillas</h2>
        <div class="plantilla-activa">
            <h3><i class="fas fa-check-circle"></i> Plantilla Activa</h3>
            <div class="nombre" id="plantilla-activa-nombre">Cargando...</div>
            <small>Aplicada actualmente</small>
        </div>
        <h3 style="font-size: 0.85rem; color: #7f8c8d; margin-bottom: 0.5rem; text-transform: uppercase;">Disponibles</h3>
        <div id="plantillas-list"></div>
    `;
    
    const list = document.getElementById('plantillas-list');
    Object.keys(PLANTILLAS).forEach(key => {
        const p = PLANTILLAS[key];
        const item = document.createElement('div');
        item.className = 'plantilla-item';
        item.setAttribute('data-plantilla', key);
        item.onclick = () => seleccionarPlantilla(key);
        item.innerHTML = `
            <div class="plantilla-icon">${p.icon || '🎨'}</div>
            <div class="plantilla-info">
                <div class="nombre">${p.nombre || 'Plantilla'}</div>
                <div class="desc">${p.descripcion || p.desc || ''}</div>
            </div>
        `;
        list.appendChild(item);
    });
}

async function cargarEmpresa() {
    try {
        const response = await fetch(`${API_URL}/empresas/${empresaId}`);
        const empresa = await response.json();
        
        renderizarContentPanel(empresa);
        cargarColoresActuales(empresa);
        actualizarPreview();
        
    } catch (error) {
        console.error('Error:', error);
        alert('Error al cargar empresa');
    }
}

function renderizarContentPanel(empresa) {
    const panel = document.getElementById('content-panel');
    
    panel.innerHTML = `
        <div class="empresa-header">
            <img id="empresa-logo" src="${empresa.logo_url || '/static/img/logo.png'}" alt="Logo" class="empresa-logo">
            <div class="empresa-info">
                <h2>${empresa.nombre}</h2>
                <div class="meta">
                    ${empresa.cif ? `<div><i class="fas fa-id-card"></i> ${empresa.cif}</div>` : ''}
                    ${empresa.email ? `<div><i class="fas fa-envelope"></i> ${empresa.email}</div>` : ''}
                    ${empresa.telefono ? `<div><i class="fas fa-phone"></i> ${empresa.telefono}</div>` : ''}
                    ${empresa.direccion ? `<div><i class="fas fa-map-marker-alt"></i> ${empresa.direccion}</div>` : ''}
                    ${empresa.web ? `<div><i class="fas fa-globe"></i> ${empresa.web}</div>` : ''}
                </div>
            </div>
        </div>
        
        <div class="preview-grid">
            <div class="preview-card">
                <h3><i class="fas fa-bars"></i> Menú Lateral</h3>
                <div class="menu-preview" id="menu-preview">
                    <div class="menu-item"><i class="fas fa-home"></i> Dashboard</div>
                    <div class="menu-item"><i class="fas fa-shopping-cart"></i> Ventas</div>
                    <div class="submenu">
                        <div class="submenu-item"><i class="fas fa-file-invoice"></i> Facturas</div>
                        <div class="submenu-item"><i class="fas fa-receipt"></i> Tickets</div>
                    </div>
                    <div class="menu-item"><i class="fas fa-users"></i> Clientes</div>
                </div>
            </div>
            
            <div class="preview-card">
                <h3><i class="fas fa-desktop"></i> Simulación App</h3>
                <div class="app-simulation">
                    <div class="app-header-sim" id="app-header-sim">
                        <span><i class="fas fa-th-large"></i> Panel</span>
                        <span><i class="fas fa-user-circle"></i></span>
                    </div>
                    <div class="app-content-sim" id="app-content-sim">
                        <div class="sim-card" id="sim-card">
                            <h4>Tarjeta</h4>
                            <p>Color secundario</p>
                        </div>
                        <button class="sim-button" id="sim-button">
                            <i class="fas fa-save"></i> Acción
                        </button>
                    </div>
                </div>
            </div>
            
            <div class="preview-card">
                <h3><i class="fas fa-exclamation-triangle"></i> Alertas</h3>
                <div class="alert-preview" id="alert-success" style="background: rgba(39, 174, 96, 0.1); border-color: #27ae60; color: #27ae60;">
                    <i class="fas fa-check-circle"></i> Operación exitosa
                </div>
                <div class="alert-preview" id="alert-warning" style="background: rgba(243, 156, 18, 0.1); border-color: #f39c12; color: #f39c12;">
                    <i class="fas fa-exclamation-triangle"></i> Advertencia
                </div>
                <div class="alert-preview" id="alert-danger" style="background: rgba(231, 76, 60, 0.1); border-color: #e74c3c; color: #e74c3c;">
                    <i class="fas fa-times-circle"></i> Error
                </div>
            </div>
            
            <div class="preview-card">
                <h3><i class="fas fa-table"></i> Tabla</h3>
                <table class="table-preview">
                    <thead>
                        <tr id="table-header-preview">
                            <th>Producto</th>
                            <th>Precio</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td>Item 1</td>
                            <td>10.00€</td>
                        </tr>
                        <tr>
                            <td>Item 2</td>
                            <td>20.00€</td>
                        </tr>
                    </tbody>
                </table>
            </div>
            
            <div class="preview-card">
                <h3><i class="fas fa-th"></i> Grid</h3>
                <div class="grid-preview">
                    <div class="grid-item" id="grid-item-1">Item 1</div>
                    <div class="grid-item" id="grid-item-2">Item 2</div>
                    <div class="grid-item" id="grid-item-3">Item 3</div>
                    <div class="grid-item" id="grid-item-4">Item 4</div>
                </div>
            </div>
            
            <div class="preview-card">
                <h3><i class="fas fa-window-maximize"></i> Modal</h3>
                <div class="modal-preview">
                    <div class="modal-preview-header" id="modal-header-preview">
                        <i class="fas fa-info-circle"></i> Título del Modal
                    </div>
                    <div style="padding: 0.5rem 0;">
                        Contenido del modal aquí
                    </div>
                </div>
            </div>
        </div>
        
        <div class="color-editors">
            <h3><i class="fas fa-paint-brush"></i> Personalizar Colores</h3>
            
            <div class="color-section">
                <h4>🎨 Colores Principales</h4>
                <div class="color-grid">
                    ${crearInputColor('color_app_bg', 'Fondo App', '#ffffff')}
                    ${crearInputColor('color_primario', 'Menú Lateral', '#2c3e50')}
                    ${crearInputColor('color_secundario', 'Tarjetas', '#3498db')}
                    ${crearInputColor('color_header_text', 'Texto Menú', '#ffffff')}
                    ${crearInputColor('color_header_bg', 'Header', '#2c3e50')}
                </div>
            </div>
            
            <div class="color-section">
                <h4>🔘 Botones</h4>
                <div class="color-grid">
                    ${crearInputColor('color_button', 'Botón Normal', '#3498db')}
                    ${crearInputColor('color_button_hover', 'Botón Hover', '#2980b9')}
                    ${crearInputColor('color_button_text', 'Texto Botón', '#ffffff')}
                </div>
            </div>
            
            <div class="color-section">
                <h4>✅ Estados y Alertas</h4>
                <div class="color-grid">
                    ${crearInputColor('color_success', 'Éxito', '#27ae60')}
                    ${crearInputColor('color_warning', 'Advertencia', '#f39c12')}
                    ${crearInputColor('color_danger', 'Peligro', '#e74c3c')}
                    ${crearInputColor('color_info', 'Info', '#3498db')}
                </div>
            </div>
            
            <div class="color-section">
                <h4>📊 Tablas y Grids</h4>
                <div class="color-grid">
                    ${crearInputColor('color_grid_header', 'Encabezado Grid', '#34495e')}
                </div>
            </div>
            
            <div class="color-section">
                <h4>📝 Tarjetas y Texto</h4>
                <div class="color-grid">
                    ${crearInputColor('color_grid_text', 'Texto Tarjetas', '#333333')}
                    ${crearInputColor('color_icon', 'Color Iconos', '#666666')}
                </div>
                <div class="preview-text-cards" style="margin-top: 1rem;">
                    <div class="tarjeta-preview-texto" id="tarjeta-preview-texto" style="background: #f5f5f5; padding: 1rem; border-radius: 8px;">
                        <h4 style="margin: 0 0 0.5rem 0;">
                            <i class="fas fa-chart-line" id="icon-preview"></i> Vista Previa Tarjeta
                        </h4>
                        <p style="margin: 0;" id="texto-preview">
                            Este es el texto que aparecerá en las tarjetas. 
                            <i class="fas fa-info-circle"></i>
                        </p>
                        <div style="margin-top: 0.5rem;">
                            <i class="fas fa-check"></i> 
                            <i class="fas fa-star"></i> 
                            <i class="fas fa-heart"></i>
                        </div>
                    </div>
                </div>
            </div>
            
            <button class="save-button" onclick="guardarColores()">
                <i class="fas fa-save"></i> Guardar Cambios
            </button>
        </div>
    `;
}

function crearInputColor(id, label, defaultValue) {
    return `
        <div class="color-input-group">
            <label>${label}</label>
            <input type="color" id="${id}" value="${defaultValue}" onchange="actualizarPreview()">
            <span class="color-value" id="${id}-value">${defaultValue}</span>
        </div>
    `;
}

function cargarColoresActuales(empresa) {
    const campos = ['color_app_bg', 'color_primario', 'color_secundario', 'color_header_text', 'color_header_bg', 'color_button', 'color_button_hover', 'color_button_text', 'color_success', 'color_warning', 'color_danger', 'color_info', 'color_grid_header', 'color_grid_text', 'color_icon'];
    
    campos.forEach(campo => {
        const input = document.getElementById(campo);
        if (input && empresa[campo]) {
            input.value = empresa[campo];
            const valueSpan = document.getElementById(`${campo}-value`);
            if (valueSpan) valueSpan.textContent = empresa[campo];
        }
    });
}

function seleccionarPlantilla(nombre) {
    document.querySelectorAll('.plantilla-item').forEach(item => item.classList.remove('active'));
    document.querySelector(`[data-plantilla="${nombre}"]`).classList.add('active');
    
    plantillaActual = nombre;
    document.getElementById('plantilla-activa-nombre').textContent = PLANTILLAS[nombre].nombre;
    
    aplicarPlantilla(nombre);
}

function aplicarPlantilla(nombre) {
    const plantilla = PLANTILLAS[nombre];
    Object.keys(plantilla).forEach(key => {
        if (key !== 'nombre' && key !== 'desc' && key !== 'icon') {
            const input = document.getElementById(key);
            if (input) {
                input.value = plantilla[key];
                const valueSpan = document.getElementById(`${key}-value`);
                if (valueSpan) valueSpan.textContent = plantilla[key];
            }
        }
    });
    
    actualizarPreview();
}

function actualizarPreview() {
    const menuBg = document.getElementById('color_submenu_bg')?.value || '#2c3e50';
    const menuText = document.getElementById('color_submenu_text')?.value || '#ffffff';
    const appBg = document.getElementById('color_app_bg')?.value || '#ffffff';
    const secundario = document.getElementById('color_secundario')?.value || '#3498db';
    const button = document.getElementById('color_button')?.value || '#3498db';
    const buttonText = document.getElementById('color_button_text')?.value || '#ffffff';
    const headerBg = document.getElementById('color_header_bg')?.value || '#2c3e50';
    const success = document.getElementById('color_success')?.value || '#27ae60';
    const warning = document.getElementById('color_warning')?.value || '#f39c12';
    const danger = document.getElementById('color_danger')?.value || '#e74c3c';
    const gridHeader = document.getElementById('color_grid_header')?.value || '#34495e';
    
    // Menú
    const menuPreview = document.getElementById('menu-preview');
    if (menuPreview) menuPreview.style.background = menuBg;
    
    document.querySelectorAll('.menu-item').forEach(item => item.style.color = menuText);
    document.querySelectorAll('.submenu-item').forEach(item => item.style.color = menuText);
    
    // App Header
    const appHeader = document.getElementById('app-header-sim');
    if (appHeader) appHeader.style.background = headerBg;
    
    const appContent = document.getElementById('app-content-sim');
    if (appContent) appContent.style.background = appBg;
    
    const simCard = document.getElementById('sim-card');
    if (simCard) simCard.style.background = secundario;
    
    const simButton = document.getElementById('sim-button');
    if (simButton) {
        simButton.style.background = button;
        simButton.style.color = buttonText;
    }
    
    // Alertas
    const alertSuccess = document.getElementById('alert-success');
    if (alertSuccess) {
        const rgb = hexToRgb(success);
        alertSuccess.style.background = `rgba(${rgb.r}, ${rgb.g}, ${rgb.b}, 0.1)`;
        alertSuccess.style.borderColor = success;
        alertSuccess.style.color = success;
    }
    
    const alertWarning = document.getElementById('alert-warning');
    if (alertWarning) {
        const rgb = hexToRgb(warning);
        alertWarning.style.background = `rgba(${rgb.r}, ${rgb.g}, ${rgb.b}, 0.1)`;
        alertWarning.style.borderColor = warning;
        alertWarning.style.color = warning;
    }
    
    const alertDanger = document.getElementById('alert-danger');
    if (alertDanger) {
        const rgb = hexToRgb(danger);
        alertDanger.style.background = `rgba(${rgb.r}, ${rgb.g}, ${rgb.b}, 0.1)`;
        alertDanger.style.borderColor = danger;
        alertDanger.style.color = danger;
    }
    
    // Tabla
    const tableHeader = document.getElementById('table-header-preview');
    if (tableHeader) {
        tableHeader.querySelectorAll('th').forEach(th => {
            th.style.background = gridHeader;
            th.style.color = '#ffffff';
            th.style.borderBottomColor = gridHeader;
        });
    }
    
    // Grid
    [1,2,3,4].forEach(i => {
        const item = document.getElementById(`grid-item-${i}`);
        if (item) {
            const rgb = hexToRgb(gridHeader);
            item.style.background = `rgba(${rgb.r}, ${rgb.g}, ${rgb.b}, 0.1)`;
            item.style.borderLeft = `3px solid ${gridHeader}`;
        }
    });
    
    // Modal header
    const modalHeader = document.getElementById('modal-header-preview');
    if (modalHeader) {
        modalHeader.style.background = `rgba(${hexToRgb(headerBg).r}, ${hexToRgb(headerBg).g}, ${hexToRgb(headerBg).b}, 0.05)`;
        modalHeader.style.color = headerBg;
    }
    
    // PREVIEW TARJETAS Y TEXTO
    const gridText = document.getElementById('color_grid_text')?.value || '#333333';
    const colorIcon = document.getElementById('color_icon')?.value || '#666666';
    
    // Tarjeta preview con fondo secundario
    const tarjetaPreview = document.getElementById('tarjeta-preview-texto');
    if (tarjetaPreview) {
        tarjetaPreview.style.background = secundario;
        tarjetaPreview.style.color = gridText;
    }
    
    // Texto dentro de tarjeta
    const textoPreview = document.getElementById('texto-preview');
    if (textoPreview) {
        textoPreview.style.color = gridText;
    }
    
    // Iconos
    const iconosPreview = document.querySelectorAll('#tarjeta-preview-texto i, #icon-preview');
    iconosPreview.forEach(icon => {
        icon.style.color = colorIcon;
    });
    
    console.log('[EDITOR] Preview actualizado - Texto:', gridText, 'Iconos:', colorIcon);
}

function hexToRgb(hex) {
    const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
    return result ? {
        r: parseInt(result[1], 16),
        g: parseInt(result[2], 16),
        b: parseInt(result[3], 16)
    } : { r: 0, g: 0, b: 0 };
}

async function guardarColores() {
    // Recoger TODOS los colores del formulario
    const colores = {
        color_app_bg: document.getElementById('color_app_bg').value,
        color_primario: document.getElementById('color_primario').value,
        color_secundario: document.getElementById('color_secundario').value,
        color_header_text: document.getElementById('color_header_text').value,
        color_header_bg: document.getElementById('color_header_bg').value,
        color_button: document.getElementById('color_button').value,
        color_button_hover: document.getElementById('color_button_hover').value,
        color_button_text: document.getElementById('color_button_text').value,
        color_success: document.getElementById('color_success').value,
        color_warning: document.getElementById('color_warning').value,
        color_danger: document.getElementById('color_danger').value,
        color_info: document.getElementById('color_info').value,
        color_grid_header: document.getElementById('color_grid_header').value,
        color_grid_text: document.getElementById('color_grid_text').value,
        color_icon: document.getElementById('color_icon').value
    };
    
    console.log('[EDITOR] Guardando colores:', colores);
    
    try {
        const response = await fetch(`${API_URL}/empresas/${empresaId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(colores)
        });
        
        const data = await response.json();
        
        if (response.ok) {
            console.log('[EDITOR] Colores guardados correctamente:', data);
            alert(' Colores guardados exitosamente\n\nHaz LOGOUT y LOGIN para ver los cambios aplicados');
            // Redirigir después de 2 segundos
            setTimeout(() => {
                window.location.href = 'ADMIN_EMPRESAS.html';
            }, 2000);
        } else {
            console.error('[EDITOR] Error al guardar:', data);
            alert(' Error al guardar los colores: ' + (data.error || 'Error desconocido'));
        }
    } catch (error) {
        console.error('[EDITOR] Error de conexión:', error);
        alert(' Error de conexión al servidor');
    }
}
