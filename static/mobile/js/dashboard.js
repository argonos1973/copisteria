document.addEventListener('DOMContentLoaded', () => {
    initDashboard();
});

async function initDashboard() {
    const hasPermission = await checkStatsPermission();
    if (hasPermission) {
        cargarResumen();
        cargarTickets();
    } else {
        const dashboard = document.querySelector('.dashboard-mobile');
        if(dashboard) dashboard.style.display = 'none';
    }
}

async function checkStatsPermission() {
    try {
        const res = await fetch('/api/auth/session');
        if(res.ok) {
            const data = await res.json();
            
            // Actualizar UI con datos de sesión
            updateSessionUI(data);

            // Permiso para estadísticas
            // Permitir si es admin de empresa, superadmin O si tiene rol 'admin'
            return data.es_admin_empresa || data.es_superadmin || data.rol === 'admin';
        }
        return false;
    } catch(e) {
        console.error('Error verificando permisos:', e);
        return false;
    }
}

function updateSessionUI(data) {
    // Header Logo
    const headerLogo = document.querySelector('.header-left img');
    if(headerLogo && data.logo) {
        headerLogo.src = data.logo; // data.logo viene con /static/logos/...
    }
    
    // Drawer Info
    const drawerUsername = document.getElementById('drawer-username');
    const drawerRol = document.getElementById('drawer-rol');
    const drawerLogo = document.querySelector('.drawer-header img');
    
    if(drawerUsername) drawerUsername.textContent = data.usuario || data.username;
    if(drawerRol) drawerRol.textContent = data.rol || 'Usuario';
    if(drawerLogo && data.logo) drawerLogo.src = data.logo;
}

async function cargarResumen() {
    const summaryCard = document.querySelector('.summary-card');
    try {
        // Consumir API existente de estadísticas
        const response = await fetch('/api/dashboard/estadisticas_gastos');
        
        // Manejo de permisos (backend status)
        if (response.status === 401 || response.status === 403) {
            console.warn("Usuario sin permisos para ver estadísticas");
            if(summaryCard) summaryCard.style.display = 'none';
            return;
        }

        if (!response.ok) throw new Error('Error cargando datos');
        
        const data = await response.json();
        
        // Actualizar UI
        if(data.ingresos_mes_actual !== undefined) {
            document.getElementById('ventas-hoy').textContent = formatCurrency(data.ingresos_mes_actual);
        }
        if(data.balance_mes_actual !== undefined) {
            document.getElementById('balance-mes').textContent = formatCurrency(data.balance_mes_actual);
        }
        
    } catch (error) {
        console.error('Error resumen:', error);
        if(summaryCard) summaryCard.style.display = 'none';
    }
}

async function cargarTickets() {
    try {
        // Pedir últimos 5 tickets
        const response = await fetch('/api/tickets/paginado?page=1&limit=5&orden=desc');
        if (!response.ok) throw new Error('Error cargando tickets');
        
        const data = await response.json();
        const tickets = data.tickets || data.data || data.items || []; // Ajustar según respuesta real
        
        const list = document.getElementById('ultimos-tickets-list');
        list.innerHTML = '';

        if (tickets.length === 0) {
            list.innerHTML = '<div style="padding:15px; text-align:center;">No hay tickets recientes</div>';
            return;
        }

        tickets.forEach(ticket => {
            const el = document.createElement('div');
            el.className = 'card ticket-item';
            el.onclick = () => window.location.href = `/api/auth/mobile/tickets/gestion?id=${ticket.id}`; // Editar
            
            // Determinar clase de estado
            let badgeClass = 'badge-success';
            let estadoTexto = ticket.estado;
            if(ticket.estado === 'P' || ticket.estado === 'Pendiente') {
                badgeClass = 'badge-warning';
                estadoTexto = 'Pendiente';
            } else if(ticket.estado === 'C' || ticket.estado === 'Cobrado') {
                badgeClass = 'badge-success';
                estadoTexto = 'Cobrado';
            } else {
                badgeClass = 'badge-danger';
            }

            el.innerHTML = `
                <div class="ticket-header">
                    <span class="ticket-id">${ticket.numero}</span>
                    <span class="ticket-status ${badgeClass}" style="background-color: ${badgeClass === 'badge-success' ? '#2ecc71' : (badgeClass === 'badge-warning' ? '#f39c12' : '#e74c3c')}; color: white; padding: 2px 8px; border-radius: 10px; font-size: 10px;">${estadoTexto}</span>
                </div>
                <div class="ticket-body">
                    <span class="ticket-date">${ticket.fecha}</span>
                    <span class="ticket-total">${formatCurrency(ticket.total)}</span>
                </div>
            `;
            list.appendChild(el);
        });
        
    } catch (error) {
        console.error('Error tickets:', error);
        document.getElementById('ultimos-tickets-list').innerHTML = '<div style="color:red; text-align:center;">Error cargando tickets</div>';
    }
}

function formatCurrency(value) {
    let num = value;
    if (typeof value === 'string') {
        num = parseFloat(value.replace(/\./g, '').replace(',', '.'));
    }
    
    if (num === null || num === undefined || isNaN(num)) {
        return new Intl.NumberFormat('es-ES', { style: 'currency', currency: 'EUR' }).format(0);
    }
    return new Intl.NumberFormat('es-ES', { style: 'currency', currency: 'EUR' }).format(num);
}
