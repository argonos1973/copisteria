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

    const total = cant * precio * (1 + iva/100);
    
    // Protección contra NaN
    if(isNaN(total)) {
        return alert('Error en el cálculo de totales. Verifica los importes.');
    }

    const linea = {
        concepto: desc, // En backend se usa 'concepto'
        descripcion: desc,
        cantidad: cant,
        precio: precio,
        impuestos: iva,
        total: total // Total con IVA
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
                    <div class="line-meta">${linea.cantidad} x ${formatCurrency(linea.precio)} (+${linea.impuestos}%)</div>
                </div>
                <div class="line-price">${formatCurrency(linea.total)}</div>
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
        const baseLinea = l.cantidad * l.precio;
        const impLinea = baseLinea * (l.impuestos / 100);
        base += baseLinea;
        totalImpuestos += impLinea;
        total += l.total; // O recalcular: base + impuestos
    });

    document.getElementById('resumen-base').textContent = formatCurrency(base);
    document.getElementById('resumen-iva').textContent = formatCurrency(totalImpuestos);
    document.getElementById('total-final').textContent = formatCurrency(total);
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
    
    // Obtener número (asegurar que no es 'NUEVO' o 'AUTO')
    let numero = document.getElementById('page-title').textContent;
    if(!numero || numero === 'NUEVO') {
        return alert('No se ha generado un número de ticket válido. Recarga la página.');
    }

    const payload = {
        idContacto: clienteId,
        fecha: fecha,
        detalles: lineas,
        total: totalCalc,
        estado: cobrar ? 'C' : 'P', // C=Cobrado, P=Pendiente
        formaPago: 'E', // Defecto Efectivo
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
        
        alert(cobrar ? 'Ticket Cobrado Correctamente' : 'Ticket Guardado');
        window.location.href = '/api/auth/mobile/tickets'; // Volver al listado
        
    } catch(e) {
        console.error(e);
        alert('Error: ' + e.message);
    }
}

function cobrarTicket() {
    if(confirm('¿Marcar como cobrado y finalizar?')) {
        guardarTicket(true);
    }
}

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
                total: parseFloat(d.total.replace(',','.')) // Si viene formateado
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

function abrirModalCliente() { alert('Selector de clientes próximamente'); }

function formatCurrency(value) {
    if (value === null || value === undefined || isNaN(value)) {
        return new Intl.NumberFormat('es-ES', { style: 'currency', currency: 'EUR' }).format(0);
    }
    return new Intl.NumberFormat('es-ES', { style: 'currency', currency: 'EUR' }).format(value);
}
