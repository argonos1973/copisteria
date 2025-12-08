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
            if(elUser) elUser.textContent = data.usuario || data.username;
            if(elRol) elRol.textContent = data.rol || 'Usuario';
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
            // Cabecera de grupo (opcional) o items directos si son importantes
            // En móvil a veces es mejor aplanar o mostrar subcabeceras
            const header = document.createElement('div');
            header.className = 'drawer-submenu-header';
            header.textContent = item.nombre;
            container.appendChild(header);
            
            item.submenu.forEach(sub => {
                const link = createMenuItem(sub);
                container.appendChild(link);
            });
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
    // Futuro: if(href === '/CONSULTA_FACTURAS.html') href = '/api/auth/mobile/facturas';
    
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
