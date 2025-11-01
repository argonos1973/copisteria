/**
 * Theme Adapter - Compatibilidad con código antiguo
 * Traduce design tokens nuevos a variables CSS antiguas
 * Versión: 1.0
 */

class ThemeAdapter {
    constructor(themeEngine) {
        this.engine = themeEngine;
        this.legacyMapping = this.createLegacyMapping();
    }

    /**
     * Mapeo de nombres antiguos a rutas de tokens nuevos
     */
    createLegacyMapping() {
        return {
            // Colores principales
            'color_app_bg': 'semantic.bg',
            'color_primario': 'semantic.primary',
            'color_secundario': 'semantic.bg-elevated',
            'color_success': 'semantic.success',
            'color_warning': 'semantic.warning',
            'color_danger': 'semantic.danger',
            'color_info': 'semantic.info',
            
            // Botones
            'color_button': 'components.button.bg',
            'color_button_hover': 'components.button.hover-bg',
            'color_button_text': 'components.button.text',
            
            // Headers
            'color_header_bg': 'components.header.bg',
            'color_header_text': 'components.header.text',
            
            // Tablas
            'color_grid_header': 'components.table.header-bg',
            'color_grid_header_text': 'components.table.header-text',
            'color_grid_bg': 'components.table.bg',
            'color_grid_text': 'components.table.text',
            'color_grid_hover': 'components.table.row-hover',
            'color_grid_border': 'components.table.border',
            
            // Inputs
            'color_input_bg': 'components.input.bg',
            'color_input_text': 'components.input.text',
            'color_input_border': 'components.input.border',
            
            // Selects
            'color_select_bg': 'components.select.bg',
            'color_select_text': 'components.select.text',
            'color_select_border': 'components.select.border',
            
            // Modales
            'color_modal_bg': 'components.modal.bg',
            'color_modal_text': 'components.modal.text',
            'color_modal_border': 'components.modal.border',
            'color_modal_overlay': 'components.modal.overlay',
            'color_modal_shadow': 'components.modal.shadow',
            
            // Menú
            'color_submenu_bg': 'components.menu.bg',
            'color_submenu_text': 'components.menu.text',
            'color_submenu_hover': 'components.menu.hover',
            
            // Otros
            'color_icon': 'components.icon.color',
            'color_spinner_border': 'components.spinner.border',
            'color_tab_active_bg': 'components.tab.active-bg',
            'color_tab_active_text': 'components.tab.active-text',
            'color_disabled_bg': 'components.disabled.bg',
            'color_disabled_text': 'components.disabled.text'
        };
    }

    /**
     * Convierte tema nuevo a formato antiguo para compatibilidad
     */
    toLegacyFormat(themeJson) {
        const legacy = {
            nombre: themeJson.name,
            descripcion: themeJson.meta?.description || '',
            icon: themeJson.meta?.icon || '🎨'
        };

        // Obtener tokens resueltos
        const tokens = this.engine.flattenTokens(themeJson);

        // Mapear cada propiedad antigua
        for (const [oldKey, newPath] of Object.entries(this.legacyMapping)) {
            const parts = newPath.split('.');
            let value = themeJson;
            
            for (const part of parts) {
                value = value?.[part];
            }
            
            if (value) {
                // Resolver referencia si existe
                legacy[oldKey] = this.engine.resolveValue(value, themeJson);
            }
        }

        return legacy;
    }

    /**
     * Aplica tema usando el sistema nuevo pero expone variables antiguas
     */
    async applyThemeWithLegacy(themeJson, userOverrides = {}) {
        console.log('[ADAPTER] 🔄 Aplicando tema con compatibilidad legacy...');

        // Aplicar con sistema nuevo
        const result = await this.engine.applyTheme(themeJson, userOverrides);

        // Generar CSS adicional con nombres antiguos
        const legacyCSS = this.generateLegacyCSS(themeJson);
        this.injectLegacyCSS(legacyCSS);

        // Exportar formato antiguo para código que lo necesite
        window.__COLORES_EMPRESA__ = this.toLegacyFormat(result.theme);

        console.log('[ADAPTER] ✅ Tema aplicado con compatibilidad legacy');
        return result;
    }

    /**
     * Genera CSS con nombres de variables antiguas
     */
    generateLegacyCSS(themeJson) {
        const tokens = this.engine.flattenTokens(themeJson);
        let css = `:root[data-theme="${themeJson.name}"] {\n`;

        // Generar variables con nombres antiguos
        for (const [oldKey, newPath] of Object.entries(this.legacyMapping)) {
            const parts = newPath.split('.');
            let value = themeJson;
            
            for (const part of parts) {
                value = value?.[part];
            }
            
            if (value) {
                const resolved = this.engine.resolveValue(value, themeJson);
                css += `  --${oldKey.replace(/_/g, '-')}: ${resolved};\n`;
            }
        }

        css += '}\n';
        return css;
    }

    /**
     * Inyecta CSS legacy en el DOM
     */
    injectLegacyCSS(css) {
        let styleEl = document.getElementById('theme-legacy-style');
        
        if (!styleEl) {
            styleEl = document.createElement('style');
            styleEl.id = 'theme-legacy-style';
            styleEl.setAttribute('data-source', 'theme-adapter');
            document.head.appendChild(styleEl);
        }

        styleEl.textContent = css;
    }

    /**
     * Carga tema desde nombre (busca en /static/plantillas/)
     */
    async loadAndApplyTheme(themeName) {
        try {
            const url = `/static/plantillas/${themeName.toLowerCase()}.json`;
            const themeJson = await this.engine.loadTheme(url);
            return await this.applyThemeWithLegacy(themeJson);
        } catch (error) {
            console.error('[ADAPTER] ❌ Error al cargar tema:', error);
            throw error;
        }
    }
}

// Exportar instancia global
window.ThemeAdapter = ThemeAdapter;

// Inicializar cuando ThemeEngine esté disponible
if (window.themeEngine) {
    window.themeAdapter = new ThemeAdapter(window.themeEngine);
    console.log('[ADAPTER] 🔄 Theme Adapter cargado');
} else {
    document.addEventListener('DOMContentLoaded', () => {
        if (window.themeEngine) {
            window.themeAdapter = new ThemeAdapter(window.themeEngine);
            console.log('[ADAPTER] 🔄 Theme Adapter cargado (deferred)');
        }
    });
}
