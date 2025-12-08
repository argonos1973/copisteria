let currentPage = 1;
let isLoading = false;
let hasMore = true;
let searchTimer = null;

document.addEventListener('DOMContentLoaded', () => {
    // Inicializar fechas y recuperar estado
    const today = new Date();
    const lastDay = new Date(today.getFullYear(), today.getMonth() + 1, 0);
    
    // Formato YYYY-MM-DD
    const formatDate = (d) => d.toISOString().split('T')[0];
    
    const inputDesde = document.getElementById('fecha-desde');
    const inputHasta = document.getElementById('fecha-hasta');
    const inputSearch = document.getElementById('search-input');
    
    // Recuperar filtros guardados
    const savedDesde = sessionStorage.getItem('tickets_filter_desde');
    const savedHasta = sessionStorage.getItem('tickets_filter_hasta');
    const savedSearch = sessionStorage.getItem('tickets_filter_search');
    
    if(inputDesde) inputDesde.value = savedDesde || formatDate(today);
    if(inputHasta) inputHasta.value = savedHasta || formatDate(lastDay);
    if(inputSearch && savedSearch) inputSearch.value = savedSearch;

    // Listeners con persistencia
    if(inputDesde) inputDesde.addEventListener('change', (e) => {
        e.target.blur(); // Cerrar calendario
        sessionStorage.setItem('tickets_filter_desde', e.target.value);
        reload();
    });
    if(inputHasta) inputHasta.addEventListener('change', (e) => {
        e.target.blur(); // Cerrar calendario
        sessionStorage.setItem('tickets_filter_hasta', e.target.value);
        reload();
    });
    document.getElementById('btn-refresh')?.addEventListener('click', () => reload());

    loadTickets(true);
    
    // Search listener
    if(inputSearch) {
        inputSearch.addEventListener('input', (e) => {
            sessionStorage.setItem('tickets_filter_search', e.target.value);
            clearTimeout(searchTimer);
            searchTimer = setTimeout(() => {
                reload();
            }, 500);
        });
    }
    
    // Infinite scroll
    const mobileContent = document.querySelector('.mobile-content');
    if (mobileContent) {
        mobileContent.addEventListener('scroll', () => {
            if ((mobileContent.scrollTop + mobileContent.clientHeight) >= mobileContent.scrollHeight - 300) {
                if(!isLoading && hasMore) {
                    loadTickets(false);
                }
            }
        });
    }
});

function reload() {
    currentPage = 1;
    hasMore = true;
    loadTickets(true);
}

async function loadTickets(reset = false) {
    if(isLoading) return;
    isLoading = true;
    
    const container = document.getElementById('tickets-container');
    const query = document.getElementById('search-input')?.value || '';
    const fDesde = document.getElementById('fecha-desde')?.value;
    const fHasta = document.getElementById('fecha-hasta')?.value;

    if(reset) {
        container.innerHTML = '<div class="loading-spinner"><i class="fas fa-circle-notch fa-spin"></i> Cargando...</div>';
    }

    try {
        let url = `/api/tickets/paginado?page=${currentPage}&limit=10&orden=desc`;
        if(query) url += `&search=${encodeURIComponent(query)}`;
        if(fDesde) url += `&fecha_inicio=${fDesde}`;
        if(fHasta) url += `&fecha_fin=${fHasta}`;
        
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
    if(estadoText === 'A') estadoText = 'Anulado';

    // Forma de Pago
    const paymentMap = { 'E': 'Efectivo', 'T': 'Tarjeta', 'R': 'Transf.', 'B': 'Bizum' };
    const formaPago = paymentMap[ticket.formaPago] || ticket.formaPago || 'Efectivo'; // Default a Efectivo si falta

    // Parsear fecha y hora
    let fechaDisplay = ticket.fecha;
    let horaDisplay = '';
    
    if (ticket.timestamp) {
        try {
            const dateObj = new Date(ticket.timestamp);
            if (!isNaN(dateObj.getTime())) {
                const day = dateObj.getDate().toString().padStart(2, '0');
                const month = (dateObj.getMonth() + 1).toString().padStart(2, '0');
                const year = dateObj.getFullYear();
                const hours = dateObj.getHours().toString().padStart(2, '0');
                const minutes = dateObj.getMinutes().toString().padStart(2, '0');
                fechaDisplay = `${day}/${month}/${year}`;
                horaDisplay = `${hours}:${minutes}`;
            }
        } catch(e) { console.error(e); }
    }

    div.innerHTML = `
        <div class="tc-header">
            <span class="tc-number">${ticket.numero}</span>
            <div class="tc-date-time" style="text-align: right;">
                <div class="tc-date">${fechaDisplay}</div>
                ${horaDisplay ? `<div class="tc-time" style="font-size: 11px; color: #999;">${horaDisplay}</div>` : ''}
            </div>
        </div>
        <div class="tc-client">${ticket.razonsocial || ticket.nombre_cliente || 'Cliente Contado'}</div>
        
        <div class="tc-details" style="margin-top: 8px; padding: 8px 0; border-top: 1px dashed #eee; border-bottom: 1px dashed #eee; font-size: 13px;">
            <div style="display: flex; justify-content: space-between; margin-bottom: 2px;">
                <span style="color: #7f8c8d;">Base:</span>
                <span>${formatCurrency(ticket.importe_bruto)}</span>
            </div>
            <div style="display: flex; justify-content: space-between; margin-bottom: 2px;">
                <span style="color: #7f8c8d;">IVA:</span>
                <span>${formatCurrency(ticket.importe_impuestos)}</span>
            </div>
            <div style="display: flex; justify-content: space-between;">
                <span style="color: #7f8c8d;">Total:</span>
                <span style="font-weight: 600;">${formatCurrency(ticket.total)}</span>
            </div>
        </div>

        <div class="tc-footer" style="border-top: none; padding-top: 5px;">
            <div style="display:flex; gap: 5px;">
                <span class="ticket-status ${ticket.estado === 'C' ? 'status-success' : 'status-warning'}" 
                      style="font-size: 11px; padding: 2px 8px; border-radius: 4px; background: ${ticket.estado === 'C' ? '#d4edda' : (ticket.estado === 'P' ? '#fff3cd' : '#f8d7da')}; color: ${ticket.estado === 'C' ? '#155724' : (ticket.estado === 'P' ? '#856404' : '#721c24')};">
                    ${estadoText}
                </span>
                <span class="ticket-payment" style="font-size: 11px; padding: 2px 8px; border-radius: 4px; background: #e2e6ea; color: #495057;">
                    <i class="fas ${formaPago === 'Tarjeta' ? 'fa-credit-card' : (formaPago === 'Transf.' ? 'fa-university' : 'fa-money-bill-wave')}"></i> ${formaPago}
                </span>
            </div>
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
    let num = value;
    if (typeof value === 'string') {
        num = parseFloat(value.replace(/\./g, '').replace(',', '.'));
    }

    if (num === null || num === undefined || isNaN(num)) {
        return new Intl.NumberFormat('es-ES', { style: 'currency', currency: 'EUR' }).format(0);
    }
    return new Intl.NumberFormat('es-ES', { style: 'currency', currency: 'EUR' }).format(num);
}
