/**
 * subir_factura.js
 * Funcionalidad para subir facturas de proveedores
 */

import { mostrarNotificacion } from './notificaciones.js';

// Variables globales
let archivosSeleccionados = [];
let proveedores = [];

// ============================================================================
// INICIALIZACIÓN
// ============================================================================

document.addEventListener('DOMContentLoaded', () => {
    console.log('[Subir Factura] Inicializando...');
    
    cargarProveedores();
    configurarEventListeners();
});

function configurarEventListeners() {
    const uploadZone = document.getElementById('uploadZone');
    const fileInput = document.getElementById('fileInput');
    
    // Click en zona de carga
    uploadZone.addEventListener('click', () => fileInput.click());
    
    // Selección de archivos
    fileInput.addEventListener('change', (e) => {
        manejarArchivos(e.target.files);
    });
    
    // Drag and drop
    uploadZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadZone.classList.add('dragover');
    });
    
    uploadZone.addEventListener('dragleave', () => {
        uploadZone.classList.remove('dragover');
    });
    
    uploadZone.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadZone.classList.remove('dragover');
        manejarArchivos(e.dataTransfer.files);
    });
    
    // Cálculo automático del total
    document.getElementById('baseImponible').addEventListener('input', calcularTotal);
    document.getElementById('iva').addEventListener('input', calcularTotal);
    
    // Botones
    document.getElementById('btnCancelar').addEventListener('click', cancelar);
    document.getElementById('btnGuardar').addEventListener('click', guardarFactura);
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
            
            const select = document.getElementById('proveedor');
            select.innerHTML = '<option value="">Seleccionar proveedor...</option>';
            
            proveedores.forEach(prov => {
                const option = document.createElement('option');
                option.value = prov.id;
                option.textContent = `${prov.nombre} (${prov.nif})`;
                select.appendChild(option);
            });
            
            console.log(`[Subir Factura] ${proveedores.length} proveedores cargados`);
        }
    } catch (error) {
        console.error('[Subir Factura] Error cargando proveedores:', error);
        mostrarNotificacion('Error al cargar proveedores', 'error');
    }
}

// ============================================================================
// MANEJO DE ARCHIVOS
// ============================================================================

function manejarArchivos(files) {
    const archivosArray = Array.from(files);
    
    // Validar archivos
    const archivosValidos = archivosArray.filter(archivo => {
        const extension = archivo.name.split('.').pop().toLowerCase();
        const tamañoMB = archivo.size / (1024 * 1024);
        
        if (!['pdf', 'jpg', 'jpeg', 'png'].includes(extension)) {
            mostrarNotificacion(`Archivo ${archivo.name}: formato no válido`, 'error');
            return false;
        }
        
        if (tamañoMB > 10) {
            mostrarNotificacion(`Archivo ${archivo.name}: tamaño máximo 10MB`, 'error');
            return false;
        }
        
        return true;
    });
    
    if (archivosValidos.length === 0) return;
    
    archivosSeleccionados = archivosValidos;
    mostrarVistaPrevia();
    mostrarFormulario();
}

function mostrarVistaPrevia() {
    const preview = document.getElementById('filePreview');
    const fileList = document.getElementById('fileList');
    
    fileList.innerHTML = '';
    
    archivosSeleccionados.forEach((archivo, index) => {
        const item = document.createElement('div');
        item.className = 'file-item';
        
        const extension = archivo.name.split('.').pop().toLowerCase();
        const icono = extension === 'pdf' ? 'fa-file-pdf' : 'fa-file-image';
        
        item.innerHTML = `
            <div class="file-info">
                <div class="file-icon">
                    <i class="fas ${icono}"></i>
                </div>
                <div class="file-details">
                    <div class="file-name">${archivo.name}</div>
                    <div class="file-size">${formatearTamaño(archivo.size)}</div>
                </div>
            </div>
            <button class="btn-remove" onclick="eliminarArchivo(${index})">
                <i class="fas fa-trash"></i> Eliminar
            </button>
        `;
        
        fileList.appendChild(item);
    });
    
    preview.style.display = 'block';
}

function mostrarFormulario() {
    document.getElementById('formSection').style.display = 'block';
    
    // Establecer fecha de emisión a hoy
    const hoy = new Date().toISOString().split('T')[0];
    document.getElementById('fechaEmision').value = hoy;
}

window.eliminarArchivo = function(index) {
    archivosSeleccionados.splice(index, 1);
    
    if (archivosSeleccionados.length === 0) {
        document.getElementById('filePreview').style.display = 'none';
        document.getElementById('formSection').style.display = 'none';
        document.getElementById('fileInput').value = '';
    } else {
        mostrarVistaPrevia();
    }
};

function formatearTamaño(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(2) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(2) + ' MB';
}

// ============================================================================
// CÁLCULOS
// ============================================================================

function calcularTotal() {
    const base = parseFloat(document.getElementById('baseImponible').value) || 0;
    const iva = parseFloat(document.getElementById('iva').value) || 0;
    const total = base + iva;
    
    document.getElementById('total').value = total.toFixed(2);
}

// ============================================================================
// GUARDAR FACTURA
// ============================================================================

async function guardarFactura() {
    // Validar formulario
    const proveedor = document.getElementById('proveedor').value;
    const numeroFactura = document.getElementById('numeroFactura').value.trim();
    const fechaEmision = document.getElementById('fechaEmision').value;
    const baseImponible = parseFloat(document.getElementById('baseImponible').value);
    const iva = parseFloat(document.getElementById('iva').value);
    const total = parseFloat(document.getElementById('total').value);
    
    if (!proveedor) {
        mostrarNotificacion('Selecciona un proveedor', 'error');
        return;
    }
    
    if (!numeroFactura) {
        mostrarNotificacion('Ingresa el número de factura', 'error');
        return;
    }
    
    if (!fechaEmision) {
        mostrarNotificacion('Ingresa la fecha de emisión', 'error');
        return;
    }
    
    if (isNaN(baseImponible) || baseImponible <= 0) {
        mostrarNotificacion('Ingresa una base imponible válida', 'error');
        return;
    }
    
    if (isNaN(iva) || iva < 0) {
        mostrarNotificacion('Ingresa un IVA válido', 'error');
        return;
    }
    
    if (archivosSeleccionados.length === 0) {
        mostrarNotificacion('Selecciona al menos un archivo', 'error');
        return;
    }
    
    // Mostrar indicador de procesamiento
    document.getElementById('processing').classList.add('active');
    document.getElementById('btnGuardar').disabled = true;
    
    try {
        // Crear FormData
        const formData = new FormData();
        formData.append('proveedor_id', proveedor);
        formData.append('numero_factura', numeroFactura);
        formData.append('fecha_emision', fechaEmision);
        formData.append('fecha_vencimiento', document.getElementById('fechaVencimiento').value || '');
        formData.append('base_imponible', baseImponible);
        formData.append('iva', iva);
        formData.append('total', total);
        formData.append('concepto', document.getElementById('concepto').value.trim());
        
        // Agregar archivos
        archivosSeleccionados.forEach(archivo => {
            formData.append('archivos', archivo);
        });
        
        // Enviar al servidor
        const response = await fetch('/api/facturas-proveedores/subir', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (data.success) {
            mostrarNotificacion('Factura guardada correctamente', 'success');
            
            // Limpiar formulario después de 1 segundo
            setTimeout(() => {
                limpiarFormulario();
                // Redirigir a consulta
                window.parent.postMessage({
                    action: 'navigate',
                    url: '/CONSULTA_FACTURAS_RECIBIDAS.html'
                }, '*');
            }, 1000);
        } else {
            throw new Error(data.error || 'Error al guardar factura');
        }
        
    } catch (error) {
        console.error('[Subir Factura] Error:', error);
        mostrarNotificacion('Error al guardar factura: ' + error.message, 'error');
    } finally {
        document.getElementById('processing').classList.remove('active');
        document.getElementById('btnGuardar').disabled = false;
    }
}

// ============================================================================
// UTILIDADES
// ============================================================================

function cancelar() {
    if (confirm('¿Deseas cancelar? Se perderán los datos ingresados.')) {
        limpiarFormulario();
        window.parent.postMessage({
            action: 'navigate',
            url: '/CONSULTA_FACTURAS_RECIBIDAS.html'
        }, '*');
    }
}

function limpiarFormulario() {
    archivosSeleccionados = [];
    document.getElementById('fileInput').value = '';
    document.getElementById('filePreview').style.display = 'none';
    document.getElementById('formSection').style.display = 'none';
    
    // Limpiar campos
    document.getElementById('proveedor').value = '';
    document.getElementById('numeroFactura').value = '';
    document.getElementById('fechaEmision').value = '';
    document.getElementById('fechaVencimiento').value = '';
    document.getElementById('baseImponible').value = '';
    document.getElementById('iva').value = '';
    document.getElementById('total').value = '';
    document.getElementById('concepto').value = '';
}
