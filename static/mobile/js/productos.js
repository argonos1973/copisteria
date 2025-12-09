let currentPage = 1;
let isLoading = false;
let hasMore = true;
let searchTimer = null;

document.addEventListener('DOMContentLoaded', () => {
    const inputSearch = document.getElementById('search-input');
    if(inputSearch) inputSearch.value = sessionStorage.getItem('productos_search') || '';

    inputSearch?.addEventListener('input', (e) => {
        sessionStorage.setItem('productos_search', e.target.value);
        clearTimeout(searchTimer);
        searchTimer = setTimeout(() => reload(), 500);
    });

    loadProductos(true);
    
    const mobileContent = document.querySelector('.mobile-content');
    if (mobileContent) {
        mobileContent.addEventListener('scroll', () => {
            if ((mobileContent.scrollTop + mobileContent.clientHeight) >= mobileContent.scrollHeight - 300) {
                if(!isLoading && hasMore) loadProductos(false);
            }
        });
    }
});

function reload() {
    currentPage = 1;
    hasMore = true;
    loadProductos(true);
}

async function loadProductos(reset = false) {
    if(isLoading) return;
    isLoading = true;
    
    const container = document.getElementById('list-container');
    const query = document.getElementById('search-input')?.value || '';

    if(reset) container.innerHTML = '<div class="loading-spinner"><i class="fas fa-circle-notch fa-spin"></i> Cargando...</div>';

    try {
        let url = `/api/productos/paginado?page=${currentPage}&page_size=20&sort=nombre&order=ASC`;
        if(query) url += `&search=${encodeURIComponent(query)}`;
        
        const response = await fetch(url);
        const data = await response.json();
        const items = data.productos || data.items || [];
        
        if(reset) container.innerHTML = '';
        
        if(items.length === 0) {
            hasMore = false;
            if(reset) container.innerHTML = '<div style="text-align:center; padding:30px; color:#999;">No se encontraron productos</div>';
        } else {
            items.forEach(item => {
                const card = createProductoCard(item);
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

function createProductoCard(p) {
    const div = document.createElement('div');
    div.className = 'ticket-card';
    div.style.borderLeft = '4px solid #9b59b6';
    div.onclick = () => window.location.href = `/api/auth/mobile/productos/gestion?id=${p.id}`;
    
    const precio = new Intl.NumberFormat('es-ES', { style: 'currency', currency: 'EUR' }).format(p.precio_venta || 0);
    
    div.innerHTML = `
        <div class="tc-header">
            <span class="tc-number" style="font-weight:600; font-size:16px;">${p.nombre}</span>
            <span class="tc-total" style="color:#9b59b6;">${precio}</span>
        </div>
        <div class="tc-details" style="font-size:13px; color:#666; margin-top:5px;">
            <div>IVA: ${p.iva || 21}%</div>
            <div>Ref: ${p.referencia || ''}</div>
        </div>
    `;
    return div;
}
