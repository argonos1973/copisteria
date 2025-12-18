// Gestor de plantillas de colores
// Carga plantillas desde archivos JSON

let plantillasColores = {};

function resolveValue(value, context) {
    if (typeof value !== 'string') return value;

    const refPattern = /^\{(.+)\}$/;
    const match = refPattern.exec(value);

    if (!match) return value;

    const path = match[1].split('.');
    let resolved = context;

    for (const key of path) {
        resolved = resolved?.[key];
        if (resolved === undefined) {
            return value;
        }
    }

    return resolveValue(resolved, context);
}

function toLegacyFormat(themeJson) {
    const legacyMapping = {
        color_app_bg: 'semantic.bg',
        color_primario: 'semantic.primary',
        color_secundario: 'semantic.bg-elevated',
        color_success: 'semantic.success',
        color_warning: 'semantic.warning',
        color_danger: 'semantic.danger',
        color_info: 'semantic.info',

        color_button: 'components.button.bg',
        color_button_hover: 'components.button.hover-bg',
        color_button_text: 'components.button.text',

        color_header_bg: 'components.header.bg',
        color_header_text: 'components.header.text',

        color_grid_header: 'components.table.header-bg',
        color_grid_header_text: 'components.table.header-text',
        color_grid_bg: 'components.table.bg',
        color_grid_text: 'components.table.text',
        color_grid_hover: 'components.table.row-hover',
        color_grid_border: 'components.table.border',

        color_input_bg: 'components.input.bg',
        color_input_text: 'components.input.text',
        color_input_border: 'components.input.border',

        color_select_bg: 'components.select.bg',
        color_select_text: 'components.select.text',
        color_select_border: 'components.select.border',

        color_modal_bg: 'components.modal.bg',
        color_modal_text: 'components.modal.text',
        color_modal_border: 'components.modal.border',
        color_modal_overlay: 'components.modal.overlay',
        color_modal_shadow: 'components.modal.shadow',

        color_submenu_bg: 'components.menu.bg',
        color_submenu_text: 'components.menu.text',
        color_submenu_hover: 'components.menu.hover',

        color_icon: 'components.icon.color',
        color_spinner_border: 'components.spinner.border',
        color_tab_active_bg: 'components.tab.active-bg',
        color_tab_active_text: 'components.tab.active-text',
        color_disabled_bg: 'components.disabled.bg',
        color_disabled_text: 'components.disabled.text'
    };

    const legacy = {
        nombre: themeJson.name,
        descripcion: themeJson.meta?.description || '',
        icon: themeJson.meta?.icon || '🎨'
    };

    for (const [oldKey, newPath] of Object.entries(legacyMapping)) {
        const parts = newPath.split('.');
        let value = themeJson;

        for (const part of parts) {
            value = value?.[part];
        }

        if (value !== undefined && value !== null && value !== '') {
            legacy[oldKey] = resolveValue(value, themeJson);
        }
    }

    return legacy;
}

// Lista de plantillas disponibles
const plantillasDisponibles = ['minimal', 'dark', 'eink', 'classic', 'login_glass'];

// Cargar todas las plantillas
async function cargarPlantillas() {
    console.log('📦 Cargando plantillas de colores...');
    
    const promesas = plantillasDisponibles.map(async (nombre) => {
        try {
            const response = await fetch(`/static/plantillas/${nombre}.json?v=${Date.now()}`);
            if (response.ok) {
                let plantilla = await response.json();
                if (plantilla && plantilla.name && plantilla.palette && plantilla.semantic && plantilla.components) {
                    plantilla = toLegacyFormat(plantilla);
                }
                plantillasColores[nombre] = plantilla;
                console.log(`✅ Plantilla "${nombre}" cargada`);
            } else {
                console.error(`❌ Error cargando plantilla "${nombre}":`, response.status);
            }
        } catch (error) {
            console.error(`❌ Error cargando plantilla "${nombre}":`, error);
        }
    });
    
    await Promise.all(promesas);
    console.log('✅ Todas las plantillas cargadas:', Object.keys(plantillasColores));
    
    return plantillasColores;
}

// Exportar para uso global
window.cargarPlantillas = cargarPlantillas;
window.plantillasColores = plantillasColores;
