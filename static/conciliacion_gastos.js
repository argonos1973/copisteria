// conciliacion_gastos.js
import { IP_SERVER, PORT } from './constantes.js';
import { mostrarNotificacion } from './notificaciones.js';

const API_URL = `http://${IP_SERVER}:${PORT}/api`;

let gastoSeleccionado = null;
let coincidenciaSeleccionada = null;

// Variables de paginación
let gastosPendientesCompletos = [];
let paginaActualPendientes = 1;
let itemsPorPaginaPendientes = 10;

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
        cargarConciliados(),
        cargarEstadisticas()
    ]);
}

async function cargarGastosPendientes() {
    const loading = document.getElementById('loading-pendientes');
    const empty = document.getElementById('empty-pendientes');
    const tabla = document.getElementById('tabla-pendientes');
    const pagination = document.getElementById('pagination-pendientes');
    
    loading.style.display = 'block';
    empty.style.display = 'none';
    tabla.style.display = 'none';
    pagination.style.display = 'none';
    
    try {
        const response = await fetch(`${API_URL}/conciliacion/gastos-pendientes`);
        const data = await response.json();
        
        if (data.success && data.gastos.length > 0) {
            gastosPendientesCompletos = data.gastos;
            paginaActualPendientes = 1;
            renderizarPaginaPendientes();
            tabla.style.display = 'table';
            pagination.style.display = 'flex';
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
            window.buscarCoincidencias(gasto.id);
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
    const tbody = document.getElementById('tbody-conciliados');
    
    loading.style.display = 'block';
    empty.style.display = 'none';
    tabla.style.display = 'none';
    
    try {
        const response = await fetch(`${API_URL}/conciliacion/conciliados`);
        const data = await response.json();
        
        if (data.success && data.conciliaciones.length > 0) {
            tbody.innerHTML = '';
            
            data.conciliaciones.forEach(conc => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td>${formatearFecha(conc.fecha_operacion)}</td>
                    <td>${conc.concepto_gasto || '-'}</td>
                    <td>
                        <span class="badge badge-info">
                            ${conc.tipo_documento.toUpperCase()} ${conc.numero_documento}
                        </span>
                    </td>
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
                    <td>
                        <button class="btn btn-danger" onclick="eliminarConciliacion(${conc.id})">
                            <i class="fas fa-trash"></i>
                        </button>
                    </td>
                `;
                tbody.appendChild(tr);
            });
            
            tabla.style.display = 'table';
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
    if (!confirm('¿Eliminar esta conciliación?')) {
        return;
    }
    
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
