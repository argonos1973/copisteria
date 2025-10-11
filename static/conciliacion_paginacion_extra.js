// Funciones de paginación adicionales para Conciliación
// Añadir estas variables al inicio del archivo conciliacion_gastos.js después de las variables de paginación existentes:

/*
let transferenciasCompletas = [];
let paginaActualTransferencias = 1;
let itemsPorPaginaTransferencias = 10;

let liquidacionesCompletas = [];
let paginaActualLiquidaciones = 1;
let itemsPorPaginaLiquidaciones = 10;

let conciliadosCompletos = [];
let paginaActualConciliados = 1;
let itemsPorPaginaConciliados = 10;
*/

// ============================================================================
// PAGINACIÓN TRANSFERENCIAS
// ============================================================================

// Modificar cargarTransferencias() para usar paginación:
// 1. Añadir: const pagination = document.getElementById('pagination-transferencias');
// 2. Añadir: pagination.style.display = 'none';
// 3. Cambiar: const transferencias = ... por: transferenciasCompletas = ...
// 4. Reemplazar el forEach por: paginaActualTransferencias = 1; renderizarPaginaTransferencias();
// 5. Añadir: pagination.style.display = 'flex';

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

// ============================================================================
// PAGINACIÓN LIQUIDACIONES TPV
// ============================================================================

// Modificar cargarLiquidacionesTPV() para usar paginación similar a transferencias

function renderizarPaginaLiquidaciones() {
    const tbody = document.getElementById('tbody-liquidaciones');
    tbody.innerHTML = '';
    
    const inicio = (paginaActualLiquidaciones - 1) * itemsPorPaginaLiquidaciones;
    const fin = inicio + itemsPorPaginaLiquidaciones;
    const liquidacionesPagina = liquidacionesCompletas.slice(inicio, fin);
    
    liquidacionesPagina.forEach(liq => {
        const tr = document.createElement('tr');
        
        let estadoClass = '';
        let estadoTexto = '';
        if (liq.estado === 'exacto') {
            estadoClass = 'estado-exacto';
            estadoTexto = 'Exacto';
        } else if (liq.estado === 'aceptable') {
            estadoClass = 'estado-aceptable';
            estadoTexto = 'Aceptable';
        } else {
            estadoClass = 'estado-revisar';
            estadoTexto = 'Revisar';
        }
        
        tr.innerHTML = `
            <td>${liq.fecha}</td>
            <td class="text-center">${liq.num_liquidaciones}</td>
            <td class="text-right">${formatearImporte(liq.total_liquidaciones)}</td>
            <td class="text-center">${liq.num_tickets}</td>
            <td class="text-center">${liq.num_facturas}</td>
            <td class="text-right">${formatearImporte(liq.total_documentos)}</td>
            <td class="text-right ${liq.diferencia > 0.02 ? 'importe-negativo' : 'importe-positivo'}">
                ${formatearImporte(liq.diferencia)}
            </td>
            <td class="text-center">
                <span class="${estadoClass}">${estadoTexto}</span>
            </td>
            <td class="text-center">
                <button class="btn btn-sm btn-success" onclick="conciliarLiquidacion('${liq.ids_gastos}', '${liq.fecha}')">
                    Conciliar
                </button>
            </td>
        `;
        tbody.appendChild(tr);
    });
    
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

// ============================================================================
// PAGINACIÓN CONCILIADOS
// ============================================================================

// Modificar cargarConciliados() para usar paginación

function renderizarPaginaConciliados() {
    const tbody = document.getElementById('tbody-conciliados');
    tbody.innerHTML = '';
    
    const inicio = (paginaActualConciliados - 1) * itemsPorPaginaConciliados;
    const fin = inicio + itemsPorPaginaConciliados;
    const conciliadosPagina = conciliadosCompletos.slice(inicio, fin);
    
    conciliadosPagina.forEach(conc => {
        const tr = document.createElement('tr');
        
        // Formatear según el tipo
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
