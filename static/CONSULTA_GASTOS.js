import { IP_SERVER, PORT } from '../static/constantes.js';
import { formatearImporte } from '../static/scripts_utils.js';
import { mostrarNotificacion } from '../static/notificaciones.js';

const fechaInicioInput = document.getElementById('fecha-inicio');
const fechaFinInput = document.getElementById('fecha-fin');
const conceptoInput = document.getElementById('concepto');
const buscarBtn = document.getElementById('buscar-btn');
const tipoMovimientoInput = document.getElementById('tipo-movimiento');
const tablaBody = document.querySelector('#tabla-gastos tbody');
const noResultados = document.getElementById('no-resultados');
const notificacion = document.getElementById('notificacion');

// Inicializar fechas con el primer y último día del mes actual
document.addEventListener('DOMContentLoaded', () => {
    inicializarFechasMesActual();
    buscarGastos();
});

function inicializarFechasMesActual() {
    const hoy = new Date();
    // Primer día del mes a mediodía
    const primerDia = new Date(hoy.getFullYear(), hoy.getMonth(), 1, 12, 0, 0);
    // Último día del mes a mediodía
    const ultimoDia = new Date(hoy.getFullYear(), hoy.getMonth() + 1, 0, 12, 0, 0);
    if (fechaInicioInput) {
        const fechaISO = primerDia.toISOString().slice(0, 10);
        fechaInicioInput.value = '';
        fechaInicioInput.value = fechaISO;
        fechaInicioInput.setAttribute('value', fechaISO);
        fechaInicioInput.dispatchEvent(new Event('change', { bubbles: true }));
        // Forzar repaint visual
        fechaInicioInput.type = 'text';
        fechaInicioInput.type = 'date';
        console.log('Fecha inicio asignada:', fechaInicioInput.value);
    }
    if (fechaFinInput) {
        const fechaISO = ultimoDia.toISOString().slice(0, 10);
        fechaFinInput.value = '';
        fechaFinInput.value = fechaISO;
        fechaFinInput.setAttribute('value', fechaISO);
        fechaFinInput.dispatchEvent(new Event('change', { bubbles: true }));
        // Forzar repaint visual
        fechaFinInput.type = 'text';
        fechaFinInput.type = 'date';
        console.log('Fecha fin asignada:', fechaFinInput.value);
    }
}


function renderizarGastos(gastos) {
    tablaBody.innerHTML = '';
    let total = 0;
    if (!gastos.length) {
        noResultados.classList.remove('oculto');
        const totalImporteGastos = document.getElementById('totalImporteGastos');
        if (totalImporteGastos) {
            totalImporteGastos.textContent = formatearImporte(0);
            totalImporteGastos.classList.remove('hidden');
        }
        // Asegura que los otros totales también se ponen a 0 y se muestran
        const spanIngresos = document.getElementById('totalIngresos');
        const spanGastos = document.getElementById('totalGastos');
        const spanDiferencia = document.getElementById('totalDiferencia');
        if (spanIngresos) { spanIngresos.textContent = formatearImporte(0); spanIngresos.classList.remove('hidden'); }
        if (spanGastos) { spanGastos.textContent = formatearImporte(0); spanGastos.classList.remove('hidden'); }
        if (spanDiferencia) { spanDiferencia.textContent = formatearImporte(0); spanDiferencia.classList.remove('hidden'); }
        return;
    }
    noResultados.classList.add('oculto');
    gastos.forEach(gasto => {
        total += Number(gasto.importe_eur) || 0;
        const fila = document.createElement('tr');
        const claseImporte = Number(gasto.importe_eur) < 0 ? 'importe-negativo' : 'importe-positivo';
        fila.innerHTML = `
            <td>${gasto.fecha_operacion}</td>
            <td>${gasto.fecha_valor}</td>
            <td>${gasto.concepto}</td>
            <td class="text-right ${claseImporte}">${formatearImporte(Number(gasto.importe_eur))}</td>
        `;
        tablaBody.appendChild(fila);
    });
    const totalImporteGastos = document.getElementById('totalImporteGastos');
    if (totalImporteGastos) {
        totalImporteGastos.textContent = formatearImporte(total);
        totalImporteGastos.classList.remove('hidden');
    }
    // Asegura que los otros totales también se muestran
    const spanIngresos = document.getElementById('totalIngresos');
    const spanGastos = document.getElementById('totalGastos');
    const spanDiferencia = document.getElementById('totalDiferencia');
    if (spanIngresos) spanIngresos.classList.remove('hidden');
    if (spanGastos) spanGastos.classList.remove('hidden');
    if (spanDiferencia) spanDiferencia.classList.remove('hidden');
}

// Mostrar/ocultar totales como en facturas
function updateIconGastos(show) {
    const icon = document.querySelector('.fixed-footer-gastos .toggle-totals i');
    if (!icon) return;
    if (show) {
        icon.classList.remove('fa-eye-slash');
        icon.classList.add('fa-eye');
    } else {
        icon.classList.remove('fa-eye');
        icon.classList.add('fa-eye-slash');
    }
}

function showTotalsGastos() {
    document.querySelectorAll('.fixed-footer-gastos .content-cell').forEach(cell => cell.classList.remove('hidden'));
    document.querySelectorAll('.fixed-footer-gastos .label-totales-small').forEach(label => label.classList.remove('hidden'));
    updateIconGastos(true);
}

function hideTotalsGastos() {
    document.querySelectorAll('.fixed-footer-gastos .content-cell').forEach(cell => cell.classList.add('hidden'));
    document.querySelectorAll('.fixed-footer-gastos .label-totales-small').forEach(label => label.classList.add('hidden'));
    updateIconGastos(false);
}

async function buscarGastos() {
    const params = new URLSearchParams();
    if (fechaInicioInput.value) params.append('fecha_inicio', fechaInicioInput.value);
    if (fechaFinInput.value) params.append('fecha_fin', fechaFinInput.value);
    if (conceptoInput.value) params.append('concepto', conceptoInput.value);
    if (tipoMovimientoInput && tipoMovimientoInput.value !== 'todos') {
        params.append('tipo', tipoMovimientoInput.value);
    }
    try {
        const url = `http://${IP_SERVER}:${PORT}/api/gastos?${params.toString()}`;
        const response = await fetch(url);
        if (!response.ok) {
            throw new Error('Error al consultar los gastos');
        }
        const data = await response.json();
        renderizarGastos(data.gastos || []);
        // Mostrar los totales nuevos, solo si existen los spans
        const spanIngresos = document.getElementById('totalIngresos');
        const spanGastos = document.getElementById('totalGastos');
        const spanDiferencia = document.getElementById('totalDiferencia');
        if (spanIngresos) {
            spanIngresos.textContent = formatearImporte(data.total_positivos || 0);
            spanIngresos.classList.remove('hidden');
            spanIngresos.classList.remove('importe-negativo', 'importe-positivo');
            spanIngresos.classList.add((data.total_positivos || 0) >= 0 ? 'importe-positivo' : 'importe-negativo');
        }
        if (spanGastos) {
            spanGastos.textContent = formatearImporte(data.total_negativos || 0);
            spanGastos.classList.remove('hidden');
            spanGastos.classList.remove('importe-negativo', 'importe-positivo');
            spanGastos.classList.add((data.total_negativos || 0) >= 0 ? 'importe-positivo' : 'importe-negativo');
        }
        if (spanDiferencia) {
            spanDiferencia.textContent = formatearImporte(data.diferencia || 0);
            spanDiferencia.classList.remove('hidden');
            spanDiferencia.classList.remove('importe-negativo', 'importe-positivo');
            spanDiferencia.classList.add((data.diferencia || 0) >= 0 ? 'importe-positivo' : 'importe-negativo');
        }
        // Asegura que los totales están visibles siempre tras cada búsqueda
        showTotalsGastos();
    } catch (error) {
        mostrarNotificacion(error.message, 'error');
    }
}

// Búsqueda interactiva
fechaInicioInput.addEventListener('change', buscarGastos);
fechaFinInput.addEventListener('change', buscarGastos);
conceptoInput.addEventListener('input', buscarGastos);
buscarBtn.addEventListener('click', buscarGastos);
tipoMovimientoInput.addEventListener('change', buscarGastos);

document.addEventListener('DOMContentLoaded', () => {
    inicializarFechasMesActual();
    buscarGastos();
    // Control de visibilidad de totales
    const toggle = document.querySelector('.fixed-footer-gastos .toggle-totals');
    let totalsVisible = sessionStorage.getItem('totalsVisibleGastos');
    if (totalsVisible === 'true') {
        showTotalsGastos();
    } else {
        hideTotalsGastos();
    }
    toggle.addEventListener('click', function() {
        let currentlyVisible = sessionStorage.getItem('totalsVisibleGastos') === 'true';
        if (currentlyVisible) {
            hideTotalsGastos();
        } else {
            showTotalsGastos();
        }
        sessionStorage.setItem('totalsVisibleGastos', !currentlyVisible);
    });
    toggle.addEventListener('keypress', function(event) {
        if (event.key === 'Enter' || event.key === ' ') {
            event.preventDefault();
            toggle.click();
        }
    });
});
