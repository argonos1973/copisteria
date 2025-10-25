// Cargador de menú dinámico
// Sistema multiempresa - carga menú según permisos del usuario

async function verificarSesionYCargarMenu() {
    try {
        console.log('[MENU] Iniciando carga de menú según permisos...');
        
        const menuResponse = await fetch('/api/auth/menu');
        
        if (!menuResponse.ok) {
            throw new Error(`Error ${menuResponse.status}: ${menuResponse.statusText}`);
        }
        
        const menuData = await menuResponse.json();
        console.log('[MENU] Menú recibido según permisos del usuario:', menuData);
        
        if (!menuData || menuData.length === 0) {
            console.warn('[MENU] Usuario sin permisos asignados');
            document.querySelector('.menu-list').innerHTML = `
                <li style="padding: 20px; color: white; text-align: center;">
                    <i class="fas fa-lock"></i>
                    <p style="margin: 10px 0;">Sin permisos asignados</p>
                    <p style="font-size: 12px; opacity: 0.8;">Contacte al administrador</p>
                </li>
            `;
            return;
        }
        
        renderizarMenu(menuData);
        
    } catch (error) {
        console.error('[MENU] Error cargando menú:', error);
        document.querySelector('.menu-list').innerHTML = `
            <li style="padding: 20px; color: white; text-align: center;">
                <i class="fas fa-exclamation-triangle"></i>
                <p style="margin: 10px 0;">Error cargando menú</p>
                <p style="font-size: 12px; opacity: 0.8;">${error.message}</p>
                <button onclick="location.reload()" style="margin-top: 10px; padding: 8px 16px; background: #e74c3c; color: white; border: none; border-radius: 4px; cursor: pointer;">Reintentar</button>
            </li>
        `;
    }
}

function renderizarMenu(menuItems) {
    const menuList = document.querySelector('.menu-list');
    if (!menuList) {
        console.error('[MENU] Contenedor .menu-list no encontrado');
        return;
    }
    
    menuList.innerHTML = '';
    
    // Renderizar módulos según permisos
    menuItems.forEach(modulo => {
        const menuItem = crearMenuItem(
            modulo.nombre,
            modulo.icono || 'fas fa-folder',
            modulo.ruta,
            modulo.submodulos
        );
        menuList.appendChild(menuItem);
    });
    
    console.log('[MENU] Menú renderizado correctamente');
    
    // Forzar reinicialización de eventos del menú después de un pequeño delay
    setTimeout(() => {
        // Disparar evento personalizado para que menu.js reconfigure eventos
        window.dispatchEvent(new Event('menuRendered'));
    }, 100);
}

function crearMenuItem(nombre, icono, ruta, submodulos) {
    const li = document.createElement('li');
    li.className = 'menu-item';

    const link = document.createElement('a');
    link.href = '#';
    link.className = 'menu-link';
    if (ruta && ruta !== '#') {
        link.dataset.target = ruta;
    }
    link.innerHTML = `<i class="${icono}"></i>${nombre}`;

    li.appendChild(link);

    if (submodulos && submodulos.length > 0) {
        const submenu = document.createElement('div');
        submenu.className = 'submenu';

        submodulos.forEach(sub => {
            // Si el submódulo tiene sus propios submódulos (anidados)
            if (sub.submodulos && sub.submodulos.length > 0) {
                const subBlock = document.createElement('div');
                subBlock.className = 'submenu-block';
                
                const subHeader = document.createElement('a');
                subHeader.href = '#';
                subHeader.className = 'submenu-item submenu-header';
                subHeader.innerHTML = `<i class="${sub.icono || 'fas fa-circle'}"></i> ${sub.nombre}`;
                subBlock.appendChild(subHeader);
                
                // Crear sub-submenu
                const subSubmenu = document.createElement('div');
                subSubmenu.className = 'submenu';
                
                sub.submodulos.forEach(subSub => {
                    const subSubLink = document.createElement('a');
                    subSubLink.href = '#';
                    subSubLink.className = 'submenu-item submenu-nested';
                    if (subSub.ruta && subSub.ruta !== '#') {
                        subSubLink.dataset.target = subSub.ruta;
                    }
                    subSubLink.innerHTML = `<i class="${subSub.icono || 'fas fa-circle'}"></i> ${subSub.nombre}`;
                    subSubmenu.appendChild(subSubLink);
                });
                
                subBlock.appendChild(subSubmenu);
                submenu.appendChild(subBlock);
            } else {
                // Submódulo simple sin anidamiento
                const subLink = document.createElement('a');
                subLink.href = '#';
                subLink.className = 'submenu-item';
                if (sub.ruta && sub.ruta !== '#') {
                    subLink.dataset.target = sub.ruta;
                }
                subLink.innerHTML = `<i class="${sub.icono || 'fas fa-circle'}"></i> ${sub.nombre}`;
                submenu.appendChild(subLink);
            }
        });

        li.appendChild(submenu);
    }

    return li;
}

// Exportar función
window.verificarSesionYCargarMenu = verificarSesionYCargarMenu;
