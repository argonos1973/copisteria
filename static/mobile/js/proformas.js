let currentPage = 1;
let isLoading = false;
let hasMore = true;
let searchTimer = null;

document.addEventListener('DOMContentLoaded', () => {
    // Inicializar fechas
    const today = new Date();
    const lastDay = new Date(today.getFullYear(), today.getMonth() + 1, 0);
    const formatDate = (d) => d.toISOString().split('T')[0];
    
    const inputDesde = document.getElementById('fecha-desde');
    const inputHasta = document.getElementById('fecha-hasta');
    const inputSearch = document.getElementById('search-input');
    
    // Recuperar filtros
    inputDesde.value = sessionStorage.getItem('prof_desde') || formatDate(today);
    inputHasta.value = sessionStorage.getItem('prof_hasta') || formatDate(lastDay);
    if(inputSearch) inputSearch.value = sessionStorage.getItem('prof_search') || '';

    // Listeners
    inputDesde.addEventListener('change', (e) => {
        sessionStorage.setItem('prof_desde', e.target.value);
        reload();
    });
    inputHasta.addEventListener('change', (e) => {
        sessionStorage.setItem('prof_hasta', e.target.value);
        reload();
    });
    inputSearch?.addEventListener('input', (e) => {
        sessionStorage.setItem('prof_search', e.target.value);
        clearTimeout(searchTimer);
        searchTimer = setTimeout(() => reload(), 500);
    });
    document.getElementById('btn-refresh')?.addEventListener('click', () => reload());

    loadProformas(true);
    
    const mobileContent = document.querySelector('.mobile-content');
    if (mobileContent) {
        mobileContent.addEventListener('scroll', () => {
            if ((mobileContent.scrollTop + mobileContent.clientHeight) >= mobileContent.scrollHeight - 300) {
                if(!isLoading && hasMore) loadProformas(false);
            }
        });
    }
});

function reload() {
    currentPage = 1;
    hasMore = true;
    loadProformas(true);
}

async function loadProformas(reset = false) {
    if(isLoading) return;
    isLoading = true;
    
    const container = document.getElementById('tickets-container');
    const query = document.getElementById('search-input')?.value || '';
    const fDesde = document.getElementById('fecha-desde').value;
    const fHasta = document.getElementById('fecha-hasta').value;

    if(reset) container.innerHTML = '<div class="loading-spinner"><i class="fas fa-circle-notch fa-spin"></i> Cargando...</div>';

    try {
        let url = `/api/proformas/paginado?page=${currentPage}&pageSize=10&order=DESC&sort=fecha`;
        if(query) {
             if (/^\d+$/.test(query)) url += `&numero=${encodeURIComponent(query)}`;
             else url += `&contacto=${encodeURIComponent(query)}`;
        }
        if(fDesde) url += `&fecha_inicio=${fDesde}`;
        if(fHasta) url += `&fecha_fin=${fHasta}`;
        
        const response = await fetch(url);
        const data = await response.json();
        const items = data.items || data.proformas || [];
        
        if(reset) container.innerHTML = '';
        
        if(items.length === 0) {
            hasMore = false;
            if(reset) container.innerHTML = '<div style="text-align:center; padding:30px; color:#999;">No se encontraron proformas</div>';
        } else {
            items.forEach(item => {
                const card = createProformaCard(item);
                container.appendChild(card);
            });
            currentPage++;
        }

    } catch (error) {
        console.error(error);
        if(reset) container.innerHTML = '<div style="text-align:center; color:red;">Error al cargar datos</div>';
    } finally {
        isLoading = false;
    }
}

function createProformaCard(p) {
    const div = document.createElement('div');
    
    let estadoClass = 'estado-P'; 
    if(p.estado === 'A' || p.estado === 'Facturada') estadoClass = 'estado-C';
    
    div.className = `ticket-card ${estadoClass}`;
    div.onclick = () => window.location.href = `/api/auth/mobile/proformas/gestion?id=${p.id}`;
    
    let estadoText = p.estado || 'Pendiente';
    if(estadoText === 'A') estadoText = 'Facturada';
    if(estadoText === 'P') estadoText = 'Pendiente';
    
    div.innerHTML = `
        <div class="tc-header">
            <span class="tc-number">${p.numero}</span>
            <span class="tc-date">${p.fecha ? p.fecha.split('T')[0] : ''}</span>
        </div>
        <div class="tc-client">${p.razonsocial || p.nombre_cliente || 'Cliente'}</div>
        
        <div class="tc-details" style="margin-top: 8px; padding: 8px 0; border-top: 1px dashed #eee; border-bottom: 1px dashed #eee; font-size: 13px;">
            <div style="display: flex; justify-content: space-between;">
                <span style="color: #7f8c8d;">Total:</span>
                <span style="font-weight: 600;">${formatCurrency(p.total)}</span>
            </div>
        </div>

        <div class="tc-footer" style="border-top: none; padding-top: 5px;">
            <span class="ticket-status">${estadoText}</span>
            <div class="tc-actions">
                <a href="/api/auth/mobile/proformas/gestion?id=${p.id}" class="btn-icon-action" onclick="event.stopPropagation()">
                    <i class="fas fa-pen"></i>
                </a>
            </div>
        </div>
    `;
    return div;
}

function formatCurrency(value) {
    return new Intl.NumberFormat('es-ES', { style: 'currency', currency: 'EUR' }).format(value || 0);
}
