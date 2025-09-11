import { formatearImporte, fetchConManejadorErrores } from './scripts_utils.js';
import { mostrarNotificacion } from './notificaciones.js';

// Función para obtener las estadísticas del año actual y anterior
async function obtenerEstadisticas() {
    try {
        // Obtener estadísticas por documento
        const datosDocumentos = await fetchConManejadorErrores('/api/ventas/media_por_documento');
        // Obtener estadísticas mensuales
        const datosMensuales = await fetchConManejadorErrores('/api/ventas/media_por_mes');
        
        actualizarDashboard(datosDocumentos);
    } catch (error) {
        console.error('Error:', error);
        mostrarNotificacion('Error al cargar las estadísticas', 'error');
    }
}

// Función para actualizar el dashboard con los datos
function actualizarDashboard(data) {
    // Tickets
    actualizarTarjeta('tickets-actuales', data.tickets.actual.cantidad);
    actualizarTarjeta('tickets-anteriores', data.tickets.anterior.cantidad);
    actualizarVariacion('tickets-variacion', data.tickets.actual.cantidad, data.tickets.anterior.cantidad);
    actualizarTotal('tickets-total-actual', data.tickets.actual.total);
    actualizarTotal('tickets-total-anterior', data.tickets.anterior.total);

    // Facturas
    actualizarTarjeta('facturas-actuales', data.facturas.actual.cantidad);
    actualizarTarjeta('facturas-anteriores', data.facturas.anterior.cantidad);
    actualizarVariacion('facturas-variacion', data.facturas.actual.cantidad, data.facturas.anterior.cantidad);
    actualizarTotal('facturas-total-actual', data.facturas.actual.total);
    actualizarTotal('facturas-total-anterior', data.facturas.anterior.total);

    // Actualizar totales globales
    const totalActual = data.global.actual.total;
    const totalAnterior = data.global.anterior.total;
    actualizarTotal('total-actual', totalActual);
    actualizarTotal('total-anterior', totalAnterior);
    actualizarVariacion('total-variacion', totalActual, totalAnterior);
}

// Función para actualizar una tarjeta individual
function actualizarTarjeta(id, valor) {
    const elemento = document.getElementById(id);
    if (elemento) {
        elemento.textContent = valor;
    }
}

// Función para actualizar el total monetario
function actualizarTotal(id, valor) {
    const elemento = document.getElementById(id);
    if (elemento) {
        elemento.textContent = formatearImporte(valor);
    }
}

// Función para actualizar el indicador de variación
function actualizarVariacion(id, actual, anterior) {
    const elemento = document.getElementById(id);
    if (elemento) {
        const variacion = anterior === 0 ? 100 : ((actual - anterior) / anterior) * 100;
        const esPositivo = variacion >= 0;
        
        elemento.textContent = `${variacion.toFixed(1)}%`;
        elemento.className = `variacion ${esPositivo ? 'positiva' : 'negativa'}`;
        elemento.innerHTML = `${esPositivo ? '▲' : '▼'} ${Math.abs(variacion).toFixed(1)}%`;
    }
}

// Función para mostrar errores
function mostrarError(mensaje) {
    const contenedor = document.getElementById('dashboard-error');
    if (contenedor) {
        contenedor.textContent = mensaje;
        contenedor.style.display = 'block';
        setTimeout(() => {
            contenedor.style.display = 'none';
        }, 5000);
    }
}

// Inicializar el dashboard cuando se carga la página
document.addEventListener('DOMContentLoaded', () => {
    obtenerEstadisticas();
    
    // Actualizar cada 5 minutos
    setInterval(obtenerEstadisticas, 5 * 60 * 1000);
});
