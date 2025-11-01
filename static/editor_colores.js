const API_URL = 'http://192.168.1.23:5001/api';
let empresaId = null;
let plantillaActual = null;
let plantillaOriginal = null;
let hayCambiosSinGuardar = false;

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
        
        // FORMATO NUEVO: meta.icon, meta.description, name
        const icon = p.meta?.icon || p.icon || '🎨';
        const nombre = p.name || p.nombre || 'Plantilla';
        const descripcion = p.meta?.description || p.descripcion || p.desc || '';
        
        item.innerHTML = `
            <div class="plantilla-icon">${icon}</div>
            <div class="plantilla-info">
                <div class="nombre">${nombre}</div>
                <div class="desc">${descripcion}</div>
            </div>
        `;
        list.appendChild(item);
    });
}

async function cargarEmpresa() {
    try {
        const response = await fetch(`${API_URL}/empresas/${empresaId}`, {
            credentials: 'include',
            headers: {
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            }
        });
        
        if (!response.ok) {
            console.error('Error en respuesta:', response.status, response.statusText);
            throw new Error(`Error ${response.status}: ${response.statusText}`);
        }
        
        const contentType = response.headers.get('content-type');
        if (!contentType || !contentType.includes('application/json')) {
            console.error('Respuesta no es JSON:', contentType);
            const text = await response.text();
            console.error('Contenido recibido:', text.substring(0, 200));
            throw new Error('La respuesta del servidor no es JSON válido');
        }
        
        const empresa = await response.json();
        console.log('✅ Empresa cargada:', empresa);
        
        renderizarContentPanel(empresa);
        cargarColoresActuales(empresa);
        aplicarEstilosDePlantilla(empresa);
        
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
        
        <div class="instrucciones-plantillas">
            <div class="instruccion-card">
                <i class="fas fa-palette fa-3x"></i>
                <h3>Selecciona una Plantilla</h3>
                <p>Utiliza el panel lateral para elegir una de las plantillas prediseñadas disponibles.</p>
                <p><strong>Las plantillas incluyen todos los colores y estilos necesarios para tu aplicación.</strong></p>
                <div class="plantillas-info">
                    <div class="plantilla-desc">
                        <i class="fas fa-sun"></i>
                        <strong>Minimal:</strong> Diseño minimalista blanco y negro
                    </div>
                    <div class="plantilla-desc">
                        <i class="fas fa-moon"></i>
                        <strong>Dark:</strong> Tema oscuro para reducir fatiga visual
                    </div>
                    <div class="plantilla-desc">
                        <i class="fas fa-book"></i>
                        <strong>EInk:</strong> Colores cálidos inspirados en papel
                    </div>
                </div>
            </div>
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

function aplicarEstilosDePlantilla(empresa) {
    // Aplicar estilos de la plantilla directamente al editor
    console.log('🎨 [EDITOR] Aplicando estilos de plantilla...');
    
    if (!empresa) return;
    
    // Crear/actualizar elemento de estilo
    let styleEl = document.getElementById('editor-plantilla-styles');
    if (styleEl) styleEl.remove();
    
    styleEl = document.createElement('style');
    styleEl.id = 'editor-plantilla-styles';
    document.head.appendChild(styleEl);
    
    const bg = empresa.color_app_bg || '#ffffff';
    const text = empresa.color_grid_text || '#333333';
    const cardBg = empresa.color_secundario || '#f5f5f5';
    const headerBg = empresa.color_header_bg || '#2c3e50';
    const headerText = empresa.color_header_text || '#ffffff';
    
    styleEl.textContent = `
        /* Ocultar DOCTYPE si aparece */
        body::before {
            content: none !important;
        }
        
        /* Fondo general */
        html, body {
            background-color: ${bg} !important;
            color: ${text} !important;
            margin: 0 !important;
            padding: 0 !important;
        }
        
        /* Header */
        .header {
            background-color: ${headerBg} !important;
            color: ${headerText} !important;
        }
        
        .header h1, .header * {
            color: ${headerText} !important;
        }
        
        /* Main container y scrollable content */
        .main-container,
        .scrollable-content,
        .content-wrapper {
            background-color: ${bg} !important;
        }
        
        /* Content panel (zona blanca) - MUY IMPORTANTE */
        #content-panel,
        .content-panel,
        .color-editors {
            background-color: ${bg} !important;
            color: ${text} !important;
        }
        
        /* Sidebar */
        .sidebar, #sidebar {
            background-color: ${cardBg} !important;
            color: ${text} !important;
        }
        
        .sidebar h2, .sidebar h3 {
            color: ${text} !important;
        }
        
        /* Acordeones */
        .accordion-section {
            background-color: ${cardBg} !important;
            border-color: ${empresa.color_input_border || '#ddd'} !important;
        }
        
        .accordion-header {
            background-color: ${headerBg} !important;
            color: ${headerText} !important;
        }
        
        .accordion-header span,
        .accordion-header i {
            color: ${headerText} !important;
        }
        
        .accordion-content {
            background-color: ${cardBg} !important;
        }
        
        /* Color grid */
        .color-grid {
            background-color: ${cardBg} !important;
        }
        
        .color-input-group {
            background-color: ${bg} !important;
        }
        
        /* Labels y textos */
        label, p, h3, h5, span:not(.color-value) {
            color: ${text} !important;
        }
        
        /* Inputs */
        input[type="text"],
        input[type="color"],
        input[type="checkbox"] {
            background-color: ${empresa.color_input_bg || '#fff'} !important;
            color: ${empresa.color_input_text || '#333'} !important;
            border-color: ${empresa.color_input_border || '#ccc'} !important;
        }
        
        /* Botón guardar */
        .save-button {
            background-color: ${empresa.color_button || '#3498db'} !important;
            color: ${empresa.color_button_text || '#fff'} !important;
        }
        
        .save-button:hover {
            background-color: ${empresa.color_button_hover || '#2980b9'} !important;
        }
        
        /* Plantilla items */
        .plantilla-item {
            background-color: ${bg} !important;
            border-color: ${empresa.color_input_border || '#ddd'} !important;
        }
        
        .plantilla-item:hover {
            background-color: ${cardBg} !important;
        }
        
        .plantilla-item.active {
            background-color: ${empresa.color_button || '#3498db'} !important;
            color: ${empresa.color_button_text || '#fff'} !important;
        }
        
        /* Plantilla activa */
        .plantilla-activa {
            background-color: ${cardBg} !important;
            color: ${text} !important;
        }
    `;
    
    console.log('✅ [EDITOR] Estilos aplicados:', {
        fondo: bg,
        texto: text,
        tarjetas: cardBg
    });
}


async function seleccionarPlantilla(nombre) {
    // Obtener nombre descriptivo (formato nuevo usa .name, antiguo .nombre)
    const nombreDescriptivo = PLANTILLAS[nombre].name || PLANTILLAS[nombre].nombre || nombre;
    
    // Mostrar spinner
    mostrarSpinnerAplicando(nombreDescriptivo);
    
    document.querySelectorAll('.plantilla-item').forEach(item => item.classList.remove('active'));
    document.querySelector(`[data-plantilla="${nombre}"]`).classList.add('active');
    
    plantillaActual = nombre;
    plantillaOriginal = nombre;
    document.getElementById('plantilla-activa-nombre').textContent = nombreDescriptivo;
    
    // NUEVO: Cargar y aplicar el tema usando branding.js
    console.log(`🎨 [PLANTILLA] Cargando JSON de plantilla: ${nombre}`);
    try {
        const response = await fetch(`/static/plantillas/${nombre}.json`, { cache: 'no-cache' });
        if (response.ok) {
            const themeJson = await response.json();
            console.log(`🎨 [PLANTILLA] Aplicando tema en el editor: ${themeJson.name}`);
            
            // Aplicar tema en el documento actual del editor
            if (typeof applyTheme === 'function') {
                await applyTheme(themeJson);
            }
            
            // También aplicar al parent (si existe)
            if (window.parent && typeof window.parent.applyTheme === 'function') {
                console.log(`🎨 [PLANTILLA] Aplicando tema al parent también`);
                await window.parent.applyTheme(themeJson);
            }
        }
    } catch (error) {
        console.error(`❌ [PLANTILLA] Error cargando JSON:`, error);
    }
    
    // Guardar el KEY de la plantilla en BD (minimal, dark, eink)
    console.log(`🎨 [PLANTILLA] Guardando key: "${nombre}"`);
    await guardarNombrePlantilla(nombre); // <- ENVIAR KEY (minimal, dark, eink)
    
    // Ocultar spinner
    ocultarSpinnerAplicando();
    console.log(`✅ [PLANTILLA] Plantilla aplicada y guardada`);
}

async function guardarNombrePlantilla(nombrePlantilla) {
    try {
        const response = await fetch(`${API_URL}/empresas/${empresaId}/colores`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                plantilla_personalizada: nombrePlantilla
            })
        });
        
        if (response.ok) {
            const data = await response.json();
            console.log(`✅ [PLANTILLA] Backend devolvió:`, data);
            console.log(`✅ [PLANTILLA] data.success:`, data.success);
            console.log(`✅ [PLANTILLA] data.plantilla:`, data.plantilla);
            console.log(`✅ [PLANTILLA] data.colores exists:`, !!data.colores);
            
            // Backend devuelve el JSON nuevo (design tokens)
            if (data.colores && window.parent && window.parent.applyTheme) {
                console.log('[PLANTILLA] ✅ Aplicando tema desde respuesta del backend...');
                console.log('[PLANTILLA] JSON recibido:', data.colores.name);
                await window.parent.applyTheme(data.colores);
            } else {
                console.warn('[PLANTILLA] ⚠️ applyTheme no disponible, usando fallback');
                if (window.parent && window.parent.cargarColoresEmpresa) {
                    console.log('[PLANTILLA] Recargando estilos (fallback)...');
                    await window.parent.cargarColoresEmpresa();
                }
            }
        } else {
            const error = await response.text();
            console.error('❌ Error al guardar nombre de plantilla:', error);
        }
    } catch (error) {
        console.error('❌ Error al guardar nombre de plantilla:', error);
    }
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
    console.log(`🎨 [DEBUG] Aplicando plantilla "${nombre}":`);
    console.log(`🎨 [DEBUG] color_grid_header_text en plantilla:`, plantilla.color_grid_header_text);
    
    Object.keys(plantilla).forEach(key => {
        if (key !== 'nombre' && key !== 'desc' && key !== 'icon') {
            const input = document.getElementById(key);
            if (input) {
                input.value = plantilla[key];
                const valueSpan = document.getElementById(`${key}-value`);
                if (valueSpan) valueSpan.textContent = plantilla[key];
            } else if (key === 'color_grid_header_text') {
                console.log(`❌ [DEBUG] Input NO encontrado para: ${key}`);
            }
        }
    });
    
    // Verificar que se aplicó correctamente
    const inputTest = document.getElementById('color_grid_header_text');
    if (inputTest) {
        console.log(`✅ [DEBUG] color_grid_header_text input value después:`, inputTest.value);
    }
    
    // Aplicar estilos visualmente a la página
    aplicarEstilosDePlantilla(plantilla);
    
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

