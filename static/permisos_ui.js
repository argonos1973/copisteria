/**
 * Sistema de control de permisos en la UI
 * Oculta/deshabilita botones y acciones según los permisos del usuario
 */

// Caché de permisos del usuario
let permisosUsuario = null;
let sesionUsuario = null;

/**
 * Obtener permisos del usuario desde la sesión
 */
async function cargarPermisos() {
    try {
        const response = await fetch('/api/auth/session', {
            credentials: 'include'
        });
        
        if (!response.ok) {
            console.error('[PERMISOS] Error obteniendo sesión');
            return null;
        }
        
        sesionUsuario = await response.json();
        console.log('[PERMISOS] Sesión cargada:', sesionUsuario);
        
        // Obtener permisos detallados
        const permisosResponse = await fetch('/api/auth/permisos', {
            credentials: 'include'
        });
        
        if (permisosResponse.ok) {
            permisosUsuario = await permisosResponse.json();
            console.log('[PERMISOS] Permisos cargados:', permisosUsuario);
        } else {
            // Si no hay endpoint de permisos, usar valores de sesión
            permisosUsuario = {};
            console.log('[PERMISOS] Usando permisos de sesión');
        }
        
        return permisosUsuario;
    } catch (error) {
        console.error('[PERMISOS] Error cargando permisos:', error);
        return null;
    }
}

/**
 * Verificar si el usuario tiene un permiso específico
 */
function tienePermiso(modulo, accion) {
    // Superadmin tiene todos los permisos
    if (sesionUsuario && sesionUsuario.es_superadmin === 1) {
        return true;
    }
    
    // Admin de empresa tiene todos los permisos
    if (sesionUsuario && sesionUsuario.es_admin_empresa === 1) {
        return true;
    }
    
    // Verificar permisos específicos
    if (permisosUsuario && permisosUsuario[modulo]) {
        const permisos = permisosUsuario[modulo];
        
        switch(accion) {
            case 'ver':
            case 'consultar':
                return permisos.puede_ver === 1;
            case 'crear':
            case 'nuevo':
                return permisos.puede_crear === 1;
            case 'editar':
            case 'modificar':
                return permisos.puede_editar === 1;
            case 'eliminar':
            case 'borrar':
                return permisos.puede_eliminar === 1;
            case 'anular':
                return permisos.puede_anular === 1;
            case 'exportar':
                return permisos.puede_exportar === 1;
            default:
                return false;
        }
    }
    
    // Por defecto, no tiene permiso
    return false;
}

/**
 * Aplicar permisos a los elementos de la UI
 */
function aplicarPermisosUI() {
    // console.log('[PERMISOS] Aplicando permisos a la UI...');
    
    // Buscar todos los elementos con data-modulo y data-accion
    const elementosConPermisos = document.querySelectorAll('[data-modulo][data-accion]');
    
    elementosConPermisos.forEach(elemento => {
        const modulo = elemento.getAttribute('data-modulo');
        const accion = elemento.getAttribute('data-accion');
        
        if (!tienePermiso(modulo, accion)) {
            // Ocultar el elemento
            elemento.style.display = 'none';
            elemento.disabled = true;
            // console.log(`[PERMISOS] Ocultado: ${modulo}.${accion}`);
        } else {
            // console.log(`[PERMISOS] Permitido: ${modulo}.${accion}`);
        }
    });
    
    // Ocultar columnas de acciones si no hay permisos
    ocultarColumnasAcciones();
}

/**
 * Ocultar columnas de tabla que solo contienen acciones sin permiso
 */
function ocultarColumnasAcciones() {
    // Buscar todas las tablas
    const tablas = document.querySelectorAll('table.grid, table');
    
    tablas.forEach(tabla => {
        const thead = tabla.querySelector('thead tr');
        const tbody = tabla.querySelector('tbody');
        
        if (!thead || !tbody) return;
        
        const headers = Array.from(thead.querySelectorAll('th'));
        const filas = Array.from(tbody.querySelectorAll('tr'));
        
        // Verificar cada columna
        headers.forEach((th, index) => {
            // Si la columna tiene clase "acciones-col" o título de acción
            const esColumnaAccion = th.classList.contains('acciones-col') || 
                                   th.title.includes('Crear') || 
                                   th.title.includes('Eliminar') ||
                                   th.title.includes('Editar');
            
            if (esColumnaAccion) {
                // Verificar si hay botones visibles en esta columna
                let tieneBotonVisible = false;
                
                filas.forEach(fila => {
                    const celda = fila.children[index];
                    if (celda) {
                        const botones = celda.querySelectorAll('button, a, .btn');
                        botones.forEach(boton => {
                            if (boton.style.display !== 'none' && !boton.disabled) {
                                tieneBotonVisible = true;
                            }
                        });
                    }
                });
                
                // Si no hay botones visibles, ocultar toda la columna
                if (!tieneBotonVisible) {
                    th.style.display = 'none';
                    filas.forEach(fila => {
                        const celda = fila.children[index];
                        if (celda) {
                            celda.style.display = 'none';
                        }
                    });
                    console.log(`[PERMISOS] Columna de acción oculta: ${th.textContent || th.title}`);
                }
            }
        });
    });
}

/**
 * Inicializar sistema de permisos
 */
async function inicializarPermisos() {
    console.log('[PERMISOS] Inicializando sistema de permisos...');
    
    await cargarPermisos();
    
    // Aplicar permisos cuando el DOM esté listo
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', aplicarPermisosUI);
    } else {
        aplicarPermisosUI();
    }
    
    // Re-aplicar permisos cuando se actualice el contenido dinámico
    const observer = new MutationObserver(() => {
        aplicarPermisosUI();
    });
    
    observer.observe(document.body, {
        childList: true,
        subtree: true
    });
}

// Exportar funciones
export {
    inicializarPermisos,
    tienePermiso,
    aplicarPermisosUI,
    cargarPermisos
};

// Auto-inicializar si no es módulo
if (typeof module === 'undefined') {
    inicializarPermisos();
}
