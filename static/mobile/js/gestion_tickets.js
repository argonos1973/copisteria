// Funciones de utilidad (Copiadas para evitar dependencias de módulos en móvil)
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

let ticketId = null; // null = Nuevo
let lineas = [];

document.addEventListener('DOMContentLoaded', () => {
    // Detectar si es edición
    const params = new URLSearchParams(window.location.search);
    if(params.has('id')) {
        ticketId = params.get('id');
        // Se cargará el numero real en cargarTicket
        cargarTicket(ticketId);
    } else {
        // Es nuevo: Obtener siguiente número
        obtenerSiguienteNumero();
    }
});

async function obtenerSiguienteNumero() {
    try {
        const res = await fetch('/api/tickets/obtener_numerador/T');
        if(res.ok) {
            const data = await res.json();
            const year = new Date().getFullYear().toString().slice(-2);
            const num = data.numerador.toString().padStart(4, '0');
            document.getElementById('page-title').textContent = `T${year}-${num}`;
        }
    } catch(e) {
        console.error("Error obteniendo numerador", e);
        document.getElementById('page-title').textContent = "NUEVO";
    }
}

// --- Gestión de Líneas ---
function agregarLineaManual() {
    const desc = document.getElementById('prod-desc').value;
    
    // Parseo robusto: reemplazar coma por punto
    let cantStr = document.getElementById('prod-cant').value.toString().replace(',', '.');
    let precioStr = document.getElementById('prod-precio').value.toString().replace(',', '.');
    
    const cant = parseFloat(cantStr) || 0;
    const precio = parseFloat(precioStr) || 0;
    const iva = parseFloat(document.getElementById('prod-iva').value) || 21;

    if(!desc) return alert('Descripción requerida');
    if(cant <= 0) return alert('Cantidad inválida');

    // CÁLCULO ESTÁNDAR: Usando redondearImporte de scripts_utils
    const subtotalRaw = cant * precio;
    const impuestoMonto = redondearImporte(subtotalRaw * (iva / 100));
    const totalLinea = redondearImporte(subtotalRaw + impuestoMonto);
    
    if(isNaN(totalLinea)) {
        return alert('Error en el cálculo de totales. Verifica los importes.');
    }

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
async function guardarTicket(cobrar = false) {
    if(lineas.length === 0) return alert('El ticket está vacío');

    const clienteId = document.getElementById('cliente-id').value;
    const fecha = new Date().toISOString().split('T')[0]; // YYYY-MM-DD
    
    // Recalcular total exacto de lineas
    let totalCalc = lineas.reduce((sum, l) => sum + (l.total || 0), 0);
    
    if (isNaN(totalCalc)) {
        console.error("Total calculado es NaN");
        totalCalc = 0;
    }
    
    // Obtener número
    let numero = document.getElementById('page-title').textContent;
    if(!numero || numero === 'NUEVO') {
        return alert('No se ha generado un número de ticket válido. Recarga la página.');
    }

    const payload = {
        idContacto: clienteId,
        fecha: fecha,
        detalles: lineas,
        total: totalCalc,
        estado: cobrar ? 'C' : 'P',
        formaPago: 'E',
        numero: ticketId ? numero : numero,
        importe_cobrado: cobrar ? totalCalc : 0
    };

    const url = ticketId ? `/api/tickets/${ticketId}` : '/api/tickets';
    const method = ticketId ? 'PUT' : 'POST';

    try {
        const res = await fetch(url, {
            method: method,
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(payload)
        });
        
        const data = await res.json();
        
        if(!res.ok) throw new Error(data.error || 'Error al guardar');
        
        if (cobrar) {
            alert('Ticket Cobrado Correctamente');
        } else {
            // Solo alertar si es guardado manual, no cobro
            alert('Ticket Guardado');
        }
        window.location.href = '/api/auth/mobile/tickets'; // Volver al listado
        
    } catch(e) {
        console.error(e);
        alert('Error: ' + e.message);
    }
}

// --- Búsqueda de Productos ---
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
                        div.innerHTML = `
                            <div style="font-weight:500;">${p.nombre}</div>
                            <div style="font-size:12px; color:#666;">${formatearImporte(p.precio_venta)} + ${p.iva}% IVA</div>
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
    document.getElementById('prod-desc').value = p.nombre || '';
    
    // Precio: asegurar formato numérico con 2 decimales
    const precio = parseFloat(p.precio_venta || p.precio || 0);
    document.getElementById('prod-precio').value = precio.toFixed(2);
    
    // IVA: seleccionar opción correcta
    const iva = parseInt(p.iva || 21);
    const selectIva = document.getElementById('prod-iva');
    selectIva.value = iva.toString();
    
    // Fallback por si el valor exacto (string) no coincide
    if(selectIva.value !== iva.toString()) {
        for(let i=0; i<selectIva.options.length; i++) {
            if(parseInt(selectIva.options[i].value) === iva) {
                selectIva.selectedIndex = i;
                break;
            }
        }
    }
    
    document.getElementById('prod-resultados').style.display = 'none';
    document.getElementById('prod-search').value = '';
}

// --- Cobro ---
function cobrarTicket() {
    if(lineas.length === 0) return alert('El ticket está vacío');
    
    // Calcular total actual
    let total = lineas.reduce((sum, l) => sum + (l.total || 0), 0);
    document.getElementById('pago-total').value = formatearImporte(total);
    document.getElementById('pago-entregado').value = total.toFixed(2); // Por defecto exacto
    document.getElementById('pago-metodo').value = 'E';
    actualizarCambio();
    
    document.getElementById('modal-pagos').classList.add('active');
    document.getElementById('pago-entregado').focus();
}

function cerrarModalPagos() {
    document.getElementById('modal-pagos').classList.remove('active');
}

function actualizarCambio() {
    const total = parseImporteInput(document.getElementById('pago-total').value);
    const entregado = parseFloat(document.getElementById('pago-entregado').value) || 0;
    const metodo = document.getElementById('pago-metodo').value;
    
    // Si es tarjeta o banco, entregado = total
    if (metodo !== 'E') {
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
    // Convertir "1.234,56 €" a 1234.56
    if(!val) return 0;
    let s = val.toString().replace(' €', '').replace(/\./g, '').replace(',', '.');
    return parseFloat(s) || 0;
}

function confirmarPago() {
    const metodo = document.getElementById('pago-metodo').value;
    const total = parseImporteInput(document.getElementById('pago-total').value);
    let entregado = parseFloat(document.getElementById('pago-entregado').value) || 0;
    
    if (metodo !== 'E') entregado = total; // Tarjeta/Banco: cobro exacto
    
    if (metodo === 'E' && entregado < total) {
        if(!confirm('La cantidad entregada es menor al total. ¿Guardar como Pendiente?')) {
            return;
        }
    }
    
    // Cerrar modal
    cerrarModalPagos();
    
    // Llamar a guardar con opciones
    guardarTicketDefinitivo(metodo, entregado, total);
}

async function guardarTicketDefinitivo(formaPago, importeCobrado, totalTicket) {
    // Determinar estado
    // Usamos redondear para evitar problemas de float
    const cobradoRed = redondearImporte(importeCobrado);
    const totalRed = redondearImporte(totalTicket);
    
    const estado = (cobradoRed >= totalRed) ? 'C' : 'P';
    
    // Reutilizar lógica de guardarTicket pero modificando el payload antes de enviar...
    // Como guardarTicket es monolítica, mejor la adaptamos o creamos payload aquí
    
    const clienteId = document.getElementById('cliente-id').value;
    const fecha = new Date().toISOString().split('T')[0];
    let numero = document.getElementById('page-title').textContent;
    
    const payload = {
        idContacto: clienteId,
        fecha: fecha,
        detalles: lineas,
        total: totalRed,
        estado: estado,
        formaPago: formaPago,
        numero: (numero === 'NUEVO') ? null : numero, // Dejar que backend asigne si es nuevo? No, backend espera numero
        importe_cobrado: cobradoRed
    };
    
    // Si numero es NUEVO, necesitamos uno real. Pero guardarTicket ya lo valida.
    // Vamos a llamar a guardarTicket pasando "cobrar=true" y hackear un poco o refactorizar guardarTicket.
    // Mejor refactorizar guardarTicket para aceptar params.
    
    // Refactorización inline: Copiar lógica de envío
    const url = ticketId ? `/api/tickets/${ticketId}` : '/api/tickets';
    const method = ticketId ? 'PUT' : 'POST';
    
    try {
        const res = await fetch(url, {
            method: method,
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if(!res.ok) throw new Error(data.error || 'Error al guardar');
        
        alert('Ticket Finalizado Correctamente');
        window.location.href = '/api/auth/mobile/tickets';
    } catch(e) {
        alert('Error: ' + e.message);
    }
}

// Modificar guardarTicket original para que sea solo "Guardar Borrador"
// (Ya hace P por defecto)

// --- Carga de Datos (Edición) ---
async function cargarTicket(id) {
    try {
        const res = await fetch(`/api/tickets/${id}`);
        if(!res.ok) throw new Error('Error cargando ticket');
        const data = await res.json();
        
        document.getElementById('page-title').textContent = data.numero;
        document.getElementById('cliente-nombre').textContent = data.razonsocial || 'Cliente';
        document.getElementById('cliente-id').value = data.idContacto;
        
        // Mapear detalles
        if(data.detalles) {
            lineas = data.detalles.map(d => ({
                concepto: d.concepto,
                descripcion: d.descripcion || d.concepto,
                cantidad: parseFloat(d.cantidad),
                precio: parseFloat(d.precio),
                impuestos: parseFloat(d.impuestos),
                total: parseFloat(d.total.replace(',','.'))
            }));
            renderLineas();
        }
        
    } catch(e) {
        console.error(e);
        alert('No se pudo cargar el ticket');
    }
}

// --- Modales ---
function abrirModalProducto() { 
    document.getElementById('modal-producto').classList.add('active'); 
    document.getElementById('prod-desc').focus();
}
function cerrarModalProducto() { document.getElementById('modal-producto').classList.remove('active'); }
function limpiarModalProducto() {
    document.getElementById('prod-desc').value = '';
    document.getElementById('prod-cant').value = '1';
    document.getElementById('prod-precio').value = '';
}

// --- Gestión de Clientes ---
function abrirModalCliente() { 
    document.getElementById('modal-cliente').classList.add('active');
    const input = document.getElementById('cliente-search');
    input.value = '';
    input.focus();
    buscarClientes(''); // Cargar iniciales
}

function cerrarModalCliente() { 
    document.getElementById('modal-cliente').classList.remove('active'); 
}

let clienteSearchTimeout = null;
async function buscarClientes(query) {
    clearTimeout(clienteSearchTimeout);
    clienteSearchTimeout = setTimeout(async () => {
        const container = document.getElementById('cliente-resultados');
        container.innerHTML = '<div style="padding:10px;color:#999;text-align:center;"><i class="fas fa-circle-notch fa-spin"></i> Buscando...</div>';
        
        try {
            let url = `/api/contactos/paginado?page=1&page_size=20`;
            if(query) url += `&search=${encodeURIComponent(query)}`;
            else url += `&sort=razonsocial&order=ASC`;
            
            const res = await fetch(url);
            if(res.ok) {
                const data = await res.json();
                const items = data.contactos || data.items || [];
                
                container.innerHTML = '';
                
                // Opción Cliente Contado siempre disponible si no hay búsqueda o si coincide
                if(!query || 'cliente contado'.includes(query.toLowerCase())) {
                    const div = document.createElement('div');
                    div.className = 'client-item'; // Style in CSS if needed
                    div.style.cssText = 'padding:12px; border-bottom:1px solid #eee; cursor:pointer; display:flex; justify-content:space-between; align-items:center;';
                    div.innerHTML = `<div><div style="font-weight:600">Cliente Contado</div><div style="font-size:12px;color:#666">Genérico</div></div><i class="fas fa-user-tag" style="color:#aaa;"></i>`;
                    div.onclick = () => seleccionarCliente({id: 1, razonsocial: 'Cliente Contado'});
                    container.appendChild(div);
                }

                if(items.length === 0 && query) {
                    container.innerHTML = '<div style="padding:10px;text-align:center;color:#999">No se encontraron clientes</div>';
                } else {
                    items.forEach(c => {
                        const div = document.createElement('div');
                        div.style.cssText = 'padding:12px; border-bottom:1px solid #eee; cursor:pointer;';
                        div.innerHTML = `<div style="font-weight:600">${c.razonsocial || c.nombre}</div><div style="font-size:12px;color:#666">${c.identificador || 'Sin NIF'}</div>`;
                        div.onclick = () => seleccionarCliente(c);
                        container.appendChild(div);
                    });
                }
            }
        } catch(e) {
            console.error(e);
            container.innerHTML = '<div style="padding:10px;color:red;text-align:center;">Error al buscar clientes</div>';
        }
    }, 300);
}

function seleccionarCliente(c) {
    document.getElementById('cliente-id').value = c.id || c.idContacto || 1;
    document.getElementById('cliente-nombre').textContent = c.razonsocial || c.nombre || 'Cliente Contado';
    cerrarModalCliente();
}

// Exponer funciones al scope global para que los onclick del HTML funcionen
window.agregarLineaManual = agregarLineaManual;
window.eliminarLinea = eliminarLinea;
window.guardarTicket = guardarTicket;
window.cobrarTicket = cobrarTicket;
window.abrirModalProducto = abrirModalProducto;
window.cerrarModalProducto = cerrarModalProducto;
window.limpiarModalProducto = limpiarModalProducto;
window.abrirModalCliente = abrirModalCliente;
window.cerrarModalCliente = cerrarModalCliente;
window.buscarClientes = buscarClientes;
window.seleccionarCliente = seleccionarCliente;
window.confirmarPago = confirmarPago;
window.cerrarModalPagos = cerrarModalPagos;
window.actualizarCambio = actualizarCambio;
window.buscarProductos = buscarProductos;
window.seleccionarProducto = seleccionarProducto;
