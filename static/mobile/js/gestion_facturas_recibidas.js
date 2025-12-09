function calcularTotal() {
    const base = parseFloat(document.getElementById('base').value) || 0;
    const iva = parseFloat(document.getElementById('iva').value) || 0;
    document.getElementById('total').value = (base + iva).toFixed(2);
}

document.addEventListener('DOMContentLoaded', () => {
    // Si hay ID en URL, cargar datos (modo edición - no implementado subir archivo en edición)
    const params = new URLSearchParams(window.location.search);
    if(params.has('id')) {
        // Cargar factura...
        // Por ahora nos centramos en creación (subir)
        document.querySelector('.header-title').textContent = 'Detalle Factura';
        cargarFactura(params.get('id'));
    }
    
    // Listener OCR
    const fileInput = document.getElementById('archivo');
    if(fileInput) {
        fileInput.addEventListener('change', async (e) => {
            if(e.target.files.length > 0) {
                await procesarOcr(e.target.files[0]);
            }
        });
    }
});

async function procesarOcr(file) {
    const loadingDiv = document.createElement('div');
    loadingDiv.id = 'ocr-loading';
    loadingDiv.style.cssText = 'position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(255,255,255,0.9);z-index:9999;display:flex;justify-content:center;align-items:center;flex-direction:column;';
    loadingDiv.innerHTML = '<i class="fas fa-magic fa-spin" style="font-size:40px;color:var(--color-primary);"></i><div style="margin-top:15px;font-weight:bold;font-size:18px;">Analizando factura con IA...</div>';
    document.body.appendChild(loadingDiv);

    try {
        const formData = new FormData();
        formData.append('archivo', file);
        
        const res = await fetch('/api/facturas-proveedores/ocr', {
            method: 'POST',
            body: formData
        });
        
        const data = await res.json();
        
        if(data.success && data.datos) {
            const d = data.datos;
            
            if(d.numero_factura) document.getElementById('numero').value = d.numero_factura;
            if(d.fecha_emision) document.getElementById('fecha').value = d.fecha_emision;
            if(d.concepto) document.getElementById('concepto').value = d.concepto;
            
            if(d.importes) {
                document.getElementById('base').value = d.importes.base || 0;
                document.getElementById('iva').value = d.importes.iva || 0;
                document.getElementById('total').value = d.importes.total || 0;
            }
            
            if(d.proveedor) {
                await buscarYSeleccionarProveedor(d.proveedor.nombre, d.proveedor.nif);
            }
            
            // alert('Datos extraídos con IA. Por favor verifica antes de guardar.');
        } else {
            console.error('OCR Error:', data);
            alert('No se pudieron extraer datos automáticamente. Rellena el formulario manualmente.');
        }
    } catch(e) {
        console.error(e);
        alert('Error al analizar factura');
    } finally {
        if(document.body.contains(loadingDiv)) document.body.removeChild(loadingDiv);
    }
}

async function buscarYSeleccionarProveedor(nombre, nif) {
    if(!nombre && !nif) return;
    
    try {
        const res = await fetch(`/api/proveedores/listar?activos=true`);
        const data = await res.json();
        const items = data.proveedores || [];
        
        let match = null;
        // Buscar por NIF
        if(nif) {
            match = items.find(p => p.nif && p.nif.toLowerCase().replace(/[^a-z0-9]/g, '') === nif.toLowerCase().replace(/[^a-z0-9]/g, ''));
        }
        // Buscar por Nombre
        if(!match && nombre) {
            match = items.find(p => p.nombre.toLowerCase().includes(nombre.toLowerCase()));
        }
        
        if(match) {
            document.getElementById('proveedor-id').value = match.id;
            document.getElementById('proveedor-nombre').textContent = match.nombre;
        } else if(nombre) {
            if(confirm(`Proveedor "${nombre}" no encontrado. ¿Deseas crearlo ahora?`)) {
                 const resProv = await fetch('/api/proveedores/crear', {
                    method: 'POST',
                    headers: {'Content-Type':'application/json'},
                    body: JSON.stringify({nombre: nombre, nif: nif || ''})
                });
                const dProv = await resProv.json();
                if(dProv.success) {
                    document.getElementById('proveedor-id').value = dProv.id;
                    document.getElementById('proveedor-nombre').textContent = nombre;
                }
            }
        }
    } catch(e) { console.error(e); }
}

async function cargarFactura(id) {
    try {
        const res = await fetch(`/api/facturas-proveedores/${id}`);
        if(res.ok) {
            const data = await res.json();
            const f = data.factura;
            document.getElementById('numero').value = f.numero_factura;
            document.getElementById('fecha').value = f.fecha_emision ? f.fecha_emision.split('T')[0] : '';
            document.getElementById('proveedor-id').value = f.proveedor_id;
            document.getElementById('proveedor-nombre').textContent = f.proveedor_nombre;
            document.getElementById('base').value = f.base_imponible;
            document.getElementById('iva').value = f.iva_importe;
            document.getElementById('total').value = f.total;
            document.getElementById('concepto').value = f.concepto;
        }
    } catch(e) { console.error(e); }
}

async function guardarFactura() {
    const provId = document.getElementById('proveedor-id').value;
    const fileInput = document.getElementById('archivo');
    
    if(!provId) return alert('Selecciona un proveedor');
    
    const formData = new FormData();
    formData.append('proveedor_id', provId);
    formData.append('numero_factura', document.getElementById('numero').value);
    formData.append('fecha_emision', document.getElementById('fecha').value);
    formData.append('base_imponible', document.getElementById('base').value);
    formData.append('iva', document.getElementById('iva').value);
    formData.append('total', document.getElementById('total').value);
    formData.append('concepto', document.getElementById('concepto').value);

    // Si hay archivo, es CREACIÓN
    if(fileInput.files.length > 0) {
        formData.append('archivos', fileInput.files[0]);
        try {
            const res = await fetch('/api/facturas-proveedores/subir', {
                method: 'POST',
                body: formData
            });
            const data = await res.json();
            if(data.success) {
                alert('Factura subida correctamente');
                window.location.href = '/api/auth/mobile/facturas_recibidas';
            } else {
                alert('Error: ' + (data.error || data.mensaje));
            }
        } catch(e) { alert('Error de conexión'); }
    } else {
        // EDICIÓN
        const params = new URLSearchParams(window.location.search);
        if(params.has('id')) {
            const id = params.get('id');
            const payload = {};
            formData.forEach((value, key) => payload[key] = value);
            
            try {
                const res = await fetch(`/api/facturas-proveedores/${id}`, {
                    method: 'PUT',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(payload)
                });
                const data = await res.json();
                if(data.success) {
                    alert('Actualizado');
                    window.location.href = '/api/auth/mobile/facturas_recibidas';
                } else alert('Error: ' + data.error);
            } catch(e) { alert('Error de conexión'); }
        } else {
            alert('Debes seleccionar un archivo para una nueva factura');
        }
    }
}

// --- Proveedores ---
function abrirModalProveedor() { document.getElementById('modal-proveedor').classList.add('active'); buscarProveedores(''); }
function cerrarModalProveedor() { document.getElementById('modal-proveedor').classList.remove('active'); }

let searchTimer = null;
async function buscarProveedores(q) {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(async () => {
        const res = await fetch(`/api/proveedores/listar?activos=true`); // La API de listar devuelve todos, filtraremos en cliente si es necesario o buscar si API soporta
        // API listar no soporta 'search', devuelve todos. Filtramos en JS.
        const data = await res.json();
        const c = document.getElementById('prov-resultados');
        c.innerHTML = '';
        
        let items = data.proveedores || [];
        if(q) {
            const lower = q.toLowerCase();
            items = items.filter(p => p.nombre.toLowerCase().includes(lower) || p.nif.toLowerCase().includes(lower));
        }
        
        items.forEach(p => {
            const d = document.createElement('div');
            d.style.cssText = 'padding:10px; border-bottom:1px solid #eee; cursor:pointer;';
            d.innerHTML = `<b>${p.nombre}</b> <span style="color:#888;font-size:12px;">${p.nif}</span>`;
            d.onclick = () => {
                document.getElementById('proveedor-id').value = p.id;
                document.getElementById('proveedor-nombre').textContent = p.nombre;
                cerrarModalProveedor();
            };
            c.appendChild(d);
        });
    }, 300);
}

function crearNuevoProveedor() {
    const nombre = prompt('Nombre del nuevo proveedor:');
    if(nombre) {
        // Simple create logic if needed, or redirect to full provider form
        // API /api/proveedores/crear expects {nombre, nif, ...}
        const nif = prompt('NIF del proveedor:');
        if(!nif) return;
        
        fetch('/api/proveedores/crear', {
            method: 'POST',
            headers: {'Content-Type':'application/json'},
            body: JSON.stringify({nombre, nif})
        }).then(r=>r.json()).then(d=>{
            if(d.success) {
                document.getElementById('proveedor-id').value = d.id;
                document.getElementById('proveedor-nombre').textContent = nombre;
                cerrarModalProveedor();
            } else alert(d.error);
        });
    }
}

window.abrirModalProveedor = abrirModalProveedor;
window.cerrarModalProveedor = cerrarModalProveedor;
window.buscarProveedores = buscarProveedores;
window.crearNuevoProveedor = crearNuevoProveedor;
window.guardarFactura = guardarFactura;
window.calcularTotal = calcularTotal;
