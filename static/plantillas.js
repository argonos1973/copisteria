// Gestor de plantillas de colores
// Carga plantillas desde archivos JSON

let plantillasColores = {};

// Lista de plantillas disponibles
const plantillasDisponibles = ['minimal', 'dark', 'eink'];

// Cargar todas las plantillas
async function cargarPlantillas() {
    console.log('📦 Cargando plantillas de colores...');
    
    const promesas = plantillasDisponibles.map(async (nombre) => {
        try {
            const response = await fetch(`/static/plantillas/${nombre}.json`);
            if (response.ok) {
                const plantilla = await response.json();
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
