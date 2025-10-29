// Gestor de plantillas de colores v3
// Carga plantillas predefinidas (JSON) + personalizadas (BD via API)

let plantillasColores = {};
let plantillasDisponibles = [];

// Cargar todas las plantillas (predefinidas + personalizadas)
async function cargarPlantillas() {
    console.log('📦 [PLANTILLAS V3] Cargando plantillas...');
    
    try {
        plantillasColores = {};
        plantillasDisponibles = [];
        
        // 1. Cargar plantillas predefinidas desde archivos JSON
        const predefinidas = ['minimal', 'dark', 'eink'];
        
        for (const nombre of predefinidas) {
            try {
                const response = await fetch(`/static/plantillas/${nombre}.json`, {
                    cache: 'no-cache'
                });
                
                if (response.ok) {
                    const plantilla = await response.json();
                    plantillasColores[nombre] = plantilla;
                    plantillasDisponibles.push({
                        archivo: nombre,
                        nombre: plantilla.nombre || nombre,
                        descripcion: plantilla.descripcion || '',
                        icon: plantilla.icon || '📄',
                        personalizada: false,
                        basada_en: ''
                    });
                    console.log(`✅ Plantilla predefinida "${plantilla.nombre}" cargada`);
                }
            } catch (error) {
                console.error(`❌ Error cargando plantilla ${nombre}:`, error);
            }
        }
        
        // 2. Cargar plantillas personalizadas desde BD
        try {
            const response = await fetch('/api/plantillas/personalizadas', {
                credentials: 'include',
                cache: 'no-cache'
            });
            
            if (response.ok) {
                const data = await response.json();
                
                if (data.success && data.plantillas && data.plantillas.length > 0) {
                    console.log(`📋 ${data.plantillas.length} plantillas personalizadas encontradas`);
                    
                    data.plantillas.forEach(p => {
                        const nombreArchivo = `custom_${p.id}`;
                        
                        // Convertir datos de BD a formato de plantilla
                        plantillasColores[nombreArchivo] = {
                            nombre: p.nombre,
                            descripcion: p.descripcion,
                            icon: '🎨',
                            personalizada: true,
                            basada_en: p.plantilla_base,
                            // Colores
                            color_primario: p.color_primario,
                            color_secundario: p.color_secundario,
                            color_success: p.color_success,
                            color_warning: p.color_warning,
                            color_danger: p.color_danger,
                            color_info: p.color_info,
                            color_button: p.color_button,
                            color_button_hover: p.color_button_hover,
                            color_button_text: p.color_button_text,
                            color_app_bg: p.color_app_bg,
                            color_header_bg: p.color_header_bg,
                            color_header_text: p.color_header_text,
                            color_grid_header: p.color_grid_header,
                            color_grid_hover: p.color_grid_hover,
                            color_input_bg: p.color_input_bg,
                            color_input_text: p.color_input_text,
                            color_input_border: p.color_input_border,
                            color_select_bg: p.color_select_bg,
                            color_select_text: p.color_select_text,
                            color_select_border: p.color_select_border,
                            color_disabled_bg: p.color_disabled_bg,
                            color_disabled_text: p.color_disabled_text,
                            color_submenu_bg: p.color_submenu_bg,
                            color_submenu_text: p.color_submenu_text,
                            color_submenu_hover: p.color_submenu_hover,
                            color_grid_bg: p.color_grid_bg,
                            color_grid_text: p.color_grid_text,
                            color_icon: p.color_icon
                        };
                        
                        plantillasDisponibles.push({
                            archivo: nombreArchivo,
                            nombre: p.nombre,
                            descripcion: p.descripcion || `Basada en ${p.plantilla_base}`,
                            icon: '🎨',
                            personalizada: true,
                            basada_en: p.plantilla_base
                        });
                        
                        console.log(`✅ Plantilla personalizada "${p.nombre}" cargada`);
                    });
                }
            }
        } catch (error) {
            console.error('❌ Error cargando plantillas personalizadas:', error);
        }
        
        console.log(`✅ Total: ${Object.keys(plantillasColores).length} plantillas cargadas`);
        return plantillasColores;
        
    } catch (error) {
        console.error('❌ Error fatal cargando plantillas:', error);
        return plantillasColores;
    }
}

// Guardar plantilla personalizada
async function guardarPlantillaPersonalizada(colores, basadaEn, nombreCustom = '') {
    console.log('💾 Guardando plantilla personalizada...');
    
    try {
        const data = {
            nombre: nombreCustom,
            descripcion: `Basada en ${basadaEn}`,
            plantilla_base: basadaEn,
            ...colores
        };
        
        const response = await fetch('/api/plantillas/personalizadas', {
            method: 'POST',
            credentials: 'include',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Error guardando plantilla');
        }
        
        const result = await response.json();
        console.log('✅ Plantilla guardada:', result);
        
        // Recargar plantillas
        await cargarPlantillas();
        
        return {
            success: true,
            nombre_plantilla: nombreCustom,
            nombre_archivo: `custom_${nombreCustom.replace(/ /g, '_')}`
        };
        
    } catch (error) {
        console.error('❌ Error guardando plantilla:', error);
        throw error;
    }
}

// Eliminar plantilla personalizada
async function eliminarPlantillaPersonalizada(id) {
    console.log(`🗑️ Eliminando plantilla ID: ${id}`);
    
    try {
        const response = await fetch(`/api/plantillas/personalizadas/${id}`, {
            method: 'DELETE',
            credentials: 'include'
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Error eliminando plantilla');
        }
        
        console.log('✅ Plantilla eliminada');
        
        // Recargar plantillas
        await cargarPlantillas();
        
        return true;
        
    } catch (error) {
        console.error('❌ Error eliminando plantilla:', error);
        throw error;
    }
}

// Exportar para uso global
window.cargarPlantillas = cargarPlantillas;
window.guardarPlantillaPersonalizada = guardarPlantillaPersonalizada;
window.eliminarPlantillaPersonalizada = eliminarPlantillaPersonalizada;
window.plantillasColores = plantillasColores;
window.plantillasDisponibles = plantillasDisponibles;
