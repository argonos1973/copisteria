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
    if (uploadZone && fileInput) {
        uploadZone.addEventListener('click', (e) => {
            // Evitar recursión si el click viene del propio input (aunque esté fuera ahora)
            if (e.target === fileInput) return;
            
            if (!procesando) {
                console.log('[Masivo] Click en zona de carga -> abriendo selector');
                fileInput.click();
            }
        });
    } else {
        console.error('[Masivo] No se encontraron elementos uploadZone o fileInput');
    }
    
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
        // AÑADIR TIMESTAMP PARA EVITAR CACHÉ DE NAVEGADOR
        const response = await fetch(`/api/proveedores/listar?t=${Date.now()}`);
        const data = await response.json();
        
        if (data.success) {
            // Crear cache de proveedores por NIF
            proveedoresCache.clear(); // Limpiar antes de llenar
            data.proveedores.forEach(prov => {
                if (prov.nif) {
                    proveedoresCache.set(prov.nif.toLowerCase(), prov);
                }
            });
            
            console.log(`[Masivo] ${proveedoresCache.size} proveedores cargados en cache`);
        }
    } catch (error) {
        console.error('[Masivo] Error cargando proveedores:', error);
    }
}

// ============================================================================
// MANEJO DE ARCHIVOS
// ============================================================================

async function agregarArchivos(files) {
    const archivosArray = Array.from(files);
    let nuevosArchivosCount = 0;
    
    for (const archivo of archivosArray) {
        const extension = archivo.name.split('.').pop().toLowerCase();
        
        // DETECCIÓN DE ZIP
        if (extension === 'zip') {
            try {
                mostrarIndicadorProcesamiento(archivo.name, 'Descomprimiendo ZIP...');
                addLog(`📦 Descomprimiendo: ${archivo.name}`, 'info');
                
                // Verificar si JSZip está cargado
                if (typeof JSZip === 'undefined') {
                    throw new Error('Librería JSZip no cargada. Recarga la página.');
                }
                
                const zip = await JSZip.loadAsync(archivo);
                const promises = [];
                
                // Iterar sobre archivos del ZIP
                zip.forEach((relativePath, zipEntry) => {
                    if (!zipEntry.dir) {
                        const ext = zipEntry.name.split('.').pop().toLowerCase();
                        
                        // Filtrar solo extensiones válidas
                        if (['pdf', 'jpg', 'jpeg', 'png'].includes(ext)) {
                            // Ignorar basura de macOS y archivos ocultos
                            if (!zipEntry.name.includes('__MACOSX') && !zipEntry.name.startsWith('.')) {
                                
                                // Aplanar nombre: carpeta/factura.pdf -> carpeta_factura.pdf
                                // Esto evita problemas con directorios en el backend si no existen
                                const flatName = zipEntry.name.replace(/\//g, '_');
                                
                                promises.push(
                                    zipEntry.async('blob').then(blob => {
                                        // Recrear objeto File
                                        return new File([blob], flatName, { 
                                            type: ext === 'pdf' ? 'application/pdf' : `image/${ext}` 
                                        });
                                    })
                                );
                            }
                        }
                    }
                });
                
                const extractedFiles = await Promise.all(promises);
                extractedFiles.forEach(f => {
                    if (procesarArchivoIndividual(f)) nuevosArchivosCount++;
                });
                
                addLog(`✅ ZIP extraído: ${extractedFiles.length} archivos válidos`, 'success');
                
            } catch (error) {
                addLog(`❌ Error descomprimiendo ZIP: ${error.message}`, 'error');
                console.error(error);
                mostrarNotificacion('Error al leer el archivo ZIP', 'error');
            } finally {
                ocultarIndicadorProcesamiento();
            }
            continue; 
        }

        // Archivo normal
        if (procesarArchivoIndividual(archivo)) nuevosArchivosCount++;
    }
    
    if (nuevosArchivosCount > 0) {
        actualizarStats();
        renderizarArchivos();
        mostrarControles();
        
        // Mostrar notificación de confirmación para iniciar proceso
        mostrarNotificacionConfirmacion();
    }
}

function procesarArchivoIndividual(archivo) {
    const extension = archivo.name.split('.').pop().toLowerCase();
    const tamañoMB = archivo.size / (1024 * 1024);
    
    if (!['pdf', 'jpg', 'jpeg', 'png'].includes(extension)) {
        // addLog(`⚠️ ${archivo.name}: formato no válido`, 'warning');
        return false;
    }
    
    if (tamañoMB > 20) {
        addLog(`⚠️ ${archivo.name}: tamaño máximo 20MB`, 'warning');
        return false;
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
    
    return true;
}

async function mostrarNotificacionConfirmacion() {
    const totalArchivos = archivosSeleccionados.length;
    const mensaje = `Se han cargado ${totalArchivos} factura${totalArchivos > 1 ? 's' : ''}. ¿Deseas iniciar el procesamiento automático?`;
    
    // Crear diálogo de confirmación personalizado
    const overlay = document.createElement('div');
    overlay.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0, 0, 0, 0.5);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 10000;
    `;
    
    const dialog = document.createElement('div');
    dialog.style.cssText = `
        background: var(--bg-elevated, #fff);
        padding: 30px;
        border-radius: 12px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
        max-width: 500px;
        text-align: center;
        color: var(--text, #333);
        border: 1px solid var(--border-color, transparent);
    `;
    
    dialog.innerHTML = `
        <div style="margin-bottom: 20px;">
            <i class="fas fa-file-invoice" style="font-size: 48px; color: #667eea;"></i>
        </div>
        <h3 style="margin-bottom: 15px; color: var(--text, #333);">Procesar Facturas</h3>
        <p style="margin-bottom: 25px; color: var(--text-muted, #666); font-size: 16px;">${mensaje}</p>
        <div style="display: flex; gap: 10px; justify-content: center;">
            <button id="btnConfirmarProcesar" class="btn btn-primary" style="padding: 10px 30px;">
                <i class="fas fa-play"></i> Procesar Ahora
            </button>
            <button id="btnCancelarProcesar" class="btn btn-secondary" style="padding: 10px 30px;">
                <i class="fas fa-times"></i> Cancelar
            </button>
        </div>
    `;
    
    overlay.appendChild(dialog);
    document.body.appendChild(overlay);
    
    // Event listeners
    document.getElementById('btnConfirmarProcesar').addEventListener('click', () => {
        document.body.removeChild(overlay);
        procesarTodas();
    });
    
    document.getElementById('btnCancelarProcesar').addEventListener('click', () => {
        document.body.removeChild(overlay);
        mostrarNotificacion('Procesamiento cancelado. Puedes procesarlas cuando quieras.', 'info');
    });
    
    // Cerrar al hacer click fuera del diálogo
    overlay.addEventListener('click', (e) => {
        if (e.target === overlay) {
            document.body.removeChild(overlay);
            mostrarNotificacion('Procesamiento cancelado. Puedes procesarlas cuando quieras.', 'info');
        }
    });
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
    // Contar completadas Y duplicadas como "completadas" para que cuadren los números
    stats.completadas = archivosSeleccionados.filter(f => f.estado === 'completada' || f.estado === 'duplicada').length;
    stats.errores = archivosSeleccionados.filter(f => f.estado === 'error').length;
    
    const duplicadas = archivosSeleccionados.filter(f => f.estado === 'duplicada').length;
    const textoCompletadas = duplicadas > 0 ? `${stats.completadas} (${duplicadas} dupl.)` : stats.completadas;

    document.getElementById('statTotal').textContent = stats.total;
    document.getElementById('statProcesando').textContent = stats.procesando;
    document.getElementById('statCompletadas').textContent = textoCompletadas;
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
    
    // addLog('🚀 Iniciando procesamiento masivo...', 'info');
    
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
    
    // addLog('✅ Procesamiento completado', 'success');
    
    // Si hubo errores, mostrar resumen detallado
    if (stats.errores > 0) {
        mostrarModalErrores();
    } else {
        const duplicadas = archivosSeleccionados.filter(f => f.estado === 'duplicada').length;
        const guardadas = archivosSeleccionados.filter(f => f.estado === 'completada').length;
        
        mostrarNotificacion(
            `Procesamiento completado: ${guardadas} guardadas, ${duplicadas} duplicadas`,
            'success'
        );
    }
}

function mostrarModalErrores() {
    const archivosErroneos = archivosSeleccionados.filter(f => f.estado === 'error');
    
    // Crear lista de errores HTML
    let listaErrores = '<ul style="text-align: left; max-height: 200px; overflow-y: auto; margin: 10px 0; padding-left: 20px;">';
    archivosErroneos.forEach(f => {
        listaErrores += `<li style="margin-bottom: 5px;"><strong>${f.archivo.name}:</strong> ${f.error || 'Error desconocido'}</li>`;
    });
    listaErrores += '</ul>';
    
    // Crear modal
    const overlay = document.createElement('div');
    overlay.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0, 0, 0, 0.5);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 10000;
    `;
    
    const dialog = document.createElement('div');
    dialog.style.cssText = `
        background: var(--bg-elevated, #fff);
        padding: 30px;
        border-radius: 12px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
        max-width: 600px;
        width: 90%;
        text-align: center;
        color: var(--text, #333);
        border: 1px solid var(--border-color, transparent);
    `;
    
    dialog.innerHTML = `
        <div style="margin-bottom: 20px;">
            <i class="fas fa-exclamation-triangle" style="font-size: 48px; color: #dc3545;"></i>
        </div>
        <h3 style="margin-bottom: 15px; color: var(--text, #333);">Procesamiento finalizado con errores</h3>
        <p style="margin-bottom: 15px; color: var(--text-muted, #666);">
            Se completaron ${stats.completadas} facturas correctamente, pero ocurrieron ${stats.errores} errores:
        </p>
        
        <div style="background: rgba(220, 53, 69, 0.1); border: 1px solid var(--border-color, #ffcdd2); border-radius: 6px; padding: 10px; margin-bottom: 20px; color: var(--text, #333);">
            ${listaErrores}
        </div>
        
        <button id="btnCerrarErrores" class="btn btn-primary" style="padding: 10px 30px;">
            Cerrar
        </button>
    `;
    
    overlay.appendChild(dialog);
    document.body.appendChild(overlay);
    
    document.getElementById('btnCerrarErrores').addEventListener('click', () => {
        document.body.removeChild(overlay);
    });
    
    overlay.addEventListener('click', (e) => {
        if (e.target === overlay) {
            document.body.removeChild(overlay);
        }
    });
}

async function procesarArchivo(item) {
    try {
        // Actualizar estado
        item.estado = 'procesando';
        item.progreso = 10;
        item.mensaje = 'Escaneando con IA...';
        actualizarStats();
        renderizarArchivos();
        mostrarIndicadorProcesamiento(item.archivo.name, 'Escaneando con IA...');
        
        // addLog(`📄 Procesando: ${item.archivo.name}`, 'info');
        
        // 1. Escanear con OCR
        const datosOCR = await escanearFactura(item.archivo);
        item.progreso = 40;
        item.datos = datosOCR;
        renderizarArchivos();
        
        // Validar que existan datos de proveedor
        // LIMPIEZA DEFENSIVA DE 'NULL' STRING
        if (datosOCR.proveedor) {
            ['nombre', 'nif', 'direccion', 'email'].forEach(campo => {
                if (datosOCR.proveedor[campo] && (datosOCR.proveedor[campo] === 'NULL' || datosOCR.proveedor[campo] === 'null')) {
                    datosOCR.proveedor[campo] = '';
                }
            });
        }
        const datosProveedor = datosOCR.proveedor || { nombre: 'Proveedor Desconocido' };
        const total = datosOCR.factura?.total || '0.00';
        actualizarIndicadorConDatos(datosProveedor.nombre, total, 'Extrayendo datos del proveedor...');
        
        // addLog(`  ✓ OCR completado: ${datosProveedor.nombre}`, 'success');
        
        // 2. Buscar o crear proveedor
        item.mensaje = 'Buscando proveedor...';
        renderizarArchivos();
        actualizarIndicadorProcesamiento('Buscando/creando proveedor...');
        
        // Datos del proveedor
        if (datosOCR.proveedor) {
            // LIMPIEZA DEFENSIVA DE 'NULL' STRING
            ['nombre', 'nif', 'direccion', 'email'].forEach(campo => {
                if (datosOCR.proveedor[campo] === 'NULL' || datosOCR.proveedor[campo] === 'null') {
                    datosOCR.proveedor[campo] = '';
                }
            });
        }

        // REGLA: Todo en mayúsculas (nombre de proveedor)
        if (datosProveedor.nombre) {
            datosProveedor.nombre = datosProveedor.nombre.toUpperCase();
        }
        
        const proveedorId = await buscarOCrearProveedorSilencioso(datosProveedor);
        item.progreso = 60;
        renderizarArchivos();
        
        // addLog(`  ✓ Proveedor: ${datosProveedor.nombre} (ID: ${proveedorId})`, 'success');
        
        // 3. Guardar factura
        item.mensaje = 'Guardando factura...';
        renderizarArchivos();
        actualizarIndicadorProcesamiento('Guardando factura en base de datos...');
        
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
            // addLog(`  ✅ Factura guardada: ${datosOCR.factura?.numero}`, 'success');
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
    ocultarIndicadorProcesamiento();
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

    console.log('[Masivo] Buscando/Creando proveedor:', datosProveedor);

    // Si no tiene NIF, crear con nombre solamente
    if (!datosProveedor.nif) {
        // addLog(`  Proveedor sin NIF: ${datosProveedor.nombre}`, 'warning');
        // Buscar por nombre exacto
        const responseList = await fetch(`/api/proveedores/listar?activos=false&t=${Date.now()}`);
        const dataList = await responseList.json();

        if (dataList.success) {
            const proveedorExistente = dataList.proveedores.find(p =>
                p.nombre && p.nombre.toLowerCase() === datosProveedor.nombre.toLowerCase()
            );

            if (proveedorExistente) {
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
            const proveedorId = data.id || data.proveedor?.id;
            return proveedorId;
        }

        throw new Error(data.error || 'Error creando proveedor sin NIF');
    }

    const nifLower = datosProveedor.nif.toLowerCase();

    // Buscar en cache
    if (proveedoresCache.has(nifLower)) {
        const cached = proveedoresCache.get(nifLower);

        // MEJORA CRÍTICA: Si el proveedor en caché tiene nombre "SIN NOMBRE" o similar,
        // y el nuevo nombre es bueno, ACTUALIZARLO.
        const nombreActual = (cached.nombre || '').toUpperCase();
        const nuevoNombre = (datosProveedor.nombre || '').toUpperCase();

        const esGenerico = nombreActual.includes('SIN NOMBRE') ||
            nombreActual.includes('NO IDENTIFICADO') ||
            nombreActual.includes('PROVEEDOR DESCONOCIDO');

        const esValido = nuevoNombre && nuevoNombre.length > 2 && !nuevoNombre.includes('SIN NOMBRE');

        if (esGenerico && esValido) {
            console.log(`[Masivo] Actualizando nombre de proveedor ID ${cached.id}: ${nombreActual} -> ${nuevoNombre}`);
            addLog(`  Actualizando nombre proveedor: ${nuevoNombre}`, 'info');

            try {
                await fetch(`/api/proveedores/${cached.id}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ nombre: nuevoNombre })
                });
                // Actualizar cache local
                cached.nombre = nuevoNombre;
                proveedoresCache.set(nifLower, cached);
            } catch (e) {
                console.error('[Masivo] Error actualizando nombre proveedor:', e);
            }
        }

        return cached.id;
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
        // Si backend no devuelve objeto proveedor, lo construimos
        const proveedor = data.proveedor || { ...nuevoProveedor, id: data.id };
        
        proveedoresCache.set(nifLower, proveedor);
        
        if (data.ya_existia) {
            // addLog(`  ✓ Proveedor existente: ${proveedor.nombre} (ID: ${proveedor.id})`, 'info');
        } else {
            // addLog(`  ✓ Proveedor creado: ${proveedor.nombre} (ID: ${proveedor.id})`, 'success');
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
            // addLog(`  ✓ Proveedor existente: ${proveedorExistente.nombre} (ID: ${proveedorExistente.id})`, 'info');
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
// INDICADOR DE PROCESAMIENTO
// ============================================================================

function mostrarIndicadorProcesamiento(filename, status) {
    const indicator = document.getElementById('processingIndicator');
    const filenameEl = document.getElementById('processingFilename');
    const statusEl = document.getElementById('processingStatusText');
    
    filenameEl.textContent = filename;
    statusEl.textContent = status;
    indicator.style.display = 'flex';
}

function actualizarIndicadorProcesamiento(status) {
    const statusEl = document.getElementById('processingStatusText');
    statusEl.textContent = status;
}

function actualizarIndicadorConDatos(proveedor, total, status) {
    const providerEl = document.getElementById('processingProvider');
    const totalEl = document.getElementById('processingTotal');
    const statusEl = document.getElementById('processingStatusText');
    
    if (providerEl) providerEl.textContent = `🏢 ${proveedor}`;
    if (totalEl) totalEl.textContent = `💰 ${parseFloat(total).toFixed(2)}€`;
    if (statusEl) statusEl.textContent = status;
}

function ocultarIndicadorProcesamiento() {
    const indicator = document.getElementById('processingIndicator');
    indicator.style.display = 'none';
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
    ocultarIndicadorProcesamiento();
    
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
