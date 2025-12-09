function redondearImporte(v){const n=Number(v);if(!isFinite(n))return 0;return Math.round(n*100)/100;}
function formatearImporte(v){return new Intl.NumberFormat('es-ES',{style:'currency',currency:'EUR'}).format(v||0);}

let proformaId = null;
let lineas = [];

document.addEventListener('DOMContentLoaded', () => {
    const params = new URLSearchParams(window.location.search);
    if(params.has('id')) {
        proformaId = params.get('id');
        cargarProforma(proformaId);
    }
});

async function cargarProforma(id) {
    try {
        const res = await fetch(`/api/proformas/${id}`);
        if(!res.ok) throw new Error('Error al cargar');
        const data = await res.json();
        
        document.getElementById('page-title').textContent = data.numero || 'Editar Proforma';
        document.getElementById('cliente-id').value = data.idContacto;
        document.getElementById('cliente-nombre').textContent = data.razonsocial || 'Cliente';
        
        if(data.detalles) {
            lineas = data.detalles.map(d => ({
                concepto: d.concepto,
                cantidad: parseFloat(d.cantidad),
                precio: parseFloat(d.precio),
                impuestos: parseFloat(d.impuestos),
                total: parseFloat(d.total)
            }));
            renderLineas();
        }
    } catch(e) { console.error(e); }
}

async function guardarProforma() {
    const clienteId = document.getElementById('cliente-id').value;
    if(!clienteId) return alert('Selecciona un cliente');
    if(lineas.length === 0) return alert('Añade productos');

    const total = lineas.reduce((s,l)=>s+l.total,0);
    const payload = {
        idContacto: clienteId,
        fecha: new Date().toISOString().split('T')[0],
        detalles: lineas,
        total: redondearImporte(total),
        estado: 'P' // Inicialmente pendiente
    };

    const url = proformaId ? `/api/proformas/${proformaId}` : '/api/proformas';
    const method = proformaId ? 'PUT' : 'POST';

    try {
        const res = await fetch(url, {
            method: method,
            headers: {'Content-Type':'application/json'},
            body: JSON.stringify(payload)
        });
        if(!res.ok) throw new Error('Error al guardar');
        alert('Proforma guardada');
        window.location.href = '/api/auth/mobile/proformas';
    } catch(e) { alert(e.message); }
}

// --- Lineas ---
function renderLineas() {
    const c = document.getElementById('lineas-container');
    c.innerHTML = lineas.length ? '' : '<div style="text-align:center;padding:20px;color:#aaa;">Añade productos</div>';
    
    lineas.forEach((l,i) => {
        const d = document.createElement('div');
        d.className = 'line-item';
        d.innerHTML = `
            <div class="line-info"><div class="line-title">${l.concepto}</div><div class="line-meta">${l.cantidad} x ${formatearImporte(l.precio)}</div></div>
            <div class="line-price">${formatearImporte(l.total)}</div>
            <button class="btn-remove-line" onclick="eliminarLinea(${i})"><i class="fas fa-trash"></i></button>
        `;
        c.appendChild(d);
    });
    calcularTotales();
}

function calcularTotales() {
    let base=0, iva=0, total=0;
    lineas.forEach(l => {
        const sub = l.cantidad * l.precio;
        const imp = redondearImporte(sub * (l.impuestos/100));
        base += sub; iva += imp; total += l.total;
    });
    document.getElementById('resumen-base').textContent = formatearImporte(base);
    document.getElementById('resumen-iva').textContent = formatearImporte(iva);
    document.getElementById('total-final').textContent = formatearImporte(total);
}

function agregarLineaManual() {
    const desc = document.getElementById('prod-desc').value;
    const cant = parseFloat(document.getElementById('prod-cant').value)||0;
    const precio = parseFloat(document.getElementById('prod-precio').value)||0;
    const iva = parseFloat(document.getElementById('prod-iva').value)||21;
    
    if(!desc || cant<=0) return alert('Datos inválidos');
    
    const sub = cant*precio;
    const imp = redondearImporte(sub*(iva/100));
    const total = redondearImporte(sub+imp);
    
    lineas.push({concepto:desc, cantidad:cant, precio:precio, impuestos:iva, total:total});
    renderLineas();
    cerrarModalProducto();
    document.getElementById('prod-desc').value='';
    document.getElementById('prod-precio').value='';
}

function eliminarLinea(i) { lineas.splice(i,1); renderLineas(); }

// --- Modals ---
function abrirModalProducto() { document.getElementById('modal-producto').classList.add('active'); }
function cerrarModalProducto() { document.getElementById('modal-producto').classList.remove('active'); }

function abrirModalCliente() { document.getElementById('modal-cliente').classList.add('active'); buscarClientes(''); }
function cerrarModalCliente() { document.getElementById('modal-cliente').classList.remove('active'); }

let searchTimer = null;
async function buscarClientes(q) {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(async () => {
        const res = await fetch(`/api/contactos/paginado?page=1&page_size=10&search=${encodeURIComponent(q)}`);
        const data = await res.json();
        const c = document.getElementById('cliente-resultados');
        c.innerHTML = '';
        (data.items||data.contactos||[]).forEach(item => {
            const d = document.createElement('div');
            d.style.cssText = 'padding:10px; border-bottom:1px solid #eee; cursor:pointer;';
            d.innerHTML = `<b>${item.razonsocial||item.nombre}</b>`;
            d.onclick = () => {
                document.getElementById('cliente-id').value = item.id||item.idContacto;
                document.getElementById('cliente-nombre').textContent = item.razonsocial||item.nombre;
                cerrarModalCliente();
            };
            c.appendChild(d);
        });
    }, 300);
}

async function buscarProductos(q) {
    if(!q) return;
    const res = await fetch(`/api/productos/paginado?page=1&page_size=10&search=${encodeURIComponent(q)}`);
    const data = await res.json();
    const c = document.getElementById('prod-resultados');
    c.style.display = 'block';
    c.innerHTML = '';
    (data.items||data.productos||[]).forEach(p => {
        const d = document.createElement('div');
        d.style.cssText = 'padding:10px; border-bottom:1px solid #eee; cursor:pointer;';
        d.innerHTML = `<b>${p.nombre}</b> - ${p.precio_venta}€`;
        d.onclick = () => {
            document.getElementById('prod-desc').value = p.nombre;
            document.getElementById('prod-precio').value = p.precio_venta;
            document.getElementById('prod-iva').value = p.iva;
            c.style.display = 'none';
        };
        c.appendChild(d);
    });
}

window.agregarLineaManual = agregarLineaManual;
window.eliminarLinea = eliminarLinea;
window.guardarProforma = guardarProforma;
window.abrirModalProducto = abrirModalProducto;
window.cerrarModalProducto = cerrarModalProducto;
window.abrirModalCliente = abrirModalCliente;
window.cerrarModalCliente = cerrarModalCliente;
window.buscarClientes = buscarClientes;
window.buscarProductos = buscarProductos;
