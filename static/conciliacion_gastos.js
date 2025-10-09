// conciliacion_gastos.js
import { IP_SERVER, PORT } from './constantes.js';
import { mostrarNotificacion, mostrarConfirmacion } from './notificaciones.js';

const API_URL = `http://${IP_SERVER}:${PORT}/api`;

let gastoSeleccionado = null;
let coincidenciaSeleccionada = null;

// Variables de paginación
let gastosPendientesCompletos = [];
let paginaActualPendientes = 1;
let itemsPorPaginaPendientes = 10;

let transferenciasCompletas = [];
let paginaActualTransferencias = 1;
let itemsPorPaginaTransferencias = 10;

let liquidacionesCompletas = [];
let paginaActualLiquidaciones = 1;
let itemsPorPaginaLiquidaciones = 10;

let conciliadosCompletos = [];
let paginaActualConciliados = 1;
let itemsPorPaginaConciliados = 10;

let ingresosCompletos = [];
let paginaActualIngresos = 1;
let itemsPorPaginaIngresos = 10;

// ============================================================================
// INICIALIZACIÓN
// ============================================================================

document.addEventListener('DOMContentLoaded', () => {
    inicializarPestanas();
    cargarDatos();
    
    // Ejecutar conciliación automática al cargar (si hay pendientes)
    setTimeout(() => {
        ejecutarConciliacionInicial();
    }, 1000);
});

function inicializarPestanas() {
    const tabs = document.querySelectorAll('.tab');
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            const tabName = tab.dataset.tab;
            
            // Desactivar todas las pestañas
            tabs.forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            
            // Activar la pestaña seleccionada
            tab.classList.add('active');
            document.getElementById(`tab-${tabName}`).classList.add('active');
        });
    });
}

// ============================================================================
// CARGA DE DATOS
// ============================================================================

window.cargarDatos = async function() {
    await Promise.all([
        cargarGastosPendientes(),
        cargarTransferencias(),
        cargarLiquidacionesTPV(),
        cargarIngresosEfectivo(),
        cargarConciliados(),
        cargarEstadisticas()
    ]);
}

async function cargarTransferencias() {
    const loading = document.getElementById('loading-transferencias');
    const empty = document.getElementById('empty-transferencias');
    const tabla = document.getElementById('tabla-transferencias');
    const pagination = document.getElementById('pagination-transferencias');
    
    loading.style.display = 'block';
    empty.style.display = 'none';
    tabla.style.display = 'none';
    pagination.style.display = 'none';
    
    try {
        const response = await fetch(`${API_URL}/conciliacion/gastos-pendientes?tipo=transferencia`);
        const data = await response.json();
        
        loading.style.display = 'none';
        
        if (data.success && data.gastos && data.gastos.length > 0) {
            // Filtrar solo transferencias
            transferenciasCompletas = data.gastos.filter(g => 
                g.concepto && (
                    g.concepto.toLowerCase().includes('transferencia') ||
                    g.concepto.toLowerCase().includes('transf.')
                )
            );
            
            if (transferenciasCompletas.length > 0) {
                paginaActualTransferencias = 1;
                renderizarPaginaTransferencias();
                tabla.style.display = 'table';
                pagination.style.display = 'flex';
            } else {
                empty.style.display = 'block';
            }
        } else {
            empty.style.display = 'block';
        }
    } catch (error) {
        console.error('Error al cargar transferencias:', error);
        loading.style.display = 'none';
        empty.style.display = 'block';
    }
}

function renderizarPaginaTransferencias() {
    const tbody = document.getElementById('tbody-transferencias');
    tbody.innerHTML = '';
    
    const inicio = (paginaActualTransferencias - 1) * itemsPorPaginaTransferencias;
    const fin = inicio + itemsPorPaginaTransferencias;
    const transferenciasPagina = transferenciasCompletas.slice(inicio, fin);
    
    transferenciasPagina.forEach(gasto => {
        const tr = document.createElement('tr');
        tr.style.cursor = 'pointer';
        tr.onclick = () => buscarCoincidencias(gasto.id);
        
        tr.innerHTML = `
            <td>${formatearFecha(gasto.fecha_operacion)}</td>
            <td>${gasto.concepto}</td>
            <td class="text-right ${gasto.importe_eur >= 0 ? 'importe-positivo' : 'importe-negativo'}">
                ${formatearImporte(gasto.importe_eur)}
            </td>
        `;
        tbody.appendChild(tr);
    });
    
    actualizarControlesPaginacionTransferencias();
}

function actualizarControlesPaginacionTransferencias() {
    const totalPaginas = Math.ceil(transferenciasCompletas.length / itemsPorPaginaTransferencias);
    document.getElementById('pageInfoTransferencias').textContent = `Página ${paginaActualTransferencias} de ${totalPaginas}`;
    document.getElementById('prevPageTransferencias').disabled = paginaActualTransferencias === 1;
    document.getElementById('nextPageTransferencias').disabled = paginaActualTransferencias === totalPaginas;
}

window.cambiarPaginaTransferencias = function(accion) {
    const totalPaginas = Math.ceil(transferenciasCompletas.length / itemsPorPaginaTransferencias);
    if (accion === 'anterior' && paginaActualTransferencias > 1) paginaActualTransferencias--;
    if (accion === 'siguiente' && paginaActualTransferencias < totalPaginas) paginaActualTransferencias++;
    renderizarPaginaTransferencias();
};

window.cambiarItemsPorPaginaTransferencias = function() {
    itemsPorPaginaTransferencias = parseInt(document.getElementById('items-por-pagina-transferencias').value);
    paginaActualTransferencias = 1;
    renderizarPaginaTransferencias();
};

/**
 * Busca documentos en efectivo y aplica algoritmo de conciliación automática
 * para un ingreso en efectivo pendiente (versión silenciosa para procesamiento masivo)
 * Solo concilia si la diferencia es < 1€
 */
async function buscarYConciliarIngresoEfectivoSilencioso(gasto) {
    try {
        // Buscar documentos en efectivo cercanos a la fecha del gasto
        const response = await fetch(`${API_URL}/conciliacion/documentos-efectivo?fecha=${encodeURIComponent(gasto.fecha_operacion)}`);
        const data = await response.json();
        
        if (!data.success || !data.documentos || data.documentos.length === 0) {
            return false;
        }
        
        const objetivo = Math.abs(parseFloat(gasto.importe_eur));
        const documentos = data.documentos.map(d => ({
            ...d,
            importe: parseFloat(d.total)
        }));
        
        // Usar algoritmo de varita mágica para encontrar mejor combinación
        const mejorCombinacion = encontrarMejorCombinacion(documentos, objetivo);
        
        if (mejorCombinacion.length === 0) {
            return false;
        }
        
        const totalCombinacion = mejorCombinacion.reduce((sum, d) => sum + parseFloat(d.total), 0);
        const diferencia = Math.abs(objetivo - totalCombinacion);
        
        // Solo conciliar si la diferencia es menor a 1€
        if (diferencia >= 1.0) {
            console.log(`⊗ Ingreso ${gasto.fecha_operacion} (${formatearImporte(gasto.importe_eur)}) - diferencia muy alta: ${formatearImporte(diferencia)} - requiere revisión manual`);
            return false;
        }
        
        // Preparar datos para conciliación
        const documentosSeleccionados = mejorCombinacion.map(doc => ({
            tipo: doc.tipo,
            id: doc.id,
            numero: doc.numero,
            total: doc.total
        }));
        
        // Conciliar
        const conciliarResponse = await fetch(`${API_URL}/conciliacion/conciliar-ingreso-efectivo`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                ids_gastos: gasto.id.toString(),
                fecha: gasto.fecha_operacion,
                documentos_seleccionados: documentosSeleccionados
            })
        });
        
        const result = await conciliarResponse.json();
        
        if (result.success) {
            const tipoMatch = diferencia < 0.01 ? 'EXACTA' : 'CERCANA';
            console.log(`✓ Ingreso ${gasto.fecha_operacion} (${formatearImporte(gasto.importe_eur)}) conciliado [${tipoMatch}] con ${mejorCombinacion.length} documentos (dif: ${formatearImporte(diferencia)})`);
            return true;
        }
        
        return false;
    } catch (error) {
        console.error('Error al conciliar ingreso efectivo:', error);
        return false;
    }
}

/**
 * Busca documentos en efectivo y aplica algoritmo de conciliación automática
 * para un ingreso en efectivo pendiente (versión con notificaciones para clic manual)
 * Solo concilia si la diferencia es < 1€
 */
async function buscarYConciliarIngresoEfectivo(gasto) {
    try {
        mostrarNotificacion('Buscando documentos en efectivo...', 'info');
        
        // Buscar documentos en efectivo cercanos a la fecha del gasto
        const response = await fetch(`${API_URL}/conciliacion/documentos-efectivo?fecha=${encodeURIComponent(gasto.fecha_operacion)}`);
        const data = await response.json();
        
        if (!data.success || !data.documentos || data.documentos.length === 0) {
            mostrarNotificacion('No se encontraron documentos en efectivo disponibles', 'warning');
            return;
        }
        
        const objetivo = Math.abs(parseFloat(gasto.importe_eur));
        const documentos = data.documentos.map(d => ({
            ...d,
            importe: parseFloat(d.total)
        }));
        
        // Usar algoritmo de varita mágica para encontrar mejor combinación
        const mejorCombinacion = encontrarMejorCombinacion(documentos, objetivo);
        
        if (mejorCombinacion.length === 0) {
            mostrarNotificacion('No se encontró ninguna combinación válida de documentos', 'warning');
            return;
        }
        
        const totalCombinacion = mejorCombinacion.reduce((sum, d) => sum + parseFloat(d.total), 0);
        const diferencia = Math.abs(objetivo - totalCombinacion);
        
        // Verificar si la diferencia es aceptable (< 1€)
        if (diferencia >= 1.0) {
            mostrarNotificacion(`⚠ Diferencia muy alta: ${formatearImporte(diferencia)}. No se puede conciliar automáticamente. Requiere revisión manual.`, 'warning');
            return;
        }
        
        // Preparar datos para conciliación
        const documentosSeleccionados = mejorCombinacion.map(doc => ({
            tipo: doc.tipo,
            id: doc.id,
            numero: doc.numero,
            total: doc.total
        }));
        
        // Mostrar notificación con resultado
        if (diferencia < 0.01) {
            mostrarNotificacion(`✓ Combinación exacta encontrada: ${mejorCombinacion.length} documentos. Conciliando...`, 'success');
        } else {
            mostrarNotificacion(`Mejor combinación: ${mejorCombinacion.length} documentos (diferencia: ${formatearImporte(diferencia)}). Conciliando...`, 'info');
        }
        
        // Conciliar
        const conciliarResponse = await fetch(`${API_URL}/conciliacion/conciliar-ingreso-efectivo`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                ids_gastos: gasto.id.toString(),
                fecha: gasto.fecha_operacion,
                documentos_seleccionados: documentosSeleccionados
            })
        });
        
        const result = await conciliarResponse.json();
        
        if (result.success) {
            mostrarNotificacion(`✓ Ingreso conciliado con ${mejorCombinacion.length} documentos`, 'success');
            await cargarDatos();
        } else {
            mostrarNotificacion(`Error: ${result.error}`, 'error');
        }
    } catch (error) {
        console.error('Error al conciliar ingreso efectivo:', error);
        mostrarNotificacion(`Error: ${error.message}`, 'error');
    }
}

async function cargarGastosPendientes() {
    const loading = document.getElementById('loading-pendientes');
    const empty = document.getElementById('empty-pendientes');
    const tabla = document.getElementById('tabla-pendientes');
    const tbody = document.getElementById('tbody-pendientes');
    const pagination = document.getElementById('pagination-pendientes');
    
    loading.style.display = 'block';
    empty.style.display = 'none';
    tabla.style.display = 'none';
    pagination.style.display = 'none';
    
    try {
        const response = await fetch(`${API_URL}/conciliacion/gastos-pendientes`);
        const data = await response.json();
        
        if (data.success && data.gastos.length > 0) {
            // Excluir transferencias de pendientes (tienen su propia pestaña)
            let gastosFiltrados = data.gastos.filter(g => 
                !g.concepto || (
                    !g.concepto.toLowerCase().includes('transferencia') &&
                    !g.concepto.toLowerCase().includes('transf.')
                )
            );
            
            // Separar ingresos en efectivo (importe positivo) de otros gastos
            const ingresosEfectivo = gastosFiltrados.filter(g => g.importe_eur > 0);
            const otrosGastos = gastosFiltrados.filter(g => g.importe_eur <= 0);
            
            // Procesar automáticamente los ingresos en efectivo
            if (ingresosEfectivo.length > 0) {
                console.log(`Procesando automáticamente ${ingresosEfectivo.length} ingresos en efectivo...`);
                
                for (const ingreso of ingresosEfectivo) {
                    await buscarYConciliarIngresoEfectivoSilencioso(ingreso);
                }
                
                // Recargar gastos pendientes después de procesar
                const responseActualizado = await fetch(`${API_URL}/conciliacion/gastos-pendientes`);
                const dataActualizado = await responseActualizado.json();
                
                if (dataActualizado.success) {
                    gastosFiltrados = dataActualizado.gastos.filter(g => 
                        !g.concepto || (
                            !g.concepto.toLowerCase().includes('transferencia') &&
                            !g.concepto.toLowerCase().includes('transf.')
                        )
                    );
                }
            }
            
            gastosPendientesCompletos = gastosFiltrados;
            
            if (gastosPendientesCompletos.length > 0) {
                paginaActualPendientes = 1;
                renderizarPaginaPendientes();
                tabla.style.display = 'table';
                pagination.style.display = 'flex';
            } else {
                empty.style.display = 'block';
            }
        } else {
            empty.style.display = 'block';
        }
    } catch (error) {
        console.error('Error al cargar gastos pendientes:', error);
        mostrarNotificacion('Error al cargar gastos pendientes', 'error');
    } finally {
        loading.style.display = 'none';
    }
}

function renderizarPaginaPendientes() {
    const tbody = document.getElementById('tbody-pendientes');
    tbody.innerHTML = '';
    
    const inicio = (paginaActualPendientes - 1) * itemsPorPaginaPendientes;
    const fin = inicio + itemsPorPaginaPendientes;
    const gastosPagina = gastosPendientesCompletos.slice(inicio, fin);
    
    gastosPagina.forEach(gasto => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td style="width: 100px;">${formatearFecha(gasto.fecha_operacion)}</td>
            <td>${gasto.concepto || '-'}</td>
            <td style="width: 120px;" class="text-right ${gasto.importe_eur >= 0 ? 'importe-positivo' : 'importe-negativo'}">
                ${formatearImporte(gasto.importe_eur)}
            </td>
        `;
        
        // Hacer toda la fila clickeable
        tr.addEventListener('click', () => {
            // Si es un ingreso en efectivo (importe positivo), usar algoritmo automático
            if (gasto.importe_eur > 0) {
                buscarYConciliarIngresoEfectivo(gasto);
            } else {
                window.buscarCoincidencias(gasto.id);
            }
        });
        
        tbody.appendChild(tr);
    });
    
    actualizarControlesPaginacion();
}

function actualizarControlesPaginacion() {
    const totalPaginas = Math.ceil(gastosPendientesCompletos.length / itemsPorPaginaPendientes);
    
    document.getElementById('pageInfoPendientes').textContent = `Página ${paginaActualPendientes} de ${totalPaginas}`;
    
    // Actualizar estado de botones
    document.getElementById('prevPagePendientes').disabled = paginaActualPendientes === 1;
    document.getElementById('nextPagePendientes').disabled = paginaActualPendientes === totalPaginas;
}

window.cambiarPaginaPendientes = function(accion) {
    const totalPaginas = Math.ceil(gastosPendientesCompletos.length / itemsPorPaginaPendientes);
    
    switch(accion) {
        case 'primera':
            paginaActualPendientes = 1;
            break;
        case 'anterior':
            if (paginaActualPendientes > 1) paginaActualPendientes--;
            break;
        case 'siguiente':
            if (paginaActualPendientes < totalPaginas) paginaActualPendientes++;
            break;
        case 'ultima':
            paginaActualPendientes = totalPaginas;
            break;
    }
    
    renderizarPaginaPendientes();
};

window.cambiarItemsPorPagina = function() {
    itemsPorPaginaPendientes = parseInt(document.getElementById('items-por-pagina-pendientes').value);
    paginaActualPendientes = 1;
    renderizarPaginaPendientes();
};

async function cargarConciliados() {
    const loading = document.getElementById('loading-conciliados');
    const empty = document.getElementById('empty-conciliados');
    const tabla = document.getElementById('tabla-conciliados');
    const pagination = document.getElementById('pagination-conciliados');
    
    loading.style.display = 'block';
    empty.style.display = 'none';
    tabla.style.display = 'none';
    pagination.style.display = 'none';
    
    try {
        const response = await fetch(`${API_URL}/conciliacion/conciliados`);
        const data = await response.json();
        
        if (data.success && data.conciliaciones.length > 0) {
            conciliadosCompletos = data.conciliaciones;
            paginaActualConciliados = 1;
            renderizarPaginaConciliados();
            tabla.style.display = 'table';
            pagination.style.display = 'flex';
        } else {
            empty.style.display = 'block';
        }
    } catch (error) {
        console.error('Error al cargar conciliados:', error);
        mostrarNotificacion('Error al cargar conciliados', 'error');
    } finally {
        loading.style.display = 'none';
    }
}

function renderizarPaginaConciliados() {
    const tbody = document.getElementById('tbody-conciliados');
    tbody.innerHTML = '';
    
    const inicio = (paginaActualConciliados - 1) * itemsPorPaginaConciliados;
    const fin = inicio + itemsPorPaginaConciliados;
    const conciliadosPagina = conciliadosCompletos.slice(inicio, fin);
    
    conciliadosPagina.forEach(conc => {
        const tr = document.createElement('tr');
        
        let tipoDocumento = '';
        if (conc.tipo_documento === 'liquidacion_tpv') {
            tipoDocumento = `<span class="badge badge-info">LIQUIDACIÓN TPV (${conc.num_liquidaciones || 0})</span>`;
        } else {
            tipoDocumento = `<span class="badge badge-info">${conc.tipo_documento.toUpperCase()} ${conc.numero_documento || ''}</span>`;
        }
        
        tr.innerHTML = `
            <td>${formatearFecha(conc.fecha_operacion)}</td>
            <td>${conc.concepto_gasto || '-'}</td>
            <td>${tipoDocumento}</td>
            <td>${formatearImporte(conc.importe_gasto)}</td>
            <td>${formatearImporte(conc.importe_documento)}</td>
            <td class="${Math.abs(conc.diferencia) < 0.01 ? 'importe-positivo' : 'importe-negativo'}">
                ${formatearImporte(conc.diferencia)}
            </td>
            <td>
                <span class="badge ${conc.metodo === 'automatico' ? 'badge-success' : 'badge-warning'}">
                    ${conc.metodo === 'automatico' ? 'Auto' : 'Manual'}
                </span>
            </td>
            <td class="text-center">
                <span class="delete-x" onclick="eliminarConciliacion(${conc.id})" title="Eliminar conciliación">✕</span>
            </td>
        `;
        tbody.appendChild(tr);
    });
    
    actualizarControlesPaginacionConciliados();
}

function actualizarControlesPaginacionConciliados() {
    const totalPaginas = Math.ceil(conciliadosCompletos.length / itemsPorPaginaConciliados);
    document.getElementById('pageInfoConciliados').textContent = `Página ${paginaActualConciliados} de ${totalPaginas}`;
    document.getElementById('prevPageConciliados').disabled = paginaActualConciliados === 1;
    document.getElementById('nextPageConciliados').disabled = paginaActualConciliados === totalPaginas;
}

window.cambiarPaginaConciliados = function(accion) {
    const totalPaginas = Math.ceil(conciliadosCompletos.length / itemsPorPaginaConciliados);
    if (accion === 'anterior' && paginaActualConciliados > 1) paginaActualConciliados--;
    if (accion === 'siguiente' && paginaActualConciliados < totalPaginas) paginaActualConciliados++;
    renderizarPaginaConciliados();
};

window.cambiarItemsPorPaginaConciliados = function() {
    itemsPorPaginaConciliados = parseInt(document.getElementById('items-por-pagina-conciliados').value);
    paginaActualConciliados = 1;
    renderizarPaginaConciliados();
};

async function cargarEstadisticas() {
    try {
        const [pendientes, conciliados] = await Promise.all([
            fetch(`${API_URL}/conciliacion/gastos-pendientes`).then(r => r.json()),
            fetch(`${API_URL}/conciliacion/conciliados`).then(r => r.json())
        ]);
        
        if (pendientes.success) {
            document.getElementById('stat-pendientes').textContent = pendientes.total;
            const totalPendiente = pendientes.gastos.reduce((sum, g) => sum + Math.abs(g.importe_eur), 0);
            document.getElementById('stat-total-pendiente').textContent = formatearImporte(totalPendiente);
        }
        
        if (conciliados.success) {
            document.getElementById('stat-conciliados').textContent = conciliados.total;
            const totalConciliado = conciliados.conciliaciones.reduce((sum, c) => sum + Math.abs(c.importe_gasto), 0);
            document.getElementById('stat-total-conciliado').textContent = formatearImporte(totalConciliado);
        }
    } catch (error) {
        console.error('Error al cargar estadísticas:', error);
    }
}

// ============================================================================
// BÚSQUEDA DE COINCIDENCIAS
// ============================================================================

window.buscarCoincidencias = async function(gastoId) {
    gastoSeleccionado = gastoId;
    coincidenciaSeleccionada = null;
    
    const modal = document.getElementById('modal-coincidencias');
    const loading = document.getElementById('loading-coincidencias');
    const container = document.getElementById('coincidencias-container');
    const gastoInfo = document.getElementById('gasto-info');
    const btnConfirmar = document.getElementById('btn-confirmar');
    
    modal.classList.add('active');
    loading.style.display = 'block';
    container.innerHTML = '';
    btnConfirmar.disabled = true;
    
    try {
        const response = await fetch(`${API_URL}/conciliacion/buscar/${gastoId}`);
        const data = await response.json();
        
        if (data.success) {
            const gasto = data.gasto;
            
            // Mostrar info del gasto
            gastoInfo.innerHTML = `
                <h3 style="margin: 0 0 10px 0;">Gasto Bancario</h3>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 10px;">
                    <div>
                        <strong>Fecha:</strong> ${formatearFecha(gasto.fecha_operacion)}
                    </div>
                    <div>
                        <strong>Concepto:</strong> ${gasto.concepto || '-'}
                    </div>
                    <div>
                        <strong>Importe:</strong> <span class="${gasto.importe_eur >= 0 ? 'importe-positivo' : 'importe-negativo'}">${formatearImporte(gasto.importe_eur)}</span>
                    </div>
                </div>
            `;
            
            // Mostrar coincidencias
            if (data.coincidencias.length > 0) {
                // Verificar si hay coincidencia exacta (diferencia = 0)
                const coincidenciaExacta = data.coincidencias.find(c => Math.abs(c.diferencia) < 0.01);
                
                if (coincidenciaExacta) {
                    // Conciliar automáticamente
                    await conciliarAutomaticamente(gastoId, coincidenciaExacta.tipo, coincidenciaExacta.id);
                    modal.classList.remove('active');
                    mostrarNotificacion(`Transferencia conciliada automáticamente con ${coincidenciaExacta.tipo.toUpperCase()} ${coincidenciaExacta.numero}`, 'success');
                    await cargarDatos();
                    return;
                }
                
                // Si no hay coincidencia exacta, intentar encontrar combinación óptima
                const objetivo = Math.abs(parseFloat(gasto.importe_eur));
                const documentos = data.coincidencias.map(c => ({
                    ...c,
                    importe: parseFloat(c.importe)
                }));
                
                const mejorCombinacion = encontrarMejorCombinacion(documentos, objetivo);
                
                // Si encontramos una combinación exacta o muy cercana (< 1€), conciliar automáticamente
                if (mejorCombinacion.length > 0) {
                    const totalCombinacion = mejorCombinacion.reduce((sum, d) => sum + d.importe, 0);
                    const diferencia = Math.abs(objetivo - totalCombinacion);
                    
                    if (diferencia < 1.0) {
                        // Conciliar automáticamente con la combinación
                        modal.classList.remove('active');
                        mostrarNotificacion(`Conciliando automáticamente con ${mejorCombinacion.length} documentos (diferencia: ${formatearImporte(diferencia)})...`, 'info');
                        
                        for (const doc of mejorCombinacion) {
                            await conciliarAutomaticamente(gastoId, doc.tipo, doc.id);
                        }
                        
                        mostrarNotificacion(`✓ Gasto conciliado con ${mejorCombinacion.length} documentos`, 'success');
                        await cargarDatos();
                        return;
                    }
                }
                
                container.innerHTML = '<h3>Coincidencias Encontradas:</h3><div class="coincidencias-list"></div>';
                const lista = container.querySelector('.coincidencias-list');
                
                data.coincidencias.forEach(coin => {
                    const div = document.createElement('div');
                    div.className = 'coincidencia-item';
                    div.dataset.tipo = coin.tipo;
                    div.dataset.id = coin.id;
                    
                    const scoreClass = coin.score >= 80 ? 'score-high' : coin.score >= 60 ? 'score-medium' : 'score-low';
                    
                    div.innerHTML = `
                        <div class="coincidencia-header">
                            <div>
                                <strong>${coin.tipo.toUpperCase()} ${coin.numero}</strong>
                            </div>
                            <div class="score-badge ${scoreClass}">
                                Score: ${coin.score}%
                            </div>
                        </div>
                        <div class="coincidencia-details">
                            <div class="detail-item">
                                <span class="detail-label">Fecha</span>
                                <span class="detail-value">${formatearFecha(coin.fecha)}</span>
                            </div>
                            <div class="detail-item">
                                <span class="detail-label">Importe</span>
                                <span class="detail-value">${formatearImporte(coin.importe)}</span>
                            </div>
                            <div class="detail-item">
                                <span class="detail-label">Diferencia</span>
                                <span class="detail-value ${coin.diferencia < 0.01 ? 'importe-positivo' : 'importe-negativo'}">
                                    ${formatearImporte(coin.diferencia)}
                                </span>
                            </div>
                        </div>
                    `;
                    
                    div.addEventListener('click', () => {
                        document.querySelectorAll('.coincidencia-item').forEach(item => {
                            item.classList.remove('selected');
                        });
                        div.classList.add('selected');
                        coincidenciaSeleccionada = {
                            tipo: coin.tipo,
                            id: coin.id
                        };
                        btnConfirmar.disabled = false;
                        
                        // Cargar PDF en el visor
                        cargarPDFEnVisor(coin.tipo, coin.id, coin.numero);
                    });
                    
                    lista.appendChild(div);
                });
            } else {
                container.innerHTML = `
                    <div class="empty-state">
                        <i class="fas fa-search"></i>
                        <p>No se encontraron coincidencias automáticas</p>
                        <p style="font-size: 12px; color: #999;">Intenta ajustar los criterios de búsqueda o concilia manualmente</p>
                    </div>
                `;
            }
        } else {
            mostrarNotificacion('Error al buscar coincidencias', 'error');
        }
    } catch (error) {
        console.error('Error:', error);
        mostrarNotificacion('Error al buscar coincidencias', 'error');
    } finally {
        loading.style.display = 'none';
    }
};

async function conciliarAutomaticamente(gastoId, tipoDocumento, documentoId) {
    try {
        const response = await fetch(`${API_URL}/conciliacion/conciliar`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                gasto_id: gastoId,
                tipo_documento: tipoDocumento,
                documento_id: documentoId,
                metodo: 'automatico'
            })
        });
        
        const data = await response.json();
        
        if (!data.success) {
            mostrarNotificacion(data.error || 'Error al conciliar automáticamente', 'error');
        }
    } catch (error) {
        console.error('Error:', error);
        mostrarNotificacion('Error al realizar conciliación automática', 'error');
    }
}

window.confirmarConciliacion = async function() {
    if (!gastoSeleccionado || !coincidenciaSeleccionada) {
        mostrarNotificacion('Selecciona una coincidencia', 'error');
        return;
    }
    
    try {
        const response = await fetch(`${API_URL}/conciliacion/conciliar`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                gasto_id: gastoSeleccionado,
                tipo_documento: coincidenciaSeleccionada.tipo,
                documento_id: coincidenciaSeleccionada.id,
                metodo: 'manual'
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            mostrarNotificacion('Conciliación realizada exitosamente', 'success');
            cerrarModal();
            cargarDatos();
        } else {
            mostrarNotificacion(data.error || 'Error al conciliar', 'error');
        }
    } catch (error) {
        console.error('Error:', error);
        mostrarNotificacion('Error al realizar conciliación', 'error');
    }
};

window.cerrarModal = function() {
    document.getElementById('modal-coincidencias').classList.remove('active');
    gastoSeleccionado = null;
    coincidenciaSeleccionada = null;
    
    // Ocultar visor de PDF
    document.getElementById('pdf-viewer').style.display = 'none';
    document.getElementById('pdf-placeholder').style.display = 'flex';
};

function cargarPDFEnVisor(tipo, id, numero) {
    const pdfViewer = document.getElementById('pdf-viewer');
    const pdfPlaceholder = document.getElementById('pdf-placeholder');
    const pdfFrame = document.getElementById('pdf-frame');
    const pdfTitle = document.getElementById('pdf-title');
    const pdfDownload = document.getElementById('pdf-download');
    
    // Construir URL del PDF según el tipo
    const tipoMayus = tipo.toUpperCase();
    let pdfUrl;
    
    if (tipo === 'factura') {
        pdfUrl = `${API_URL}/imprimir_factura_pdf/${id}`;
    } else if (tipo === 'ticket') {
        pdfUrl = `${API_URL}/imprimir_ticket_pdf/${id}`;
    } else {
        pdfUrl = `${API_URL}/imprimir_${tipo}_pdf/${id}`;
    }
    
    // Actualizar título y enlace
    pdfTitle.textContent = `${tipoMayus} ${numero}`;
    pdfDownload.href = pdfUrl;
    
    // Cargar PDF en iframe
    pdfFrame.src = pdfUrl;
    
    // Mostrar visor
    pdfViewer.style.display = 'block';
    pdfPlaceholder.style.display = 'none';
}

// ============================================================================
// ACCIONES
// ============================================================================

window.inicializarSistema = async function() {
    try {
        const response = await fetch(`${API_URL}/conciliacion/inicializar`, {
            method: 'POST'
        });
        const data = await response.json();
        
        if (data.success) {
            mostrarNotificacion('Sistema inicializado correctamente', 'success');
            cargarDatos();
        } else {
            mostrarNotificacion(data.error || 'Error al inicializar', 'error');
        }
    } catch (error) {
        console.error('Error:', error);
        mostrarNotificacion('Error al inicializar sistema', 'error');
    }
};

async function ejecutarConciliacionInicial() {
    // Ejecutar conciliación automática al cargar la página
    try {
        const response = await fetch(`${API_URL}/conciliacion/procesar-automatico`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                umbral_score: 85,
                auto_conciliar: true
            })
        });
        
        const data = await response.json();
        
        if (data.success && data.resultados.conciliados > 0) {
            const res = data.resultados;
            mostrarNotificacion(
                `Conciliación automática: ${res.conciliados} gastos conciliados`,
                'success'
            );
            cargarDatos();
        }
    } catch (error) {
        console.error('Error en conciliación inicial:', error);
    }
}

window.procesarAutomatico = async function() {
    mostrarNotificacion('Procesando conciliaciones automáticas...', 'info');
    
    try {
        const response = await fetch(`${API_URL}/conciliacion/procesar-automatico`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                umbral_score: 85,
                auto_conciliar: true
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            const res = data.resultados;
            
            let mensaje = `Procesados: ${res.procesados} | Conciliados: ${res.conciliados}`;
            if (res.sugerencias > 0) {
                mensaje += ` | Sugerencias: ${res.sugerencias}`;
            }
            mensaje += ` | Pendientes: ${res.pendientes}`;
            
            mostrarNotificacion(mensaje, 'success');
            cargarDatos();
            
            // Mostrar detalles en consola
            if (res.detalles && res.detalles.length > 0) {
                console.log('Detalles de conciliación:');
                res.detalles.forEach(d => {
                    if (d.estado === 'conciliado') {
                        console.log(`  ✓ ${d.fecha} - ${d.concepto} (${d.importe}€) → ${d.documento} [Score: ${d.score}%]`);
                    } else if (d.estado === 'sugerencia') {
                        console.log(`  ? ${d.fecha} - ${d.concepto} (${d.importe}€) → ${d.documento} [Score: ${d.score}%] (revisar manualmente)`);
                    }
                });
            }
        } else {
            mostrarNotificacion(data.error || 'Error al procesar', 'error');
        }
    } catch (error) {
        console.error('Error:', error);
        mostrarNotificacion('Error al procesar automático', 'error');
    }
};

window.eliminarConciliacion = async function(conciliacionId) {
    const confirmado = await mostrarConfirmacion('¿Está seguro de eliminar esta conciliación?');
    if (!confirmado) return;
    
    try {
        const response = await fetch(`${API_URL}/conciliacion/eliminar/${conciliacionId}`, {
            method: 'DELETE'
        });
        
        const data = await response.json();
        
        if (data.success) {
            mostrarNotificacion('Conciliación eliminada', 'success');
            cargarDatos();
        } else {
            mostrarNotificacion(data.error || 'Error al eliminar', 'error');
        }
    } catch (error) {
        console.error('Error:', error);
        mostrarNotificacion('Error al eliminar conciliación', 'error');
    }
};

// ============================================================================
// UTILIDADES
// ============================================================================

function formatearFecha(fecha) {
    if (!fecha) return '-';
    
    // Manejar formato DD/MM/YYYY o D/M/YYYY
    if (fecha.includes('/')) {
        const [dia, mes, anio] = fecha.split('/');
        // Asegurar formato DD/MM/YYYY con ceros a la izquierda
        const diaFormateado = dia.padStart(2, '0');
        const mesFormateado = mes.padStart(2, '0');
        return `${diaFormateado}/${mesFormateado}/${anio}`;
    }
    
    // Manejar formato YYYY-MM-DD
    const d = new Date(fecha + 'T00:00:00');
    return d.toLocaleDateString('es-ES');
}

function formatearImporte(importe) {
    if (importe === null || importe === undefined) return '-';
    return new Intl.NumberFormat('es-ES', {
        style: 'currency',
        currency: 'EUR'
    }).format(importe);
}

// ============================================================================
// LIQUIDACIONES TPV
// ============================================================================

async function cargarLiquidacionesTPV() {
    const loading = document.getElementById('loading-liquidaciones');
    const empty = document.getElementById('empty-liquidaciones');
    const tabla = document.getElementById('tabla-liquidaciones');
    const pagination = document.getElementById('pagination-liquidaciones');
    
    loading.style.display = 'block';
    empty.style.display = 'none';
    tabla.style.display = 'none';
    pagination.style.display = 'none';
    
    try {
        const response = await fetch(`${API_URL}/conciliacion/liquidaciones-tpv`);
        const data = await response.json();
        
        loading.style.display = 'none';
        
        if (data.success && data.liquidaciones.length > 0) {
            liquidacionesCompletas = data.liquidaciones;
            paginaActualLiquidaciones = 1;
            await renderizarPaginaLiquidaciones();
            tabla.style.display = 'table';
            pagination.style.display = 'flex';
        } else {
            empty.style.display = 'block';
        }
    } catch (error) {
        console.error('Error al cargar liquidaciones TPV:', error);
        loading.style.display = 'none';
        empty.style.display = 'block';
    }
}

async function renderizarPaginaLiquidaciones() {
    const tbody = document.getElementById('tbody-liquidaciones');
    tbody.innerHTML = '';
    
    const inicio = (paginaActualLiquidaciones - 1) * itemsPorPaginaLiquidaciones;
    const fin = inicio + itemsPorPaginaLiquidaciones;
    const liquidacionesPagina = liquidacionesCompletas.slice(inicio, fin);
    
    // Procesar liquidaciones automáticamente
    for (const liq of liquidacionesPagina) {
        const tr = document.createElement('tr');
        
        let estadoClass = '';
        let estadoTexto = '';
        let accion = '';
        
        if (liq.estado === 'exacto') {
            estadoClass = 'estado-exacto';
            estadoTexto = 'Exacto';
            // Conciliar automáticamente las exactas
            await conciliarLiquidacionAutomatica(liq);
        } else if (liq.estado === 'aceptable') {
            estadoClass = 'estado-aceptable';
            estadoTexto = 'Aceptable';
            accion = `<i class="fas fa-check-circle" onclick='confirmarConciliacionLiquidacion(${JSON.stringify(liq)})' style="cursor:pointer;color:#28a745;font-size:20px;" title="Conciliar"></i>`;
        } else {
            estadoClass = 'estado-revisar';
            estadoTexto = 'Revisar';
        }
        
        tr.innerHTML = `
            <td>${formatearFecha(liq.fecha)}</td>
            <td class="text-center">${liq.num_liquidaciones}</td>
            <td class="text-right">${formatearImporte(Math.abs(liq.total_liquidaciones))}</td>
            <td class="text-center">${liq.num_tickets}</td>
            <td class="text-center">${liq.num_facturas || 0}</td>
            <td class="text-right">${formatearImporte(liq.total_documentos)}</td>
            <td class="text-right">${formatearImporte(liq.diferencia)}</td>
            <td class="text-center"><span class="${estadoClass}">${estadoTexto}</span></td>
            ${accion ? `<td class="text-center">${accion}</td>` : ''}
        `;
        
        tbody.appendChild(tr);
    }
    
    actualizarControlesPaginacionLiquidaciones();
}

function actualizarControlesPaginacionLiquidaciones() {
    const totalPaginas = Math.ceil(liquidacionesCompletas.length / itemsPorPaginaLiquidaciones);
    document.getElementById('pageInfoLiquidaciones').textContent = `Página ${paginaActualLiquidaciones} de ${totalPaginas}`;
    document.getElementById('prevPageLiquidaciones').disabled = paginaActualLiquidaciones === 1;
    document.getElementById('nextPageLiquidaciones').disabled = paginaActualLiquidaciones === totalPaginas;
}

window.cambiarPaginaLiquidaciones = function(accion) {
    const totalPaginas = Math.ceil(liquidacionesCompletas.length / itemsPorPaginaLiquidaciones);
    if (accion === 'anterior' && paginaActualLiquidaciones > 1) paginaActualLiquidaciones--;
    if (accion === 'siguiente' && paginaActualLiquidaciones < totalPaginas) paginaActualLiquidaciones++;
    renderizarPaginaLiquidaciones();
};

window.cambiarItemsPorPaginaLiquidaciones = function() {
    itemsPorPaginaLiquidaciones = parseInt(document.getElementById('items-por-pagina-liquidaciones').value);
    paginaActualLiquidaciones = 1;
    renderizarPaginaLiquidaciones();
};

async function conciliarLiquidacionAutomatica(liq) {
    try {
        const response = await fetch(`${API_URL}/conciliacion/conciliar-liquidacion`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                ids_gastos: liq.ids_gastos,
                fecha: liq.fecha
            })
        });
        
        const result = await response.json();
        if (result.success) {
            console.log(`Liquidación ${liq.fecha} conciliada automáticamente`);
        }
    } catch (error) {
        console.error('Error al conciliar liquidación automática:', error);
    }
}

window.confirmarConciliacionLiquidacion = async function(liq) {
    const mensaje = `¿Conciliar liquidación del ${liq.fecha}? Diferencia: ${liq.diferencia}€ (${liq.porcentaje_diferencia}%)`;
    const confirmado = await mostrarConfirmacion(mensaje);
    if (!confirmado) return;
    
    try {
        const response = await fetch(`${API_URL}/conciliacion/conciliar-liquidacion`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                ids_gastos: liq.ids_gastos,
                fecha: liq.fecha
            })
        });
        
        const result = await response.json();
        if (result.success) {
            mostrarNotificacion(`Liquidación conciliada: ${result.conciliados} documentos`, 'success');
            cargarLiquidacionesTPV();
        } else {
            mostrarNotificacion(`Error: ${result.error}`, 'error');
        }
    } catch (error) {
        mostrarNotificacion(`Error al conciliar: ${error.message}`, 'error');
    }
}

// ============================================================================
// INGRESOS EFECTIVO
// ============================================================================

/**
 * Concilia automáticamente un ingreso en efectivo agrupado (versión silenciosa)
 * Solo concilia si diferencia < 1€
 */
async function conciliarIngresoAutomaticoSilencioso(ing) {
    try {
        // Cargar documentos disponibles para esa fecha
        const response = await fetch(`${API_URL}/conciliacion/documentos-efectivo?fecha=${encodeURIComponent(ing.fecha)}`);
        const data = await response.json();
        
        if (!data.success || !data.documentos || data.documentos.length === 0) {
            return false;
        }
        
        const objetivo = Math.abs(parseFloat(ing.total_ingresos));
        const documentos = data.documentos.map(d => ({
            ...d,
            importe: parseFloat(d.total)
        }));
        
        // Usar algoritmo de varita mágica para encontrar combinación exacta
        const mejorCombinacion = encontrarMejorCombinacion(documentos, objetivo);
        
        if (mejorCombinacion.length === 0) {
            return false;
        }
        
        const totalCombinacion = mejorCombinacion.reduce((sum, d) => sum + parseFloat(d.total), 0);
        const diferencia = Math.abs(objetivo - totalCombinacion);
        
        // Solo conciliar si es exacto o muy cercano (< 1€)
        if (diferencia < 1.0) {
            // Preparar datos para conciliación
            const documentosSeleccionados = mejorCombinacion.map(doc => ({
                tipo: doc.tipo,
                id: doc.id,
                numero: doc.numero,
                total: doc.total
            }));
            
            // Conciliar
            const conciliarResponse = await fetch(`${API_URL}/conciliacion/conciliar-ingreso-efectivo`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    ids_gastos: ing.ids_gastos,
                    fecha: ing.fecha,
                    documentos_seleccionados: documentosSeleccionados
                })
            });
            
            const result = await conciliarResponse.json();
            
            if (result.success) {
                const tipoMatch = diferencia < 0.01 ? 'EXACTA' : 'CERCANA';
                console.log(`✓ Ingreso agrupado ${ing.fecha} (${formatearImporte(ing.total_ingresos)}) conciliado [${tipoMatch}] con ${mejorCombinacion.length} documentos (dif: ${formatearImporte(diferencia)})`);
                return true;
            }
        } else {
            console.log(`⊗ Ingreso agrupado ${ing.fecha} (${formatearImporte(ing.total_ingresos)}) - diferencia muy alta: ${formatearImporte(diferencia)} - requiere revisión manual`);
        }
        
        return false;
    } catch (error) {
        console.error('Error en conciliación automática de ingreso agrupado:', error);
        return false;
    }
}

/**
 * Concilia automáticamente un ingreso en efectivo cuando la diferencia es 0
 */
async function conciliarIngresoAutomatico(ing) {
    try {
        // Cargar documentos disponibles para esa fecha
        const response = await fetch(`${API_URL}/conciliacion/documentos-efectivo?fecha=${encodeURIComponent(ing.fecha)}`);
        const data = await response.json();
        
        if (!data.success || !data.documentos || data.documentos.length === 0) {
            return;
        }
        
        const objetivo = Math.abs(parseFloat(ing.total_ingresos));
        const documentos = data.documentos.map(d => ({
            ...d,
            importe: parseFloat(d.total)
        }));
        
        // Usar algoritmo de varita mágica para encontrar combinación exacta
        const mejorCombinacion = encontrarMejorCombinacion(documentos, objetivo);
        
        if (mejorCombinacion.length === 0) {
            return;
        }
        
        const totalCombinacion = mejorCombinacion.reduce((sum, d) => sum + parseFloat(d.total), 0);
        const diferencia = Math.abs(objetivo - totalCombinacion);
        
        // Solo conciliar si es exacto (diferencia < 0.01€)
        if (diferencia < 0.01) {
            // Preparar datos para conciliación
            const documentosSeleccionados = mejorCombinacion.map(doc => ({
                tipo: doc.tipo,
                id: doc.id,
                numero: doc.numero,
                total: doc.total
            }));
            
            // Conciliar
            const conciliarResponse = await fetch(`${API_URL}/conciliacion/conciliar-ingreso-efectivo`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    ids_gastos: ing.ids_gastos,
                    fecha: ing.fecha,
                    documentos_seleccionados: documentosSeleccionados
                })
            });
            
            const result = await conciliarResponse.json();
            
            if (result.success) {
                console.log(`✓ Ingreso ${ing.fecha} conciliado automáticamente con ${mejorCombinacion.length} documentos`);
            }
        }
    } catch (error) {
        console.error('Error en conciliación automática de ingreso:', error);
    }
}

async function cargarIngresosEfectivo() {
    const loading = document.getElementById('loading-ingresos');
    const empty = document.getElementById('empty-ingresos');
    const tabla = document.getElementById('tabla-ingresos');
    const pagination = document.getElementById('pagination-ingresos');
    
    loading.style.display = 'block';
    empty.style.display = 'none';
    tabla.style.display = 'none';
    pagination.style.display = 'none';
    
    try {
        const response = await fetch(`${API_URL}/conciliacion/ingresos-efectivo`);
        const data = await response.json();
        
        loading.style.display = 'none';
        
        if (data.success && data.ingresos.length > 0) {
            // Procesar automáticamente ingresos con diferencia < 1€
            console.log(`Procesando automáticamente ${data.ingresos.length} ingresos en efectivo agrupados...`);
            
            for (const ing of data.ingresos) {
                const diferencia = Math.abs(ing.diferencia);
                if (diferencia < 1.0) {
                    await conciliarIngresoAutomaticoSilencioso(ing);
                }
            }
            
            // Recargar ingresos después de procesar
            const responseActualizado = await fetch(`${API_URL}/conciliacion/ingresos-efectivo`);
            const dataActualizado = await responseActualizado.json();
            
            if (dataActualizado.success && dataActualizado.ingresos.length > 0) {
                ingresosCompletos = dataActualizado.ingresos;
                paginaActualIngresos = 1;
                await renderizarPaginaIngresos();
                tabla.style.display = 'table';
                pagination.style.display = 'flex';
            } else {
                empty.style.display = 'block';
            }
        } else {
            empty.style.display = 'block';
        }
    } catch (error) {
        console.error('Error al cargar ingresos efectivo:', error);
        loading.style.display = 'none';
        empty.style.display = 'block';
    }
}

async function renderizarPaginaIngresos() {
    const tbody = document.getElementById('tbody-ingresos');
    tbody.innerHTML = '';
    
    const inicio = (paginaActualIngresos - 1) * itemsPorPaginaIngresos;
    const fin = inicio + itemsPorPaginaIngresos;
    const ingresosPagina = ingresosCompletos.slice(inicio, fin);
    
    for (const ing of ingresosPagina) {
        const tr = document.createElement('tr');
        
        let estadoClass = '';
        let estadoTexto = '';
        let accion = '';
        
        if (ing.estado === 'exacto') {
            estadoClass = 'estado-exacto';
            estadoTexto = 'Exacto';
            // Si es exacto, intentar conciliación automática
            if (Math.abs(ing.diferencia) < 0.01) {
                // Conciliar automáticamente en segundo plano
                conciliarIngresoAutomatico(ing);
                continue; // Saltar este ingreso, se conciliará automáticamente
            }
        } else {
            estadoClass = ing.estado === 'aceptable' ? 'estado-aceptable' : 'estado-revisar';
            estadoTexto = ing.estado === 'aceptable' ? 'Aceptable' : 'Revisar';
        }
        
        // Siempre mostrar botón para seleccionar documentos
        accion = `<button class="btn btn-sm" onclick='abrirSeleccionDocumentos(${JSON.stringify(ing)})' style="padding:6px 10px;font-size:14px;background:white;color:black;border:1px solid #ddd;">
            <i class="fas fa-search"></i>
        </button>`;
        
        tr.innerHTML = `
            <td>${formatearFecha(ing.fecha)}</td>
            <td class="text-center">${ing.num_ingresos}</td>
            <td class="text-right">${formatearImporte(Math.abs(ing.total_ingresos))}</td>
            <td class="text-center">${ing.num_facturas}</td>
            <td class="text-center">${ing.num_tickets}</td>
            <td class="text-right">${formatearImporte(ing.total_documentos)}</td>
            <td class="text-right">${formatearImporte(ing.diferencia)}</td>
            <td class="text-center"><span class="${estadoClass}">${estadoTexto}</span></td>
            ${accion ? `<td class="text-center">${accion}</td>` : '<td></td>'}
        `;
        
        tbody.appendChild(tr);
    }
    
    actualizarControlesPaginacionIngresos();
}

function actualizarControlesPaginacionIngresos() {
    const totalPaginas = Math.ceil(ingresosCompletos.length / itemsPorPaginaIngresos);
    document.getElementById('pageInfoIngresos').textContent = `Página ${paginaActualIngresos} de ${totalPaginas}`;
    document.getElementById('prevPageIngresos').disabled = paginaActualIngresos === 1;
    document.getElementById('nextPageIngresos').disabled = paginaActualIngresos === totalPaginas;
}

window.cambiarPaginaIngresos = function(accion) {
    const totalPaginas = Math.ceil(ingresosCompletos.length / itemsPorPaginaIngresos);
    if (accion === 'anterior' && paginaActualIngresos > 1) paginaActualIngresos--;
    if (accion === 'siguiente' && paginaActualIngresos < totalPaginas) paginaActualIngresos++;
    renderizarPaginaIngresos();
};

window.cambiarItemsPorPaginaIngresos = function() {
    itemsPorPaginaIngresos = parseInt(document.getElementById('items-por-pagina-ingresos').value);
    paginaActualIngresos = 1;
    renderizarPaginaIngresos();
};

// Variables para el modal de selección
let ingresoActual = null;
let documentosDisponibles = [];
let documentosSeleccionados = [];
let paginaActualModalDocs = 1;
let itemsPorPaginaModalDocs = 10;

window.abrirSeleccionDocumentos = async function(ing) {
    ingresoActual = ing;
    documentosSeleccionados = [];
    
    const modal = document.getElementById('modal-seleccion-documentos');
    const loading = document.getElementById('loading-documentos');
    const lista = document.getElementById('lista-documentos');
    
    // Mostrar modal y loading
    modal.classList.add('active');
    loading.style.display = 'block';
    lista.style.display = 'none';
    
    // Actualizar info del ingreso
    document.getElementById('ingreso-fecha').textContent = ing.fecha;
    document.getElementById('ingreso-importe').textContent = formatearImporte(ing.total_ingresos);
    
    try {
        // Cargar documentos disponibles
        const response = await fetch(`${API_URL}/conciliacion/documentos-efectivo?fecha=${encodeURIComponent(ing.fecha)}`);
        const data = await response.json();
        
        if (data.success) {
            documentosDisponibles = data.documentos;
            paginaActualModalDocs = 1;
            renderizarDocumentosDisponibles();
            loading.style.display = 'none';
            document.getElementById('header-documentos').style.display = 'block';
            lista.style.display = 'block';
            document.getElementById('pagination-modal-docs').style.display = 'flex';
            document.getElementById('total-documentos-disponibles').textContent = `${data.documentos.length} documentos disponibles`;
        } else {
            mostrarNotificacion('Error al cargar documentos', 'error');
            cerrarModalSeleccion();
        }
    } catch (error) {
        console.error('Error:', error);
        mostrarNotificacion('Error al cargar documentos', 'error');
        cerrarModalSeleccion();
    }
};

function renderizarDocumentosDisponibles() {
    const tbody = document.getElementById('tbody-documentos-seleccion');
    tbody.innerHTML = '';
    
    const inicio = (paginaActualModalDocs - 1) * itemsPorPaginaModalDocs;
    const fin = inicio + itemsPorPaginaModalDocs;
    const documentosPagina = documentosDisponibles.slice(inicio, fin);
    
    documentosPagina.forEach((doc, indexPagina) => {
        const indexGlobal = inicio + indexPagina;
        const tr = document.createElement('tr');
        const isSelected = documentosSeleccionados.some(d => d.tipo === doc.tipo && d.id === doc.id);
        
        tr.innerHTML = `
            <td class="text-center" style="min-width: 60px; max-width: 60px; width: 60px;">
                <input type="checkbox" 
                       id="doc-${indexGlobal}" 
                       ${isSelected ? 'checked' : ''}
                       onchange="toggleDocumento(${indexGlobal})"
                       style="cursor:pointer;width:18px;height:18px;">
            </td>
            <td style="min-width: 150px; max-width: 150px; width: 150px;"><span class="badge ${doc.tipo === 'factura' ? 'badge-info' : 'badge-secondary'}">${doc.tipo.toUpperCase()}</span></td>
            <td style="min-width: 180px; max-width: 180px; width: 180px;">${doc.numero}</td>
            <td style="min-width: 150px; max-width: 150px; width: 150px;">${formatearFecha(doc.fecha)}</td>
            <td style="min-width: 200px;">${doc.cliente || '-'}</td>
            <td class="text-right" style="min-width: 150px; max-width: 150px; width: 150px;">${formatearImporte(doc.total)}</td>
        `;
        
        tbody.appendChild(tr);
    });
    
    actualizarControlesPaginacionModalDocs();
    actualizarCheckboxSeleccionarTodos();
    actualizarTotalesSeleccion();
}

function actualizarCheckboxSeleccionarTodos() {
    const inicio = (paginaActualModalDocs - 1) * itemsPorPaginaModalDocs;
    const fin = inicio + itemsPorPaginaModalDocs;
    const documentosPagina = documentosDisponibles.slice(inicio, fin);
    
    const todosSeleccionados = documentosPagina.every(doc => 
        documentosSeleccionados.some(d => d.tipo === doc.tipo && d.id === doc.id)
    );
    
    const checkbox = document.getElementById('select-all-docs');
    if (checkbox) {
        checkbox.checked = todosSeleccionados && documentosPagina.length > 0;
    }
}

window.seleccionarTodosPagina = function() {
    const checkbox = document.getElementById('select-all-docs');
    const seleccionar = checkbox.checked;
    
    const inicio = (paginaActualModalDocs - 1) * itemsPorPaginaModalDocs;
    const fin = inicio + itemsPorPaginaModalDocs;
    const documentosPagina = documentosDisponibles.slice(inicio, fin);
    
    documentosPagina.forEach(doc => {
        const indexSeleccionado = documentosSeleccionados.findIndex(d => d.tipo === doc.tipo && d.id === doc.id);
        
        if (seleccionar && indexSeleccionado < 0) {
            // Seleccionar
            documentosSeleccionados.push(doc);
        } else if (!seleccionar && indexSeleccionado >= 0) {
            // Deseleccionar
            documentosSeleccionados.splice(indexSeleccionado, 1);
        }
    });
    
    renderizarDocumentosDisponibles();
};

window.toggleDocumento = function(index) {
    const doc = documentosDisponibles[index];
    const indexSeleccionado = documentosSeleccionados.findIndex(d => d.tipo === doc.tipo && d.id === doc.id);
    
    if (indexSeleccionado >= 0) {
        // Deseleccionar
        documentosSeleccionados.splice(indexSeleccionado, 1);
    } else {
        // Seleccionar
        documentosSeleccionados.push(doc);
    }
    
    actualizarCheckboxSeleccionarTodos();
    actualizarTotalesSeleccion();
};

function actualizarTotalesSeleccion() {
    const totalSeleccionado = documentosSeleccionados.reduce((sum, doc) => sum + doc.total, 0);
    const diferencia = Math.abs(ingresoActual.total_ingresos - totalSeleccionado);
    
    document.getElementById('docs-seleccionados-count').textContent = documentosSeleccionados.length;
    document.getElementById('total-seleccionado').textContent = formatearImporte(totalSeleccionado);
    document.getElementById('diferencia-seleccion').textContent = formatearImporte(diferencia);
    
    // Colorear diferencia
    const diffElem = document.getElementById('diferencia-seleccion');
    if (diferencia <= 1.0) {
        diffElem.style.color = '#28a745';
    } else if (diferencia <= 5.0) {
        diffElem.style.color = '#ffc107';
    } else {
        diffElem.style.color = '#dc3545';
    }
    
    // Habilitar/deshabilitar botón
    document.getElementById('btn-conciliar-seleccionados').disabled = documentosSeleccionados.length === 0;
}

function actualizarControlesPaginacionModalDocs() {
    const totalPaginas = Math.ceil(documentosDisponibles.length / itemsPorPaginaModalDocs);
    document.getElementById('pageInfoModalDocs').textContent = `Página ${paginaActualModalDocs} de ${totalPaginas}`;
    document.getElementById('prevPageModalDocs').disabled = paginaActualModalDocs === 1;
    document.getElementById('nextPageModalDocs').disabled = paginaActualModalDocs === totalPaginas;
}

window.cambiarPaginaModalDocs = function(accion) {
    const totalPaginas = Math.ceil(documentosDisponibles.length / itemsPorPaginaModalDocs);
    if (accion === 'anterior' && paginaActualModalDocs > 1) paginaActualModalDocs--;
    if (accion === 'siguiente' && paginaActualModalDocs < totalPaginas) paginaActualModalDocs++;
    renderizarDocumentosDisponibles();
};

window.cambiarItemsPorPaginaModalDocs = function() {
    itemsPorPaginaModalDocs = parseInt(document.getElementById('items-por-pagina-modal-docs').value);
    paginaActualModalDocs = 1;
    renderizarDocumentosDisponibles();
};

window.cerrarModalSeleccion = function() {
    document.getElementById('modal-seleccion-documentos').classList.remove('active');
    document.getElementById('pagination-modal-docs').style.display = 'none';
    document.getElementById('header-documentos').style.display = 'none';
    ingresoActual = null;
    documentosDisponibles = [];
    documentosSeleccionados = [];
    paginaActualModalDocs = 1;
    itemsPorPaginaModalDocs = 10;
};

window.conciliarDocumentosSeleccionados = async function() {
    if (documentosSeleccionados.length === 0) {
        mostrarNotificacion('Selecciona al menos un documento', 'warning');
        return;
    }
    
    const totalSeleccionado = documentosSeleccionados.reduce((sum, doc) => sum + doc.total, 0);
    const diferencia = Math.abs(ingresoActual.total_ingresos - totalSeleccionado);
    
    const mensaje = `¿Conciliar ingreso?\n\nIngreso: ${formatearImporte(ingresoActual.total_ingresos)}\nDocumentos: ${formatearImporte(totalSeleccionado)}\nDiferencia: ${formatearImporte(diferencia)}\n\n${documentosSeleccionados.length} documentos seleccionados`;
    const confirmado = await mostrarConfirmacion(mensaje);
    if (!confirmado) return;
    
    try {
        const response = await fetch(`${API_URL}/conciliacion/conciliar-ingreso-efectivo`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                ids_gastos: ingresoActual.ids_gastos,
                fecha: ingresoActual.fecha,
                documentos_seleccionados: documentosSeleccionados
            })
        });
        
        const result = await response.json();
        if (result.success) {
            mostrarNotificacion(`Ingreso conciliado: ${result.conciliados} registros`, 'success');
            cerrarModalSeleccion();
            cargarIngresosEfectivo();
            cargarConciliados();
        } else {
            mostrarNotificacion(`Error: ${result.error}`, 'error');
        }
    } catch (error) {
        mostrarNotificacion(`Error al conciliar: ${error.message}`, 'error');
    }
};

/**
 * Conciliación automática: selecciona documentos que sumen exactamente
 * o se acerquen lo máximo posible al total del ingreso y ejecuta la conciliación
 * Solo concilia si la diferencia es < 1€
 */
window.conciliacionAutomatica = async function() {
    if (!ingresoActual || !documentosDisponibles || documentosDisponibles.length === 0) {
        mostrarNotificacion('No hay documentos disponibles para conciliar', 'warning');
        return;
    }
    
    const objetivo = parseFloat(ingresoActual.total_ingresos);
    const documentos = documentosDisponibles.map(d => ({
        ...d,
        importe: parseFloat(d.total)
    }));
    
    // Algoritmo de mochila (subset sum problem)
    // Busca la combinación de documentos que más se acerque al objetivo
    const mejorCombinacion = encontrarMejorCombinacion(documentos, objetivo);
    
    if (mejorCombinacion.length === 0) {
        mostrarNotificacion('No se encontró ninguna combinación válida', 'warning');
        return;
    }
    
    // Limpiar selección actual
    documentosSeleccionados = [];
    
    // Seleccionar los documentos de la mejor combinación
    mejorCombinacion.forEach(doc => {
        documentosSeleccionados.push(doc);
    });
    
    // Actualizar UI
    renderizarDocumentosDisponibles();
    
    const totalSeleccionado = documentosSeleccionados.reduce((sum, d) => sum + parseFloat(d.total), 0);
    const diferencia = Math.abs(objetivo - totalSeleccionado);
    
    // Verificar si la diferencia es aceptable (< 1€)
    if (diferencia >= 1.0) {
        mostrarNotificacion(`⚠ Diferencia muy alta: ${formatearImporte(diferencia)}. No se puede conciliar automáticamente. Selecciona manualmente los documentos correctos.`, 'warning');
        return;
    }
    
    // Mostrar notificación de lo que se va a conciliar
    if (diferencia < 0.01) {
        mostrarNotificacion(`✓ Conciliación exacta encontrada: ${documentosSeleccionados.length} documentos (${formatearImporte(totalSeleccionado)}). Conciliando...`, 'success');
    } else {
        mostrarNotificacion(`Mejor aproximación: ${documentosSeleccionados.length} documentos (${formatearImporte(totalSeleccionado)}, diferencia: ${formatearImporte(diferencia)}). Conciliando...`, 'info');
    }
    
    // Esperar un momento para que se vea la notificación
    await new Promise(resolve => setTimeout(resolve, 500));
    
    // Ejecutar la conciliación automáticamente
    await conciliarDocumentosSeleccionados();
};

/**
 * Encuentra la mejor combinación de documentos que sume lo más cercano al objetivo
 * Usa programación dinámica para resolver el problema de la mochila
 */
function encontrarMejorCombinacion(documentos, objetivo) {
    const n = documentos.length;
    
    // Convertir importes a centavos para evitar problemas de precisión
    const objetivoCentavos = Math.round(objetivo * 100);
    const importesCentavos = documentos.map(d => Math.round(d.importe * 100));
    
    // Limitar el objetivo máximo para optimización (máximo 100000€ = 10000000 centavos)
    const maxObjetivo = Math.min(objetivoCentavos, 10000000);
    
    // dp[i][j] = true si es posible sumar exactamente j usando los primeros i documentos
    const dp = Array(n + 1).fill(null).map(() => Array(maxObjetivo + 1).fill(false));
    dp[0][0] = true;
    
    // Llenar la tabla dp
    for (let i = 1; i <= n; i++) {
        const importe = importesCentavos[i - 1];
        for (let j = 0; j <= maxObjetivo; j++) {
            // No incluir el documento i
            dp[i][j] = dp[i - 1][j];
            
            // Incluir el documento i (si cabe)
            if (j >= importe && dp[i - 1][j - importe]) {
                dp[i][j] = true;
            }
        }
    }
    
    // Encontrar la suma más cercana al objetivo
    let mejorSuma = 0;
    let menorDiferencia = objetivoCentavos;
    
    for (let j = 0; j <= maxObjetivo; j++) {
        if (dp[n][j]) {
            const diferencia = Math.abs(objetivoCentavos - j);
            if (diferencia < menorDiferencia) {
                menorDiferencia = diferencia;
                mejorSuma = j;
            }
        }
    }
    
    // Reconstruir la solución (backtracking)
    const seleccionados = [];
    let sumaActual = mejorSuma;
    
    for (let i = n; i > 0 && sumaActual > 0; i--) {
        const importe = importesCentavos[i - 1];
        
        // Si no usamos este documento, la suma sería la misma
        if (sumaActual >= importe && dp[i - 1][sumaActual - importe]) {
            seleccionados.push(documentos[i - 1]);
            sumaActual -= importe;
        }
    }
    
    return seleccionados;
}
