let currentPage = 1;
let isLoading = false;
let hasMore = true;
let searchTimer = null;

document.addEventListener('DOMContentLoaded', () => {
    const inputSearch = document.getElementById('search-input');
    
    // Recuperar filtros
    if(inputSearch) inputSearch.value = sessionStorage.getItem('contactos_search') || '';

    // Listeners
    inputSearch?.addEventListener('input', (e) => {
        sessionStorage.setItem('contactos_search', e.target.value);
        clearTimeout(searchTimer);
        searchTimer = setTimeout(() => {
            reload();
        }, 500);
    });

    loadContactos(true);
    
    const mobileContent = document.querySelector('.mobile-content');
    if (mobileContent) {
        mobileContent.addEventListener('scroll', () => {
            if ((mobileContent.scrollTop + mobileContent.clientHeight) >= mobileContent.scrollHeight - 300) {
                if(!isLoading && hasMore) loadContactos(false);
            }
        });
    }
});

function reload() {
    currentPage = 1;
    hasMore = true;
    loadContactos(true);
}

async function loadContactos(reset = false) {
    if(isLoading) return;
    isLoading = true;
    
    const container = document.getElementById('list-container');
    const query = document.getElementById('search-input')?.value || '';

    if(reset) {
        container.innerHTML = '<div class="loading-spinner"><i class="fas fa-circle-notch fa-spin"></i> Cargando...</div>';
    }

    try {
        let url = `/api/contactos/paginado?page=${currentPage}&page_size=20&sort=razonsocial&order=ASC`;
        if(query) url += `&search=${encodeURIComponent(query)}`;
        
        const response = await fetch(url);
        const data = await response.json();
        const items = data.contactos || data.items || [];
        
        if(reset) container.innerHTML = '';
        
        if(items.length === 0) {
            hasMore = false;
            if(reset) container.innerHTML = '<div style="text-align:center; padding:30px; color:#999;">No se encontraron contactos</div>';
        } else {
            items.forEach(item => {
                const card = createContactoCard(item);
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

function createContactoCard(c) {
    const div = document.createElement('div');
    div.className = 'ticket-card';
    div.style.borderLeft = '4px solid #3498db';
    div.onclick = () => window.location.href = `/api/auth/mobile/contactos/gestion?id=${c.id || c.idContacto}`;
    
    div.innerHTML = `
        <div class="tc-header">
            <span class="tc-number" style="font-weight:600; font-size:16px;">${c.razonsocial || c.nombre}</span>
        </div>
        <div class="tc-details" style="font-size:13px; color:#666; margin-top:5px;">
            <div>${c.identificador || c.nif || ''}</div>
            <div>${c.mail || c.email || ''}</div>
            <div>${c.telefono || ''}</div>
        </div>
    `;
    return div;
}
