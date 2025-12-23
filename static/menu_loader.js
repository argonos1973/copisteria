// Cargador de menú dinámico
// Sistema multiempresa - carga menú según permisos del usuario

async function verificarSesionYCargarMenu() {
    try {
        console.log('[MENU] Iniciando carga de menú según permisos...');
        
        // 1. OBTENER DATOS DE SESIÓN (con caché)
        let sessionData = null;
        const cachedSession = sessionStorage.getItem('aleph70_session_data');
        
        if (cachedSession) {
            sessionData = JSON.parse(cachedSession);
            console.log('[MENU] ⚡ Usando sesión en caché');
        } else {
            const sessionResponse = await fetch('/api/auth/session', { credentials: 'include' });
            if (!sessionResponse.ok) {
                console.error('[MENU] Sesión no válida');
                window.location.href = '/LOGIN.html';
                return;
            }
            sessionData = await sessionResponse.json();
            sessionStorage.setItem('aleph70_session_data', JSON.stringify(sessionData));
        }
        
        console.log('[MENU] Datos de sesión:', sessionData);
        
        // Actualizar info de usuario
        actualizarInfoUsuario(sessionData);
        
        // Verificar estado de suscripción (trial, activa, expirada)
        verificarSuscripcion(sessionData);
        
        // 2. CARGAR EL MENÚ (con caché)
        let menuData = null;
        const cachedMenu = sessionStorage.getItem('aleph70_menu_data');
        
        const fetchMenu = async () => {
            const menuResponse = await fetch('/api/auth/menu', { credentials: 'include' });
            if (!menuResponse.ok) {
                throw new Error(`Error ${menuResponse.status}: ${menuResponse.statusText}`);
            }
            const fresh = await menuResponse.json();
            sessionStorage.setItem('aleph70_menu_data', JSON.stringify(fresh));
            return fresh;
        };

        if (cachedMenu) {
            menuData = JSON.parse(cachedMenu);
            console.log('[MENU] ⚡ Usando menú en caché');

            const esAdmin = sessionData && (sessionData.es_admin_empresa || sessionData.es_superadmin);
            if (esAdmin) {
                const adminItem = Array.isArray(menuData) ? menuData.find(i => i && i.codigo === 'admin') : null;
                const adminSub = adminItem && Array.isArray(adminItem.submenu) ? adminItem.submenu : [];
                const tieneProcesos = adminSub.some(s => s && (s.nombre === 'Procesos' || s.ruta === '/ADMIN_BATCH.html'));
                if (!tieneProcesos) {
                    console.log('[MENU] Menú admin cacheado sin Procesos, recargando desde servidor...');
                    menuData = await fetchMenu();
                }
            }
        } else {
            menuData = await fetchMenu();
        }

        // Fallback: si el backend aún no devolvió el subitem, inyectarlo para admins
        try {
            const esAdminFinal = sessionData && (sessionData.es_admin_empresa || sessionData.es_superadmin);
            if (esAdminFinal && Array.isArray(menuData)) {
                const adminItem = menuData.find(i => i && i.codigo === 'admin');
                if (adminItem) {
                    adminItem.submenu = Array.isArray(adminItem.submenu) ? adminItem.submenu : [];
                    const tieneProcesos = adminItem.submenu.some(s => s && (s.nombre === 'Procesos' || s.ruta === '/ADMIN_BATCH.html'));
                    if (!tieneProcesos) {
                        adminItem.submenu.push({
                            nombre: 'Procesos',
                            icono: 'fas fa-clock',
                            ruta: '/ADMIN_BATCH.html'
                        });
                        sessionStorage.setItem('aleph70_menu_data', JSON.stringify(menuData));
                        console.log('[MENU] Fallback aplicado: submenú Procesos añadido a Administración');
                    }
                }
            }
        } catch (e) {
            // noop
        }
        
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
        
        renderizarMenu(menuData, sessionData);
        
        // Cargar página inicial en el iframe según tipo de usuario
        const tieneEmpresa = sessionData && sessionData.empresa && sessionData.empresa !== 'Sin Empresa';
        const esAdmin = sessionData && sessionData.es_admin_empresa;
        const paginaInicial = (tieneEmpresa && esAdmin) ? '/estadisticas.html' : '/bienvenida.html';
        
        console.log('[MENU] sessionData completo:', sessionData);
        console.log('[MENU] empresa:', sessionData?.empresa);
        console.log('[MENU] tiene empresa:', tieneEmpresa);
        console.log('[MENU] es_admin_empresa:', sessionData?.es_admin_empresa);
        console.log('[MENU] Usuario es admin:', esAdmin);
        console.log('[MENU] Página a cargar:', paginaInicial);
        
        const iframe = document.getElementById('content-frame');
        if (iframe) {
            iframe.src = paginaInicial;
            console.log('[MENU] ✅ Iframe src configurado a:', iframe.src);
            
            // Verificar que se cargó correctamente
            iframe.onload = () => {
                console.log('[MENU] ✅ Iframe cargado correctamente:', iframe.contentWindow.location.href);
            };
            
            iframe.onerror = (e) => {
                console.error('[MENU] ❌ Error cargando iframe:', e);
                console.error('[MENU] Intentando cargar página alternativa...');
                iframe.src = '/bienvenida.html';
            };
        } else {
            console.error('[MENU] ❌ Iframe content-frame no encontrado');
            // Reintentar después de un momento
            setTimeout(() => {
                const iframeRetry = document.getElementById('content-frame');
                if (iframeRetry) {
                    iframeRetry.src = paginaInicial;
                    console.log('[MENU] ✅ Iframe encontrado en reintento, cargando:', paginaInicial);
                }
            }, 500);
        }
        
        // Inicializar sistema de permisos
        if (typeof inicializarPermisos === 'function') {
            inicializarPermisos(menuData);
        }
        
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
        // Agregar timestamp para evitar caché
        const timestamp = new Date().getTime();
        logoEmpresa.src = sessionData.logo + '?t=' + timestamp;
        logoEmpresa.style.display = 'block';
        logoEmpresa.onerror = function() {
            console.error('[MENU] Error cargando logo:', sessionData.logo);
            this.src = '/static/logos/aleph70_default.svg';
        };
        console.log('[MENU] Logo actualizado a:', sessionData.logo);
    } else {
        console.warn('[MENU] Logo no disponible en sessionData:', sessionData);
    }
    
    // Actualizar avatar del usuario
    const menuAvatar = document.getElementById('menu-usuario-avatar');
    if (menuAvatar && sessionData.avatar) {
        const timestamp = new Date().getTime();
        menuAvatar.src = sessionData.avatar + '?t=' + timestamp;
        menuAvatar.onerror = function() {
            console.error('[MENU] Error cargando avatar:', sessionData.avatar);
            this.src = '/static/avatars/default.svg';
        };
        console.log('[MENU] Avatar actualizado:', sessionData.avatar);
    } else if (menuAvatar) {
        menuAvatar.src = '/static/avatars/default.svg';
    }
    
    // Actualizar info en menú (usar IDs correctos del HTML)
    const menuUsuario = document.getElementById('menu-usuario-nombre');
    const menuEmpresa = document.getElementById('menu-empresa-nombre');
    const menuUltimoAcceso = document.getElementById('menu-ultimo-acceso');
    
    if (menuUsuario) {
        menuUsuario.textContent = sessionData.usuario || 'Usuario';
        console.log('[MENU] Usuario actualizado:', sessionData.usuario);
    } else {
        console.warn('[MENU] Elemento menu-usuario-nombre NO encontrado en el DOM');
    }
    
    if (menuEmpresa) {
        menuEmpresa.textContent = sessionData.empresa || 'Empresa';
        console.log('[MENU] Empresa actualizada:', sessionData.empresa);
    } else {
        console.warn('[MENU] Elemento menu-empresa-nombre NO encontrado en el DOM');
    }
    
    // Mostrar último acceso
    if (menuUltimoAcceso && sessionData.ultimo_acceso) {
        mostrarUltimoAcceso(sessionData.ultimo_acceso);
    } else if (menuUltimoAcceso) {
        menuUltimoAcceso.textContent = 'Primer acceso';
    }
}

function mostrarUltimoAcceso(ultimoAcceso) {
    const menuTime = document.getElementById('menu-ultimo-acceso');
    if (!menuTime) {
        console.warn('[MENU] Elemento menu-ultimo-acceso no encontrado');
        return;
    }
    
    if (!ultimoAcceso) {
        menuTime.textContent = 'Primer acceso';
        return;
    }
    
    try {
        const fecha = new Date(ultimoAcceso);
        const hoy = new Date();
        const ayer = new Date(hoy);
        ayer.setDate(ayer.getDate() - 1);
        
        const esHoy = fecha.toDateString() === hoy.toDateString();
        const esAyer = fecha.toDateString() === ayer.toDateString();
        
        const hora = fecha.toLocaleTimeString('es-ES', { 
            hour: '2-digit', 
            minute: '2-digit' 
        });
        
        if (esHoy) {
            menuTime.textContent = `Hoy a las ${hora}`;
        } else if (esAyer) {
            menuTime.textContent = `Ayer a las ${hora}`;
        } else {
            const dia = fecha.toLocaleDateString('es-ES', { 
                day: '2-digit', 
                month: '2-digit' 
            });
            menuTime.textContent = `${dia} a las ${hora}`;
        }
    } catch (error) {
        console.error('[MENU] Error formateando fecha último acceso:', error);
        menuTime.textContent = 'Hace tiempo';
    }
}

function renderizarMenu(menuItems, sessionData) {
    const menuList = document.querySelector('.menu-list');
    if (!menuList) {
        console.error('[MENU] Contenedor .menu-list no encontrado');
        return;
    }
    
    menuList.innerHTML = '';
    
    // Determinar página de inicio según tipo de usuario
    const tieneEmpresa = sessionData && sessionData.empresa && sessionData.empresa !== 'Sin Empresa';
    const esAdmin = sessionData && sessionData.es_admin_empresa;
    const paginaInicio = (tieneEmpresa && esAdmin) ? '/estadisticas.html' : '/bienvenida.html';
    
    console.log(`[MENU] Usuario tiene empresa: ${tieneEmpresa}, es admin: ${esAdmin}, página inicio: ${paginaInicio}`);
    
    // Siempre añadir "Inicio" primero
    const inicioItem = crearMenuItem('Inicio', 'fas fa-home', paginaInicio, null);
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

// Verificar estado de suscripción y mostrar banner de trial
async function verificarSuscripcion(sessionData) {
    try {
        if (!sessionData || !sessionData.empresa_id) return;
        
        const response = await fetch(`/api/subscription/status/${sessionData.empresa_id}`, {
            credentials: 'include'
        });
        
        if (!response.ok) return;
        
        const sub = await response.json();
        console.log('[SUBSCRIPTION] Estado:', sub);
        
        // Guardar en sessionStorage para uso en otras páginas
        sessionStorage.setItem('aleph70_subscription', JSON.stringify(sub));
        
        // Mostrar banner según estado
        if (sub.status === 'free_trial') {
            mostrarBannerTrial(sub.days_remaining);
        } else if (sub.status === 'expired' || (sub.status === 'free_trial' && sub.days_remaining <= 0)) {
            mostrarBannerExpirado();
        }
        
    } catch (e) {
        console.error('[SUBSCRIPTION] Error verificando:', e);
    }
}

function mostrarBannerTrial(diasRestantes) {
    // Evitar duplicados
    if (document.getElementById('trial-banner')) return;
    
    const banner = document.createElement('div');
    banner.id = 'trial-banner';
    banner.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        background: linear-gradient(135deg, #3498db, #2ecc71);
        color: white;
        padding: 10px 20px;
        text-align: center;
        font-size: 14px;
        font-weight: 500;
        z-index: 10000;
        box-shadow: 0 2px 10px rgba(0,0,0,0.2);
    `;
    
    const diasTexto = diasRestantes === 1 ? 'día' : 'días';
    const urgencia = diasRestantes <= 3 ? '⚠️' : '🎁';
    
    banner.innerHTML = `
        ${urgencia} <strong>Periodo de prueba:</strong> Te quedan <strong>${diasRestantes} ${diasTexto}</strong> de prueba gratuita
        <a href="/SUSCRIPCION.html" style="color: white; margin-left: 15px; background: rgba(255,255,255,0.2); padding: 5px 15px; border-radius: 20px; text-decoration: none;">
            Suscribirse ahora
        </a>
        <button onclick="this.parentElement.remove()" style="position: absolute; right: 10px; top: 50%; transform: translateY(-50%); background: none; border: none; color: white; font-size: 18px; cursor: pointer;">×</button>
    `;
    
    document.body.insertBefore(banner, document.body.firstChild);
    
    // Ajustar padding del body para no tapar contenido
    document.body.style.paddingTop = '45px';
}

function mostrarBannerExpirado() {
    // Evitar duplicados
    if (document.getElementById('expired-banner')) return;
    
    const banner = document.createElement('div');
    banner.id = 'expired-banner';
    banner.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(0,0,0,0.9);
        color: white;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        z-index: 10001;
        text-align: center;
        padding: 40px;
    `;
    
    banner.innerHTML = `
        <div style="max-width: 500px;">
            <i class="fas fa-clock" style="font-size: 60px; color: #e74c3c; margin-bottom: 20px;"></i>
            <h2 style="margin-bottom: 15px; font-size: 28px;">Tu periodo de prueba ha terminado</h2>
            <p style="margin-bottom: 30px; opacity: 0.8; font-size: 16px;">
                Para seguir usando Aleph70, activa tu suscripción y accede a todas las funcionalidades.
            </p>
            <a href="/SUSCRIPCION.html" style="display: inline-block; background: #2ecc71; color: white; padding: 15px 40px; border-radius: 30px; text-decoration: none; font-weight: 600; font-size: 18px;">
                Activar suscripción
            </a>
            <p style="margin-top: 20px; font-size: 14px; opacity: 0.6;">
                <a href="/api/auth/logout" style="color: white;">Cerrar sesión</a>
            </p>
        </div>
    `;
    
    document.body.appendChild(banner);
}

// Formatear y mostrar último acceso
function mostrarUltimoAcceso(ultimoAcceso) {
    const menuUltimoAcceso = document.getElementById('menu-ultimo-acceso');
    if (!menuUltimoAcceso) return;
    
    if (!ultimoAcceso) {
        menuUltimoAcceso.textContent = 'Primer acceso';
        return;
    }
    
    try {
        const fecha = new Date(ultimoAcceso);
        const opciones = { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' };
        menuUltimoAcceso.textContent = fecha.toLocaleString('es-ES', opciones);
    } catch (e) {
        menuUltimoAcceso.textContent = ultimoAcceso;
    }
}
