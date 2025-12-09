document.addEventListener('DOMContentLoaded', () => {
    console.log('Mobile App Loaded');
    
    // Iniciar componentes
    setupDrawer();
    setupNavigation();
    
    // Cargar datos
    cargarUsuario();
    cargarMenu();
});

function setupNavigation() {
    const navItems = document.querySelectorAll('.bottom-nav .nav-item');
    navItems.forEach(item => {
        item.addEventListener('click', (e) => {
            // Lógica simple de cambio de clase active
            // En una SPA real, aquí cambiaríamos la vista
            navItems.forEach(nav => nav.classList.remove('active'));
            item.classList.add('active');
        });
    });
}

// === Drawer Logic ===
function setupDrawer() {
    const btnOpen = document.getElementById('btn-menu-drawer');
    const btnClose = document.getElementById('btn-close-drawer');
    const drawer = document.getElementById('mobile-drawer');
    const overlay = document.getElementById('drawer-overlay');
    
    function toggleDrawer(show) {
        if (show) {
            drawer.classList.add('active');
            overlay.classList.add('active');
        } else {
            drawer.classList.remove('active');
            overlay.classList.remove('active');
        }
    }
    
    if(btnOpen) btnOpen.addEventListener('click', () => toggleDrawer(true));
    if(btnClose) btnClose.addEventListener('click', () => toggleDrawer(false));
    if(overlay) overlay.addEventListener('click', () => toggleDrawer(false));
}

async function cargarUsuario() {
    try {
        const response = await fetch('/api/auth/session');
        if(response.ok) {
            const data = await response.json();
            const elUser = document.getElementById('drawer-username');
            const elRol = document.getElementById('drawer-rol');
            const drawerLogo = document.querySelector('.drawer-header img');
            const headerLogo = document.querySelector('.header-left img'); // Header principal

            if(elUser) elUser.textContent = data.usuario || data.username;
            if(elRol) elRol.textContent = data.rol || 'Usuario';
            
            // Actualizar logos
            if(data.logo) {
                if(drawerLogo) drawerLogo.src = data.logo;
                if(headerLogo && !headerLogo.src.includes(data.logo)) {
                     headerLogo.src = data.logo;
                }
            }
        }
    } catch(e) { console.error('Error cargando usuario', e); }
}

async function cargarMenu() {
    try {
        const response = await fetch('/api/auth/menu');
        if(!response.ok) throw new Error('Error al obtener menú');
        
        const menuData = await response.json();
        renderMenu(menuData);
        
    } catch (error) {
        console.error('Error menú:', error);
        document.getElementById('drawer-menu-list').innerHTML = '<div style="padding:20px; text-align:center; color:red;">Error cargando menú</div>';
    }
}

function renderMenu(items) {
    const container = document.getElementById('drawer-menu-list');
    container.innerHTML = '';
    
    items.forEach(item => {
        // Renderizar item principal
        if (item.submenu && item.submenu.length > 0) {
            // Contenedor del grupo
            const groupDiv = document.createElement('div');
            groupDiv.className = 'drawer-group';
            
            // Header clickable (Toggle)
            const header = document.createElement('div');
            header.className = 'drawer-submenu-header';
            header.innerHTML = `<span><i class="${item.icono}"></i> ${item.nombre}</span> <i class="fas fa-chevron-down arrow"></i>`;
            header.onclick = () => {
                groupDiv.classList.toggle('open');
            };
            groupDiv.appendChild(header);
            
            // Contenedor de items del submenu
            const subContainer = document.createElement('div');
            subContainer.className = 'drawer-submenu-items';
            
            item.submenu.forEach(sub => {
                const link = createMenuItem(sub);
                subContainer.appendChild(link);
            });
            groupDiv.appendChild(subContainer);
            
            container.appendChild(groupDiv);
            
        } else {
            const link = createMenuItem(item);
            container.appendChild(link);
        }
    });
}

function createMenuItem(item) {
    const a = document.createElement('a');
    a.className = 'drawer-menu-item';
    
    // Interceptar rutas para versión móvil
    let href = item.ruta;
    if(href === '/CONSULTA_TICKETS.html') href = '/api/auth/mobile/tickets';
    if(href === '/GESTION_TICKETS.html') href = '/api/auth/mobile/tickets/gestion';
    if(href === '/CONSULTA_FACTURAS.html') href = '/api/auth/mobile/facturas';
    if(href === '/GESTION_FACTURAS.html') href = '/api/auth/mobile/facturas/gestion';
    
    if(href === '/CONSULTA_GASTOS.html') href = '/api/auth/mobile/gastos';
    
    if(href === '/CONSULTA_CONTACTOS.html') href = '/api/auth/mobile/contactos';
    if(href === '/GESTION_CONTACTOS.html') href = '/api/auth/mobile/contactos/gestion';
    
    if(href === '/CONSULTA_PRODUCTOS.html') href = '/api/auth/mobile/productos';
    if(href === '/GESTION_PRODUCTOS.html') href = '/api/auth/mobile/productos/gestion';
    
    if(href === '/CONSULTA_PRESUPUESTOS.html') href = '/api/auth/mobile/presupuestos';
    if(href === '/GESTION_PRESUPUESTOS.html') href = '/api/auth/mobile/presupuestos/gestion';
    
    if(href === '/CONSULTA_PROFORMAS.html') href = '/api/auth/mobile/proformas';
    if(href === '/GESTION_PROFORMAS.html') href = '/api/auth/mobile/proformas/gestion';
    
    a.href = href === '#' ? 'javascript:void(0)' : href;
    
    // Si es una ruta relativa html, asegurar que funcione en móvil (quizás necesite prefijo o manejo de ruta)
    // Por ahora asumimos que las rutas HTML funcionan (abren nueva página)
    
    a.innerHTML = `<i class="${item.icono}"></i> <span>${item.nombre}</span>`;
    return a;
}

async function logoutApp() {
    if(confirm('¿Cerrar sesión?')) {
        try {
            await fetch('/api/auth/logout', { method: 'POST' });
            window.location.href = '/index.html';
        } catch(e) {
            alert('Error al cerrar sesión');
        }
    }
}
