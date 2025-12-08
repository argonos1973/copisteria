document.addEventListener('DOMContentLoaded', () => {
    console.log('Dashboard Móvil Iniciado');
    cargarResumen();
    cargarTickets();
});

async function cargarResumen() {
    try {
        // Consumir API existente de estadísticas
        const response = await fetch('/api/dashboard/estadisticas_gastos');
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
    return new Intl.NumberFormat('es-ES', { style: 'currency', currency: 'EUR' }).format(value);
}
