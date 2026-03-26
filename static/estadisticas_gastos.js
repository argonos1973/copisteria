// ===== ESTADISTICAS GASTOS =====
import { formatearImporte, formatearPorcentaje, escaparHtml } from './scripts_utils.js';

// Inicialización de pestañas y controles
function initGastosTabs() {
    console.log('[GASTOS] Inicializando pestañas de gastos...');
    
    const tabs = document.querySelectorAll('.tab');
    const tabContents = document.querySelectorAll('.tab-content');
    
    tabs.forEach(tab => {
        tab.addEventListener('click', function() {
            const tabName = this.getAttribute('data-tab');
            console.log(`[GASTOS] Pestaña clickeada: ${tabName}`);
            
            // Remover active de todos
            tabs.forEach(t => t.classList.remove('active'));
            tabContents.forEach(tc => tc.classList.remove('active'));
            
            // Agregar active al clickeado
            this.classList.add('active');
            document.getElementById(`tab-${tabName}`).classList.add('active');
            
            // Cargar datos según la pestaña
            if (tabName === 'gastos') {
                console.log('[GASTOS] Cargando datos de gastos...');
                setTimeout(() => cargarEstadisticasGastos(), 100);
            }
        });
    });
    
    // Inicializar controles de colapso para las tarjetas de gastos
    initCollapseControlsGastos();
    
    console.log('[GASTOS] Pestañas inicializadas correctamente');
}

async function initCollapseControlsGastos() {
    // Cargar preferencias del usuario
    let prefs = {};
    try {
        const res = await fetch('/api/auth/preferencias');
        if (res.ok) prefs = await res.json();
    } catch (e) {}
    
    document.querySelectorAll('#tab-gastos .toggle-card').forEach(btn => {
        const card = btn.closest('.stats-card');
        const key = `statsHidden_${card.id}`;
        
        // Aplicar estado guardado - ocultar completamente
        if (prefs[key] === '1') {
            card.style.display = 'none';
        }
        
        btn.addEventListener('click', async (e) => {
            e.preventDefault();
            // Ocultar la tarjeta
            card.style.display = 'none';
            
            // Guardar preferencia
            try {
                await fetch('/api/auth/preferencias', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ [key]: '1' })
                });
            } catch (e) {}
            
            // Actualizar menú de tarjetas ocultas (si existe la función)
            if (typeof actualizarMenuTarjetasOcultas === 'function') {
                actualizarMenuTarjetasOcultas();
            }
        });
    });
}

// ===== CARGAR ESTADÍSTICAS =====
async function cargarEstadisticasGastos() {
    try {
        console.log('[GASTOS] Iniciando carga de estadísticas...');
        const selectorFecha = document.getElementById('selector-fecha');
        if (!selectorFecha || !selectorFecha.value) {
            console.error('[GASTOS] Selector de fecha no disponible');
            return;
        }
        
        const [anio, mes] = selectorFecha.value.split('-');
        console.log(`[GASTOS] Año: ${anio}, Mes: ${mes}`);
        
        const apiHost = window.location.hostname;
        const protocol = window.location.protocol;
        const usePort = window.location.port ? `:${window.location.port}` : '';
        const response = await fetch(`${protocol}//${apiHost}${usePort}/api/gastos/estadisticas?anio=${anio}&mes=${parseInt(mes)}`);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        console.log('[GASTOS] Datos recibidos:', data);
        
        if (data.error) {
            console.error('Error al cargar estadísticas de gastos:', data.error);
            return;
        }
        
        // Actualizar tarjetas
        const elementos = {
            'gastos-total-mes-solo': formatearImporte(data.total_gastos_mes_solo),
            'gastos-pct-mes-previo': formatearPorcentaje(data.porcentaje_mes_previo),
            'gastos-mes-previo': `Mes anterior: ${formatearImporte(data.total_gastos_mes_previo)}`,
            'gastos-pct-mes-solo': formatearPorcentaje(data.porcentaje_mes_solo),
            'gastos-mes-solo-anterior': `Mismo mes año anterior: ${formatearImporte(data.total_gastos_mes_solo_anterior)}`,
            'gastos-cantidad-mes-solo': data.cantidad_gastos_mes_solo,
            'gastos-total-mes': formatearImporte(data.total_gastos_mes),
            'gastos-pct-mes': formatearPorcentaje(data.porcentaje_mes),
            'gastos-mes-anterior': `Mismo trimestre año anterior: ${formatearImporte(data.total_gastos_mes_anterior)}`,
            'gastos-cantidad-mes': data.cantidad_gastos_mes,
            'gastos-total-anio': formatearImporte(data.total_gastos_anio),
            'gastos-pct-anio': formatearPorcentaje(data.porcentaje_anio),
            'gastos-anio-anterior': `Año anterior: ${formatearImporte(data.total_gastos_anio_anterior)}`,
            'gastos-media-mensual': formatearImporte(data.media_mensual),
            'gastos-cantidad-anio': data.cantidad_gastos_anio,
            'gastos-prevision': formatearImporte(data.prevision_gastos_anio)
        };
        
        for (const [id, valor] of Object.entries(elementos)) {
            const elem = document.getElementById(id);
            if (elem) {
                elem.textContent = valor;
            } else {
                console.warn(`[GASTOS] Elemento no encontrado: ${id}`);
            }
        }
        
        // Actualizar clases de porcentajes
        const pctMesPrevio = document.getElementById('gastos-pct-mes-previo');
        if (pctMesPrevio) {
            pctMesPrevio.className = `stats-percentage ${data.porcentaje_mes_previo > 0 ? 'negative' : 'positive'}`;
        }
        
        const pctMesSolo = document.getElementById('gastos-pct-mes-solo');
        if (pctMesSolo) {
            pctMesSolo.className = `stats-percentage ${data.porcentaje_mes_solo > 0 ? 'negative' : 'positive'}`;
        }
        
        const pctMes = document.getElementById('gastos-pct-mes');
        if (pctMes) {
            pctMes.className = `stats-percentage ${data.porcentaje_mes > 0 ? 'negative' : 'positive'}`;
        }
        
        const pctAnio = document.getElementById('gastos-pct-anio');
        if (pctAnio) {
            pctAnio.className = `stats-percentage ${data.porcentaje_anio > 0 ? 'negative' : 'positive'}`;
        }
        
        console.log('[GASTOS] Tarjetas actualizadas, cargando gráfico mes y Top 10...');
        
        // Cargar gráfico del mes
        await cargarGraficoGastosMesSolo(anio, parseInt(mes));
        
        // Cargar top 10
        await cargarTop10Gastos(anio);
        
        console.log('[GASTOS] Carga completa');
        
    } catch (error) {
        console.error('[GASTOS] Error al cargar estadísticas:', error);
        alert('Error al cargar estadísticas de gastos: ' + error.message);
    }
}

let graficoGastosMesSolo = null;

async function cargarGraficoGastosMesSolo(anio, mes) {
    try {
        const apiHost = window.location.hostname;
        const protocol = window.location.protocol;
        const usePort = window.location.port ? `:${window.location.port}` : '';
        const response = await fetch(`${protocol}//${apiHost}${usePort}/api/gastos/por-categoria-mes-solo?anio=${anio}&mes=${mes}`);
        
        if (!response.ok) return;
        
        const datos = await response.json();
        
        if (!datos.categorias || datos.categorias.length === 0) return;
        
        const canvas = document.getElementById('grafico-gastos-mes-solo');
        if (!canvas) return;
        
        const ctx = canvas.getContext('2d');
        
        if (graficoGastosMesSolo) {
            graficoGastosMesSolo.destroy();
        }
        
        const colores = [
            '#e74c3c', '#3498db', '#f39c12', '#2ecc71', '#9b59b6',
            '#1abc9c', '#e67e22', '#34495e', '#16a085', '#c0392b'
        ];
        
        const labels = datos.categorias.map(c => c.categoria);
        const valores = datos.categorias.map(c => c.total);
        
        graficoGastosMesSolo = new Chart(ctx, {
            type: 'pie',
            data: {
                labels: labels,
                datasets: [{
                    data: valores,
                    backgroundColor: colores.slice(0, labels.length),
                    borderWidth: 2,
                    borderColor: '#fff'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                onClick: (event, elements) => {
                    if (elements.length > 0) {
                        const index = elements[0].index;
                        const proveedor = labels[index];
                        abrirModalDetallesProveedor(proveedor, anio, mes);
                    }
                },
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            padding: 10,
                            font: { size: 11 }
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const label = context.label || '';
                                const value = context.parsed || 0;
                                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                const pct = total > 0 ? ((value / total) * 100).toFixed(1) : 0;
                                return `${label}: ${formatearImporte(value)} (${pct}%)`;
                            }
                        }
                    }
                }
            }
        });
    } catch (error) {
        console.error('[GASTOS] Error al cargar gráfico del mes:', error);
    }
}

async function cargarTop10Gastos(anio) {
    try {
        console.log(`[TOP10 GASTOS] Cargando top 10 para año ${anio}`);
        const apiHost = window.location.hostname;
        const protocol = window.location.protocol;
        const usePort = window.location.port ? `:${window.location.port}` : '';
        const response = await fetch(`${protocol}//${apiHost}${usePort}/api/gastos/top10?anio=${anio}`);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        console.log('[TOP10 GASTOS] Datos recibidos:', data);
        
        const tbody = document.getElementById('topGastosBody');
        if (!tbody) {
            console.error('[TOP10 GASTOS] No se encontró el elemento topGastosBody');
            return;
        }
        
        tbody.innerHTML = '';
        
        if (!data.top_gastos || data.top_gastos.length === 0) {
            tbody.innerHTML = '<tr><td colspan="3" style="text-align:center;padding:1rem;">No hay datos disponibles</td></tr>';
            return;
        }
        
        data.top_gastos.forEach((gasto, index) => {
            const tr = document.createElement('tr');
            
            // Mostrar diferencia si hay datos del año anterior
            let diferenciaHTML = '<span style="color:#999;font-size:0.7rem;">-</span>';
            if (gasto.total_anterior && gasto.total_anterior > 0) {
                const pctClass = gasto.diferencia > 0 ? 'negative' : 'positive';
                const pctSymbol = gasto.diferencia > 0 ? '▲' : '▼';
                diferenciaHTML = `<span class="stats-percentage ${pctClass}">${pctSymbol} ${formatearPorcentaje(Math.abs(gasto.porcentaje_diferencia))}</span>`;
            }
            
            tr.innerHTML = `
                <td style="font-size:0.8rem;padding:0.5rem 0.3rem;">
                    <span style="color:#999;font-weight:600;margin-right:0.5rem;">${index + 1}.</span>
                    ${escaparHtml(gasto.concepto)}
                </td>
                <td style="text-align:right;font-size:0.85rem;font-weight:600;padding:0.5rem 0.3rem;">${formatearImporte(gasto.total)}</td>
                <td style="text-align:center;font-size:0.75rem;padding:0.5rem 0.3rem;">
                    ${diferenciaHTML}
                </td>
            `;
            
            // Agregar evento click para abrir modal con detalles
            tr.style.cursor = 'pointer';
            tr.addEventListener('click', () => {
                if (typeof window.abrirModalDetallesGasto === 'function') {
                    window.abrirModalDetallesGasto(gasto.concepto, anio);
                } else {
                    console.error('[TOP10 GASTOS] Función abrirModalDetallesGasto no encontrada');
                }
            });
            
            // Hover effect
            tr.addEventListener('mouseenter', () => {
                tr.style.backgroundColor = '#f5f5f5';
            });
            tr.addEventListener('mouseleave', () => {
                tr.style.backgroundColor = '';
            });
            
            tbody.appendChild(tr);
        });
        
        console.log(`[TOP10 GASTOS] Se cargaron ${data.top_gastos.length} gastos`);
        
    } catch (error) {
        console.error('[TOP10 GASTOS] Error al cargar:', error);
        const tbody = document.getElementById('topGastosBody');
        if (tbody) {
            tbody.innerHTML = `<tr><td colspan="3" style="text-align:center;padding:1rem;color:red;">Error: ${error.message}</td></tr>`;
        }
    }
}

// ===== MODAL DETALLES PROVEEDOR =====
async function abrirModalDetallesProveedor(proveedor, anio, mes, trimestre) {
    const modal = document.getElementById('modal-detalles-gasto');
    if (!modal) return;

    modal.classList.add('show');
    modal.style.display = 'flex';

    let titulo = proveedor;
    if (mes) titulo += ` - Mes ${mes}/${anio}`;
    else if (trimestre) titulo += ` - T${trimestre}/${anio}`;
    else titulo += ` - Año ${anio}`;

    document.getElementById('modal-concepto-titulo').textContent = titulo;
    document.getElementById('modal-detalles-body').innerHTML =
        '<tr><td colspan="5" style="text-align:center;padding:2rem;">⏳ Cargando detalles...</td></tr>';

    try {
        const apiHost = window.location.hostname;
        const protocol = window.location.protocol;
        const usePort = window.location.port ? `:${window.location.port}` : '';
        let url = `${protocol}//${apiHost}${usePort}/api/gastos/detalles-proveedor?proveedor=${encodeURIComponent(proveedor)}&anio=${anio}`;
        if (mes) url += `&mes=${mes}`;
        if (trimestre) url += `&trimestre=${trimestre}`;

        const respuesta = await fetch(url);
        if (!respuesta.ok) throw new Error(`HTTP ${respuesta.status}`);

        const datos = await respuesta.json();

        // Actualizar estadísticas
        document.getElementById('modal-total').textContent = formatearImporte(datos.estadisticas.total);
        document.getElementById('modal-cantidad').textContent = datos.estadisticas.cantidad;
        document.getElementById('modal-promedio').textContent = formatearImporte(datos.estadisticas.promedio);
        document.getElementById('modal-minimo').textContent = formatearImporte(datos.estadisticas.minimo);
        document.getElementById('modal-maximo').textContent = formatearImporte(datos.estadisticas.maximo);

        const tbody = document.getElementById('modal-detalles-body');
        tbody.innerHTML = '';

        if (!datos.facturas || datos.facturas.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;padding:2rem;">No hay facturas registradas</td></tr>';
            return;
        }

        datos.facturas.forEach((f, index) => {
            const fila = document.createElement('tr');
            const estadoColor = f.estado === 'pagada' ? '#2ecc71' : (f.estado === 'pendiente' ? '#f39c12' : '#999');
            fila.innerHTML = `
                <td style="padding: 0.5rem 0.3rem; font-size: 0.85rem; width: 40%;">
                    <span style="font-weight:600;margin-right:0.3rem;">${index + 1}.</span>
                    ${escaparHtml(f.concepto || f.numero_factura)}
                </td>
                <td style="padding: 0.5rem 0.3rem; font-size: 0.8rem; text-align: center; width: 15%;">${f.numero_factura}</td>
                <td style="padding: 0.5rem 0.3rem; font-size: 0.85rem; text-align: right; font-weight: 600; width: 15%;">${formatearImporte(f.total)}</td>
                <td style="padding: 0.5rem 0.3rem; font-size: 0.8rem; text-align: center; width: 15%;">
                    <span style="color:${estadoColor};font-weight:500;">${f.estado}</span>
                </td>
                <td style="padding: 0.5rem 0.3rem; font-size: 0.8rem; text-align: center; width: 15%;">${f.fecha}</td>
            `;
            tbody.appendChild(fila);
        });

    } catch (error) {
        console.error('[MODAL PROVEEDOR] Error:', error);
        document.getElementById('modal-detalles-body').innerHTML =
            `<tr><td colspan="5" style="text-align:center;padding:2rem;">❌ Error: ${error.message}</td></tr>`;
    }
}

// Exponer globalmente para que los gráficos inline puedan usarla
window.abrirModalDetallesProveedor = abrirModalDetallesProveedor;

// ===== FUNCIONES AUXILIARES =====
// Las funciones formatearImporte, formatearPorcentaje y escaparHtml 
// ahora se importan desde scripts_utils.js

// ===== INICIALIZACIÓN =====
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initGastosTabs);
} else {
    initGastosTabs();
}

console.log('[GASTOS] Módulo cargado correctamente');
