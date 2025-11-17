/**
 * subir_facturas_masivo.js
 * Procesamiento masivo de facturas con OCR automático
 */

import { mostrarNotificacion } from './notificaciones.js';

// Variables globales
let archivosSeleccionados = [];
let proveedoresCache = new Map(); // Cache de proveedores para evitar duplicados
let procesando = false;
let stats = {
    total: 0,
    procesando: 0,
    completadas: 0,
    errores: 0
};

// ============================================================================
// INICIALIZACIÓN
// ============================================================================

document.addEventListener('DOMContentLoaded', () => {
    console.log('[Masivo] Inicializando...');
    
    cargarProveedores();
    configurarEventListeners();
});

function configurarEventListeners() {
    const uploadZone = document.getElementById('uploadZone');
    const fileInput = document.getElementById('fileInput');
    
    // Click en zona de carga
    uploadZone.addEventListener('click', () => {
        if (!procesando) {
            fileInput.click();
        }
    });
    
    // Selección de archivos
    fileInput.addEventListener('change', (e) => {
        agregarArchivos(e.target.files);
    });
    
    // Drag and drop
    uploadZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        if (!procesando) {
            uploadZone.classList.add('dragover');
        }
    });
    
    uploadZone.addEventListener('dragleave', () => {
        uploadZone.classList.remove('dragover');
    });
    
    uploadZone.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadZone.classList.remove('dragover');
        if (!procesando) {
            agregarArchivos(e.dataTransfer.files);
        }
    });
    
    // Botones
    document.getElementById('btnProcesar').addEventListener('click', procesarTodas);
    document.getElementById('btnCancelar').addEventListener('click', cancelar);
    document.getElementById('btnToggleLog').addEventListener('click', toggleLog);
}

// ============================================================================
// CARGA DE PROVEEDORES
// ============================================================================

async function cargarProveedores() {
    try {
        const response = await fetch('/api/proveedores/listar');
        const data = await response.json();
        
        if (data.success) {
            // Crear cache de proveedores por NIF
            data.proveedores.forEach(prov => {
                if (prov.nif) {
                    proveedoresCache.set(prov.nif.toLowerCase(), prov);
                }
            });
            
            console.log(`[Masivo] ${proveedoresCache.size} proveedores en cache`);
        }
    } catch (error) {
        console.error('[Masivo] Error cargando proveedores:', error);
    }
}

// ============================================================================
// MANEJO DE ARCHIVOS
// ============================================================================

function agregarArchivos(files) {
    const archivosArray = Array.from(files);
    
    // Validar y agregar archivos
    archivosArray.forEach(archivo => {
        const extension = archivo.name.split('.').pop().toLowerCase();
        const tamañoMB = archivo.size / (1024 * 1024);
        
        if (!['pdf', 'jpg', 'jpeg', 'png'].includes(extension)) {
            addLog(`⚠️ ${archivo.name}: formato no válido`, 'warning');
            return;
        }
        
        if (tamañoMB > 10) {
            addLog(`⚠️ ${archivo.name}: tamaño máximo 10MB`, 'warning');
            return;
        }
        
        // Agregar archivo con estado inicial
        archivosSeleccionados.push({
            archivo: archivo,
            id: Date.now() + Math.random(),
            estado: 'pendiente', // pendiente, procesando, completada, error
            progreso: 0,
            mensaje: 'En cola',
            datos: null,
            error: null
        });
    });
    
    if (archivosSeleccionados.length > 0) {
        actualizarStats();
        renderizarArchivos();
        mostrarControles();
        addLog(`📁 ${archivosArray.length} archivo(s) agregado(s)`, 'info');
    }
}

function renderizarArchivos() {
    const container = document.getElementById('filesList');
    container.innerHTML = '';
    
    archivosSeleccionados.forEach(item => {
        const div = document.createElement('div');
        div.className = `file-item ${item.estado}`;
        div.id = `file-${item.id}`;
        
        const extension = item.archivo.name.split('.').pop().toLowerCase();
        const iconClass = extension === 'pdf' ? 'pdf' : 'image';
        const icon = extension === 'pdf' ? 'fa-file-pdf' : 'fa-file-image';
        
        let statusIcon = '';
        if (item.estado === 'procesando') {
            statusIcon = '<span class="spinner"></span>';
        } else if (item.estado === 'completada') {
            statusIcon = '<i class="fas fa-check-circle" style="color: #28a745;"></i> ';
        } else if (item.estado === 'error') {
            statusIcon = '<i class="fas fa-times-circle" style="color: #dc3545;"></i> ';
        }
        
        div.innerHTML = `
            <div class="file-icon ${iconClass}">
                <i class="fas ${icon}"></i>
            </div>
            <div class="file-info">
                <div class="file-name">${item.archivo.name}</div>
                <div class="file-status">${statusIcon}${item.mensaje}</div>
                ${item.datos ? `
                    <div class="file-details">
                        Proveedor: ${item.datos.proveedor?.nombre || 'N/A'} | 
                        Factura: ${item.datos.factura?.numero || 'N/A'} | 
                        Total: ${item.datos.factura?.total || 'N/A'}€
                    </div>
                ` : ''}
                ${item.error ? `
                    <div class="file-details" style="color: #dc3545;">
                        Error: ${item.error}
                    </div>
                ` : ''}
                <div class="file-progress">
                    <div class="file-progress-bar ${item.estado}" style="width: ${item.progreso}%"></div>
                </div>
            </div>
        `;
        
        container.appendChild(div);
    });
}

function mostrarControles() {
    document.getElementById('statsContainer').style.display = 'grid';
    document.getElementById('actionButtons').style.display = 'flex';
}

function actualizarStats() {
    stats.total = archivosSeleccionados.length;
    stats.procesando = archivosSeleccionados.filter(f => f.estado === 'procesando').length;
    stats.completadas = archivosSeleccionados.filter(f => f.estado === 'completada').length;
    stats.errores = archivosSeleccionados.filter(f => f.estado === 'error').length;
    
    document.getElementById('statTotal').textContent = stats.total;
    document.getElementById('statProcesando').textContent = stats.procesando;
    document.getElementById('statCompletadas').textContent = stats.completadas;
    document.getElementById('statErrores').textContent = stats.errores;
}

// ============================================================================
// PROCESAMIENTO MASIVO
// ============================================================================

async function procesarTodas() {
    if (procesando) return;
    
    procesando = true;
    document.getElementById('btnProcesar').disabled = true;
    document.getElementById('uploadZone').style.opacity = '0.5';
    document.getElementById('uploadZone').style.pointerEvents = 'none';
    
    addLog('🚀 Iniciando procesamiento masivo...', 'info');
    
    // Procesar archivos secuencialmente
    for (const item of archivosSeleccionados) {
        if (item.estado === 'pendiente') {
            await procesarArchivo(item);
            // Pausa entre archivos para evitar "database is locked"
            await sleep(1000);
        }
    }
    
    procesando = false;
    document.getElementById('btnProcesar').disabled = false;
    document.getElementById('uploadZone').style.opacity = '1';
    document.getElementById('uploadZone').style.pointerEvents = 'auto';
    
    addLog('✅ Procesamiento completado', 'success');
    mostrarNotificacion(
        `Procesamiento completado: ${stats.completadas} exitosas, ${stats.errores} errores`,
        stats.errores > 0 ? 'warning' : 'success'
    );
}

async function procesarArchivo(item) {
    try {
        // Actualizar estado
        item.estado = 'procesando';
        item.progreso = 10;
        item.mensaje = 'Escaneando con IA...';
        actualizarStats();
        renderizarArchivos();
        
        addLog(`📄 Procesando: ${item.archivo.name}`, 'info');
        
        // 1. Escanear con OCR
        const datosOCR = await escanearFactura(item.archivo);
        item.progreso = 40;
        item.datos = datosOCR;
        renderizarArchivos();
        
        addLog(`  ✓ OCR completado: ${datosOCR.proveedor?.nombre || 'Sin nombre'}`, 'success');
        
        // 2. Buscar o crear proveedor
        item.mensaje = 'Buscando proveedor...';
        renderizarArchivos();
        
        const proveedorId = await buscarOCrearProveedorSilencioso(datosOCR.proveedor);
        item.progreso = 60;
        renderizarArchivos();
        
        addLog(`  ✓ Proveedor: ${datosOCR.proveedor?.nombre} (ID: ${proveedorId})`, 'success');
        
        // 3. Guardar factura
        item.mensaje = 'Guardando factura...';
        renderizarArchivos();
        
        const resultado = await guardarFactura(item.archivo, datosOCR, proveedorId);
        item.progreso = 100;
        
        // Verificar si es duplicada
        if (resultado.duplicada) {
            item.estado = 'duplicada';
            item.mensaje = '⚠️ Duplicada';
            addLog(`  ⚠️ Factura duplicada: ${datosOCR.factura?.numero} (ya existe)`, 'warning');
        } else {
            item.estado = 'completada';
            item.mensaje = '✓ Completada';
            addLog(`  ✅ Factura guardada: ${datosOCR.factura?.numero}`, 'success');
        }
        
    } catch (error) {
        item.estado = 'error';
        item.progreso = 100;
        item.mensaje = 'Error';
        item.error = error.message;
        
        addLog(`  ❌ Error: ${error.message}`, 'error');
        console.error('[Masivo] Error procesando archivo:', error);
    }
    
    actualizarStats();
    renderizarArchivos();
}

async function escanearFactura(archivo) {
    const formData = new FormData();
    formData.append('archivo', archivo);
    
    const response = await fetch('/api/facturas-proveedores/ocr', {
        method: 'POST',
        body: formData
    });
    
    // Verificar si la respuesta es HTML (sesión expirada)
    const contentType = response.headers.get('content-type');
    if (contentType && contentType.includes('text/html')) {
        throw new Error('Sesión expirada. Por favor, recarga la página y vuelve a iniciar sesión.');
    }
    
    const data = await response.json();
    
    if (!data.success) {
        throw new Error(data.error || 'Error en OCR');
    }
    
    return data.datos;
}

async function buscarOCrearProveedorSilencioso(datosProveedor) {
    if (!datosProveedor) {
        throw new Error('Datos de proveedor no disponibles');
    }
    
    // Si no tiene NIF, crear con nombre solamente
    if (!datosProveedor.nif) {
        addLog(`  ⚠️ Proveedor sin NIF: ${datosProveedor.nombre}`, 'warning');
        // Buscar por nombre exacto
        const responseList = await fetch('/api/proveedores/listar?activos=false');
        const dataList = await responseList.json();
        
        if (dataList.success) {
            const proveedorExistente = dataList.proveedores.find(p => 
                p.nombre && p.nombre.toLowerCase() === datosProveedor.nombre.toLowerCase()
            );
            
            if (proveedorExistente) {
                addLog(`  ✓ Proveedor encontrado por nombre: ${proveedorExistente.nombre} (ID: ${proveedorExistente.id})`, 'success');
                return proveedorExistente.id;
            }
        }
        
        // Crear sin NIF
        const nuevoProveedor = {
            nombre: datosProveedor.nombre || 'Proveedor sin nombre',
            nif: '',  // NIF vacío
            email: datosProveedor.email || '',
            telefono: datosProveedor.telefono || '',
            direccion: datosProveedor.direccion || '',
            activo: true,
            requiere_revision: true
        };
        
        const response = await fetch('/api/proveedores/crear', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(nuevoProveedor)
        });
        
        const data = await response.json();
        if (data.success) {
            addLog(`  ✓ Proveedor creado sin NIF: ${data.proveedor.nombre} (ID: ${data.proveedor.id})`, 'success');
            return data.proveedor.id;
        }
        
        throw new Error(data.error || 'Error creando proveedor sin NIF');
    }
    
    const nifLower = datosProveedor.nif.toLowerCase();
    
    // Buscar en cache
    if (proveedoresCache.has(nifLower)) {
        return proveedoresCache.get(nifLower).id;
    }
    
    // Intentar crear nuevo proveedor
    const nuevoProveedor = {
        nombre: datosProveedor.nombre || 'Sin nombre',
        nif: datosProveedor.nif,
        email: datosProveedor.email || '',
        telefono: datosProveedor.telefono || '',
        direccion: datosProveedor.direccion || '',
        activo: true,
        creado_automaticamente: true,
        requiere_revision: true
    };
    
    const response = await fetch('/api/proveedores/crear', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(nuevoProveedor)
    });
    
    // Verificar si la respuesta es HTML (sesión expirada)
    const contentType = response.headers.get('content-type');
    if (contentType && contentType.includes('text/html')) {
        throw new Error('Sesión expirada. Por favor, recarga la página y vuelve a iniciar sesión.');
    }
    
    const data = await response.json();
    
    if (data.success) {
        // Proveedor creado o ya existente
        const proveedor = data.proveedor;
        proveedoresCache.set(nifLower, proveedor);
        
        if (data.ya_existia) {
            addLog(`  ✓ Proveedor existente: ${proveedor.nombre} (ID: ${proveedor.id})`, 'info');
        } else {
            addLog(`  ✓ Proveedor creado: ${proveedor.nombre} (ID: ${proveedor.id})`, 'success');
        }
        
        return proveedor.id;
    }
    
    // Si falla, puede ser porque ya existe (duplicado)
    // Buscar en la lista de proveedores (incluir inactivos)
    const responseList = await fetch('/api/proveedores/listar?activos=false');
    const dataList = await responseList.json();
    
    if (dataList.success) {
        const proveedorExistente = dataList.proveedores.find(p => 
            p.nif && p.nif.toLowerCase() === nifLower
        );
        
        if (proveedorExistente) {
            proveedoresCache.set(nifLower, proveedorExistente);
            addLog(`  ✓ Proveedor existente: ${proveedorExistente.nombre} (ID: ${proveedorExistente.id})`, 'info');
            return proveedorExistente.id;
        }
    }
    
    throw new Error(data.error || 'Error creando/buscando proveedor');
}

async function guardarFactura(archivo, datosOCR, proveedorId) {
    const formData = new FormData();
    formData.append('proveedor_id', proveedorId);
    formData.append('numero_factura', datosOCR.factura?.numero || '');
    formData.append('fecha_emision', datosOCR.factura?.fecha_emision || '');
    formData.append('fecha_vencimiento', datosOCR.factura?.fecha_vencimiento || '');
    formData.append('base_imponible', datosOCR.factura?.base_imponible || '0');
    formData.append('iva', datosOCR.factura?.iva || '0');
    formData.append('total', datosOCR.factura?.total || '0');
    formData.append('concepto', datosOCR.factura?.concepto || '');
    formData.append('archivos', archivo);
    
    const response = await fetch('/api/facturas-proveedores/subir', {
        method: 'POST',
        body: formData
    });
    
    // Verificar si la respuesta es HTML (sesión expirada)
    const contentType = response.headers.get('content-type');
    if (contentType && contentType.includes('text/html')) {
        throw new Error('Sesión expirada. Por favor, recarga la página y vuelve a iniciar sesión.');
    }
    
    const data = await response.json();
    
    if (!data.success) {
        // Si es factura duplicada, retornar info en lugar de error
        if (data.duplicada) {
            return {
                success: false,
                duplicada: true,
                mensaje: data.mensaje,
                info: data.info
            };
        }
        throw new Error(data.error || 'Error guardando factura');
    }
    
    return data;
}

// ============================================================================
// UTILIDADES
// ============================================================================

function cancelar() {
    if (procesando) {
        if (!confirm('Hay un procesamiento en curso. ¿Deseas cancelar?')) {
            return;
        }
    }
    
    archivosSeleccionados = [];
    proveedoresCache.clear();
    procesando = false;
    stats = { total: 0, procesando: 0, completadas: 0, errores: 0 };
    
    document.getElementById('filesList').innerHTML = '';
    document.getElementById('statsContainer').style.display = 'none';
    document.getElementById('actionButtons').style.display = 'none';
    document.getElementById('logContainer').innerHTML = '';
    document.getElementById('logContainer').classList.remove('active');
    document.getElementById('fileInput').value = '';
    
    cargarProveedores();
    addLog('🔄 Sistema reiniciado', 'info');
}

function toggleLog() {
    const log = document.getElementById('logContainer');
    log.classList.toggle('active');
}

function addLog(mensaje, tipo = 'info') {
    const log = document.getElementById('logContainer');
    const entry = document.createElement('div');
    entry.className = `log-entry log-${tipo}`;
    
    const time = new Date().toLocaleTimeString();
    entry.innerHTML = `<span class="log-time">[${time}]</span>${mensaje}`;
    
    log.appendChild(entry);
    log.scrollTop = log.scrollHeight;
    
    console.log(`[Masivo] ${mensaje}`);
}

function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}
