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
    const savedDesde = sessionStorage.getItem('facturas_filter_desde');
    const savedHasta = sessionStorage.getItem('facturas_filter_hasta');
    const savedSearch = sessionStorage.getItem('facturas_filter_search');
    
    if(inputDesde) inputDesde.value = savedDesde || formatDate(today);
    if(inputHasta) inputHasta.value = savedHasta || formatDate(lastDay);
    if(inputSearch && savedSearch) inputSearch.value = savedSearch;

    // Listeners con persistencia
    if(inputDesde) inputDesde.addEventListener('change', (e) => {
        e.target.blur();
        sessionStorage.setItem('facturas_filter_desde', e.target.value);
        reload();
    });
    if(inputHasta) inputHasta.addEventListener('change', (e) => {
        e.target.blur();
        sessionStorage.setItem('facturas_filter_hasta', e.target.value);
        reload();
    });
    document.getElementById('btn-refresh')?.addEventListener('click', () => reload());

    loadFacturas(true);
    
    // Search listener
    if(inputSearch) {
        inputSearch.addEventListener('input', (e) => {
            sessionStorage.setItem('facturas_filter_search', e.target.value);
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
                    loadFacturas(false);
                }
            }
        });
    }
});

function reload() {
    currentPage = 1;
    hasMore = true;
    loadFacturas(true);
}

async function loadFacturas(reset = false) {
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
        let url = `/api/facturas/paginado?page=${currentPage}&pageSize=10&order=DESC&sort=fecha`;
        // Los parámetros pueden variar según implementation del backend (search vs numero/contacto)
        // routes/facturas_routes.py usa: numero, contacto, concepto, estado
        // Vamos a intentar pasar 'numero' o 'contacto' si es numérico o texto
        if(query) {
             // Si parece un número, buscar por número, sino por contacto
             if (/^\d+$/.test(query)) {
                 url += `&numero=${encodeURIComponent(query)}`;
             } else {
                 url += `&contacto=${encodeURIComponent(query)}`;
             }
        }
        
        if(fDesde) url += `&fecha_inicio=${fDesde}`;
        if(fHasta) url += `&fecha_fin=${fHasta}`;
        
        const response = await fetch(url);
        const data = await response.json();
        
        const facturas = data.items || data.facturas || []; // Ajustar según respuesta real
        
        if(reset) container.innerHTML = '';
        
        if(facturas.length === 0) {
            hasMore = false;
            if(reset) container.innerHTML = '<div style="text-align:center; padding:30px; color:#999;">No se encontraron facturas</div>';
        } else {
            facturas.forEach(factura => {
                const card = createFacturaCard(factura);
                container.appendChild(card);
            });
            currentPage++;
        }

    } catch (error) {
        console.error('Error loading facturas:', error);
        if(reset) container.innerHTML = '<div style="text-align:center; color:red;">Error al cargar facturas</div>';
    } finally {
        isLoading = false;
    }
}

function createFacturaCard(factura) {
    const div = document.createElement('div');
    // Estados: 'Pendiente', 'Cobrada', 'Anulada'
    let estadoClass = 'estado-P';
    if (factura.estado === 'Cobrada' || factura.estado === 'cobrada' || factura.estado === 'C') estadoClass = 'estado-C';
    if (factura.estado === 'Anulada' || factura.estado === 'anulada' || factura.estado === 'A') estadoClass = 'estado-A';
    
    div.className = `ticket-card ${estadoClass}`; // Reutilizamos estilos de ticket-card
    div.onclick = () => window.location.href = `/api/auth/mobile/facturas/gestion?id=${factura.id}`;
    
    let estadoText = factura.estado || 'Pendiente';
    let estadoColor = '#f39c12'; // Default Pendiente
    let estadoBg = '#fff3cd';
    
    if(estadoText.toLowerCase() === 'cobrada' || estadoText === 'C') {
        estadoText = 'Cobrada';
        estadoColor = '#155724';
        estadoBg = '#d4edda';
    } else if(estadoText.toLowerCase() === 'anulada' || estadoText === 'A') {
        estadoText = 'Anulada';
        estadoColor = '#721c24';
        estadoBg = '#f8d7da';
    } else {
        estadoText = 'Pendiente';
        estadoColor = '#856404';
        estadoBg = '#fff3cd';
    }

    const fecha = factura.fecha ? factura.fecha.split('T')[0] : '';
    
    div.innerHTML = `
        <div class="tc-header">
            <span class="tc-number">${factura.numero}</span>
            <span class="tc-date">${fecha}</span>
        </div>
        <div class="tc-client">${factura.razonsocial || factura.nombre_cliente || 'Cliente'}</div>
        
        <div class="tc-details" style="margin-top: 8px; padding: 8px 0; border-top: 1px dashed #eee; border-bottom: 1px dashed #eee; font-size: 13px;">
            <div style="display: flex; justify-content: space-between; margin-bottom: 2px;">
                <span style="color: #7f8c8d;">Base:</span>
                <span>${formatCurrency(factura.importe_bruto)}</span>
            </div>
            <div style="display: flex; justify-content: space-between; margin-bottom: 2px;">
                <span style="color: #7f8c8d;">IVA:</span>
                <span>${formatCurrency(factura.importe_impuestos)}</span>
            </div>
            <div style="display: flex; justify-content: space-between;">
                <span style="color: #7f8c8d;">Total:</span>
                <span style="font-weight: 600;">${formatCurrency(factura.total)}</span>
            </div>
        </div>

        <div class="tc-footer" style="border-top: none; padding-top: 5px;">
            <span class="ticket-status" 
                  style="font-size: 11px; padding: 2px 8px; border-radius: 4px; background: ${estadoBg}; color: ${estadoColor};">
                ${estadoText}
            </span>
            <div class="tc-actions">
                <a href="/api/auth/mobile/facturas/gestion?id=${factura.id}" class="btn-icon-action" onclick="event.stopPropagation()">
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
