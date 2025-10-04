document.addEventListener('DOMContentLoaded', function() {
    // Eliminar cualquier estado guardado de menús activos
    sessionStorage.removeItem('activeMenus');

    const menuItems = document.querySelectorAll('.menu-item');
    const contentFrame = document.getElementById('content-frame');
    
    // NO restaurar el estado del menú de sessionStorage
    // const activeMenus = JSON.parse(sessionStorage.getItem('activeMenus') || '[]');
    let activeMenus = [];
    
    // --- SUBMENÚS ANIDADOS ---
    // Gestionar el despliegue de los submenu-block (Tickets, Proformas, etc. dentro de Facturas Emitidas)
    const submenuBlocks = document.querySelectorAll('.submenu-block > .submenu-item');
    submenuBlocks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const block = link.parentElement;
            // Plegar todos los bloques hermanos
            const allBlocks = block.parentElement.querySelectorAll('.submenu-block');
            allBlocks.forEach(b => {
                if (b !== block) b.classList.remove('active');
            });
            // Alternar el bloque clicado
            block.classList.toggle('active');
        });
    });

    // Función para cerrar todos los submenús excepto el actual
    function closeOtherMenus(currentItem) {
        menuItems.forEach(item => {
            if (item !== currentItem && item.classList.contains('active')) {
                item.classList.remove('active');
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
            // Si hay función navegarSeguro en el iframe, usarla
            try {
                const iframeWindow = contentFrame.contentWindow;
                if (iframeWindow && iframeWindow.navegarSeguro) {
                    await iframeWindow.navegarSeguro(url);
                } else if (iframeWindow && iframeWindow.__verificarCambiosGlobal) {
                    const hayCambios = iframeWindow.__verificarCambiosGlobal();
                    console.log('[Menu] Verificando cambios:', hayCambios);
                    if (hayCambios) {
                        // Usar mostrarConfirmacion global del padre (index.html)
                        if (window.mostrarConfirmacion) {
                            const guardar = await window.mostrarConfirmacion('Hay cambios sin guardar. ¿Desea guardarlos antes de salir?');
                            console.log('[Menu] Usuario respondió:', guardar ? 'Guardar' : 'No guardar');
                            const callbackGuardar = iframeWindow.__callbackGuardarGlobal;
                            if (guardar && callbackGuardar) {
                                try {
                                    console.log('[Menu] Ejecutando callback de guardar...');
                                    await callbackGuardar();
                                    console.log('[Menu] Guardado completado');
                                    // Esperar un poco más para asegurar que el guardado termine
                                    await new Promise(resolve => setTimeout(resolve, 1000));
                                    console.log('[Menu] Navegando después de guardar a:', url);
                                    contentFrame.src = url;
                                    return;
                                } catch (e) {
                                    console.error('[Menu] Error al guardar:', e);
                                    return; // No navegar si falla el guardado
                                }
                            } else if (!guardar) {
                                // Usuario decidió no guardar, continuar
                                console.log('[Menu] Navegando sin guardar');
                                contentFrame.src = url;
                                return;
                            } else {
                                console.log('[Menu] Cancelando navegación');
                                return; // Cancelar navegación
                            }
                        }
                    }
                    console.log('[Menu] No hay cambios, navegando a:', url);
                    contentFrame.src = url;
                } else {
                    contentFrame.src = url;
                }
            } catch (e) {
                // Si falla, navegar normalmente
                contentFrame.src = url;
            }
        }
    }
    
    menuItems.forEach(item => {
        const link = item.querySelector('.menu-link');
        
        // No restaurar estado activo
        // if (activeMenus.includes(link.textContent)) {
        //     item.classList.add('active');
        // }
        
        // Cargar página si el enlace tiene un target
        if (link.dataset.target && link.dataset.target !== '#') {
            link.addEventListener('click', async function(e) {
                e.preventDefault();
                await loadPage(link.dataset.target);
            });
        }
        
        link.addEventListener('click', (e) => {
            e.preventDefault();
            
            // Cerrar otros menús
            closeOtherMenus(item);
            
            // Si el ítem ya está activo, lo desactivamos
            if (item.classList.contains('active')) {
                item.classList.remove('active');
                // Eliminar del array de activos
                const index = activeMenus.indexOf(link.textContent);
                if (index > -1) {
                    activeMenus.splice(index, 1);
                }
            } else {
                item.classList.add('active');
                // Añadir al array de activos
                activeMenus.push(link.textContent);
            }
            // Guardar estado en sessionStorage
            sessionStorage.setItem('activeMenus', JSON.stringify(activeMenus));
        });
    });
    
    // Manejar los enlaces de submenú
    const submenuLinks = document.querySelectorAll('.submenu-item');
    submenuLinks.forEach(link => {
        link.addEventListener('click', async (e) => {
            // Si es un submenu-block, pero tiene data-target, SÍ debe cargar la página
            if (link.parentElement.classList.contains('submenu-block') && !link.dataset.target) return;
            e.preventDefault();
            
            // Cargar la página en el iframe si tiene un target
            if (link.dataset.target && link.dataset.target !== '#') {
                await loadPage(link.dataset.target);
            }
            
            // Actualizar la clase activa en el menú principal
            const menuItem = link.closest('.menu-item');
            if (!menuItem.classList.contains('active')) {
                closeOtherMenus(menuItem);
                menuItem.classList.add('active');
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
    // if (menuItems.length > 0 && !activeMenus.length) {
    //     const firstMenuItem = menuItems[0];
    //     firstMenuItem.classList.add('active');
    //     const menuTitle = firstMenuItem.querySelector('.menu-link').textContent;
    //     activeMenus.push(menuTitle);
    //     sessionStorage.setItem('activeMenus', JSON.stringify(activeMenus));
    // }
});
