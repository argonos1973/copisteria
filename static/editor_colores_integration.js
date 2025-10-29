// Integración del Preview Compacto y Guardar Plantillas Personalizadas
// Este archivo extiende la funcionalidad del editor_colores.js

// Inicializar preview compacto cuando cargue el editor
(function() {
    const originalDOMContentLoaded = window.addEventListener;
    
    // Esperar a que el DOM esté listo y el editor_colores.js haya cargado
    setTimeout(() => {
    agregarEventListenersColores();
        if (typeof inicializarPreviewCompacto === 'function') {
            window.previewCompacto = inicializarPreviewCompacto('preview-compacto-container');
            console.log('✅ Preview compacto inicializado');
        }
    }, 500);
})();

// Sobrescribir la función actualizarPreview original para incluir el preview compacto
const actualizarPreviewOriginal = window.actualizarPreview;

window.actualizarPreview = function() {
    // Llamar a la función original
    if (typeof actualizarPreviewOriginal === 'function') {
        actualizarPreviewOriginal();
    }
    
    // Actualizar el preview compacto
    if (window.previewCompacto) {
        const colores = obtenerColoresActuales();
        window.previewCompacto.actualizar(colores);
    }
};

// Función para obtener todos los colores actuales del formulario
function obtenerColoresActuales() {
    const colores = {};
    
    const campos = [
        'color_primario', 'color_secundario', 'color_success', 'color_warning',
        'color_danger', 'color_info', 'color_button', 'color_button_hover',
        'color_button_text', 'color_app_bg', 'color_header_bg', 'color_header_text',
        'color_grid_header', 'color_grid_header_text', 'color_grid_hover', 'color_grid_bg', 'color_grid_text',
        'color_input_bg', 'color_input_text', 'color_input_border',
        'color_select_bg', 'color_select_text', 'color_select_border',
        'color_disabled_bg', 'color_disabled_text',
        'color_submenu_bg', 'color_submenu_text', 'color_submenu_hover',
        'color_modal_bg', 'color_modal_text', 'color_modal_border',
        'color_disabled_bg', 'color_disabled_text', 'color_modal_overlay', 'color_modal_shadow', 'color_spinner_border',
        'color_icon', 'color_spinner_border'
    ];
    
    campos.forEach(campo => {
        const elemento = document.getElementById(campo);
        if (elemento) {
            colores[campo] = elemento.value;
        }
    });
    
    return colores;
}

window.obtenerColoresActuales = obtenerColoresActuales;

// Agregar el botón cuando se renderice el panel de contenido
setTimeout(() => {
    agregarEventListenersColores();
    agregarEventListenersAcordeones();
    agregarEventListenerGuardar();
    
    // También actualizar el preview inicial si ya hay colores cargados
    if (window.previewCompacto) {
        const colores = obtenerColoresActuales();
        if (Object.keys(colores).length > 0) {
            window.previewCompacto.actualizar(colores);
        }
    }
}, 1000);

console.log('✅ Editor Colores Integration cargado');

// Agregar event listeners a todos los inputs de color (sin onchange inline)
function agregarEventListenersColores() {
    const colorInputs = document.querySelectorAll('input[type="color"]');
    
    colorInputs.forEach(input => {
        // Eliminar listener previo si existe
        input.removeEventListener('change', handleColorChange);
        // Agregar nuevo listener
        input.addEventListener('change', handleColorChange);
    });
    
    console.log(`✅ ${colorInputs.length} event listeners agregados a inputs de color`);
}

// Handler para cambios de color
function handleColorChange(event) {
    const colorId = event.target.id;
    const newValue = event.target.value;
    
    // Actualizar el span que muestra el valor
    const valueSpan = document.getElementById(`${colorId}-value`);
    if (valueSpan) {
        valueSpan.textContent = newValue;
    }
    
    // Actualizar preview compacto
    if (window.actualizarPreview && typeof window.actualizarPreview === 'function') {
        window.actualizarPreview();
    }
}

// Exportar
window.agregarEventListenersColores = agregarEventListenersColores;
window.handleColorChange = handleColorChange;


// Agregar event listeners a los acordeones (sin onclick inline)
function agregarEventListenersAcordeones() {
    const headers = document.querySelectorAll('.accordion-header');
    
    headers.forEach(header => {
        // Eliminar listener previo si existe
        header.removeEventListener('click', handleAccordionClick);
        // Agregar nuevo listener
        header.addEventListener('click', handleAccordionClick);
    });
    
    console.log(`✅ ${headers.length} event listeners agregados a acordeones`);
}

// Handler para clicks en acordeones
function handleAccordionClick(event) {
    const header = event.currentTarget;
    if (typeof toggleAccordion === 'function') {
        toggleAccordion(header);
    }
}

// Exportar
window.agregarEventListenersAcordeones = agregarEventListenersAcordeones;
window.handleAccordionClick = handleAccordionClick;


// Agregar event listener al botón "Guardar Cambios" (sin onclick inline)
function agregarEventListenerGuardar() {
    const saveButton = document.querySelector('.save-button');
    
    if (saveButton) {
        // Eliminar listener previo si existe
        saveButton.removeEventListener('click', handleSaveClick);
        // Agregar nuevo listener
        saveButton.addEventListener('click', handleSaveClick);
        console.log('✅ Event listener agregado al botón "Guardar Cambios"');
    }
}

// Handler para click en guardar
function handleSaveClick(event) {
    event.preventDefault();
    if (typeof guardarColores === 'function') {
        guardarColores();
    }
}

// Exportar
window.agregarEventListenerGuardar = agregarEventListenerGuardar;
window.handleSaveClick = handleSaveClick;

