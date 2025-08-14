import { IP_SERVER, PORT, API_URL } from './constantes.js'
import { mostrarNotificacion } from './notificaciones.js'
import { formatearImporte, formatearFechaSoloDia, parsearImporte, mostrarCargando, ocultarCargando } from './scripts_utils.js'

window.buscarTickets = buscarTickets;
// Selecciona todos los botones en la página
const botones = document.querySelectorAll('button');
const API_ENDPOINT = '/tickets/consulta'

// Añade un evento de clic a cada botón
botones.forEach(boton => {
    boton.addEventListener('click', function() {
        mostrarBarraDeProgreso();
    });
});

document.addEventListener("DOMContentLoaded", function () {
    if (sessionStorage.getItem('ticketFilters')) {
        const filters = JSON.parse(sessionStorage.getItem('ticketFilters'));

        // Aplicar los filtros almacenados
        document.getElementById('startDate').value = filters.startDate || '';
        document.getElementById('endDate').value = filters.endDate || '';
        document.getElementById('status').value = filters.status || '';
        document.getElementById('ticketNumber').value = filters.ticketNumber || '';
        document.getElementById('conceptFilter').value = filters.conceptFilter || '';
        document.getElementById('paymentMethod').value = filters.paymentMethod || '';
    } else {
        // Obtener la fecha de hoy
        const today = new Date();
        const yyyy = today.getFullYear();
        const mm = String(today.getMonth() + 1).padStart(2, '0');
        const dd = String(today.getDate()).padStart(2, '0');

        // Formatear la fecha de hoy
        const todayFormatted = `${yyyy}-${mm}-${dd}`;

        // Obtener los elementos de fecha del DOM
        const startDate = document.getElementById('startDate');
        const endDate = document.getElementById('endDate');

        // Asignar los valores a los inputs
        startDate.value = todayFormatted;

        // Obtener el último día del mes actual
        const lastDayOfMonth = new Date(yyyy, today.getMonth() + 1, 0);
        const lastDay = String(lastDayOfMonth.getDate()).padStart(2, '0');
        const lastDayFormatted = `${yyyy}-${mm}-${lastDay}`;
        endDate.value = lastDayFormatted;
    }

    // Asociar eventos para búsqueda interactiva
    document.getElementById('startDate').addEventListener('change', () => {
        guardarFiltros();
        buscarTickets();
    });

    document.getElementById('endDate').addEventListener('change', () => {
        guardarFiltros();
        buscarTickets();
    });

    document.getElementById('status').addEventListener('change', () => {
        guardarFiltros();
        buscarTickets();
    });

    document.getElementById('ticketNumber').addEventListener('input', (event) => {
        guardarFiltros();
        busquedaInteractiva(event);
    });

    document.getElementById('conceptFilter').addEventListener('input', (event) => {
        guardarFiltros();
        busquedaInteractiva(event);
    });

    document.getElementById('paymentMethod').addEventListener('change', () => {
        guardarFiltros();
        buscarTickets();
    });
 
    buscarTickets();
});

// Función para búsqueda interactiva
let timeoutId = null;
let currentController = null;
function busquedaInteractiva(event) {
    const valor = event.target.value.trim();
    const campo = event.target.id;
    
    // Limpiar el timeout anterior si existe
    if (timeoutId) {
        clearTimeout(timeoutId);
    }

    // Esperar 500 ms después de que el usuario deje de escribir
    timeoutId = setTimeout(() => {
        const suficiente = valor.length === 0 || valor.length >= 3; // al menos 3 caracteres antes de buscar
        if ((campo === 'ticketNumber' || campo === 'conceptFilter') && suficiente) {
            buscarTickets();
        }
    }, 500);
}

function mostrarBarraDeProgreso() {
    mostrarCargando();
}
/* eliminado progreso local, usando spinner global
    mostrarCargando();
}
    
    

    
    // Eliminado progreso porcentual
    
        
            
           

        }
    }, 300);
*/

function ocultarBarraDeProgreso() {
    ocultarCargando();
}
    
    
// Función para guardar los filtros en sessionStorage
function guardarFiltros() {
    const filtros = {
        startDate: document.getElementById('startDate').value,
        endDate: document.getElementById('endDate').value,
        status: document.getElementById('status').value,
        ticketNumber: document.getElementById('ticketNumber').value,
        paymentMethod: document.getElementById('paymentMethod').value,
        conceptFilter: document.getElementById('conceptFilter').value
    };
    sessionStorage.setItem('ticketFilters', JSON.stringify(filtros));
}

async function buscarTickets() {
    mostrarBarraDeProgreso();

    const paymentMethod = document.getElementById('paymentMethod').value;
    const conceptFilter = document.getElementById('conceptFilter').value;
    const startDate = document.getElementById('startDate').value;
    const endDate = document.getElementById('endDate').value;
    const status = document.getElementById('status').value;
    const ticketNumber = document.getElementById('ticketNumber').value;

    const url = new URL(`${API_URL}/api${API_ENDPOINT}`);

    // Verificar si hay filtros de estado o número de ticket
    const ignorarFechas = status || ticketNumber;

    // Solo agregar fechas si no hay filtros de estado o número de ticket
    if (!ignorarFechas) {
        if (startDate) url.searchParams.append('fecha_inicio', startDate);
        if (endDate) url.searchParams.append('fecha_fin', endDate);
    }
    
    // Agregar el resto de filtros normalmente
    if (status) url.searchParams.append('estado', status);
    if (ticketNumber) url.searchParams.append('numero', ticketNumber);
    if (paymentMethod) url.searchParams.append('formaPago', paymentMethod);
    if (conceptFilter) url.searchParams.append('concepto', conceptFilter);
    
    try {
        // Cancelar petición previa
        if (currentController) currentController.abort();
        currentController = new AbortController();
        console.log('Buscando tickets con URL:', url.toString());
        const response = await fetch(url, { signal: currentController.signal });
        if (!response.ok) throw new Error('Error al consultar los tickets');
        
        const tickets = await response.json();
        mostrarTickets(tickets);
        actualizarTotales(tickets);
        ocultarBarraDeProgreso();
    } catch (error) {
        if (error.name === 'AbortError') {
            // Petición anterior abortada: no mostrar error ni notificación
            return;
        }
        console.error(error);
        mostrarNotificacion('Error al consultar los tickets', 'error');
        ocultarBarraDeProgreso();
    }
}

function mostrarTickets(tickets) {
    const gridBody = document.getElementById('gridBody');
    gridBody.innerHTML = '';

    if (tickets.length > 0) {
        tickets.forEach(ticket => {
            let textoEstado = '';
            let claseEstado = '';
            let textoPago = '';

            if (ticket.formaPago === "T") {
                textoPago = "Tarjeta";
            } else {
                textoPago = "Efectivo";
            }

            if (ticket.estado === 'C') {
                textoEstado = 'Cobrado';
                claseEstado = 'estado-cobrado';
            } else if (ticket.estado === 'A') {
                textoEstado = 'Anulado';
                claseEstado = 'estado-anulada';
                textoPago   = '?' ;
            } else if (['RF','RC','RE'].includes(ticket.estado)) {
                textoEstado = 'Rectific.';
                claseEstado = 'estado-rectificativa';
                textoPago   = '?';
            } else {
                textoEstado = 'Pendiente';
                claseEstado = 'estado-pendiente';
                textoPago   = '?'
            }

            // Crear la fila (tr)
            const row = document.createElement('tr');

            // Aplicar estilos de fila y bloqueo según estado
            if (ticket.estado === 'A') {
                // Anulado → misma clase que facturas anuladas
                row.classList.add('fila-anulada', 'fila-bloqueada');
                row.style.cursor = 'default';
            } else if (['RF','RC','RE'].includes(ticket.estado)) {
                // Rectificativos
                row.classList.add('fila-rectificativa', 'fila-bloqueada');
                row.style.cursor = 'default';
            } else {
                row.style.cursor = 'pointer';
                row.addEventListener('click', () => {
                    window.location.href = `GESTION_TICKETS.html?ticketId=${ticket.id}`;
                });
            }

            // Crear y añadir las celdas (td)
            const fechaCell = document.createElement('td');
            fechaCell.textContent = `${formatearFechaSoloDia(ticket.fecha)} ${formatearHora(ticket.timestamp)}`;
            row.appendChild(fechaCell);

            const numeroCell = document.createElement('td');
            numeroCell.textContent = ticket.numero;
            row.appendChild(numeroCell);

            const importeBrutoCell = document.createElement('td');
            importeBrutoCell.classList.add('text-right');
            importeBrutoCell.textContent = formatearImporte(ticket.importe_bruto);
            row.appendChild(importeBrutoCell);

            const impuestosCell = document.createElement('td');
            impuestosCell.classList.add('text-right');
            impuestosCell.textContent = formatearImporte(ticket.importe_impuestos);
            row.appendChild(impuestosCell);

            const importeCobradoCell = document.createElement('td');
            importeCobradoCell.classList.add('text-right');
            importeCobradoCell.textContent = formatearImporte(ticket.importe_cobrado);
            row.appendChild(importeCobradoCell);

            const totalCell = document.createElement('td');
            totalCell.classList.add('text-right');
            totalCell.textContent = formatearImporte(ticket.total);
            row.appendChild(totalCell);

            const estadoCell = document.createElement('td');
            estadoCell.classList.add('text-center', claseEstado);
            estadoCell.textContent = textoEstado;
            row.appendChild(estadoCell);

            const pagoCell = document.createElement('td');
            pagoCell.classList.add('text-center');
            pagoCell.textContent = textoPago;
            row.appendChild(pagoCell);

            // Crear la celda para el icono de imprimir
            const printCell = document.createElement('td');
            printCell.classList.add('text-center', 'col-imprimir');
            if (ticket.estado !== 'A') {
                const printIcon = document.createElement('i');
                printIcon.classList.add('fas', 'fa-print', 'icono-imprimir');
                printIcon.style.cursor = 'pointer';
                printIcon.style.color = '#000000';
                printIcon.addEventListener('click', function(event) {
                    event.stopPropagation();
                    imprimirFactura(ticket.id);
                });
                printCell.appendChild(printIcon);
            }
            row.appendChild(printCell);

            // Añadir la fila al cuerpo de la tabla
            gridBody.appendChild(row);
        });
    } else {
        gridBody.innerHTML = '<tr><td colspan="9" class="no-results">No se encontraron resultados</td></tr>';
    }
}

function formatearHora(timestamp) {
    const fecha = new Date(timestamp);
    const horas = fecha.getHours().toString().padStart(2, '0');
    const minutos = fecha.getMinutes().toString().padStart(2, '0');
    const segundos = fecha.getSeconds().toString().padStart(2, '0');
    return `${horas}:${minutos}:${segundos}`;
}

function actualizarTotales(tickets) {
    let totalImporteBruto = 0;
    let totalImporteImpuestos = 0;
    let totalImporteCobrado = 0;
    let totalTotal = 0;

    const gridBody = document.getElementById('gridBody');
    const rows = gridBody.getElementsByTagName('tr');

    for (let row of rows) {
        const cells = row.getElementsByTagName('td');

        // Verificar que la fila no sea una fila de 'No se encontraron resultados'
        if (cells.length < 7) continue;

        // Obtener los valores de las celdas y convertirlos a números
        let importeBruto = parsearImporte(cells[2].textContent);
        let importeImpuestos = parsearImporte(cells[3].textContent);
        let importeCobrado = parsearImporte(cells[4].textContent);
        let total = parsearImporte(cells[5].textContent);

        if (cells[7].textContent != '?') {
            totalImporteBruto += importeBruto;
            totalImporteImpuestos += importeImpuestos;
            totalImporteCobrado += importeCobrado;
            totalTotal += total;
        }
    }

    // Actualizar los totales en el DOM
    const totalBrutoElement = document.getElementById('totalImporteBruto');
    const totalImpuestosElement = document.getElementById('totalImporteImpuestos');
    const totalCobradoElement = document.getElementById('totalImporteCobrado');
    const totalTotalElement = document.getElementById('totalTotal');

    if (totalBrutoElement) totalBrutoElement.textContent = formatearImporte(totalImporteBruto);
    if (totalImpuestosElement) totalImpuestosElement.textContent = formatearImporte(totalImporteImpuestos);
    if (totalCobradoElement) totalCobradoElement.textContent = formatearImporte(totalImporteCobrado);
    if (totalTotalElement) totalTotalElement.textContent = formatearImporte(totalTotal);
}


function imprimirFactura(idTicket) {
    try {
        // Construir la URL para la página de impresión con el parámetro 'ticketId'
        const urlImprimir = `imprimir-ticket.html?ticketId=${encodeURIComponent(idTicket)}`;
        // Abrir una nueva ventana con la página de impresión
        window.open(urlImprimir, '_blank', 'width=800,height=600');
    } catch (error) {
        console.error('Error al preparar la impresión:', error);
        mostrarNotificacion('Error al preparar la impresión', 'error');
    }
}

document.getElementById('btn-nuevo-ticket').addEventListener('click', function() {
    window.location.href = 'GESTION_TICKETS.html';
});
