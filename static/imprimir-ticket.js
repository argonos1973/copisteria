/**
 * Función principal que se ejecuta al cargar la página.
 */
import { formatearImporte } from './scripts_utils.js';

window.onload = function() {
    const idTicket = obtenerIdTicket(); // Obtener el ID del ticket desde la URL
    obtenerDatosDelTicket(idTicket).then(datos => {
        rellenarFactura(datos).then(() => {
            // Imprimir cuando el QR esté listo (o tras timeout)
            window.print();
        });
    }).catch(error => {
        console.error('Error al obtener los datos del ticket:', error);
        alert('Hubo un problema al obtener los datos del ticket.');
    });
};

window.addEventListener('afterprint', function() {
        window.close();
    });

/**
 * Obtiene el ID del ticket desde los parámetros de la URL.
 * @returns {string} El ID del ticket.
 */
function obtenerIdTicket() {
    const urlParams = new URLSearchParams(window.location.search);
    return urlParams.get('ticketId') || '1'; // Valor por defecto si no hay ticketId
}

/**
 * Obtiene los datos del ticket desde el servidor.
 * @param {string} idTicket - El ID del ticket.
 * @returns {Promise<Object>} Una promesa que resuelve con los datos del ticket.
 */
function obtenerDatosDelTicket(idTicket) {
    return new Promise((resolve, reject) => {
        // URL de la API para obtener los datos del ticket
        // Endpoint para obtener ticket con detalles y datos VERI*FACTU
        const url = `/api/tickets/obtenerTicket/${encodeURIComponent(idTicket)}`;

        // Hacer la solicitud al servidor
        fetch(url)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json(); // Parsear la respuesta como JSON
            })
            .then(data => {
                resolve(data); // Resolver la promesa con los datos obtenidos
            })
            .catch(error => {
                reject(error); // Rechazar la promesa si hay un error
            });
    });
}

/**
/**
 * Capitaliza la primera letra de una cadena.
 * @param {string} texto - El texto a capitalizar.
 * @returns {string} El texto con la primera letra en mayúscula.
 */
function capitalizarPrimeraLetra(texto) {
    if (!texto) return '';
    return texto.charAt(0).toUpperCase() + texto.slice(1).toLowerCase();
}

/**
 * Rellena la factura con los datos proporcionados.
 * @param {Object} datos - Objeto con los datos del ticket.
 */
async function rellenarFactura(datos) {
    // Procesamos la información y, al final, esperamos a que el QR (si existe) acabe de cargar
    // Asegurarnos de que 'datos' tiene la estructura esperada
    if (!datos.ticket || !datos.detalles) {
        alert('Datos del ticket incompletos');
        return;
    }

    const ticket = datos.ticket;
    const detalles = datos.detalles;

    // Actualizar el título del documento para que coincida con el número de ticket
    document.title = `Ticket ${ticket.numero}`;

    // -------------------
    //  Bloque rectificativo
    // -------------------
    const esRectificativo = (ticket.estado === 'RF' || ticket.estado === 'RE' || ticket.tipo === 'R' || (ticket.numero && String(ticket.numero).endsWith('-R')));
    if (esRectificativo) {
        // Cambiar el título principal
        const tituloElem = document.getElementById('titulo-principal');
        if (tituloElem) tituloElem.textContent = 'TICKET RECTIFICATIVO';

        // Mostrar bloque y rellenar datos
        const bloqueRect = document.getElementById('info-rectificativo');
        if (bloqueRect) bloqueRect.style.display = 'block';

        // Obtener información del ticket original
        if (ticket.id_ticket_rectificado) {
            try {
                const respOrig = await fetch(`/api/tickets/obtenerTicket/${ticket.id_ticket_rectificado}`);
                if (respOrig.ok) {
                    const datosOrig = await respOrig.json();
                    if (datosOrig && datosOrig.ticket) {
                        document.getElementById('ticket-original-numero').textContent = datosOrig.ticket.numero;
                        // Formatear fecha original
                        const fechaOrig = datosOrig.ticket.fecha || '';
                        const partes = fechaOrig.split('-');
                        let fechaFmt = fechaOrig;
                        if (partes.length === 3) fechaFmt = `${partes[2]}/${partes[1]}/${partes[0]}`;
                        document.getElementById('ticket-original-fecha').textContent = fechaFmt;
                    }
                }
            } catch (e) {
                console.warn('No se pudo obtener ticket original', e);
            }
        }
    }

    // Rellenar la cabecera
    document.getElementById('numero').textContent = ticket.numero;

    // Formatear la fecha al formato DD/MM/AAAA
    const fechaOriginal = ticket.fecha; // Asumiendo que 'ticket.fecha' es la fecha original
    const partesFecha = fechaOriginal.split('-');
    let fechaFormateada = fechaOriginal; // Valor por defecto
    if (partesFecha.length === 3) {
        fechaFormateada = `${partesFecha[2]}/${partesFecha[1]}/${partesFecha[0]}`;
    }
    document.getElementById('fecha').textContent = fechaFormateada;

    // Determinar el estado descriptivo
    let textoEstado = '';
    if (['RF','RC','RE'].includes(ticket.estado)) {
        textoEstado = 'Rectificativo';
    } else if (ticket.estado === 'A') {
        textoEstado = 'Anulado';
    } else if (ticket.estado === 'P') {
        textoEstado = 'Pendiente';
    } else {
        textoEstado = 'Pagado'; // Estado C
    }
    document.getElementById('estado').textContent = textoEstado;

    // Datos del emisor en mayúsculas
    document.getElementById('emisor-nombre').textContent = 'SAMUEL RODRIGUEZ MIQUEL';
    document.getElementById('emisor-direccion').textContent = 'LEGALITAT, 70, BARCELONA (08024)';
    document.getElementById('emisor-nif').textContent = '44007535W';
    document.getElementById('emisor-email').textContent = 'info@aleph70.com';

    // Si hay un campo para la forma de pago, lo capitalizamos
    if (ticket.forma_pago) {
        const formaPagoCapitalizada = capitalizarPrimeraLetra(ticket.forma_pago);
        //document.getElementById('forma-pago').textContent = formaPagoCapitalizada;
    }

    // Rellenar la tabla de productos
    const tbody = document.getElementById('productos');
    tbody.innerHTML = ''; // Limpiar cualquier contenido existente

    detalles.forEach(detalle => {
        const fila = document.createElement('tr');

        // Asumiendo que los campos son 'concepto', 'precio', 'cantidad', 'impuestos', 'total'
        fila.innerHTML = `
            <td>${detalle.concepto}</td>
            <td class="numero">${detalle.precio !== undefined ? detalle.precio.toFixed(5).replace('.', ',') : ''}€</td>
            <td class="numero">${detalle.cantidad}</td>
            <td class="numero">21</td>
            <td class="numero">${formatearImporte(detalle.total)}€</td>
        `;

        tbody.appendChild(fila);
    });

    // Rellenar los totales
     document.getElementById('base-imponible').textContent = `${formatearImporte(ticket.importe_bruto)}€`;
     document.getElementById('iva').textContent = `${ticket.importe_impuestos.toFixed(2).replace('.', ',')}€`;
     document.getElementById('total').textContent = `${formatearImporte(ticket.total)}€`;

    // Mostrar información VERI*FACTU
    const verifactuDisponible = datos.codigo_qr && datos.codigo_qr.length > 50;
    const bloqueVerifactu = document.getElementById('hash-ticket')?.parentElement?.parentElement;
    if (!verifactuDisponible && bloqueVerifactu) {
        // Ocultar sección si no hay datos
        bloqueVerifactu.style.display = 'none';
    }

    // QR
    if (verifactuDisponible) {
        const imgQR = document.getElementById('qr-verifactu');
        imgQR.src = `data:image/png;base64,${datos.codigo_qr}`;
    }

    // CSV / Hash (se usa CSV como identificador comprobante)
    if (datos.csv) {
        const csvElem = document.getElementById('hash-ticket');
        if (csvElem) csvElem.textContent = `CSV: ${datos.csv}`;
    }

    // ---- Esperar carga QR ----
    await new Promise((res) => {
        const imgQR = document.getElementById('qr-verifactu');
        if (imgQR && imgQR.complete) {
            res();
        } else if (imgQR) {
            imgQR.onload = () => res();
            // Seguridad: timeout 1 s
            setTimeout(res, 1000);
        } else {
            res();
        }
    });
}
