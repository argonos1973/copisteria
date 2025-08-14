import { IP_SERVER, PORT } from '../static/constantes.js';
import { formatearImporte, debounce } from '../static/scripts_utils.js';
import { mostrarNotificacion } from '../static/notificaciones.js';

const fechaInicioInput = document.getElementById('fecha-inicio');
const fechaFinInput = document.getElementById('fecha-fin');
const conceptoInput = document.getElementById('concepto');
const buscarBtn = document.getElementById('buscar-btn');
const tipoMovimientoInput = document.getElementById('tipo-movimiento');
const tablaBody = document.querySelector('#tabla-gastos tbody');
const noResultados = document.getElementById('no-resultados');
const notificacion = document.getElementById('notificacion');
const graficoBtn = document.getElementById('btn-grafico');
let datosConsulta = [];

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
    // Ordenar por fecha (valor u operación) descendente
    gastos.sort((a,b) => new Date(b.fecha_valor || b.fecha_operacion) - new Date(a.fecha_valor || a.fecha_operacion));
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
        datosConsulta = data.gastos || [];
        renderizarGastos(datosConsulta);
        // Mostrar / ocultar botón gráfico
        if (graficoBtn) {
            if (conceptoInput.value.trim() && datosConsulta.length) {
                graficoBtn.style.display = 'flex';
            } else {
                graficoBtn.style.display = 'none';
            }
        }
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

/**
 * Descarga un CSV con los resultados actuales de la consulta.
 */
async function descargarCSV() {
    const params = new URLSearchParams();
    if (fechaInicioInput.value) params.append('fecha_inicio', fechaInicioInput.value);
    if (fechaFinInput.value) params.append('fecha_fin', fechaFinInput.value);
    if (conceptoInput.value) params.append('concepto', conceptoInput.value);
    if (tipoMovimientoInput && tipoMovimientoInput.value !== 'todos') {
        params.append('tipo', tipoMovimientoInput.value);
    }
    const url = `http://${IP_SERVER}:${PORT}/api/gastos?${params.toString()}`;
    try {
        const res = await fetch(url);
        if (!res.ok) throw new Error('Error al generar CSV');
        const data = await res.json();
        const gastos = data.gastos || [];
        const SEP = ';';
        const header = ['Fecha Operación','Fecha Valor','Concepto','Importe (€)'].join(SEP);
        const filas = gastos.map(g => [
            g.fecha_operacion,
            g.fecha_valor,
            `"${(g.concepto || '').replace(/"/g,'""')}"`,
            (Number(g.importe_eur)||0).toString().replace('.',',')
        ].join(SEP));
        const csv = [header, ...filas].join('\n');
        const link = document.createElement('a');
        link.href = URL.createObjectURL(new Blob([csv], { type: 'text/csv' }));
        const hoy = new Date().toISOString().slice(0, 10);
        link.download = `gastos_${hoy}.csv`;
        link.click();
    } catch (e) {
        mostrarNotificacion(e.message || 'Error inesperado', 'error');
    }
}

/**
 * Muestra un gráfico modal agrupando los importes por mes.
 */
function mostrarGrafico(gastos) {
    if (!gastos || !gastos.length) {
        mostrarNotificacion('No hay datos para graficar', 'info');
        return;
    }
    const mesesNombre = ['Enero','Febrero','Marzo','Abril','Mayo','Junio','Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre'];
    const sumMes = Array(12).fill(0);
    gastos.forEach(g => {
        const fechaStr = g.fecha_valor || g.fecha_operacion || '';
        if (!fechaStr) return;
        let mesIdx = -1;
        // Formatos posibles: YYYY-MM-DD, DD/MM/YYYY, DD-MM-YYYY
        if (/^\d{4}-\d{2}-\d{2}$/.test(fechaStr)) {
            mesIdx = parseInt(fechaStr.slice(5,7),10) - 1;
        } else if (/^\d{2}[\/\-]\d{2}[\/\-]\d{4}$/.test(fechaStr)) {
            mesIdx = parseInt(fechaStr.slice(3,5),10) - 1;
        }
        if (mesIdx < 0 || mesIdx > 11 || isNaN(mesIdx)) return;
        if (mesIdx < 0 || mesIdx > 11) return;
        const importe = Math.abs(Number(g.importe_eur) || 0);
        sumMes[mesIdx] += importe;
    });
    const pares = sumMes.map((v, i) => ({ idx: i, val: v})).filter(p => p.val > 0);
    if (!pares.length) {
        mostrarNotificacion('Sin datos válidos para graficar', 'info');
        return;
    }
    pares.sort((a,b)=>a.idx - b.idx);
    const labels = pares.map(p => mesesNombre[p.idx]);
    const valores = pares.map(p => p.val);

    let modal = document.getElementById('modal-gastos-grafico');
    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'modal-gastos-grafico';
        Object.assign(modal.style, {
            position: 'fixed', top: 0, left: 0, width: '100%', height: '100%',
            background: 'rgba(0,0,0,0.6)', display: 'flex', alignItems: 'center', justifyContent: 'center',
            zIndex: 1000
        });
        modal.addEventListener('click', e => { if (e.target === modal) modal.style.display = 'none'; });

        const content = document.createElement('div');
        Object.assign(content.style, {
            background: '#fff', padding: '20px', borderRadius: '8px', maxWidth: '800px', width: '90%',
            maxHeight: '90%', overflow: 'auto', position: 'relative'
        });
        const closeBtn = document.createElement('span');
        closeBtn.innerHTML = '&times;';
        closeBtn.className = 'cerrar-modal';
        Object.assign(closeBtn.style, {
            position: 'absolute', top: '10px', right: '16px', fontSize: '28px', fontWeight: 'bold', color: '#aaa', cursor: 'pointer'
        });
        closeBtn.addEventListener('mouseenter', () => closeBtn.style.color = '#000');
        closeBtn.addEventListener('mouseleave', () => closeBtn.style.color = '#aaa');
        closeBtn.addEventListener('click', () => modal.style.display = 'none');
        content.appendChild(closeBtn);

        const canvas = document.createElement('canvas');
        canvas.id = 'chart-gastos';
        canvas.style.maxHeight = '500px';
        content.appendChild(canvas);
        modal.appendChild(content);
        document.body.appendChild(modal);
    } else {
        modal.style.display = 'flex';
    }

    const ctx = document.getElementById('chart-gastos').getContext('2d');
    if (window.gastosChart) window.gastosChart.destroy();

    window.gastosChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels,
            datasets: [{
                label: 'Importe (€)',
                data: valores,
                backgroundColor: '#3498db'
            }]
        },
        options: {
            plugins: { legend: { display: false } },
            scales: {
                y: {
                    ticks: {
                        callback: value => formatearImporte(value)
                    }
                }
            }
        }
    });
}

// Búsqueda interactiva
fechaInicioInput.addEventListener('change', buscarGastos);
fechaFinInput.addEventListener('change', buscarGastos);
// Input de concepto con debounce para evitar peticiones excesivas
conceptoInput.addEventListener('input', debounce(buscarGastos, 400));
buscarBtn.addEventListener('click', buscarGastos);
tipoMovimientoInput.addEventListener('change', buscarGastos);

document.addEventListener('DOMContentLoaded', () => {
    inicializarFechasMesActual();
    buscarGastos();
    document.getElementById('btn-descargar-csv')?.addEventListener('click', descargarCSV);
    graficoBtn?.addEventListener('click', () => mostrarGrafico(datosConsulta));
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
