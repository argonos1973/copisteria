// ============================================================================
// FUNCIONES PRINCIPALES DE LA APLICACIÓN
// ============================================================================

const API_URL = `http://${window.location.hostname}:5001/api`;
let notificacionesActuales = [];

// Función para cerrar sesión
async function cerrarSesion() {
    if (!confirm('¿Cerrar sesión?')) return;
    try {
        await fetch('/api/auth/logout', { method: 'POST' });
    } catch (error) {
        console.error('Error al cerrar sesión:', error);
    }
    window.location.href = '/LOGIN.html';
}

// Inyectar cabecera global en la página cargada del iframe
function injectHeader(doc) {
    if (!doc || !doc.body) return;
    
    // NO inyectar header si la página ya tiene .header (páginas de administración)
    if (doc.querySelector('.header')) {
        return;
    }
    
    let header = doc.querySelector('.page-header');
    if (!header) {
        const firstH1 = doc.querySelector('h1');
        const txt = firstH1 ? firstH1.textContent.trim() : (doc.title || '');
        if (firstH1) firstH1.remove();
        header = doc.createElement('div');
        header.className = 'page-header';
        // NO agregar estilos inline - usar CSS con variables de plantilla
        const h1 = doc.createElement('h1');
        h1.textContent = txt;
        header.appendChild(h1);
        doc.body.insertBefore(header, doc.body.firstChild);
    } else {
        // eliminar h1 sueltos para evitar duplicados
        doc.querySelectorAll('h1').forEach(el => {
            if (!header.contains(el)) el.remove();
        });
    }
}

// ============================================================================
// SISTEMA DE NOTIFICACIONES
// ============================================================================

async function inicializarNotificaciones() {
    // Verificar que los elementos existan
    const notifIcon = document.getElementById('notificaciones-icon');
    const notifPanel = document.getElementById('notificaciones-panel');
    
    if (!notifIcon || !notifPanel) {
        console.warn('[NOTIF] Elementos de notificaciones no encontrados');
        return;
    }
    
    // Cargar notificaciones al iniciar
    await cargarNotificaciones();
    
    // Actualizar cada 30 segundos
    setInterval(cargarNotificaciones, 30000);
    
    // Click en el icono
    notifIcon.addEventListener('click', toggleNotificaciones);
    
    // Cerrar al hacer click fuera
    document.addEventListener('click', (e) => {
        if (notifPanel.classList.contains('active') && 
            !notifPanel.contains(e.target) && 
            !notifIcon.contains(e.target)) {
            cerrarNotificaciones();
        }
    });
}

async function cargarNotificaciones() {
    try {
        const response = await fetch(`${API_URL}/conciliacion/notificaciones`);
        const data = await response.json();
        
        if (data.success) {
            notificacionesActuales = data.notificaciones;
            actualizarBadge(data.total);
        }
    } catch (error) {
        console.error('Error al cargar notificaciones:', error);
    }
}

function actualizarBadge(total) {
    const badge = document.getElementById('notificaciones-badge');
    
    if (!badge) {
        console.warn('[NOTIF] Badge de notificaciones no encontrado');
        return;
    }
    
    if (total > 0) {
        badge.textContent = total > 99 ? '99+' : total;
        badge.style.display = 'block';
    } else {
        badge.style.display = 'none';
    }
}

function toggleNotificaciones() {
    const panel = document.getElementById('notificaciones-panel');
    
    if (panel.classList.contains('active')) {
        cerrarNotificaciones();
    } else {
        abrirNotificaciones();
    }
}

function abrirNotificaciones() {
    const panel = document.getElementById('notificaciones-panel');
    const lista = document.getElementById('notificaciones-lista');
    const selectAllContainer = document.getElementById('select-all-container');
    const footer = document.getElementById('notif-footer');
    
    panel.classList.add('active');
    
    if (notificacionesActuales.length > 0) {
        // Mostrar checkbox "Todas" y footer
        selectAllContainer.style.display = 'flex';
        footer.style.display = 'block';
        
        lista.innerHTML = '';
        
        notificacionesActuales.forEach(notif => {
            const item = document.createElement('div');
            item.className = 'notif-item';
            item.dataset.id = notif.id;
            
            // Determinar si es notificación general o de conciliación
            if (notif.origen === 'general') {
                // Notificación general (facturas vencidas, cartas, etc.)
                const fecha = new Date(notif.fecha_conciliacion);
                const fechaStr = fecha.toLocaleDateString('es-ES');
                
                const iconos = {
                    'warning': 'fa-exclamation-triangle',
                    'info': 'fa-info-circle',
                    'success': 'fa-check-circle',
                    'error': 'fa-times-circle'
                };
                
                const colores = {
                    'warning': '#f39c12',
                    'info': '#3498db',
                    'success': '#27ae60',
                    'error': '#e74c3c'
                };
                
                const icono = iconos[notif.tipo] || 'fa-bell';
                const color = colores[notif.tipo] || '#95a5a6';
                
                item.innerHTML = `
                    <input type="checkbox" class="notif-checkbox" data-notif-id="${notif.id}" data-origen="${notif.origen}">
                    <div class="notif-content">
                        <div class="notif-title">
                            <i class="fas ${icono}" style="color: ${color};"></i>
                            ${notif.tipo === 'warning' ? 'Aviso' : 'Notificación'}
                        </div>
                        <div class="notif-desc">
                            ${notif.mensaje}
                        </div>
                        <div class="notif-time">
                            <i class="fas fa-calendar"></i> ${fechaStr}
                        </div>
                    </div>
                `;
            } else {
                // Notificación de conciliación
                // Convertir fecha DD/MM/YYYY a formato válido
                let fechaStr = 'Fecha no disponible';
                if (notif.fecha_operacion) {
                    if (notif.fecha_operacion.includes('/')) {
                        // Formato DD/MM/YYYY
                        fechaStr = notif.fecha_operacion;
                    } else {
                        // Formato YYYY-MM-DD
                        const fecha = new Date(notif.fecha_operacion + 'T00:00:00');
                        fechaStr = fecha.toLocaleDateString('es-ES');
                    }
                }
                
                const importe = new Intl.NumberFormat('es-ES', {
                    style: 'currency',
                    currency: 'EUR'
                }).format(notif.importe_gasto);
                
                const tipoNotif = notif.metodo === 'manual' ? 'manual' : 'automática';
                const metodoLabel = notif.metodo === 'manual' ? 'Manual' : 'Auto';
                
                item.innerHTML = `
                    <input type="checkbox" class="notif-checkbox" data-notif-id="${notif.id}" data-origen="${notif.origen}">
                    <div class="notif-content clickable">
                        <div class="notif-title">
                            <i class="fas fa-check-circle" style="color: #27ae60;"></i>
                            Conciliación ${tipoNotif}
                        </div>
                        <div class="notif-desc">
                            ${notif.concepto_gasto || 'Gasto bancario'} (${importe}) 
                            → ${notif.tipo_documento ? notif.tipo_documento.toUpperCase() : ''} ${notif.numero_documento || ''}
                        </div>
                        <div class="notif-time">
                            <i class="fas fa-calendar"></i> ${fechaStr}
                            <span style="color: ${notif.metodo === 'manual' ? '#f39c12' : '#27ae60'};"> • ${metodoLabel}</span>
                        </div>
                    </div>
                `;
                
                // Solo el contenido navega, no el checkbox
                item.querySelector('.notif-content').addEventListener('click', () => {
                    document.getElementById('content-frame').src = 'CONCILIACION_GASTOS.html';
                    cerrarNotificaciones();
                });
            }
            
            lista.appendChild(item);
        });
    } else {
        // Ocultar checkbox "Todas" y footer
        selectAllContainer.style.display = 'none';
        footer.style.display = 'none';
        
        lista.innerHTML = `
            <div class="notif-empty">
                <i class="fas fa-check-circle" style="font-size: 32px; color: #ddd;"></i>
                <p>No hay notificaciones nuevas</p>
            </div>
        `;
    }
}

function cerrarNotificaciones() {
    document.getElementById('notificaciones-panel').classList.remove('active');
}

function toggleSeleccionarTodas() {
    const selectAll = document.getElementById('select-all-notif');
    const checkboxes = document.querySelectorAll('.notif-checkbox');
    checkboxes.forEach(cb => cb.checked = selectAll.checked);
}

async function marcarSeleccionadasLeidas() {
    const checkboxes = document.querySelectorAll('.notif-checkbox:checked');
    
    console.log('Checkboxes seleccionados:', checkboxes.length);
    
    if (checkboxes.length === 0) {
        alert('Selecciona al menos una notificación para marcar como leída');
        return;
    }
    
    try {
        // Separar notificaciones generales de conciliación
        const notifGenerales = [];
        const notifConciliacion = [];
        
        checkboxes.forEach(cb => {
            const id = parseInt(cb.dataset.notifId);
            const origen = cb.dataset.origen;
            
            console.log('Procesando:', id, origen);
            
            if (origen === 'general') {
                notifGenerales.push(id);
            } else {
                notifConciliacion.push(id);
            }
        });
        
        console.log('Notif generales:', notifGenerales);
        console.log('Notif conciliación:', notifConciliacion);
        
        // Eliminar notificaciones generales
        if (notifGenerales.length > 0) {
            console.log('Eliminando notificaciones generales...');
            const response = await fetch(`${API_URL}/notificaciones/eliminar`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ ids: notifGenerales })
            });
            
            const data = await response.json();
            console.log('Respuesta eliminar:', data);
            
            if (!response.ok) throw new Error('Error al eliminar notificaciones generales');
        }
        
        // Marcar conciliaciones como notificadas
        if (notifConciliacion.length > 0) {
            console.log('Marcando conciliaciones...');
            const response = await fetch(`${API_URL}/conciliacion/marcar-notificadas`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ ids: notifConciliacion })
            });
            
            const data = await response.json();
            console.log('Respuesta marcar:', data);
            
            if (!response.ok) throw new Error('Error al marcar conciliaciones');
        }
        
        console.log('Recargando notificaciones...');
        // Recargar notificaciones
        await cargarNotificaciones();
        
        // Si el panel está abierto, actualizar su contenido
        const panel = document.getElementById('notificaciones-panel');
        if (panel.classList.contains('active')) {
            abrirNotificaciones();
        }
        
        document.getElementById('select-all-notif').checked = false;
        
    } catch (error) {
        console.error('Error completo:', error);
        alert('Error al marcar notificaciones como leídas: ' + error.message);
    }
}

async function marcarTodasLeidas() {
    if (notificacionesActuales.length === 0) return;
    
    try {
        const ids = notificacionesActuales.map(n => n.id);
        
        const response = await fetch(`${API_URL}/conciliacion/marcar-notificadas`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ids })
        });
        
        const data = await response.json();
        
        if (data.success) {
            notificacionesActuales = [];
            actualizarBadge(0);
            cerrarNotificaciones();
        }
    } catch (error) {
        console.error('Error al marcar como leídas:', error);
    }
}

// ============================================================================
// INICIALIZACIÓN DE LA APLICACIÓN
// ============================================================================

document.addEventListener('DOMContentLoaded', async () => {
    console.log('[INIT] Iniciando aplicación...');
    await verificarSesionYCargarMenu();
    
    const iframe = document.getElementById('content-frame');
    iframe.addEventListener('load', () => {
        // Scroll en el propio iframe
        iframe.style.overflow = 'auto';
        iframe.style.overflowY = 'scroll';

        try {
            const iframeURL = new URL(iframe.src, window.location.href);
            if (iframeURL.origin === window.location.origin) {
                const doc = iframe.contentDocument || iframe.contentWindow.document;
                injectHeader(doc);
            }
        } catch(_) {/* ignorar cross-origin */}

        // Ajustar overflow del documento interno
        try {
            const iframeURL = new URL(iframe.src, window.location.href);
            if (iframeURL.origin === window.location.origin) {
                const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
                if (iframeDoc && iframeDoc.body) {
                    iframeDoc.body.style.overflowY = 'auto';
                    iframeDoc.body.style.minHeight = '100vh';
                }
            }
        } catch (_) {
            /* Distinto origen: no hacemos nada para evitar SecurityError */
        }
    });
    
    // Sistema de notificaciones de conciliación
    inicializarNotificaciones();
});

// Exportar funciones globales
window.cerrarSesion = cerrarSesion;
window.cerrarNotificaciones = cerrarNotificaciones;
window.toggleSeleccionarTodas = toggleSeleccionarTodas;
window.marcarSeleccionadasLeidas = marcarSeleccionadasLeidas;
window.marcarTodasLeidas = marcarTodasLeidas;
