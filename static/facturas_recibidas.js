/**
 * facturas_recibidas.js
 * Gestión de facturas recibidas de proveedores
 */

import { mostrarNotificacion } from './notificaciones.js';
import { formatearImporte } from './scripts_utils.js';

// Variables globales
let paginaActual = 1;
let porPagina = parseInt(sessionStorage.getItem('facturas_por_pagina')) || 10;
let totalPaginas = 1;
let proveedores = [];
let filtrosActuales = {};
let timeoutBusqueda = null;
let facturasCache = [];

let __nuevaFacturaPreviewBlobUrl = null;

function _revokeNuevaFacturaPreviewBlobUrl() {
    try {
        if (__nuevaFacturaPreviewBlobUrl) {
            URL.revokeObjectURL(__nuevaFacturaPreviewBlobUrl);
        }
    } catch (_) {}
    __nuevaFacturaPreviewBlobUrl = null;
}

function _renderNuevaFacturaPreview(preview) {
    let url = '';
    let mime = '';
    if (preview && typeof preview === 'object') {
        url = String(preview.url || preview.preview_url || '');
        mime = String(preview.mime || preview.type || '');
    } else {
        url = String(preview || '');
    }
    if (!url) return;

    // Opción A: la vista previa se muestra en el panel derecho.
    // Si está colapsado, se expande automáticamente para que el usuario vea el preview.
    try {
        const right = document.getElementById('nuevaFacturaRightCol');
        const isCollapsed = !right || right.style.display === 'none';
        if (isCollapsed && typeof window._setPanelNuevaFacturaCollapsed === 'function') {
            window._setPanelNuevaFacturaCollapsed(false);
        }
    } catch (_) {}

    const container = document.getElementById('nuevaFacturaPreviewContainer');
    const body = document.getElementById('nuevaFacturaPreviewBody');
    if (!container || !body) return;

    body.innerHTML = '';

    const lower = url.toLowerCase();
    const isPdf = (mime && mime.toLowerCase().includes('pdf')) || lower.includes('.pdf');
    if (isPdf) {
        const embed = document.createElement('embed');
        embed.src = url;
        embed.type = 'application/pdf';
        embed.style.width = '100%';
        embed.style.height = '100%';
        embed.style.border = '0';
        body.appendChild(embed);
    } else {
        const img = document.createElement('img');
        img.src = url;
        img.alt = 'Vista previa factura';
        img.style.width = '100%';
        img.style.height = '100%';
        img.style.objectFit = 'contain';
        img.style.display = 'block';
        body.appendChild(img);
    }

    container.style.display = 'block';
}

function _hideNuevaFacturaPreview() {
    _revokeNuevaFacturaPreviewBlobUrl();
    const containerRight = document.getElementById('nuevaFacturaPreviewContainer');
    const bodyRight = document.getElementById('nuevaFacturaPreviewBody');
    if (bodyRight) bodyRight.innerHTML = '';
    if (containerRight) containerRight.style.display = 'none';
}

window._setPanelNuevaFacturaCollapsed = function(collapsed) {
    const left = document.getElementById('nuevaFacturaLeftCol');
    const right = document.getElementById('nuevaFacturaRightCol');
    const icon = document.getElementById('btnToggleNuevaFacturaPanelIcon');

    if (!left || !right) return;

    if (collapsed) {
        right.style.display = 'none';
        left.style.width = '100%';
        left.style.flex = '1 1 auto';
        if (icon) icon.textContent = '⟩';
    } else {
        right.style.display = 'flex';
        left.style.width = '68%';
        left.style.flex = '0 0 68%';
        if (icon) icon.textContent = '⟨';
    }

    // Persistencia suave en sesión
    try {
        sessionStorage.setItem('facturas_recibidas_nueva_panel_collapsed', collapsed ? '1' : '0');
    } catch (_) {}
};

window.togglePanelNuevaFactura = function() {
    const right = document.getElementById('nuevaFacturaRightCol');
    const isCollapsed = !right || right.style.display === 'none';
    window._setPanelNuevaFacturaCollapsed(!isCollapsed);
};

// ============================================================================
// INICIALIZACIÓN
// ============================================================================

document.addEventListener('DOMContentLoaded', () => {
    console.log('[Facturas Recibidas] Inicializando...');
    
    // Restaurar valor del selector de registros por página
    const perPageSelect = document.getElementById('perPage');
    if (perPageSelect) {
        perPageSelect.value = porPagina;
    }
    
    // Establecer fechas del trimestre actual (no necesario, el select ya tiene 'actual' seleccionado por defecto)
    // Llenar selector de años
    llenarSelectorAnios();
    
    // Cargar proveedores para el filtro
    cargarProveedores();
    
    // Cargar facturas
    cargarFacturas();
    
    // Event listeners
    configurarEventListeners();

    try {
        const params = new URLSearchParams(window.location.search || '');
        const shouldOpen = params.get('nueva') === '1' || window.location.hash === '#nueva';
        if (shouldOpen) {
            setTimeout(() => abrirNuevaFactura(), 200);
            params.delete('nueva');
            const newQuery = params.toString();
            const newUrl = window.location.pathname + (newQuery ? `?${newQuery}` : '') + '';
            window.history.replaceState({}, '', newUrl);
        }
    } catch (_) {}
});

function configurarEventListeners() {
    // Búsqueda interactiva en todos los filtros con debounce
    const filtros = ['proveedorFilter', 'trimestreFilter', 'anioFilter', 'busquedaFilter'];
    filtros.forEach(filtroId => {
        const elemento = document.getElementById(filtroId);
        if (elemento) {
            // Para selects: change event
            elemento.addEventListener('change', (e) => {
                // Mostrar/ocultar selector de año si es necesario
                if (e.target.id === 'trimestreFilter') {
                    toggleSelectorAnio(e.target.value);
                }
                busquedaInteractiva(e);
            });
            
            // Para campo de texto: input event (mientras escribe)
            if (filtroId === 'busquedaFilter') {
                elemento.addEventListener('input', (e) => busquedaInteractiva(e));
            }
        }
    });
    
    // Paginación
    document.getElementById('prevPage').addEventListener('click', () => cambiarPagina(-1));
    document.getElementById('nextPage').addEventListener('click', () => cambiarPagina(1));
    
    document.getElementById('perPage').addEventListener('change', (e) => {
        porPagina = parseInt(e.target.value);
        sessionStorage.setItem('facturas_por_pagina', porPagina);
        paginaActual = 1;
        cargarFacturas();
    });

    const btnNueva = document.getElementById('btnNuevaFactura');
    if (btnNueva) {
        btnNueva.addEventListener('click', () => {
            abrirNuevaFactura();
        });
    }
}

function waitForElement(id, timeoutMs = 5000) {
    return new Promise((resolve, reject) => {
        const start = Date.now();
        const tick = () => {
            const el = document.getElementById(id);
            if (el) return resolve(el);
            if (Date.now() - start > timeoutMs) return reject(new Error(`No se encontró #${id}`));
            setTimeout(tick, 100);
        };
        tick();
    });
}

async function abrirNuevaFactura() {
    try {
        await waitForElement('modalNuevaFactura', 6000);

        try {
            if (typeof window._ensureNuevaFacturaArchivoBlock === 'function') {
                window._ensureNuevaFacturaArchivoBlock();
            }
        } catch (_) {}

        try { _hideNuevaFacturaPreview(); } catch (_) {}

        // Fecha por defecto
        const hoy = new Date().toISOString().split('T')[0];
        const fechaEmisionEl = document.getElementById('nueva-fecha-emision');
        if (fechaEmisionEl) fechaEmisionEl.value = hoy;

        // Reset form
        const form = document.getElementById('formNuevaFactura');
        if (form) form.reset();
        if (fechaEmisionEl) fechaEmisionEl.value = hoy;

        const ocrEstado = document.getElementById('nueva-ocr-estado');
        if (ocrEstado) ocrEstado.textContent = '';
        const fileEl = document.getElementById('nueva-archivo');
        if (fileEl) {
            fileEl.value = '';
            fileEl.onchange = () => {
                const hasFile = !!fileEl?.files?.[0];
                if (!hasFile) {
                    try { _hideNuevaFacturaPreview(); } catch (_) {}
                    return;
                }

                try {
                    const f = fileEl.files[0];
                    try {
                        if (typeof window._setPanelNuevaFacturaCollapsed === 'function') {
                            window._setPanelNuevaFacturaCollapsed(false);
                        }
                    } catch (_) {}
                    _revokeNuevaFacturaPreviewBlobUrl();
                    __nuevaFacturaPreviewBlobUrl = URL.createObjectURL(f);
                    _renderNuevaFacturaPreview({ url: __nuevaFacturaPreviewBlobUrl, mime: f.type });
                } catch (_) {}
            };
        }

        // Panel derecho: colapsado por defecto (si el usuario lo expandió antes, se respeta)
        try {
            if (typeof window._setPanelNuevaFacturaCollapsed === 'function') {
                let initialCollapsed = true;
                try {
                    const stored = sessionStorage.getItem('facturas_recibidas_nueva_panel_collapsed');
                    if (stored !== null) initialCollapsed = stored === '1';
                } catch (_) {}
                window._setPanelNuevaFacturaCollapsed(initialCollapsed);
            }
        } catch (_) {}

        // Default IVA
        const ivaPct = document.getElementById('nueva-iva-porcentaje');
        if (ivaPct && !ivaPct.value) ivaPct.value = '21';

        // Modo proveedor por defecto
        const provExistBlock = document.getElementById('proveedorExistenteBlock');
        const provManualBlock = document.getElementById('proveedorManualBlock');
        if (provExistBlock) provExistBlock.style.display = 'block';
        if (provManualBlock) provManualBlock.style.display = 'none';
        const radioExist = document.querySelector('input[name="proveedorModo"][value="existente"]');
        if (radioExist) radioExist.checked = true;

        // Rellenar proveedores en select
        await cargarProveedoresParaModalNueva();

        // Toggle proveedor modo
        const radios = Array.from(document.querySelectorAll('input[name="proveedorModo"]'));
        radios.forEach(r => {
            r.onchange = () => {
                const modo = document.querySelector('input[name="proveedorModo"]:checked')?.value;
                if (provExistBlock) provExistBlock.style.display = (modo === 'existente') ? 'block' : 'none';
                if (provManualBlock) provManualBlock.style.display = (modo === 'manual') ? 'block' : 'none';
            };
        });

        // Calcular importes
        const baseInput = document.getElementById('nueva-base');
        const ivaInput = document.getElementById('nueva-iva-porcentaje');
        const calcular = () => {
            const base = parseFloat(baseInput?.value) || 0;
            const ivaPorcentaje = parseFloat(ivaInput?.value) || 0;
            const ivaImporte = base * (ivaPorcentaje / 100);
            const total = base + ivaImporte;
            const ivaImpEl = document.getElementById('nueva-iva-importe');
            const totalEl = document.getElementById('nueva-total');
            if (ivaImpEl) ivaImpEl.value = ivaImporte.toFixed(2);
            if (totalEl) totalEl.value = total.toFixed(2);
        };
        if (baseInput) baseInput.oninput = calcular;
        if (ivaInput) ivaInput.oninput = calcular;
        calcular();

        // Adjuntar CP validator (manual proveedor)
        try {
            if (window.CpValidator && typeof window.CpValidator.attachToInput === 'function') {
                const cpEl = document.getElementById('nueva-prov-cp');
                if (cpEl) {
                    window.CpValidator.attachToInput(cpEl, {
                        localityId: 'nueva-prov-poblacion',
                        provinceId: 'nueva-prov-provincia',
                        noSubmitBlock: true
                    });
                }
            }
        } catch (_) {}

        abrirModal('modalNuevaFactura');
    } catch (err) {
        console.error('[Facturas] Error abriendo modal nueva:', err);
        mostrarNotificacion('No se pudo abrir el formulario de nueva factura', 'error');
    }
}

window._ensureNuevaFacturaArchivoBlock = function() {
    if (document.getElementById('nueva-archivo')) return;

    const modal = document.getElementById('modalNuevaFactura');
    if (!modal) return;

    const form = document.getElementById('formNuevaFactura') || modal.querySelector('form') || null;
    const anchor = document.getElementById('proveedorManualBlock') ||
        document.getElementById('proveedorExistenteBlock') ||
        document.getElementById('nueva-proveedor') ||
        (form ? form.querySelector('#nueva-proveedor') : null);

    if (!form || !anchor) {
        try {
            if (!window.__reloading_modales_facturas_recibidas__) {
                window.__reloading_modales_facturas_recibidas__ = true;
                const container = document.getElementById('modales-container');
                if (container) {
                    fetch('/MODALES_FACTURAS_RECIBIDAS.html?cb=' + Date.now())
                        .then(r => r.text())
                        .then(html => {
                            container.innerHTML = html;
                            window.__reloading_modales_facturas_recibidas__ = false;
                            setTimeout(() => {
                                try { window._ensureNuevaFacturaArchivoBlock(); } catch (_) {}
                            }, 50);
                        })
                        .catch(() => { window.__reloading_modales_facturas_recibidas__ = false; });
                } else {
                    window.__reloading_modales_facturas_recibidas__ = false;
                }
            }
        } catch (_) {
            window.__reloading_modales_facturas_recibidas__ = false;
        }
        return;
    }

    const wrapper = document.createElement('div');
    wrapper.className = 'form-group';
    wrapper.style.marginTop = '10px';
    wrapper.innerHTML = `
        <label for="nueva-archivo" style="display:block;font-weight:bold;margin-bottom:5px;">Archivo (PDF/Imagen) (opcional)</label>
        <input type="file" id="nueva-archivo" class="form-control" accept=".pdf,.png,.jpg,.jpeg,.webp" />
        <div style="display:flex; gap:10px; margin-top:10px; align-items:center; flex-wrap:wrap;">
            <button type="button" class="btn btn-modal-primary" id="btnOcrNuevaFactura">
                <i class="fas fa-magic"></i> Escanear con IA
            </button>
            <span id="nueva-ocr-estado" style="font-size: 12px; opacity: 0.9;"></span>
        </div>
        <small>Si escaneas, se rellenarán automáticamente proveedor y datos de la factura (usa GPT-4 Vision).</small>
    `.trim();

    if (anchor && anchor.insertAdjacentElement) {
        anchor.insertAdjacentElement('afterend', wrapper);
    } else if (form && form.appendChild) {
        form.appendChild(wrapper);
    }

    const btn = document.getElementById('btnOcrNuevaFactura');
    if (btn) {
        btn.onclick = () => {
            if (typeof window.escanearNuevaFacturaOCR === 'function') {
                window.escanearNuevaFacturaOCR();
            }
        };
    }
};

function _setOcrEstado(texto) {
    const el = document.getElementById('nueva-ocr-estado');
    if (el) el.textContent = texto || '';
}

function _normalizarNumero(v) {
    if (v === null || v === undefined) return '';
    const s = String(v).replace(',', '.').trim();
    return s;
}

function _toFloatOrZero(v) {
    const n = parseFloat(_normalizarNumero(v));
    return isFinite(n) ? n : 0;
}

function _buscarProveedorExistenteId(datosProveedor) {
    if (!datosProveedor) return null;
    const nif = (datosProveedor.nif || '').toUpperCase().replace(/[-\s]/g, '').trim();
    const nombre = (datosProveedor.nombre || '').toUpperCase().trim();

    if (Array.isArray(proveedores) && proveedores.length) {
        if (nif) {
            const matchNif = proveedores.find(p => (p.nif || '').toUpperCase().replace(/[-\s]/g, '').trim() === nif);
            if (matchNif) return matchNif.id;
        }
        if (nombre) {
            const matchNombre = proveedores.find(p => (p.nombre || '').toUpperCase().trim() === nombre);
            if (matchNombre) return matchNombre.id;
        }
    }
    return null;
}

function _rellenarProveedorEnModal(datosProveedor) {
    const prov = datosProveedor || {};
    const existenteId = _buscarProveedorExistenteId(prov);

    if (existenteId) {
        const radioExist = document.querySelector('input[name="proveedorModo"][value="existente"]');
        if (radioExist) radioExist.checked = true;
        const provExistBlock = document.getElementById('proveedorExistenteBlock');
        const provManualBlock = document.getElementById('proveedorManualBlock');
        if (provExistBlock) provExistBlock.style.display = 'block';
        if (provManualBlock) provManualBlock.style.display = 'none';
        const select = document.getElementById('nueva-proveedor');
        if (select) select.value = String(existenteId);
        return;
    }

    const radioManual = document.querySelector('input[name="proveedorModo"][value="manual"]');
    if (radioManual) radioManual.checked = true;
    const provExistBlock = document.getElementById('proveedorExistenteBlock');
    const provManualBlock = document.getElementById('proveedorManualBlock');
    if (provExistBlock) provExistBlock.style.display = 'none';
    if (provManualBlock) provManualBlock.style.display = 'block';

    const setVal = (id, val) => {
        const el = document.getElementById(id);
        if (el) el.value = (val || '').toString();
    };

    setVal('nueva-prov-nombre', (prov.nombre || '').toString().toUpperCase());
    setVal('nueva-prov-nif', (prov.nif || '').toString().toUpperCase());
    setVal('nueva-prov-direccion', prov.direccion || '');
    setVal('nueva-prov-email', prov.email || '');
    setVal('nueva-prov-telefono', prov.telefono || '');
}

function _rellenarFacturaEnModal(datosFactura) {
    const f = datosFactura || {};

    const setVal = (id, val) => {
        const el = document.getElementById(id);
        if (el && val !== undefined && val !== null) el.value = String(val);
    };

    setVal('nueva-numero', f.numero || '');
    setVal('nueva-fecha-emision', f.fecha_emision || '');
    setVal('nueva-fecha-vencimiento', f.fecha_vencimiento || '');
    setVal('nueva-concepto', f.concepto || '');

    const base = _toFloatOrZero(f.base_imponible);
    const ivaImporte = _toFloatOrZero(f.iva);
    const total = _toFloatOrZero(f.total);
    const ivaPct = base > 0 ? (ivaImporte / base) * 100 : (parseFloat(document.getElementById('nueva-iva-porcentaje')?.value || '0') || 0);

    setVal('nueva-base', base ? base.toFixed(2) : '0.00');
    setVal('nueva-iva-porcentaje', isFinite(ivaPct) ? Math.round(ivaPct).toString() : '0');
    setVal('nueva-iva-importe', ivaImporte ? ivaImporte.toFixed(2) : '0.00');
    setVal('nueva-total', total ? total.toFixed(2) : (base + ivaImporte).toFixed(2));
}

window.escanearNuevaFacturaOCR = async function() {
    try {
        const fileEl = document.getElementById('nueva-archivo');
        const archivo = fileEl?.files?.[0];
        if (!archivo) {
            try { _hideNuevaFacturaPreview(); } catch (_) {}
            mostrarNotificacion('Selecciona un archivo (PDF o imagen) para escanear', 'error');
            return;
        }

        _setOcrEstado('Escaneando con IA...');

        const formData = new FormData();
        formData.append('archivo', archivo);

        const response = await fetch('/api/facturas-proveedores/ocr', {
            method: 'POST',
            body: formData
        });

        const contentType = response.headers.get('content-type');
        if (contentType && contentType.includes('text/html')) {
            throw new Error('Sesión expirada. Recarga la página e inicia sesión de nuevo.');
        }

        const data = await response.json();
        if (!response.ok || !data.success) {
            throw new Error(data.error || 'Error en OCR');
        }

        await cargarProveedores();

        const datos = data.datos || {};
        _rellenarProveedorEnModal(datos.proveedor || {});
        _rellenarFacturaEnModal(datos.factura || {});

        try {
            if (data.preview_url) {
                _renderNuevaFacturaPreview(data.preview_url);
            } else {
                _hideNuevaFacturaPreview();
            }
        } catch (_) {}

        _setOcrEstado('✅ OCR completado. Revisa y ajusta antes de guardar.');
        mostrarNotificacion('OCR completado. Revisa los datos antes de guardar.', 'success');
    } catch (err) {
        console.error('[Facturas] Error OCR nueva factura:', err);
        try { _hideNuevaFacturaPreview(); } catch (_) {}
        _setOcrEstado('❌ Error en OCR');
        mostrarNotificacion('Error en OCR: ' + (err.message || err), 'error');
    }
};

async function cargarProveedoresParaModalNueva() {
    // Reutilizar el array global "proveedores" si ya está cargado; si no, recargar.
    if (!Array.isArray(proveedores) || proveedores.length === 0) {
        await cargarProveedores();
    }

    const select = document.getElementById('nueva-proveedor');
    if (!select) return;
    select.innerHTML = '<option value="">Seleccionar proveedor...</option>';
    proveedores.forEach(prov => {
        const opt = document.createElement('option');
        opt.value = prov.id;
        opt.textContent = `${prov.nombre} (${prov.nif})`;
        select.appendChild(opt);
    });
}

window.guardarNuevaFactura = async function() {
    try {
        const fileEl = document.getElementById('nueva-archivo');
        const archivoAdjunto = fileEl?.files?.[0] || null;

        const modo = document.querySelector('input[name="proveedorModo"]:checked')?.value || 'existente';

        let proveedorId = null;
        let proveedorManual = null;

        if (modo === 'existente') {
            proveedorId = parseInt(document.getElementById('nueva-proveedor')?.value || '', 10);
            if (!proveedorId) {
                mostrarNotificacion('Selecciona un proveedor', 'error');
                return;
            }
        } else {
            const nombre = (document.getElementById('nueva-prov-nombre')?.value || '').trim();
            const nifEl = document.getElementById('nueva-prov-nif');
            const nif = (nifEl?.value || '').trim();
            if (!nombre) {
                mostrarNotificacion('El nombre del proveedor es obligatorio', 'error');
                return;
            }

            // Validar CP si se rellena
            const cpEl = document.getElementById('nueva-prov-cp');
            const cpRaw = (cpEl?.value || '').trim();
            if (cpRaw && window.CpValidator) {
                const cp = window.CpValidator.normalizeCp(cpRaw);
                if (cpEl) cpEl.value = cp;
                if (!window.CpValidator.isValidFormat(cp)) {
                    mostrarNotificacion('El CP del proveedor debe tener 5 dígitos', 'error');
                    return;
                }

                if (typeof window.CpValidator.getCpData === 'function') {
                    const data = await window.CpValidator.getCpData(cp);
                    if (!Array.isArray(data) || !data.length) {
                        mostrarNotificacion('El CP del proveedor no existe', 'error');
                        return;
                    }
                }
            }

            proveedorManual = {
                nombre,
                nif,
                direccion: (document.getElementById('nueva-prov-direccion')?.value || '').trim(),
                cp: (document.getElementById('nueva-prov-cp')?.value || '').trim(),
                poblacion: (document.getElementById('nueva-prov-poblacion')?.value || '').trim(),
                provincia: (document.getElementById('nueva-prov-provincia')?.value || '').trim(),
                email: (document.getElementById('nueva-prov-email')?.value || '').trim(),
                telefono: (document.getElementById('nueva-prov-telefono')?.value || '').trim()
            };
        }

        const fechaEmision = document.getElementById('nueva-fecha-emision')?.value;
        const base = parseFloat(document.getElementById('nueva-base')?.value || '0');
        const ivaPct = parseFloat(document.getElementById('nueva-iva-porcentaje')?.value || '0');
        const ivaImp = parseFloat(document.getElementById('nueva-iva-importe')?.value || '0');
        const total = parseFloat(document.getElementById('nueva-total')?.value || '0');

        if (!fechaEmision) {
            mostrarNotificacion('La fecha de emisión es obligatoria', 'error');
            return;
        }
        if (!isFinite(base) || base < 0) {
            mostrarNotificacion('La base imponible no es válida', 'error');
            return;
        }

        // Si hay archivo, reutilizar pipeline de subida masiva (OCR opcional previo)
        if (archivoAdjunto) {
            // Resolver proveedor_id (creando si hace falta)
            if (!proveedorId) {
                const nuevoProveedor = {
                    nombre: (proveedorManual?.nombre || 'Proveedor sin nombre').toUpperCase(),
                    nif: (proveedorManual?.nif || '').toUpperCase(),
                    email: proveedorManual?.email || '',
                    telefono: proveedorManual?.telefono || '',
                    direccion: proveedorManual?.direccion || '',
                    cp: proveedorManual?.cp || '',
                    poblacion: proveedorManual?.poblacion || '',
                    provincia: proveedorManual?.provincia || '',
                    activo: true,
                    requiere_revision: true
                };

                const respProv = await fetch('/api/proveedores/crear', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(nuevoProveedor)
                });
                const dataProv = await respProv.json();
                if (!respProv.ok || !dataProv.success) {
                    throw new Error(dataProv.error || 'Error creando proveedor');
                }
                proveedorId = dataProv.id || dataProv.proveedor?.id;
                if (!proveedorId) throw new Error('No se pudo obtener el ID del proveedor creado');
            }

            const formData = new FormData();
            formData.append('proveedor_id', String(proveedorId));
            formData.append('numero_factura', (document.getElementById('nueva-numero')?.value || '').trim());
            formData.append('fecha_emision', fechaEmision);
            formData.append('fecha_vencimiento', (document.getElementById('nueva-fecha-vencimiento')?.value || '').trim());
            formData.append('base_imponible', String(isFinite(base) ? base : 0));
            formData.append('iva_porcentaje', String(isFinite(ivaPct) ? ivaPct : 0));
            formData.append('iva', String(isFinite(ivaImp) ? ivaImp : 0));
            formData.append('total', String(isFinite(total) ? total : 0));
            formData.append('concepto', (document.getElementById('nueva-concepto')?.value || '').trim());
            formData.append('notas', (document.getElementById('nueva-notas')?.value || '').trim());
            formData.append('estado', 'P');
            formData.append('archivos', archivoAdjunto);

            const respUp = await fetch('/api/facturas-proveedores/subir', {
                method: 'POST',
                body: formData
            });

            const contentType = respUp.headers.get('content-type');
            if (contentType && contentType.includes('text/html')) {
                throw new Error('Sesión expirada. Por favor, recarga la página y vuelve a iniciar sesión.');
            }

            const dataUp = await respUp.json();
            if (!respUp.ok || !dataUp.success) {
                if (dataUp.duplicada) {
                    mostrarNotificacion('⚠️ Factura duplicada: ya existe', 'warning');
                    return;
                }
                throw new Error(dataUp.error || 'Error guardando factura con archivo');
            }

            mostrarNotificacion('✅ Factura creada correctamente (con archivo)', 'success');
            cerrarModal('modalNuevaFactura');
            await cargarProveedores();
            cargarFacturas();
            return;
        }

        const payload = {
            proveedor_id: proveedorId,
            proveedor: proveedorManual,
            factura: {
                numero_factura: (document.getElementById('nueva-numero')?.value || '').trim(),
                fecha_emision: fechaEmision,
                fecha_vencimiento: (document.getElementById('nueva-fecha-vencimiento')?.value || '').trim(),
                base_imponible: base,
                iva_porcentaje: ivaPct,
                iva_importe: ivaImp,
                total,
                concepto: (document.getElementById('nueva-concepto')?.value || '').trim(),
                notas: (document.getElementById('nueva-notas')?.value || '').trim(),
                estado: 'P'
            }
        };

        const response = await fetch('/api/facturas-proveedores/crear', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const data = await response.json();
        if (!response.ok || !data.success) {
            throw new Error(data.error || 'Error creando factura');
        }

        mostrarNotificacion('✅ Factura creada correctamente', 'success');
        cerrarModal('modalNuevaFactura');
        await cargarProveedores();
        cargarFacturas();
    } catch (err) {
        console.error('[Facturas] Error creando factura:', err);
        mostrarNotificacion('Error al crear factura: ' + (err.message || err), 'error');
    }
};

// ============================================================================
// FUNCIONES DE TRIMESTRE Y FECHAS
// ============================================================================

function llenarSelectorAnios() {
    const anioSelect = document.getElementById('anioFilter');
    const anioActual = new Date().getFullYear();
    
    for (let i = 0; i < 5; i++) {
        const option = document.createElement('option');
        option.value = anioActual - i;
        option.textContent = anioActual - i;
        anioSelect.appendChild(option);
    }
}

function toggleSelectorAnio(valor) {
    const anioContainer = document.getElementById('anioContainer');
    // Mostrar selector de año si se elige un trimestre específico (1T, 2T, etc)
    if (['1T', '2T', '3T', '4T'].includes(valor)) {
        anioContainer.style.display = 'block';
    } else {
        anioContainer.style.display = 'none';
    }
}

function obtenerRangoFechas() {
    const tipo = document.getElementById('trimestreFilter').value;
    const anioSeleccionado = parseInt(document.getElementById('anioFilter').value) || new Date().getFullYear();
    const hoy = new Date();
    const year = (['actual', 'anterior'].includes(tipo)) ? hoy.getFullYear() : anioSeleccionado;
    
    let inicio, fin;

    switch(tipo) {
        case 'actual':
            // Trimestre actual
            const mes = hoy.getMonth();
            const q = Math.floor(mes / 3);
            inicio = new Date(year, q * 3, 1);
            fin = new Date(year, (q * 3) + 3, 0);
            break;
        case 'anterior':
            // Trimestre anterior
            const mesAnt = hoy.getMonth();
            const qAnt = Math.floor(mesAnt / 3) - 1;
            if (qAnt < 0) {
                inicio = new Date(year - 1, 9, 1);
                fin = new Date(year - 1, 12, 0);
            } else {
                inicio = new Date(year, qAnt * 3, 1);
                fin = new Date(year, (qAnt * 3) + 3, 0);
            }
            break;
        case 'anio_actual':
            inicio = new Date(hoy.getFullYear(), 0, 1);
            fin = new Date(hoy.getFullYear(), 11, 31);
            break;
        case 'anio_anterior':
            inicio = new Date(hoy.getFullYear() - 1, 0, 1);
            fin = new Date(hoy.getFullYear() - 1, 11, 31);
            break;
        case '1T':
            inicio = new Date(year, 0, 1);
            fin = new Date(year, 3, 0);
            break;
        case '2T':
            inicio = new Date(year, 3, 1);
            fin = new Date(year, 6, 0);
            break;
        case '3T':
            inicio = new Date(year, 6, 1);
            fin = new Date(year, 9, 0);
            break;
        case '4T':
            inicio = new Date(year, 9, 1);
            fin = new Date(year, 12, 0);
            break;
        case 'todos':
            return { fecha_desde: null, fecha_hasta: null };
        default:
             // Fallback trimestre actual
            const m = hoy.getMonth();
            const qu = Math.floor(m / 3);
            inicio = new Date(year, qu * 3, 1);
            fin = new Date(year, (qu * 3) + 3, 0);
    }
    
    return {
        fecha_desde: formatearFechaInput(inicio),
        fecha_hasta: formatearFechaInput(fin)
    };
}

function formatearFechaInput(fecha) {
    const año = fecha.getFullYear();
    const mes = String(fecha.getMonth() + 1).padStart(2, '0');
    const dia = String(fecha.getDate()).padStart(2, '0');
    return `${año}-${mes}-${dia}`;
}

// ============================================================================
// BÚSQUEDA INTERACTIVA CON DEBOUNCE
// ============================================================================

function busquedaInteractiva(event) {
    // Cancelar búsqueda anterior si existe
    if (timeoutBusqueda) {
        clearTimeout(timeoutBusqueda);
    }
    
    // Mostrar indicador de búsqueda
    const searchingIndicator = document.getElementById('searchingIndicator');
    const busquedaInput = document.getElementById('busquedaFilter');
    
    if (event && event.target === busquedaInput) {
        // Mostrar spinner solo para campo de texto
        if (searchingIndicator) {
            searchingIndicator.style.display = 'inline';
        }
        busquedaInput.style.borderColor = '#ffc107';
    }
    
    // Determinar delay según el tipo de filtro
    let delay = 300; // Por defecto 300ms para campos de texto
    
    // Para selects y fechas, búsqueda más rápida (50ms)
    if (event && event.target && (
        event.target.tagName === 'SELECT' || 
        event.target.type === 'date'
    )) {
        delay = 50;
    }
    
    // Esperar antes de buscar (debounce)
    timeoutBusqueda = setTimeout(() => {
        paginaActual = 1;
        cargarFacturas();
        
        // Quitar indicador de búsqueda
        if (searchingIndicator) {
            searchingIndicator.style.display = 'none';
        }
        if (busquedaInput) {
            busquedaInput.style.borderColor = '';
        }
    }, delay);
    
    console.log(`[Facturas] Búsqueda programada en ${delay}ms (tipo: ${event?.target?.tagName || 'unknown'})`);
}

// ============================================================================
// CARGA DE DATOS
// ============================================================================

async function cargarProveedores() {
    try {
        const response = await fetch('/api/proveedores/listar?activos=true');
        const data = await response.json();
        
        if (data.success) {
            proveedores = data.proveedores;
            
            // Llenar dropdown
            const select = document.getElementById('proveedorFilter');
            select.innerHTML = '<option value="todos">Todos</option>';
            
            proveedores.forEach(prov => {
                const option = document.createElement('option');
                option.value = prov.id;
                option.textContent = `${prov.nombre} (${prov.nif})`;
                select.appendChild(option);
            });
            
            console.log(`[Facturas] ${proveedores.length} proveedores cargados`);
        }
    } catch (error) {
        console.error('[Facturas] Error cargando proveedores:', error);
    }
}

async function cargarFacturas() {
    try {
        // Mostrar loading
        const tbody = document.getElementById('facturasBody');
        tbody.innerHTML = `
            <tr>
                <td colspan="9" style="text-align: center; padding: 40px;">
                    <i class="fas fa-spinner fa-spin"></i> Cargando facturas...
                </td>
            </tr>
        `;
        
        // Construir filtros
        const filtros = {
            pagina: paginaActual,
            por_pagina: porPagina,
            orden_campo: 'fecha_emision',
            orden_direccion: 'DESC'
        };
        
        // Filtro de proveedor
        const proveedorId = document.getElementById('proveedorFilter').value;
        if (proveedorId !== 'todos') {
            filtros.proveedor_id = parseInt(proveedorId);
        }
        
        
        // Filtro de fechas calculado dinámicamente
        const rangoFechas = obtenerRangoFechas();
        if (rangoFechas.fecha_desde) filtros.fecha_desde = rangoFechas.fecha_desde;
        if (rangoFechas.fecha_hasta) filtros.fecha_hasta = rangoFechas.fecha_hasta;
        
        // Búsqueda
        const busqueda = document.getElementById('busquedaFilter').value.trim();
        if (busqueda) {
            filtros.busqueda = busqueda;
        }
        
        filtrosActuales = filtros;
        
        // Llamar a la API
        const response = await fetch('/api/facturas-proveedores/consultar', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(filtros)
        });
        
        const data = await response.json();
        
        if (data.success) {
            renderizarTabla(data.facturas);
            actualizarResumen(data);
            actualizarPaginacion(data);
            verificarAlertas(data);
            
            console.log(`[Facturas] ${data.facturas.length} facturas cargadas`);
        } else {
            throw new Error(data.error || 'Error desconocido');
        }
        
    } catch (error) {
        console.error('[Facturas] Error cargando facturas:', error);
        mostrarNotificacion('Error al cargar facturas: ' + error.message, 'error');
        
        const tbody = document.getElementById('facturasBody');
        tbody.innerHTML = `
            <tr>
                <td colspan="9" style="text-align: center; padding: 40px; color: #dc3545;">
                    <i class="fas fa-exclamation-triangle"></i> Error al cargar facturas
                </td>
            </tr>
        `;
    }
}

// ============================================================================
// RENDERIZADO
// ============================================================================

function renderizarTabla(facturas) {
    const tbody = document.getElementById('facturasBody');
    tbody.innerHTML = '';
    
    if (facturas.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="9" style="text-align: center; padding: 40px;">
                    📭 No se encontraron facturas con los filtros aplicados
                </td>
            </tr>
        `;
        return;
    }
    
    facturas.forEach(factura => {
        const tr = document.createElement('tr');
        
        // Determinar color de fila según estado
        // Color de fondo según estado
        if (factura.icono_estado === '🔴') {
            tr.style.backgroundColor = '#fff5f5';
        } else if (factura.icono_estado === '⚠️') {
            tr.style.backgroundColor = '#fffbf0';
        }
        
        // Hacer toda la fila clicable (excepto botones)
        tr.style.cursor = 'pointer';
        tr.onclick = function(e) {
            // No abrir si se hace click en un botón
            if (!e.target.closest('button')) {
                editarFactura(factura.id);
            }
        };
        
        tr.innerHTML = `
            <td>${factura.proveedor_nombre}</td>
            <td>${factura.proveedor_nif}</td>
            <td style="font-weight: 600;">${factura.numero_factura}</td>
            <td>${formatearFecha(factura.fecha_emision)}</td>
            <td>${formatearFecha(factura.fecha_vencimiento)}</td>
            <td style="text-align: right;">${formatearImporte(factura.base_imponible)}</td>
            <td style="text-align: right;">${formatearImporte(factura.iva_importe)}</td>
            <td style="text-align: right;"><strong>${formatearImporte(factura.total)}</strong></td>
            <td style="text-align: center;">
                ${factura.ruta_archivo ? `
                    <button class="btn-icon" onclick="event.stopPropagation(); descargarPDF(${factura.id})" title="Descargar PDF">
                        <i class="fas fa-file-pdf"></i>
                    </button>
                ` : ''}
                <button class="btn-icon text-danger" onclick="event.stopPropagation(); eliminarFactura(${factura.id})" title="Eliminar">
                    <i class="fas fa-times"></i>
                </button>
            </td>
        `;
        
        tbody.appendChild(tr);
    });
}

function actualizarResumen(data) {
    // Actualizar resumen superior
    document.getElementById('resumenTotal').textContent = formatearImporte(data.total_general || 0);
    document.getElementById('resumenPendiente').textContent = formatearImporte(data.total_pendiente || 0);
    document.getElementById('resumenPagado').textContent = formatearImporte(data.total_pagado || 0);
    document.getElementById('resumenVencido').textContent = formatearImporte(data.total_vencido || 0);
    
    // Actualizar footer fijo
    const footerBase = document.getElementById('footerBase');
    const footerIVA = document.getElementById('footerIVA');
    const footerTotal = document.getElementById('footerTotal');
    
    if (footerBase) footerBase.textContent = formatearImporte(data.total_base || 0);
    if (footerIVA) footerIVA.textContent = formatearImporte(data.total_iva || 0);
    if (footerTotal) footerTotal.textContent = formatearImporte(data.total_general || 0);
}

function actualizarPaginacion(data) {
    paginaActual = data.pagina;
    totalPaginas = data.total_paginas;
    
    const pageInfo = `Página ${paginaActual} de ${totalPaginas}`;
    document.getElementById('pageInfo').textContent = pageInfo;
    
    // Habilitar/deshabilitar botones
    document.getElementById('prevPage').disabled = paginaActual === 1;
    document.getElementById('nextPage').disabled = paginaActual === totalPaginas;
}

function verificarAlertas(data) {
    const container = document.getElementById('alertasContainer');
    container.innerHTML = '';
    
    let hayAlertas = false;
    
    // Alerta de facturas vencidas
    if (data.total_vencido > 0) {
        hayAlertas = true;
        const alerta = document.createElement('div');
        alerta.className = 'alerta roja';
        alerta.innerHTML = `
            🔴 Tienes facturas vencidas por un total de <strong>${formatearImporte(data.total_vencido)}</strong>
            <a onclick="filtrarVencidas()">Ver facturas vencidas</a>
        `;
        container.appendChild(alerta);
    }
    
    container.style.display = hayAlertas ? 'flex' : 'none';
}

// ============================================================================
// ACCIONES
// ============================================================================

function cambiarPagina(delta) {
    const nuevaPagina = paginaActual + delta;
    if (nuevaPagina >= 1 && nuevaPagina <= totalPaginas) {
        paginaActual = nuevaPagina;
        cargarFacturas();
    }
}

function filtrarVencidas() {
    // Función deshabilitada - filtro de estado eliminado
    mostrarNotificacion('Filtro de estado eliminado', 'info');
}

async function exportarExcel() {
    mostrarNotificacion('Exportando a Excel...', 'info');
    
    try {
        const response = await fetch('/api/facturas-proveedores/exportar', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(filtrosActuales)
        });
        
        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `facturas_recibidas_${new Date().toISOString().split('T')[0]}.xlsx`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
            
            mostrarNotificacion('✅ Excel exportado correctamente', 'success');
        } else {
            throw new Error('Error al exportar');
        }
    } catch (error) {
        console.error('[Facturas] Error exportando:', error);
        mostrarNotificacion('Error al exportar a Excel', 'error');
    }
}

function subirFactura() {
    mostrarNotificacion('Función de subida en desarrollo', 'info');
    // TODO: Implementar modal de subida
}

// ============================================================================
// FUNCIONES GLOBALES (llamadas desde HTML)
// ============================================================================

window.verDetalle = async function(facturaId) {
    try {
        const response = await fetch(`/api/facturas-proveedores/${facturaId}`);
        const data = await response.json();
        
        if (data.success) {
            mostrarModalDetalle(data.factura);
        } else {
            mostrarNotificacion('Error al cargar factura: ' + data.error, 'error');
        }
    } catch (error) {
        console.error('[Facturas] Error cargando detalle:', error);
        mostrarNotificacion('Error al cargar factura', 'error');
    }
};

window.descargarPDF = async function(facturaId) {
    try {
        // Verificar si el PDF existe
        const response = await fetch(`/api/facturas-proveedores/${facturaId}/pdf`, {
            method: 'HEAD' // Solo verificar headers, no descargar el archivo
        });
        
        if (response.ok) {
            // El archivo existe, abrirlo
            window.open(`/api/facturas-proveedores/${facturaId}/pdf`, '_blank');
        } else if (response.status === 404) {
            // Archivo no encontrado
            mostrarNotificacion('❌ El archivo PDF no existe en el servidor', 'error');
        } else {
            // Otro error
            mostrarNotificacion('❌ Error al acceder al archivo PDF', 'error');
        }
    } catch (error) {
        console.error('Error al verificar PDF:', error);
        mostrarNotificacion('❌ Error al verificar el archivo PDF', 'error');
    }
};

window.marcarPagada = async function(facturaId) {
    try {
        const response = await fetch(`/api/facturas-proveedores/${facturaId}`);
        const data = await response.json();
        
        if (data.success) {
            mostrarModalPagar(data.factura);
        } else {
            mostrarNotificacion('Error al cargar factura', 'error');
        }
    } catch (error) {
        console.error('[Facturas] Error:', error);
        mostrarNotificacion('Error al cargar factura', 'error');
    }
};

window.editarFactura = async function(facturaId) {
    try {
        const response = await fetch(`/api/facturas-proveedores/${facturaId}`);
        const data = await response.json();
        
        if (data.success) {
            mostrarModalEditar(data.factura);
        } else {
            mostrarNotificacion('Error al cargar factura', 'error');
        }
    } catch (error) {
        console.error('[Facturas] Error:', error);
        mostrarNotificacion('Error al cargar factura', 'error');
    }
};

window.eliminarFactura = async function(facturaId) {
    if (!confirm('¿Estás seguro de que deseas eliminar esta factura?\n\nEsta acción no se puede deshacer.')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/facturas-proveedores/${facturaId}`, {
            method: 'DELETE'
        });
        
        const data = await response.json();
        
        if (data.success) {
            mostrarNotificacion('✅ Factura eliminada correctamente', 'success');
            cargarFacturas(); // Recargar tabla
        } else {
            mostrarNotificacion('Error: ' + data.error, 'error');
        }
    } catch (error) {
        console.error('[Facturas] Error eliminando:', error);
        mostrarNotificacion('Error al eliminar factura', 'error');
    }
};

// ============================================================================
// FUNCIONES DE MODALES
// ============================================================================

function mostrarModalDetalle(factura) {
    // Llenar datos del proveedor
    document.getElementById('detalle-proveedor-nombre').textContent = factura.proveedor_nombre || '-';
    document.getElementById('detalle-proveedor-nif').textContent = factura.proveedor_nif || '-';
    document.getElementById('detalle-proveedor-direccion').textContent = factura.proveedor_direccion || '-';
    document.getElementById('detalle-proveedor-telefono').textContent = factura.proveedor_telefono || '-';
    
    // Llenar datos de la factura
    document.getElementById('detalle-numero').textContent = factura.numero_factura;
    document.getElementById('detalle-fecha-emision').textContent = formatearFecha(factura.fecha_emision);
    document.getElementById('detalle-fecha-vencimiento').textContent = formatearFecha(factura.fecha_vencimiento);
    
    const estadoBadge = document.getElementById('detalle-estado');
    estadoBadge.textContent = factura.estado;
    estadoBadge.className = `badge ${factura.estado}`;
    
    // Importes
    document.getElementById('detalle-base').textContent = formatearImporte(factura.base_imponible);
    document.getElementById('detalle-iva').textContent = formatearImporte(factura.iva_importe) + ` (${factura.iva_porcentaje}%)`;
    document.getElementById('detalle-total').textContent = formatearImporte(factura.total);
    
    // Concepto y notas
    document.getElementById('detalle-concepto').textContent = factura.concepto || '-';
    document.getElementById('detalle-notas').textContent = factura.notas || '-';
    
    // Líneas (si existen)
    if (factura.lineas && factura.lineas.length > 0) {
        const tbody = document.getElementById('detalle-lineas-body');
        tbody.innerHTML = '';
        
        factura.lineas.forEach(linea => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${linea.concepto}</td>
                <td>${linea.cantidad}</td>
                <td>${formatearImporte(linea.precio_unitario)}</td>
                <td>${linea.iva_porcentaje}%</td>
                <td>${formatearImporte(linea.total_linea)}</td>
            `;
            tbody.appendChild(tr);
        });
        
        document.getElementById('seccion-lineas').style.display = 'block';
    } else {
        document.getElementById('seccion-lineas').style.display = 'none';
    }
    
    // Historial
    if (factura.historial && factura.historial.length > 0) {
        const historialDiv = document.getElementById('detalle-historial');
        historialDiv.innerHTML = '';
        
        factura.historial.forEach(h => {
            const item = document.createElement('div');
            item.className = 'historial-item';
            item.innerHTML = `
                <div class="fecha">${formatearFechaHora(h.fecha)}</div>
                <div class="accion">${h.accion}</div>
                <div class="usuario">Por: ${h.usuario}</div>
            `;
            historialDiv.appendChild(item);
        });
        
        document.getElementById('seccion-historial').style.display = 'block';
    } else {
        document.getElementById('seccion-historial').style.display = 'none';
    }
    
    // Guardar ID para descargar PDF
    window.facturaDetalleId = factura.id;
    
    // Mostrar modal
    abrirModal('modalDetalle');
}

function mostrarModalPagar(factura) {
    document.getElementById('pagar-factura-id').value = factura.id;
    document.getElementById('pagar-fecha').value = new Date().toISOString().split('T')[0];
    document.getElementById('pagar-metodo').value = 'transferencia';
    document.getElementById('pagar-referencia').value = '';
    
    document.getElementById('pagar-info-numero').textContent = factura.numero_factura;
    document.getElementById('pagar-info-proveedor').textContent = factura.proveedor_nombre;
    document.getElementById('pagar-info-total').textContent = formatearImporte(factura.total);
    
    abrirModal('modalPagar');
}

function _setEditarPreviewVisible(visible) {
    const modal = document.getElementById('modalEditar');
    if (!modal) return;
    const formCol = modal.querySelector('.edit-form-column');
    const previewCol = modal.querySelector('.edit-preview-column');
    if (!formCol || !previewCol) return;

    if (visible) {
        previewCol.style.display = 'flex';
        formCol.style.width = '40%';
        formCol.style.flex = '0 0 40%';
    } else {
        previewCol.style.display = 'none';
        formCol.style.width = '100%';
        formCol.style.flex = '1 1 auto';
    }
}

function mostrarModalEditar(factura) {
    document.getElementById('editar-factura-id').value = factura.id;
    
    // Llenar y seleccionar proveedor
    const selectProveedor = document.getElementById('editar-proveedor');
    if (selectProveedor) {
        selectProveedor.innerHTML = '<option value="">Seleccionar proveedor...</option>';
        if (typeof proveedores !== 'undefined' && proveedores.length > 0) {
            proveedores.forEach(prov => {
                const option = document.createElement('option');
                option.value = prov.id;
                option.textContent = `${prov.nombre} (${prov.nif})`;
                selectProveedor.appendChild(option);
            });
            // Seleccionar el proveedor actual
            if (factura.proveedor_id) {
                selectProveedor.value = factura.proveedor_id;
            }
        }
    }

    document.getElementById('editar-numero').value = factura.numero_factura;
    document.getElementById('editar-fecha-emision').value = factura.fecha_emision;
    document.getElementById('editar-fecha-vencimiento').value = factura.fecha_vencimiento || '';
    document.getElementById('editar-base').value = factura.base_imponible;
    document.getElementById('editar-iva-porcentaje').value = factura.iva_porcentaje;
    document.getElementById('editar-iva-importe').value = factura.iva_importe;
    document.getElementById('editar-total').value = factura.total;
    document.getElementById('editar-concepto').value = factura.concepto || '';
    document.getElementById('editar-notas').value = factura.notas || '';
    // Checkbox eliminado: document.getElementById('editar-revisado').checked = factura.revisado === 1;
    
    // Event listeners para cálculo automático
    const baseInput = document.getElementById('editar-base');
    const ivaSelect = document.getElementById('editar-iva-porcentaje');
    
    const calcular = () => {
        const base = parseFloat(baseInput.value) || 0;
        const ivaPorcentaje = parseFloat(ivaSelect.value) || 0;
        const ivaImporte = base * (ivaPorcentaje / 100);
        const total = base + ivaImporte;
        
        document.getElementById('editar-iva-importe').value = ivaImporte.toFixed(2);
        document.getElementById('editar-total').value = total.toFixed(2);
    };
    
    baseInput.addEventListener('input', calcular);
    ivaSelect.addEventListener('change', calcular);
    
    // Cargar previsualización en iframe
    const previewFrame = document.getElementById('editar-preview-frame');
    const previewPlaceholder = document.getElementById('editar-preview-placeholder');

    const tieneArchivo = !!(factura && factura.ruta_archivo && String(factura.ruta_archivo).trim());
    const url = (factura && factura.id) ? `/api/facturas-proveedores/${factura.id}/pdf` : '';

    if (!previewFrame) {
        _setEditarPreviewVisible(false);
    } else if (!tieneArchivo || !url) {
        previewFrame.src = '';
        previewFrame.style.display = 'none';
        if (previewPlaceholder) previewPlaceholder.style.display = 'none';
        _setEditarPreviewVisible(false);
    } else {
        // Por defecto mostramos placeholder mientras validamos que el endpoint devuelve un archivo
        _setEditarPreviewVisible(true);
        previewFrame.src = '';
        previewFrame.style.display = 'none';
        if (previewPlaceholder) previewPlaceholder.style.display = 'flex';

        // Validación ligera: si el endpoint responde JSON/HTML o 404, ocultar el preview
        fetch(url, { method: 'HEAD' })
            .then(resp => {
                const ct = (resp.headers.get('content-type') || '').toLowerCase();
                const isBad = ct.includes('application/json') || ct.includes('text/html');
                if (!resp.ok || isBad) {
                    previewFrame.src = '';
                    previewFrame.style.display = 'none';
                    if (previewPlaceholder) previewPlaceholder.style.display = 'none';
                    _setEditarPreviewVisible(false);
                    return;
                }
                previewFrame.src = url;
                previewFrame.style.display = 'block';
                if (previewPlaceholder) previewPlaceholder.style.display = 'none';
            })
            .catch(() => {
                previewFrame.src = '';
                previewFrame.style.display = 'none';
                if (previewPlaceholder) previewPlaceholder.style.display = 'none';
                _setEditarPreviewVisible(false);
            });

        previewFrame.onerror = function() {
            previewFrame.src = '';
            previewFrame.style.display = 'none';
            if (previewPlaceholder) previewPlaceholder.style.display = 'none';
            _setEditarPreviewVisible(false);
        };
    }
    
    abrirModal('modalEditar');
}

window.abrirModal = function(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.add('show');
        modal.style.display = 'flex';
        // Reducir z-index del menú para que el overlay lo cubra
        const menu = document.querySelector('.menu, nav.menu');
        if (menu) menu.style.zIndex = '1';
    }
};

window.cerrarModal = function(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.remove('show');
        setTimeout(() => {
            modal.style.display = 'none';
            // Restaurar z-index del menú si no hay otros modales abiertos
            const modalesAbiertos = document.querySelectorAll('.modal.show, .modal[style*="display: flex"], .modal[style*="display:flex"]');
            if (modalesAbiertos.length === 0) {
                const menu = document.querySelector('.menu, nav.menu');
                if (menu) menu.style.zIndex = '';
            }
        }, 300);
    }
};

window.descargarPDFDesdeModal = async function() {
    if (window.facturaDetalleId) {
        try {
            // Verificar si el PDF existe
            const response = await fetch(`/api/facturas-proveedores/${window.facturaDetalleId}/pdf`, {
                method: 'HEAD'
            });
            
            if (response.ok) {
                // El archivo existe, abrirlo
                window.open(`/api/facturas-proveedores/${window.facturaDetalleId}/pdf`, '_blank');
            } else if (response.status === 404) {
                // Archivo no encontrado
                mostrarNotificacion('❌ El archivo PDF no existe en el servidor', 'error');
            } else {
                // Otro error
                mostrarNotificacion('❌ Error al acceder al archivo PDF', 'error');
            }
        } catch (error) {
            console.error('Error al verificar PDF:', error);
            mostrarNotificacion('❌ Error al verificar el archivo PDF', 'error');
        }
    }
};

window.confirmarPago = async function() {
    const facturaId = document.getElementById('pagar-factura-id').value;
    const fechaPago = document.getElementById('pagar-fecha').value;
    const metodoPago = document.getElementById('pagar-metodo').value;
    const referenciaPago = document.getElementById('pagar-referencia').value;
    
    if (!fechaPago) {
        mostrarNotificacion('La fecha de pago es obligatoria', 'error');
        return;
    }
    
    try {
        const response = await fetch(`/api/facturas-proveedores/${facturaId}/pagar`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                fecha_pago: fechaPago,
                metodo_pago: metodoPago,
                referencia_pago: referenciaPago
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            mostrarNotificacion('✅ Factura marcada como pagada', 'success');
            cerrarModal('modalPagar');
            cargarFacturas(); // Recargar tabla
        } else {
            mostrarNotificacion('Error: ' + data.error, 'error');
        }
    } catch (error) {
        console.error('[Facturas] Error:', error);
        mostrarNotificacion('Error al marcar como pagada', 'error');
    }
};

window.guardarEdicion = async function() {
    const facturaId = document.getElementById('editar-factura-id').value;
    
    const datos = {
        proveedor_id: document.getElementById('editar-proveedor').value,
        numero_factura: document.getElementById('editar-numero').value,
        fecha_emision: document.getElementById('editar-fecha-emision').value,
        fecha_vencimiento: document.getElementById('editar-fecha-vencimiento').value,
        base_imponible: parseFloat(document.getElementById('editar-base').value),
        iva_porcentaje: parseFloat(document.getElementById('editar-iva-porcentaje').value),
        iva_importe: parseFloat(document.getElementById('editar-iva-importe').value),
        total: parseFloat(document.getElementById('editar-total').value),
        concepto: document.getElementById('editar-concepto').value,
        notas: document.getElementById('editar-notas').value,
        revisado: 1 // Al editar manualmente, marcamos como revisado por defecto
    };
    
    try {
        const response = await fetch(`/api/facturas-proveedores/${facturaId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(datos)
        });
        
        const data = await response.json();
        
        if (data.success) {
            mostrarNotificacion('✅ Factura actualizada correctamente', 'success');
            cerrarModal('modalEditar');
            cargarFacturas(); // Recargar tabla
        } else {
            mostrarNotificacion('Error: ' + data.error, 'error');
        }
    } catch (error) {
        console.error('[Facturas] Error:', error);
        mostrarNotificacion('Error al guardar cambios', 'error');
    }
};

// Cerrar modal al hacer click fuera
window.addEventListener('click', (e) => {
    if (e.target.classList.contains('modal')) {
        e.target.classList.remove('show');
        setTimeout(() => {
            e.target.style.display = 'none';
        }, 300);
    }
});

// ============================================================================
// UTILIDADES
// ============================================================================

function formatearFecha(fecha) {
    if (!fecha) return '-';
    const [year, month, day] = fecha.split('-');
    return `${day}/${month}/${year}`;
}

function formatearFechaHora(fechaHora) {
    if (!fechaHora) return '-';
    try {
        const fecha = new Date(fechaHora);
        const dia = fecha.getDate().toString().padStart(2, '0');
        const mes = (fecha.getMonth() + 1).toString().padStart(2, '0');
        const año = fecha.getFullYear();
        const hora = fecha.getHours().toString().padStart(2, '0');
        const minutos = fecha.getMinutes().toString().padStart(2, '0');
        return `${dia}/${mes}/${año} ${hora}:${minutos}`;
    } catch (e) {
        return fechaHora;
    }
}

function obtenerTituloEstado(factura) {
    if (factura.estado === 'pagada') return 'Pagada';
    if (factura.icono_estado === '🔴') return 'Vencida';
    if (factura.revisado === 0) return 'Requiere revisión';
    return 'Pendiente';
}
