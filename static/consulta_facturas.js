import { IP_SERVER, PORT, API_URL } from './constantes.js?v=1762757322';
import { mostrarNotificacion } from './notificaciones.js';
import { formatearImporte, formatearFechaSoloDia, mostrarCargando, ocultarCargando, debounce, getEstadoFormateado as getEstadoFormateadoFactura, getEstadoClass as getEstadoClassFactura, parsearImporte } from './scripts_utils.js';

// Estados y clases se importan desde scripts_utils.js

// Función para mostrar el overlay de carga
const showOverlay = () => {
    mostrarCargando();
};

// Función para ocultar el overlay de carga
const hideOverlay = () => {
    ocultarCargando();
};

// Función para actualizar los totales desde el backend (totales globales)
const updateTotalsFromBackend = (totalesGlobales) => {
    console.log('[FACTURAS] Actualizando totales desde backend:', totalesGlobales);
    const baseEl = document.getElementById('totalBase');
    const ivaEl = document.getElementById('totalIVA');
    const cobradoEl = document.getElementById('totalCobrado');
    const totalEl = document.getElementById('totalTotal');
    
    if (baseEl) baseEl.textContent = totalesGlobales.total_base ? `${totalesGlobales.total_base} €` : '';
    if (ivaEl) ivaEl.textContent = totalesGlobales.total_iva ? `${totalesGlobales.total_iva} €` : '';
    if (cobradoEl) cobradoEl.textContent = totalesGlobales.total_cobrado ? `${totalesGlobales.total_cobrado} €` : '';
    if (totalEl) totalEl.textContent = totalesGlobales.total_total ? `${totalesGlobales.total_total} €` : '';
    
    console.log('[FACTURAS] Totales actualizados en DOM');
};

// Función para actualizar los totales (fallback - solo página actual)
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
    return formatearFechaSoloDia(dateStr);
}

// Función para convertir fecha para la API
// convertirFechaParaAPI centralizado en scripts_utils.js

// Las funciones getEstadoFormateado y getEstadoClass ahora se importan desde scripts_utils.js

// Estado de paginación
let pagination = {
    page: 1,
    pageSize: 20,
    totalPages: 1
};

function loadPaginationState() {
    try {
        const saved = sessionStorage.getItem('paginationFacturas');
        if (saved) {
            const p = JSON.parse(saved);
            pagination.page = Math.max(parseInt(p.page || 1), 1);
            pagination.pageSize = Math.min(Math.max(parseInt(p.pageSize || 20), 1), 100);
            pagination.totalPages = parseInt(p.totalPages || 1) || 1;
        }
    } catch {}
}

function savePaginationState() {
    sessionStorage.setItem('paginationFacturas', JSON.stringify(pagination));
}

function updatePaginationUI() {
    const pageInfo = document.getElementById('pageInfoFacturas');
    const prevBtn = document.getElementById('prevPageFacturas');
    const nextBtn = document.getElementById('nextPageFacturas');
    const pageSizeSel = document.getElementById('pageSizeSelectFacturas');
    if (pageInfo) pageInfo.textContent = `Página ${pagination.page} de ${pagination.totalPages}`;
    if (prevBtn) prevBtn.disabled = pagination.page <= 1;
    if (nextBtn) nextBtn.disabled = pagination.page >= pagination.totalPages;
    if (pageSizeSel) pageSizeSel.value = String(pagination.pageSize);
}

function handlePageSizeChange() {
    const sel = document.getElementById('pageSizeSelectFacturas');
    const newSize = parseInt(sel.value || '20');
    pagination.pageSize = Math.min(Math.max(newSize, 1), 100);
    pagination.page = 1; // reset al cambiar tamaño
    savePaginationState();
    buscarFacturas(true);
}

function gotoPrevPage() {
    if (pagination.page > 1) {
        pagination.page -= 1;
        savePaginationState();
        buscarFacturas(true);
    }
}

function gotoNextPage() {
    if (pagination.page < pagination.totalPages) {
        pagination.page += 1;
        savePaginationState();
        buscarFacturas(true);
    }
}

// Función para buscar facturas
async function buscarFacturas(usarFiltrosGuardados = false) {
    showOverlay();
    
    try {
        let startDate, endDate, status, facturaNumber, contacto, identificador, conceptFilter;
        
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
                identificador = '';
                conceptFilter = filtros.conceptFilter;
            } else {
                // Si no hay filtros guardados, usamos los valores actuales del formulario
                startDate = document.getElementById('startDate').value;
                endDate = document.getElementById('endDate').value;
                status = document.getElementById('statusFilter') ? document.getElementById('statusFilter').value : document.getElementById('status').value;
                facturaNumber = document.getElementById('facturaNumber').value.trim();
                contacto = document.getElementById('contacto').value.trim();
                identificador = '';
            conceptFilter = document.getElementById('conceptFilter').value.trim();
            }
        } else {
            // Obtener valores actuales del formulario
            startDate = document.getElementById('startDate').value;
            endDate = document.getElementById('endDate').value;
            status = document.getElementById('statusFilter') ? document.getElementById('statusFilter').value : document.getElementById('status').value;
            facturaNumber = document.getElementById('facturaNumber').value.trim();
            contacto = document.getElementById('contacto').value.trim();
            identificador = '';
            conceptFilter = document.getElementById('conceptFilter').value.trim();
        }
            
        // Guardar los filtros actuales
        guardarFiltros();

        const params = new URLSearchParams();
        
        // Comprobar si hay algún filtro adicional informado (excluyendo "todos")
        const hayFiltrosAdicionales = !!(
            (status && status !== 'todos') ||
            (facturaNumber && facturaNumber.length >= 1) ||
            (contacto && contacto.length >= 2) ||
            
            (conceptFilter && conceptFilter.length >= 3)
        );
        
        // Las fechas ya vienen en formato YYYY-MM-DD del input type="date"
        // Agregar fechas siempre que estén informadas
        if (startDate) params.append('fecha_inicio', startDate);
        if (endDate) params.append('fecha_fin', endDate);

        // Añadir los demás filtros si tienen valor (excluyendo "todos")
        if (status && status !== 'todos') {
            console.log(`Aplicando filtro de estado: ${status}`);
            params.append('estado', status);
        }
        
        // Manejar búsqueda por número de factura
        if (facturaNumber && facturaNumber.length >= 1) {
            params.append('numero', facturaNumber);
        }
        
        // Manejar búsqueda por razón social
        if (contacto && contacto.length >= 2) {
            params.append('contacto', contacto);
        }

        // Manejar búsqueda por concepto
        if (conceptFilter && conceptFilter.length >= 3) {
            params.append('concepto', conceptFilter);
        }

        // Paginación y orden
        params.append('page', String(pagination.page));
        params.append('page_size', String(pagination.pageSize));
        params.append('sort', 'fecha');
        params.append('order', 'DESC');

        const url = `/api/facturas/paginado?${params.toString()}`;
        console.log('URL de búsqueda:', url);

        const response = await fetch(url, {
            credentials: 'include'  // Incluir cookies en la petición
        });
        if (!response.ok) {
            throw new Error('Error al buscar facturas');
        }
        const data = await response.json();
        
        console.log('Resultados obtenidos:', data);

        // Estructura paginada
        const items = Array.isArray(data.items) ? data.items : [];
        pagination.totalPages = parseInt(data.total_pages || 1) || 1;
        pagination.page = parseInt(data.page || pagination.page) || 1;
        savePaginationState();
        updatePaginationUI();

        const tbody = document.getElementById('gridBody');
        tbody.innerHTML = '';

        if (items.length === 0) {
            tbody.innerHTML = '<tr><td colspan="11" class="text-center">No se encontraron resultados</td></tr>';
            return;
        }

        let totalBase = 0;
        let totalIVA = 0;
        let totalCobrado = 0;
        let totalTotal = 0;

        items.forEach(factura => {
            const row = document.createElement('tr');
            
            // Debug: verificar explícitamente el valor de enviado para cada factura
            console.log(`Factura ID: ${factura.id}, Número: ${factura.numero}, Enviado: ${factura.enviado}, Tipo: ${typeof factura.enviado}`);
            
            // Tomar SIEMPRE los valores tal cual llegan del backend para la UI
            const baseRaw = (factura.base ?? '').toString();
            const ivaRaw = (factura.iva ?? '').toString();
            const cobradoRaw = (factura.importe_cobrado ?? '').toString();
            const totalRaw = (factura.total ?? '').toString();

            // Para sumatorios, parsear desde los valores del backend (admite coma o punto)
            const baseNum = parsearImporte(factura.base);
            const ivaNum = parsearImporte(factura.iva);
            const cobradoNum = parsearImporte(factura.importe_cobrado);
            const totalNum = parsearImporte(factura.total);

            // Añadir clases de fila según estado para estilos y deshabilitar interacción
            if (factura.estado === 'A') {
                row.classList.add('fila-anulada', 'fila-bloqueada');
            } else if (factura.estado === 'RE') {
                row.classList.add('fila-rectificativa', 'fila-bloqueada');
            }

            // Calcular días hasta vencimiento solo para PENDIENTES y VENCIDAS
            let tooltipText = '';
            let vencimientoDisplay = '';
            let vencimientoStyle = '';
            
            if (factura.fvencimiento) {
                vencimientoDisplay = formatDateToDisplay(factura.fvencimiento);
                
                // Solo mostrar tooltip para estados P (Pendiente) y V (Vencida)
                if (factura.estado === 'P' || factura.estado === 'V') {
                    const hoy = new Date();
                    hoy.setHours(0, 0, 0, 0);
                    const fechaVenc = new Date(factura.fvencimiento);
                    fechaVenc.setHours(0, 0, 0, 0);
                    const diffTime = hoy - fechaVenc;  // Invertido: hoy - vencimiento para contar días vencidos
                    const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24));  // Math.floor para días exactos
                    
                    
                    if (diffDays > 0) {
                        // Factura vencida (vencimiento en el pasado)
                        tooltipText = `Vencida hace ${diffDays} día${diffDays !== 1 ? 's' : ''}`;
                    } else if (diffDays === 0) {
                        tooltipText = 'Vence hoy';
                    } else {
                        // Factura por vencer (vencimiento en el futuro)
                        tooltipText = `Vence en ${diffDays} día${diffDays !== 1 ? 's' : ''}`;
                    }
                    vencimientoStyle = 'cursor: help;';
                }
            }

            row.innerHTML = `
                <td>${formatDateToDisplay(factura.fecha)}</td>
                <td title="${tooltipText}" style="${vencimientoStyle}">${vencimientoDisplay}</td>
                <td>${factura.fechaCobro ? formatDateToDisplay(factura.fechaCobro) : '-'}</td>
                <td>${factura.numero}</td>
                <td>${factura.razonsocial || ''}</td>
                <td class="text-right">${baseRaw} €</td>
                <td class="text-right">${ivaRaw} €</td>
                <td class="text-right">${cobradoRaw} €</td>
                <td class="text-right">${totalRaw} €</td>
                <td class="text-center ${getEstadoClassFactura(factura.estado)}">${getEstadoFormateadoFactura(factura.estado)}</td>
                <td class="text-center">
                    ${(['A'].includes(factura.estado)) ? '' : `<i class=\"fas fa-print print-icon\" style=\"cursor: pointer;\" data-id=\"${factura.id}\"></i>`}
                </td>
                <td class="text-center">
                    ${(['A'].includes(factura.estado)) ? '' : (
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
                <td class="text-center">
                    ${(!['A','RE'].includes(factura.estado) && (Number(factura.carta_enviada) === 1 || factura.carta_enviada === '1')) ? 
                        `<i class="fas fa-file-pdf carta-icon" 
                            style="cursor: pointer; color: #dc3545;" 
                            data-numero="${factura.numero}" 
                            title="Descargar carta de reclamación"
                        ></i>` : ''
                    }
                </td>
            `;
            
            // Añadir evento de clic para editar la factura (excepto en el icono de impresión)
            const cells = row.querySelectorAll('td:not(:last-child)');
            // Permitir edición solo si la factura NO está anulada ni es rectificativa
            if (!['A','RE'].includes(factura.estado)) {
                cells.forEach(cell => {
                    cell.addEventListener('click', () => {
                        // Usar navegarSeguro si existe (verifica cambios sin guardar)
                        const url = `GESTION_FACTURAS.html?idFactura=${factura.id}&idContacto=${factura.idcontacto}`;
                        if (window.navegarSeguro) {
                            window.navegarSeguro(url);
                        } else {
                            window.location.href = url;
                        }
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
                    const response = await fetch(`${API_URL}/api/facturas/email/${facturaId}`, {
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
                    
                    // Esperamos un momento y luego refrescamos la tabla
                    setTimeout(() => {
                        buscarFacturas(true);
                    }, 1500);
                    
                } catch (error) {
                    mostrarNotificacion('Error', error.message, 'error');
                } finally {
                    hideOverlay();
                }
            };
            emailIcon.addEventListener('click', handleEmailClick);
            }
            
            // Añadir evento de clic para descargar carta de reclamación
            const cartaIcon = row.querySelector('.carta-icon');
            if (cartaIcon) {
                cartaIcon.addEventListener('click', (e) => {
                    e.stopPropagation(); // Evitar que se propague al evento de la fila
                    const numeroFactura = cartaIcon.getAttribute('data-numero');
                    
                    // Abrir la carta en una nueva ventana/pestaña
                    const url = `${API_URL}/api/carta-reclamacion/${numeroFactura}`;
                    window.open(url, '_blank');
                });
            }
            
            tbody.appendChild(row);

            // Actualizar totales usando únicamente los valores del backend
            totalBase += isNaN(baseNum) ? 0 : baseNum;
            totalIVA += isNaN(ivaNum) ? 0 : ivaNum;
            totalCobrado += isNaN(cobradoNum) ? 0 : cobradoNum;
            totalTotal += isNaN(totalNum) ? 0 : totalNum;
        });

        // Actualizar los totales en el pie de página (totales globales del filtro)
        console.log('[FACTURAS] Verificando totales_globales:', data.totales_globales);
        if (data.totales_globales) {
            console.log('[FACTURAS] Llamando a updateTotalsFromBackend');
            updateTotalsFromBackend(data.totales_globales);
        } else {
            console.log('[FACTURAS] No hay totales_globales, usando fallback');
            // Fallback: calcular de la página actual si no hay totales globales
            updateTotals(items);
        }

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
    let minLength;
    if (input.id === 'contacto') {
        minLength = 2;
    } else if (input.id === 'conceptFilter') {
        minLength = 3;
    } else {
        minLength = 1;
    }
    
    if (input.value.length >= minLength || input.value.length === 0) {
        // Guardar los filtros antes de realizar la búsqueda
        guardarFiltros();
        
        // Realizar la búsqueda
        pagination.page = 1; // reiniciar a primera página en cambios de filtros
        savePaginationState();
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
        
        conceptFilter: document.getElementById('conceptFilter').value
    };
    console.log('Filtros a guardar:', filtros);
    sessionStorage.setItem('filtrosFacturas', JSON.stringify(filtros));
}

// Función para restaurar los filtros desde sessionStorage
function restaurarFiltros() {
    const filtrosGuardados = sessionStorage.getItem('filtrosFacturas');
    
    if (filtrosGuardados) {
        const filtros = JSON.parse(filtrosGuardados);
        
        // Establecer fechas: usar las guardadas o por defecto (primer día del mes y hoy)
        if (filtros.startDate && filtros.endDate) {
            document.getElementById('startDate').value = filtros.startDate;
            document.getElementById('endDate').value = filtros.endDate;
        } else {
            // Si no hay fechas guardadas, establecer fechas por defecto
            const hoy = new Date();
            const primerDiaMes = new Date(hoy.getFullYear(), hoy.getMonth(), 1);
            
            document.getElementById('startDate').value = formatDate(primerDiaMes);
            document.getElementById('endDate').value = formatDate(hoy);
        }
        
        document.getElementById('status').value = filtros.status || 'todos';
        document.getElementById('facturaNumber').value = filtros.facturaNumber || '';
        document.getElementById('contacto').value = filtros.contacto || '';
        if (document.getElementById('conceptFilter')) {
            document.getElementById('conceptFilter').value = filtros.conceptFilter || '';
        }
        
        
        // Cargar paginación
        loadPaginationState();
        updatePaginationUI();
        // Realizar búsqueda con los filtros restaurados
        buscarFacturas(true);
    } else {
        // Si no hay filtros guardados, establecer valores por defecto
        document.getElementById('status').value = 'todos';
        
        // Establecer fechas por defecto: primer día del mes actual y fecha actual
        const hoy = new Date();
        const primerDiaMes = new Date(hoy.getFullYear(), hoy.getMonth(), 1);
        
        document.getElementById('startDate').value = formatDate(primerDiaMes);
        document.getElementById('endDate').value = formatDate(hoy);
        
        // Cargar paginación por defecto
        loadPaginationState();
        updatePaginationUI();
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
    
    // Debounce para evitar llamadas excesivas mientras se escribe el concepto
    document.getElementById('conceptFilter').addEventListener('input', debounce(busquedaInteractiva, 400));
    
    // Event listeners para cambios en fechas y estado
    document.getElementById('startDate').addEventListener('change', () => {
        guardarFiltros();
        pagination.page = 1;
        savePaginationState();
        buscarFacturas();
    });
    
    document.getElementById('endDate').addEventListener('change', () => {
        guardarFiltros();
        pagination.page = 1;
        savePaginationState();
        buscarFacturas();
    });
    
    document.getElementById('status').addEventListener('change', () => {
        guardarFiltros();
        pagination.page = 1;
        savePaginationState();
        buscarFacturas();
    });

    // Paginación: listeners
    const pageSizeSel = document.getElementById('pageSizeSelectFacturas');
    if (pageSizeSel) pageSizeSel.addEventListener('change', handlePageSizeChange);
    const prevBtn = document.getElementById('prevPageFacturas');
    if (prevBtn) prevBtn.addEventListener('click', (e) => { e.preventDefault(); gotoPrevPage(); });
    const nextBtn = document.getElementById('nextPageFacturas');
    if (nextBtn) nextBtn.addEventListener('click', (e) => { e.preventDefault(); gotoNextPage(); });
});