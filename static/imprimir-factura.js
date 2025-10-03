import { IP_SERVER, PORT } from './constantes.js';
import { formatearImporte, formatearFecha, formatearFechaSoloDia } from './scripts_utils.js';
import { mostrarNotificacion } from './notificaciones.js';

/**
 * Función principal que se ejecuta al cargar la página.
 */
window.onload = function() {
    const idFactura = obtenerIdFactura(); // Obtener el ID de la factura desde la URL
    obtenerDatosDeLaFactura(idFactura).then(datos => {
        rellenarFactura(datos);
        
        // Retraso para asegurar que el QR se cargue completamente antes de imprimir
        console.log('Esperando a que se cargue el código QR antes de imprimir...');
        setTimeout(() => {
            console.log('Iniciando impresión automática');
            window.print();
        }, 2000); // Esperar 2 segundos para que se cargue el QR (aumentado de 1,5 a 2 segundos para mayor seguridad)
    }).catch(error => {
        console.error('Error al obtener los datos de la factura:', error);
        mostrarNotificacion('Hubo un problema al obtener los datos de la factura.', 'error');
    });
};

window.addEventListener('afterprint', function() {
    window.close();
});

/**
 * Obtiene el ID de la factura desde los parámetros de la URL.
 * @returns {string} El ID de la factura.
 */
function obtenerIdFactura() {
    const urlParams = new URLSearchParams(window.location.search);
    return urlParams.get('facturaId');
}

// Helpers de formato numérico ES (coma decimal, punto de miles)
function _splitSign(s) {
    return s.startsWith('-') ? ['-', s.slice(1)] : ['', s];
}

function formatNumberEsMax5(val) {
    // Hasta 5 decimales, sin redondear (trunca), quitar ceros finales
    if (val === null || val === undefined) return '0';
    let s = String(val).replace(',', '.');
    const [sign, rest] = _splitSign(s);
    let entero = rest, dec = '';
    if (rest.includes('.')) {
        [entero, dec] = rest.split('.', 2);
    }
    let enteroFmt;
    try {
        enteroFmt = Number.parseInt(entero, 10).toLocaleString('es-ES');
    } catch {
        enteroFmt = entero;
    }
    if (dec) {
        dec = dec.slice(0, 5).replace(/0+$/g, '');
    }
    return sign + enteroFmt + (dec ? ',' + dec : '');
}

function formatTotalEsTwo(val) {
    // Total con exactamente 2 decimales
    const num = Number.parseFloat(val ?? 0) || 0;
    const fixed = num.toFixed(2);
    const [sign, rest] = _splitSign(fixed);
    const [entero, dec] = rest.split('.');
    let enteroFmt;
    try {
        enteroFmt = Number.parseInt(entero, 10).toLocaleString('es-ES');
    } catch {
        enteroFmt = entero;
    }
    return sign + enteroFmt + ',' + (dec || '00');
}

/**
 * Obtiene los datos de la factura desde el servidor.
 * @param {string} idFactura - El ID de la factura.
 * @returns {Promise<Object>} Una promesa que resuelve con los datos de la factura.
 */
async function obtenerDatosDeLaFactura(idFactura) {
    try {
        if (!idFactura) {
            console.error('ID de factura no proporcionado. URL actual:', window.location.href);
            throw new Error('ID de factura no proporcionado');
        }

        console.log('Obteniendo datos de la factura:', idFactura);
        
        // Volver a usar la ruta original que funciona
        const url = `http://${IP_SERVER}:${PORT}/api/facturas/consulta/${idFactura}`;
        console.log('URL de la solicitud:', url);
        
        const response = await fetch(url);
        console.log('Estado de la respuesta:', response.status);
        
        if (!response.ok) {
            const errorText = await response.text();
            console.error('Error en la respuesta:', errorText);
            throw new Error(`Error HTTP: ${response.status}. Detalles: ${errorText}`);
        }

        const datos = await response.json();
        console.log('Datos recibidos:', datos);
        
        // Devolver los datos tal cual vienen del servidor
        return datos;

    } catch (error) {
        console.error('Error al obtener datos de la factura:', error);
        throw error;
    }
}

/**
 * Formatea un importe numérico utilizando coma como separador decimal.
 * @param {number} importe - El importe a formatear.
 * @param {number} decimales - Número de decimales a mostrar (por defecto 2).
 * @returns {string} El importe formateado.
 */
// La función formatearImporte ahora se importa desde scripts_utils.js

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
 * Decodifica la forma de pago.
 * @param {string} formaPago - La forma de pago a decodificar.
 * @returns {string} La forma de pago decodificada.
 */
function decodificarFormaPago(formaPago) {
    console.log('Decodificando forma de pago:', formaPago);
    
    const formasPago = {
        'T': 'Tarjeta',
        'E': 'Efectivo',
        'R': 'Transferencia'
    };
    
    //Pago por transferencia bancaria al siguiente número de cuenta ES4200494752902216156784

    const formaPagoDecodificada = formasPago[formaPago?.toUpperCase()] || 'No especificada';
    console.log('Forma de pago decodificada:', formaPagoDecodificada);
    return formaPagoDecodificada;
}

/**
 * Rellena la factura con los datos proporcionados.
 * @param {Object} datos - Objeto con los datos de la factura.
 */
async function rellenarFactura(datos) {
    console.log('Iniciando rellenado de factura con datos:', datos);

    if (!datos || !datos.factura) {
        throw new Error('Datos de factura no proporcionados');
    }

    const factura = datos.factura;

    // Verificar datos obligatorios
    if (!factura.numero || !factura.fecha) {
        throw new Error('Datos básicos de factura incompletos');
    }

    // Actualizar el título y datos de factura
    document.title = `Factura ${factura.numero}`;
    document.getElementById('numero').textContent = factura.numero;
    document.getElementById('fecha').textContent = formatearFechaSoloDia(factura.fecha);
    if (factura.fvencimiento) {
        document.getElementById('fecha-vencimiento').textContent = formatearFechaSoloDia(factura.fvencimiento);
    }

    // Datos del emisor (hardcodeados por ahora)
    document.getElementById('emisor-nombre').textContent = 'SAMUEL RODRIGUEZ MIQUEL';
    document.getElementById('emisor-direccion').textContent = 'LEGALITAT, 70';
    document.getElementById('emisor-cp-ciudad').textContent = 'BARCELONA (08024), BARCELONA, España';
    document.getElementById('emisor-nif').textContent = '44007535W';
    document.getElementById('emisor-email').textContent = 'info@aleph70.com';

    // Datos del cliente
    if (factura.contacto) {
        document.getElementById('razonsocial').textContent = factura.contacto.razonsocial || '';
        document.getElementById('direccion').textContent = factura.contacto.direccion || '';
        
        const datosUbicacion = [];
        if (factura.contacto.cp) datosUbicacion.push(factura.contacto.cp);
        if (factura.contacto.localidad) datosUbicacion.push(factura.contacto.localidad);
        if (factura.contacto.provincia) datosUbicacion.push(factura.contacto.provincia);
        
        document.getElementById('cp-localidad').textContent = datosUbicacion.join(', ');
        document.getElementById('nif').textContent = factura.contacto.identificador || '';
    }

    // Forma de pago
    document.getElementById('forma-pago').textContent = decodificarFormaPago(factura.formaPago || '');

    if (factura.formaPago === 'R') {
        // Pago por transferencia bancaria al siguiente número de cuenta ES4200494752902216156784
        document.getElementById('forma-pago').textContent = 'Pago por transferencia bancaria al siguiente número de cuenta ES4200494752902216156784';
    }

    // Rellenar detalles
    const tbody = document.getElementById('detalles-factura');
    if (!tbody) {
        console.error('No se encontró el elemento tbody#detalles-factura');
        return;
    }
    tbody.innerHTML = '';

    console.log('Detalles de la factura:', factura.detalles); // Debug

    if (Array.isArray(factura.detalles)) {
        factura.detalles.forEach(detalle => {
            console.log('Procesando detalle:', detalle); // Debug
            const fila = document.createElement('tr');
            const cantidadRaw = detalle.cantidad ?? '';
            const precioRaw = detalle.precio ?? '';
            const subtotalRaw = detalle.total ? `${detalle.total}€` : '';
            fila.innerHTML = `
                <td>
                    <div class="detalle-concepto">
                        <span>${detalle.concepto || ''}</span>
                        ${detalle.descripcion ? `<span class="detalle-descripcion">${detalle.descripcion}</span>` : ''}
                    </div>
                </td>
                <td class="cantidad">${cantidadRaw}</td>
                <td class="precio">${precioRaw}</td>
                <td class="total">${subtotalRaw}</td>
            `;
            tbody.appendChild(fila);
        });
    } else {
        console.error('factura.detalles no es un array:', factura.detalles);
    }

    // Totales documento: mostrar exactamente lo provisto por el backend
    document.getElementById('base').textContent = factura.base ? `${factura.base}€` : '';
    document.getElementById('iva').textContent = factura.iva ? `${factura.iva}€` : '';
    document.getElementById('total').textContent = factura.total ? `${factura.total}€` : '';
    
    // Sección FACTURA RECTIFICATIVA
    const rectInfoDiv = document.getElementById('rectificativa-info');
    if (rectInfoDiv) {
        const esRectificativa = (factura.tipo === 'R') || (factura.estado === 'RE') || (String(factura.numero).endsWith('-R'));
        if (esRectificativa) {
            let numOrig = '';
            let fechaOrig = '';
            const motivo = factura.motivo_rectificacion || 'Anulación de factura';
            if (factura.id_factura_rectificada) {
                try {
                    // Obtener directamente del backend número y fecha
                    const respOrig = await fetch(`http://${IP_SERVER}:${PORT}/api/facturas/consulta/${factura.id_factura_rectificada}`);
                    if (respOrig.ok) {
                        const datosOrig = await respOrig.json();
                        if (datosOrig && datosOrig.factura) {
                            numOrig = datosOrig.factura.numero || '';
                            fechaOrig = datosOrig.factura.fecha || '';
                        }
                    }
                } catch (e) {
                    console.error('Error obteniendo factura original:', e);
                }
            }
            rectInfoDiv.innerHTML = `
            <div style="border:2px solid #c00; padding:10px; margin:10px 0;">
                <h2 style="color:#c00; text-align:center;">FACTURA RECTIFICATIVA</h2>
                <p><strong>Factura rectificada:</strong> Nº ${numOrig} de fecha ${fechaOrig}</p>
                <p><strong>Motivo rectificación:</strong> ${motivo}</p>
                <p><strong>Importe rectificado:</strong> ${factura.total ? `${factura.total}€` : ''}</p>
            </div>`;
        } else {
            rectInfoDiv.style.display = 'none';
        }
    }

    // Información VERI*FACTU
    console.log('Información VERI*FACTU completa:', factura);
    const verifactuDisponible = !!(factura.qr_verifactu && factura.qr_verifactu.length > 50);
    if (!verifactuDisponible) {
        console.warn('VERI*FACTU no disponible para esta factura. Ocultando secciones relacionadas.');
        // 1. Ocultar etiqueta VERI*FACTU del título
        const labelVerifactu = document.querySelector('.header h1 span');
        if (labelVerifactu) labelVerifactu.style.display = 'none';
        // 2. Ocultar bloque de información y QR VERI*FACTU
        try {
            const qrContainerOuter = document.getElementById('qr-verifactu')?.parentElement?.parentElement;
            if (qrContainerOuter) qrContainerOuter.style.display = 'none';
            const infoBlock = document.getElementById('hash-factura')?.parentElement?.parentElement;
            if (infoBlock) infoBlock.style.display = 'none';
        } catch (err) {
            console.error('Error ocultando secciones VERI*FACTU:', err);
        }
    }
    console.log('Datos QR:', {
        hash: factura.hash_verifactu,
        qrExists: factura.qr_verifactu !== null && factura.qr_verifactu !== undefined,
        qrLength: factura.qr_verifactu ? factura.qr_verifactu.length : 0,
        qrFirstChars: factura.qr_verifactu ? factura.qr_verifactu.substring(0, 50) + '...' : 'No disponible'
    });
    
    // Insertar hash en el elemento correspondiente
    const hashElement = document.getElementById('hash-factura');
    if (hashElement) {
        const hashValue = factura.hash_verifactu || 'No disponible';
        hashElement.textContent = `Hash: ${hashValue}`;
        console.log('Hash insertado:', hashValue);
    } else {
        console.error('No se encontró el elemento #hash-factura');
    }
    
    // Buscar e identificar el elemento QR
    const qrElement = document.getElementById('qr-verifactu');
    console.log('Elemento QR encontrado:', qrElement ? 'Sí' : 'No');
    if (qrElement) {
        console.log('Propiedades del elemento QR:', {
            id: qrElement.id,
            className: qrElement.className,
            innerHTML: qrElement.innerHTML
        });
    }
    
    // Insertar código QR si VERI*FACTU está disponible
    if (qrElement && verifactuDisponible) {
        // Limpiar el contenedor QR primero
        qrElement.innerHTML = '';
        
        try {
            // Plan A: Usar la cadena base64 directamente si existe
            if (factura.qr_verifactu) {
                console.log('Intentando mostrar QR desde datos base64, longitud:', factura.qr_verifactu.length);
                
                // Crear un elemento de imagen
                const imgElement = document.createElement('img');
                // Construir la URL de la imagen
                imgElement.src = `data:image/png;base64,${factura.qr_verifactu}`;
                imgElement.alt = 'Código QR VERI*FACTU';
                imgElement.style.width = '150px';
                imgElement.style.height = '150px';
                imgElement.style.display = 'block'; // Garantizar que la imagen sea visible
                
                // Añadir la imagen al contenedor
                qrElement.appendChild(imgElement);
                console.log('Imagen QR añadida al DOM desde base64');
                
                // Manejar errores en la carga de la imagen
                imgElement.onerror = function(e) {
                    console.error('Error al cargar la imagen QR desde base64, intentando plan B', e);
                    cargarImagenTemporal();
                };
                
                // También intentar con imagen temporal como respaldo en caso de problemas no detectables
                setTimeout(() => {
                    // Si después de 500ms el QR no es visible (problema común con imágenes base64 grandes)
                    if (imgElement.naturalWidth === 0) {
                        console.warn('QR no cargado correctamente después de 500ms, intentando plan B');
                        cargarImagenTemporal();
                    }
                }, 500);
            } else {
                console.warn('QR no disponible en datos de factura, intentando plan B');
                cargarImagenTemporal();
            }
        } catch (error) {
            console.error('Error al procesar QR:', error);
            cargarImagenTemporal();
        }
        
        // Plan B: Cargar desde archivo temporal
        function cargarImagenTemporal() {
            try {
                console.log('Plan B: Cargando QR desde archivo temporal');
                
                // Limpiar el contenedor por si acaso
                qrElement.innerHTML = '';
                
                // Usar un timestamp para evitar la caché del navegador
                const timestamp = new Date().getTime();
                const imgSrc = `/static/tmp_qr/qr_temp.png?t=${timestamp}`;
                
                const imgElement = document.createElement('img');
                imgElement.src = imgSrc;
                imgElement.alt = 'Código QR VERI*FACTU';
                imgElement.style.width = '150px';
                imgElement.style.height = '150px';
                imgElement.style.display = 'block'; // Garantizar que la imagen sea visible
                
                qrElement.appendChild(imgElement);
                console.log('Imagen QR temporal añadida al DOM');
                
                // En caso de error al cargar la imagen temporal
                imgElement.onerror = function(e) {
                    console.error('Error al cargar la imagen QR temporal:', e);
                    mostrarQRNoDisponible();
                };
            } catch (error) {
                console.error('Error en plan B:', error);
                mostrarQRNoDisponible();
            }
        }
        
        // Último recurso: mostrar mensaje de QR no disponible
        function mostrarQRNoDisponible() {
            qrElement.innerHTML = '<div style="width:150px;height:150px;border:1px solid #ddd;display:flex;justify-content:center;align-items:center;text-align:center;">QR no disponible</div>';
        }
    } else {
        console.error('No se encontró el elemento #qr-verifactu');
    }

    // Pie de página
    //document.getElementById('numero-pie').textContent = `Factura ${factura.numero}`;
    //document.getElementById('total-pie').textContent = formatearImporte(factura.total || 0);
}
