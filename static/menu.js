// Variable global para evitar inicialización múltiple
let menuEventosConfigurados = false;

function inicializarEventosMenu() {
    // Evitar inicialización múltiple
    if (menuEventosConfigurados) {
        console.log('[MENU] ⚠️ Eventos ya configurados, omitiendo duplicado');
        return;
    }
    
    // Eliminar cualquier estado guardado de menús activos
    sessionStorage.removeItem('activeMenus');
    
    const menuItems = document.querySelectorAll('.menu-item');
    const contentFrame = document.getElementById('content-frame');
    
    if (menuItems.length === 0) {
        console.log('[MENU] No hay items de menú para configurar eventos');
        return;
    }
    
    console.log('[MENU] Configurando eventos para', menuItems.length, 'items');
    menuEventosConfigurados = true;
    
    let activeMenus = [];
    
    // --- SUBMENÚS ANIDADOS ---
    // Gestionar el despliegue de los submenu-block (Tickets, Proformas, etc. dentro de Facturas Emitidas)
    // Usar .submenu-header en lugar de .submenu-block > .submenu-item para evitar conflictos
    const submenuHeaders = document.querySelectorAll('.submenu-header');
    console.log('[MENU] Submenu headers encontrados:', submenuHeaders.length);
    submenuHeaders.forEach(header => {
        header.addEventListener('click', function(e) {
            e.preventDefault();
            const block = header.parentElement; // El .submenu-block
            // Plegar todos los bloques hermanos
            const allBlocks = block.parentElement.querySelectorAll('.submenu-block');
            allBlocks.forEach(b => {
                if (b !== block) b.classList.remove('active');
            });
            // Alternar el bloque clicado
            block.classList.toggle('active');
            console.log('[MENU] Toggle submenu-block:', block.classList.contains('active') ? 'abierto' : 'cerrado');
        });
    });

    // Función para cerrar todos los submenús excepto el actual
    function aplicarEstiloActivo(menuItem, activo) {
        if (!menuItem) return;
        const link = menuItem.querySelector('.menu-link');
        if (activo) {
            menuItem.style.setProperty('background', 'transparent', 'important');
            menuItem.style.setProperty('background-color', 'transparent', 'important');
            if (link) {
                link.style.setProperty('background', 'transparent', 'important');
                link.style.setProperty('background-color', 'transparent', 'important');
                link.style.setProperty('box-shadow', 'none', 'important');
            }
        } else {
            menuItem.style.removeProperty('background');
            menuItem.style.removeProperty('background-color');
            if (link) {
                link.style.removeProperty('background');
                link.style.removeProperty('background-color');
                link.style.removeProperty('box-shadow');
            }
        }
    }

    function closeOtherMenus(currentItem) {
        menuItems.forEach(item => {
            if (item !== currentItem && item.classList.contains('active')) {
                item.classList.remove('active');
                aplicarEstiloActivo(item, false);
                // Eliminar del array de activos
                const menuTitle = item.querySelector('.menu-link').textContent;
                const index = activeMenus.indexOf(menuTitle);
                if (index > -1) {
                    activeMenus.splice(index, 1);
                }
            }
        });
    }
    
    // Cargar página en el iframe con verificación de cambios
    async function loadPage(url) {
        if (url && url !== '#') {
            // Agregar timestamp para evitar caché del iframe
            const separator = url.includes('?') ? '&' : '?';
            const urlWithCache = url + separator + '_t=' + Date.now();
            
            // Si hay función navegarSeguro en el iframe, usarla
            try {
                const iframeWindow = contentFrame.contentWindow;
                if (iframeWindow && iframeWindow.navegarSeguro) {
                    await iframeWindow.navegarSeguro(urlWithCache);
                } else if (iframeWindow && iframeWindow.__verificarCambiosGlobal) {
                    const hayCambios = iframeWindow.__verificarCambiosGlobal();
                    console.log('[Menu] Verificando cambios:', hayCambios);
                    if (hayCambios) {
                        // Usar mostrarConfirmacion global del padre (index.html)
                        if (window.mostrarConfirmacion) {
                            const guardar = await window.mostrarConfirmacion('Hay cambios sin guardar. ¿Desea guardarlos antes de salir?');
                            console.log('[Menu] Usuario respondió:', guardar === true ? 'Guardar' : 'Cancelar');
                            
                            // Si el usuario canceló (guardar === null), no hacer nada
                            if (!guardar) {
                                console.log('[Menu] Usuario canceló, quedarse en la página');
                                return; // No navegar
                            }
                            
                            const callbackGuardar = iframeWindow.__callbackGuardarGlobal;
                            if (guardar && callbackGuardar) {
                                try {
                                    console.log('[Menu] Ejecutando callback de guardar...');
                                    await callbackGuardar();
                                    console.log('[Menu] Guardado completado');
                                    // Esperar brevemente para mostrar la notificación
                                    await new Promise(resolve => setTimeout(resolve, 500));
                                    console.log('[Menu] Navegando después de guardar a:', urlWithCache);
                                    contentFrame.src = urlWithCache;
                                    return;
                                } catch (e) {
                                    console.log('[Menu] Usuario canceló modal de pagos o error al guardar:', e.message);
                                    // No navegar si el usuario canceló o si falló el guardado
                                    return;
                                }
                            }
                        }
                    }
                    console.log('[Menu] No hay cambios, navegando a:', urlWithCache);
                    contentFrame.src = urlWithCache;
                } else {
                    contentFrame.src = urlWithCache;
                }
            } catch (e) {
                // Si falla, navegar normalmente
                contentFrame.src = urlWithCache;
            }
        }
    }
    
    menuItems.forEach(item => {
        const link = item.querySelector('.menu-link');
        const submenu = item.querySelector('.submenu');
        
        link.addEventListener('click', async (e) => {
            e.preventDefault();
            
            // Si NO tiene submenú Y tiene una ruta → Cargar la página
            if (!submenu && link.dataset.target && link.dataset.target !== '#') {
                console.log('[MENU] Item sin submenú, cargando página:', link.dataset.target);
                await loadPage(link.dataset.target);
                // Cerrar otros menús y activar este
                closeOtherMenus(item);
                item.classList.add('active');
                aplicarEstiloActivo(item, true);
                if (!activeMenus.includes(link.textContent)) {
                    activeMenus.push(link.textContent);
                    sessionStorage.setItem('activeMenus', JSON.stringify(activeMenus));
                }
                return;
            }
            
            // Si tiene submenú → Solo toggle expand/collapse
            console.log('[MENU] Item con submenú, toggle expand/collapse');
            
            // Cerrar otros menús
            closeOtherMenus(item);
            
            // Si el ítem ya está activo, lo desactivamos
            if (item.classList.contains('active')) {
                console.log('[MENU] ❌ Desactivando menú:', link.textContent);
                item.classList.remove('active');
                aplicarEstiloActivo(item, false);
                // Eliminar del array de activos
                const index = activeMenus.indexOf(link.textContent);
                if (index > -1) {
                    activeMenus.splice(index, 1);
                }
            } else {
                console.log('[MENU] ✅ Activando menú:', link.textContent);
                item.classList.add('active');
                aplicarEstiloActivo(item, true);
                console.log('[MENU] Clase active añadida. classList:', item.classList.value);
                // Añadir al array de activos
                activeMenus.push(link.textContent);
            }
            // Guardar estado en sessionStorage
            sessionStorage.setItem('activeMenus', JSON.stringify(activeMenus));
        });
    });
    
    // Manejar los enlaces de submenú
    const submenuLinks = document.querySelectorAll('.submenu-item:not(.submenu-header)');
    console.log('[MENU] Submenu links (no headers) encontrados:', submenuLinks.length);
    submenuLinks.forEach(link => {
        link.addEventListener('click', async (e) => {
            e.preventDefault();
            
            // Cargar la página en el iframe si tiene un target
            if (link.dataset.target && link.dataset.target !== '#') {
                console.log('[MENU] Cargando submenú:', link.dataset.target);
                await loadPage(link.dataset.target);
            }
            
            // Actualizar la clase activa en el menú principal
            const menuItem = link.closest('.menu-item');
            if (!menuItem.classList.contains('active')) {
                closeOtherMenus(menuItem);
                menuItem.classList.add('active');
                aplicarEstiloActivo(menuItem, true);
                // Añadir al array de activos si no está ya
                const menuTitle = menuItem.querySelector('.menu-link').textContent;
                if (!activeMenus.includes(menuTitle)) {
                    activeMenus.push(menuTitle);
                    sessionStorage.setItem('activeMenus', JSON.stringify(activeMenus));
                }
            }
        });
    });

    // NO abrir ningún menú por defecto
}

// Inicializar eventos cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', inicializarEventosMenu);

// Reinicializar cuando se renderice el menú dinámicamente
window.addEventListener('menuRendered', inicializarEventosMenu);
