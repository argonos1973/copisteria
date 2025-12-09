let allGastos = [];
let currentPage = 1;
const pageSize = 20;
let isLoading = false;

document.addEventListener('DOMContentLoaded', () => {
    // Inicializar fechas
    const today = new Date();
    const firstDay = new Date(today.getFullYear(), today.getMonth(), 1);
    const lastDay = new Date(today.getFullYear(), today.getMonth() + 1, 0);
    
    const formatDate = (d) => d.toISOString().split('T')[0];
    
    const inputDesde = document.getElementById('fecha-desde');
    const inputHasta = document.getElementById('fecha-hasta');
    const inputSearch = document.getElementById('search-input');
    
    // Recuperar filtros
    inputDesde.value = sessionStorage.getItem('gastos_desde') || formatDate(firstDay);
    inputHasta.value = sessionStorage.getItem('gastos_hasta') || formatDate(lastDay);
    if(inputSearch) inputSearch.value = sessionStorage.getItem('gastos_search') || '';

    // Listeners
    inputDesde.addEventListener('change', (e) => {
        sessionStorage.setItem('gastos_desde', e.target.value);
        loadGastos();
    });
    inputHasta.addEventListener('change', (e) => {
        sessionStorage.setItem('gastos_hasta', e.target.value);
        loadGastos();
    });
    inputSearch?.addEventListener('input', (e) => {
        sessionStorage.setItem('gastos_search', e.target.value);
        filterAndRender();
    });
    document.getElementById('btn-refresh')?.addEventListener('click', () => loadGastos());

    // Carga inicial
    loadGastos();

    // Infinite Scroll (local pagination)
    const mobileContent = document.querySelector('.mobile-content');
    if (mobileContent) {
        mobileContent.addEventListener('scroll', () => {
            if ((mobileContent.scrollTop + mobileContent.clientHeight) >= mobileContent.scrollHeight - 100) {
                renderMore();
            }
        });
    }
});

async function loadGastos() {
    if(isLoading) return;
    isLoading = true;
    
    const container = document.getElementById('tickets-container');
    container.innerHTML = '<div class="loading-spinner"><i class="fas fa-circle-notch fa-spin"></i> Cargando...</div>';
    
    const fDesde = document.getElementById('fecha-desde').value;
    const fHasta = document.getElementById('fecha-hasta').value;
    
    try {
        const url = `/api/gastos?fecha_inicio=${fDesde}&fecha_fin=${fHasta}&tipo=todos`;
        const res = await fetch(url);
        if(!res.ok) throw new Error('Error al cargar gastos');
        
        const data = await res.json();
        allGastos = data.gastos || [];
        
        currentPage = 1;
        filterAndRender();
        
    } catch(e) {
        console.error(e);
        container.innerHTML = '<div style="text-align:center; color:red; padding:20px;">Error cargando datos</div>';
    } finally {
        isLoading = false;
    }
}

function filterAndRender() {
    const query = document.getElementById('search-input')?.value.toLowerCase() || '';
    const container = document.getElementById('tickets-container');
    
    let filtered = allGastos;
    if(query) {
        filtered = allGastos.filter(g => 
            (g.concepto && g.concepto.toLowerCase().includes(query)) ||
            (g.importe_eur && g.importe_eur.toString().includes(query))
        );
    }
    
    // Reset pagination for render
    container.innerHTML = '';
    renderBatch(filtered, 1);
    
    // Store filtered reference for infinite scroll
    window.currentFiltered = filtered;
}

function renderMore() {
    if(!window.currentFiltered) return;
    const maxPage = Math.ceil(window.currentFiltered.length / pageSize);
    if(currentPage < maxPage) {
        currentPage++;
        renderBatch(window.currentFiltered, currentPage);
    }
}

function renderBatch(list, page) {
    const start = (page - 1) * pageSize;
    const end = start + pageSize;
    const batch = list.slice(start, end);
    
    const container = document.getElementById('tickets-container');
    
    if(list.length === 0) {
        container.innerHTML = '<div style="text-align:center; padding:30px; color:#999;">No hay movimientos</div>';
        return;
    }

    batch.forEach(g => {
        const div = document.createElement('div');
        const importe = parseFloat(g.importe_eur);
        const isIngreso = importe >= 0;
        const color = isIngreso ? '#2ecc71' : '#e74c3c';
        const sign = isIngreso ? '+' : '';
        
        div.className = 'ticket-card'; // Reuse style
        div.style.borderLeft = `4px solid ${color}`;
        
        div.innerHTML = `
            <div class="tc-header">
                <span class="tc-date" style="color:#666;">${g.fecha_operacion}</span>
                <span class="tc-total" style="color:${color}; font-weight:bold;">${sign}${formatCurrency(importe)}</span>
            </div>
            <div class="tc-client" style="margin-top:5px; font-size:14px;">${g.concepto}</div>
        `;
        container.appendChild(div);
    });
}

function formatCurrency(value) {
    return new Intl.NumberFormat('es-ES', { style: 'currency', currency: 'EUR' }).format(value);
}
