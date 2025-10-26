const API_URL = 'http://192.168.1.23:5001/api';
let empresaId = null;
let plantillaActual = null;

const PLANTILLAS = {
    minimal: { nombre: 'Minimal', desc: 'Negro y blanco', icon: '✨', color_primario: '#ffffff', color_secundario: '#f5f5f5', color_button: '#000000', color_button_hover: '#333333', color_header_text: '#000000', color_app_bg: '#ffffff', color_success: '#000000', color_warning: '#666666', color_danger: '#000000', color_info: '#333333' },
    zen: { nombre: 'Zen', desc: 'Ultra minimalista', icon: '🧘', color_primario: '#f8f8f8', color_secundario: '#ececec', color_button: '#cccccc', color_button_hover: '#aaaaaa', color_header_text: '#111111', color_app_bg: '#ffffff', color_success: '#999999', color_warning: '#777777', color_danger: '#555555', color_info: '#888888' },
    glassmorphism: { nombre: 'Glassmorphism', desc: 'Efecto cristal', icon: '🌙', color_primario: '#1a1a2e', color_secundario: '#16213e', color_button: '#0f3460', color_button_hover: '#533483', color_header_text: '#e94560', color_app_bg: '#0a0a14', color_success: '#00d9ff', color_warning: '#ff6b6b', color_danger: '#ee5a6f', color_info: '#4ecdc4' },
    cyber: { nombre: 'Cyber Night', desc: 'Futurista oscuro', icon: '🚀', color_primario: '#0a0e27', color_secundario: '#1a1f3a', color_button: '#3d52d5', color_button_hover: '#5a67d8', color_header_text: '#00ffff', color_app_bg: '#050816', color_success: '#00ff88', color_warning: '#ffaa00', color_danger: '#ff0055', color_info: '#00d4ff' },
    oceano: { nombre: 'Océano', desc: 'Azules profundos', icon: '🌊', color_primario: '#006994', color_secundario: '#13678A', color_button: '#012A4A', color_button_hover: '#013A63', color_header_text: '#A9D6E5', color_app_bg: '#E8F4F8', color_success: '#2A9D8F', color_warning: '#F4A261', color_danger: '#E76F51', color_info: '#89C2D9' },
    default: { nombre: 'Por Defecto', desc: 'Clásico', icon: '🎨', color_primario: '#2c3e50', color_secundario: '#3498db', color_button: '#3498db', color_button_hover: '#2980b9', color_header_text: '#ffffff', color_app_bg: '#ffffff', color_success: '#27ae60', color_warning: '#f39c12', color_danger: '#e74c3c', color_info: '#3498db' }
};

window.addEventListener('DOMContentLoaded', async () => {
    const params = new URLSearchParams(window.location.search);
    empresaId = params.get('id');
    
    if (!empresaId) {
        alert('No se especificó ID de empresa');
        window.location.href = 'ADMIN_EMPRESAS.html';
        return;
    }
    
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
        <h3 style="font-size: 0.95rem; color: #7f8c8d; margin-bottom: 0.75rem; text-transform: uppercase;">Disponibles</h3>
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
            <div class="plantilla-icon">${p.icon}</div>
            <div class="plantilla-info">
                <div class="nombre">${p.nombre}</div>
                <div class="desc">${p.desc}</div>
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
                    <i class="fas fa-id-card"></i> ${empresa.cif || '-'} | 
                    <i class="fas fa-envelope"></i> ${empresa.email || '-'}
                </div>
            </div>
        </div>
        
        <div class="preview-grid">
            <div class="preview-card">
                <h3><i class="fas fa-bars"></i> Preview Menú Lateral</h3>
                <div class="menu-preview" id="menu-preview">
                    <div class="menu-item"><i class="fas fa-home"></i> Dashboard</div>
                    <div class="menu-item"><i class="fas fa-shopping-cart"></i> Ventas</div>
                    <div class="submenu">
                        <div class="submenu-item"><i class="fas fa-file-invoice"></i> Facturas</div>
                        <div class="submenu-item"><i class="fas fa-receipt"></i> Tickets</div>
                    </div>
                    <div class="menu-item"><i class="fas fa-users"></i> Clientes</div>
                    <div class="menu-item"><i class="fas fa-box"></i> Productos</div>
                </div>
            </div>
            
            <div class="preview-card">
                <h3><i class="fas fa-desktop"></i> Simulación App</h3>
                <div class="app-simulation">
                    <div class="app-header-sim" id="app-header-sim">
                        <span><i class="fas fa-th-large"></i> Panel de Control</span>
                        <span><i class="fas fa-user-circle"></i></span>
                    </div>
                    <div class="app-content-sim" id="app-content-sim">
                        <div class="sim-card" id="sim-card">
                            <h4 style="margin-bottom: 0.5rem;">Tarjeta de Ejemplo</h4>
                            <p style="opacity: 0.9;">Esta tarjeta muestra el color secundario</p>
                        </div>
                        <button class="sim-button" id="sim-button">
                            <i class="fas fa-save"></i> Botón de Acción
                        </button>
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
                </div>
            </div>
            
            <div class="color-section">
                <h4>🔘 Botones</h4>
                <div class="color-grid">
                    ${crearInputColor('color_button', 'Botón Normal', '#3498db')}
                    ${crearInputColor('color_button_hover', 'Botón Hover', '#2980b9')}
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
    const campos = ['color_app_bg', 'color_primario', 'color_secundario', 'color_header_text', 'color_button', 'color_button_hover', 'color_success', 'color_warning', 'color_danger', 'color_info'];
    
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
    const menuBg = document.getElementById('color_primario')?.value || '#2c3e50';
    const menuText = document.getElementById('color_header_text')?.value || '#ffffff';
    const appBg = document.getElementById('color_app_bg')?.value || '#ffffff';
    const secundario = document.getElementById('color_secundario')?.value || '#3498db';
    const button = document.getElementById('color_button')?.value || '#3498db';
    
    const menuPreview = document.getElementById('menu-preview');
    if (menuPreview) menuPreview.style.background = menuBg;
    
    document.querySelectorAll('.menu-item').forEach(item => item.style.color = menuText);
    document.querySelectorAll('.submenu-item').forEach(item => item.style.color = menuText);
    
    const appHeader = document.getElementById('app-header-sim');
    if (appHeader) appHeader.style.background = menuBg;
    
    const appContent = document.getElementById('app-content-sim');
    if (appContent) appContent.style.background = appBg;
    
    const simCard = document.getElementById('sim-card');
    if (simCard) simCard.style.background = secundario;
    
    const simButton = document.getElementById('sim-button');
    if (simButton) simButton.style.background = button;
}

async function guardarColores() {
    const colores = {
        color_app_bg: document.getElementById('color_app_bg').value,
        color_primario: document.getElementById('color_primario').value,
        color_secundario: document.getElementById('color_secundario').value,
        color_header_text: document.getElementById('color_header_text').value,
        color_button: document.getElementById('color_button').value,
        color_button_hover: document.getElementById('color_button_hover').value,
        color_success: document.getElementById('color_success').value,
        color_warning: document.getElementById('color_warning').value,
        color_danger: document.getElementById('color_danger').value,
        color_info: document.getElementById('color_info').value
    };
    
    try {
        const response = await fetch(`${API_URL}/empresas/${empresaId}/colores`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(colores)
        });
        
        if (response.ok) {
            alert('✅ Colores guardados exitosamente');
        } else {
            alert('❌ Error al guardar colores');
        }
    } catch (error) {
        console.error('Error:', error);
        alert('❌ Error de conexión');
    }
}
