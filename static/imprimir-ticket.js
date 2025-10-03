/**
 * Función principal que se ejecuta al cargar la página.
 */
import { IP_SERVER, PORT } from './constantes.js';
import {
    formatearImporte,
    formatearImporteVariable,
    parsearImporte,
    redondearImporte
} from './scripts_utils.js';
import { mostrarNotificacion } from './notificaciones.js';

window.onload = function() {
    const idTicket = obtenerIdTicket(); // Obtener el ID del ticket desde la URL
    obtenerDatosDelTicket(idTicket).then(datos => {
        rellenarFactura(datos).then(() => {
            // Imprimir cuando el QR esté listo (o tras timeout)
            window.print();
        });
    }).catch(error => {
        console.error('Error al obtener los datos del ticket:', error);
        mostrarNotificacion('Hubo un problema al obtener los datos del ticket.', 'error');
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
    const url = `http://${IP_SERVER}:${PORT}/api/tickets/obtenerTicket/${encodeURIComponent(idTicket)}`;
    return fetch(url)
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
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
        mostrarNotificacion('Datos del ticket incompletos', 'error');
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
        const concepto = detalle?.concepto || '';
        const cantidadNum = parsearImporte(detalle?.cantidad ?? 0);
        const precioNum = parsearImporte(detalle?.precio ?? 0);
        const subtotalSinIVA = redondearImporte(cantidadNum * precioNum);

        const precioDisplay = formatearImporteVariable(precioNum, 0, 5);
        const cantidadDisplay = Number.isFinite(cantidadNum)
            ? cantidadNum.toLocaleString('es-ES', { minimumFractionDigits: 0, maximumFractionDigits: 3 })
            : '';
        const subtotalDisplay = formatearImporte(subtotalSinIVA);

        fila.innerHTML = `
            <td>${concepto}</td>
            <td class="numero">${precioNum ? precioDisplay : ''}</td>
            <td class="numero">${cantidadDisplay}</td>
            <td class="numero">${subtotalSinIVA ? subtotalDisplay : formatearImporte(0)}</td>
        `;

        tbody.appendChild(fila);
    });

    const baseImponible = parsearImporte(ticket.importe_bruto ?? 0);
    const importeIVA = parsearImporte(ticket.importe_impuestos ?? 0);
    const totalTicket = parsearImporte(ticket.total ?? 0);

    document.getElementById('base-imponible').textContent = baseImponible ? formatearImporte(baseImponible) : '';
    document.getElementById('iva').textContent = importeIVA ? formatearImporte(importeIVA) : '';
    document.getElementById('total').textContent = totalTicket ? formatearImporte(totalTicket) : '';

    // Verificar si VERIFACTU está habilitado consultando config.json
    let verifactuHabilitado = false;
    try {
        const configResponse = await fetch('/config.json');
        const config = await configResponse.json();
        verifactuHabilitado = config.verifactu_enabled === true;
    } catch (e) {
        console.log('No se pudo cargar config.json, asumiendo VERIFACTU desactivado');
        verifactuHabilitado = false;
    }

    // Mostrar información VERI*FACTU solo si está habilitado
    const bloqueVerifactu = document.getElementById('hash-ticket')?.parentElement?.parentElement;
    
    if (!verifactuHabilitado) {
        // Si VERIFACTU está desactivado, ocultar toda la sección
        if (bloqueVerifactu) {
            bloqueVerifactu.style.display = 'none';
        }
    } else {
        // Si está habilitado, mostrar solo si hay datos
        const verifactuDisponible = datos.codigo_qr && datos.codigo_qr.length > 50;
        if (!verifactuDisponible && bloqueVerifactu) {
            bloqueVerifactu.style.display = 'none';
        } else {
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
        }
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
