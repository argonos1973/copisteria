// Cargador de menú dinámico
// Sistema multiempresa - carga menú según permisos del usuario

async function verificarSesionYCargarMenu() {
    try {
        console.log('[MENU] Iniciando carga de menú según permisos...');
        
        // Primero obtener datos de sesión
        const sessionResponse = await fetch('/api/auth/session');
        if (!sessionResponse.ok) {
            console.error('[MENU] Sesión no válida');
            window.location.href = '/LOGIN.html';
            return;
        }
        
        const sessionData = await sessionResponse.json();
        console.log('[MENU] Datos de sesión:', sessionData);
        
        // Actualizar info de usuario
        actualizarInfoUsuario(sessionData);
        
        // Luego cargar el menú
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

function actualizarInfoUsuario(sessionData) {
    console.log('[MENU] Actualizando info de usuario:', sessionData);
    
    // Actualizar logo de la empresa
    const logoEmpresa = document.getElementById('logo-empresa');
    if (logoEmpresa && sessionData.logo) {
        logoEmpresa.src = sessionData.logo;
        logoEmpresa.style.display = 'block';
        console.log('[MENU] Logo actualizado a:', sessionData.logo);
    }
    
    // Actualizar info en menú superior (header)
    const topUsuario = document.getElementById('top-usuario');
    const topEmpresa = document.getElementById('top-empresa');
    
    if (topUsuario) {
        topUsuario.textContent = sessionData.usuario || 'Usuario';
    }
    if (topEmpresa) {
        topEmpresa.textContent = sessionData.empresa || 'Empresa';
    }
    
    // Actualizar info en menú inferior
    const bottomUsuario = document.getElementById('bottom-usuario');
    const bottomEmpresa = document.getElementById('bottom-empresa');
    const bottomTime = document.getElementById('bottom-time');
    
    if (bottomUsuario) {
        bottomUsuario.textContent = sessionData.usuario || 'Usuario';
        console.log('[MENU] Usuario actualizado:', sessionData.usuario);
    }
    if (bottomEmpresa) {
        bottomEmpresa.textContent = sessionData.empresa || 'Empresa';
        console.log('[MENU] Empresa actualizada:', sessionData.empresa);
    }
    
    // Mostrar último acceso
    if (bottomTime && sessionData.ultimo_acceso) {
        mostrarUltimoAcceso(sessionData.ultimo_acceso);
    }
}

function mostrarUltimoAcceso(ultimoAcceso) {
    const bottomTime = document.getElementById('bottom-time');
    if (!bottomTime) return;
    
    if (!ultimoAcceso) {
        bottomTime.textContent = 'Primer acceso';
        return;
    }
    
    try {
        const fecha = new Date(ultimoAcceso);
        const hoy = new Date();
        const ayer = new Date(hoy);
        ayer.setDate(ayer.getDate() - 1);
        
        const esMismoDia = fecha.toDateString() === hoy.toDateString();
        const esAyer = fecha.toDateString() === ayer.toDateString();
        
        const horas = String(fecha.getHours()).padStart(2, '0');
        const minutos = String(fecha.getMinutes()).padStart(2, '0');
        const horaStr = `${horas}:${minutos}`;
        
        if (esMismoDia) {
            bottomTime.textContent = `Hoy ${horaStr}`;
        } else if (esAyer) {
            bottomTime.textContent = `Ayer ${horaStr}`;
        } else {
            const dia = String(fecha.getDate()).padStart(2, '0');
            const mes = String(fecha.getMonth() + 1).padStart(2, '0');
            bottomTime.textContent = `${dia}/${mes} ${horaStr}`;
        }
    } catch (error) {
        console.error('[MENU] Error formateando último acceso:', error);
        bottomTime.textContent = 'No disponible';
    }
}

function renderizarMenu(menuItems) {
    const menuList = document.querySelector('.menu-list');
    if (!menuList) {
        console.error('[MENU] Contenedor .menu-list no encontrado');
        return;
    }
    
    menuList.innerHTML = '';
    
    // Siempre añadir "Inicio" primero
    const inicioItem = crearMenuItem('Inicio', 'fas fa-home', '/estadisticas.html', null);
    menuList.appendChild(inicioItem);
    console.log('[MENU] Item "Inicio" añadido');
    
    // Renderizar módulos según permisos
    menuItems.forEach(modulo => {
        console.log('[MENU] Módulo:', modulo.nombre, '- estructura:', modulo);
        console.log('[MENU] Campos:', Object.keys(modulo).join(', '));
        const menuItem = crearMenuItem(
            modulo.nombre,
            modulo.icono || 'fas fa-folder',
            modulo.ruta,
            modulo.submenu || modulo.submodulos  // ← API usa 'submenu', no 'submodulos'
        );
        menuList.appendChild(menuItem);
    });
    
    console.log('[MENU] Menú renderizado correctamente');
    
    // Cargar colores de la empresa DESPUÉS de renderizar el menú
    if (window.cargarColoresEmpresa) {
        console.log('[MENU] Cargando colores de empresa...');
        window.cargarColoresEmpresa();
    }
    
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
            const subSubmenuArray = sub.submenu || sub.submodulos || [];
            if (subSubmenuArray && subSubmenuArray.length > 0) {
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
                
                subSubmenuArray.forEach(subSub => {
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
