// Iconos para cada tipo de notificación
const ICONOS = {
    success: '✓',
    error: '✕',
    warning: '⚠',
    info: 'ℹ'
};

// Cola de notificaciones
let notificacionesActivas = [];
const MAX_NOTIFICACIONES = 4;

// Función para mostrar notificaciones
export function mostrarNotificacion(mensaje, tipo = 'info') {
    let contenedor = document.getElementById('notificaciones-contenedor');
    if (!contenedor) {
        const contenedorNuevo = document.createElement('div');
        contenedorNuevo.id = 'notificaciones-contenedor';
        contenedorNuevo.className = 'notificaciones-contenedor';
        // Estilos inline por si el CSS no se ha cargado
        contenedorNuevo.style.position = 'fixed';
        contenedorNuevo.style.top = '20px';
        contenedorNuevo.style.right = '20px';
        contenedorNuevo.style.display = 'flex';
        contenedorNuevo.style.flexDirection = 'column';
        contenedorNuevo.style.gap = '10px';
        contenedorNuevo.style.zIndex = '10000';
        document.body.appendChild(contenedorNuevo);
    }

    const notificacion = document.createElement('div');
    notificacion.className = `notificacion ${tipo}`;
    notificacion.textContent = mensaje;
    
    contenedor = document.getElementById('notificaciones-contenedor');
    contenedor.appendChild(notificacion);
    
    notificacionesActivas.push(notificacion);

    if (notificacionesActivas.length > MAX_NOTIFICACIONES) {
        const notificacionAntigua = notificacionesActivas.shift();
        notificacionAntigua.remove();
    }

    setTimeout(() => {
        notificacion.classList.add('visible');
    }, 100);
    
    setTimeout(() => {
        notificacion.classList.remove('visible');
        setTimeout(() => {
            notificacion.remove();
            notificacionesActivas = notificacionesActivas.filter(n => n !== notificacion);
            
            // Limpiar el contenedor si no hay más notificaciones
            let contenedor = document.getElementById('notificaciones-contenedor');
            if (contenedor && !contenedor.hasChildNodes()) {
                contenedor.remove();
            }
        }, 300);
    }, 3000);
}

function cerrarNotificacion(notificacion) {
    // Añadir animación de salida
    notificacion.style.animation = 'slideOut 0.5s ease-out';
    
    // Eliminar la notificación después de la animación
    setTimeout(() => {
        if (notificacion.parentElement) {
            notificacion.parentElement.removeChild(notificacion);
        }
        notificacionesActivas = notificacionesActivas.filter(n => n !== notificacion);
        
        // Limpiar el contenedor si no hay más notificaciones
        let contenedor = document.getElementById('notificaciones-contenedor');
        if (contenedor && !contenedor.hasChildNodes()) {
            contenedor.remove();
        }
    }, 500);
}

// Función para limpiar todas las notificaciones
export function limpiarNotificaciones() {
    let contenedor = document.getElementById('notificaciones-contenedor');
    if (contenedor) {
        notificacionesActivas.forEach(notificacion => cerrarNotificacion(notificacion));
    }
}

// Función para mostrar diálogo de confirmación
export function mostrarConfirmacion(mensaje) {
    return new Promise((resolve) => {
        const overlay = document.createElement('div');
        overlay.className = 'confirmacion-overlay';
        
        const dialog = document.createElement('div');
        dialog.className = 'confirmacion-dialog';
        
        const mensajeElement = document.createElement('p');
        mensajeElement.textContent = mensaje;
        
        const buttonContainer = document.createElement('div');
        buttonContainer.className = 'confirmacion-buttons';
        
        const guardarBtn = document.createElement('button');
        guardarBtn.textContent = 'Guardar';
        guardarBtn.className = 'btn-confirmar';
        
        const cancelarBtn = document.createElement('button');
        cancelarBtn.textContent = 'Cancelar';
        cancelarBtn.className = 'btn-cancelar';
        
        buttonContainer.appendChild(guardarBtn);
        buttonContainer.appendChild(cancelarBtn);
        
        dialog.appendChild(mensajeElement);
        dialog.appendChild(buttonContainer);
        overlay.appendChild(dialog);
        
        document.body.appendChild(overlay);
        
        const cleanup = () => {
            document.body.removeChild(overlay);
        };
        
        guardarBtn.onclick = () => {
            cleanup();
            resolve(true);  // Guardar y navegar
        };
        
        cancelarBtn.onclick = () => {
            cleanup();
            resolve(null);  // Cancelar: NO navegar, quedarse en página
        };
    });
}

// SSE eliminado: no se conecta a ningún endpoint de notificaciones