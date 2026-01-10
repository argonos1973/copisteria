/**
 * Chat con IA local - Asistente de consultas SQL
 * Solo permite operaciones de lectura sobre la BD del usuario
 */

(function() {
    'use strict';

    const API_BASE = window.API_BASE || '';
    let currentSQL = null;
    let lastResultados = null;
    let conversationHistory = [];

    // Elementos del DOM
    const elements = {
        fab: () => document.getElementById('ia-fab'),
        modal: () => document.getElementById('ia-modal'),
        closeBtn: () => document.getElementById('ia-modal-close'),
        status: () => document.getElementById('ia-status'),
        messages: () => document.getElementById('ia-chat-messages'),
        input: () => document.getElementById('ia-chat-input'),
        sendBtn: () => document.getElementById('ia-chat-send'),
        sqlPreview: () => document.getElementById('ia-sql-preview'),
        sqlCode: () => document.getElementById('ia-sql-code'),
        executeBtn: () => document.getElementById('ia-sql-execute'),
        clearBtn: () => document.getElementById('ia-chat-clear'),
        // Modal de resultados
        resultsModal: () => document.getElementById('ia-results-modal'),
        resultsInfo: () => document.getElementById('ia-results-info'),
        resultsTable: () => document.getElementById('ia-results-table'),
        resultsClose: () => document.getElementById('ia-results-close'),
        resultsModalClose: () => document.getElementById('ia-results-modal-close'),
        resultsExport: () => document.getElementById('ia-results-export')
    };

    // Abrir/cerrar modal
    function toggleModal() {
        const modal = elements.modal();
        if (!modal) return;
        
        if (modal.style.display === 'none') {
            modal.style.display = 'flex';
            elements.input()?.focus();
        } else {
            modal.style.display = 'none';
        }
    }

    function closeModal() {
        const modal = elements.modal();
        if (modal) modal.style.display = 'none';
    }

    // Verificar estado de la IA
    async function checkIAStatus() {
        const statusEl = elements.status();
        if (!statusEl) return;

        try {
            const response = await fetch(`${API_BASE}/api/ia/status`, { credentials: 'include' });
            const data = await response.json();
            
            if (data.success && data.status === 'online') {
                statusEl.textContent = 'Online';
                statusEl.className = 'badge online';
            } else {
                statusEl.textContent = 'Offline';
                statusEl.className = 'badge offline';
            }
        } catch (e) {
            statusEl.textContent = 'Offline';
            statusEl.className = 'badge offline';
        }
    }

    // Añadir mensaje al chat
    function addMessage(text, type = 'assistant', isHtml = false) {
        const messagesEl = elements.messages();
        if (!messagesEl) return;

        const msg = document.createElement('div');
        msg.className = `ia-message ${type}`;
        if (isHtml) {
            msg.innerHTML = text;
        } else {
            msg.textContent = text;
        }
        messagesEl.appendChild(msg);
        messagesEl.scrollTop = messagesEl.scrollHeight;
    }

    // Mostrar loading
    function showLoading() {
        const messagesEl = elements.messages();
        if (!messagesEl) return;

        const loading = document.createElement('div');
        loading.className = 'ia-message assistant';
        loading.id = 'ia-loading';
        loading.innerHTML = '<span class="ia-loading"><i class="fas fa-circle-notch fa-spin"></i> Procesando...</span>';
        messagesEl.appendChild(loading);
        messagesEl.scrollTop = messagesEl.scrollHeight;
    }

    function hideLoading() {
        const loading = document.getElementById('ia-loading');
        if (loading) loading.remove();
    }

    // Mostrar SQL generado
    function showSQL(sql) {
        currentSQL = sql;
        const previewEl = elements.sqlPreview();
        const codeEl = elements.sqlCode();
        
        if (previewEl && codeEl) {
            codeEl.textContent = sql;
            previewEl.style.display = 'block';
        }
    }

    // Ocultar SQL
    function hideSQL() {
        currentSQL = null;
        const previewEl = elements.sqlPreview();
        if (previewEl) previewEl.style.display = 'none';
    }

    // Mostrar resultados en modal separada (o en chat si es 1 solo registro)
    function showResults(data) {
        lastResultados = data;
        const modalEl = elements.resultsModal();
        const tableEl = elements.resultsTable();
        const infoEl = elements.resultsInfo();

        if (!modalEl || !tableEl) return;

        if (!data.success) {
            addMessage(`Error: ${data.error}`, 'error');
            return;
        }

        if (!data.datos || data.datos.length === 0) {
            addMessage('La consulta no devolvió resultados.', 'assistant');
            return;
        }

        // Si solo hay 1 registro, mostrar directamente en el chat sin modal
        if (data.datos.length === 1) {
            const row = data.datos[0];
            let resultHtml = '<div class="ia-resultado-inline">';
            data.columnas.forEach(col => {
                const val = row[col];
                resultHtml += `<div><strong>${escapeHtml(col)}:</strong> ${escapeHtml(formatValue(val))}</div>`;
            });
            resultHtml += '</div>';
            addMessage(resultHtml, 'assistant', true);
            return;
        }

        // Múltiples registros: mostrar en modal
        // Mostrar info
        if (infoEl) {
            infoEl.innerHTML = `<strong>${data.total}</strong> registros encontrados`;
        }

        // Construir tabla
        let html = '<table><thead><tr>';
        data.columnas.forEach(col => {
            html += `<th>${escapeHtml(col)}</th>`;
        });
        html += '</tr></thead><tbody>';

        data.datos.forEach(row => {
            html += '<tr>';
            data.columnas.forEach(col => {
                const val = row[col];
                html += `<td>${escapeHtml(formatValue(val))}</td>`;
            });
            html += '</tr>';
        });
        html += '</tbody></table>';

        tableEl.innerHTML = html;
        modalEl.style.display = 'flex';
        
        addMessage(`Consulta ejecutada: ${data.total} registros.`, 'assistant');
    }

    // Cerrar modal de resultados
    function closeResultsModal() {
        const modalEl = elements.resultsModal();
        if (modalEl) modalEl.style.display = 'none';
    }

    // Variables para proceso y email pendientes
    let pendingProceso = null;
    let pendingEmail = null;

    // Mostrar confirmación de proceso
    function showProcesoConfirm(proceso) {
        pendingProceso = proceso;
        const descripciones = {
            'batchFacturasVencidas': 'Revisar facturas vencidas y enviar recordatorios',
            'batchTotalDia': 'Generar resumen del día',
            'batchScanFacturasRecibidas': 'Escanear facturas recibidas pendientes'
        };
        const desc = descripciones[proceso] || proceso;
        
        const html = `
            <div class="ia-action-confirm">
                <p><strong>Proceso:</strong> ${desc}</p>
                <div class="ia-action-buttons">
                    <button class="btn btn-success btn-small" onclick="window.iaChat.ejecutarProceso()">
                        <i class="fas fa-play"></i> Ejecutar
                    </button>
                    <button class="btn btn-secondary btn-small" onclick="window.iaChat.cancelarAccion()">
                        Cancelar
                    </button>
                </div>
            </div>
        `;
        addMessage(html, 'assistant', true);
    }

    // Mostrar confirmación de email
    function showEmailConfirm(destinatario, asunto, cuerpo) {
        pendingEmail = { destinatario, asunto, cuerpo };
        
        const html = `
            <div class="ia-action-confirm">
                <p><strong>Para:</strong> ${escapeHtml(destinatario)}</p>
                <p><strong>Asunto:</strong> ${escapeHtml(asunto)}</p>
                <p><strong>Mensaje:</strong> ${escapeHtml(cuerpo.substring(0, 100))}${cuerpo.length > 100 ? '...' : ''}</p>
                <div class="ia-action-buttons">
                    <button class="btn btn-success btn-small" onclick="window.iaChat.enviarEmail()">
                        <i class="fas fa-paper-plane"></i> Enviar
                    </button>
                    <button class="btn btn-secondary btn-small" onclick="window.iaChat.cancelarAccion()">
                        Cancelar
                    </button>
                </div>
            </div>
        `;
        addMessage(html, 'assistant', true);
    }

    // Ejecutar proceso pendiente
    async function ejecutarProceso() {
        if (!pendingProceso) return;
        
        showLoading();
        try {
            const response = await fetch(`${API_BASE}/api/ia/ejecutar-proceso`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({ proceso: pendingProceso })
            });
            
            hideLoading();
            const data = await response.json();
            
            if (data.success) {
                addMessage(`✅ ${data.mensaje}`, 'assistant');
            } else {
                addMessage(`❌ Error: ${data.error}`, 'error');
            }
        } catch (e) {
            hideLoading();
            addMessage(`❌ Error: ${e.message}`, 'error');
        }
        pendingProceso = null;
    }

    // Enviar email pendiente
    async function enviarEmail() {
        if (!pendingEmail) return;
        
        showLoading();
        try {
            const response = await fetch(`${API_BASE}/api/ia/enviar-email`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify(pendingEmail)
            });
            
            hideLoading();
            const data = await response.json();
            
            if (data.success) {
                addMessage(`✅ ${data.mensaje}`, 'assistant');
            } else {
                addMessage(`❌ Error: ${data.error}`, 'error');
            }
        } catch (e) {
            hideLoading();
            addMessage(`❌ Error: ${e.message}`, 'error');
        }
        pendingEmail = null;
    }

    // Cancelar acción pendiente
    function cancelarAccion() {
        pendingProceso = null;
        pendingEmail = null;
        pendingSchedule = null;
        pendingNewProceso = null;
        pendingGenericProceso = null;
        addMessage('Acción cancelada.', 'assistant');
    }

    // Variables para schedule y nuevo proceso
    let pendingSchedule = null;
    let pendingNewProceso = null;

    // Mostrar confirmación de schedule
    function showScheduleConfirm(proceso, cron, dias) {
        pendingSchedule = { proceso, cron, dias };
        
        const html = `
            <div class="ia-action-confirm">
                <p><strong>Programar proceso:</strong> ${escapeHtml(proceso)}</p>
                <p><strong>Expresión cron:</strong> ${escapeHtml(cron)}</p>
                ${dias ? `<p><strong>Días:</strong> ${escapeHtml(dias)}</p>` : ''}
                <div class="ia-action-buttons">
                    <button class="btn btn-success btn-small" onclick="window.iaChat.crearSchedule()">
                        <i class="fas fa-calendar-plus"></i> Programar
                    </button>
                    <button class="btn btn-secondary btn-small" onclick="window.iaChat.cancelarAccion()">
                        Cancelar
                    </button>
                </div>
            </div>
        `;
        addMessage(html, 'assistant', true);
    }

    // Mostrar confirmación de nuevo proceso
    function showNewProcesoConfirm(code, name, handler, timeout) {
        pendingNewProceso = { code, name, handler, timeout };
        
        const html = `
            <div class="ia-action-confirm">
                <p><strong>Crear proceso:</strong> ${escapeHtml(name)}</p>
                <p><strong>Código:</strong> ${escapeHtml(code)}</p>
                <p><strong>Handler:</strong> ${escapeHtml(handler)}</p>
                <p><strong>Timeout:</strong> ${timeout}s</p>
                <div class="ia-action-buttons">
                    <button class="btn btn-success btn-small" onclick="window.iaChat.crearNewProceso()">
                        <i class="fas fa-plus-circle"></i> Crear
                    </button>
                    <button class="btn btn-secondary btn-small" onclick="window.iaChat.cancelarAccion()">
                        Cancelar
                    </button>
                </div>
            </div>
        `;
        addMessage(html, 'assistant', true);
    }

    // Crear schedule
    async function crearSchedule() {
        if (!pendingSchedule) return;
        
        showLoading();
        try {
            const response = await fetch(`${API_BASE}/api/ia/crear-schedule`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify(pendingSchedule)
            });
            
            hideLoading();
            const data = await response.json();
            
            if (data.success) {
                addMessage(`✅ ${data.mensaje}`, 'assistant');
            } else {
                addMessage(`❌ Error: ${data.error}`, 'error');
            }
        } catch (e) {
            hideLoading();
            addMessage(`❌ Error: ${e.message}`, 'error');
        }
        pendingSchedule = null;
    }

    // Crear nuevo proceso
    async function crearNewProceso() {
        if (!pendingNewProceso) return;
        
        showLoading();
        try {
            const response = await fetch(`${API_BASE}/api/ia/crear-proceso`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify(pendingNewProceso)
            });
            
            hideLoading();
            const data = await response.json();
            
            if (data.success) {
                addMessage(`✅ ${data.mensaje}`, 'assistant');
            } else {
                addMessage(`❌ Error: ${data.error}`, 'error');
            }
        } catch (e) {
            hideLoading();
            addMessage(`❌ Error: ${e.message}`, 'error');
        }
        pendingNewProceso = null;
    }

    // Variable para proceso genérico
    let pendingGenericProceso = null;

    // Mostrar confirmación de proceso genérico
    function showGenericProcesoConfirm(code, name, params) {
        pendingGenericProceso = { code, name, params };
        
        const accionDesc = {
            'enviar_email': 'Enviar email',
            'ejecutar_sql': 'Ejecutar SQL y enviar resultados',
            'generar_reporte': 'Generar reporte'
        };
        
        const html = `
            <div class="ia-action-confirm">
                <p><strong>Crear proceso:</strong> ${escapeHtml(name)}</p>
                <p><strong>Código:</strong> ${escapeHtml(code)}</p>
                <p><strong>Acción:</strong> ${accionDesc[params.accion] || params.accion}</p>
                ${params.destinatarios ? `<p><strong>Destinatarios:</strong> ${params.destinatarios.join(', ')}</p>` : ''}
                ${params.sql ? `<p><strong>SQL:</strong> <code>${escapeHtml(params.sql.substring(0, 50))}...</code></p>` : ''}
                <div class="ia-action-buttons">
                    <button class="btn btn-success btn-small" onclick="window.iaChat.crearGenericProceso()">
                        <i class="fas fa-plus-circle"></i> Crear
                    </button>
                    <button class="btn btn-secondary btn-small" onclick="window.iaChat.cancelarAccion()">
                        Cancelar
                    </button>
                </div>
            </div>
        `;
        addMessage(html, 'assistant', true);
    }

    // Crear proceso genérico
    async function crearGenericProceso() {
        if (!pendingGenericProceso) return;
        
        showLoading();
        try {
            const response = await fetch(`${API_BASE}/api/ia/crear-proceso-generico`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify(pendingGenericProceso)
            });
            
            hideLoading();
            const data = await response.json();
            
            if (data.success) {
                addMessage(`✅ ${data.mensaje}`, 'assistant');
            } else {
                addMessage(`❌ Error: ${data.error}`, 'error');
            }
        } catch (e) {
            hideLoading();
            addMessage(`❌ Error: ${e.message}`, 'error');
        }
        pendingGenericProceso = null;
    }

    // Limpiar chat
    function clearChat() {
        const messagesEl = elements.messages();
        if (messagesEl) messagesEl.innerHTML = '';
        hideSQL();
        closeResultsModal();
        currentSQL = null;
        lastResultados = null;
        conversationHistory = [];
        addMessage('¡Hola! Soy tu asistente de consultas. Dime qué información necesitas.', 'assistant');
    }

    // Formatear valores para mostrar
    function formatValue(val) {
        if (val === null || val === undefined) return '';
        if (typeof val === 'number') {
            return val.toLocaleString('es-ES', { maximumFractionDigits: 2 });
        }
        return String(val);
    }

    // Escapar HTML
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // Enviar prompt a la IA
    async function sendPrompt() {
        const inputEl = elements.input();
        const sendBtn = elements.sendBtn();
        
        if (!inputEl) return;
        
        const prompt = inputEl.value.trim();
        if (!prompt) return;

        // Limpiar y mostrar mensaje del usuario
        hideSQL();
        closeResultsModal();
        addMessage(prompt, 'user');
        
        // Guardar en historial
        conversationHistory.push({ role: 'user', content: prompt });
        
        inputEl.value = '';
        
        // Deshabilitar mientras procesa
        if (sendBtn) sendBtn.disabled = true;
        showLoading();

        try {
            const response = await fetch(`${API_BASE}/api/ia/chat`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({ prompt, historial: conversationHistory })
            });

            hideLoading();

            if (!response.ok) {
                const err = await response.json();
                addMessage(`Error: ${err.error || 'Error desconocido'}`, 'error');
                return;
            }

            const data = await response.json();

            if (!data.success) {
                addMessage(`${data.error || 'No se pudo procesar la solicitud'}`, 'error');
                if (data.sql) showSQL(data.sql);
                return;
            }

            // Manejar diferentes tipos de respuesta
            if (data.tipo === 'proceso') {
                conversationHistory.push({ role: 'assistant', content: `PROCESO: ${data.proceso}` });
                showProcesoConfirm(data.proceso);
            } else if (data.tipo === 'email') {
                conversationHistory.push({ role: 'assistant', content: `EMAIL: ${data.destinatario}` });
                showEmailConfirm(data.destinatario, data.asunto, data.cuerpo);
            } else if (data.tipo === 'schedule') {
                conversationHistory.push({ role: 'assistant', content: `SCHEDULE: ${data.proceso}` });
                showScheduleConfirm(data.proceso, data.cron, data.dias);
            } else if (data.tipo === 'newproceso') {
                conversationHistory.push({ role: 'assistant', content: `NEWPROCESO: ${data.code}` });
                showNewProcesoConfirm(data.code, data.name, data.handler, data.timeout);
            } else if (data.tipo === 'genericproceso') {
                conversationHistory.push({ role: 'assistant', content: `GENERICPROCESO: ${data.code}` });
                showGenericProcesoConfirm(data.code, data.name, data.params);
            } else {
                // SQL - Auto-ejecutar sin preguntar
                conversationHistory.push({ role: 'assistant', content: `SQL: ${data.sql}` });
                currentSQL = data.sql;
                // Ejecutar automáticamente
                await autoExecuteSQL(data.sql);
            }

        } catch (e) {
            hideLoading();
            addMessage(`Error de conexión: ${e.message}`, 'error');
        } finally {
            if (sendBtn) sendBtn.disabled = false;
        }
    }

    // Auto-ejecutar SQL y mostrar en MODAL
    async function autoExecuteSQL(sql) {
        showLoading();
        try {
            const response = await fetch(`${API_BASE}/api/ia/ejecutar`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({ sql: sql })
            });
            hideLoading();
            const data = await response.json();
            showResults(data);  // Usar la función original que muestra en modal
        } catch (e) {
            hideLoading();
            addMessage(`Error ejecutando: ${e.message}`, 'error');
        }
    }

    // Ejecutar SQL (mantener para compatibilidad)
    async function executeSQL() {
        if (!currentSQL) return;

        const executeBtn = elements.executeBtn();
        if (executeBtn) executeBtn.disabled = true;

        showLoading();

        try {
            const response = await fetch(`${API_BASE}/api/ia/ejecutar`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({ sql: currentSQL })
            });

            hideLoading();

            const data = await response.json();
            showResultsInChat(data);

        } catch (e) {
            hideLoading();
            addMessage(`Error ejecutando: ${e.message}`, 'error');
        } finally {
            if (executeBtn) executeBtn.disabled = false;
        }
    }

    // Exportar a CSV
    function exportCSV() {
        if (!lastResultados || !lastResultados.datos) return;

        const { columnas, datos } = lastResultados;
        
        // Construir CSV
        let csv = columnas.join(';') + '\n';
        datos.forEach(row => {
            const values = columnas.map(col => {
                let val = row[col];
                if (val === null || val === undefined) val = '';
                if (typeof val === 'number') val = String(val).replace('.', ',');
                if (typeof val === 'string' && (val.includes(';') || val.includes('"') || val.includes('\n'))) {
                    val = '"' + val.replace(/"/g, '""') + '"';
                }
                return val;
            });
            csv += values.join(';') + '\n';
        });

        // Descargar
        const blob = new Blob(['\ufeff' + csv], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement('a');
        link.href = URL.createObjectURL(blob);
        link.download = `consulta_ia_${new Date().toISOString().slice(0,10)}.csv`;
        link.click();
    }

    // Inicializar
    function init() {
        // Verificar si estamos en la página correcta
        if (!document.getElementById('ia-fab')) return;

        // Verificar estado
        checkIAStatus();
        setInterval(checkIAStatus, 30000);

        // Event listeners - Modal
        const fab = elements.fab();
        const closeBtn = elements.closeBtn();
        
        if (fab) {
            fab.addEventListener('click', toggleModal);
        }
        
        if (closeBtn) {
            closeBtn.addEventListener('click', closeModal);
        }

        // Event listeners - Chat
        const sendBtn = elements.sendBtn();
        const inputEl = elements.input();
        const executeBtn = elements.executeBtn();

        if (sendBtn) {
            sendBtn.addEventListener('click', sendPrompt);
        }

        if (inputEl) {
            inputEl.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    sendPrompt();
                }
            });
        }

        if (executeBtn) {
            executeBtn.addEventListener('click', executeSQL);
        }

        // Event listener - Limpiar chat
        const clearBtn = elements.clearBtn();
        if (clearBtn) {
            clearBtn.addEventListener('click', clearChat);
        }

        // Event listeners - Modal de resultados
        const resultsClose = elements.resultsClose();
        const resultsModalClose = elements.resultsModalClose();
        const resultsExport = elements.resultsExport();

        if (resultsClose) {
            resultsClose.addEventListener('click', closeResultsModal);
        }
        if (resultsModalClose) {
            resultsModalClose.addEventListener('click', closeResultsModal);
        }
        if (resultsExport) {
            resultsExport.addEventListener('click', exportCSV);
        }

        // Cerrar modal al hacer clic fuera
        const resultsModal = elements.resultsModal();
        if (resultsModal) {
            resultsModal.addEventListener('click', (e) => {
                if (e.target === resultsModal) closeResultsModal();
            });
        }

        // Mensaje inicial
        addMessage('¡Hola! Soy tu asistente de consultas. Dime qué información necesitas.', 'assistant');
    }

    // Exponer funciones globalmente para botones onclick
    window.iaChat = {
        ejecutarProceso,
        enviarEmail,
        crearSchedule,
        crearNewProceso,
        crearGenericProceso,
        cancelarAccion
    };

    // Ejecutar cuando el DOM esté listo
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();
