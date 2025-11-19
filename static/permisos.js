/**
 * Sistema de Permisos - Aleph70
 * Gestiona permisos de usuario a nivel de módulo y acción
 */

// Variable global para almacenar permisos del usuario
window.usuarioPermisos = {};

/**
 * Inicializar permisos del usuario desde el menú
 * Debe llamarse después de cargar el menú
 */
function inicializarPermisos(menuData) {
    console.log('[PERMISOS] Inicializando permisos desde menú');
    
    window.usuarioPermisos = {};
    
    if (!menuData || !Array.isArray(menuData)) {
        console.warn('[PERMISOS] No se recibieron datos de menú');
        return;
    }
    
    // Función recursiva para extraer permisos de módulos y submódulos
    function extraerPermisos(items) {
        items.forEach(modulo => {
            if (modulo.codigo && modulo.permisos) {
                window.usuarioPermisos[modulo.codigo] = {
                    ver: modulo.permisos.ver || 0,
                    crear: modulo.permisos.crear || 0,
                    editar: modulo.permisos.editar || 0,
                    eliminar: modulo.permisos.eliminar || 0,
                    anular: modulo.permisos.anular || 0,
                    exportar: modulo.permisos.exportar || 0
                };
                console.log(`[PERMISOS] ${modulo.codigo}:`, window.usuarioPermisos[modulo.codigo]);
            } else if (modulo.codigo && !modulo.permisos) {
                console.warn(`[PERMISOS] ⚠️ Módulo ${modulo.codigo} sin permisos:`, modulo);
            }
            
            // Procesar submódulos recursivamente
            if (modulo.submenu && Array.isArray(modulo.submenu)) {
                console.log(`[PERMISOS] Procesando ${modulo.submenu.length} submódulos de ${modulo.codigo || modulo.nombre}`);
                extraerPermisos(modulo.submenu);
            }
        });
    }
    
    // Extraer permisos de todos los módulos y submódulos
    extraerPermisos(menuData);
    
    console.log('[PERMISOS] Permisos cargados:', window.usuarioPermisos);
    console.log('[PERMISOS] Total módulos cargados:', Object.keys(window.usuarioPermisos).length);
    console.log('[PERMISOS] Módulos:', Object.keys(window.usuarioPermisos));
    
    // Aplicar permisos a la página actual
    aplicarPermisosAElementos();
}

/**
 * Verificar si el usuario tiene un permiso específico
 * @param {string} modulo - Código del módulo (ej: 'facturas', 'productos')
 * @param {string} accion - Acción a verificar ('ver', 'crear', 'editar', 'eliminar', 'anular', 'exportar')
 * @returns {boolean}
 */
function tienePermiso(modulo, accion) {
    // Intentar obtener permisos del contexto actual o del padre (si estamos en iframe)
    let permisos = window.usuarioPermisos;
    
    // Verificar si permisos está vacío o no existe
    const permisosVacios = !permisos || Object.keys(permisos).length === 0;
    
    // Si no hay permisos locales y estamos en iframe, buscar en el padre
    if (permisosVacios && window.parent && window.parent !== window) {
        console.log('[PERMISOS] No hay permisos locales (vacío o undefined), buscando en window.parent');
        try {
            permisos = window.parent.usuarioPermisos;
            console.log('[PERMISOS] Permisos obtenidos del padre:', permisos ? Object.keys(permisos) : 'undefined');
        } catch (e) {
            console.error('[PERMISOS] Error accediendo a window.parent.usuarioPermisos:', e.message);
        }
    }
    
    if (!permisos || Object.keys(permisos).length === 0) {
        console.error(`[PERMISOS] window.usuarioPermisos NO existe ni en local ni en parent`);
        return false;
    }
    
    if (!permisos[modulo]) {
        console.warn(`[PERMISOS] Módulo ${modulo} no encontrado en permisos`);
        console.warn(`[PERMISOS] Módulos disponibles:`, Object.keys(permisos));
        return false;
    }
    
    const tiene = permisos[modulo][accion] === 1;
    // Log deshabilitado para reducir ruido en consola
    // console.log(`[PERMISOS] tienePermiso('${modulo}', '${accion}') = ${tiene}`, permisos[modulo]);
    return tiene;
}

/**
 * Aplicar permisos a elementos con atributos data-permiso
 * Busca elementos con data-modulo y data-accion y los oculta/deshabilita
 */
function aplicarPermisosAElementos() {
    console.log('[PERMISOS] Aplicando permisos a elementos de la página');
    
    // Buscar todos los elementos con data-modulo y data-accion
    const elementosConPermiso = document.querySelectorAll('[data-modulo][data-accion]');
    
    elementosConPermiso.forEach(elemento => {
        const modulo = elemento.getAttribute('data-modulo');
        const accion = elemento.getAttribute('data-accion');
        const modo = elemento.getAttribute('data-permiso-modo') || 'ocultar'; // 'ocultar' o 'deshabilitar'
        
        const tieneAcceso = tienePermiso(modulo, accion);
        
        if (!tieneAcceso) {
            if (modo === 'ocultar') {
                // Ocultar el elemento
                elemento.style.setProperty('display', 'none', 'important');
                elemento.setAttribute('data-permiso-oculto', 'true');
                
                // Si el padre es un form-group vacío, ocultarlo también
                const padre = elemento.parentElement;
                if (padre && padre.classList.contains('form-group')) {
                    // Verificar si el padre solo tiene este elemento
                    const hijosVisibles = Array.from(padre.children).filter(hijo => {
                        return hijo.style.display !== 'none' && hijo !== elemento;
                    });
                    if (hijosVisibles.length === 0) {
                        padre.style.setProperty('display', 'none', 'important');
                        console.log(`[PERMISOS] Padre también ocultado: ${padre.tagName}`);
                    }
                }
                
                console.log(`[PERMISOS] Ocultado: ${elemento.tagName} - ${modulo}.${accion}`);
            } else if (modo === 'deshabilitar') {
                elemento.disabled = true;
                elemento.style.opacity = '0.5';
                elemento.style.cursor = 'not-allowed';
                elemento.title = 'No tienes permisos para esta acción';
                console.log(`[PERMISOS] Deshabilitado: ${elemento.tagName} - ${modulo}.${accion}`);
            }
        }
    });
    
    console.log(`[PERMISOS] Procesados ${elementosConPermiso.length} elementos con permisos`);
}

/**
 * Verificar permiso y mostrar alerta si no tiene acceso
 * @param {string} modulo - Código del módulo
 * @param {string} accion - Acción a verificar
 * @returns {boolean} true si tiene permiso, false si no
 */
function verificarPermisoConAlerta(modulo, accion) {
    if (!tienePermiso(modulo, accion)) {
        const mensajes = {
            'crear': 'No tienes permisos para crear registros',
            'editar': 'No tienes permisos para editar registros',
            'eliminar': 'No tienes permisos para eliminar registros',
            'anular': 'No tienes permisos para anular registros',
            'exportar': 'No tienes permisos para exportar datos'
        };
        
        alert(mensajes[accion] || 'No tienes permisos para realizar esta acción');
        return false;
    }
    return true;
}

/**
 * Obtener todos los permisos de un módulo
 * @param {string} modulo - Código del módulo
 * @returns {object|null} Objeto con todos los permisos o null
 */
function obtenerPermisosModulo(modulo) {
    return window.usuarioPermisos[modulo] || null;
}

/**
 * Verificar múltiples permisos a la vez
 * @param {string} modulo - Código del módulo
 * @param {string[]} acciones - Array de acciones a verificar
 * @returns {boolean} true si tiene TODOS los permisos
 */
function tienePermisosMultiples(modulo, acciones) {
    return acciones.every(accion => tienePermiso(modulo, accion));
}

/**
 * Crear botón con control de permisos
 * @param {object} config - {texto, icono, modulo, accion, clase, onclick}
 * @returns {HTMLElement|null} Botón o null si no tiene permiso
 */
function crearBotonConPermiso(config) {
    const {texto, icono, modulo, accion, clase = 'btn btn-primary', onclick} = config;
    
    if (!tienePermiso(modulo, accion)) {
        console.log(`[PERMISOS] Botón "${texto}" no creado: sin permiso ${modulo}.${accion}`);
        return null;
    }
    
    const boton = document.createElement('button');
    boton.className = clase;
    boton.innerHTML = `${icono ? `<i class="${icono}"></i> ` : ''}${texto}`;
    
    if (onclick) {
        boton.addEventListener('click', onclick);
    }
    
    return boton;
}

// Aplicar permisos cuando la página carga
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', aplicarPermisosAElementos);
} else {
    // Si la página ya cargó, esperar un poco por si se están cargando permisos
    setTimeout(aplicarPermisosAElementos, 500);
}

console.log('[PERMISOS] ✅ Sistema de permisos cargado');
