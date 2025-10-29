const API_URL = 'http://192.168.1.23:5001/api';
let empresaId = null;
let plantillaActual = null;

// Plantillas cargadas dinámicamente desde plantillas.js
let PLANTILLAS = {};

// Cargar plantillas al inicio
async function cargarPlantillasEditor() {
    console.log('📦 Cargando plantillas en editor...');
    if (typeof window.cargarPlantillas === 'function') {
        const plantillasCargadas = await window.cargarPlantillas();
        PLANTILLAS = plantillasCargadas || window.plantillasColores || {};
        console.log('✅ Plantillas cargadas:', Object.keys(PLANTILLAS));
        console.log('📊 Total plantillas disponibles:', Object.keys(PLANTILLAS).length);
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
    inicializarAcordeones();
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
        
        
        <div class="color-editors">
            <h3><i class="fas fa-paint-brush"></i> Personalizar Colores</h3>
            <p><i class="fas fa-info-circle"></i> Haz clic en cada categoría para expandir/contraer</p>
            
            <!-- Acordeón 1: Colores Principales -->
            <div class="accordion-section active">
                <div class="accordion-header">
                    <span><i class="fas fa-palette"></i> Colores Principales</span>
                    <i class="fas fa-chevron-up"></i>
                </div>
                <div class="accordion-content">
                    <div class="color-grid">
                        ${crearInputColor('color_app_bg', 'Fondo App', '#ffffff')}
                        ${crearInputColor('color_primario', 'Menú Lateral', '#2c3e50')}
                        ${crearInputColor('color_secundario', 'Tarjetas', '#3498db')}
                        ${crearInputColor('color_header_text', 'Texto Menú', '#ffffff')}
                        ${crearInputColor('color_header_bg', 'Header Panel', '#2c3e50')}
                    </div>
                </div>
            </div>
            
            <!-- Acordeón 2: Botones -->
            <div class="accordion-section">
                <div class="accordion-header">
                    <span><i class="fas fa-square"></i> Botones</span>
                    <i class="fas fa-chevron-down"></i>
                </div>
                <div class="accordion-content">
                    <div class="color-grid">
                        ${crearInputColor('color_button', 'Botón Normal', '#3498db')}
                        ${crearInputColor('color_button_hover', 'Botón Hover', '#2980b9')}
                        ${crearInputColor('color_button_text', 'Texto Botón', '#ffffff')}
                    </div>
                </div>
            </div>
            
            <!-- Acordeón 3: Notificaciones -->
            <div class="accordion-section">
                <div class="accordion-header">
                    <span><i class="fas fa-bell"></i> Notificaciones y Alertas</span>
                    <i class="fas fa-chevron-down"></i>
                </div>
                <div class="accordion-content">
                    <div class="color-grid">
                        ${crearInputColor('color_success', 'Éxito', '#27ae60')}
                        ${crearInputColor('color_warning', 'Advertencia', '#f39c12')}
                        ${crearInputColor('color_danger', 'Peligro', '#e74c3c')}
                        ${crearInputColor('color_info', 'Info', '#3498db')}
                    </div>
                </div>
            </div>
            
            <!-- Acordeón 4: Tablas y Grids -->
            <div class="accordion-section">
                <div class="accordion-header">
                    <span><i class="fas fa-table"></i> Tablas y Grids</span>
                    <i class="fas fa-chevron-down"></i>
                </div>
                <div class="accordion-content">
                    <div class="color-grid">
                        ${crearInputColor('color_grid_header', 'Encabezado Grid', '#34495e')}
                        ${crearInputColor('color_grid_header_text', 'Texto Encabezado', '#ffffff')}
                        ${crearInputColor('color_grid_text', 'Texto Grid', '#333333')}
                        ${crearInputColor('color_grid_bg', 'Fondo Grid', '#ffffff')}
                    </div>
                    <h5 style="margin: 1.5rem 0 1rem 0; color: #667eea; font-size: 0.9rem;">Hover Fila</h5>
                    <div class="color-grid">
                        ${crearInputColor('color_grid_hover', 'Color Hover', '#f5f5f5')}
                    </div>
                    <h5 style="margin: 1.5rem 0 1rem 0; color: #667eea; font-size: 0.9rem;">Celdas con Iconos</h5>
                    <div class="color-grid">
                        ${crearInputColor('color_icon_cell_bg', 'Fondo Celda Icono', '#f8f9fa')}
                    </div>
                </div>
            </div>
            
            <!-- Acordeón 5: Formularios -->
            <div class="accordion-section">
                <div class="accordion-header">
                    <span><i class="fas fa-edit"></i> Formularios</span>
                    <i class="fas fa-chevron-down"></i>
                </div>
                <div class="accordion-content">
                    <h5 style="margin: 0 0 1rem 0; color: #667eea; font-size: 0.9rem;">Labels</h5>
                    <div class="color-grid">
                        ${crearInputColor('color_label', 'Color Labels', '#333333')}
                    </div>
                    
                    <h5 style="margin: 1.5rem 0 1rem 0; color: #667eea; font-size: 0.9rem;">Inputs de Texto</h5>
                    <div class="color-grid">
                        ${crearInputColor('color_input_bg', 'Fondo Input', '#ffffff')}
                        ${crearInputColor('color_input_text', 'Texto Input', '#333333')}
                        ${crearInputColor('color_input_border', 'Borde Input', '#cccccc')}
                    </div>
                    
                    <h5 style="margin: 1.5rem 0 1rem 0; color: #667eea; font-size: 0.9rem;">Selects / Desplegables</h5>
                    <div class="color-grid">
                        ${crearInputColor('color_select_bg', 'Fondo Select', '#ffffff')}
                        ${crearInputColor('color_select_text', 'Texto Select', '#333333')}
                        ${crearInputColor('color_select_border', 'Borde Select', '#cccccc')}
                    </div>
                    
                    <h5 style="margin: 1.5rem 0 1rem 0; color: #667eea; font-size: 0.9rem;">Estados Deshabilitados</h5>
                    <div class="color-grid">
                        ${crearInputColor('color_disabled_bg', 'Fondo Deshabilitado', '#f5f5f5')}
                        ${crearInputColor('color_disabled_text', 'Texto Deshabilitado', '#9ca3af')}
                    </div>
                </div>
            </div>
            
            <!-- Acordeón 6: Iconos -->
            <div class="accordion-section">
                <div class="accordion-header">
                    <span><i class="fas fa-icons"></i> Iconos</span>
                    <i class="fas fa-chevron-down"></i>
                </div>
                <div class="accordion-content">
                    <div class="color-grid">
                        ${crearInputColor('color_icon', 'Color Iconos', '#666666')}
                    </div>
                </div>
            </div>
            
            <!-- Acordeón 7: Menú Lateral -->
            <div class="accordion-section">
                <div class="accordion-header">
                    <span><i class="fas fa-bars"></i> Menú Lateral</span>
                    <i class="fas fa-chevron-down"></i>
                </div>
                <div class="accordion-content">
                    <h5 style="margin: 1rem 0 1rem 0; color: #667eea; font-size: 0.9rem;">Fondo y Texto</h5>
                    <div class="color-grid">
                        ${crearInputColor('color_submenu_bg', 'Fondo Menú', '#ffffff')}
                        ${crearInputColor('color_submenu_text', 'Texto Menú', '#000000')}
                    </div>
                    <h5 style="margin: 1.5rem 0 1rem 0; color: #667eea; font-size: 0.9rem;">Interacción</h5>
                    <div class="color-grid">
                        ${crearInputColor('color_submenu_hover', 'Color Hover', '#f5f5f5')}
                    </div>
                </div>
            </div>
            
            <!-- Acordeón 8: Modales -->
            <div class="accordion-section">
                <div class="accordion-header">
                    <span><i class="fas fa-window-restore"></i> Modales y Diálogos</span>
                    <i class="fas fa-chevron-down"></i>
                </div>
                <div class="accordion-content">
                    <div class="color-grid">
                        ${crearInputColor('color_modal_bg', 'Fondo Modal', '#ffffff')}
                        ${crearInputColor('color_modal_text', 'Texto Modal', '#333333')}
                        ${crearInputColor('color_modal_border', 'Borde Modal', '#cccccc')}
                        ${crearInputColor('color_modal_overlay', 'Overlay Fondo', 'rgba(0,0,0,0.5)')}
                        ${crearInputColor('color_modal_shadow', 'Sombra Modal', 'rgba(0,0,0,0.3)')}
                    </div>
                </div>
            </div>
            
            <!-- Acordeón 9: Opciones Avanzadas -->
            <div class="accordion-section">
                <div class="accordion-header">
                    <span><i class="fas fa-cog"></i> Opciones Avanzadas</span>
                    <i class="fas fa-chevron-down"></i>
                </div>
                <div class="accordion-content">
                    <div class="color-grid" style="margin-bottom: 1.5rem;">
                        ${crearInputColor('color_spinner_border', 'Borde Spinner', '#3b82f6')}
                    </div>
                    <div style="padding: 1rem 0;">
                        <label style="display: flex; align-items: center; gap: 0.75rem; cursor: pointer;">
                            <input type="checkbox" id="grid_cell_borders" checked style="width: 20px; height: 20px; cursor: pointer;">
                            <span style="font-size: 1rem; color: #333;">Mostrar bordes en celdas de tabla</span>
                        </label>
                    </div>
                </div>
            </div>
            
            <button class="save-button">
                <i class="fas fa-save"></i> Guardar Cambios
            </button>
        </div>
    `;
}

function crearInputColor(id, label, defaultValue) {
    return `
        <div class="color-input-group">
            <label>${label}</label>
            <input type="color" id="${id}" value="${defaultValue}">
            <span class="color-value" id="${id}-value">${defaultValue}</span>
        </div>
    `;
}

function cargarColoresActuales(empresa) {
    const campos = ['color_app_bg', 'color_primario', 'color_secundario', 'color_header_text', 'color_header_bg', 'color_button', 'color_button_hover', 'color_button_text', 'color_success', 'color_warning', 'color_danger', 'color_info', 'color_grid_header', 'color_grid_text', 'color_grid_hover', 'color_grid_bg', 'color_icon', 'color_icon_cell_bg', 'color_label', 'color_input_bg', 'color_input_text', 'color_input_border', 'color_select_bg', 'color_select_text', 'color_select_border', 'color_disabled_bg', 'color_disabled_text', 'color_submenu_bg', 'color_submenu_text', 'color_submenu_hover', 'color_modal_bg', 'color_modal_text', 'color_modal_border', 'color_modal_overlay', 'color_modal_shadow', 'color_spinner_border'];
    
    campos.forEach(campo => {
        const input = document.getElementById(campo);
        if (input && empresa[campo]) {
            input.value = empresa[campo];
            const valueSpan = document.getElementById(`${campo}-value`);
            if (valueSpan) valueSpan.textContent = empresa[campo];
        }
    });
    
    // Actualizar preview después de cargar colores de la empresa
    if (typeof window.actualizarPreview === 'function') {
        window.actualizarPreview();
        console.log('✅ Preview actualizado con colores de la empresa');
    }
}

async function seleccionarPlantilla(nombre) {
    // Mostrar spinner
    mostrarSpinnerAplicando(PLANTILLAS[nombre].nombre);
    
    document.querySelectorAll('.plantilla-item').forEach(item => item.classList.remove('active'));
    document.querySelector(`[data-plantilla="${nombre}"]`).classList.add('active');
    
    plantillaActual = nombre;
    plantillaOriginal = nombre;
    document.getElementById('plantilla-activa-nombre').textContent = PLANTILLAS[nombre].nombre;
    
    // Aplicar plantilla a los inputs
    aplicarPlantilla(nombre);
    
    // Guardar automáticamente en la BD
    console.log(`🎨 [PLANTILLA] Aplicando "${PLANTILLAS[nombre].nombre}" en tiempo real...`);
    await guardarColores();
    
    // Esperar un poco para que plantilla_sync.js detecte el cambio
    await new Promise(resolve => setTimeout(resolve, 3000));
    
    // Ocultar spinner
    ocultarSpinnerAplicando();
    console.log(`✅ [PLANTILLA] Plantilla aplicada y guardada`);
}

function mostrarSpinnerAplicando(nombrePlantilla) {
    // Crear overlay con spinner si no existe
    let overlay = document.getElementById('spinner-overlay');
    if (!overlay) {
        overlay = document.createElement('div');
        overlay.id = 'spinner-overlay';
        overlay.innerHTML = `
            <div class="spinner-container">
                <div class="spinner"></div>
                <div class="spinner-text">
                    <div style="font-size: 1.2rem; font-weight: 600; margin-bottom: 0.5rem;">
                        Aplicando plantilla...
                    </div>
                    <div id="spinner-plantilla-nombre" style="font-size: 0.9rem; opacity: 0.8;">
                        ${nombrePlantilla}
                    </div>
                </div>
            </div>
        `;
        document.body.appendChild(overlay);
    } else {
        document.getElementById('spinner-plantilla-nombre').textContent = nombrePlantilla;
    }
    overlay.style.display = 'flex';
}

function ocultarSpinnerAplicando() {
    const overlay = document.getElementById('spinner-overlay');
    if (overlay) {
        overlay.style.display = 'none';
    }
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
    
    // NO actualizar preview - aplicamos directamente
    console.log(`🔄 [PLANTILLA] Colores aplicados a inputs: ${plantilla.nombre || nombre}`);
}




// ===== FUNCIÓN ACORDEONES =====

function inicializarAcordeones() {
    setTimeout(() => {
        const primeraSeccion = document.querySelector('.accordion-section.active');
        if (primeraSeccion) {
            const content = primeraSeccion.querySelector('.accordion-content');
            if (content) {
                content.style.maxHeight = content.scrollHeight + 50 + 'px';
            }
        }
    }, 300);
}


function toggleAccordion(header) {
    const section = header.parentElement;
    const content = section.querySelector('.accordion-content');
    const icon = header.querySelector('.fa-chevron-down, .fa-chevron-up');
    
    // Cerrar otros acordeones (opcional - comentar si quieres múltiples abiertos)
    // document.querySelectorAll('.accordion-section.active').forEach(s => {
    //     if (s !== section) {
    //         s.classList.remove('active');
    //         const otherContent = s.querySelector('.accordion-content');
    //         const otherIcon = s.querySelector('.fa-chevron-down, .fa-chevron-up');
    //         otherContent.style.maxHeight = '0';
    //         otherIcon.classList.remove('fa-chevron-up');
    //         otherIcon.classList.add('fa-chevron-down');
    //     }
    // });
    
    // Toggle actual
    section.classList.toggle('active');
    
    if (section.classList.contains('active')) {
        content.style.maxHeight = content.scrollHeight + 50 + 'px';
        icon.classList.remove('fa-chevron-down');
        icon.classList.add('fa-chevron-up');
    } else {
        content.style.maxHeight = '0';
        icon.classList.remove('fa-chevron-up');
        icon.classList.add('fa-chevron-down');
    }
}


// ===== FUNCIONES V2 MEJORADAS =====

function detectarCambiosPlantilla() {
    if (plantillaOriginal === 'custom') return false;
    
    const plantilla = PLANTILLAS[plantillaOriginal];
    if (!plantilla) return false;
    
    const campos = Object.keys(plantilla).filter(k => k.startsWith('color_'));
    
    return campos.some(campo => {
        const input = document.getElementById(campo);
        return input && input.value.toUpperCase() !== plantilla[campo].toUpperCase();
    });
}

async function guardarColores() {
    try {
        const huboChange = detectarCambiosPlantilla();
        let nombrePersonalizado = null;
        
        // Si hay cambios, guardar automáticamente como plantilla personalizada
        if (huboChange && plantillaOriginal && plantillaOriginal !== 'custom') {
            const plantillaBase = PLANTILLAS[plantillaOriginal]?.nombre || plantillaOriginal;
            const timestamp = new Date().toISOString().slice(0, 16).replace('T', ' ');
            nombrePersonalizado = `${plantillaBase} (${timestamp})`;
            console.log(`✅ Guardando como plantilla personalizada: ${nombrePersonalizado}`);
        }
        
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
            color_grid_header_text: document.getElementById('color_grid_header_text').value,
            color_grid_header: document.getElementById('color_grid_header').value,
            color_grid_text: document.getElementById('color_grid_text').value,
            color_grid_bg: document.getElementById('color_grid_bg').value,
            color_grid_hover: document.getElementById('color_grid_hover').value,
            color_icon_cell_bg: document.getElementById('color_icon_cell_bg').value,
            color_icon: document.getElementById('color_icon').value,
            color_label: document.getElementById('color_label').value,
            color_input_bg: document.getElementById('color_input_bg').value,
            color_input_text: document.getElementById('color_input_text').value,
            color_input_border: document.getElementById('color_input_border').value,
            color_select_bg: document.getElementById('color_select_bg').value,
            color_select_text: document.getElementById('color_select_text').value,
            color_select_border: document.getElementById('color_select_border').value,
            color_submenu_bg: document.getElementById('color_submenu_bg').value,
            color_submenu_text: document.getElementById('color_submenu_text').value,
            color_submenu_hover: document.getElementById('color_submenu_hover').value,
            color_modal_bg: document.getElementById('color_modal_bg').value,
            color_modal_text: document.getElementById('color_modal_text').value,
            color_modal_border: document.getElementById('color_modal_border').value,
            color_disabled_bg: document.getElementById('color_disabled_bg').value,
            color_disabled_text: document.getElementById('color_disabled_text').value,
            color_modal_overlay: document.getElementById('color_modal_overlay').value,
            color_modal_shadow: document.getElementById('color_modal_shadow').value,
            color_spinner_border: document.getElementById('color_spinner_border').value,
            grid_cell_borders: document.getElementById('grid_cell_borders').checked ? 'true' : 'false',
            plantilla_personalizada: nombrePersonalizado
        };
        
        const response = await fetch(`${API_URL}/empresas/${empresaId}/colores`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(colores)
        });
        
        if (response.ok) {
            
            // Si hay cambios y se generó nombre personalizado, guardar plantilla
            if (nombrePersonalizado && typeof window.guardarPlantillaPersonalizada === 'function') {
                try {
                    const resultado = await window.guardarPlantillaPersonalizada(
                        colores,
                        plantillaOriginal,
                        nombrePersonalizado
                    );
                    console.log('✅ Plantilla personalizada guardada:', resultado.nombre_plantilla);
                    
                    // Recargar plantillas
                    if (typeof window.cargarPlantillas === 'function') {
                        await window.cargarPlantillas();
                        window.PLANTILLAS = window.plantillasColores;
                        renderizarSidebar(); // Actualizar UI del sidebar
                    }
                    
                    plantillaActual = resultado.nombre_archivo;
                    plantillaOriginal = resultado.nombre_archivo;
                    coloresOriginales = {...colores};
                    actualizarPlantillaActiva(resultado.nombre_archivo, nombrePersonalizado);
                    
                    console.log(`✅ Colores guardados y plantilla personalizada creada: "${nombrePersonalizado}"`);
                } catch (errorPlantilla) {
                    console.error('❌ Error guardando plantilla:', errorPlantilla);
                    console.warn('✅ Colores guardados, pero hubo un error al crear la plantilla personalizada');
                }
            } else {
                console.log('✅ Colores guardados correctamente');
            }
        } else {
            const error = await response.text();
            console.error('❌ Error al guardar colores:', error);
        }
        
    } catch (error) {
        console.error('❌ Error al guardar colores:', error);
    }
}

// ===== SISTEMA DE AUTO-GUARDADO EN TIEMPO REAL =====

let autoSaveTimeout = null;
let haycambiosSinGuardar = false;

function inicializarAutoGuardado() {
    // Agregar event listeners a todos los inputs de color
    const inputs = document.querySelectorAll('input[type="color"]');
    
    inputs.forEach(input => {
        input.addEventListener('input', (e) => {
            hayCambiosSinGuardar = true;
            
            // Debounce: esperar 500ms después del último cambio antes de guardar
            if (autoSaveTimeout) {
                clearTimeout(autoSaveTimeout);
            }
            
            autoSaveTimeout = setTimeout(async () => {
                console.log('🎨 [AUTO-SAVE] Cambio detectado, guardando...');
                await guardarColores();
                console.log('✅ [AUTO-SAVE] Guardado automático completado');
            }, 500);
        });
    });
    
    console.log(`✅ [AUTO-SAVE] Sistema inicializado en ${inputs.length} inputs`);
}

// Preguntar al salir si guardar como personalizada
function configurarSalidaEditor() {
    window.addEventListener('beforeunload', (e) => {
        // Solo preguntar si hay cambios y no es una plantilla personalizada ya guardada
        if (hayCambiosSinGuardar && plantillaOriginal && !plantillaOriginal.startsWith('personalizada_')) {
            e.preventDefault();
            e.returnValue = '¿Deseas guardar estos cambios como una plantilla personalizada?';
            return e.returnValue;
        }
    });
}

// Inicializar cuando el DOM esté listo
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        setTimeout(() => {
            inicializarAutoGuardado();
            configurarSalidaEditor();
        }, 1000);
    });
} else {
    setTimeout(() => {
        inicializarAutoGuardado();
        configurarSalidaEditor();
    }, 1000);
}

