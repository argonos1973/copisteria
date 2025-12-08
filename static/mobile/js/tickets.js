let currentPage = 1;
let isLoading = false;
let hasMore = true;
let searchTimer = null;

document.addEventListener('DOMContentLoaded', () => {
    loadTickets(true);
    
    // Search listener
    document.getElementById('search-input').addEventListener('input', (e) => {
        clearTimeout(searchTimer);
        searchTimer = setTimeout(() => {
            currentPage = 1;
            hasMore = true;
            loadTickets(true, e.target.value);
        }, 500);
    });
    
    // Infinite scroll (simple version)
    window.addEventListener('scroll', () => {
        if ((window.innerHeight + window.scrollY) >= document.body.offsetHeight - 500) {
            if(!isLoading && hasMore) {
                loadTickets(false, document.getElementById('search-input').value);
            }
        }
    });
});

async function loadTickets(reset = false, query = '') {
    if(isLoading) return;
    isLoading = true;
    
    const container = document.getElementById('tickets-container');
    if(reset) {
        container.innerHTML = '<div class="loading-spinner"><i class="fas fa-circle-notch fa-spin"></i> Cargando...</div>';
    }

    try {
        let url = `/api/tickets/paginado?page=${currentPage}&limit=10&orden=desc`;
        if(query) url += `&search=${encodeURIComponent(query)}`;
        
        const response = await fetch(url);
        const data = await response.json();
        
        const tickets = data.tickets || data.data || data.items || [];
        
        if(reset) container.innerHTML = '';
        
        if(tickets.length === 0) {
            hasMore = false;
            if(reset) container.innerHTML = '<div style="text-align:center; padding:30px; color:#999;">No se encontraron tickets</div>';
        } else {
            tickets.forEach(ticket => {
                const card = createTicketCard(ticket);
                container.appendChild(card);
            });
            currentPage++;
        }

    } catch (error) {
        console.error('Error loading tickets:', error);
        if(reset) container.innerHTML = '<div style="text-align:center; color:red;">Error al cargar tickets</div>';
    } finally {
        isLoading = false;
    }
}

function createTicketCard(ticket) {
    const div = document.createElement('div');
    div.className = `ticket-card estado-${ticket.estado}`;
    div.onclick = () => window.location.href = `/api/auth/mobile/tickets/gestion?id=${ticket.id}`;
    
    // Formatear estado
    let estadoClass = '';
    let estadoText = ticket.estado;
    if(estadoText === 'C') estadoText = 'Cobrado';
    if(estadoText === 'P') estadoText = 'Pendiente';

    div.innerHTML = `
        <div class="tc-header">
            <span class="tc-number">${ticket.numero}</span>
            <span class="tc-date">${ticket.fecha}</span>
        </div>
        <div class="tc-client">${ticket.razonsocial || ticket.nombre_cliente || 'Cliente Contado'}</div>
        <div class="tc-footer">
            <span class="tc-total">${formatCurrency(ticket.total)}</span>
            <div class="tc-actions">
                <a href="/api/auth/mobile/tickets/gestion?id=${ticket.id}" class="btn-icon-action" onclick="event.stopPropagation()">
                    <i class="fas fa-pen"></i>
                </a>
            </div>
        </div>
    `;
    return div;
}

function formatCurrency(value) {
    return new Intl.NumberFormat('es-ES', { style: 'currency', currency: 'EUR' }).format(value);
}
