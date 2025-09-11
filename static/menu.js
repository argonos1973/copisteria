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
    
    // Cargar página en el iframe
    function loadPage(url) {
        if (url && url !== '#') {
            contentFrame.src = url;
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
            link.addEventListener('click', function(e) {
                e.preventDefault();
                loadPage(link.dataset.target);
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
        link.addEventListener('click', (e) => {
            // Si es un submenu-block, pero tiene data-target, SÍ debe cargar la página
            if (link.parentElement.classList.contains('submenu-block') && !link.dataset.target) return;
            e.preventDefault();
            
            // Cargar la página en el iframe si tiene un target
            if (link.dataset.target && link.dataset.target !== '#') {
                loadPage(link.dataset.target);
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
