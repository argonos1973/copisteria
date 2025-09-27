import { IP_SERVER, PORT } from './constantes.js';
import { mostrarNotificacion, mostrarConfirmacion } from './notificaciones.js';
import { formatearImporte, formatearFechaSoloDia, getEstadoFormateado, getEstadoClass, parsearImporte } from './scripts_utils.js';

// Función para mostrar el overlay de carga
const showOverlay = () => {
    document.getElementById('overlay').style.display = 'flex';
};

// Función para ocultar el overlay de carga
const hideOverlay = () => {
    document.getElementById('overlay').style.display = 'none';
};

// Función para actualizar los totales desde el backend (totales globales)
const updateTotalsFromBackend = (totalesGlobales) => {
    const setText = (id, valor) => {
        const el = document.getElementById(id);
        if (el) el.textContent = valor ? `${valor} €` : '';
    };

    setText('totalBase', totalesGlobales.total_base);
    setText('totalIVA', totalesGlobales.total_iva);
    setText('totalCobrado', totalesGlobales.total_cobrado);
    setText('totalTotal', totalesGlobales.total_total);
};

// Función para actualizar los totales (fallback - solo página actual)
const updateTotals = (proformas) => {
    let totalBase = 0;
    let totalIVA = 0;
    let totalCobrado = 0;
    let totalTotal = 0;

    proformas.forEach(proforma => {
        totalBase += parsearImporte(proforma.base || 0) || 0;
        totalIVA += parsearImporte(proforma.iva || 0) || 0;
        totalCobrado += parsearImporte(proforma.importe_cobrado || 0) || 0;
        totalTotal += parsearImporte(proforma.total || 0) || 0;
    });

    const formatEuros = (valor) => `${valor.toFixed(2).replace('.', ',')} €`;

    document.getElementById('totalBase').textContent = formatEuros(totalBase);
    document.getElementById('totalIVA').textContent = formatEuros(totalIVA);
    document.getElementById('totalCobrado').textContent = formatEuros(totalCobrado);
    document.getElementById('totalTotal').textContent = formatEuros(totalTotal);
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

// convertirFechaParaAPI centralizado en scripts_utils.js

// Las funciones getEstadoFormateado y getEstadoClass ahora se importan desde scripts_utils.js

// Función para buscar proformas
async function buscarProformas() {
    showOverlay();
    
    try {
        const startDate = document.getElementById('startDate').value;
        const endDate = document.getElementById('endDate').value;
        const status = document.getElementById('status').value;
        const proformaNumber = document.getElementById('proformaNumber').value.trim();
        const contacto = document.getElementById('contacto').value.trim();
        const identificador = document.getElementById('identificador').value.trim();

        console.log('Realizando búsqueda con parámetros:', {
            startDate,
            endDate,
            status,
            proformaNumber,
            contacto,
            identificador
        });

        const params = new URLSearchParams();
        
        // Comprobar si hay algún filtro adicional informado
        const hayFiltrosAdicionales = !!(
            status ||
            (proformaNumber && proformaNumber.length >= 1) ||
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
        if (status) params.append('estado', status);
        
        // Manejar búsqueda por número de proforma
        if (proformaNumber && proformaNumber.length >= 1) {
            params.append('numero', proformaNumber);
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

        const url = `http://${IP_SERVER}:${PORT}/api/proformas/consulta?${params}`;
        console.log('URL de búsqueda:', url);

        const response = await fetch(url);
        if (!response.ok) {
            throw new Error('Error al buscar proformas');
        }
        const data = await response.json();
        
        console.log('Resultados obtenidos:', data);

        // Manejar nueva estructura de respuesta con totales globales
        const proformas = data.items || data;
        const totalesGlobales = data.totales_globales;

        if (!Array.isArray(proformas)) {
            console.error('La respuesta no contiene un array válido:', data);
            throw new Error('Formato de respuesta inválido');
        }

        const tbody = document.getElementById('gridBody');
        tbody.innerHTML = '';

        if (proformas.length === 0) {
            tbody.innerHTML = '<tr><td colspan="9" class="text-center">No se encontraron resultados</td></tr>';
            // Actualizar totales a cero
            updateTotals([]);
            return;
        }

        let totalBase = 0;
        let totalIVA = 0;
        let totalCobrado = 0;
        let totalTotal = 0;

        proformas.forEach(proforma => {
            const row = document.createElement('tr');
            
            // Asegurar que los valores numéricos sean válidos (parseo robusto)
            const base = parsearImporte(proforma.base) || 0;
            const iva = parsearImporte(proforma.iva) || 0;
            const importeCobrado = parsearImporte(proforma.importe_cobrado) || 0;
            const total = parsearImporte(proforma.total) || 0;
            const estadoUp = String(proforma.estado || '').toUpperCase();
            // Si está facturada ('F') o cobrada ('C'), Total debe igualar al importe cobrado mostrado
            const totalDisplay = (estadoUp === 'F' || estadoUp === 'C') ? importeCobrado : total;
            const baseRaw = (proforma.base ?? '').toString();
            const ivaRaw = (proforma.iva ?? '').toString();
            const cobradoRaw = (proforma.importe_cobrado ?? '').toString();
            const totalDisplayRaw = (estadoUp === 'F' || estadoUp === 'C')
                ? (proforma.importe_cobrado ?? '').toString()
                : (proforma.total ?? '').toString();

            // Crear la celda de acciones con el icono de conversión a factura
            const accionesTd = document.createElement('td');
            accionesTd.className = 'text-center';
            
            // Solo mostrar el icono de conversión si la proforma no está facturada
            if (proforma.estado !== 'F') {
                const convertirIcon = document.createElement('i');
                convertirIcon.className = 'fas fa-file-invoice action-icon';
                convertirIcon.title = 'Convertir a Factura';
                convertirIcon.style.cursor = 'pointer';
                convertirIcon.style.marginLeft = '5px';
                convertirIcon.style.color = '#007bff';
                
                // Añadir evento al icono para convertir a factura
                convertirIcon.addEventListener('click', async (event) => {
                    event.stopPropagation(); // Evitar que se active el evento de clic de la fila
                    
                    try {
                        const confirmado = await mostrarConfirmacion(`¿Estás seguro de que deseas convertir la proforma ${proforma.numero} a factura?`);
                        if (confirmado) {
                            showOverlay();
                            const response = await fetch(`http://${IP_SERVER}:${PORT}/api/proformas/${proforma.id}/convertir`, {
                                method: 'POST',
                                headers: {
                                    'Content-Type': 'application/json'
                                }
                            });
                            
                            if (!response.ok) {
                                throw new Error('Error al convertir la proforma a factura');
                            }
                            
                            const result = await response.json();
                            mostrarNotificacion(`Proforma ${proforma.numero} convertida a factura correctamente`, 'success');
                            
                            // Recargar la lista de proformas después de un breve retraso
                            setTimeout(() => {
                                buscarProformas();
                            }, 1000);
                        }
                    } catch (error) {


                        console.error('Error al convertir proforma a factura:', error);
                        mostrarNotificacion('Error al convertir la proforma a factura', 'error');
                    } finally {
                        hideOverlay();
                    }
                });
                
                accionesTd.appendChild(convertirIcon);
            }

            row.innerHTML = `
                <td>${formatDateToDisplay(proforma.fecha)}</td>
                <td>${proforma.numero}</td>
                <td>${proforma.razonsocial || ''}</td>
                <td class="text-right">${baseRaw ? `${baseRaw} €` : ''}</td>
                <td class="text-right">${ivaRaw ? `${ivaRaw} €` : ''}</td>
                <td class="text-right">${cobradoRaw ? `${cobradoRaw} €` : ''}</td>
                <td class="text-right">${totalDisplayRaw ? `${totalDisplayRaw} €` : ''}</td>
                <td class="text-center ${getEstadoClass(proforma.estado)}">${getEstadoFormateado(proforma.estado, 'proforma')}</td>
            `;
            
            // Añadir la celda de acciones a la fila
            row.appendChild(accionesTd);
            
            // Añadir evento de clic para editar la proforma
            row.addEventListener('click', () => {
                const contactoId = proforma.idcontacto ?? proforma.idContacto ?? '';
                const params = new URLSearchParams({ idProforma: proforma.id });
                if (contactoId !== '' && contactoId !== null && contactoId !== undefined) {
                    params.set('idContacto', contactoId);
                }
                window.location.href = `GESTION_PROFORMAS.html?${params.toString()}`;
            });
            
            tbody.appendChild(row);

            // Acumular totales usando los valores ya parseados
            totalBase += base;
            totalIVA += iva;
            totalCobrado += importeCobrado;
            totalTotal += totalDisplay;
        });

        // Usar totales globales del backend si están disponibles
        if (totalesGlobales) {
            updateTotalsFromBackend(totalesGlobales);
        } else {
            // Fallback: usar totales calculados de la página actual
            document.getElementById('totalBase').textContent = formatearImporte(totalBase || 0);
            document.getElementById('totalIVA').textContent = formatearImporte(totalIVA || 0);
            document.getElementById('totalCobrado').textContent = formatearImporte(totalCobrado || 0);
            document.getElementById('totalTotal').textContent = formatearImporte(totalTotal || 0);
        }

    } catch (error) {
        console.error('Error al buscar proformas:', error);
        mostrarNotificacion('Error al buscar proformas', 'error');
    } finally {
        hideOverlay();
    }
}

// Función para búsqueda interactiva
let timeoutId = null;
function busquedaInteractiva(event) {
    const valor = event.target.value.trim();
    const campo = event.target.id;
    console.log(`Búsqueda interactiva en ${campo}:`, valor);
    
    // Limpiar el timeout anterior si existe
    if (timeoutId) {
        clearTimeout(timeoutId);
    }

    // Esperar 300ms después de que el usuario deje de escribir
    timeoutId = setTimeout(() => {
        console.log(`Ejecutando búsqueda para ${campo}:`, valor);
        // Si es campo de contacto, buscar con 2 o más caracteres o si está vacío
        if (campo === 'contacto' && (valor.length >= 2 || valor.length === 0)) {
            buscarProformas();
        }
        // Si es campo de identificador, buscar desde el primer carácter o si está vacío
        else if (campo === 'identificador' && (valor.length >= 1 || valor.length === 0)) {
            buscarProformas();
        }
        // Si es campo de número de proforma, buscar con 1 o más caracteres o si está vacío
        else if (campo === 'proformaNumber' && (valor.length >= 1 || valor.length === 0)) {
            buscarProformas();
        }
    }, 300);
}

// Función para guardar los filtros en sessionStorage
function guardarFiltros() {
    const filtros = {
        startDate: document.getElementById('startDate').value,
        endDate: document.getElementById('endDate').value,
        estado: document.getElementById('status').value,
        numero: document.getElementById('proformaNumber').value,
        contacto: document.getElementById('contacto').value,
        identificador: document.getElementById('identificador').value
    };
    sessionStorage.setItem('filtrosProformas', JSON.stringify(filtros));
}

// Función para restaurar los filtros desde sessionStorage
function restaurarFiltros() {
    const filtrosGuardados = sessionStorage.getItem('filtrosProformas');
    if (filtrosGuardados) {
        const filtros = JSON.parse(filtrosGuardados);
        document.getElementById('startDate').value = filtros.startDate || '';
        document.getElementById('endDate').value = filtros.endDate || '';
        document.getElementById('status').value = filtros.estado || '';
        document.getElementById('proformaNumber').value = filtros.numero || '';
        document.getElementById('contacto').value = filtros.contacto || '';
        document.getElementById('identificador').value = filtros.identificador || '';
    } else {
        // Si no hay filtros guardados, establecer valores por defecto
        const today = new Date();
        
        // Obtener el primer día del mes actual
        const firstDay = new Date(today.getFullYear(), today.getMonth(), 1);
        
        // Obtener el último día del mes actual
        const lastDay = new Date(today.getFullYear(), today.getMonth() + 1, 0);
        
        // Formatear las fechas como YYYY-MM-DD
        document.getElementById('startDate').value = formatDate(firstDay);
        document.getElementById('endDate').value = formatDate(lastDay);
        
        // Establecer estado inicial en 'A' (Abierta)
        document.getElementById('status').value = 'A';
        
        // Guardar estos filtros iniciales
        guardarFiltros();
    }

    // Siempre ejecutar la búsqueda al restaurar los filtros
    buscarProformas();
}

document.addEventListener("DOMContentLoaded", function () {
    // Restaurar filtros guardados
    restaurarFiltros();
    
    // Agregar eventos para guardar filtros cuando cambien
    document.getElementById('startDate').addEventListener('change', () => {
        guardarFiltros();
        buscarProformas();
    });
    document.getElementById('endDate').addEventListener('change', () => {
        guardarFiltros();
        buscarProformas();
    });
    document.getElementById('status').addEventListener('change', () => {
        guardarFiltros();
        buscarProformas();
    });
    document.getElementById('proformaNumber').addEventListener('input', () => {
        guardarFiltros();
        busquedaInteractiva(event);
    });
    document.getElementById('contacto').addEventListener('input', () => {
        guardarFiltros();
        busquedaInteractiva(event);
    });
    document.getElementById('identificador').addEventListener('input', () => {
        guardarFiltros();
        busquedaInteractiva(event);
    });
});