// modal_theme.js - Forzar aplicación de tema a modales

function applyThemeToModals() {
    // Obtener variables CSS computadas del root
    const root = document.documentElement;
    const style = getComputedStyle(root);
    
    // Leer las variables del tema actual
    const modalBg = style.getPropertyValue('--modal-bg').trim() || '#ffffff';
    const modalText = style.getPropertyValue('--modal-text').trim() || '#000000';
    const modalBorder = style.getPropertyValue('--modal-border').trim() || '#d4d4d4';
    const modalHeaderBg = style.getPropertyValue('--modal-header-bg').trim() || '#3498db';
    const modalHeaderText = style.getPropertyValue('--modal-header-text').trim() || '#ffffff';
    const modalBodyBg = style.getPropertyValue('--modal-body-bg').trim() || modalBg;
    const modalBodyText = style.getPropertyValue('--modal-body-text').trim() || modalText;
    const modalLabelColor = style.getPropertyValue('--modal-label-color').trim() || modalText;
    const modalInputBg = style.getPropertyValue('--modal-input-bg').trim() || '#ffffff';
    const modalInputText = style.getPropertyValue('--modal-input-text').trim() || modalText;
    const modalInputBorder = style.getPropertyValue('--modal-input-border').trim() || modalBorder;
    const buttonBg = style.getPropertyValue('--button-bg').trim() || '#6c757d';
    const buttonText = style.getPropertyValue('--button-text').trim() || '#ffffff';
    const buttonHoverBg = style.getPropertyValue('--button-hover-bg').trim() || '#5a6268';
    const tabActiveBg = style.getPropertyValue('--tab-active-bg').trim() || '#f5f5f5';
    const tabActiveText = style.getPropertyValue('--tab-active-text').trim() || '#000000';
    const tabInactiveText = style.getPropertyValue('--tab-inactive-text').trim() || '#999999';
    const tabBorder = style.getPropertyValue('--tab-border').trim() || '#000000';
    
    const temaActual = root.dataset.theme || 'unknown';
    
    // console.log('[MODAL_THEME] 🎨 Aplicando tema a modales...');
    // console.log('[MODAL_THEME] Tema activo:', temaActual);
    // console.log('[MODAL_THEME] Variables leídas:', {
        // modalBg,
        // modalText,
        // modalBorder,
        // modalHeaderBg,
        // modalHeaderText,
        // modalBodyBg,
        // modalInputBg,
        // buttonBg
    // });
    
    // MODAL DE PERFIL
    const modalPerfilContent = document.querySelector('.modal-perfil-content');
    if (modalPerfilContent) {
        // console.log('[MODAL_THEME] ✓ Aplicando a .modal-perfil-content:', modalBg);
        modalPerfilContent.style.setProperty('background-color', modalBg, 'important');
        modalPerfilContent.style.setProperty('color', modalText, 'important');
        // Borde blanco forzado
        modalPerfilContent.style.setProperty('border', '4px solid rgba(255, 255, 255, 0.8)', 'important');
    } else {
        // console.log('[MODAL_THEME] ⚠️ No se encontró .modal-perfil-content');
    }
    
    const modalPerfilHeader = document.querySelector('.modal-perfil-header');
    if (modalPerfilHeader) {
        // console.log('[MODAL_THEME] ✓ Aplicando a .modal-perfil-header:', modalHeaderBg);
        
        // Limpiar cualquier background previo
        modalPerfilHeader.style.removeProperty('background');
        modalPerfilHeader.style.removeProperty('background-image');
        
        // Aplicar nuevos estilos
        modalPerfilHeader.style.setProperty('background-color', modalHeaderBg, 'important');
        modalPerfilHeader.style.setProperty('background', modalHeaderBg, 'important');
        modalPerfilHeader.style.setProperty('color', modalHeaderText, 'important');
        
        const h2 = modalPerfilHeader.querySelector('h2');
        if (h2) {
            h2.style.setProperty('color', modalHeaderText, 'important');
        }
    } else {
        // console.log('[MODAL_THEME] ⚠️ No se encontró .modal-perfil-header');
    }
    
    const modalPerfilTabs = document.querySelector('.modal-perfil-tabs');
    if (modalPerfilTabs) {
        modalPerfilTabs.style.setProperty('background-color', modalBg, 'important');
        modalPerfilTabs.style.setProperty('border-bottom', `2px solid ${modalBorder}`, 'important');
    }
    
    // Aplicar a los contenidos de tabs
    document.querySelectorAll('.tab-content').forEach(tabContent => {
        tabContent.style.setProperty('background-color', modalBg, 'important');
        tabContent.style.setProperty('color', modalText, 'important');
    });
    
    // Aplicar a todos los labels
    document.querySelectorAll('.modal-perfil .form-group label').forEach(label => {
        label.style.setProperty('color', modalLabelColor, 'important');
        const icon = label.querySelector('i');
        if (icon) {
            icon.style.setProperty('color', modalHeaderBg, 'important');
        }
    });
    
    // Aplicar a todos los inputs
    document.querySelectorAll('.modal-perfil .form-group input').forEach(input => {
        input.style.setProperty('background-color', modalInputBg, 'important');
        input.style.setProperty('color', modalInputText, 'important');
        input.style.setProperty('border', `2px solid ${modalInputBorder}`, 'important');
    });
    
    // Aplicar a TODOS los botones guardar (azul uniforme)
    document.querySelectorAll('.btn-guardar').forEach(btnGuardar => {
        btnGuardar.style.setProperty('background-color', '#3498db', 'important');
        btnGuardar.style.setProperty('color', '#ffffff', 'important');
    });
    
    // MODAL DE AVATARES
    const modalAvataresContent = document.querySelector('.modal-avatares-content');
    if (modalAvataresContent) {
        modalAvataresContent.style.setProperty('background-color', modalBg, 'important');
        modalAvataresContent.style.setProperty('color', modalText, 'important');
        modalAvataresContent.style.setProperty('border', `1px solid ${modalBorder}`, 'important');
    }
    
    const modalAvataresHeader = document.querySelector('.modal-avatares-header');
    if (modalAvataresHeader) {
        // Limpiar cualquier background previo
        modalAvataresHeader.style.removeProperty('background');
        modalAvataresHeader.style.removeProperty('background-image');
        
        // Aplicar nuevos estilos
        modalAvataresHeader.style.setProperty('background-color', modalHeaderBg, 'important');
        modalAvataresHeader.style.setProperty('background', modalHeaderBg, 'important');
        modalAvataresHeader.style.setProperty('color', modalHeaderText, 'important');
        
        const h3 = modalAvataresHeader.querySelector('h3');
        if (h3) {
            h3.style.setProperty('color', modalHeaderText, 'important');
        }
        
        const closeBtn = modalAvataresHeader.querySelector('.modal-avatares-close');
        if (closeBtn) {
            closeBtn.style.setProperty('color', modalHeaderText, 'important');
        }
    }
    
    const modalAvataresBody = document.querySelector('.modal-avatares-body');
    if (modalAvataresBody) {
        modalAvataresBody.style.setProperty('background-color', modalBodyBg, 'important');
    }
    
    const modalAvataresTabs = document.querySelector('.modal-avatares-tabs');
    if (modalAvataresTabs) {
        modalAvataresTabs.style.setProperty('border-bottom', `2px solid ${modalBorder}`, 'important');
    }
    
    // Aplicar a botones de tabs de avatares
    document.querySelectorAll('.avatar-tab-btn').forEach(btn => {
        if (btn.classList.contains('active')) {
            btn.style.setProperty('background-color', tabActiveBg, 'important');
            btn.style.setProperty('color', tabActiveText, 'important');
            btn.style.setProperty('border', `2px solid ${tabBorder}`, 'important');
        } else {
            btn.style.setProperty('background-color', 'transparent', 'important');
            btn.style.setProperty('color', tabInactiveText, 'important');
            btn.style.setProperty('border', `1px solid ${modalBorder}`, 'important');
        }
    });
    
    // Aplicar a área de subir avatar
    const subirArea = document.querySelector('.subir-avatar-area');
    if (subirArea) {
        subirArea.style.setProperty('border', `2px dashed ${modalBorder}`, 'important');
        const icon = subirArea.querySelector('i');
        if (icon) {
            icon.style.setProperty('color', modalHeaderBg, 'important');
        }
    }
    
    const subirTexto = document.querySelector('.subir-avatar-text');
    if (subirTexto) {
        subirTexto.style.setProperty('color', modalBodyText, 'important');
    }
    
    const subirHint = document.querySelector('.subir-avatar-hint');
    if (subirHint) {
        subirHint.style.setProperty('color', modalText, 'important');
    }
    
    // console.log('[MODAL_THEME] ✅ Tema aplicado a modales');
}

// Aplicar cuando el DOM esté listo
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        setTimeout(applyThemeToModals, 200);
    });
} else {
    setTimeout(applyThemeToModals, 200);
}

// Observar cambios en el atributo data-theme del documento
const observer = new MutationObserver((mutations) => {
    mutations.forEach((mutation) => {
        if (mutation.type === 'attributes' && mutation.attributeName === 'data-theme') {
            // console.log('[MODAL_THEME] 🔄 Tema cambiado, reaplicando...');
            setTimeout(applyThemeToModals, 100);
        }
    });
});

observer.observe(document.documentElement, {
    attributes: true,
    attributeFilter: ['data-theme']
});

// También reaplicar cuando se inyecta el style de branding
const styleObserver = new MutationObserver((mutations) => {
    mutations.forEach((mutation) => {
        mutation.addedNodes.forEach((node) => {
            if (node.id === 'theme-style') {
                // console.log('[MODAL_THEME] 🎨 Nuevo tema detectado, reaplicando...');
                setTimeout(applyThemeToModals, 100);
            }
        });
    });
});

styleObserver.observe(document.head, {
    childList: true,
    subtree: true
});

// Exportar para uso manual
window.applyThemeToModals = applyThemeToModals;
