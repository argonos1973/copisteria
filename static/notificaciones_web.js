// Este script consulta notificaciones recientes y las muestra como alertas flotantes en la web

async function obtenerNotificaciones() {
    try {
        const resp = await fetch('/notificaciones');
        if (!resp.ok) return [];
        return await resp.json();
    } catch (e) {
        return [];
    }
}

function mostrarToastNotificacion(notificacion) {
    const toast = document.createElement('div');
    toast.className = `toast-notificacion toast-${notificacion.tipo}`;
    toast.innerHTML = `<strong>${notificacion.tipo.toUpperCase()}</strong>: ${notificacion.mensaje}`;
    document.body.appendChild(toast);
    setTimeout(() => toast.classList.add('mostrar'), 100);
    setTimeout(() => {
        toast.classList.remove('mostrar');
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

async function mostrarNotificacionesRecientes() {
    const notificaciones = await obtenerNotificaciones();
    notificaciones.reverse().slice(0, 5).forEach(mostrarToastNotificacion);
}

// Llama a esta función tras cargar la página o periódicamente
document.addEventListener('DOMContentLoaded', mostrarNotificacionesRecientes);
// Opcional: refresco periódico
setInterval(mostrarNotificacionesRecientes, 60000);

// CSS básico para los toast
const estiloToast = document.createElement('style');
estiloToast.textContent = `
.toast-notificacion {
  position: fixed;
  right: 24px;
  bottom: 24px;
  min-width: 220px;
  background: #2a5298;
  color: #fff;
  padding: 12px 18px;
  border-radius: 6px;
  margin-top: 8px;
  opacity: 0;
  transform: translateY(40px);
  transition: all 0.3s;
  z-index: 9999;
  box-shadow: 0 2px 12px rgba(0,0,0,0.18);
  font-size: 15px;
}
.toast-notificacion.mostrar {
  opacity: 1;
  transform: translateY(0);
}
.toast-success { background: #43a047; }
.toast-error { background: #c62828; }
.toast-warning { background: #f9a825; color: #222; }
.toast-info { background: #1976d2; }
`;
document.head.appendChild(estiloToast);
