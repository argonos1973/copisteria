// ===== ESTADISTICAS GASTOS =====

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

function initCollapseControlsGastos() {
    document.querySelectorAll('#tab-gastos .toggle-card').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            const card = btn.closest('.stats-card');
            const isCollapsed = card.classList.contains('collapsed');
            
            if (isCollapsed) {
                card.classList.remove('collapsed');
                card.style.opacity = '1';
                card.style.borderLeft = '';
                btn.querySelector('i').classList.remove('fa-eye');
                btn.querySelector('i').classList.add('fa-eye-slash');
                btn.title = 'Ocultar';
            } else {
                card.classList.add('collapsed');
                card.style.opacity = '0.85';
                card.style.borderLeft = '4px solid #ccc';
                btn.querySelector('i').classList.remove('fa-eye-slash');
                btn.querySelector('i').classList.add('fa-eye');
                btn.title = 'Mostrar';
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
        
        const response = await fetch(`http://localhost:5001/api/gastos/estadisticas?anio=${anio}&mes=${parseInt(mes)}`);
        
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
            'gastos-total-mes': formatImporte(data.total_gastos_mes),
            'gastos-pct-mes': formatPorcentaje(data.porcentaje_mes),
            'gastos-mes-anterior': `Mismo mes año anterior: ${formatImporte(data.total_gastos_mes_anterior)}`,
            'gastos-cantidad-mes': data.cantidad_gastos_mes,
            'gastos-total-anio': formatImporte(data.total_gastos_anio),
            'gastos-pct-anio': formatPorcentaje(data.porcentaje_anio),
            'gastos-anio-anterior': `Año anterior: ${formatImporte(data.total_gastos_anio_anterior)}`,
            'gastos-media-mensual': formatImporte(data.media_mensual),
            'gastos-cantidad-anio': data.cantidad_gastos_anio,
            'gastos-prevision': formatImporte(data.prevision_gastos_anio)
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
        const pctMes = document.getElementById('gastos-pct-mes');
        if (pctMes) {
            pctMes.className = `stats-percentage ${data.porcentaje_mes > 0 ? 'negative' : 'positive'}`;
        }
        
        const pctAnio = document.getElementById('gastos-pct-anio');
        if (pctAnio) {
            pctAnio.className = `stats-percentage ${data.porcentaje_anio > 0 ? 'negative' : 'positive'}`;
        }
        
        console.log('[GASTOS] Tarjetas actualizadas, cargando Top 10...');
        
        // Cargar top 10
        await cargarTop10Gastos(anio);
        
        console.log('[GASTOS] Carga completa');
        
    } catch (error) {
        console.error('[GASTOS] Error al cargar estadísticas:', error);
        alert('Error al cargar estadísticas de gastos: ' + error.message);
    }
}

async function cargarTop10Gastos(anio) {
    try {
        console.log(`[TOP10 GASTOS] Cargando top 10 para año ${anio}`);
        const response = await fetch(`http://localhost:5001/api/gastos/top10?anio=${anio}`);
        
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
                diferenciaHTML = `<span class="stats-percentage ${pctClass}">${pctSymbol} ${formatPorcentaje(Math.abs(gasto.porcentaje_diferencia))}</span>`;
            }
            
            tr.innerHTML = `
                <td style="font-size:0.8rem;padding:0.5rem 0.3rem;">
                    <span style="color:#999;font-weight:600;margin-right:0.5rem;">${index + 1}.</span>
                    ${escapeHtml(gasto.concepto)}
                </td>
                <td style="text-align:right;font-size:0.85rem;font-weight:600;padding:0.5rem 0.3rem;">${formatImporte(gasto.total)}</td>
                <td style="text-align:center;font-size:0.75rem;padding:0.5rem 0.3rem;">
                    ${diferenciaHTML}
                </td>
            `;
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

// ===== FUNCIONES AUXILIARES =====
function formatImporte(importe) {
    if (importe === null || importe === undefined) return '0,00 €';
    return new Intl.NumberFormat('es-ES', {
        style: 'currency',
        currency: 'EUR',
        minimumFractionDigits: 2
    }).format(importe);
}

function formatPorcentaje(pct) {
    if (pct === null || pct === undefined || isNaN(pct)) return '0%';
    const sign = pct > 0 ? '+' : '';
    return `${sign}${pct.toFixed(2)}%`;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ===== INICIALIZACIÓN =====
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initGastosTabs);
} else {
    initGastosTabs();
}

console.log('[GASTOS] Módulo cargado correctamente');
