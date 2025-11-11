// Gestor de plantillas de colores v2
// Carga plantillas predefinidas + personalizadas desde el API

let plantillasColores = {};
let plantillasDisponibles = [];

// Cargar todas las plantillas (predefinidas + personalizadas)
async function cargarPlantillas() {
    console.log('📦 [PLANTILLAS V2] Cargando plantillas desde API...');
    
    try {
        // Cargar plantillas predefinidas desde archivos JSON
        const plantillasPredefinidas = ['minimal', 'dark', 'eink'];
        const plantillas = [];
        
        // 1. Cargar plantillas predefinidas
        for (const nombre of plantillasPredefinidas) {
            try {
                const response = await fetch(`/static/plantillas/${nombre}.json`, {
                    cache: 'no-cache'
                });
                
                if (response.ok) {
                    const plantilla = await response.json();
                    plantillas.push({
                        archivo: nombre,
                        nombre: plantilla.nombre,
                        descripcion: plantilla.descripcion,
                        icon: plantilla.icon || '📄',
                        personalizada: false,
                        basada_en: ''
                    });
                }
            } catch (error) {
                console.error(`Error cargando ${nombre}:`, error);
            }
        }
        
        // 2. Cargar plantillas personalizadas desde BD
        const response = await fetch('/api/plantillas/personalizadas', { credentials: 'include' }, {
            credentials: 'include',
            cache: 'no-cache'
        });
        
        if (!response.ok) {
            console.error('❌ Error al listar plantillas:', response.status);
            return cargarPlantillasPredefinidas(); // Fallback
        }
        
        const data = await response.json();
        console.log('📋 Plantillas disponibles:', data.plantillas.length);
        
        // Cargar cada plantilla
        const promesas = data.plantillas.map(async (info) => {
            try {
                const plantillaResponse = await fetch(`/static/plantillas/${info.archivo}.json`, {
                    cache: 'no-cache'
                });
                
                if (plantillaResponse.ok) {
                    const plantilla = await plantillaResponse.json();
                    plantillasColores[info.archivo] = plantilla;
                    plantillasDisponibles.push(info);
                    console.log(`✅ Plantilla "${info.nombre}" cargada (${info.personalizada ? 'personalizada' : 'predefinida'})`);
                }
            } catch (error) {
                console.error(`❌ Error cargando plantilla "${info.nombre}":`, error);
            }
        });
        
        await Promise.all(promesas);
        console.log(`✅ Total plantillas cargadas: ${Object.keys(plantillasColores).length}`);
        
        return plantillasColores;
        
    } catch (error) {
        console.error('❌ Error cargando plantillas:', error);
        return cargarPlantillasPredefinidas(); // Fallback
    }
}

// Fallback: Cargar solo plantillas predefinidas
async function cargarPlantillasPredefinidas() {
    console.log('⚠️ Cargando plantillas predefinidas (fallback)...');
    const predefinidas = ['minimal', 'dark', 'eink'];
    
    const promesas = predefinidas.map(async (nombre) => {
        try {
            const response = await fetch(`/static/plantillas/${nombre}.json`);
            if (response.ok) {
                const plantilla = await response.json();
                plantillasColores[nombre] = plantilla;
                plantillasDisponibles.push({
                    archivo: nombre,
                    nombre: plantilla.nombre,
                    descripcion: plantilla.descripcion,
                    icon: plantilla.icon,
                    personalizada: false,
                    basada_en: ''
                });
            }
        } catch (error) {
            console.error(`❌ Error cargando plantilla "${nombre}":`, error);
        }
    });
    
    await Promise.all(promesas);
    return plantillasColores;
}

// Guardar plantilla personalizada
async function guardarPlantillaPersonalizada(colores, basadaEn, nombreCustom = '') {
    console.log('💾 Guardando plantilla personalizada...');
    
    try {
        const response = await fetch('/api/plantillas/guardar', { credentials: 'include' }, {
            method: 'POST',
            credentials: 'include',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                colores: colores,
                basada_en: basadaEn,
                nombre_custom: nombreCustom
            })
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Error guardando plantilla');
        }
        
        const result = await response.json();
        console.log('✅ Plantilla guardada:', result.nombre_plantilla);
        
        // Recargar plantillas para incluir la nueva
        await cargarPlantillas();
        
        return result;
        
    } catch (error) {
        console.error('❌ Error guardando plantilla:', error);
        throw error;
    }
}

// Eliminar plantilla personalizada
async function eliminarPlantillaPersonalizada(nombre) {
    console.log(`🗑️ Eliminando plantilla: ${nombre}`);
    
    try {
        const response = await fetch(`/api/plantillas/eliminar/${nombre}`, {
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
