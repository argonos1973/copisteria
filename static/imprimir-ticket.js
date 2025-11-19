/**
 * Función principal que se ejecuta al cargar la página.
 */
import { IP_SERVER, PORT, API_URL } from './constantes.js?v=1762757322';
import {
    formatearImporte,
    formatearImporteVariable,
    parsearImporte,
    redondearImporte
} from './scripts_utils.js';
import { mostrarNotificacion } from './notificaciones.js';

console.log('[TICKET] Script imprimir-ticket.js cargado');

/**
 * Obtiene los datos del emisor desde el endpoint específico
 * @returns {Promise<Object>} Una promesa que resuelve con los datos del emisor
 */
async function obtenerDatosEmisor() {
    try {
        const response = await fetch('/api/auth/emisor', { credentials: 'include' });
        if (!response.ok) {
            throw new Error('No se pudo obtener datos del emisor');
        }
        const data = await response.json();
        console.log('[TICKET] Datos emisor cargados:', data);
        return data.emisor || {};
    } catch (error) {
        console.error('[TICKET] Error al obtener datos del emisor:', error);
        // Retornar datos vacíos en caso de error
        return {
            nombre: '',
            nif: '',
            direccion: '',
            cp: '',
            ciudad: '',
            provincia: '',
            pais: 'ESP',
            email: '',
            telefono: ''
        };
    }
}

window.onload = function() {
    console.log('[TICKET] window.onload ejecutado');
    const idTicket = obtenerIdTicket(); // Obtener el ID del ticket desde la URL
    
    // Cargar datos del emisor y del ticket en paralelo
    Promise.all([
        obtenerDatosEmisor(),
        obtenerDatosDelTicket(idTicket)
    ]).then(([emisor, datos]) => {
        rellenarFactura(datos, emisor).then(() => {
            // Esperar 1 segundo adicional antes de imprimir para asegurar que todo se renderice
            console.log('[TICKET] Esperando 1 segundo antes de imprimir...');
            setTimeout(() => {
                console.log('[TICKET] Lanzando impresión');
                window.print();
            }, 1000);
        });
    }).catch(error => {
        console.error('[TICKET] Error al obtener los datos:', error);
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
    const url = `${API_URL}/api/tickets/obtenerTicket/${encodeURIComponent(idTicket)}`;
    console.log('[TICKET] Obteniendo datos de:', url);
    return fetch(url, {
        credentials: 'same-origin'  // Importante: enviar cookies de sesión
    })
        .then(response => {
            console.log('[TICKET] Respuesta recibida:', response.status);
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
 * @param {Object} emisor - Objeto con los datos del emisor.
 */
async function rellenarFactura(datos, emisor) {
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

    // Datos del emisor desde JSON del emisor (en mayúsculas)
    document.getElementById('emisor-nombre').textContent = (emisor.nombre || '').toUpperCase();
    
    // Construir dirección completa: DIRECCION, CIUDAD (CP)
    const direccionCompleta = [emisor.direccion, emisor.ciudad, `(${emisor.cp})`]
        .filter(Boolean)
        .join(', ');
    document.getElementById('emisor-direccion').textContent = direccionCompleta.toUpperCase();
    document.getElementById('emisor-nif').textContent = (emisor.nif || '').toUpperCase();
    document.getElementById('emisor-email').textContent = (emisor.email || '').toLowerCase();
    
    console.log('[TICKET] Datos del emisor aplicados:', {
        nombre: emisor.nombre,
        nif: emisor.nif,
        direccion: emisor.direccion,
        ciudad: emisor.ciudad,
        cp: emisor.cp,
        email: emisor.email
    });

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

    // Verificar si VERIFACTU está habilitado desde los datos del ticket
    const verifactuHabilitado = datos.verifactu_enabled === true;
    console.log('[VERIFACTU] Estado recibido del servidor:', verifactuHabilitado);

    // DEBUG: Mostrar datos recibidos
    console.log('[VERIFACTU] Datos recibidos:', {
        verifactuHabilitado,
        tiene_codigo_qr: !!datos.codigo_qr,
        longitud_qr: datos.codigo_qr ? datos.codigo_qr.length : 0,
        tipo_codigo_qr: typeof datos.codigo_qr,
        codigo_qr_preview: datos.codigo_qr ? datos.codigo_qr.substring(0, 50) : 'null/undefined',
        tiene_csv: !!datos.csv,
        csv: datos.csv,
        estado_envio: datos.estado_envio,
        errores_aeat: datos.errores_aeat
    });

    // Mostrar información VERI*FACTU
    const bloqueVerifactu = document.getElementById('hash-ticket')?.parentElement?.parentElement;
    const tieneQR = !!(datos.codigo_qr && datos.codigo_qr.length > 50);
    
    if (!verifactuHabilitado) {
        // Si VERIFACTU está desactivado, ocultar toda la sección
        console.log('[VERIFACTU] Desactivado - ocultando bloque');
        if (bloqueVerifactu) {
            bloqueVerifactu.style.display = 'none';
        }
    } else {
        console.log('[VERIFACTU] Habilitado - mostrando datos disponibles (QR:', tieneQR, ')');
        
        // Mostrar bloque VERIFACTU
        if (bloqueVerifactu) {
            bloqueVerifactu.style.display = 'block';
        }
        
        // 1. Mostrar CSV si existe
        const csvElem = document.getElementById('hash-ticket');
        if (csvElem) {
            if (datos.csv) {
                csvElem.textContent = `CSV: ${datos.csv}`;
                console.log('[VERIFACTU] CSV asignado:', datos.csv);
            } else {
                csvElem.textContent = 'CSV: Pendiente de envío a AEAT';
            }
        }
        
        // 2. Gestionar QR o mensaje de error
        const imgQR = document.getElementById('qr-verifactu');
        if (imgQR) {
            if (tieneQR) {
                // Hay QR válido - mostrarlo
                imgQR.src = `data:image/png;base64,${datos.codigo_qr}`;
                imgQR.style.display = 'block';
                console.log('[VERIFACTU] QR asignado a imagen');
            } else if (datos.estado_envio === 'ERROR' && datos.errores_aeat) {
                // Error de AEAT - mostrar mensaje de error
                console.error('[VERIFACTU] Error de AEAT:', datos.errores_aeat);
                const errorMatch = datos.errores_aeat.match(/Codigo\[(\d+)\]\.([^:]+)/);
                const codigoError = errorMatch ? errorMatch[1] : 'N/A';
                const mensajeCorto = errorMatch ? errorMatch[2].substring(0, 40) + '...' : 'Error de AEAT';
                
                // Crear div con mensaje de error
                const errorDiv = document.createElement('div');
                errorDiv.style.cssText = 'width:140px;height:140px;border:2px solid #dc3545;display:flex;justify-content:center;align-items:center;text-align:center;padding:10px;font-size:10px;background:#fff5f5;';
                errorDiv.innerHTML = `
                    <div>
                        <div style="color:#dc3545;font-weight:bold;margin-bottom:5px;">❌ ERROR AEAT</div>
                        <div style="font-size:9px;color:#666;">Código: ${codigoError}</div>
                        <div style="font-size:8px;color:#888;margin-top:5px;" title="${datos.errores_aeat}">${mensajeCorto}</div>
                    </div>
                `;
                imgQR.replaceWith(errorDiv);
                console.log('[VERIFACTU] Mensaje de error mostrado');
            } else {
                // Pendiente de envío
                console.log('[VERIFACTU] QR pendiente - mostrando mensaje');
                const pendienteDiv = document.createElement('div');
                pendienteDiv.style.cssText = 'width:140px;height:140px;border:1px solid #ddd;display:flex;justify-content:center;align-items:center;text-align:center;padding:10px;font-size:11px;';
                pendienteDiv.textContent = 'QR pendiente';
                imgQR.replaceWith(pendienteDiv);
            }
        }
    }

    // ---- Esperar carga QR y datos ----
    console.log('[VERIFACTU] Esperando carga de QR...');
    await new Promise((res) => {
        const imgQR = document.getElementById('qr-verifactu');
        if (imgQR && imgQR.complete && imgQR.naturalWidth > 0) {
            console.log('[VERIFACTU] QR ya cargado');
            res();
        } else if (imgQR && imgQR.src) {
            imgQR.onload = () => {
                console.log('[VERIFACTU] QR cargado con éxito');
                res();
            };
            imgQR.onerror = () => {
                console.log('[VERIFACTU] Error al cargar QR');
                res();
            };
            // Seguridad: timeout 3 segundos (aumentado)
            setTimeout(() => {
                console.log('[VERIFACTU] Timeout - continuando con impresión');
                res();
            }, 3000);
        } else {
            console.log('[VERIFACTU] No hay QR para cargar');
            res();
        }
    });
    
    console.log('[VERIFACTU] Listo para imprimir');
}
