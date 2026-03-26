(function () {
    const $ = (id) => document.getElementById(id);

    const alertBox = $('batch-alert');

    function showAlert(message, type = 'info') {
        if (typeof window.mostrarNotificacion === 'function') {
            const t = (type === 'error' || type === 'success' || type === 'warning' || type === 'info') ? type : 'info';
            window.mostrarNotificacion(message, t);
            return;
        }
        alertBox.style.display = 'block';
        alertBox.className = `batch-alert batch-alert-${type}`;
        alertBox.textContent = message;
        window.setTimeout(() => {
            alertBox.style.display = 'none';
        }, 4000);
    }

    async function confirmDialog(message, opts) {
        if (typeof window.mostrarConfirmacion === 'function') {
            return await window.mostrarConfirmacion(message, opts || {});
        }
        return window.confirm(message);
    }

    function safeJsonParse(text) {
        const t = (text || '').trim();
        if (!t) return null;
        return JSON.parse(t);
    }

    function pad2(n) {
        const x = String(n);
        return x.length === 1 ? '0' + x : x;
    }

    const SYSTEM_JOB_CODES = new Set(['batchOptimizar', 'batchReindex']);

    const JOB_DESCRIPTIONS = {
        batchfacturasVencidas: 'Marca facturas emitidas como vencidas según antigüedad y puede generar/enviar cartas de reclamación.',
        batchPol: 'Procesa ficheros CSV de Proformas (POL) y actualiza/importa datos relacionados en la base de datos.',
        batchTotalDia: 'Calcula el total del día (tickets + facturas) y envía un resumen por correo.',
        batchScanFacturasRecibidas: 'Escanea una carpeta de entrada, aplica OCR a facturas recibidas (PDF/imagen) y las registra igual que "Subir factura".',
        batchFacturasRecurrentes: 'Genera automáticamente las facturas de proveedores marcadas como recurrentes para el mes actual.',
    };

    function isSystemJob(code) {
        return SYSTEM_JOB_CODES.has((code || '').trim());
    }

    function stripBatchPrefix(name) {
        const n = String(name || '');
        return n.toLowerCase().startsWith('batch ') ? n.slice(6) : n;
    }

    function updateJobDescription(jobCode) {
        const el = $('batch-job-description');
        if (!el) return;
        const code = (jobCode || $('batch-job')?.value || '').trim();
        el.textContent = JOB_DESCRIPTIONS[code] || '';
    }

    function setBuilderVisibility() {
        const mode = $('batch-schedule-mode')?.value || 'interval';
        const isInterval = mode === 'interval';
        const isDaily = mode === 'daily';
        const isMonthly = mode === 'monthly';
        
        $('batch-interval-wrap').style.display = isInterval ? '' : 'none';
        $('batch-daily-wrap').style.display = isDaily ? '' : 'none';
        
        // Controles mensuales
        const monthlyWrap = $('batch-monthly-wrap');
        const monthlyTimeWrap = $('batch-monthly-time-wrap');
        if (monthlyWrap) monthlyWrap.style.display = isMonthly ? '' : 'none';
        if (monthlyTimeWrap) monthlyTimeWrap.style.display = isMonthly ? '' : 'none';
        
        // Días de la semana - ocultar en modo mensual
        const daysWrap = document.querySelector('.batch-inline:has(#batch-day-0)');
        if (daysWrap) daysWrap.style.display = isMonthly ? 'none' : '';

        const winEnabled = $('batch-window-enabled').checked;
        $('batch-window-wrap').style.display = (isInterval && winEnabled) ? '' : 'none';
        if (!isInterval) {
            $('batch-window-enabled').checked = false;
            $('batch-window-wrap').style.display = 'none';
        }
        
        // Ocultar franja horaria en modo mensual
        const winCheck = document.querySelector('.batch-check:has(#batch-window-enabled)');
        if (winCheck) winCheck.style.display = isMonthly ? 'none' : '';
    }

    function resetScheduleBuilderDefaults() {
        if ($('batch-schedule-mode')) $('batch-schedule-mode').value = 'interval';
        _ensureSelectHasValue($('batch-interval-min'), '15', 'Cada 15 min');
        if ($('batch-daily-time')) $('batch-daily-time').value = '02:00';
        if ($('batch-window-enabled')) $('batch-window-enabled').checked = false;
        _ensureSelectHasValue($('batch-window-start'), '9', '09');
        _ensureSelectHasValue($('batch-window-end'), '18', '18');
        setBuilderVisibility();
    }

    function isVencidasJobSelected() {
        const code = $('batch-job')?.value || '';
        return code === 'batchfacturasVencidas';
    }

    function isPolJobSelected() {
        const code = $('batch-job')?.value || '';
        return code === 'batchPol';
    }

    function isTotalDiaJobSelected() {
        const code = $('batch-job')?.value || '';
        return code === 'batchTotalDia';
    }

    function isScanFacturasRecibidasJobSelected() {
        const code = $('batch-job')?.value || '';
        return code === 'batchScanFacturasRecibidas';
    }

    function jobSupportsParams(jobCode) {
        // Todos los procesos soportan params (especialmente los genéricos creados por IA)
        return true;
    }

    function currentJobSupportsParams() {
        return jobSupportsParams($('batch-job')?.value || '');
    }

    function setParamsVisibility() {
        const wrap = $('batch-vencidas-params-wrap');
        if (wrap) {
            wrap.style.display = isVencidasJobSelected() ? '' : 'none';
        }

        const polWrap = $('batch-pol-params-wrap');
        if (polWrap) {
            polWrap.style.display = isPolJobSelected() ? '' : 'none';
        }

        const totalWrap = $('batch-totaldia-params-wrap');
        if (totalWrap) {
            totalWrap.style.display = isTotalDiaJobSelected() ? '' : 'none';
        }

        const scanWrap = $('batch-scan-zip-wrap');
        if (scanWrap) {
            scanWrap.style.display = isScanFacturasRecibidasJobSelected() ? '' : 'none';
        }
    }

    async function uploadScanZipToInbox() {
        const fileEl = $('batch-scan-zip-file');
        const statusEl = $('batch-scan-zip-status');

        if (statusEl) statusEl.textContent = '';
        const files = Array.from(fileEl?.files || []).filter((x) => x && x.name && x.name.toLowerCase().endsWith('.zip'));
        if (!files.length) {
            showAlert('Selecciona un ZIP', 'error');
            return;
        }

        const fd = new FormData();
        files.forEach((f) => fd.append('archivo', f));

        if (statusEl) statusEl.textContent = files.length > 1 ? `Subiendo ${files.length} ZIPs...` : 'Subiendo...';
        let resp;
        try {
            resp = await fetch('/api/facturas-proveedores/inbox/upload-zip', {
                method: 'POST',
                body: fd,
            });
        } catch (e) {
            if (statusEl) statusEl.textContent = '';
            throw e;
        }

        let data = null;
        try {
            data = await resp.json();
        } catch (e) {
            data = null;
        }

        if (!resp.ok || !data || !data.success) {
            const msg = (data && (data.error || data.message)) ? String(data.error || data.message) : `HTTP ${resp.status}`;
            if (statusEl) statusEl.textContent = '';
            showAlert(`Error subiendo ZIP: ${msg}`, 'error');
            return;
        }

        const inboxDir = String(data.inbox_dir || '').trim();
        const filesInfo = Array.isArray(data.files) ? data.files : null;
        const savedName = String(data.saved_name || '').trim();

        const ta = $('batch-params');
        // Siempre creamos un objeto nuevo para evitar mezclar con params antiguos
        let obj = {};

        if (inboxDir) obj.input_dir = inboxDir;
        obj.process_zip = 1;
        if (filesInfo && filesInfo.length > 1) {
            obj.process_all_zips = 1;
        } else {
            const oneName = filesInfo && filesInfo.length === 1 ? String(filesInfo[0]?.saved_name || '').trim() : savedName;
            if (oneName) obj.zip_name_contains = oneName;
        }

        if (ta) ta.value = JSON.stringify(obj, null, 2);
        if (statusEl) {
            if (filesInfo && filesInfo.length > 1) {
                statusEl.textContent = `Subidos: ${filesInfo.length} ZIPs`;
            } else {
                const oneName = filesInfo && filesInfo.length === 1 ? String(filesInfo[0]?.saved_name || '').trim() : savedName;
                statusEl.textContent = `Subido: ${oneName}`;
            }
        }
        showAlert(files.length > 1 ? 'ZIPs subidos. Ya puedes ejecutar el batch.' : 'ZIP subido. Ya puedes ejecutar el batch.', 'success');
    }

    function buildTotalDiaParamsFromUI() {
        const correo = ($('batch-totaldia-email')?.value || '').trim();
        const out = {};
        if (correo) out.correo = correo;
        return out;
    }

    function normalizeTotalDiaParams(params) {
        const out = {};
        if (params && typeof params === 'object' && !Array.isArray(params)) {
            if (params.correo) out.correo = String(params.correo).trim();
            if (params.db_path) out.db_path = String(params.db_path).trim();
        }
        if (!out.correo) {
            const ui = buildTotalDiaParamsFromUI();
            if (ui.correo) out.correo = ui.correo;
        }
        return out;
    }

    function buildVencidasParamsFromUI() {
        const diasVencer = parseInt($('batch-vencidas-dias-vencer')?.value || '15', 10);
        const diasCarta = parseInt($('batch-vencidas-dias-carta')?.value || '30', 10);
        return {
            dias_para_vencer: isNaN(diasVencer) ? 15 : Math.max(0, diasVencer),
            dias_para_carta: isNaN(diasCarta) ? 30 : Math.max(0, diasCarta),
        };
    }

    function buildPolParamsFromUI() {
        const csvBase = ($('batch-pol-csv-base')?.value || '').trim();
        const idContacto = parseInt($('batch-pol-id-contacto')?.value || '732', 10);
        const tarifaNormal = parseFloat($('batch-pol-tarifa-normal')?.value || '0.22314');
        const tarifaMate = parseFloat($('batch-pol-tarifa-mate')?.value || '0.7438');
        const iva = parseInt($('batch-pol-iva')?.value || '21', 10);

        const out = {};
        if (csvBase) out.csv_base_path = csvBase;
        if (!isNaN(idContacto)) out.id_contacto = Math.max(0, idContacto);
        if (!isNaN(tarifaNormal)) out.tarifa_normal = tarifaNormal;
        if (!isNaN(tarifaMate)) out.tarifa_mate = tarifaMate;
        if (!isNaN(iva)) out.iva = Math.max(0, iva);
        return out;
    }

    function buildScanFacturasRecibidasParamsDefault() {
        return {
            process_zip: 0,
        };
    }

    function syncParamsTextareaIfVencidas() {
        if (!currentJobSupportsParams()) return;
        if (!isVencidasJobSelected()) return;
        const ta = $('batch-params');
        if (!ta) return;
        ta.value = JSON.stringify(buildVencidasParamsFromUI(), null, 2);
    }

    function syncParamsTextareaIfPol() {
        if (!currentJobSupportsParams()) return;
        if (!isPolJobSelected()) return;
        const ta = $('batch-params');
        if (!ta) return;
        ta.value = JSON.stringify(buildPolParamsFromUI(), null, 2);
    }

    function syncParamsTextareaIfTotalDia() {
        if (!currentJobSupportsParams()) return;
        if (!isTotalDiaJobSelected()) return;
        const ta = $('batch-params');
        if (!ta) return;
        ta.value = JSON.stringify(buildTotalDiaParamsFromUI(), null, 2);
    }

    function syncParamsTextareaIfScanFacturasRecibidas() {
        if (!currentJobSupportsParams()) return;
        if (!isScanFacturasRecibidasJobSelected()) return;
        const ta = $('batch-params');
        if (!ta) return;
        // Si no hay params aún, ponemos un template mínimo para que el usuario vea qué se puede enviar
        if ((ta.value || '').trim()) return;
        ta.value = JSON.stringify(buildScanFacturasRecibidasParamsDefault(), null, 2);
    }

    function syncParamsEnabledState() {
        const enabled = currentJobSupportsParams();
        const ta = $('batch-params');
        if (ta) ta.disabled = !enabled;

        const ids = [
            'batch-vencidas-dias-vencer',
            'batch-vencidas-dias-carta',
            'batch-pol-csv-base',
            'batch-pol-id-contacto',
            'batch-pol-tarifa-normal',
            'batch-pol-tarifa-mate',
            'batch-pol-iva',
            'batch-totaldia-email',
        ];
        ids.forEach((id) => {
            const el = $(id);
            if (el) el.disabled = !enabled;
        });
    }

    function buildCronFromUI() {
        const mode = $('batch-schedule-mode')?.value || 'interval';
        if (mode === 'daily') {
            const t = ($('batch-daily-time').value || '02:00').split(':');
            const hh = parseInt(t[0], 10);
            const mm = parseInt(t[1], 10);
            const m = isNaN(mm) ? 0 : mm;
            const h = isNaN(hh) ? 2 : hh;
            return `${m} ${h} * * *`;
        }

        if (mode === 'monthly') {
            const day = parseInt($('batch-monthly-day')?.value || '1', 10);
            const t = ($('batch-monthly-time')?.value || '06:00').split(':');
            const hh = parseInt(t[0], 10);
            const mm = parseInt(t[1], 10);
            const m = isNaN(mm) ? 0 : mm;
            const h = isNaN(hh) ? 6 : hh;
            const d = isNaN(day) || day < 1 || day > 28 ? 1 : day;
            return `${m} ${h} ${d} * *`;
        }

        const intervalMin = parseInt($('batch-interval-min').value || '15', 10);
        const n = isNaN(intervalMin) || intervalMin < 1 ? 15 : intervalMin;

        const winEnabled = $('batch-window-enabled').checked;
        if (winEnabled) {
            const startH = parseInt($('batch-window-start').value || '9', 10);
            const endH = parseInt($('batch-window-end').value || '18', 10);
            const s = isNaN(startH) ? 9 : startH;
            const e = isNaN(endH) ? 18 : endH;
            return `*/${n} ${s}-${e} * * *`;
        }

        return `*/${n} * * * *`;
    }

    function buildHumanText() {
        const mode = $('batch-schedule-mode')?.value || 'interval';
        if (mode === 'daily') {
            const t = $('batch-daily-time').value || '02:00';
            return `Diario a las ${t}`;
        }

        if (mode === 'monthly') {
            const day = parseInt($('batch-monthly-day')?.value || '1', 10);
            const t = $('batch-monthly-time')?.value || '06:00';
            return `Mensual, día ${day} a las ${t}`;
        }

        const intervalMin = parseInt($('batch-interval-min').value || '15', 10);
        const n = isNaN(intervalMin) || intervalMin < 1 ? 15 : intervalMin;
        const winEnabled = $('batch-window-enabled').checked;
        if (winEnabled) {
            const s = pad2(parseInt($('batch-window-start').value || '9', 10));
            const e = pad2(parseInt($('batch-window-end').value || '18', 10));
            return `Cada ${n} min (de ${s}:00 a ${e}:59)`;
        }
        return `Cada ${n} min (todo el día)`;
    }

    function getDaysOfWeekFromUI() {
        const days = [];
        for (let i = 0; i < 7; i++) {
            const cb = $(`batch-day-${i}`);
            if (cb && cb.checked) days.push(i);
        }
        return days.length > 0 ? days.join(',') : '0,1,2,3,4,5,6';
    }

    function setDaysOfWeekInUI(daysStr) {
        const days = new Set();
        (daysStr || '0,1,2,3,4,5,6').split(',').forEach((d) => {
            const n = parseInt(d.trim(), 10);
            if (!isNaN(n) && n >= 0 && n <= 6) days.add(n);
        });
        for (let i = 0; i < 7; i++) {
            const cb = $(`batch-day-${i}`);
            if (cb) cb.checked = days.has(i);
        }
    }

    function formatDaysOfWeek(daysStr) {
        const names = ['L', 'M', 'X', 'J', 'V', 'S', 'D'];
        const days = new Set();
        (daysStr || '0,1,2,3,4,5,6').split(',').forEach((d) => {
            const n = parseInt(d.trim(), 10);
            if (!isNaN(n) && n >= 0 && n <= 6) days.add(n);
        });
        if (days.size === 7) return 'Todos';
        if (days.size === 5 && [0,1,2,3,4].every(d => days.has(d))) return 'L-V';
        return Array.from(days).sort((a,b) => a-b).map(d => names[d]).join(',');
    }

    function _ensureSelectHasValue(selectEl, value, label) {
        if (!selectEl) return;
        const v = String(value);
        const exists = Array.from(selectEl.options || []).some((o) => String(o.value) === v);
        if (!exists) {
            const opt = document.createElement('option');
            opt.value = v;
            opt.textContent = label != null ? String(label) : v;
            selectEl.appendChild(opt);
        }
        selectEl.value = v;
    }

    function _safeParseJsonObject(text) {
        const t = (text || '').trim();
        if (!t) return null;
        try {
            const obj = JSON.parse(t);
            return obj && typeof obj === 'object' && !Array.isArray(obj) ? obj : null;
        } catch (e) {
            return null;
        }
    }

    function _applyParamsObjectToUI(jobCode, obj) {
        const code = (jobCode || '').trim();
        const p = obj || {};

        if (code === 'batchfacturasVencidas') {
            if ($('batch-vencidas-dias-vencer') && p.dias_para_vencer != null) {
                $('batch-vencidas-dias-vencer').value = String(p.dias_para_vencer);
            }
            if ($('batch-vencidas-dias-carta') && p.dias_para_carta != null) {
                $('batch-vencidas-dias-carta').value = String(p.dias_para_carta);
            }
        }

        if (code === 'batchPol') {
            if ($('batch-pol-csv-base') && p.csv_base_path != null) {
                $('batch-pol-csv-base').value = String(p.csv_base_path);
            }
            if ($('batch-pol-id-contacto') && p.id_contacto != null) {
                $('batch-pol-id-contacto').value = String(p.id_contacto);
            }
            if ($('batch-pol-tarifa-normal') && p.tarifa_normal != null) {
                $('batch-pol-tarifa-normal').value = String(p.tarifa_normal);
            }
            if ($('batch-pol-tarifa-mate') && p.tarifa_mate != null) {
                $('batch-pol-tarifa-mate').value = String(p.tarifa_mate);
            }
            if ($('batch-pol-iva') && p.iva != null) {
                $('batch-pol-iva').value = String(p.iva);
            }
        }

        if (code === 'batchTotalDia') {
            const correo = (p.correo || p.email || p.to || '').toString().trim();
            if ($('batch-totaldia-email')) {
                $('batch-totaldia-email').value = correo;
            }
        }
    }

    function _applyCronExprToBuilder(cronExpr) {
        const c = String(cronExpr || '').trim();
        if (!c) return;

        // Mensual: m h d * * (día específico del mes)
        const monthly = c.match(/^\s*(\d+)\s+(\d+)\s+(\d+)\s+\*\s+\*\s*$/);
        if (monthly) {
            const mm = pad2(parseInt(monthly[1], 10) || 0);
            const hh = pad2(parseInt(monthly[2], 10) || 0);
            const day = parseInt(monthly[3], 10) || 1;
            if ($('batch-schedule-mode')) $('batch-schedule-mode').value = 'monthly';
            if ($('batch-monthly-day')) $('batch-monthly-day').value = String(day);
            if ($('batch-monthly-time')) $('batch-monthly-time').value = `${hh}:${mm}`;
            if ($('batch-window-enabled')) $('batch-window-enabled').checked = false;
            setBuilderVisibility();
            return;
        }

        // Diario: m h * * *
        const daily = c.match(/^\s*(\d+)\s+(\d+)\s+\*\s+\*\s+\*\s*$/);
        if (daily) {
            const mm = pad2(parseInt(daily[1], 10) || 0);
            const hh = pad2(parseInt(daily[2], 10) || 0);
            if ($('batch-schedule-mode')) $('batch-schedule-mode').value = 'daily';
            if ($('batch-daily-time')) $('batch-daily-time').value = `${hh}:${mm}`;
            if ($('batch-window-enabled')) $('batch-window-enabled').checked = false;
            setBuilderVisibility();
            return;
        }

        const intervalWithWindow = c.match(/^\s*\*\/(\d+)\s+(\d+)\-(\d+)\s+\*\s+\*\s+\*\s*$/);
        if (intervalWithWindow) {
            const n = parseInt(intervalWithWindow[1], 10) || 15;
            const s = parseInt(intervalWithWindow[2], 10);
            const e = parseInt(intervalWithWindow[3], 10);
            if ($('batch-schedule-mode')) $('batch-schedule-mode').value = 'interval';
            _ensureSelectHasValue($('batch-interval-min'), String(n), `Cada ${n} min`);
            if ($('batch-window-enabled')) $('batch-window-enabled').checked = true;
            _ensureSelectHasValue($('batch-window-start'), String(isNaN(s) ? 9 : s), pad2(isNaN(s) ? 9 : s));
            _ensureSelectHasValue($('batch-window-end'), String(isNaN(e) ? 18 : e), pad2(isNaN(e) ? 18 : e));
            setBuilderVisibility();
            return;
        }

        const interval = c.match(/^\s*\*\/(\d+)\s+\*\s+\*\s+\*\s+\*\s*$/);
        if (interval) {
            const n = parseInt(interval[1], 10) || 15;
            if ($('batch-schedule-mode')) $('batch-schedule-mode').value = 'interval';
            _ensureSelectHasValue($('batch-interval-min'), String(n), `Cada ${n} min`);
            if ($('batch-window-enabled')) $('batch-window-enabled').checked = false;
            setBuilderVisibility();
            return;
        }
    }

    function _buildTodayTimesPreview() {
        const mode = $('batch-schedule-mode')?.value || 'interval';
        if (mode === 'daily') {
            const t = $('batch-daily-time')?.value || '';
            return t ? `Hoy: ${t}` : '';
        }
        if (mode === 'monthly') {
            const day = $('batch-monthly-day')?.value || '1';
            const t = $('batch-monthly-time')?.value || '06:00';
            return `Día ${day} de cada mes a las ${t}`;
        }

        const intervalMin = parseInt($('batch-interval-min')?.value || '15', 10);
        const step = isNaN(intervalMin) || intervalMin < 1 ? 15 : intervalMin;
        const winEnabled = !!$('batch-window-enabled')?.checked;
        let startMin = 0;
        let endMin = 24 * 60 - 1;
        if (winEnabled) {
            const s = parseInt($('batch-window-start')?.value || '0', 10);
            const e = parseInt($('batch-window-end')?.value || '23', 10);
            const sh = isNaN(s) ? 0 : Math.max(0, Math.min(23, s));
            const eh = isNaN(e) ? 23 : Math.max(0, Math.min(23, e));
            startMin = sh * 60;
            endMin = (eh + 1) * 60 - 1;
        }

        const out = [];
        const limit = 16;
        for (let m = startMin; m <= endMin; m += step) {
            const hh = pad2(Math.floor(m / 60));
            const mm = pad2(m % 60);
            out.push(`${hh}:${mm}`);
            if (out.length >= limit) break;
        }

        if (out.length === 0) return '';

        const approxTotal = Math.floor((endMin - startMin) / step) + 1;
        const suffix = approxTotal > out.length ? ` … (+${approxTotal - out.length})` : '';
        return `Hoy: ${out.join(', ')}${suffix}`;
    }

    function refreshCronPreview() {
        const advanced = $('batch-advanced')?.checked;
        const cronInput = $('batch-cron');
        const human = $('batch-cron-human');
        if (human) human.textContent = buildHumanText();

        const timesEl = $('batch-cron-times');
        if (timesEl) {
            timesEl.textContent = _buildTodayTimesPreview();
        }

        if (!cronInput) return;

        cronInput.readOnly = !advanced;
        if (!advanced) {
            cronInput.value = buildCronFromUI();
        }
    }

    async function apiJson(url, options) {
        // Anti-cache param for GET requests
        let finalUrl = url;
        if (!options || !options.method || options.method === 'GET') {
            const sep = finalUrl.includes('?') ? '&' : '?';
            finalUrl += `${sep}_t=${Date.now()}`;
        }

        const res = await fetch(finalUrl, {
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            ...options,
        });
        const data = await res.json().catch(() => ({}));
        if (!res.ok || data.success === false) {
            const msg = data.error || `Error ${res.status}`;
            throw new Error(msg);
        }
        return data;
    }

    async function loadDefinitions() {
        const data = await apiJson('/api/batch/definitions');
        const sel = $('batch-job');
        sel.innerHTML = '';
        (data.definitions || []).forEach((d) => {
            if (isSystemJob(d.code)) return;
            const opt = document.createElement('option');
            opt.value = d.code;
            opt.textContent = stripBatchPrefix(d.name);
            sel.appendChild(opt);
        });
        updateJobDescription(sel.value);
    }

    function formatTs(v) {
        if (!v) return '';
        return String(v).replace('T', ' ').slice(0, 19);
    }

    function formatDuration(ms) {
        if (!ms) return '';
        const s = Math.round(ms / 1000);
        if (s < 60) return `${s}s`;
        const m = Math.floor(s / 60);
        const r = s % 60;
        return `${m}m ${r}s`;
    }

    async function loadSchedules() {
        const data = await apiJson('/api/batch/schedules');
        const tbody = $('batch-schedules-table').querySelector('tbody');
        tbody.innerHTML = '';

        window.__batchSchedulesCache = (data.schedules || []).slice();

        (data.schedules || []).forEach((s) => {
            if (isSystemJob(s.job_code)) return;
            const tr = document.createElement('tr');

            const enabled = s.enabled ? 'Activo' : 'Inactivo';
            tr.innerHTML = `
                <td>${stripBatchPrefix(s.job_name || s.job_code)}</td>
                <td><code>${s.cron_expr || ''}</code> <span style="color:#888;font-size:11px;">(${formatDaysOfWeek(s.days_of_week)})</span></td>
                <td>${enabled}</td>
                <td>${formatTs(s.next_run_at)}</td>
                <td class="batch-actions"></td>
            `;

            tr.style.cursor = 'pointer';
            tr.addEventListener('click', (ev) => {
                try {
                    if (ev && ev.target && ev.target.closest && ev.target.closest('.batch-actions')) return;

                    if ($('batch-job')) {
                        $('batch-job').value = s.job_code;
                        $('batch-job').dispatchEvent(new Event('change'));
                    }

                    if (s.cron_expr) {
                        _applyCronExprToBuilder(s.cron_expr);
                    }

                    setDaysOfWeekInUI(s.days_of_week);

                    const ta = $('batch-params');
                    const supports = jobSupportsParams(s.job_code);
                    if (!supports) {
                        if (ta) ta.value = '';
                    } else {
                        const obj = _safeParseJsonObject(s.params_json);
                        if (ta) ta.value = obj ? JSON.stringify(obj, null, 2) : '';
                        if (obj) {
                            _applyParamsObjectToUI(s.job_code, obj);
                        }
                    }

                    setParamsVisibility();
                    syncParamsEnabledState();
                    refreshCronPreview();
                } catch (e) {
                    // noop
                }
            });

            const actions = tr.querySelector('.batch-actions');

            const btnRun = document.createElement('button');
            btnRun.className = 'btn-icon-compact';
            btnRun.style.color = '#3498db';
            btnRun.innerHTML = '<i class="fas fa-play"></i>';
            btnRun.title = 'Ejecutar ahora';
            btnRun.addEventListener('click', async (e) => {
                if (e) e.stopPropagation();
                try {
                    let payload = null;
                    if (jobSupportsParams(s.job_code)) {
                        const rawParams = ($('batch-params')?.value || '').trim();
                        let params = null;
                        if (rawParams) {
                            try {
                                params = safeJsonParse(rawParams);
                            } catch (e) {
                                showAlert('JSON de parámetros inválido', 'error');
                                return;
                            }
                        }

                        if (params == null && s.job_code === 'batchfacturasVencidas') {
                            params = buildVencidasParamsFromUI();
                        }
                        if (params == null && s.job_code === 'batchPol') {
                            params = buildPolParamsFromUI();
                        }

                        payload = { params };
                    }

                    const r = await apiJson(`/api/batch/schedules/${s.id}/run`, {
                        method: 'POST',
                        body: payload ? JSON.stringify(payload) : '{}',
                    });
                    showAlert(`Run encolado (#${r.run_id})`, 'success');
                    await loadRuns();
                } catch (e) {
                    showAlert(e.message, 'error');
                }
            });

            const btnToggle = document.createElement('button');
            btnToggle.className = 'btn-icon-compact';
            btnToggle.style.color = s.enabled ? '#f39c12' : '#27ae60';
            btnToggle.innerHTML = s.enabled ? '<i class="fas fa-pause"></i>' : '<i class="fas fa-power-off"></i>';
            btnToggle.title = s.enabled ? 'Desactivar' : 'Activar';
            btnToggle.addEventListener('click', async () => {
                try {
                    await apiJson(`/api/batch/schedules/${s.id}`, {
                        method: 'PUT',
                        body: JSON.stringify({ enabled: !s.enabled }),
                    });
                    await loadSchedules();
                } catch (e) {
                    showAlert(e.message, 'error');
                }
            });

            const btnDelete = document.createElement('button');
            btnDelete.className = 'btn-icon-compact';
            btnDelete.style.color = '#c0392b';
            btnDelete.innerHTML = '<i class="fas fa-trash-alt"></i>';
            btnDelete.title = 'Eliminar programación';
            btnDelete.addEventListener('click', async (e) => {
                if (e) e.stopPropagation();
                
                const ok = await confirmDialog('¿Eliminar esta programación permanentemente?', {
                    textoConfirmar: 'Eliminar',
                    textoCancelar: 'Cancelar',
                    tipo: 'danger',
                    titulo: 'Confirmar eliminación'
                });
                if (!ok) return;

                try {
                    await apiJson(`/api/batch/schedules/${s.id}`, {
                        method: 'DELETE'
                    });
                    await loadSchedules();
                    showAlert('Programación eliminada', 'success');
                } catch (e) {
                    showAlert(e.message, 'error');
                }
            });

            actions.appendChild(btnRun);
            actions.appendChild(btnToggle);
            actions.appendChild(btnDelete);

            tbody.appendChild(tr);
        });
    }

    async function createSchedule() {
        const job_code = $('batch-job').value;
        const cron_expr = ($('batch-cron').value || '').trim();
        const enabled = true;

        if (isSystemJob(job_code)) {
            showAlert('No se pueden gestionar procesos del sistema desde esta pantalla', 'error');
            return;
        }

        let params = null;
        if (jobSupportsParams(job_code)) {
            const rawParams = ($('batch-params').value || '').trim();
            try {
                params = safeJsonParse(rawParams);
            } catch (e) {
                showAlert('JSON de parámetros inválido', 'error');
                return;
            }

            if (params == null && isVencidasJobSelected()) {
                params = buildVencidasParamsFromUI();
            }

            if (params == null && isPolJobSelected()) {
                params = buildPolParamsFromUI();
            }

            if (params == null && isTotalDiaJobSelected()) {
                params = buildTotalDiaParamsFromUI();
            }
        }

        if (job_code === 'batchTotalDia') {
            params = normalizeTotalDiaParams(params);
            const correo = (params && params.correo) ? String(params.correo).trim() : '';
            if (!correo) {
                showAlert('Correo requerido para Total del día', 'error');
                return;
            }
        }

        const days_of_week = getDaysOfWeekFromUI();
        const payload = { job_code, cron_expr, enabled, params, days_of_week };

        const data = await apiJson('/api/batch/schedules', {
            method: 'POST',
            body: JSON.stringify(payload),
        });

        showAlert(`Schedule creado (#${data.schedule_id})`, 'success');
        await loadSchedules();
    }

    async function runJobNow() {
        const job_code = $('batch-job').value;

        let params = null;
        if (jobSupportsParams(job_code)) {
            const rawParams = ($('batch-params').value || '').trim();
            if (rawParams) {
                try {
                    params = safeJsonParse(rawParams);
                } catch (e) {
                    showAlert('JSON de parámetros inválido', 'error');
                    return;
                }
            }

            if (params == null && isVencidasJobSelected()) {
                params = buildVencidasParamsFromUI();
            }

            if (params == null && isPolJobSelected()) {
                params = buildPolParamsFromUI();
            }

            if (params == null && isTotalDiaJobSelected()) {
                params = buildTotalDiaParamsFromUI();
            }
        }

        if (job_code === 'batchTotalDia') {
            params = normalizeTotalDiaParams(params);
            const correo = (params && params.correo) ? String(params.correo).trim() : '';
            if (!correo) {
                showAlert('Correo requerido para Total del día', 'error');
                return;
            }
        }

        const payload = { job_code, params };
        const data = await apiJson('/api/batch/run', {
            method: 'POST',
            body: JSON.stringify(payload),
        });

        showAlert(`Run encolado (#${data.run_id})`, 'success');
        await loadRuns();
        startRunPolling();
    }

    let pollInterval = null;
    let lastRuns = [];

    function hasActiveRuns() {
        return (lastRuns || []).some((r) => r && (r.status === 'queued' || r.status === 'running'));
    }

    function startRunPolling() {
        if (pollInterval) return;
        pollInterval = setInterval(async () => {
            try {
                await loadRuns();
                if (!hasActiveRuns()) {
                    stopRunPolling();
                }
            } catch (e) {
                stopRunPolling();
            }
        }, 2000);
    }

    function stopRunPolling() {
        if (!pollInterval) return;
        clearInterval(pollInterval);
        pollInterval = null;
    }

    async function showRunLogs(r) {
        if (!r || r.id == null) return;
        try {
            window.__batchSelectedRunId = r.id;
            $('logs-meta').textContent = `Run #${r.id} - ${r.status}`;
            const logs = await apiJson(`/api/batch/runs/${r.id}/logs?limit=400`);
            $('batch-logs').textContent = (logs.logs || [])
                .map((l) => `${l.ts} [${l.level}] ${l.message}`)
                .join('\n');
        } catch (e) {
            showAlert(e.message, 'error');
        }
    }

    async function loadRuns() {
        const data = await apiJson('/api/batch/runs?limit=5');
        lastRuns = data.runs || [];
        const tbody = $('batch-runs-table').querySelector('tbody');
        tbody.innerHTML = '';

        (lastRuns || []).forEach((r) => {
            const tr = document.createElement('tr');
            if (r && r.status === 'success') {
                tr.classList.add('batch-run-success');
            } else if (r && r.status === 'error') {
                tr.classList.add('batch-run-error');
            } else if (r && r.status === 'running') {
                tr.classList.add('batch-run-running');
            } else if (r && r.status === 'queued') {
                tr.classList.add('batch-run-queued');
            }
            tr.innerHTML = `
                <td>#${r.id}</td>
                <td>${r.job_name || r.job_code}</td>
                <td>${r.status}</td>
                <td>${formatTs(r.started_at)}</td>
                <td>${formatTs(r.finished_at)}</td>
                <td>${formatDuration(r.duration_ms)}</td>
            `;

            tr.style.cursor = 'pointer';
            tr.addEventListener('click', async () => {
                await showRunLogs(r);
            });
            tbody.appendChild(tr);
        });
    }

    async function init() {
        const paramsCacheByJob = {};
        let lastSelectedJobCode = null;

        try {
            await loadDefinitions();
            setParamsVisibility();
            syncParamsEnabledState();
            syncParamsTextareaIfVencidas();
            syncParamsTextareaIfPol();
            syncParamsTextareaIfTotalDia();
            syncParamsTextareaIfScanFacturasRecibidas();
            await loadSchedules();
            await loadRuns();
            if (hasActiveRuns()) startRunPolling();
        } catch (e) {
            showAlert(e.message, 'error');
        }

        // Schedule builder
        try {
            setBuilderVisibility();
            refreshCronPreview();

            $('batch-schedule-mode').addEventListener('change', () => {
                setBuilderVisibility();
                refreshCronPreview();
            });
            $('batch-interval-min').addEventListener('change', refreshCronPreview);
            $('batch-daily-time').addEventListener('change', refreshCronPreview);
            if ($('batch-monthly-day')) $('batch-monthly-day').addEventListener('change', refreshCronPreview);
            if ($('batch-monthly-time')) $('batch-monthly-time').addEventListener('change', refreshCronPreview);
            $('batch-window-enabled').addEventListener('change', () => {
                setBuilderVisibility();
                refreshCronPreview();
            });
            $('batch-window-start').addEventListener('change', refreshCronPreview);
            $('batch-window-end').addEventListener('change', refreshCronPreview);
            $('batch-advanced').addEventListener('change', () => {
                refreshCronPreview();
            });
        } catch (e) {
            // noop
        }

        try {
            $('batch-job').addEventListener('change', () => {
                try {
                    const ta = $('batch-params');
                    const prev = lastSelectedJobCode;
                    if (prev && ta) {
                        paramsCacheByJob[prev] = ta.value || '';
                    }
                } catch (e) {
                    // noop
                }

                try {
                    resetScheduleBuilderDefaults();
                } catch (e) {
                    // noop
                }

                updateJobDescription($('batch-job')?.value || '');

                setParamsVisibility();
                syncParamsEnabledState();

                try {
                    const newCode = $('batch-job')?.value || '';
                    const schedules = window.__batchSchedulesCache || [];
                    const found = schedules.find((x) => (x.job_code || '') === newCode);
                    if (found && found.cron_expr) {
                        _applyCronExprToBuilder(found.cron_expr);
                    }
                    if (found && found.days_of_week) {
                        setDaysOfWeekInUI(found.days_of_week);
                    }
                    if (found) {
                        lastSelectedJobCode = newCode;
                        const supports = jobSupportsParams(newCode);
                        const ta2 = $('batch-params');
                        if (supports) {
                            const obj = _safeParseJsonObject(found.params_json);
                            if (ta2) ta2.value = obj ? JSON.stringify(obj, null, 2) : '';
                            if (obj) _applyParamsObjectToUI(newCode, obj);
                        } else {
                            if (ta2) ta2.value = '';
                        }

                        setParamsVisibility();
                        syncParamsEnabledState();
                        refreshCronPreview();
                        return;
                    }
                } catch (e) {
                    // noop
                }

                const newCode = $('batch-job')?.value || '';
                lastSelectedJobCode = newCode;
                const supports = jobSupportsParams(newCode);
                const ta = $('batch-params');

                if (!supports) {
                    if (ta) ta.value = '';
                    syncParamsEnabledState();
                    return;
                }
                syncParamsEnabledState();

                if (ta && paramsCacheByJob[newCode] != null) {
                    ta.value = paramsCacheByJob[newCode];
                } else {
                    // Si no hay caché, limpiamos para no mezclar con params del job anterior
                    if (ta) ta.value = '';
                }

                syncParamsTextareaIfVencidas();
                syncParamsTextareaIfPol();
                syncParamsTextareaIfTotalDia();
                syncParamsTextareaIfScanFacturasRecibidas();
            });
            $('batch-vencidas-dias-vencer').addEventListener('change', syncParamsTextareaIfVencidas);
            $('batch-vencidas-dias-carta').addEventListener('change', syncParamsTextareaIfVencidas);

            $('batch-pol-csv-base').addEventListener('change', syncParamsTextareaIfPol);
            $('batch-pol-id-contacto').addEventListener('change', syncParamsTextareaIfPol);
            $('batch-pol-tarifa-normal').addEventListener('change', syncParamsTextareaIfPol);
            $('batch-pol-tarifa-mate').addEventListener('change', syncParamsTextareaIfPol);
            $('batch-pol-iva').addEventListener('change', syncParamsTextareaIfPol);

            $('batch-totaldia-email').addEventListener('change', syncParamsTextareaIfTotalDia);

        } catch (e) {
            // noop
        }

        try {
            lastSelectedJobCode = $('batch-job')?.value || null;
            if (lastSelectedJobCode && !jobSupportsParams(lastSelectedJobCode)) {
                const ta = $('batch-params');
                if (ta) ta.value = '';
                syncParamsEnabledState();
            }
        } catch (e) {
            // noop
        }

        // Al entrar, el selector ya tiene un valor, pero no se dispara el 'change' automáticamente.
        // Disparamos aquí (una vez cargados schedules y registrados listeners) para aplicar cron_expr/params.
        try {
            $('batch-job')?.dispatchEvent(new Event('change'));
        } catch (e) {
            // noop
        }

        $('batch-create').addEventListener('click', async () => {
            try {
                await createSchedule();
            } catch (e) {
                showAlert(e.message, 'error');
            }
        });

        $('batch-run-now').addEventListener('click', async () => {
            try {
                await runJobNow();
            } catch (e) {
                showAlert(e.message, 'error');
            }
        });

        try {
            $('batch-scan-zip-upload')?.addEventListener('click', async (ev) => {
                ev.preventDefault();
                try {
                    await uploadScanZipToInbox();
                } catch (e) {
                    showAlert(e.message || String(e), 'error');
                }
            });
        } catch (e) {
            // noop
        }

        // Botones de días de la semana
        try {
            $('batch-days-all')?.addEventListener('click', () => {
                for (let i = 0; i < 7; i++) {
                    const cb = $(`batch-day-${i}`);
                    if (cb) cb.checked = true;
                }
            });
            $('batch-days-weekdays')?.addEventListener('click', () => {
                for (let i = 0; i < 7; i++) {
                    const cb = $(`batch-day-${i}`);
                    if (cb) cb.checked = (i < 5); // L-V
                }
            });
        } catch (e) {
            // noop
        }

        const batchRefreshBtn = $('batch-refresh');
        if (batchRefreshBtn) {
            batchRefreshBtn.addEventListener('click', async () => {
                const btn = batchRefreshBtn;
                const originalHtml = btn.innerHTML;
                btn.disabled = true;
                btn.innerHTML = '<i class="fas fa-sync fa-spin"></i> Recargando...';
                try {
                    await loadDefinitions();
                    await loadSchedules();
                    await loadRuns();
                    if (hasActiveRuns()) startRunPolling();
                    showAlert('Recargado', 'success');
                } catch (e) {
                    showAlert(e.message, 'error');
                } finally {
                    btn.disabled = false;
                    btn.innerHTML = originalHtml;
                }
            });
        }

        const runsRefreshBtn = $('runs-refresh');
        if (runsRefreshBtn) {
            runsRefreshBtn.addEventListener('click', async () => {
                try {
                    await loadRuns();
                } catch (e) {
                    showAlert(e.message, 'error');
                }
            });
        }

        $('logs-clear').addEventListener('click', async () => {
            const confirmMsg = '¿Borrar TODO el historial de ejecuciones y sus logs de esta empresa?';

            const ok = await confirmDialog(confirmMsg, {
                textoConfirmar: 'Borrar',
                textoCancelar: 'Cancelar',
                tipo: 'danger',
                titulo: 'Confirmación',
            });
            if (!ok) return;

            try {
                await apiJson('/api/batch/runs', { method: 'DELETE' });
                lastRuns = [];
                try {
                    const tbody = $('batch-runs-table')?.querySelector('tbody');
                    if (tbody) tbody.innerHTML = '';
                } catch (e) {
                    // noop
                }
                try {
                    stopRunPolling();
                } catch (e) {
                    // noop
                }
                showAlert('Historial eliminado', 'success');
            } catch (e) {
                showAlert(e.message, 'error');
            } finally {
                $('batch-logs').textContent = '';
                $('logs-meta').textContent = '';
                window.__batchSelectedRunId = null;
                try {
                    await loadRuns();
                } catch (e) {
                    // noop
                }
            }
        });
    }

    document.addEventListener('DOMContentLoaded', init);
})();
