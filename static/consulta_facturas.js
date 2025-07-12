import { IP_SERVER, PORT } from './constantes.js';
import { mostrarNotificacion } from './notificaciones.js';
import { formatearImporte } from './scripts_utils.js';

// Mapeo de estados específico para FACTURAS
const ESTADOS_FACTURA = {
    'P': 'Pendiente',
    'C': 'Cobrada',
    'V': 'Vencida',
    'A': 'Anulada',
    'RE': 'Rectificativa'
};

const getEstadoFormateado = (estado) => ESTADOS_FACTURA[estado] || estado;

const getEstadoClass = (estado) => {
    const clases = {
        'P': 'estado-pendiente',
        'C': 'estado-cobrado',
        'V': 'estado-vencido',
        'A': 'estado-anulada',
        'RE': 'estado-rectificativa'
    };
    return clases[estado] || '';
};

// Función para mostrar el overlay de carga
const showOverlay = () => {
    document.getElementById('overlay').style.display = 'flex';
};

// Función para ocultar el overlay de carga
const hideOverlay = () => {
    document.getElementById('overlay').style.display = 'none';
};

// Función para actualizar los totales
const updateTotals = (facturas) => {
    let totalBase = 0;
    let totalIVA = 0;
    let totalCobrado = 0;
    let totalTotal = 0;

    facturas.forEach(factura => {
        // Solo sumar si la factura está cobrada (estado 'C')
        if (factura.estado === 'C') {
            totalBase += parseFloat(factura.base || 0);
            totalIVA += parseFloat(factura.iva || 0);
            totalCobrado += parseFloat(factura.importe_cobrado || 0);
            totalTotal += parseFloat(factura.total || 0);
        }
    });

    document.getElementById('totalBase').textContent = formatearImporte(totalBase);
    document.getElementById('totalIVA').textContent = formatearImporte(totalIVA);
    document.getElementById('totalCobrado').textContent = formatearImporte(totalCobrado);
    document.getElementById('totalTotal').textContent = formatearImporte(totalTotal);
};

// Función para formatear fechas como DD/MM/AAAA
function formatDate(date) {
    const day = String(date.getDate()).padStart(2, '0');
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const year = date.getFullYear();
    return `${year}-${month}-${day}`; // Formato YYYY-MM-DD para el input type="date"
}

// Función para convertir fecha de YYYY-MM-DD a DD/MM/AAAA para mostrar
function formatDateToDisplay(dateStr) {
    if (!dateStr) return '';
    const [year, month, day] = dateStr.split('-');
    return `${day}/${month}/${year}`;
}

// Función para convertir fecha para la API
function convertirFechaParaAPI(fecha) {
    if (!fecha) return '';
    return fecha; // Ya está en formato YYYY-MM-DD
}

// Las funciones getEstadoFormateado y getEstadoClass ahora se importan desde scripts_utils.js

// Función para buscar facturas
async function buscarFacturas(usarFiltrosGuardados = false) {
    showOverlay();
    
    try {
        let startDate, endDate, status, facturaNumber, contacto, identificador;
        
        // Si se solicita usar filtros guardados, intentamos recuperarlos de sessionStorage
        if (usarFiltrosGuardados) {
            const filtrosGuardados = sessionStorage.getItem('filtrosFacturas');
            if (filtrosGuardados) {
                const filtros = JSON.parse(filtrosGuardados);
                console.log('Usando filtros guardados:', filtros);
                
                // Usamos los filtros guardados
                startDate = filtros.startDate;
                endDate = filtros.endDate;
                status = filtros.status;
                facturaNumber = filtros.facturaNumber;
                contacto = filtros.contacto;
                identificador = filtros.identificador;
            } else {
                // Si no hay filtros guardados, usamos los valores actuales del formulario
                startDate = document.getElementById('startDate').value;
                endDate = document.getElementById('endDate').value;
                status = document.getElementById('statusFilter') ? document.getElementById('statusFilter').value : document.getElementById('status').value;
                facturaNumber = document.getElementById('facturaNumber').value.trim();
                contacto = document.getElementById('contacto').value.trim();
                identificador = document.getElementById('identificador').value.trim();
            }
        } else {
            // Obtener valores actuales del formulario
            startDate = document.getElementById('startDate').value;
            endDate = document.getElementById('endDate').value;
            status = document.getElementById('statusFilter') ? document.getElementById('statusFilter').value : document.getElementById('status').value;
            facturaNumber = document.getElementById('facturaNumber').value.trim();
            contacto = document.getElementById('contacto').value.trim();
            identificador = document.getElementById('identificador').value.trim();
        }
            
        // Guardar los filtros actuales
        guardarFiltros();

        const params = new URLSearchParams();
        
        // Comprobar si hay algún filtro adicional informado
        const hayFiltrosAdicionales = !!(
            status ||
            (facturaNumber && facturaNumber.length >= 1) ||
            (contacto && contacto.length >= 2) ||
            (identificador && identificador.length >= 1)
        );
        
        // Las fechas ya vienen en formato YYYY-MM-DD del input type="date"
        // Solo agregar fechas si no hay otros filtros
        if (!hayFiltrosAdicionales) {
            if (startDate) params.append('fecha_inicio', startDate);
            if (endDate) params.append('fecha_fin', endDate);
        }

        // Añadir los demás filtros si tienen valor
        if (status) {
            console.log(`Aplicando filtro de estado: ${status}`);
            params.append('estado', status);
        }
        
        // Manejar búsqueda por número de factura
        if (facturaNumber && facturaNumber.length >= 1) {
            params.append('numero', facturaNumber);
            params.append('limit', '10');
        }
        
        // Manejar búsqueda por razón social
        if (contacto && contacto.length >= 2) {
            params.append('contacto', contacto);
            params.append('limit', '10');
        }

        // Manejar búsqueda por identificador
        if (identificador && identificador.length >= 1) {
            params.append('identificador', identificador);
            params.append('limit', '10');
        }

        const url = `http://${IP_SERVER}:${PORT}/api/facturas/consulta?${params}`;
        console.log('URL de búsqueda:', url);

        const response = await fetch(url);
        if (!response.ok) {
            throw new Error('Error al buscar facturas');
        }
        const data = await response.json();
        
        console.log('Resultados obtenidos:', data);

        if (!Array.isArray(data)) {
            console.error('La respuesta no es un array:', data);
            throw new Error('Formato de respuesta inválido');
        }

        const tbody = document.getElementById('gridBody');
        tbody.innerHTML = '';

        if (data.length === 0) {
            tbody.innerHTML = '<tr><td colspan="10" class="text-center">No se encontraron resultados</td></tr>';
            return;
        }

        let totalBase = 0;
        let totalIVA = 0;
        let totalCobrado = 0;
        let totalTotal = 0;

        data.forEach(factura => {
            const row = document.createElement('tr');
            
            // Debug: verificar explícitamente el valor de enviado para cada factura
            console.log(`Factura ID: ${factura.id}, Número: ${factura.numero}, Enviado: ${factura.enviado}, Tipo: ${typeof factura.enviado}`);
            
            // Asegurar que los valores numéricos sean válidos
            const base = parseFloat(factura.base) || 0;
            const iva = parseFloat(factura.iva) || 0;
            const importeCobrado = parseFloat(factura.importe_cobrado) || 0;
            const total = parseFloat(factura.total) || 0;

            // Añadir clases de fila según estado para estilos y deshabilitar interacción
            if (factura.estado === 'A') {
                row.classList.add('fila-anulada', 'fila-bloqueada');
            } else if (factura.estado === 'RE') {
                row.classList.add('fila-rectificativa', 'fila-bloqueada');
            }

            row.innerHTML = `
                <td>${formatDateToDisplay(factura.fecha)}</td>
                <td>${factura.numero}</td>
                <td>${factura.razonsocial || ''}</td>
                <td class="text-right">${formatearImporte(base)}</td>
                <td class="text-right">${formatearImporte(iva)}</td>
                <td class="text-right">${formatearImporte(importeCobrado)}</td>
                <td class="text-right">${formatearImporte(total)}</td>
                <td class="text-center ${getEstadoClass(factura.estado)}">${getEstadoFormateado(factura.estado)}</td>
                <td class="text-center">
                    ${(['P','A'].includes(factura.estado)) ? '' : `<i class=\"fas fa-print print-icon\" style=\"cursor: pointer;\" data-id=\"${factura.id}\"></i>`}
                </td>
                <td class="text-center">
                    ${(['P','A'].includes(factura.estado)) ? '' : (
                        factura.estado === 'V' ? 
                            `<i class="fas fa-envelope email-icon-urgent" 
                                style="cursor: pointer; color: #dc3545; font-weight: bold;" 
                                data-id="${factura.id}" 
                                title="Enviar correo a ${factura.mail && factura.mail.trim() !== '' ? factura.mail : 'sin email'} (Factura vencida)"
                            ></i>` :
                            (Number(factura.enviado) === 1 || factura.enviado === '1' ? 
                                `<i class="fas fa-envelope-open-text email-sent-icon" style="color: #28a745; cursor: default;" 
                                    data-id="${factura.id}" 
                                    title="Factura ya enviada a ${factura.mail && factura.mail.trim() !== '' ? factura.mail : 'sin email'}"
                                ></i>` : 
                                `<i class="fas fa-envelope email-icon" 
                                    style="cursor: pointer;" 
                                    data-id="${factura.id}" 
                                    title="Enviar correo a ${factura.mail && factura.mail.trim() !== '' ? factura.mail : 'sin email'}"
                                ></i>`
                            )
                        )
                    }
                </td>
            `;
            
            // Añadir evento de clic para editar la factura (excepto en el icono de impresión)
            const cells = row.querySelectorAll('td:not(:last-child)');
            // Permitir edición solo si la factura NO está anulada ni es rectificativa
            if (!['A','RE'].includes(factura.estado)) {
                cells.forEach(cell => {
                    cell.addEventListener('click', () => {
                        window.location.href = `GESTION_FACTURAS.html?idFactura=${factura.id}&idContacto=${factura.idcontacto}`;
                    });
                });
            }
            
            // Añadir evento de clic para imprimir
            const printIcon = row.querySelector('.print-icon');
            if (printIcon) {
            printIcon.addEventListener('click', (e) => {
                e.stopPropagation(); // Evitar que se propague al evento de la fila
                const facturaId = printIcon.getAttribute('data-id');
                const width = 800;
                const height = 600;
                const left = (window.screen.width - width) / 2;
                const top = (window.screen.height - height) / 2;
                window.open(
                    `IMPRIMIR_FACTURA.html?facturaId=${facturaId}`,
                    'ImprimirFactura',
                    `width=${width},height=${height},left=${left},top=${top}`
                );
            });
            }
            
            // Añadir evento de clic para enviar email solo a los que no se han enviado
            const emailIcon = row.querySelector('.email-icon, .email-icon-urgent');
            if (emailIcon) { // Solo añadir evento si existe el icono (y no está pendiente)
                const handleEmailClick = async (e) => {
                e.stopPropagation(); // Evitar que se propague al evento de la fila
                const facturaId = emailIcon.getAttribute('data-id');
                
                try {
                    showOverlay();
                    const response = await fetch(`http://${IP_SERVER}:${PORT}/api/facturas/email/${facturaId}`, {
                        method: 'POST'
                    });
                    
                    const data = await response.json();
                    
                    if (!response.ok) {
                        throw new Error(data.error || 'Error al enviar el correo');
                    }
                    
                    mostrarNotificacion('Factura enviada correctamente por correo', 'success');
                    
                    // Al enviar correctamente, actualizamos manualmente el icono primero para mostrar feedback instantáneo
                    emailIcon.innerHTML = '<i class="fas fa-envelope-open-text" title="Correo enviado"></i>';
                    emailIcon.classList.remove('email-icon');
                    emailIcon.classList.remove('email-icon-urgent');
                    emailIcon.classList.add('email-sent-icon');
                    emailIcon.style.color = '#28a745'; // Color verde para indicar éxito
                    emailIcon.style.cursor = 'default';
                    emailIcon.removeEventListener('click', handleEmailClick);
                    
                    // Forzamos a guardar los filtros actuales antes de refrescar
                    guardarFiltros();
                    
                    console.log('Correo enviado. Se refrescará la consulta de facturas en unos segundos...');
                    
                    // Esperamos un momento y luego refrescamos la tabla completa para asegurar consistencia
                    setTimeout(async () => {
                        try {
                            // Forzar una nueva búsqueda sin usar caché
                            await buscarFacturas(true);
                            const filtrosGuardados = sessionStorage.getItem('filtrosFacturas');
                            if (filtrosGuardados) {
                                console.log('Recargando con filtros guardados:', JSON.parse(filtrosGuardados));
                                
                                // Aplicar los filtros a los elementos visibles
                                const filtros = JSON.parse(filtrosGuardados);
                                if (document.getElementById('startDate')) document.getElementById('startDate').value = filtros.startDate || '';
                                if (document.getElementById('endDate')) document.getElementById('endDate').value = filtros.endDate || '';
                                if (document.getElementById('statusFilter')) {
                                    document.getElementById('statusFilter').value = filtros.status || '';
                                } else if (document.getElementById('status')) {
                                    document.getElementById('status').value = filtros.status || '';
                                }
                                if (document.getElementById('facturaNumber')) document.getElementById('facturaNumber').value = filtros.facturaNumber || '';
                                if (document.getElementById('contacto')) document.getElementById('contacto').value = filtros.contacto || '';
                                if (document.getElementById('identificador')) document.getElementById('identificador').value = filtros.identificador || '';
                                
                                // Pasar true para utilizar los filtros guardados
                                buscarFacturas(true);
                            } else {
                                // Si no hay filtros guardados, realizar búsqueda normal
                                console.log('No hay filtros guardados, se usarán los valores actuales');
                                buscarFacturas();
                            }
                        } catch (error) {
                            console.error('Error al refrescar la consulta:', error);
                            // Si hay un error, intentamos una búsqueda estándar
                            buscarFacturas();
                        }
                    }, 1500); // Aumentamos el tiempo para dar más margen a la actualización de la BD
                } catch (error) {
                    mostrarNotificacion('Error', error.message, 'error');
                } finally {
                    hideOverlay();
                }
            };
            emailIcon.addEventListener('click', handleEmailClick);
            }
            
            tbody.appendChild(row);

            // Actualizar totales
            totalBase += base;
            totalIVA += iva;
            totalCobrado += importeCobrado;
            totalTotal += total;
        });

        // Actualizar los totales en el pie de página
        updateTotals(data);

    } catch (error) {
        console.error('Error:', error);
        mostrarNotificacion('Error al buscar facturas', 'error');
    } finally {
        hideOverlay();
    }
}

// Función para búsqueda interactiva
function busquedaInteractiva(event) {
    const input = event.target;
    const minLength = input.id === 'contacto' ? 2 : 1;
    
    if (input.value.length >= minLength || input.value.length === 0) {
        // Guardar los filtros antes de realizar la búsqueda
        guardarFiltros();
        
        // Realizar la búsqueda
        buscarFacturas();
    }
}

// Función para guardar los filtros en sessionStorage
function guardarFiltros() {
    console.log('Guardando filtros actuales en sessionStorage');
    const filtros = {
        startDate: document.getElementById('startDate').value,
        endDate: document.getElementById('endDate').value,
        status: document.getElementById('statusFilter') ? document.getElementById('statusFilter').value : document.getElementById('status').value,
        facturaNumber: document.getElementById('facturaNumber').value,
        contacto: document.getElementById('contacto').value,
        identificador: document.getElementById('identificador').value
    };
    console.log('Filtros a guardar:', filtros);
    sessionStorage.setItem('filtrosFacturas', JSON.stringify(filtros));
}

// Función para restaurar los filtros desde sessionStorage
function restaurarFiltros() {
    const filtrosGuardados = sessionStorage.getItem('filtrosFacturas');
    
    if (filtrosGuardados) {
        const filtros = JSON.parse(filtrosGuardados);
        
        // Si no hay fechas guardadas, establecer fechas por defecto
        if (!filtros.startDate || !filtros.endDate) {
            const hoy = new Date();
            
            document.getElementById('startDate').value = formatDate(hoy);
            document.getElementById('endDate').value = formatDate(hoy);
        } else {
            document.getElementById('startDate').value = filtros.startDate;
            document.getElementById('endDate').value = filtros.endDate;
        }
        
        document.getElementById('status').value = filtros.status || '';
        document.getElementById('facturaNumber').value = filtros.facturaNumber || '';
        document.getElementById('contacto').value = filtros.contacto || '';
        document.getElementById('identificador').value = filtros.identificador || '';
        
        // Realizar búsqueda con los filtros restaurados
        buscarFacturas();
    } else {
        // Si no hay filtros guardados, establecer fechas por defecto
        const hoy = new Date();
        
        document.getElementById('startDate').value = formatDate(hoy);
        document.getElementById('endDate').value = formatDate(hoy);
        
        // Realizar búsqueda inicial
        buscarFacturas();
    }
}

document.addEventListener("DOMContentLoaded", function () {
    // Restaurar filtros guardados
    restaurarFiltros();
    
    // Event listeners para búsqueda interactiva
    document.getElementById('facturaNumber').addEventListener('input', busquedaInteractiva);
    document.getElementById('contacto').addEventListener('input', busquedaInteractiva);
    document.getElementById('identificador').addEventListener('input', busquedaInteractiva);
    
    // Event listeners para cambios en fechas y estado
    document.getElementById('startDate').addEventListener('change', () => {
        guardarFiltros();
        buscarFacturas();
    });
    
    document.getElementById('endDate').addEventListener('change', () => {
        guardarFiltros();
        buscarFacturas();
    });
    
    document.getElementById('status').addEventListener('change', () => {
        guardarFiltros();
        buscarFacturas();
    });
});