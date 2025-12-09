let currentPage = 1;
let isLoading = false;
let hasMore = true; // API might not support pagination if not implemented, check routes
// routes/facturas_recibidas_routes.py -> consultar_facturas_recibidas calls db_utils...
// It seems it returns all results? Or maybe pagination?
// looking at code it calls `consultar_facturas_recibidas`...
// usually it returns full list if no limit specified.
// I'll assume full list for now or client-side filter if needed.

let searchTimer = null;

document.addEventListener('DOMContentLoaded', () => {
    const today = new Date();
    const firstDay = new Date(today.getFullYear(), today.getMonth(), 1);
    const lastDay = new Date(today.getFullYear(), today.getMonth() + 1, 0);
    const formatDate = (d) => d.toISOString().split('T')[0];
    
    const inputDesde = document.getElementById('fecha-desde');
    const inputHasta = document.getElementById('fecha-hasta');
    const inputSearch = document.getElementById('search-input');
    
    inputDesde.value = sessionStorage.getItem('fr_desde') || formatDate(firstDay);
    inputHasta.value = sessionStorage.getItem('fr_hasta') || formatDate(lastDay);
    if(inputSearch) inputSearch.value = sessionStorage.getItem('fr_search') || '';

    inputDesde.addEventListener('change', (e) => {
        sessionStorage.setItem('fr_desde', e.target.value);
        loadFacturas(true);
    });
    inputHasta.addEventListener('change', (e) => {
        sessionStorage.setItem('fr_hasta', e.target.value);
        loadFacturas(true);
    });
    inputSearch?.addEventListener('input', (e) => {
        sessionStorage.setItem('fr_search', e.target.value);
        clearTimeout(searchTimer);
        searchTimer = setTimeout(() => loadFacturas(true), 500);
    });
    document.getElementById('btn-refresh')?.addEventListener('click', () => loadFacturas(true));

    loadFacturas(true);
});

async function loadFacturas(reset = false) {
    if(isLoading) return;
    isLoading = true;
    
    const container = document.getElementById('tickets-container');
    const query = document.getElementById('search-input')?.value || '';
    const fDesde = document.getElementById('fecha-desde').value;
    const fHasta = document.getElementById('fecha-hasta').value;

    if(reset) container.innerHTML = '<div class="loading-spinner"><i class="fas fa-circle-notch fa-spin"></i> Cargando...</div>';

    try {
        const payload = {
            fecha_inicio: fDesde,
            fecha_fin: fHasta,
            busqueda: query
        };
        
        const response = await fetch('/api/facturas-proveedores/consultar', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(payload)
        });
        
        if(!response.ok) throw new Error('Error al cargar');
        
        const data = await response.json();
        // data.facturas is the list
        const items = data.facturas || [];
        
        if(reset) container.innerHTML = '';
        
        if(items.length === 0) {
            if(reset) container.innerHTML = '<div style="text-align:center; padding:30px; color:#999;">No se encontraron facturas</div>';
        } else {
            items.forEach(item => {
                const card = createFacturaCard(item);
                container.appendChild(card);
            });
        }

    } catch (error) {
        console.error(error);
        if(reset) container.innerHTML = '<div style="text-align:center; color:red;">Error al cargar datos</div>';
    } finally {
        isLoading = false;
    }
}

function createFacturaCard(f) {
    const div = document.createElement('div');
    // Estado: Pendiente, Pagada?
    // Fields: id, numero_factura, proveedor_nombre, fecha_emision, total, estado_pago?
    
    // Check if 'pagada' or 'estado' exists
    let estadoClass = 'estado-P';
    let estadoText = f.estado || 'Pendiente';
    if(f.pagada || estadoText === 'Pagada') {
        estadoClass = 'estado-C';
        estadoText = 'Pagada';
    }
    
    div.className = `ticket-card ${estadoClass}`;
    div.onclick = () => window.location.href = `/api/auth/mobile/facturas_recibidas/gestion?id=${f.id}`;
    
    div.innerHTML = `
        <div class="tc-header">
            <span class="tc-number">${f.numero_factura || 'S/N'}</span>
            <span class="tc-date">${f.fecha_emision ? f.fecha_emision.split('T')[0] : ''}</span>
        </div>
        <div class="tc-client">${f.proveedor_nombre || 'Proveedor'}</div>
        
        <div class="tc-details" style="margin-top: 8px; padding: 8px 0; border-top: 1px dashed #eee; border-bottom: 1px dashed #eee; font-size: 13px;">
            <div style="display: flex; justify-content: space-between;">
                <span style="color: #7f8c8d;">Total:</span>
                <span style="font-weight: 600;">${formatCurrency(f.total)}</span>
            </div>
        </div>

        <div class="tc-footer" style="border-top: none; padding-top: 5px;">
            <span class="ticket-status">${estadoText}</span>
            <div class="tc-actions">
                <i class="fas fa-chevron-right" style="color:#ccc"></i>
            </div>
        </div>
    `;
    return div;
}

function formatCurrency(value) {
    return new Intl.NumberFormat('es-ES', { style: 'currency', currency: 'EUR' }).format(value || 0);
}
