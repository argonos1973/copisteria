// Funciones de utilidad
function redondearImporte(valor) {
  const n = Number(valor);
  if (!isFinite(n)) return 0;
  const factor = 100;
  return (n >= 0)
    ? Math.round(n * factor) / factor
    : -Math.round(Math.abs(n) * factor) / factor;
}

function formatearImporte(valor) {
    if (valor === null || valor === undefined || isNaN(valor)) {
        return new Intl.NumberFormat('es-ES', { style: 'currency', currency: 'EUR' }).format(0);
    }
    return new Intl.NumberFormat('es-ES', { style: 'currency', currency: 'EUR' }).format(valor);
}

let facturaId = null; // null = Nueva
let numeroFacturaGenerado = ''; // Almacenar el número
let lineas = [];

document.addEventListener('DOMContentLoaded', () => {
    const params = new URLSearchParams(window.location.search);
    if(params.has('id')) {
        facturaId = params.get('id');
        cargarFactura(facturaId);
    } else {
        // Restricción: Solo permitir crear si hay cliente_id
        if(!params.has('cliente_id')) {
            alert("Para crear una factura debe seleccionar un cliente desde la Agenda.");
            window.location.href = '/api/auth/mobile/tickets'; // Redirigir a inicio/tickets
            return;
        }

        obtenerSiguienteNumero();
        // Cargar cliente si viene por parámetro
        if(params.has('cliente_id')) {
            cargarCliente(params.get('cliente_id'));
        }
    }
});

async function cargarCliente(id) {
    try {
        // Usar endpoint de contactos
        const res = await fetch(`/api/contactos/get_contacto/${id}`);
        if(res.ok) {
            const cliente = await res.json();
            seleccionarCliente(cliente);
        }
    } catch(e) { console.error("Error cargando cliente", e); }
}

async function obtenerSiguienteNumero() {
    try {
        const res = await fetch('/api/facturas/obtener_numerador/F');
        if(res.ok) {
            const data = await res.json();
            const year = new Date().getFullYear().toString().substr(-2); // 2 dígitos (25)
            const num = data.numerador.toString().padStart(4, '0'); // 4 dígitos (0501)
            numeroFacturaGenerado = `F${year}${num}`;
            document.getElementById('page-title').textContent = `Nueva ${numeroFacturaGenerado}`;
        }
    } catch(e) {
        console.error("Error obteniendo numerador", e);
    }
}

// --- Gestión de Líneas ---
function agregarLineaManual() {
    const desc = document.getElementById('prod-desc').value;
    let cantStr = document.getElementById('prod-cant').value.toString().replace(',', '.');
    let precioStr = document.getElementById('prod-precio').value.toString().replace(',', '.');
    
    const cant = parseFloat(cantStr) || 0;
    const precio = parseFloat(precioStr) || 0;
    const iva = parseFloat(document.getElementById('prod-iva').value) || 21;

    if(!desc) return alert('Descripción requerida');
    if(cant <= 0) return alert('Cantidad inválida');

    const subtotalRaw = cant * precio;
    const impuestoMonto = redondearImporte(subtotalRaw * (iva / 100));
    const totalLinea = redondearImporte(subtotalRaw + impuestoMonto);
    
    const linea = {
        concepto: desc,
        descripcion: desc,
        cantidad: cant,
        precio: precio,
        impuestos: iva,
        total: totalLinea
    };
    
    lineas.push(linea);
    renderLineas();
    cerrarModalProducto();
    limpiarModalProducto();
}

function renderLineas() {
    const container = document.getElementById('lineas-container');
    const emptyMsg = document.getElementById('empty-msg');
    
    if(lineas.length === 0) {
        container.innerHTML = '';
        container.appendChild(emptyMsg);
        emptyMsg.style.display = 'block';
    } else {
        container.innerHTML = '';
        emptyMsg.style.display = 'none';
        
        lineas.forEach((linea, index) => {
            const div = document.createElement('div');
            div.className = 'line-item';
            div.innerHTML = `
                <div class="line-info">
                    <div class="line-title">${linea.concepto}</div>
                    <div class="line-meta">${linea.cantidad} x ${formatearImporte(linea.precio)} (+${linea.impuestos}%)</div>
                </div>
                <div class="line-price">${formatearImporte(linea.total)}</div>
                <button class="btn-remove-line" onclick="eliminarLinea(${index})">
                    <i class="fas fa-trash"></i>
                </button>
            `;
            container.appendChild(div);
        });
    }
    calcularTotales();
}

function eliminarLinea(index) {
    lineas.splice(index, 1);
    renderLineas();
}

function calcularTotales() {
    let base = 0;
    let totalImpuestos = 0;
    let total = 0;

    lineas.forEach(l => {
        const subtotalRaw = l.cantidad * l.precio;
        const impuestoMonto = redondearImporte(subtotalRaw * (l.impuestos / 100));
        
        base += subtotalRaw;
        totalImpuestos += impuestoMonto;
        total += l.total;
    });

    document.getElementById('resumen-base').textContent = formatearImporte(base);
    document.getElementById('resumen-iva').textContent = formatearImporte(totalImpuestos);
    document.getElementById('total-final').textContent = formatearImporte(total);
}

// --- Acciones ---
async function guardarFactura(opcionesPago = null) {
    if(lineas.length === 0) return alert('La factura está vacía');

    const clienteId = document.getElementById('cliente-id').value;
    if(!clienteId) return alert('Selecciona un cliente');

    const fecha = new Date().toISOString().split('T')[0];
    
    let totalCalc = lineas.reduce((sum, l) => sum + (l.total || 0), 0);
    
    // Payload compatible con crear_factura
    const payload = {
        id: facturaId ? facturaId : undefined,
        numero: numeroFacturaGenerado, // Incluir número
        idcontacto: clienteId,
        fecha: fecha,
        detalles: lineas,
        total: totalCalc,
        // Estado
        estado: opcionesPago ? opcionesPago.estado : 'Pendiente',
        // Pagos
        forma_pago: opcionesPago ? opcionesPago.formaPago : undefined,
        importe_cobrado: opcionesPago ? opcionesPago.importeCobrado : 0
    };

    const url = facturaId ? `/api/facturas/${facturaId}` : '/api/facturas';
    const method = facturaId ? 'PUT' : 'POST'; // Backend usa PUT para update? routes dice PUT

    try {
        const res = await fetch(url, {
            method: method,
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(payload)
        });
        
        const data = await res.json();
        
        if(!res.ok) throw new Error(data.error || 'Error al guardar');
        
        if (opcionesPago) {
            alert('Factura Cobrada Correctamente');
        } else {
            alert('Factura Guardada');
        }
        window.location.href = '/api/auth/mobile/facturas';
        
    } catch(e) {
        console.error(e);
        alert('Error: ' + e.message);
    }
}

// --- Búsqueda de Productos (Igual que tickets) ---
let searchTimeout = null;
async function buscarProductos(query) {
    const container = document.getElementById('prod-resultados');
    if(!query || query.length < 2) {
        container.style.display = 'none';
        return;
    }
    
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(async () => {
        try {
            const res = await fetch(`/api/productos/paginado?search=${encodeURIComponent(query)}&page_size=10`);
            if(res.ok) {
                const data = await res.json();
                const productos = data.items || data.productos || [];
                
                container.innerHTML = '';
                if(productos.length > 0) {
                    container.style.display = 'block';
                    productos.forEach(p => {
                        const div = document.createElement('div');
                        div.style.padding = '10px';
                        div.style.borderBottom = '1px solid #eee';
                        div.style.cursor = 'pointer';
                        const precio = p.precio_venta || p.precio || 0;
                        div.innerHTML = `
                            <div style="font-weight:500;">${p.nombre}</div>
                            <div style="font-size:12px; color:#666;">${formatearImporte(precio)} + ${p.iva}% IVA</div>
                        `;
                        div.onclick = () => seleccionarProducto(p);
                        container.appendChild(div);
                    });
                } else {
                    container.style.display = 'none';
                }
            }
        } catch(e) { console.error(e); }
    }, 300);
}

function seleccionarProducto(p) {
    document.getElementById('prod-desc').value = p.nombre;
    document.getElementById('prod-precio').value = p.precio_venta || p.precio || 0;
    document.getElementById('prod-iva').value = p.iva;
    document.getElementById('prod-resultados').style.display = 'none';
    document.getElementById('prod-search').value = '';
}

// --- Búsqueda de Clientes ---
let clientSearchTimeout = null;
async function buscarClientes(query) {
    const container = document.getElementById('clientes-resultados');
    if(!query || query.length < 2) {
        container.innerHTML = '';
        return;
    }
    
    clearTimeout(clientSearchTimeout);
    clientSearchTimeout = setTimeout(async () => {
        try {
            const res = await fetch(`/api/contactos/paginado?search=${encodeURIComponent(query)}&page_size=20`);
            if(res.ok) {
                const data = await res.json();
                const contactos = data.items || data.contactos || [];
                
                container.innerHTML = '';
                if(contactos.length > 0) {
                    contactos.forEach(c => {
                        const div = document.createElement('div');
                        div.className = 'line-item'; // Reutilizar estilo
                        div.style.cursor = 'pointer';
                        div.innerHTML = `
                            <div class="line-info">
                                <div class="line-title">${c.razonsocial || c.nombre || 'Sin nombre'}</div>
                                <div class="line-meta">${c.nif || ''}</div>
                            </div>
                        `;
                        div.onclick = () => seleccionarCliente(c);
                        container.appendChild(div);
                    });
                } else {
                    container.innerHTML = '<div style="padding:10px; color:#999; text-align:center;">No encontrados</div>';
                }
            }
        } catch(e) { console.error(e); }
    }, 300);
}

function seleccionarCliente(c) {
    const id = c.id || c.idContacto;
    const nombre = c.razonsocial || c.nombre || 'Cliente sin nombre';
    const nif = c.nif || c.identificador || '';
    const direccion = c.direccion || '';
    
    document.getElementById('cliente-id').value = id;
    
    // Renderizar tarjeta de cliente en lugar de texto simple
    const container = document.querySelector('.client-selector');
    container.innerHTML = `
        <div class="client-info-card" style="width:100%;">
            <div style="font-weight:600; font-size:16px;">${nombre}</div>
            <div style="font-size:13px; color:#666; margin-top:2px;">${nif}</div>
            ${direccion ? `<div style="font-size:12px; color:#888; margin-top:2px;">${direccion}</div>` : ''}
        </div>
        <i class="fas fa-pen" style="color:var(--color-primary); margin-left:10px;"></i>
    `;
    
    cerrarModalCliente();
}

// --- Modales ---
function abrirModalProducto() { 
    document.getElementById('modal-producto').classList.add('active'); 
    document.getElementById('prod-search').focus();
}
function cerrarModalProducto() { document.getElementById('modal-producto').classList.remove('active'); }
function limpiarModalProducto() {
    document.getElementById('prod-desc').value = '';
    document.getElementById('prod-cant').value = '1';
    document.getElementById('prod-precio').value = '';
}

function abrirModalCliente() { 
    document.getElementById('modal-cliente').classList.add('active'); 
    document.getElementById('cliente-search').focus();
    buscarClientes(''); // Cargar recientes?
}
function cerrarModalCliente() { document.getElementById('modal-cliente').classList.remove('active'); }

// --- Cobro ---
function cobrarFactura() {
    if(lineas.length === 0) return alert('La factura está vacía');
    if(!document.getElementById('cliente-id').value) return alert('Selecciona cliente');

    let total = lineas.reduce((sum, l) => sum + (l.total || 0), 0);
    document.getElementById('pago-total').value = formatearImporte(total);
    document.getElementById('pago-entregado').value = total.toFixed(2);
    document.getElementById('pago-metodo').value = 'Transferencia';
    actualizarCambio();
    
    document.getElementById('modal-pagos').classList.add('active');
}
function cerrarModalPagos() { document.getElementById('modal-pagos').classList.remove('active'); }

function actualizarCambio() {
    const total = parseImporteInput(document.getElementById('pago-total').value);
    const entregado = parseFloat(document.getElementById('pago-entregado').value) || 0;
    const metodo = document.getElementById('pago-metodo').value;
    
    if (metodo !== 'Efectivo') {
        document.getElementById('div-entregado').style.display = 'none';
        document.getElementById('div-cambio').style.display = 'none';
    } else {
        document.getElementById('div-entregado').style.display = 'block';
        document.getElementById('div-cambio').style.display = 'block';
    }
    
    const cambio = entregado - total;
    document.getElementById('pago-cambio').value = formatearImporte(cambio > 0 ? cambio : 0);
}
function parseImporteInput(val) {
    if(!val) return 0;
    let s = val.toString().replace(' €', '').replace(/\./g, '').replace(',', '.');
    return parseFloat(s) || 0;
}

function confirmarPago() {
    const metodo = document.getElementById('pago-metodo').value;
    const total = parseImporteInput(document.getElementById('pago-total').value);
    let entregado = parseFloat(document.getElementById('pago-entregado').value) || 0;
    
    if (metodo !== 'Efectivo') entregado = total;
    
    // Guardar
    guardarFactura({
        estado: 'Cobrada',
        formaPago: metodo,
        importeCobrado: entregado
    });
    cerrarModalPagos();
}

async function cargarFactura(id) {
    try {
        const res = await fetch(`/api/facturas/${id}`);
        if(!res.ok) throw new Error('Error cargando factura');
        const json = await res.json();
        const data = json.factura || json;
        
        numeroFacturaGenerado = data.numero; // Guardar número existente
        document.getElementById('page-title').textContent = data.numero || `Factura #${id}`;
        
        if(data.contacto) {
            // Usar nueva lógica de selección
            seleccionarCliente(data.contacto);
        } else if(data.idContacto) {
             // Fetch contact?
             cargarCliente(data.idContacto);
        }

        if(data.detalles) {
            lineas = data.detalles.map(d => ({
                concepto: d.concepto,
                descripcion: d.descripcion || d.concepto,
                cantidad: parseFloat(d.cantidad),
                precio: parseFloat(d.precio),
                impuestos: parseFloat(d.impuestos),
                total: parseFloat(d.total)
            }));
            renderLineas();
        }
        
    } catch(e) {
        console.error(e);
        alert('Error cargando factura');
    }
}

// Globales
window.agregarLineaManual = agregarLineaManual;
window.eliminarLinea = eliminarLinea;
window.guardarFactura = guardarFactura;
window.cobrarFactura = cobrarFactura;
window.buscarProductos = buscarProductos;
window.buscarClientes = buscarClientes;
window.seleccionarProducto = seleccionarProducto;
window.seleccionarCliente = seleccionarCliente;
window.abrirModalProducto = abrirModalProducto;
window.cerrarModalProducto = cerrarModalProducto;
window.limpiarModalProducto = limpiarModalProducto;
window.abrirModalCliente = abrirModalCliente;
window.cerrarModalCliente = cerrarModalCliente;
window.abrirModalPagos = abrirModalPagos; // typo in previous logic?
window.cerrarModalPagos = cerrarModalPagos;
window.actualizarCambio = actualizarCambio;
window.confirmarPago = confirmarPago;
