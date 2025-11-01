/**
 * Theme Engine - Design Tokens System
 * Compila plantillas JSON (palette → semantic → components) a CSS variables
 * Versión: 1.0
 */

class ThemeEngine {
    constructor() {
        this.currentTheme = null;
        this.cache = new Map();
    }

    /**
     * Resuelve referencias {palette.x} y {semantic.x} recursivamente
     */
    resolveValue(value, context) {
        if (typeof value !== 'string') return value;
        
        const refPattern = /^\{(.+)\}$/;
        const match = refPattern.exec(value);
        
        if (!match) return value;
        
        const path = match[1].split('.');
        let resolved = context;
        
        for (const key of path) {
            resolved = resolved?.[key];
            if (resolved === undefined) {
                console.warn(`[THEME] Referencia no resuelta: ${match[1]}`);
                return value;
            }
        }
        
        // Resolver recursivamente si el valor también es una referencia
        return this.resolveValue(resolved, context);
    }

    /**
     * Aplana el objeto de componentes y resuelve todas las referencias
     */
    flattenTokens(themeJson) {
        const context = themeJson;
        const tokens = {};

        const walk = (obj, prefix = []) => {
            for (const [key, value] of Object.entries(obj)) {
                if (typeof value === 'object' && value !== null && !Array.isArray(value)) {
                    walk(value, [...prefix, key]);
                } else {
                    const cssKey = [...prefix, key]
                        .join('-')
                        .replace(/^(palette|semantic|components)-/, '')
                        .replace(/_/g, '-');
                    
                    tokens[cssKey] = this.resolveValue(value, context);
                }
            }
        };

        // Solo procesamos semantic y components (palette es solo materia prima)
        walk({ semantic: themeJson.semantic, components: themeJson.components });

        return tokens;
    }

    /**
     * Genera el bloque CSS con variables
     */
    generateCSS(themeJson, tokens) {
        const themeName = themeJson.name;
        let css = `:root[data-theme="${themeName}"] {\n`;

        // Variables CSS (--semantic-x, --btn-x, etc.)
        for (const [key, value] of Object.entries(tokens)) {
            const varName = `--${key}`.toLowerCase().replace(/[^a-z0-9-]/g, '');
            css += `  ${varName}: ${value};\n`;
        }

        css += '}\n';
        return css;
    }

    /**
     * Valida contraste WCAG AA (4.5:1 texto normal, 3:1 headers)
     */
    validateContrast(fgColor, bgColor, level = 'AA', size = 'normal') {
        const getLuminance = (hex) => {
            const rgb = parseInt(hex.replace('#', ''), 16);
            const r = ((rgb >> 16) & 0xff) / 255;
            const g = ((rgb >> 8) & 0xff) / 255;
            const b = (rgb & 0xff) / 255;

            const [rs, gs, bs] = [r, g, b].map(c => 
                c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4)
            );

            return 0.2126 * rs + 0.7152 * gs + 0.0722 * bs;
        };

        const l1 = getLuminance(fgColor);
        const l2 = getLuminance(bgColor);
        const contrast = (Math.max(l1, l2) + 0.05) / (Math.min(l1, l2) + 0.05);

        const minContrast = size === 'large' || size === 'header' ? 3 : 4.5;
        const passes = contrast >= minContrast;

        return {
            contrast: contrast.toFixed(2),
            passes,
            level: passes ? level : 'FAIL',
            recommendation: passes ? null : `Contraste insuficiente: ${contrast.toFixed(2)}:1 (mínimo ${minContrast}:1)`
        };
    }

    /**
     * Aplica el tema al documento
     */
    async applyTheme(themeJson, userOverrides = {}) {
        console.log('[THEME] 🎨 Aplicando tema:', themeJson.name);

        // Merge con overrides del usuario (deep merge)
        const merged = this.deepMerge(themeJson, userOverrides);

        // Aplanar y resolver referencias
        const tokens = this.flattenTokens(merged);
        console.log('[THEME] 📋 Tokens resueltos:', Object.keys(tokens).length);

        // Generar CSS
        const css = this.generateCSS(merged, tokens);

        // Inyectar en DOM
        this.injectCSS(css);

        // Activar tema
        document.documentElement.dataset.theme = merged.name;

        // Guardar en cache
        this.currentTheme = merged;
        this.cache.set(merged.name, { json: merged, tokens, css });

        // Persistir en localStorage
        localStorage.setItem('aleph70_theme', JSON.stringify(merged));
        localStorage.setItem('aleph70_theme_name', merged.name);

        console.log('[THEME] ✅ Tema aplicado:', merged.name);

        return { theme: merged, tokens };
    }

    /**
     * Inyecta CSS en el DOM
     */
    injectCSS(css) {
        let styleEl = document.getElementById('theme-style');
        
        if (!styleEl) {
            styleEl = document.createElement('style');
            styleEl.id = 'theme-style';
            styleEl.setAttribute('data-source', 'theme-engine');
            document.head.appendChild(styleEl);
        }

        styleEl.textContent = css;
    }

    /**
     * Deep merge de objetos
     */
    deepMerge(target, source) {
        const output = JSON.parse(JSON.stringify(target));

        if (!source) return output;

        for (const key in source) {
            if (source[key] instanceof Object && key in output) {
                output[key] = this.deepMerge(output[key], source[key]);
            } else {
                output[key] = source[key];
            }
        }

        return output;
    }

    /**
     * Carga tema desde URL
     */
    async loadTheme(url) {
        try {
            const response = await fetch(url);
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            
            const themeJson = await response.json();
            
            // Validar estructura
            if (!themeJson.name || !themeJson.palette || !themeJson.semantic || !themeJson.components) {
                throw new Error('JSON de tema inválido: faltan propiedades requeridas');
            }

            console.log('[THEME] ✅ Tema cargado:', themeJson.name);
            return themeJson;
        } catch (error) {
            console.error('[THEME] ❌ Error al cargar tema:', error);
            throw error;
        }
    }

    /**
     * Migra plantilla antigua (color_x) a nuevo formato
     */
    migrateOldFormat(oldJson) {
        console.log('[THEME] 🔄 Migrando formato antiguo...');

        // Mapa de migración
        const migration = {
            color_app_bg: 'semantic.bg',
            color_primario: 'semantic.primary',
            color_secundario: 'semantic.bg-elevated',
            color_header_bg: 'components.header.bg',
            color_header_text: 'components.header.text',
            color_button: 'components.button.bg',
            color_button_hover: 'components.button.hover-bg',
            color_button_text: 'components.button.text',
            color_grid_header: 'components.table.header-bg',
            color_grid_header_text: 'components.table.header-text',
            color_grid_text: 'components.table.text',
            color_input_bg: 'components.input.bg',
            color_input_text: 'components.input.text',
            color_input_border: 'components.input.border',
            color_modal_bg: 'components.modal.bg',
            color_modal_text: 'components.modal.text'
        };

        const newFormat = {
            name: oldJson.nombre || oldJson.name || 'Custom',
            version: 1,
            meta: {
                author: 'migrated',
                icon: oldJson.icon || '🎨',
                dark: oldJson.color_app_bg && oldJson.color_app_bg.startsWith('#0'),
                description: oldJson.descripcion || ''
            },
            palette: {},
            semantic: {},
            components: {
                button: {},
                input: {},
                table: {},
                modal: {},
                header: {}
            }
        };

        // Mapear colores antiguos a nuevos
        for (const [oldKey, newPath] of Object.entries(migration)) {
            if (oldJson[oldKey]) {
                const parts = newPath.split('.');
                let target = newFormat;
                
                for (let i = 0; i < parts.length - 1; i++) {
                    target = target[parts[i]];
                }
                
                target[parts[parts.length - 1]] = oldJson[oldKey];
            }
        }

        console.log('[THEME] ✅ Formato migrado');
        return newFormat;
    }

    /**
     * Restaura tema desde localStorage
     */
    restoreTheme() {
        const saved = localStorage.getItem('aleph70_theme');
        if (saved) {
            try {
                const theme = JSON.parse(saved);
                return this.applyTheme(theme);
            } catch (e) {
                console.warn('[THEME] ⚠️ Error al restaurar tema guardado:', e);
            }
        }
        return null;
    }
}

// Exportar instancia global
window.ThemeEngine = ThemeEngine;
window.themeEngine = new ThemeEngine();

console.log('[THEME] 🎨 Theme Engine cargado');
